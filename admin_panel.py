import json
import os
from dotenv import load_dotenv
import psycopg2
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QPushButton, QWidget, QLineEdit, QDialog, QFormLayout, QMessageBox, 
    QInputDialog, QTabWidget, QLabel, QCheckBox, QHeaderView
)
from PyQt6.QtCore import QTimer
from setup_proxy_and_mitm import launch_proxy, disable_windows_proxy
import subprocess
import random
import string
from datetime import datetime, timedelta
from email_utils import send_2fa_code
import requests


class BaseDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.layout = QFormLayout()
        self.setLayout(self.layout)


class AddSiteDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__('Add Site', parent)
        self.site_input = QLineEdit(self)
        self.layout.addRow("Site URL:", self.site_input)
        self.add_button = QPushButton("Add", self)
        self.add_button.clicked.connect(self.accept)
        self.layout.addWidget(self.add_button)

    def get_input(self):
        return self.site_input.text()


class TwoFactorDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__('Two-Factor Authentication', parent)
        self.code_input = QLineEdit()
        self.layout.addRow("Enter Code:", self.code_input)
        
        verify_button = QPushButton("Verify")
        verify_button.clicked.connect(self.accept)
        self.layout.addWidget(verify_button)
    
    def get_code(self):
        return self.code_input.text().strip()


class LoginDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__('Login', parent)
        self.setModal(True)
        self.setMinimumWidth(300)
        
        self.username_input = QLineEdit()
        self.layout.addRow('Username:', self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addRow('Password:', self.password_input)
        
        login_button = QPushButton('Login')
        login_button.clicked.connect(self.try_login)
        self.layout.addRow(login_button)
        
        load_dotenv()
        self.db_config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST')
        }
        self.current_user_id = None

    def generate_2fa_code(self):
        return ''.join(random.choices(string.digits, k=6))

    def save_2fa_code(self, cur, user_id, code):
        # Delete any existing codes for this user
        cur.execute(
            "DELETE FROM two_factor_codes WHERE user_id = %s",
            (user_id,)
        )
        
        # Insert new code with 10-minute expiry
        expiry = datetime.now() + timedelta(minutes=10)
        cur.execute(
            "INSERT INTO two_factor_codes (user_id, code, expiry) VALUES (%s, %s, %s)",
            (user_id, code, expiry)
        )

    def verify_2fa_code(self, cur, user_id, entered_code):
        cur.execute(
            """
            SELECT code FROM two_factor_codes 
            WHERE user_id = %s AND code = %s AND expiry > NOW()
            """,
            (user_id, entered_code)
        )
        return cur.fetchone() is not None

    def try_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Check credentials and get user info
            cur.execute(
                """
                SELECT id, email, is_2fa_enabled 
                FROM users 
                WHERE username = %s AND password = %s
                """,
                (username, password)
            )
            
            user_data = cur.fetchone()
            if not user_data:
                QMessageBox.warning(self, 'Login Failed', 'Invalid username or password')
                return

            user_id, email, is_2fa_enabled = user_data
            self.current_user_id = user_id  # Store the user ID
            
            if is_2fa_enabled:
                # Check if there's an active code
                cur.execute(
                    """
                    SELECT code FROM two_factor_codes 
                    WHERE user_id = %s AND expiry > NOW()
                    ORDER BY expiry DESC LIMIT 1
                    """,
                    (user_id,)
                )
                existing_code = cur.fetchone()
                
                if not existing_code:
                    # No valid code exists, generate and send new one
                    code = self.generate_2fa_code()
                    self.save_2fa_code(cur, user_id, code)
                    conn.commit()
                    
                    # Send code via email
                    if not send_2fa_code(email, code):
                        QMessageBox.critical(self, 'Email Error', 'Failed to send 2FA code')
                        return

                # Show 2FA verification dialog
                while True:  # Loop for multiple attempts
                    two_factor_dialog = TwoFactorDialog(self)
                    if not two_factor_dialog.exec():  # User cancelled
                        return
                        
                    entered_code = two_factor_dialog.get_code()
                    if self.verify_2fa_code(cur, user_id, entered_code):
                        # Delete the used code
                        cur.execute(
                            "DELETE FROM two_factor_codes WHERE user_id = %s AND code = %s",
                            (user_id, entered_code)
                        )
                        conn.commit()
                        self.accept()
                        break  # Exit the loop on successful verification
                    else:
                        QMessageBox.information(self, 'Verification Failed', 'Incorrect code. Please try again.')
            else:
                self.accept()
            
            cur.close()
            conn.close()
            
        except Exception as e:
            QMessageBox.critical(self, 'Database Error', f'Could not connect to database: {str(e)}')


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

    def populate(self, categories):
        self.setRowCount(0)
        for category, keywords in categories.items():
            row_position = self.rowCount()
            self.insertRow(row_position)
            self.setItem(row_position, 0, QTableWidgetItem(category))
            self.setItem(row_position, 1, QTableWidgetItem(", ".join(keywords)))


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Content Monitoring Dashboard')
        self.blocked_sites_file = 'blocked_sites.json'
        self.blocked_sites, self.excluded_sites, self.category_keywords = self.load_data()
        self.current_user_id = None
        
        # Load database configuration
        load_dotenv()
        self.db_config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST')
        }
        
        self.server_url = os.getenv('SERVER_URL', 'http://192.168.0.103:8000')  # Get server URL from env with fallback
        
        self.setup_ui()

    def setup_ui(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_blocked_sites_tab(), "Blocked Sites")
        self.tab_widget.addTab(self.create_excluded_sites_tab(), "Excluded Sites")
        self.tab_widget.addTab(self.create_categories_tab(), "Categories")
        self.tab_widget.addTab(self.create_settings_tab(), "Settings")
        self.tab_widget.addTab(self.create_online_users_tab(), "Online Users")
        self.setCentralWidget(self.tab_widget)

    def create_blocked_sites_tab(self):
        self.blocked_table = SiteTable('Blocked Sites')
        self.blocked_table.populate(self.blocked_sites)
        
        add_site_button = QPushButton('Add Site')
        add_site_button.clicked.connect(self.open_add_site_dialog)
        delete_site_button = QPushButton('Delete Site')
        delete_site_button.clicked.connect(self.delete_selected_site)

        return self.create_tab_layout(self.blocked_table, [add_site_button, delete_site_button])

    def create_excluded_sites_tab(self):
        self.excluded_table = SiteTable('Excluded Sites')
        self.excluded_table.populate(self.excluded_sites)
        
        add_site_button = QPushButton('Add Site')
        add_site_button.clicked.connect(self.open_add_site_dialog)
        delete_site_button = QPushButton('Delete Site')
        delete_site_button.clicked.connect(self.delete_selected_site)

        return self.create_tab_layout(self.excluded_table, [add_site_button, delete_site_button])

    def create_categories_tab(self):
        self.categories_table = CategoryTable()
        self.categories_table.populate(self.category_keywords)
        
        add_category_button = QPushButton('Add Category')
        add_category_button.clicked.connect(self.add_category)
        delete_category_button = QPushButton('Delete Category')
        delete_category_button.clicked.connect(self.delete_category)

        return self.create_tab_layout(self.categories_table, [add_category_button, delete_category_button])

    def create_settings_tab(self):
        container = QWidget()
        layout = QVBoxLayout()

        # 2FA Toggle
        self.twofa_checkbox = QCheckBox("Enable Two-Factor Authentication")
        self.twofa_checkbox.stateChanged.connect(self.toggle_2fa)
        layout.addWidget(self.twofa_checkbox)

        # Email settings
        email_label = QLabel("Email for 2FA:")
        self.email_input = QLineEdit()
        layout.addWidget(email_label)
        layout.addWidget(self.email_input)

        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        layout.addStretch()
        container.setLayout(layout)
        return container

    def create_online_users_tab(self):
        container = QWidget()
        layout = QVBoxLayout()

        # Create table for online users
        self.online_users_table = QTableWidget()
        self.online_users_table.setColumnCount(2)
        self.online_users_table.setHorizontalHeaderLabels(['User ID', 'Last Active'])
        self.online_users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Add refresh button
        refresh_button = QPushButton("Refresh Online Users")
        refresh_button.clicked.connect(self.refresh_online_users)
        layout.addWidget(refresh_button)
        
        layout.addWidget(self.online_users_table)
        container.setLayout(layout)
        return container
        
    def create_tab_layout(self, table_widget, buttons):
        layout = QVBoxLayout()
        layout.addWidget(table_widget)
        for button in buttons:
            layout.addWidget(button)
        container = QWidget()
        container.setLayout(layout)
        return container

    def load_data(self):
        try:
            with open(self.blocked_sites_file, 'r') as file:
                data = json.load(file)
                return data.get("sites", []), data.get("excluded_sites", []), data.get("categories", {})
        except (FileNotFoundError, json.JSONDecodeError):
            return [], [], {}

    def save_data(self):
        data = {
            "sites": self.blocked_sites,
            "excluded_sites": self.excluded_sites,
            "categories": self.category_keywords
        }
        with open(self.blocked_sites_file, 'w') as file:
            json.dump(data, file)

    def open_add_site_dialog(self):
        dialog = AddSiteDialog(self)
        if dialog.exec():
            site = dialog.get_input()
            if not site:
                return
                
            if site in self.blocked_sites or site in self.excluded_sites:
                QMessageBox.warning(self, "Duplicate Entry", "Site is already in the blocked or excluded list.")
                return

            choice, ok = QInputDialog.getItem(
                self, "Choose List", "Add site to:", 
                ["Blocked Sites", "Excluded Sites"], 0, False
            )
            if ok and choice:
                if choice == "Blocked Sites":
                    self.blocked_sites.append(site)
                    self.blocked_table.populate(self.blocked_sites)
                else:
                    self.excluded_sites.append(site)
                    self.excluded_table.populate(self.excluded_sites)

                self.save_data()
                self.restart_mitmproxy()

    def delete_selected_site(self):
        current_tab = self.tab_widget.currentWidget()
        table = None
        sites_list = None
        
        if current_tab.findChild(SiteTable):
            table = current_tab.findChild(SiteTable)
            if table == self.blocked_table:
                sites_list = self.blocked_sites
            else:
                sites_list = self.excluded_sites
        
        if not table or table.currentRow() == -1:
            QMessageBox.warning(self, "No Selection", "Please select a site to delete.")
            return
            
        site_item = table.item(table.currentRow(), 0)
        if site_item:
            site = site_item.text()
            list_name = "Blocked Sites" if table == self.blocked_table else "Excluded Sites"
            self.confirm_delete_site(site, list_name, sites_list, table)

    def confirm_delete_site(self, site, list_name, sites_list, table):
        confirmation = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to remove {site} from {list_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirmation == QMessageBox.StandardButton.Yes:
            sites_list.remove(site)
            table.populate(sites_list)
            self.save_data()
            self.restart_mitmproxy()

    def add_category(self):
        category_name, ok = QInputDialog.getText(self, "Add Category", "Category Name:")
        if ok and category_name:
            keywords, ok = QInputDialog.getText(self, "Add Keywords", "Keywords (comma separated):")
            if ok:
                keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
                self.category_keywords[category_name] = keywords_list
                self.save_data()
                self.categories_table.populate(self.category_keywords)
                self.restart_mitmproxy()

    def delete_category(self):
        if self.categories_table.currentRow() == -1:
            QMessageBox.warning(self, "No Selection", "Please select a category to delete.")
            return
            
        category_item = self.categories_table.item(self.categories_table.currentRow(), 0)
        if category_item:
            category_name = category_item.text()
            confirmation = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete category '{category_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirmation == QMessageBox.StandardButton.Yes:
                del self.category_keywords[category_name]
                self.save_data()
                self.categories_table.populate(self.category_keywords)
                self.restart_mitmproxy()

    def restart_mitmproxy(self):
        subprocess.call(["taskkill", "/F", "/IM", "mitmdump.exe"])
        subprocess.Popen(['mitmdump', '--listen-host', '127.0.0.1', '--listen-port', '8080', '-s', 'block_sites.py'])

    def load_user_settings(self, user_id):
        print(f"Loading settings for user ID: {user_id}")  # Debug log
        self.current_user_id = user_id
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            cur.execute(
                "SELECT email, is_2fa_enabled FROM users WHERE id = %s",
                (user_id,)
            )
            user_data = cur.fetchone()
            
            if user_data:
                email, is_2fa_enabled = user_data
                print(f"Found user settings - Email: {email}, 2FA: {is_2fa_enabled}")  # Debug log
                self.email_input.setText(email or "")
                self.twofa_checkbox.setChecked(is_2fa_enabled)
            else:
                print(f"No user data found for ID: {user_id}")  # Debug log
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error loading user settings: {str(e)}")  # Debug log
            QMessageBox.critical(self, 'Database Error', f'Could not load user settings: {str(e)}')

    def toggle_2fa(self, state):
        if state and not self.email_input.text().strip():
            QMessageBox.warning(self, 'Email Required', 'Please enter an email address to enable 2FA')
            self.twofa_checkbox.setChecked(False)
            return

    def save_settings(self):
        print(f"Attempting to save settings for user ID: {self.current_user_id}")  # Debug log
        if not self.current_user_id:
            print("No user ID found")  # Debug log
            QMessageBox.warning(self, 'Error', 'No user is currently logged in')
            return

        email = self.email_input.text().strip()
        is_2fa_enabled = self.twofa_checkbox.isChecked()
        print(f"Settings to save - Email: {email}, 2FA: {is_2fa_enabled}")  # Debug log

        if is_2fa_enabled and not email:
            QMessageBox.warning(self, 'Email Required', 'Please enter an email address to enable 2FA')
            return

        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # First verify if the user exists
            cur.execute("SELECT id FROM users WHERE id = %s", (self.current_user_id,))
            if not cur.fetchone():
                print(f"User not found in database: {self.current_user_id}")  # Debug log
                QMessageBox.critical(self, 'Error', 'User not found')
                return
            
            print("Executing update query...")  # Debug log
            cur.execute(
                """
                UPDATE users 
                SET email = %s, is_2fa_enabled = %s 
                WHERE id = %s
                RETURNING id, email, is_2fa_enabled
                """,
                (email, is_2fa_enabled, self.current_user_id)
            )
            
            updated_user = cur.fetchone()
            print(f"Update result: {updated_user}")  # Debug log
            
            conn.commit()
            cur.close()
            conn.close()
            
            QMessageBox.information(self, 'Success', 'Settings saved successfully')
        except Exception as e:
            print(f"Error saving settings: {str(e)}")  # Debug log
            QMessageBox.critical(self, 'Database Error', f'Could not save settings: {str(e)}')

    def refresh_online_users(self):
        try:
            response = requests.get(f"{self.server_url}/online-users/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.online_users_table.setRowCount(0)
                for user in data['online_users']:
                    row = self.online_users_table.rowCount()
                    self.online_users_table.insertRow(row)
                    self.online_users_table.setItem(row, 0, QTableWidgetItem(str(user['user_id'])))
                    last_active = datetime.fromisoformat(user['last_heartbeat'].replace('Z', '+00:00'))
                    self.online_users_table.setItem(row, 1, QTableWidgetItem(last_active.strftime('%Y-%m-%d %H:%M:%S')))
        except Exception as e:
            print(f"Error refreshing online users: {str(e)}")

    def closeEvent(self, event):
        # Stop the refresh timer when closing the window
        confirmation = QMessageBox.question(
            self, "Confirm Exit", "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirmation == QMessageBox.StandardButton.Yes:
            disable_windows_proxy()
            self.save_data()
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    launch_proxy()
    app = QApplication(sys.argv)
    
    login_dialog = LoginDialog()
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        print(f"Login successful, user ID: {login_dialog.current_user_id}")  # Debug log
        window = DashboardWindow()
        window.current_user_id = login_dialog.current_user_id  # Set the user ID
        print(f"Setting dashboard user ID to: {window.current_user_id}")  # Debug log
        window.load_user_settings(login_dialog.current_user_id)  # Load settings for logged-in user
        window.show()
        sys.exit(app.exec())