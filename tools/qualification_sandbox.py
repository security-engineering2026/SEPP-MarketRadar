from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, "application/json", b'{"status":"ok","sandbox":true}')
            return
        if self.path == "/dynamic":
            body = b"""<!doctype html>
<html><head><meta charset="utf-8"><title>MarketRadar Qualification Sandbox</title></head>
<body><div id="status">loading</div>
<script>
setTimeout(function () {
  document.getElementById("status").textContent =
    "MarketRadar dynamic sandbox rendered successfully";
}, 50);
</script></body></html>"""
            self._send(200, "text/html; charset=utf-8", body)
            return
        self._send(404, "application/json", b'{"error":"not_found"}')

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length:
            self.rfile.read(min(length, 64 * 1024))
        payload = {
            "sandbox": True,
            "accepted": True,
            "path": self.path,
        }
        if self.path in {"/engine", "/application", "/payment", "/push"}:
            self._send(200, "application/json", json.dumps(payload).encode())
            return
        self._send(404, "application/json", b'{"error":"not_found"}')

    def log_message(self, format: str, *args) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
