// Fotoğraftaki kafayı (saçıyla birlikte) arka plandan ayırır ve cinsiyeti tahmin eder.
// Her şey telefonda çalışır; fotoğraf hiçbir sunucuya gönderilmez.
import * as faceapi from './lib/face-api/face-api.esm.js';

const tf = faceapi.tf;
const MODELS = './models';

// Çıktı düzeni (HEAD_SIZE kare): göz ortası EYE_MID'de, göz arası EYE_GAP piksel.
export const HEAD_SIZE = 512;
export const EYE_GAP = 88;
export const EYE_MID = [256, 232];

const SEG = 256;
let ready = null;
let selfie = null;

export function warmup() {
  if (!ready) {
    ready = (async () => {
      try {
        await tf.setBackend('webgl');
      } catch (e) {
        await tf.setBackend('cpu');
      }
      await tf.ready();
      await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(MODELS),
        faceapi.nets.faceLandmark68Net.loadFromUri(MODELS),
        faceapi.nets.ageGenderNet.loadFromUri(MODELS),
        tf.loadGraphModel(`${MODELS}/selfie.json`).then(m => { selfie = m; }),
      ]);
    })();
    ready.catch(() => { ready = null; });
  }
  return ready;
}

const mean = pts => [pts.reduce((s, p) => s + p.x, 0) / pts.length, pts.reduce((s, p) => s + p.y, 0) / pts.length];

async function detect(canvas) {
  const run = size => faceapi
    .detectAllFaces(canvas, new faceapi.TinyFaceDetectorOptions({ inputSize: size, scoreThreshold: 0.35 }))
    .withFaceLandmarks()
    .withAgeAndGender();
  let found = await run(416);
  if (!found.length) found = await run(608);
  if (!found.length) found = await run(224);
  if (!found.length) return null;
  return found.sort((a, b) => b.detection.box.area - a.detection.box.area)[0];
}

function segment(canvas) {
  return tf.tidy(() => {
    const img = tf.browser.fromPixels(canvas).toFloat().div(255);
    const input = tf.image.resizeBilinear(img, [SEG, SEG]).expandDims(0);
    const out = selfie.predict(input);
    return out.squeeze().dataSync();
  });
}

const smooth = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/**
 * photo: canvas veya resim. Dönüş: { head: canvas(512, saydam), gender, genderScore, faceFound }
 * Yüz bulunamazsa null döner.
 */
export async function cutHead(photo) {
  await warmup();
  const found = await detect(photo);
  if (!found) return null;

  const lm = found.landmarks.positions;
  const eyeL = mean(lm.slice(36, 42));
  const eyeR = mean(lm.slice(42, 48));
  const mouth = mean(lm.slice(48, 68));
  const chin = [lm[8].x, lm[8].y];
  const gap = Math.hypot(eyeR[0] - eyeL[0], eyeR[1] - eyeL[1]);
  const angle = Math.atan2(eyeR[1] - eyeL[1], eyeR[0] - eyeL[0]);
  const mid = [(eyeL[0] + eyeR[0]) / 2, (eyeL[1] + eyeR[1]) / 2];
  const k = EYE_GAP / gap;

  // Fotoğrafı düzeltilmiş düzende çiz: gözler yatay, göz ortası EYE_MID'de.
  const aligned = document.createElement('canvas');
  aligned.width = aligned.height = HEAD_SIZE;
  const actx = aligned.getContext('2d', { willReadFrequently: true });
  actx.imageSmoothingQuality = 'high';
  actx.translate(EYE_MID[0], EYE_MID[1]);
  actx.rotate(-angle);
  actx.scale(k, k);
  actx.translate(-mid[0], -mid[1]);
  actx.drawImage(photo, 0, 0);
  actx.setTransform(1, 0, 0, 1, 0, 0);

  const toAligned = ([x, y]) => {
    const dx = (x - mid[0]) * k;
    const dy = (y - mid[1]) * k;
    const c = Math.cos(-angle);
    const s = Math.sin(-angle);
    return [EYE_MID[0] + dx * c - dy * s, EYE_MID[1] + dx * s + dy * c];
  };
  const chinA = toAligned(chin);
  const mouthA = toAligned(mouth);
  const jaw = lm.slice(0, 17).map(p => toAligned([p.x, p.y]));

  // Kişi maskesi (saç dahil). Kenarları fotoğraf dışına taşan bölgeler boş kalır.
  const covered = document.createElement('canvas');
  covered.width = covered.height = HEAD_SIZE;
  const cctx = covered.getContext('2d', { willReadFrequently: true });
  cctx.translate(EYE_MID[0], EYE_MID[1]);
  cctx.rotate(-angle);
  cctx.scale(k, k);
  cctx.translate(-mid[0], -mid[1]);
  cctx.fillStyle = '#fff';
  cctx.fillRect(0, 0, photo.width, photo.height);
  const inside = cctx.getImageData(0, 0, HEAD_SIZE, HEAD_SIZE).data;

  const mask = segment(aligned);
  const pixels = actx.getImageData(0, 0, HEAD_SIZE, HEAD_SIZE);
  const d = pixels.data;

  // Çenenin altı kesilir; kesim çizgisi çene hattını takip edip boyuna doğru daralır.
  const faceHalf = Math.abs(jaw[16][0] - jaw[0][0]) / 2;
  const cutY = chinA[1] + EYE_GAP * 0.07;
  const feather = EYE_GAP * 0.14;
  const sideLimit = faceHalf * 1.9;
  const sample = (x, y) => {
    const fx = Math.min(SEG - 1, Math.max(0, (x / HEAD_SIZE) * SEG - 0.5));
    const fy = Math.min(SEG - 1, Math.max(0, (y / HEAD_SIZE) * SEG - 0.5));
    const x0 = Math.floor(fx), y0 = Math.floor(fy);
    const x1 = Math.min(SEG - 1, x0 + 1), y1 = Math.min(SEG - 1, y0 + 1);
    const tx = fx - x0, ty = fy - y0;
    const a = mask[y0 * SEG + x0] * (1 - tx) + mask[y0 * SEG + x1] * tx;
    const b = mask[y1 * SEG + x0] * (1 - tx) + mask[y1 * SEG + x1] * tx;
    return a * (1 - ty) + b * ty;
  };

  // Yüz ovali her zaman tam görünür; maske bazen açık tenli yüzü kaçırabilir.
  const ovalCx = EYE_MID[0];
  const ovalCy = (EYE_MID[1] + chinA[1]) / 2 - EYE_GAP * 0.1;
  const ovalRx = faceHalf * 0.92;
  const ovalRy = (chinA[1] - EYE_MID[1]) * 0.5 + EYE_GAP * 0.55;

  // Saç rengi: başın tepesindeki kişi pikselleri. Çene altına sarkan saç bu renge göre seçilir,
  // böylece ceket ve gömlek yakası kesilir.
  const hairPx = [];
  for (let y = 0; y < EYE_MID[1] - EYE_GAP * 0.95; y += 2) {
    for (let x = EYE_MID[0] - faceHalf; x < EYE_MID[0] + faceHalf; x += 2) {
      const p = (y * HEAD_SIZE + Math.round(x)) * 4;
      if (sample(x, y) > 0.8 && inside[p + 3] > 250) hairPx.push([d[p], d[p + 1], d[p + 2]]);
    }
  }
  let hair = null;
  if (hairPx.length > 60) {
    hair = [0, 1, 2].map(ch => hairPx.map(c => c[ch]).sort((a, b) => a - b)[hairPx.length >> 1]);
  }
  // Çene hattı: yüz çizgisinin içi her zaman kalır. Ağız hizasının altında hattın dışında
  // kalan pikseller (boyun, yaka, ceket) yalnızca saç rengindeyse tutulur.
  const jawMask = document.createElement('canvas');
  jawMask.width = jawMask.height = HEAD_SIZE;
  const jctx = jawMask.getContext('2d', { willReadFrequently: true });
  const grow = ([x, y]) => [EYE_MID[0] + (x - EYE_MID[0]) * 1.04, y + (y - mouthA[1]) * 0.04];
  jctx.beginPath();
  jctx.moveTo(jaw[0][0], 0);
  jaw.map(grow).forEach(([x, y]) => jctx.lineTo(x, y));
  jctx.lineTo(jaw[16][0], 0);
  jctx.closePath();
  jctx.fillStyle = '#fff';
  jctx.fill();
  const jawIn = jctx.getImageData(0, 0, HEAD_SIZE, HEAD_SIZE).data;
  const below = mouthA[1];
  const hairDrop = hair ? EYE_GAP * (found.gender === 'female' ? 1.1 : 0.35) : 0;
  const hairWide = found.gender === 'female' ? 1.75 : 1.3;

  let opaque = 0;
  let minX = HEAD_SIZE, minY = HEAD_SIZE, maxX = 0, maxY = 0;
  for (let y = 0, i = 0; y < HEAD_SIZE; y++) {
    for (let x = 0; x < HEAD_SIZE; x++, i++) {
      const p = i * 4;
      const seg = smooth(0.35, 0.75, sample(x, y));
      const oval = 1 - smooth(0.82, 1, Math.hypot((x - ovalCx) / ovalRx, (y - ovalCy) / ovalRy));
      const lateral = 1 - smooth(sideLimit * 0.9, sideLimit, Math.abs(x - EYE_MID[0]));
      let a = Math.max(seg, oval) * lateral * (inside[p + 3] / 255);
      if (y > below && !jawIn[p + 3]) {
        let keep = 0;
        if (hair) {
          const dist = Math.hypot(d[p] - hair[0], d[p + 1] - hair[1], d[p + 2] - hair[2]);
          const rel = Math.abs(x - EYE_MID[0]) / faceHalf;
          keep = (1 - smooth(50, 90, dist)) * (1 - smooth(cutY + hairDrop - feather, cutY + hairDrop, y)) *
            (1 - smooth(hairWide - 0.2, hairWide, rel));
          // Çenenin hemen altı boyundur; öne düşen saç nadirdir, orası hep kesilir.
          if (y > chinA[1]) keep *= smooth(0.7, 0.95, rel);
          keep = smooth(0.3, 0.8, keep);
        }
        // Ağız hizasından itibaren yumuşak geçiş, sert kenar oluşmasın.
        a *= Math.max(keep, 1 - smooth(below, below + feather, y));
      } else if (y > chinA[1]) {
        a = Math.min(a, 1 - smooth(chinA[1], cutY, y));
      }
      d[p + 3] = Math.round(a * 255);
      if (a > 0.5) {
        opaque++;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }
  actx.putImageData(pixels, 0, 0);

  return {
    head: aligned,
    gender: found.gender === 'female' ? 'female' : 'male',
    genderScore: found.genderProbability,
    bounds: [minX, minY, maxX, maxY],
    chin: chinA,
    mouth: mouthA,
    faceHalf,
    coverage: opaque / (HEAD_SIZE * HEAD_SIZE),
  };
}
