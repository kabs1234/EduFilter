import json
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QPushButton, QWidget, QLineEdit, QDialog, QFormLayout, QMessageBox, QInputDialog
)
from setup_proxy_and_mitm import launch_proxy, disable_windows_proxy
import subprocess


class AddSiteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Site')
        self.layout = QFormLayout()

        self.site_input = QLineEdit(self)
        self.layout.addRow("Site URL:", self.site_input)

        self.add_button = QPushButton("Add", self)
        self.add_button.clicked.connect(self.accept)
        self.layout.addWidget(self.add_button)

        self.setLayout(self.layout)

    def get_input(self):
        return self.site_input.text()


class ExcludedSitesDialog(QDialog):
    def __init__(self, excluded_sites, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Excluded Sites')
        self.excluded_sites = excluded_sites
        self.parent = parent  # Reference to the parent (DashboardWindow)

        self.layout = QVBoxLayout()

        self.excluded_table = QTableWidget(self)
        self.excluded_table.setColumnCount(1)
        self.excluded_table.setHorizontalHeaderLabels(['Excluded Sites'])
        self.populate_excluded_table()

        self.add_site_button = QPushButton('Add Site', self)
        self.add_site_button.clicked.connect(self.open_add_site_dialog)

        self.delete_site_button = QPushButton('Delete Site', self)
        self.delete_site_button.clicked.connect(self.delete_selected_site)

        self.layout.addWidget(self.excluded_table)
        self.layout.addWidget(self.add_site_button)
        self.layout.addWidget(self.delete_site_button)

        self.setLayout(self.layout)

    def populate_excluded_table(self):
        self.excluded_table.setRowCount(0)  # Clear existing rows
        for site in self.excluded_sites:
            self.add_to_excluded_table(site)

    def add_to_excluded_table(self, site):
        row_position = self.excluded_table.rowCount()
        self.excluded_table.insertRow(row_position)
        self.excluded_table.setItem(row_position, 0, QTableWidgetItem(site))

    def open_add_site_dialog(self):
        dialog = AddSiteDialog(self)
        if dialog.exec():
            site = dialog.get_input()
            if site:
                if site in self.excluded_sites:
                    QMessageBox.warning(self, "Duplicate Entry", "Site is already in the excluded list.")
                    return
                self.excluded_sites.append(site)
                self.populate_excluded_table()
                self.parent.save_blocked_sites()  # Save changes immediately
                self.parent.restart_mitmproxy()  # Restart mitmproxy

    def delete_selected_site(self):
        selected_row = self.excluded_table.currentRow()
        if selected_row != -1:
            site_item = self.excluded_table.item(selected_row, 0)
            if site_item:
                site = site_item.text()
                confirmation = QMessageBox.question(
                    self, "Confirm Delete", f"Are you sure you want to remove {site} from excluded sites?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirmation == QMessageBox.StandardButton.Yes:
                    self.excluded_sites.remove(site)
                    self.populate_excluded_table()
                    self.parent.save_blocked_sites()  # Save changes immediately
                    self.parent.restart_mitmproxy()  # Restart mitmproxy


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Content Monitoring Dashboard')

        # File to store blocked sites
        self.blocked_sites_file = 'blocked_sites.json'

        # Load blocked sites from file
        self.blocked_sites, self.excluded_sites, self.category_keywords = self.load_blocked_sites()

        # Content Table for Blocked Sites
        self.blocked_table = QTableWidget(self)
        self.blocked_table.setColumnCount(1)
        self.blocked_table.setHorizontalHeaderLabels(['Blocked Sites'])
        self.populate_blocked_table()

        # Add Site Button
        self.add_site_button = QPushButton('Add Site', self)
        self.add_site_button.clicked.connect(self.open_add_site_dialog)

        # Delete Site Button
        self.delete_site_button = QPushButton('Delete Site', self)
        self.delete_site_button.clicked.connect(self.delete_selected_site)

        # Excluded Sites Button
        self.excluded_sites_button = QPushButton('Excluded Sites', self)
        self.excluded_sites_button.clicked.connect(self.open_excluded_sites_dialog)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.blocked_table)
        layout.addWidget(self.add_site_button)
        layout.addWidget(self.delete_site_button)
        layout.addWidget(self.excluded_sites_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_blocked_sites(self):
        try:
            with open(self.blocked_sites_file, 'r') as file:
                data = json.load(file)
                return data.get("sites", []), data.get("excluded_sites", []), data.get("categories", {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return [], [], {}

    def save_blocked_sites(self):
        data = {
            "sites": self.blocked_sites,
            "excluded_sites": self.excluded_sites,
            "categories": self.category_keywords
        }
        with open(self.blocked_sites_file, 'w') as file:
            json.dump(data, file)

    def populate_blocked_table(self):
        self.blocked_table.setRowCount(0)  # Clear existing rows
        for site in self.blocked_sites:
            self.add_to_blocked_table(site)

    def add_to_blocked_table(self, site):
        row_position = self.blocked_table.rowCount()
        self.blocked_table.insertRow(row_position)
        self.blocked_table.setItem(row_position, 0, QTableWidgetItem(site))

    def open_add_site_dialog(self):
        dialog = AddSiteDialog(self)
        if dialog.exec():
            site = dialog.get_input()
            if site:
                if site in self.blocked_sites:
                    QMessageBox.warning(self, "Duplicate Entry", "Site is already in the blocked list.")
                    return
                self.blocked_sites.append(site)
                self.populate_blocked_table()
                self.save_blocked_sites()
                self.restart_mitmproxy()

    def delete_selected_site(self):
        selected_row = self.blocked_table.currentRow()
        if selected_row != -1:
            site_item = self.blocked_table.item(selected_row, 0)
            if site_item:
                site = site_item.text()
                confirmation = QMessageBox.question(
                    self, "Confirm Delete", f"Are you sure you want to remove {site} from blocked sites?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirmation == QMessageBox.StandardButton.Yes:
                    self.blocked_sites.remove(site)
                    self.populate_blocked_table()
                    self.save_blocked_sites()
                    self.restart_mitmproxy()

    def open_excluded_sites_dialog(self):
        dialog = ExcludedSitesDialog(self.excluded_sites, self)
        dialog.exec()

    def closeEvent(self, event):
        confirmation = QMessageBox.question(
            self, "Confirm Exit", "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirmation == QMessageBox.StandardButton.Yes:
            disable_windows_proxy()
            self.save_blocked_sites()
            event.accept()
        else:
            event.ignore()

    def restart_mitmproxy(self):
        subprocess.call(["taskkill", "/F", "/IM", "mitmproxy.exe"])
        subprocess.Popen(['mitmproxy', '--listen-host', '127.0.0.1', '--listen-port', '8080', '-s', 'block_sites.py'])


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication

    launch_proxy()
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())