// Oyunun insansı avatarı: kadın/erkek modelleri, dokunma tepkileri, boşta hareketler ve yüz ifadeleri.
import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { AvatarSkin, GENDERS } from './avatar_textures.js';

const BLANK = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';
const FIGHTER_HEIGHT = 2.1;
const RAW_HEIGHT = { male: 182.2, female: 173.5 };
const HEAD_SCALE = 0.36;

// FaceAlignmentProcessor çıktısındaki sabit noktalar (512x512): gözler y=0.425, göz arası 0.295.
const FACE_LANDMARKS = [[180.5, 217.6], [331.5, 217.6], [256, 376]];

const MORPHS = {
  blinkL: 'AK_09_EyeBlinkLeft',
  blinkR: 'AK_10_EyeBlinkRight',
  smileL: 'AK_44_MouthSmileLeft',
  smileR: 'AK_45_MouthSmileRight',
  jaw: 'AK_25_JawOpen',
  brow: 'AK_03_BrowInnerUp',
  wideL: 'AK_21_EyeWideLeft',
  wideR: 'AK_22_EyeWideRight',
  squintL: 'AK_19_EyeSquintLeft',
  squintR: 'AK_20_EyeSquintRight',
  funnel: 'AK_32_MouthFunnel',
};

const EXPRESSIONS = {
  idle: { smileL: 0.14, smileR: 0.14 },
  hit: { jaw: 0.6, brow: 0.9, wideL: 1, wideR: 1 },
  gut: { jaw: 0.8, funnel: 0.45, brow: 0.7, squintL: 0.8, squintR: 0.8 },
  dizzy: { jaw: 0.22, brow: 0.5, squintL: 0.45, squintR: 0.45 },
  wet: { jaw: 0.18, squintL: 1, squintR: 1, brow: 0.6 },
  laugh: { smileL: 1, smileR: 1, jaw: 0.45, squintL: 0.6, squintR: 0.6 },
  yawn: { jaw: 1, squintL: 1, squintR: 1, brow: 0.3 },
  ouch: { jaw: 0.5, squintL: 1, squintR: 1, brow: 0.9 },
};

// idle: kullanıcı dokunmadığında karakterin kendi kendine yaptığı hareketler.
const GESTURES = {
  look: { dur: 3.2, idle: true },
  scratch: { dur: 2.6, idle: true },
  stretch: { dur: 3.4, idle: true, expr: 'yawn' },
  laugh: { dur: 1.7, expr: 'laugh' },
  hop: { dur: 1.5, expr: 'ouch' },
  fall: { dur: 3.6, expr: 'dizzy' },
};

const smoothstep = (a, b, x) => {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`Görsel yüklenemedi: ${url.slice(0, 60)}`));
    img.src = url;
  });
}

const handMat = new THREE.MeshStandardMaterial({ color: 0xf0c3a0, roughness: 0.6 });

// Tokat düğmesiyle ekrana gelen açık el.
function buildStrikeHand() {
  const hand = new THREE.Group();
  const palm = new THREE.Mesh(new THREE.SphereGeometry(0.17, 20, 16), handMat);
  palm.scale.set(1, 1.1, 0.42);
  hand.add(palm);
  for (let i = 0; i < 4; i++) {
    const finger = new THREE.Mesh(new THREE.CapsuleGeometry(0.04, 0.17, 6, 12), handMat);
    finger.position.set(-0.12 + i * 0.08, 0.27 - Math.abs(i - 1.5) * 0.025, 0);
    hand.add(finger);
  }
  const thumb = new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.12, 6, 12), handMat);
  thumb.position.set(0.19, 0.03, 0.02);
  thumb.rotation.z = -0.7;
  hand.add(thumb);
  hand.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return hand;
}

// Yumruk düğmesiyle ekrana gelen kol ve yumruk; parmak boğumları karaktere bakar.
function buildStrikeFist() {
  const fist = new THREE.Group();
  const palm = new THREE.Mesh(new THREE.SphereGeometry(0.17, 20, 16), handMat);
  palm.scale.set(1, 0.9, 0.85);
  fist.add(palm);
  for (let i = 0; i < 4; i++) {
    const knuckle = new THREE.Mesh(new THREE.SphereGeometry(0.055, 12, 10), handMat);
    knuckle.position.set(-0.12 + i * 0.08, 0.05, -0.13);
    fist.add(knuckle);
  }
  const arm = new THREE.Mesh(new THREE.CapsuleGeometry(0.09, 0.5, 8, 16), handMat);
  arm.rotation.x = Math.PI / 2;
  arm.position.z = 0.42;
  fist.add(arm);
  fist.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return fist;
}

// Tekme düğmesiyle ekrana gelen bacak ve ayakkabı; burun karaktere bakar.
function buildStrikeBoot() {
  const shoeMat = new THREE.MeshStandardMaterial({ color: 0x1b1c22, roughness: 0.5 });
  const soleMat = new THREE.MeshStandardMaterial({ color: 0xe8e8e2, roughness: 0.7 });
  const legMat = new THREE.MeshStandardMaterial({ color: 0x23252e, roughness: 0.85 });
  const boot = new THREE.Group();
  const shoe = new THREE.Mesh(new THREE.SphereGeometry(0.17, 20, 16), shoeMat);
  shoe.scale.set(0.8, 0.72, 1.7);
  shoe.position.z = -0.12;
  boot.add(shoe);
  const sole = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.04, 0.56), soleMat);
  sole.position.set(0, -0.12, -0.12);
  boot.add(sole);
  const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.11, 1.1, 16), legMat);
  leg.position.set(0, -0.31, 0.55);
  leg.rotation.x = -0.96;
  boot.add(leg);
  boot.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return boot;
}

function buildHeadgear(headGroup, kitMat, goldMat) {
  const map = { pro_hair: new THREE.Group(), bald_pro: new THREE.Group() };

  const helm = new THREE.Group();
  helm.visible = false;
  const browPad = new THREE.Mesh(new THREE.TorusGeometry(0.355, 0.058, 14, 32, Math.PI * 1.15), kitMat);
  browPad.rotation.x = Math.PI / 2 - 0.12;
  browPad.rotation.z = -0.22;
  browPad.position.set(0, 0.19, 0.03);
  helm.add(browPad);
  const backPad = new THREE.Mesh(new THREE.SphereGeometry(0.395, 24, 18, 0, Math.PI * 2, 0, Math.PI * 0.55), kitMat);
  backPad.rotation.x = -0.55;
  backPad.scale.set(0.95, 1.12, 1);
  helm.add(backPad);
  [-1, 1].forEach(side => {
    const guard = new THREE.Mesh(new THREE.SphereGeometry(0.115, 16, 14), kitMat);
    guard.scale.set(0.55, 1.15, 0.95);
    guard.position.set(side * 0.31, -0.06, 0.2);
    helm.add(guard);
  });
  headGroup.add(helm);
  map.boxing_helm = helm;

  const crown = new THREE.Group();
  crown.visible = false;
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.29, 0.26, 0.12, 24, 1, true), goldMat);
  base.position.set(0, 0.45, 0.02);
  crown.add(base);
  const gemMat = new THREE.MeshStandardMaterial({ color: 0xff1744, emissive: 0x880e4f, roughness: 0.15 });
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    const spike = new THREE.Mesh(new THREE.ConeGeometry(0.065, 0.14, 4), goldMat);
    spike.position.set(Math.sin(a) * 0.275, 0.56, Math.cos(a) * 0.275 + 0.02);
    crown.add(spike);
    const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.028, 0), gemMat);
    gem.position.set(Math.sin(a) * 0.29, 0.45, Math.cos(a) * 0.29 + 0.02);
    crown.add(gem);
  }
  headGroup.add(crown);
  map.crown = crown;
  return map;
}

function pruneMorphs(mesh) {
  const dict = mesh.morphTargetDictionary;
  const geo = mesh.geometry;
  if (!dict) return;
  const keys = Object.keys(MORPHS).filter(k => dict[`blendShape1.${MORPHS[k]}`] !== undefined);
  const indices = keys.map(k => dict[`blendShape1.${MORPHS[k]}`]);
  for (const attr of Object.keys(geo.morphAttributes)) {
    geo.morphAttributes[attr] = indices.map(i => geo.morphAttributes[attr][i]);
  }
  mesh.morphTargetDictionary = Object.fromEntries(keys.map((k, i) => [k, i]));
  mesh.morphTargetInfluences = new Array(keys.length).fill(0);
}

const slapUniform = { value: new THREE.Vector2(0, 1) };

function addSlapMark(material) {
  material.onBeforeCompile = shader => {
    shader.uniforms.uSlap = slapUniform;
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform vec2 uSlap;')
      .replace('#include <map_fragment>', `#include <map_fragment>
      if (uSlap.x > 0.01) {
        vec2 px = vec2(vMapUv.x, 1.0 - vMapUv.y) * 1024.0;
        float ang = uSlap.y * 0.32;
        mat2 rot = mat2(cos(ang), -sin(ang), sin(ang), cos(ang));
        vec2 q = rot * (px - vec2(uSlap.y >= 0.0 ? 614.0 : 410.0, 396.0));
        float mark = 1.0 - smoothstep(0.72, 1.0, length(q / vec2(46.0, 40.0)));
        for (int i = 0; i < 4; i++) {
          vec2 f = (q - vec2(-36.0 + float(i) * 24.0, -52.0)) / vec2(10.0, 28.0);
          mark = max(mark, 1.0 - smoothstep(0.7, 1.0, length(f)));
        }
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.95, 0.05, 0.16), mark * uSlap.x * 0.55);
      }`);
  };
  material.customProgramCacheKey = () => 'avatar-head-slap';
}

// ---------- Fotoğraf kafası ----------
// Kesilmiş kafa fotoğrafı (512 kare, saydam), gözler PHOTO_EYE_MID'de ve PHOTO_EYE_GAP aralıkla durur.
const PHOTO_SIZE = 512;
const PHOTO_EYE_GAP = 88;
const PHOTO_EYE_MID = [256, 232];

// Android tarafındaki eski yüz çıktısını (gözler FACE_LANDMARKS'ta, saydamsız) fotoğraf kafasına çevirir.
function legacyFaceToHead(image) {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = PHOTO_SIZE;
  const ctx = canvas.getContext('2d');
  const gap = FACE_LANDMARKS[1][0] - FACE_LANDMARKS[0][0];
  const k = PHOTO_EYE_GAP / gap;
  ctx.translate(PHOTO_EYE_MID[0] - 256 * k, PHOTO_EYE_MID[1] - FACE_LANDMARKS[0][1] * k);
  ctx.scale(k, k);
  ctx.drawImage(image, 0, 0, 512, 512);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const g = ctx.createRadialGradient(0, 0, 0.82, 0, 0, 1);
  g.addColorStop(0, 'rgba(0,0,0,1)');
  g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.globalCompositeOperation = 'destination-in';
  const rx = PHOTO_EYE_GAP * 1.12;
  const ry = PHOTO_EYE_GAP * 1.45;
  ctx.setTransform(rx, 0, 0, ry, PHOTO_EYE_MID[0], PHOTO_EYE_MID[1] + PHOTO_EYE_GAP * 0.42);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(0, 0, 1, 0, Math.PI * 2);
  ctx.fill();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const mouthY = PHOTO_EYE_MID[1] + (FACE_LANDMARKS[2][1] - FACE_LANDMARKS[0][1]) * k;
  return {
    canvas,
    mouth: [256, mouthY],
    chin: [256, mouthY + PHOTO_EYE_GAP * 0.75],
    faceHalf: PHOTO_EYE_GAP * 1.05,
    bounds: [256 - rx, PHOTO_EYE_MID[1] + PHOTO_EYE_GAP * 0.42 - ry, 256 + rx, PHOTO_EYE_MID[1] + PHOTO_EYE_GAP * 0.42 + ry],
  };
}

function averageColor(canvas, x0, y0, x1, y1) {
  const data = canvas.getContext('2d').getImageData(x0, y0, Math.max(1, x1 - x0), Math.max(1, y1 - y0)).data;
  const sum = [0, 0, 0];
  let n = 0;
  for (let p = 0; p < data.length; p += 4) {
    if (data[p + 3] < 200) continue;
    sum[0] += data[p]; sum[1] += data[p + 1]; sum[2] += data[p + 2];
    n++;
  }
  return n ? new THREE.Color(sum[0] / n / 255, sum[1] / n / 255, sum[2] / n / 255).convertSRGBToLinear() : null;
}

const photoSlapUniform = { value: new THREE.Vector2(0, 1) };

function addPhotoSlapMark(material) {
  const cheekX = PHOTO_EYE_GAP * 0.8 / PHOTO_SIZE;
  const cheekY = (PHOTO_EYE_MID[1] + PHOTO_EYE_GAP * 0.8) / PHOTO_SIZE;
  material.onBeforeCompile = shader => {
    shader.uniforms.uSlap = photoSlapUniform;
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform vec2 uSlap;')
      .replace('#include <map_fragment>', `#include <map_fragment>
      if (uSlap.x > 0.01) {
        vec2 px = vec2(vMapUv.x, 1.0 - vMapUv.y);
        vec2 c = vec2(0.5 + (uSlap.y >= 0.0 ? ${cheekX.toFixed(4)} : -${cheekX.toFixed(4)}), ${cheekY.toFixed(4)});
        vec2 q = (px - c) * ${PHOTO_SIZE.toFixed(1)};
        float mark = 1.0 - smoothstep(0.6, 1.0, length(q / vec2(30.0, 26.0)));
        for (int i = 0; i < 4; i++) {
          vec2 f = (q - vec2(-22.0 + float(i) * 15.0, -32.0)) / vec2(6.0, 17.0);
          mark = max(mark, 1.0 - smoothstep(0.7, 1.0, length(f)));
        }
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.95, 0.05, 0.16), mark * uSlap.x * 0.5);
      }`);
  };
  material.customProgramCacheKey = () => 'avatar-photo-slap';
}

// Fotoğrafı kafa biçiminde öne doğru kubbeleşen bir kabuğa giydirir; arkasına saç renginde bir kafa küresi koyar.
function buildPhotoHead(avatar, head) {
  const rest = avatar.photoRest;
  const eyeMid = rest.eyeL.clone().add(rest.eyeR).multiplyScalar(0.5);
  const gapWorld = rest.eyeL.distanceTo(rest.eyeR);
  const s = gapWorld / PHOTO_EYE_GAP; // fotoğraf pikseli başına dünya birimi
  const skull = rest.skull;
  const centerZ = skull ? (skull.min.z + skull.max.z) / 2 : rest.headPos.z;
  const front = Math.max(gapWorld * 1.1, eyeMid.z - centerZ + gapWorld * 0.55,
    skull ? skull.max.z - centerZ + gapWorld * 0.1 : 0);

  const [bx0, by0, bx1] = head.bounds;
  const faceHalf = head.faceHalf;
  const chinY = head.chin[1];
  // Kafa elipsi (fotoğraf pikseli): yüz genişliği ve tepeden çeneye yükseklik.
  const rx = Math.max(faceHalf * 1.08, Math.min((bx1 - bx0) / 2, faceHalf * 1.45));
  const top = Math.min(by0, PHOTO_EYE_MID[1] - PHOTO_EYE_GAP * 1.4);
  const cy = (top + chinY) / 2;
  const ry = (chinY - top) / 2 * 1.04;

  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = PHOTO_SIZE;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(head.canvas, 0, 0);
  const base = ctx.getImageData(0, 0, PHOTO_SIZE, PHOTO_SIZE);

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;

  const geo = new THREE.PlaneGeometry(PHOTO_SIZE * s, PHOTO_SIZE * s, 64, 64);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const px = pos.getX(i) / s + PHOTO_SIZE / 2;
    const py = PHOTO_SIZE / 2 - pos.getY(i) / s;
    const nx = (px - PHOTO_EYE_MID[0]) / rx;
    const ny = (py - cy) / ry;
    const r2 = nx * nx + ny * ny;
    // Elips içinde kubbe, dışında (saç uçları) yumuşakça geriye kıvrılan kenar.
    const dome = r2 < 1 ? Math.sqrt(1 - r2) : 0;
    const rim = r2 >= 1 ? -Math.min(0.5, (Math.sqrt(r2) - 1) * 0.9) : 0;
    // Burun bölgesine hafif çıkıntı.
    const nose = Math.exp(-(((px - PHOTO_EYE_MID[0]) / (PHOTO_EYE_GAP * 0.32)) ** 2 +
      ((py - (PHOTO_EYE_MID[1] + PHOTO_EYE_GAP * 0.42)) / (PHOTO_EYE_GAP * 0.42)) ** 2));
    pos.setZ(i, dome * front + rim * front + nose * gapWorld * 0.12);
  }
  geo.computeVertexNormals();

  const shellMat = new THREE.MeshStandardMaterial({
    map: tex, emissiveMap: tex, emissive: 0xffffff, emissiveIntensity: 0.32,
    roughness: 0.78, metalness: 0, transparent: true, alphaTest: 0.08, side: THREE.DoubleSide,
  });
  addPhotoSlapMark(shellMat);
  const shell = new THREE.Mesh(geo, shellMat);
  shell.castShadow = true;
  // Gözler fotoğrafta (256, 232) noktasında; düzlemin ortası (256, 256).
  shell.position.set((PHOTO_SIZE / 2 - PHOTO_EYE_MID[0]) * s, (PHOTO_EYE_MID[1] - PHOTO_SIZE / 2) * s, 0);

  // Arka kafa: saç rengi (yoksa ten rengi) elipsoit, ön kabuğun biraz içinde.
  const hairColor = averageColor(head.canvas, Math.round(256 - faceHalf * 0.6), Math.max(0, Math.round(top + 4)),
    Math.round(256 + faceHalf * 0.6), Math.round(top + PHOTO_EYE_GAP * 0.35));
  const skinColor = averageColor(head.canvas, Math.round(256 - PHOTO_EYE_GAP * 0.9), Math.round(PHOTO_EYE_MID[1] + PHOTO_EYE_GAP * 0.55),
    Math.round(256 - PHOTO_EYE_GAP * 0.55), Math.round(PHOTO_EYE_MID[1] + PHOTO_EYE_GAP * 0.85));
  const backMat = new THREE.MeshStandardMaterial({ color: hairColor || skinColor || new THREE.Color(0x3a2a20), roughness: 0.85 });
  // Modelin kendi kafatası bu kürenin içinde kalır; yalnızca boynu görünür.
  const backGeo = new THREE.SphereGeometry(1, 40, 28);
  let backX = rx * s * 0.94;
  let backY = ry * s * 0.96;
  let backZ = front * 0.95;
  let backCy = (PHOTO_EYE_MID[1] - cy) * s;
  // Modelin kafatası kesildiği için küre fotoğraf silüetinin içinde kalır; derinliği modelin kafasınca.
  if (skull) backZ = Math.max(backZ, centerZ - skull.min.z);
  // Ön yarı basık tutulur ki fotoğrafın arkasında kalsın; arka yarı kafatasını sarar.
  // Ön-alt kısım ağız hizasının üstünde biter ki çenenin altından saç rengi görünmesin.
  const bp = backGeo.attributes.position;
  const frontBottom = Math.max(gapWorld * 0.2, backCy + gapWorld * 0.35);
  const backBottom = Math.min(backY, backCy + gapWorld * 1.15); // ense ağız hizasında biter, boyna sarkmaz
  for (let i = 0; i < bp.count; i++) {
    const z = bp.getZ(i);
    const y = bp.getY(i);
    // Arkada enseye kadar iner, yanlarda ve önde ağız hizasının üstünde kalır.
    const down = y < 0 ? backBottom + (frontBottom - backBottom) * smoothstep(-0.65, -0.05, z) : backY;
    bp.setXYZ(i, bp.getX(i) * backX, y * down + backCy, z * (z > 0 ? front * 0.55 : backZ));
  }
  backGeo.computeVertexNormals();
  const back = new THREE.Mesh(backGeo, backMat);
  back.castShadow = true;

  const group = new THREE.Group();
  group.add(back, shell);

  // Grup holder uzayında göz ortasına (derinlikte kafa merkezine) oturur, sonra kafa kemiğine bağlanır.
  const desired = new THREE.Matrix4().makeTranslation(eyeMid.x, eyeMid.y, centerZ);
  const local = rest.headWorldInv.clone().multiply(desired);
  local.decompose(group.position, group.quaternion, group.scale);
  avatar.bones.Head.add(group);

  return {
    group, canvas, ctx, base, tex,
    materials: [shellMat, backMat],
    geometries: [geo, back.geometry],
  };
}

function disposePhotoHead(ph) {
  ph.group.parent?.remove(ph.group);
  ph.tex.dispose();
  ph.materials.forEach(m => m.dispose());
  ph.geometries.forEach(g => g.dispose());
}

async function buildAvatar(gender) {
  const dir = `./avatar/${gender}`;
  const manager = new THREE.LoadingManager();
  manager.setURLModifier(u => (/\.(tga|dds|bmp|png|jpe?g)$/i.test(u) ? BLANK : u));
  const texLoader = new THREE.TextureLoader();

  const [fbx, headImg, bodyImg, headNormal, bodyNormal, opacity] = await Promise.all([
    new FBXLoader(manager).loadAsync(`${dir}/avatar.fbx`),
    loadImage(`${dir}/head_color.jpg`),
    loadImage(`${dir}/body_color.jpg`),
    texLoader.loadAsync(`${dir}/head_normal.jpg`),
    texLoader.loadAsync(`${dir}/body_normal.jpg`),
    texLoader.loadAsync(`${dir}/opacity_color.png`),
  ]);
  opacity.colorSpace = THREE.SRGBColorSpace;

  const skin = new AvatarSkin(GENDERS[gender], headImg, bodyImg);
  const makeTex = canvas => {
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 4;
    return tex;
  };
  const headTex = makeTex(skin.headCanvas);
  const bodyTex = makeTex(skin.bodyCanvas);

  let mesh = null;
  fbx.traverse(o => { if (o.isSkinnedMesh) mesh = o; });
  if (!mesh) throw new Error('Model içinde iskeletli gövde bulunamadı');
  mesh.frustumCulled = false;
  mesh.castShadow = true;
  pruneMorphs(mesh);

  mesh.material = (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).map(old => {
    old.dispose();
    if (/head/i.test(old.name)) {
      const m = new THREE.MeshStandardMaterial({
        name: old.name, map: headTex, normalMap: headNormal,
        normalScale: new THREE.Vector2(0.55, 0.55), roughness: 0.62, metalness: 0,
      });
      addSlapMark(m);
      return m;
    }
    if (/opacity/i.test(old.name)) {
      return new THREE.MeshStandardMaterial({
        name: old.name, map: opacity, roughness: 0.7, metalness: 0,
        transparent: true, alphaTest: 0.32, side: THREE.DoubleSide,
      });
    }
    return new THREE.MeshStandardMaterial({
      name: old.name, map: bodyTex, normalMap: bodyNormal, roughness: 0.86, metalness: 0,
    });
  });

  const scale = FIGHTER_HEIGHT / RAW_HEIGHT[gender];
  const holder = new THREE.Group();
  holder.scale.setScalar(scale);
  holder.add(fbx);
  holder.updateMatrixWorld(true);

  const bones = {};
  fbx.traverse(o => { if (o.isBone) bones[o.name.replace('Bip01_', '')] = o; });
  const world = o => o.getWorldPosition(new THREE.Vector3());
  const worldQ = o => o.getWorldQuaternion(new THREE.Quaternion());

  if (world(bones.LEye).z < world(bones.Head).z) {
    fbx.rotation.y = Math.PI;
    holder.updateMatrixWorld(true);
  }

  // Ek dönüşler dünya eksenlerinde tanımlanır, kemiklerin kendi eksen yönleri önemsizleşir.
  const rec = bone => {
    const inv = worldQ(bone.parent).invert();
    return {
      bone,
      base: bone.quaternion.clone(),
      basePos: bone.position.clone(),
      x: new THREE.Vector3(1, 0, 0).applyQuaternion(inv),
      y: new THREE.Vector3(0, 1, 0).applyQuaternion(inv),
      z: new THREE.Vector3(0, 0, 1).applyQuaternion(inv),
    };
  };
  const rig = {};
  for (const name of ['Spine', 'Spine1', 'Spine2', 'Neck', 'Head', 'L_Thigh', 'R_Thigh', 'L_Calf', 'R_Calf', 'L_Foot', 'R_Foot', 'L_UpperArm', 'R_UpperArm']) {
    rig[name] = rec(bones[name]);
  }

  const thighLen = world(bones.L_Thigh).distanceTo(world(bones.L_Calf));
  const calfLen = world(bones.L_Calf).distanceTo(world(bones.L_Foot));

  const headRestInv = worldQ(bones.Head).invert();
  const headCenter = world(bones.Head).add(new THREE.Vector3(0, 0.1, 0.018));
  const headOffset = bones.Head.worldToLocal(headCenter.clone());
  const spineRestInv = worldQ(bones.Spine1).invert();

  let headUpAxis = 0;
  let bestDot = 0;
  const headRest = worldQ(bones.Head);
  [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)].forEach((axis, i) => {
    const dot = Math.abs(axis.applyQuaternion(headRest).y);
    if (dot > bestDot) { bestDot = dot; headUpAxis = i; }
  });

  const armRest = {};
  const aim = (bone, child, target) => {
    const dir = world(child).sub(world(bone)).normalize();
    const delta = new THREE.Quaternion().setFromUnitVectors(dir, target.clone().normalize());
    const next = delta.multiply(worldQ(bone));
    bone.quaternion.copy(worldQ(bone.parent).invert().multiply(next));
    bone.updateWorldMatrix(true, true);
  };
  const capture = (side, upperDir, foreDir) => {
    const upper = bones[`${side}_UpperArm`];
    const fore = bones[`${side}_Forearm`];
    upper.quaternion.copy(armRest[side].upper);
    fore.quaternion.copy(armRest[side].fore);
    upper.updateWorldMatrix(true, true);
    aim(upper, fore, upperDir);
    aim(fore, bones[`${side}_Hand`], foreDir);
    return { upper: upper.quaternion.clone(), fore: fore.quaternion.clone() };
  };

  const centerX = world(bones.Spine2).x;
  const arms = {};
  const v = (x, y, z) => new THREE.Vector3(x, y, z);
  for (const side of ['L', 'R']) {
    const out = Math.sign(world(bones[`${side}_UpperArm`]).x - centerX);
    armRest[side] = { upper: bones[`${side}_UpperArm`].quaternion.clone(), fore: bones[`${side}_Forearm`].quaternion.clone() };
    arms[side] = {
      out,
      open: capture(side, v(out * 0.85, -0.45, 0.1), v(out * 0.75, -0.35, 0.35)),
      clutch: capture(side, v(out * 0.28, -0.9, 0.3), v(-out * 0.88, 0.1, 0.46)),
      scratch: capture(side, v(out * 0.75, 0.25, 0.2), v(-out * 0.55, 0.75, 0.1)),
      stretch: capture(side, v(out * 0.2, 1, 0), v(out * 0.05, 1, 0.05)),
      relaxed: capture(side, v(out * 0.17, -1, 0.02), v(out * 0.1, -1, 0.15)),
    };
  }

  // Fotoğraf kafasının yerleşimi için dinlenme pozundaki göz ve kafa ölçüleri (holder uzayında).
  const photoRest = {
    eyeL: world(bones.LEye),
    eyeR: world(bones.REye),
    headPos: world(bones.Head),
    headWorldInv: bones.Head.matrixWorld.clone().invert(),
    skull: null,
  };
  // Modelin kafatasının sınırları (boyun hariç): fotoğraf kafası bunu tamamen örtmeli.
  {
    const geo = mesh.geometry;
    const headIndex = mesh.material.findIndex(m => /head/i.test(m.name));
    const posAttr = geo.attributes.position;
    const idx = geo.index;
    const eyeY = (photoRest.eyeL.y + photoRest.eyeR.y) / 2;
    const gap = photoRest.eyeL.distanceTo(photoRest.eyeR);
    const box = new THREE.Box3();
    const p = new THREE.Vector3();
    mesh.updateMatrixWorld(true);
    for (const group of geo.groups) {
      if (group.materialIndex !== headIndex) continue;
      for (let i = group.start; i < group.start + group.count; i++) {
        const vi = idx ? idx.getX(i) : i;
        p.fromBufferAttribute(posAttr, vi).applyMatrix4(mesh.matrixWorld);
        if (p.y > eyeY - gap * 1.6) box.expandByPoint(p);
      }
    }
    if (!box.isEmpty()) photoRest.skull = box;

    // Fotoğraf kafası takılınca modelin kafası çene hizasından kesilir, yalnızca boynu kalır.
    // Boyun ekseni çevresindeki dar silindir ağız hizasına kadar kalır; çene, ense saçı ve kafatası gider.
    const topY = eyeY - gap * 1.2;
    const neckPos = world(bones.Neck);
    const headPos = photoRest.headPos;
    const neckR = gap * 1.3;
    const uvAttr = geo.attributes.uv;
    const tex = skin.headBase;
    const isHair = (u, w) => {
      const x = Math.min(1023, Math.max(0, Math.round(u * 1023)));
      const y = Math.min(1023, Math.max(0, Math.round((1 - w) * 1023)));
      const p = (y * 1024 + x) * 4;
      return Math.max(tex[p], tex[p + 1], tex[p + 2]) < 70;
    };
    const full = { index: idx, groups: geo.groups.map(g => ({ ...g })) };
    const kept = [];
    const groups = [];
    const v = new THREE.Vector3();
    const keepNeck = (a, b, c) => {
      const cx = [a, b, c].reduce((s, vi) => s.add(v.fromBufferAttribute(posAttr, vi).applyMatrix4(mesh.matrixWorld)), new THREE.Vector3()).divideScalar(3);
      if (cx.y > topY) return false;
      const t = Math.min(1.4, Math.max(0, (cx.y - neckPos.y) / Math.max(1e-4, headPos.y - neckPos.y)));
      const ax = neckPos.x + (headPos.x - neckPos.x) * t;
      const az = neckPos.z + (headPos.z - neckPos.z) * t;
      // Çene hizasının altında yalnızca boyun vardır; üstünde (çene/çene altı) dar silindir tutulur.
      if (cx.y > eyeY - gap * 2.05 && Math.hypot(cx.x - ax, cx.z - az) > neckR) return false;
      if (uvAttr) {
        const u = (uvAttr.getX(a) + uvAttr.getX(b) + uvAttr.getX(c)) / 3;
        const w = (uvAttr.getY(a) + uvAttr.getY(b) + uvAttr.getY(c)) / 3;
        if (isHair(u, w)) return false;
      }
      return true;
    };
    for (const group of geo.groups) {
      const start = kept.length;
      for (let i = group.start; i < group.start + group.count; i += 3) {
        const a = idx ? idx.getX(i) : i;
        const b = idx ? idx.getX(i + 1) : i + 1;
        const c = idx ? idx.getX(i + 2) : i + 2;
        if (group.materialIndex === headIndex && !keepNeck(a, b, c)) continue;
        kept.push(a, b, c);
      }
      groups.push({ start, count: kept.length - start, materialIndex: group.materialIndex });
    }
    const cutIndex = new THREE.BufferAttribute(posAttr.count > 65535 ? new Uint32Array(kept) : new Uint16Array(kept), 1);
    photoRest.setHeadCut = on => {
      geo.setIndex(on ? cutIndex : full.index);
      geo.groups = (on ? groups : full.groups).map(g => ({ ...g }));
    };
  }

  return {
    gender, holder, fbx, mesh, skin, headTex, bodyTex, bones, rig, arms, scale, photoRest,
    headMats: mesh.material.filter(m => /opacity/i.test(m.name)),
    thighLen, calfLen, headOffset, headRestInv, spineRestInv, headUpAxis,
    textures: [headTex, bodyTex, headNormal, bodyNormal, opacity],
    morphNow: {},
  };
}

function disposeAvatar(avatar) {
  avatar.textures.forEach(t => t.dispose());
  avatar.holder.traverse(o => {
    if (!o.isMesh) return;
    o.geometry.dispose();
    (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => m.dispose());
  });
}

const q1 = new THREE.Quaternion();
const q2 = new THREE.Quaternion();
const q3 = new THREE.Quaternion();

function turn(r, x, y, z) {
  q1.setFromAxisAngle(r.z, z);
  q2.setFromAxisAngle(r.y, y);
  q3.setFromAxisAngle(r.x, x);
  r.bone.quaternion.copy(q1).multiply(q2).multiply(q3).multiply(r.base);
}

class Fighter {
  constructor(first) {
    this.root = new THREE.Group();
    this.avatar = null;
    this.gender = first.gender;
    this.loadToken = 0;
    this.headSource = null;
    this.photoHead = null;
    this.shirtImage = null;
    this.bandageOn = false;
    this.blinkAt = 2;
    this.blinkStart = -1;
    this.headScaleNow = 1;
    this.gesture = null;
    this.shirtColor = null;
    this.mats = first.mats;

    this.headAnchor = new THREE.Group();
    this.chestPivot = new THREE.Group();
    this.footAnchors = { L: new THREE.Group(), R: new THREE.Group() };
    this.root.add(this.headAnchor, this.chestPivot, this.footAnchors.L, this.footAnchors.R);

    const headGroup = new THREE.Group();
    headGroup.scale.setScalar(HEAD_SCALE);
    this.headAnchor.add(headGroup);
    this.headData = {
      headGroup,
      headRadius: 0.33,
      headgearMap: buildHeadgear(headGroup, this.mats.kit, this.mats.gold),
    };

    const hitMat = new THREE.MeshBasicMaterial({ visible: false });
    const hit = (parent, r, x, y, z, zone) => {
      const m = new THREE.Mesh(new THREE.SphereGeometry(r, 8, 8), hitMat);
      m.position.set(x, y, z);
      m.userData.zone = zone;
      parent.add(m);
      return m;
    };
    this.hitboxes = [
      hit(headGroup, 0.3, 0, -0.34, 0.2, 'chin'),
      hit(headGroup, 0.42, -0.2, 0.04, 0.14, 'head_left'),
      hit(headGroup, 0.42, 0.2, 0.04, 0.14, 'head_right'),
      hit(this.chestPivot, 0.34, 0, 0.02, 0.1, 'body'),
      hit(this.footAnchors.L, 0.2, 0, 0.04, 0.06, 'foot'),
      hit(this.footAnchors.R, 0.2, 0, 0.04, 0.06, 'foot'),
    ];

    this.materials = {
      kitPrimaryMat: this.mats.kit,
      trimMat: this.mats.trim,
      goldMat: this.mats.gold,
      satinShortsMat: { color: { setHex() {} } },
    };
    this.mount(first);
  }

  mount(avatar) {
    if (this.avatar) {
      if (this.photoHead) disposePhotoHead(this.photoHead);
      this.photoHead = null;
      this.root.remove(this.avatar.holder);
      disposeAvatar(this.avatar);
    }
    this.avatar = avatar;
    this.gender = avatar.gender;
    this.root.add(avatar.holder);
    if (this.shirtColor) avatar.skin.setShirt({ color: this.shirtColor });
    if (this.shirtImage) avatar.skin.setShirt({ image: this.shirtImage });
    this.applyPhotoHead();
    avatar.headTex.needsUpdate = true;
    avatar.bodyTex.needsUpdate = true;
  }

  // Yüklenen kafayı mevcut avatara takar; yoksa modelin kendi kafasını gösterir.
  applyPhotoHead() {
    const a = this.avatar;
    if (this.photoHead) disposePhotoHead(this.photoHead);
    this.photoHead = null;
    const head = this.headSource;
    a.headMats.forEach(m => { m.visible = !head; });
    if (a.photoRest.setHeadCut) a.photoRest.setHeadCut(!!head);
    if (!head) {
      a.skin.setFace(null);
      if (this.bandageOn) a.skin.setBandage(true);
      return;
    }
    this.photoHead = buildPhotoHead(a, head);
    // Kol ve bacak teni fotoğraftaki tene yaklaşsın.
    a.skin.setFace(head.canvas, [
      [PHOTO_EYE_MID[0] - PHOTO_EYE_GAP / 2, PHOTO_EYE_MID[1]],
      [PHOTO_EYE_MID[0] + PHOTO_EYE_GAP / 2, PHOTO_EYE_MID[1]],
      head.mouth,
    ]);
    this.drawPhotoBandage();
  }

  drawPhotoBandage() {
    const ph = this.photoHead;
    if (!ph) return;
    ph.ctx.putImageData(ph.base, 0, 0);
    if (this.bandageOn) {
      const ctx = ph.ctx;
      ctx.save();
      ctx.translate(PHOTO_EYE_MID[0] + PHOTO_EYE_GAP * 0.72, PHOTO_EYE_MID[1] + PHOTO_EYE_GAP * 0.72);
      ctx.rotate(-0.3);
      ctx.fillStyle = '#FDE68A';
      ctx.strokeStyle = '#B45309';
      ctx.lineWidth = 3;
      ctx.fillRect(-30, -11, 60, 22);
      ctx.strokeRect(-30, -11, 60, 22);
      ctx.fillStyle = '#FEF3C7';
      ctx.fillRect(-10, -10, 20, 20);
      ctx.restore();
    }
    ph.tex.needsUpdate = true;
  }

  async setGender(gender) {
    if (!GENDERS[gender] || gender === this.gender) return;
    const token = ++this.loadToken;
    this.gender = gender;
    const next = await buildAvatar(gender);
    if (token !== this.loadToken) { disposeAvatar(next); return; }
    this.mount(next);
  }

  // Eski yol (Android): gözleri hizalanmış kare yüz fotoğrafı. Oval kesilip fotoğraf kafası yapılır.
  async setFace(dataUrl) {
    const image = dataUrl ? await loadImage(dataUrl) : null;
    this.headSource = image ? legacyFaceToHead(image) : null;
    this.applyPhotoHead();
    this.avatar.headTex.needsUpdate = true;
    this.avatar.bodyTex.needsUpdate = true;
  }

  // Yeni yol: photo_head.js ile saçıyla birlikte kesilmiş kafa.
  async setPhotoHead(info) {
    if (!info) return this.setFace(null);
    const image = await loadImage(info.headDataUrl);
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = PHOTO_SIZE;
    canvas.getContext('2d').drawImage(image, 0, 0, PHOTO_SIZE, PHOTO_SIZE);
    this.headSource = { canvas, mouth: info.mouth, chin: info.chin, faceHalf: info.faceHalf, bounds: info.bounds };
    this.applyPhotoHead();
    this.avatar.headTex.needsUpdate = true;
    this.avatar.bodyTex.needsUpdate = true;
  }

  async setShirtImage(dataUrl) {
    const image = dataUrl ? await loadImage(dataUrl) : null;
    this.shirtImage = image;
    this.avatar.skin.setShirt({ image });
    this.avatar.bodyTex.needsUpdate = true;
  }

  setSlapMark(alpha, side) {
    slapUniform.value.set(alpha, side);
    photoSlapUniform.value.set(alpha, side);
  }

  setBandage(on) {
    if (this.photoHead) {
      if (this.bandageOn !== on) {
        this.bandageOn = on;
        this.drawPhotoBandage();
      }
      return;
    }
    this.bandageOn = on;
    if (this.avatar.skin.setBandage(on)) this.avatar.headTex.needsUpdate = true;
  }

  setShirtColor(hex) {
    this.shirtColor = hex;
    this.avatar.skin.setShirt({ color: hex });
    this.avatar.bodyTex.needsUpdate = true;
  }

  createStrikeHand() {
    return buildStrikeHand();
  }

  createStrikeFist() {
    return buildStrikeFist();
  }

  createStrikeBoot() {
    return buildStrikeBoot();
  }

  playGesture(name) {
    if (!GESTURES[name]) return;
    if (this.gesture && this.gesture.name === 'fall' && name !== 'fall') return;
    this.gesture = { name, time: 0, side: Math.random() < 0.5 ? 'L' : 'R' };
  }

  cancelIdleGesture() {
    if (this.gesture && GESTURES[this.gesture.name].idle) this.gesture = null;
  }

  clearGesture() {
    this.gesture = null;
  }

  get isBusy() {
    return !!this.gesture;
  }

  applyExpression(expr, t, dt) {
    const a = this.avatar;
    const dict = a.mesh.morphTargetDictionary;
    if (!dict) return;
    const target = EXPRESSIONS[expr] || EXPRESSIONS.idle;
    const rate = Math.min(1, dt * 18);
    for (const key of Object.keys(dict)) {
      if (key === 'blinkL' || key === 'blinkR') continue;
      const now = a.morphNow[key] || 0;
      const next = now + ((target[key] || 0) - now) * rate;
      a.morphNow[key] = next;
      a.mesh.morphTargetInfluences[dict[key]] = next;
    }
    if (t > this.blinkAt) {
      this.blinkStart = t;
      this.blinkAt = t + 2.2 + Math.random() * 3.2;
    }
    const k = (t - this.blinkStart) / 0.15;
    const blink = expr === 'hit' ? 0 : (k >= 0 && k <= 1 ? Math.sin(k * Math.PI) : 0);
    if (dict.blinkL !== undefined) a.mesh.morphTargetInfluences[dict.blinkL] = blink;
    if (dict.blinkR !== undefined) a.mesh.morphTargetInfluences[dict.blinkR] = blink;
  }

  applyPose(t, dt, phys, expr, headScaleTarget) {
    const a = this.avatar;
    const r = a.rig;

    // Oynayan hareketin ilerlemesi ve yumuşak giriş/çıkışı
    let progress = 0;
    let env = 0;
    if (this.gesture) {
      this.gesture.time += dt;
      progress = this.gesture.time / GESTURES[this.gesture.name].dur;
      if (progress >= 1) this.gesture = null;
      else env = smoothstep(0, 0.14, progress) * (1 - smoothstep(0.84, 1, progress));
    }
    const active = this.gesture ? this.gesture.name : null;
    const gestureSide = this.gesture ? this.gesture.side : 'L';
    const weight = name => (active === name ? env : 0);
    const laugh = weight('laugh');
    const stretch = weight('stretch');
    const look = weight('look');
    const scratch = weight('scratch');
    const hop = weight('hop');
    const fall = active === 'fall' ? smoothstep(0, 0.14, progress) * (1 - smoothstep(0.72, 0.94, progress)) : 0;

    const breath = Math.sin(t * 1.5) * 0.012;
    const swayX = Math.sin(t * 0.9) * 0.012;

    // Bacaklar: rahat duruş; ayağına dokununca tek ayak üstünde zıplar.
    const bend = 0.04 + phys.kneeBend * 0.6;
    for (const side of ['L', 'R']) {
      const out = a.arms[side].out;
      const lift = side === gestureSide ? hop : 0;
      const thigh = -bend - lift * 0.95;
      const calf = bend * 1.9 + lift * 1.45;
      turn(r[`${side}_Thigh`], thigh, 0, out * 0.03);
      turn(r[`${side}_Calf`], calf, 0, 0);
      turn(r[`${side}_Foot`], -(thigh + calf) * (1 - lift), 0, 0);
    }
    const drop = (a.thighLen + a.calfLen) * (1 - Math.cos(bend));
    const hopY = hop * Math.abs(Math.sin(t * 9)) * 0.13;
    this.root.position.set(swayX, 0.05 + hopY - drop, this.root.position.z);

    // Çok darbe alınca sırtüstü düşüp geri kalkar.
    a.holder.rotation.x = -1.5 * fall;
    a.holder.position.y = 0.14 * fall;

    // Gövde
    const chestX = phys.chestRotX + breath + laugh * (0.12 + Math.sin(t * 22) * 0.05) - stretch * 0.16;
    const chestY = phys.chestRotY;
    const chestZ = phys.chestRotZ + swayX * 0.5;
    for (const name of ['Spine', 'Spine1', 'Spine2']) turn(r[name], chestX / 3, chestY / 3, chestZ / 3);

    // Boyun ve baş: insan boynu fazla esnemesin diye savrulma kısılır.
    const neckLimit = 0.72;
    const neckX = phys.neckRotX * neckLimit + Math.sin(t * 0.8) * 0.02 - 0.04 - stretch * 0.22 - laugh * 0.12;
    const neckY = phys.neckRotY * neckLimit + Math.sin(t * 0.4) * 0.06 + Math.sin(progress * Math.PI * 2) * 0.6 * look;
    const neckZ = phys.neckRotZ * neckLimit - a.arms[gestureSide].out * 0.16 * scratch;
    turn(r.Neck, neckX * 0.4, neckY * 0.4, neckZ * 0.4);
    turn(r.Head, neckX * 0.6, neckY * 0.6, neckZ * 0.6);

    const shift = 0.3 / a.scale;
    r.Head.bone.position.copy(r.Head.basePos)
      .addScaledVector(r.Head.x, phys.headShiftX * shift)
      .addScaledVector(r.Head.y, phys.headShiftY * shift)
      .addScaledVector(r.Head.z, phys.headShiftZ * shift);

    this.headScaleNow += (headScaleTarget - this.headScaleNow) * Math.min(1, dt * 8);
    const sy = this.headScaleNow * (1 + phys.squash * 0.6);
    const sxz = this.headScaleNow / Math.sqrt(Math.max(0.6, 1 + phys.squash * 0.6));
    const sc = [sxz, sxz, sxz];
    sc[a.headUpAxis] = sy;
    r.Head.bone.scale.set(sc[0], sc[1], sc[2]);

    // Kollar: rahat duruş, darbede savrulma, karnını tutma ve hareketler.
    const open = Math.max(Math.min(1, Math.max(0, phys.guardOpen)), hop * 0.55, fall);
    const clutch = Math.max(Math.min(1, Math.max(0, phys.gutClutch)), laugh * 0.85);
    for (const side of ['L', 'R']) {
      const arm = a.arms[side];
      const upper = a.bones[`${side}_UpperArm`];
      const fore = a.bones[`${side}_Forearm`];
      const rub = side === gestureSide ? scratch : 0;
      upper.quaternion.copy(arm.relaxed.upper).slerp(arm.open.upper, open).slerp(arm.clutch.upper, clutch)
        .slerp(arm.stretch.upper, stretch).slerp(arm.scratch.upper, rub);
      fore.quaternion.copy(arm.relaxed.fore).slerp(arm.open.fore, open).slerp(arm.clutch.fore, clutch)
        .slerp(arm.stretch.fore, stretch).slerp(arm.scratch.fore, rub);
      const axis = r[`${side}_UpperArm`].x;
      q1.setFromAxisAngle(axis, Math.sin(t * 1.5 + (side === 'L' ? 0 : 1.2)) * 0.02);
      upper.quaternion.premultiply(q1);
      if (rub > 0) fore.quaternion.premultiply(q1.setFromAxisAngle(axis, Math.sin(t * 15) * 0.16 * rub));
    }

    const gestureExpr = active ? GESTURES[active].expr : null;
    this.applyExpression(gestureExpr && (expr === 'idle' || active === 'fall') ? gestureExpr : expr, t, dt);

    // Efektlerin ve dokunma alanlarının bağlandığı noktalar kemikleri takip eder.
    this.root.updateMatrixWorld(true);
    const head = a.bones.Head;
    this.headAnchor.position.copy(head.localToWorld(a.headOffset.clone()));
    this.root.worldToLocal(this.headAnchor.position);
    head.getWorldQuaternion(this.headAnchor.quaternion).multiply(a.headRestInv);

    const spine = a.bones.Spine1;
    spine.getWorldPosition(this.chestPivot.position);
    this.root.worldToLocal(this.chestPivot.position);
    spine.getWorldQuaternion(this.chestPivot.quaternion).multiply(a.spineRestInv);

    for (const side of ['L', 'R']) {
      a.bones[`${side}_Foot`].getWorldPosition(this.footAnchors[side].position);
      this.root.worldToLocal(this.footAnchors[side].position);
    }
  }
}

let preloaded = null;

export const AvatarFighter = {
  async preload(gender) {
    const mats = {
      kit: new THREE.MeshPhysicalMaterial({ color: 0xd91b38, roughness: 0.3, metalness: 0.08, clearcoat: 0.6, clearcoatRoughness: 0.24 }),
      trim: new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.4, metalness: 0.06 }),
      gold: new THREE.MeshStandardMaterial({ color: 0xffc800, roughness: 0.24, metalness: 0.8 }),
    };
    const avatar = await buildAvatar(gender);
    avatar.mats = mats;
    preloaded = avatar;
  },
  createCompleteFighter() {
    return new Fighter(preloaded);
  },
};
