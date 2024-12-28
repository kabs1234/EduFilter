import subprocess
import winreg as reg
import elevate

# Function to set the proxy in Windows registry
def set_windows_proxy(proxy_address='127.0.0.1', proxy_port=8080):
    try:
        registry_key = reg.OpenKey(
            reg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, reg.KEY_WRITE)
        reg.SetValueEx(registry_key, "ProxyEnable", 0, reg.REG_DWORD, 1)
        reg.SetValueEx(registry_key, "ProxyServer", 0, reg.REG_SZ, f"{proxy_address}:{proxy_port}")
        reg.CloseKey(registry_key)
        print(f"Proxy is set to {proxy_address}:{proxy_port} in Windows settings.")
    except Exception as e:
        print(f"Error setting proxy in Windows registry: {e}")


# Function to automatically set the proxy in Windows
def set_proxy_automatically():
    elevate.elevate()
    set_windows_proxy()


# Function to start mitmproxy
def start_mitmproxy():
    try:
        subprocess.Popen(['mitmproxy', '--listen-host', '127.0.0.1', '--listen-port', '8080', '-s', 'block_sites.py'])
        print("mitmproxy is running at 127.0.0.1:8080")
    except Exception as e:
        print(f"Error starting mitmproxy: {e}")


def launch_proxy():
    set_proxy_automatically()
    start_mitmproxy()
