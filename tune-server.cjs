// Dev-only static server with a tiny save endpoint for the ?tune control panels.
//
//   node tune-server.cjs        → serves the site on http://localhost:3000
//
// Open http://localhost:3000/particles/?tune and drag the sliders. The biolum
// tuner POSTs its params to /__tune on every change; we write them straight to
// particles/defaults.json — the file the page loads as its source of truth. So
// tuned values are "saved" instantly; commit + push that file to ship them live.
// Use this instead of `npx serve` when tuning.
const http = require('http');
const fs   = require('fs');
const path = require('path');

const ROOT = __dirname;
const PORT = process.env.PORT || 3000;
const STATE_FILE = path.join(ROOT, 'particles', 'defaults.json');

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.css': 'text/css', '.json': 'application/json', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
  '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.wasm': 'application/wasm',
  '.woff': 'font/woff', '.woff2': 'font/woff2'
};

http.createServer((req, res) => {
  // ── tuner persistence endpoint ──
  if (req.method === 'POST' && req.url === '/__tune') {
    let body = '';
    req.on('data', c => { body += c; if (body.length > 1e6) req.destroy(); });
    req.on('end', () => {
      try {
        JSON.parse(body);                     // validate before writing
        fs.writeFileSync(STATE_FILE, body);
        res.writeHead(200); res.end('ok');
      } catch (e) { res.writeHead(400); res.end('bad json'); }
    });
    return;
  }

  // ── static files ──
  let urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
  if (urlPath.endsWith('/')) urlPath += 'index.html';
  const file = path.join(ROOT, urlPath);
  if (!file.startsWith(ROOT)) { res.writeHead(403); res.end('forbidden'); return; }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end('not found'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream' });
    res.end(data);
  });
}).listen(PORT, () => console.log(`tune server on http://localhost:${PORT}  (tuner → ${path.relative(ROOT, STATE_FILE)})`));
