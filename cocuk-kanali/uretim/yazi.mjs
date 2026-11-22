// Ekran yazılarını (genel; kullanım: node yazi.mjs <şarkı klasörü>) (başlık ve ses sözcükleri) şeffaf PNG olarak üretir.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const D = path.resolve(process.argv[2]); const BETIK = path.dirname(fileURLToPath(import.meta.url));
const b64 = f => fs.readFileSync(path.join(BETIK, '..', 'uzun-01', 'fonts', f)).toString('base64');
const AYAR = JSON.parse(fs.readFileSync(path.join(process.argv[2], 'sozler.json'), 'utf8'));
const R = AYAR.yazilar;   // { anahtar: [metin, renk adı ("renkli" = her harf ayrı renk), yatay kaydırma px (isteğe bağlı), harf boyu px (isteğe bağlı)] }
const RENK = { kirmizi: ['#E53935', '#FF8A80', '#9A1212'], mavi: ['#1E88E5', '#90CAF9', '#0B3C8A'], yesil: ['#43A047', '#A5D6A7', '#14521A'],
  turuncu: ['#FB8C00', '#FFCC80', '#A84E00'], mor: ['#8E24AA', '#CE93D8', '#43117A'], sari: ['#FBC02D', '#FFF59D', '#8A5A00'],
  pembe: ['#EC407A', '#F8BBD0', '#8E1244'], turkuaz: ['#00ACC1', '#80DEEA', '#00565F'], gri: ['#90A4AE', '#ECEFF1', '#37474F'], lacivert: ['#3949AB', '#9FA8DA', '#1A237E'] };
const PALET = [RENK.kirmizi, RENK.mavi, RENK.turuncu, RENK.yesil, RENK.mor];
fs.mkdirSync(path.join(D, 'yazi'), { recursive: true });
const tarayici = await chromium.launch();
const s = await tarayici.newPage({ viewport: { width: 1920, height: 400 } });
await s.setContent(`<style>
@font-face{font-family:Fredoka;font-weight:700;src:url(data:font/woff2;base64,${b64('fredoka-latin-ext-700-normal.woff2')}) format('woff2');unicode-range:U+0100-02BA,U+1E00-1E9F}
@font-face{font-family:Fredoka;font-weight:700;src:url(data:font/woff2;base64,${b64('fredoka-latin-700-normal.woff2')}) format('woff2');unicode-range:U+0000-00FF,U+0131}
body{margin:0;background:transparent}</style><canvas id=c width=1920 height=400></canvas>`);
await s.evaluate(async () => { await document.fonts.load('700 100px Fredoka', 'Şİıç abc'); await document.fonts.ready; });
const ciz = (harfler, boy, dx = 0, enCok = 1760) => s.evaluate(([harfler, boy, dx, enCok]) => {
  const c = document.getElementById('c'), g = c.getContext('2d'); g.clearRect(0, 0, 1920, 400);
  const olc = () => { g.font = `700 ${boy}px Fredoka`; return harfler.map(h => g.measureText(h[0]).width); };
  let gen = olc(); let top = gen.reduce((a, b) => a + b, 0) + boy * 0.08 * (gen.length - 1);
  if (top > enCok) { boy = Math.floor(boy * enCok / top); gen = olc(); top = gen.reduce((a, b) => a + b, 0) + boy * 0.08 * (gen.length - 1); }
  g.textBaseline = 'middle'; g.textAlign = 'left'; g.lineJoin = 'round';
  const bosluk = boy * 0.08;
  let x = 960 + dx - top / 2;
  harfler.forEach(([h, cc, a, k], i) => {
    if (h !== ' ') {
      g.save(); g.translate(x, 190);
      g.strokeStyle = k; g.lineWidth = boy * 0.2; for (let q = 5; q >= 0; q--) g.strokeText(h, 0, boy * 0.085 * q / 5 + boy * 0.01);
      g.strokeStyle = '#fff'; g.lineWidth = boy * 0.12; g.strokeText(h, 0, 0);
      const gr = g.createLinearGradient(0, -boy * 0.45, 0, boy * 0.45); gr.addColorStop(0, a); gr.addColorStop(0.45, cc); gr.addColorStop(1, cc);
      g.fillStyle = gr; g.fillText(h, 0, 0); g.restore();
    }
    x += gen[i] + bosluk;
  });
  return c.toDataURL('image/png').split(',')[1];
}, [harfler, boy, dx, enCok]);
const harfle = (metin, renk) => { let n = 0; return [...metin].map(h => h === ' ' ? [' '] : [h, ...(renk === 'renkli' ? PALET[n++ % 5] : RENK[renk])]); };
for (const [ad, [metin, renk, dx, boy]] of Object.entries(R))
  fs.writeFileSync(path.join(D, 'yazi', ad + '.png'), Buffer.from(await ciz(harfle(metin, renk), boy || 150, dx || 0), 'base64'));
fs.writeFileSync(path.join(D, 'yazi', 'baslik.png'), Buffer.from(await ciz(harfle(AYAR.baslik_yazi, 'renkli'), 170), 'base64'));
await tarayici.close(); console.log(fs.readdirSync(path.join(D, 'yazi')).join(' '));
