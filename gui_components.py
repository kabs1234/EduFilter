from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QDialog, QFormLayout
)

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