from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from typing import List, Dict, Any, Union

class TableManager:
    @staticmethod
    def setup_table(table: QTableWidget, headers: List[str], stretch_columns: List[int] = None):
        """Setup a table with headers and column stretching"""
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        if stretch_columns:
            for col in range(table.columnCount()):
                if col in stretch_columns:
                    table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
                else:
                    table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

    @staticmethod
    def populate_table(table: QTableWidget, data: Union[List[str], List[List[str]], Dict[str, List[str]]], is_dict: bool = False, is_list_of_lists: bool = False):
        """Populate table with data"""
        table.setRowCount(0)
        
        if is_dict:
            for key, value in data.items():
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(key))
                table.setItem(row, 1, QTableWidgetItem(", ".join(value) if isinstance(value, list) else str(value)))
        elif is_list_of_lists:
            for row_data in data:
                row = table.rowCount()
                table.insertRow(row)
                for col, value in enumerate(row_data):
                    table.setItem(row, col, QTableWidgetItem(str(value)))
        else:
            for item in data:
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(str(item)))

    @staticmethod
    def get_table_data(table: QTableWidget, as_dict: bool = False) -> Union[List[str], Dict[str, List[str]]]:
        """Get data from table"""
        if as_dict:
            data = {}
            for row in range(table.rowCount()):
                key = table.item(row, 0).text()
                value = [v.strip() for v in table.item(row, 1).text().split(",")]
                data[key] = value
            return data
        else:
            return [table.item(row, 0).text() for row in range(table.rowCount())]

    @staticmethod
    def add_item(table: QTableWidget, item: str, check_duplicates: bool = True) -> bool:
        """Add an item to the table"""
        if check_duplicates:
            current_items = TableManager.get_table_data(table)
            if item in current_items:
                return False
                
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(item))
        return True

    @staticmethod
    def edit_item(table: QTableWidget, row: int, new_value: str, check_duplicates: bool = True) -> bool:
        """Edit an item in the table"""
        if check_duplicates:
            current_items = TableManager.get_table_data(table)
            if new_value in current_items:
                return False
                
        table.setItem(row, 0, QTableWidgetItem(new_value))
        return True

    @staticmethod
    def delete_item(table: QTableWidget, row: int):
        """Delete an item from the table"""
        table.removeRow(row)
