#!/usr/bin/env node
// A byte-stream relay: never parse, cache or replay Docker API requests.
import net from 'node:net';
import http from 'node:http';
import { chmod, lstat, mkdir, unlink } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export const DEFAULT_LISTEN = '/run/hermes-docker/docker.sock';
export const DEFAULT_UPSTREAM = '/run/playground/docker.sock';

async function removeStaleSocket(path) {
  let before;
  try {
    before = await lstat(path);
  } catch (error) {
    if (error.code === 'ENOENT') return;
    throw error;
  }
  if (!before.isSocket()) throw new Error('refusing to replace a non-socket listener path');
  // Another relay may still own the path. A slow listener is not proof of death.
  await new Promise((done, reject) => {
    const probe = net.createConnection(path);
    const timer = setTimeout(() => {
      probe.destroy();
      reject(new Error('existing listener did not respond; leaving it intact'));
    }, 1000);
    probe.once('connect', () => {
      clearTimeout(timer);
      probe.destroy();
      reject(new Error('listener is already in use'));
    });
    probe.once('error', error => {
      clearTimeout(timer);
      probe.destroy();
      if (error.code === 'ECONNREFUSED' || error.code === 'ENOENT') done();
      else reject(error);
    });
  });
  try {
    const after = await lstat(path);
    if (before.dev !== after.dev || before.ino !== after.ino) {
      throw new Error('listener path changed during startup; leaving it intact');
    }
    await unlink(path);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}

export async function startRelay({
  listenPath = DEFAULT_LISTEN,
  upstreamPath = DEFAULT_UPSTREAM,
  connectTimeout = 5000,
  maxConnections = 256,
  log = message => console.error(`[docker-socket-relay] ${message}`),
} = {}) {
  if (resolve(listenPath) === resolve(upstreamPath)) {
    throw new Error('listener and upstream paths must differ');
  }
  await mkdir(dirname(listenPath), { recursive: true, mode: 0o700 });
  await chmod(dirname(listenPath), 0o700);
  await removeStaleSocket(listenPath);

  const sockets = new Set();
  let lastWarning = 0;
  const server = net.createServer({ allowHalfOpen: true }, client => {
    // Resolve the pathname on EVERY connection. Only the sidecar sees the
    // parent directory mount, so replacement of the host socket is visible.
    client.pause();
    const upstream = net.createConnection({ path: upstreamPath, allowHalfOpen: true });
    sockets.add(client);
    sockets.add(upstream);
    const closePair = () => {
      clearTimeout(timer);
      client.destroy();
      upstream.destroy();
    };
    const timer = setTimeout(closePair, connectTimeout);
    for (const [socket, peer] of [[client, upstream], [upstream, client]]) {
      socket.on('error', closePair);
      socket.once('close', hadError => {
        sockets.delete(socket);
        clearTimeout(timer);
        // A clean EOF may still have a large response buffered in the peer.
        // Let pipe/end drain it; only abort the other half on an abrupt close.
        if (hadError || !socket.readableEnded) peer.destroy();
      });
    }
    upstream.once('error', error => {
      if (Date.now() - lastWarning >= 5000) {
        lastWarning = Date.now();
        log(`upstream unavailable (${error.code || 'connection error'})`);
      }
    });
    upstream.once('connect', () => {
      clearTimeout(timer);
      // pipe provides bounded buffering/backpressure and preserves half-close,
      // HTTP keep-alive, chunked bodies and Docker's hijacked exec/attach stream.
      upstream.pipe(client);
      client.pipe(upstream);
    });
  });
  server.maxConnections = maxConnections;
  await new Promise((done, reject) => {
    server.once('error', reject);
    server.listen(listenPath, () => {
      server.removeListener('error', reject);
      done();
    });
  });
  try {
    await chmod(listenPath, 0o600);
  } catch (error) {
    await new Promise(done => server.close(done));
    throw error;
  }
  return {
    server,
    close: () => new Promise(done => {
      server.close(done);
      for (const socket of sockets) socket.destroy();
    }),
  };
}

export function checkHealth(socketPath = DEFAULT_LISTEN, timeout = 2000) {
  return new Promise((done, reject) => {
    const request = http.get({
      socketPath, path: '/_ping', agent: false, headers: { Connection: 'close' },
    }, response => {
      let body = '';
      response.setEncoding('utf8');
      response.on('error', reject);
      response.on('data', chunk => {
        body += chunk;
        if (body.length > 1024) request.destroy(new Error('oversized health response'));
      });
      response.on('end', () => {
        if (response.statusCode === 200 && body.trim() === 'OK') done();
        else reject(new Error('Docker ping failed'));
      });
    });
    const timer = setTimeout(() => request.destroy(new Error('Docker ping timed out')), timeout);
    request.on('error', reject);
    request.once('close', () => clearTimeout(timer));
  });
}

async function main() {
  const listenPath = process.env.DOCKER_RELAY_LISTEN || DEFAULT_LISTEN;
  if (process.argv.includes('--check')) {
    await checkHealth(listenPath);
    console.log('Docker socket relay: OK');
    return;
  }
  const relay = await startRelay({
    listenPath,
    upstreamPath: process.env.DOCKER_RELAY_UPSTREAM || DEFAULT_UPSTREAM,
  });
  console.log('[docker-socket-relay] listening on local Unix socket');
  let stopping = false;
  const stop = () => {
    if (stopping) return;
    stopping = true;
    relay.close().then(() => process.exit(0));
  };
  process.on('SIGTERM', stop);
  process.on('SIGINT', stop);
  relay.server.on('error', error => {
    console.error(`[docker-socket-relay] listener failed (${error.code || 'error'})`);
    process.exitCode = 1;
    relay.close();
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch(error => {
    console.error(`[docker-socket-relay] ${error.message}`);
    process.exitCode = 1;
  });
}
