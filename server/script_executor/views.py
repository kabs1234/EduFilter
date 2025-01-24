from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import subprocess
import os
from pathlib import Path

# Allowed scripts (for security)

# Base directory of the Django project
BASE_DIR = Path(__file__).resolve().parent.parent

# Absolute path to the scripts directory
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')

# Allowed scripts (for security)
ALLOWED_SCRIPTS = {
    "script.py": os.path.join(SCRIPTS_DIR, "script.py"),  # Absolute path
}

# API key for authentication (change this to a secure key)
API_KEY = "secret123"  # Replace this with a strong key in production

@csrf_exempt
def execute_script(request):
    if request.method == 'POST':
        script_name = request.POST.get('script')

        if script_name not in ALLOWED_SCRIPTS:
            return JsonResponse({"error": "Unauthorized script"}, status=403)

        script_path = ALLOWED_SCRIPTS[script_name]
        print(f"Executing script: {script_path}")  # Debug print

        try:
            result = subprocess.run(
                ["python", script_path],  # Explicitly use Python to run the script
                capture_output=True,
                text=True,
                shell=True
            )
            print(f"Script output: {result.stdout}")  # Debug print
            print(f"Script error: {result.stderr}")   # Debug print
            return JsonResponse({
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)