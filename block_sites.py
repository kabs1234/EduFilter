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
        self.load_blocked_sites()

    def load_blocked_sites(self):
        try:
            with open(self.blocked_sites_file, 'r') as file:
                data = json.load(file)
                self.blocked_sites = data.get("sites", [])
                self.excluded_sites = data.get("excluded_sites", [])
                self.category_keywords = data.get("categories", {})
                ctx.log.info(f"Loaded blocked sites: {self.blocked_sites}")
                ctx.log.info(f"Loaded excluded sites: {self.excluded_sites}")
                ctx.log.info(f"Loaded category keywords: {self.category_keywords}")
        except FileNotFoundError:
            ctx.log.error(f"{self.blocked_sites_file} not found. Ensure the file exists and is correctly formatted.")
        except json.JSONDecodeError:
            ctx.log.error(f"Error decoding {self.blocked_sites_file}. Ensure it contains valid JSON.")

    def create_pattern_for_keywords(self, keywords):
        if not keywords:
            return None
        pattern_string = "|".join(rf"\b{re.escape(keyword)}\b" for keyword in keywords)
        return re.compile(pattern_string, re.IGNORECASE)

    def is_excluded(self, host):
        return any(excluded in host for excluded in self.excluded_sites)

    def request(self, flow: mitmproxy.http.HTTPFlow) -> None:
        # First check if the site is excluded
        if self.is_excluded(flow.request.host):
            ctx.log.info(f"Allowing excluded site: {flow.request.pretty_url}")
            return

        # Then check if it should be blocked
        for blocked_site in self.blocked_sites:
            if flow.request.host == blocked_site or flow.request.pretty_url.startswith(f"https://{blocked_site}"):
                flow.response = mitmproxy.http.Response.make(
                    403,
                    b"Blocked Site",
                    {"Content-Type": "text/html"}
                )
                ctx.log.info(f"Blocked request to: {flow.request.pretty_url}")
                return

    def response(self, flow: mitmproxy.http.HTTPFlow) -> None:
        # Skip content checking for excluded sites
        if self.is_excluded(flow.request.host):
            return

        # Dynamically block based on content for non-excluded sites
        try:
            if flow.response and flow.response.content:
                content = flow.response.content.decode('utf-8', errors='ignore')

                for category, keywords in self.category_keywords.items():
                    pattern = self.create_pattern_for_keywords(keywords)

                    if pattern and pattern.search(content):
                        flow.response = mitmproxy.http.Response.make(
                            403,
                            f"Blocked due to category: {category}".encode('utf-8'),
                            {"Content-Type": "text/html"}
                        )
                        ctx.log.info(f"Blocked content from {flow.request.pretty_url} due to category: {category}")
                        return
        except Exception as e:
            ctx.log.error(f"Error processing response: {e}")


addons = [BlockSites()]