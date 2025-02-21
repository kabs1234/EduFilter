import json
import os
import requests
import uuid
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QTabWidget, QApplication, QMessageBox,
    QPushButton, QLineEdit, QLabel, QHBoxLayout, QFormLayout
)
from PyQt6.QtCore import QTimer
from dotenv import load_dotenv
from setup_proxy_and_mitm import launch_proxy, disable_windows_proxy
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import socket
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

def get_local_ip():
    try:
        # Create a socket to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "online", "user_id": self.server.user_id}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

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
        self.user_id = self.get_or_create_user_id()
        self.api_key = self.user_id  # Set api_key before loading data
        self.server_url = os.getenv('SERVER_URL', 'http://127.0.0.1:8000')  # Use localhost as default
        
        # Initialize connection status label
        self.connection_status = QLabel("Not Connected")
        
        # Start status server
        self.local_ip = get_local_ip()
        self.status_port = 8081
        self.start_status_server()
        
        # Register IP with main server
        self.register_ip_with_server()
        
        # Load data after api_key is set
        self.blocked_sites, self.excluded_sites = self.load_data()
        
        self.setup_ui()

    def get_or_create_user_id(self):
        """Get existing user ID from .env file or create a new one."""
        env_path = '.env'
        user_id = None

        # Try to read existing user ID from .env
        if os.path.exists(env_path):
            load_dotenv()
            user_id = os.getenv('USER_ID')

        # If no user ID exists, create a new one
        if not user_id:
            user_id = str(uuid.uuid4())
            
            # Read existing .env content
            env_content = ''
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    env_content = f.read()

            # Add or update USER_ID in .env
            if 'USER_ID=' in env_content:
                lines = env_content.splitlines()
                new_lines = []
                for line in lines:
                    if line.startswith('USER_ID='):
                        new_lines.append(f'USER_ID={user_id}')
                    else:
                        new_lines.append(line)
                env_content = '\n'.join(new_lines)
            else:
                env_content += f'\nUSER_ID={user_id}'

            # Write back to .env
            with open(env_path, 'w') as f:
                f.write(env_content)

            # Reload environment variables
            load_dotenv()

        return user_id

    def start_status_server(self):
        try:
            server = HTTPServer((self.local_ip, self.status_port), StatusHandler)
            server.user_id = self.api_key  # Pass user_id to handler
            server.dashboard = self  # Pass dashboard reference to handler
            self.status_server = server
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
        except Exception as e:
            # Try with localhost if binding to local_ip fails
            try:
                server = HTTPServer(("127.0.0.1", self.status_port), StatusHandler)
                server.user_id = self.api_key
                server.dashboard = self
                self.status_server = server
                server_thread = threading.Thread(target=server.serve_forever, daemon=True)
                server_thread.start()
                self.local_ip = "127.0.0.1"
            except Exception:
                pass  # Silently handle server start failure

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

        container.setLayout(layout)
        return container

    def on_server_settings_changed(self):
        new_url = self.server_url_input.text().strip()
        new_key = self.api_key_input.text().strip()
        
        if new_url and new_key:
            self.server_url = new_url
            self.api_key = new_key
        else:
            self.connection_status.setText("Not Connected")

    def load_data(self):
        """Fetch user settings from the server or use defaults from blocked_sites.json."""
        try:
            # First try to get settings from API
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            url = f"{self.server_url}/api/user-settings/"
            
            response = requests.get(
                url,
                headers=headers,
                timeout=5,
                verify=False  # Add this to handle self-signed certificates
            )
            
            if response.status_code == 200:
                data = response.json()
                blocked_sites = data.get('blocked_sites', [])
                excluded_sites = data.get('excluded_sites', [])
                return blocked_sites, excluded_sites
            
            # If API request fails, fall back to local file
            logging.info("API request failed, falling back to local settings file")
            if os.path.exists(self.blocked_sites_file):
                with open(self.blocked_sites_file, 'r') as f:
                    data = json.load(f)
                    return data.get('blocked_sites', []), data.get('excluded_sites', [])
            
            # If both API and local file fail, return empty lists
            return [], []
                
        except Exception as e:
            # Log the error and try to load from local file
            logging.error(f"Error fetching settings from API: {str(e)}")
            try:
                if os.path.exists(self.blocked_sites_file):
                    with open(self.blocked_sites_file, 'r') as f:
                        data = json.load(f)
                        return data.get('blocked_sites', []), data.get('excluded_sites', [])
            except Exception as file_error:
                logging.error(f"Error loading local settings file: {str(file_error)}")
            
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

    def register_ip_with_server(self):
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            data = {
                'user_id': self.api_key,
                'ip_address': self.local_ip,
                'port': self.status_port
            }
            
            response = requests.post(
                f"{self.server_url}/api/register-ip/",
                json=data,
                headers=headers,
                verify=False  # Add this to handle self-signed certificates
            )
            
            if response.status_code == 200:
                self.connection_status.setText("Connected")
            else:
                self.connection_status.setText("Failed to register")
                
        except Exception:
            self.connection_status.setText("Connection Error")

    def unregister_ip(self):
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            data = {'user_id': self.api_key}
            
            response = requests.post(
                f"{self.server_url}/api/delete-ip/",
                json=data,
                headers=headers,
                verify=False  # Add this to handle self-signed certificates
            )
            
            if response.status_code == 200:
                self.connection_status.setText("Disconnected")
            else:
                self.connection_status.setText("Failed to unregister")
                
        except Exception:
            self.connection_status.setText("Connection Error")

    def update_settings(self, settings):
        """Update settings received from admin"""
        try:
            blocked_sites = settings.get('blocked_sites', [])
            excluded_sites = settings.get('excluded_sites', [])
            
            # Update only if settings have changed
            if (sorted(blocked_sites) != sorted(self.blocked_sites) or 
                sorted(excluded_sites) != sorted(self.excluded_sites)):
                self.blocked_sites = blocked_sites
                self.excluded_sites = excluded_sites
                self.blocked_table.populate(self.blocked_sites)
                self.excluded_table.populate(self.excluded_sites)
        except Exception as e:
            logging.error(f"Error updating settings: {str(e)}")

    def closeEvent(self, event):
        confirmation = QMessageBox.question(
            self, "Confirm Exit", "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirmation == QMessageBox.StandardButton.Yes:
            # Unregister IP
            self.unregister_ip()
            # Stop the status server
            if hasattr(self, 'status_server'):
                self.status_server.shutdown()
                self.status_server.server_close()
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