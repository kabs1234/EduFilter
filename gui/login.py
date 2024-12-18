from PyQt6.QtWidgets import QApplication, QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QWidget, QLabel

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Admin Login')

        # Username and Password
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Enter username")

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Login Button
        self.login_button = QPushButton('Login', self)
        self.login_button.clicked.connect(self.login)

        # Error Label
        self.error_label = QLabel("", self)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        layout.addWidget(self.error_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def login(self):
        # Validate username and password (simple validation)
        if self.username_input.text() == 'admin' and self.password_input.text() == 'password':
            self.error_label.setText("Login successful!")
            self.open_dashboard()
        else:
            self.error_label.setText("Invalid credentials. Please try again.")

    def open_dashboard(self):
        self.dashboard = DashboardWindow()
        self.dashboard.show()
        self.close()

