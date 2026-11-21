# -*- coding: utf-8 -*-
"""Bir varyasyonun ayrintili zarfi (50 ms adim) + stereo iliskisi. Kullanim: 02_ayrinti.py ad [ad...]"""
import sys, os, subprocess, numpy as np
from ortak import *

for ad in sys.argv[1:]:
    yol = os.path.join(ALT, ad + '.mp3')
    x = oku(yol)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', yol, '-ar', str(SR), '-f', 'f32le', '-'], check=True, capture_output=True).stdout
    st = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    L, R = st[:, 0], st[:, 1]
    kor = float(np.corrcoef(L, R)[0, 1])
    yan = rms_db((L - R) / 2) - rms_db((L + R) / 2)
    t, db = zarf(x)
    print('== %s  sure %.3f  tepe %.1f dBFS  L/R korelasyon %.3f  yan/orta %.1f dB' % (ad, len(x) / SR, tepe_db(x), kor, yan))
    adim = 10  # 50 ms
    sat = []
    for i in range(0, len(t), adim):
        sat.append('%.2f:%4.0f' % (t[i], db[i:i + adim].max()))
    for i in range(0, len(sat), 10):
        print('  ' + '  '.join(sat[i:i + 10]))
