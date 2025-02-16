from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QPushButton,
    QVBoxLayout, QLabel, QMessageBox, QInputDialog
)
from typing import Optional, Tuple, Any

class DialogManager:
    """A utility class to manage dialog interactions consistently across the application."""

    @staticmethod
    def show_warning_dialog(title: str, message: str, parent=None):
        """Show a warning dialog with the given title and message."""
        QMessageBox.warning(parent, title, message)

    @staticmethod
    def show_error_dialog(title: str, message: str, parent=None):
        """Show an error dialog with the given title and message."""
        QMessageBox.critical(parent, title, message)

    @staticmethod
    def show_info_dialog(title: str, message: str, parent=None):
        """Show an information dialog with the given title and message."""
        QMessageBox.information(parent, title, message)

    @staticmethod
    def show_confirmation_dialog(title: str, message: str, parent=None) -> bool:
        """Show a confirmation dialog with Yes/No buttons.
        
        Returns:
            bool: True if user clicked Yes, False otherwise
        """
        reply = QMessageBox.question(
            parent,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    @staticmethod
    def show_input_dialog(title: str, message: str, parent=None, default: str = "", items: list = None) -> tuple:
        """Show an input dialog for text or item selection.
        
        Args:
            title: Dialog title
            message: Dialog message/prompt
            parent: Parent widget
            default: Default text value for text input
            items: List of items for item selection
            
        Returns:
            tuple: (input_value, ok_pressed)
            - For text input: (str, bool)
            - For item selection: (str, bool)
        """
        if items:
            return QInputDialog.getItem(parent, title, message, items, 0, False)
        else:
            return QInputDialog.getText(parent, title, message, text=default)

    @staticmethod
    def show_custom_dialog(dialog_class, parent=None, *args, **kwargs):
        """Show a custom dialog and return its result.
        
        Args:
            dialog_class: The dialog class to instantiate
            parent: Parent widget
            *args, **kwargs: Additional arguments for the dialog class
            
        Returns:
            tuple: (dialog_instance, dialog_result)
        """
        dialog = dialog_class(parent, *args, **kwargs)
        result = dialog.exec()
        return dialog, result

class InputDialog(QDialog):
    def __init__(
        self,
        title: str,
        fields: list,
        parent: Any = None,
        buttons: list = None
    ):
        """
        Generic input dialog
        
        Args:
            title: Dialog title
            fields: List of (label, default_value) tuples
            parent: Parent widget
            buttons: List of (button_text, slot) tuples
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.layout = QFormLayout()
        self.setLayout(self.layout)
        
        # Create input fields
        self.inputs = {}
        for label, default in fields:
            input_field = QLineEdit(default)
            self.layout.addRow(label, input_field)
            self.inputs[label] = input_field
            
        # Add buttons
        if not buttons:
            buttons = [("OK", self.accept)]
            
        button_layout = QVBoxLayout()
        for text, slot in buttons:
            button = QPushButton(text)
            button.clicked.connect(slot)
            button_layout.addWidget(button)
            
        self.layout.addRow("", button_layout)
        
    def get_values(self) -> dict:
        """Get the values from all input fields"""
        return {label: field.text() for label, field in self.inputs.items()}
