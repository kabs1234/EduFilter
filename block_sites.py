import mitmproxy.http
from mitmproxy import ctx
import json
import re


class BlockSites:
    def __init__(self):
        self.blocked_sites_file = 'blocked_sites.json'
        self.blocked_sites = []
        self.excluded_sites = []
        self.category_keywords = {}
        self.last_update_time = 0
        self.reload_interval = 5  # Check for updates every 5 seconds
        self.api_failed = False  # Flag to track API connection failure
        self.load_blocked_sites()

    def load_blocked_sites(self):
        # If API previously failed, just load from local file
        if self.api_failed:
            self.load_from_local_file()
            return
            
        try:
            # First try to get settings from API
            import requests
            import os
            from dotenv import load_dotenv
            from urllib3.util.retry import Retry
            from requests.adapters import HTTPAdapter
            load_dotenv()

            server_url = os.getenv('SERVER_URL', 'http://127.0.0.1:8000')
            # Get the user ID from the .env file
            user_id = None
            try:
                with open('.env', 'r') as f:
                    for line in f:
                        if line.startswith('USER_ID='):
                            user_id = line.strip().split('=')[1]
                            break
            except Exception as e:
                ctx.log.info(f"Could not read USER_ID from .env: {e}")

            if user_id:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {user_id}'
                }
                
                url = f"{server_url}/api/user-settings/{user_id}/"
                
                # Configure session with minimal retries
                session = requests.Session()
                retries = Retry(
                    total=1,  # Only retry once (2 total attempts)
                    backoff_factor=0.1,  # Quick backoff
                    status_forcelist=[500, 502, 503, 504]
                )
                session.proxies = {
                    'http': None,
                    'https': None,
                }
                session.trust_env = False
                adapter = HTTPAdapter(max_retries=retries)
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                
                try:
                    response = session.get(
                        url,
                        headers=headers,
                        timeout=5  # Reduced timeout
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.blocked_sites = data.get('blocked_sites', [])
                        self.excluded_sites = data.get('excluded_sites', [])
                        self.category_keywords = data.get('categories', {})
                        ctx.log.info("Successfully loaded configuration from API")
                        return
                    else:
                        raise Exception(f"API returned status code: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    raise Exception(f"Network error while connecting to API: {str(e)}")
            
        except Exception as e:
            ctx.log.info(f"Error fetching settings from API: {e}")
            ctx.log.info("Falling back to local file")
            self.api_failed = True  # Mark API as failed to prevent future attempts
            self.load_from_local_file()

    def load_from_local_file(self):
        """Load settings from local file."""
        try:
            with open(self.blocked_sites_file, 'r') as f:
                data = json.load(f)
                self.blocked_sites = data.get('blocked_sites', [])
                self.excluded_sites = data.get('excluded_sites', [])
                self.category_keywords = data.get('categories', {})
                ctx.log.info("Configuration loaded successfully from local file.")
        except Exception as e:
            ctx.log.error(f"Error loading local configuration file: {e}")
            # If local file fails, initialize with empty values
            self.blocked_sites = []
            self.excluded_sites = []
            self.category_keywords = {}
            ctx.log.info("Initialized with empty configuration")

    def create_pattern_for_keywords(self, keywords):
        if not keywords:
            return None
        return re.compile("|".join(rf"\b{re.escape(keyword)}\b" for keyword in keywords), re.IGNORECASE)

    def is_excluded(self, host):
        # Always allow localhost and local network
        if host in ['localhost', '127.0.0.1', '::1'] or '.local' in host:
            return True
            
        # Always allow the server URL
        server_host = self.get_server_host()
        if server_host and server_host in host:
            return True

        # Check excluded sites
        for excluded in self.excluded_sites:
            if excluded in host:
                return True
                
        return False

    def get_server_host(self):
        """Extract host from SERVER_URL in .env"""
        try:
            from urllib.parse import urlparse
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            server_url = os.getenv('SERVER_URL', 'http://127.0.0.1:8000')
            parsed = urlparse(server_url)
            return parsed.netloc
        except:
            return None

    def show_warning_page(self, flow, message):
        """Respond with a custom warning page."""
        html_content = f"""
        <html>
        <head><title>Site Blocked</title></head>
        <body>
            <h1>Access Blocked</h1>
            <p>{message}</p>
            <p>If you think this is a mistake, please contact your administrator.</p>
        </body>
        </html>
        """
        flow.response = mitmproxy.http.Response.make(
            403,
            html_content.encode('utf-8'),
            {"Content-Type": "text/html"}
        )

    def request(self, flow: mitmproxy.http.HTTPFlow) -> None:
        # Skip if no host
        if not flow.request.host:
            return
            
        import time
        current_time = time.time()
        if current_time - self.last_update_time > self.reload_interval:
            self.load_blocked_sites()
            self.last_update_time = current_time

        if self.is_excluded(flow.request.host):
            ctx.log.info(f"Allowing excluded site: {flow.request.pretty_url}")
            return

        for blocked_site in self.blocked_sites:
            if blocked_site in flow.request.host:
                self.show_warning_page(flow, f"Site '{flow.request.host}' is blocked.")
                ctx.log.info(f"Blocked site: {flow.request.pretty_url}")
                return

    def response(self, flow: mitmproxy.http.HTTPFlow) -> None:
        # Skip if no host or is excluded
        if not flow.request.host or self.is_excluded(flow.request.host):
            return

        try:
            if flow.response and flow.response.content:
                content_type = flow.response.headers.get("content-type", "")
                # Only check text content
                if "text" in content_type or "javascript" in content_type:
                    content = flow.response.content.decode('utf-8', errors='ignore')
                    for category, keywords in self.category_keywords.items():
                        pattern = self.create_pattern_for_keywords(keywords)
                        if pattern:
                            matches = pattern.findall(content)
                            if matches:  # Block if any keyword is found
                                self.show_warning_page(flow, f"Blocked due to inappropriate content in category: {category}.")
                                ctx.log.info(f"Blocked content from {flow.request.pretty_url} due to category: {category}")
                                return
        except Exception as e:
            ctx.log.error(f"Error processing response: {e}")


addons = [BlockSites()]