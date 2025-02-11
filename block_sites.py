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
        self.load_blocked_sites()

    def load_blocked_sites(self):
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
                ctx.log.error(f"Error reading USER_ID from .env: {e}")

            if user_id:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {user_id}'
                }
                
                url = f"{server_url}/api/user-settings/"
                
                # Disable the proxy for this request to avoid loop
                session = requests.Session()
                session.trust_env = False  # Don't use environment proxies
                
                response = session.get(
                    url,
                    headers=headers,
                    timeout=5,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.blocked_sites = data.get('blocked_sites', [])
                    self.excluded_sites = data.get('excluded_sites', [])
                    self.category_keywords = data.get('categories', {})
                    ctx.log.info("Settings loaded successfully from API")
                    return
                else:
                    ctx.log.error(f"Failed to get settings from API (status {response.status_code}), falling back to local file")

        except Exception as e:
            ctx.log.error(f"Error fetching settings from API: {e}")
            ctx.log.info("Falling back to local file")

        # Fallback to local file if API fails
        try:
            with open(self.blocked_sites_file, 'r') as file:
                data = json.load(file)
                self.blocked_sites = data.get("sites", [])
                self.excluded_sites = data.get("excluded_sites", [])
                self.category_keywords = data.get("categories", {})
                ctx.log.info("Configuration loaded successfully from local file.")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            ctx.log.error(f"Error loading {self.blocked_sites_file}: {e}")

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