import json
import os
from dotenv import load_dotenv
import psycopg2
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QPushButton, QWidget, QLineEdit, QDialog, QFormLayout, QMessageBox, 
    QInputDialog, QTabWidget, QLabel, QCheckBox, QHeaderView, QHBoxLayout, QComboBox, QGroupBox
)
from PyQt6.QtCore import QTimer
from setup_proxy_and_mitm import launch_proxy, disable_windows_proxy
import subprocess
import random
import string
from datetime import datetime, timedelta
from email_utils import send_2fa_code
import requests
from admin_utils.gui_components import (
    BaseDialog, AddSiteDialog, TwoFactorDialog,
    SiteTable, CategoryTable
)
from admin_utils.database_utils import DatabaseManager, DatabaseError
from admin_utils.dialog_utils import DialogManager
from admin_utils.table_utils import TableManager  # Import TableManager

class LoginDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__('Login', parent)
        self.setModal(True)
        self.setMinimumWidth(300)
        
        self.username_input = QLineEdit()
        self.username_input.setText("admin")  # Set default username for development
        self.layout.addRow('Username:', self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setText("1234")  # Set default password for development
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addRow('Password:', self.password_input)
        
        login_button = QPushButton('Login')
        login_button.clicked.connect(self.try_login)
        self.layout.addRow(login_button)
        
        self.db = DatabaseManager()
        self.current_user_id = None

    def generate_2fa_code(self):
        return ''.join(random.choices(string.digits, k=6))

    def try_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        try:
            # Check credentials and get user info
            result = self.db.execute_query(
                """
                SELECT id, email, is_2fa_enabled 
                FROM users 
                WHERE username = %s AND password = %s
                """,
                (username, password)
            )
            
            if not result:
                DialogManager.show_warning_dialog('Login Failed', 'Invalid username or password', self)
                return

            user_id, email, is_2fa_enabled = result
            self.current_user_id = user_id
            
            if is_2fa_enabled:
                # Check if there's an active code
                existing_code = self.db.execute_query(
                    """
                    SELECT code FROM two_factor_codes 
                    WHERE user_id = %s AND expiry > NOW()
                    ORDER BY expiry DESC LIMIT 1
                    """,
                    (user_id,)
                )
                
                if not existing_code:
                    # No valid code exists, generate and send new one
                    code = self.generate_2fa_code()
                    self.db.manage_2fa_codes(user_id, code)
                    
                    # Send code via email
                    if not send_2fa_code(email, code):
                        DialogManager.show_error_dialog('Email Error', 'Failed to send 2FA code', self)
                        return

                # Show 2FA verification dialog
                while True:  # Loop for multiple attempts
                    two_factor_dialog = TwoFactorDialog(self)
                    if not two_factor_dialog.exec():  # User cancelled
                        return
                        
                    entered_code = two_factor_dialog.get_code()
                    if self.db.manage_2fa_codes(user_id, entered_code, verify=True):
                        # Delete the used code
                        self.db.manage_2fa_codes(user_id, delete=True)
                        self.accept()
                        break  # Exit the loop on successful verification
                    else:
                        DialogManager.show_info_dialog('Verification Failed', 'Incorrect code. Please try again.', self)
            else:
                self.accept()
            
        except DatabaseError as e:
            DialogManager.show_error_dialog('Database Error', f'Could not connect to database: {str(e)}', self)

class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Content Monitoring Dashboard')
        self.blocked_sites_file = 'blocked_sites.json'
        self.blocked_sites, self.excluded_sites, self.category_keywords = self.load_data()
        self.current_user_id = None
        
        self.db = DatabaseManager()
        self.server_url = os.getenv('SERVER_URL', 'http://192.168.0.103:8000')
        
        self.setup_ui()

    def setup_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create and add tabs
        self.tabs.addTab(self.create_blocked_sites_tab(), "Blocked Sites")
        self.tabs.addTab(self.create_excluded_sites_tab(), "Excluded Sites")
        self.tabs.addTab(self.create_categories_tab(), "Categories")
        self.tabs.addTab(self.create_settings_tab(), "Settings")
        self.tabs.addTab(self.create_online_users_tab(), "Online Users")
        self.tabs.addTab(self.create_user_management_tab(), "User Management")  # New tab

        self.setGeometry(100, 100, 800, 600)

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
        TableManager.setup_table(
            self.online_users_table,
            ['User ID', 'Address'],
            stretch_columns=[0, 1]
        )
        layout.addWidget(self.online_users_table)

        # Refresh button
        refresh_button = QPushButton("Refresh Users")
        refresh_button.clicked.connect(self.refresh_online_users)
        layout.addWidget(refresh_button)

        # Initial refresh
        self.refresh_online_users()

        container.setLayout(layout)
        return container

    def create_user_management_tab(self):
        # Create main widget and layout
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Create user selection section
        user_selection_layout = QHBoxLayout()
        user_label = QLabel("Select User:")
        self.user_combo = QComboBox()  # Will be populated with online users
        self.user_combo.setMinimumWidth(300)  # Set minimum width to make dropdown wider
        self.user_combo.currentTextChanged.connect(self.on_user_selected)  # Add signal handler
        user_selection_layout.addWidget(user_label)
        user_selection_layout.addWidget(self.user_combo)
        
        # Add refresh button next to user selection
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_online_users)
        user_selection_layout.addWidget(refresh_btn)
        user_selection_layout.addStretch()
        
        layout.addLayout(user_selection_layout)
        
        # Create tables for user settings
        tables_layout = QHBoxLayout()
        
        # Blocked Sites Table
        blocked_group = QGroupBox("Blocked Sites")
        blocked_layout = QVBoxLayout()
        self.user_blocked_table = QTableWidget()
        TableManager.setup_table(
            self.user_blocked_table,
            ["Site URL"],
            stretch_columns=[0]
        )
        blocked_layout.addWidget(self.user_blocked_table)
        
        # Add buttons for blocked sites
        blocked_buttons = QHBoxLayout()
        add_blocked_btn = QPushButton("Add")
        add_blocked_btn.clicked.connect(lambda: self.add_site_to_user_list("blocked"))
        edit_blocked_btn = QPushButton("Edit")
        edit_blocked_btn.clicked.connect(lambda: self.edit_user_site("blocked"))
        delete_blocked_btn = QPushButton("Delete")
        delete_blocked_btn.clicked.connect(lambda: self.delete_user_site("blocked"))
        blocked_buttons.addWidget(add_blocked_btn)
        blocked_buttons.addWidget(edit_blocked_btn)
        blocked_buttons.addWidget(delete_blocked_btn)
        blocked_layout.addLayout(blocked_buttons)
        blocked_group.setLayout(blocked_layout)
        
        # Excluded Sites Table
        excluded_group = QGroupBox("Excluded Sites")
        excluded_layout = QVBoxLayout()
        self.user_excluded_table = QTableWidget()
        TableManager.setup_table(
            self.user_excluded_table,
            ["Site URL"],
            stretch_columns=[0]
        )
        excluded_layout.addWidget(self.user_excluded_table)
        
        # Add buttons for excluded sites
        excluded_buttons = QHBoxLayout()
        add_excluded_btn = QPushButton("Add")
        add_excluded_btn.clicked.connect(lambda: self.add_site_to_user_list("excluded"))
        edit_excluded_btn = QPushButton("Edit")
        edit_excluded_btn.clicked.connect(lambda: self.edit_user_site("excluded"))
        delete_excluded_btn = QPushButton("Delete")
        delete_excluded_btn.clicked.connect(lambda: self.delete_user_site("excluded"))
        excluded_buttons.addWidget(add_excluded_btn)
        excluded_buttons.addWidget(edit_excluded_btn)
        excluded_buttons.addWidget(delete_excluded_btn)
        excluded_layout.addLayout(excluded_buttons)
        excluded_group.setLayout(excluded_layout)
        
        # Categories Table
        categories_group = QGroupBox("Categories")
        categories_layout = QVBoxLayout()
        self.user_categories_table = QTableWidget()
        TableManager.setup_table(
            self.user_categories_table,
            ["Category", "Keywords"],
            stretch_columns=[1]
        )
        categories_layout.addWidget(self.user_categories_table)
        
        # Add buttons for categories
        categories_buttons = QHBoxLayout()
        add_category_btn = QPushButton("Add")
        add_category_btn.clicked.connect(self.add_user_category)
        edit_category_btn = QPushButton("Edit")
        edit_category_btn.clicked.connect(self.edit_user_category)
        delete_category_btn = QPushButton("Delete")
        delete_category_btn.clicked.connect(self.delete_user_category)
        categories_buttons.addWidget(add_category_btn)
        categories_buttons.addWidget(edit_category_btn)
        categories_buttons.addWidget(delete_category_btn)
        categories_layout.addLayout(categories_buttons)
        categories_group.setLayout(categories_layout)
        
        # Add tables to layout
        tables_layout.addWidget(blocked_group)
        tables_layout.addWidget(excluded_group)
        tables_layout.addWidget(categories_group)
        
        # Create save button layout
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_user_settings)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        
        # Add all components to main layout
        layout.addLayout(tables_layout)
        layout.addLayout(button_layout)
        
        tab.setLayout(layout)
        return tab

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
                DialogManager.show_warning_dialog(
                    "Duplicate Entry",
                    "Site is already in the blocked or excluded list.",
                    self
                )
                return

            choice, ok = DialogManager.show_input_dialog(
                "Choose List",
                "Add site to:",
                parent=self,
                items=["Blocked Sites", "Excluded Sites"]
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
        current_tab = self.tabs.currentWidget()
        table = None
        sites_list = None
        
        if current_tab.findChild(SiteTable):
            table = current_tab.findChild(SiteTable)
            if table == self.blocked_table:
                sites_list = self.blocked_sites
            else:
                sites_list = self.excluded_sites
        
        if not table or table.currentRow() == -1:
            DialogManager.show_warning_dialog(
                "No Selection",
                "Please select a site to delete.",
                self
            )
            return
            
        site_item = table.item(table.currentRow(), 0)
        if site_item:
            site = site_item.text()
            list_name = "Blocked Sites" if table == self.blocked_table else "Excluded Sites"
            self.confirm_delete_site(site, list_name, sites_list, table)

    def confirm_delete_site(self, site, list_name, sites_list, table):
        if DialogManager.show_confirmation_dialog(
            "Confirm Delete",
            f"Are you sure you want to remove {site} from {list_name}?",
            self
        ):
            sites_list.remove(site)
            table.populate(sites_list)
            self.save_data()
            self.restart_mitmproxy()

    def add_category(self):
        category_name, ok = DialogManager.show_input_dialog(
            "Add Category",
            "Category Name:",
            parent=self
        )
        if ok and category_name:
            keywords, ok = DialogManager.show_input_dialog(
                "Add Keywords",
                "Keywords (comma separated):",
                parent=self
            )
            if ok:
                keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
                self.category_keywords[category_name] = keywords_list
                self.save_data()
                self.categories_table.populate(self.category_keywords)
                self.restart_mitmproxy()

    def delete_category(self):
        if self.categories_table.currentRow() == -1:
            DialogManager.show_warning_dialog(
                "No Selection",
                "Please select a category to delete.",
                self
            )
            return
            
        category_item = self.categories_table.item(self.categories_table.currentRow(), 0)
        if category_item:
            category_name = category_item.text()
            if DialogManager.show_confirmation_dialog(
                "Confirm Delete",
                f"Are you sure you want to delete category '{category_name}'?",
                self
            ):
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
            email, is_2fa_enabled = self.db.get_user_settings(user_id)
            if email is not None:
                print(f"Found user settings - Email: {email}, 2FA: {is_2fa_enabled}")  # Debug log
                self.email_input.setText(email or "")
                self.twofa_checkbox.setChecked(is_2fa_enabled)
            else:
                print(f"No user data found for ID: {user_id}")  # Debug log
            
        except DatabaseError as e:
            print(f"Error loading user settings: {str(e)}")  # Debug log
            DialogManager.show_error_dialog('Database Error', f'Could not load user settings: {str(e)}', self)

    def toggle_2fa(self, state):
        if state and not self.email_input.text().strip():
            DialogManager.show_warning_dialog('Email Required', 'Please enter an email address to enable 2FA', self)
            self.twofa_checkbox.setChecked(False)
            return

    def save_settings(self):
        print(f"Attempting to save settings for user ID: {self.current_user_id}")  # Debug log
        if not self.current_user_id:
            print("No user ID found")  # Debug log
            DialogManager.show_warning_dialog('Error', 'No user is currently logged in', self)
            return

        email = self.email_input.text().strip()
        is_2fa_enabled = self.twofa_checkbox.isChecked()
        print(f"Settings to save - Email: {email}, 2FA: {is_2fa_enabled}")  # Debug log

        if is_2fa_enabled and not email:
            DialogManager.show_warning_dialog('Email Required', 'Please enter an email address to enable 2FA', self)
            return

        try:
            # First verify if the user exists
            if not self.db.verify_user_exists(self.current_user_id):
                print(f"User not found in database: {self.current_user_id}")  # Debug log
                DialogManager.show_error_dialog('Error', 'User not found', self)
                return
            
            print("Executing update query...")  # Debug log
            if self.db.update_user_settings(self.current_user_id, email, is_2fa_enabled):
                DialogManager.show_info_dialog('Success', 'Settings saved successfully', self)
            else:
                DialogManager.show_error_dialog('Error', 'Failed to save settings', self)
            
        except DatabaseError as e:
            print(f"Error saving settings: {str(e)}")  # Debug log
            DialogManager.show_error_dialog('Database Error', f'Could not save settings: {str(e)}', self)

    def refresh_online_users(self):
        try:
            # Get registered users and their IPs
            response = requests.get(f"{self.server_url}/user-ips/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Update online users table
                online_users_data = []
                user_combo_data = []
                
                for user in data['user_ips']:
                    # Prepare table data
                    address = f"{user['ip_address']}:{user['port']}"
                    online_users_data.append([str(user['user_id']), address])
                    
                    # Prepare combo box data
                    display_text = f"{user['user_id']} - {address}"
                    user_combo_data.append(display_text)
                
                # Update table
                TableManager.populate_table(
                    self.online_users_table,
                    online_users_data,
                    is_list_of_lists=True
                )
                
                # Update combo box if in user management tab
                if hasattr(self, 'user_combo'):
                    current_user = self.user_combo.currentText()
                    self.user_combo.clear()
                    self.user_combo.addItems(user_combo_data)
                    
                    # Restore previous selection if it still exists
                    if current_user:
                        index = self.user_combo.findText(current_user)
                        if index >= 0:
                            self.user_combo.setCurrentIndex(index)
                    
        except Exception as e:
            print(f"Error refreshing users: {str(e)}")

    def on_user_selected(self):
        # Get the selected user info from the combo box
        selected_user = self.user_combo.currentText()
        if selected_user:
            try:
                # Extract user ID from the combo box text (format: "User ID - IP:Port")
                user_id = selected_user.split(" - ")[0]
                self.current_user_id = user_id
                
                # Get user settings directly from the main server
                user_settings_url = f"{self.server_url}/api/user-settings/"
                headers = {'Authorization': f'Bearer {user_id}'}
                print(f"Getting settings from: {user_settings_url}")  # Debug print
                
                user_settings_response = requests.get(user_settings_url, headers=headers, timeout=5)
                if user_settings_response.status_code == 200:
                    data = user_settings_response.json()
                    
                    # Update tables using TableManager
                    TableManager.populate_table(self.user_blocked_table, data.get('blocked_sites', []))
                    TableManager.populate_table(self.user_excluded_table, data.get('excluded_sites', []))
                    TableManager.populate_table(self.user_categories_table, data.get('categories', {}), is_dict=True)
                        
            except Exception as e:
                print(f"Error loading user settings: {str(e)}")
                DialogManager.show_error_dialog("Error", f"Failed to load user settings: {str(e)}", self)

    def save_user_settings(self):
        # Get selected user's info from combo box
        selected_user = self.user_combo.currentText()
        if not selected_user:
            DialogManager.show_warning_dialog("Error", "No user selected", self)
            return
            
        try:
            # Extract user ID and address from combo box text (format: "User ID - IP:Port")
            user_id, address = selected_user.split(" - ")
            
            # Get data from tables using TableManager
            blocked_sites = TableManager.get_table_data(self.user_blocked_table)
            excluded_sites = TableManager.get_table_data(self.user_excluded_table)
            categories = TableManager.get_table_data(self.user_categories_table, as_dict=True)
            
            # Prepare settings data
            settings = {
                'blocked_sites': blocked_sites,
                'excluded_sites': excluded_sites,
                'categories': categories
            }

            # Save to main server using POST method
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {user_id}'
            }
            
            server_response = requests.post(
                f"{self.server_url}/api/user-settings/",
                json=settings,
                headers=headers,
                verify=False
            )
            
            if server_response.status_code != 200:
                DialogManager.show_warning_dialog("Error", f"Failed to save settings to server: {server_response.text}", self)
                return
            
            DialogManager.show_info_dialog("Success", "Settings saved successfully. They will be applied when the user's client next polls for updates.", self)
            
        except Exception as e:
            print(f"Error saving user settings: {str(e)}")
            DialogManager.show_error_dialog("Error", f"Failed to save user settings: {str(e)}", self)

    def add_site_to_user_list(self, list_type):
        if not self.current_user_id:
            DialogManager.show_warning_dialog(
                "No User Selected",
                "Please select a user first.",
                self
            )
            return
            
        dialog = AddSiteDialog(self)
        if dialog.exec():
            site = dialog.get_input()
            if not site:
                return
                
            table = self.user_blocked_table if list_type == "blocked" else self.user_excluded_table
            if not TableManager.add_item(table, site, check_duplicates=True):
                DialogManager.show_warning_dialog(
                    "Duplicate Entry",
                    "Site is already in the list.",
                    self
                )

    def add_user_category(self):
        if not self.current_user_id:
            DialogManager.show_warning_dialog(
                "No User Selected",
                "Please select a user first.",
                self
            )
            return
            
        category, ok = DialogManager.show_input_dialog(
            "Add Category",
            "Category name:",
            parent=self
        )
        if ok and category:
            keywords, ok = DialogManager.show_input_dialog(
                "Add Keywords",
                "Keywords (comma separated):",
                parent=self
            )
            if ok:
                keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
                data = {category: keywords_list}
                TableManager.populate_table(self.user_categories_table, data, is_dict=True)

    def edit_user_category(self):
        if not self.current_user_id:
            DialogManager.show_warning_dialog(
                "No User Selected",
                "Please select a user first.",
                self
            )
            return
            
        current_row = self.user_categories_table.currentRow()
        if current_row == -1:
            DialogManager.show_warning_dialog(
                "No Selection",
                "Please select a category to edit.",
                self
            )
            return
            
        current_category = self.user_categories_table.item(current_row, 0).text()
        current_keywords = self.user_categories_table.item(current_row, 1).text()
        
        category, ok = DialogManager.show_input_dialog(
            "Edit Category",
            "Category name:",
            default=current_category,
            parent=self
        )
        if ok and category:
            keywords, ok = DialogManager.show_input_dialog(
                "Edit Keywords",
                "Keywords (comma separated):",
                default=current_keywords,
                parent=self
            )
            if ok:
                keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
                TableManager.edit_item(self.user_categories_table, current_row, category, keywords_list)

    def delete_user_category(self):
        if not self.current_user_id:
            DialogManager.show_warning_dialog(
                "No User Selected",
                "Please select a user first.",
                self
            )
            return
            
        current_row = self.user_categories_table.currentRow()
        if current_row == -1:
            DialogManager.show_warning_dialog(
                "No Selection",
                "Please select a category to delete.",
                self
            )
            return
            
        category = self.user_categories_table.item(current_row, 0).text()
        if DialogManager.show_confirmation_dialog(
            "Confirm Delete",
            f"Are you sure you want to delete category '{category}'?",
            self
        ):
            TableManager.delete_item(self.user_categories_table, current_row)

    def edit_user_site(self, list_type):
        if not self.current_user_id:
            DialogManager.show_warning_dialog(
                "No User Selected",
                "Please select a user first.",
                self
            )
            return
            
        table = self.user_blocked_table if list_type == "blocked" else self.user_excluded_table
        current_row = table.currentRow()
        if current_row == -1:
            DialogManager.show_warning_dialog(
                "No Selection",
                "Please select a site to edit.",
                self
            )
            return
            
        current_site = table.item(current_row, 0).text()
        dialog = AddSiteDialog(self, current_site)
        if dialog.exec():
            new_site = dialog.get_input()
            if new_site and new_site != current_site:
                TableManager.edit_item(table, current_row, new_site)

    def delete_user_site(self, list_type):
        if not self.current_user_id:
            DialogManager.show_warning_dialog(
                "No User Selected",
                "Please select a user first.",
                self
            )
            return
            
        table = self.user_blocked_table if list_type == "blocked" else self.user_excluded_table
        current_row = table.currentRow()
        if current_row == -1:
            DialogManager.show_warning_dialog(
                "No Selection",
                "Please select a site to delete.",
                self
            )
            return
            
        site = table.item(current_row, 0).text()
        if DialogManager.show_confirmation_dialog(
            "Confirm Delete",
            f"Are you sure you want to delete site '{site}'?",
            self
        ):
            TableManager.delete_item(table, current_row)

    def check_user_status(self, address, user_id):
        try:
            response = requests.get(f"http://{address}/status", timeout=2)
            if response.status_code == 200:
                data = response.json()
                if str(data.get('user_id')) == str(user_id):  # Verify user_id matches
                    return True, "Online"
            return False, "Offline"
        except:
            return False, "Offline"

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