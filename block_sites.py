import mitmproxy.http
from mitmproxy import ctx
import json
import re

class BlockSites:
    def __init__(self):
        self.blocked_sites_file = 'blocked_sites.json'
        self.blocked_sites = []
        self.categories = []
        self.load_blocked_sites()
        self.pattern = self.create_pattern_from_categories()  # Create the pattern from categories

    def load_blocked_sites(self):
        try:
            with open(self.blocked_sites_file, 'r') as file:
                data = json.load(file)
                self.blocked_sites = data.get("sites", [])
                self.categories = data.get("categories", [])
        except FileNotFoundError:
            ctx.log.error(f"{self.blocked_sites_file} not found. Ensure the file exists and is correctly formatted.")
        except json.JSONDecodeError:
            ctx.log.error(f"Error decoding {self.blocked_sites_file}. Ensure it contains valid JSON.")

    def create_pattern_from_categories(self):
        # Create a regex pattern from the categories list
        if not self.categories:
            return re.compile("")  # Return an empty pattern if no categories are present
        
        # Join categories into a pattern, using "|" (OR) for regex matching
        pattern_string = "|".join(map(re.escape, self.categories))
        return re.compile(pattern_string, re.IGNORECASE)

    def request(self, flow: mitmproxy.http.HTTPFlow) -> None:
        # Block requests to specific domains immediately
        if any(blocked_site in flow.request.pretty_url for blocked_site in self.blocked_sites):
            flow.response = mitmproxy.http.Response.make(
                403,  # Forbidden status code
                b"Blocked Site",  # Response body
                {"Content-Type": "text/html"}
            )
            ctx.log.info(f"Blocked request to: {flow.request.pretty_url}")
            return  # Prevent further processing of this flow

    def response(self, flow: mitmproxy.http.HTTPFlow) -> None:
        try:
            if flow.response and flow.response.content:
                content = flow.response.content.decode('utf-8', errors='ignore')  # Decode content to string
                if self.pattern.search(content):  # Search for the pattern from categories
                    flow.response = mitmproxy.http.Response.make(
                        403,  # Forbidden status code
                        b"Blocked due to content",
                        {"Content-Type": "text/html"}
                    )
                    ctx.log.info(f"Blocked content from: {flow.request.pretty_url}")
        except Exception as e:
            ctx.log.error(f"Error processing response: {e}")


addons = [BlockSites()]
