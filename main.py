import sys
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QTextEdit, QPushButton, QVBoxLayout, QWidget, QMessageBox, QDateEdit, QScrollArea, QHBoxLayout
from PyQt5.QtCore import Qt, QDate
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtGui import QFontDatabase, QFont, QColor

import matplotlib as mpl
from matplotlib.font_manager import FontProperties

# 設置中文字型
try:
    font = FontProperties(fname=r'/System/Library/Fonts/PingFang.ttc')
except:
    font = FontProperties()

mpl.rcParams['font.family'] = font.get_name()

class PortfolioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("投資組合比較")
        self.setGeometry(100, 100, 800, 600)

        self.setStyleSheet("background-color: #1e1e2f; color: white;")
        
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)

        # 設置當前日期
        today = QDate.currentDate()

        self.start_date_label = QLabel("開始日期:", self)
        self.start_date_input = QDateEdit(self)
        self.start_date_input.setDate(today)
        self.start_date_input.setCalendarPopup(True)

        self.end_date_label = QLabel("結束日期:", self)
        self.end_date_input = QDateEdit(self)
        self.end_date_input.setDate(today)
        self.end_date_input.setCalendarPopup(True)

        self.portfolio_label = QLabel("投資組合 (使用Python字典格式):", self)
        self.portfolio_input = QTextEdit(self)
        self.portfolio_input.setStyleSheet("border: 2px solid white; color: white; background-color: #2e2e3e;")
        self.portfolio_input.setText(
            "{\n"
            "    'Portfolio A': {'TSLA': 0.4, 'MSFT': 0.3, 'AMZN': 0.3},\n"
            "    'Portfolio B': {'GOOGL': 0.5, 'META': 0.5},\n"
            "}"
        )

        self.compare_button = QPushButton("比較", self)
        self.compare_button.setStyleSheet("background-color: #2d8cf0; color: white;")
        self.compare_button.clicked.connect(self.compare_portfolios)

        layout = QVBoxLayout()
        layout.addWidget(self.start_date_label)
        layout.addWidget(self.start_date_input)
        layout.addWidget(self.end_date_label)
        layout.addWidget(self.end_date_input)
        layout.addWidget(self.portfolio_label)
        layout.addWidget(self.portfolio_input)
        layout.addWidget(self.compare_button)

        # 繪圖區域
        self.figure = plt.Figure(facecolor='#1e1e2f')
        self.canvas = FigureCanvas(self.figure)

        # 包裝繪圖區域和滾動條
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.addWidget(self.canvas)
        scroll_area.setWidget(scroll_content)

        layout.addWidget(scroll_area)

        main_widget.setLayout(layout)

    def get_stock_data(self, tickers, start_date, end_date):
        try:
            data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']
            if data.empty:
                raise ValueError("未能獲取股票數據。請檢查股票代碼和日期範圍。")
            return data
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"獲取股票數據時出錯: {e}")
            return None

    def calculate_portfolio_return(self, data, weights):
        returns = data.pct_change()
        portfolio_return = (returns * weights).sum(axis=1)
        cumulative_return = (1 + portfolio_return).cumprod() - 1
        return cumulative_return

    def compare_portfolios(self):
        start_date = self.start_date_input.date().toString("yyyy-MM-dd")
        end_date = self.end_date_input.date().toString("yyyy-MM-dd")
        try:
            portfolios = eval(self.portfolio_input.toPlainText())
            results = self.compare_portfolios_data(portfolios, start_date, end_date)
            if results is not None:
                self.plot_results(results, portfolios)
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"處理投資組合時出錯: {e}")

    def compare_portfolios_data(self, portfolios, start_date, end_date):
        all_tickers = list(set([ticker for portfolio in portfolios.values() for ticker in portfolio.keys()]))
        data = self.get_stock_data(all_tickers, start_date, end_date)
        if data is None:
            return None
        
        results = {}
        for name, portfolio in portfolios.items():
            if isinstance(data, pd.Series):
                weights = np.array([portfolio.get(data.name, 0)])
            else:
                weights = np.array([portfolio.get(ticker, 0) for ticker in data.columns])
            results[name] = self.calculate_portfolio_return(data, weights)
        
        return pd.DataFrame(results)

    def plot_results(self, results, portfolios):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#1e1e2f')
        ax.tick_params(colors='white')
        final_returns = results.iloc[-1] * 100
        for portfolio in results.columns:
            line, = ax.plot(results.index, results[portfolio] * 100, label=portfolio)
            ax.annotate(f'{final_returns[portfolio]:.2f}%', 
                        xy=(results.index[-1], results[portfolio].iloc[-1] * 100),
                        xytext=(10, 0), 
                        textcoords='offset points',
                        ha='left',
                        va='center',
                        color=line.get_color())
        
        ax.set_title('投資組合表現比較', fontsize=16, color='white')
        ax.set_xlabel('日期', fontsize=12, color='white')
        ax.set_ylabel('累積報酬率 (%)', fontsize=12, color='white')
        
        # 仅显示投资组合名称，不显示股票代号及权重
        custom_legend = list(portfolios.keys())
        
        # 将图例放置在图表内部左上方
        ax.legend(custom_legend, loc='upper left', fontsize=10, frameon=True, facecolor='lightgray', edgecolor='gray')
        ax.grid(True, color='gray', linestyle='--', linewidth=0.5)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.0f}%'.format(y)))

        # 调整布局以防止日期标签被截断
        self.figure.tight_layout()

        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PortfolioApp()
    window.show()
    sys.exit(app.exec_())
