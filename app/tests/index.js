// Entry point so `node --test app/tests/` works: Node resolves a directory argument to its index.js.
// It loads every *.test.mjs in this folder (they can also be run directly: node --test app/tests/*.test.mjs).
const { readdirSync } = require('node:fs');
const { join } = require('node:path');
const { pathToFileURL } = require('node:url');

for (const f of readdirSync(__dirname).filter((x) => x.endsWith('.test.mjs')).sort()) {
  import(pathToFileURL(join(__dirname, f)).href);
}
