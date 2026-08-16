#!/usr/bin/env python3
import http.client
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "content" / "lazycat-ticket-lease.mjs"


class UpstreamHandler(BaseHTTPRequestHandler):
    seen = []
    status = 200

    def log_message(self, format, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        type(self).seen.append((self.path, dict(self.headers), body))
        self.send_response(type(self).status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Mcp-Session-Id", "test-session")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(port, method, path, headers=None, body=b""):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse()
    data = response.read()
    result = response.status, dict(response.getheaders()), data
    conn.close()
    return result


class TicketLeaseTest(unittest.TestCase):
    def setUp(self):
        UpstreamHandler.seen = []
        UpstreamHandler.status = 200
        self.upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        threading.Thread(target=self.upstream.serve_forever, daemon=True).start()
        self.port = free_port()
        self.token = "lease-test-token"
        env = os.environ.copy()
        # Runtime NODE_OPTIONS/SOCKET_PATH from the installed wrapper must not
        # redirect this isolated TCP fixture into the production-style UDS.
        for name in ("NODE_OPTIONS", "SOCKET_PATH", "SOCKET_GID", "CATALOG_FILE"):
            env.pop(name, None)
        env.update({
            "PORT": str(self.port),
            "LEASE_TTL_MS": "250",
            "ALLOWED_HOST_SUFFIX": ".lzcx",
            "TEST_ALLOW_LOOPBACK": "1",
        })
        self.proc = subprocess.Popen(
            ["node", str(SERVER)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                if request(self.port, "GET", "/healthz")[0] == 200:
                    break
            except OSError:
                time.sleep(0.05)
        else:
            self.fail("ticket lease server did not become ready")

    def tearDown(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.upstream.shutdown()
        self.upstream.server_close()
        output = (self.proc.stdout.read() if self.proc.stdout else "") + (self.proc.stderr.read() if self.proc.stderr else "")
        if self.proc.stdout:
            self.proc.stdout.close()
        if self.proc.stderr:
            self.proc.stderr.close()
        self.assertNotIn("secret-ticket-A", output)

    @property
    def target(self):
        return f"http://127.0.0.1:{self.upstream.server_port}/mcp"

    def capture(self, ticket="secret-ticket-A", user="user-a"):
        return request(self.port, "POST", "/internal/capture", {
            "X-HC-USER-TICKET": ticket,
            "X-HC-User-ID": user,
            "X-HC-SOURCE": "client",
        })

    def proxy(self):
        return request(self.port, "POST", "/internal/proxy", {
            "X-LazyCat-Target": self.target,
            "Content-Type": "application/json",
        }, b'{"jsonrpc":"2.0"}')

    def test_fails_closed_until_authenticated_request_captures_ticket(self):
        self.assertEqual(self.proxy()[0], 428)
        status, headers, body = self.capture()
        self.assertEqual(status, 204)
        self.assertNotIn("secret-ticket-A", repr(headers) + repr(body))
        status, headers, body = self.proxy()
        self.assertEqual(status, 200)
        lower_headers = {key.lower(): value for key, value in headers.items()}
        self.assertEqual(lower_headers.get("mcp-session-id"), "test-session")
        seen_headers = {key.lower(): value for key, value in UpstreamHandler.seen[-1][1].items()}
        self.assertEqual(seen_headers["x-hc-user-ticket"], "secret-ticket-A")

    def test_ticket_expires_and_is_not_reused(self):
        self.capture()
        time.sleep(0.35)
        self.assertEqual(self.proxy()[0], 428)
        self.assertEqual(UpstreamHandler.seen, [])

    def test_auth_rejection_revokes_ticket(self):
        self.capture()
        UpstreamHandler.status = 401
        self.assertEqual(self.proxy()[0], 401)
        UpstreamHandler.status = 200
        self.assertEqual(self.proxy()[0], 428)

    def test_capture_requires_trusted_source_and_identity(self):
        status, _, _ = request(self.port, "POST", "/internal/capture", {
            "X-HC-USER-TICKET": "secret-ticket-A", "X-HC-SOURCE": "client"
        })
        self.assertEqual(status, 403)
        status, _, _ = request(self.port, "POST", "/internal/capture", {
            "X-HC-USER-TICKET": "secret-ticket-A",
            "X-HC-SOURCE": "app:evil",
        })
        self.assertEqual(status, 403)

    def test_capture_rejects_different_user_while_lease_is_live(self):
        self.assertEqual(self.capture(user="user-a")[0], 204)
        self.assertEqual(self.capture(ticket="secret-ticket-B", user="user-b")[0], 409)
        self.assertEqual(self.proxy()[0], 200)
        seen_headers = {key.lower(): value for key, value in UpstreamHandler.seen[-1][1].items()}
        self.assertEqual(seen_headers["x-hc-user-ticket"], "secret-ticket-A")

    def test_proxy_rejects_arbitrary_targets(self):
        self.capture()
        status, _, _ = request(self.port, "POST", "/internal/proxy", {
            "X-LazyCat-Target": "http://example.com/mcp",
        })
        self.assertEqual(status, 400)

    def test_proxy_strips_forged_lazycat_identity_headers(self):
        self.capture()
        status, _, _ = request(self.port, "POST", "/internal/proxy", {
            "X-LazyCat-Target": self.target,
            "X-HC-USER-TICKET": "forged-ticket",
            "X-HC-User-ID": "forged-user",
            "X-HC-SOURCE": "client",
            "X-HC-Role": "owner",
            "Content-Type": "application/json",
        }, b"{}")
        self.assertEqual(status, 200)
        seen_headers = {key.lower(): value for key, value in UpstreamHandler.seen[-1][1].items()}
        self.assertEqual(seen_headers["x-hc-user-ticket"], "secret-ticket-A")
        self.assertNotIn("x-hc-user-id", seen_headers)
        self.assertNotIn("x-hc-source", seen_headers)
        self.assertNotIn("x-hc-role", seen_headers)

    def test_proxy_rejects_non_mcp_methods(self):
        self.capture()
        status, _, _ = request(self.port, "HEAD", "/internal/proxy", {
            "X-LazyCat-Target": self.target,
        })
        self.assertEqual(status, 405)


if __name__ == "__main__":
    unittest.main()
