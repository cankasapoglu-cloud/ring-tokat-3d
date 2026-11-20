// Three.js ve avatarı hazırlar, ardından oyun motoru dosyalarını sırayla yükler.
import * as THREE from 'three';
import { AvatarFighter } from './avatar_fighter.js';

window.THREE = Object.assign({}, THREE);
window.AvatarFighter = AvatarFighter;

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`Dosya yüklenemedi: ${src}`));
    document.body.appendChild(script);
  });
}

try {
  await AvatarFighter.preload('male');
  for (const src of ['arena_audio.js', 'stadium_ring.js', 'arena_engine.js']) {
    await loadScript(src);
  }
} catch (err) {
  console.error('Oyun başlatılamadı:', err);
  window.AndroidBridge?.onSceneReady?.();
}
