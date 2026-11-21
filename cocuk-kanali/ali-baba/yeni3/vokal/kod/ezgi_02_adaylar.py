#!/usr/bin/env python3
"""ezgi_02: uc adayi uretir (tam uzunlukta, vokal_dogal ile ayni zaman cizgisi, PCM_16).

  A dunya_tam   : parca basina tam WORLD yeniden sentezi (yalniz f0 degisir)
  B dunya_karma : ozgun ornekler + yalniz sesli-ve-kaydirilan adalarda WORLD
  C psola       : TD-PSOLA (otumsuz ve sifir-kaydirmali bolgeler birebir ozgun)
Her adayda degistirilen bolgelerde kisa sureli duzey ozgune esitlenir (+-3 dB sinirli)."""
import os, json, time, numpy as np, soundfile as sf
import ezgi_ortak as o, ezgi_yontem as ym

x, Y = o.oku()
N = len(x)
out = {k: np.zeros(N) for k in ("A_dunya_tam", "B_dunya_karma", "C_psola")}
modm = {k: np.zeros(N, dtype=bool) for k in out}
kaz = {k: np.ones(N) for k in out}
bilgi = {k: [] for k in out}
t00 = time.time()
for c in o.parcalar(Y):
    seg, t, f0, f0r, ncc, lev = o.parca_cozumle(x, c)
    s = np.load(os.path.join(o.ARA, "egri_%s.npy" % c["id"].replace("+", "_")))
    n = len(seg); P = o.PAD
    tw, f0w, sp, ap = ym.world_coz(seg, t, f0)
    yw = ym.world_sentez(seg, tw, f0w, sp, ap, s)
    km = ym.kenar_maskesi(n)
    res = {}
    # A
    yA = yw * km
    modA = np.zeros(n, dtype=bool); modA[P:n - P] = True
    res["A_dunya_tam"] = (yA, modA, dict(level_db_before_eq=float(10 * np.log10(np.mean(yA ** 2) / np.mean(seg ** 2)))))
    # B
    b = {}
    yB, modB = ym.world_karma(seg, t, f0, s, yw, bilgi=b)
    b["level_db_before_eq"] = float(10 * np.log10(np.mean(yB ** 2) / np.mean(seg ** 2)))
    res["B_dunya_karma"] = (yB, modB, b)
    # C
    b = {}
    yC, modC = ym.psola(seg, t, f0, s, bilgi=b)
    b["level_db_before_eq"] = float(10 * np.log10(np.mean(yC ** 2) / np.mean(seg ** 2)))
    res["C_psola"] = (yC, modC, b)
    for k, (y, mod, b) in res.items():
        ye, g = ym.duzey_esitle(seg, y, mod)
        assert np.all(ye[:P] == 0) and np.all(ye[n - P:] == 0), (k, c["id"])
        out[k][c["a"]:c["b"]] = ye[P:n - P]
        modm[k][c["a"]:c["b"]] = mod[P:n - P]
        kaz[k][c["a"]:c["b"]] = g[P:n - P]
        b["id"] = c["id"]; b["eq_gain_db_min_max"] = [float(20 * np.log10(g.min())), float(20 * np.log10(g.max()))]
        b["level_db_after_eq"] = float(10 * np.log10(np.mean(ye ** 2) / np.mean(seg ** 2)))
        bilgi[k].append(b)
    print("%-8s %.1f s | duzey (esitleme oncesi) A %+.2f B %+.2f C %+.2f dB | B ada %d (surekli ek %d, cift %d) | C kosu %d kilit %d/%d" % (
        c["id"], time.time() - t00, res["A_dunya_tam"][2]["level_db_before_eq"], res["B_dunya_karma"][2]["level_db_before_eq"],
        res["C_psola"][2]["level_db_before_eq"], res["B_dunya_karma"][2]["islands"], res["B_dunya_karma"][2]["coherent_joins"],
        res["B_dunya_karma"][2]["double_coherent"], res["C_psola"][2]["runs_processed"], res["C_psola"][2]["locks"],
        res["C_psola"][2]["locks"] + res["C_psola"][2]["lock_failed"]), flush=True)

akt = np.zeros(N, dtype=bool)
for c in o.parcalar(Y):
    akt[c["a"]:c["b"]] = True
ozet = {}
for k in out:
    y = out[k]
    pk = float(np.abs(y).max())
    g = 1.0
    if pk > 10 ** (-1.0 / 20):                    # guvenlik: tepe -1 dBFS'yi asarsa tek genel kazanc
        g = 10 ** (-1.0 / 20) / pk
        y = y * g
    assert np.abs(y).max() < 1.0
    yol = os.path.join(o.ARA, "aday_%s.wav" % k)
    sf.write(yol, y, o.SR, subtype="PCM_16")          # libsndfile: x32768, yuvarlama; kopya ornekler birebir kalir
    q, _ = sf.read(yol, dtype="float64")
    np.save(os.path.join(o.ARA, "mod_%s.npy" % k), modm[k])
    np.save(os.path.join(o.ARA, "kazanc_%s.npy" % k), kaz[k].astype(np.float32))
    ozet[k] = dict(peak_dbfs=round(20 * np.log10(pk), 3), safety_gain_db=round(20 * np.log10(g), 3),
                   rms_db_re_dogal=round(float(10 * np.log10(np.mean(y[akt] ** 2) / np.mean(x[akt] ** 2))), 3),
                   modified_ratio_of_sung_samples=round(float(np.mean(modm[k][akt])), 4),
                   exact_copy_samples_ratio=round(float(np.mean(q[akt] == x[akt])), 4),
                   unmodified_samples_all_exact=bool(np.all(q[akt & ~modm[k]] == x[akt & ~modm[k]])), silence_outside_chunks_exact=bool(np.all(q[~akt] == 0)), chunks=bilgi[k])
    print(k, {kk: vv for kk, vv in ozet[k].items() if kk != "chunks"})
with open(os.path.join(o.ARA, "adaylar.json"), "w", encoding="utf8") as f:
    json.dump(ozet, f, ensure_ascii=False, indent=1, default=float)
