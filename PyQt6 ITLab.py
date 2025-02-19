from PyQt6 import QtWidgets, QtGui, QtCore
import pymysql
import os

class DatabaseViewer(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("База данных Фото")
        self.setGeometry(100, 100, 1200, 700)  
        
        
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b8d99, stop:1 #003366);
                color: white;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            QTableWidget {
                font-size: 16px;
                background-color: rgba(0, 0, 0, 0.85);  # Сделали фон таблицы темным (почти черным)
                border: 1px solid #00b5e2;
                border-radius: 10px;
            }
            QTableWidget::item {
                padding: 12px;
                border-radius: 5px;
            }
            QTableWidget::item:selected {
                background-color: #00b5e2;
                color: black;
            }
            QHeaderView::section {
                background-color: #003366;
                padding: 8px;
                font-size: 18px;
                font-weight: bold;
                border: none;
            }
            QTableWidget::horizontalHeader {
                background-color: #003366;
            }
            QLabel {
                border: 2px solid #00b5e2;
                padding: 5px;
                background-color: rgba(0, 0, 0, 0.6);
            }
        """)

        self.layout = QtWidgets.QVBoxLayout()
        self.table = QtWidgets.QTableWidget()
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        
        self.load_data()
    
    def load_data(self):
        try:
            # Используем pymysql для подключения к базе данных
            conn = pymysql.connect(
                host="localhost",
                user="root",
                password="Dorogusha1",  
                database="JupiterDB"
            )
            cursor = conn.cursor()
            cursor.execute("SELECT id, original_path, compressed_path, original_size, compressed_size FROM Photos")
            
            rows = cursor.fetchall()
            conn.close()
            
            self.table.setRowCount(len(rows))
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["ID", "Фото", "Сжатое Фото", "Размер", "Сжатый размер", "Разрешение"])

            
            self.table.setColumnWidth(0, 180)
            self.table.setColumnWidth(1, 250)
            self.table.setColumnWidth(2, 250)
            self.table.setColumnWidth(3, 200)
            self.table.setColumnWidth(4, 200)
            self.table.setColumnWidth(5, 220)
            
            for row_idx, row_data in enumerate(rows):
                for col_idx, col_data in enumerate(row_data):
                    item = QtWidgets.QTableWidgetItem(str(col_data))
                    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                    if col_idx == 0:
                        item.setForeground(QtGui.QBrush(QtGui.QColor("#ffffff")))  
                    self.table.setItem(row_idx, col_idx, item)
                    
                self.table.item(row_idx, 0).setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
                self.table.item(row_idx, 0).setForeground(QtGui.QBrush(QtGui.QColor("#ffffff")))  # ID - белый
                self.table.item(row_idx, 0).setFont(QtGui.QFont("Segoe UI", 14, QtGui.QFont.Weight.Bold))
            
            self.table.cellClicked.connect(self.show_image)
        except pymysql.MySQLError as err:
            print(f"Ошибка подключения к БД: {err}")
    
    def show_image(self, row, col):
        if col == 0:
            image_path = self.table.item(row, 1).text()
            if os.path.exists(image_path):
                self.display_image(image_path)
    
    def display_image(self, path):
        image_viewer = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(path)
        image_viewer.setPixmap(pixmap)
        image_viewer.setScaledContents(True)
        image_viewer.setWindowTitle("Просмотр изображения")
        image_viewer.resize(600, 400)
        image_viewer.setStyleSheet("background-color: #000; border: 2px solid #00b5e2;")
        image_viewer.show()
        self.image_viewer = image_viewer

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    viewer = DatabaseViewer()
    viewer.show()
    sys.exit(app.exec())
