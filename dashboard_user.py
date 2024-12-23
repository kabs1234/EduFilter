import json
from PyQt6.QtWidgets import (
    QMainWindow, QLabel, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QPushButton, QWidget, QLineEdit, QDialog, QFormLayout, QMessageBox
)
from filter_settings import FilterSettingsWindow  # Import FilterSettingsWindow from filter_settings.py


class AddSiteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Site')
        self.layout = QFormLayout()

        self.site_input = QLineEdit(self)
        self.status_input = QLineEdit(self)

        self.layout.addRow("Site URL:", self.site_input)
        self.layout.addRow("Status:", self.status_input)

        self.add_button = QPushButton("Add", self)
        self.add_button.clicked.connect(self.accept)
        self.layout.addWidget(self.add_button)

        self.setLayout(self.layout)

    def get_inputs(self):
        return self.site_input.text(), self.status_input.text()


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Content Monitoring Dashboard')

        # Load blocked sites from file
        self.blocked_sites = self.load_blocked_sites()

        # Content Table
        self.content_table = QTableWidget(self)
        self.content_table.setColumnCount(2)
        self.content_table.setHorizontalHeaderLabels(['Content', 'Status'])

        # Alert Panel
        self.alert_label = QLabel("No alerts", self)

        # Filter Settings Button
        self.filter_settings_button = QPushButton('Filter Settings', self)
        self.filter_settings_button.clicked.connect(self.open_filter_settings)

        # Add Site Button
        self.add_site_button = QPushButton('Add Site', self)
        self.add_site_button.clicked.connect(self.open_add_site_dialog)

        # Delete Site Button
        self.delete_site_button = QPushButton('Delete Site', self)
        self.delete_site_button.clicked.connect(self.delete_selected_site)

        # View Blocked Sites Button
        self.view_blocked_sites_button = QPushButton('View Blocked Sites', self)
        self.view_blocked_sites_button.clicked.connect(self.view_blocked_sites)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.content_table)
        layout.addWidget(self.alert_label)
        layout.addWidget(self.filter_settings_button)
        layout.addWidget(self.add_site_button)
        layout.addWidget(self.delete_site_button)
        layout.addWidget(self.view_blocked_sites_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_blocked_sites(self):
        try:
            with open('blocked_sites.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def save_blocked_sites(self):
        with open('blocked_sites.json', 'w') as file:
            json.dump(self.blocked_sites, file)

    def open_filter_settings(self):
        self.filter_settings_window = FilterSettingsWindow()
        self.filter_settings_window.show()

    def open_add_site_dialog(self):
        dialog = AddSiteDialog(self)
        if dialog.exec():
            site, status = dialog.get_inputs()
            if site and status:
                self.add_to_content_table(site, status)

    def add_to_content_table(self, site, status):
        row_position = self.content_table.rowCount()
        self.content_table.insertRow(row_position)
        self.content_table.setItem(row_position, 0, QTableWidgetItem(site))
        self.content_table.setItem(row_position, 1, QTableWidgetItem(status))
        if status.lower() == "blocked":
            self.blocked_sites.append(site)
            self.save_blocked_sites()  # Save after adding a blocked site

    def delete_selected_site(self):
        selected_row = self.content_table.currentRow()
        if selected_row != -1:
            site_item = self.content_table.item(selected_row, 0)  # Get the site cell
            status_item = self.content_table.item(selected_row, 1)  # Get the status cell

            if site_item and status_item:  # Ensure both items exist
                site = site_item.text()
                status = status_item.text()

                confirmation = QMessageBox.question(
                    self, "Confirm Delete", "Are you sure you want to delete the selected site?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirmation == QMessageBox.StandardButton.Yes:
                    self.content_table.removeRow(selected_row)
                    if status.lower() == "blocked" and site in self.blocked_sites:
                        self.blocked_sites.remove(site)
                        self.save_blocked_sites()  # Save after removing a blocked site
            else:
                QMessageBox.warning(self, "Invalid Selection", "The selected row is incomplete or invalid.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select a site to delete.")

    def view_blocked_sites(self):
        if self.blocked_sites:
            blocked_sites_str = "\n".join(self.blocked_sites)
            QMessageBox.information(self, "Blocked Sites", f"The following sites are blocked:\n{blocked_sites_str}")
        else:
            QMessageBox.information(self, "Blocked Sites", "No sites are currently blocked.")
