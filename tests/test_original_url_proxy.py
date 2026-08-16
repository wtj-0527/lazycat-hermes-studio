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
PACKAGE = "cloud.lazycat.app.lazycat-agent-browser-skill"
ORIGINAL = f"http://wtj.manager.{PACKAGE}.lzcapp:8080/mcp"
TARGET = f"http://app.{PACKAGE}.lzcx/mcp"


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
        self.catalog_path.write_text(json.dumps([{
            "package_id": PACKAGE,
            "resource_id": "lazycat-agent-browser",
            "endpoint": "/mcp",
            "original_host_suffix": f"manager.{PACKAGE}.lzcapp",
            "original_port": 8080,
            "proxy_path": f"/lazycat-mcp/{PACKAGE}/lazycat-agent-browser",
        }]))
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
            "ORIGINAL_MCP_HOST": f"wtj.manager.{PACKAGE}.lzcapp",
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
            self.fail("original URL proxy did not become ready")

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
        self.uds.shutdown()
        self.uds.server_close()
        self.upstream.shutdown()
        self.upstream.server_close()
        self.echo.shutdown()
        self.echo.server_close()
        self.tmp.cleanup()

    def test_maps_original_multi_instance_url_to_exact_independent_provider(self):
        status, headers, body = proxy_request(
            self.port, "POST", ORIGINAL, b'{"jsonrpc":"2.0"}'
        )
        self.assertEqual(status, 200)
        response_headers = {key.lower(): value for key, value in headers.items()}
        self.assertEqual(response_headers.get("mcp-session-id"), "transparent-test")
        request_line, seen_headers, seen_body = UnixHTTPHandler.seen[-1]
        self.assertEqual(request_line, "POST /internal/proxy HTTP/1.1")
        self.assertEqual(seen_headers["x-lazycat-target"], TARGET)
        self.assertNotIn("x-hc-user-id", seen_headers)
        self.assertNotIn("x-hc-source", seen_headers)
        self.assertEqual(seen_body, b'{"jsonrpc":"2.0"}')

    def test_maps_direct_origin_form_request_after_hosts_override(self):
        status, _, body = direct_request(
            self.port,
            "POST",
            "/mcp",
            f"wtj.manager.{PACKAGE}.lzcapp:8080",
            b'{"jsonrpc":"2.0"}',
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"ok":true}')
        _, seen_headers, seen_body = UnixHTTPHandler.seen[-1]
        self.assertEqual(seen_headers["x-lazycat-target"], TARGET)
        self.assertEqual(seen_body, b'{"jsonrpc":"2.0"}')

    def test_strips_caller_supplied_lazycat_identity_headers(self):
        status, _, _ = proxy_request(
            self.port,
            "POST",
            ORIGINAL,
            b"{}",
            {"X-HC-User-ID": "forged", "X-HC-Source": "client", "X-HC-Role": "owner"},
        )
        self.assertEqual(status, 200)
        _, headers, _ = UnixHTTPHandler.seen[-1]
        self.assertFalse(any(name.startswith("x-hc-") for name in headers))

    def test_rejects_unknown_lazycat_package(self):
        status, _, _ = proxy_request(
            self.port, "POST", "http://wtj.manager.unknown.example.lzcapp:8080/mcp"
        )
        self.assertEqual(status, 400)
        self.assertEqual(UnixHTTPHandler.seen, [])

    def test_rejects_wrong_endpoint_for_known_provider(self):
        status, _, _ = proxy_request(self.port, "POST", ORIGINAL + "/other")
        self.assertEqual(status, 400)
        self.assertEqual(UnixHTTPHandler.seen, [])

    def test_rejects_wrong_service_or_port_for_known_provider(self):
        for url in (
            f"http://wtj.worker.{PACKAGE}.lzcapp:8080/mcp",
            f"http://wtj.manager.{PACKAGE}.lzcapp:9999/mcp",
        ):
            with self.subTest(url=url):
                UnixHTTPHandler.seen = []
                status, _, _ = proxy_request(self.port, "POST", url)
                self.assertEqual(status, 400)
                self.assertEqual(UnixHTTPHandler.seen, [])

    def test_rejects_invalid_or_multi_label_user_prefix(self):
        for prefix in (
            "extra.wtj",
            "-wtj",
            "wtj-",
            "wtj_user",
            "a" * 64,
        ):
            with self.subTest(prefix=prefix):
                UnixHTTPHandler.seen = []
                url = f"http://{prefix}.manager.{PACKAGE}.lzcapp:8080/mcp"
                status, _, _ = proxy_request(self.port, "POST", url)
                self.assertEqual(status, 400)
                self.assertEqual(UnixHTTPHandler.seen, [])

    def test_preload_does_not_start_relay_for_unrelated_node_processes(self):
        port = free_port()
        env = os.environ.copy()
        env.update({
            "NODE_OPTIONS": f"--import={PROXY}",
            "ORIGINAL_URL_PROXY_PORT": str(port),
            "ORIGINAL_MCP_HOST": f"wtj.manager.{PACKAGE}.lzcapp",
            "SOCKET_PATH": self.socket_path,
            "CATALOG_FILE": str(self.catalog_path),
        })
        result = subprocess.run(
            ["node", "-e", "console.log('child-ok')"],
            env=env,
            text=True,
            capture_output=True,
            timeout=3,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "child-ok")
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", port), timeout=0.2)

    def test_rejects_unrelated_http(self):
        UnixHTTPHandler.seen = []
        url = f"http://127.0.0.1:{self.upstream.server_address[1]}/ordinary"
        status, _, _ = proxy_request(self.port, "POST", url, b"plain")
        self.assertEqual(status, 403)
        self.assertEqual(UnixHTTPHandler.seen, [])

    def test_rejects_unrelated_http_methods(self):
        for method in ("HEAD", "PUT", "PATCH", "OPTIONS"):
            with self.subTest(method=method):
                UnixHTTPHandler.seen = []
                url = f"http://127.0.0.1:{self.upstream.server_address[1]}/ordinary"
                status, _, _ = proxy_request(self.port, method, url, b"plain")
                self.assertEqual(status, 403)
                self.assertEqual(UnixHTTPHandler.seen, [])

    def test_rejects_connect_tunnelling(self):
        authority = f"127.0.0.1:{self.echo.server_address[1]}"
        status_line, echoed = connect_tunnel(self.port, authority)
        self.assertEqual(status_line, b"HTTP/1.1 405 Method Not Allowed")
        self.assertEqual(echoed, b"")


if __name__ == "__main__":
    unittest.main()
