#!/usr/bin/env python3
"""Soru 4 ek: tiz bantta (2-16 kHz) ritmin alt bölünmesi. Dört BİTMİŞ karışımda aynı ölçüm (vokal dahil tam karışım, 20.-80. saniye):
vuruşlar librosa ile bulunur (tempo 80-160 aralığına katlanır); her vuruş 4 onaltılığa bölünür; her yuvanın çevresindeki (+-25 ms) tiz bant yükselişi toplanır.
onaltilik/sekizlik = (yuva 1 + yuva 3) / (yuva 0 + yuva 2);  vurus_arasi/vurus = yuva 2 / yuva 0  (vuruş fazı yarım vuruş kayarsa bu ikinci oran tersine döner; ilki dönmez)."""
import json, os, sys, numpy as np, librosa
from scipy import signal
from ortak import *
DOSYA = {"RED_reddedilen": RED_MP3, "REF_v2_2": REF_MP3, "ONAY_el_yikama_coskulu_2": os.path.join(KOK, "el-yikama", "coskulu_2.mp3"), "ONAY_parmak_ailesi_coskulu_1": os.path.join(KOK, "parmak-ailesi", "coskulu_1.mp3")}
BILINEN = {"RED_reddedilen": (VURUS, ON + 0.005), "REF_v2_2": (REF_VURUS, REF_FAZ)}
sonuc = {"tanim": __doc__}
for ad, yol in DOSYA.items():
    y, sr = librosa.load(yol, sr=22050, mono=True, offset=20.0, duration=60.0)
    yh = signal.sosfiltfilt(signal.butter(4, 2000, "highpass", fs=sr, output="sos"), y)
    hop = 64; oe = librosa.onset.onset_strength(y=yh, sr=sr, hop_length=hop, aggregate=np.median); fe = sr / hop
    if ad in BILINEN:
        v, faz = BILINEN[ad]; k0 = int(np.ceil((20.0 - faz) / v)); beats = faz + (k0 + np.arange(int(58 / v))) * v - 20.0; tempo = 60 / v; kaynak = "bilinen ızgara"
    else:
        tempo, bf = librosa.beat.beat_track(onset_envelope=oe, sr=sr, hop_length=hop, start_bpm=110, tightness=200); tempo = float(np.atleast_1d(tempo)[0]); beats = librosa.frames_to_time(bf, sr=sr, hop_length=hop); kaynak = "librosa"
        while tempo < 80: tempo *= 2; beats = np.sort(np.concatenate([beats[:-1], (beats[:-1] + beats[1:]) / 2]))
        while tempo > 160: tempo /= 2; beats = beats[::2]
    g = np.zeros(4); n = 0
    for a, b in zip(beats[:-1], beats[1:]):
        if not 0.3 < b - a < 0.8: continue
        for s in range(4):
            t = a + s * (b - a) / 4; i, j = int((t - 0.025) * fe), int((t + 0.025) * fe)
            if i >= 0 and j < len(oe): g[s] += oe[i:j].sum()
        n += 1
    g /= max(n, 1)
    sonuc[ad] = {"tempo_bpm": round(tempo, 1), "vurus_kaynagi": kaynak, "vurus_sayisi": n, "yuva_gucu_0_1_2_3": [round(float(x), 2) for x in g],
                 "onaltilik_bolu_sekizlik": round(float((g[1] + g[3]) / (g[0] + g[2])), 2), "vurus_arasi_bolu_vurus": round(float(g[2] / g[0]), 2)}
    print(ad, sonuc[ad])
json.dump(sonuc, open(os.path.join(ARA, "09_alt_bolunme.json"), "w"), ensure_ascii=False, indent=1)
