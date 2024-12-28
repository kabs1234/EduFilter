import mitmproxy.http
from mitmproxy import ctx
import json

class BlockSites:
    def __init__(self):
        self.blocked_sites_file = 'blocked_sites.json'
        self.blocked_sites = self.load_blocked_sites()

    def load_blocked_sites(self):
        try:
            with open(self.blocked_sites_file, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

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
        # Optional: Additional blocking logic based on response content
        try:
            if flow.response and flow.response.content:
                if b"violence" in flow.response.content:
                    flow.response = mitmproxy.http.Response.make(
                        403,
                        b"Blocked due to content",
                        {"Content-Type": "text/html"}
                    )
                    ctx.log.info(f"Blocked content from: {flow.request.pretty_url}")
        except Exception as e:
            ctx.log.error(f"Error processing response: {e}")


addons = [BlockSites()]
