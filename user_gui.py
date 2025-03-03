import json
import os
import requests
import uuid
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QPushButton, QWidget, QLineEdit, QMessageBox,
    QTabWidget, QStatusBar, QLabel, QHBoxLayout, QFormLayout,
    QSystemTrayIcon, QMenu, QStyle
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtNetwork import QNetworkProxy
from PyQt6.QtWebSockets import QWebSocket
from dotenv import load_dotenv
from setup_proxy_and_mitm import launch_proxy, disable_windows_proxy
import logging
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

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
        elif self.path == '/reload':
            self.send_response(200)
            self.end_headers()
            # Trigger a reload of the proxy settings
            # This is a workaround to get mitmproxy to reload its settings
            logging.info("Received reload signal, reloading proxy settings...")
            try:
                # Reload the block_sites.py script
                # For mitmproxy, we need to save the settings to a file that it can access
                with open('blocked_sites.json', 'r') as f:
                    data = json.load(f)
                    blocked_sites = data.get('blocked_sites', [])
                    excluded_sites = data.get('excluded_sites', [])
                    categories = data.get('categories', {})
                # Update the dashboard with the new settings
                self.server.dashboard.blocked_sites = blocked_sites
                self.server.dashboard.excluded_sites = excluded_sites
                self.server.dashboard.blocked_table.populate(blocked_sites)
                self.server.dashboard.excluded_table.populate(excluded_sites)
                logging.info("Proxy settings reloaded")
            except Exception as e:
                logging.error(f"Error reloading proxy settings: {str(e)}", exc_info=True)
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

class CategoryTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Category', 'Keywords'])
        self.horizontalHeader().setStretchLastSection(True)

    def populate(self, categories):
        self.setRowCount(0)
        for category, keywords in categories.items():
            self.add_category(category, keywords)

    def add_category(self, category, keywords):
        row_position = self.rowCount()
        self.insertRow(row_position)
        self.setItem(row_position, 0, QTableWidgetItem(category))
        self.setItem(row_position, 1, QTableWidgetItem(', '.join(keywords)))

class UserDashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Content Monitoring - User Mode')
        self.blocked_sites_file = 'blocked_sites.json'
        self.user_id = self.get_or_create_user_id()
        self.api_key = self.user_id  # Set api_key before loading data
        self.server_url = os.getenv('SERVER_URL', 'http://127.0.0.1:8000')  # Use localhost as default
        
        # Initialize data structures
        self.blocked_sites = []
        self.excluded_sites = []
        self.categories = {}  # Add categories field
        
        # Create system tray icon
        self.create_tray_icon()
        
        # Initialize connection status label
        self.connection_status = QLabel("WebSocket: Not Connected")
        
        # Initialize WebSocket
        self.websocket = QWebSocket()
        self.websocket.connected.connect(self.on_websocket_connected)
        self.websocket.disconnected.connect(self.on_websocket_disconnected)
        self.websocket.textMessageReceived.connect(self.on_websocket_message)
        
        # Get WebSocket URL from server URL
        ws_url = self.server_url.replace('http://', 'ws://') + '/ws/status/'
        self.ws_url = ws_url
        
        # Start status server
        self.local_ip = get_local_ip()
        self.status_port = 8081
        self.start_status_server()
        
        # Register IP with main server
        self.register_ip_with_server()
        
        # Load data after api_key is set
        self.load_data()
        
        self.setup_ui()
        
        # Connect to WebSocket after UI is set up
        self.connect_websocket()

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

    def connect_websocket(self):
        """Connect to the WebSocket server"""
        # Configure QWebSocket to bypass proxy
        proxy = QNetworkProxy()
        proxy.setType(QNetworkProxy.ProxyType.NoProxy)
        self.websocket.setProxy(proxy)
        self.websocket.open(QUrl(self.ws_url))

    def on_websocket_connected(self):
        """Handle WebSocket connection"""
        self.connection_status.setText("WebSocket: Connected")
        # Send initial user status
        self.websocket.sendTextMessage(json.dumps({
            'type': 'user_status',
            'user_id': self.user_id,
            'status': 'online'
        }))

    def on_websocket_disconnected(self):
        """Handle WebSocket disconnection"""
        self.connection_status.setText("WebSocket: Disconnected")
        # Try to reconnect after 5 seconds
        QTimer.singleShot(5000, self.connect_websocket)

    def on_websocket_message(self, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            logging.info(f"WebSocket message received: {message_type}")
            logging.debug(f"Message content: {data}")
            
            if message_type == 'settings_change':
                # Update settings if they changed
                if data.get('user_id') == self.user_id:
                    logging.info("Received settings update for this user")
                    settings = data.get('settings', {})
                    self.update_settings(settings)
                    
                    # Reload proxy settings
                    self.reload_proxy_settings()
                    
                    # Show notification to user
                    self.statusBar().showMessage("Settings updated from admin panel", 5000)
            elif message_type == 'ping':
                # Respond to ping with pong
                logging.debug("Received ping, sending pong")
                self.websocket.sendTextMessage(json.dumps({
                    'type': 'pong',
                    'user_id': self.user_id
                }))
            elif message_type == 'admin_connected':
                logging.info("Admin connection confirmed")
                # Optionally refresh status or update UI
            else:
                logging.warning(f"Unknown message type received: {message_type}")
            
        except json.JSONDecodeError:
            logging.error(f"Error: Invalid JSON message received: {message}")
        except Exception as e:
            logging.error(f"Error handling WebSocket message: {str(e)}", exc_info=True)

    def setup_ui(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_blocked_sites_tab(), "Blocked Sites")
        self.tab_widget.addTab(self.create_excluded_sites_tab(), "Excluded Sites")
        self.tab_widget.addTab(self.create_categories_tab(), "Categories")
        self.tab_widget.addTab(self.create_script_execution_tab(), "Script Execution")
        self.setCentralWidget(self.tab_widget)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def create_blocked_sites_tab(self):
        self.blocked_table = SiteTable('Blocked Sites')
        self.blocked_table.populate(self.blocked_sites)
        return self.create_tab_layout(self.blocked_table)

    def create_excluded_sites_tab(self):
        self.excluded_table = SiteTable('Excluded Sites')
        self.excluded_table.populate(self.excluded_sites)
        return self.create_tab_layout(self.excluded_table)

    def create_categories_tab(self):
        self.categories_table = CategoryTable()
        self.categories_table.populate(self.categories)
        return self.create_tab_layout(self.categories_table)

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
            
            url = f"{self.server_url}/api/user-settings/{self.user_id}/"
            
            response = requests.get(
                url,
                headers=headers,
                timeout=5,
                verify=False  # Add this to handle self-signed certificates
            )
            
            if response.status_code == 200:
                data = response.json()
                self.blocked_sites = data.get('blocked_sites', [])
                self.excluded_sites = data.get('excluded_sites', [])
                self.categories = data.get('categories', {})
                return self.blocked_sites, self.excluded_sites
            
            # If API request fails, fall back to local file
            logging.info("API request failed, falling back to local settings file")
            if os.path.exists(self.blocked_sites_file):
                with open(self.blocked_sites_file, 'r') as f:
                    data = json.load(f)
                    self.blocked_sites = data.get('blocked_sites', [])
                    self.excluded_sites = data.get('excluded_sites', [])
                    self.categories = data.get('categories', {})
                    return self.blocked_sites, self.excluded_sites
            
            # If both API and local file fail, return empty lists
            return [], []
                
        except Exception as e:
            # Log the error and try to load from local file
            logging.error(f"Error fetching settings from API: {str(e)}")
            try:
                if os.path.exists(self.blocked_sites_file):
                    with open(self.blocked_sites_file, 'r') as f:
                        data = json.load(f)
                        self.blocked_sites = data.get('blocked_sites', [])
                        self.excluded_sites = data.get('excluded_sites', [])
                        self.categories = data.get('categories', {})
                        return self.blocked_sites, self.excluded_sites
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
            logging.info("Processing settings update")
            
            # Extract settings with proper defaults
            blocked_sites = settings.get('blocked_sites', [])
            excluded_sites = settings.get('excluded_sites', [])
            categories = settings.get('categories', {})
            
            # Log changes for debugging
            logging.debug(f"New blocked sites: {blocked_sites}")
            logging.debug(f"New excluded sites: {excluded_sites}")
            logging.debug(f"New categories: {categories}")
            
            # Check if settings have actually changed
            blocked_changed = sorted(blocked_sites) != sorted(self.blocked_sites)
            excluded_changed = sorted(excluded_sites) != sorted(self.excluded_sites)
            categories_changed = categories != self.categories  # Add categories comparison
            
            if blocked_changed or excluded_changed or categories_changed:
                logging.info("Settings have changed, updating UI and local data")
                
                # Update local data
                self.blocked_sites = blocked_sites
                self.excluded_sites = excluded_sites
                self.categories = categories  # Update categories
                
                # Update UI tables
                self.blocked_table.populate(self.blocked_sites)
                self.excluded_table.populate(self.excluded_sites)
                self.categories_table.populate(self.categories)  # Update categories table
                
                # Save to local file as backup
                try:
                    with open(self.blocked_sites_file, 'w') as f:
                        json.dump({
                            'blocked_sites': self.blocked_sites,
                            'excluded_sites': self.excluded_sites,
                            'categories': self.categories
                        }, f, indent=4)
                    logging.info("Settings saved to local file")
                except Exception as save_error:
                    logging.error(f"Error saving settings to local file: {str(save_error)}")
            else:
                logging.info("No changes in settings detected")
                
        except Exception as e:
            logging.error(f"Error updating settings: {str(e)}", exc_info=True)

    def reload_proxy_settings(self):
        """Reload the proxy settings by reloading the block_sites.py script"""
        logging.info("Reloading proxy settings...")
        try:
            # For mitmproxy, we need to save the settings to a file that it can access
            with open('blocked_sites.json', 'w') as f:
                json.dump({
                    'blocked_sites': self.blocked_sites,
                    'excluded_sites': self.excluded_sites,
                    'categories': self.categories  # Use the instance categories
                }, f, indent=4)
            
            logging.info("Proxy settings saved to blocked_sites.json for mitmproxy to reload")
            
            # Send a message to the status server to trigger a reload
            # This is a workaround to get mitmproxy to reload its settings
            url = f"http://{self.local_ip}:{self.status_port}/reload"
            logging.debug(f"Sending request to reload proxy: {url}")
            try:
                # Use a session to avoid the proxy for this request
                session = requests.Session()
                session.trust_env = False  # Don't use environment proxies
                session.get(url, timeout=1)  # Short timeout, we don't need a response
            except requests.exceptions.RequestException:
                # This is expected to timeout or fail, it's just a trigger
                pass
                
            logging.info("Reload signal sent to proxy")
        except Exception as e:
            logging.error(f"Error reloading proxy settings: {str(e)}", exc_info=True)

    def create_tray_icon(self):
        """Create and set up the system tray icon"""
        # Create the tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Load custom icon if available, otherwise use default
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'edufilter.ico')
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        # Create the tray menu
        tray_menu = QMenu()
        
        # Add menu items
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        
        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        
        # Add actions to menu
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        # Set the tray menu
        self.tray_icon.setContextMenu(tray_menu)
        
        # Make the tray icon visible
        self.tray_icon.show()
        
        # Connect double click action
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def quit_application(self):
        """Clean up and quit the application"""
        # Cleanup code here (stop servers, close connections, etc.)
        if hasattr(self, 'status_server'):
            self.status_server.shutdown()
            self.status_server.server_close()
        
        if hasattr(self, 'websocket'):
            self.websocket.close()
        
        disable_windows_proxy()
        
        # Hide tray icon before quitting
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        
        QApplication.instance().quit()

    def closeEvent(self, event):
        """Handle the window close event"""
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "EduFilter",
                "Application is still running in the system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            self.quit_application()
            event.accept()

if __name__ == '__main__':
    import sys
    launch_proxy()
    app = QApplication(sys.argv)
    
    # Enable system tray if supported
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "System Tray",
                           "System tray is not available on this system")
        sys.exit(1)
    
    # Create and show the main window
    window = UserDashboardWindow()
    window.show()
    
    # Start the event loop
    try:
        sys.exit(app.exec())
    except SystemExit:
        # Clean up when the application is closing
        if hasattr(window, 'status_server'):
            window.status_server.shutdown()
            window.status_server.server_close()
        if hasattr(window, 'websocket'):
            window.websocket.close()
        disable_windows_proxy()