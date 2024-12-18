from PyQt6.QtWidgets import QMainWindow, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QPushButton, QWidget
from filter_settings import FilterSettingsWindow  # Import LoginWindow from login_window.py


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Content Monitoring Dashboard')

        # Content Table
        self.content_table = QTableWidget(self)
        self.content_table.setRowCount(3)
        self.content_table.setColumnCount(2)
        self.content_table.setHorizontalHeaderLabels(['Content', 'Status'])
        self.populate_content_table()

        # Alert Panel
        self.alert_label = QLabel("No alerts", self)

        # Filter Settings Button
        self.filter_settings_button = QPushButton('Filter Settings', self)
        self.filter_settings_button.clicked.connect(self.open_filter_settings)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.content_table)
        layout.addWidget(self.alert_label)
        layout.addWidget(self.filter_settings_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def populate_content_table(self):
        # Sample content for demo
        self.content_table.setItem(0, 0, QTableWidgetItem("http://example.com"))
        self.content_table.setItem(0, 1, QTableWidgetItem("Blocked"))

        self.content_table.setItem(1, 0, QTableWidgetItem("http://safe-content.com"))
        self.content_table.setItem(1, 1, QTableWidgetItem("Safe"))

        self.content_table.setItem(2, 0, QTableWidgetItem("http://bad-site.com"))
        self.content_table.setItem(2, 1, QTableWidgetItem("Blocked"))

    def open_filter_settings(self):
        self.filter_settings_window = FilterSettingsWindow()
        self.filter_settings_window.show()
