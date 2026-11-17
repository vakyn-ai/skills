"""The share example: POSTs the request with the key and prints the short link."""

import importlib.util
import json
import os
import pathlib
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("share_link", ROOT / "skills/share/examples/share_link.py")
share_link = importlib.util.module_from_spec(spec)
spec.loader.exec_module(share_link)


class Server(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Server.seen.append((self.path, self.headers["Authorization"], body))
        out = json.dumps({"id": "k3x9m2pa", "url": "https://vakyn.com/p/k3x9m2pa"}).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


class Share(unittest.TestCase):
    def test_posts_the_request_and_returns_the_link(self):
        server = HTTPServer(("localhost", 0), Server)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            share_link.BASE_URL = f"http://localhost:{server.server_port}"
            os.environ["VAKYN_API_KEY"] = "vk_test"
            request = json.loads((ROOT / "skills/share/examples/vakyn-request.sample.json").read_text())
            self.assertEqual(share_link.share(request), "https://vakyn.com/p/k3x9m2pa")
            self.assertEqual(Server.seen, [("/v1/playground-links", "Bearer vk_test", request)])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
