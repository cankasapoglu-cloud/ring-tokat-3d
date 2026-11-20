// Sahneyi kare kare çizip MP4'e dönüştürür.
// Kullanım: node render.mjs [kareKlasoru] [--onizleme t1,t2,...]
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require(path.join(process.env.NODE_PATH || '/opt/node22/lib/node_modules', 'playwright'))); }

const D = path.dirname(fileURLToPath(import.meta.url));
const TL = JSON.parse(fs.readFileSync(path.join(D, 'zaman.json'), 'utf8'));
const ZARF = JSON.parse(fs.readFileSync(path.join(D, 'zarf.json'), 'utf8'));
const args = process.argv.slice(2);
const oi = args.indexOf('--onizleme');
const onizleme = oi >= 0 ? args[oi + 1].split(',').map(Number) : null;
const kareler = path.resolve(args[0] && !args[0].startsWith('--') ? args[0] : path.join(D, 'kareler'));
fs.mkdirSync(kareler, { recursive: true });

const ISCI = 4;
const toplam = Math.round(TL.sure * TL.fps);
const tarayici = await chromium.launch();

async function sayfaAc() {
  const s = await tarayici.newPage({ viewport: { width: 1920, height: 1080 } });
  await s.addInitScript(([tl, zarf]) => { window.TL = tl; window.ZARF = zarf; }, [TL, ZARF]);
  await s.goto('file://' + path.join(D, 'sahne.html'));
  await s.evaluate(async () => { await document.fonts.load('700 100px Fredoka', 'Pıtır ŞİĞ abc 123'); await document.fonts.ready; });
  return s;
}
const ciz = (s, t, kalite) => s.evaluate(([t, k]) => {
  window.kareCiz(t);
  return document.getElementById('c').toDataURL(k ? 'image/jpeg' : 'image/png', k || undefined).split(',')[1];
}, [t, kalite]);

if (onizleme) {
  const s = await sayfaAc();
  for (const t of onizleme) fs.writeFileSync(path.join(kareler, `onizleme_${t.toFixed(1)}.png`), Buffer.from(await ciz(s, t, 0), 'base64'));
  await tarayici.close();
  console.log('önizleme kareleri:', kareler);
} else {
  const t0 = Date.now();
  await Promise.all(Array.from({ length: ISCI }, async (_, w) => {
    const s = await sayfaAc();
    for (let i = w; i < toplam; i += ISCI) {
      fs.writeFileSync(path.join(kareler, `k_${String(i).padStart(5, '0')}.jpg`), Buffer.from(await ciz(s, i / TL.fps, 0.94), 'base64'));
      if (w === 0 && i % 400 === 0) console.log(`kare ${i}/${toplam}`);
    }
  }));
  await tarayici.close();
  console.log(`${toplam} kare, ${((Date.now() - t0) / 1000).toFixed(0)} sn`);
  const cikti = path.join(D, 'pitir-ile-ogren-01.mp4');
  const r = spawnSync('ffmpeg', ['-y', '-v', 'error', '-framerate', String(TL.fps), '-i', path.join(kareler, 'k_%05d.jpg'),
    '-i', path.join(D, 'ses', 'mix.wav'), '-c:v', 'libx264', '-preset', 'slow', '-crf', '25', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', cikti], { stdio: 'inherit' });
  if (r.status !== 0) process.exit(r.status ?? 1);
  console.log('video:', cikti);
}
