"""Tani amacli iz dokumu: python3 iz.py bas bit [adim]  ->  zaman: R5 / E12 / ELOW8 / F2B / EHI / f0(MIDI)"""
import sys, numpy as np
from zarf import *
a, b = float(sys.argv[1]), float(sys.argv[2]); step = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
row = []
for tt in np.arange(a, b, step):
    i = fi(tt); j = int(round(tt / FP)); f = f0h[j]
    row.append("%.2f:%3.0f/%3.0f/%3.0f/%3.0f/%3.0f/%s" % (tt, R5[i], E12[i], ELOW8[i], F2B[i], EHI[i], "%.1f" % midi(f) if f > 0 else " -  "))
for k in range(0, len(row), 5):
    print("  ".join(row[k:k + 5]))
