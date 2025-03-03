from cx_Freeze import setup, Executable
import sys

# Dependencies are automatically detected, but it might need fine-tuning.
build_exe_options = {
    "packages": [
        "json", "os", "sys", "uuid", "socket", "threading", "logging",
        "http.server", "datetime", "random", "string", "requests",
        "dotenv", "psycopg2", "PyQt6", "email_utils",
        "mitmproxy", "mitmproxy.http", "mitmproxy.ctx", "urllib.parse",
        "re", "winreg"  # Added winreg for Windows registry operations
    ],
    "excludes": [],
    "include_files": [
        "blocked_sites.json",
        ".env",
        "admin_utils/",
        "icons/",  # Include icons directory
        "block_sites.py",  # Include the proxy script
    ]
}

# GUI applications require a different base on Windows
base = None
if sys.platform == "win32":
    base = "Win32GUI"

executables = [
    Executable(
        "admin_panel.py",
        base=base,
        target_name="admin_panel.exe",
        icon="icons/edufilter.ico"  # Set icon for admin panel
    ),
    Executable(
        "user_gui.py",
        base=base,
        target_name="user_gui.exe",
        icon="icons/edufilter.ico"  # Set icon for user GUI
    )
]

setup(
    name="EduFilter",
    version="1.0",
    description="Content Monitoring and Filtering System",
    options={"build_exe": build_exe_options},
    executables=executables)
