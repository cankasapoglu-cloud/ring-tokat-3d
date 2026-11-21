# -*- coding: utf-8 -*-
"""Tum varyasyonlarin zarf analizi: cagri sinirlari tablosu.
Her dosya icin: tepe, gurultu tabani, -20 dB (tepeye gore) bolutleri ve bunlarin
-35 / -45 dB'ye kadar genisletilmis (dogal bas/son) sinirlari."""
import os, glob, json, numpy as np
from ortak import *

sonuc = {}
print('%-10s %5s %6s %6s | %s' % ('dosya', 'sure', 'tepe', 'taban', 'bolutler: [-20dB bas-son] -> dogal [-45dB bas-son] sure / kuyruk'))
for yol in sorted(glob.glob(os.path.join(ALT, '*.mp3'))):
    ad = os.path.basename(yol)[:-4]
    x = oku(yol)
    t, db = zarf(x)
    tepe = db.max()
    taban = np.percentile(db, 5)
    segs = bolutler(t, db, tepe - 20, min_bosluk=0.06, min_sure=0.03)
    satir = []
    kayit = []
    for k, (s, e) in enumerate(segs):
        sol = segs[k - 1][1] if k > 0 else 0.0
        sag = segs[k + 1][0] if k + 1 < len(segs) else len(x) / SR
        s35, e35 = genislet(t, db, s, e, tepe - 35, (sol, sag))
        s45, e45 = genislet(t, db, s, e, tepe - 45, (sol, sag))
        segtepe = db[(t >= s) & (t < e)].max()
        kayit.append(dict(s20=round(s, 3), e20=round(e, 3), s35=round(s35, 3), e35=round(e35, 3),
                          s45=round(s45, 3), e45=round(e45, 3), tepe_db=round(float(segtepe), 1)))
        satir.append('[%.2f-%.2f]->[%.2f-%.2f] %.2fs/k%.2f (%.0fdB)' % (s, e, s45, e45, e45 - s45, e45 - e, segtepe))
    sonuc[ad] = dict(sure=round(len(x) / SR, 3), tepe_db=round(float(tepe), 1), taban_db=round(float(taban), 1), bolutler=kayit)
    print('%-10s %5.2f %6.1f %6.1f | %s' % (ad, len(x) / SR, tepe, taban, '  '.join(satir)))
os.makedirs(os.path.join(OUT, 'ara'), exist_ok=True)
json.dump(sonuc, open(os.path.join(OUT, 'ara', 'tarama.json'), 'w'), indent=1)
