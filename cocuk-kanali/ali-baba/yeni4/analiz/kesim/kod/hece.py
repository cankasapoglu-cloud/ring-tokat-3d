#!/usr/bin/env python3
"""Hece cekirdekleri ve hece SINIRLARI (yalniz sesten).  yeni3/analiz/kesim/kod/kesim.py'deki sinir_bul'un
v2_2 sozlerine gore genisletilmis hali.

CEKIRDEK: izgara.py'nin bekledigi unlu baslangicinin cevresindeki pencerede ([t_exp - 40 ms, sonraki t_exp - 40 ms])
          sesli karelerde 300-3400 Hz zarfinin (30 ms) tepesi; cevresinde tepe - 6 dB ustunde kalan sesli bolge.

SINIR (ardisik iki cekirdek arasinda; kind / where):
  dip / deepest               : 300-3400 Hz zarfinda (12 ms) >= 3 dB cukur; cukurun ortasi (unsuzun ortasi / kapanis).
  dip / last_low              : koda + onset varsa sonraki hecenin onset'inden onceki SON dusuk bolge.
  dip / closure_after_sonorant: koda n, m, l, r + patlamali onset (nın|bir, ğin|de, bir|çift, ör|dek, rır|çift):
                                sonraki unluden onceki 100 ms icindeki tam-bant (5 ms) en dusuk an = kapanis.
  dip / voicing_onset         : otumsuz koda (t, k, f ... , z) + akici onset (çift|li, nek|le, roz|la): patlama /
                                surtunme bittikten sonra otumun basladigi an (100-1000 Hz, 8 ms zarf, tepe - 12 dB).
  dip / fricative_onset       : unlu + 's' (di|si): onceki unlunun bittigi an (100-1000 Hz zarfi tepe - 15 dB).
  spectral / nasal_release    : genizsi koda + akici onset (yun|la): genizsinin bittigi an (pozitif spektral aki tepesi).
  spectral / glide_*          : 'y' kaymasi (ko|yun, di|ye): F2 tepesi ya da iki parcali spektral bolme.
  spectral / two_segment_fit  : cukur yok ama unluler farkli: log-mel spektrumu iki sabit parcaya en iyi bolen an.
  pitch_step                  : cukur da spektral degisim de yok (ayni unlu, 'ğ': li|ği) ama perde degisiyor:
                                f0'in iki hecenin perdelerinin ortasindan gectigi an (nota degisimi).
  grid (FLAG)                 : hicbir akustik isaret yok (ayni unlu, ayni perde: li|ğin): sinir, sonraki hecenin
                                vurus izgarasindaki beklenen yerine konur.  -> kelime FLAG edilir.
"""
import numpy as np
from scipy.signal import find_peaks
from zarf import (z, t, DT, fi, E12, E30, ELOW, ELOW8, F2B, EHI, R5, FLX, FLXP, LMEL, th, f0h, f0s, FP, midi, db_ham)

STOP = set("bdgptkç"); OTUMSUZ_KODA = set("tkpfsçzh"); AKICI = set("lrnmyv"); GENIZ = set("nm")
OTUMLU_STOP = set("bdg"); SONOR_KODA = set("nmlr"); SURTUNMELI = set("sf"); ARKA_UNLU = set("aıou")
MIN_HECE = 0.06
SUNG = None          # kesim.py atar (soylenen RMS, dBFS)
VOIG = None          # kesim.py atar: 2 ms izgarada "sesli ve yeterince guclu" maskesi


def cekirdek(h, w0, w1):
    """h hecesinin cekirdegi [w0, w1] penceresinde. Donus: (tepe_ani, cekirdek_bas, cekirdek_bit) saniye."""
    ia, ib = fi(w0), fi(w1)
    seg = np.where(VOIG[ia:ib + 1], E30[ia:ib + 1], -200.0)
    # tepe: beklenen unlu baslangicindan sonraki ilk 200 ms icinde (pencereyi asmadan)
    pa = max(ia, fi(h["t_exp"] + 0.01)); pb = min(ib, fi(h["t_exp"] + 0.20))
    if pb <= pa or seg[pa - ia:pb - ia + 1].max() < -150:
        pa, pb = ia, ib
    ip = pa + int(np.argmax(seg[pa - ia:pb - ia + 1])); tepe = E30[ip]
    L = ip
    while L > ia and E30[L - 1] > tepe - 6 and VOIG[L - 1]:
        L -= 1
    R = ip
    while R < ib and E30[R + 1] > tepe - 6 and VOIG[R + 1]:
        R += 1
    return ip * DT, L * DT, (R + 1) * DT


def cukur_merkezi(E, i, a, b, taban, pay=2.0):
    """i karesi cevresinde (tabana kirpilmis) E < E[i]+pay olan bitisik pencerenin ortasi ([a,b] icinde)."""
    esik = max(E[i], taban) + pay
    L = i
    while L > a and E[L - 1] < esik:
        L -= 1
    R = i
    while R < b and E[R + 1] < esik:
        R += 1
    return (L + R) // 2, (R - L + 1) * DT


def iki_parca(a, b, enaz=0.03):
    """[a,b] araligini log-mel spektrumu iki sabit parcaya en iyi bolen an. Donus: (zaman, aciklanan varyans orani)."""
    ia, ib = fi(a), fi(b)
    X = LMEL[:, ia:ib + 1].T
    n = len(X); m = max(2, int(enaz / DT))
    if n < 2 * m + 2:
        return (a + b) / 2, 0.0
    top = ((X - X.mean(0)) ** 2).sum()
    c1 = np.cumsum(X, 0); c2 = np.cumsum(X ** 2, 0)
    en = (None, np.inf)
    for k in range(m, n - m):
        sl = c2[k - 1].sum() - (c1[k - 1] ** 2).sum() / k
        sr = (c2[-1] - c2[k - 1]).sum() - ((c1[-1] - c1[k - 1]) ** 2).sum() / (n - k)
        if sl + sr < en[1]:
            en = (k, sl + sr)
    return (ia + en[0]) * DT, float(1 - en[1] / (top + 1e-12))


def perde_ort(a, b):
    m = (th >= a) & (th < b) & (f0h > 0)
    if m.sum() < 3:
        return None
    return float(np.median(midi(f0h[m])))


def perde_adimi(L, R):
    """Iki cekirdegin perdeleri >= 0.7 yarim ses farkliysa, f0'in orta degerden gectigi an. Donus: (t, pL, pR) | None"""
    # plato perdeleri: cekirdeklerin sinira UZAK yarilari (gecis kareleri disarida kalsin)
    pL = perde_ort(L["cs"], (L["cs"] + L["ce"]) / 2 + 0.01); pR = perde_ort((R["cs"] + R["ce"]) / 2 - 0.01, R["ce"])
    if pL is None or pR is None or abs(pL - pR) < 0.7:
        return None
    orta = (pL + pR) / 2
    m = np.where((th >= L["nuc"]) & (th <= R["ce"]) & (f0h > 0))[0]
    if len(m) < 4:
        return None
    mm = midi(f0h[m]); s = np.sign(pR - pL)
    # son gecis: bundan sonra hep R tarafinda kalinan ilk kare
    taraf = (mm - orta) * s > 0
    k = len(taraf) - 1
    if not taraf[k]:
        return None
    while k > 0 and taraf[k - 1]:
        k -= 1
    if k == 0:
        return None
    a_, b_ = mm[k - 1], mm[k]
    tt = th[m[k - 1]] + (orta - a_) / (b_ - a_) * (th[m[k]] - th[m[k - 1]]) if b_ != a_ else th[m[k]]
    return float(tt), pL, pR


def sinir_bul(L, R, lim_a=None, lim_b=None):
    """L / R: ardisik iki hece (nuc, cs, ce, onset, vowel, coda, t_exp). Donus: sinir sozlugu."""
    C = L["coda"]; O = R["onset"]
    a, b = fi(L["nuc"]), fi(R["nuc"])
    Lcs, Lce, Rcs, Rce = L["cs"], L["ce"], R["cs"], R["ce"]
    if lim_a is not None:
        a = max(a, fi(lim_a))
    if lim_b is not None:
        b = min(b, fi(lim_b))
    unsuz = C + "|" + O
    out = {"consonants": unsuz}
    if b <= a + 2:
        out.update({"t": (a + b) / 2 * DT, "kind": "grid", "where": "search_window_collapsed", "depth_db": None})
        return out
    sol_a = fi(Lcs); sag_b = fi(Rce)
    tepeL = float(E12[sol_a:fi(Lce) + 1].max()); tepeR = float(E12[fi(Rcs):sag_b + 1].max())
    taban = min(tepeL, tepeR) - 35.0
    Ek = lambda i: max(float(E12[i]), taban)
    iR = a + int(np.argmin(E12[a:b + 1])); ER = Ek(iR)
    derin = lambda i0: float(min(E12[sol_a:i0 + 1].max(), E12[i0:sag_b + 1].max()) - E12[i0])
    dR = derin(iR)
    out["deepest_dip_db"] = round(dR, 1)

    def don(tt, kind, where, **ek):
        out.update({"t": float(tt), "kind": kind, "where": where}); out.update(ek)
        return out

    def izgara():
        tt = min(max(R["t_exp"], (a + 2) * DT), (b - 2) * DT)
        return don(tt, "grid", "expected_onset_on_beat_grid", depth_db=None)

    def yakin(tt):
        """Zayif kanitli sinir turleri (spektral bolme, perde adimi) yalniz izgaradaki beklenen yerin +-70 ms yakininda
        kabul edilir (kayitta butun heceler izgaraya +-45 ms icinde oturuyor)."""
        return a * DT < tt < b * DT and abs(tt - R["t_exp"]) <= 0.07

    # ---- 'ğ' (unsuz yok sayilir) : li|ği, li|ğin, ba|ğı
    if O == "ğ" and not C:
        if L["vowel"] != R["vowel"]:
            tb, kaz = iki_parca(Lcs + 0.01, Rce - 0.01)
            if kaz >= 0.30 and (tb - Lcs) >= 0.04 and (Rce - tb) >= 0.04 and yakin(tb):
                return don(tb, "spectral", "two_segment_fit", spectral_gain=round(kaz, 2), depth_db=None)
        ps = perde_adimi(L, R)
        if ps and yakin(ps[0]):
            return don(ps[0], "pitch_step", "f0_crosses_midpoint", pitch_left_midi=round(ps[1], 2),
                       pitch_right_midi=round(ps[2], 2), depth_db=None)
        return izgara()
    # ---- unlu | unlu (kelime sinirinda: de|i, de|a, de|ö, de|A)
    if not O and not C:
        if dR >= 4.0:
            ic, gen = cukur_merkezi(E12, iR, a, b, taban)
            return don(ic * DT, "dip", "glottal", depth_db=round(dR, 1), low_window_ms=round(gen * 1000, 1))
        tb, kaz = iki_parca(Lcs + 0.01, Rce - 0.01)
        if kaz >= 0.30 and yakin(tb):
            return don(tb, "spectral", "two_segment_fit", spectral_gain=round(kaz, 2), depth_db=round(dR, 1))
        ps = perde_adimi(L, R)
        if ps and yakin(ps[0]):
            return don(ps[0], "pitch_step", "f0_crosses_midpoint", pitch_left_midi=round(ps[1], 2),
                       pitch_right_midi=round(ps[2], 2), depth_db=round(dR, 1))
        return izgara()
    koda_son = C[-1] if C else ""; onset_ilk = O[0] if O else ""
    # ---- 'y' kaymasi (ko|yun, di|ye)
    if onset_ilk == "y" and not C:
        if L["vowel"] in ARKA_UNLU:
            f2 = np.convolve(10 * np.log10(z["b_f2"] + 1e-12), np.hanning(9) / np.hanning(9).sum(), "same")
            ip = a + int(np.argmax(f2[a:b + 1]))
            cik = float(f2[ip] - max(f2[a:ip + 1].min(), f2[ip:b + 1].min()))
            if cik >= 3.0 and a < ip < b and yakin(ip * DT):
                return don(ip * DT, "spectral", "glide_f2_peak", f2_peak_db=round(cik, 1), depth_db=None)
        tb, kaz = iki_parca(Lcs + 0.03, Rce - 0.02)
        if kaz >= 0.25 and (tb - Lcs) >= 0.05 and (Rce - tb) >= 0.05 and yakin(tb):
            return don(tb, "spectral", "glide_two_segment_fit", spectral_gain=round(kaz, 2), depth_db=None)
        ps = perde_adimi(L, R)
        if ps and yakin(ps[0]):
            return don(ps[0], "pitch_step", "f0_crosses_midpoint", pitch_left_midi=round(ps[1], 2),
                       pitch_right_midi=round(ps[2], 2), depth_db=None)
        return izgara()
    # Asagidaki kurallarda arama penceresi sonraki hecenin BEKLENEN unlu baslangicina (izgara) ve olculen tepesine
    # gore kurulur; cekirdek baslangici (cs) kullanilmaz, cunku guclu genizsi / akici unsuzler cekirdege karisabiliyor.
    w_lo = max(a, fi(R["t_exp"] - 0.10)); w_hi = min(b, fi(R["nuc"]))
    # ---- genizsi koda + akici onset (yun|la): genizsinin bittigi an
    if koda_son in GENIZ and onset_ilk in AKICI:
        if w_hi > w_lo + 2:
            ip = w_lo + int(np.argmax(FLXP[w_lo:w_hi + 1]))
            ftab = float(np.median(FLXP[sol_a:sag_b + 1]))
            oran = float(FLXP[ip] / (ftab + 1e-9))
            f2art = float(F2B[min(ip + fi(0.02), b)] - F2B[max(ip - fi(0.02), a)])
            if (oran >= 2.5 and FLXP[ip] >= 15.0) or f2art >= 6.0:
                return don(ip * DT, "spectral", "nasal_release", flux_ratio=round(oran, 2), f2_band_rise_db=round(f2art, 1), depth_db=None)
    # ---- akici / genizsi koda + patlamali onset: kapanis
    if koda_son in SONOR_KODA and onset_ilk in STOP:
        if w_hi > w_lo + 2:
            if onset_ilk in OTUMLU_STOP:
                # b, d, g: kapanis cok kisa (5-20 ms) ve unluye bitisik; unlu izgaraya +-30 ms icinde oturuyor ->
                # yalniz beklenen unlu baslangicinin [-50, +30] ms cevresinde aranir (genizsinin ortasindaki daha
                # erken bir cukur ya da unlunun icindeki dalgalanma degil)
                q_lo = max(w_lo, fi(R["t_exp"] - 0.05)); q_hi = min(w_hi, fi(R["t_exp"] + 0.03))
                if q_hi <= q_lo:
                    q_lo, q_hi = w_lo, w_hi
                i0 = q_lo + int(np.argmin(R5[q_lo:q_hi + 1]))
            else:
                i0 = w_lo + int(np.argmin(R5[w_lo:w_hi + 1]))
            d5 = float(min(R5[sol_a:i0 + 1].max(), R5[i0:sag_b + 1].max()) - R5[i0])
            if d5 >= 2.0:
                tb5 = min(R5[sol_a:fi(Lce) + 1].max(), R5[fi(Rcs):sag_b + 1].max()) - 35.0
                ic, gen = cukur_merkezi(R5, i0, w_lo, w_hi, tb5)
                return don(ic * DT, "dip", "closure_after_sonorant", depth_db=round(d5, 1), low_window_ms=round(gen * 1000, 1))
    # ---- otumsuz koda + akici onset / unlu: otum baslangici
    if koda_son in OTUMSUZ_KODA and (not O or onset_ilk in AKICI):
        ipk = fi(R["nuc"])
        pk = float(ELOW8[max(a, ipk - fi(0.03)):min(sag_b, ipk + fi(0.03)) + 1].max())
        i = ipk; n20 = fi(0.02)
        # geriye dogru: zarfin (tepe - 12 dB) altina inip en az 20 ms orada kaldigi ilk yer (l ile unlu arasindaki
        # 10 ms'lik kisa cukurlar atlanir -> akici unsuz sonraki hecede kalir)
        while i > a + 1 and not (ELOW8[i] <= pk - 12.0 and np.all(ELOW8[max(a, i - n20):i + 1] <= pk - 12.0)):
            i -= 1
        lo = max(a + 1, i - fi(0.012)); hi = min(b - 1, i + 1)
        if hi > lo:
            i0 = lo + int(np.argmin(R5[lo:hi + 1]))
            return don(i0 * DT, "dip", "voicing_onset", depth_db=round(derin(i0), 1), level_dbfs=round(float(R5[i0]), 1))
    # ---- unlu + 's' / 'f': onceki unlunun bittigi an
    if not C and onset_ilk in SURTUNMELI:
        ipk = fi(L["nuc"])
        pk = float(ELOW8[sol_a:fi(Lce) + 1].max())
        i = ipk
        while i < b - 1 and ELOW8[i] > pk - 15.0:
            i += 1
        return don(i * DT, "dip", "fricative_onset", depth_db=round(derin(i), 1))
    # ---- genel: enerji cukuru (yeni3 mantigi)
    pay = float(np.clip(0.5 * dR, 1.0, 6.0))
    dusuk = np.array([Ek(i) <= ER + pay for i in range(a, b + 1)])
    j1 = int(np.max(np.where(dusuk)[0])); j0 = j1
    while j0 > 0 and dusuk[j0 - 1]:
        j0 -= 1
    iS = a + j0 + int(np.argmin(E12[a + j0:a + j1 + 1]))
    adaylar = []
    if C and iS != iR:
        adaylar.append((iS, a + j0, a + j1, "last_low"))
    adaylar.append((iR, a, b, "deepest"))
    for i0, lo, hi, yer in adaylar:
        d = derin(i0)
        if d >= 3.0:
            ic, gen = cukur_merkezi(E12, i0, lo, hi, taban)
            return don(ic * DT, "dip", yer, depth_db=round(d, 1), low_window_ms=round(gen * 1000, 1))
    out["depth_db"] = round(dR, 1)
    if L["vowel"] != R["vowel"] and koda_son not in GENIZ:
        tb, kaz = iki_parca(Lcs + 0.01, Rce - 0.01)
        if kaz >= 0.30 and (tb - Lcs) >= 0.04 and (Rce - tb) >= 0.04 and yakin(tb):
            return don(tb, "spectral", "two_segment_fit", spectral_gain=round(kaz, 2))
    lo, hi = w_lo, w_hi
    if hi > lo + 2:
        ip = lo + int(np.argmax(FLX[lo:hi + 1]))
        ftab = float(np.median(np.concatenate([FLX[sol_a:fi(Lce) + 1], FLX[fi(Rcs):sag_b + 1]])))
        oran = float(FLX[ip] / (ftab + 1e-9))
        if oran >= 2.0 and FLX[ip] >= 20.0:
            return don(ip * DT, "spectral", "flux_peak", flux_ratio=round(oran, 2))
    ps = perde_adimi(L, R)
    if ps and yakin(ps[0]):
        return don(ps[0], "pitch_step", "f0_crosses_midpoint", pitch_left_midi=round(ps[1], 2), pitch_right_midi=round(ps[2], 2))
    return izgara()


def parca_sinirlari(heceler, bas, bit):
    """Bir parcanin (L1 / L2 / diye+L4) heceleri icin cekirdekler + sinirlar. heceler yerinde guncellenir."""
    n = len(heceler)
    for i, h in enumerate(heceler):
        w0 = bas if i == 0 else max(bas, h["t_exp"] - 0.04)
        w1 = bit if i == n - 1 else min(bit, heceler[i + 1]["t_exp"] - 0.04)
        h["nuc"], h["cs"], h["ce"] = cekirdek(h, w0, w1)
        h["win"] = (w0, w1)
    sin = [sinir_bul(heceler[i], heceler[i + 1]) for i in range(n - 1)]
    guven = lambda s_: (s_.get("depth_db") or 0.0) if s_["kind"] == "dip" else 0.0
    for _tur in range(4):
        degisti = False
        for i in range(len(sin) - 1):
            if sin[i + 1]["t"] - sin[i]["t"] < MIN_HECE:
                if guven(sin[i]) <= guven(sin[i + 1]):
                    yeni = sinir_bul(heceler[i], heceler[i + 1], lim_b=sin[i + 1]["t"] - MIN_HECE)
                    yeni["conflict_resolved_with"] = "next"; sin[i] = yeni
                else:
                    yeni = sinir_bul(heceler[i + 1], heceler[i + 2], lim_a=sin[i]["t"] + MIN_HECE)
                    yeni["conflict_resolved_with"] = "previous"; sin[i + 1] = yeni
                degisti = True
        if not degisti:
            break
    kenar = [bas] + [s["t"] for s in sin] + [bit]
    assert all(b_ > a_ for a_, b_ in zip(kenar[:-1], kenar[1:])), kenar
    for i, h in enumerate(heceler):
        h["start"] = kenar[i]; h["end"] = kenar[i + 1]
        h["end_boundary"] = sin[i] if i < len(sin) else None
    return sin


# ------------------------------------------------------------------ kor cekirdek sayimi (izgara KULLANMADAN)
def kor_cekirdek(a, b):
    """Gorev tanimindaki kor yontem: kelime araliginda yumusatilmis sesli-enerji zarfinin tepeleri = cekirdekler;
    aralarindaki en dusuk nokta = sinir. Donus: (tepe zamanlari, sinir zamanlari)."""
    ia, ib = fi(a), fi(b)
    EV = np.where(VOIG[ia:ib + 1], E30[ia:ib + 1], -120.0)
    if len(EV) < 5 or EV.max() < -100:
        return [], []
    taban = EV.max() - 40.0
    pad = np.concatenate([[taban], np.maximum(EV, taban), [taban]])
    pk, _ = find_peaks(pad, prominence=3.0, distance=max(1, int(0.05 / DT)))
    pk = pk - 1
    ok = [p for p in pk if EV[p] >= EV.max() - 15.0]
    tepeler = [(ia + p) * DT for p in ok]
    sinirlar = [(ia + p + int(np.argmin(E12[ia + p:ia + q + 1]))) * DT for p, q in zip(ok[:-1], ok[1:])]
    return tepeler, sinirlar
