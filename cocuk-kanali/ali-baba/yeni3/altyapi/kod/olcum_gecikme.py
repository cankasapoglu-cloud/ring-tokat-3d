#!/usr/bin/env python3
# Measurements behind two constants of build.py (nothing here is needed to rebuild the backing):
#   LAT : FluidSynth's file renderer starts every note 82..145 samples after its MIDI time (64-sample blocks + 1 ms timer).
#   ADV : how late each patch reaches 10 % / 50 % of its level (slow attacks get a negative track delay in build.py).
# usage: olcum_gecikme.py <scratch folder>
import sys, os, subprocess, numpy as np, mido, soundfile as sf
T = sys.argv[1]; os.makedirs(T, exist_ok=True)
TPB = 480; bpm = 116.015; beat = 60 / bpm; sr = 44100; SF2 = '/usr/share/sounds/sf2/FluidR3_GM.sf2'
tests = [('kick', 9, 36, 0), ('snare', 9, 38, 0), ('hat', 9, 42, 0), ('crash', 9, 49, 0), ('trumpet', 5, 72, 56), ('flute', 7, 72, 73), ('clarinet', 7, 72, 71),
         ('clarinet G4', 7, 67, 71), ('clarinet A4', 7, 69, 71), ('clarinet G5', 7, 79, 71), ('glock', 4, 84, 9), ('brass', 6, 72, 61), ('bass', 0, 36, 33),
         ('piano', 3, 72, 1), ('banjo', 1, 62, 105), ('accordion', 2, 72, 21)]
for name, ch, note, prog in tests:
    mid = mido.MidiFile(ticks_per_beat=TPB); tr = mido.MidiTrack(); mid.tracks.append(tr)
    msgs = [(0, 0, mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))]
    if ch != 9: msgs.append((0, 1, mido.Message('program_change', channel=ch, program=prog)))
    msgs.append((0, 1, mido.Message('control_change', channel=ch, control=91, value=0)))
    B = [1 + 6 * i + (i % 8) * 0.125 for i in range(12)]
    for b in B:
        msgs.append((round(b * TPB), 3, mido.Message('note_on', channel=ch, note=note, velocity=110)))
        msgs.append((round((b + .5) * TPB), 2, mido.Message('note_off', channel=ch, note=note, velocity=0)))
    msgs.append((round((B[-1] + 6) * TPB), 4, mido.Message('control_change', channel=15, control=7, value=100)))
    msgs.sort(key=lambda m: (m[0], m[1])); t = 0
    for tk, _, m in msgs: tr.append(m.copy(time=tk - t)); t = tk
    mid.save(f'{T}/t.mid')
    subprocess.run(['fluidsynth', '-ni', '-q', '-g', '0.22', '-r', '44100', '-O', 'float', '-R', '0', '-C', '0', '-F', f'{T}/t.wav', SF2, f'{T}/t.mid'], check=True, capture_output=True)
    x, _ = sf.read(f'{T}/t.wav'); m = np.abs(x).max(1); d1 = []; d10 = []; d50 = []
    for b in B:
        i0 = int(round(b * beat * sr)); seg = m[i0 - 400:i0 + int(0.25 * sr)]; pk = seg.max(); pre = m[i0 - 2000:i0 - 400].max()
        f = lambda fr: (np.argmax(seg > max(fr * pk, pre * 2)) - 400)
        d1.append(f(0.001)); d10.append(f(0.1)); d50.append(f(0.5))
    print(f'{name:12s} first sound (0.1 % of peak) after the MIDI time: {min(d1)}..{max(d1)} samples;  10 % of peak: {np.mean(d10) / sr * 1000:5.1f} ms;  50 % of peak: {np.mean(d50) / sr * 1000:5.1f} ms')
