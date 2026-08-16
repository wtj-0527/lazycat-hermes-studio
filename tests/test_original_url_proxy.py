#!/usr/bin/env python3
import http.client
import json
import os
import socket
import socketserver
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROXY = ROOT / "content" / "lazycat-original-url-proxy.mjs"
BROWSER_PACKAGE = "cloud.lazycat.app.lazycat-agent-browser-skill"
TODO_PACKAGE = "cloud.lazycat.app.todolist"
BROWSER_HOST = f"app.{BROWSER_PACKAGE}.lzcx"
TODO_HOST = f"app.{TODO_PACKAGE}.lzcx"
BROWSER_URL = f"http://{BROWSER_HOST}/mcp"
TODO_URL = f"http://{TODO_HOST}/api/mcp"


class UnixHTTPHandler(socketserver.StreamRequestHandler):
    seen = []

    def handle(self):
        request_line = self.rfile.readline().decode("ascii").rstrip("\r\n")
        headers = {}
        while True:
            line = self.rfile.readline()
            if line in (b"\r\n", b"\n", b""):
                break
            key, value = line.decode("latin1").split(":", 1)
            headers[key.lower()] = value.strip()
        length = int(headers.get("content-length", "0"))
        body = self.rfile.read(length)
        type(self).seen.append((request_line, headers, body))
        payload = b'{"ok":true}'
        self.wfile.write(
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
            b"Mcp-Session-Id: transparent-test\r\nContent-Length: "
            + str(len(payload)).encode()
            + b"\r\nConnection: close\r\n\r\n"
            + payload
        )


class UnixServer(socketserver.UnixStreamServer):
    allow_reuse_address = True


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def proxy_request(port, method, absolute_url, body=b"", headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.putrequest(method, absolute_url, skip_host=True)
    conn.putheader("Host", absolute_url.split("//", 1)[1].split("/", 1)[0])
    conn.putheader("Content-Type", "application/json")
    conn.putheader("Content-Length", str(len(body)))
    for key, value in (headers or {}).items():
        conn.putheader(key, value)
    conn.endheaders(body)
    response = conn.getresponse()
    payload = response.read()
    result = response.status, dict(response.getheaders()), payload
    conn.close()
    return result


def direct_request(port, method, path, host, body=b""):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request(method, path, body=body, headers={
        "Host": host,
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
    })
    response = conn.getresponse()
    payload = response.read()
    result = response.status, dict(response.getheaders()), payload
    conn.close()
    return result


def connect_tunnel(port, authority, payload=b"ping"):
    sock = socket.create_connection(("127.0.0.1", port), timeout=3)
    sock.sendall(f"CONNECT {authority} HTTP/1.1\r\nHost: {authority}\r\n\r\n".encode())
    response = b""
    while b"\r\n\r\n" not in response:
        response += sock.recv(4096)
    sock.sendall(payload)
    echoed = sock.recv(len(payload))
    sock.close()
    return response.split(b"\r\n", 1)[0], echoed


class EchoHandler(socketserver.BaseRequestHandler):
    def handle(self):
        while data := self.request.recv(4096):
            self.request.sendall(data)


class OriginalUrlProxyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.socket_path = str(Path(self.tmp.name) / "lease.sock")
        self.catalog_path = Path(self.tmp.name) / "providers.json"
        self.catalog_path.write_text(json.dumps([
            {
                "package_id": BROWSER_PACKAGE,
                "resource_id": "lazycat-agent-browser",
                "endpoint": "/mcp",
                "canonical_host": BROWSER_HOST,
                "proxy_path": f"/lazycat-mcp/{BROWSER_PACKAGE}/lazycat-agent-browser",
            },
            {
                "package_id": TODO_PACKAGE,
                "resource_id": "default",
                "endpoint": "/api/mcp",
                "canonical_host": TODO_HOST,
                "proxy_path": f"/lazycat-mcp/{TODO_PACKAGE}/default",
            },
        ]))
        UnixHTTPHandler.seen = []
        self.uds = UnixServer(self.socket_path, UnixHTTPHandler)
        threading.Thread(target=self.uds.serve_forever, daemon=True).start()
        self.upstream = socketserver.ThreadingTCPServer(("127.0.0.1", 0), UnixHTTPHandler)
        threading.Thread(target=self.upstream.serve_forever, daemon=True).start()
        self.echo = socketserver.ThreadingTCPServer(("127.0.0.1", 0), EchoHandler)
        threading.Thread(target=self.echo.serve_forever, daemon=True).start()
        self.port = free_port()
        env = os.environ.copy()
        env.update({
            "ORIGINAL_URL_PROXY_PORT": str(self.port),
            "SOCKET_PATH": self.socket_path,
            "CATALOG_FILE": str(self.catalog_path),
        })
        self.proc = subprocess.Popen(
            ["node", str(PROXY)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=.2):
                    break
            except OSError:
                time.sleep(.05)
        else:
            self.fail("canonical URL proxy did not become ready")

    def tearDown(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        output = (self.proc.stdout.read() if self.proc.stdout else "") + (self.proc.stderr.read() if self.proc.stderr else "")
        if self.proc.stdout:
            self.proc.stdout.close()
        if self.proc.stderr:
            self.proc.stderr.close()
        self.assertNotIn("x-hc-user-ticket", output.lower())
        self.uds.shutdown(); self.uds.server_close()
        self.upstream.shutdown(); self.upstream.server_close()
        self.echo.shutdown(); self.echo.server_close()
        self.tmp.cleanup()

    def test_maps_each_exact_canonical_provider_url(self):
        for url, target in ((BROWSER_URL, BROWSER_URL), (TODO_URL, TODO_URL)):
            with self.subTest(url=url):
                UnixHTTPHandler.seen = []
                status, headers, body = proxy_request(self.port, "POST", url, b'{"jsonrpc":"2.0"}')
                self.assertEqual(status, 200)
                self.assertEqual({k.lower(): v for k, v in headers.items()}.get("mcp-session-id"), "transparent-test")
                request_line, seen_headers, seen_body = UnixHTTPHandler.seen[-1]
                self.assertEqual(request_line, "POST /internal/proxy HTTP/1.1")
                self.assertEqual(seen_headers["x-lazycat-target"], target)
                self.assertFalse(any(name.startswith("x-hc-") for name in seen_headers))
                self.assertEqual(seen_body, b'{"jsonrpc":"2.0"}')

    def test_maps_origin_form_request_after_dynamic_hosts_override(self):
        status, _, body = direct_request(self.port, "POST", "/mcp", BROWSER_HOST, b"{}")
        self.assertEqual((status, body), (200, b'{"ok":true}'))
        self.assertEqual(UnixHTTPHandler.seen[-1][1]["x-lazycat-target"], BROWSER_URL)

    def test_strips_caller_supplied_lazycat_identity_headers(self):
        status, _, _ = proxy_request(self.port, "POST", BROWSER_URL, b"{}", {
            "X-HC-User-ID": "forged", "X-HC-Source": "client", "X-HC-Role": "owner",
        })
        self.assertEqual(status, 200)
        self.assertFalse(any(name.startswith("x-hc-") for name in UnixHTTPHandler.seen[-1][1]))

    def test_rejects_unknown_host_wrong_endpoint_port_and_https(self):
        urls = (
            "http://app.cloud.lazycat.app.unknown.lzcx/mcp",
            f"http://{BROWSER_HOST}/other",
            f"http://{BROWSER_HOST}:8080/mcp",
            f"https://{BROWSER_HOST}/mcp",
        )
        for url in urls:
            with self.subTest(url=url):
                UnixHTTPHandler.seen = []
                status, _, _ = proxy_request(self.port, "POST", url)
                self.assertIn(status, (400, 403))
                self.assertEqual(UnixHTTPHandler.seen, [])

    def test_rejects_legacy_browser_specific_url(self):
        status, _, _ = proxy_request(
            self.port, "POST", f"http://wtj.manager.{BROWSER_PACKAGE}.lzcapp:8080/mcp"
        )
        self.assertIn(status, (400, 403))
        self.assertEqual(UnixHTTPHandler.seen, [])

    def test_preload_does_not_start_relay_for_unrelated_node_processes(self):
        port = free_port()
        env = os.environ.copy()
        env.update({
            "NODE_OPTIONS": f"--import={PROXY}",
            "ORIGINAL_URL_PROXY_PORT": str(port),
            "SOCKET_PATH": self.socket_path,
            "CATALOG_FILE": str(self.catalog_path),
        })
        result = subprocess.run(
            ["node", "-e", "console.log('child-ok')"], env=env,
            text=True, capture_output=True, timeout=3,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "child-ok")
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", port), timeout=0.2)

    def test_rejects_unrelated_http(self):
        url = f"http://127.0.0.1:{self.upstream.server_address[1]}/ordinary"
        status, _, _ = proxy_request(self.port, "POST", url, b"plain")
        self.assertEqual(status, 403)
        self.assertEqual(UnixHTTPHandler.seen, [])

    def test_rejects_unrelated_http_methods(self):
        for method in ("HEAD", "PUT", "PATCH", "OPTIONS"):
            with self.subTest(method=method):
                UnixHTTPHandler.seen = []
                status, _, _ = proxy_request(self.port, method, BROWSER_URL, b"plain")
                self.assertEqual(status, 405)
                self.assertEqual(UnixHTTPHandler.seen, [])

    def test_rejects_connect_tunnelling(self):
        authority = f"127.0.0.1:{self.echo.server_address[1]}"
        status_line, echoed = connect_tunnel(self.port, authority)
        self.assertEqual(status_line, b"HTTP/1.1 405 Method Not Allowed")
        self.assertEqual(echoed, b"")


if __name__ == "__main__":
    unittest.main()
