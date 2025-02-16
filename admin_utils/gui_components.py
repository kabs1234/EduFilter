from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QDialog, QFormLayout, QHeaderView
)
from .table_utils import TableManager
from .dialog_utils import InputDialog

class BaseDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.layout = QFormLayout()
        self.setLayout(self.layout)

class AddSiteDialog(InputDialog):
    def __init__(self, parent=None, current_site=None):
        title = 'Edit Site' if current_site else 'Add Site'
        super().__init__(
            title,
            [("Site URL:", current_site or "")],
            parent
        )

    def get_input(self):
        return self.get_values()["Site URL:"]

class TwoFactorDialog(InputDialog):
    def __init__(self, parent=None):
        super().__init__(
            'Two-Factor Authentication',
            [("Enter Code:", "")],
            parent
        )
    
    def get_code(self):
        return self.get_values()["Enter Code:"].strip()

class BaseTable(QTableWidget):
    def __init__(self, headers, stretch_columns=None):
        super().__init__()
        TableManager.setup_table(self, headers, stretch_columns)

class SiteTable(BaseTable):
    def __init__(self, header_label):
        super().__init__([header_label], [0])

    def populate(self, sites):
        TableManager.populate_table(self, sites)

    def add_site(self, site):
        return TableManager.add_item(self, site)
  
class CategoryTable(BaseTable):
    def __init__(self):
        super().__init__(['Category', 'Keywords'], [1])

    def populate(self, categories):
        TableManager.populate_table(self, categories, is_dict=True)