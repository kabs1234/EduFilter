import json
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QPushButton, QWidget, QLineEdit, QDialog, QFormLayout, QMessageBox
)
from setup_proxy_and_mitm import launch_proxy, disable_windows_proxy


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

    def closeEvent(self, event):
        # Call disable_windows_proxy before closing the window

        # Ask for confirmation before closing the window
        confirmation = QMessageBox.question(
            self, "Confirm Exit", "Are you sure you want to exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirmation == QMessageBox.StandardButton.Yes:
            # Perform any other necessary actions before closing, such as saving data
            disable_windows_proxy()
            self.save_blocked_sites()  # Save the blocked sites before closing
            event.accept()  # Proceed with closing the window
        else:
            event.ignore()  # Cancel the close event (window stays open)


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication

    launch_proxy()
    app = QApplication(sys.argv)
    window = DashboardWindow()
    window.show()
    sys.exit(app.exec())
