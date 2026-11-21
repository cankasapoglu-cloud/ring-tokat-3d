#!/usr/bin/env python3
"""Yapay zekâ şarkıcısının ayrılmış vokalini (dinle_2_vokal.wav) geleneksel ezgiye oturtur.
Her hece, yazıya dökümdeki kelime zamanlarından bulunur; notasının süresine uzatılır/kısaltılır ve
perdesi notaya çekilir (WORLD). Çıktı: yeni2/vokal.wav (altyapıyla aynı zaman çizgisi)."""
import json, os, numpy as np, soundfile as sf, pyworld as pw
Y = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); A = os.path.dirname(Y)
z = json.load(open(os.path.join(Y, "zaman.json"), encoding="utf8"))
w = json.load(open(os.path.join(A, "dinle_2_words.json"), encoding="utf8")); w = w["words"] if isinstance(w, dict) else w
w = [q for q in w if q.get("type", "word") == "word"]
x, fs = sf.read(os.path.join(A, "dinle_2_vokal.wav")); x = x.astype(np.float64)
FP = 5.0; UNLU = set("aeıioöuüAEIİOÖUÜ")
kucuk = lambda s: s.replace("İ", "i").replace("I", "ı").lower().strip('".,!?')
bas = [i for i in range(len(w) - 1) if kucuk(w[i]["text"]) == "ali" and kucuk(w[i + 1]["text"]).startswith("baba")]
assert len(bas) == 7, len(bas)
cikti = np.zeros(int(z["dosya_suresi_sn"] * fs) + fs)
for k, kita in enumerate(z["kitalar"]):
    sozler = [kita[a]["soz"] for a in ("satir1", "satir2", "satir3", "satir4")]
    beklenen = [(s, kel) for s, soz in enumerate(sozler, 1) for kel in soz.replace(",", " ").replace("!", " ").replace("?", " ").split()]
    kel = w[bas[k]:bas[k] + len(beklenen)]
    notalar = kita["notalar"]
    # heceleri kelimelere dağıt
    hece = []                                   # (kaynak başlangıç, kaynak bitiş, nota)
    ni = 0
    for (satir, bek), q in zip(beklenen, kel):
        n = sum(c in UNLU for c in bek)
        ns = notalar[ni:ni + n]; ni += n
        assert all(m["satir"] == satir for m in ns), (k, bek, [m["hece"] for m in ns])
        ag = np.array([len(m["hece"].replace("'", "")) + 0.6 for m in ns]); sin = np.concatenate([[0], np.cumsum(ag) / ag.sum()])
        for j, m in enumerate(ns):
            hece.append((q["start"] + sin[j] * (q["end"] - q["start"]), q["start"] + sin[j + 1] * (q["end"] - q["start"]), m))
    assert ni == len(notalar), (k, ni, len(notalar))
    if k == 5:      # 6. kıtada şarkıcı "köpekleri" yerine "ördekleri" demiş: "kö-pek" hecelerini 3. dizedeki "Köpekler"den al
        kaynak = [h for h in hece if h[2]["satir"] == 3][:2]
        for i, h in enumerate(hece):
            if h[2]["satir"] == 2 and kucuk(h[2]["hece"]) in ("kö", "pek"):
                q = kaynak[0] if kucuk(h[2]["hece"]) == "kö" else kaynak[1]
                hece[i] = (q[0], q[1], h[2])
    t0, t1 = kel[0]["start"] - 0.15, kel[-1]["end"] + 0.25
    seg = x[int(t0 * fs):int(t1 * fs)]
    f0, t = pw.harvest(seg, fs, f0_floor=150, f0_ceil=700, frame_period=FP)
    sp = pw.cheaptrick(seg, f0, t, fs); ap = pw.d4c(seg, f0, t, fs); N = len(f0)
    lf = np.where(f0 > 0, np.log2(np.maximum(f0, 1)), np.nan)
    for satir in (1, 2, 3, 4):
        hs = [h for h in hece if h[2]["satir"] == satir]
        cizgi0 = hs[0][2]["baslangic"]
        idx, hf, sus = [], [], []
        for j, (a, b, m) in enumerate(hs):
            s, e = int((a - t0) * 1000 / FP), int((b - t0) * 1000 / FP); L = max(2, e - s)
            sonraki = hs[j + 1][2]["baslangic"] if j + 1 < len(hs) else m["baslangic"] + m["sure"]
            T = int(round((sonraki - cizgi0) * 1000 / FP)) - sum(len(q) for q in idx)      # bu hecenin kaplayacağı kare
            H = min(T, max(3, int(round(m["sure"] * 1000 / FP * (0.9 if j == len(hs) - 1 else 1.0)))))
            on = min(int(L * 0.3), 12, H // 2); son = min(int(L * 0.15), 6, H // 4)
            mm = np.concatenate([np.arange(s, s + on), np.linspace(s + on, e - son - 1, max(1, H - on - son)), np.arange(e - son, e)])[:H]
            orta = np.nanmedian(lf[s:e]) if np.isfinite(lf[s:e]).any() else np.nan
            sap = np.zeros(len(mm))
            if np.isfinite(orta):
                d = lf[np.round(mm).astype(int).clip(0, N - 1)] - orta; sap = np.clip(np.nan_to_num(d), -0.04, 0.04) * 0.5
            hedef = np.log2(440.0 * 2 ** ((m["midi"] - 69) / 12)) + sap
            bos = T - len(mm)
            idx.append(np.concatenate([mm, np.full(bos, mm[-1])])); hf.append(np.concatenate([hedef, np.full(bos, hedef[-1])]))
            sus.append(np.concatenate([np.ones(len(mm)), np.zeros(bos)]))
        idx, hf, sus = np.concatenate(idx), np.concatenate(hf), np.concatenate(sus)
        cek = np.hanning(9); cek /= cek.sum(); hf = 2 ** np.convolve(np.pad(hf, 4, "edge"), cek, "valid")
        lo = np.floor(idx).astype(int).clip(0, N - 1); fr = idx - np.floor(idx); hi = np.minimum(lo + 1, N - 1)
        kaz = np.convolve(np.pad(sus, 3, "edge"), np.ones(7) / 7, "valid")[:, None] ** 2 + 1e-8
        sp2 = (sp[lo] * (1 - fr)[:, None] + sp[hi] * fr[:, None]) * kaz
        ap2 = ap[lo] * (1 - fr)[:, None] + ap[hi] * fr[:, None]
        f02 = np.where((f0[np.round(idx).astype(int).clip(0, N - 1)] > 0) & (sus > 0), hf, 0.0)
        y = pw.synthesize(f02, np.ascontiguousarray(sp2), np.ascontiguousarray(ap2), fs, FP)
        y[:200] *= np.linspace(0, 1, 200); y[-600:] *= np.linspace(1, 0, 600)
        p = int(cizgi0 * fs); cikti[p:p + len(y)] += y
    print(k + 1, kita["hayvan"], " ".join(kucuk(q["text"]) for q in kel))
cikti *= 0.9 / np.abs(cikti).max()
sf.write(os.path.join(Y, "vokal.wav"), cikti, fs)
