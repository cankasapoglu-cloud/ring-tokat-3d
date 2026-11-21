#!/usr/bin/env python3
"""Kıta içi ölçü ölçü ses yüksekliği: orkestra tek başına, vokal, hayvan sesi ve bitmiş karışım (7 kıtanın enerji ortalaması).
Reddedilen: 8 ölçülük kıta (0.100 + (4 + 8k + i) * 2.285714).  Referans: 6 ölçülük kıta (8.5713 + k * 13.7139 + i * 2.285714).
Kullanım: python3 01b_olcu_profili.py"""
import numpy as np
from ortak import *
def olcu_lufs(xk, t0, t1): return -0.691 + dbp(np.sum(np.mean(np.square(xk[int(t0 * FS):int(t1 * FS)]), axis=0)))
S = {}
v, b, h, m = esitle(yukle("red_vokal"), yukle("red_altyapi"), yukle("red_hayvan"), yukle("red_karisim")); K = {k: kagirlik(x) for k, x in (("vokal", v), ("orkestra", b), ("hayvan", h), ("karisim", m))}
S["red"] = {"aciklama": "ölçü 0..7; -120 = sessiz", "olculer": []}
for i in range(8):
    satir = {"olcu": i}
    for ad, xk in K.items(): satir[ad + "_lufs"] = R(dbp(np.mean([10 ** (olcu_lufs(xk, ON + (4 + 8 * k + i) * B_RED, ON + (5 + 8 * k + i) * B_RED) / 10) for k in range(7)])), 1)
    S["red"]["olculer"].append(satir)
S["red"]["giris_4_olcu_orkestra_lufs"] = [R(olcu_lufs(K["orkestra"], ON + i * B_RED, ON + (i + 1) * B_RED), 1) for i in range(4)]
S["red"]["bitis_4_olcu_orkestra_lufs"] = [R(olcu_lufs(K["orkestra"], ON + (60 + i) * B_RED, ON + (61 + i) * B_RED), 1) for i in range(4)]
v, b, m = esitle(yukle("ref_vokal"), yukle("ref_altyapi"), yukle("ref_karisim")); K = {k: kagirlik(x) for k, x in (("vokal", v), ("orkestra", b), ("karisim", m))}
S["ref"] = {"aciklama": "ölçü 0..5 (0-3 söylenen, 4-5 çalgısal); parçalar karışıma göre 1.02 dB düşük ölçekli", "olculer": []}
for i in range(6):
    satir = {"olcu": i}
    for ad, xk in K.items(): satir[ad + "_lufs"] = R(dbp(np.mean([10 ** (olcu_lufs(xk, REF_K0 + k * REF_KITA + i * B_RED, REF_K0 + k * REF_KITA + (i + 1) * B_RED) / 10) for k in range(7) if REF_K0 + k * REF_KITA + (i + 1) * B_RED < len(v) / FS])), 1)
    S["ref"]["olculer"].append(satir)
S["ref"]["giris_orkestra_lufs_0_8.57sn"] = R(olcu_lufs(K["orkestra"], 0.3, REF_K0), 1)
yaz("01b_olcu_profili", S)
for e in ("red", "ref"):
    print(e, S[e]["aciklama"])
    for s in S[e]["olculer"]: print("  ", s)
print(S["red"]["giris_4_olcu_orkestra_lufs"], S["red"]["bitis_4_olcu_orkestra_lufs"], S["ref"]["giris_orkestra_lufs_0_8.57sn"])
