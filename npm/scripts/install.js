#!/usr/bin/env node
'use strict';

// Downloads the ArpWise program that matches this system from the GitHub
// release, checks its SHA-256 against the published SHA256SUMS.txt, and
// unpacks it into ../vendor. No dependencies.

const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const zlib = require('zlib');
const crypto = require('crypto');

const pkg = require('../package.json');

if (process.env.ARPWISE_SKIP_DOWNLOAD) {
  console.log('arpwise: ARPWISE_SKIP_DOWNLOAD is set, skipping the download.');
  process.exit(0);
}

const PLATFORMS = { win32: 'win32', linux: 'linux' };
const ARCHS = { x64: 'x64', ia32: 'ia32', arm64: 'arm64' };

const platform = PLATFORMS[process.platform];
const arch = ARCHS[process.arch];
if (!platform || !arch) {
  console.error(
    `arpwise: unsupported system (${process.platform}/${process.arch}). ` +
      'Windows and Linux on x64, ia32 and arm64 are supported.'
  );
  process.exit(1);
}

const version = pkg.version;
const base =
  process.env.ARPWISE_DOWNLOAD_BASE ||
  `https://github.com/Qoats/ArpWise/releases/download/v${version}`;
const archive = `arpwise-${version}-${platform}-${arch}.tar.gz`;
const vendor = path.join(__dirname, '..', 'vendor');
const wanted = new Set(
  process.platform === 'win32' ? ['arpwise.exe', 'arpwise-gui.exe'] : ['arpwise', 'arpwise-gui']
);

function get(url, redirects = 8) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('http://') ? http : https;
    client
      .get(url, { headers: { 'User-Agent': `arpwise-npm/${version}` } }, (res) => {
        const code = res.statusCode || 0;
        if ([301, 302, 303, 307, 308].includes(code) && res.headers.location) {
          res.resume();
          if (redirects <= 0) return reject(new Error('too many redirects'));
          return resolve(get(new URL(res.headers.location, url).toString(), redirects - 1));
        }
        if (code !== 200) {
          res.resume();
          return reject(new Error(`HTTP ${code} for ${url}`));
        }
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => resolve(Buffer.concat(chunks)));
        res.on('error', reject);
      })
      .on('error', reject);
  });
}

function field(header, from, to) {
  return header.toString('utf8', from, to).replace(/\0.*$/s, '');
}

/** Minimal tar reader: yields { name, data } for regular files. */
function* untar(buffer) {
  let offset = 0;
  while (offset + 512 <= buffer.length) {
    const header = buffer.subarray(offset, offset + 512);
    const name = field(header, 0, 100);
    if (!name) break; // end of archive
    const size = parseInt(field(header, 124, 136).trim() || '0', 8);
    const type = String.fromCharCode(header[156] || 48);
    offset += 512;
    if (type === '0') yield { name, data: buffer.subarray(offset, offset + size) };
    offset += Math.ceil(size / 512) * 512;
  }
}

async function main() {
  console.log(`arpwise: downloading ${archive}`);
  const [data, sums] = await Promise.all([get(`${base}/${archive}`), get(`${base}/SHA256SUMS.txt`)]);

  const line = sums
    .toString('utf8')
    .split(/\r?\n/)
    .map((l) => l.trim().split(/\s+/))
    .find((parts) => parts[1] === archive || parts[1] === `*${archive}`);
  if (!line) throw new Error(`${archive} is not listed in SHA256SUMS.txt`);
  const actual = crypto.createHash('sha256').update(data).digest('hex');
  if (actual !== line[0].toLowerCase()) {
    throw new Error(`checksum mismatch for ${archive}: expected ${line[0]}, got ${actual}`);
  }

  fs.mkdirSync(vendor, { recursive: true });
  let found = 0;
  for (const entry of untar(zlib.gunzipSync(data))) {
    const file = path.basename(entry.name); // never trust paths inside the archive
    if (!wanted.has(file)) continue;
    const target = path.join(vendor, file);
    fs.writeFileSync(target, entry.data);
    if (process.platform !== 'win32') fs.chmodSync(target, 0o755);
    found += 1;
  }
  if (found !== wanted.size) throw new Error(`${archive} does not contain the expected programs`);
  console.log('arpwise: installed. Run "arpwise" (terminal) or "arpwise-gui" (window).');
}

main().catch((error) => {
  console.error(`arpwise: installation failed: ${error.message}`);
  console.error('You can also download ArpWise from https://qoats.github.io/ArpWise/');
  process.exit(1);
});
