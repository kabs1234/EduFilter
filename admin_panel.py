import json
import os
from dotenv import load_dotenv
import psycopg2
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QPushButton, QWidget, QLineEdit, QDialog, QFormLayout, QMessageBox, 
    QInputDialog, QTabWidget, QLabel
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


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Login')
        self.setModal(True)
        self.setMinimumWidth(300)
        
        layout = QFormLayout()
        
        # Username input
        self.username_input = QLineEdit()
        layout.addRow('Username:', self.username_input)
        
        # Password input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow('Password:', self.password_input)
        
        # Login button
        login_button = QPushButton('Login')
        login_button.clicked.connect(self.try_login)
        layout.addRow(login_button)
        
        self.setLayout(layout)
        
        # Load database configuration
        load_dotenv()
        self.db_config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST')
        }
        
    def try_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            # Check if user exists and password matches
            cur.execute(
                "SELECT * FROM users WHERE username = %s AND password = %s",
                (username, password)
            )
            
            if cur.fetchone():
                self.accept()
            else:
                QMessageBox.warning(self, 'Login Failed', 'Invalid username or password')
            
            cur.close()
            conn.close()
            
        except Exception as e:
            QMessageBox.critical(self, 'Database Error', f'Could not connect to database: {str(e)}')


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Content Monitoring Dashboard')

        # File to store blocked sites
        self.blocked_sites_file = 'blocked_sites.json'

        # Load blocked sites from file
        self.blocked_sites, self.excluded_sites, self.category_keywords = self.load_blocked_sites()

        # Create tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_blocked_sites_tab(), "Blocked Sites")
        self.tab_widget.addTab(self.create_excluded_sites_tab(), "Excluded Sites")
        self.tab_widget.addTab(self.create_categories_tab(), "Categories")

        self.setCentralWidget(self.tab_widget)

    def create_blocked_sites_tab(self):
        # Blocked sites table
        self.blocked_table = QTableWidget()
        self.blocked_table.setColumnCount(1)
        self.blocked_table.setHorizontalHeaderLabels(['Blocked Sites'])
        self.populate_blocked_table()

        # Add and delete buttons
        add_site_button = QPushButton('Add Site')
        add_site_button.clicked.connect(self.open_add_site_dialog)

        delete_site_button = QPushButton('Delete Site')
        delete_site_button.clicked.connect(self.delete_selected_site)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.blocked_table)
        layout.addWidget(add_site_button)
        layout.addWidget(delete_site_button)

        container = QWidget()
        container.setLayout(layout)
        return container

    def create_excluded_sites_tab(self):
        # Excluded sites table
        self.excluded_table = QTableWidget()
        self.excluded_table.setColumnCount(1)
        self.excluded_table.setHorizontalHeaderLabels(['Excluded Sites'])
        self.populate_excluded_table()

        # Add and delete buttons
        add_site_button = QPushButton('Add Site')
        add_site_button.clicked.connect(self.open_add_site_dialog)

        delete_site_button = QPushButton('Delete Site')
        delete_site_button.clicked.connect(self.delete_selected_site)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.excluded_table)
        layout.addWidget(add_site_button)
        layout.addWidget(delete_site_button)

        container = QWidget()
        container.setLayout(layout)
        return container

    def create_categories_tab(self):
        # Categories table
        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(2)
        self.categories_table.setHorizontalHeaderLabels(['Category', 'Keywords'])
        self.populate_categories_table()

        # Add and delete buttons
        add_category_button = QPushButton('Add Category')
        add_category_button.clicked.connect(self.add_category)

        delete_category_button = QPushButton('Delete Category')
        delete_category_button.clicked.connect(self.delete_category)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.categories_table)
        layout.addWidget(add_category_button)
        layout.addWidget(delete_category_button)

        container = QWidget()
        container.setLayout(layout)
        return container

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

    def populate_categories_table(self):
        self.categories_table.setRowCount(0)
        for category, keywords in self.category_keywords.items():
            row_position = self.categories_table.rowCount()
            self.categories_table.insertRow(row_position)
            self.categories_table.setItem(row_position, 0, QTableWidgetItem(category))
            self.categories_table.setItem(row_position, 1, QTableWidgetItem(", ".join(keywords)))

    def open_add_site_dialog(self):
        dialog = AddSiteDialog(self)
        if dialog.exec():
            site = dialog.get_input()
            if site:
                if site in self.blocked_sites or site in self.excluded_sites:
                    QMessageBox.warning(self, "Duplicate Entry", "Site is already in the blocked or excluded list.")
                    return

                choice, ok = QInputDialog.getItem(self, "Choose List", "Add site to:", ["Blocked Sites", "Excluded Sites"], 0, False)
                if ok and choice:
                    if choice == "Blocked Sites":
                        self.blocked_sites.append(site)
                        self.populate_blocked_table()
                    elif choice == "Excluded Sites":
                        self.excluded_sites.append(site)
                        self.populate_excluded_table()

                self.save_blocked_sites()
                self.restart_mitmproxy()

    def delete_selected_site(self):
        selected_row_blocked = self.blocked_table.currentRow()
        selected_row_excluded = self.excluded_table.currentRow()

        if selected_row_blocked != -1:
            site_item = self.blocked_table.item(selected_row_blocked, 0)
            if site_item:
                site = site_item.text()
                self.confirm_delete_site(site, "Blocked Sites", selected_row_blocked)
        elif selected_row_excluded != -1:
            site_item = self.excluded_table.item(selected_row_excluded, 0)
            if site_item:
                site = site_item.text()
                self.confirm_delete_site(site, "Excluded Sites", selected_row_excluded)
        else:
            QMessageBox.warning(self, "No Selection", "Please select a site to delete.")

    def confirm_delete_site(self, site, list_name, row):
        confirmation = QMessageBox.question(
            self, "Confirm Delete", f"Are you sure you want to remove {site} from {list_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirmation == QMessageBox.StandardButton.Yes:
            if list_name == "Blocked Sites":
                self.blocked_sites.remove(site)
                self.populate_blocked_table()
            elif list_name == "Excluded Sites":
                self.excluded_sites.remove(site)
                self.populate_excluded_table()

            self.save_blocked_sites()
            self.restart_mitmproxy()

    def add_category(self):
        category_name, ok = QInputDialog.getText(self, "Add Category", "Category Name:")
        if ok and category_name:
            keywords, ok = QInputDialog.getText(self, "Add Keywords", "Keywords (comma separated):")
            if ok:
                keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
                self.category_keywords[category_name] = keywords_list
                self.save_blocked_sites()
                self.populate_categories_table()
                self.restart_mitmproxy()

    def delete_category(self):
        selected_row = self.categories_table.currentRow()
        if selected_row != -1:
            category_item = self.categories_table.item(selected_row, 0)
            if category_item:
                category_name = category_item.text()
                confirmation = QMessageBox.question(
                    self, "Confirm Delete", f"Are you sure you want to delete category '{category_name}'?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirmation == QMessageBox.StandardButton.Yes:
                    del self.category_keywords[category_name]
                    self.save_blocked_sites()
                    self.populate_categories_table()
                    self.restart_mitmproxy()

    def restart_mitmproxy(self):
        subprocess.call(["taskkill", "/F", "/IM", "mitmdump.exe"])
        subprocess.Popen(['mitmdump', '--listen-host', '127.0.0.1', '--listen-port', '8080', '-s', 'block_sites.py'])

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


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    launch_proxy()
    app = QApplication(sys.argv)
    
    # Show login dialog first
    login_dialog = LoginDialog()
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        # Only show main window if login was successful
        window = DashboardWindow()
        window.show()
        sys.exit(app.exec())