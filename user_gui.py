import json
import os
import requests
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QTabWidget, QApplication, QMessageBox,
    QPushButton, QLineEdit, QLabel, QHBoxLayout, QFormLayout
)
from PyQt6.QtCore import QTimer
from dotenv import load_dotenv
from setup_proxy_and_mitm import launch_proxy, disable_windows_proxy

# Load environment variables
load_dotenv()

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
        self.server_url = os.getenv('SERVER_URL', 'http://192.168.0.103:8000')  # Get server URL from env with fallback
        self.api_key = os.getenv('DEFAULT_API_KEY', '123')  # Get default API key from env with fallback
        
        self.setup_ui()

    def setup_ui(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_blocked_sites_tab(), "Blocked Sites")
        self.tab_widget.addTab(self.create_excluded_sites_tab(), "Excluded Sites")
        self.tab_widget.addTab(self.create_script_execution_tab(), "Script Execution")
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

    def create_script_execution_tab(self):
        container = QWidget()
        layout = QVBoxLayout()

        # Server settings
        settings_group = QWidget()
        settings_layout = QFormLayout()
        
        self.server_url_input = QLineEdit(self.server_url)
        self.server_url_input.textChanged.connect(self.on_server_settings_changed)
        settings_layout.addRow("Server URL:", self.server_url_input)
        
        self.api_key_input = QLineEdit(self.api_key)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.textChanged.connect(self.on_server_settings_changed)
        settings_layout.addRow("API Key:", self.api_key_input)
        
        # Add connection status label
        self.connection_status = QLabel("Not Connected")
        settings_layout.addRow("Status:", self.connection_status)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Script execution
        script_group = QWidget()
        script_layout = QHBoxLayout()
        
        self.script_name_input = QLineEdit()
        script_layout.addWidget(QLabel("Script Name:"))
        script_layout.addWidget(self.script_name_input)
        
        execute_button = QPushButton("Execute Script")
        execute_button.clicked.connect(self.execute_script)
        script_layout.addWidget(execute_button)
        
        script_group.setLayout(script_layout)
        layout.addWidget(script_group)

        # Send initial heartbeat
        self.send_heartbeat()

        container.setLayout(layout)
        return container

    def on_server_settings_changed(self):
        new_url = self.server_url_input.text().strip()
        new_key = self.api_key_input.text().strip()
        
        if new_url and new_key:
            self.server_url = new_url
            self.api_key = new_key
            self.send_heartbeat()  # Send heartbeat when settings change
        else:
            self.connection_status.setText("Not Connected")

    def load_data(self):
        try:
            with open(self.blocked_sites_file, 'r') as file:
                data = json.load(file)
                return data.get("sites", []), data.get("excluded_sites", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return [], []

    def execute_script(self):
        if not all([self.server_url_input.text().strip(), self.api_key_input.text().strip(), self.script_name_input.text().strip()]):
            QMessageBox.warning(self, "Input Error", "Please fill in all fields")
            return

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {"script": self.script_name_input.text().strip()}
            
            response = requests.post(
                f"{self.server_url}/api/execute/",
                data=payload,
                headers=headers
            )
            
            result = response.json()
            QMessageBox.information(self, "Script Execution Result", str(result))
            
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error", f"Failed to connect to server: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def send_heartbeat(self):
        if not self.api_key:  # Skip if API key is not set
            self.connection_status.setText("Not Connected")
            return
            
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            response = requests.post(
                f"{self.server_url}/heartbeat/", 
                json={'user_id': self.api_key},
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                self.connection_status.setText("Connected")
            else:
                self.connection_status.setText(f"Error: {response.status_code}")
                print(f"Failed to send heartbeat: {response.text}")
                if response.status_code in [400, 401]:  # Bad request or unauthorized
                    pass
        except Exception as e:
            self.connection_status.setText("Connection Failed")
            print(f"Error sending heartbeat: {str(e)}")

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