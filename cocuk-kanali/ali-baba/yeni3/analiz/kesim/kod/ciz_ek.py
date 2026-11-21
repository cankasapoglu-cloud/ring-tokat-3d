#!/usr/bin/env python3
"""6. kita onariminin ek yerlerini yakindan cizer (dalga bicimi + 5 ms RMS) -> cizim/K6_ek_yerleri.png
Yalnizca gozle kontrol icindir; ses dinlenmedi."""
import os, json, numpy as np, soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.dirname(os.path.dirname(os.path.dirname(K)))
d = json.load(open(os.path.join(K, "kesim.json"), encoding="utf8"))
x, fs = sf.read(os.path.join(A, "dinle_2_vokal.wav"))
R = d["verse6_repair"]; on = R["front_cut"]["t"]
os.makedirs(os.path.join(K, "cizim"), exist_ok=True)
fig, ax = plt.subplots(3, 1, figsize=(18, 10))
satirlar = (("ördekleri (L2): 'dek' | k kapanisi | 'leri'", R["splice_in_ordekleri"], 77.05, 77.42),
            ("Köpekler (L3): 'pek' | k kapanisi | 'ler'", R["splice_in_kopekler"], 78.33, 78.70),
            ("on kesim: 'de' | 'ör' (sessizlik yok)", {"splice_t": on, "closure_start": on, "closure_end": on}, on - 0.19, on + 0.18))
c = np.concatenate([[0], np.cumsum(x ** 2)]); w = int(0.005 * fs)
for a_, (ad, q, t0, t1) in zip(ax, satirlar):
    i0, i1 = int(t0 * fs), int(t1 * fs); t = np.arange(i0, i1) / fs
    a_.plot(t, x[i0:i1], lw=0.5, color="k"); a_.axvline(q["splice_t"], color="r", lw=2, label="ek ani %.4f" % q["splice_t"])
    a_.axvspan(q["closure_start"], q["closure_end"], color="orange", alpha=0.3, label="kapanis")
    b_ = a_.twinx(); idx = np.arange(i0, i1, 44)
    b_.plot(idx / fs, 10 * np.log10((c[idx + w // 2] - c[idx - w // 2]) / w + 1e-12), color="b", lw=1)
    b_.set_ylim(-100, 0); b_.set_ylabel("5 ms RMS dBFS")
    a_.set_title(ad); a_.legend(loc="upper right"); a_.set_xlim(t0, t1)
plt.tight_layout(); plt.savefig(os.path.join(K, "cizim", "K6_ek_yerleri.png"), dpi=70)
print("cizim/K6_ek_yerleri.png")
