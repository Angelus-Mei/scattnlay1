import sys
import numpy as np
import PyMieScatt as ps  # 替换 scattnlay
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mie Calculator (PyMieScatt)")
        self.resize(1000, 800)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # 左侧控制
        control_panel = QVBoxLayout()
        layout.addLayout(control_panel, 1)
        
        # 参数
        gb_global = QGroupBox("环境参数")
        gb_layout = QVBoxLayout()
        self.inp_wl = self.add_inp("波长 (nm):", "532.0", gb_layout)
        self.inp_n = self.add_inp("环境折射率 n:", "1.0", gb_layout)
        gb_global.setLayout(gb_layout)
        control_panel.addWidget(gb_global)

        # 表格
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["直径(nm)", "实部 n", "虚部 k"]) # PyMieScatt使用直径
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        control_panel.addWidget(self.table)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("添加层")
        btn_add.clicked.connect(self.add_layer)
        btn_reset = QPushButton("重置")
        btn_reset.clicked.connect(self.reset_table)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_reset)
        control_panel.addLayout(btn_layout)
        
        # 说明
        lbl_note = QLabel("注意: 此版本支持单球(1层)或核壳结构(2层)。\n请输入'直径'而不是半径。")
        lbl_note.setStyleSheet("color: gray; font-size: 10px;")
        control_panel.addWidget(lbl_note)
        
        self.btn_calc = QPushButton("计算")
        self.btn_calc.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold; height: 40px;")
        self.btn_calc.clicked.connect(self.run_calc)
        control_panel.addWidget(self.btn_calc)
        
        self.lbl_res = QLabel("结果显示区")
        self.lbl_res.setStyleSheet("border: 1px solid #ddd; padding: 10px; background: #f8f8f8;")
        self.lbl_res.setWordWrap(True)
        control_panel.addWidget(self.lbl_res)
        control_panel.addStretch()

        # 右侧绘图
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas, 2)
        
        # 默认初始化一个核壳结构
        self.add_layer("200", "1.5", "0.0") # Core
        self.add_layer("300", "1.33", "0.0") # Shell

    def add_inp(self, txt, val, lay):
        h = QHBoxLayout()
        h.addWidget(QLabel(txt))
        inp = QLineEdit(val)
        h.addWidget(inp)
        lay.addLayout(h)
        return inp

    def add_layer(self, d=None, n=None, k=None):
        if self.table.rowCount() >= 2:
            QMessageBox.warning(self, "限制", "PyMieScatt 版本仅支持最多 2 层 (Core-Shell)。")
            return
        rr = self.table.rowCount()
        self.table.insertRow(rr)
        # 默认值
        self.table.setItem(rr, 0, QTableWidgetItem(d if d else "200"))
        self.table.setItem(rr, 1, QTableWidgetItem(n if n else "1.5"))
        self.table.setItem(rr, 2, QTableWidgetItem(k if k else "0.0"))
        
    def reset_table(self):
        self.table.setRowCount(0)
        self.add_layer("200", "1.5", "0")

    def run_calc(self):
        try:
            wl = float(self.inp_wl.text())
            n_env = float(self.inp_n.text())
            n_layers = self.table.rowCount()

            if n_layers == 0:
                return

            # 获取层数据
            ds = [] # 直径
            ms = [] # 折射率
            for i in range(n_layers):
                d_val = float(self.table.item(i,0).text())
                n_val = float(self.table.item(i,1).text())
                k_val = float(self.table.item(i,2).text())
                ds.append(d_val)
                ms.append(complex(n_val, k_val))

            Qext, Qsca, Qabs, g, Qback = 0, 0, 0, 0, 0
            theta = np.linspace(0, np.pi, 300)
            
            # --- 核心计算逻辑 ---
            if n_layers == 1:
                # 单球 Mie
                # PyMieScatt 需要将环境折射率考虑进去：m_rel = m_particle / m_env
                # 波长也要调整：lambda_env = lambda_vac / m_env
                # 但 PyMieScatt 的 MieQ 函数通常接受相对折射率
                
                m_rel = ms[0] / n_env
                d_real = ds[0]
                
                # 计算效率因子
                Qext, Qsca, Qabs, g, Qback, Qratio, Qpr = ps.MieQ(m_rel, wl, d_real, nMedium=n_env, asDict=False)
                
                # 计算散射相函数
                # PyMieScatt 的 ScatteringFunction 返回 theta, SL, SR, SU
                theta_p, SL, SR, SU = ps.ScatteringFunction(m_rel, wl, d_real, nMedium=n_env, minAngle=0, maxAngle=180, angularResolution=0.5)
                
                # 强度 (非偏振) = SU
                intensity = SU

            elif n_layers == 2:
                # 核-壳 Mie
                # Core: index 0, Shell: index 1
                # 需注意：PyMieScatt CoreShell 定义中，Shell 直径是整体直径
                d_core = ds[0]
                d_shell = ds[1]
                
                if d_core >= d_shell:
                    QMessageBox.warning(self, "尺寸错误", "外壳直径必须大于核心直径！")
                    return

                m_core = ms[0]
                m_shell = ms[1]
                
                # 效率因子
                Qext, Qsca, Qabs, g, Qback, Qratio, Qpr = ps.MieQCoreShell(m_core, m_shell, wl, d_core, d_shell, nMedium=n_env, asDict=False)
                
                # 相函数 CoreShellScatteringFunction
                theta_p, SL, SR, SU = ps.CoreShellScatteringFunction(m_core, m_shell, wl, d_core, d_shell, nMedium=n_env, minAngle=0, maxAngle=180, angularResolution=0.5)
                intensity = SU

            # 更新文字
            res_txt = (f"Qext: {Qext:.4f}\n"
                       f"Qsca: {Qsca:.4f}\n"
                       f"Qabs: {Qabs:.4f}\n"
                       f"Qback: {Qback:.4f}\n"
                       f"g (不对称): {g:.4f}")
            self.lbl_res.setText(res_txt)
            
            # 绘图
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            
            # theta_p 是弧度，转为角度
            angles = np.degrees(theta_p)
            
            ax.plot(angles, intensity, 'r-', label='Intensity (Unpolarized)')
            ax.set_yscale('log')
            ax.set_xlabel('Scattering Angle (deg)')
            ax.set_ylabel('Intensity (a.u.)')
            ax.set_title(f'Scattering Pattern ({n_layers} Layers)')
            ax.grid(True, which="both", alpha=0.3)
            ax.legend()
            
            self.canvas.draw()
            
        except Exception as e:
            QMessageBox.critical(self, "计算错误", str(e))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
