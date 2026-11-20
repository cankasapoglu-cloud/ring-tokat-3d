// "Pıtır ile Öğren" — uzun bölüm sahneleri.
// Her şey t'nin (saniye) saf fonksiyonu: window.kareCiz(t).
// TL (zaman.json) ve ZARF (zarf.json) render.mjs tarafından enjekte edilir.
(() => {
  const W = 1920, H = 1080;
  const TL = window.TL, ZARF = window.ZARF || [];
  const g = document.getElementById('c').getContext('2d');

  // ---------- yardımcılar ----------
  const sinirla = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const ara = (a, b, p) => a + (b - a) * p;
  const ilerle = (t, t0, d) => sinirla((t - t0) / d);
  const yumusak = x => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  const yavasla = x => 1 - Math.pow(1 - x, 3);
  const geri = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const patla = (t, t0, d = 0.5) => { const p = ilerle(t, t0, d); return p <= 0 ? 0 : geri(p); };
  const zipla = (t, t0, d = 0.5) => Math.sin(Math.PI * ilerle(t, t0, d));
  const rasgele = k => { const x = Math.sin(k * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  const gorun = (t, a, b, gir = 0.45, cik = 0.35) => patla(t, a, gir) * (1 - yumusak(ilerle(t, b - cik, cik)));
  const daire = (x, y, r) => { g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); };
  const elips = (x, y, rx, ry, a = 0) => { g.beginPath(); g.ellipse(x, y, rx, ry, a, 0, 7); g.fill(); };
  const kutu = (x, y, w, h, r) => { g.beginPath(); g.roundRect(x, y, w, h, r); g.fill(); };

  const RENK = [
    { ad: 'KIRMIZI', c: '#E53935', a: '#FF8A80', k: '#B71C1C', nesne: 'elma' },
    { ad: 'MAVİ', c: '#1E88E5', a: '#90CAF9', k: '#0D47A1', nesne: 'deniz' },
    { ad: 'SARI', c: '#FDD835', a: '#FFF59D', k: '#F57F17', nesne: 'gunes' },
    { ad: 'YEŞİL', c: '#43A047', a: '#A5D6A7', k: '#1B5E20', nesne: 'yaprak' },
    { ad: 'TURUNCU', c: '#FB8C00', a: '#FFCC80', k: '#BF5B00', nesne: null },
    { ad: 'MOR', c: '#8E24AA', a: '#CE93D8', k: '#4A148C', nesne: 'uzum' },
  ];
  const TURUNCU = '#FF8A3D';
  const MOR = { c: '#8E24AA', k: '#4A148C' };

  // ---------- yazı ----------
  function buyukYazi(metin, x, y, boy, dolgu, kenar, olcek = 1, aci = 0) {
    if (olcek <= 0.01) return;
    g.save(); g.translate(x, y); g.rotate(aci); g.scale(olcek, olcek);
    g.font = `700 ${boy}px Fredoka`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineJoin = 'round';
    g.strokeStyle = kenar; g.lineWidth = boy * 0.26; g.strokeText(metin, 0, 0);
    g.strokeStyle = '#fff'; g.lineWidth = boy * 0.15; g.strokeText(metin, 0, 0);
    g.fillStyle = dolgu; g.fillText(metin, 0, 0);
    g.restore();
  }
  function renkliYazi(metin, x, y, boy, t, olcek = 1) {
    if (olcek <= 0.01) return;
    g.save(); g.translate(x, y); g.scale(olcek, olcek);
    g.font = `700 ${boy}px Fredoka`; g.textBaseline = 'middle'; g.textAlign = 'left'; g.lineJoin = 'round';
    const palet = [RENK[0], RENK[1], RENK[4], RENK[3], RENK[5]];
    const bosluk = boy * 0.07;
    let cx = -(g.measureText(metin).width + bosluk * (metin.length - 1)) / 2, n = 0;
    for (const h of metin) {
      const gen = g.measureText(h).width;
      if (h !== ' ') {
        const r = palet[n % palet.length], dy = Math.sin(t * 3 + n * 0.7) * boy * 0.05;
        g.strokeStyle = r.k; g.lineWidth = boy * 0.26; g.strokeText(h, cx, dy);
        g.strokeStyle = '#fff'; g.lineWidth = boy * 0.15; g.strokeText(h, cx, dy);
        g.fillStyle = r.c; g.fillText(h, cx, dy); n++;
      }
      cx += gen + bosluk;
    }
    g.restore();
  }
  function soruIsaretleri(t, tur, x1 = 1420, y1 = 300, x2 = 650, y2 = 240) {
    const o = gorun(t, tur.soruBit + 0.1, tur.cevap, 0.4, 0.25);
    if (o <= 0) return;
    buyukYazi('?', x1, y1 + Math.sin(t * 3) * 14, 260, MOR.c, MOR.k, o, Math.sin(t * 2.4) * 0.18);
    buyukYazi('?', x2, y2 + Math.sin(t * 3 + 2) * 14, 180, MOR.c, MOR.k, o * 0.95, Math.sin(t * 2.4 + 2) * 0.18);
  }
  function kelime(t, tur, metin, dolgu, kenar, x = 1000, y = 150, boy = 176) {
    const o = gorun(t, tur.cevap, tur.bit - 0.3);
    buyukYazi(metin, x, y, boy, dolgu, kenar, o * (1 + 0.04 * Math.sin(t * 6)));
  }
  function yuz(y = 0, s = 1) {
    g.fillStyle = '#3B2A20'; daire(-26 * s, y - 8 * s, 9 * s); daire(26 * s, y - 8 * s, 9 * s);
    g.strokeStyle = '#3B2A20'; g.lineWidth = 6 * s; g.lineCap = 'round';
    g.beginPath(); g.arc(0, y + 8 * s, 22 * s, 0.2, Math.PI - 0.2); g.stroke();
  }
  function rozet(x, y, olcek, t, ciz) {
    if (olcek <= 0.01) return;
    g.save(); g.translate(x, y + Math.sin(t * 2 + x) * 8); g.scale(olcek, olcek);
    g.fillStyle = 'rgba(255,255,255,0.92)'; daire(0, 0, 165);
    g.strokeStyle = 'rgba(120,160,190,0.35)'; g.lineWidth = 6; g.stroke();
    ciz(); g.restore();
  }
  function isilti(x, y, r, t, adet = 8, renk = '#FFD54F') {
    g.fillStyle = renk;
    for (let k = 0; k < adet; k++) {
      const a = k * (6.283 / adet) + t * 1.5, rr = r * (0.8 + 0.2 * Math.sin(t * 5 + k));
      yildizYol(x + Math.cos(a) * rr, y + Math.sin(a) * rr, 16 + 6 * Math.sin(t * 6 + k * 2), 4); g.fill();
    }
  }
  function yildizYol(x, y, r, uc = 5) {
    g.beginPath();
    for (let k = 0; k < uc * 2; k++) {
      const a = -Math.PI / 2 + k * Math.PI / uc, rr = k % 2 ? r * 0.45 : r;
      g.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr);
    }
    g.closePath();
  }

  // ---------- arka plan ----------
  function bulut(x, y, s) {
    g.save(); g.translate(x, y); g.scale(s, s); g.fillStyle = 'rgba(255,255,255,0.92)';
    for (const [cx, cy, r] of [[-70, 10, 50], [-20, -20, 65], [45, -5, 55], [95, 15, 40], [10, 25, 60]]) daire(cx, cy, r);
    g.restore();
  }
  function cicek(x, y, renk, t, k) {
    g.save(); g.translate(x, y); g.rotate(Math.sin(t * 1.4 + k) * 0.08);
    g.strokeStyle = '#6DBE6A'; g.lineWidth = 6; g.lineCap = 'round';
    g.beginPath(); g.moveTo(0, 0); g.lineTo(0, -46); g.stroke();
    g.translate(0, -52); g.fillStyle = renk;
    for (let p = 0; p < 5; p++) daire(Math.cos(p * 1.2566) * 13, Math.sin(p * 1.2566) * 13, 10);
    g.fillStyle = '#FFF3C4'; daire(0, 0, 8);
    g.restore();
  }
  function arkaPlan(t, cicekli = true, hiz = 1) {
    const gok = g.createLinearGradient(0, 0, 0, H);
    gok.addColorStop(0, '#BDE7FF'); gok.addColorStop(0.7, '#EAF8FF'); gok.addColorStop(1, '#F7FCFF');
    g.fillStyle = gok; g.fillRect(0, 0, W, H);
    [[200, 170, 1.2, 9], [900, 300, 0.8, 6], [1450, 330, 1.0, 11], [1750, 560, 0.7, 7]]
      .forEach(([x, y, s, v]) => bulut(((x + t * v * hiz + 300) % (W + 600)) - 300, y, s));
    g.fillStyle = '#D5F0CC';
    g.beginPath(); g.moveTo(0, 860); g.quadraticCurveTo(480, 700, 960, 850); g.quadraticCurveTo(1500, 990, W, 800); g.lineTo(W, H); g.lineTo(0, H); g.fill();
    g.fillStyle = '#B4E3AC';
    g.beginPath(); g.moveTo(0, 930); g.quadraticCurveTo(500, 850, 1000, 940); g.quadraticCurveTo(1500, 1020, W, 930); g.lineTo(W, H); g.lineTo(0, H); g.fill();
    if (cicekli) {
      const cc = ['#FFB3D1', '#FFFFFF', '#D9B8FF', '#FFB3D1', '#FFFFFF', '#D9B8FF', '#FFB3D1'];
      [80, 610, 820, 1130, 1380, 1640, 1850].forEach((x, k) => cicek(x, 1010 + (k % 3) * 22, cc[k], t, k));
    }
  }
  function nota(x, y, s, renk) {
    g.save(); g.translate(x, y); g.scale(s, s); g.fillStyle = renk; g.strokeStyle = renk;
    elips(0, 0, 20, 15, -0.4); g.lineWidth = 7; g.lineCap = 'round';
    g.beginPath(); g.moveTo(17, -4); g.lineTo(17, -72); g.lineTo(48, -58); g.stroke();
    g.restore();
  }
  function notalar(t, t0) {
    for (let k = 0; k < 9; k++) {
      const p = ((t - t0) * 0.16 + rasgele(k + 3)) % 1;
      const x = 150 + rasgele(k + 40) * 1620 + Math.sin(t * 1.5 + k) * 40, y = 950 - p * 900;
      g.globalAlpha = Math.sin(Math.PI * p) * 0.8; nota(x, y, 0.8 + rasgele(k) * 0.6, RENK[k % 6].c); g.globalAlpha = 1;
    }
  }
  function konfeti(t, t0) {
    const dt = t - t0; if (dt < 0) return;
    for (let k = 0; k < 150; k++) {
      const y = ((-60 - rasgele(k + 500) * 1300 + dt * (220 + rasgele(k) * 200)) % (H + 1400));
      if (y < -40 || y > H + 40) continue;
      g.save(); g.translate(rasgele(k + 900) * W + Math.sin(t * 2 + k) * 36, y); g.rotate(t * (2 + rasgele(k + 70) * 3) + k);
      g.fillStyle = RENK[k % 6].c;
      g.fillRect(-11, -7 * Math.abs(Math.cos(t * 4 + k)) - 1, 22, 14 * Math.abs(Math.cos(t * 4 + k)) + 2);
      g.restore();
    }
  }

  // ---------- balon ----------
  function balon(x, y, s, r, t, k = 0, yazi = null) {
    if (s <= 0.01) return;
    g.save(); g.translate(x, y); g.scale(s, s); g.rotate(Math.sin(t * 1.3 + k * 2) * 0.05);
    g.strokeStyle = '#8D99A6'; g.lineWidth = 5; g.lineCap = 'round';
    g.beginPath(); g.moveTo(0, 222);
    for (let q = 1; q <= 12; q++) g.lineTo(Math.sin(q * 0.9 + t * 2 + k) * 12, 222 + q * 20);
    g.stroke();
    g.fillStyle = r.k; g.beginPath(); g.moveTo(0, 198); g.lineTo(-20, 232); g.lineTo(20, 232); g.closePath(); g.fill();
    const gr = g.createRadialGradient(-60, -80, 20, 0, 0, 230);
    gr.addColorStop(0, r.a); gr.addColorStop(0.55, r.c); gr.addColorStop(1, r.k);
    g.fillStyle = gr; elips(0, 0, 172, 205);
    g.fillStyle = 'rgba(255,255,255,0.55)'; elips(-72, -95, 28, 52, 0.5);
    if (yazi) {
      g.font = '700 230px Fredoka'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineJoin = 'round';
      g.strokeStyle = r.k; g.lineWidth = 26; g.strokeText(yazi, 0, 14); g.fillStyle = '#fff'; g.fillText(yazi, 0, 14);
    }
    g.restore();
  }

  // ---------- küçük nesneler ----------
  function elma(x, y, s, yuzlu = false, yazi = null) {
    g.save(); g.translate(x, y); g.scale(s, s);
    g.fillStyle = '#E53935'; elips(-36, 12, 68, 82, 0.12); elips(36, 12, 68, 82, -0.12);
    g.strokeStyle = '#6D4C41'; g.lineWidth = 10; g.lineCap = 'round';
    g.beginPath(); g.moveTo(0, -58); g.quadraticCurveTo(4, -88, 18, -100); g.stroke();
    g.fillStyle = '#66BB6A'; elips(42, -92, 30, 14, -0.5);
    g.fillStyle = 'rgba(255,255,255,0.5)'; elips(-58, -22, 12, 24, 0.4);
    if (yuzlu) yuz(22);
    if (yazi) {
      g.font = '700 120px Fredoka'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineJoin = 'round';
      g.strokeStyle = '#B71C1C'; g.lineWidth = 18; g.strokeText(yazi, 0, 22); g.fillStyle = '#fff'; g.fillText(yazi, 0, 22);
    }
    g.restore();
  }
  const NESNE = {
    elma: () => elma(0, 0, 1, true),
    deniz: t => {
      g.save(); g.beginPath(); g.arc(0, 0, 140, 0, 7); g.clip();
      g.fillStyle = '#D6F1FF'; g.fillRect(-150, -150, 300, 300);
      ['#64B5F6', '#1E88E5', '#1565C0'].forEach((c, k) => {
        g.fillStyle = c; g.beginPath(); g.moveTo(-160, 160);
        for (let px = -160; px <= 160; px += 10) g.lineTo(px, -20 + k * 45 + Math.sin(px * 0.045 + t * 2.2 + k * 1.6) * 14);
        g.lineTo(160, 160); g.fill();
      });
      g.restore();
      const by = -52 + Math.sin(t * 2.2) * 8;
      g.fillStyle = '#fff'; g.beginPath(); g.moveTo(0, by - 70); g.lineTo(46, by); g.lineTo(0, by); g.fill();
      g.fillStyle = '#8D6E63'; g.beginPath(); g.moveTo(-50, by + 6); g.lineTo(58, by + 6); g.lineTo(40, by + 30); g.lineTo(-34, by + 30); g.fill();
    },
    gunes: t => {
      g.save(); g.rotate(t * 0.5); g.fillStyle = '#FFB300';
      for (let q = 0; q < 12; q++) { g.rotate(Math.PI / 6); g.beginPath(); g.moveTo(-17, -88); g.lineTo(0, -138); g.lineTo(17, -88); g.fill(); }
      g.restore();
      g.fillStyle = '#FDD835'; daire(0, 0, 88);
      g.fillStyle = 'rgba(255,138,128,0.6)'; daire(-50, 22, 13); daire(50, 22, 13);
      yuz(4);
    },
    yaprak: t => {
      g.rotate(0.5 + Math.sin(t * 1.8) * 0.08); g.fillStyle = '#43A047';
      g.beginPath(); g.moveTo(0, -128); g.bezierCurveTo(110, -70, 100, 70, 0, 118); g.bezierCurveTo(-100, 70, -110, -70, 0, -128); g.fill();
      g.strokeStyle = '#A5D6A7'; g.lineWidth = 8; g.lineCap = 'round';
      g.beginPath(); g.moveTo(0, -96); g.lineTo(0, 138); g.stroke(); g.lineWidth = 6;
      for (const yy of [-40, 10, 60]) { g.beginPath(); g.moveTo(0, yy); g.lineTo(46, yy - 30); g.moveTo(0, yy); g.lineTo(-46, yy - 30); g.stroke(); }
    },
    uzum: () => {
      g.strokeStyle = '#6D4C41'; g.lineWidth = 10; g.lineCap = 'round';
      g.beginPath(); g.moveTo(0, -80); g.lineTo(8, -122); g.stroke();
      g.fillStyle = '#66BB6A'; elips(40, -108, 34, 16, -0.4);
      [[-52, -52], [0, -56], [52, -52], [-28, -8], [28, -8], [-52, 34], [0, 36], [52, 34], [-26, 78], [26, 78], [0, 118]].forEach(([x, y], k) => {
        g.fillStyle = k % 2 ? '#8E24AA' : '#7B1FA2'; daire(x, y, 31);
        g.fillStyle = 'rgba(255,255,255,0.35)'; daire(x - 10, y - 10, 8);
      });
    },
    top: () => {
      g.fillStyle = '#FB8C00'; daire(0, 0, 105);
      g.strokeStyle = '#fff'; g.lineWidth = 12; g.beginPath(); g.arc(-150, 0, 150, -0.72, 0.72); g.stroke();
      g.beginPath(); g.arc(150, 0, 150, Math.PI - 0.72, Math.PI + 0.72); g.stroke();
      g.fillStyle = 'rgba(255,255,255,0.4)'; elips(-40, -50, 18, 30, 0.5);
    },
    pencere: () => {
      g.fillStyle = '#8D6E63'; kutu(-108, -108, 216, 216, 14);
      g.fillStyle = '#BBDEFB'; g.fillRect(-90, -90, 180, 180);
      g.fillStyle = '#fff'; elips(-40, -40, 30, 16); elips(30, 34, 26, 13);
      g.fillStyle = '#8D6E63'; g.fillRect(-8, -90, 16, 180); g.fillRect(-90, -8, 180, 16);
    },
    cati: () => {
      g.fillStyle = '#FFE0B2'; g.fillRect(-80, -10, 160, 110);
      g.fillStyle = '#8D6E63'; g.fillRect(-20, 40, 40, 60);
      g.fillStyle = '#E53935'; g.beginPath(); g.moveTo(-115, -6); g.lineTo(0, -118); g.lineTo(115, -6); g.closePath(); g.fill();
    },
    gece: t => {
      g.fillStyle = '#283593'; daire(0, 0, 140);
      g.fillStyle = '#FFF59D'; daire(62, -58, 30); g.fillStyle = '#283593'; daire(76, -66, 26);
      g.fillStyle = '#FDD835';
      [[-70, -50, 22], [-20, 30, 30], [60, 50, 18], [-80, 60, 14], [10, -80, 14]].forEach(([x, y, r], k) => {
        yildizYol(x, y, r * (0.85 + 0.15 * Math.sin(t * 4 + k * 2))); g.fill();
      });
    },
  };

  // ---------- Pıtır ----------
  // d: x,y,s,hop,agiz,bx,by,sag,sol (kol açıları; null=varsayılan),donus(scaleX),egim,kolOnde,nefes
  function pitir(t, d) {
    const s = d.s || 1, hop = d.hop || 0, agiz = d.agiz || 0;
    g.save(); g.translate(d.x, d.y);
    g.fillStyle = 'rgba(60,110,70,0.18)'; elips(0, 6 * s, (150 - hop * 0.5) * s, 22 * s);
    g.translate(0, -hop); g.scale(s * (d.donus === undefined ? 1 : d.donus), s); g.rotate(d.egim || 0);
    const nefes = 1 + Math.sin(t * 2.6) * 0.015 + hop * 0.0012 + (d.nefes || 0);
    g.scale(1 / Math.sqrt(nefes), nefes);
    g.strokeStyle = '#F47A2A'; g.lineWidth = 46; g.lineCap = 'round';
    const ks = Math.sin(t * 2.2) * 18;
    g.beginPath(); g.moveTo(80, -70); g.quadraticCurveTo(190 + ks, -80, 185 + ks, -190); g.stroke();
    g.fillStyle = '#FFE3C2'; daire(185 + ks, -196, 25);
    g.fillStyle = '#E06A1B'; elips(-58, -10, 50, 24); elips(58, -10, 50, 24);
    const kol = (yon, aci, boy = 100) => {
      g.strokeStyle = '#F47A2A'; g.lineWidth = 44; g.lineCap = 'round';
      g.beginPath(); g.moveTo(yon * 100, -178); g.lineTo(yon * (100 + Math.cos(aci) * boy), -178 + Math.sin(aci) * boy); g.stroke();
    };
    const sol = d.sol == null ? 1.05 + Math.sin(t * 2.6) * 0.04 : d.sol;
    const sag = d.sag == null ? 1.15 : d.sag;
    if (!d.kolOnde) kol(-1, sol);
    g.fillStyle = TURUNCU; elips(0, -122, 122, 126);
    g.fillStyle = '#FFE3C2'; elips(0, -100, 76, 86);
    if (!d.kolOnde) kol(1, sag);
    g.save(); g.translate(0, -300); g.rotate(Math.sin(t * 5.5) * 0.035 * agiz + Math.sin(t * 0.9) * 0.02);
    g.fillStyle = TURUNCU; g.strokeStyle = TURUNCU; g.lineWidth = 22; g.lineJoin = 'round';
    for (const yon of [-1, 1]) {
      g.beginPath(); g.moveTo(yon * 132, -52); g.lineTo(yon * 138, -168); g.lineTo(yon * 48, -128); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = '#FFB7A8'; g.beginPath(); g.moveTo(yon * 118, -76); g.lineTo(yon * 122, -140); g.lineTo(yon * 72, -118); g.closePath(); g.fill();
      g.fillStyle = TURUNCU;
    }
    daire(0, 0, 152);
    g.fillStyle = '#FFE3C2'; elips(0, 52, 92, 66);
    g.fillStyle = 'rgba(255,120,130,0.45)'; daire(-104, 34, 24); daire(104, 34, 24);
    const kirp = (t % 3.7) < 0.13 || d.gozKapali, bx = d.bx || 0, by = d.by || 0;
    for (const yon of [-1, 1]) {
      const ex = yon * 60, ey = -22;
      if (kirp) {
        g.strokeStyle = '#3B2A20'; g.lineWidth = 8; g.lineCap = 'round';
        g.beginPath(); g.arc(ex, ey - 6, 26, 0.25, Math.PI - 0.25); g.stroke();
      } else {
        g.fillStyle = '#fff'; elips(ex, ey, 36, 42);
        g.fillStyle = '#3B2A20'; daire(ex + bx * 11, ey + by * 11, 21);
        g.fillStyle = '#fff'; daire(ex + bx * 11 - 7, ey + by * 11 - 8, 7);
      }
    }
    g.fillStyle = '#E2647A'; elips(0, 24, 15, 10);
    if (agiz < 0.1) {
      g.strokeStyle = '#7A2E1D'; g.lineWidth = 7; g.lineCap = 'round';
      g.beginPath(); g.arc(0, 44, 30, 0.25, Math.PI - 0.25); g.stroke();
    } else {
      g.fillStyle = '#7A2E1D'; elips(0, 64, 26 + 8 * agiz, 6 + 28 * agiz);
      g.fillStyle = '#FF8FA3'; elips(0, 64 + 16 * agiz, 15, 3 + 11 * agiz);
    }
    g.restore();
    if (d.kolOnde) { kol(-1, sol, 125); kol(1, sag, 125); }
    g.restore();
  }
  const agizAl = t => ZARF[Math.min(ZARF.length - 1, Math.max(0, Math.round(t * TL.fps)))] || 0;
  const bak = (px, py, hx, hy) => { const dx = hx - px, dy = hy - (py - 320), u = Math.hypot(dx, dy) || 1; return { bx: dx / u, by: dy / u }; };
  const sallaAci = t => -1.15 + Math.sin(t * 9) * 0.38;
  // Soru-cevap turlarında Pıtır'ın ortak davranışı
  function pitirTur(t, b, d = {}) {
    let hop = 0, isaret = 0, hedef = d.hedef || null;
    (b.turlar || []).forEach(r => {
      hop += 55 * zipla(t, r.cevap, 0.5) + 30 * zipla(t, r.cevap + 0.55, 0.4);
      if (t >= r.t && t < r.bit) isaret = yumusak(ilerle(t, r.soru, 0.5)) * (1 - yumusak(ilerle(t, r.bit - 0.8, 0.5)));
    });
    if (b.ozet && b.ozet.vuruslar) b.ozet.vuruslar.forEach(v => { hop += 40 * zipla(t, v, 0.45); });
    const x = d.x || 300, y = d.y || 900;
    const bk = hedef ? bak(x, y, hedef.x, hedef.y) : { bx: 0, by: 0 };
    const giris = b.giris ? gorun(t, b.giris.t, b.giris.t + 2.2, 0.4, 0.5) : 0;
    let sag = ara(1.15, -0.55, isaret);
    if (giris > 0) sag = ara(sag, sallaAci(t), sinirla(giris));
    pitir(t, Object.assign({ x, y, hop, agiz: agizAl(t), sag }, bk, d.ek || {}));
  }

  // ---------- şekiller ----------
  function sekil(tip, x, y, s, renk, kenar, t, yuzlu = true, aci = 0) {
    if (s <= 0.01) return;
    g.save(); g.translate(x, y); g.scale(s, s); g.rotate(aci);
    g.fillStyle = renk; g.strokeStyle = kenar; g.lineWidth = 14; g.lineJoin = 'round';
    let fy = 0;
    if (tip === 'daire') { g.beginPath(); g.arc(0, 0, 150, 0, 7); }
    else if (tip === 'kare') { g.beginPath(); g.roundRect(-140, -140, 280, 280, 10); }
    else if (tip === 'ucgen') { g.beginPath(); g.moveTo(0, -150); g.lineTo(165, 130); g.lineTo(-165, 130); g.closePath(); fy = 40; }
    else { yildizYol(0, 0, 175); fy = 8; }
    g.fill(); g.stroke();
    if (yuzlu) yuz(fy, 1.3);
    g.restore();
  }
  const SEKIL = [
    { tip: 'daire', ad: 'DAİRE', c: '#FB8C00', k: '#BF5B00', nesne: 'top' },
    { tip: 'kare', ad: 'KARE', c: '#1E88E5', k: '#0D47A1', nesne: 'pencere' },
    { tip: 'ucgen', ad: 'ÜÇGEN', c: '#E53935', k: '#B71C1C', nesne: 'cati' },
    { tip: 'yildiz', ad: 'YILDIZ', c: '#FDD835', k: '#F57F17', nesne: 'gece' },
  ];

  // ---------- hayvanlar ----------
  function hayvan(tip, x, y, s, t) {
    if (s <= 0.01) return;
    g.save(); g.translate(x, y); g.scale(s, s); g.rotate(Math.sin(t * 2 + x) * 0.03);
    const goz = (gx, gy, r = 15) => { g.fillStyle = '#fff'; daire(gx, gy, r + 9); g.fillStyle = '#2B2B2B'; daire(gx, gy + 2, r); g.fillStyle = '#fff'; daire(gx - 5, gy - 4, 5); };
    if (tip === 'inek') {
      g.fillStyle = '#fff'; elips(0, 190, 150, 120); g.fillStyle = '#3B3B3B'; elips(60, 170, 55, 40, 0.4);
      g.fillStyle = '#F5E6C8'; g.beginPath(); g.moveTo(-95, -120); g.quadraticCurveTo(-125, -190, -85, -200); g.quadraticCurveTo(-80, -150, -60, -130); g.fill();
      g.beginPath(); g.moveTo(95, -120); g.quadraticCurveTo(125, -190, 85, -200); g.quadraticCurveTo(80, -150, 60, -130); g.fill();
      g.fillStyle = '#fff'; elips(-150, -70, 52, 30, -0.4); elips(150, -70, 52, 30, 0.4);
      g.fillStyle = '#FFB7C5'; elips(-150, -70, 30, 15, -0.4); elips(150, -70, 30, 15, 0.4);
      g.fillStyle = '#fff'; elips(0, -20, 135, 130);
      g.fillStyle = '#3B3B3B'; elips(-70, -80, 55, 48, -0.3); elips(85, -20, 34, 44, 0.2);
      g.fillStyle = '#FFB7C5'; elips(0, 62, 98, 58);
      g.fillStyle = '#C97A8C'; elips(-34, 56, 13, 17); elips(34, 56, 13, 17);
      goz(-52, -36); goz(52, -36);
    } else if (tip === 'koyun') {
      g.fillStyle = '#F7F7F2';
      for (let k = 0; k < 9; k++) daire(Math.cos(k * 0.7) * 110, 190 + Math.sin(k * 0.7) * 70, 62);
      elips(0, 190, 120, 90);
      for (let k = 0; k < 8; k++) daire(Math.cos(k * 0.785 - 3.14) * 105, -50 + Math.sin(k * 0.785 - 3.14) * 100, 50);
      g.fillStyle = '#5D5560'; elips(-125, 0, 45, 24, 0.5); elips(125, 0, 45, 24, -0.5);
      g.fillStyle = '#6B6370'; elips(0, 0, 98, 112);
      g.fillStyle = '#F7F7F2'; daire(-40, -100, 40); daire(0, -112, 44); daire(40, -100, 40);
      goz(-40, -14); goz(40, -14);
      g.fillStyle = '#3F3944'; elips(0, 48, 16, 11);
      g.strokeStyle = '#3F3944'; g.lineWidth = 6; g.lineCap = 'round'; g.beginPath(); g.arc(0, 56, 22, 0.3, Math.PI - 0.3); g.stroke();
    } else if (tip === 'ordek') {
      g.fillStyle = '#FFD93B'; elips(0, 190, 135, 105); g.fillStyle = '#F2C200'; elips(70, 180, 60, 42, -0.3);
      g.fillStyle = '#FFD93B'; daire(0, -10, 118);
      g.beginPath(); g.moveTo(-14, -120); g.quadraticCurveTo(0, -170, 30, -150); g.quadraticCurveTo(10, -140, 14, -118); g.fill();
      g.fillStyle = '#FB8C00'; elips(0, 44, 72, 34); g.fillStyle = '#E67700'; elips(0, 54, 58, 14);
      goz(-46, -30); goz(46, -30);
      g.fillStyle = 'rgba(255,120,130,0.45)'; daire(-86, 14, 18); daire(86, 14, 18);
    } else {
      g.fillStyle = '#B9814F'; elips(0, 190, 135, 110); g.fillStyle = '#F3DFC4'; elips(0, 200, 75, 80);
      g.fillStyle = '#7A4F2B'; elips(-128, -10, 48, 96, 0.25); elips(128, -10, 48, 96, -0.25);
      g.fillStyle = '#B9814F'; elips(0, -20, 125, 120);
      g.fillStyle = '#7A4F2B'; elips(-52, -44, 44, 50);
      g.fillStyle = '#F3DFC4'; elips(0, 44, 76, 58);
      goz(-50, -40); goz(50, -40);
      g.fillStyle = '#2B2B2B'; elips(0, 20, 24, 17);
      g.strokeStyle = '#2B2B2B'; g.lineWidth = 6; g.lineCap = 'round'; g.beginPath(); g.moveTo(0, 36); g.lineTo(0, 54); g.arc(-18, 54, 18, 0, Math.PI); g.moveTo(0, 54); g.arc(18, 54, 18, Math.PI, 0, true); g.stroke();
      g.fillStyle = '#FF7B93'; elips(0, 84, 17, 24);
    }
    g.restore();
  }
  const HAYVAN = [
    { tip: 'inek', ad: 'İNEK', ses: 'Möö!', c: '#EC407A', k: '#880E4F' },
    { tip: 'koyun', ad: 'KOYUN', ses: 'Mee!', c: '#5C6BC0', k: '#1A237E' },
    { tip: 'ordek', ad: 'ÖRDEK', ses: 'Vak vak!', c: '#FB8C00', k: '#BF5B00' },
    { tip: 'kopek', ad: 'KÖPEK', ses: 'Hav hav!', c: '#8D6E63', k: '#3E2723' },
  ];
  function balonKonusma(x, y, metin, olcek, renk = '#37474F') {
    if (olcek <= 0.01) return;
    g.save(); g.translate(x, y); g.scale(olcek, olcek);
    g.font = '700 96px Fredoka'; const gen = Math.max(260, g.measureText(metin).width + 110);
    g.fillStyle = '#fff'; g.strokeStyle = '#B0BEC5'; g.lineWidth = 6;
    g.beginPath(); g.roundRect(-gen / 2, -90, gen, 180, 80); g.fill(); g.stroke();
    g.beginPath(); g.moveTo(-30, 86); g.lineTo(0, 150); g.lineTo(40, 86); g.fill();
    g.fillStyle = renk; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(metin, 0, 6);
    g.restore();
  }

  // ---------- taşıtlar ----------
  function teker(x, y, r, t) {
    g.fillStyle = '#37474F'; daire(x, y, r); g.fillStyle = '#CFD8DC'; daire(x, y, r * 0.5);
    g.strokeStyle = '#37474F'; g.lineWidth = 5;
    for (let k = 0; k < 3; k++) { const a = t * 6 + k * 2.094; g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * r * 0.5, y + Math.sin(a) * r * 0.5); g.stroke(); }
  }
  function tasit(tip, x, y, s, t, hareket = 1) {
    g.save(); g.translate(x, y + Math.abs(Math.sin(t * 9)) * -4 * hareket); g.scale(s, s);
    const tt = t * hareket;
    if (tip === 'araba') {
      g.fillStyle = '#E53935'; kutu(-230, -120, 460, 110, 40);
      g.beginPath(); g.moveTo(-130, -118); g.quadraticCurveTo(-100, -230, 0, -230); g.lineTo(60, -230); g.quadraticCurveTo(130, -225, 170, -118); g.fill();
      g.fillStyle = '#BBDEFB'; g.beginPath(); g.moveTo(-95, -125); g.quadraticCurveTo(-78, -200, -10, -200); g.lineTo(-10, -125); g.fill();
      g.beginPath(); g.moveTo(15, -125); g.lineTo(15, -200); g.lineTo(55, -200); g.quadraticCurveTo(105, -195, 130, -125); g.fill();
      g.fillStyle = '#FFF59D'; elips(-222, -70, 14, 20); g.fillStyle = '#B71C1C'; elips(224, -70, 10, 18);
      teker(-130, -10, 52, tt); teker(130, -10, 52, tt);
    } else if (tip === 'otobus') {
      g.fillStyle = '#FDD835'; kutu(-330, -300, 660, 290, 36);
      g.fillStyle = '#F9A825'; g.fillRect(-330, -110, 660, 26);
      g.fillStyle = '#BBDEFB'; for (let k = 0; k < 5; k++) kutu(-300 + k * 122, -262, 98, 110, 12);
      g.fillStyle = '#FFF59D'; elips(-322, -60, 12, 20);
      teker(-200, -10, 56, tt); teker(200, -10, 56, tt);
    } else if (tip === 'tren') {
      for (let k = 0; k < 2; k++) {
        const wx = 150 + k * 300; g.fillStyle = k ? '#E53935' : '#1E88E5'; kutu(wx - 130, -210, 260, 200, 22);
        g.fillStyle = '#BBDEFB'; kutu(wx - 100, -180, 80, 80, 10); kutu(wx + 20, -180, 80, 80, 10);
        g.fillStyle = '#546E7A'; g.fillRect(wx - 160, -60, 40, 14);
        teker(wx - 70, -10, 40, tt); teker(wx + 70, -10, 40, tt);
      }
      g.fillStyle = '#43A047'; kutu(-290, -180, 300, 170, 24); kutu(-130, -290, 150, 130, 18);
      g.fillStyle = '#BBDEFB'; kutu(-106, -264, 100, 80, 10);
      g.fillStyle = '#2E7D32'; kutu(-250, -270, 60, 100, 8); kutu(-266, -290, 92, 30, 8);
      g.fillStyle = '#FDD835'; daire(-286, -90, 20);
      for (let k = 0; k < 3; k++) { const p = (t * 0.6 + k / 3) % 1; g.fillStyle = `rgba(255,255,255,${0.85 * (1 - p)})`; daire(-220 + p * 150, -310 - p * 170, 28 + p * 40); }
      teker(-220, -10, 46, tt); teker(-110, -10, 46, tt); teker(-20, -10, 46, tt);
    } else {
      g.rotate(Math.sin(t * 1.5) * 0.04);
      g.fillStyle = '#1E88E5'; g.beginPath(); g.moveTo(200, -40); g.lineTo(290, -160); g.lineTo(330, -160); g.lineTo(290, -20); g.fill();
      g.beginPath(); g.moveTo(-40, -30); g.lineTo(90, -170); g.lineTo(150, -170); g.lineTo(80, -30); g.fill();
      g.fillStyle = '#fff'; g.strokeStyle = '#CFD8DC'; g.lineWidth = 6;
      g.beginPath(); g.ellipse(0, 0, 320, 86, 0, 0, 7); g.fill(); g.stroke();
      g.fillStyle = '#1E88E5'; g.beginPath(); g.moveTo(-60, 20); g.lineTo(100, 190); g.lineTo(170, 190); g.lineTo(90, 20); g.fill();
      g.fillStyle = '#BBDEFB'; for (let k = 0; k < 5; k++) daire(-130 + k * 70, -14, 20);
      g.beginPath(); g.moveTo(-300, -10); g.quadraticCurveTo(-270, -52, -220, -52); g.lineTo(-220, -10); g.fill();
      g.fillStyle = '#E53935'; g.fillRect(-120, 34, 300, 12);
    }
    g.restore();
  }
  const TASIT = [
    { tip: 'araba', ad: 'ARABA', c: '#E53935', k: '#B71C1C', y: 930, s: 1.0 },
    { tip: 'otobus', ad: 'OTOBÜS', c: '#FDD835', k: '#F57F17', y: 930, s: 0.95 },
    { tip: 'tren', ad: 'TREN', c: '#43A047', k: '#1B5E20', y: 930, s: 0.85 },
    { tip: 'ucak', ad: 'UÇAK', c: '#1E88E5', k: '#0D47A1', y: 470, s: 0.9 },
  ];

  // ================= SAHNELER =================
  const SAHNE = {};

  SAHNE.tema = (t, b) => {
    arkaPlan(t);
    const dt = t - b.t0;
    for (let i = 0; i < 6; i++) balon(210 + i * 300, H + 300 - ((dt * 170 + i * 260) % (H + 700)), 0.42, RENK[i], t, i);
    notalar(t, b.t0);
    renkliYazi('Pıtır ile Öğren', 960, 210, 180, t, patla(t, b.t0 - 0.3, 0.7));
    const hop = 46 * Math.abs(Math.sin(Math.PI * dt * 2));
    pitir(t, { x: 960, y: 960, s: 1.1, hop, agiz: agizAl(t), egim: Math.sin(Math.PI * dt) * 0.07, sag: sallaAci(t * 0.7), sol: sallaAci(t * 0.7 + 1.5) });
  };

  SAHNE.selam = (t, b) => {
    arkaPlan(t);
    const s = b.giris, sure = s.bit - s.t;
    const ciz = [
      () => { g.scale(0.55, 0.55); balon(0, -40, 1, RENK[0], t); },
      () => buyukYazi('123', 0, 6, 120, RENK[1].c, RENK[1].k),
      () => { sekil('daire', -62, 50, 0.36, SEKIL[0].c, SEKIL[0].k, t, false); sekil('kare', 62, 50, 0.36, SEKIL[1].c, SEKIL[1].k, t, false); sekil('ucgen', 0, -62, 0.4, SEKIL[2].c, SEKIL[2].k, t, false); },
      () => hayvan('inek', 0, -10, 0.62, 0),
    ];
    [0.26, 0.36, 0.45, 0.54].forEach((f, i) => rozet(820 + i * 290, 470, patla(t, s.t + sure * f, 0.45) * 0.78, t, ciz[i]));
    const salla = gorun(t, s.t, s.t + 2.6, 0.4, 0.5);
    pitir(t, { x: 380, y: 930, s: 1.05, hop: 60 * zipla(t, s.t, 0.55) + 50 * zipla(t, s.bit - 1.6, 0.5), agiz: agizAl(t), sag: ara(1.15, sallaAci(t), sinirla(salla)) });
  };

  // --- renkler ---
  const R_MERKEZ = { x: 1010, y: 480 };
  SAHNE.renkler = (t, b) => {
    arkaPlan(t);
    const O = b.ozet, yuva = i => ({ x: 1345 + i * 100, y: 105 }), sira = i => ({ x: 640 + i * 222, y: 540 });
    let hedef = null; const durum = [];
    b.turlar.forEach((r, i) => {
      if (t < r.t) return;
      let x = R_MERKEZ.x, y = ara(H + 420, R_MERKEZ.y, yavasla(ilerle(t, r.t, 2.4))), s = 1 + 0.10 * zipla(t, r.cevap, 0.45);
      const p1 = yumusak(ilerle(t, r.bit - 1.1, 1.0)), y1 = yuva(i);
      x = ara(x, y1.x, p1); y = ara(y, y1.y, p1); s = ara(s, 0.21, p1);
      const p2 = yumusak(ilerle(t, O.t + 0.2 + i * 0.1, 1.2)), s1 = sira(i);
      x = ara(x, s1.x, p2); y = ara(y, s1.y, p2); s = ara(s, 0.5, p2);
      y -= 80 * zipla(t, O.vuruslar[i], 0.5); s *= 1 + 0.18 * zipla(t, O.vuruslar[i], 0.5);
      y -= 40 * zipla(t, O.son + i * 0.1, 0.5);
      y += Math.sin(t * 1.6 + i * 1.7) * 12 * s; x += Math.sin(t * 1.1 + i) * 7 * s;
      durum.push({ i, x, y, s });
      if (t < r.bit) hedef = { x, y };
    });
    b.turlar.forEach((r, i) => {
      if (t < r.t || t > r.bit) return;
      soruIsaretleri(t, r);
      kelime(t, r, RENK[i].ad, RENK[i].c, RENK[i].k, 860, 150);
      const no = gorun(t, r.cevap + (r.cevapBit - r.cevap) * 0.55, r.bit - 0.9);
      if (RENK[i].nesne) rozet(1530, 560, no, t, () => NESNE[RENK[i].nesne](t));
      else if (no > 0) isilti(300, 640, 250 * Math.min(1, no), t, 10);
    });
    durum.forEach(d => balon(d.x, d.y, d.s, RENK[d.i], t, d.i));
    O.vuruslar.forEach((v, i) => {
      const bit = i < 5 ? O.vuruslar[i + 1] : O.son;
      buyukYazi(RENK[i].ad, 1100, 180, 180, RENK[i].c, RENK[i].k, gorun(t, v, bit + 0.1, 0.3, 0.15));
    });
    renkliYazi('6 Renk!', 1100, 180, 190, t, gorun(t, O.son, b.t1 + 1, 0.4, 0.3));
    pitirTur(t, b, { hedef });
  };

  // --- sayılar ---
  function agac(t) {
    g.fillStyle = '#8D6E63'; g.beginPath(); g.moveTo(1520, 960); g.quadraticCurveTo(1560, 700, 1530, 520); g.lineTo(1640, 520); g.quadraticCurveTo(1610, 700, 1660, 960); g.fill();
    g.fillStyle = '#66BB6A';
    [[1420, 420, 170], [1600, 330, 200], [1760, 440, 170], [1500, 270, 150], [1700, 280, 150], [1590, 470, 190]].forEach(([x, y, r], k) => daire(x + Math.sin(t * 1.2 + k) * 4, y, r));
    g.fillStyle = '#81C784'; daire(1540, 300, 80); daire(1700, 400, 70);
  }
  const DAL = [[1430, 430], [1560, 300], [1700, 360], [1790, 470], [1600, 480]];
  SAHNE.sayilar = (t, b) => {
    arkaPlan(t); agac(t);
    const O = b.ozet, SX = 1000, SY = 900, yer = i => ({ x: SX + (i - 2) * 66, y: SY - 92 - (i % 2) * 30 }), sira = i => ({ x: 600 + i * 165, y: 470 });
    g.fillStyle = '#A1764A'; elips(SX, SY - 70, 215, 46);
    b.turlar.forEach((r, i) => {
      const p = ilerle(t, r.t + 0.15, 0.95), a = DAL[i], z = yer(i);
      let x = ara(a[0], z.x, p), y = ara(a[1], z.y, p * p), s = 0.5 + 0.06 * zipla(t, r.cevap + i * 0.0, 0.4), yazi = null;
      y -= 26 * zipla(t, r.t + 1.1, 0.3);
      b.turlar.forEach((r2, j) => { if (j >= i) y -= 22 * zipla(t, r2.cevap + (i * 0.12), 0.35); });
      const p2 = yumusak(ilerle(t, O.vuruslar[i] - 0.25, 0.5)), s1 = sira(i);
      if (p2 > 0) { x = ara(x, s1.x, p2); y = ara(y, s1.y, p2) - 60 * Math.sin(Math.PI * p2); s = ara(s, 0.78, p2); yazi = p2 > 0.6 ? String(i + 1) : null; }
      y -= 40 * zipla(t, O.son + i * 0.1, 0.5);
      elma(x, y + (p2 > 0 ? Math.sin(t * 2 + i) * 6 : 0), s, false, yazi);
    });
    // sepetin ön yüzü
    g.fillStyle = '#C8935A'; g.beginPath(); g.moveTo(SX - 215, SY - 70); g.quadraticCurveTo(SX, SY - 20, SX + 215, SY - 70); g.lineTo(SX + 165, SY + 70); g.quadraticCurveTo(SX, SY + 100, SX - 165, SY + 70); g.closePath(); g.fill();
    g.strokeStyle = '#A1764A'; g.lineWidth = 7;
    for (let k = -3; k <= 3; k++) { g.beginPath(); g.moveTo(SX + k * 56, SY - 46); g.lineTo(SX + k * 44, SY + 84); g.stroke(); }
    g.beginPath(); g.moveTo(SX - 190, SY + 10); g.quadraticCurveTo(SX, SY + 50, SX + 190, SY + 10); g.stroke();
    b.turlar.forEach((r, i) => {
      if (t < r.t || t > r.bit) return;
      soruIsaretleri(t, r, 1250, 330, 700, 300);
      buyukYazi(String(i + 1), 1000, 330, 380, RENK[0].c, RENK[0].k, gorun(t, r.cevap, r.bit - 0.3) * (1 + 0.04 * Math.sin(t * 6)));
    });
    renkliYazi('5 Elma!', 1000, 200, 180, t, gorun(t, O.son, b.t1 + 1, 0.4, 0.3));
    pitirTur(t, b, { hedef: { x: SX, y: SY - 100 } });
  };

  // --- şarkı ---
  SAHNE.sarki = (t, b) => {
    arkaPlan(t);
    if (t < b.sarki) { pitirTur(t, b, { x: 960, ek: { s: 1.1 } }); return; }
    const dt = t - b.sarki, vur = Math.abs(Math.sin(Math.PI * dt * 110 / 60));
    for (let i = 0; i < 6; i++) balon(160 + i * 320, H + 300 - ((dt * 120 + i * 300) % (H + 700)), 0.3, RENK[(i + 3) % 6], t, i + 9);
    notalar(t, b.sarki);
    for (let i = 0; i < 4; i++) {
      const x = i < 2 ? 250 + i * 280 : 1390 + (i - 2) * 280;
      balon(x + Math.sin(dt * 1.1 + i) * 30, 430 + Math.sin(dt * 2.2 + i * 0.9) * 45, 0.6 * (1 + 0.05 * vur), RENK[i], t, i);
    }
    renkliYazi('Balon Şarkısı', 960, 150, 140, t, gorun(t, b.sarki, b.sarki + 5));
    pitir(t, { x: 960, y: 970, s: 1.15, hop: 42 * vur, agiz: agizAl(t), egim: Math.sin(Math.PI * dt * 110 / 120) * 0.07, sag: sallaAci(t * 0.6), sol: sallaAci(t * 0.6 + 1.5) });
  };

  // --- şekiller ---
  SAHNE.sekiller = (t, b) => {
    arkaPlan(t);
    const O = b.ozet, KX = 1010, KY = 900, yuva = i => ({ x: 1380 + i * 130, y: 115 });
    const EV = [{ x: 1640, y: 250, s: 0.75 }, { x: 1010, y: 720, s: 1.15 }, { x: 1010, y: 395, s: 1.42 }, { x: 600, y: 230, s: 0.6 }];
    const sirasi = [1, 2, 0, 3]; // özet cümlesindeki sıra: kare, üçgen, daire, yıldız
    const evde = i => O.vuruslar[sirasi.indexOf(i)];
    let hedef = null; const cizim = [];
    b.turlar.forEach((r, i) => {
      if (t < r.t) return;
      const p0 = yavasla(ilerle(t, r.t + 0.1, 1.5));
      let x = KX, y = ara(KY - 60, 470, p0), s = ara(0.15, 1, p0) * (1 + 0.1 * zipla(t, r.cevap, 0.45)), aci = Math.sin(t * 1.5 + i) * 0.06;
      const p1 = yumusak(ilerle(t, r.bit - 1.1, 1.0)), y1 = yuva(i);
      x = ara(x, y1.x, p1); y = ara(y, y1.y, p1); s = ara(s, 0.3, p1);
      const p2 = yumusak(ilerle(t, evde(i) - 0.2, 0.9)), e = EV[i];
      x = ara(x, e.x, p2); y = ara(y, e.y, p2); s = ara(s, e.s, p2); aci *= 1 - p2;
      if (i === 0 || i === 3) aci += p2 * (i === 0 ? 0 : Math.sin(t * 2) * 0.12);
      cizim.push({ i, x, y, s, aci, yuzlu: p2 < 0.5, ev: p2 });
      if (t < r.bit) hedef = { x, y };
    });
    // sihirli kutu
    const kutuIn = yumusak(ilerle(t, O.t + 0.2, 0.8)) * 360;
    g.save(); g.translate(KX, KY + kutuIn);
    g.fillStyle = '#6A1B9A'; kutu(-150, -90, 300, 190, 18);
    g.fillStyle = '#8E24AA'; kutu(-170, -120, 340, 56, 16);
    g.fillStyle = '#FDD835'; yildizYol(0, 20, 50); g.fill();
    isilti(0, -130, 150, t, 6); g.restore();
    cizim.forEach(d => {
      const S = SEKIL[d.i];
      sekil(S.tip, d.x, d.y, d.s, S.c, S.k, t, d.yuzlu, d.aci);
      if (d.i === 1 && d.ev > 0.95) { // duvara kapı + pencere
        const o = patla(t, evde(1) + 0.75, 0.4);
        g.save(); g.translate(d.x, d.y); g.scale(o, o);
        g.fillStyle = '#8D6E63'; kutu(-45, 20, 90, 140, 10); g.fillStyle = '#FDD835'; daire(24, 96, 8);
        g.fillStyle = '#BBDEFB'; kutu(-125, -110, 90, 90, 8); kutu(35, -110, 90, 90, 8); g.restore();
      }
    });
    b.turlar.forEach((r, i) => {
      if (t < r.t || t > r.bit) return;
      soruIsaretleri(t, r);
      kelime(t, r, SEKIL[i].ad, SEKIL[i].c, SEKIL[i].k, 960, 150);
      rozet(1560, 580, gorun(t, r.cevap + (r.cevapBit - r.cevap) * 0.6, r.bit - 0.9), t, () => NESNE[SEKIL[i].nesne](t));
    });
    renkliYazi('Ne güzel bir ev!', 1010, 110, 120, t, gorun(t, O.son, b.t1 + 1, 0.4, 0.3));
    pitirTur(t, b, { hedef });
  };

  // --- hareket etkinliği ---
  const HAREKET = ['EL ÇIRP!', 'ZIPLA!', 'UÇAK OL!', 'DÖN!', 'NEFES AL'];
  SAHNE.hareket = (t, b) => {
    const r = b.turlar.find(r => t >= r.t && t < r.bit), i = r ? b.turlar.indexOf(r) : -1;
    arkaPlan(t, true, i === 2 ? 14 : 1);
    if (!r) { pitirTur(t, b, { x: 960, ek: { s: 1.2, y: 950 } }); return; }
    const k = yumusak(ilerle(t, r.hareket, 0.4)) * (1 - yumusak(ilerle(t, r.bit - 0.4, 0.4))), dt = t - r.hareket;
    const d = { x: 960, y: 950, s: 1.2, agiz: agizAl(t), hop: 0 };
    if (i === 0) {
      const c = 0.5 - 0.5 * Math.cos(dt * 2 * Math.PI * 3);
      d.kolOnde = true; d.sag = ara(1.15, ara(-1.0, -2.25, c), k); d.sol = d.sag;
      if (k > 0.9 && c > 0.8) isilti(960, 950 - 330 * 1.2, 70, t, 6);
    } else if (i === 1) d.hop = k * 190 * Math.abs(Math.sin(Math.PI * dt / 0.62));
    else if (i === 2) { d.sag = ara(1.15, 0, k); d.sol = d.sag; d.egim = k * Math.sin(dt * 2.2) * 0.22; d.x += k * Math.sin(dt * 1.3) * 260; d.hop = k * (60 + Math.sin(dt * 2.6) * 30); }
    else if (i === 3) { const c = Math.cos(dt * 2 * Math.PI / 1.3); d.donus = ara(1, (c < 0 ? -1 : 1) * Math.max(0.2, Math.abs(c)), k); d.sag = ara(1.15, -0.6, k); d.sol = d.sag; d.hop = k * 20; }
    else {
      const n = 0.5 - 0.5 * Math.cos(dt * 2 * Math.PI / 5.2);
      d.nefes = k * n * 0.09; d.sag = ara(1.15, ara(0.9, -0.3, n), k); d.sol = d.sag; d.gozKapali = k > 0.5;
      g.strokeStyle = `rgba(30,136,229,${0.35 * k})`; g.lineWidth = 16; g.beginPath(); g.arc(960, 600, 300 + n * 130, 0, 7); g.stroke();
    }
    pitir(t, d);
    const R = RENK[[0, 3, 1, 5, 1][i]];
    buyukYazi(HAREKET[i], 960, 150, 170, R.c, R.k, gorun(t, r.t + 0.5, r.bit));
    const kalan = (r.bit - t), adet = Math.ceil(r.bit - r.konusmaBit);
    if (t > r.konusmaBit) for (let q = 0; q < adet; q++) { g.fillStyle = q < kalan ? '#FDD835' : 'rgba(255,255,255,0.7)'; yildizYol(960 + (q - (adet - 1) / 2) * 90, 290, 30); g.fill(); }
  };

  // --- hayvanlar ---
  function ciftlik(t) {
    arkaPlan(t, false);
    g.fillStyle = '#C62828'; g.fillRect(1500, 520, 330, 300);
    g.fillStyle = '#8E1B1B'; g.beginPath(); g.moveTo(1470, 530); g.lineTo(1665, 380); g.lineTo(1860, 530); g.closePath(); g.fill();
    g.fillStyle = '#fff'; g.fillRect(1610, 640, 110, 180); g.fillStyle = '#C62828'; g.fillRect(1622, 652, 86, 168);
    g.strokeStyle = '#fff'; g.lineWidth = 8; g.beginPath(); g.moveTo(1622, 652); g.lineTo(1708, 820); g.moveTo(1708, 652); g.lineTo(1622, 820); g.stroke();
    g.fillStyle = '#fff'; daire(1665, 480, 34); g.fillStyle = '#37474F'; daire(1665, 480, 24);
    g.fillStyle = '#E8D3B0';
    for (let x = 520; x < 1500; x += 130) kutu(x, 760, 26, 150, 8);
    g.fillRect(500, 790, 1010, 22); g.fillRect(500, 850, 1010, 22);
  }
  function cali(x, y, t, salla) {
    g.save(); g.translate(x, y); g.rotate(Math.sin(t * 22) * 0.025 * salla); g.scale(1 + Math.sin(t * 18) * 0.02 * salla, 1);
    g.fillStyle = '#388E3C'; [[-190, 20, 120], [-70, -50, 150], [80, -60, 150], [200, 10, 125], [0, 40, 150]].forEach(([cx, cy, r]) => daire(cx, cy, r));
    g.fillStyle = '#4CAF50'; [[-150, 30, 90], [-40, -30, 110], [100, -30, 105], [190, 40, 80]].forEach(([cx, cy, r]) => daire(cx, cy, r));
    g.fillStyle = '#E53935'; [[-120, -40], [40, -90], [150, 10], [-30, 40]].forEach(([cx, cy]) => daire(cx, cy, 13));
    g.restore();
  }
  SAHNE.hayvanlar = (t, b) => {
    ciftlik(t);
    const CX = 1010, CY = 860, yuva = i => ({ x: 1180 + i * 190, y: 150 });
    let salla = 0, hedef = { x: CX, y: CY - 150 };
    const cizim = [];
    b.turlar.forEach((r, i) => {
      if (t < r.cevap - 0.1) { if (t >= r.soru && t < r.cevap) salla = gorun(t, r.soru + 0.3, r.soruBit - 0.6, 0.3, 0.3); return; }
      const p0 = yavasla(ilerle(t, r.cevap - 0.1, 0.6));
      let x = CX, y = ara(CY + 120, CY - 330, p0) - 30 * zipla(t, r.cevap + 0.6, 0.4), s = 1;
      const p1 = yumusak(ilerle(t, r.bit - 1.1, 1.0)), y1 = yuva(i);
      x = ara(x, y1.x, p1); y = ara(y, y1.y, p1); s = ara(s, 0.36, p1);
      if (b.ozet) { const sure = b.ozet.bit - b.ozet.t; y -= 40 * zipla(t, b.ozet.t + sure * (0.48 + i * 0.07), 0.45); }
      cizim.push({ i, x, y, s, on: p1 > 0.02 });
    });
    cizim.filter(d => !d.on).forEach(d => hayvan(HAYVAN[d.i].tip, d.x, d.y, d.s, t));
    cali(CX, CY, t, salla);
    cizim.filter(d => d.on).forEach(d => hayvan(HAYVAN[d.i].tip, d.x, d.y, d.s, t));
    b.turlar.forEach((r, i) => {
      if (t < r.t || t > r.bit) return;
      balonKonusma(CX + 40, 500, HAYVAN[i].ses, gorun(t, r.soru + 0.5, r.soruBit - 0.7, 0.35, 0.25), HAYVAN[i].k);
      soruIsaretleri(t, r, 1400, 420, 660, 300);
      kelime(t, r, HAYVAN[i].ad, HAYVAN[i].c, HAYVAN[i].k, 800, 150);
    });
    if (b.ozet) balonKonusma(560, 380, 'Miyav!', gorun(t, b.ozet.t + 1.3, b.ozet.t + 3.4, 0.35, 0.25), '#BF5B00');
    pitirTur(t, b, { hedef });
  };

  // --- taşıtlar ---
  function yol(t, ray) {
    arkaPlan(t, false);
    g.fillStyle = '#78909C'; g.fillRect(0, 880, W, 130);
    g.fillStyle = '#B4E3AC'; g.fillRect(0, 1010, W, 70);
    if (ray > 0) {
      g.globalAlpha = ray; g.fillStyle = '#6D4C41'; for (let x = 0; x < W; x += 70) g.fillRect(x, 925, 30, 70);
      g.fillStyle = '#CFD8DC'; g.fillRect(0, 935, W, 12); g.fillRect(0, 975, W, 12); g.globalAlpha = 1;
    }
    if (ray < 1) { g.globalAlpha = 1 - ray; g.fillStyle = '#fff'; for (let x = 30; x < W; x += 180) g.fillRect(x, 938, 90, 14); g.globalAlpha = 1; }
  }
  SAHNE.tasitlar = (t, b) => {
    const tr = b.turlar[2];
    yol(t, gorun(t, tr.t - 0.5, tr.bit + 0.3, 0.5, 0.5) > 0 ? sinirla(gorun(t, tr.t - 0.5, tr.bit + 0.3, 0.5, 0.5)) : 0);
    let hedef = null;
    pitirTur(t, b, { x: 250, y: 870, ek: { s: 0.85 }, hedef: (() => { const r = b.turlar.find(r => t >= r.t && t < r.bit); return r ? { x: 1100, y: TASIT[b.turlar.indexOf(r)].y - 150 } : null; })() });
    b.turlar.forEach((r, i) => {
      if (t < r.t || t > r.bit + 0.2) return;
      const T = TASIT[i], gir = yavasla(ilerle(t, r.t + 0.2, 2.4)), cik = Math.pow(ilerle(t, r.bit - 1.3, 1.5), 2);
      const x = ara(W + 700, 1130, gir) - cik * 2000;
      tasit(T.tip, x, T.y - 40 * zipla(t, r.cevap, 0.45), T.s, t, gir < 0.98 || cik > 0 ? 1 : 0.15);
      soruIsaretleri(t, r, 1560, 250, 640, 260);
      kelime(t, r, T.ad, T.c, T.k, 1000, 150);
    });
    if (b.ozet && t >= b.ozet.t) {
      const sure = b.ozet.bit + 1.2 - b.ozet.t;
      TASIT.forEach((T, i) => {
        const p = ilerle(t, b.ozet.t + i * sure * 0.13, sure * 0.6);
        if (p > 0 && p < 1) tasit(T.tip, ara(W + 600, -700, p), T.y, T.s * 0.8, t, 1);
      });
    }
  };

  // --- hafıza oyunu ---
  SAHNE.oyun = (t, b) => {
    arkaPlan(t);
    const yer = i => ({ x: 720 + i * 270, y: 480 });
    let perde = 0, r0 = b.turlar.find(r => t >= r.t && t < r.bit);
    for (let i = 0; i < 4; i++) {
      let p = yer(i), y = p.y, s = 0.62 * patla(t, b.giris.t + 0.3 + i * 0.25, 0.5), gizli = false;
      b.turlar.forEach(r => {
        if (r.eksik !== i) return;
        const kapa = r.soru + 1.0, don = r.cevap;
        if (t >= kapa + 0.45 && t < don) gizli = true;
        if (t >= don) { y = ara(-400, p.y, geri(ilerle(t, don, 0.7))); if (t < don + 2.2) isilti(p.x, p.y, 190, t, 8); }
      });
      if (!gizli) balon(p.x + Math.sin(t * 1.1 + i) * 6, y + Math.sin(t * 1.6 + i * 1.7) * 10, s, RENK[i], t, i);
    }
    b.turlar.forEach(r => {
      const kapa = r.soru + 1.0, ac = r.soruBit - 1.8;
      perde = Math.max(perde, yumusak(ilerle(t, kapa, 0.45)) * (1 - yumusak(ilerle(t, ac, 0.45))));
      if (t >= r.t && t <= r.bit) {
        const p = yer(r.eksik), o = gorun(t, r.soruBit + 0.1, r.cevap, 0.4, 0.25);
        buyukYazi('?', p.x, p.y + Math.sin(t * 3) * 14, 300, MOR.c, MOR.k, o, Math.sin(t * 2.4) * 0.15);
        kelime(t, r, RENK[r.eksik].ad, RENK[r.eksik].c, RENK[r.eksik].k, 1120, 150);
      }
    });
    pitirTur(t, b, { hedef: r0 ? yer(r0.eksik) : null, ek: { gozKapali: perde > 0.5 } });
    if (perde > 0) {
      const gen = perde * (W / 2 + 40);
      g.fillStyle = '#7E57C2'; g.fillRect(0, 0, gen, H); g.fillRect(W - gen, 0, gen, H);
      g.fillStyle = '#673AB7'; for (let k = 0; k < 6; k++) { g.fillRect(gen - 40 - k * 170, 0, 16, H); g.fillRect(W - gen + 24 + k * 170, 0, 16, H); }
      g.fillStyle = '#FDD835'; for (let k = 0; k < 8; k++) { yildizYol(gen - 150 - (k % 4) * 220, 160 + Math.floor(k / 4) * 620 + (k % 2) * 120, 34); g.fill(); yildizYol(W - gen + 150 + (k % 4) * 220, 260 + Math.floor(k / 4) * 520 + (k % 2) * 100, 34); g.fill(); }
      if (perde > 0.9) {
        g.strokeStyle = '#fff'; g.lineWidth = 22; g.lineCap = 'round';
        g.beginPath(); g.arc(780, 500, 110, 0.2, Math.PI - 0.2); g.stroke(); g.beginPath(); g.arc(1140, 500, 110, 0.2, Math.PI - 0.2); g.stroke();
      }
    }
  };

  // --- kapanış ---
  SAHNE.kapanis = (t, b) => {
    arkaPlan(t);
    const s = b.giris, dt = t - b.sarki;
    konfeti(t, s.t + 0.5);
    if (t < b.sarki) {
      renkliYazi('Aferin!', 1150, 300, 230, t, gorun(t, s.t + 0.3, b.sarki + 1, 0.5, 0.4));
      pitir(t, { x: 480, y: 940, s: 1.1, hop: 60 * zipla(t, s.t, 0.55) + 60 * zipla(t, s.bit - 4, 0.5), agiz: agizAl(t), sag: ara(1.15, sallaAci(t), yumusak(ilerle(t, s.bit - 3.2, 0.5))) });
      return;
    }
    for (let i = 0; i < 6; i++) balon(210 + i * 300, H + 300 - ((dt * 170 + i * 260) % (H + 700)), 0.42, RENK[i], t, i);
    renkliYazi('Hoşça kalın!', 960, 210, 180, t, patla(t, b.sarki, 0.6));
    pitir(t, { x: 960, y: 960, s: 1.1, hop: 46 * Math.abs(Math.sin(Math.PI * dt * 2)), agiz: agizAl(t), egim: Math.sin(Math.PI * dt) * 0.07, sag: sallaAci(t), sol: sallaAci(t * 0.7 + 1.5) });
  };

  // ---------- ana kare ----------
  const B = TL.bolumler;
  window.kareCiz = function (t) {
    const b = B.find(b => t >= b.t0 && t < b.t1) || B[B.length - 1];
    SAHNE[b.tip](t, b);
    if (b.baslik && b.giris) {
      const son = b.tip === 'sarki' ? b.sarki : b.giris.bit + 0.3;
      renkliYazi(b.baslik, 1010, b.tip === 'hareket' || b.tip === 'sarki' ? 170 : 300, 170, t, gorun(t, b.t0 + 0.5, son, 0.5, 0.35));
    }
    // bölüm geçişi: renkli daire kapanıp açılır
    B.forEach((x, k) => {
      if (k === 0) return;
      const p = 1 - Math.abs(t - x.t0) / 0.55;
      if (p > 0) { g.fillStyle = RENK[k % 6].c; daire(W / 2, H / 2, yumusak(p) * 1150); g.fillStyle = RENK[k % 6].a; daire(W / 2, H / 2, yumusak(p) * 1150 - 40 > 0 ? yumusak(p) * 1150 - 40 : 0); }
    });
    const son = ilerle(t, TL.sure - 1.0, 1.0);
    if (son > 0) { g.fillStyle = `rgba(255,255,255,${son})`; g.fillRect(0, 0, W, H); }
  };
})();
