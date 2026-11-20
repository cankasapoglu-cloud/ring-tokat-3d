// "Pıtır ile Renkler" — Bölüm 1 sahnesi.
// Tüm çizim t (saniye) değerinin saf fonksiyonudur: window.kareCiz(t).
// TL (zaman.json) ve ZARF (zarf.json) render.mjs tarafından enjekte edilir.
(() => {
  const W = 1920, H = 1080;
  const TL = window.TL, ZARF = window.ZARF || [];
  const cv = document.getElementById('c');
  const g = cv.getContext('2d');

  const sinirla = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const ara = (a, b, p) => a + (b - a) * p;
  const ilerle = (t, t0, d) => sinirla((t - t0) / d);
  const yumusak = x => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  const yavasla = x => 1 - Math.pow(1 - x, 3);
  const geri = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const patla = (t, t0, d = 0.5) => { const p = ilerle(t, t0, d); return p <= 0 ? 0 : geri(p); };
  const zipla = (t, t0, d = 0.5) => Math.sin(Math.PI * ilerle(t, t0, d));
  const rasgele = k => { const x = Math.sin(k * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

  const RENK = [
    { ad: 'KIRMIZI', c: '#E53935', a: '#FF8A80', k: '#B71C1C', nesne: 'elma' },
    { ad: 'MAVİ', c: '#1E88E5', a: '#90CAF9', k: '#0D47A1', nesne: 'deniz' },
    { ad: 'SARI', c: '#FDD835', a: '#FFF59D', k: '#F57F17', nesne: 'gunes' },
    { ad: 'YEŞİL', c: '#43A047', a: '#A5D6A7', k: '#1B5E20', nesne: 'yaprak' },
  ];
  const TURUNCU = '#FF8A3D';
  const P = TL.tur, SAY = TL.sayma, KAP = TL.kapanis;
  const MERKEZ = { x: 1010, y: 480 };
  const yuva = i => ({ x: 1490 + i * 118, y: 118 });
  const sira = i => ({ x: 770 + i * 300, y: 520 });

  // ---------- arka plan ----------
  function bulut(x, y, s) {
    g.save(); g.translate(x, y); g.scale(s, s);
    g.fillStyle = 'rgba(255,255,255,0.92)';
    for (const [cx, cy, r] of [[-70, 10, 50], [-20, -20, 65], [45, -5, 55], [95, 15, 40], [10, 25, 60]]) {
      g.beginPath(); g.arc(cx, cy, r, 0, 7); g.fill();
    }
    g.restore();
  }
  function cicek(x, y, renk, t, k) {
    const sal = Math.sin(t * 1.4 + k) * 0.08;
    g.save(); g.translate(x, y); g.rotate(sal);
    g.strokeStyle = '#6DBE6A'; g.lineWidth = 6; g.lineCap = 'round';
    g.beginPath(); g.moveTo(0, 0); g.lineTo(0, -46); g.stroke();
    g.translate(0, -52); g.fillStyle = renk;
    for (let p = 0; p < 5; p++) { g.beginPath(); g.arc(Math.cos(p * 1.2566) * 13, Math.sin(p * 1.2566) * 13, 10, 0, 7); g.fill(); }
    g.fillStyle = '#FFF3C4'; g.beginPath(); g.arc(0, 0, 8, 0, 7); g.fill();
    g.restore();
  }
  function arkaPlan(t) {
    const gok = g.createLinearGradient(0, 0, 0, H);
    gok.addColorStop(0, '#BDE7FF'); gok.addColorStop(0.7, '#EAF8FF'); gok.addColorStop(1, '#F7FCFF');
    g.fillStyle = gok; g.fillRect(0, 0, W, H);
    const bl = [[200, 170, 1.2, 9], [900, 300, 0.8, 6], [1450, 330, 1.0, 11], [1750, 560, 0.7, 7]];
    bl.forEach(([x, y, s, v]) => bulut(((x + t * v + 300) % (W + 600)) - 300, y, s));
    g.fillStyle = '#D5F0CC';
    g.beginPath(); g.moveTo(0, 860); g.quadraticCurveTo(480, 700, 960, 850); g.quadraticCurveTo(1500, 990, W, 800); g.lineTo(W, H); g.lineTo(0, H); g.fill();
    g.fillStyle = '#B4E3AC';
    g.beginPath(); g.moveTo(0, 930); g.quadraticCurveTo(500, 850, 1000, 940); g.quadraticCurveTo(1500, 1020, W, 930); g.lineTo(W, H); g.lineTo(0, H); g.fill();
    const cc = ['#FFB3D1', '#FFFFFF', '#D9B8FF', '#FFB3D1', '#FFFFFF', '#D9B8FF', '#FFB3D1'];
    [80, 610, 820, 1130, 1380, 1640, 1850].forEach((x, k) => cicek(x, 1010 + (k % 3) * 22, cc[k], t, k));
  }

  // ---------- balon ----------
  function balon(x, y, s, r, t, k, yazi) {
    g.save(); g.translate(x, y); g.scale(s, s); g.rotate(Math.sin(t * 1.3 + k * 2) * 0.05);
    g.strokeStyle = '#8D99A6'; g.lineWidth = 5; g.lineCap = 'round';
    g.beginPath(); g.moveTo(0, 222);
    for (let q = 1; q <= 12; q++) g.lineTo(Math.sin(q * 0.9 + t * 2 + k) * 12, 222 + q * 20);
    g.stroke();
    g.fillStyle = r.k; g.beginPath(); g.moveTo(0, 198); g.lineTo(-20, 232); g.lineTo(20, 232); g.closePath(); g.fill();
    const gr = g.createRadialGradient(-60, -80, 20, 0, 0, 230);
    gr.addColorStop(0, r.a); gr.addColorStop(0.55, r.c); gr.addColorStop(1, r.k);
    g.fillStyle = gr; g.beginPath(); g.ellipse(0, 0, 172, 205, 0, 0, 7); g.fill();
    g.fillStyle = 'rgba(255,255,255,0.55)';
    g.beginPath(); g.ellipse(-72, -95, 28, 52, 0.5, 0, 7); g.fill();
    if (yazi) {
      g.font = '700 230px Fredoka'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.lineJoin = 'round'; g.strokeStyle = r.k; g.lineWidth = 26; g.strokeText(yazi, 0, 14);
      g.fillStyle = '#fff'; g.fillText(yazi, 0, 14);
    }
    g.restore();
  }
  function balonDurum(i, t) {
    const T = TL.turlar[i].t;
    if (t < T) return null;
    let x = MERKEZ.x, y = ara(H + 420, MERKEZ.y, yavasla(ilerle(t, T, 2.6))), s = 1;
    s *= 1 + 0.10 * zipla(t, T + P.cevap, 0.45);
    const y1 = yuva(i), p1 = yumusak(ilerle(t, T + P.tasi, 1.1));
    x = ara(x, y1.x, p1); y = ara(y, y1.y, p1); s = ara(s, 0.27, p1);
    const s1 = sira(i), p2 = yumusak(ilerle(t, SAY.t + 0.15 + i * 0.12, 1.2));
    x = ara(x, s1.x, p2); y = ara(y, s1.y, p2); s = ara(s, 0.62, p2);
    y -= 70 * zipla(t, SAY.t + SAY.vuruslar[i], 0.5);
    s *= 1 + 0.12 * zipla(t, SAY.t + SAY.vuruslar[i], 0.5);
    y -= 35 * zipla(t, SAY.t + SAY.son + 0.3 + i * 0.12, 0.5);
    y -= 80 * zipla(t, KAP.t + KAP.renkler[i], 0.5);
    s *= 1 + 0.15 * zipla(t, KAP.t + KAP.renkler[i], 0.5);
    y += Math.sin(t * 1.6 + i * 1.7) * 12 * s; x += Math.sin(t * 1.1 + i) * 7 * s;
    let yazi = null;
    if (t >= SAY.t + SAY.vuruslar[i] && t < KAP.t - 0.2) yazi = String(i + 1);
    return { x, y, s, yazi };
  }

  // ---------- yazı ----------
  function buyukYazi(metin, x, y, boy, dolgu, kenar, olcek = 1, aci = 0) {
    if (olcek <= 0) return;
    g.save(); g.translate(x, y); g.rotate(aci); g.scale(olcek, olcek);
    g.font = `700 ${boy}px Fredoka`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineJoin = 'round';
    g.strokeStyle = kenar; g.lineWidth = boy * 0.26; g.strokeText(metin, 0, 0);
    g.strokeStyle = '#fff'; g.lineWidth = boy * 0.15; g.strokeText(metin, 0, 0);
    g.fillStyle = dolgu; g.fillText(metin, 0, 0);
    g.restore();
  }
  function renkliYazi(metin, x, y, boy, t, olcek = 1) {
    if (olcek <= 0) return;
    g.save(); g.translate(x, y); g.scale(olcek, olcek);
    g.font = `700 ${boy}px Fredoka`; g.textBaseline = 'middle'; g.textAlign = 'left'; g.lineJoin = 'round';
    const palet = [RENK[0], RENK[1], { c: '#FB8C00', k: '#BF5B00' }, RENK[3], { c: '#8E24AA', k: '#4A148C' }];
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

  // ---------- nesneler ----------
  function yuz(y = 0) {
    g.fillStyle = '#3B2A20';
    g.beginPath(); g.arc(-26, y - 8, 9, 0, 7); g.arc(26, y - 8, 9, 0, 7); g.fill();
    g.strokeStyle = '#3B2A20'; g.lineWidth = 6; g.lineCap = 'round';
    g.beginPath(); g.arc(0, y + 8, 22, 0.2, Math.PI - 0.2); g.stroke();
  }
  function nesne(tur, x, y, olcek, t) {
    if (olcek <= 0) return;
    g.save(); g.translate(x, y + Math.sin(t * 2) * 8); g.scale(olcek, olcek);
    g.fillStyle = 'rgba(255,255,255,0.9)'; g.beginPath(); g.arc(0, 0, 165, 0, 7); g.fill();
    g.strokeStyle = 'rgba(120,160,190,0.35)'; g.lineWidth = 6; g.stroke();
    if (tur === 'elma') {
      g.fillStyle = '#E53935';
      g.beginPath(); g.ellipse(-36, 12, 68, 82, 0.12, 0, 7); g.ellipse(36, 12, 68, 82, -0.12, 0, 7); g.fill();
      g.strokeStyle = '#6D4C41'; g.lineWidth = 10; g.lineCap = 'round';
      g.beginPath(); g.moveTo(0, -58); g.quadraticCurveTo(4, -88, 18, -100); g.stroke();
      g.fillStyle = '#66BB6A'; g.beginPath(); g.ellipse(42, -92, 30, 14, -0.5, 0, 7); g.fill();
      g.fillStyle = 'rgba(255,255,255,0.5)'; g.beginPath(); g.ellipse(-58, -22, 12, 24, 0.4, 0, 7); g.fill();
      yuz(22);
    } else if (tur === 'deniz') {
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
    } else if (tur === 'gunes') {
      g.save(); g.rotate(t * 0.5); g.fillStyle = '#FFB300';
      for (let q = 0; q < 12; q++) { g.rotate(Math.PI / 6); g.beginPath(); g.moveTo(-17, -88); g.lineTo(0, -138); g.lineTo(17, -88); g.fill(); }
      g.restore();
      g.fillStyle = '#FDD835'; g.beginPath(); g.arc(0, 0, 88, 0, 7); g.fill();
      g.fillStyle = 'rgba(255,138,128,0.6)'; g.beginPath(); g.arc(-50, 22, 13, 0, 7); g.arc(50, 22, 13, 0, 7); g.fill();
      yuz(4);
    } else {
      g.rotate(0.5 + Math.sin(t * 1.8) * 0.08);
      g.fillStyle = '#43A047';
      g.beginPath(); g.moveTo(0, -128); g.bezierCurveTo(110, -70, 100, 70, 0, 118); g.bezierCurveTo(-100, 70, -110, -70, 0, -128); g.fill();
      g.strokeStyle = '#A5D6A7'; g.lineWidth = 8; g.lineCap = 'round';
      g.beginPath(); g.moveTo(0, -96); g.lineTo(0, 138); g.stroke();
      g.lineWidth = 6;
      for (const yy of [-40, 10, 60]) { g.beginPath(); g.moveTo(0, yy); g.lineTo(46, yy - 30); g.moveTo(0, yy); g.lineTo(-46, yy - 30); g.stroke(); }
    }
    g.restore();
  }

  // ---------- Pıtır ----------
  function pitir(t, d) {
    g.save(); g.translate(d.x, d.y - d.hop);
    const nefes = 1 + Math.sin(t * 2.6) * 0.015 + d.hop * 0.0012;
    g.scale(1 / nefes, nefes);
    g.fillStyle = 'rgba(60,110,70,0.18)';
    g.save(); g.translate(0, d.hop); g.beginPath(); g.ellipse(0, 6, 150 - d.hop * 0.5, 22, 0, 0, 7); g.fill(); g.restore();
    // kuyruk
    g.strokeStyle = '#F47A2A'; g.lineWidth = 46; g.lineCap = 'round';
    const ks = Math.sin(t * 2.2) * 18;
    g.beginPath(); g.moveTo(80, -70); g.quadraticCurveTo(190 + ks, -80, 185 + ks, -190); g.stroke();
    g.fillStyle = '#FFE3C2'; g.beginPath(); g.arc(185 + ks, -196, 25, 0, 7); g.fill();
    // ayaklar
    g.fillStyle = '#E06A1B';
    g.beginPath(); g.ellipse(-58, -10, 50, 24, 0, 0, 7); g.ellipse(58, -10, 50, 24, 0, 0, 7); g.fill();
    // sol kol
    g.strokeStyle = '#F47A2A'; g.lineWidth = 44;
    g.beginPath(); g.moveTo(-100, -175); g.lineTo(-138, -105 + Math.sin(t * 2.6) * 4); g.stroke();
    // gövde
    g.fillStyle = TURUNCU; g.beginPath(); g.ellipse(0, -122, 122, 126, 0, 0, 7); g.fill();
    g.fillStyle = '#FFE3C2'; g.beginPath(); g.ellipse(0, -100, 76, 86, 0, 0, 7); g.fill();
    // sağ kol (işaret / el sallama)
    let aci = ara(1.15, -0.55, d.isaret);
    if (d.salla > 0) aci = ara(aci, -1.15 + Math.sin(t * 9) * 0.38, d.salla);
    g.strokeStyle = '#F47A2A'; g.lineWidth = 44;
    g.beginPath(); g.moveTo(100, -178); g.lineTo(100 + Math.cos(aci) * 100, -178 + Math.sin(aci) * 100); g.stroke();
    // baş
    g.save(); g.translate(0, -300); g.rotate(Math.sin(t * 5.5) * 0.035 * d.agiz + Math.sin(t * 0.9) * 0.02);
    g.fillStyle = TURUNCU; g.strokeStyle = TURUNCU; g.lineWidth = 22; g.lineJoin = 'round';
    for (const yon of [-1, 1]) {
      g.beginPath(); g.moveTo(yon * 132, -52); g.lineTo(yon * 138, -168); g.lineTo(yon * 48, -128); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = '#FFB7A8'; g.beginPath(); g.moveTo(yon * 118, -76); g.lineTo(yon * 122, -140); g.lineTo(yon * 72, -118); g.closePath(); g.fill();
      g.fillStyle = TURUNCU;
    }
    g.beginPath(); g.arc(0, 0, 152, 0, 7); g.fill();
    g.fillStyle = '#FFE3C2'; g.beginPath(); g.ellipse(0, 52, 92, 66, 0, 0, 7); g.fill();
    g.fillStyle = 'rgba(255,120,130,0.45)'; g.beginPath(); g.arc(-104, 34, 24, 0, 7); g.arc(104, 34, 24, 0, 7); g.fill();
    // gözler
    const kirp = (t % 3.7) < 0.13;
    for (const yon of [-1, 1]) {
      const ex = yon * 60, ey = -22;
      if (kirp) {
        g.strokeStyle = '#3B2A20'; g.lineWidth = 8; g.lineCap = 'round';
        g.beginPath(); g.arc(ex, ey - 6, 26, 0.25, Math.PI - 0.25); g.stroke();
      } else {
        g.fillStyle = '#fff'; g.beginPath(); g.ellipse(ex, ey, 36, 42, 0, 0, 7); g.fill();
        g.fillStyle = '#3B2A20'; g.beginPath(); g.arc(ex + d.bx * 11, ey + d.by * 11, 21, 0, 7); g.fill();
        g.fillStyle = '#fff'; g.beginPath(); g.arc(ex + d.bx * 11 - 7, ey + d.by * 11 - 8, 7, 0, 7); g.fill();
      }
    }
    // burun + ağız
    g.fillStyle = '#E2647A'; g.beginPath(); g.ellipse(0, 24, 15, 10, 0, 0, 7); g.fill();
    if (d.agiz < 0.1) {
      g.strokeStyle = '#7A2E1D'; g.lineWidth = 7; g.lineCap = 'round';
      g.beginPath(); g.arc(0, 44, 30, 0.25, Math.PI - 0.25); g.stroke();
    } else {
      g.fillStyle = '#7A2E1D'; g.beginPath(); g.ellipse(0, 64, 26 + 8 * d.agiz, 6 + 28 * d.agiz, 0, 0, 7); g.fill();
      g.fillStyle = '#FF8FA3'; g.beginPath(); g.ellipse(0, 64 + 16 * d.agiz, 15, 3 + 11 * d.agiz, 0, 0, 7); g.fill();
    }
    g.restore();
    g.restore();
  }

  function soruIsareti(x, y, boy, t, k, olcek) {
    buyukYazi('?', x, y + Math.sin(t * 3 + k) * 14, boy, '#8E24AA', '#4A148C', olcek, Math.sin(t * 2.4 + k) * 0.18);
  }

  function konfeti(t) {
    const dt = t - KAP.t; if (dt < 0) return;
    const renkler = [RENK[0].c, RENK[1].c, RENK[2].c, RENK[3].c, '#FB8C00', '#8E24AA'];
    for (let k = 0; k < 150; k++) {
      const hiz = 220 + rasgele(k) * 200;
      const y = -60 - rasgele(k + 500) * 1300 + dt * hiz;
      if (y < -40 || y > H + 40) continue;
      const x = rasgele(k + 900) * W + Math.sin(t * 2 + k) * 36;
      g.save(); g.translate(x, y); g.rotate(t * (2 + rasgele(k + 70) * 3) + k);
      g.fillStyle = renkler[k % renkler.length];
      g.fillRect(-11, -7 * Math.abs(Math.cos(t * 4 + k)) - 1, 22, 14 * Math.abs(Math.cos(t * 4 + k)) + 2);
      g.restore();
    }
  }

  // ---------- ana kare ----------
  window.kareCiz = function (t) {
    arkaPlan(t);

    // giriş: arkadan yükselen mini balonlar + başlık
    if (t < 9) {
      for (let i = 0; i < 4; i++) balon(720 + i * 290, H + 260 - t * 190 - (i % 2) * 110, 0.42, RENK[i], t, i + 5);
      const cik = 1 - yumusak(ilerle(t, 8.2, 0.7));
      renkliYazi('Pıtır ile Renkler', 1010, 250 - (1 - cik) * 420, 150, t, patla(t, -0.35, 0.7));
    }

    // aktif tur
    let hedef = null, isaret = 0, hop = 0;
    hop += 60 * zipla(t, 0.9, 0.55) + 40 * zipla(t, 6.6, 0.5);
    TL.turlar.forEach((tur, i) => {
      const T = tur.t, r = RENK[i];
      if (t >= T && t < T + P.tasi + 1.2) {
        const b = balonDurum(i, t); hedef = b;
        isaret = Math.max(isaret, yumusak(ilerle(t, T + 0.4, 0.5)) * (1 - yumusak(ilerle(t, T + P.tasi - 0.3, 0.5))));
      }
      hop += 55 * zipla(t, T + P.cevap, 0.5) + 30 * zipla(t, T + P.cevap + 0.55, 0.4);
      if (t >= T + P.dusun && t < T + P.cevap + 0.3) {
        const o = patla(t, T + P.dusun, 0.4) * (1 - ilerle(t, T + P.cevap - 0.05, 0.25));
        soruIsareti(1420, 300, 260, t, 0, o); soruIsareti(650, 240, 180, t, 2, o * 0.95);
      }
      if (t >= T + P.cevap && t < T + P.tasi + 0.8) {
        const o = patla(t, T + P.cevap, 0.45) * (1 - yumusak(ilerle(t, T + P.tasi + 0.1, 0.5)));
        buyukYazi(r.ad, 990, 150, 176, r.c, r.k, o * (1 + 0.04 * Math.sin(t * 6)));
        const no = patla(t, T + P.nesne, 0.45) * (1 - yumusak(ilerle(t, T + P.tasi, 0.5)));
        nesne(r.nesne, 1530, 560, no, t);
      }
    });

    // balonlar
    TL.turlar.forEach((tur, i) => { const b = balonDurum(i, t); if (b) balon(b.x, b.y, b.s, RENK[i], t, i, b.yazi); });

    // sayma
    if (t >= SAY.t && t < KAP.t) {
      SAY.vuruslar.forEach((v, i) => {
        const bas = SAY.t + v, bit = i < 3 ? SAY.t + SAY.vuruslar[i + 1] : KAP.t - 0.4;
        if (t >= bas && t < bit + 0.2) {
          const o = patla(t, bas, 0.4) * (1 - ilerle(t, bit, 0.2));
          buyukYazi(String(i + 1), 1220, 190, 250, RENK[i].c, RENK[i].k, o);
        }
        hop += 45 * zipla(t, bas, 0.45);
      });
    }

    // kapanış
    if (t >= KAP.t) {
      konfeti(t);
      const a1 = patla(t, KAP.t, 0.5) * (1 - yumusak(ilerle(t, KAP.t + KAP.veda - 0.4, 0.4)));
      renkliYazi('AFERİN!', 1220, 190, 210, t, a1);
      renkliYazi('Hoşça kalın!', 1220, 190, 170, t, patla(t, KAP.t + KAP.veda, 0.5));
      hop += 70 * zipla(t, KAP.t, 0.55) + 50 * zipla(t, KAP.t + 0.6, 0.5);
      KAP.renkler.forEach(v => { hop += 25 * zipla(t, KAP.t + v, 0.4); });
    }

    // Pıtır
    const px = 330, py = 900;
    let bx = 0, by = 0;
    if (hedef) { const dx = hedef.x - px, dy = hedef.y - (py - 320), u = Math.hypot(dx, dy) || 1; bx = dx / u; by = dy / u; }
    else if (t >= SAY.t && t < KAP.t) { bx = 0.8; by = -0.2; }
    const salla = Math.max(yumusak(ilerle(t, 1.0, 0.4)) * (1 - yumusak(ilerle(t, 3.2, 0.5))),
      yumusak(ilerle(t, KAP.t + KAP.veda, 0.4)));
    const kare = Math.min(ZARF.length - 1, Math.max(0, Math.round(t * TL.fps)));
    pitir(t, { x: px, y: py, hop, agiz: ZARF[kare] || 0, bx, by, isaret, salla });

    // açılış / kapanış geçişi
    const son = ilerle(t, TL.sure - 1.0, 1.0);
    if (son > 0) { g.fillStyle = `rgba(255,255,255,${son})`; g.fillRect(0, 0, W, H); }
  };
})();
