/* Android arayüzünün web karşılığı: skor, menüler, fotoğraf işleme ve oyun motoru köprüsü. */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var clamp = function (v, lo, hi) { return Math.max(lo, Math.min(hi, v)); };

  var BEST_KEY = 'ring-tokat-best';
  var MAX_PHOTO = 1600;
  var MAX_SHIRT = 1024;
  var FACE_SIZE = 512;
  var LOAD_TIMEOUT_MS = 60000;

  var OPTIONS = {
    gender: [['male', 'Erkek'], ['female', 'Kadın']],
    kit: [
      ['pure_white', 'Beyaz', '#F4F4F1'], ['classic_red', 'Kırmızı', '#D91B38'],
      ['champion_gold', 'Altın', '#F59E0B'], ['cyber_cyan', 'Turkuaz', '#00B8D4'],
      ['emerald_pro', 'Zümrüt', '#059669']
    ],
    headgear: [['pro_hair', 'Şampiyon Saç'], ['boxing_helm', 'Boks Kaskı'], ['crown', 'Kral Tacı'], ['bald_pro', 'Aksesuarsız']],
    proportion: [['athletic', 'Normal'], ['bobble', 'Koca Kafa']]
  };

  var STRESS_GAIN = { uppercut: .24, kick: .26, punch: .22, pie: .22, slap: .19, water: .18, body: .16 };
  var CALLOUTS = {
    uppercut: 'ÇENE APARKATI!', punch: 'TAM YUMRUK!', kick: 'TEKMEYİ YEDİ!', body: 'UFFF! KARIN DARBESİ!',
    slap: 'ŞAAAK TOKAT!', water: 'ŞAKIR ŞUKUR!', pie: 'ŞLOP! PASTA!'
  };
  var HOOK_WORDS = ['ŞAAAK!', 'SERT TOKAT!', 'ÇAT!', 'GÜM!', 'TAM İSABET!'];

  var game = {
    ready: false, stress: 0, combo: 0, multiplier: 1, score: 0, best: readBest(),
    isSuper: false, orbit: false, sound: true, lastHit: 0,
    look: { gender: 'male', kit: 'pure_white', headgear: 'pro_hair', proportion: 'athletic' },
    pendingFace: '', pendingShirt: ''
  };
  var superTimer = 0;
  var calloutTimer = 0;

  function readBest() {
    try { return parseInt(localStorage.getItem(BEST_KEY), 10) || 0; } catch (e) { return 0; }
  }
  function saveBest() {
    try { localStorage.setItem(BEST_KEY, String(game.best)); } catch (e) { /* gizli sekmede kayıt tutulmaz */ }
  }
  function engine() { return window.RingGame || null; }

  /* ---------- Hata ekranı ---------- */
  function showFatal(message) {
    if (game.ready) return;
    $('loading').hidden = true;
    $('fatalText').textContent = message;
    $('fatal').hidden = false;
  }
  $('fatalRetry').addEventListener('click', function () { location.reload(); });

  if (!(window.HTMLScriptElement && HTMLScriptElement.supports && HTMLScriptElement.supports('importmap'))) {
    showFatal('Bu oyun için iOS 16.4 veya daha yeni bir sürüm gerekiyor. Ayarlar > Genel > Yazılım Güncelleme bölümünden güncelleyebilirsin.');
  }
  var loadWatch = setTimeout(function () {
    showFatal('Arena zamanında yüklenemedi. İnternet bağlantını kontrol edip yeniden dene.');
  }, LOAD_TIMEOUT_MS);
  window.addEventListener('error', function (e) {
    if (!game.ready && e.message) showFatal('Telefonun 3D grafiği başlatamadı. Safari sekmesini kapatıp yeniden dene.');
  });

  /* ---------- Oyun motorunun beklediği köprü ---------- */
  window.AndroidBridge = {
    onSceneReady: function () {
      clearTimeout(loadWatch);
      if (!engine()) {
        showFatal('Oyun dosyaları yüklenemedi. Bağlantını kontrol edip yeniden dene.');
        return;
      }
      game.ready = true;
      $('loading').hidden = true;
      engine().setSoundEnabled(game.sound);
      engine().setOrbitMode(game.orbit);
      applyLook();
    },
    onCharacterHit: onCharacterHit,
    getPendingFaceJson: function () {
      return game.pendingFace ? JSON.stringify({ textureDataUrl: game.pendingFace }) : '';
    },
    getPendingShirtImage: function () { return game.pendingShirt; }
  };

  function applyLook() {
    var l = game.look;
    if (engine()) engine().applyCustomization(l.kit, l.headgear, l.proportion, l.gender);
  }

  /* ---------- Skor, kombo ve nakavt barı ---------- */
  function onCharacterHit(intensity, kind) {
    var now = Date.now();
    var quickChain = now - game.lastHit < 2000;
    game.lastHit = now;
    if (navigator.vibrate) navigator.vibrate(clamp(Math.round(22 + intensity * 30), 18, 90));

    game.combo = quickChain ? game.combo + 1 : 1;
    game.multiplier = Math.min(10, 1 + Math.floor(game.combo / 3));
    var earned = Math.max(12, Math.round(18 * intensity)) * game.multiplier * (game.isSuper ? 2 : 1);
    $('hint').hidden = true;

    if (!game.isSuper) {
      var gain = STRESS_GAIN[kind] || clamp(.10 + intensity * .06, .09, .19);
      game.stress = Math.min(1, game.stress + gain);
      if (game.stress >= 1) {
        addScore(earned + 300);
        startSuperKnockout();
        return;
      }
    }
    addScore(earned);
    if (!game.isSuper) showCallout(CALLOUTS[kind] || HOOK_WORDS[game.combo % HOOK_WORDS.length]);
    renderMeter();
  }

  function addScore(points) {
    game.score += points;
    $('score').textContent = game.score.toLocaleString('tr-TR');
    if (game.score > game.best) {
      game.best = game.score;
      saveBest();
    }
    renderBest();
  }
  function renderBest() { $('best').textContent = 'REKOR ' + game.best.toLocaleString('tr-TR'); }

  function renderMeter() {
    $('meterFill').style.transform = 'scaleX(' + game.stress + ')';
    var combo = $('combo');
    combo.hidden = game.multiplier < 2;
    combo.textContent = 'x' + game.multiplier + ' KOMBO';
    $('meterLabel').textContent = game.isSuper ? 'SÜPER NAKAVT!' : 'NAKAVT BARI';
  }

  function showCallout(text) {
    var el = $('callout');
    clearTimeout(calloutTimer);
    el.classList.remove('pop', 'super');
    el.textContent = text;
    void el.offsetWidth; // Aynı animasyonun baştan oynaması için gerekir.
    el.classList.add('pop');
    calloutTimer = setTimeout(function () { el.classList.remove('pop'); el.textContent = ''; }, 950);
  }

  function startSuperKnockout() {
    game.isSuper = true;
    game.multiplier = Math.max(game.multiplier, 5);
    clearTimeout(calloutTimer);
    var el = $('callout');
    el.classList.remove('pop');
    el.classList.add('super');
    el.textContent = 'SÜPER NAKAVT!';
    $('feverFrame').hidden = false;
    renderMeter();
    if (navigator.vibrate) navigator.vibrate([60, 40, 90]);
    if (engine()) engine().startSuperCombo();
    clearTimeout(superTimer);
    superTimer = setTimeout(endSuperKnockout, 5000);
  }

  function endSuperKnockout() {
    clearTimeout(superTimer);
    game.isSuper = false;
    game.stress = 0;
    game.combo = 0;
    game.multiplier = 1;
    $('feverFrame').hidden = true;
    var el = $('callout');
    el.classList.remove('super', 'pop');
    el.textContent = '';
    renderMeter();
  }

  setInterval(function () {
    if (game.isSuper || game.stress <= 0 || Date.now() - game.lastHit <= 2300) return;
    game.stress = Math.max(0, game.stress - .016);
    if (game.stress === 0) {
      game.combo = 0;
      game.multiplier = 1;
    }
    renderMeter();
  }, 120);

  /* ---------- Düğmeler ---------- */
  // iOS sesi yalnızca parmak kalkınca açar; bu yüzden her dokunuşun sonunda denenir.
  ['touchend', 'click'].forEach(function (type) {
    document.addEventListener(type, function () {
      if (window.ArenaAudio) window.ArenaAudio.unlock();
    }, { passive: true, capture: true });
  });
  document.addEventListener('gesturestart', function (e) { e.preventDefault(); });

  function setOrbit(on) {
    game.orbit = on;
    $('orbitBtn').setAttribute('aria-pressed', String(on));
    $('hint').hidden = !on;
    if (on) $('hint').textContent = '360° inceleme: parmağınla sürükleyerek avatarı çevir.';
    if (engine()) engine().setOrbitMode(on);
  }

  document.querySelectorAll('[data-attack]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!engine()) return;
      if (game.orbit) setOrbit(false);
      engine()[btn.dataset.attack]();
    });
  });

  $('resetBtn').addEventListener('click', function () {
    endSuperKnockout();
    if (engine()) engine().triggerReset();
  });
  $('orbitBtn').addEventListener('click', function () { setOrbit(!game.orbit); });
  $('soundBtn').addEventListener('click', function () {
    game.sound = !game.sound;
    var btn = $('soundBtn');
    btn.setAttribute('aria-pressed', String(game.sound));
    btn.setAttribute('aria-label', game.sound ? 'Sesi kapat' : 'Sesi aç');
    $('soundOn').toggleAttribute('hidden', !game.sound);
    $('soundOff').toggleAttribute('hidden', game.sound);
    if (engine()) engine().setSoundEnabled(game.sound);
  });
  $('guideBtn').addEventListener('click', function () { $('guideSheet').showModal(); });
  $('wardrobeBtn').addEventListener('click', function () { $('wardrobeSheet').showModal(); });

  document.querySelectorAll('dialog').forEach(function (dialog) {
    dialog.addEventListener('click', function (e) {
      if (e.target === dialog || e.target.closest('[data-close]')) dialog.close();
    });
  });

  /* ---------- Ekipman ---------- */
  function buildChips(containerId, key, options) {
    var box = $(containerId);
    options.forEach(function (opt) {
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.dataset.value = opt[0];
      chip.setAttribute('aria-pressed', String(game.look[key] === opt[0]));
      if (opt[2]) {
        var swatch = document.createElement('span');
        swatch.className = 'swatch';
        swatch.style.background = opt[2];
        chip.appendChild(swatch);
      }
      chip.appendChild(document.createTextNode(opt[1]));
      chip.addEventListener('click', function () {
        game.look[key] = opt[0];
        box.querySelectorAll('.chip').forEach(function (c) {
          c.setAttribute('aria-pressed', String(c === chip));
        });
        applyLook();
      });
      box.appendChild(chip);
    });
  }
  buildChips('genderChips', 'gender', OPTIONS.gender);
  buildChips('kitChips', 'kit', OPTIONS.kit);
  buildChips('headChips', 'headgear', OPTIONS.headgear);
  buildChips('propChips', 'proportion', OPTIONS.proportion);

  /* ---------- Fotoğraf okuma ---------- */
  function loadPhoto(file, maxSide) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        var ratio = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
        var canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(img.naturalWidth * ratio));
        canvas.height = Math.max(1, Math.round(img.naturalHeight * ratio));
        var ctx = canvas.getContext('2d');
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        resolve(canvas);
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        reject(new Error('photo'));
      };
      img.src = url;
    });
  }

  /* ---------- Tişört baskısı ---------- */
  $('shirtPick').addEventListener('click', function () { $('shirtFile').click(); });
  $('shirtFile').addEventListener('change', function (e) {
    var file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    loadPhoto(file, MAX_SHIRT).then(function (canvas) {
      game.pendingShirt = canvas.toDataURL('image/png');
      $('shirtRemove').hidden = false;
      if (engine()) engine().pullShirtImageFromBridge();
    }).catch(function () {
      $('shirtPick').textContent = 'Görsel okunamadı, başka görsel seç';
    });
  });
  $('shirtRemove').addEventListener('click', function () {
    game.pendingShirt = '';
    $('shirtRemove').hidden = true;
    $('shirtPick').textContent = 'Tişörte Görsel Yükle';
    if (engine()) engine().clearShirtImage();
  });

  /* ---------- Yüz yerleştirme ---------- */
  var studio = { photo: null, bg: '#8a6a58', x: 256, y: 256, scale: 1, rot: 0, minScale: .1, maxScale: 4, queued: false };
  var stage = $('faceStage');
  var faceCtx = $('faceCanvas').getContext('2d');
  var pointers = new Map();

  function averageColor(canvas) {
    var probe = document.createElement('canvas');
    probe.width = probe.height = 1;
    var ctx = probe.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(canvas, 0, 0, 1, 1);
    var d = ctx.getImageData(0, 0, 1, 1).data;
    return 'rgb(' + d[0] + ',' + d[1] + ',' + d[2] + ')';
  }

  function paintFace(ctx, size) {
    var k = size / FACE_SIZE;
    var p = studio.photo;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = studio.bg;
    ctx.fillRect(0, 0, size, size);
    ctx.imageSmoothingQuality = 'high';
    ctx.setTransform(k, 0, 0, k, 0, 0);
    ctx.translate(studio.x, studio.y);
    ctx.rotate(studio.rot);
    ctx.scale(studio.scale, studio.scale);
    ctx.drawImage(p, -p.width / 2, -p.height / 2);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  function queuePaint() {
    if (studio.queued) return;
    studio.queued = true;
    requestAnimationFrame(function () {
      studio.queued = false;
      if (studio.photo) paintFace(faceCtx, faceCtx.canvas.width);
    });
  }

  function syncSliders() {
    var range = Math.log(studio.maxScale / studio.minScale);
    $('faceZoom').value = String(100 * Math.log(studio.scale / studio.minScale) / range);
    $('faceRotate').value = String(studio.rot * 180 / Math.PI);
  }

  function setStudioPhoto(canvas) {
    studio.photo = canvas;
    studio.bg = averageColor(canvas);
    var fit = FACE_SIZE / (Math.min(canvas.width, canvas.height) * .86);
    studio.scale = fit;
    studio.minScale = fit * .35;
    studio.maxScale = fit * 6;
    studio.rot = 0;
    studio.x = FACE_SIZE / 2;
    studio.y = FACE_SIZE / 2 + canvas.height * .06 * fit;
    syncSliders();
    queuePaint();
  }

  // Yakınlaştırma sahnenin ortasını sabit tutar.
  function zoomStageCenter(nextScale) {
    var ratio = nextScale / studio.scale;
    studio.x = FACE_SIZE / 2 + (studio.x - FACE_SIZE / 2) * ratio;
    studio.y = FACE_SIZE / 2 + (studio.y - FACE_SIZE / 2) * ratio;
    studio.scale = nextScale;
  }

  $('faceZoom').addEventListener('input', function (e) {
    var range = Math.log(studio.maxScale / studio.minScale);
    zoomStageCenter(studio.minScale * Math.exp(range * e.target.value / 100));
    queuePaint();
  });
  $('faceRotate').addEventListener('input', function (e) {
    var next = e.target.value * Math.PI / 180;
    var delta = next - studio.rot;
    var dx = studio.x - FACE_SIZE / 2;
    var dy = studio.y - FACE_SIZE / 2;
    studio.x = FACE_SIZE / 2 + dx * Math.cos(delta) - dy * Math.sin(delta);
    studio.y = FACE_SIZE / 2 + dx * Math.sin(delta) + dy * Math.cos(delta);
    studio.rot = next;
    queuePaint();
  });

  function stagePoint(e) {
    var r = stage.getBoundingClientRect();
    var k = FACE_SIZE / r.width;
    return { x: (e.clientX - r.left) * k, y: (e.clientY - r.top) * k };
  }

  stage.addEventListener('pointerdown', function (e) {
    pointers.set(e.pointerId, stagePoint(e));
    try { stage.setPointerCapture(e.pointerId); } catch (err) { /* parmak çoktan kalkmış olabilir */ }
  });

  stage.addEventListener('pointermove', function (e) {
    if (!pointers.has(e.pointerId) || !studio.photo) return;
    var ids = Array.from(pointers.keys());
    var next = stagePoint(e);

    if (ids.length === 1) {
      var prev = pointers.get(e.pointerId);
      studio.x += next.x - prev.x;
      studio.y += next.y - prev.y;
    } else {
      var otherId = ids[0] === e.pointerId ? ids[1] : ids[0];
      var other = pointers.get(otherId);
      var before = pointers.get(e.pointerId);
      var d0 = Math.hypot(before.x - other.x, before.y - other.y) || 1;
      var d1 = Math.hypot(next.x - other.x, next.y - other.y) || 1;
      var nextScale = clamp(studio.scale * d1 / d0, studio.minScale, studio.maxScale);
      var ratio = nextScale / studio.scale;
      var a0 = Math.atan2(before.y - other.y, before.x - other.x);
      var a1 = Math.atan2(next.y - other.y, next.x - other.x);
      var limit = Math.PI / 3;
      var spin = Math.atan2(Math.sin(a1 - a0), Math.cos(a1 - a0));
      var nextRot = clamp(studio.rot + spin, -limit, limit);
      var turn = nextRot - studio.rot;
      var cx0 = (before.x + other.x) / 2;
      var cy0 = (before.y + other.y) / 2;
      var cx1 = (next.x + other.x) / 2;
      var cy1 = (next.y + other.y) / 2;
      var dx = (studio.x - cx0) * ratio;
      var dy = (studio.y - cy0) * ratio;
      studio.x = cx1 + dx * Math.cos(turn) - dy * Math.sin(turn);
      studio.y = cy1 + dx * Math.sin(turn) + dy * Math.cos(turn);
      studio.scale = nextScale;
      studio.rot = nextRot;
      syncSliders();
    }
    pointers.set(e.pointerId, next);
    queuePaint();
  });

  ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(function (type) {
    stage.addEventListener(type, function (e) { pointers.delete(e.pointerId); });
  });

  function pickFace() { $('faceFile').click(); }

  $('faceBtn').addEventListener('click', function () {
    if (studio.photo) $('faceSheet').showModal();
    else pickFace();
  });
  $('facePick').addEventListener('click', pickFace);

  $('faceFile').addEventListener('change', function (e) {
    var file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    $('faceStatus').textContent = '';
    loadPhoto(file, MAX_PHOTO).then(function (canvas) {
      setStudioPhoto(canvas);
      if (!$('faceSheet').open) $('faceSheet').showModal();
    }).catch(function () {
      $('faceStatus').textContent = 'Fotoğraf okunamadı, başka bir fotoğraf dene.';
      if (!$('faceSheet').open && studio.photo) $('faceSheet').showModal();
      if (!studio.photo) {
        $('faceBtnLabel').textContent = 'Fotoğraf okunamadı';
        setTimeout(function () { $('faceBtnLabel').textContent = 'Yüz Yükle'; }, 2600);
      }
    });
  });

  $('faceApply').addEventListener('click', function () {
    if (!studio.photo) return;
    var out = document.createElement('canvas');
    out.width = out.height = FACE_SIZE;
    paintFace(out.getContext('2d'), FACE_SIZE);
    game.pendingFace = out.toDataURL('image/jpeg', .92);
    $('faceThumb').src = game.pendingFace;
    $('faceThumb').hidden = false;
    $('faceIcon').style.display = 'none';
    $('faceBtn').classList.add('has-face');
    $('faceBtnLabel').textContent = 'Yüzü Düzenle';
    $('faceRestore').hidden = false;
    if (engine()) engine().pullCustomFaceFromBridge();
    $('faceSheet').close();
  });

  $('faceRestore').addEventListener('click', function () {
    game.pendingFace = '';
    studio.photo = null;
    $('faceThumb').hidden = true;
    $('faceThumb').removeAttribute('src');
    $('faceIcon').style.display = '';
    $('faceBtn').classList.remove('has-face');
    $('faceBtnLabel').textContent = 'Yüz Yükle';
    $('faceRestore').hidden = true;
    if (engine()) engine().restoreDefaultFace();
    $('faceSheet').close();
  });

  /* ---------- Çevrimdışı kullanım ---------- */
  var isLocal = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  if ('serviceWorker' in navigator && window.isSecureContext && !isLocal) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('sw.js').catch(function () { /* oyun çevrimiçi çalışmaya devam eder */ });
    });
  }

  renderBest();
  renderMeter();
})();
