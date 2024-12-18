from PyQt6.QtWidgets import QApplication
from dashboard_user import DashboardWindow  # Import LoginWindow from login_window.py

if __name__ == '__main__':
    app = QApplication([])

    # Start with Login Window
    dashboardwindow = DashboardWindow()
    dashboardwindow.show()

    app.exec()
