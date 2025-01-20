import json
import subprocess
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QTabWidget, QApplication, QMessageBox
)
from setup_proxy_and_mitm import launch_proxy, disable_windows_proxy


class UserDashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Content Monitoring - User Mode')

        # File to store blocked sites
        self.blocked_sites_file = 'blocked_sites.json'

        # Load blocked sites from file
        self.blocked_sites, self.excluded_sites = self.load_blocked_sites()

        # Create tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_blocked_sites_tab(), "Blocked Sites")
        self.tab_widget.addTab(self.create_excluded_sites_tab(), "Excluded Sites")

        self.setCentralWidget(self.tab_widget)

    def create_blocked_sites_tab(self):
        # Blocked sites table
        self.blocked_table = QTableWidget()
        self.blocked_table.setColumnCount(1)
        self.blocked_table.setHorizontalHeaderLabels(['Blocked Sites'])
        self.populate_blocked_table()

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.blocked_table)

        container = QWidget()
        container.setLayout(layout)
        return container

    def create_excluded_sites_tab(self):
        # Excluded sites table
        self.excluded_table = QTableWidget()
        self.excluded_table.setColumnCount(1)
        self.excluded_table.setHorizontalHeaderLabels(['Excluded Sites'])
        self.populate_excluded_table()

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.excluded_table)

        container = QWidget()
        container.setLayout(layout)
        return container

    def load_blocked_sites(self):
        try:
            with open(self.blocked_sites_file, 'r') as file:
                data = json.load(file)
                return data.get("sites", []), data.get("excluded_sites", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return [], []

    def populate_blocked_table(self):
        self.blocked_table.setRowCount(0)
        for site in self.blocked_sites:
            self.add_to_blocked_table(site)

    def add_to_blocked_table(self, site):
        row_position = self.blocked_table.rowCount()
        self.blocked_table.insertRow(row_position)
        self.blocked_table.setItem(row_position, 0, QTableWidgetItem(site))

    def populate_excluded_table(self):
        self.excluded_table.setRowCount(0)
        for site in self.excluded_sites:
            self.add_to_excluded_table(site)

    def add_to_excluded_table(self, site):
        row_position = self.excluded_table.rowCount()
        self.excluded_table.insertRow(row_position)
        self.excluded_table.setItem(row_position, 0, QTableWidgetItem(site))

    def closeEvent(self, event):
        """Handle the window close event to disable the proxy."""
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

    # Launch the proxy and start the GUI
    launch_proxy()
    app = QApplication(sys.argv)
    window = UserDashboardWindow()
    window.show()
    sys.exit(app.exec())