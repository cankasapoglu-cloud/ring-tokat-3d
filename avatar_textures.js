// Avatar dokularını çalışma anında üretir: kıyafet boyama, yüz fotoğrafı ve tişört baskısı.
// Tüm koordinatlar 1024x1024 doku pikselidir.

export const SIZE = 1024;

export const GENDERS = {
  male: {
    label: 'Erkek',
    eyes: [[441, 290], [583, 290]],
    mouth: [510, 412],
    face: { cx: 512, cy: 322, rx: 205, ry: 212 },
    toneSamples: [[418, 385], [606, 385], [512, 205]],
    shirt: [[332, 36, 692, 906]],
    sleeves: [[0, 445, 318, 598], [706, 445, 1024, 598]],
    printErase: [[430, 545, 610, 735], [548, 800, 632, 860]],
    jeans: [[0, 0, 312, 446], [712, 0, 1024, 446]],
    shoes: [[214, 712, 432, 1024], [592, 712, 812, 1024]],
    skin: [[0, 585, 316, 1024], [708, 585, 1024, 1024]],
    blemish: [92, 755, 132, 845],
    print: { cx: 512, cy: 655, size: 225, aspect: 0.78 },
  },
  female: {
    label: 'Kadın',
    eyes: [[443, 290], [583, 290]],
    mouth: [512, 415],
    face: { cx: 512, cy: 325, rx: 190, ry: 205 },
    toneSamples: [[425, 385], [600, 385], [512, 205]],
    shirt: [[345, 0, 682, 782]],
    sleeves: [],
    printErase: [[440, 488, 582, 632]],
    jeans: [[0, 575, 345, 1024], [680, 575, 1024, 1024]],
    shoes: [[138, 0, 338, 310], [688, 0, 888, 310]],
    skin: [[0, 0, 200, 275], [824, 0, 1024, 275], [0, 270, 356, 540], [668, 270, 1024, 540]],
    blemish: null,
    print: { cx: 512, cy: 575, size: 185, aspect: 1 },
  },
};

const smooth = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const inRect = (x, y, r) => x >= r[0] && y >= r[1] && x < r[2] && y < r[3];
const inAny = (x, y, rects) => rects.some(r => inRect(x, y, r));
const luma = (r, g, b) => 0.299 * r + 0.587 * g + 0.114 * b;

function rectFeather(x, y, r, f) {
  const d = Math.min(x - r[0], r[2] - x, y - r[1], r[3] - y);
  return smooth(0, f, d);
}

function skinness(r, g, b) {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  if (max !== r || d === 0) return 0;
  const s = d / max;
  const v = max / 255;
  const h = 60 * ((g - b) / d);
  return smooth(2, 10, h) * (1 - smooth(38, 50, h)) * smooth(0.12, 0.24, s) *
    (1 - smooth(0.72, 0.85, s)) * smooth(0.34, 0.46, v);
}

function boxBlur(src, radius) {
  const n = SIZE;
  const tmp = new Float32Array(src.length);
  const out = new Float32Array(src.length);
  const span = radius * 2 + 1;
  for (let y = 0; y < n; y++) {
    let sum = 0;
    for (let x = -radius; x <= radius; x++) sum += src[y * n + Math.max(0, x)];
    for (let x = 0; x < n; x++) {
      tmp[y * n + x] = sum / span;
      sum += src[y * n + Math.min(n - 1, x + radius + 1)] - src[y * n + Math.max(0, x - radius)];
    }
  }
  for (let x = 0; x < n; x++) {
    let sum = 0;
    for (let y = -radius; y <= radius; y++) sum += tmp[Math.max(0, y) * n + x];
    for (let y = 0; y < n; y++) {
      out[y * n + x] = sum / span;
      sum += tmp[Math.min(n - 1, y + radius + 1) * n + x] - tmp[Math.max(0, y - radius) * n + x];
    }
  }
  return out;
}

function canvas2d(opts) {
  const c = document.createElement('canvas');
  c.width = c.height = SIZE;
  return c.getContext('2d', { willReadFrequently: true, ...opts });
}

function hexToRgb(hex) {
  const v = parseInt(hex.replace('#', ''), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}

// Üç noktayı (iki göz, ağız) dokudaki karşılıklarına taşıyan afin dönüşüm.
export function solveAffine(src, dst) {
  const [[x1, y1], [x2, y2], [x3, y3]] = src;
  const det = x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2);
  if (Math.abs(det) < 1e-6) return null;
  const solve = (v1, v2, v3) => [
    (v1 * (y2 - y3) + v2 * (y3 - y1) + v3 * (y1 - y2)) / det,
    (v1 * (x3 - x2) + v2 * (x1 - x3) + v3 * (x2 - x1)) / det,
    (v1 * (x2 * y3 - x3 * y2) + v2 * (x3 * y1 - x1 * y3) + v3 * (x1 * y2 - x2 * y1)) / det,
  ];
  const [a, c, e] = solve(dst[0][0], dst[1][0], dst[2][0]);
  const [b, d, f] = solve(dst[0][1], dst[1][1], dst[2][1]);
  return [a, b, c, d, e, f];
}

export class AvatarSkin {
  constructor(cfg, headImg, bodyImg) {
    this.cfg = cfg;
    this.headCtx = canvas2d();
    this.bodyCtx = canvas2d();
    this.headCtx.drawImage(headImg, 0, 0, SIZE, SIZE);
    this.bodyCtx.drawImage(bodyImg, 0, 0, SIZE, SIZE);
    this.headOut = this.headCtx.getImageData(0, 0, SIZE, SIZE);
    this.bodyOut = this.bodyCtx.getImageData(0, 0, SIZE, SIZE);
    this.headBase = this.headOut.data.slice();
    this.bodyBase = this.bodyOut.data.slice();

    this.gain = [1, 1, 1];
    this.facePhoto = null;
    this.shirt = { image: null, color: '#f4f4f1', scale: 1 };
    this.printLayer = null;

    this.prepareHead();
    this.prepareBody();
    this.renderHead();
    this.renderBody();
  }

  get headCanvas() { return this.headCtx.canvas; }
  get bodyCanvas() { return this.bodyCtx.canvas; }

  prepareHead() {
    const { face } = this.cfg;
    const b = this.headBase;
    const skin = new Float32Array(SIZE * SIZE);
    const hair = new Float32Array(SIZE * SIZE);
    for (let y = 0, i = 0; y < SIZE; y++) {
      for (let x = 0; x < SIZE; x++, i++) {
        const p = i * 4;
        const atlas = y > 600 && x < 370;
        skin[i] = atlas ? 0 : skinness(b[p], b[p + 1], b[p + 2]);
        hair[i] = Math.max(b[p], b[p + 1], b[p + 2]) < 85 ? 1 : 0;
      }
    }
    this.headSkin = boxBlur(skin, 2);
    const hairSoft = boxBlur(hair, 6);
    this.faceMask = new Float32Array(SIZE * SIZE);
    for (let y = 0, i = 0; y < SIZE; y++) {
      for (let x = 0; x < SIZE; x++, i++) {
        const d = Math.hypot((x - face.cx) / face.rx, (y - face.cy) / face.ry);
        const oval = 1 - smooth(0.78, 1, d);
        const inner = 1 - smooth(0.62, 0.78, d);
        this.faceMask[i] = oval * Math.max(inner, 1 - smooth(0.15, 0.55, hairSoft[i]));
      }
    }
  }

  prepareBody() {
    const c = this.cfg;
    const b = this.bodyBase;
    const n = SIZE * SIZE;
    const clean = b.slice();
    this.bodySkin = new Float32Array(n);
    this.shirtWeight = new Float32Array(n);

    if (c.blemish) {
      const r = c.blemish;
      for (let y = r[1] - 12; y < r[3] + 12; y++) {
        for (let x = r[0] - 12; x < r[2] + 12; x++) {
          const k = rectFeather(x, y, [r[0] - 12, r[1] - 12, r[2] + 12, r[3] + 12], 12);
          const p = (y * SIZE + x) * 4;
          const q = (y * SIZE + x + 52) * 4;
          for (let ch = 0; ch < 3; ch++) clean[p + ch] += (b[q + ch] - b[p + ch]) * k;
        }
      }
    }

    const lum = new Float32Array(n);
    const samples = [];
    for (let y = 0, i = 0; y < SIZE; y++) {
      for (let x = 0; x < SIZE; x++, i++) {
        const p = i * 4;
        const l = luma(clean[p], clean[p + 1], clean[p + 2]);
        lum[i] = l;
        const skin = inAny(x, y, c.skin) ? skinness(clean[p], clean[p + 1], clean[p + 2]) : 0;
        this.bodySkin[i] = skin;

        if (inAny(x, y, c.shirt)) {
          this.shirtWeight[i] = 1;
          if (!inAny(x, y, c.printErase) && l > 8 && i % 37 === 0) samples.push(l);
        } else if (inAny(x, y, c.sleeves)) {
          this.shirtWeight[i] = 1 - skin;
        }

        if (inAny(x, y, c.jeans)) {
          clean[p] = l * 0.27 + 10; clean[p + 1] = l * 0.27 + 10; clean[p + 2] = l * 0.27 + 13;
        } else if (inAny(x, y, c.shoes) && skin < 0.5) {
          clean[p] = l * 0.42; clean[p + 1] = l * 0.42; clean[p + 2] = l * 0.44;
        }
      }
    }
    this.bodyClean = clean;

    samples.sort((a, d) => a - d);
    const ref = samples[Math.floor(samples.length * 0.5)] || 1;
    const soft = boxBlur(lum, 9);
    this.shirtShade = new Float32Array(n);
    for (let y = 0, i = 0; y < SIZE; y++) {
      for (let x = 0; x < SIZE; x++, i++) {
        if (!this.shirtWeight[i]) continue;
        let shade = Math.min(1.06, Math.max(0.64, soft[i] / ref));
        for (const r of c.printErase) {
          const pad = [r[0] - 22, r[1] - 22, r[2] + 22, r[3] + 22];
          if (inRect(x, y, pad)) shade += (1 - shade) * rectFeather(x, y, pad, 22);
        }
        this.shirtShade[i] = shade;
      }
    }
  }

  renderHead() {
    const out = this.headOut.data;
    const b = this.headBase;
    const [gr, gg, gb] = this.gain;
    const photo = this.facePhoto;
    for (let i = 0, p = 0; i < SIZE * SIZE; i++, p += 4) {
      const k = this.headSkin[i];
      let r = b[p] * (1 + (gr - 1) * k);
      let g = b[p + 1] * (1 + (gg - 1) * k);
      let v = b[p + 2] * (1 + (gb - 1) * k);
      if (photo) {
        const m = this.faceMask[i] * photo[p + 3] / 255;
        r += (photo[p] - r) * m;
        g += (photo[p + 1] - g) * m;
        v += (photo[p + 2] - v) * m;
      }
      out[p] = r; out[p + 1] = g; out[p + 2] = v; out[p + 3] = 255;
    }
    this.headCtx.putImageData(this.headOut, 0, 0);
    if (this.bandage) this.drawBandage();
  }

  // Art arda darbelerden sonra yanağa çıkan komik yara bandı.
  drawBandage() {
    const ctx = this.headCtx;
    ctx.save();
    ctx.translate(622, 372);
    ctx.rotate(-0.28);
    ctx.fillStyle = '#FDE68A';
    ctx.strokeStyle = '#B45309';
    ctx.lineWidth = 4;
    ctx.fillRect(-44, -17, 88, 34);
    ctx.strokeRect(-44, -17, 88, 34);
    ctx.fillStyle = '#FEF3C7';
    ctx.fillRect(-16, -15, 32, 30);
    ctx.restore();
  }

  setBandage(on) {
    if (this.bandage === on) return false;
    this.bandage = on;
    this.renderHead();
    return true;
  }

  renderBody() {
    const out = this.bodyOut.data;
    const b = this.bodyClean;
    const [gr, gg, gb] = this.gain;
    const [sr, sg, sb] = hexToRgb(this.shirt.color);
    const print = this.printLayer;
    for (let i = 0, p = 0; i < SIZE * SIZE; i++, p += 4) {
      const k = this.bodySkin[i];
      let r = b[p] * (1 + (gr - 1) * k);
      let g = b[p + 1] * (1 + (gg - 1) * k);
      let v = b[p + 2] * (1 + (gb - 1) * k);
      const w = this.shirtWeight[i];
      if (w) {
        const shade = this.shirtShade[i];
        let cr = sr, cg = sg, cb = sb;
        if (print && print[p + 3]) {
          const a = print[p + 3] / 255;
          cr += (print[p] - cr) * a;
          cg += (print[p + 1] - cg) * a;
          cb += (print[p + 2] - cb) * a;
        }
        r += (cr * shade - r) * w;
        g += (cg * shade - g) * w;
        v += (cb * shade - v) * w;
      }
      out[p] = r; out[p + 1] = g; out[p + 2] = v; out[p + 3] = 255;
    }
    this.bodyCtx.putImageData(this.bodyOut, 0, 0);
  }

  // landmarks: [[gözX, gözY], [gözX, gözY], [ağızX, ağızY]] fotoğraf pikseli olarak.
  setFace(image, landmarks) {
    if (!image) {
      this.facePhoto = null;
      this.gain = [1, 1, 1];
      this.renderHead();
      this.renderBody();
      return true;
    }
    const eyes = landmarks.slice(0, 2).sort((p, q) => p[0] - q[0]);
    const m = solveAffine([eyes[0], eyes[1], landmarks[2]], [this.cfg.eyes[0], this.cfg.eyes[1], this.cfg.mouth]);
    if (!m) return false;

    const ctx = canvas2d();
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.setTransform(...m);
    ctx.drawImage(image, 0, 0);
    const photo = ctx.getImageData(0, 0, SIZE, SIZE).data;

    const mean = (data) => {
      const sum = [0, 0, 0];
      let count = 0;
      for (const [cx, cy] of this.cfg.toneSamples) {
        for (let y = cy - 22; y <= cy + 22; y += 2) {
          for (let x = cx - 22; x <= cx + 22; x += 2) {
            const p = (y * SIZE + x) * 4;
            if (data[p + 3] < 250) continue;
            sum[0] += data[p]; sum[1] += data[p + 1]; sum[2] += data[p + 2];
            count++;
          }
        }
      }
      return count ? sum.map(v => v / count) : null;
    };
    const target = mean(photo);
    const base = mean(this.headBase);
    this.gain = target && base
      ? target.map((v, i) => Math.min(1.6, Math.max(0.5, v / Math.max(1, base[i]))))
      : [1, 1, 1];

    this.facePhoto = photo;
    this.renderHead();
    this.renderBody();
    return true;
  }

  setShirt({ image, color, scale }) {
    if (image !== undefined) this.shirt.image = image;
    if (color !== undefined) this.shirt.color = color;
    if (scale !== undefined) this.shirt.scale = scale;

    const img = this.shirt.image;
    if (img) {
      const { cx, cy, size } = this.cfg.print;
      const iw = img.naturalWidth || img.width;
      const ih = img.naturalHeight || img.height;
      const fit = (size * this.shirt.scale) / Math.max(iw, ih);
      const w = iw * fit;
      const h = ih * fit * this.cfg.print.aspect; // Dokudaki tişört dikeyde gerili, baskı bozulmasın.
      const ctx = canvas2d();
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(img, cx - w / 2, cy - h / 2, w, h);
      this.printLayer = ctx.getImageData(0, 0, SIZE, SIZE).data;
    } else {
      this.printLayer = null;
    }
    this.renderBody();
  }
}
