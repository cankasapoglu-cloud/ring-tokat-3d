// "Pıtır ile Öğren" — uzun bölüm, 3D görselli sahneler.
// Zamanlama ve ses uzun-01 ile aynıdır; çizim 3d/hazir/ içindeki görsellerle yapılır.
// window.hazirla(adlar, kok) görselleri yükler, window.kareCiz(t) bir kare çizer.
(() => {
  const W = 1920, H = 1080;
  const TL = window.TL, ZARF = window.ZARF || [], AYAR = window.AYAR || {};
  const g = document.getElementById('c').getContext('2d');
  g.imageSmoothingQuality = 'high';
  const IMG = {};
  window.hazirla = (adlar, kok) => Promise.all(adlar.map(a => new Promise((res, rej) => {
    const i = new Image(); i.onload = () => { IMG[a] = i; res(); }; i.onerror = () => rej(new Error('yüklenemedi: ' + a)); i.src = kok + a;
  })));

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
  const elips = (x, y, rx, ry) => { g.beginPath(); g.ellipse(x, y, Math.max(0, rx), Math.max(0, ry), 0, 0, 7); g.fill(); };

  // Görsel çiz. Varsayılan çapa: alt-orta. o: orta (merkezden), cy (0-1 dikey çapa), aci, sx, sy, alfa
  function spr(ad, x, y, h, o = {}) {
    const im = IMG[ad + '.png'] || IMG[ad + '.jpg']; if (!im || h <= 0.5) return;
    const w = h * im.width / im.height, cy = o.cy !== undefined ? o.cy : (o.orta ? 0.5 : 1);
    g.save(); g.translate(x, y); if (o.aci) g.rotate(o.aci); g.scale(o.sx || 1, o.sy || 1);
    if (o.alfa !== undefined) g.globalAlpha = o.alfa;
    g.drawImage(im, -w / 2, -h * cy, w, h); g.restore();
  }
  const var_ = ad => !!(IMG[ad + '.png'] || IMG[ad + '.jpg']);
  function golge(x, y, rx, alfa = 0.22) { g.fillStyle = `rgba(30,60,40,${alfa})`; elips(x, y, rx, rx * 0.16); }

  const RENK = [
    { id: 'kirmizi', ad: 'KIRMIZI', c: '#E53935', a: '#FF8A80', k: '#9A1212', nesne: 'elma' },
    { id: 'mavi', ad: 'MAVİ', c: '#1E88E5', a: '#90CAF9', k: '#0B3C8A', nesne: 'yelkenli' },
    { id: 'sari', ad: 'SARI', c: '#FBC02D', a: '#FFF59D', k: '#C67100', nesne: 'gunes' },
    { id: 'yesil', ad: 'YEŞİL', c: '#43A047', a: '#A5D6A7', k: '#14521A', nesne: 'yaprak' },
    { id: 'turuncu', ad: 'TURUNCU', c: '#FB8C00', a: '#FFCC80', k: '#A84E00', nesne: null },
    { id: 'mor', ad: 'MOR', c: '#8E24AA', a: '#CE93D8', k: '#43117A', nesne: 'uzum' },
  ];
  const MOR = RENK[5];

  // ---------- 3D görünümlü yazı ----------
  function harf3d(metin, r, boy, hiza) {
    g.font = `700 ${boy}px Fredoka`; g.textAlign = hiza; g.textBaseline = 'middle'; g.lineJoin = 'round';
    const d = boy * 0.085;
    g.strokeStyle = r.k; g.fillStyle = r.k; g.lineWidth = boy * 0.2;
    for (let k = 5; k >= 0; k--) g.strokeText(metin, 0, d * k / 5 + boy * 0.01);
    g.strokeStyle = '#fff'; g.lineWidth = boy * 0.12; g.strokeText(metin, 0, 0);
    const gr = g.createLinearGradient(0, -boy * 0.45, 0, boy * 0.45);
    gr.addColorStop(0, r.a); gr.addColorStop(0.45, r.c); gr.addColorStop(1, r.c);
    g.fillStyle = gr; g.fillText(metin, 0, 0);
  }
  function yazi3d(metin, x, y, boy, r, olcek = 1, aci = 0) {
    if (olcek <= 0.01) return;
    g.save(); g.translate(x, y); g.rotate(aci); g.scale(olcek, olcek); harf3d(metin, r, boy, 'center'); g.restore();
  }
  function renkliYazi(metin, x, y, boy, t, olcek = 1) {
    if (olcek <= 0.01) return;
    g.save(); g.translate(x, y); g.scale(olcek, olcek);
    g.font = `700 ${boy}px Fredoka`;
    const palet = [RENK[0], RENK[1], RENK[4], RENK[3], RENK[5]], bosluk = boy * 0.08;
    const gen = [...metin].map(h => g.measureText(h).width);
    let cx = -(gen.reduce((a, b) => a + b, 0) + bosluk * (gen.length - 1)) / 2, n = 0;
    [...metin].forEach((h, i) => {
      if (h !== ' ') { g.save(); g.translate(cx, Math.sin(t * 3 + n * 0.7) * boy * 0.05); harf3d(h, palet[n % palet.length], boy, 'left'); g.restore(); n++; }
      cx += gen[i] + bosluk;
    });
    g.restore();
  }
  function soru(x, y, h, t, k, olcek) {
    if (olcek <= 0.01) return;
    spr('soru', x, y + Math.sin(t * 3 + k) * 14, h * olcek, { orta: true, aci: Math.sin(t * 2.4 + k) * 0.16 });
  }
  function soruIsaretleri(t, tur, x1 = 1440, y1 = 320, x2 = 660, y2 = 250) {
    const o = gorun(t, tur.soruBit + 0.1, tur.cevap, 0.4, 0.25);
    soru(x1, y1, 300, t, 0, o); soru(x2, y2, 210, t, 2, o * 0.95);
  }
  function kelime(t, tur, metin, r, x = 1000, y = 150, boy = 176) {
    yazi3d(metin, x, y, boy, r, gorun(t, tur.cevap, tur.bit - 0.3) * (1 + 0.04 * Math.sin(t * 6)));
  }
  function rozet(x, y, olcek, t, ad, ic = 230) {
    if (olcek <= 0.01) return;
    const yy = y + Math.sin(t * 2 + x) * 8;
    g.save(); g.translate(x, yy); g.scale(olcek, olcek);
    g.fillStyle = 'rgba(40,70,110,0.18)'; elips(8, 14, 178, 178);
    const gr = g.createRadialGradient(-50, -60, 20, 0, 0, 180); gr.addColorStop(0, '#FFFFFF'); gr.addColorStop(1, '#DCECFB');
    g.fillStyle = gr; elips(0, 0, 172, 172); g.strokeStyle = '#fff'; g.lineWidth = 10; g.stroke();
    g.restore();
    spr(ad, x, yy, ic * olcek, { orta: true });
  }
  function isilti(x, y, r, t, adet = 8) {
    for (let k = 0; k < adet; k++) {
      const a = k * (6.283 / adet) + t * 1.5, rr = r * (0.8 + 0.2 * Math.sin(t * 5 + k));
      spr('yildiz_parlak', x + Math.cos(a) * rr, y + Math.sin(a) * rr, 44 + 16 * Math.sin(t * 6 + k * 2), { orta: true, aci: t * 2 + k });
    }
  }

  // ---------- arka plan ----------
  function arkaPlan(ad, t, yak = 1.03) {
    const im = IMG[ad + '.jpg'] || IMG[ad + '.png'];
    const s = yak + Math.sin(t * 0.21) * 0.008, dx = Math.sin(t * 0.13) * 10;
    g.drawImage(im, W / 2 - W * s / 2 + dx, H / 2 - H * s / 2, W * s, H * s);
  }
  function notalar(t, t0) {
    for (let k = 0; k < 9; k++) {
      const p = ((t - t0) * 0.16 + rasgele(k + 3)) % 1;
      spr('nota', 150 + rasgele(k + 40) * 1620 + Math.sin(t * 1.5 + k) * 40, 950 - p * 900, 90 + rasgele(k) * 50, { orta: true, aci: Math.sin(t * 2 + k) * 0.25, alfa: Math.sin(Math.PI * p) * 0.9 });
    }
  }
  function konfeti(t, t0) {
    const dt = t - t0; if (dt < 0) return;
    for (let k = 0; k < 150; k++) {
      const y = ((-60 - rasgele(k + 500) * 1300 + dt * (220 + rasgele(k) * 200)) % (H + 1400));
      if (y < -40 || y > H + 40) continue;
      g.save(); g.translate(rasgele(k + 900) * W + Math.sin(t * 2 + k) * 36, y); g.rotate(t * (2 + rasgele(k + 70) * 3) + k);
      g.fillStyle = RENK[k % 6].c; g.fillRect(-12, -8 * Math.abs(Math.cos(t * 4 + k)) - 1, 24, 16 * Math.abs(Math.cos(t * 4 + k)) + 2);
      g.restore();
    }
  }

  // ---------- balon ----------
  const BALON_H = 640, BALON_CY = AYAR.balonCy || 0.33; // gövde merkezi görselin üstünden oranı
  function balon(x, y, s, i, t, k = 0, yazi = null) {
    if (s <= 0.01) return;
    spr('balon_' + RENK[i].id, x, y, BALON_H * s, { cy: BALON_CY, aci: Math.sin(t * 1.3 + k * 2) * 0.05 });
    if (yazi) yazi3d(yazi, x, y + 6 * s, 230 * s, { c: '#fff', a: '#fff', k: RENK[i].k });
  }

  // ---------- Pıtır ----------
  const P_H = AYAR.pitirH || 620;
  // d: x,y,s,poz,agiz,hop,egim,donus,kirp
  function pitir(t, d) {
    const s = d.s || 1, hop = d.hop || 0, h = P_H * s;
    let poz = d.poz || 'durus';
    if (!var_('pitir_' + poz)) poz = 'durus';
    golge(d.x, d.y + 4, h * 0.27 * (1 - Math.min(0.5, hop / 500)));
    const nefes = 1 + Math.sin(t * 2.6) * 0.012 + Math.min(0.06, hop * 0.0004) + (d.nefes || 0);
    const o = { aci: d.egim || 0, sx: (d.donus === undefined ? 1 : d.donus) / Math.sqrt(nefes), sy: nefes };
    const kirp = d.kirp || (t % 3.9) < 0.14;
    const taban = kirp && var_('pitir_' + poz + '_goz') ? 'pitir_' + poz + '_goz' : 'pitir_' + poz;
    spr(taban, d.x, d.y - hop, h, o);
    const agiz = d.agiz || 0;
    if (agiz > 0.06 && var_('pitir_' + poz + '_agiz') && taban === 'pitir_' + poz) spr('pitir_' + poz + '_agiz', d.x, d.y - hop, h, Object.assign({ alfa: sinirla(agiz * 2.0) }, o));
  }
  const agizAl = t => ZARF[Math.min(ZARF.length - 1, Math.max(0, Math.round(t * TL.fps)))] || 0;
  const PX = 300, PY = 965;
  function pitirTur(t, b, d = {}) {
    let hop = 0, isaret = 0, sevinc = 0;
    (b.turlar || []).forEach(r => {
      hop += 60 * zipla(t, r.cevap, 0.5) + 30 * zipla(t, r.cevap + 0.55, 0.4);
      if (t >= r.cevap - 0.05 && t < r.cevap + 1.0) sevinc = 1;
      if (t >= r.soru && t < r.bit - 0.8) isaret = 1;
    });
    if (b.ozet && b.ozet.vuruslar) b.ozet.vuruslar.forEach(v => { hop += 42 * zipla(t, v, 0.45); });
    const selam = b.giris && t >= b.giris.t && t < b.giris.t + 2.2;
    let poz = d.poz || 'durus', egim = Math.sin(t * 1.1) * 0.012;
    if (selam) { poz = 'salla'; egim = Math.sin(t * 9) * 0.04; }
    else if (sevinc) poz = 'sevinc';
    else if (isaret) poz = 'isaret';
    pitir(t, Object.assign({ x: d.x || PX, y: d.y || PY, hop, agiz: agizAl(t), poz, egim }, d.ek || {}));
  }
  function pitirDans(t, dt, x, y, s, bpm) {
    const v = dt * bpm / 60, hop = 46 * Math.abs(Math.sin(Math.PI * v));
    const poz = ['sevinc', 'salla', 'sevinc', 'durus'][Math.floor(v / 2) % 4];
    pitir(t, { x, y, s, hop, agiz: agizAl(t), poz, egim: Math.sin(Math.PI * v / 2) * 0.07 });
  }

  // ================= SAHNELER =================
  const SAHNE = {};

  SAHNE.tema = (t, b) => {
    arkaPlan('bg_parti', t);
    const dt = t - b.t0;
    for (let i = 0; i < 6; i++) balon(210 + i * 300, H + 300 - ((dt * 170 + i * 260) % (H + 700)), 0.42, i, t, i);
    notalar(t, b.t0);
    renkliYazi('Pıtır ile Öğren', 960, 215, 180, t, patla(t, b.t0 - 0.3, 0.7));
    pitirDans(t, dt, 960, 1010, 1.12, 120);
  };

  SAHNE.selam = (t, b) => {
    arkaPlan('bg_cayir', t);
    const s = b.giris, sure = s.bit - s.t;
    ['balon_kirmizi', 'sayilar', 'sekil_ucgen', 'inek'].forEach((ad, i) => {
      const o = patla(t, s.t + sure * [0.26, 0.36, 0.45, 0.54][i], 0.45) * 0.8, x = 850 + i * 290;
      if (ad === 'sayilar') { rozet(x, 470, o, t, null); yazi3d('123', x, 470 + Math.sin(t * 2 + x) * 8, 120 * o, RENK[1], o > 0.05 ? 1 : 0); }
      else rozet(x, 470, o, t, ad, ad === 'balon_kirmizi' ? 290 : 230);
    });
    const salla = t >= s.t && t < s.t + 2.6;
    pitir(t, { x: 380, y: 990, s: 1.08, hop: 60 * zipla(t, s.t, 0.55) + 50 * zipla(t, s.bit - 1.6, 0.5), agiz: agizAl(t), poz: salla ? 'salla' : (t > s.bit - 1.8 ? 'sevinc' : 'durus'), egim: salla ? Math.sin(t * 9) * 0.04 : 0 });
  };

  // --- renkler ---
  SAHNE.renkler = (t, b) => {
    arkaPlan('bg_cayir', t);
    const O = b.ozet, M = { x: 1010, y: 430 }, yuva = i => ({ x: 1345 + i * 100, y: 100 }), sira = i => ({ x: 640 + i * 222, y: 500 });
    const durum = [];
    b.turlar.forEach((r, i) => {
      if (t < r.t) return;
      let x = M.x, y = ara(H + 420, M.y, yavasla(ilerle(t, r.t, 2.4))), s = 1 + 0.10 * zipla(t, r.cevap, 0.45);
      const p1 = yumusak(ilerle(t, r.bit - 1.1, 1.0)), y1 = yuva(i);
      x = ara(x, y1.x, p1); y = ara(y, y1.y, p1); s = ara(s, 0.2, p1);
      const p2 = yumusak(ilerle(t, O.t + 0.2 + i * 0.1, 1.2)), s1 = sira(i);
      x = ara(x, s1.x, p2); y = ara(y, s1.y, p2); s = ara(s, 0.5, p2);
      y -= 80 * zipla(t, O.vuruslar[i], 0.5); s *= 1 + 0.18 * zipla(t, O.vuruslar[i], 0.5);
      y -= 40 * zipla(t, O.son + i * 0.1, 0.5);
      y += Math.sin(t * 1.6 + i * 1.7) * 12 * s; x += Math.sin(t * 1.1 + i) * 7 * s;
      durum.push({ i, x, y, s });
    });
    b.turlar.forEach((r, i) => {
      if (t < r.t || t > r.bit) return;
      soruIsaretleri(t, r);
      kelime(t, r, RENK[i].ad, RENK[i], 860, 150);
      const no = gorun(t, r.cevap + (r.cevapBit - r.cevap) * 0.55, r.bit - 0.9);
      if (RENK[i].nesne) rozet(1540, 560, no, t, RENK[i].nesne);
      else if (no > 0) isilti(PX, PY - 330, 300 * Math.min(1, no), t, 10);
    });
    durum.forEach(d => balon(d.x, d.y, d.s, d.i, t, d.i));
    O.vuruslar.forEach((v, i) => yazi3d(RENK[i].ad, 1100, 170, 180, RENK[i], gorun(t, v, (i < 5 ? O.vuruslar[i + 1] : O.son) + 0.1, 0.3, 0.15)));
    renkliYazi('6 Renk!', 1100, 170, 190, t, gorun(t, O.son, b.t1 + 1, 0.4, 0.3));
    pitirTur(t, b);
  };

  // --- sayılar ---
  const DAL = [[1440, 380], [1570, 250], [1710, 310], [1790, 430], [1600, 440]];
  SAHNE.sayilar = (t, b) => {
    arkaPlan('bg_cayir', t);
    golge(1620, 985, 230); spr('agac', 1620, 1000, 900);
    const O = b.ozet, SX = 1000, SY = 1010, SH = 250, yer = i => ({ x: SX + (i - 2) * 66, y: SY - SH * 0.74 - (i % 2) * 26 }), sira = i => ({ x: 600 + i * 165, y: 450 });
    golge(SX, SY - 6, 230); spr('sepet', SX, SY, SH);
    b.turlar.forEach((r, i) => {
      const p = ilerle(t, r.t + 0.15, 0.95), a = DAL[i], z = yer(i);
      let x = ara(a[0], z.x, p), y = ara(a[1], z.y, p * p), h = 120 * (1 + 0.1 * zipla(t, r.cevap, 0.4)), yazi = null;
      y -= 26 * zipla(t, r.t + 1.1, 0.3);
      b.turlar.forEach((r2, j) => { if (j >= i) y -= 22 * zipla(t, r2.cevap + i * 0.12, 0.35); });
      const p2 = yumusak(ilerle(t, O.vuruslar[i] - 0.25, 0.5)), s1 = sira(i);
      if (p2 > 0) { x = ara(x, s1.x, p2); y = ara(y, s1.y, p2) - 60 * Math.sin(Math.PI * p2); h = ara(h, 170, p2); yazi = p2 > 0.6 ? String(i + 1) : null; }
      y -= 40 * zipla(t, O.son + i * 0.1, 0.5);
      const yy = y + (p2 > 0 ? Math.sin(t * 2 + i) * 6 : 0);
      spr('elma', x, yy, h, { orta: true, aci: p > 0 && p < 1 ? p * 3 : 0 });
      if (yazi) yazi3d(yazi, x, yy + 12, 100, { c: '#fff', a: '#fff', k: RENK[0].k });
    });
    // sepetin ön yarısı elmaların önünde kalsın
    if (IMG['sepet.png']) { g.save(); g.beginPath(); g.rect(SX - 400, SY - SH * 0.62, 800, SH); g.clip(); spr('sepet', SX, SY, SH); g.restore(); }
    b.turlar.forEach((r, i) => {
      if (t < r.t || t > r.bit) return;
      soruIsaretleri(t, r, 1260, 340, 700, 300);
      yazi3d(String(i + 1), 1000, 340, 380, RENK[0], gorun(t, r.cevap, r.bit - 0.3) * (1 + 0.04 * Math.sin(t * 6)));
    });
    renkliYazi('5 Elma!', 950, 200, 180, t, gorun(t, O.son, b.t1 + 1, 0.4, 0.3));
    pitirTur(t, b);
  };

  // --- şarkı ---
  SAHNE.sarki = (t, b) => {
    arkaPlan('bg_parti', t);
    if (t < b.sarki) { pitirTur(t, b, { x: 960, y: 1010, ek: { s: 1.12 } }); return; }
    const dt = t - b.sarki, vur = Math.abs(Math.sin(Math.PI * dt * 110 / 60));
    for (let i = 0; i < 6; i++) balon(160 + i * 320, H + 300 - ((dt * 120 + i * 300) % (H + 700)), 0.3, (i + 3) % 6, t, i + 9);
    notalar(t, b.sarki);
    for (let i = 0; i < 4; i++) balon((i < 2 ? 250 + i * 280 : 1390 + (i - 2) * 280) + Math.sin(dt * 1.1 + i) * 30, 400 + Math.sin(dt * 2.2 + i * 0.9) * 45, 0.6 * (1 + 0.05 * vur), i, t, i);
    renkliYazi('Balon Şarkısı', 960, 150, 140, t, gorun(t, b.sarki, b.sarki + 5));
    pitirDans(t, dt, 960, 1020, 1.15, 110);
  };

  // --- şekiller ---
  const SEKIL = [
    { id: 'sekil_daire', ad: 'DAİRE', r: RENK[4], nesne: 'top' },
    { id: 'sekil_kare', ad: 'KARE', r: RENK[1], nesne: 'pencere' },
    { id: 'sekil_ucgen', ad: 'ÜÇGEN', r: RENK[0], nesne: 'ev' },
    { id: 'sekil_yildiz', ad: 'YILDIZ', r: RENK[2], nesne: 'ay_yildiz' },
  ];
  SAHNE.sekiller = (t, b) => {
    arkaPlan('bg_cayir', t);
    const O = b.ozet, KX = 1010, KY = 1020, yuva = i => ({ x: 1380 + i * 130, y: 105 });
    const EV = [{ x: 1650, y: 250, h: 240 }, { x: 1010, y: 700, h: 400 }, { x: 1010, y: 340, h: 380 }, { x: 600, y: 240, h: 230 }];
    const sirasi = [1, 2, 0, 3], evde = i => O.vuruslar[sirasi.indexOf(i)];
    const cizim = [];
    b.turlar.forEach((r, i) => {
      if (t < r.t) return;
      const p0 = yavasla(ilerle(t, r.t + 0.1, 1.5));
      let x = KX, y = ara(KY - 200, 440, p0), h = ara(50, 330, p0) * (1 + 0.1 * zipla(t, r.cevap, 0.45)), aci = Math.sin(t * 1.5 + i) * 0.06;
      const p1 = yumusak(ilerle(t, r.bit - 1.1, 1.0)), y1 = yuva(i);
      x = ara(x, y1.x, p1); y = ara(y, y1.y, p1); h = ara(h, 105, p1);
      const p2 = yumusak(ilerle(t, evde(i) - 0.2, 0.9)), e = EV[i];
      x = ara(x, e.x, p2); y = ara(y, e.y, p2); h = ara(h, e.h, p2); aci *= 1 - p2;
      if (i === 3) aci += p2 * Math.sin(t * 2) * 0.12;
      y -= 30 * zipla(t, O.son + i * 0.12, 0.5);
      cizim.push({ i, x, y, h, aci });
    });
    const kutuIn = yumusak(ilerle(t, O.t + 0.2, 0.8)) * 480;
    golge(KX, KY - 4 + kutuIn, 190);
    spr('sihirli_kutu', KX, KY + kutuIn, 330);
    if (kutuIn < 10) isilti(KX, KY - 330, 120, t, 5);
    cizim.forEach(d => spr(SEKIL[d.i].id, d.x, d.y, d.h, { orta: true, aci: d.aci }));
    b.turlar.forEach((r, i) => {
      if (t < r.t || t > r.bit) return;
      soruIsaretleri(t, r);
      kelime(t, r, SEKIL[i].ad, SEKIL[i].r, 880, 150);
      rozet(1560, 600, gorun(t, r.cevap + (r.cevapBit - r.cevap) * 0.6, r.bit - 0.9), t, SEKIL[i].nesne);
    });
    renkliYazi('Ne güzel bir ev!', 1010, 100, 110, t, gorun(t, O.son, b.t1 + 1, 0.4, 0.3));
    pitirTur(t, b);
  };

  // --- hareket etkinliği ---
  const HAREKET = ['EL ÇIRP!', 'ZIPLA!', 'UÇAK OL!', 'DÖN!', 'NEFES AL'];
  SAHNE.hareket = (t, b) => {
    arkaPlan('bg_cayir', t, 1.03);
    const r = b.turlar.find(r => t >= r.t && t < r.bit), i = r ? b.turlar.indexOf(r) : -1;
    if (!r) { pitirTur(t, b, { x: 960, y: 1020, ek: { s: 1.22 } }); return; }
    const aktif = t >= r.hareket && t < r.bit - 0.3, dt = t - r.hareket;
    const d = { x: 960, y: 1020, s: 1.22, agiz: agizAl(t), hop: 0, poz: 'durus' };
    if (aktif) {
      if (i === 0) { const c = Math.sin(dt * 2 * Math.PI * 3) > 0; d.poz = c ? 'alkis' : 'alkis_acik'; if (c) isilti(960, 1020 - P_H * 1.22 * 0.42, 120, t, 6); }
      else if (i === 1) { d.hop = 210 * Math.abs(Math.sin(Math.PI * dt / 0.62)); d.poz = d.hop > 50 ? 'sevinc' : 'durus'; }
      else if (i === 2) { d.poz = 'ucak'; d.egim = Math.sin(dt * 2.2) * 0.2; d.x += Math.sin(dt * 1.3) * 280; d.hop = 70 + Math.sin(dt * 2.6) * 30; }
      else if (i === 3) { const q = Math.floor(dt / 0.32) % 4; d.poz = ['durus', 'yan', 'arka', 'yan'][q]; d.donus = q === 3 ? -1 : 1; d.hop = 16 * Math.abs(Math.sin(Math.PI * dt / 0.32)); }
      else {
        const n = 0.5 - 0.5 * Math.cos(dt * 2 * Math.PI / 5.2);
        d.poz = 'nefes'; d.nefes = n * 0.07;
        g.strokeStyle = 'rgba(255,255,255,0.75)'; g.lineWidth = 18; g.beginPath(); g.arc(960, 640, 330 + n * 130, 0, 7); g.stroke();
        g.strokeStyle = 'rgba(30,136,229,0.35)'; g.lineWidth = 8; g.stroke();
      }
    }
    pitir(t, d);
    yazi3d(HAREKET[i], 960, 150, 170, RENK[[0, 3, 1, 5, 1][i]], gorun(t, r.t + 0.5, r.bit));
    const kalan = r.bit - t, adet = Math.ceil(r.bit - r.konusmaBit);
    if (t > r.konusmaBit) for (let q = 0; q < adet; q++) spr('yildiz_parlak', 300 + q * 80, 150, 64, { orta: true, alfa: q < kalan ? 1 : 0.25 });
  };

  // --- hayvanlar ---
  const HAYVAN = [
    { id: 'inek', ad: 'İNEK', ses: 'Möö!', r: { c: '#EC407A', a: '#F8BBD0', k: '#880E4F' } },
    { id: 'koyun', ad: 'KOYUN', ses: 'Mee!', r: { c: '#5C6BC0', a: '#C5CAE9', k: '#1A237E' } },
    { id: 'ordek', ad: 'ÖRDEK', ses: 'Vak vak!', r: RENK[4] },
    { id: 'kopek', ad: 'KÖPEK', ses: 'Hav hav!', r: { c: '#8D6E63', a: '#D7CCC8', k: '#3E2723' } },
  ];
  function balonKonusma(x, y, metin, olcek, renk) {
    if (olcek <= 0.01) return;
    g.save(); g.translate(x, y); g.scale(olcek, olcek);
    g.font = '700 96px Fredoka'; const gen = Math.max(260, g.measureText(metin).width + 110);
    g.fillStyle = 'rgba(40,70,110,0.18)'; g.beginPath(); g.roundRect(-gen / 2 + 8, -78, gen, 180, 80); g.fill();
    g.fillStyle = '#fff'; g.beginPath(); g.roundRect(-gen / 2, -90, gen, 180, 80); g.fill();
    g.beginPath(); g.moveTo(-30, 86); g.lineTo(0, 150); g.lineTo(40, 86); g.fill();
    g.fillStyle = renk; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(metin, 0, 6);
    g.restore();
  }
  SAHNE.hayvanlar = (t, b) => {
    arkaPlan('bg_ciftlik', t);
    golge(1640, 915, 250); spr('ahir', 1640, 930, 520);
    const CX = 1010, CY = 1030, CH = 400, yuva = i => ({ x: 1180 + i * 190, y: 235 });
    let salla = 0; const cizim = [];
    b.turlar.forEach((r, i) => {
      if (t < r.cevap - 0.1) { if (t >= r.soru && t < r.cevap) salla = Math.max(salla, sinirla(gorun(t, r.soru + 0.3, r.soruBit - 0.6, 0.3, 0.3))); return; }
      const p0 = yavasla(ilerle(t, r.cevap - 0.1, 0.6));
      let x = CX, y = ara(CY + 150, CY - 210, p0) - 30 * zipla(t, r.cevap + 0.6, 0.4), h = 420;
      const p1 = yumusak(ilerle(t, r.bit - 1.1, 1.0)), y1 = yuva(i);
      x = ara(x, y1.x, p1); y = ara(y, y1.y, p1); h = ara(h, 170, p1);
      if (b.ozet) { const sure = b.ozet.bit - b.ozet.t; y -= 40 * zipla(t, b.ozet.t + sure * (0.48 + i * 0.07), 0.45); }
      cizim.push({ i, x, y, h, on: p1 > 0.02 });
    });
    cizim.filter(d => !d.on).forEach(d => spr(HAYVAN[d.i].id, d.x, d.y, d.h, { aci: Math.sin(t * 2) * 0.03 }));
    golge(CX, CY - 8, 330);
    spr('cali', CX, CY, CH, { aci: Math.sin(t * 22) * 0.02 * salla, sx: 1 + Math.sin(t * 18) * 0.02 * salla });
    cizim.filter(d => d.on).forEach(d => spr(HAYVAN[d.i].id, d.x, d.y, d.h));
    b.turlar.forEach((r, i) => {
      if (t < r.t || t > r.bit) return;
      balonKonusma(CX + 40, 480, HAYVAN[i].ses, gorun(t, r.soru + 0.5, r.soruBit - 0.7, 0.35, 0.25), HAYVAN[i].r.k);
      soruIsaretleri(t, r, 1420, 430, 660, 300);
      kelime(t, r, HAYVAN[i].ad, HAYVAN[i].r, 780, 150);
    });
    if (b.ozet) balonKonusma(600, 330, 'Miyav!', gorun(t, b.ozet.t + 1.3, b.ozet.t + 3.4, 0.35, 0.25), RENK[4].k);
    pitirTur(t, b);
  };

  // --- taşıtlar ---
  const YOL = AYAR.yolY || 960;
  const TASIT = [
    { id: 'araba', ad: 'ARABA', r: RENK[0], y: YOL, h: 300 },
    { id: 'otobus', ad: 'OTOBÜS', r: RENK[2], y: YOL, h: 400 },
    { id: 'tren', ad: 'TREN', r: RENK[3], y: YOL, h: 330 },
    { id: 'ucak', ad: 'UÇAK', r: RENK[1], y: 560, h: 330 },
  ];
  function tasit(T, x, y, t, hareket, s = 1) {
    const yon = (AYAR.sagaBakan || []).includes(T.id) ? -1 : 1;
    if (T.id !== 'ucak') golge(x, T.y - 6, T.h * s * 0.9, 0.2);
    spr(T.id, x, y - Math.abs(Math.sin(t * 9)) * 5 * hareket + (T.id === 'ucak' ? Math.sin(t * 1.6) * 14 : 0), T.h * s, { sx: yon, aci: T.id === 'ucak' ? Math.sin(t * 1.5) * 0.04 : 0 });
  }
  SAHNE.tasitlar = (t, b) => {
    arkaPlan('bg_yol', t, 1.0);
    const r0 = b.turlar.find(r => t >= r.t && t < r.bit);
    pitirTur(t, b, { x: 260, y: AYAR.yolPitirY || 880, ek: { s: 0.8 } });
    b.turlar.forEach((r, i) => {
      if (t < r.t || t > r.bit + 0.2) return;
      const T = TASIT[i], gir = yavasla(ilerle(t, r.t + 0.2, 2.4)), cik = Math.pow(ilerle(t, r.bit - 1.3, 1.5), 2);
      tasit(T, ara(W + 800, 1150, gir) - cik * 2200, T.y - 40 * zipla(t, r.cevap, 0.45), t, gir < 0.98 || cik > 0 ? 1 : 0.15);
      soruIsaretleri(t, r, 1600, 230, 660, 240);
      kelime(t, r, T.ad, T.r, 1000, 150);
    });
    if (b.ozet && t >= b.ozet.t) {
      const sure = b.ozet.bit + 1.2 - b.ozet.t;
      TASIT.forEach((T, i) => { const p = ilerle(t, b.ozet.t + i * sure * 0.13, sure * 0.6); if (p > 0 && p < 1) tasit(T, ara(W + 700, -800, p), T.y, t, 1, 0.85); });
    }
  };

  // --- hafıza oyunu ---
  SAHNE.oyun = (t, b) => {
    arkaPlan('bg_cayir', t);
    const yer = i => ({ x: 720 + i * 270, y: 430 });
    let perde = 0;
    for (let i = 0; i < 4; i++) {
      let p = yer(i), y = p.y, s = 0.62 * patla(t, b.giris.t + 0.3 + i * 0.25, 0.5), gizli = false;
      b.turlar.forEach(r => {
        if (r.eksik !== i) return;
        if (t >= r.soru + 1.45 && t < r.cevap) gizli = true;
        if (t >= r.cevap) { y = ara(-400, p.y, geri(ilerle(t, r.cevap, 0.7))); if (t < r.cevap + 2.2) isilti(p.x, p.y, 210, t, 8); }
      });
      if (!gizli) balon(p.x + Math.sin(t * 1.1 + i) * 6, y + Math.sin(t * 1.6 + i * 1.7) * 10, s, i, t, i);
    }
    b.turlar.forEach(r => {
      perde = Math.max(perde, yumusak(ilerle(t, r.soru + 1.0, 0.45)) * (1 - yumusak(ilerle(t, r.soruBit - 1.8, 0.45))));
      if (t >= r.t && t <= r.bit) {
        const p = yer(r.eksik);
        soru(p.x, p.y, 330, t, 0, gorun(t, r.soruBit + 0.1, r.cevap, 0.4, 0.25));
        kelime(t, r, RENK[r.eksik].ad, RENK[r.eksik], 1120, 130);
      }
    });
    pitirTur(t, b, { ek: { kirp: perde > 0.5 } });
    if (perde > 0) {
      const ac = (1 - perde) * (W / 2 + 60);
      const sol = IMG['perde_sol.jpg'], sag = IMG['perde_sag.jpg'];
      g.drawImage(sol, -ac, 0, W / 2 + 2, H); g.drawImage(sag, W / 2 - 2 + ac, 0, W / 2 + 2, H);
      if (perde > 0.9) {
        g.strokeStyle = '#fff'; g.lineWidth = 24; g.lineCap = 'round';
        g.beginPath(); g.arc(780, 500, 110, 0.2, Math.PI - 0.2); g.stroke(); g.beginPath(); g.arc(1140, 500, 110, 0.2, Math.PI - 0.2); g.stroke();
      }
    }
  };

  // --- kapanış ---
  SAHNE.kapanis = (t, b) => {
    arkaPlan('bg_parti', t);
    const s = b.giris, dt = t - b.sarki;
    konfeti(t, s.t + 0.5);
    if (t < b.sarki) {
      renkliYazi('Aferin!', 1150, 300, 230, t, gorun(t, s.t + 0.3, b.sarki + 1, 0.5, 0.4));
      const veda = t > s.bit - 3.2;
      pitir(t, { x: 480, y: 1000, s: 1.12, hop: 60 * zipla(t, s.t, 0.55) + 60 * zipla(t, s.bit - 4, 0.5), agiz: agizAl(t), poz: veda ? 'salla' : (t < s.t + 1.2 ? 'sevinc' : 'durus'), egim: veda ? Math.sin(t * 9) * 0.04 : 0 });
      return;
    }
    for (let i = 0; i < 6; i++) balon(210 + i * 300, H + 300 - ((dt * 170 + i * 260) % (H + 700)), 0.42, i, t, i);
    renkliYazi('Hoşça kalın!', 960, 215, 180, t, patla(t, b.sarki, 0.6));
    pitirDans(t, dt, 960, 1010, 1.12, 120);
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
    B.forEach((x, k) => {
      if (k === 0) return;
      const p = 1 - Math.abs(t - x.t0) / 0.55;
      if (p > 0) { const r = yumusak(p) * 1150; g.fillStyle = RENK[k % 6].c; elips(W / 2, H / 2, r, r); g.fillStyle = RENK[k % 6].a; elips(W / 2, H / 2, r - 40, r - 40); }
    });
    const son = ilerle(t, TL.sure - 1.0, 1.0);
    if (son > 0) { g.fillStyle = `rgba(255,255,255,${son})`; g.fillRect(0, 0, W, H); }
  };
})();
