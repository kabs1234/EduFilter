from cx_Freeze import setup, Executable
import sys

# Dependencies are automatically detected, but it might need fine-tuning.
build_exe_options = {
    "packages": [
        "json", "os", "sys", "uuid", "socket", "threading", "logging",
        "http.server", "datetime", "random", "string", "requests",
        "dotenv", "psycopg2", "PyQt6", "email_utils"
    ],
    "excludes": [],
    "include_files": [
        "blocked_sites.json",
        ".env",
        "admin_utils/",
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
        icon=None  # You can add an icon file here if you have one
    ),
    Executable(
        "user_gui.py",
        base=base,
        target_name="user_gui.exe",
        icon=None  # You can add an icon file here if you have one
    )
]

setup(
    name="EduFilter",
    version="1.0",
    description="Content Monitoring and Filtering System",
    options={"build_exe": build_exe_options},
    executables=executables
)
