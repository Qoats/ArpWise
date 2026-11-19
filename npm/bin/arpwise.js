#!/usr/bin/env node
'use strict';

// Runs the command-line program downloaded by scripts/install.js.
const path = require('path');
const { spawnSync } = require('child_process');

const exe = path.join(__dirname, '..', 'vendor', process.platform === 'win32' ? 'arpwise.exe' : 'arpwise');
const result = spawnSync(exe, process.argv.slice(2), { stdio: 'inherit' });

if (result.error) {
  console.error(`arpwise: ${result.error.message}`);
  console.error('Try reinstalling: npm install -g arpwise');
  process.exit(1);
}
process.exit(result.status === null ? 1 : result.status);
