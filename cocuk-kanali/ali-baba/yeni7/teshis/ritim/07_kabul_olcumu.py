#!/usr/bin/env python3
"""KABUL ÖLÇÜMÜ (bir sonraki karışım için; şemadan bağımsız, yalnız ses):
Vokal kökü ile orkestranın vokalin altında çaldığı ezgi kökü (ezgi_alti / rehber ezgi; tek sesli) AYNI ANDA AYNI NOTADA mı?
Kullanım: python3 07_kabul_olcumu.py <vokal.wav> <ezgi.wav> [ezginin başına eklenecek sessizlik sn = 0.100]
Çıktı: kayma 0'da perde sınıfı uyumu, en iyi uyumu veren kayma (ms; + = vokal geride), büyük ikili (2 yarım ses) çatışma payı.
GEÇER: |en iyi kayma| <= 25 ms  VE  kayma 0'da uyum >= 0.85  VE  büyük ikili çatışma payı <= %5."""
import sys, json, numpy as np, parselmouth
from ortak import *

def olc(vok_yolu, ezgi_yolu, on=ON):
    vok = oku_mono(vok_yolu); ezg = np.concatenate([np.zeros(int(on * FS)), oku_mono(ezgi_yolu)])
    def f0(x, lo, hi):
        p = parselmouth.Sound(x, sampling_frequency=FS).to_pitch_ac(time_step=0.005, pitch_floor=lo, pitch_ceiling=hi); return p.xs(), p.selected_array["frequency"]
    tv, fv = f0(vok, 150, 720); te, fe = f0(bant(ezg, 400, 1100), 450, 950)       # klarnet G5-D5 alanı; ezgi başka oktavdaysa sınırlar değiştirilmeli
    tt = np.arange(0.2, min(len(vok), len(ezg)) / FS - 0.2, 0.005)
    def orn(t, f):
        i = np.clip(np.searchsorted(t, tt), 1, len(t) - 1); i = np.where(np.abs(t[i - 1] - tt) < np.abs(t[i] - tt), i - 1, i); return f[i]
    V, E = orn(tv, fv), orn(te, fe)
    mv = np.where(V > 0, 69 + 12 * np.log2(np.maximum(V, 1) / 440), np.nan); me = np.where(E > 0, 69 + 12 * np.log2(np.maximum(E, 1) / 440), np.nan)
    def uyum(kms):
        k = int(round(kms / 5)); a = mv[max(0, k):len(mv) + min(0, k)]; b = me[max(0, -k):len(me) + min(0, -k)]; m = ~np.isnan(a) & ~np.isnan(b)
        d = np.abs(((a[m] - b[m]) + 6) % 12 - 6); return float((d < 0.6).mean()), float(((d > 1.4) & (d < 2.6)).mean()), int(m.sum())
    e = {k: uyum(k) for k in range(-600, 601, 5)}; en = max(e, key=lambda k: e[k][0])
    s = {"vokal": vok_yolu, "ezgi": ezgi_yolu, "ortak_sesli_sure_sn": round(e[0][2] * 0.005, 1), "uyum_kayma_0": round(e[0][0], 3), "buyuk_ikili_catisma_payi_kayma_0": round(e[0][1], 3),
         "en_iyi_kayma_ms": en, "en_iyi_kaymada_uyum": round(e[en][0], 3), "egri_her_50ms": {str(k): round(e[k][0], 3) for k in range(-400, 401, 50)}}
    s["GECER"] = bool(abs(en) <= 25 and e[0][0] >= 0.85 and e[0][1] <= 0.05)
    return s

if __name__ == "__main__":
    r = olc(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else ON); print(json.dumps(r, ensure_ascii=False, indent=1))
