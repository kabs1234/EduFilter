# Server Commands

## Start Development Server
To start the Django development server that's accessible from other devices on your network:
```bash
cd server
python manage.py runserver 0.0.0.0:8000
```

The server will be available at:
- Local: http://127.0.0.1:8000
- Network: http://<your-ip-address>:8000

## Start WebSocket-enabled Server
To start the Daphne server with WebSocket support:
```bash
cd server
python run_server.py
```

This server supports both HTTP and WebSocket protocols and is suitable for production use.
The server will be available at:
- HTTP: http://0.0.0.0:8000
- WebSocket: ws://0.0.0.0:8000/ws/status/

## Database Commands

### Apply Migrations
To apply database migrations:
```bash
cd server
python manage.py migrate
```

### Create New Migrations
After making changes to models, create new migration files:
```bash
cd server
python manage.py makemigrations
```

## Build Executable Files
To create Windows executable files (.exe) for both admin panel and user GUI:

1. First, install cx_Freeze if not already installed:
```bash
pip install cx_Freeze
```

2. Build the executables:
```bash
python setup.py build
```

The executables will be created in the `build/exe.win-amd64-3.10` directory:
- `admin_panel.exe` - Administrator interface
- `user_gui.exe` - User interface

Note: When distributing the application, include the entire `build/exe.win-amd64-3.10` directory as it contains all necessary dependencies.
