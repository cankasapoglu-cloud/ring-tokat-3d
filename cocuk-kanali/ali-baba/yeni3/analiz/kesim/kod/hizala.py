#!/usr/bin/env python3
"""2. adim: harf (ses birimi) duzeyinde zorlamali hizalama - disaridan model indirmeden.
Yontem: her harf 2 durumlu soldan-saga HMM, durum basina tek kosegen Gauss (MFCC+delta+seslilik, 4 ms kare).
Modeller ayni kayittan duz baslangicla (kelime araligi harflere paylastirilir) ve Viterbi yeniden
kestirimiyle ogrenilir (28 dize + kullanilmayan 2 'Dinle bak' tekrari yalniz egitim icin).
- Kelime sinirlari dinle_2_words.json zamanlarinin +-TOL yakininda kalmaya zorlanir.
- Unsuzlere sinif bazli EN UZUN SURE siniri konur (yoksa 'v', 'ğ' gibi zayif unsuzlerin modeli
  komsu unluyu yutuyor: ilk denemede gorulen hata).
Bu hizalama yalnizca UNLULERIN (hece cekirdeklerinin) kabaca yerini bulmak icindir; kesin hece
sinirlari kesim.py'de ses zarfindan (enerji cukuru / spektral degisim) bulunur.
Cikti: ara/hizalama.json  (parca -> kelime -> harf araliklari)."""
import os, json, numpy as np
from scipy.fft import dct
from ortak import K, kelimeleri_oku, kitalari_esle, ozellik, kucuk, UNLU

z = ozellik(); t2 = z["t"]; DT2 = float(t2[1] - t2[0])
ADIM = 2                                    # 2 ms kareleri 2'ser atla -> 4 ms
db2 = 20 * np.log10(z["rms"] + 1e-9)
LM = z["logmel"].astype(np.float64)
C = dct(LM, type=2, axis=0, norm="ortho")[:13]
D = 5
dl = np.zeros_like(C); dl[:, D:-D] = (C[:, 2 * D:] - C[:, :-2 * D]) / 2
voi = np.interp(t2, z["th"], (z["f0h"] > 0).astype(float))
voi = np.convolve(voi, np.ones(5) / 5, "same")
F = np.vstack([C, dl, voi[None]]).T[::ADIM]                     # (kare, 27)
t = t2[::ADIM]; DT = float(t[1] - t[0])

w = kelimeleri_oku(); kita = kitalari_esle(w)
TOL = 0.045            # kelime siniri icin izin verilen kayma (s)
ITER = 14
VAR_TABAN = 0.12
ESIK_DB = -62.0        # enerji baslangici / bitisi esigi (dBFS)

# durum basina (en az, en cok) sure, ms.  None = sinirsiz
SINIF = {}
for ch in "aeıioöuü":
    SINIF[ch] = ("unlu", 12, None, 2.5)
for ch in "vlryğ":
    SINIF[ch] = ("yari", 8, 50, 0.7)
SINIF["h"] = ("yari", 12, 80, 0.9)
for ch in "nm":
    SINIF[ch] = ("genizsi", 8, 130, 1.0)
for ch in "bdgc":
    SINIF[ch] = ("otumlu_patlamali", 8, 70, 0.9)
for ch in "ptkç":
    SINIF[ch] = ("otumsuz_patlamali", 12, 120, 1.2)
for ch in "fsşz":
    SINIF[ch] = ("surtunmeli", 12, 110, 1.3)

# --- parcalar: L1, L2, L3+L4 (kesintisiz) ---
parcalar = []
for v in range(7):
    for dz in ([0], [1], [2, 3]):
        kel = [q for d in dz for q in kita[v][d]]
        dize_sonu = set()
        n = 0
        for d in dz:
            n += len(kita[v][d]); dize_sonu.add(n - 1)
        parcalar.append({"kita": v, "dizeler": dz, "kel": kel, "dize_sonu": dize_sonu})
son = [q for q in w if q["start"] > 100.0]          # yalniz egitim icin
for i in range(0, len(son), 4):
    kel = [dict(q, soz=kucuk(q["text"])) for q in son[i:i + 4]]
    if len(kel) == 4:
        parcalar.append({"kita": -1, "dizeler": [3], "kel": kel, "dize_sonu": {3}})


def sinir_bul(a, b):
    """Parcanin enerji baslangici ve bitisi (2 ms zarf uzerinde)."""
    i1 = int(a / DT2) + 10; i0 = int(max(0, a - 0.30) / DT2)
    on = i1
    for i in range(i1, i0, -1):
        if db2[i] < ESIK_DB:
            break
        on = i
    j0 = int((b - 0.10) / DT2); j1 = min(len(db2) - 1, int((b + 1.0) / DT2))
    off = j1; say = 0
    for j in range(j0, j1):
        if db2[j] < ESIK_DB:
            say += 1
            if say * DT2 >= 0.15:
                off = j - say + 1
                break
        else:
            say = 0
    return on * DT2, off * DT2


from dize import dizeleri_bul
DZ, SEV = dizeleri_bul(kita)
for p in parcalar:
    if p["kita"] >= 0:      # dize sinirlari dize.py'den (enerji cukurlari)
        p["t0"] = DZ[p["kita"]][p["dizeler"][0]]["baslangic"]; p["t1"] = DZ[p["kita"]][p["dizeler"][-1]]["bitis"]
    else:
        p["t0"], p["t1"] = sinir_bul(p["kel"][0]["start"], p["kel"][-1]["end"])
    harfler = []
    for ki, q in enumerate(p["kel"]):
        hs = list(kucuk(q["soz"]))
        for hi, ch in enumerate(hs):
            harfler.append((ki, ch, hi == len(hs) - 1 and ki in p["dize_sonu"]))    # dize sonu harfi mi
    p["harf"] = harfler

mask = np.zeros(len(t), bool)
for p in parcalar:
    mask[int(p["t0"] / DT):int(p["t1"] / DT)] = True
mu = F[mask].mean(0); sd = F[mask].std(0) + 1e-9
F = (F - mu) / sd
F[:, -1] *= 2.0        # seslilik agirligi
F[:, 13:26] *= 0.7     # delta agirligi


def durumlar(p):
    """[(ad, kelime_no, enaz_kare, encok_kare|None)]"""
    ds = []
    nh = len(p["harf"])
    for i, (ki, ch, dsonu) in enumerate(p["harf"]):
        _, mn, mx, _ = SINIF[ch]
        if dsonu and mx is not None:
            mx = None if i == nh - 1 else 170          # dize sonu unsuzu uzayabilir (var -> surtunmeli r, bak -> k + kuyruk)
        a = max(1, int(round(mn / 1000 / DT))); b = None if mx is None else max(a + 1, int(round(mx / 1000 / DT)))
        ds.append((ch + "0", ki, a, b)); ds.append((ch + "1", ki, a, b))
    return ds


def pencere(p, ki):
    kel = p["kel"]
    lo = -1e9 if ki == 0 else kel[ki - 1]["end"] - TOL
    hi = 1e9 if ki == len(kel) - 1 else kel[ki + 1]["start"] + TOL
    return lo, hi


def kareler(p):
    i0 = int(round(p["t0"] / DT)); n = int(round(p["t1"] / DT)) - i0
    return i0, n


def duz_baslangic(p):
    i0, n = kareler(p)
    et = np.zeros(n, int); kel = p["kel"]; si = 0
    sin = []         # durum sinir zamanlari
    for ki, q in enumerate(kel):
        hs = [ch for k2, ch, _ in p["harf"] if k2 == ki]
        ag = np.array([SINIF[ch][3] for ch in hs]); cs = np.concatenate([[0], np.cumsum(ag) / ag.sum()])
        a = p["t0"] if ki == 0 else (kel[ki - 1]["end"] + q["start"]) / 2
        b = p["t1"] if ki == len(kel) - 1 else (q["end"] + kel[ki + 1]["start"]) / 2
        for j in range(len(hs)):
            s = a + cs[j] * (b - a); e = a + cs[j + 1] * (b - a)
            sin.append((s, (s + e) / 2, si)); sin.append(((s + e) / 2, e, si + 1)); si += 2
    for s, e, k in sin:
        et[max(0, int(round(s / DT)) - i0):max(0, int(round(e / DT)) - i0)] = k
    et[max(0, int(round(sin[-1][0] / DT)) - i0):] = sin[-1][2]
    return et


def kestir(etiketler):
    top = {}
    for p, et in zip(parcalar, etiketler):
        i0, n = kareler(p); ds = durumlar(p); X = F[i0:i0 + n]
        for si, d in enumerate(ds):
            m = et == si
            if m.any():
                top.setdefault(d[0], []).append(X[m])
    model = {}
    for ad, xs in top.items():
        X = np.concatenate(xs)
        model[ad] = (X.mean(0), np.maximum(X.var(0), VAR_TABAN), len(X))
    return model


def viterbi(p, model):
    i0, n = kareler(p); X = F[i0:i0 + n]; tt = t[i0:i0 + n]
    ds = durumlar(p); S = len(ds)
    em = np.full((n, S), -1e12)
    for si, (ad, ki, mn, mx) in enumerate(ds):
        m, v, _ = model[ad]
        ll = -0.5 * (((X - m) ** 2) / v + np.log(2 * np.pi * v)).sum(1)
        lo, hi = pencere(p, ki)
        ok = (tt >= lo) & (tt <= hi)
        em[ok, si] = ll[ok]
    # mikro durum zinciri
    par = []; ilk = []; kendi = []; cikis = []
    for si, (ad, ki, mn, mx) in enumerate(ds):
        L = mn if mx is None else mx
        ilk.append(len(par))
        for d in range(L):
            par.append(si)
            kendi.append(mx is None and d == L - 1)
            cikis.append(d >= mn - 1)
    par = np.array(par); kendi = np.array(kendi); cikis = np.array(cikis); ilk = np.array(ilk); Mn = len(par)
    ilk_mi = np.zeros(Mn, bool); ilk_mi[ilk] = True
    # her durumun cikis mikro-durumlari (dolgulu indeks tablosu)
    Dm = max(int(cikis[ilk[s]:(ilk[s + 1] if s + 1 < S else Mn)].sum()) for s in range(S))
    tab = np.full((S, Dm), Mn, int)
    for s in range(S):
        a = ilk[s]; b = ilk[s + 1] if s + 1 < S else Mn
        ix = np.arange(a, b)[cikis[a:b]]
        tab[s, :len(ix)] = ix
    delta = np.full(Mn, -np.inf); delta[0] = em[0, 0]
    bp = np.zeros((n, Mn), np.int32)
    ar = np.arange(Mn)
    for i in range(1, n):
        de = np.concatenate([delta, [-np.inf]])
        cv = de[tab]                                   # (S, Dm)
        am = cv.argmax(1); best = cv[np.arange(S), am]; kaynak = tab[np.arange(S), am]
        ilerle = np.concatenate([[-np.inf], delta[:-1]]); onceki = ar - 1
        # durumun ilk mikro-durumu: onceki durumun en iyi cikisindan
        ilerle[ilk[1:]] = best[:-1]; onceki = onceki.copy(); onceki[ilk[1:]] = kaynak[:-1]
        ilerle[0] = -np.inf
        kal = np.where(kendi, delta, -np.inf)
        sec = ilerle >= kal
        yeni = np.where(sec, ilerle, kal) + em[i, par]
        bp[i] = np.where(sec, onceki, ar)
        delta = yeni
    # bitis: son durumun cikisa izinli mikro-durumlarindan en iyisi
    a = ilk[-1]
    adaylar = np.arange(a, Mn)[cikis[a:]]
    j = int(adaylar[np.argmax(delta[adaylar])]); skor = float(delta[j])
    yol = np.zeros(n, int)
    for i in range(n - 1, -1, -1):
        yol[i] = j
        j = int(bp[i, j])
    return par[yol], skor


etiket = [duz_baslangic(p) for p in parcalar]
for it in range(ITER):
    model = kestir(etiket)
    yeni = []; LL = 0.0
    for p in parcalar:
        et, ll = viterbi(p, model); yeni.append(et); LL += ll
    deg = sum(int((a != b).sum()) for a, b in zip(etiket, yeni)); etiket = yeni
    print("iter %2d  logL %.0f  degisen kare %d" % (it, LL, deg), flush=True)

cik = []
for p, et in zip(parcalar, etiket):
    if p["kita"] < 0:
        continue
    i0, n = kareler(p)
    kel = [{"soz": q["soz"], "json_bas": q["start"], "json_bit": q["end"], "harf": []} for q in p["kel"]]
    for hi, (ki, ch, _) in enumerate(p["harf"]):
        m = np.where((et == 2 * hi) | (et == 2 * hi + 1))[0]
        assert len(m), (p["kita"], ch)
        kel[ki]["harf"].append({"harf": ch, "bas": round(float(t[i0 + m[0]]), 4), "bit": round(float(t[i0 + m[-1]] + DT), 4)})
    cik.append({"kita": p["kita"] + 1, "dizeler": [d + 1 for d in p["dizeler"]], "t0": round(p["t0"], 4), "t1": round(p["t1"], 4), "kel": kel})
json.dump(cik, open(os.path.join(K, "ara", "hizalama.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
print("yazildi: ara/hizalama.json")
for c in cik:
    print(c["kita"], c["dizeler"], " ".join("%s[%.2f-%.2f]" % (h["harf"], h["bas"], h["bit"]) for q in c["kel"] for h in q["harf"]))
