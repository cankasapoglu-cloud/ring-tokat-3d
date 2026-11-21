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
R5 = zarf(None, None, 5)         # tam bant, 5 ms (ek yeri / kapanis cukuru icin)
FLX = np.convolve(z["fluxabs"], np.hanning(7) / np.hanning(7).sum(), "same")
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


def cukur_merkezi(i, a, b, pay=2.0):
    """i karesi cevresinde E12 < E12[i]+pay olan bitisik pencerenin ortasi ([a,b] icinde)."""
    L = i
    while L > a and E12[L - 1] < E12[i] + pay:
        L -= 1
    R = i
    while R < b and E12[R + 1] < E12[i] + pay:
        R += 1
    return (L + R) // 2, (R - L + 1) * DT


LMEL = z["logmel"].astype(np.float64)


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


def sinir_bul(sol, sag):
    """sol / sag: ardisik iki hecenin harf yapisi (hizalamadan). Donus: sinir sozlugu."""
    vs_j, ve_j = sol["vowel"]["bas"], sol["vowel"]["bit"]
    vs_n, ve_n = sag["vowel"]["bas"], sag["vowel"]["bit"]
    a = fi(max(ve_j - 0.03, (vs_j + ve_j) / 2)); b = fi(min(vs_n + 0.03, (vs_n + ve_n) / 2))
    if b <= a + 1:
        a, b = fi((vs_j + ve_j) / 2), fi((vs_n + ve_n) / 2)
    unsuz = "".join(s_["harf"] for s_ in sol["coda"]) + "|" + "".join(s_["harf"] for s_ in sag["onset"])
    out = {"consonants": unsuz}
    iR = a + int(np.argmin(E12[a:b + 1])); ER = E12[iR]
    adaylar = []
    if sag["onset"]:
        wa = max(a, fi(sag["onset"][-1]["bas"] - 0.025)); wb = min(b, fi(sag["onset"][-1]["bit"] + 0.025))
        if wb > wa:
            iW = wa + int(np.argmin(E12[wa:wb + 1]))
            if E12[iW] <= ER + 6.0:
                adaylar.append((iW, wa, wb, "onset"))
    else:
        wa, wb = a, b
    adaylar.append((iR, a, b, "deepest"))
    sol_a = fi(vs_j - 0.02); sag_b = fi(ve_n + 0.02)
    ayni_unlu_g = (unsuz == "|ğ" and sol["vowel"]["harf"] == sag["vowel"]["harf"])
    if ayni_unlu_g:
        # "li-ği", "li-ğin": yumusak g iki AYNI unlu arasinda -> tek uzun unlu, akustik sinir yok.
        # (Enerji / spektrum olcutleri burada komsu unsuze gecisi yakaliyor: bilerek kullanilmiyor.)
        out.update({"t": (vs_j + ve_n) / 2, "kind": "midpoint", "depth_db": None,
                    "merged_vowel": [round(vs_j, 4), round(ve_n, 4)]})
        return out
    for i0, lo, hi, yer in adaylar:
        # gercek cukur derinligi: cukurun iki yanindaki (unlu) tepelerin dusugu - cukur
        derinlik = float(min(E12[sol_a:i0 + 1].max(), E12[i0:sag_b + 1].max()) - E12[i0])
        if derinlik >= 3.0:
            ic, gen = cukur_merkezi(i0, lo, hi)
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
    # unsuz var ama enerji cukuru yok (n|l, y, v ...): unsuz bolgesindeki en buyuk spektral degisim
    lo, hi = (wa, wb) if (sag["onset"] and wb > wa) else (a, b)
    ip = lo + int(np.argmax(FLX[lo:hi + 1]))
    taban = float(np.median(np.concatenate([FLX[fi(vs_j):fi(ve_j) + 1], FLX[fi(vs_n):fi(ve_n) + 1]])))
    oran = float(FLX[ip] / (taban + 1e-9))
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
                  "syllables_expected": beklenen, "nuclei_detected": len(tep), "nuclei_count_mismatch": bool(say_tutmadi),
                  "flag": bool(flag), "note": "; ".join(neden) if neden else None,
                  "boundary_kinds": turler,
                  "blind_vs_final_max_dev_ms": None if sapma is None else round(sapma, 1),
                  "f0_hz": r3(f0m), "f0_midi": None if f0mi is None else round(f0mi, 2), "voiced_ratio": round(vr, 3)}
            words.append(wd); tum_kelime.append((v + 1, d + 1, wd))
            for h in wh:
                a, b = h["start"], h["end"]
                ia, ib = fi(a), fi(b)
                # cekirdek: sesli karelerde E30 tepesi
                seg = np.where(VOI[ia:ib + 1], E30[ia:ib + 1], -200.0)
                ip = ia + int(np.argmax(seg)); tepe = E30[ip]
                L = ip
                while L > ia and E30[L - 1] > tepe - 6 and VOI[L - 1]:
                    L -= 1
                R = ip
                while R < ib and E30[R + 1] > tepe - 6 and VOI[R + 1]:
                    R += 1
                f0m, f0mi, vr, iqr = f0_olc(a, b)
                c0m, c0mi, _, _ = f0_olc(L * DT, (R + 1) * DT)
                d0m, d0mi, dvr, _ = f0_olc(a, b, f0s)
                eb = h["end_boundary"]
                sd = {"text": h["text"], "word": h["word"], "word_index": h["word_i"], "index_in_word": h["syl_i"],
                      "start": r3(a), "end": r3(b), "duration": r3(b - a),
                      "f0_hz": None if f0m is None else round(f0m, 2), "f0_midi": None if f0mi is None else round(f0mi, 2),
                      "note": None if f0mi is None else nota_adi(f0mi),
                      "cents_from_note": None if f0mi is None else int(round((f0mi - round(f0mi)) * 100)),
                      "voiced_ratio": round(vr, 3), "f0_iqr_semitones": None if iqr is None else round(iqr, 2),
                      "nucleus": r3(ip * DT), "core_start": r3(L * DT), "core_end": r3((R + 1) * DT),
                      "f0_core_hz": None if c0m is None else round(c0m, 2), "f0_core_midi": None if c0mi is None else round(c0mi, 2),
                      "f0_dio_midi": None if d0mi is None else round(d0mi, 2),
                      "peak_dbfs": round(float(db_ham[ia:ib + 1].max()), 1),
                      "rms_dbfs": round(float(10 * np.log10(np.mean(z["rms"][ia:ib + 1] ** 2) + 1e-12)), 1),
                      "end_boundary": None if eb is None else {k_: (r3(val) if k_ == "t" else val) for k_, val in eb.items()},
                      "flag": bool(eb is not None and eb["kind"] in ("midpoint", "model")) or bool(
                          h["syl_i"] > 0 and wh[h["syl_i"] - 1]["end_boundary"]["kind"] in ("midpoint", "model"))}
                syls.append(sd); tum_hece.append((v + 1, d + 1, sd))
        f0m, f0mi, vr, _ = f0_olc(L_start, L_end)
        ia, ib = fi(L_start), fi(L_end)
        ld = {"line": d + 1, "text": dize_sozleri(v)[d], "start": r3(L_start), "end": r3(L_end), "duration": r3(L_end - L_start),
              "cut_in": r3(dz["kesim_giris"]), "cut_out": r3(dz["kesim_cikis"]),
              "cut_in_info": dz.get("giris_cukuru"), "cut_out_info": dz.get("cikis_cukuru"),
              "rms_dbfs": round(float(10 * np.log10(np.mean(z["rms"][ia:ib + 1] ** 2) + 1e-12)), 1),
              "peak_dbfs": round(float(db_ham[ia:ib + 1].max()), 1),
              "f0_hz": r3(f0m), "f0_midi": None if f0mi is None else round(f0mi, 2),
              "words": words, "syllables": syls}
        if d == 3:
            ld["tail_end"] = r3(dz["kuyruk_bitis"])
        if d == 1 and v == 5:
            ld["text_as_sung"] = dize_sozleri(v)[d]; ld["text_intended"] = L2_OLMASI_GEREKEN[v]
        vout["lines"].append(ld)
    # parcalar (kesilecek butunler)
    Ls = vout["lines"]
    vout["chunks"] = [
        {"lines": [1], "cut_in": Ls[0]["cut_in"], "start": Ls[0]["start"], "end": Ls[0]["end"], "cut_out": Ls[0]["cut_out"]},
        {"lines": [2], "cut_in": Ls[1]["cut_in"], "start": Ls[1]["start"], "end": Ls[1]["end"], "cut_out": Ls[1]["cut_out"]},
        {"lines": [3, 4], "cut_in": Ls[2]["cut_in"], "start": Ls[2]["start"], "end": Ls[3]["end"], "cut_out": Ls[3]["cut_out"],
         "l4_start_offset": r3(Ls[3]["start"] - Ls[2]["start"])}]
    vout["start"] = Ls[0]["start"]; vout["end"] = Ls[3]["end"]
    verses.append(vout)

json.dump({"verses": verses, "levels": SEV}, open(os.path.join(K, "ara", "kesim_ham.json"), "w", encoding="utf8"),
          ensure_ascii=False, indent=1)

# ------------------------------------------------------------------ ozet
nk = len(tum_kelime); nf = sum(1 for _, _, w_ in tum_kelime if w_["flag"])
print("kelime %d  hece %d  FLAG %d" % (nk, len(tum_hece), nf))
from collections import Counter
print("sinir turleri:", Counter(s["end_boundary"]["kind"] for _, _, s in tum_hece if s["end_boundary"]))
for v_, d_, w_ in tum_kelime:
    if w_["flag"] or w_["nuclei_count_mismatch"] or "spectral" in w_["boundary_kinds"] or (w_["blind_vs_final_max_dev_ms"] or 0) > 40:
        print("K%d L%d %-12s bekl %d bulunan %d  turler %s  sapma %s  %s %s" % (
            v_, d_, w_["text"], w_["syllables_expected"], w_["nuclei_detected"], w_["boundary_kinds"],
            w_["blind_vs_final_max_dev_ms"], "FLAG" if w_["flag"] else "", "SAYIM" if w_["nuclei_count_mismatch"] else ""))
print("sayim tutmayan kelime:", sum(1 for _, _, w_ in tum_kelime if w_["nuclei_count_mismatch"]))
