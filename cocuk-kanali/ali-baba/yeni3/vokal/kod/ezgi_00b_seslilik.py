#!/usr/bin/env python3
"""ezgi_00b: seslilik (V/UV) olcutlerini ayarlamak icin kare kare dokum (yalniz okuma)."""
import json, sys, os, numpy as np, soundfile as sf, pyworld as pw
from scipy.signal import butter, sosfiltfilt
V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
x, sr = sf.read(V + '/vokal_dogal.wav', dtype='float64')
Y = json.load(open(V + '/yerlesim.json', encoding='utf8'))
which = sys.argv[1:] or ['1.1']
sos = butter(4, 1200, 'low', fs=sr, output='sos')
for L in Y['lines']:
    key = '%d.%d' % (L['verse'], L['line'])
    if key not in which: continue
    a = int((L['dest_in'] - 0.05) * sr); b = int((L['dest_out'] + 0.05) * sr)
    seg = x[a:b]; xl = sosfiltfilt(sos, seg)
    f0, t = pw.harvest(seg, sr, f0_floor=150, f0_ceil=700, frame_period=5.0)
    f0s = pw.stonemask(seg, f0, t, sr)
    f0d, td = pw.dio(seg, sr, f0_floor=150, f0_ceil=700, frame_period=5.0); f0d = pw.stonemask(seg, f0d, td, sr)
    print('=== K%d L%d %s' % (L['verse'], L['line'], L['text']))
    for s in L['syllables']:
        row = []
        for i, ti in enumerate(t):
            tt = ti + a / sr
            if not (s['dest_start'] <= tt < s['dest_end']): continue
            k = int(ti * sr); n10 = int(0.005 * sr)
            e = 20 * np.log10(np.sqrt(np.mean(seg[max(0, k - n10):k + n10] ** 2)) + 1e-9)
            if f0s[i] > 0:
                P = int(round(sr / f0s[i])); best = -1
                for PP in (P - 1, P, P + 1):
                    u = xl[max(0, k - PP):k + PP]; v = xl[max(0, k - PP) + PP:k + PP + PP]
                    m = min(len(u), len(v))
                    if m < 10: continue
                    r = np.dot(u[:m], v[:m]) / (np.sqrt(np.dot(u[:m], u[:m]) * np.dot(v[:m], v[:m])) + 1e-12)
                    best = max(best, r)
                row.append('%.1f/%d/%02d%s' % (69 + 12 * np.log2(f0s[i] / 440), round(e), round(max(best, 0) * 99), 'd' if f0d[i] > 0 else ' '))
            else:
                row.append('--/%d%s' % (round(e), 'd' if f0d[i] > 0 else ' '))
        print(' %-5s %s' % (s['text'], ' '.join(row)))
