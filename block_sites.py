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
        self.load_blocked_sites()

    def load_blocked_sites(self):
        local_file_loaded = False
        api_error = None
        
        try:
            # First try to get settings from API
            import requests
            import os
            from dotenv import load_dotenv
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
                
                # Disable the proxy for this request to avoid loop
                session = requests.Session()
                session.trust_env = False  # Don't use environment proxies
                
                response = session.get(
                    url,
                    headers=headers,
                    timeout=5  # Add timeout to prevent hanging
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.blocked_sites = data.get('blocked_sites', [])
                    self.excluded_sites = data.get('excluded_sites', [])
                    self.category_keywords = data.get('categories', {})
                    ctx.log.info("Successfully loaded configuration from API")
                    return
                else:
                    api_error = f"API returned status code: {response.status_code}"
                    raise Exception(api_error)
            
        except Exception as e:
            api_error = str(e)
            ctx.log.info(f"Error fetching settings from API: {api_error}")
            ctx.log.info("Falling back to local file")

        # If we get here, try loading from local file
        try:
            with open(self.blocked_sites_file, 'r') as f:
                data = json.load(f)
                self.blocked_sites = data.get('blocked_sites', [])
                self.excluded_sites = data.get('excluded_sites', [])
                self.category_keywords = data.get('categories', {})
                local_file_loaded = True
                ctx.log.info("Configuration loaded successfully from local file.")
        except Exception as e:
            ctx.log.error(f"Error loading local configuration file: {e}")
            if not local_file_loaded:
                # If neither API nor local file worked, initialize with empty values
                self.blocked_sites = []
                self.excluded_sites = []
                self.category_keywords = {}
                ctx.log.info("Initialized with empty configuration")

    def create_pattern_for_keywords(self, keywords):
        if not keywords:
            return None
        return re.compile("|".join(rf"\b{re.escape(keyword)}\b" for keyword in keywords), re.IGNORECASE)

    def is_excluded(self, host):
        # Check if it's the user settings API endpoint
        if '/api/user-settings/' in host or any(excluded in host for excluded in self.excluded_sites):
            return True
        return False

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
        if self.is_excluded(flow.request.host) or '/api/user-settings/' in flow.request.pretty_url:
            return

        try:
            if flow.response and flow.response.content:
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