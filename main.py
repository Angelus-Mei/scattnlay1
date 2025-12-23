import sys
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# 尝试导入 scattnlay，失败则提示
try:
    from scattnlay import scattnlay
except ImportError:
    pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scattnlay Mie Calculator")
        self.resize(1000, 800)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # 左侧控制
        control_panel = QVBoxLayout()
        layout.addLayout(control_panel, 1)
        
        # 参数
        gb_global = QGroupBox("参数")
        gb_layout = QVBoxLayout()
        self.inp_wl = self.add_inp("波长 (nm):", "532.0", gb_layout)
        self.inp_n = self.add_inp("环境 n:", "1.0", gb_layout)
        gb_global.setLayout(gb_layout)
        control_panel.addWidget(gb_global)

        # 表格
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["半径(nm)", "实部 n", "虚部 k"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        control_panel.addWidget(self.table)
        
        # 按钮
        btn_add = QPushButton("添加层")
        btn_add.clicked.connect(self.add_layer)
        control_panel.addWidget(btn_add)
        
        self.btn_calc = QPushButton("计算")
        self.btn_calc.setStyleSheet("background-color:blue; color:white; font-weight:bold;")
        self.btn_calc.clicked.connect(self.run_calc)
        control_panel.addWidget(self.btn_calc)
        
        self.lbl_res = QLabel("结果区")
        self.lbl_res.setWordWrap(True)
        control_panel.addWidget(self.lbl_res)
        control_panel.addStretch()

        # 右侧绘图
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas, 2)
        
        self.add_layer("100", "1.33", "0")

    def add_inp(self, txt, val, lay):
        h = QHBoxLayout()
        h.addWidget(QLabel(txt))
        inp = QLineEdit(val)
        h.addWidget(inp)
        lay.addLayout(h)
        return inp

    def add_layer(self, r=None, n=None, k=None):
        rr = self.table.rowCount()
        self.table.insertRow(rr)
        self.table.setItem(rr, 0, QTableWidgetItem(r if r else "150"))
        self.table.setItem(rr, 1, QTableWidgetItem(n if n else "1.5"))
        self.table.setItem(rr, 2, QTableWidgetItem(k if k else "0.0"))

    def run_calc(self):
        try:
            wl = float(self.inp_wl.text())
            n_env = float(self.inp_n.text())
            radii, ms = [], []
            for i in range(self.table.rowCount()):
                radii.append(float(self.table.item(i,0).text()))
                ms.append(complex(float(self.table.item(i,1).text()), float(self.table.item(i,2).text())))
            
            x = np.array([[2*np.pi*r*n_env/wl for r in radii]], dtype=np.float64)
            m = np.array([[mm/n_env for mm in ms]], dtype=np.complex128)
            theta = np.linspace(0, np.pi, 500, dtype=np.float64)
            
            terms, Qext, Qsca, Qabs, Qbk, Qpr, g, Albedo, S1, S2 = scattnlay(x, m, theta)
            
            self.lbl_res.setText(f"Qext: {Qext[0]:.4f}\nQsca: {Qsca[0]:.4f}\ng: {g[0]:.4f}")
            
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.semilogy(np.degrees(theta), (np.abs(S1[0])**2 + np.abs(S2[0])**2)/2, 'r')
            ax.set_title("Scattering Intensity")
            self.canvas.draw()
        except Exception as e:
            QMessageBox.critical(self, "Err", str(e))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
