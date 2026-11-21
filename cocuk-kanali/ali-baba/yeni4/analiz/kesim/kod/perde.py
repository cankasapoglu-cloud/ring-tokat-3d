#!/usr/bin/env python3
"""Hece basina perde: cekirdek ortancasi, sesli orani, bas / orta / son perdesi (kayma) ve hece icindeki NOTALAR.
f0 = pyworld harvest (5 ms); capraz kontrol = dio + stonemask.
Kapi: kare sesli (harvest) VE 100-1000 Hz bandinin 8 ms zarfi > soylenen RMS - 11 dB.  (Ilk denemede kapi "10 ms RMS >
soylenen - 25 dB" idi: harvest 'çift'in f / t gurultusunde de perde buldugu icin sahte notalar cikti; alcak bant
kapisi surtunme ve patlamalari disarida birakir.)

NOTA (plato) tanimi: 25 ms ortanca suzgecinden gecmis f0 (MIDI) 20 ms'de 0.35 yarim sesten az degisiyorsa kare
"duragan"dir; ayni yarim sese yuvarlanan ardisik duragan kareler (<= 10 ms bosluk) bir platodur; >= 40 ms suren
platolar nota sayilir. Hecenin notalari heceyi BOLER: ilk nota hecenin basinda baslar, ardisik iki nota arasindaki
sinir iki platonun arasindaki gecisin ortasidir, son nota hecenin sonunda biter."""
import numpy as np
from scipy.signal import medfilt
from zarf import th, f0h, f0s, FP, midi, db_ham, DT, fi, E30, ELOW8, t, nota_adi

KAPI_DB = 11.0   # kapi: alcak bant zarfi > soylenen RMS - 11 dB
SUNG = None      # kesim.py atar
GATE = None      # 5 ms izgarada kapi (sesli & guclu)


def kur(sung):
    global SUNG, GATE
    SUNG = sung
    lvl = np.interp(th, t, ELOW8)
    GATE = (f0h > 0) & (lvl > sung - KAPI_DB)


def kareler(a, b):
    """[a,b) araligindaki 5 ms kareleri: (indeksler, kapili maske)"""
    i0 = int(np.ceil(a / FP - 1e-9)); i1 = int(np.ceil(b / FP - 1e-9))
    idx = np.arange(i0, max(i0, i1))
    return idx, GATE[idx]


def ortanca(a, b, f0=None):
    idx, g = kareler(a, b)
    f = (f0h if f0 is None else f0)[idx]
    m = g & (f > 0)
    if m.sum() == 0:
        return None
    return float(np.median(midi(f[m])))


def cekirdek_ic(a, b, VOIG):
    """Hecenin [a,b] icindeki cekirdegi: sesli karelerde E30 tepesi ve cevresinde tepe - 6 dB ustunde kalan sesli bolge."""
    ia, ib = fi(a), max(fi(a) + 1, fi(b) - 1)
    seg = np.where(VOIG[ia:ib + 1], E30[ia:ib + 1], -200.0)
    ip = ia + int(np.argmax(seg)); tepe = E30[ip]
    L = ip
    while L > ia and E30[L - 1] > tepe - 6 and VOIG[L - 1]:
        L -= 1
    R = ip
    while R < ib and E30[R + 1] > tepe - 6 and VOIG[R + 1]:
        R += 1
    return ip * DT, L * DT, (R + 1) * DT


def platolar(a, b):
    """[a,b) icindeki nota platolari: [(bas, bit, ortanca_midi, kare_sayisi)]"""
    idx, g = kareler(a, b)
    if g.sum() < 4:
        return []
    out = []
    # bitisik kapili kosular
    k = 0; n = len(idx)
    while k < n:
        if not g[k]:
            k += 1; continue
        j = k
        while j < n and g[j]:
            j += 1
        m = midi(f0h[idx[k:j]])
        if len(m) >= 5:
            mm = medfilt(m, 5)
            mm[:2] = m[:2]; mm[-2:] = m[-2:]
        else:
            mm = m.copy()
        egim = np.abs(np.concatenate([[9, 9], mm[4:] - mm[:-4], [9, 9]])) if len(mm) >= 5 else np.full(len(mm), 9.0)
        # kenar kareleri: 2 karelik fark
        if len(mm) >= 5:
            egim[0] = egim[1] = abs(mm[2] - mm[0]) * 2; egim[-1] = egim[-2] = abs(mm[-1] - mm[-3]) * 2
        dur = egim <= 0.35
        q = np.round(mm).astype(int)
        i = 0; L = len(mm)
        while i < L:
            if not dur[i]:
                i += 1; continue
            e = i; bos = 0; son = i
            while e + 1 < L and bos <= 2:
                if dur[e + 1] and q[e + 1] == q[i]:
                    son = e + 1; bos = 0
                elif dur[e + 1] and q[e + 1] != q[i]:
                    break
                else:
                    bos += 1
                e += 1
            if son - i + 1 >= 8:
                out.append((float(th[idx[k + i]]), float(th[idx[k + son]] + FP), float(np.median(m[i:son + 1])), int(son - i + 1)))
            i = son + 1
        k = j
    # ayni yarim sese yuvarlanan komsu platolari birlestir
    bir = []
    for p in out:
        if bir and round(bir[-1][2]) == round(p[2]) and p[0] - bir[-1][1] < 0.06:
            a0, b0, m0, n0 = bir[-1]
            bir[-1] = (a0, p[1], (m0 * n0 + p[2] * p[3]) / (n0 + p[3]), n0 + p[3])
        else:
            bir.append(p)
    return bir


def hece_perdesi(a, b, cs, ce):
    """Donus: sozluk (f0 ortancasi, sesli orani, bas/orta/son, notalar)."""
    idx, g = kareler(a, b)
    vr = float(g.mean()) if len(g) else 0.0
    cidx, cg = kareler(cs, ce)
    cm = midi(f0h[cidx][cg]) if cg.sum() else np.array([])
    if len(cm) == 0:
        cm = midi(f0h[idx][g]) if g.sum() else np.array([])
    out = {"voiced_ratio": round(vr, 3)}
    if len(cm) == 0:
        out.update({"f0_hz": None, "f0_midi": None, "note": None, "cents_from_note": None, "pitch_start_midi": None,
                    "pitch_mid_midi": None, "pitch_end_midi": None, "glide_semitones": None, "is_glide": False, "notes": []})
        return out
    med = float(np.median(cm))
    n = len(cm)
    if n >= 8:
        k = max(3, n // 4)
        bas = float(np.median(cm[:k])); son = float(np.median(cm[-k:])); orta = float(np.median(cm[n // 4:n - n // 4]))
    else:
        bas = orta = son = med
    dm = None
    dd = midi(f0s[cidx][cg & (f0s[cidx] > 0)]) if (cg & (f0s[cidx] > 0)).sum() else np.array([])
    if len(dd):
        dm = float(np.median(dd))
    out.update({"f0_hz": round(float(440 * 2 ** ((med - 69) / 12)), 2), "f0_midi": round(med, 2), "note": nota_adi(med),
                "cents_from_note": int(round((med - round(med)) * 100)),
                "f0_iqr_semitones": round(float(np.percentile(cm, 75) - np.percentile(cm, 25)), 2),
                "f0_dio_midi": None if dm is None else round(dm, 2),
                "pitch_start_midi": round(bas, 2), "pitch_mid_midi": round(orta, 2), "pitch_end_midi": round(son, 2),
                "pitch_start_note": nota_adi(bas), "pitch_mid_note": nota_adi(orta), "pitch_end_note": nota_adi(son),
                "glide_semitones": round(son - bas, 2), "is_glide": bool(abs(son - bas) >= 0.7)})
    pl = platolar(a, b)
    notalar = []
    if not pl:
        notalar.append({"note": nota_adi(med), "midi": round(med, 2), "start": a, "end": b, "plateau_start": None, "plateau_end": None,
                        "plateau_ms": 0, "no_plateau": True})
    else:
        kenar = [a] + [(p[1] + q[0]) / 2 for p, q in zip(pl[:-1], pl[1:])] + [b]
        for i, p in enumerate(pl):
            notalar.append({"note": nota_adi(p[2]), "midi": round(p[2], 2), "start": kenar[i], "end": kenar[i + 1],
                            "plateau_start": round(p[0], 4), "plateau_end": round(p[1], 4), "plateau_ms": int(round(p[3] * FP * 1000)),
                            "no_plateau": False})
    out["notes"] = notalar
    return out
