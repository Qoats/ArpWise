#!/usr/bin/env node
'use strict';

// Opens the ArpWise window and returns to the terminal right away.
const path = require('path');
const { spawn } = require('child_process');

const exe = path.join(__dirname, '..', 'vendor', process.platform === 'win32' ? 'arpwise-gui.exe' : 'arpwise-gui');
const child = spawn(exe, process.argv.slice(2), { detached: true, stdio: 'ignore' });

child.on('error', (error) => {
  console.error(`arpwise-gui: ${error.message}`);
  console.error('Try reinstalling: npm install -g arpwise');
  process.exit(1);
});
child.unref();
