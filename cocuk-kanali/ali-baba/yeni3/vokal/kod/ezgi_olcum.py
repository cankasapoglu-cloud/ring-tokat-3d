#!/usr/bin/env python3
"""ezgi_olcum: bir aday / sonuc dosyasinin vokal_dogal'a gore nesnel olcumleri (kulakla dinleme YOK).

 perde   : hece cekirdegi ortanca perdesi - hedef (cent); iki bagimsiz bulucu: pYIN (librosa) ve
           harvest+stonemask (seslilik: donemsellik olcusu ile)
 seslilik: sesli/otumsuz uyumu (pYIN ve harvest tabanli)
 zaman   : dize basina enerji zarfi capraz ilintisi -> gecikme (ms)
 duzey   : genel / dize basina RMS, LUFS, tepe
 tik     : 6 kHz ustu kisa sureli enerji sicramasi (ozgunde olmayan) + ornekler arasi en buyuk sicrama
 sicrama : sesli kosu icinde > 2 yarim seslik f0 sicramasi (planli gecislerden uzak, ozgunde olmayan)
 tayf    : kaydirilmayan bolgelerde mel tayf uzakligi (dB)
 zarf    : kaydirilan unlu cekirdeklerinde tayf zarfi (cheaptrick) uzakligi (dB) + kaba bant dengesi
 hnr     : donemsellikten harmonik/gurultu orani farki (tam bant ve 2-8 kHz), tepe faktoru farki"""
import os, hashlib, numpy as np, librosa, pyworld as pw
from scipy.signal import butter, sosfiltfilt
from scipy.ndimage import maximum_filter1d, uniform_filter1d
import ezgi_ortak as o

SR = o.SR
HOP_P = 220
_SOS_HP6 = butter(6, 6000.0, "high", fs=SR, output="sos")
_SOS_HF = butter(4, [2000.0, 8000.0], "band", fs=SR, output="sos")
_MEL40 = None
_MEL_ENV = None


def _h(a):
    return hashlib.md5(np.ascontiguousarray(a).tobytes()).hexdigest()[:10]


def pyin_onbellek(sig, ad):
    p = os.path.join(o.ARA, "pyin_%s_%s.npz" % (ad, _h(sig)))
    if os.path.exists(p):
        d = np.load(p); return d["t"], d["f0"], d["v"]
    f0, vf, vp = librosa.pyin(sig, fmin=150, fmax=750, sr=SR, frame_length=2048, hop_length=HOP_P, fill_na=np.nan)
    t = np.arange(len(f0)) * HOP_P / SR
    np.savez(p, t=t, f0=f0, v=vf)
    return t, f0, vf


def harvest_onbellek(sig, ad):
    p = os.path.join(o.ARA, "f0c_%s_%s.npz" % (ad, _h(sig)))
    if os.path.exists(p):
        d = np.load(p); return d["t"], d["f0"], d["lev"]
    t, f0, f0r, ncc, lev = o.f0_analiz(sig)
    np.savez(p, t=t, f0=f0, lev=lev)
    return t, f0, lev


def zarf(sig, ms=5.0):
    n = max(1, int(ms * 1e-3 * SR))
    return np.sqrt(uniform_filter1d(sig ** 2, n, mode="constant"))


def gecikme_ms(ex, ey, maxlag_ms=40.0):
    """ey, ex'e gore kac ms gec (+) / erken (-): capraz ilinti tepe noktasi (kesirli)."""
    d = 11
    a = ex[::d] - np.mean(ex[::d]); b = ey[::d] - np.mean(ey[::d])
    L = int(maxlag_ms * 1e-3 * SR / d)
    lags = np.arange(-L, L + 1)
    cc = np.array([np.dot(a[max(0, -l):len(a) - max(0, l)], b[max(0, l):len(b) - max(0, -l)]) for l in lags])
    k = int(np.argmax(cc)); lf = float(lags[k])
    if 0 < k < len(cc) - 1:
        den = cc[k - 1] - 2 * cc[k] + cc[k + 1]
        if abs(den) > 1e-20:
            lf += 0.5 * (cc[k - 1] - cc[k + 1]) / den
    nrm = np.sqrt(np.dot(a, a) * np.dot(b, b)) + 1e-20
    return lf * d / SR * 1000.0, float(cc[k] / nrm)


def _ncc(sig, k, P):
    P = int(round(P))
    if k - P < 0 or k + 2 * P > len(sig):
        return np.nan
    u = sig[k - P:k + P]; v = sig[k:k + 2 * P]
    d = np.sqrt(np.dot(u, u) * np.dot(v, v))
    return float(np.dot(u, v) / d) if d > 1e-14 else np.nan


def _hnr(r):
    r = np.clip(r, 0.01, 0.999)
    return 10 * np.log10(r / (1 - r))


def tam_olcum(x, y, Y, plan, ad, ayrinti=False):
    global _MEL40, _MEL_ENV
    if _MEL40 is None:
        _MEL40 = librosa.filters.mel(sr=SR, n_fft=1024, n_mels=40, fmin=80, fmax=12000)
        _MEL_ENV = librosa.filters.mel(sr=SR, n_fft=2048, n_mels=40, fmin=100, fmax=8000)
    N = len(x)
    assert len(y) == N
    hece_tablo = []
    vu_p = [0, 0]; vu_h = [0, 0]
    lags = []; lvl_line = []
    tik = []; sic = []
    sic_say = dict(harvest_out=0, pyin_out=0, harvest_orig=0, pyin_orig=0); egri = dict(harvest=[], pyin=[]); hece_olc = []
    lsd_unv = []; lsd_vz = []; env_d = []; kaba_d = []
    hnr_d = []; hnr_hf_d = []; crest_d = []
    max_jump = [0.0, 0.0]
    pc = {c["id"]: c for c in plan["chunks"]}
    for c in o.parcalar(Y):
        P = o.PAD
        sx, t, f0x, _, _, levx = o.parca_cozumle(x, c)
        sy = np.concatenate([np.zeros(P), y[c["a"]:c["b"]], np.zeros(P)])
        n = len(sx)
        t0 = o.seg_zaman(c)
        ty, f0y, levy = harvest_onbellek(sy, ad)
        tpx, pfx, pvx = pyin_onbellek(sx, "dogal")
        tpy, pfy, pvy = pyin_onbellek(sy, ad)
        s = np.load(os.path.join(o.ARA, "egri_%s.npy" % c["id"].replace("+", "_")))
        s = np.where(np.abs(s) < 1e-6, 0.0, s)
        pl = pc[c["id"]]
        # ---- perde
        mx, my = o.midi(f0x), o.midi(f0y)
        for h in pl["syllables"]:
            cs, ce = h["core_start"] - t0, h["core_end"] - t0
            ss, se = h["start"] - t0, h["end"] - t0
            row = dict(verse=h["verse"], line=h["line"], text=h["text"], shift=h["shift"], copied=h["copied"], uniform=h["uniform"])
            # harvest
            sel = (ty >= cs) & (ty < ce) & (f0y > 0)
            if sel.sum() < 5:
                sel = (ty >= ss) & (ty < se) & (f0y > 0)
            row["harvest_midi"] = float(np.median(my[sel])) if sel.any() else None
            row["target_harvest"] = h["target_midi"]
            # pyin
            selp = (tpy >= cs) & (tpy < ce) & pvy & np.isfinite(pfy)
            selo = (tpx >= cs) & (tpx < ce) & pvx & np.isfinite(pfx)
            if selp.sum() < 3 or selo.sum() < 3:
                selp = (tpy >= ss) & (tpy < se) & pvy & np.isfinite(pfy)
                selo = (tpx >= ss) & (tpx < se) & pvx & np.isfinite(pfx)
            pm = float(np.median(o.midi(pfy[selp]))) if selp.any() else None
            po = float(np.median(o.midi(pfx[selo]))) if selo.any() else None
            row["pyin_midi"] = pm; row["pyin_midi_dogal"] = po
            row["target_pyin"] = (po + h["shift"]) if (h["uniform"] and po is not None) else h["target_midi"]
            row["err_cents_harvest"] = None if row["harvest_midi"] is None else 100.0 * (row["harvest_midi"] - row["target_harvest"])
            row["err_cents_pyin"] = None if (pm is None or row["target_pyin"] is None) else 100.0 * (pm - row["target_pyin"])
            row["applied_shift_err_cents_pyin"] = None if (pm is None or po is None) else 100.0 * ((pm - po) - h["shift"])
            row["applied_shift_err_cents_harvest"] = None if row["harvest_midi"] is None else 100.0 * ((row["harvest_midi"] - h["measured_midi"]) - h["shift"])
            a, b = int(max(cs, 0) * SR), int(ce * SR)
            row["core_level_db_re_dogal"] = float(10 * np.log10((np.mean(sy[a:b] ** 2) + 1e-20) / (np.mean(sx[a:b] ** 2) + 1e-20)))
            hece_tablo.append(row)
        # ---- seslilik uyumu
        inp = (tpx >= P / SR) & (tpx <= (n - P) / SR)
        m = min(len(pvx), len(pvy))
        vu_p[0] += int(np.sum(pvx[:m][inp[:m]] == pvy[:m][inp[:m]])); vu_p[1] += int(np.sum(inp[:m]))
        inh = (t >= P / SR) & (t <= (n - P) / SR)
        m = min(len(f0x), len(f0y))
        vu_h[0] += int(np.sum((f0x[:m] > 0)[inh[:m]] == (f0y[:m] > 0)[inh[:m]])); vu_h[1] += int(np.sum(inh[:m]))
        # ---- zaman + duzey (dize basina)
        ex, ey = zarf(sx), zarf(sy)
        for L in c["lines"]:
            a, b = int((L["dest_in"] - t0) * SR), int((L["dest_out"] - t0) * SR)
            lg, cc = gecikme_ms(ex[a:b], ey[a:b])
            lags.append(dict(verse=L["verse"], line=L["line"], lag_ms=round(lg, 3), env_corr=round(cc, 4)))
            lvl_line.append(dict(verse=L["verse"], line=L["line"],
                                 rms_db_re_dogal=round(float(10 * np.log10(np.mean(sy[a:b] ** 2) / np.mean(sx[a:b] ** 2))), 3)))
        # ---- tik: 6 kHz ustu 1 ms enerji, ozgunun +-5 ms en buyugune gore
        hx, hy = sosfiltfilt(_SOS_HP6, sx), sosfiltfilt(_SOS_HP6, sy)
        k1 = int(0.001 * SR)
        e_x = uniform_filter1d(hx ** 2, k1, mode="constant"); e_y = uniform_filter1d(hy ** 2, k1, mode="constant")
        e_xm = maximum_filter1d(e_x, int(0.010 * SR), mode="constant")
        fl = (10 ** (-60 / 20.0)) ** 2
        ratio = 10 * np.log10((e_y + 1e-20) / (e_xm + fl))
        cand = np.where((ratio > 15.0) & (e_y > (10 ** (-45 / 20.0)) ** 2))[0]
        if len(cand):
            grp = np.split(cand, np.where(np.diff(cand) > int(0.005 * SR))[0] + 1)
            for g in grp:
                kmax = g[np.argmax(ratio[g])]
                tik.append(dict(t=round(float(kmax / SR + t0), 4), hf_ratio_db=round(float(ratio[kmax]), 1),
                                hf_level_dbfs=round(float(10 * np.log10(e_y[kmax])), 1), chunk=c["id"]))
        max_jump[0] = max(max_jump[0], float(np.abs(np.diff(sx)).max())); max_jump[1] = max(max_jump[1], float(np.abs(np.diff(sy)).max()))
        # ---- f0 sicramalari (5 ms; iki bulucu) + egri sadakati
        st5 = 5
        fx5, fy5, t5 = f0x[::st5], f0y[::st5], t[::st5]
        lx5, ly5 = levx[::st5], levy[::st5]
        s5 = s[np.clip(np.round(t5 * SR).astype(int), 0, n - 1)]
        # pYIN'i ayni 5 ms izgarasina tasi (en yakin kare)
        def pyin_izgara(tp, pf, pv):
            j = np.clip(np.round(t5 * SR / HOP_P).astype(int), 0, len(tp) - 1)
            return np.where(pv[j] & np.isfinite(pf[j]), pf[j], 0.0)
        px5, py5 = pyin_izgara(tpx, pfx, pvx), pyin_izgara(tpy, pfy, pvy)

        def sicramalar(f, lv, esik):
            g = np.abs(np.diff(o.midi(f)))
            ok = (f[:-1] > 0) & (f[1:] > 0) & (np.minimum(lv[:-1], lv[1:]) > -30)
            return np.where(ok & (g > esik))[0], g
        jyh, gyh = sicramalar(fy5, ly5, 2.0); jyp, gyp = sicramalar(py5, ly5, 2.0)
        jxh, _ = sicramalar(fx5, lx5, 1.5); jxp, _ = sicramalar(px5, lx5, 1.5)
        sic_say["harvest_out"] += len(jyh); sic_say["pyin_out"] += len(jyp)
        sic_say["harvest_orig"] += len(sicramalar(fx5, lx5, 2.0)[0]); sic_say["pyin_orig"] += len(sicramalar(px5, lx5, 2.0)[0])
        for k in jyh:
            tk = t5[k] + t0
            if not (len(jyp) and np.min(np.abs(jyp - k)) <= 2):
                continue                                   # iki bulucu ayni yerde gormuyorsa olcum hatasi say
            planli = any((g["start"] - 0.03 <= tk <= g["end"] + 0.03) and abs(g["to_shift"] - g["from_shift"]) >= 1.0 for g in pl["transitions"])
            ozgunde = (len(jxh) and np.min(np.abs(jxh - k)) <= 3) or (len(jxp) and np.min(np.abs(jxp - k)) <= 3)
            sic.append(dict(t=round(float(tk), 3), jump_semitones=round(float(gyh[k]), 2), near_planned_transition=bool(planli),
                            also_in_original=bool(ozgunde), level_dbfs=round(float(min(ly5[k], ly5[k + 1])), 1), chunk=c["id"]))
        for nm, fo, fc in (("harvest", fx5, fy5), ("pyin", px5, py5)):
            ok = (fo > 0) & (fc > 0) & (lx5 > -30)
            if ok.any():
                egri[nm].append(100.0 * (o.midi(fc[ok]) - (o.midi(fo[ok]) + s5[ok])))
        # ---- kaydirilmayan bolgelerde mel tayf uzakligi
        Mx = librosa.feature.melspectrogram(y=sx, sr=SR, n_fft=1024, hop_length=441, n_mels=40, fmin=80, fmax=12000, power=2.0)
        My = librosa.feature.melspectrogram(y=sy, sr=SR, n_fft=1024, hop_length=441, n_mels=40, fmin=80, fmax=12000, power=2.0)
        dX = 10 * np.log10(Mx + 1e-10); dY = 10 * np.log10(My + 1e-10)
        f0s_x = np.interp(np.arange(n) / SR, t, (f0x > 0).astype(float)) > 0.5
        hw = 512
        for fi in range(Mx.shape[1]):
            cn = fi * 441
            a, b = max(0, cn - hw), min(n, cn + hw)
            if a < P or b > n - P:
                continue
            if 10 * np.log10(np.mean(sx[a:b] ** 2) + 1e-20) < -55:
                continue
            d = float(np.sqrt(np.mean((dY[:, fi] - dX[:, fi]) ** 2)))
            if not f0s_x[a:b].any():
                lsd_unv.append(d)
            elif f0s_x[a:b].all() and np.all(s[a:b] == 0.0):
                lsd_vz.append(d)
        # ---- zarf uzakligi, HNR, tepe faktoru: kaydirilan hecelerin cekirdek kareleri (5 ms)
        fx5c = np.ascontiguousarray(fx5); fy5c = np.ascontiguousarray(fy5); t5c = np.ascontiguousarray(t5)
        spx = pw.cheaptrick(sx, fx5c, t5c, SR); spy = pw.cheaptrick(sy, fy5c, t5c, SR)
        Sx = np.abs(librosa.stft(sx, n_fft=2048, hop_length=220, center=True)) ** 2
        Sy = np.abs(librosa.stft(sy, n_fft=2048, hop_length=220, center=True)) ** 2
        fr = np.arange(1025) * SR / 2048.0
        bands = [(k * 1000.0, (k + 1) * 1000.0) for k in range(8)]
        yhf, xhf = sosfiltfilt(_SOS_HF, sy), sosfiltfilt(_SOS_HF, sx)
        for h in pl["syllables"]:
            if abs(h["shift"]) <= o.KOPYA_ESIK:
                continue
            cs, ce = h["core_start"] - t0, h["core_end"] - t0
            idx = np.where((t5 >= cs) & (t5 < ce) & (fx5 > 0) & (fy5 > 0))[0]
            if len(idx) < 3:
                continue
            ex_ = 10 * np.log10(_MEL_ENV @ spx[idx].T + 1e-20); ey_ = 10 * np.log10(_MEL_ENV @ spy[idx].T + 1e-20)
            dd = (ey_ - ey_.mean(axis=0)) - (ex_ - ex_.mean(axis=0))
            env_d.append(float(np.mean(np.sqrt(np.mean(dd ** 2, axis=0)))))
            kf = np.clip(np.round(t5[idx] * SR / 220).astype(int), 0, Sx.shape[1] - 1)
            bx = np.array([[Sx[(fr >= lo) & (fr < hi), k].sum() for k in kf] for lo, hi in bands])
            by = np.array([[Sy[(fr >= lo) & (fr < hi), k].sum() for k in kf] for lo, hi in bands])
            bx = 10 * np.log10(bx + 1e-20); by = 10 * np.log10(by + 1e-20)
            dk = (by - by.mean(axis=0)) - (bx - bx.mean(axis=0))
            kaba_d.append(float(np.mean(np.sqrt(np.mean(dk ** 2, axis=0)))))
            hx_, hy_, hxf, hyf, cx_, cy_ = [], [], [], [], [], []
            for i in idx:
                k = int(round(t5[i] * SR)); Px, Py = SR / fx5[i], SR / fy5[i]
                hx_.append(_hnr(_ncc(sx, k, Px))); hy_.append(_hnr(_ncc(sy, k, Py)))
                hxf.append(_hnr(_ncc(xhf, k, Px))); hyf.append(_hnr(_ncc(yhf, k, Py)))
                wx = sx[max(0, k - int(Px)):k + int(Px)]; wy = sy[max(0, k - int(Py)):k + int(Py)]
                cx_.append(20 * np.log10(np.abs(wx).max() / (np.sqrt(np.mean(wx ** 2)) + 1e-12) + 1e-12))
                cy_.append(20 * np.log10(np.abs(wy).max() / (np.sqrt(np.mean(wy ** 2)) + 1e-12) + 1e-12))
            hece_olc.append(dict(verse=h["verse"], line=h["line"], text=h["text"], shift=h["shift"], env=env_d[-1], coarse=kaba_d[-1],
                                 hnr=float(np.nanmedian(hy_) - np.nanmedian(hx_)), hnr_hf=float(np.nanmedian(hyf) - np.nanmedian(hxf)), crest=float(np.median(cy_) - np.median(cx_))))
            hnr_d.append(float(np.nanmedian(hy_) - np.nanmedian(hx_)))
            hnr_hf_d.append(float(np.nanmedian(hyf) - np.nanmedian(hxf)))
            crest_d.append(float(np.median(cy_) - np.median(cx_)))
    # ---- ozet
    def ist(rows, key):
        v = np.array([abs(r[key]) for r in rows if r[key] is not None])
        return dict(n=int(len(v)), mean_abs=round(float(v.mean()), 2) if len(v) else None, max_abs=round(float(v.max()), 2) if len(v) else None,
                    over_50=int(np.sum(v > 50)))
    kay = [r for r in hece_tablo if not r["copied"]]
    kop = [r for r in hece_tablo if r["copied"]]
    akt = np.zeros(N, dtype=bool)
    for c in o.parcalar(Y):
        akt[c["a"]:c["b"]] = True
    import pyloudnorm
    meter = pyloudnorm.Meter(SR)
    lufs_x, lufs_y = float(meter.integrated_loudness(x)), float(meter.integrated_loudness(y))
    yeni_sic = [q for q in sic if not q["near_planned_transition"] and not q["also_in_original"]]
    res = dict(
        name=ad,
        pitch=dict(shifted_syllables=dict(pyin=ist(kay, "err_cents_pyin"), harvest=ist(kay, "err_cents_harvest")),
                   applied_shift_check=dict(pyin=ist(kay, "applied_shift_err_cents_pyin"), harvest=ist(kay, "applied_shift_err_cents_harvest")),
                   over_50_confirmed_by_both=int(sum(1 for r in kay if r["err_cents_pyin"] is not None and r["err_cents_harvest"] is not None and abs(r["err_cents_pyin"]) > 50 and abs(r["err_cents_harvest"]) > 50)),
                   copied_syllables=dict(pyin=ist(kop, "err_cents_pyin"), harvest=ist(kop, "err_cents_harvest")),
                   all_syllables=dict(pyin=ist(hece_tablo, "err_cents_pyin"), harvest=ist(hece_tablo, "err_cents_harvest")),
                   over_50_cents=[dict(verse=r["verse"], line=r["line"], text=r["text"], shift=r["shift"], copied=r["copied"],
                                       err_cents_pyin=None if r["err_cents_pyin"] is None else round(r["err_cents_pyin"], 1),
                                       err_cents_harvest=None if r["err_cents_harvest"] is None else round(r["err_cents_harvest"], 1))
                                  for r in hece_tablo if (r["err_cents_pyin"] is not None and abs(r["err_cents_pyin"]) > 50)
                                  or (r["err_cents_harvest"] is not None and abs(r["err_cents_harvest"]) > 50)]),
        voicing_agreement=dict(pyin_percent=round(100.0 * vu_p[0] / max(1, vu_p[1]), 2), harvest_percent=round(100.0 * vu_h[0] / max(1, vu_h[1]), 2)),
        timing=dict(max_abs_lag_ms=round(max(abs(q["lag_ms"]) for q in lags), 3), mean_abs_lag_ms=round(float(np.mean([abs(q["lag_ms"]) for q in lags])), 3),
                    min_env_corr=round(min(q["env_corr"] for q in lags), 4), lines=lags),
        level=dict(rms_db_re_dogal=round(float(10 * np.log10(np.mean(y[akt] ** 2) / np.mean(x[akt] ** 2))), 3),
                   lufs_dogal=round(lufs_x, 2), lufs=round(lufs_y, 2), lufs_diff=round(lufs_y - lufs_x, 2),
                   peak_dbfs=round(float(20 * np.log10(np.abs(y).max())), 2), peak_dbfs_dogal=round(float(20 * np.log10(np.abs(x).max())), 2),
                   line_rms_db_max_abs=round(max(abs(q["rms_db_re_dogal"]) for q in lvl_line), 3), lines=lvl_line,
                   syllable_core_level_db_mean_abs=round(float(np.mean([abs(r["core_level_db_re_dogal"]) for r in hece_tablo])), 3),
                   syllable_core_level_db_max_abs=round(float(np.max([abs(r["core_level_db_re_dogal"]) for r in hece_tablo])), 3)),
        clicks=dict(count=len(tik), events=tik[:50], max_sample_jump=round(max_jump[1], 5), max_sample_jump_dogal=round(max_jump[0], 5)),
        f0_jumps=dict(definition="5 ms frames, both frames voiced and above -30 dBFS, |step| > 2 semitones; an output jump counts only if BOTH detectors (harvest+stonemask and pYIN) show it within 10 ms",
                      raw_counts=sic_say, confirmed_total=len(sic), near_planned_transitions=int(sum(q["near_planned_transition"] for q in sic)),
                      also_in_original=int(sum(q["also_in_original"] and not q["near_planned_transition"] for q in sic)),
                      new_away_from_transitions=len(yeni_sic), new_events=yeni_sic[:60]),
        contour=dict(definition="frame-wise detected f0 of the result minus (f0 of vokal_dogal + planned shift), frames voiced in both and above -30 dBFS, cents",
                     **{nm: dict(frames=int(len(np.concatenate(v))), rms=round(float(np.sqrt(np.mean(np.concatenate(v) ** 2))), 1),
                                 median_abs=round(float(np.median(np.abs(np.concatenate(v)))), 1), p95_abs=round(float(np.percentile(np.abs(np.concatenate(v)), 95)), 1),
                                 over_100_cents_percent=round(float(100 * np.mean(np.abs(np.concatenate(v)) > 100)), 2)) for nm, v in egri.items()}),
        spectral=dict(unvoiced_frames=len(lsd_unv), unvoiced_lsd_db=round(float(np.mean(lsd_unv)), 3) if lsd_unv else None,
                      voiced_unshifted_frames=len(lsd_vz), voiced_unshifted_lsd_db=round(float(np.mean(lsd_vz)), 3) if lsd_vz else None,
                      unshifted_all_lsd_db=round(float(np.mean(lsd_unv + lsd_vz)), 3) if (lsd_unv or lsd_vz) else None,
                      shifted_envelope_dist_db=round(float(np.mean(env_d)), 3), shifted_envelope_dist_db_p90=round(float(np.percentile(env_d, 90)), 3),
                      shifted_coarse_band_dist_db=round(float(np.mean(kaba_d)), 3)),
        periodicity=dict(hnr_diff_db_mean=round(float(np.mean(hnr_d)), 2), hnr_diff_db_mean_abs=round(float(np.mean(np.abs(hnr_d))), 2),
                         hnr_2_8k_diff_db_mean=round(float(np.mean(hnr_hf_d)), 2), hnr_2_8k_diff_db_mean_abs=round(float(np.mean(np.abs(hnr_hf_d))), 2),
                         crest_diff_db_mean=round(float(np.mean(crest_d)), 2), crest_diff_db_mean_abs=round(float(np.mean(np.abs(crest_d))), 2),
                         syllables=len(hnr_d)))
    res["_per_syllable_quality"] = hece_olc
    if ayrinti:
        res["syllables"] = hece_tablo
    return res
