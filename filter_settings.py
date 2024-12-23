from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QRadioButton, QPushButton, QHBoxLayout, QLabel, QWidget

class FilterSettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Filter Settings')

        # Filter Levels
        self.strict_filter = QRadioButton('Strict')
        self.moderate_filter = QRadioButton('Moderate')
        self.relaxed_filter = QRadioButton('Relaxed')

        # Buttons
        self.save_button = QPushButton('Save', self)
        self.save_button.clicked.connect(self.save_settings)

        # Layout
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(self.strict_filter)
        filter_layout.addWidget(self.moderate_filter)
        filter_layout.addWidget(self.relaxed_filter)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)

        layout = QVBoxLayout()
        layout.addLayout(filter_layout)
        layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def save_settings(self):
        if self.strict_filter.isChecked():
            print("Filter level set to Strict")
        elif self.moderate_filter.isChecked():
            print("Filter level set to Moderate")
        elif self.relaxed_filter.isChecked():
            print("Filter level set to Relaxed")
