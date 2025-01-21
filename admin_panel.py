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
        
    def try_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
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
        
        self.setup_ui()

    def setup_ui(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_blocked_sites_tab(), "Blocked Sites")
        self.tab_widget.addTab(self.create_excluded_sites_tab(), "Excluded Sites")
        self.tab_widget.addTab(self.create_categories_tab(), "Categories")
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

    def closeEvent(self, event):
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
        window = DashboardWindow()
        window.show()
        sys.exit(app.exec())