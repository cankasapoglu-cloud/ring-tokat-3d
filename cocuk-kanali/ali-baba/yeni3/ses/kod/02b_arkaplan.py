# -*- coding: utf-8 -*-
"""Kaynak kayitlarda cagri DISI bolgelerin (arka plan) niteligi + secili aralarin ince zarfi.
Kullanim: 02b_arkaplan.py ad bas son [ad bas son ...]  -> o araligin duzeyi/spektrumu
"""
import sys, os, numpy as np
from scipy import signal
from ortak import *

def bolge(ad, a, b):
    x = oku(os.path.join(ALT, ad + '.mp3'))
    c = x[int(a * SR):int(b * SR)]
    f, P = signal.welch(c, fs=SR, nperseg=2048, noverlap=1536)
    band = (f >= 100) & (f <= 8000)
    Pb = P[band] + 1e-20
    duz = float(np.exp(np.mean(np.log(Pb))) / np.mean(Pb))
    mer = float((f[band] * Pb).sum() / Pb.sum())
    bantlar = [(20, 100), (100, 300), (300, 1000), (1000, 3000), (3000, 8000), (8000, 20000)]
    tot = P.sum()
    oran = ['%d-%d:%4.0f' % (lo, hi, 10 * np.log10(P[(f >= lo) & (f < hi)].sum() / tot + 1e-12)) for lo, hi in bantlar]
    # en guclu 3 spektral tepe
    pk, _ = signal.find_peaks(10 * np.log10(Pb), prominence=10)
    pk = sorted(pk, key=lambda k: -Pb[k])[:4]
    print('%-8s %.2f-%.2f  rms %6.1f dBFS  duzluk(welch) %.3f  merkez %5.0f Hz  bant dB: %s  tepeler: %s' % (
        ad, a, b, rms_db(c), duz, mer, ' '.join(oran), ' '.join('%.0fHz' % f[band][k] for k in pk)))

def ince(ad, a, b, adim=0.010):
    x = oku(os.path.join(ALT, ad + '.mp3'))
    t, d = zarf(x, hop=0.001, win=0.010)
    i0, i1 = int(a / 0.001), int(b / 0.001)
    st = int(adim / 0.001)
    print('  ince zarf %s:' % ad, ' '.join('%.2f:%.0f' % (t[i], d[i:i + st].max()) for i in range(i0, i1, st)))

args = sys.argv[1:]
for i in range(0, len(args), 4):
    mod, ad, a, b = args[i], args[i + 1], float(args[i + 2]), float(args[i + 3])
    if mod == 'b': bolge(ad, a, b)
    else: ince(ad, a, b)
