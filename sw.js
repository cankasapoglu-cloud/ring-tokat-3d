/* Oyunu ilk açılıştan sonra internetsiz de çalıştırır. Liste build.py tarafından doldurulur. */
const CACHE_NAME = 'ring-tokat-3ce601738a13';
const PRECACHE = ["./", "arena_audio.js", "arena_engine.js", "avatar/female/avatar.fbx", "avatar/female/body_color.jpg", "avatar/female/body_normal.jpg", "avatar/female/head_color.jpg", "avatar/female/head_normal.jpg", "avatar/female/opacity_color.png", "avatar/male/avatar.fbx", "avatar/male/body_color.jpg", "avatar/male/body_normal.jpg", "avatar/male/head_color.jpg", "avatar/male/head_normal.jpg", "avatar/male/opacity_color.png", "avatar/ROCKETBOX_LICENSE.md", "avatar_fighter.js", "avatar_textures.js", "boot.js", "game_ui.js", "icons/icon-180.png", "icons/icon-192.png", "icons/icon-512.png", "index.html", "lib/face-api/face-api.esm.js", "lib/face-api/LICENSE", "lib/three/build/three.module.min.js", "lib/three/examples/jsm/controls/OrbitControls.js", "lib/three/examples/jsm/curves/NURBSCurve.js", "lib/three/examples/jsm/curves/NURBSUtils.js", "lib/three/examples/jsm/libs/fflate.module.js", "lib/three/examples/jsm/loaders/FBXLoader.js", "lib/three/examples/jsm/loaders/TGALoader.js", "lib/three/LICENSE", "manifest.webmanifest", "models/age_gender_model-weights_manifest.json", "models/age_gender_model.bin", "models/face_landmark_68_model-weights_manifest.json", "models/face_landmark_68_model.bin", "models/selfie.bin", "models/selfie.json", "models/SELFIE_LICENSE", "models/tiny_face_detector_model-weights_manifest.json", "models/tiny_face_detector_model.bin", "photo_head.js", "stadium_ring.js", "style.css"];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;
  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then((hit) => hit || fetch(event.request))
  );
});
