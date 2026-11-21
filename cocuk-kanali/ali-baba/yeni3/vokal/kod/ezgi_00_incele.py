#!/usr/bin/env python3
"""ezgi_00: vokal_dogal uzerinde hizli f0 incelemesi (yalniz okuma, cikti yok)."""
import json, sys, numpy as np, soundfile as sf, pyworld as pw
V = __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
x, sr = sf.read(V + '/vokal_dogal.wav', dtype='float64')
Y = json.load(open(V + '/yerlesim.json', encoding='utf8'))
print('sr', sr, 'n', len(x), 'peak', 20*np.log10(np.abs(x).max()))
which = sys.argv[1:] or ['1.1']
for L in Y['lines']:
    key = '%d.%d' % (L['verse'], L['line'])
    if key not in which: continue
    a = int((L['dest_in'] - 0.05) * sr); b = int((L['dest_out'] + 0.05) * sr)
    seg = x[a:b]
    f0, t = pw.harvest(seg, sr, f0_floor=150, f0_ceil=700, frame_period=5.0)
    f0s = pw.stonemask(seg, f0, t, sr)
    midi = np.where(f0s > 0, 69 + 12*np.log2(np.maximum(f0s, 1)/440), 0)
    t = t + a / sr
    n10 = int(0.010*sr)
    print('=== K%d L%d %s' % (L['verse'], L['line'], L['text']))
    for s in L['syllables']:
        m = (t >= s['dest_start']) & (t < s['dest_end'])
        row = []
        for ti, mi in zip(t[m], midi[m]):
            k = int(ti*sr); e = 20*np.log10(np.sqrt(np.mean(x[max(0,k-n10//2):k+n10//2]**2))+1e-9)
            tag = 'c' if (s['dest_core_start'] <= ti < s['dest_core_end']) else ' '
            row.append('%s%s/%d' % (tag, ('%.1f' % mi) if mi > 0 else '--', round(e)))
        print(' %-5s midi=%.2f [%0.3f-%0.3f] %s' % (s['text'], s['midi'], s['dest_start'], s['dest_end'], ' '.join(row)))
