#!/usr/bin/env python3
import http.server, json, os, socketserver, subprocess, sys, tempfile, threading, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class Up(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers(); self.wfile.write(b'<html><head></head><body>ok</body></html>')
class Provider(http.server.BaseHTTPRequestHandler):
    seen=None
    def log_message(self,*a): pass
    def do_POST(self):
        Provider.seen=self.headers.get('X-HC-USER-TICKET')
        n=int(self.headers.get('Content-Length','0')); self.rfile.read(n)
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Mcp-Session-Id','acceptance'); self.end_headers(); self.wfile.write(b'{"ok":true}')

def run(*a,**kw): return subprocess.run(a,text=True,capture_output=True,check=True,**kw)
with tempfile.TemporaryDirectory() as td:
    td=Path(td); runtime=td/'runtime'; resources=td/'resources/mcp-providers/app.test/default'; runtime.mkdir(parents=True); resources.mkdir(parents=True)
    (resources/'mcp.yml').write_text('endpoint: /mcp\n')
    (runtime/'internal-token').write_text('runtime-acceptance-token')
    env=os.environ|{'MCP_RESOURCE_ROOT':str(td/'resources/mcp-providers'),'MCP_NGINX_OUTPUT':str(td/'generated.conf'),'MCP_CATALOG_OUTPUT':str(runtime/'providers.json'),'MCP_INTERNAL_TOKEN':'runtime-acceptance-token'}
    run('sh',str(ROOT/'content/generate-lazycat-mcp-proxy.sh'),env=env)
    lease_port=0
    import socket
    with socket.socket() as sock: sock.bind(('127.0.0.1',0)); lease_port=sock.getsockname()[1]
    lease_env=os.environ|{'PORT':str(lease_port),'LEASE_TTL_MS':'10000','INTERNAL_TOKEN_FILE':str(runtime/'internal-token'),'CATALOG_FILE':str(runtime/'providers.json'),'TEST_ALLOW_LOOPBACK':'1'}
    lease=subprocess.Popen(['node',str(ROOT/'content/lazycat-ticket-lease.mjs')],env=lease_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        for _ in range(50):
            try:
                import urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{lease_port}/healthz',timeout=.2); break
            except Exception: time.sleep(.05)
        def req(path,headers=None,data=b''):
            import urllib.request, urllib.error
            q=urllib.request.Request(f'http://127.0.0.1:{lease_port}'+path,data=data,headers=headers or {},method='POST')
            try:
                with urllib.request.urlopen(q,timeout=2) as r:return r.status,dict(r.headers),r.read()
            except urllib.error.HTTPError as e:return e.code,dict(e.headers),e.read()
        provider=socketserver.TCPServer(('127.0.0.1',0),Provider); threading.Thread(target=provider.serve_forever,daemon=True).start()
        target=f'http://127.0.0.1:{provider.server_address[1]}/mcp'
        h={'X-Internal-Token':'runtime-acceptance-token','X-LazyCat-Target':target,'Content-Type':'application/json'}
        assert req('/internal/proxy',h,b'{}')[0]==428
        cap={'X-Internal-Token':'runtime-acceptance-token','X-HC-USER-TICKET':'acceptance-secret','X-HC-User-ID':'u','X-HC-SOURCE':'client'}
        assert req('/internal/capture',cap)[0]==204
        try:
            status,headers,_=req('/internal/proxy',h,b'{}'); assert status==200,(status,_); assert Provider.seen=='acceptance-secret'; assert {k.lower():v for k,v in headers.items()}.get('mcp-session-id')=='acceptance'
        finally: provider.shutdown(); provider.server_close()
        print('runtime lease acceptance: PASS')
    finally:
        lease.terminate(); lease.wait(timeout=3)
        out=(lease.stdout.read() if lease.stdout else '')+(lease.stderr.read() if lease.stderr else '')
        assert 'acceptance-secret' not in out
