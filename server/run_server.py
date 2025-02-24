import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'script_server.settings')
    try:
        django.setup()
        from daphne.cli import CommandLineInterface
        sys.argv = ['daphne', '-b', '0.0.0.0', '-p', '8000', 'script_server.asgi:application']
        CommandLineInterface.entrypoint()
    except Exception as e:
        print(f"Error starting server: {e}")
