#!/usr/bin/env python3
# Extra checks for a listener on a phone: (a) mono fold-down loss of the delivered files and of each stem,
# (b) what is left of the slot bars above 300 Hz (a phone speaker reproduces little below that), (c) sample jumps / dropouts.
# usage: 06_telefon_mono_tik.py <delivered folder> <work 104.96> <out json>
import sys, json
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
DEL, WORK, OUTJ = sys.argv[1:4]; P = lambda *a: print(*a, flush=True); R = {}
db = lambda v: 20 * np.log10(np.maximum(v, 1e-12)); rms = lambda x: float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0
sr = 44100; BPM = 104.96; BEAT = 60 / BPM; BAR = 4 * BEAT
def mono_loss(x): return float(db(rms(x.mean(1))) - db(np.sqrt((rms(x[:, 0]) ** 2 + rms(x[:, 1]) ** 2) / 2)))
for key in ('G', 'C'):
    r = R[key] = {}
    for n in ('altyapi', 'ezgi_alti'):
        x, _ = sf.read(f'{DEL}/{n}_{key}.wav'); r[f'mono_loss_{n}_db'] = mono_loss(x)
        if n == 'altyapi':
            hp = sosfiltfilt(butter(4, 300, 'high', fs=sr, output='sos'), x.mean(1)); full = x.mean(1); rows = []
            for v in range(7):
                v0 = (4 + 8 * v) * BAR; seg = lambda b0, b1, s=hp: db(rms(s[int((v0 + b0 * BAR) * sr):int((v0 + b1 * BAR) * sr)]))
                rows.append([seg(0, 1), seg(1, 2), seg(2, 3), seg(3, 4), seg(4, 5), seg(5, 5.5), seg(5.5, 6), seg(6, 7), seg(7, 8)])
            m = np.mean(rows, 0); r['above_300Hz_mono_db'] = dict(bar0=float(m[0]), bar1=float(m[1]), bar2=float(m[2]), slot3=float(m[3]), slot4=float(m[4]), bar5_fill=float(m[5]), bar5_band=float(m[6]), bar6=float(m[7]), bar7=float(m[8]))
            P(f'[{key}] altyapi, mono, ABOVE 300 Hz only (phone-speaker view), mean dBFS RMS per verse bar: 0: {m[0]:.1f}  1: {m[1]:.1f}  2: {m[2]:.1f}  slot 3: {m[3]:.1f}  slot 4: {m[4]:.1f}  5 fill half: {m[5]:.1f}  5 band half: {m[6]:.1f}  6: {m[7]:.1f}  7: {m[8]:.1f}'
              f'  -> slot bars are {min(m[0], m[2], m[7]) - max(m[3], m[4]):.1f} dB below the quietest vocal bar in this band (full band: about 11-12 dB)')
            # the slot bar without its first 300 ms (ring-over of bar 2)
            s3 = np.mean([db(rms(hp[int(((4 + 8 * v + 3) * BAR + .3) * sr):int((4 + 8 * v + 4) * BAR * sr)])) for v in range(7)])
            r['slot3_after_300ms_above_300Hz_db'] = float(s3); P(f'[{key}]   slot bar 3 after its first 300 ms, above 300 Hz: {s3:.1f} dBFS')
            d = np.abs(np.diff(x, axis=0)).max(1); i = int(np.argmax(d)); r['max_sample_jump'] = dict(value_fs=float(d[i]), at_s=i / sr, p9999=float(np.percentile(d, 99.99)))
            z = (np.abs(x).max(1) == 0); runs = np.flatnonzero(np.diff(np.concatenate([[0], z.view(np.int8), [0]]))); L = (runs[1::2] - runs[::2]) if len(runs) else np.array([0])
            r['longest_digital_silence_ms'] = float(1000 * L.max() / sr) if len(L) else 0.0; r['longest_digital_silence_at_s'] = float(runs[::2][int(np.argmax(L))] / sr) if len(L) and L.max() > 0 else None
            P(f'[{key}] altyapi: largest sample-to-sample jump {d[i]:.3f} FS at {i / sr:.3f} s (99.99th pct {np.percentile(d, 99.99):.3f}); longest run of exact digital zero {r["longest_digital_silence_ms"]:.1f} ms at {r["longest_digital_silence_at_s"]} s')
        P(f'[{key}] {n}: mono fold-down (L+R)/2 vs stereo: {r[f"mono_loss_{n}_db"]:+.2f} dB')
    meta = json.load(open(f'{WORK}/{key}/meta.json')); CUT = meta['CUT']; out = {}
    for st in ('davul', 'bas', 'banjo', 'akordeon', 'piyano', 'glockenspiel', 'trompet', 'brass', 'klarnet', 'glockenspiel_hafif'):
        x, _ = sf.read(f'{WORK}/{key}/st_{st}.wav', start=CUT, stop=CUT + int(60 * sr)); out[st] = round(mono_loss(x), 2)
    r['mono_loss_per_stem_db'] = out; P(f'[{key}] mono fold-down loss per instrument stem (first 60 s), dB: {out}')
json.dump(R, open(OUTJ, 'w'), indent=1, ensure_ascii=False)
