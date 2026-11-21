#!/usr/bin/env python3
"""3. adim (ana betik): dize sinirlari + hece sinirlari + hece perdeleri + 6. kita onarim verisi + gurultu tabani.
Girdi : dinle_2_vokal.wav, dinle_2_words.json, ara/ozellik.npz (ozellik.py), ara/hizalama.json (hizala.py)
Cikti : kesim.json  (anahtarlar Ingilizce: start, end, cut_in, cut_out, syllables, f0_hz ...)

HECE SINIRI YONTEMI
  1) Hece cekirdegi (unlu) kabaca nerede: hizala.py'nin harf hizalamasindaki unlu araliklari.
  2) Kesin sinir: ardisik iki unlu arasinda, 300-3400 Hz bandinin 12 ms'lik enerji zarfindaki CUKUR.
     Oncelik sonraki hecenin bastaki unsuzunun (onset) cevresindeki cukurdadir (Din|le: sinir n ile l
     arasina gelsin diye); orasi yeterince dusuk degilse iki unlu arasindaki en derin cukur alinir.
     kind = "dip"
  3) Cukur yoksa (derinlik < 3 dB; tipik olarak 'ğ' ya da unlu-unlu gecisi): iki unlu arasindaki en buyuk
     spektral degisim ani (log-mel aki).  kind = "spectral"
  4) O da belirgin degilse (li-ği gibi ayni unlu): birlesik unlunun ORTASI.  kind = "midpoint" (akustik sinir yok)
  Bagimsiz capraz kontrol ("kor" yontem, gorev tanimindaki): kelime araliginda yumusatilmis sesli-enerji
  zarfinin tepe sayisi = bulunan cekirdek sayisi. Beklenen hece sayisini tutmuyorsa kelime FLAG edilir.
"""
import os, json, numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt, find_peaks
from ortak import (K, A, VOKAL, HAYVAN, kelimeleri_oku, kitalari_esle, ozellik, kucuk, hecele, UNLU,
                   dize_sozleri, L2_OLMASI_GEREKEN)
from dize import dizeleri_bul, t, DT, fi, db_ham

z = ozellik()
x, fs = sf.read(VOKAL)
if x.ndim > 1:
    x = x.mean(axis=1)
x = x.astype(np.float64)
HOP = int(z["hop"])
kita = kitalari_esle(kelimeleri_oku())
DZ, SEV = dizeleri_bul(kita)
HZ = json.load(open(os.path.join(K, "ara", "hizalama.json"), encoding="utf8"))


def zarf(lo, hi, pencere_ms):
    """Bant geciren + kare + Hann yumusatma -> 2 ms izgarada dB zarf."""
    if lo is None:
        y = x
    else:
        sos = butter(4, [lo, hi], btype="band", fs=fs, output="sos"); y = sosfiltfilt(sos, x)
    n = int(pencere_ms / 1000 * fs) | 1
    h = np.hanning(n + 2)[1:-1]; h /= h.sum()
    p = np.convolve(y ** 2, h, "same")
    idx = np.minimum(np.arange(len(t)) * HOP, len(x) - 1)
    return 10 * np.log10(p[idx] + 1e-12)


E12 = zarf(300, 3400, 12)        # sinir cukurlari icin
E30 = zarf(300, 3400, 30)        # cekirdek (tepe) sayimi icin
ELOW = zarf(100, 1000, 20)       # temel + F1 bandi: unlu baslangici (otumsuz surtunme / patlama burada zayif)
R5 = zarf(None, None, 5)         # tam bant, 5 ms (ek yeri / kapanis cukuru icin)
FLX = np.convolve(z["fluxabs"], np.hanning(7) / np.hanning(7).sum(), "same")
FLXP = np.convolve(z["flux"], np.hanning(7) / np.hanning(7).sum(), "same")       # yalniz artis (onset) akisi
th = z["th"]; f0h = z["f0h"]; f0s = z["f0s"]
VOI = np.interp(t, th, (f0h > 0).astype(float)) > 0.5
midi = lambda f: 69 + 12 * np.log2(f / 440.0)
NOTA = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def nota_adi(m):
    r = int(round(m)); return "%s%d" % (NOTA[r % 12], r // 12 - 1)


def f0_olc(a, b, f0=f0h):
    m = (th >= a) & (th < b)
    v = f0[m]; s = v[v > 0]
    if len(s) == 0:
        return None, None, 0.0, None
    med = float(np.median(s)); mm = midi(s)
    return med, float(midi(med)), float(len(s) / max(1, len(v))), float(np.percentile(mm, 75) - np.percentile(mm, 25))


def r3(v):
    return None if v is None else round(float(v), 4)


# ------------------------------------------------------------------ hece yapisi
def hece_harfleri(kel_hz, soz):
    """Kelimenin hizalanmis harflerini hecelere dagit. Donus: [{text, onset:[..], vowel:{}, coda:[..]}]"""
    hs = hecele(soz); out = []; i = 0
    for h in hs:
        hk = kucuk(h); seg = kel_hz["harf"][i:i + len(hk)]; i += len(hk)
        assert "".join(s["harf"] for s in seg) == hk, (soz, hk, seg)
        vi = [j for j, s in enumerate(seg) if s["harf"] in UNLU]
        assert len(vi) == 1, (soz, h)
        out.append({"text": h, "onset": seg[:vi[0]], "vowel": seg[vi[0]], "coda": seg[vi[0] + 1:]})
    assert i == len(kel_hz["harf"])
    return out


def cukur_merkezi(i, a, b, taban, pay=2.0):
    """i karesi cevresinde (tabana kirpilmis) E12 < E12[i]+pay olan bitisik pencerenin ortasi ([a,b] icinde)."""
    esik = max(E12[i], taban) + pay
    L = i
    while L > a and E12[L - 1] < esik:
        L -= 1
    R = i
    while R < b and E12[R + 1] < esik:
        R += 1
    return (L + R) // 2, (R - L + 1) * DT


LMEL = z["logmel"].astype(np.float64)
MIN_HECE = 0.06


def iki_parca(a, b, enaz=0.03):
    """[a,b] araligini log-mel spektrumu iki sabit parcaya en iyi bolen an (unlu-unlu gecisi).
    Donus: (zaman, kazanc)  kazanc = aciklanan varyans orani (0..1)."""
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


def sinir_bul(sol, sag, lim_a=None, lim_b=None):
    """sol / sag: ardisik iki hecenin harf yapisi (hizalamadan). Donus: sinir sozlugu.
    lim_a / lim_b: komsu sinirlarla cakisma cozulurken konan kesin alt / ust zaman siniri."""
    vs_j, ve_j = sol["vowel"]["bas"], sol["vowel"]["bit"]
    vs_n, ve_n = sag["vowel"]["bas"], sag["vowel"]["bit"]
    # arama bolgesi: iki unlunun (hizalamadaki) ORTALARI arasi - hizalamanin unsuz kenarlarina guvenilmez
    a, b = fi((vs_j + ve_j) / 2), fi((vs_n + ve_n) / 2)
    if lim_a is not None:
        a = max(a, fi(lim_a)); vs_j = max(vs_j, lim_a - 0.06); ve_j = max(ve_j, vs_j + 0.01)
    if lim_b is not None:
        b = min(b, fi(lim_b)); ve_n = min(ve_n, lim_b + 0.0); vs_n = min(vs_n, ve_n - 0.01)
    if b <= a + 2:
        return {"consonants": "?", "t": (a + b) / 2 * DT, "kind": "model", "depth_db": None, "note": "search window collapsed"}
    unsuz = "".join(s_["harf"] for s_ in sol["coda"]) + "|" + "".join(s_["harf"] for s_ in sag["onset"])
    out = {"consonants": unsuz}
    sol_a = fi(vs_j); sag_b = fi(ve_n)
    # sessizlik tabani: ayrilmis vokal kapili oldugundan kapanislar -60..-100 dB arasinda gezinir;
    # komsu unlu tepesinin 35 dB altindaki her sey "esit derecede sessiz" sayilir
    taban = float(min(E12[sol_a:fi(ve_j) + 1].max(), E12[fi(vs_n):sag_b + 1].max()) - 35.0)
    Ek = lambda i: max(float(E12[i]), taban)
    iR = a + int(np.argmin(E12[a:b + 1])); ER = Ek(iR)
    # iki unlu arasinda birden cok dusuk bolge varsa (kapanis + patlama + sessizlik: "bak|din"), SONUNCUSU alinir:
    # sinir = sonraki hecenin enerjisi yukselmeden onceki son dusuk nokta (patlama onceki hecede kalir).
    dR = float(min(E12[sol_a:iR + 1].max(), E12[iR:sag_b + 1].max()) - ER)        # en derin cukurun derinligi
    pay = float(np.clip(0.5 * dR, 1.0, 6.0))                                      # sig cukurda dar, derin kapanista genis
    dusuk = np.array([Ek(i) <= ER + pay for i in range(a, b + 1)])
    j1 = int(np.max(np.where(dusuk)[0])); j0 = j1
    while j0 > 0 and dusuk[j0 - 1]:
        j0 -= 1
    seg = E12[a + j0:a + j1 + 1]
    iS = a + j0 + int(np.argmin(seg))
    # koda varsa (VC|CV: bak|din, nek|ler, çift|li): son dusuk bolge (sonraki hecenin onset'inden hemen once);
    # koda yoksa (V|CV: ba|ba, na|sıl): en derin noktanin cevresi (unsuzun ortasi)
    adaylar = []
    if sol["coda"] and iS != iR:
        adaylar.append((iS, a + j0, a + j1, "last_low"))
    adaylar.append((iR, a, b, "deepest"))
    wa = wb = None
    if sag["onset"]:
        wa = max(a, fi(sag["onset"][-1]["bas"] - 0.025)); wb = min(b, fi(sag["onset"][-1]["bit"] + 0.025))
    ayni_unlu_g = (unsuz == "|ğ" and sol["vowel"]["harf"] == sag["vowel"]["harf"])
    if ayni_unlu_g:
        # "li-ği", "li-ğin": yumusak g iki AYNI unlu arasinda -> tek uzun unlu, akustik sinir yok.
        # (Enerji / spektrum olcutleri burada komsu unsuze gecisi yakaliyor: bilerek kullanilmiyor.)
        out.update({"t": (vs_j + ve_n) / 2, "kind": "midpoint", "depth_db": None,
                    "merged_vowel": [round(vs_j, 4), round(ve_n, 4)]})
        return out
    FLP = FLXP
    koda_son = sol["coda"][-1]["harf"] if sol["coda"] else ""
    onset_ilk = sag["onset"][0]["harf"] if sag["onset"] else ""
    if koda_son in "nm" and koda_son and onset_ilk in ("l", "y", "r", "v", "n", "m"):
        # "Din|le", "yun|la": uzun genizsi (n) + akici unsuz. Sinir genizsinin BITTIGI yerdedir
        # (ust bantlarda ani enerji artisi = pozitif spektral aki tepesi), genizsinin ortasinda degil.
        lo = max(fi((vs_j + ve_j) / 2), fi(sag["onset"][0]["bas"] - 0.06)); hi = min(fi((vs_n + ve_n) / 2), fi(sag["onset"][-1]["bit"] + 0.03))
        if hi > lo + 2:
            ip = lo + int(np.argmax(FLP[lo:hi + 1]))
            ftab = float(np.median(FLP[fi(vs_j):fi(ve_n) + 1]))
            oran = float(FLP[ip] / (ftab + 1e-9))
            if oran >= 2.5 and FLP[ip] >= 15.0:
                out.update({"t": ip * DT, "kind": "spectral", "where": "nasal_release", "flux_ratio": round(oran, 2),
                            "depth_db": None})
                return out
    if onset_ilk == "y" and not sol["coda"]:
        # "ko|yun", "mi|yav": 'y' yari unludur, enerji cukuru yapmaz (i gibi parlak); sig cukur varsa kaymanin SONUNDA olur.
        # Sinir = iki unlu arasindaki spektral gecis (iki parcali bolme).
        if sol["vowel"]["harf"] in "aıou":
            # arka unluden sonra 'y': kayma, 1-3.4 kHz bandinin (F2) parladigi kisa andir -> sinir = o tepe
            f2 = np.convolve(10 * np.log10(z["b_f2"] + 1e-12), np.hanning(9) / np.hanning(9).sum(), "same")
            ip = a + int(np.argmax(f2[a:b + 1]))
            cik = float(f2[ip] - max(f2[a:ip + 1].min(), f2[ip:b + 1].min()))
            if cik >= 3.0 and a < ip < b:
                out.update({"t": ip * DT, "kind": "spectral", "where": "glide_f2_peak", "f2_peak_db": round(cik, 1), "depth_db": None})
                return out
        tb, kazanc = iki_parca(vs_j + 0.03, ve_n - 0.02)
        if kazanc >= 0.25 and (tb - vs_j) >= 0.05 and (ve_n - tb) >= 0.05:
            out.update({"t": tb, "kind": "spectral", "where": "glide_two_segment_fit", "spectral_gain": round(kazanc, 2),
                        "depth_db": None})
            return out
    for i0, lo, hi, yer in adaylar:
        # gercek cukur derinligi: cukurun iki yanindaki (unlu) tepelerin dusugu - cukur
        derinlik = float(min(E12[sol_a:i0 + 1].max(), E12[i0:sag_b + 1].max()) - E12[i0])
        if derinlik >= 3.0:
            ic, gen = cukur_merkezi(i0, lo, hi, taban)
            out.update({"t": ic * DT, "kind": "dip", "depth_db": round(derinlik, 1), "where": yer,
                        "low_window_ms": round(gen * 1000, 1), "level_dbfs": round(float(R5[ic]), 1)})
            return out
    out["depth_db"] = round(float(min(E12[sol_a:iR + 1].max(), E12[iR:sag_b + 1].max()) - ER), 1)
    arada_unsuz = unsuz.replace("|", "").replace("ğ", "")
    if not arada_unsuz:
        # 'ğ' ya da unlu-unlu: birlesik unluyu spektruma gore ikiye bol; belirgin degilse ortadan
        tb, kazanc = iki_parca(vs_j, ve_n)
        ic_mi = (tb - vs_j) >= 0.04 and (ve_n - tb) >= 0.04
        if kazanc >= 0.30 and ic_mi:
            out.update({"t": tb, "kind": "spectral", "spectral_gain": round(kazanc, 2)})
        else:
            out.update({"t": (vs_j + ve_n) / 2, "kind": "midpoint", "spectral_gain": round(kazanc, 2)})
        return out
    # unsuz var ama enerji cukuru yok (a|nın, o|yun, i|yav ...): once iki unlunun tamamini spektruma gore ikiye bol
    if sol["vowel"]["harf"] != sag["vowel"]["harf"] and koda_son not in ("n", "m"):
        tb, kazanc = iki_parca(vs_j + 0.01, ve_n - 0.01)
        if kazanc >= 0.30 and (tb - vs_j) >= 0.04 and (ve_n - tb) >= 0.04:
            out.update({"t": tb, "kind": "spectral", "where": "two_segment_fit", "spectral_gain": round(kazanc, 2)})
            return out
    lo, hi = (wa, wb) if (wa is not None and wb > wa) else (a, b)
    ip = lo + int(np.argmax(FLX[lo:hi + 1]))
    ftab = float(np.median(np.concatenate([FLX[fi(vs_j):fi(ve_j) + 1], FLX[fi(vs_n):fi(ve_n) + 1]])))
    oran = float(FLX[ip] / (ftab + 1e-9))
    if oran >= 2.0 and FLX[ip] >= 20.0:
        out.update({"t": ip * DT, "kind": "spectral", "flux_ratio": round(oran, 2)})
    else:
        tm = sag["onset"][0]["bas"] if sag["onset"] else (ve_j + vs_n) / 2
        out.update({"t": tm, "kind": "model", "flux_ratio": round(oran, 2)})
    return out


# ------------------------------------------------------------------ kor cekirdek sayimi (gorev tanimindaki yontem)
VOI2 = np.interp(t, th, ((f0h > 0) & (f0s > 0)).astype(float))
VOI2 = np.convolve(VOI2, np.ones(11) / 11, "same") > 0.6          # ~20 ms cogunluk: patlama gurultusundeki sahte sesliligi eler
EV = np.where(VOI2, E30, -120.0)                                  # "sesli enerji" zarfi


def kor_cekirdek(a, b):
    """Gorev tanimindaki kor yontem: kelime araliginda yumusatilmis sesli-enerji zarfinin tepeleri = cekirdekler."""
    ia, ib = fi(a), fi(b)
    seg = EV[ia:ib + 1]
    if len(seg) < 5 or seg.max() < -100:
        return [], []
    taban = seg.max() - 40.0
    pad = np.concatenate([[taban], np.maximum(seg, taban), [taban]])
    pk, pr = find_peaks(pad, prominence=3.0, distance=max(1, int(0.05 / DT)))
    pk = pk - 1
    ok = [p for p in pk if seg[p] >= seg.max() - 15.0]
    tepeler = [(ia + p) * DT for p in ok]
    sinirlar = []
    for p, q in zip(ok[:-1], ok[1:]):
        sinirlar.append((ia + p + int(np.argmin(E12[ia + p:ia + q + 1]))) * DT)
    return tepeler, sinirlar


def cukur_bilgisi(c):
    """dize.py'nin Turkce anahtarli cukur bilgisini cikti semasina cevirir."""
    if not c:
        return None
    return {"t": c.get("an"), "level_dbfs": c.get("duzey_dbfs"), "min_level_dbfs": c.get("en_dusuk_dbfs"),
            "quiet_window_ms": c.get("esik_alti_pencere_ms")}


# ------------------------------------------------------------------ ana dongu
verses = []
tum_hece = []; tum_kelime = []
for v in range(7):
    parc = [p for p in HZ if p["kita"] == v + 1]
    # parca -> hece listesi (dize, kelime bilgisiyle)
    lines = [None] * 4
    for p in parc:
        kel_no = 0; heceler = []
        dize_kel = []
        for d in p["dizeler"]:
            for j, q in enumerate(kita[v][d - 1]):
                dize_kel.append((d - 1, j, q))
        for (d, j, q), khz in zip(dize_kel, p["kel"]):
            for hi_, h in enumerate(hece_harfleri(khz, q["soz"])):
                h.update({"line": d, "word_i": j, "word": q["soz"], "syl_i": hi_, "q": q})
                heceler.append(h)
        # sinirlar
        sin = [sinir_bul(heceler[i], heceler[i + 1]) for i in range(len(heceler) - 1)]
        # cakisma cozumu: ardisik iki sinir 60 ms'den yakinsa ikisi ayni akustik olayi (ayni cukuru) sahiplenmistir.
        # Guveni dusuk olan (sig cukur / cukur disi), digerinden 60 ms uzakta kalacak sekilde yeniden aranir.
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
        for i, s_ in enumerate(sin):
            h0, h1 = heceler[i], heceler[i + 1]
            if (h0["line"], h0["word_i"]) != (h1["line"], h1["word_i"]):
                g0, g1 = h0["q"]["json_bit"], h1["q"]["json_bas"]
                s_["word_boundary"] = True; s_["json_gap"] = [g0, g1]
                if s_["consonants"] == "|" and s_["kind"] != "dip" and not (g0 <= s_["t"] <= g1):
                    # kelime sinirinda unlu-unlu gecisi (de|ör): yavas gecis, olcum belirsiz -> yazi dokumunun boslugu icine kirp
                    s_["t_unclamped"] = round(s_["t"], 4); s_["t"] = float(min(max(s_["t"], g0), g1)); s_["clamped_to_json_gap"] = True
        for i, s_ in enumerate(sin):
            # iki cekirdek (hizalamadaki unlu ortalari) arasindaki en dusuk tam-bant duzey: kapanis ne kadar sessiz?
            ca = fi((heceler[i]["vowel"]["bas"] + heceler[i]["vowel"]["bit"]) / 2)
            cb = fi((heceler[i + 1]["vowel"]["bas"] + heceler[i + 1]["vowel"]["bit"]) / 2)
            s_["min_level_dbfs"] = round(float(R5[ca:cb + 1].min()), 1)
            s_["level_at_t_dbfs"] = round(float(R5[fi(s_["t"])]), 1)
            s_.pop("level_dbfs", None)
        bas = DZ[v][p["dizeler"][0] - 1]["baslangic"]; bit = DZ[v][p["dizeler"][-1] - 1]["bitis"]
        kenar = [bas] + [s["t"] for s in sin] + [bit]
        assert all(b > a for a, b in zip(kenar[:-1], kenar[1:])), (v + 1, p["dizeler"], kenar)
        for i, h in enumerate(heceler):
            h["start"] = kenar[i]; h["end"] = kenar[i + 1]
            h["end_boundary"] = sin[i] if i < len(sin) else None
        for d in p["dizeler"]:
            lines[d - 1] = [h for h in heceler if h["line"] == d - 1]
    vout = {"verse": v + 1, "animal": HAYVAN[v], "lines": []}
    for d in range(4):
        hs = lines[d]; dz = DZ[v][d]
        L_start = hs[0]["start"]; L_end = hs[-1]["end"]
        words = []; syls = []
        for j, q in enumerate(kita[v][d]):
            wh = [h for h in hs if h["word_i"] == j]
            ws, we = wh[0]["start"], wh[-1]["end"]
            tep, ksin = kor_cekirdek(ws, we)
            beklenen = len(wh)
            ic_sinir = [h["end_boundary"] for h in wh[:-1]]
            turler = [s["kind"] for s in ic_sinir]
            sapma = None
            if len(tep) == beklenen and beklenen > 1:
                sapma = max(abs(a - s["t"]) for a, s in zip(ksin, ic_sinir)) * 1000
            say_tutmadi = len(tep) != beklenen
            kural = [i for i, k_ in enumerate(turler) if k_ in ("midpoint", "model")]
            flag = bool(kural)
            neden = []
            if kural:
                neden.append("no acoustic boundary at %s (placed by rule: %s)" % (
                    ",".join(wh[i]["text"] + "|" + wh[i + 1]["text"] for i in kural), ",".join(turler[i] for i in kural)))
            if say_tutmadi:
                neden.append("blind envelope peak picking found %d nuclei, expected %d" % (len(tep), beklenen))
            f0m, f0mi, vr, _ = f0_olc(ws, we)
            wd = {"text": q["soz"], "start": r3(ws), "end": r3(we), "json_start": q["json_bas"], "json_end": q["json_bit"],
                  "syllables_expected": beklenen,
                  "flag": bool(flag), "flag_reason": neden[0] if kural else None,
                  "boundary_kinds": turler,
                  "blind_check": {"nuclei_detected": len(tep), "count_matches": not say_tutmadi,
                                  "max_dev_from_final_ms": None if sapma is None else round(sapma, 1)},
                  "f0_all_hz": None if f0m is None else round(f0m, 2), "f0_all_midi": None if f0mi is None else round(f0mi, 2),
                  "voiced_ratio": round(vr, 3)}
            words.append(wd); tum_kelime.append((v + 1, d + 1, wd))
            for h in wh:
                a, b = h["start"], h["end"]
                ia, ib = fi(a), fi(b)
                # cekirdek (unlu govdesi): sesli karelerde E30 tepesi ve cevresinde tepe-6 dB ustunde kalan sesli bolge
                seg = np.where(VOI[ia:ib + 1], E30[ia:ib + 1], -200.0)
                ip = ia + int(np.argmax(seg)); tepe = E30[ip]
                L = ip
                while L > ia and E30[L - 1] > tepe - 6 and VOI[L - 1]:
                    L -= 1
                R = ip
                while R < ib and E30[R + 1] > tepe - 6 and VOI[R + 1]:
                    R += 1
                # unlu baslangici (vurus ani): 100-1000 Hz bandinin (f0 + F1) 20 ms zarfi hecedeki tepesinin 6 dB altina
                # ILK ulastigi an. Otumsuz surtunme / patlama ve otumlu kapanis bu bantta zayif kalir -> unluye kadar bekler.
                tpl = ELOW[ia:ib + 1].max(); io = ia
                while io < ib and ELOW[io] < tpl - 6.0:
                    io += 1
                f0m, f0mi, vr, _ = f0_olc(a, b)
                c0m, c0mi, _, ciqr = f0_olc(L * DT, (R + 1) * DT)
                d0m, d0mi, dvr, _ = f0_olc(L * DT, (R + 1) * DT, f0s)
                if c0m is None:
                    c0m, c0mi = f0m, f0mi
                eb = h["end_boundary"]
                onceki = wh[h["syl_i"] - 1]["end_boundary"] if h["syl_i"] > 0 else None
                kuralli = [x for x in (onceki, eb) if x is not None and x["kind"] in ("midpoint", "model")]
                sd = {"text": h["text"], "word": h["word"], "word_index": h["word_i"], "index_in_word": h["syl_i"],
                      "start": r3(a), "end": r3(b), "duration": r3(b - a),
                      "vowel_onset": r3(io * DT),
                      "nucleus": r3(ip * DT), "core_start": r3(L * DT), "core_end": r3((R + 1) * DT),
                      "f0_hz": None if c0m is None else round(c0m, 2), "f0_midi": None if c0mi is None else round(c0mi, 2),
                      "note": None if c0mi is None else nota_adi(c0mi),
                      "cents_from_note": None if c0mi is None else int(round((c0mi - round(c0mi)) * 100)),
                      "f0_iqr_semitones": None if ciqr is None else round(ciqr, 2),
                      "f0_all_hz": None if f0m is None else round(f0m, 2), "f0_all_midi": None if f0mi is None else round(f0mi, 2),
                      "f0_dio_midi": None if d0mi is None else round(d0mi, 2),
                      "voiced_ratio": round(vr, 3),
                      "peak_dbfs": round(float(db_ham[ia:ib + 1].max()), 1),
                      "rms_dbfs": round(float(10 * np.log10(np.mean(z["rms"][ia:ib + 1] ** 2) + 1e-12)), 1),
                      "end_boundary": None if eb is None else {k_: (r3(val) if k_ == "t" else val) for k_, val in eb.items()},
                      "flag": bool(kuralli),
                      "flag_reason": ("start or end boundary has no acoustic evidence (%s)" % kuralli[0]["kind"]) if kuralli else None}
                syls.append(sd); tum_hece.append((v + 1, d + 1, sd))
        ia, ib = fi(L_start), fi(L_end)
        guclu = ia
        while guclu < ib and db_ham[guclu] < SEV["soylenen_rms_dbfs"] - 20.0:
            guclu += 1
        cm = [s_["f0_midi"] for s_ in syls if s_["f0_midi"] is not None]
        ld = {"line": d + 1, "text": dize_sozleri(v)[d], "start": r3(L_start), "end": r3(L_end), "duration": r3(L_end - L_start),
              "onset_strong": r3(guclu * DT), "first_vowel_onset": syls[0]["vowel_onset"],
              "cut_in": r3(dz["kesim_giris"]), "cut_out": r3(dz["kesim_cikis"]),
              "cut_in_info": cukur_bilgisi(dz.get("giris_cukuru")), "cut_out_info": cukur_bilgisi(dz.get("cikis_cukuru")),
              "rms_dbfs": round(float(10 * np.log10(np.mean(z["rms"][ia:ib + 1] ** 2) + 1e-12)), 1),
              "peak_dbfs": round(float(db_ham[ia:ib + 1].max()), 1),
              "f0_midi_median_of_syllables": round(float(np.median(cm)), 2),
              "words": words, "syllables": syls}
        if d == 3:
            ld["tail_end"] = r3(dz["kuyruk_bitis"])
        if d == 1 and v == 5:
            ld["text_as_sung"] = dize_sozleri(v)[d]; ld["text_intended"] = L2_OLMASI_GEREKEN[v]
            ld["defect"] = "singer sang 'ördekleri' instead of 'köpekleri' (see verse6_repair)"
        vout["lines"].append(ld)
    Ls = vout["lines"]
    # L3|L4 ic siniri bilgi icin (kesintisiz soyleniyor)
    Ls[2]["cut_out"] = None; Ls[3]["cut_in"] = None
    ic = fi(Ls[3]["start"])
    bilgi = {"t": Ls[3]["start"], "level_dbfs": round(float(R5[ic]), 1),
             "note": "L3 and L4 are sung without a gap; this is NOT a safe cut point (use only with a short crossfade)"}
    Ls[2]["cut_out_info"] = bilgi; Ls[3]["cut_in_info"] = bilgi
    # parcalar (kesilecek butunler)
    vout["chunks"] = [
        {"lines": [1], "cut_in": Ls[0]["cut_in"], "start": Ls[0]["start"], "end": Ls[0]["end"], "cut_out": Ls[0]["cut_out"],
         "first_vowel_onset": Ls[0]["first_vowel_onset"]},
        {"lines": [2], "cut_in": Ls[1]["cut_in"], "start": Ls[1]["start"], "end": Ls[1]["end"], "cut_out": Ls[1]["cut_out"],
         "first_vowel_onset": Ls[1]["first_vowel_onset"]},
        {"lines": [3, 4], "cut_in": Ls[2]["cut_in"], "start": Ls[2]["start"], "end": Ls[3]["end"], "cut_out": Ls[3]["cut_out"],
         "first_vowel_onset": Ls[2]["first_vowel_onset"],
         "l4_start_offset": r3(Ls[3]["start"] - Ls[2]["start"]),
         "l4_first_vowel_offset": r3(Ls[3]["first_vowel_onset"] - Ls[2]["start"])}]
    for c_ in vout["chunks"]:
        # sonumleme paylari: giris sonumlemesi 'start'tan once bitmeli, cikis sonumlemesi 'end'den sonra baslamali
        c_["fade_in_max_ms"] = round((c_["start"] - c_["cut_in"]) * 1000, 1)
        c_["fade_out_max_ms"] = round((c_["cut_out"] - c_["end"]) * 1000, 1)
        c_["cut_in_level_dbfs"] = round(float(R5[fi(c_["cut_in"])]), 1); c_["cut_out_level_dbfs"] = round(float(R5[fi(c_["cut_out"])]), 1)
    vout["start"] = Ls[0]["start"]; vout["end"] = Ls[3]["end"]
    verses.append(vout)

# ================================================================== L4 sonlari (son "bak") ve fazladan ses denetimi
SUS = -50.0          # dBFS: 5 ms RMS bunun altindaysa "sessiz"


def etkin_bolgeler(a, b, esik=SUS, bosluk=0.012):
    """[a,b] icinde R5 > esik olan bolgeler (12 ms'den kisa bosluklar birlestirilir)."""
    ia, ib = fi(a), fi(b); on = R5[ia:ib + 1] > esik
    out = []; i = 0; n = len(on)
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            out.append([ia + i, ia + j - 1]); i = j
        else:
            i += 1
    m = []
    for s_ in out:
        if m and (s_[0] - m[-1][1]) * DT < bosluk:
            m[-1][1] = s_[1]
        else:
            m.append(s_)
    return m


def son_bak(v):
    L4 = verses[v]["lines"][3]; s_ = L4["syllables"][-1]
    unlu_bit = s_["core_end"]
    bolgeler = etkin_bolgeler(unlu_bit, L4["end"] + 0.05)
    parcalar = []; ek = None; onceki_bit = unlu_bit
    for (i0, i1) in bolgeler:
        t0, t1 = i0 * DT, (i1 + 1) * DT
        m = (th >= t0) & (th < t1)
        ses = (f0h[m] > 0) & (f0s[m] > 0)
        vo = float(ses.mean()) if m.any() else 0.0
        med = float(midi(np.median(f0h[m][ses]))) if ses.any() else None
        p = {"start": r3(t0), "end": r3(t1), "duration": r3(t1 - t0), "peak_dbfs": round(float(R5[i0:i1 + 1].max()), 1),
             "voiced_ratio": round(vo, 2), "f0_midi": None if med is None else round(med, 2),
             "gap_before_ms": round((t0 - onceki_bit) * 1000, 1)}
        parcalar.append(p)
        # fazladan sesli hece: unluden sonra >= 30 ms sessizlik + >= 60 ms suren, cogu sesli, guclu bolge
        if ek is None and t0 - unlu_bit > 0.03 and p["gap_before_ms"] >= 30 and (t1 - t0) >= 0.06 and vo >= 0.5 and p["peak_dbfs"] > -35:
            g0, g1 = fi(onceki_bit), i0
            gm = g0 + int(np.argmin(R5[g0:g1 + 1]))
            L = gm
            while L > g0 and R5[L - 1] < SUS:
                L -= 1
            Rr = gm
            while Rr < g1 and R5[Rr + 1] < SUS:
                Rr += 1
            ek = {"start": p["start"], "end": p["end"], "peak_dbfs": p["peak_dbfs"], "f0_midi": p["f0_midi"],
                  "voiced_ratio": p["voiced_ratio"],
                  "silent_gap_before": [r3(L * DT), r3((Rr + 1) * DT)],
                  "cut_out_before_extra_sound": r3((L + Rr + 1) / 2 * DT),
                  "note": "a voiced after-sound follows the word after a silent gap (not part of the lyric); "
                          "cut at cut_out_before_extra_sound to drop it, or do not use this ending"}
        onceki_bit = t1
    return {"final_vowel_end": unlu_bit, "after_vowel_segments": parcalar, "extra_voiced_sound": ek,
            "energy_end": L4["end"], "tail_end": L4["tail_end"],
            "decay_ms_vowel_end_to_energy_end": round((L4["end"] - unlu_bit) * 1000, 1)}


for v in range(7):
    L4 = verses[v]["lines"][3]
    L4["ending"] = son_bak(v)
    ek = L4["ending"]["extra_voiced_sound"]
    if ek:
        L4["defect"] = "extra voiced sound after the last 'bak' at %.3f-%.3f s" % (ek["start"], ek["end"])
        L4["cut_out_before_extra_sound"] = ek["cut_out_before_extra_sound"]
        verses[v]["chunks"][2]["cut_out_before_extra_sound"] = ek["cut_out_before_extra_sound"]

# ================================================================== L4 karsilastirmasi (6. kita icin verici secimi)
def kelime_olc(a, b):
    m, mi, vr, _ = f0_olc(a, b)
    return None if mi is None else round(mi, 2)


l4 = []
for v in range(7):
    L3, L4 = verses[v]["lines"][2], verses[v]["lines"][3]
    S = L4["syllables"]; W = L4["words"]
    cek = [s_["nucleus"] - S[0]["nucleus"] for s_ in S]
    unlu = [s_["vowel_onset"] - S[0]["vowel_onset"] for s_ in S]
    l4.append({
        "verse": v + 1,
        "words": [w_["text"] for w_ in W],
        "word_median_midi": [w_["f0_all_midi"] for w_ in W],                       # kelimenin tum sesli karelerinin ortancasi
        "word_core_midi": [round(float(np.median([s_["f0_midi"] for s_ in S if s_["word_index"] == j])), 2) for j in range(4)],
        "syllables": [s_["text"] for s_ in S],
        "syllable_midi": [s_["f0_midi"] for s_ in S],
        "syllable_notes": [s_["note"] for s_ in S],
        "final_bak_midi": S[-1]["f0_midi"], "final_bak_note": S[-1]["note"], "final_bak_cents_from_C4": int(round((S[-1]["f0_midi"] - 60) * 100)),
        "duration_start_to_energy_end": r3(L4["end"] - L4["start"]),
        "duration_start_to_final_vowel_end": r3(L4["ending"]["final_vowel_end"] - L4["start"]),
        "syllable_start_offsets_ms": [round((s_["start"] - L4["start"]) * 1000) for s_ in S],
        "vowel_onset_offsets_ms": [round(x * 1000) for x in unlu],
        "nucleus_offsets_ms": [round(x * 1000) for x in cek],
        "rms_dbfs": L4["rms_dbfs"], "peak_dbfs": L4["peak_dbfs"], "syllable_peak_dbfs": [s_["peak_dbfs"] for s_ in S],
        "l3_rms_dbfs": L3["rms_dbfs"],
        "l3_l4_junction": {"t": L4["start"], "level_dbfs": L4["cut_in_info"]["level_dbfs"]},
        "b_closure_before_final_bak": {"t": S[-2]["end_boundary"]["t"], "level_dbfs": S[-2]["end_boundary"]["level_at_t_dbfs"],
                                       "min_level_dbfs": S[-2]["end_boundary"]["min_level_dbfs"]},
        "mean_syllable_peak_dbfs": round(float(np.mean([s_["peak_dbfs"] for s_ in S])), 2),
        "extra_voiced_sound": L4["ending"]["extra_voiced_sound"] is not None,
    })
def verici_sirala(hedef):
    """hedef kitanin L4'une en cok benzeyen (zamanlama, ses duzeyi, ilk 5 hecenin perdesi), C4'te biten, kusursuz L4'ler."""
    ref = l4[hedef - 1]; out = []
    for r_ in l4:
        if r_["verse"] == hedef:
            continue
        zf = float(np.mean(np.abs(np.array(r_["vowel_onset_offsets_ms"][1:]) - np.array(ref["vowel_onset_offsets_ms"][1:]))))
        lf = abs(r_["mean_syllable_peak_dbfs"] - ref["mean_syllable_peak_dbfs"])
        pf = float(np.mean(np.abs(np.array(r_["syllable_midi"][:5]) - np.array(ref["syllable_midi"][:5]))))
        cf = abs(r_["final_bak_midi"] - 60.0)
        uygun = (cf <= 0.5) and not r_["extra_voiced_sound"]
        out.append({"verse": r_["verse"], "timing_mean_abs_diff_ms": round(zf, 1), "loudness_abs_diff_db": round(lf, 2),
                    "gain_to_match_db": round(ref["mean_syllable_peak_dbfs"] - r_["mean_syllable_peak_dbfs"], 2),
                    "pitch_mean_abs_diff_semitones_first5": round(pf, 2), "final_bak_abs_dev_from_C4_semitones": round(cf, 2),
                    "eligible": bool(uygun), "score": round(zf / 20.0 + lf / 1.0 + pf / 0.3 + cf / 0.3, 2)})
    return sorted(out, key=lambda q_: (not q_["eligible"], q_["score"]))


SKOR = "timing_ms/20 + |mean syllable peak diff| dB/1 + pitch_st(first 5 syllables)/0.3 + final_dev_from_C4_st/0.3 (lower is better)"
sira6 = verici_sirala(6); sira3 = verici_sirala(3)
for r_ in l4:
    r_["vs_verse6"] = next((q_ for q_ in sira6 if q_["verse"] == r_["verse"]), None)
onerilen = next(q_["verse"] for q_ in sira6 if q_["eligible"])
onerilen3 = next(q_["verse"] for q_ in sira3 if q_["eligible"] and q_["verse"] != 6)

# kullanilmayan iki "Dinle bak dinle bak" tekrari (yalniz bilgi; kelime zamanlari yazi dokumunden)
tekrar = []
son = [q for q in kelimeleri_oku() if q["start"] > 100.0]
for i in range(0, len(son), 4):
    ws = son[i:i + 4]
    if len(ws) < 4:
        continue
    ia = fi(ws[0]["start"] + 0.02)
    while ia > 0 and not np.all(db_ham[ia - 5:ia] < SEV["esik_dbfs"]):
        ia -= 1
    tekrar.append({"words": [q["text"] for q in ws], "json_times": [[q["start"], q["end"]] for q in ws],
                   "energy_start": r3(ia * DT),
                   "word_median_midi": [kelime_olc(q["start"], q["end"]) for q in ws],
                   "word_start_offsets_ms": [round((q["start"] - ws[0]["start"]) * 1000) for q in ws],
                   "rms_dbfs": round(float(10 * np.log10(np.mean(z["rms"][fi(ws[0]["start"]):fi(ws[-1]["end"])] ** 2))), 1),
                   "note": "outro repeat, not part of the new song form; word times are the transcript's (not refined)"})
ref_w = [round((w_["json_start"] - verses[5]["lines"][3]["words"][0]["json_start"]) * 1000) for w_ in verses[5]["lines"][3]["words"]]

# ================================================================== 6. kita onarimi: "ördekleri" -> "köpekleri"
def kapanis(sol_hece, sag_hece):
    """sol hecenin unlusu ile sag hecenin unlusu arasindaki /k/ kapanisi: 5 ms RMS en dusuk nokta ve sessiz pencere."""
    a = fi(sol_hece["core_end"]); b = fi(sag_hece["core_start"])
    if b <= a:
        a, b = fi(sol_hece["nucleus"]), fi(sag_hece["nucleus"])
    im = a + int(np.argmin(R5[a:b + 1]))
    esik = max(R5[im] + 6.0, -55.0)
    L = im
    while L > a and R5[L - 1] < esik:
        L -= 1
    Rr = im
    while Rr < b and R5[Rr + 1] < esik:
        Rr += 1
    return {"closure_start": r3(L * DT), "closure_end": r3((Rr + 1) * DT), "closure_ms": round((Rr + 1 - L) * DT * 1000, 1),
            "energy_min_t": r3(im * DT), "energy_min_dbfs": round(float(R5[im]), 1),
            "splice_t": r3((L + Rr + 1) / 2 * DT), "level_at_splice_dbfs": round(float(R5[(L + Rr + 1) // 2]), 1),
            "threshold_dbfs": round(float(esik), 1)}


K6 = verses[5]
L2s = K6["lines"][1]["syllables"]; L3s = K6["lines"][2]["syllables"]
ord_ = [s_ for s_ in L2s if s_["word"] == "ördekleri"]          # ör, dek, le, ri
kop = [s_ for s_ in L3s if s_["word"] == "Köpekler"]            # Kö, pek, ler
assert [kucuk(s_["text"]) for s_ in ord_] == ["ör", "dek", "le", "ri"] and [kucuk(s_["text"]) for s_ in kop] == ["kö", "pek", "ler"]
kA = kapanis(kop[1], kop[2]); kB = kapanis(ord_[1], ord_[2])
de = [s_ for s_ in L2s if s_["word"] == "Çiftliğinde"][-1]
on_t = ord_[0]["start"]
A0 = K6["lines"][2]["start"]                                    # "Kö" patlamasinin basladigi an (L3 basi)
pA = f0_olc(A0, kA["splice_t"]); pB = f0_olc(on_t, kB["splice_t"])
# dogal "unlu + k" kapanis sureleri (karsilastirma icin): de|ko (K2 L2), nek|le, dek|le, pek|le
ornek = []
for vv in verses:
    for ln in vv["lines"]:
        S = ln["syllables"]
        for i in range(len(S) - 1):
            eb = S[i]["end_boundary"]
            if eb and eb["consonants"] in ("|k", "k|l", "r|k", "l|k"):
                kk = kapanis(S[i], S[i + 1])
                ornek.append({"verse": vv["verse"], "line": ln["line"], "between": S[i]["text"] + "|" + S[i + 1]["text"],
                              "consonants": eb["consonants"], "closure_ms": kk["closure_ms"], "energy_min_dbfs": kk["energy_min_dbfs"]})
dk = [o for o in ornek if o["consonants"] == "|k"]
yeni_sure = (kA["splice_t"] - A0) ; eski_sure = (kB["splice_t"] - on_t)
onarim = {
    "problem": "verse 6, line 2: the singer sang 'ördekleri' (%.3f-%.3f s) instead of 'köpekleri'" % (ord_[0]["start"], ord_[-1]["end"]),
    "plan": "replace [front_cut .. splice_in_ordekleri] ('ördek' up to the /k/ closure) by [kopek_source_start .. splice_in_kopekler] "
            "('Köpek' up to the /k/ closure) taken from line 3 of the same verse; keep the /k/ burst + 'leri' of 'ördekleri'",
    "splice_in_kopekler": dict(kA, word="Köpekler", meaning="end of 'köpe' + first part of the /k/ closure: take source audio up to splice_t"),
    "splice_in_ordekleri": dict(kB, word="ördekleri", meaning="matching /k/ closure before 'leri': keep target audio from splice_t on"),
    "kopek_source_start": r3(A0), "kopek_source_cut_in": K6["lines"][2]["cut_in"],
    "kopek_part": {"start": r3(A0), "end": kA["splice_t"], "duration": r3(yeni_sure),
                   "median_f0_hz": None if pA[0] is None else round(pA[0], 2), "median_midi": None if pA[1] is None else round(pA[1], 2),
                   "syllables": [{"text": s_["text"], "start": s_["start"], "end": s_["end"], "f0_midi": s_["f0_midi"],
                                  "f0_all_midi": s_["f0_all_midi"], "note": s_["note"]} for s_ in kop[:2]]},
    "ordek_part": {"start": r3(on_t), "end": kB["splice_t"], "duration": r3(eski_sure),
                   "median_f0_hz": None if pB[0] is None else round(pB[0], 2), "median_midi": None if pB[1] is None else round(pB[1], 2),
                   "syllables": [{"text": s_["text"], "start": s_["start"], "end": s_["end"], "f0_midi": s_["f0_midi"],
                                  "f0_all_midi": s_["f0_all_midi"], "note": s_["note"]} for s_ in ord_[:2]]},
    "duration_change_s": r3(yeni_sure - eski_sure),
    "front_cut": {"t": r3(on_t), "level_dbfs": round(float(R5[fi(on_t)]), 1), "boundary": de["end_boundary"],
                  "preceding_vowel_core_end": de["core_end"],
                  "note": "'de' runs straight into 'ör' (vowel to vowel, NO silence here): fade the end of 'de' out over about "
                          "15-25 ms ending at t, then leave a /k/ closure silence before the 'Kö' burst"},
    "natural_k_closure_reference": {"after_vowel_examples": dk,
                                    "median_closure_ms_after_vowel": round(float(np.median([o["closure_ms"] for o in dk])), 1) if dk else None,
                                    "all_k_closures": ornek},
    "pitch_note": "E4 = MIDI 64. 'Kö' is the first syllable of line 3 and is sung lower than the reciting tone (see kopek_part.syllables); "
                  "in the 'dogal' variant the spliced 'kö' will therefore sit about %.1f semitones under the surrounding E4 unless only that "
                  "syllable is corrected" % (64.0 - kop[0]["f0_midi"]),
    "remaining_leri": {"start": kB["splice_t"], "end": ord_[-1]["end"], "syllables": [s_["text"] for s_ in ord_[2:]]},
}

# ================================================================== gurultu tabani
def rms_db(a, b):
    seg = x[int(a * fs):int(b * fs)]
    return float(10 * np.log10(np.mean(seg ** 2) + 1e-20))


bosluk = []
for v in range(6):
    a = verses[v]["lines"][3]["tail_end"] + 0.10; b = verses[v + 1]["lines"][0]["cut_in"] - 0.10
    seg = x[int(a * fs):int(b * fs)]
    bosluk.append({"between_verses": [v + 1, v + 2], "start": r3(a), "end": r3(b), "rms_dbfs": round(rms_db(a, b), 1),
                   "peak_dbfs": round(float(20 * np.log10(np.abs(seg).max() + 1e-12)), 1),
                   "nonzero_sample_ratio": round(float((seg != 0).mean()), 3)})
tum = np.concatenate([x[int(g["start"] * fs):int(g["end"] * fs)] for g in bosluk])
gap_db = float(10 * np.log10(np.mean(tum ** 2) + 1e-20))
soy = np.concatenate([x[int(ln["start"] * fs):int(ln["end"] * fs)] for vv in verses for ln in vv["lines"]])
sung_db = float(10 * np.log10(np.mean(soy ** 2)))
# dize ici kapanislar (otumsuz patlamalilar): band calarken sesin sustugu anlar -> sizinti icin ust sinir
kap = [s_["end_boundary"]["min_level_dbfs"] for _, _, s_ in tum_hece
       if s_["end_boundary"] and any(c in s_["end_boundary"]["consonants"] for c in "ptk")]
# harmonik / harmonik-arasi orani (uzun unlulerde): nefes + olasi sizinti + yanki icin kaba gosterge
NF = 4096; pen = np.hanning(NF); hnr = []
fr = np.fft.rfftfreq(NF, 1 / fs)
for _, _, s_ in tum_hece:
    if s_["core_end"] - s_["core_start"] < 0.16 or s_["f0_hz"] is None:
        continue
    for c in np.arange(s_["core_start"] + NF / fs / 2, s_["core_end"] - NF / fs / 2 + 1e-9, 0.03):
        i0 = int(c * fs) - NF // 2
        mm = (th >= c - 0.04) & (th <= c + 0.04); f0m = f0h[mm]; f0m = f0m[f0m > 0]
        if len(f0m) < 5 or (midi(f0m.max()) - midi(f0m.min())) > 0.3:
            continue                                   # perde oynuyorsa harmonikler yayilir, olcum anlamsizlasir
        f0c = float(np.median(f0m)); P = np.abs(np.fft.rfft(x[i0:i0 + NF] * pen)) ** 2
        for hno in range(1, 9):
            fc = hno * f0c
            if fc < 300 or fc > 2500:
                continue
            tp = P[(fr > fc - 0.12 * f0c) & (fr < fc + 0.12 * f0c)].max()
            ar = np.median(P[(fr > fc + 0.35 * f0c) & (fr < fc + 0.65 * f0c)])
            hnr.append(10 * np.log10(tp / (ar + 1e-20)))
gurultu = {
    "sung_rms_dbfs": round(sung_db, 2),
    "gap_rms_dbfs": round(gap_db, 2),
    "noise_floor_db_re_sung_rms": round(gap_db - sung_db, 1),
    "one_lsb_16bit_dbfs": round(float(20 * np.log10(1 / 32768)), 1),
    "gaps": bosluk,
    "median_gap_rms_dbfs": round(float(np.median([g["rms_dbfs"] for g in bosluk])), 1),
    "worst_gap_rms_dbfs": round(float(np.max([g["rms_dbfs"] for g in bosluk])), 1),
    "worst_gap_peak_dbfs": round(float(np.max([g["peak_dbfs"] for g in bosluk])), 1),
    "interpretation": "Between verses the stem sits at about the 16-bit quantisation floor (1 LSB = -90.3 dBFS); a few isolated blips "
                      "(see gaps[].peak_dbfs) raise the pooled RMS. The stem is effectively gated: no audible band bleed and no long "
                      "reverb tail in the gaps.",
    "in_line_stop_closures": {"count": len(kap), "median_level_dbfs": round(float(np.median(kap)), 1),
                              "p25_p75_dbfs": [round(float(np.percentile(kap, 25)), 1), round(float(np.percentile(kap, 75)), 1)],
                              "min_level_dbfs": round(float(np.min(kap)), 1),
                              "max_level_dbfs": round(float(np.max(kap)), 1),
                              "median_db_re_sung_rms": round(float(np.median(kap)) - sung_db, 1),
                              "meaning": "level of the stem inside voiceless stop closures WITHIN lines (the band was playing there in the "
                                         "original mix): an upper bound for instrument bleed at those instants"},
    "tail_after_last_word_ms": [vv["lines"][3]["ending"]["decay_ms_vowel_end_to_energy_end"] for vv in verses],
    "harmonic_to_interharmonic_db": {"frames": len(hnr), "median": round(float(np.median(hnr)), 1),
                                     "p10": round(float(np.percentile(hnr, 10)), 1),
                                     "meaning": "steady vowels, 300-2500 Hz: harmonic peak vs level between harmonics; a rough "
                                                "indicator of breath + possible bleed/reverb UNDER the voice (cannot separate them)"},
    "unverified": "bleed or reverb under the sung vowels themselves cannot be measured from the stem alone and was not checked by ear",
}

# ================================================================== ozet + yazim
from collections import Counter
bayrakli = [(v_, d_, w_) for v_, d_, w_ in tum_kelime if w_["flag"]]
tutmayan = [(v_, d_, w_) for v_, d_, w_ in tum_kelime if not w_["blind_check"]["count_matches"]]
turler = Counter(s_["end_boundary"]["kind"] for _, _, s_ in tum_hece if s_["end_boundary"])
ozet = {
    "verses": 7, "lines": 28, "words": len(tum_kelime), "syllables": len(tum_hece),
    "flagged_words": len(bayrakli),
    "flagged_words_list": ["K%d L%d %s" % (v_, d_, w_["text"]) for v_, d_, w_ in bayrakli],
    "flagged_syllables": sum(1 for _, _, s_ in tum_hece if s_["flag"]),
    "flag_meaning": "a syllable boundary inside the word has NO acoustic evidence and was placed by rule (midpoint of the merged vowel). "
                    "All cases are 'çift-li-ği' / 'Çift-li-ğin-de': the soft g between two identical vowels is one long [i:].",
    "boundary_kinds": dict(turler),
    "blind_peak_count_mismatch_words": len(tutmayan),
    "blind_peak_count_mismatch_list": ["K%d L%d %s (found %d, expected %d)" % (v_, d_, w_["text"], w_["blind_check"]["nuclei_detected"],
                                                                                 w_["syllables_expected"]) for v_, d_, w_ in tutmayan],
    "blind_check_meaning": "the plain method (peaks of the smoothed voiced-energy envelope inside the word) did not find the expected number "
                           "of nuclei in these words; they were NOT split proportionally: boundaries come from the alignment-guided cues "
                           "(end_boundary.kind) instead",
    "noise_floor_db_re_sung_rms": gurultu["noise_floor_db_re_sung_rms"],
    "verse6_splice_in_kopekler": kA["splice_t"], "verse6_splice_in_ordekleri": kB["splice_t"],
    "lines_with_faint_pre_noise": [{"verse": vv["verse"], "line": ln["line"], "start": ln["start"], "onset_strong": ln["onset_strong"],
                                    "ms": round((ln["onset_strong"] - ln["start"]) * 1000)}
                                   for vv in verses for ln in vv["lines"] if ln["onset_strong"] - ln["start"] > 0.03],
    "verse6_l4_recommended_donor_verse": onerilen, "verse6_l4_donor_runner_ups": [q_["verse"] for q_ in sira6 if q_["eligible"]][1:3],
    "vowel_onset_spread_ms": {"L4_syllables_max_minus_min_over_7_verses": [int(round(q_)) for q_ in np.ptp(np.array(
        [[s_["vowel_onset"] - vv["lines"][3]["syllables"][0]["vowel_onset"] for s_ in vv["lines"][3]["syllables"]] for vv in verses]) * 1000, 0)]},
    "other_defects": [("K%d L4: " % (vv["verse"])) + vv["lines"][3]["defect"] for vv in verses if vv["lines"][3].get("defect")],
}
sema = {
    "time_base": "seconds on the timeline of dinle_2_vokal.wav (= dinle_2.mp3); 44.1 kHz mono",
    "verses[].lines[]": {
        "start / end": "energy onset / decay of the sung line (10 ms RMS crossing sung_rms - 45 dB; inside a verse: around the energy dip between lines)",
        "onset_strong": "first instant the 10 ms RMS exceeds sung_rms - 20 dB (ignores faint pre-noise; 'start' can lie up to 120 ms "
                        "earlier where a faint breath/noise precedes the first consonant: see summary.lines_with_faint_pre_noise)",
        "first_vowel_onset": "vowel_onset of the first syllable: the instant to put on the bar line",
        "cut_in / cut_out": "safe cut instants (energy minima). L1|L2 and L2|L3 share one instant; L3.cut_out and L4.cut_in are null because "
                            "L3+L4 are one continuous chunk; cut_in_info / cut_out_info give level (dBFS) and quiet_window_ms of the dip",
        "tail_end (L4)": "where the release/reverb tail reaches the noise floor; L4.cut_out = tail_end + 20 ms",
        "ending (L4)": "what follows the last vowel; extra_voiced_sound flags a non-lyric after-sound",
    },
    "verses[].chunks[]": "the three pieces to cut per verse: [L1], [L2], [L3+L4]. fade_in_max_ms = start - cut_in and "
                         "fade_out_max_ms = cut_out - end: keep fades inside these so they never touch the sung sound "
                         "(some gaps between lines are only 5-15 ms wide)",
    "syllables[]": {
        "start / end": "contiguous tiling of the line; boundary = end_boundary.t",
        "end_boundary.kind": "dip = energy minimum in the consonant between the two vowels (reliable); spectral = no dip, largest spectral "
                             "change (nasal release, glide, vowel-to-vowel); midpoint = no acoustic boundary, merged vowel split in the middle (flag)",
        "vowel_onset": "first instant the 100-1000 Hz band (f0 + F1; 20 ms envelope) comes within 6 dB of its peak in the syllable: "
                       "skips voiceless frication, bursts and voiced closures; equals the syllable start for sonorant onsets. "
                       "Beat-alignment point (approximate, see summary.vowel_onset_spread_ms)",
        "nucleus / core_start / core_end": "vowel peak and the voiced region within 6 dB of it",
        "f0_hz / f0_midi": "median f0 of the vowel core (pyworld harvest, 150-700 Hz, 5 ms) = the sung pitch of the syllable",
        "f0_all_*": "median over ALL voiced frames in [start,end) (includes consonant dips and scoops)",
        "f0_dio_midi": "same core, dio+stonemask (cross-check)",
        "voiced_ratio": "voiced 5 ms frames / all frames in [start,end)",
        "flag": "true when its start or end boundary was placed by rule",
    },
    "words[]": {"flag": "true when a boundary inside the word was placed by rule",
                "blind_check": "result of the plain envelope-peak nuclei count (cross-check only)"},
}
cikti = {
    "description": "Vocal segmentation of dinle_2_vokal.wav: 7 verses x 4 lines, cut points, syllables with pitch, verse-6 repair data, noise floor",
    "source": {"vocal": "dinle_2_vokal.wav", "words": "dinle_2_words.json",
               "scripts": ["kod/calistir.sh", "kod/ortak.py", "kod/ozellik.py", "kod/dize.py", "kod/hizala.py", "kod/kesim.py",
                           "kod/dogrula.py", "kod/ciz.py", "kod/cizhepsi.sh"]},
    "not_verified_by_ear": "Everything here is measured by code and checked on spectrogram plots (cizim/*.png). Nobody listened to the audio.",
    "schema": sema,
    "summary": ozet,
    "levels": {"sung_rms_dbfs": round(SEV["soylenen_rms_dbfs"], 2), "onset_threshold_dbfs": round(SEV["esik_dbfs"], 2),
               "gap_floor_dbfs": round(SEV["taban_dbfs"], 2)},
    "noise_floor": gurultu,
    "verses": verses,
    "verse6_repair": onarim,
    "l4_comparison": {"per_verse": l4, "recommended_donor_verse_for_verse6": onerilen,
                      "ranking": sira6, "score_formula": SKOR,
                      "verse3_note": "verse 3's own L4 ends with an extra voiced after-sound (lines[3].ending). Either cut it at "
                                     "cut_out_before_extra_sound (the word then ends in an unreleased k) or reuse another L4 / final 'bak'",
                      "ranking_for_verse3": sira3, "recommended_donor_verse_for_verse3": onerilen3,
                      "final_word_only_alternative": "instead of the whole L4, only the last 'bak' can be replaced: cut at "
                                                     "per_verse[].b_closure_before_final_bak.t in both verses (verse 6's closure is silent, "
                                                     "the donors' closures are voiced at about -25..-35 dBFS, so use a 10 ms crossfade)",
                      "verse6_problem": "final 'bak' of verse 6 is on %s (MIDI %.2f) instead of C4" % (l4[5]["final_bak_note"], l4[5]["final_bak_midi"]),
                      "how_to_reuse": "cut verse 6's chunk [L3+L4] at its own L3|L4 junction (lines[2].end) and continue with the donor's L4 "
                                      "from the donor's L3|L4 junction (lines[3].start) to its cut_out, with a short (about 10 ms) crossfade: "
                                      "neither junction is silent (see l3_l4_junction.level_dbfs)",
                      "outro_repeats_not_used": tekrar, "verse6_word_start_offsets_ms_json": ref_w},
}
json.dump(cikti, open(os.path.join(K, "kesim.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1, allow_nan=False)

print("kelime %d  hece %d  FLAG (kuralla konan sinir) %d kelime  |  kor sayim tutmayan %d kelime" % (
    len(tum_kelime), len(tum_hece), len(bayrakli), len(tutmayan)))
print("sinir turleri:", dict(turler))
print("gurultu tabani: bosluk %.1f dBFS, soylenen %.1f dBFS -> %.1f dB" % (gap_db, sung_db, gap_db - sung_db))
for g in bosluk:
    print("   bosluk", g)
print("dize ici kapanis ortanca %.1f dBFS (%d adet)  |  harmonik/ara ortanca %.1f dB" % (np.median(kap), len(kap), np.median(hnr)))
print("ek yeri Köpekler: %s" % kA); print("ek yeri ördekleri: %s" % kB)
print("köpek parcasi %.3f s (midi %.2f), ördek parcasi %.3f s (midi %.2f)" % (yeni_sure, pA[1], eski_sure, pB[1]))
for r_ in l4:
    print("K%d L4 kelime midi %s  hece midi %s  sure %.3f  rms %.1f  ek ses %s  %s" % (
        r_["verse"], r_["word_median_midi"], r_["syllable_midi"], r_["duration_start_to_energy_end"], r_["rms_dbfs"],
        r_["extra_voiced_sound"], r_["vs_verse6"] and (r_["vs_verse6"]["score"], r_["vs_verse6"]["eligible"])))
print("3. kita icin verici sirasi:", [(q_["verse"], q_["score"], q_["eligible"]) for q_ in sira3])
print("onerilen verici kita:", onerilen)
for tk in tekrar:
    print("tekrar:", tk["json_times"][0][0], tk["word_median_midi"], tk["word_start_offsets_ms"], tk["rms_dbfs"])
