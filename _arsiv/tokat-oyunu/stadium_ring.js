/* =========================================================================
 * CHAMPIONSHIP STADIUM BOXING RING, TRUSS LIGHTS, CROWD & CAMERA FLASHES
 * ========================================================================= */
window.StadiumRing = (function() {

  function createChampionshipRing(scene) {
    var arenaGroup = new THREE.Group();
    scene.add(arenaGroup);

    // 1.Ring Apron Skirt with Fabric Fold Texture
    var skirtCanvas = document.createElement('canvas');
    skirtCanvas.width = 512;
    skirtCanvas.height = 128;
    var sCtx = skirtCanvas.getContext('2d');
    var sGrad = sCtx.createLinearGradient(0, 0, 0, 128);
    sGrad.addColorStop(0, '#141B3A');
    sGrad.addColorStop(1, '#080C1D');
    sCtx.fillStyle = sGrad;
    sCtx.fillRect(0, 0, 512, 128);
    for (var fx = 0; fx < 512; fx += 16) {
      sCtx.fillStyle = fx % 32 === 0 ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.18)';
      sCtx.fillRect(fx, 0, 8, 128);
    }
    sCtx.fillStyle = '#FFC800';
    sCtx.fillRect(0, 0, 512, 10);
    var skirtTex = new THREE.CanvasTexture(skirtCanvas); skirtTex.colorSpace = THREE.SRGBColorSpace;

    var apronMesh = new THREE.Mesh(
      new THREE.BoxGeometry(5.9, 0.85, 5.5),
      new THREE.MeshStandardMaterial({ map: skirtTex, roughness: 0.65 })
    );
    apronMesh.position.y = -0.44;
    apronMesh.receiveShadow = true;
    arenaGroup.add(apronMesh);

    // 2. Pro Championship Canvas Mat
    var matCanvas = document.createElement('canvas');
    matCanvas.width = 1024;
    matCanvas.height = 1024;
    var mCtx = matCanvas.getContext('2d');
    var matGrad = mCtx.createRadialGradient(512, 512, 60, 512, 512, 680);
    matGrad.addColorStop(0, '#1E40AF');
    matGrad.addColorStop(0.72, '#172554');
    matGrad.addColorStop(1, '#0F172A');
    mCtx.fillStyle = matGrad;
    mCtx.fillRect(0, 0, 1024, 1024);

    // Subtle canvas weave grid
    mCtx.strokeStyle = 'rgba(255,255,255,0.03)';
    mCtx.lineWidth = 2;
    for (var g = 0; g < 1024; g += 32) {
      mCtx.beginPath();
      mCtx.moveTo(g, 0); mCtx.lineTo(g, 1024);
      mCtx.moveTo(0, g); mCtx.lineTo(1024, g);
      mCtx.stroke();
    }

    // Ring boundary stripes & Championship Center Emblem
    mCtx.strokeStyle = 'rgba(248, 250, 252, 0.82)';
    mCtx.lineWidth = 14;
    mCtx.strokeRect(76, 76, 872, 872);

    mCtx.strokeStyle = '#FF2A54';
    mCtx.lineWidth = 8;
    mCtx.strokeRect(98, 98, 828, 828);

    mCtx.beginPath();
    mCtx.arc(512, 512, 185, 0, Math.PI * 2);
    mCtx.fillStyle = 'rgba(15, 23, 42, 0.55)';
    mCtx.fill();
    mCtx.lineWidth = 12;
    mCtx.strokeStyle = '#FFC800';
    mCtx.stroke();

    mCtx.font = 'bold 54px sans-serif';
    mCtx.textAlign = 'center';
    mCtx.fillStyle = '#FFC800';
    mCtx.fillText('CHAMPIONSHIP', 512, 502);
    mCtx.font = 'bold 40px sans-serif';
    mCtx.fillStyle = '#00E5FF';
    mCtx.fillText('RING 3D', 512, 554);

    var matTex = new THREE.CanvasTexture(matCanvas); matTex.colorSpace = THREE.SRGBColorSpace;
    var matMesh = new THREE.Mesh(
      new THREE.BoxGeometry(5.8, 0.10, 5.4),
      new THREE.MeshStandardMaterial({ map: matTex, roughness: 0.72, metalness: 0.04 })
    );
    matMesh.position.y = 0.0;
    matMesh.receiveShadow = true;
    arenaGroup.add(matMesh);

    // 3. Corner Posts, Padded Cushions, Turnbuckles & Ropes
    var corners = [
      { x: -2.65, z: -2.45, color: 0xFF2A54 },
      { x:  2.65, z: -2.45, color: 0x00E5FF },
      { x: -2.65, z:  2.45, color: 0xF8FAFC },
      { x:  2.65, z:  2.45, color: 0xF8FAFC }
    ];
    var chromeMat = new THREE.MeshStandardMaterial({ color: 0xCBD5E1, metalness: 0.85, roughness: 0.2 });

    corners.forEach(function(c) {
      var post = new THREE.Mesh(
        new THREE.CylinderGeometry(0.095, 0.105, 1.72, 18),
        new THREE.MeshStandardMaterial({ color: 0x1E293B, metalness: 0.7, roughness: 0.3 })
      );
      post.position.set(c.x, 0.84, c.z);
      post.castShadow = true;
      arenaGroup.add(post);

      // Padded Vertical Corner Cushion facing inward toward center
      var pad = new THREE.Mesh(
        new THREE.CylinderGeometry(0.09, 0.09, 1.22, 14),
        new THREE.MeshStandardMaterial({ color: c.color, roughness: 0.38 })
      );
      var inX = -Math.sign(c.x) * 0.14;
      var inZ = -Math.sign(c.z) * 0.14;
      pad.position.set(c.x + inX, 0.96, c.z + inZ);
      arenaGroup.add(pad);

      // Turnbuckle links
      [0.48, 0.94, 1.40].forEach(function(ry) {
        var tb = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.26, 8), chromeMat);
        tb.rotation.z = Math.PI / 2;
        tb.rotation.y = Math.atan2(c.z, c.x);
        tb.position.set(c.x + inX * 0.5, ry, c.z + inZ * 0.5);
        arenaGroup.add(tb);
      });
    });

    // Corner Fighter Stool in back-red corner for authentic gym/stadium detail!
    var stoolTop = new THREE.Mesh(
      new THREE.CylinderGeometry(0.22, 0.22, 0.06, 18),
      new THREE.MeshStandardMaterial({ color: 0xFF2A54, roughness: 0.4 })
    );
    stoolTop.position.set(-2.05, 0.42, -1.90);
    arenaGroup.add(stoolTop);
    for (var sl = 0; sl < 3; sl++) {
      var sAng = (sl / 3) * Math.PI * 2;
      var sLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.016, 0.42, 8), chromeMat);
      sLeg.position.set(-2.05 + Math.cos(sAng) * 0.14, 0.21, -1.90 + Math.sin(sAng) * 0.14);
      arenaGroup.add(sLeg);
    }

    // Tensioned Ropes (Back, Left, Right)
    var ropeSpecs = [
      { y: 0.48, color: 0xFF2A54 },
      { y: 0.94, color: 0xF8FAFC },
      { y: 1.40, color: 0x00E5FF }
    ];
    var ropeMeshes = [];

    function addCatenaryRope(p1, p2, baseY, colorHex) {
      var pts = [];
      for (var s = 0; s <= 16; s++) {
        var t = s / 16;
        var sag = Math.sin(t * Math.PI) * -0.022;
        pts.push(new THREE.Vector3(
          p1.x + (p2.x - p1.x) * t,
          baseY + sag,
          p1.z + (p2.z - p1.z) * t
        ));
      }
      var curve = new THREE.CatmullRomCurve3(pts);
      var rMesh = new THREE.Mesh(
        new THREE.TubeGeometry(curve, 20, 0.026, 8, false),
        new THREE.MeshStandardMaterial({ color: colorHex, roughness: 0.38 })
      );
      arenaGroup.add(rMesh);
      ropeMeshes.push({ mesh: rMesh, baseY: 0 });
    }

    ropeSpecs.forEach(function(rs) {
      addCatenaryRope({ x: -2.51, z: -2.31 }, { x: 2.51, z: -2.31 }, rs.y, rs.color);
      addCatenaryRope({ x: -2.51, z: -2.31 }, { x: -2.51, z: 2.31 }, rs.y, rs.color);
      addCatenaryRope({ x:  2.51, z: -2.31 }, { x:  2.51, z: 2.31 }, rs.y, rs.color);
    });

    // 4. Overhead Lighting Truss & Volumetric Stadium Spotlight Beams
    var trussGroup = new THREE.Group();
    trussGroup.position.y = 4.55;
    arenaGroup.add(trussGroup);

    var trussMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8, roughness: 0.3 });
    var trussRing = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.16, 4.2), trussMat);
    trussGroup.add(trussRing);

    var beamCones = [];
    var spotColors = [0x00E5FF, 0xFF2A54, 0xFFFBEB, 0xFFC800];
    [
      { x: -2.1, z: -1.9 },
      { x:  2.1, z: -1.9 },
      { x: -1.8, z:  1.6 },
      { x:  1.8, z:  1.6 }
    ].forEach(function(sp, idx) {
      var coneGeo = new THREE.ConeGeometry(1.35, 4.8, 20, 1, true);
      var coneMat = new THREE.MeshBasicMaterial({
        color: spotColors[idx],
        transparent: true,
        opacity: 0.018,
        side: THREE.DoubleSide,
        depthWrite: false,
        blending: THREE.AdditiveBlending
      });
      var cone = new THREE.Mesh(coneGeo, coneMat);
      cone.position.set(sp.x * 0.55, -2.3, sp.z * 0.55);
      cone.rotation.z = sp.x * 0.12;
      cone.rotation.x = -sp.z * 0.12;
      trussGroup.add(cone);
      beamCones.push(cone);
    });

    // 5. Animated Cheering Stadium Crowd Silhouettes & Camera Flashbulbs in Background
    var crowdActors = [];
    var crowdMat = new THREE.MeshBasicMaterial({ color: 0x0B1124 });
    for (var cIdx = 0; cIdx < 46; cIdx++) {
      var ang = Math.PI * 0.82 + (cIdx / 45) * Math.PI * 1.36; // Behind and beside the ring
      var radius = 6.2 + (cIdx % 3) * 0.95;
      var person = new THREE.Group();
      var pBody = new THREE.Mesh(new THREE.SphereGeometry(0.24, 8, 8), crowdMat);
      pBody.scale.set(1.1, 1.5, 0.7);
      var pHead = new THREE.Mesh(new THREE.SphereGeometry(0.13, 8, 8), crowdMat);
      pHead.position.y = 0.42;
      person.add(pBody);
      person.add(pHead);
      var baseY = -0.15 + (cIdx % 3) * 0.38;
      person.position.set(Math.sin(ang) * radius, baseY, Math.cos(ang) * radius);
      person.lookAt(0, 1.0, 0);
      arenaGroup.add(person);
      crowdActors.push({ mesh: person, baseY: baseY, phase: cIdx * 0.9 });
    }

    // Camera Flashbulbs in Stadium Stands
    var flashMat = new THREE.MeshBasicMaterial({
      color: 0xFFFFFF,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending
    });
    var flashMesh = new THREE.Mesh(new THREE.SphereGeometry(0.28, 8, 8), flashMat);
    arenaGroup.add(flashMesh);
    var flashTimer = 0;

    return {
      ropeMeshes: ropeMeshes,
      beamCones: beamCones,
      triggerCameraFlash: function() {
        var fAng = Math.PI * (0.85 + Math.random() * 1.3);
        var fRad = 6.5 + Math.random() * 2.5;
        flashMesh.position.set(Math.sin(fAng) * fRad, 0.9 + Math.random() * 1.8, Math.cos(fAng) * fRad);
        flashMat.opacity = 0.95;
        flashTimer = 0.12;
      },
      update: function(dt, elapsed, excitement, ropeBounce) {
        for (var i = 0; i < ropeMeshes.length; i++) {
          ropeMeshes[i].mesh.position.y = Math.sin(elapsed * 20 + i) * ropeBounce * 0.045;
        }
        var jumpAmp = 0.03 + excitement * 0.09;
        var jumpFreq = 4.0 + excitement * 7.0;
        for (var c = 0; c < crowdActors.length; c++) {
          var ca = crowdActors[c];
          ca.mesh.position.y = ca.baseY + Math.abs(Math.sin(elapsed * jumpFreq + ca.phase)) * jumpAmp;
        }
        if (flashTimer > 0) {
          flashTimer -= dt;
          flashMat.opacity = Math.max(0, flashTimer / 0.12);
        } else if (excitement > 0.6 && Math.random() < 0.08) {
          this.triggerCameraFlash();
        }
      }
    };
  }

  return {
    createChampionshipRing: createChampionshipRing
  };
})();
