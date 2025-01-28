import requests

def execute_script_on_server(server_url, script_name, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"script": script_name}

    try:
        response = requests.post(
            f"{server_url}/api/execute/",
            data=payload,
            headers=headers
        )
        print("Response from server:")
        print(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to server: {e}")

if __name__ == '__main__':
    SERVER_URL = "http://192.168.0.101:8000"  # Replace with your server's IP and port
    SCRIPT_NAME = "script.py"  # Replace with the script you want to execute
    API_KEY = "secret123"  # Replace with your actual API key

    execute_script_on_server(SERVER_URL, SCRIPT_NAME, API_KEY)