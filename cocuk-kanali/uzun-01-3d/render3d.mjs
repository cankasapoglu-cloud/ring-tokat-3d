// 3D görselli sahneyi kare kare çizip MP4'e dönüştürür.
// Kullanım: node render3d.mjs [kareKlasoru] [--onizleme t1,t2,...]
import { createRequire } from 'node:module';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require(path.join(process.env.NODE_PATH || '/opt/node22/lib/node_modules', 'playwright'))); }

const D = path.dirname(fileURLToPath(import.meta.url));
const KOK = path.resolve(D, '..');                       // cocuk-kanali/
const VERI = path.join(KOK, 'uzun-01');
const TL = JSON.parse(fs.readFileSync(path.join(VERI, 'zaman.json'), 'utf8'));
const ZARF = JSON.parse(fs.readFileSync(path.join(VERI, 'zarf.json'), 'utf8'));
const AYAR = fs.existsSync(path.join(D, 'ayar.json')) ? JSON.parse(fs.readFileSync(path.join(D, 'ayar.json'), 'utf8')) : {};
const VARLIK = fs.readdirSync(path.join(KOK, '3d', 'hazir')).filter(f => /\.(png|jpg)$/.test(f));
const args = process.argv.slice(2);
const oi = args.indexOf('--onizleme');
const onizleme = oi >= 0 ? args[oi + 1].split(',').map(Number) : null;
const kareler = path.resolve(args[0] && !args[0].startsWith('--') ? args[0] : path.join(D, 'kareler'));
fs.mkdirSync(kareler, { recursive: true });

// Görseller canvas'ı "kirletmesin" diye dosyalar yerel bir http sunucusundan verilir.
const TUR = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const sunucu = http.createServer((q, r) => {
  const p = path.normalize(path.join(KOK, decodeURIComponent(q.url.split('?')[0])));
  if (!p.startsWith(KOK) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { r.writeHead(404); r.end(); return; }
  r.writeHead(200, { 'Content-Type': TUR[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(r);
});
await new Promise(res => sunucu.listen(0, '127.0.0.1', res));
const URL0 = `http://127.0.0.1:${sunucu.address().port}`;

const ISCI = 3;
const toplam = Math.round(TL.sure * TL.fps);
const tarayici = await chromium.launch();
async function sayfaAc() {
  const s = await tarayici.newPage({ viewport: { width: 1920, height: 1080 } });
  s.on('pageerror', e => console.error('SAYFA HATASI:', e.message));
  await s.addInitScript(([tl, zarf, ayar]) => { window.TL = tl; window.ZARF = zarf; window.AYAR = ayar; }, [TL, ZARF, AYAR]);
  await s.goto(`${URL0}/uzun-01-3d/sahne3d.html`);
  await s.evaluate(async (v) => {
    await document.fonts.load('700 100px Fredoka', 'Pıtır ŞİĞ abc 123'); await document.fonts.ready;
    await window.hazirla(v, '../3d/hazir/');
  }, VARLIK);
  return s;
}
const ciz = (s, t, kalite) => s.evaluate(([t, k]) => {
  window.kareCiz(t);
  return document.getElementById('c').toDataURL(k ? 'image/jpeg' : 'image/png', k || undefined).split(',')[1];
}, [t, kalite]);

if (onizleme) {
  const s = await sayfaAc();
  for (const t of onizleme) fs.writeFileSync(path.join(kareler, `onizleme_${t.toFixed(1)}.jpg`), Buffer.from(await ciz(s, t, 0.9), 'base64'));
  console.log('önizleme kareleri:', kareler);
} else {
  const t0 = Date.now();
  await Promise.all(Array.from({ length: ISCI }, async (_, w) => {
    const s = await sayfaAc();
    for (let i = w; i < toplam; i += ISCI) {
      fs.writeFileSync(path.join(kareler, `k_${String(i).padStart(5, '0')}.jpg`), Buffer.from(await ciz(s, i / TL.fps, 0.94), 'base64'));
      if (w === 0 && i % 1500 === 0) console.log(`kare ${i}/${toplam}`);
    }
  }));
  console.log(`${toplam} kare, ${((Date.now() - t0) / 1000).toFixed(0)} sn`);
  const cikti = path.join(D, 'pitir-ile-ogren-01-3d.mp4');
  const r = spawnSync('ffmpeg', ['-y', '-v', 'error', '-framerate', String(TL.fps), '-i', path.join(kareler, 'k_%05d.jpg'),
    '-i', path.join(VERI, 'ses', 'mix.wav'), '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', cikti], { stdio: 'inherit' });
  if (r.status !== 0) process.exit(r.status ?? 1);
  console.log('video:', cikti);
}
await tarayici.close(); sunucu.close();
