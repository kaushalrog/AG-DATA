// Stamps app/sw.js with a content hash of every precached shell file, so any change to the
// app shell produces a new cache version and reaches installed clients (red-team RT-17).
//   node app/tools/stamp-sw.mjs          # rewrite VERSION in sw.js
//   node app/tools/stamp-sw.mjs --check  # exit 1 if VERSION is out of date (used by tests)
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export function shellHash() {
  const sw = readFileSync(path.join(APP, 'sw.js'), 'utf8');
  const list = JSON.parse(sw.match(/const PRECACHE = (\[[\s\S]*?\]);/)[1].replace(/'/g, '"').replace(/,\s*\]/, ']'));
  const files = list.filter((f) => f !== './').sort();
  const h = createHash('sha256');
  for (const f of files) h.update(f).update(readFileSync(path.join(APP, f)));
  // the service worker's own logic, minus the VERSION line
  h.update(sw.replace(/const VERSION = '[^']*';/, ''));
  return 'v-' + h.digest('hex').slice(0, 12);
}

export function currentVersion() {
  return readFileSync(path.join(APP, 'sw.js'), 'utf8').match(/const VERSION = '([^']*)';/)[1];
}

if (process.argv[1] && process.argv[1].endsWith('stamp-sw.mjs')) {
  const want = shellHash();
  if (process.argv.includes('--check')) process.exit(currentVersion() === want ? 0 : 1);
  const p = path.join(APP, 'sw.js');
  writeFileSync(p, readFileSync(p, 'utf8').replace(/const VERSION = '[^']*';/, `const VERSION = '${want}';`));
  console.log(want);
}
