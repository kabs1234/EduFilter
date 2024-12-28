import json
import subprocess
import winreg as reg
import elevate
import platform
from PyQt6.QtWidgets import (
    QMainWindow, QLabel, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QPushButton, QWidget, QLineEdit, QDialog, QFormLayout, QMessageBox
)
from filter_settings import FilterSettingsWindow  # Import FilterSettingsWindow from filter_settings.py
import mitmproxy.http
from mitmproxy import ctx


# Function to set the proxy in Windows registry
def set_windows_proxy(proxy_address='127.0.0.1', proxy_port=8080):
    try:
        registry_key = reg.OpenKey(
            reg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, reg.KEY_WRITE
        )
        reg.SetValueEx(registry_key, "ProxyEnable", 0, reg.REG_DWORD, 1)
        reg.SetValueEx(registry_key, "ProxyServer", 0, reg.REG_SZ, f"{proxy_address}:{proxy_port}")
        reg.CloseKey(registry_key)
        print(f"Proxy is set to {proxy_address}:{proxy_port} in Windows settings.")
    except Exception as e:
        print(f"Error setting proxy in Windows registry: {e}")


# Function to automatically set the proxy in Windows
def set_proxy_automatically():
    elevate.elevate()
    set_windows_proxy()


class BlockSites:
    def __init__(self):
        self.blocked_sites_file = 'blocked_sites.json'
        self.blocked_sites = self.load_blocked_sites()

    def load_blocked_sites(self):
        try:
            with open(self.blocked_sites_file, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def request(self, flow: mitmproxy.http.HTTPFlow) -> None:
        if any(blocked_site in flow.request.pretty_url for blocked_site in self.blocked_sites):
            flow.response = mitmproxy.http.Response.make(
                403,  # HTTP Forbidden
                b"Blocked Site",  # Response body
                {"Content-Type": "text/html"}
            )
            print(f"Blocked {flow.request.pretty_url}")

# Function to start mitmproxy with the BlockSites script
def start_mitmproxy():
    try:
        subprocess.Popen(['mitmproxy', '--listen-host', '127.0.0.1', '--listen-port', '8080', '-s', __file__])
        print("mitmproxy is running at 127.0.0.1:8080")
    except Exception as e:
        print(f"Error starting mitmproxy: {e}")


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


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Content Monitoring Dashboard')

        # File to store blocked sites
        self.blocked_sites_file = 'blocked_sites.json'

        # Load blocked sites from file
        self.blocked_sites = self.load_blocked_sites()

        # Content Table
        self.content_table = QTableWidget(self)
        self.content_table.setColumnCount(1)
        self.content_table.setHorizontalHeaderLabels(['Blocked Sites'])
        self.populate_content_table()

        # Add Site Button
        self.add_site_button = QPushButton('Add Site', self)
        self.add_site_button.clicked.connect(self.open_add_site_dialog)

        # Delete Site Button
        self.delete_site_button = QPushButton('Delete Site', self)
        self.delete_site_button.clicked.connect(self.delete_selected_site)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.content_table)
        layout.addWidget(self.add_site_button)
        layout.addWidget(self.delete_site_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_blocked_sites(self):
        try:
            with open(self.blocked_sites_file, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def save_blocked_sites(self):
        with open(self.blocked_sites_file, 'w') as file:
            json.dump(self.blocked_sites, file)

    def populate_content_table(self):
        self.content_table.setRowCount(0)  # Clear existing rows
        for site in self.blocked_sites:
            self.add_to_content_table(site)

    def add_to_content_table(self, site):
        row_position = self.content_table.rowCount()
        self.content_table.insertRow(row_position)
        self.content_table.setItem(row_position, 0, QTableWidgetItem(site))

    def open_add_site_dialog(self):
        dialog = AddSiteDialog(self)
        if dialog.exec():
            site = dialog.get_input()
            if site and site not in self.blocked_sites:
                self.blocked_sites.append(site)
                self.save_blocked_sites()
                self.add_to_content_table(site)
            else:
                QMessageBox.warning(self, "Duplicate Entry", "Site is already in the blocked list.")

    def delete_selected_site(self):
        selected_row = self.content_table.currentRow()
        if selected_row != -1:
            site_item = self.content_table.item(selected_row, 0)  # Get the site cell
            if site_item:
                site = site_item.text()
                confirmation = QMessageBox.question(
                    self, "Confirm Delete", f"Are you sure you want to unblock {site}?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirmation == QMessageBox.StandardButton.Yes:
                    self.blocked_sites.remove(site)
                    self.save_blocked_sites()
                    self.content_table.removeRow(selected_row)
        else:
            QMessageBox.warning(self, "No Selection", "Please select a site to delete.")

    def start_proxy(self):
        set_proxy_automatically()
        start_mitmproxy()


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())
