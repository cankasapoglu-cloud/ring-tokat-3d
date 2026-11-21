// Ekran yazılarını (başlık ve renk adları) şeffaf PNG olarak üretir.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const D = path.dirname(fileURLToPath(import.meta.url));
const b64 = f => fs.readFileSync(path.join(D, '..', 'uzun-01', 'fonts', f)).toString('base64');
const R = { bebek: ['BEBEK', '#FBC02D', '#FFF59D', '#C67100'], anne: ['ANNE', '#E53935', '#FF8A80', '#9A1212'], baba: ['BABA', '#1E88E5', '#90CAF9', '#0B3C8A'], nine: ['NİNE', '#8E24AA', '#CE93D8', '#43117A'], dede: ['DEDE', '#43A047', '#A5D6A7', '#14521A'] };
const P = { kirmizi: ['', '#E53935', '#FF8A80', '#9A1212'], mavi: ['', '#1E88E5', '#90CAF9', '#0B3C8A'], yesil: ['', '#43A047', '#A5D6A7', '#14521A'] };
const tarayici = await chromium.launch();
const s = await tarayici.newPage({ viewport: { width: 1920, height: 400 } });
await s.setContent(`<style>
@font-face{font-family:Fredoka;font-weight:700;src:url(data:font/woff2;base64,${b64('fredoka-latin-ext-700-normal.woff2')}) format('woff2');unicode-range:U+0100-02BA,U+1E00-1E9F}
@font-face{font-family:Fredoka;font-weight:700;src:url(data:font/woff2;base64,${b64('fredoka-latin-700-normal.woff2')}) format('woff2');unicode-range:U+0000-00FF,U+0131}
body{margin:0;background:transparent}</style><canvas id=c width=1920 height=400></canvas>`);
await s.evaluate(async () => { await document.fonts.load('700 100px Fredoka', 'Şİıç abc'); await document.fonts.ready; });
const ciz = (harfler, boy) => s.evaluate(([harfler, boy]) => {
  const c = document.getElementById('c'), g = c.getContext('2d'); g.clearRect(0, 0, 1920, 400);
  g.font = `700 ${boy}px Fredoka`; g.textBaseline = 'middle'; g.textAlign = 'left'; g.lineJoin = 'round';
  const bosluk = boy * 0.08, gen = harfler.map(h => g.measureText(h[0]).width);
  let x = 960 - (gen.reduce((a, b) => a + b, 0) + bosluk * (gen.length - 1)) / 2;
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
}, [harfler, boy]);
for (const [ad, [metin, c, a, k]] of Object.entries(R))
  fs.writeFileSync(path.join(D, 'yazi', ad + '.png'), Buffer.from(await ciz([...metin].map(h => [h, c, a, k]), 190), 'base64'));
const palet = [P.kirmizi, P.mavi, ['', '#FB8C00', '#FFCC80', '#A84E00'], P.yesil, ['', '#8E24AA', '#CE93D8', '#43117A']];
let n = 0;
const baslik = [..."Pıtır'ın Ailesi"].map(h => h === ' ' ? [' '] : [h, ...palet[n++ % 5].slice(1)]);
fs.writeFileSync(path.join(D, 'yazi', 'baslik.png'), Buffer.from(await ciz(baslik, 190), 'base64'));
await tarayici.close(); console.log(fs.readdirSync(path.join(D, 'yazi')).join(' '));
