#!/usr/bin/env python3
"""3. kita "atları": uc hece mi (at-la-rı) dort hece mi (a-tı-la-rı)?  Olcum + kesip atma araligi + diger kelimelerin taramasi.
kesim.py tarafindan cagrilir (hece tablosu hazir olduktan sonra).

Kanitlar
  1) cekirdek sayimi : kor zarf tepeleri (izgara kullanmadan) + sablondaki 4 yuvanin (6, 6.5, 7, 7.25. vurus) her
                       birinde yeni bir sesli baslangic olup olmadigi.
  2) sure            : 't' patlamasi bittikten sonra otumun basladigi an ile "la"nin 'a'sinin basladigi an arasi;
                       ayni olcu diger "-ları / -leri" kelimelerinde (unsuz + l + unlu).
  3) spektrum        : o araligin ilk bolumu (parlak) ile ikinci bolumu (koyu) icin bant duzeyleri, harmonik
                       genlikleri, LPC bicimlendirici kestirimi ve spektral zarfin ayni sarkicinin PERDESI YAKIN
                       a / ı / i / e / l / n ornekleriyle karsilastirmasi (harmoniklerden aradegerlenen zarf, RMS dB).
                       (Ilk denemedeki kare bazli log-mel siniflandiricisi perdeye bagimli ciktigi icin birakildi.)
"""
import numpy as np, librosa
from scipy.signal import resample_poly
from zarf import (x, fs, t, DT, fi, E12, E30, ELOW8, F2B, EHI, R5, LMEL, th, f0h, FP, midi, db_ham, nota_adi)

BANTLAR = [("200_600", 200, 600), ("600_1000", 600, 1000), ("1000_1800", 1000, 1800), ("1800_3400", 1800, 3400), ("4000_12000", 4000, 12000)]


def spektrum(a, b, nfft=2048):
    seg = x[int(a * fs):int(b * fs)]
    if len(seg) < nfft:
        seg = np.pad(seg, (0, nfft - len(seg)))
    hop = 256; w = np.hanning(nfft); P = np.zeros(nfft // 2 + 1); n = 0
    for i in range(0, len(seg) - nfft + 1, hop):
        P += np.abs(np.fft.rfft(seg[i:i + nfft] * w)) ** 2; n += 1
    return np.fft.rfftfreq(nfft, 1 / fs), P / max(n, 1)


def bant_profili(a, b):
    """Bant duzeyleri: 200-3400 Hz toplamina gore dB."""
    f, P = spektrum(a, b, 1024)
    top = P[(f >= 200) & (f < 3400)].sum() + 1e-20
    return {ad: round(float(10 * np.log10(P[(f >= lo) & (f < hi)].sum() / top + 1e-12)), 1) for ad, lo, hi in BANTLAR}


def harmonikler(a, b, n=8):
    m = (th >= a) & (th < b) & (f0h > 0)
    if m.sum() < 2:
        return None
    f0 = float(np.median(f0h[m]))
    f, P = spektrum(a, b, 4096)
    amp = []
    for k in range(1, n + 1):
        sel = (f >= k * f0 * 0.96) & (f <= k * f0 * 1.04)
        amp.append(10 * np.log10(P[sel].max() + 1e-20))
    amp = np.array(amp) - max(amp)
    return {"f0_hz": round(f0, 1), "harmonic_hz": [round(k * f0) for k in range(1, n + 1)], "level_db_re_strongest": [round(float(v), 1) for v in amp]}


def lpc_bicim(a, b):
    """LPC (11025 Hz, 12. derece) ile F1-F3 ortancalari. f0 ~ 330-350 Hz oldugundan tepeler harmoniklere kilitlenir:
    yalniz kaba gosterge."""
    seg = x[int(a * fs):int(b * fs)]
    y = resample_poly(seg, 1, 4)                      # 11025 Hz
    y = np.append(y[0], y[1:] - 0.97 * y[:-1])
    sr = fs / 4; n = int(0.03 * sr); hop = int(0.005 * sr); F = []
    for i in range(0, max(1, len(y) - n + 1), hop):
        fr = y[i:i + n]
        if len(fr) < n or np.sum(fr ** 2) < 1e-9:
            continue
        try:
            A_ = librosa.lpc(fr * np.hamming(n), order=12)
        except Exception:
            continue
        r = np.roots(A_); r = r[np.imag(r) > 0]
        fr_ = np.angle(r) * sr / (2 * np.pi); bw = -sr / np.pi * np.log(np.abs(r) + 1e-12)
        ok = sorted(fr_[(fr_ > 200) & (bw < 500)])
        if len(ok) >= 2:
            F.append((ok + [np.nan, np.nan])[:3])
    if not F:
        return None
    F = np.array(F, dtype=float)
    return [None if np.all(np.isnan(F[:, k])) else int(round(float(np.nanmedian(F[:, k])))) for k in range(3)]


ZARF_HZ = [350, 700, 1050, 1400, 1750, 2100, 2450, 2800]


def zarf_ornek(a, b):
    """Spektral zarfin sabit frekanslardaki ornekleri (dB, en gucluye gore; taban -35 dB). f0 330-440 Hz oldugu icin zarf
    yalniz harmoniklerde gorunur: harmonik tepeleri (H1..H10) frekans ekseninde dogrusal aradegerlenir."""
    h = harmonikler(a, b, 10)
    if h is None:
        return None, None
    fr = np.array(h["harmonic_hz"], float); lv = np.maximum(np.array(h["level_db_re_strongest"], float), -35.0)
    e = np.interp(ZARF_HZ, fr, lv)
    return e - e.max(), float(69 + 12 * np.log2(h["f0_hz"] / 440.0))


class ZarfKarsilastir:
    """Ayni sarkicinin a / ı / i / e / l / n seslerinin spektral zarflari (baska hecelerden); karsilastirma yalniz
    PERDESI YAKIN (+-1.5 yarim ses) orneklerle yapilir, cunku bu f0'da zarfin ornekleme noktalari perdeye baglidir."""

    def __init__(self, ornekler):
        self.orn = {}
        for ad, araliklar in ornekler.items():
            L = []
            for a, b in araliklar:
                if b - a < 0.025:
                    a, b = (a + b) / 2 - 0.0125, (a + b) / 2 + 0.0125
                e, m = zarf_ornek(a, b)
                if e is not None:
                    L.append((m, e))
            self.orn[ad] = L

    def uzaklik(self, a, b, pay=1.5):
        e, m = zarf_ornek(a, b)
        out = {}
        if e is None:
            return out, None
        for ad, L in self.orn.items():
            yakin = [q for (mm, q) in L if abs(mm - m) <= pay]
            if len(yakin) >= 2:
                ort = np.mean(yakin, axis=0)
                out[ad] = {"rms_db": round(float(np.sqrt(np.mean((e - ort) ** 2))), 1), "references_used": len(yakin)}
        en = min(out, key=lambda k_: out[k_]["rms_db"]) if out else None
        return out, en

    def sinif_zarfi(self, m, pay=1.5):
        out = {}
        for ad, L in self.orn.items():
            yakin = [q for (mm, q) in L if abs(mm - m) <= pay]
            if len(yakin) >= 2:
                out[ad] = {"n": len(yakin), "envelope_db": [round(float(v), 1) for v in np.mean(yakin, axis=0)]}
        return out


def ornek_topla(verses_ic, haric=None):
    """Hece tablosundan sinif ornekleri. verses_ic: [(v, bolum, hece sozlugu), ...]; haric: (v, bolum, word_i) atlanir.
    Unluler: genizsi / l ile baslamayan ve kodasiz hecelerin cekirdeginin orta yarisi; ayrica "var"in unlusu (ilk 100 ms).
    l, n: unlu | l / n sinirinin (cukur) +-15 ms cevresi."""
    orn = {k: [] for k in "aıiel"}; orn["n"] = []
    for i, (v, ad, h) in enumerate(verses_ic):
        if haric and (v, ad, h["word_i"]) == haric:
            continue
        cs, ce = h.get("cs2", h["cs"]), h.get("ce2", h["ce"])
        if h["vowel"] in "aıie" and not h["coda"] and h["onset"] not in ("n", "l", "m") and ce - cs >= 0.05:
            q = (ce - cs) / 4
            orn[h["vowel"]].append((cs + q, ce - q))
        elif h["text"] == "var" and ce - cs >= 0.12:
            orn["a"].append((cs + 0.02, cs + 0.10))
        eb = h.get("end_boundary")
        if eb and eb["kind"] == "dip" and eb["consonants"] in ("|l", "|n"):
            orn[eb["consonants"][1]].append((eb["t"] - 0.015, eb["t"] + 0.015))
    return orn


def iki_unlu_tepesi(a, b, dip_db=8.0, min_tepe=0.04, min_cukur=0.03):
    """FAZLA HECE DEDEKTORU (yazimdan bagimsiz): tek hecelik bir aralikta IKI ayri unlu tepesi var mi?
    "Unlu gibi" kare: sesli-guclu (100-1000 Hz zarfi, aralik tepesinin 12 dB icinde) VE 1-3.4 kHz zarfi araligin en yuksek
    degerinin 10 dB icinde VE 4-12 kHz zarfi > -55 dBFS (genizsilerde bu bant -55 .. -68 dBFS'e duser, unlulerde -35 .. -50).
    En az 40 ms suren iki boyle kosu, arada en az 30 ms suren ve 1-3.4 kHz bandi en az 8 dB dusen SESLI bir bolgeyle
    ayriliyorsa (unlu - akici unsuz - unlu) aralikta iki cekirdek vardir."""
    ia, ib = fi(a), fi(b)
    f2 = F2B[ia:ib + 1]; lo = ELOW8[ia:ib + 1]; hi = EHI[ia:ib + 1]
    ses = lo > lo.max() - 12.0
    if ses.sum() * DT < 0.1:
        return None
    mx = f2[ses].max()
    ust = ses & (f2 >= mx - 10.0) & (hi > -55.0)
    kos = []; i = 0; n = len(ust)
    while i < n:
        if ust[i]:
            j = i
            while j < n and ust[j]:
                j += 1
            if (j - i) * DT >= min_tepe:
                kos.append((i, j))
            i = j
        else:
            i += 1
    for (a1, b1), (a2, b2) in zip(kos[:-1], kos[1:]):
        ara = f2[b1:a2]
        if len(ara) * DT >= min_cukur and np.all(ses[b1:a2]) and min(f2[a1:b1].max(), f2[a2:b2].max()) - ara.min() >= dip_db:
            return {"first_vowel_peak": [round((ia + a1) * DT, 4), round((ia + b1) * DT, 4)],
                    "second_vowel_peak": [round((ia + a2) * DT, 4), round((ia + b2) * DT, 4)],
                    "dip_between_db": round(float(min(f2[a1:b1].max(), f2[a2:b2].max()) - ara.min()), 1),
                    "dip_between_ms": round(len(ara) * DT * 1000, 1)}
    return None


def otum_baslangici(a_lim, nuc):
    """nuc'ten geriye: 100-1000 Hz zarfinin (tepe - 12 dB) altina inip >= 20 ms orada kaldigi yer -> otumun basladigi an."""
    ipk = fi(nuc); a = fi(a_lim)
    pk = float(ELOW8[max(a, ipk - fi(0.03)):ipk + fi(0.03) + 1].max())
    i = ipk; n20 = fi(0.02)
    while i > a + 1 and not (ELOW8[i] <= pk - 12.0 and np.all(ELOW8[max(a, i - n20):i + 1] <= pk - 12.0)):
        i -= 1
    return (i + 1) * DT


def unsuz_l_suresi(L, R):
    """Unsuz + l + unlu baglaminda (nek|le, roz|la ...): otum baslangicindan unlunun F2 bandinin yukselisine kadar gecen sure."""
    von = otum_baslangici(L["nuc"], R["nuc"])
    ia, ib = fi(von), fi(R["nuc"] + 0.03)
    seg = F2B[ia:ib + 1]
    tepe = float(seg.max()); taban = float(seg[:max(2, fi(0.03))].min())
    esik = (tepe + taban) / 2
    j = int(np.argmax(seg))
    while j > 0 and seg[j - 1] >= esik:
        j -= 1
    return {"voicing_onset": von, "vowel_onset": (ia + j) * DT, "sonorant_ms": ((ia + j) * DT - von) * 1000,
            "f2_rise_db": tepe - taban}


def atlari_olc(a_h, ti_h, la_h, ri_h, var_h, sung):
    """Dort cekirdekli yazima gore bulunmus heceler (a, tı, la, rı) -> isaret noktalari, sureler, kesip atma araligi."""
    # 1) 'a' unlusunun bittigi an (t kapanisinin basi)
    ipk = fi(a_h["nuc"]); pk = float(ELOW8[fi(a_h["cs"]):fi(a_h["ce"]) + 1].max())
    i = ipk
    while i < fi(ti_h["nuc"]) and ELOW8[i] > pk - 15.0:
        i += 1
    a_bit = i * DT
    # 2) otumun yeniden basladigi an (t'nin surtunmeli salinimi bittikten sonra)
    von = otum_baslangici(a_bit, ti_h["nuc"])
    # 3) t patlamasinin basi: [a_bit, von] icinde 4-12 kHz zarfinin (tepe - 10 dB) ustune ilk ciktigi an
    ia, ib = fi(a_bit), fi(von)
    hi = EHI[ia:ib + 1]; j = int(np.argmax(hi >= hi.max() - 10.0)); pat = (ia + j) * DT
    # son surtunme karesi
    son = ib
    while son > ia and EHI[son] < hi.max() - 10.0:
        son -= 1
    sur_bit = (son + 1) * DT
    # 4) sessiz an (salinim ile otum arasi): [von - 25 ms, von + 2 ms] icinde 5 ms RMS'in en dusugu
    qa, qb = fi(von - 0.025), fi(von + 0.002)
    sessiz = (qa + int(np.argmin(R5[qa:qb + 1]))) * DT
    # 5) F2 bandi: ek unlunun tepesi, koyu bolumun duzeyi, "la"nin a'sinin tepesi
    i1 = fi(von); i2 = fi(la_h["nuc"] + 0.03)
    f2 = F2B[i1:i2 + 1]
    k1 = int(np.argmax(f2[:fi(0.09)])); P1 = float(f2[k1])
    ka = fi(la_h["t_exp"] - 0.03) - i1
    k2 = ka + int(np.argmax(f2[ka:])); P2 = float(f2[k2])
    orta = f2[k1:k2 + 1]
    Lmed = float(np.percentile(orta, 20))
    # ek unlunun bittigi an: tepeden sonra F2 bandinin (P1 + Lmed) / 2 altina ilk indigi an
    e1 = (P1 + Lmed) / 2; j = k1
    while j < k2 and f2[j] >= e1:
        j += 1
    ek_bit = (i1 + j) * DT
    # "la"nin a'sinin basladigi an: tepeden geriye F2 bandinin (P2 + Lmed) / 2 altina ilk indigi an
    e2 = (P2 + Lmed) / 2; j = k2
    while j > k1 and f2[j - 1] >= e2:
        j -= 1
    a2_bas = (i1 + j) * DT
    # duzeyler
    lv = lambda a, b: float(10 * np.log10(np.mean(10 ** (R5[fi(a):fi(b) + 1] / 10))))
    pm = lambda a, b: (lambda m: None if m.sum() < 2 else float(np.median(midi(f0h[m]))))((th >= a) & (th < b) & (f0h > 0))
    return {"a_end": a_bit, "t_burst_onset": pat, "t_frication_end": sur_bit, "voicing_onset": von, "quiet_instant": sessiz,
            "quiet_level_dbfs": float(R5[fi(sessiz)]),
            "extra_vowel": {"start": von, "end": ek_bit, "duration_ms": (ek_bit - von) * 1000, "level_dbfs": lv(von, ek_bit),
                            "peak_dbfs": float(R5[fi(von):fi(ek_bit) + 1].max()), "f0_midi": pm(von, ek_bit), "f2_band_peak_db": P1},
            "dark_l": {"start": ek_bit, "end": a2_bas, "duration_ms": (a2_bas - ek_bit) * 1000, "level_dbfs": lv(ek_bit, a2_bas),
                       "f0_midi": pm(ek_bit, a2_bas), "f2_band_level_db": Lmed},
            "second_a": {"onset": a2_bas, "f2_band_peak_db": P2, "f0_midi": pm(a2_bas, a2_bas + 0.08)},
            "t_closure_ms": (pat - a_bit) * 1000, "t_frication_ms": (sur_bit - pat) * 1000,
            "voiced_stretch_before_second_a_ms": (a2_bas - von) * 1000}
