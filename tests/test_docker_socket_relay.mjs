import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, readFile, rm, stat, symlink, unlink, writeFile } from 'node:fs/promises';
import http from 'node:http';
import net from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { checkHealth, startRelay } from '../content/docker-socket-relay.mjs';

const script = fileURLToPath(new URL('../content/docker-socket-relay.mjs', import.meta.url));

async function fixture(t) {
  const dir = await mkdtemp(join(tmpdir(), 'hds-'));
  const upstreamPath = join(dir, 'upstream.sock');
  const listenPath = join(dir, 'relay.sock');
  const closers = [];
  t.after(async () => {
    for (const close of closers.reverse()) await close();
    await rm(dir, { recursive: true, force: true });
  });
  return {
    dir, upstreamPath, listenPath,
    async server(handler, path = upstreamPath, httpServer = false) {
      const server = httpServer
        ? http.createServer(handler) : net.createServer({ allowHalfOpen: true }, handler);
      const sockets = new Set();
      server.on('connection', socket => {
        sockets.add(socket);
        socket.on('error', () => {});
        socket.once('close', () => sockets.delete(socket));
      });
      await new Promise((done, reject) => {
        server.once('error', reject);
        server.listen(path, done);
      });
      closers.push(() => new Promise(done => {
        server.close(done);
        for (const socket of sockets) socket.destroy();
      }));
      return server;
    },
    async relay(options = {}) {
      const relay = await startRelay({ listenPath, upstreamPath, log: () => {}, ...options });
      closers.push(relay.close);
      return relay;
    },
    async child() {
      const child = spawn(process.execPath, [script], {
        env: { ...process.env, NODE_OPTIONS: '', DOCKER_RELAY_LISTEN: listenPath, DOCKER_RELAY_UPSTREAM: upstreamPath },
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      let output = '';
      child.stdout.on('data', chunk => { output += chunk; });
      child.stderr.on('data', chunk => { output += chunk; });
      const exited = once(child, 'exit');
      closers.push(async () => {
        if (child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
        await exited;
      });
      const deadline = Date.now() + 3000;
      while (!output.includes('listening on local Unix socket')) {
        if (child.exitCode !== null || child.signalCode !== null || Date.now() > deadline) {
          throw new Error(`relay child failed to start: ${output}`);
        }
        await delay(10);
      }
      return { child, exited };
    },
  };
}

function exchange(path, payload) {
  return new Promise((done, reject) => {
    const socket = net.createConnection({ path, allowHalfOpen: true });
    const chunks = [];
    const timer = setTimeout(() => socket.destroy(new Error('test exchange timed out')), 5000);
    socket.on('connect', () => socket.end(payload));
    socket.on('data', chunk => chunks.push(chunk));
    socket.once('end', () => done(Buffer.concat(chunks)));
    socket.once('error', reject);
    socket.once('close', () => clearTimeout(timer));
  });
}

test('binary streams preserve half-close and drain large responses under backpressure', async t => {
  const f = await fixture(t);
  const request = Buffer.alloc(2 * 1024 * 1024, 0xa7);
  const response = Buffer.alloc(3 * 1024 * 1024, 0xfe);
  await f.server(socket => {
    const chunks = [];
    socket.on('data', chunk => chunks.push(chunk));
    socket.on('end', () => {
      assert.deepEqual(Buffer.concat(chunks), request);
      socket.end(response);
    });
  });
  await f.relay();
  assert.deepEqual(await exchange(f.listenPath, request), response);
});

test('new connections use a replacement upstream socket while the old server stays alive', async t => {
  const f = await fixture(t);
  let oldCalls = 0;
  await f.server(socket => {
    socket.resume();
    socket.on('end', () => { oldCalls++; socket.end('old'); });
  });
  await f.relay();
  const oldInode = (await stat(f.upstreamPath)).ino;
  assert.equal((await exchange(f.listenPath, 'first')).toString(), 'old');
  await unlink(f.upstreamPath);
  await f.server(socket => {
    socket.resume();
    socket.on('end', () => socket.end('new'));
  });
  assert.notEqual((await stat(f.upstreamPath)).ino, oldInode);
  assert.equal((await exchange(f.listenPath, 'second')).toString(), 'new');
  assert.equal(oldCalls, 1);
});

test('missing upstream and failed health checks do not stop the relay; it recovers in place', async t => {
  const f = await fixture(t);
  const relay = await f.relay();
  await assert.rejects(checkHealth(f.listenPath, 200));
  assert.equal(relay.server.listening, true);
  await f.server((_request, response) => response.end('OK'), f.upstreamPath, true);
  await checkHealth(f.listenPath);
});

test('health check has an absolute deadline even when the upstream accepts but never responds', async t => {
  const f = await fixture(t);
  await f.server(socket => socket.resume());
  const relay = await f.relay();
  await assert.rejects(checkHealth(f.listenPath, 40), /timed out/);
  assert.equal(relay.server.listening, true);
});

test('HTTP keep-alive and chunked responses pass through without request rewriting', async t => {
  const f = await fixture(t);
  const seen = [];
  await f.server((request, response) => {
    seen.push([request.method, request.url, request.headers.authorization]);
    response.write('first');
    response.end('second');
  }, f.upstreamPath, true);
  await f.relay();
  const agent = new http.Agent({ keepAlive: true });
  t.after(() => agent.destroy());
  const call = () => new Promise((done, reject) => {
    http.get({ socketPath: f.listenPath, path: '/v1.45/containers/json?all=1', agent,
      headers: { Authorization: 'test-only-value' } }, response => {
      let body = '';
      response.on('data', chunk => { body += chunk; });
      response.on('end', () => done(body));
    }).on('error', reject);
  });
  assert.equal(await call(), 'firstsecond');
  assert.equal(await call(), 'firstsecond');
  assert.deepEqual(seen, Array(2).fill(['GET', '/v1.45/containers/json?all=1', 'test-only-value']));
});

test('a broken mutation is not retried or replayed after upstream replacement', async t => {
  const f = await fixture(t);
  let mutations = 0;
  await f.server(socket => {
    socket.once('data', () => { mutations++; socket.destroy(); });
  });
  await f.relay();
  await assert.rejects(new Promise((done, reject) => {
    const request = http.request({ socketPath: f.listenPath, path: '/containers/create', method: 'POST' }, done);
    request.once('error', reject);
    request.end('{"Image":"test"}');
  }));
  await unlink(f.upstreamPath);
  await f.server((request, response) => {
    if (request.method === 'POST') mutations++;
    response.end('OK');
  }, f.upstreamPath, true);
  await checkHealth(f.listenPath);
  assert.equal(mutations, 1);
});

test('SIGKILL leaves a stale listener that a restarted relay recovers through the same client symlink', async t => {
  const f = await fixture(t);
  await f.server((_request, response) => response.end('OK'), f.upstreamPath, true);
  const clientPath = join(f.dir, 'docker.sock');
  await symlink(f.listenPath, clientPath);
  const first = await f.child();
  await checkHealth(clientPath);
  first.child.kill('SIGKILL');
  await first.exited;
  await f.child();
  await checkHealth(clientPath);
});

test('an existing active relay is not replaced by a second process', async t => {
  const f = await fixture(t);
  await f.server((_request, response) => response.end('OK'), f.upstreamPath, true);
  await f.relay();
  const inode = (await stat(f.listenPath)).ino;
  await assert.rejects(startRelay({ listenPath: f.listenPath, upstreamPath: f.upstreamPath }), /already in use/);
  assert.equal((await stat(f.listenPath)).ino, inode);
  await checkHealth(f.listenPath);
});

test('non-socket listener files are preserved and listener permissions stay private', async t => {
  const f = await fixture(t);
  await writeFile(f.listenPath, 'keep');
  await assert.rejects(f.relay(), /non-socket/);
  assert.equal(await readFile(f.listenPath, 'utf8'), 'keep');
  await unlink(f.listenPath);
  await f.relay();
  assert.equal((await stat(f.listenPath)).mode & 0o777, 0o600);
  assert.equal((await stat(f.dir)).mode & 0o777, 0o700);
});
