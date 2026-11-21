#!/usr/bin/env python3
"""ezgi_00f: PSOLA isaret yumusatma genisligi (PSI_SIGMA_MS) denemesi; hizli olcutler (yalniz okuma)."""
import os, sys, json, numpy as np, pyworld as pw
import ezgi_ortak as o, ezgi_yontem as ym, ezgi_olcum as ol
x, Y = o.oku()
plan = json.load(open(os.path.join(o.ARA, "egri.json"), encoding="utf8"))
pc = {c["id"]: c for c in plan["chunks"]}
for sg in [float(a) for a in sys.argv[1:]]:
    ym.PSI_SIGMA_MS = sg
    dev_all = []; seg_ms = 0; nseg5 = 0; loud_ms = 0; hn = []; lvl = []; envd = []
    for c in o.parcalar(Y):
        sx, t, f0x, _, _, levx = o.parca_cozumle(x, c)
        s = np.load(os.path.join(o.ARA, "egri_%s.npy" % c["id"].replace("+", "_")))
        y, mod = ym.psola(sx, t, f0x, s)
        lvl.append(10 * np.log10(np.mean(y ** 2) / np.mean(sx ** 2)))
        ye, g = ym.duzey_esitle(sx, y, mod)
        ty, f0y, f0r, ncc, levy = o.f0_analiz(ye)
        sk = s[np.clip(np.round(t * o.SR).astype(int), 0, len(s) - 1)]
        ok = (f0x > 0) & (f0y > 0) & (levx > -30)
        dev = np.where(ok, 100 * (o.midi(f0y) - o.midi(f0x) - sk), 0.0)
        dev_all.append(dev[ok])
        bad = np.abs(dev) > 100
        i = 0
        while i < len(t):
            if bad[i]:
                j = i
                while j < len(t) and bad[j]:
                    j += 1
                seg_ms += j - i; nseg5 += int(j - i >= 5)
                if levx[i:j].max() > -20:
                    loud_ms += j - i
                i = j
            else:
                i += 1
        t0 = o.seg_zaman(c)
        fx5 = np.ascontiguousarray(f0x[::5]); fy5 = np.ascontiguousarray(f0y[::5]); t5 = np.ascontiguousarray(t[::5])
        spx = pw.cheaptrick(sx, fx5, t5, o.SR); spy = pw.cheaptrick(ye, fy5, t5, o.SR)
        import librosa
        if ol._MEL_ENV is None:
            ol._MEL_ENV = librosa.filters.mel(sr=o.SR, n_fft=2048, n_mels=40, fmin=100, fmax=8000)
        for h in pc[c["id"]]["syllables"]:
            if abs(h["shift"]) <= o.KOPYA_ESIK:
                continue
            idx = np.where((t5 >= h["core_start"] - t0) & (t5 < h["core_end"] - t0) & (fx5 > 0) & (fy5 > 0))[0]
            if len(idx) < 3:
                continue
            ex_ = 10 * np.log10(ol._MEL_ENV @ spx[idx].T + 1e-20); ey_ = 10 * np.log10(ol._MEL_ENV @ spy[idx].T + 1e-20)
            dd = (ey_ - ey_.mean(axis=0)) - (ex_ - ex_.mean(axis=0))
            envd.append(float(np.mean(np.sqrt(np.mean(dd ** 2, axis=0)))))
            a_, b_ = [], []
            for i in idx:
                k = int(round(t5[i] * o.SR))
                a_.append(ol._hnr(ol._ncc(sx, k, o.SR / fx5[i]))); b_.append(ol._hnr(ol._ncc(ye, k, o.SR / fy5[i])))
            hn.append(np.nanmedian(b_) - np.nanmedian(a_))
    d = np.concatenate(dev_all)
    print("sigma %4.1f ms | egri sapmasi RMS %.1f p95 %.1f cent, >100c %%%.2f, kesim toplam %d ms (>=5 ms: %d adet; > -20 dBFS: %d ms) | zarf %.3f dB | HNR farki %+.2f (|.| %.2f) | duzey (esitleme oncesi) ort %+.2f en dusuk %+.2f dB" % (
        sg, np.sqrt(np.mean(d ** 2)), np.percentile(np.abs(d), 95), 100 * np.mean(np.abs(d) > 100), seg_ms, nseg5, loud_ms, np.mean(envd), np.mean(hn), np.mean(np.abs(hn)), np.mean(lvl), np.min(lvl)), flush=True)
