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
        self.gateway_port = free_port()
        self.token = "lease-test-token"
        self.expected_log_fragments = []
        self.tempdir = tempfile.TemporaryDirectory()
        self.gateway_seen = Path(self.tempdir.name) / "gateway-seen.json"
        self.gateway_mode = Path(self.tempdir.name) / "gateway-mode.txt"
        self.gateway_mode.write_text("ok", encoding="utf-8")
        gateway_script = Path(self.tempdir.name) / "gateway.mjs"
        gateway_script.write_text(r'''import http2 from 'node:http2'
import { readFileSync, writeFileSync } from 'node:fs'

const port = Number(process.argv[2])
const seenFile = process.argv[3]
const modeFile = process.argv[4]
const field = (number, bytes) => Buffer.concat([Buffer.from([(number << 3) | 2, bytes.length]), bytes])
const app = id => field(1, Buffer.from(id))
const response = field(1, app('cloud.lazycat.app.browser'))
const duplicate = field(1, app('cloud.lazycat.app.browser'))
const second = field(1, app('cloud.lazycat.app.notes'))
const message = Buffer.concat([response, duplicate, second])
const frame = Buffer.concat([Buffer.from([0, 0, 0, 0, message.length]), message])
const server = http2.createServer()
server.on('stream', (stream, headers) => {
  const chunks = []
  stream.on('data', chunk => chunks.push(chunk))
  stream.on('end', () => {
    writeFileSync(seenFile, JSON.stringify({ headers, body: Buffer.concat(chunks).toString('hex') }))
    const mode = readFileSync(modeFile, 'utf8').trim()
    if (mode === 'grpc-error') {
      stream.respond({ ':status': 200, 'content-type': 'application/grpc', 'grpc-status': '7' })
      stream.end()
    } else if (mode === 'missing-status') {
      stream.respond({ ':status': 200, 'content-type': 'application/grpc' })
      stream.end()
    } else if (mode === 'malformed-frame') {
      stream.respond({ ':status': 200, 'content-type': 'application/grpc', 'grpc-status': '0' })
      stream.end(Buffer.from([0, 0, 0, 0, 8, 10]))
    } else {
      stream.respond({ ':status': 200, 'content-type': 'application/grpc', 'trailer': 'grpc-status' }, { waitForTrailers: true })
      stream.on('wantTrailers', () => stream.sendTrailers({ 'grpc-status': '0' }))
      stream.end(frame)
    }
  })
})
server.listen(port, '127.0.0.1')
''', encoding="utf-8")
        self.gateway_proc = subprocess.Popen(
            ["node", str(gateway_script), str(self.gateway_port), str(self.gateway_seen), str(self.gateway_mode)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        env = os.environ.copy()
        # Runtime NODE_OPTIONS/SOCKET_PATH from the installed wrapper must not
        # redirect this isolated TCP fixture into the production-style UDS.
        for name in ("NODE_OPTIONS", "SOCKET_PATH", "SOCKET_GID", "CATALOG_FILE", "LAZYCAT_USER_ID", "LZCAPP_API_GATEWAY_ADDRESS"):
            env.pop(name, None)
        env.update({
            "PORT": str(self.port),
            "LEASE_TTL_MS": "250",
            "ALLOWED_HOST_SUFFIX": ".lzcx",
            "TEST_ALLOW_LOOPBACK": "1",
            "LAZYCAT_USER_ID": "user-a",
            "LZCAPP_API_GATEWAY_ADDRESS": f"127.0.0.1:{self.gateway_port}",
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
        self.gateway_proc.terminate()
        try:
            self.gateway_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.gateway_proc.kill()
        if self.gateway_proc.stdout:
            self.gateway_proc.stdout.close()
        if self.gateway_proc.stderr:
            self.gateway_proc.stderr.close()
        self.tempdir.cleanup()
        output = (self.proc.stdout.read() if self.proc.stdout else "") + (self.proc.stderr.read() if self.proc.stderr else "")
        if self.proc.stdout:
            self.proc.stdout.close()
        if self.proc.stderr:
            self.proc.stderr.close()
        self.assertNotIn("secret-ticket-A", output)
        self.assertNotIn("secret-ticket-B", output)
        self.assertNotIn("secret-user-B", output)
        for fragment in self.expected_log_fragments:
            self.assertIn(fragment, output)

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

    def visible_apps(self):
        return request(self.port, "GET", "/internal/visible-apps")

    def test_visible_apps_requires_current_user_ticket(self):
        self.assertEqual(self.visible_apps()[0], 428)

    def test_visible_apps_returns_only_sorted_unique_package_ids(self):
        self.capture()
        status, headers, body = self.visible_apps()
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {
            "package_ids": ["cloud.lazycat.app.browser", "cloud.lazycat.app.notes"]
        })
        self.assertEqual(headers.get("Content-Type"), "application/json; charset=utf-8")
        deadline = time.time() + 3
        while not self.gateway_seen.exists() and time.time() < deadline:
            time.sleep(0.02)
        seen = json.loads(self.gateway_seen.read_text(encoding="utf-8"))
        self.assertEqual(seen["headers"][":path"], "/cloud.lazycat.apis.sys.PackageManager/QueryApplication")
        self.assertEqual(seen["headers"]["x-hc-user-ticket"], "secret-ticket-A")
        self.assertEqual(seen["headers"]["x-hc-user-id"], "user-a")
        self.assertEqual(seen["body"], "0000000000")
        self.assertNotIn("secret-ticket-A", body.decode())

    def test_visible_apps_fails_closed_on_nonzero_grpc_status(self):
        self.capture()
        self.gateway_mode.write_text("grpc-error", encoding="utf-8")
        status, _, body = self.visible_apps()
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(body), {"error": "CURRENT_USER_APP_VISIBILITY_UNAVAILABLE"})

    def test_visible_apps_fails_closed_when_grpc_status_is_missing(self):
        self.capture()
        self.gateway_mode.write_text("missing-status", encoding="utf-8")
        status, _, body = self.visible_apps()
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(body), {"error": "CURRENT_USER_APP_VISIBILITY_UNAVAILABLE"})

    def test_visible_apps_fails_closed_on_malformed_grpc_frame(self):
        self.capture()
        self.gateway_mode.write_text("malformed-frame", encoding="utf-8")
        status, _, body = self.visible_apps()
        self.assertEqual(status, 502)
        self.assertEqual(json.loads(body), {"error": "CURRENT_USER_APP_VISIBILITY_UNAVAILABLE"})

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

    def test_provider_401_does_not_revoke_ticket_for_other_providers(self):
        self.capture()
        UpstreamHandler.status = 401
        self.assertEqual(self.proxy()[0], 401)
        UpstreamHandler.status = 200
        self.assertEqual(self.proxy()[0], 200)

    def test_provider_403_does_not_revoke_ticket_for_other_providers(self):
        self.capture()
        UpstreamHandler.status = 403
        self.assertEqual(self.proxy()[0], 403)
        self.expected_log_fragments.append(
            "upstream.auth_rejected package_id=test-loopback endpoint=/mcp status=403"
        )
        UpstreamHandler.status = 200
        self.assertEqual(self.proxy()[0], 200)

    def test_capture_requires_trusted_source_and_identity(self):
        status, _, _ = request(self.port, "POST", "/internal/capture", {
            "X-HC-USER-TICKET": "secret-ticket-A", "X-HC-SOURCE": "client"
        })
        self.assertEqual(status, 403)
        self.expected_log_fragments.append(
            "capture.rejected source_client=true ticket_present=true user_present=false configured_user_present=true user_match=false"
        )
        status, _, _ = request(self.port, "POST", "/internal/capture", {
            "X-HC-USER-TICKET": "secret-ticket-A",
            "X-HC-User-ID": "secret-user-B",
            "X-HC-SOURCE": "app:evil",
        })
        self.assertEqual(status, 403)
        self.expected_log_fragments.append(
            "capture.rejected source_client=false ticket_present=true user_present=true configured_user_present=true user_match=false"
        )

    def test_capture_logs_accept_and_renew_without_identity_values(self):
        self.assertEqual(self.capture()[0], 204)
        self.expected_log_fragments.append(
            "capture.accepted source_client=true ticket_present=true user_present=true configured_user_present=true user_match=true"
        )
        self.assertEqual(self.capture(ticket="secret-ticket-B")[0], 204)
        self.expected_log_fragments.append(
            "capture.renewed source_client=true ticket_present=true user_present=true configured_user_present=true user_match=true"
        )

    def test_capture_rejects_user_not_bound_to_deployed_instance(self):
        self.assertEqual(self.capture(ticket="secret-ticket-B", user="secret-user-B")[0], 403)
        self.expected_log_fragments.append(
            "capture.rejected source_client=true ticket_present=true user_present=true configured_user_present=true user_match=false"
        )
        self.assertEqual(self.proxy()[0], 428)

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
