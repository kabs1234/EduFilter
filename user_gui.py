import json
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QTabWidget, QApplication, QMessageBox
)
from setup_proxy_and_mitm import launch_proxy, disable_windows_proxy


class SiteTable(QTableWidget):
    def __init__(self, header_label):
        super().__init__()
        self.setColumnCount(1)
        self.setHorizontalHeaderLabels([header_label])

    def populate(self, sites):
        self.setRowCount(0)
        for site in sites:
            self.add_site(site)

    def add_site(self, site):
        row_position = self.rowCount()
        self.insertRow(row_position)
        self.setItem(row_position, 0, QTableWidgetItem(site))


class UserDashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Content Monitoring - User Mode')
        self.blocked_sites_file = 'blocked_sites.json'
        self.blocked_sites, self.excluded_sites = self.load_data()
        self.setup_ui()

    def setup_ui(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_blocked_sites_tab(), "Blocked Sites")
        self.tab_widget.addTab(self.create_excluded_sites_tab(), "Excluded Sites")
        self.setCentralWidget(self.tab_widget)

    def create_blocked_sites_tab(self):
        self.blocked_table = SiteTable('Blocked Sites')
        self.blocked_table.populate(self.blocked_sites)
        return self.create_tab_layout(self.blocked_table)

    def create_excluded_sites_tab(self):
        self.excluded_table = SiteTable('Excluded Sites')
        self.excluded_table.populate(self.excluded_sites)
        return self.create_tab_layout(self.excluded_table)

    def create_tab_layout(self, table_widget):
        layout = QVBoxLayout()
        layout.addWidget(table_widget)
        container = QWidget()
        container.setLayout(layout)
        return container

    def load_data(self):
        try:
            with open(self.blocked_sites_file, 'r') as file:
                data = json.load(file)
                return data.get("sites", []), data.get("excluded_sites", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return [], []

    def closeEvent(self, event):
        confirmation = QMessageBox.question(
            self, "Confirm Exit", "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirmation == QMessageBox.StandardButton.Yes:
            disable_windows_proxy()
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    import sys
    launch_proxy()
    app = QApplication(sys.argv)
    window = UserDashboardWindow()
    window.show()
    sys.exit(app.exec())