#!/usr/bin/env python3
"""Kesif (yalniz okur): kesim noktalarinin cevresindeki duzey profilleri.
Cikti: ekrana tablo. Hicbir dosya yazmaz."""
import json, os, numpy as np, soundfile as sf

A = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
x, sr = sf.read(os.path.join(A, "dinle_2_vokal.wav"), dtype="float64")
K = json.load(open(os.path.join(A, "yeni3/analiz/kesim/kesim.json"), encoding="utf8"))
T = json.load(open(os.path.join(A, "yeni3/analiz/tempo/tempo.json"), encoding="utf8"))


def db(v):
    return 20 * np.log10(max(float(v), 1e-10))


def rms(t0, t1):
    a, b = int(round(t0 * sr)), int(round(t1 * sr))
    return db(np.sqrt(np.mean(x[a:b] ** 2))) if b > a else -200.0


def profil(tc, yari=0.040, adim=0.002):
    """tc cevresinde 2 ms'lik RMS (dBFS) dizisi."""
    out = []
    t = tc - yari
    while t < tc + yari - 1e-9:
        out.append("%4.0f" % rms(t, t + adim))
        t += adim
    return " ".join(out)


if __name__ == "__main__":
    print("2 ms RMS profili, kesim noktasinin -40..+40 ms cevresi (dBFS); '|' = kesim ani")
    for v in K["verses"]:
        for c in v["chunks"]:
            for ad, t in (("giris", c["cut_in"]), ("cikis", c["cut_out"])):
                p = profil(t).split()
                print("K%d %-5s %-5s t=%.4f  %s | %s" % (v["verse"], str(c["lines"]), ad, t, " ".join(p[:20]), " ".join(p[20:])))
