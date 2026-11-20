/* =========================================================================
 * STUDIO MULTI-LAYER FIGHTING & SLAPSTICK WEB AUDIO SYNTHESIZER
 * ========================================================================= */
window.ArenaAudio = (function() {
  var ctx = null;
  var enabled = true;

  function ensure() {
    if (!enabled) return null;
    if (!ctx) {
      var AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) ctx = new AudioCtx();
    }
    // iOS, arka plandan dönünce sesi 'interrupted' durumunda bırakabilir.
    if (ctx && ctx.state !== 'running') {
      var resumed = ctx.resume();
      if (resumed && resumed.catch) resumed.catch(function() {});
    }
    return ctx;
  }

  function createNoiseBuffer(c, duration, decayPower) {
    var len = Math.max(1, Math.floor(c.sampleRate * duration));
    var buf = c.createBuffer(1, len, c.sampleRate);
    var ch = buf.getChannelData(0);
    var p = decayPower || 1.5;
    for (var i = 0; i < len; i++) {
      ch[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, p);
    }
    return buf;
  }

  return {
    setEnabled: function(flag) {
      enabled = !!flag;
    },
    unlock: function() {
      ensure();
    },
    playWhoosh: function(pitchScale) {
      var c = ensure();
      if (!c) return;
      var now = c.currentTime;
      var dur = 0.20;
      var src = c.createBufferSource();
      src.buffer = createNoiseBuffer(c, dur, 0.8);

      var bp = c.createBiquadFilter();
      bp.type = 'bandpass';
      bp.Q.value = 2.4;
      var base = 260 * (pitchScale || 1.0);
      bp.frequency.setValueAtTime(base, now);
      bp.frequency.exponentialRampToValueAtTime(base * 4.5, now + dur * 0.65);
      bp.frequency.exponentialRampToValueAtTime(base * 1.2, now + dur);

      var g = c.createGain();
      g.gain.setValueAtTime(0.01, now);
      g.gain.linearRampToValueAtTime(0.30, now + 0.05);
      g.gain.exponentialRampToValueAtTime(0.001, now + dur);

      src.connect(bp);
      bp.connect(g);
      g.connect(c.destination);
      src.start(now);
    },
    playCheekSlap: function(intensity) {
      var c = ensure();
      if (!c) return;
      var now = c.currentTime;
      var p = Math.min(1.5, Math.max(0.45, intensity || 0.9));

      // Crisp skin/leather crack
      var nSrc = c.createBufferSource();
      nSrc.buffer = createNoiseBuffer(c, 0.12, 2.0);
      var bp = c.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.setValueAtTime(1650 + p * 550, now);
      bp.Q.value = 1.15;
      var nGain = c.createGain();
      nGain.gain.setValueAtTime(0.58 * p, now);
      nGain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
      nSrc.connect(bp);
      bp.connect(nGain);
      nGain.connect(c.destination);
      nSrc.start(now);

      // Sub-punch thud
      var osc = c.createOscillator();
      var oGain = c.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(195 * p, now);
      osc.frequency.exponentialRampToValueAtTime(44, now + 0.15);
      oGain.gain.setValueAtTime(0.52 * p, now);
      oGain.gain.exponentialRampToValueAtTime(0.001, now + 0.16);
      osc.connect(oGain);
      oGain.connect(c.destination);
      osc.start(now);
      osc.stop(now + 0.17);
    },
    playUppercutCrunch: function(intensity) {
      var c = ensure();
      if (!c) return;
      var now = c.currentTime;
      var p = Math.min(1.5, Math.max(0.7, intensity || 1.1));

      this.playCheekSlap(p * 1.05);

      // Rising jaw impact overtone
      var osc = c.createOscillator();
      var g = c.createGain();
      osc.type = 'sawtooth';
      var lp = c.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.setValueAtTime(1400, now);
      lp.frequency.exponentialRampToValueAtTime(320, now + 0.25);

      osc.frequency.setValueAtTime(110, now);
      osc.frequency.exponentialRampToValueAtTime(310, now + 0.08);
      osc.frequency.exponentialRampToValueAtTime(75, now + 0.25);

      g.gain.setValueAtTime(0.32 * p, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.26);

      osc.connect(lp);
      lp.connect(g);
      g.connect(c.destination);
      osc.start(now);
      osc.stop(now + 0.27);
    },
    playBodyBlow: function(intensity) {
      var c = ensure();
      if (!c) return;
      var now = c.currentTime;
      var p = Math.min(1.4, Math.max(0.6, intensity || 1.0));

      // Heavy sub-bass gut thud
      var sub = c.createOscillator();
      var sGain = c.createGain();
      sub.type = 'sine';
      sub.frequency.setValueAtTime(135, now);
      sub.frequency.exponentialRampToValueAtTime(36, now + 0.22);
      sGain.gain.setValueAtTime(0.68 * p, now);
      sGain.gain.exponentialRampToValueAtTime(0.001, now + 0.24);
      sub.connect(sGain);
      sGain.connect(c.destination);
      sub.start(now);
      sub.stop(now + 0.25);

      // Breath "Ufff!" formant puff
      var breath = c.createBufferSource();
      breath.buffer = createNoiseBuffer(c, 0.24, 1.3);
      var f1 = c.createBiquadFilter();
      f1.type = 'bandpass';
      f1.frequency.setValueAtTime(420, now + 0.03);
      f1.frequency.exponentialRampToValueAtTime(260, now + 0.24);
      f1.Q.value = 4.2;
      var bGain = c.createGain();
      bGain.gain.setValueAtTime(0.34 * p, now + 0.02);
      bGain.gain.exponentialRampToValueAtTime(0.001, now + 0.24);
      breath.connect(f1);
      f1.connect(bGain);
      bGain.connect(c.destination);
      breath.start(now + 0.02);
    },
    playBoing: function(intensity) {
      var c = ensure();
      if (!c) return;
      var now = c.currentTime;
      var p = Math.min(1.3, Math.max(0.45, intensity || 0.75));
      var dur = 0.34;

      var carrier = c.createOscillator();
      var lfo = c.createOscillator();
      var lfoGain = c.createGain();
      var outGain = c.createGain();

      carrier.type = 'sine';
      var base = 155 + p * 45;
      carrier.frequency.setValueAtTime(base * 0.8, now);
      carrier.frequency.exponentialRampToValueAtTime(base * 1.65, now + 0.09);
      carrier.frequency.exponentialRampToValueAtTime(base, now + dur);

      lfo.type = 'sine';
      lfo.frequency.setValueAtTime(20, now);
      lfoGain.gain.setValueAtTime(26 * p, now);
      lfoGain.gain.exponentialRampToValueAtTime(2, now + dur);

      outGain.gain.setValueAtTime(0.18 * p, now);
      outGain.gain.exponentialRampToValueAtTime(0.001, now + dur);

      lfo.connect(lfoGain);
      lfoGain.connect(carrier.frequency);
      carrier.connect(outGain);
      outGain.connect(c.destination);
      carrier.start(now);
      lfo.start(now);
      carrier.stop(now + dur + 0.02);
      lfo.stop(now + dur + 0.02);
    },
    playSplash: function() {
      var c = ensure();
      if (!c) return;
      var now = c.currentTime;
      var dur = 0.38;
      var src = c.createBufferSource();
      src.buffer = createNoiseBuffer(c, dur, 1.25);

      var bp = c.createBiquadFilter();
      bp.type = 'bandpass';
      bp.Q.value = 3.0;
      bp.frequency.setValueAtTime(920, now);
      bp.frequency.exponentialRampToValueAtTime(2700, now + 0.08);
      bp.frequency.exponentialRampToValueAtTime(500, now + dur);

      var g = c.createGain();
      g.gain.setValueAtTime(0.55, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + dur);
      src.connect(bp);
      bp.connect(g);
      g.connect(c.destination);
      src.start(now);

      for (var b = 0; b < 4; b++) {
        var bOsc = c.createOscillator();
        var bGain = c.createGain();
        var t = now + 0.03 + b * 0.05;
        bOsc.type = 'sine';
        bOsc.frequency.setValueAtTime(450 + b * 140, t);
        bOsc.frequency.exponentialRampToValueAtTime(1180 + b * 150, t + 0.06);
        bGain.gain.setValueAtTime(0.15, t);
        bGain.gain.exponentialRampToValueAtTime(0.001, t + 0.065);
        bOsc.connect(bGain);
        bGain.connect(c.destination);
        bOsc.start(t);
        bOsc.stop(t + 0.07);
      }
    },
    playSplat: function() {
      var c = ensure();
      if (!c) return;
      var now = c.currentTime;

      var osc = c.createOscillator();
      var g = c.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(230, now);
      osc.frequency.exponentialRampToValueAtTime(48, now + 0.28);

      var lp = c.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.setValueAtTime(880, now);
      lp.frequency.exponentialRampToValueAtTime(160, now + 0.28);

      g.gain.setValueAtTime(0.42, now);
      g.gain.exponentialRampToValueAtTime(0.001, now + 0.30);
      osc.connect(lp);
      lp.connect(g);
      g.connect(c.destination);
      osc.start(now);
      osc.stop(now + 0.31);

      var n = c.createBufferSource();
      n.buffer = createNoiseBuffer(c, 0.24, 1.4);
      var nlp = c.createBiquadFilter();
      nlp.type = 'bandpass';
      nlp.frequency.setValueAtTime(640, now);
      nlp.Q.value = 1.8;
      var ng = c.createGain();
      ng.gain.setValueAtTime(0.36, now);
      ng.gain.exponentialRampToValueAtTime(0.001, now + 0.24);
      n.connect(nlp);
      nlp.connect(ng);
      ng.connect(c.destination);
      n.start(now);
    },
    playRingBell: function(dings) {
      var c = ensure();
      if (!c) return;
      var count = dings || 2;
      var partials = [830, 1244, 1975, 2630];
      for (var d = 0; d < count; d++) {
        var start = c.currentTime + d * 0.20;
        for (var p = 0; p < partials.length; p++) {
          var osc = c.createOscillator();
          var g = c.createGain();
          osc.type = 'sine';
          osc.frequency.setValueAtTime(partials[p], start);
          var amp = 0.20 / (p + 1);
          g.gain.setValueAtTime(amp, start);
          g.gain.exponentialRampToValueAtTime(0.0008, start + 0.72);
          osc.connect(g);
          g.connect(c.destination);
          osc.start(start);
          osc.stop(start + 0.75);
        }
      }
    },
    playKnockoutFanfare: function() {
      var c = ensure();
      if (!c) return;
      this.playRingBell(3);
      var now = c.currentTime;

      // Brass victory chord progression
      var notes = [
        { f: 523.25, t: 0.08, d: 0.14 },
        { f: 659.25, t: 0.20, d: 0.14 },
        { f: 783.99, t: 0.32, d: 0.14 },
        { f: 1046.50, t: 0.45, d: 0.55 }
      ];
      for (var i = 0; i < notes.length; i++) {
        var m = notes[i];
        var osc = c.createOscillator();
        var g = c.createGain();
        var lp = c.createBiquadFilter();
        osc.type = 'sawtooth';
        lp.type = 'lowpass';
        lp.frequency.value = 2500;
        osc.frequency.setValueAtTime(m.f, now + m.t);
        g.gain.setValueAtTime(0.22, now + m.t);
        g.gain.exponentialRampToValueAtTime(0.001, now + m.t + m.d);
        osc.connect(lp);
        lp.connect(g);
        g.connect(c.destination);
        osc.start(now + m.t);
        osc.stop(now + m.t + m.d + 0.02);
      }

      // Stadium crowd roar swell
      var crowd = c.createBufferSource();
      crowd.buffer = createNoiseBuffer(c, 1.8, 0.55);
      var cFilter = c.createBiquadFilter();
      cFilter.type = 'bandpass';
      cFilter.frequency.setValueAtTime(750, now);
      cFilter.Q.value = 0.85;
      var cGain = c.createGain();
      cGain.gain.setValueAtTime(0.01, now);
      cGain.gain.linearRampToValueAtTime(0.22, now + 0.35);
      cGain.gain.exponentialRampToValueAtTime(0.001, now + 1.8);
      crowd.connect(cFilter);
      cFilter.connect(cGain);
      cGain.connect(c.destination);
      crowd.start(now);
    }
  };
})();
