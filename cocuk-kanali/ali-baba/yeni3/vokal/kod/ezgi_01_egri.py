#!/usr/bin/env python3
"""ezgi_01: her parca icin kaydirma egrisi s(t) (yarim ses) tasarimi.

- Hece basina kaydirma = hedef - o hecenin KENDI olculen ortanca perdesi (unlu cekirdegi, yalniz
  guvenilir sesli kareler). L3: tekduze +3, L4: tekduze +7. |kaydirma| <= 0.30 ise 0 (ozgun
  ornekler kopyalanir).
- Farkli kaydirilan komsu heceler arasindaki gecis: 40-70 ms yukseltilmis kosinus (adim buyudukce
  uzar); iki unlunun korunan orta bolgeleri arasinda (unsuz / dusuk enerji). Yeri, sonuc perdesinin
  genlik agirlikli toplam degisimini (TV) + gecis icindeki ortalama genligi en aza indirecek sekilde
  secilir: dogal kayma ile kaydirma gecisi ust uste gelir, gecis sessiz yere duser.
- s(t) = s_0 + toplam d_k * R((t - a_k) / D_k)
Cikti: ezgi_ara/egri.json + ezgi_ara/egri_<parca>.npy (ornek basina s(t), PAD dahil)."""
import os, json, numpy as np
from scipy.signal import medfilt
import ezgi_ortak as o

x, Y = o.oku()
plan = dict(description="Per-chunk pitch-shift curves for the 'ezgi' vocal (semitones); times are seconds on the vokal_dogal timeline",
            copy_threshold_semitones=o.KOPYA_ESIK, chunks=[])
LAM = 1.0
olcum_farklari = []
for c in o.parcalar(Y):
    seg, t, f0, f0r, ncc, lev = o.parca_cozumle(x, c)
    t0 = o.seg_zaman(c)
    tt = t + t0                                        # dosya zamani (kareler)
    m = o.midi(f0)
    hec = []
    for L in c["lines"]:
        for s, (tg, uni) in zip(L["syllables"], o.hedef_listesi(L)):
            cs, ce = s["dest_core_start"], s["dest_core_end"]
            sel = (tt >= cs) & (tt < ce) & (f0 > 0)
            olcu = "core"
            if sel.sum() < 5:
                sel = (tt >= s["dest_start"]) & (tt < s["dest_end"]) & (f0 > 0); olcu = "all voiced frames of the syllable"
            med = float(np.nanmedian(m[sel])) if sel.any() else float("nan")
            olcum_farklari.append(med - s["midi"])
            if uni is not None:
                sh, hedef = float(uni), med + uni
            else:
                sh, hedef = tg - med, float(tg)
            kopya = abs(sh) <= o.KOPYA_ESIK
            hec.append(dict(verse=L["verse"], line=L["line"], index=s["index"], text=s["text"], start=s["dest_start"], end=s["dest_end"],
                            core_start=cs, core_end=ce, vowel_onset=s["dest_vowel_onset"], measured_midi=round(med, 3), measured_over=olcu,
                            voiced_frames_measured=int(sel.sum()), yerlesim_midi=s["midi"], target_midi=round(hedef, 3),
                            raw_shift=round(sh, 3), shift=0.0 if kopya else round(sh, 3), copied=bool(kopya), uniform=uni is not None))
    amp = 10 ** (lev / 20.0)
    ref = np.median(amp[f0 > 0]) if (f0 > 0).any() else 1.0
    w = np.clip(amp / ref, 0, 2.0)                    # dizenin sesli ortanca genligine gore
    v = np.isfinite(m)
    msm = m.copy()
    if v.any():                                       # 5 ms ortanca (yalniz tam sesli komsuluklarda)
        mf = medfilt(np.where(v, m, 0.0), 5)
        ok5 = medfilt(v.astype(float), 5) == 1.0
        msm = np.where(v & ok5, mf, m)
    gec = []
    n = len(seg)
    ts = np.arange(n) / o.SR + t0
    s_curve = np.full(n, hec[0]["shift"], dtype=float)
    for k in range(len(hec) - 1):
        h0, h1 = hec[k], hec[k + 1]
        d = h1["shift"] - h0["shift"]
        if abs(d) < 1e-9:
            continue
        m0 = min(0.040, 0.25 * (h0["core_end"] - h0["core_start"]))
        m1 = min(0.040, 0.25 * (h1["core_end"] - h1["core_start"]))
        lo = max(h0["core_end"] - m0, h0["end"] - 0.080)
        hi = min(h1["core_start"] + m1, max(h1["vowel_onset"], h1["start"]) + 0.060)
        lo = min(lo, h0["end"]); hi = max(hi, h1["start"])
        dar = (hi - lo) < 0.040
        Dp = float(np.clip(0.040 + 0.0075 * (abs(d) - 1.0), 0.040, 0.070))
        cands = []
        if dar:
            cands.append((0.5 * (lo + hi) - 0.020, 0.040))
        else:
            D = min(Dp, np.floor((hi - lo) * 1000.0) / 1000.0)
            a = lo
            while a + D <= hi + 1e-9:
                cands.append((a, D)); a += 0.001
        iev = np.where((tt >= lo - 0.030) & (tt <= hi + 0.030))[0]
        best = None
        for (a, D) in cands:
            sh = h0["shift"] + d * o.yukselen_kos((tt[iev] - a) / D)
            res = msm[iev] + sh
            ok = np.isfinite(res[:-1]) & np.isfinite(res[1:])
            ww = np.minimum(w[iev][:-1], w[iev][1:])
            tv = float(np.sum(np.abs(np.diff(res))[ok] * ww[ok])) if ok.any() else 0.0
            insp = (tt >= a) & (tt <= a + D)
            e = float(np.mean(w[insp])) if insp.any() else 0.0
            cost = tv + LAM * e
            if best is None or cost < best[0] - 1e-12:
                best = (cost, a, D, tv, e)
        cost, a, D, tv, e = best
        s_curve += d * o.yukselen_kos((ts - a) / D)
        insp = (tt >= a) & (tt <= a + D)
        vr = float(np.mean(f0[insp] > 0)) if insp.any() else 0.0
        gec.append(dict(between="%s|%s" % (h0["text"], h1["text"]), verse=h0["verse"], line=h0["line"], line_next=h1["line"],
                        from_shift=h0["shift"], to_shift=h1["shift"], start=round(a, 4), end=round(a + D, 4), ms=round(D * 1000, 1),
                        window=[round(lo, 4), round(hi, 4)], window_ms=round((hi - lo) * 1000, 1), narrow_window=bool(dar),
                        weighted_tv=round(tv, 3), mean_rel_amplitude=round(e, 3), voiced_ratio_in_span=round(vr, 2),
                        boundary=round(h0["end"], 4)))
    for g0, g1 in zip(gec[:-1], gec[1:]):
        if g1["start"] < g0["end"] - 1e-6:
            g1["overlaps_previous"] = True
    for h in hec:                                     # denetim: korunan cekirdek ortasinda s(t) sabit mi
        mk = min(0.040, 0.25 * (h["core_end"] - h["core_start"]))
        sel = (ts >= h["core_start"] + mk) & (ts <= h["core_end"] - mk)
        if sel.any():
            h["shift_in_protected_core_min_max"] = [round(float(s_curve[sel].min()), 4), round(float(s_curve[sel].max()), 4)]
    np.save(os.path.join(o.ARA, "egri_%s.npy" % c["id"].replace("+", "_")), s_curve)
    plan["chunks"].append(dict(id=c["id"], verse=c["verse"], a=c["a"], b=c["b"], syllables=hec, transitions=gec))

olcum_farklari = np.array(olcum_farklari)
plan["measured_vs_yerlesim_midi"] = dict(median_abs_diff=round(float(np.nanmedian(np.abs(olcum_farklari))), 3),
                                         max_abs_diff=round(float(np.nanmax(np.abs(olcum_farklari))), 3))
with open(os.path.join(o.ARA, "egri.json"), "w", encoding="utf8") as f:
    json.dump(plan, f, ensure_ascii=False, indent=1)

nk = sum(h["copied"] for c in plan["chunks"] for h in c["syllables"])
nh = sum(len(c["syllables"]) for c in plan["chunks"])
print("hece", nh, "kopya", nk, "| olcum farki (benim - yerlesim): ortanca |d| %.3f, en buyuk %.3f" % (
    plan["measured_vs_yerlesim_midi"]["median_abs_diff"], plan["measured_vs_yerlesim_midi"]["max_abs_diff"]))
allg = [g for c in plan["chunks"] for g in c["transitions"]]
print("gecis", len(allg), "dar pencere", sum(g["narrow_window"] for g in allg))
for c in plan["chunks"]:
    if c["verse"] in (1,):
        print("==", c["id"])
        print("  " + " ".join("%s:%+.2f%s" % (h["text"], h["shift"], "*" if h["copied"] else "") for h in c["syllables"]))
        for g in c["transitions"]:
            if abs(g["to_shift"] - g["from_shift"]) >= 0.3:
                print("   %-9s %+.2f->%+.2f  [%.3f-%.3f] %2.0f ms  pencere %3.0f ms%s  tv %.2f  genlik %.2f  sesli %.2f  sinir %.3f" % (
                    g["between"], g["from_shift"], g["to_shift"], g["start"], g["end"], g["ms"], g["window_ms"],
                    " DAR" if g["narrow_window"] else "", g["weighted_tv"], g["mean_rel_amplitude"], g["voiced_ratio_in_span"], g["boundary"]))
bad = []
for c in plan["chunks"]:
    for h in c["syllables"]:
        mm = h.get("shift_in_protected_core_min_max")
        if mm and (abs(mm[0] - h["shift"]) > 0.02 or abs(mm[1] - h["shift"]) > 0.02):
            bad.append("K%d L%d %s %+.2f [%+.2f..%+.2f]" % (h["verse"], h["line"], h["text"], h["shift"], mm[0], mm[1]))
print("korunan cekirdekte kaydirmasi sabit olmayan hece:", len(bad), bad[:20])
ov = [g for g in allg if g.get("overlaps_previous")]
print("ust uste binen gecis:", len(ov), [(g["verse"], g["line"], g["between"]) for g in ov])
big = [g for g in allg if abs(g["to_shift"] - g["from_shift"]) >= 0.3]
ms = np.array([g["ms"] for g in big])
print("gecis suresi (>=0.3 yarim ses adimlar): n=%d en kisa %.0f ortanca %.0f en uzun %.0f ms" % (len(ms), ms.min(), np.median(ms), ms.max()))
print("bunlardan sesli orani >= 0.5 ve bagil genligi >= 0.7 olan:", sum(1 for g in big if g["voiced_ratio_in_span"] >= 0.5 and g["mean_rel_amplitude"] >= 0.7))
