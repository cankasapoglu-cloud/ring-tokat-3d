#!/usr/bin/env python3
"""ezgi_yontem: uc aday yontem (hepsi YALNIZ perdeyi degistirir, zamanlama ayni kalir).

  psola(seg, t, f0, s)        : zaman uzayinda perde-esdurumlu ust uste bindirme (TD-PSOLA). Otumsuz
                                yerler ve kaydirmasi 0 olan sesli bolgeler ornek ornek ozgun kalir.
  world_tam(seg, t, f0, s)    : tum parca WORLD ile yeniden sentezlenir (yalniz f0 degisir).
  world_karma(seg, t, f0, s)  : yalniz 'sesli VE kaydirilan' adalar WORLD'den, gerisi ozgun ornekler
                                (capraz gecisle; sesli-surekli eklerde faz hizalamasi ile).
seg: parca (PAD dahil), t/f0: 1 ms kareler (f0=0 otumsuz), s: ornek basina kaydirma (yarim ses)."""
import numpy as np, pyworld as pw
from scipy.signal import butter, sosfiltfilt, hilbert, resample_poly
from scipy.ndimage import gaussian_filter1d
import ezgi_ortak as o

SR = o.SR
PSI_SIGMA_MS = 12.0     # perde isareti evresinin (enerji agirlik merkezi) yumusatma genisligi
_SOS_ENV = butter(4, [60.0, 5000.0], "band", fs=SR, output="sos")


def ornek_f0(n, t, f0):
    """Kare f0'ini ornek basina (log-dogrusal) ac; otumsuz = 0. Donus: f0s, sesli kosular [(n0,n1)]."""
    pos = np.round(t * SR).astype(int)
    v = f0 > 0
    f0s = np.zeros(n)
    runs = []
    i = 0
    while i < len(t):
        if v[i]:
            j = i
            while j < len(t) and v[j]:
                j += 1
            n0 = max(0, pos[i] - int(0.0005 * SR)); n1 = min(n, pos[j - 1] + int(0.0005 * SR) + 1)
            idx = np.arange(n0, n1)
            f0s[n0:n1] = np.exp(np.interp(idx, pos[i:j], np.log(f0[i:j])))
            runs.append((n0, n1))
            i = j
        else:
            i += 1
    return f0s, runs


def _kesirli_kaydir(g, delta):
    """g'yi delta (|delta|<=0.5 ornek) kadar geciktir (FFT faz egimi); donus ayni uzunluk + 2*pad."""
    pad = 24
    N = 1
    while N < len(g) + 2 * pad:
        N *= 2
    buf = np.zeros(N); buf[pad:pad + len(g)] = g
    G = np.fft.rfft(buf)
    k = np.arange(len(G))
    G *= np.exp(-2j * np.pi * k * delta / N)
    out = np.fft.irfft(G, N)
    return out[:len(g) + 2 * pad], pad


def psola_isaretler(seg, f0s, n0, n1, wenv):
    """Bir sesli kosu icin cozumleme evresi psi(n) (tam sayi gecisleri = perde isaretleri).
    psi = f0 izinden gelen evre + enerji zarfinin temel bileseninin evresi (enerji agirlik merkezi)."""
    ext = int(0.020 * SR)
    e0, e1 = max(0, n0 - ext), min(len(seg), n1 + ext)
    f = f0s[e0:e1].copy()
    f[:n0 - e0] = f0s[n0]
    f[n1 - e0:] = f0s[n1 - 1]
    phi = np.cumsum(f) / SR
    c = wenv[e0:e1] * np.exp(-2j * np.pi * phi)
    sig = PSI_SIGMA_MS * 1e-3 * SR
    z = gaussian_filter1d(c.real, sig, mode="nearest") + 1j * gaussian_filter1d(c.imag, sig, mode="nearest")
    theta = np.unwrap(np.angle(z))
    psi = phi + theta / (2 * np.pi)
    return e0, psi


def psola(seg, t, f0, s, kazanc_us=0.5, bilgi=None):
    n = len(seg)
    f0s, runs = ornek_f0(n, t, f0)
    xb = sosfiltfilt(_SOS_ENV, seg)
    wenv = np.abs(hilbert(xb)) ** 2
    s = np.where(np.abs(s) < 1e-6, 0.0, s)
    r_all = 2.0 ** (s / 12.0)
    acc = np.zeros(n + 8); cover = np.zeros(n + 8); mod = np.zeros(n + 8, dtype=bool)
    st = dict(runs=len(runs), runs_processed=0, marks=0, grains=0, locks=0, lock_failed=0, lock_eps_max=0.0,
              nonmonotone_runs=0, freq_dev_cents_p95=[], skipped_short=0)
    for (n0, n1) in runs:
        if not np.any(s[n0:n1] != 0.0):
            continue
        e0, psi = psola_isaretler(seg, f0s, n0, n1, wenv)
        idx = np.arange(e0, e0 + len(psi))
        dps = np.diff(psi)
        if np.any(dps[(idx[:-1] >= n0) & (idx[:-1] < n1)] <= 0):
            st["nonmonotone_runs"] += 1
            # tekduzeligi zorla
            mn = 0.2 * np.median(dps[dps > 0]) if np.any(dps > 0) else 1e-4
            dps = np.maximum(dps, mn)
            psi = np.concatenate([[psi[0]], psi[0] + np.cumsum(dps)])
        sel = (idx >= n0) & (idx < n1)
        ps, ix = psi[sel], idx[sel].astype(float)
        k0, k1 = int(np.ceil(ps[0] + 1e-9)), int(np.floor(ps[-1] - 1e-9))
        if k1 - k0 < 4:
            st["skipped_short"] += 1
            continue
        ks = np.arange(k0, k1 + 1)
        a = np.interp(ks, ps, ix)                       # cozumleme isaretleri (gercel ornek konumlari)
        M = len(a) - 1
        # cozumleme frekansi ile f0 izi uyumu (denetim)
        fa = SR / np.diff(a); ff = f0s[np.round(0.5 * (a[:-1] + a[1:])).astype(int)]
        dev = 1200 * np.abs(np.log2(fa / np.maximum(ff, 1e-6)))
        st["freq_dev_cents_p95"].append(float(np.percentile(dev, 95)))
        # sentez evresi Phi = integral r dpsi  (a_0'da 0), kilitleme duzeltmeleriyle
        r = r_all[n0:n1].copy()
        dpsi = np.diff(ps, append=ps[-1] + (ps[-1] - ps[-2]))
        zero = (s[n0:n1] == 0.0)
        ia0 = int(np.ceil(a[0])) - n0
        # sifir bolgelerinin baslangiclari (oncesi sifir olmayan)
        starts = [q for q in range(max(1, ia0 + 1), n1 - n0) if zero[q] and not zero[q - 1]]
        Tb = int(0.040 * SR)
        for z0 in starts:
            Phi = np.concatenate([[0.0], np.cumsum(r * dpsi)[:-1]])
            Psi = ps - ps[0]
            off = np.interp(a[0] - n0, np.arange(n1 - n0), Phi) - np.interp(a[0] - n0, np.arange(n1 - n0), Psi)
            D = (Phi[z0] - Psi[z0]) - off
            cneed = np.round(D) - D
            u0 = max(ia0, z0 - Tb)
            # onceki sifir bolgesine girmeyelim
            q = z0 - 1
            while q > u0 and not zero[q]:
                q -= 1
            u0 = max(u0, q + 1) if zero[q] else u0
            L = z0 - u0
            if L < int(0.012 * SR):
                st["lock_failed"] += 1
                continue
            b = 0.5 - 0.5 * np.cos(2 * np.pi * (np.arange(L) + 0.5) / L)
            den = float(np.sum(b * r[u0:z0] * dpsi[u0:z0]))
            eps = cneed / den if den > 0 else 0.0
            if abs(eps) > 0.15:
                st["lock_failed"] += 1
                continue
            r[u0:z0] *= (1.0 + eps * b)
            st["locks"] += 1; st["lock_eps_max"] = max(st["lock_eps_max"], abs(float(eps)))
        Phi = np.concatenate([[0.0], np.cumsum(r * dpsi)[:-1]])
        loc = np.arange(n1 - n0, dtype=float)
        Phi = Phi - np.interp(a[0] - n0, loc, Phi)
        Psi = ps - k0
        J = int(np.floor(np.interp(a[M] - n0, loc, Phi) + 1e-6))
        sj = np.interp(np.arange(0, J + 1), Phi, loc) + n0     # sentez isaretleri
        ii = np.clip(np.round(np.interp(sj - n0, loc, Psi)).astype(int), 0, M)
        rj = np.interp(sj - n0, loc, r)
        # cozumleme pencereleri
        Lw = np.empty(M + 1); Rw = np.empty(M + 1)
        Lw[1:] = np.diff(a); Lw[0] = a[1] - a[0]
        Rw[:-1] = np.diff(a); Rw[-1] = Lw[-1]
        grains = []
        used = np.zeros(M + 1, dtype=int); ident = np.zeros(M + 1, dtype=bool)
        for i in range(M + 1):
            m0 = int(np.ceil(a[i] - Lw[i])); m1 = int(np.floor(a[i] + Rw[i]))
            m0 = max(m0, 0); m1 = min(m1, n - 1)
            mm = np.arange(m0, m1 + 1)
            wl = np.cos(0.5 * np.pi * (a[i] - mm) / Lw[i]) ** 2
            wr = np.cos(0.5 * np.pi * (mm - a[i]) / Rw[i]) ** 2
            wg = np.where(mm <= a[i], wl, wr)
            grains.append((m0, wg))
            cover[m0:m1 + 1] += wg
        for j in range(len(sj)):
            i = ii[j]
            m0, wg = grains[i]
            g = seg[m0:m0 + len(wg)] * wg
            d = sj[j] - a[i]
            gain = rj[j] ** (-kazanc_us)
            used[i] += 1
            if abs(d) < 1e-6 and abs(gain - 1.0) < 1e-9:
                acc[m0:m0 + len(wg)] += g
                ident[i] = True
            else:
                Di = int(np.round(d)); dl = d - Di
                if abs(dl) < 1e-7:
                    p0 = m0 + Di
                    lo, hi = max(p0, 0), min(p0 + len(g), n)
                    acc[lo:hi] += gain * g[lo - p0:hi - p0]
                else:
                    gs, pad = _kesirli_kaydir(g, dl)
                    p0 = m0 + Di - pad
                    lo, hi = max(p0, 0), min(p0 + len(gs), n)
                    acc[lo:hi] += gain * gs[lo - p0:hi - p0]
                    lo2, hi2 = max(p0, 0), min(p0 + len(gs), n)
                    mod[lo2:hi2] = True
                mod[max(m0 + Di, 0):min(m0 + Di + len(g), n)] = True
        for i in range(M + 1):
            if not (used[i] == 1 and ident[i]):
                m0, wg = grains[i]
                mod[m0:m0 + len(wg)] = True
        st["runs_processed"] += 1; st["marks"] += M + 1; st["grains"] += len(sj)
    y = seg * (1.0 - cover[:n]) + acc[:n]
    y = np.where(mod[:n], y, seg)                      # dokunulmayan ornekler birebir ozgun
    st["modified_ratio"] = float(np.mean(mod[:n]))
    st["freq_dev_cents_p95_max"] = float(max(st["freq_dev_cents_p95"])) if st["freq_dev_cents_p95"] else 0.0
    st["freq_dev_cents_p95_median"] = float(np.median(st["freq_dev_cents_p95"])) if st["freq_dev_cents_p95"] else 0.0
    del st["freq_dev_cents_p95"]
    if bilgi is not None:
        bilgi.update(st)
    return y, mod[:n]


# ------------------------------------------------------------------ WORLD
WFP = 2.0     # WORLD kare araligi (ms)
D4C_ESIK = 0.0


def world_coz(seg, t, f0):
    step = int(round(WFP / o.FP))
    tw = np.ascontiguousarray(t[::step]); f0w = np.ascontiguousarray(f0[::step])
    sp = pw.cheaptrick(seg, f0w, tw, SR)
    # threshold=0: D4C'nin kendi sesli/otumsuz karari kapali (seslilik zaten f0_analiz'de donemsellikle belirlendi;
    # aksi halde dusuk duzeyli genizsi/sesli unsuzler gurultu olarak sentezleniyor)
    ap = pw.d4c(seg, f0w, tw, SR, threshold=D4C_ESIK)
    return tw, f0w, sp, ap


def world_sentez(seg, tw, f0w, sp, ap, s):
    """Yalniz f0 degisir (otumsuz kareler otumsuz kalir); zarf (formantlar) ve aperiyodiklik ayni."""
    si = np.interp(tw, np.arange(len(s)) / SR, s)
    f0n = np.where(f0w > 0, f0w * 2.0 ** (si / 12.0), 0.0)
    y = pw.synthesize(f0n, sp, ap, SR, WFP)
    out = np.zeros(len(seg)); m = min(len(seg), len(y)); out[:m] = y[:m]
    return out


def kenar_maskesi(n, pad=o.PAD, ms=5.0):
    """Parcanin disinda (PAD) tam sifir; ic kenarlarda 5 ms yukseltilmis kosinus."""
    m = np.zeros(n); k = int(ms * 1e-3 * SR)
    m[pad:n - pad] = 1.0
    r = 0.5 - 0.5 * np.cos(np.pi * (np.arange(k) + 0.5) / k)
    m[pad:pad + k] = r; m[n - pad - k:n - pad] = r[::-1]
    return m


def _kaydirilmis(yw, i0, i1, L0, L1):
    """yw'nin [i0,i1) bolumunu n -> n + L(n) konumlarindan oku (L dogrusal: L0..L1), 8x ust ornekleme + dogrusal."""
    mar = int(max(abs(L0), abs(L1))) + 40
    a, b = max(0, i0 - mar), min(len(yw), i1 + mar)
    up = resample_poly(yw[a:b], 8, 1)
    nn = np.arange(i0, i1)
    L = L0 + (L1 - L0) * (nn - i0) / max(1, (i1 - i0 - 1))
    pos = (nn + L - a) * 8.0
    return np.interp(pos, np.arange(len(up)), up)


def _gecikme_bul(seg, yw, c, P):
    """c orneginin cevresinde (+-1.5 donem) seg[n] ile yw[n+L] en iyi ortusen L (|L|<=P/2, kesirli)."""
    h = int(1.5 * P); Lm = int(np.ceil(P / 2)) + 1
    a, b = c - h, c + h
    if a - Lm < 0 or b + Lm > len(seg):
        return 0.0, 0.0, 0.0
    u = seg[a:b]
    lags = np.arange(-Lm, Lm + 1)
    cc = np.array([np.dot(u, yw[a + L:b + L]) / (np.sqrt(np.dot(u, u) * np.dot(yw[a + L:b + L], yw[a + L:b + L])) + 1e-12) for L in lags])
    k = int(np.argmax(cc))
    Lf = float(lags[k])
    if 0 < k < len(cc) - 1:
        y0, y1, y2 = cc[k - 1], cc[k], cc[k + 1]
        den = (y0 - 2 * y1 + y2)
        if abs(den) > 1e-12:
            Lf += 0.5 * (y0 - y2) / den
    return Lf, float(cc[k]), float(cc[Lm])       # gecikme, hizali ilinti, hizasiz (L=0) ilinti


def world_karma(seg, t, f0, s, yw, bilgi=None):
    """Ozgun ornekler + yalniz 'sesli ve kaydirilan' adalarda WORLD cikisi."""
    n = len(seg)
    f0s, runs = ornek_f0(n, t, f0)
    voiced = f0s > 0
    s0 = np.where(np.abs(s) < 1e-6, 0.0, s)
    need = voiced & (s0 != 0.0)
    # adalar; <= 20 ms bosluklari birlestir (bosluk sesli+sifir kaydirmali degilse)
    isl = []
    i = 0
    while i < n:
        if need[i]:
            j = i
            while j < n and need[j]:
                j += 1
            isl.append([i, j]); i = j
        else:
            i += 1
    mer = []
    for a, b in isl:
        if mer and (a - mer[-1][1]) <= int(0.020 * SR) and not np.any(voiced[mer[-1][1]:a] & (s0[mer[-1][1]:a] == 0.0)):
            mer[-1][1] = b
        else:
            mer.append([a, b])
    aw = np.zeros(n); ao = np.ones(n); yy = np.zeros(n); mod = np.zeros(n, dtype=bool)
    k2, k8 = int(0.002 * SR), int(0.008 * SR)
    st = dict(islands=len(mer), coherent_joins=0, unvoiced_joins=0, double_coherent=0, join_corr_before=[], join_corr_after=[],
              double_coherent_cents=[], island_ms=[])
    for (i0, i1) in mer:
        lc = i0 > 0 and voiced[i0 - 1] and s0[i0 - 1] == 0.0
        rc = i1 < n and voiced[i1] and s0[i1] == 0.0
        L0 = L1 = 0.0
        if lc:
            c = i0 - k8 // 2; P = SR / f0s[c]
            L0, ca, cb = _gecikme_bul(seg, yw, c, P)
            st["join_corr_before"].append(cb); st["join_corr_after"].append(ca)
        if rc:
            c = i1 + k8 // 2; P = SR / f0s[min(c, n - 1)] if f0s[min(c, n - 1)] > 0 else SR / f0s[i1]
            L1, ca, cb = _gecikme_bul(seg, yw, c, P)
            st["join_corr_before"].append(cb); st["join_corr_after"].append(ca)
        if lc and rc:
            P = SR / f0s[i1]
            L1 = L1 + P * np.round((L0 - L1) / P)
            st["double_coherent"] += 1
            st["double_coherent_cents"].append(float(1200 * np.log2(1.0 + (L1 - L0) / max(1, i1 - i0))))
        elif lc:
            L1 = L0
        elif rc:
            L0 = L1
        a = max(0, i0 - k8 - 4); b = min(n, i1 + k8 + 4)
        if lc or rc:
            La = L0 + (L1 - L0) * (a - i0) / max(1, (i1 - i0 - 1)); Lb = L0 + (L1 - L0) * (b - 1 - i0) / max(1, (i1 - i0 - 1))
            yy[a:b] = _kaydirilmis(yw, a, b, La, Lb)
        else:
            yy[a:b] = yw[a:b]
        # agirliklar
        aw[i0:i1] = 1.0; ao[i0:i1] = 0.0
        if lc:      # sesli-surekli: dogrusal (toplam 1), ada baslamadan hemen once
            u = (np.arange(k8) + 0.5) / k8; r = 0.5 - 0.5 * np.cos(np.pi * u)
            aw[i0 - k8:i0] = r; ao[i0 - k8:i0] = 1.0 - r; st["coherent_joins"] += 1
        else:       # otumsuz / sessiz: esit guc, seslilik baslamadan 2 ms once biter
            p0 = max(0, i0 - k8); p1 = max(p0 + 1, i0 - k2)
            u = (np.arange(p1 - p0) + 0.5) / (p1 - p0)
            aw[p0:p1] = np.sin(0.5 * np.pi * u); ao[p0:p1] = np.cos(0.5 * np.pi * u)
            aw[p1:i0] = 1.0; ao[p1:i0] = 0.0; st["unvoiced_joins"] += 1
        if rc:
            u = (np.arange(k8) + 0.5) / k8; r = 0.5 + 0.5 * np.cos(np.pi * u)
            e1 = min(n, i1 + k8)
            aw[i1:e1] = r[:e1 - i1]; ao[i1:e1] = 1.0 - r[:e1 - i1]; st["coherent_joins"] += 1
        else:
            p0 = min(n, i1 + k2); p1 = min(n, i1 + k8)
            aw[i1:p0] = 1.0; ao[i1:p0] = 0.0
            if p1 > p0:
                u = (np.arange(p1 - p0) + 0.5) / (p1 - p0)
                aw[p0:p1] = np.cos(0.5 * np.pi * u); ao[p0:p1] = np.sin(0.5 * np.pi * u)
            st["unvoiced_joins"] += 1
        mod[a:b] |= aw[a:b] > 0
        st["island_ms"].append(1000.0 * (i1 - i0) / SR)
    y = ao * seg + aw * yy
    y = np.where(mod, y, seg)
    st["modified_ratio"] = float(np.mean(mod))
    if bilgi is not None:
        bilgi.update(st)
    return y, mod


# ------------------------------------------------------------------ duzey esitleme
def duzey_esitle(seg, y, mod, sig_ms=25.0, lim_db=3.0, rampa_ms=8.0):
    """Degistirilen bolgelerde kisa sureli duzeyi ozgune esitle (yumusak kazanc, +-3 dB sinirli).
    Degistirilmeyen ornekler birebir kalir (kazanc tam 1)."""
    from scipy.ndimage import distance_transform_edt
    sig = sig_ms * 1e-3 * SR
    eps = (10 ** (-60 / 20.0)) ** 2
    eo = gaussian_filter1d(seg ** 2, sig, mode="constant")
    ey = gaussian_filter1d(y ** 2, sig, mode="constant")
    g = np.sqrt((eo + eps) / (ey + eps))
    lim = 10 ** (lim_db / 20.0)
    g = np.clip(g, 1.0 / lim, lim)
    if mod.all():
        msk = np.ones(len(seg))
    else:
        dist = distance_transform_edt(mod)                 # degistirilmeyen en yakin ornege uzaklik
        msk = np.clip(dist / (rampa_ms * 1e-3 * SR), 0.0, 1.0)
    g = 1.0 + (g - 1.0) * msk
    return y * g, g
