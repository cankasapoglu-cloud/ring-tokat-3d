/* =========================================================================
 * MAIN CHAMPIONSHIP 3D ENGINE: REGIONAL PHYSICS, HIT-STOP, FX & CAMERA
 * ========================================================================= */
(function() {

  function initChampionshipArena() {
    var canvas = document.getElementById('arena-canvas');
    var renderer;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance'
      });
    } catch (e) {
      renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true });
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    if (THREE.ACESFilmicToneMapping !== undefined) {
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.12;
    }

    var scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x090E22, 0.042);

    var camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 65);
    var baseCamDist = 4.3;
    var baseLookAt = new THREE.Vector3(0, 1.18, 0.05);

    var orbitState = {
      enabled: false,
      azimuth: 0,
      polar: 1.46,
      targetAzimuth: 0,
      targetPolar: 1.46
    };

    function updateCameraFraming() {
      var aspect = window.innerWidth / Math.max(1, window.innerHeight);
      camera.aspect = aspect;
      if (aspect < 0.54) {
        baseCamDist = 4.7;
      } else if (aspect > 1.1) {
        baseCamDist = 3.9;
      } else {
        baseCamDist = 4.3;
      }
      camera.updateProjectionMatrix();
    }
    updateCameraFraming();

    // --- Studio 4-Point PBR Fighter Lighting ---
    var hemi = new THREE.HemisphereLight(0xC7D2FE, 0x1E1B4B, 0.78);
    scene.add(hemi);

    var keyLight = new THREE.DirectionalLight(0xFFF7ED, 1.45);
    keyLight.position.set(2.4, 6.2, 4.8);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 1024;
    keyLight.shadow.mapSize.height = 1024;
    keyLight.shadow.bias = -0.0005;
    scene.add(keyLight);

    var cyanRim = new THREE.SpotLight(0x00E5FF, 2.2, 16, Math.PI * 0.38, 0.5);
    cyanRim.position.set(-3.8, 3.4, -2.6);
    scene.add(cyanRim);

    var crimsonRim = new THREE.SpotLight(0xFF2A54, 2.0, 16, Math.PI * 0.38, 0.5);
    crimsonRim.position.set(3.8, 3.2, -2.4);
    scene.add(crimsonRim);

    var feverStrobe = new THREE.PointLight(0xFFC800, 0.0, 14);
    feverStrobe.position.set(0, 3.8, 2.4);
    scene.add(feverStrobe);

    // Yeni Three.js surumunun fiziksel isik birimlerine uyarlama
    [hemi, keyLight, cyanRim, crimsonRim].forEach(function(light) { light.intensity *= Math.PI; });
    cyanRim.decay = 1;
    crimsonRim.decay = 1;
    feverStrobe.decay = 1;

    // --- Build Stadium Ring & Organic Anatomical Fighter ---
    var ring = window.StadiumRing.createChampionshipRing(scene);
    var fighter = window.AvatarFighter.createCompleteFighter();
    fighter.root.position.set(0, 0.05, 0.22);
    scene.add(fighter.root);

    var headData = fighter.headData;

    // Containers on headGroup for 3D Pie Cream, Water Beads & Knockout Stars
    var headSplatGroup = new THREE.Group();
    headData.headGroup.add(headSplatGroup);

    var dizzyCrown = new THREE.Group();
    dizzyCrown.position.set(0, 0.54, 0);
    dizzyCrown.visible = false;
    headData.headGroup.add(dizzyCrown);

    function createStarGeo(outerR, innerR) {
      var sh = new THREE.Shape();
      for (var i = 0; i < 10; i++) {
        var r = i % 2 === 0 ? outerR : innerR;
        var a = (i / 10) * Math.PI * 2 - Math.PI / 2;
        if (i === 0) sh.moveTo(Math.cos(a) * r, Math.sin(a) * r);
        else sh.lineTo(Math.cos(a) * r, Math.sin(a) * r);
      }
      sh.closePath();
      return new THREE.ExtrudeGeometry(sh, { depth: 0.022, bevelEnabled: false });
    }
    var starGeo = createStarGeo(0.068, 0.030);
    var starMat = new THREE.MeshStandardMaterial({
      color: 0xFFC800,
      emissive: 0xFF8F00,
      emissiveIntensity: 0.5,
      roughness: 0.2
    });
    for (var s = 0; s < 6; s++) {
      var st = new THREE.Mesh(starGeo, starMat);
      var sa = (s / 6) * Math.PI * 2;
      st.position.set(Math.cos(sa) * 0.36, Math.sin(sa * 2) * 0.035, Math.sin(sa) * 0.36);
      dizzyCrown.add(st);
    }

    /* =====================================================================
     * REALISTIC-STYLIZED FACE TEXTURE & 3D EYE/BROW RIG CONTROLLER
     * ===================================================================== */
    var totalHitCounter = 0;
    var idleTimer = 4;
    var hitStreak = 0;
    var lastHitMs = 0;

    var faceState = {
      expr: 'idle', // 'idle', 'hit', 'gut', 'dizzy', 'wet'
      timer: 0,
      slapAlpha: 0,
      slapSide: 1,
      blinkTimer: 1.8,
      isBlinking: false
    };

    function redrawFaceSurface() {
      fighter.setSlapMark(faceState.slapAlpha, faceState.slapSide);
      fighter.setBandage(totalHitCounter >= 6);
    }
    redrawFaceSurface();

    /* =====================================================================
     * ARTICULATED REGIONAL SPRING & SKELETAL REACTION STATE
     * ===================================================================== */
    var targetBaseHeadScale = 1.0;

    var phys = {
      neckRotX: 0, neckRotY: 0, neckRotZ: 0,
      neckVelX: 0, neckVelY: 0, neckVelZ: 0,
      headShiftX: 0, headShiftY: 0, headShiftZ: 0,
      headShiftVelX: 0, headShiftVelY: 0, headShiftVelZ: 0,
      chestRotX: 0, chestRotY: 0, chestRotZ: 0,
      chestVelX: 0, chestVelY: 0, chestVelZ: 0,
      kneeBend: 0, kneeBendVel: 0,
      guardOpen: 0, guardOpenVel: 0,
      gutClutch: 0, gutClutchVel: 0,
      squash: 0, squashVel: 0,
      ropeBounce: 0, ropeBounceVel: 0,
      camShake: 0,
      camPunchZoom: 0,
      pushZ: 0, pushVel: 0,
      hitStopTimer: 0,
      shiverTimer: 0,
      superComboTimer: 0
    };

    /* =====================================================================
     * SWEAT SPRAY, SHOCKWAVE RINGS, CONFETTI & PROJECTILES
     * ===================================================================== */
    var particles = [];
    var shockwaves = [];
    var projectiles = [];
    var confetti = [];
    var gloveStrikeAnim = null;

    var sweatMat = new THREE.MeshStandardMaterial({
      color: 0xE0F7FA,
      roughness: 0.05,
      transparent: true,
      opacity: 0.7
    });
    var waterMat = new THREE.MeshStandardMaterial({
      color: 0x00E5FF,
      roughness: 0.1,
      metalness: 0.15,
      transparent: true,
      opacity: 0.88
    });
    var creamMat = new THREE.MeshStandardMaterial({ color: 0xFFFBEB, roughness: 0.5 });
    var cherryMat = new THREE.MeshStandardMaterial({ color: 0xFF1744, roughness: 0.18 });

    function spawnShockwaveRing(worldPos, colorHex) {
      var ringGeo = new THREE.RingGeometry(0.05, 0.085, 28);
      var ringMat = new THREE.MeshBasicMaterial({
        color: colorHex || 0xFFC800,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.92,
        blending: THREE.AdditiveBlending
      });
      var rMesh = new THREE.Mesh(ringGeo, ringMat);
      rMesh.position.copy(worldPos);
      rMesh.lookAt(camera.position);
      scene.add(rMesh);
      shockwaves.push({ mesh: rMesh, mat: ringMat, age: 0, maxAge: 0.26 });
    }

    function spawnParticles(origin, kind, count, biasDirX) {
      for (var i = 0; i < count; i++) {
        var mesh;
        var speed = 2.0 + Math.random() * 3.2;
        if (kind === 'stars') {
          mesh = new THREE.Mesh(starGeo, starMat);
          mesh.scale.setScalar(0.75 + Math.random() * 0.55);
        } else if (kind === 'sweat') {
          mesh = new THREE.Mesh(new THREE.SphereGeometry(0.022 + Math.random() * 0.018, 8, 6), sweatMat);
          mesh.scale.set(0.8, 1.4, 0.8);
          speed = 2.8 + Math.random() * 3.5;
        } else if (kind === 'water') {
          mesh = new THREE.Mesh(new THREE.SphereGeometry(0.042 + Math.random() * 0.035, 10, 8), waterMat);
        } else if (kind === 'cream') {
          mesh = new THREE.Mesh(new THREE.SphereGeometry(0.055 + Math.random() * 0.045, 10, 8), creamMat);
        } else {
          mesh = new THREE.Mesh(
            new THREE.OctahedronGeometry(0.045, 0),
            new THREE.MeshBasicMaterial({ color: i % 2 === 0 ? 0x10B981 : 0xFFC800 })
          );
        }
        mesh.position.copy(origin);
        var theta = Math.random() * Math.PI * 2;
        var vx = Math.cos(theta) * speed * 0.7 + (biasDirX || 0) * 2.2;
        var vy = Math.abs(Math.sin(theta)) * speed * 0.75 + 1.2;
        var vz = (Math.random() - 0.3) * speed * 0.8;
        scene.add(mesh);
        particles.push({
          mesh: mesh,
          vel: new THREE.Vector3(vx, vy, vz),
          rotVel: new THREE.Vector3(Math.random() * 9, Math.random() * 9, Math.random() * 9),
          life: 0.55 + Math.random() * 0.4,
          maxLife: 0.95,
          gravity: kind === 'clean' ? -2.2 : 9.8
        });
      }
    }

    function attachPieCreamDecal() {
      while (headSplatGroup.children.length > 24) {
        headSplatGroup.remove(headSplatGroup.children[0]);
      }
      var R = headData.headRadius;
      var grp = new THREE.Group();
      for (var i = 0; i < 10; i++) {
        var dollop = new THREE.Mesh(new THREE.SphereGeometry(0.062 + Math.random() * 0.05, 12, 10), creamMat);
        var ang = Math.random() * Math.PI * 2;
        var rad = i === 0 ? 0 : 0.08 + Math.random() * 0.16;
        var bx = Math.cos(ang) * rad;
        var by = Math.sin(ang) * rad - 0.02;
        var bz = Math.sqrt(Math.max(0.04, R * R - bx * bx - by * by)) + 0.025;
        dollop.position.set(bx, by, bz);
        dollop.scale.set(1.15, 0.95, 0.46);
        grp.add(dollop);
      }
      var cherry = new THREE.Mesh(new THREE.SphereGeometry(0.048, 12, 10), cherryMat);
      cherry.position.set(0, -0.02, R + 0.085);
      grp.add(cherry);
      headSplatGroup.add(grp);
    }

    function attachWaterDroplets() {
      while (headSplatGroup.children.length > 24) {
        headSplatGroup.remove(headSplatGroup.children[0]);
      }
      var R = headData.headRadius;
      var grp = new THREE.Group();
      for (var i = 0; i < 14; i++) {
        var drop = new THREE.Mesh(new THREE.SphereGeometry(0.022 + Math.random() * 0.015, 8, 8), waterMat);
        var bx = (Math.random() - 0.5) * 0.46;
        var by = (Math.random() - 0.5) * 0.52;
        if (bx * bx + by * by > 0.11) { bx *= 0.6; by *= 0.6; }
        var bz = Math.sqrt(Math.max(0.04, R * R - bx * bx - by * by)) + 0.015;
        drop.position.set(bx, by, bz);
        drop.scale.set(0.85, 1.35, 0.5);
        grp.add(drop);
      }
      headSplatGroup.add(grp);
    }

    /* =====================================================================
     * REGIONAL IMPACT RESOLVER (Cheek Hook, Chin Uppercut, Body Blow, Props)
     * ===================================================================== */
    function triggerRegionalImpact(zone, dirX, dirY, rawPower, hitKind) {
      var power = Math.min(1.65, Math.max(0.45, rawPower));
      totalHitCounter++;

      fighter.cancelIdleGesture();
      idleTimer = 6 + Math.random() * 4;
      var nowMs = performance.now();
      hitStreak = (nowMs - lastHitMs < 900) ? hitStreak + 1 : 1;
      lastHitMs = nowMs;
      if (hitStreak >= 6) {
        hitStreak = 0;
        fighter.playGesture('fall');
        window.ArenaAudio.playBoing(1.2);
      }

      var impactWorld = new THREE.Vector3();
      var bridgeKind = hitKind || 'swipe';

      if (zone === 'kick') {
        // Karna tekme: öne katlanır ve geriye savrulur.
        fighter.chestPivot.getWorldPosition(impactWorld);
        impactWorld.z += 0.28;

        phys.chestVelX += 12.5 * power;
        phys.chestVelY += dirX * 5.0 * power;
        phys.neckVelX += 9.0 * power;
        phys.kneeBendVel += 5.5 * power;
        phys.gutClutchVel += 11.0 * power;
        phys.pushVel += 3.6 * power;
        phys.squash = -0.20 * power;
        phys.hitStopTimer = 0.05;

        faceState.expr = 'gut';
        faceState.timer = 0.8;
        bridgeKind = 'kick';
        window.ArenaAudio.playBodyBlow(power);
        window.ArenaAudio.playBoing(power * 0.7);
        ring.triggerCameraFlash();
        spawnShockwaveRing(impactWorld, 0xFFC800);
        spawnParticles(impactWorld, 'stars', 8, dirX);
        spawnParticles(impactWorld, 'sweat', 12, dirX);
      } else if (zone === 'punch') {
        // Yüze düz yumruk: baş geriye gider, gövde sarsılır.
        headData.headGroup.getWorldPosition(impactWorld);
        impactWorld.z += 0.16;

        phys.neckVelX -= 9.5 * power;
        phys.neckVelY += dirX * 6.0 * power;
        phys.headShiftVelZ -= 2.4 * power;
        phys.chestVelX -= 6.0 * power;
        phys.guardOpenVel += 10.0 * power;
        phys.pushVel += 2.2 * power;
        phys.squash = -0.24 * power;
        phys.hitStopTimer = 0.05;

        faceState.expr = 'hit';
        faceState.timer = 0.7;
        bridgeKind = 'punch';
        window.ArenaAudio.playUppercutCrunch(power);
        ring.triggerCameraFlash();
        spawnShockwaveRing(impactWorld, 0xFF2A54);
        spawnParticles(impactWorld, 'sweat', 14, dirX);
        spawnParticles(impactWorld, 'stars', 7, dirX);
      } else if (zone === 'body') {
        // Gut-punch / Body Blow! Boxer doubles forward clutching ribs!
        fighter.chestPivot.getWorldPosition(impactWorld);
        impactWorld.y += 0.35;
        impactWorld.z += 0.28;

        phys.chestVelX += 9.8 * power;
        phys.chestVelY += dirX * 4.5 * power;
        phys.neckVelX += 7.5 * power;
        phys.kneeBendVel += 4.2 * power;
        phys.gutClutchVel += 9.5 * power;
        phys.squash = -0.18 * power;

        faceState.expr = 'gut';
        faceState.timer = 0.72;
        bridgeKind = 'body';
        window.ArenaAudio.playBodyBlow(power);
        spawnShockwaveRing(impactWorld, 0x00E5FF);
        spawnParticles(impactWorld, 'sweat', 10, dirX);
      } else if (zone === 'uppercut') {
        // Chin Uppercut! Head snaps skyward, spine arches back!
        headData.headGroup.getWorldPosition(impactWorld);
        impactWorld.y -= 0.14;
        impactWorld.z += 0.32;

        phys.neckVelX -= 19.5 * power;
        phys.neckVelY += dirX * 7.5 * power;
        phys.headShiftVelY += 2.2 * power;
        phys.headShiftVelZ -= 1.8 * power;
        phys.chestVelX -= 6.8 * power;
        phys.guardOpenVel += 12.0 * power;
        phys.squash = 0.28 * power;
        phys.hitStopTimer = 0.048;

        faceState.expr = 'hit';
        faceState.timer = 0.75;
        bridgeKind = 'uppercut';
        window.ArenaAudio.playUppercutCrunch(power);
        ring.triggerCameraFlash();
        spawnShockwaveRing(impactWorld, 0xFFC800);
        spawnParticles(impactWorld, 'sweat', 16, dirX);
        spawnParticles(impactWorld, 'stars', 7, dirX);
      } else {
        // Left/Right Cheek Hook, Slap, Pie, or Water Balloon!
        headData.headGroup.getWorldPosition(impactWorld);
        impactWorld.z += 0.32;

        var whipX = Math.abs(dirX) < 0.2 ? (zone === 'head_left' ? 1 : -1) : dirX;
        phys.neckVelY += whipX * 17.5 * power;
        phys.neckVelZ -= whipX * 10.5 * power;
        phys.neckVelX -= dirY * 12.0 * power;

        phys.headShiftVelX += whipX * 1.4 * power;
        phys.headShiftVelZ -= 1.5 * power;
        phys.chestVelZ -= whipX * 3.8 * power;
        phys.chestVelY += whipX * 4.2 * power;
        phys.chestVelX -= 3.2 * power;
        phys.guardOpenVel += 9.5 * power;
        phys.squash = -0.26 * power;

        if (power > 1.05) {
          phys.hitStopTimer = 0.042;
          ring.triggerCameraFlash();
        }

        if (phys.superComboTimer <= 0) {
          faceState.expr = hitKind === 'water' ? 'wet' : 'hit';
          faceState.timer = hitKind === 'water' ? 1.0 : 0.58;
        }
        if (hitKind === 'slap' || hitKind === 'swipe') {
          faceState.slapAlpha = Math.min(1.0, 0.58 + power * 0.38);
          faceState.slapSide = whipX >= 0 ? 1 : -1;
        }

        var ringColor = hitKind === 'water' ? 0x00E5FF : (hitKind === 'pie' ? 0xFF6EC7 : 0xFF2A54);
        spawnShockwaveRing(impactWorld, ringColor);
        spawnParticles(impactWorld, 'sweat', Math.round(8 + power * 6), whipX);
        spawnParticles(impactWorld, 'stars', Math.round(4 + power * 4), whipX);
      }

      phys.ropeBounceVel += 3.2 * power;
      phys.camShake = Math.min(0.14, 0.048 * power);
      phys.camPunchZoom = Math.min(0.32, 0.14 * power);
      redrawFaceSurface();

      if (window.AndroidBridge && window.AndroidBridge.onCharacterHit) {
        window.AndroidBridge.onCharacterHit(power, bridgeKind);
      }
    }

    /* =====================================================================
     * RAYCASTING REGIONAL HIT DETECTION & 360 ORBIT GESTURES
     * ===================================================================== */
    var raycaster = new THREE.Raycaster();
    var ndc = new THREE.Vector2();
    var pointer = {
      down: false,
      lastX: 0,
      lastY: 0,
      lastTime: 0,
      cooldown: 0
    };

    function notifyTouch(power, kind) {
      idleTimer = 6 + Math.random() * 4;
      if (window.AndroidBridge && window.AndroidBridge.onCharacterHit) {
        window.AndroidBridge.onCharacterHit(power, kind);
      }
    }

    // Karnına dokununca gıdıklanmış gibi güler.
    function pokeBelly() {
      fighter.playGesture('laugh');
      window.ArenaAudio.playBoing(0.6);
      phys.chestVelX += 2.5;
      notifyTouch(0.6, 'body');
    }

    // Ayağına dokununca canı yanar ve tek ayak üstünde zıplar.
    function pokeFoot() {
      fighter.playGesture('hop');
      window.ArenaAudio.playBodyBlow(0.5);
      notifyTouch(0.7, 'swipe');
    }

    function detectFighterZone(clientX, clientY) {
      ndc.x = (clientX / window.innerWidth) * 2 - 1;
      ndc.y = -(clientY / window.innerHeight) * 2 + 1;
      raycaster.setFromCamera(ndc, camera);

      var hits = raycaster.intersectObjects(fighter.hitboxes, false);
      if (hits.length > 0) {
        return hits[0].object.userData.zone;
      }

      // Generous screen-space proximity check for fast arcade swipes
      var headPos = new THREE.Vector3();
      headData.headGroup.getWorldPosition(headPos);
      headPos.project(camera);
      if (Math.hypot(ndc.x - headPos.x, ndc.y - headPos.y) < 0.24) {
        return ndc.x < headPos.x ? 'head_left' : 'head_right';
      }

      var bodyPos = new THREE.Vector3();
      fighter.chestPivot.getWorldPosition(bodyPos);
      bodyPos.y += 0.35;
      bodyPos.project(camera);
      if (Math.hypot(ndc.x - bodyPos.x, ndc.y - bodyPos.y) < 0.25) {
        return 'body';
      }
      return null;
    }

    canvas.addEventListener('pointerdown', function(e) {
      window.ArenaAudio.unlock();
      pointer.down = true;
      pointer.lastX = e.clientX;
      pointer.lastY = e.clientY;
      pointer.lastTime = performance.now();

      if (orbitState.enabled) return;

      var zone = detectFighterZone(e.clientX, e.clientY);
      if (zone && pointer.cooldown <= 0) {
        if (zone === 'foot') {
          pokeFoot();
        } else if (zone === 'body') {
          pokeBelly();
        } else {
          var dirX = zone === 'head_left' ? 1 : -1;
          window.ArenaAudio.playCheekSlap(0.75);
          triggerRegionalImpact(zone, dirX, 0.1, 0.75, 'swipe');
        }
        pointer.cooldown = 0.12;
      }
    });

    canvas.addEventListener('pointermove', function(e) {
      if (!pointer.down) return;
      var now = performance.now();
      var dtMs = Math.max(8, now - pointer.lastTime);
      var dx = e.clientX - pointer.lastX;
      var dy = e.clientY - pointer.lastY;

      if (orbitState.enabled) {
        orbitState.targetAzimuth -= dx * 0.0085;
        orbitState.targetPolar = Math.max(0.85, Math.min(1.68, orbitState.targetPolar - dy * 0.005));
        pointer.lastX = e.clientX;
        pointer.lastY = e.clientY;
        pointer.lastTime = now;
        return;
      }

      var dist = Math.hypot(dx, dy);
      if (dist > 16 && pointer.cooldown <= 0) {
        var zone = detectFighterZone(e.clientX, e.clientY);
        if (zone) {
          var speed = dist / dtMs;
          var power = Math.min(1.6, Math.max(0.65, speed * 0.58));
          var nx = dx / dist;
          var ny = -dy / dist;

          if (zone === 'foot') {
            pokeFoot();
          } else if (ny > 0.58 && zone !== 'body') {
            triggerRegionalImpact('uppercut', nx, ny, power * 1.15, 'uppercut');
          } else if (zone === 'body' && Math.abs(nx) < 0.65) {
            triggerRegionalImpact('body', nx, ny, power, 'body');
          } else {
            window.ArenaAudio.playCheekSlap(power);
            if (power > 0.95) window.ArenaAudio.playBoing(power * 0.7);
            triggerRegionalImpact(zone, nx, ny, power, 'swipe');
          }
          pointer.cooldown = 0.13;
        }
      }

      pointer.lastX = e.clientX;
      pointer.lastY = e.clientY;
      pointer.lastTime = now;
    });

    function stopPointer() { pointer.down = false; }
    canvas.addEventListener('pointerup', stopPointer);
    canvas.addEventListener('pointercancel', stopPointer);

    /* =====================================================================
     * PUBLIC BRIDGE API FOR NATIVE ANDROID HUD, WARDROBE & FACE STUDIO
     * ===================================================================== */
    var hookSide = 1;
    var KIT_PALETTES = {
      pure_white:    { primary: 0xF4F4F1, shorts: 0x18181B, trim: 0xF8FAFC },
      classic_red:   { primary: 0xD91B38, shorts: 0xC81632, trim: 0xF8FAFC },
      champion_gold: { primary: 0xF59E0B, shorts: 0x18181B, trim: 0xFFC800 },
      cyber_cyan:    { primary: 0x00B8D4, shorts: 0x0F172A, trim: 0x00E5FF },
      emerald_pro:   { primary: 0x059669, shorts: 0x064E3B, trim: 0xF8FAFC }
    };

    window.RingGame = {
      setSoundEnabled: function(enabled) {
        window.ArenaAudio.setEnabled(enabled);
      },
      setOrbitMode: function(enabled) {
        orbitState.enabled = !!enabled;
        if (!orbitState.enabled) {
          orbitState.targetAzimuth = 0;
          orbitState.targetPolar = 1.46;
        }
      },
      applyCustomization: function(kitKey, headgearKey, proportionKey, genderKey) {
        var pal = KIT_PALETTES[kitKey] || KIT_PALETTES.pure_white;
        fighter.setShirtColor('#' + ('000000' + pal.primary.toString(16)).slice(-6));
        fighter.materials.kitPrimaryMat.color.setHex(pal.primary);
        fighter.materials.trimMat.color.setHex(pal.trim);

        Object.keys(headData.headgearMap).forEach(function(k) {
          headData.headgearMap[k].visible = (k === headgearKey);
        });

        targetBaseHeadScale = (proportionKey === 'bobble') ? 1.36 : 1.0;
        if (genderKey) {
          fighter.setGender(genderKey).catch(function(err) { console.error('Avatar load error:', err); });
        }
        window.ArenaAudio.playRingBell(1);
        phys.guardOpenVel += 4.5;
      },
      triggerSlap: function() {
        window.ArenaAudio.playWhoosh(1.0);
        hookSide *= -1;
        if (gloveStrikeAnim) scene.remove(gloveStrikeAnim.mesh);
        var strikeGlove = fighter.createStrikeHand();
        strikeGlove.position.set(0, -6, 0);
        scene.add(strikeGlove);
        gloveStrikeAnim = {
          mesh: strikeGlove,
          mode: hookSide > 0 ? 'hook_right' : 'hook_left',
          side: hookSide,
          progress: 0,
          hitDone: false
        };
      },
      triggerUppercut: function() {
        window.ArenaAudio.playWhoosh(1.25);
        if (gloveStrikeAnim) scene.remove(gloveStrikeAnim.mesh);
        var strikeGlove = fighter.createStrikeFist();
        strikeGlove.rotation.x = Math.PI / 2;
        strikeGlove.position.set(0, -6, 0);
        scene.add(strikeGlove);
        gloveStrikeAnim = {
          mesh: strikeGlove,
          mode: 'uppercut',
          side: (Math.random() > 0.5 ? 1 : -1),
          progress: 0,
          hitDone: false
        };
      },
      triggerPunch: function() {
        window.ArenaAudio.playWhoosh(1.2);
        hookSide *= -1;
        if (gloveStrikeAnim) scene.remove(gloveStrikeAnim.mesh);
        var fist = fighter.createStrikeFist();
        fist.position.set(0, -6, 0);
        scene.add(fist);
        gloveStrikeAnim = { mesh: fist, mode: 'punch', side: hookSide, progress: 0, hitDone: false };
      },
      triggerKick: function() {
        window.ArenaAudio.playWhoosh(0.8);
        hookSide *= -1;
        if (gloveStrikeAnim) scene.remove(gloveStrikeAnim.mesh);
        var boot = fighter.createStrikeBoot();
        boot.position.set(0, -6, 0);
        scene.add(boot);
        gloveStrikeAnim = { mesh: boot, mode: 'kick', side: hookSide, progress: 0, hitDone: false };
      },
      triggerWaterBalloon: function() {
        window.ArenaAudio.playWhoosh(1.1);
        var grp = new THREE.Group();
        var ball = new THREE.Mesh(new THREE.SphereGeometry(0.19, 18, 16), waterMat);
        ball.scale.set(0.95, 1.18, 0.95);
        grp.add(ball);
        var startPos = new THREE.Vector3((Math.random() - 0.5) * 1.1, 1.3, 3.1);
        grp.position.copy(startPos);
        scene.add(grp);
        projectiles.push({ kind: 'water', mesh: grp, start: startPos, progress: 0, duration: 0.34 });
      },
      triggerPie: function() {
        window.ArenaAudio.playWhoosh(0.9);
        var grp = new THREE.Group();
        var tin = new THREE.Mesh(
          new THREE.CylinderGeometry(0.24, 0.19, 0.06, 20),
          new THREE.MeshStandardMaterial({ color: 0xCBD5E1, metalness: 0.75, roughness: 0.25 })
        );
        grp.add(tin);
        var cream = new THREE.Mesh(new THREE.SphereGeometry(0.22, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.55), creamMat);
        cream.position.y = 0.02;
        grp.add(cream);
        var ch = new THREE.Mesh(new THREE.SphereGeometry(0.048, 12, 10), cherryMat);
        ch.position.y = 0.24;
        grp.add(ch);
        grp.rotation.x = Math.PI / 2.2;
        var startPos = new THREE.Vector3((Math.random() - 0.5) * 1.0, 1.2, 3.1);
        grp.position.copy(startPos);
        scene.add(grp);
        projectiles.push({ kind: 'pie', mesh: grp, start: startPos, progress: 0, duration: 0.36 });
      },
      triggerReset: function() {
        window.ArenaAudio.playRingBell(2);
        while (headSplatGroup.children.length > 0) {
          headSplatGroup.remove(headSplatGroup.children[0]);
        }
        confetti.forEach(function(c) { scene.remove(c.mesh); });
        confetti = [];

        totalHitCounter = 0;
        hitStreak = 0;
        fighter.clearGesture();
        phys.superComboTimer = 0;
        phys.shiverTimer = 0;
        dizzyCrown.visible = false;
        feverStrobe.intensity = 0;

        faceState.expr = 'idle';
        faceState.slapAlpha = 0;
        redrawFaceSurface();

        var headPos = new THREE.Vector3();
        headData.headGroup.getWorldPosition(headPos);
        spawnParticles(headPos, 'clean', 18, 0);
      },
      startSuperCombo: function() {
        window.ArenaAudio.playKnockoutFanfare();
        phys.superComboTimer = 5.0;
        fighter.playGesture('fall');
        dizzyCrown.visible = true;
        faceState.expr = 'dizzy';
        redrawFaceSurface();

        var cols = [0xFF2A54, 0x00E5FF, 0xFFC800, 0x10B981, 0xEC4899, 0xA855F7];
        var cGeo = new THREE.PlaneGeometry(0.11, 0.055);
        for (var i = 0; i < 115; i++) {
          var cMesh = new THREE.Mesh(
            cGeo,
            new THREE.MeshBasicMaterial({ color: cols[i % cols.length], side: THREE.DoubleSide })
          );
          cMesh.position.set(
            (Math.random() - 0.5) * 5.2,
            3.4 + Math.random() * 2.5,
            (Math.random() - 0.5) * 3.6
          );
          scene.add(cMesh);
          confetti.push({
            mesh: cMesh,
            speed: 1.1 + Math.random() * 1.35,
            phase: Math.random() * Math.PI * 2,
            spin: new THREE.Vector3(3 + Math.random() * 5, 3 + Math.random() * 5, 3)
          });
        }
      },
      pullCustomFaceFromBridge: function() {
        if (!window.AndroidBridge || !window.AndroidBridge.getPendingFaceJson) return;
        try {
          var raw = window.AndroidBridge.getPendingFaceJson();
          if (!raw) return;
          var payload = JSON.parse(raw);
          var apply = payload.headDataUrl ? fighter.setPhotoHead(payload) : fighter.setFace(payload.textureDataUrl);
          apply.then(function() {
            window.ArenaAudio.playRingBell(1);
            phys.squash = 0.20;
            phys.neckVelY += 5.0;
          }).catch(function(err) { console.error('Custom face load error:', err); });
        } catch (err) {
          console.error('Custom face load error:', err);
        }
      },
      restoreDefaultFace: function() {
        fighter.setFace(null);
        window.ArenaAudio.playRingBell(1);
      },
      pullShirtImageFromBridge: function() {
        if (!window.AndroidBridge || !window.AndroidBridge.getPendingShirtImage) return;
        var dataUrl = window.AndroidBridge.getPendingShirtImage();
        if (!dataUrl) return;
        fighter.setShirtImage(dataUrl).then(function() {
          window.ArenaAudio.playRingBell(1);
        }).catch(function(err) { console.error('Shirt image load error:', err); });
      },
      clearShirtImage: function() {
        fighter.setShirtImage(null);
      },
      playGesture: function(name) {
        fighter.playGesture(name);
      }
    };

    /* =====================================================================
     * REAL-TIME ANIMATION, FIGHTER KINEMATICS & SPRING SIMULATION
     * ===================================================================== */
    var clock = new THREE.Clock();

    function animate() {
      requestAnimationFrame(animate);
      var rawDt = Math.min(0.033, clock.getDelta());
      if (pointer.cooldown > 0) pointer.cooldown -= rawDt;

      // Hit-Stop micro-freeze for crisp AAA fighting game impact crunch!
      if (phys.hitStopTimer > 0) {
        phys.hitStopTimer -= rawDt;
        renderer.render(scene, camera);
        return;
      }

      var dt = rawDt;
      var elapsed = clock.getElapsedTime();

      // 1. Incoming Boxing Strike Glove Animation (Hook / Uppercut)
      if (gloveStrikeAnim) {
        gloveStrikeAnim.progress += dt * 4.2;
        var gp = gloveStrikeAnim.progress;
        var headW = new THREE.Vector3();
        headData.headGroup.getWorldPosition(headW);

        // Vuruş ileri gider, isabetten sonra geri çekilir.
        var strikeReach = gp < 0.5 ? gp * 2 : Math.max(0, 2 - gp * 2);
        if (gloveStrikeAnim.mode === 'punch') {
          gloveStrikeAnim.mesh.position.set(
            headW.x + gloveStrikeAnim.side * 0.35 * (1 - strikeReach),
            headW.y - 0.1 * (1 - strikeReach),
            headW.z + 0.24 + (1 - strikeReach) * 2.3
          );
          if (!gloveStrikeAnim.hitDone && gp >= 0.5) {
            gloveStrikeAnim.hitDone = true;
            triggerRegionalImpact('punch', gloveStrikeAnim.side * 0.4, 0, 1.4, 'punch');
          }
        } else if (gloveStrikeAnim.mode === 'kick') {
          var chestW = new THREE.Vector3();
          fighter.chestPivot.getWorldPosition(chestW);
          gloveStrikeAnim.mesh.position.set(
            chestW.x + gloveStrikeAnim.side * 0.9 * (1 - strikeReach),
            chestW.y - 0.12 - 0.8 * (1 - strikeReach),
            chestW.z + 0.36 + (1 - strikeReach) * 1.5
          );
          gloveStrikeAnim.mesh.rotation.x = -0.7 * (1 - strikeReach);
          if (!gloveStrikeAnim.hitDone && gp >= 0.5) {
            gloveStrikeAnim.hitDone = true;
            triggerRegionalImpact('kick', -gloveStrikeAnim.side * 0.3, 0.2, 1.4, 'kick');
          }
        } else if (gloveStrikeAnim.mode === 'uppercut') {
          gloveStrikeAnim.mesh.position.set(
            headW.x + gloveStrikeAnim.side * 0.12 * (1 - gp),
            headW.y - 0.95 + gp * 1.35,
            headW.z + 0.55 - Math.sin(gp * Math.PI) * 0.22
          );
          if (!gloveStrikeAnim.hitDone && gp >= 0.52) {
            gloveStrikeAnim.hitDone = true;
            triggerRegionalImpact('uppercut', gloveStrikeAnim.side * 0.25, 1.0, 1.42, 'uppercut');
          }
        } else {
          var arc = (gp - 0.5) * Math.PI * 0.9 * gloveStrikeAnim.side;
          gloveStrikeAnim.mesh.position.set(
            headW.x - Math.sin(arc) * 1.45,
            headW.y + Math.sin(gp * Math.PI) * 0.12,
            headW.z + 0.65 - Math.sin(gp * Math.PI) * 0.30
          );
          if (!gloveStrikeAnim.hitDone && gp >= 0.50) {
            gloveStrikeAnim.hitDone = true;
            window.ArenaAudio.playCheekSlap(1.38);
            window.ArenaAudio.playBoing(0.95);
            triggerRegionalImpact('head_hook', gloveStrikeAnim.side, 0.15, 1.38, 'slap');
          }
        }

        if (gp >= 1.0) {
          scene.remove(gloveStrikeAnim.mesh);
          gloveStrikeAnim = null;
        }
      }

      // 2. Flying Projectiles (Water Balloon & Whipped Cream Pie)
      for (var pi = projectiles.length - 1; pi >= 0; pi--) {
        var pr = projectiles[pi];
        pr.progress += dt / pr.duration;
        var pt = Math.min(1, pr.progress);
        var tgt = new THREE.Vector3();
        headData.headGroup.getWorldPosition(tgt);
        tgt.z += 0.34;

        pr.mesh.position.lerpVectors(pr.start, tgt, pt);
        pr.mesh.position.y += Math.sin(pt * Math.PI) * 0.72;
        pr.mesh.rotation.z += dt * 9;

        if (pt >= 1) {
          scene.remove(pr.mesh);
          projectiles.splice(pi, 1);
          if (pr.kind === 'water') {
            window.ArenaAudio.playSplash();
            spawnParticles(tgt, 'water', 36, 0);
            attachWaterDroplets();
            phys.shiverTimer = 0.85;
            triggerRegionalImpact('head_hook', (Math.random() - 0.5) * 1.2, -0.3, 1.08, 'water');
          } else {
            window.ArenaAudio.playSplat();
            spawnParticles(tgt, 'cream', 34, 0);
            attachPieCreamDecal();
            triggerRegionalImpact('head_hook', (Math.random() - 0.5) * 0.7, 0.25, 1.22, 'pie');
          }
        }
      }

      // 3. Super Knockout Fever Sway & Strobe
      var excitement = 0.0;
      if (phys.superComboTimer > 0) {
        excitement = 1.0;
        phys.superComboTimer -= dt;
        dizzyCrown.rotation.y += dt * 5.2;
        feverStrobe.intensity = 1.8 + Math.sin(elapsed * 20) * 1.0;
        phys.neckVelZ += Math.cos(elapsed * 7.2) * 16 * dt;
        phys.neckVelX += Math.sin(elapsed * 6.0) * 12 * dt;
        phys.chestVelZ += Math.cos(elapsed * 3.6) * 5.5 * dt;

        if (phys.superComboTimer <= 0) {
          dizzyCrown.visible = false;
          feverStrobe.intensity = 0;
          faceState.expr = 'idle';
          redrawFaceSurface();
        }
      }

      if (phys.shiverTimer > 0) {
        phys.shiverTimer -= dt;
        phys.neckVelY += Math.sin(elapsed * 60) * 44 * dt;
      }

      // 4. Damped Harmonic Springs (Neck, Spine, Knees, Guard, Gut-Clutch, Squash)
      phys.neckVelX += (-76 * phys.neckRotX - 6.6 * phys.neckVelX) * dt;
      phys.neckVelY += (-76 * phys.neckRotY - 6.6 * phys.neckVelY) * dt;
      phys.neckVelZ += (-76 * phys.neckRotZ - 6.6 * phys.neckVelZ) * dt;
      phys.neckRotX = Math.max(-1.05, Math.min(0.95, phys.neckRotX + phys.neckVelX * dt));
      phys.neckRotY = Math.max(-1.20, Math.min(1.20, phys.neckRotY + phys.neckVelY * dt));
      phys.neckRotZ = Math.max(-0.85, Math.min(0.85, phys.neckRotZ + phys.neckVelZ * dt));

      phys.headShiftVelX += (-110 * phys.headShiftX - 8.2 * phys.headShiftVelX) * dt;
      phys.headShiftVelY += (-110 * phys.headShiftY - 8.2 * phys.headShiftVelY) * dt;
      phys.headShiftVelZ += (-110 * phys.headShiftZ - 8.2 * phys.headShiftVelZ) * dt;
      phys.headShiftX = Math.max(-0.24, Math.min(0.24, phys.headShiftX + phys.headShiftVelX * dt));
      phys.headShiftY = Math.max(-0.18, Math.min(0.22, phys.headShiftY + phys.headShiftVelY * dt));
      phys.headShiftZ = Math.max(-0.26, Math.min(0.22, phys.headShiftZ + phys.headShiftVelZ * dt));

      phys.chestVelX += (-54 * phys.chestRotX - 6.8 * phys.chestVelX) * dt;
      phys.chestVelY += (-54 * phys.chestRotY - 6.8 * phys.chestVelY) * dt;
      phys.chestVelZ += (-54 * phys.chestRotZ - 6.8 * phys.chestVelZ) * dt;
      phys.chestRotX = Math.max(-0.55, Math.min(0.65, phys.chestRotX + phys.chestVelX * dt));
      phys.chestRotY = Math.max(-0.55, Math.min(0.55, phys.chestRotY + phys.chestVelY * dt));
      phys.chestRotZ = Math.max(-0.42, Math.min(0.42, phys.chestRotZ + phys.chestVelZ * dt));

      phys.kneeBendVel += (-62 * phys.kneeBend - 7.5 * phys.kneeBendVel) * dt;
      phys.kneeBend = Math.max(-0.15, Math.min(0.45, phys.kneeBend + phys.kneeBendVel * dt));

      phys.guardOpenVel += (-58 * phys.guardOpen - 7.2 * phys.guardOpenVel) * dt;
      phys.guardOpen = Math.max(-0.3, Math.min(1.2, phys.guardOpen + phys.guardOpenVel * dt));

      phys.gutClutchVel += (-48 * phys.gutClutch - 6.5 * phys.gutClutchVel) * dt;
      phys.gutClutch = Math.max(0, Math.min(1.0, phys.gutClutch + phys.gutClutchVel * dt));

      phys.squashVel += (-140 * phys.squash - 9.5 * phys.squashVel) * dt;
      phys.squash = Math.max(-0.32, Math.min(0.32, phys.squash + phys.squashVel * dt));

      // 5. Insansi avatarin durusu, darbe tepkileri ve yuz ifadeleri
      phys.pushVel += (-26 * phys.pushZ - 5.5 * phys.pushVel) * dt;
      phys.pushZ = Math.max(0, Math.min(1.1, phys.pushZ + phys.pushVel * dt));
      fighter.root.position.z = 0.22 - phys.pushZ;

      idleTimer -= dt;
      if (idleTimer <= 0 && !fighter.isBusy && phys.superComboTimer <= 0) {
        var idleMoves = ['look', 'scratch', 'stretch'];
        fighter.playGesture(idleMoves[Math.floor(Math.random() * idleMoves.length)]);
        idleTimer = 5 + Math.random() * 5;
      }
      fighter.applyPose(elapsed, dt, phys, faceState.expr, targetBaseHeadScale);

      // 7. Face Timers & Blinking
      var dirtyCanvas = false;
      if (faceState.timer > 0 && phys.superComboTimer <= 0) {
        faceState.timer -= dt;
        if (faceState.timer <= 0) {
          faceState.expr = 'idle';
          dirtyCanvas = true;
        }
      }
      if (faceState.slapAlpha > 0) {
        faceState.slapAlpha = Math.max(0, faceState.slapAlpha - dt * 0.28);
        dirtyCanvas = true;
      }
      if (dirtyCanvas) redrawFaceSurface();

      // 8. Update Shockwave Rings, Particles, Confetti & Stadium Crowd
      for (var sw = shockwaves.length - 1; sw >= 0; sw--) {
        var sItem = shockwaves[sw];
        sItem.age += dt;
        if (sItem.age >= sItem.maxAge) {
          scene.remove(sItem.mesh);
          shockwaves.splice(sw, 1);
          continue;
        }
        var sp = sItem.age / sItem.maxAge;
        sItem.mesh.scale.setScalar(1.0 + sp * 4.5);
        sItem.mat.opacity = (1.0 - sp) * 0.85;
      }

      for (var pIdx = particles.length - 1; pIdx >= 0; pIdx--) {
        var pItem = particles[pIdx];
        pItem.life -= dt;
        if (pItem.life <= 0) {
          scene.remove(pItem.mesh);
          particles.splice(pIdx, 1);
          continue;
        }
        pItem.vel.y -= pItem.gravity * dt;
        pItem.mesh.position.addScaledVector(pItem.vel, dt);
        pItem.mesh.rotation.x += pItem.rotVel.x * dt;
        pItem.mesh.rotation.y += pItem.rotVel.y * dt;
        pItem.mesh.scale.multiplyScalar(0.985);
      }

      for (var ci = confetti.length - 1; ci >= 0; ci--) {
        var cf = confetti[ci];
        cf.mesh.position.y -= cf.speed * dt;
        cf.mesh.position.x += Math.sin(elapsed * 4 + cf.phase) * 0.6 * dt;
        cf.mesh.rotation.x += cf.spin.x * dt;
        cf.mesh.rotation.y += cf.spin.y * dt;
        if (cf.mesh.position.y < -0.3) {
          if (phys.superComboTimer > 0.6) {
            cf.mesh.position.y = 4.4 + Math.random();
          } else {
            scene.remove(cf.mesh);
            confetti.splice(ci, 1);
          }
        }
      }

      phys.ropeBounceVel += (-88 * phys.ropeBounce - 6.5 * phys.ropeBounceVel) * dt;
      phys.ropeBounce += phys.ropeBounceVel * dt;
      ring.update(dt, elapsed, excitement, phys.ropeBounce);

      // 9. Smooth Orbit / Broadcast Fight Camera Update
      orbitState.azimuth += (orbitState.targetAzimuth - orbitState.azimuth) * Math.min(1, dt * 10);
      orbitState.polar += (orbitState.targetPolar - orbitState.polar) * Math.min(1, dt * 10);
      phys.camPunchZoom *= 0.86;

      var activeDist = baseCamDist - phys.camPunchZoom;
      var cx = Math.sin(orbitState.polar) * Math.sin(orbitState.azimuth) * activeDist;
      var cy = Math.cos(orbitState.polar) * activeDist + 1.15;
      var cz = Math.sin(orbitState.polar) * Math.cos(orbitState.azimuth) * activeDist;

      if (phys.camShake > 0.002) {
        cx += (Math.random() - 0.5) * phys.camShake;
        cy += (Math.random() - 0.5) * phys.camShake;
        phys.camShake *= 0.85;
      }

      camera.position.set(cx, cy, cz);
      camera.lookAt(baseLookAt);
      renderer.render(scene, camera);
    }

    window.addEventListener('resize', function() {
      renderer.setSize(window.innerWidth, window.innerHeight);
      updateCameraFraming();
    });

    animate();

    if (window.AndroidBridge && window.AndroidBridge.onSceneReady) {
      window.AndroidBridge.onSceneReady();
    }
    window.RingGame.pullCustomFaceFromBridge();
  }

  function bootThreeAndStart() {
    if (typeof THREE !== 'undefined') {
      initChampionshipArena();
      return;
    }
    var cdns = [
      'https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js',
      'https://unpkg.com/three@0.128.0/build/three.min.js'
    ];
    var idx = 0;
    function tryNext() {
      if (idx >= cdns.length) return;
      var s = document.createElement('script');
      s.src = cdns[idx++];
      s.onload = initChampionshipArena;
      s.onerror = tryNext;
      document.head.appendChild(s);
    }
    tryNext();
  }

  bootThreeAndStart();
})();
