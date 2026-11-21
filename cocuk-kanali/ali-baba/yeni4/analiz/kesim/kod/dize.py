#!/usr/bin/env python3
"""Bolum (dize) sinirlari ve kesim noktalari - yalniz ayrilmis vokalin kendi zarfindan (v2_2).
yeni3/analiz/kesim/kod/dize.py'den uyarlandi; v2_2'nin iki ZOR kesimi icin ozel olcum eklendi.

Zarflar (2 ms adim): db = 10 ms RMS (6 ms yumusatma), R5 = 5 ms RMS, F2 = 1-3.4 kHz bandi (23 ms STFT), HI = 4-12 kHz.
Seviyeler: soylenen_rms (saklanan kelime araliklarinin RMS'i), ESIK = soylenen - 45 dB.

Sinirlar (kita basina):
  L1 basi     : unluye cikan son yukselisin basladigi an (oncesinde nefes varsa ayrica raporlanir).
  L1 | L2     : "var," ile "çiftliğinde"nin 'ç' kapanisi arasindaki cukur g. bitis/baslangic = g'nin iki yaninda
                max(ESIK, cukur + 6 dB) esigini asan son / ilk an. kesim = cukurun ortasi.
  L2 sonu (a) : "var" dogrudan soylenen hayvan sesine baglaniyor. t_kapanis = "var"in unlu + r govdesinin bittigi an
                (1-3.4 kHz bandi, "var" unlusunun tepesinin 12 dB altina ILK dustugu an; en dik dususle capraz kontrol).
                Hayvan sesinin unlu baslangici = ayni bandin yeniden yukseldigi an. Aradaki ses turu (genizsi m /
                sessizlik / h surtunmesi) ve duzeyi olculur.
  diye basi(b): ikinci hayvan sesinin bittigi yer ile 'd' patlamasi arasindaki cukur.
  diye | L4   : kesintisiz (yalniz bilgi).
  L4 sonu     : son kelimenin govdesi (soylenen - 20 dB) bittikten sonra duzeyin soylenen - 24 dB altina inip en az
                60 ms orada kaldigi an (bitis). Ondan sonra ayri bir ses (nefes verme / puf) varsa "ek_ses" olarak
                raporlanir ve varsayilan kesimin DISINDA kalir."""
import numpy as np
from ortak import kelimeleri_oku, kitalari_esle, ozellik, kita_vuruslari, BEAT, BAR

z = ozellik(); t = z["t"]; DT = float(t[1] - t[0])
db_ham = 20 * np.log10(z["rms"] + 1e-9)
db = np.convolve(db_ham, np.ones(3) / 3, "same")          # 6 ms hafif yumusatma
F2 = 10 * np.log10(z["b_f2"] + 1e-12)                      # 1-3.4 kHz
HI = 10 * np.log10(z["b_hi"] + 1e-12)                      # 4-12 kHz
LOW = 10 * np.log10(z["b_low"] + 1e-12)                    # 100-1000 Hz
TH = z["th"]; F0H = z["f0h"]


def fi(x):
    return int(round(x / DT))


def seviyeler(kita):
    p = []
    for v in kita:
        for ad in ("L1", "L2", "diye", "L4"):
            for q in v[ad]:
                p.append(z["rms"][fi(q["start"]):fi(q["end"])] ** 2)
    return float(10 * np.log10(np.mean(np.concatenate(p))))


def cukur(a, b, ESIK):
    """[a,b] araliginda en dusuk nokta g; iki yaninda max(ESIK, cukur+6) esigini asan son/ilk an; en dusuk 6 dB'lik
    pencerenin ortasi."""
    ia, ib = fi(a), fi(b)
    g = ia + int(np.argmin(db[ia:ib + 1]))
    esik = max(ESIK, db[g] + 6.0)
    L = g
    while L > ia - fi(0.25) and db[L] < esik:
        L -= 1
    R = g
    while R < ib + fi(0.25) and db[R] < esik:
        R += 1
    # en dusuk 3 dB'lik bitisik pencerenin ortasi (kesim ani)
    e3 = db[g] + 3.0
    l3 = g
    while l3 > L + 1 and db[l3 - 1] < e3:
        l3 -= 1
    r3_ = g
    while r3_ < R - 1 and db[r3_ + 1] < e3:
        r3_ += 1
    gm = (l3 + r3_) / 2 * DT
    return {"g": g * DT, "orta": gm, "onceki_bitis": (L + 1) * DT, "sonraki_baslangic": R * DT,
            "duzey_dbfs": float(db_ham[fi(gm)]), "en_dusuk_dbfs": float(db_ham[ia:ib + 1].min()),
            "esik_dbfs": float(esik), "esik_alti_ms": (R - L - 1) * DT * 1000}


def hi_tepe(a, b):
    ia, ib = fi(a), fi(b)
    return (ia + int(np.argmax(HI[ia:ib + 1]))) * DT


def son_gecis(i_bas, i_son, esik, yon):
    """i_bas'tan i_son'a dogru yururken F2 zarfinin esigi yon (-1: altina, +1: ustune) gectigi ilk kare (kesirli)."""
    adim = 1 if i_son > i_bas else -1
    for i in range(i_bas, i_son, adim):
        a, b = F2[i], F2[i + adim]
        if (yon < 0 and a >= esik > b) or (yon > 0 and a < esik <= b):
            return i + adim * (a - esik) / (a - b)
    return None


def l2_sonu(v, kita, sung):
    """Zor kesim (a): "var" -> soylenen hayvan sesi."""
    var = kita[v]["L2"][-1]; s1 = kita[v]["ses"][0]
    # "var" unlusunun tepesi (F2 bandi), kelime araliginin ilk 2/3'unde
    ia, ib = fi(var["start"] + 0.01), fi(var["start"] + 0.20)
    ip = ia + int(np.argmax(np.convolve(F2, np.ones(5) / 5, "same")[ia:ib + 1]))
    tepe = float(np.max(F2[ia:ib + 1]))
    esik = tepe - 12.0
    # kapanis: tepeden sonra F2 bandinin esigin altina ilk dustugu ve en az 20 ms altinda kaldigi an
    lim = fi(s1["start"] + 0.12)
    i = ip; tk = None
    while i < lim:
        if F2[i] >= esik > F2[i + 1] and np.all(F2[i + 1:i + 1 + fi(0.02)] < esik):
            tk = (i + (F2[i] - esik) / (F2[i] - F2[i + 1])) * DT
            break
        i += 1
    assert tk is not None, ("L2 sonu bulunamadi", v + 1)
    # capraz kontrol: en dik dusus (10 ms'lik fark) [tk-60ms, tk+40ms] icinde
    ja, jb = fi(tk - 0.06), fi(tk + 0.04)
    d10 = F2[ja + 5:jb + 5] - F2[ja:jb]
    t_dik = (ja + int(np.argmin(d10)) + 2.5) * DT
    ka = fi(tk)
    # aradaki sesin turu: tk'den sonraki 50 ms (5 ms RMS, bantlar)
    w50 = slice(ka + fi(0.008), ka + fi(0.058))
    ort50 = float(10 * np.log10(np.mean(10 ** (db_ham[w50] / 10))))
    low50 = float(np.mean(LOW[w50])); f250 = float(np.mean(F2[w50])); hi50 = float(np.mean(HI[w50]))
    var_low = float(np.median(LOW[ip - fi(0.03):ip + fi(0.06)]))
    # sessiz bosluk: tk'den sonraki 150 ms icinde, 10 ms RMS'in soylenen - 12 dB altinda kaldigi ilk bitisik bolge
    lim2 = ka + fi(0.15)
    sb = [i for i in range(ka, lim2) if db_ham[i] < sung - 12.0]
    bos_a = bos_b = None
    if sb:
        bos_a = sb[0]; bos_b = bos_a
        while bos_b + 1 < lim2 and (db_ham[bos_b + 1] < sung - 12.0 or db_ham[bos_b + 1:bos_b + 1 + fi(0.012)].min() < sung - 12.0):
            bos_b += 1
    bosluk_ms = 0.0 if bos_a is None else (bos_b - bos_a + 1) * DT * 1000
    if bosluk_ms >= 30:
        tur = "pause"
    elif low50 - f250 > 12.0 and low50 - hi50 > 25.0:
        tur = "nasal_murmur"         # m: sesli, yalniz alcak bant (1 kHz alti)
    else:
        tur = "fricative"            # h: genis bantli surtunme
    # hayvan sesinin BASLADIGI an ve UNLUSUNUN basladigi an (ture ozel)
    if tur == "pause":
        t_ses = (bos_b + 1) * DT                                     # sessizlikten sonra duzeyin soylenen - 12 dB'yi astigi an
        j = bos_b
        while j < lim2 + fi(0.2) and not (db[j] >= sung - 6.0 and np.all(db[j:j + fi(0.03)] >= sung - 9.0)):
            j += 1
        tu = j * DT
    elif tur == "nasal_murmur":
        t_ses = tk
        j = ka + 2; tu = None
        while j < fi(tk + 0.35):
            if F2[j] < esik <= F2[j + 1] and np.mean(F2[j + 1:j + 1 + fi(0.03)] >= esik) > 0.8:
                tu = (j + (esik - F2[j]) / (F2[j + 1] - F2[j])) * DT
                break
            j += 1
    else:
        t_ses = tk
        j = ka + 2
        while j < fi(tk + 0.35) and not (LOW[j] >= var_low - 6.0 and np.all(LOW[j:j + fi(0.03)] >= var_low - 8.0)):
            j += 1
        tu = j * DT
    assert tu is not None, ("hayvan unlusu bulunamadi", v + 1)
    kb = fi(tu)
    seg = db_ham[ka:kb + 1]
    m = (TH >= tk) & (TH < tu)
    sesli = float((F0H[m] > 0).mean()) if m.any() else 0.0
    # "var" icindeki en dusuk an (r vurusu / kapanis): tk +- 25 ms
    da, dbb = fi(tk - 0.025), fi(tk + 0.025)
    gi = da + int(np.argmin(db_ham[da:dbb + 1]))
    # tk'den hayvan unlusune kadar en dusuk an (sessizlik varsa kesim icin en iyi an)
    gm = ka + int(np.argmin(db_ham[ka:kb + 1]))
    return {"t_close": tk, "t_steepest_fall": t_dik, "animal_sound_start": t_ses, "animal_vowel_onset": tu, "between_kind": tur,
            "between_ms": (tu - tk) * 1000, "between_mean_dbfs": float(10 * np.log10(np.mean(10 ** (seg / 10)))),
            "between_min_dbfs": float(seg.min()), "between_min_t": gm * DT,
            "first50ms_mean_dbfs": ort50, "first50ms_low_minus_f2_db": low50 - f250, "first50ms_low_minus_hi_db": low50 - hi50,
            "between_voiced_ratio": sesli, "silent_gap_ms": bosluk_ms,
            "silent_gap": None if bos_a is None or bosluk_ms < 30 else [bos_a * DT, (bos_b + 1) * DT],
            "dip_t": gi * DT, "dip_dbfs": float(db_ham[gi]), "var_f2_peak_db": tepe,
            "level_at_close_dbfs": float(db_ham[fi(tk)])}


def kalici_dusus(i0, i1, esik, sure=0.15):
    say = 0
    for j in range(i0, i1):
        if db[j] < esik:
            say += 1
            if say * DT >= sure:
                return j - say + 1
        else:
            say = 0
    return i1


def dizeleri_bul(kita=None):
    if kita is None:
        kita = kitalari_esle(kelimeleri_oku())
    sung = seviyeler(kita)
    ESIK = sung - 45.0
    vd = kita_vuruslari()
    out = []
    for v in range(7):
        k = kita[v]; r = {}
        # ---------------- L1 basi
        w0 = k["L1"][0]
        ia = fi(w0["start"] - 0.10); ib = fi(w0["start"] + 0.08)
        guclu = ia
        while guclu < ib and db[guclu] < sung - 10.0:
            guclu += 1
        i = guclu
        while i > guclu - fi(0.15) and db[i] > sung - 25.0:
            i -= 1
        bas = (i + 1) * DT
        # kesim_giris: baslangictan 10-60 ms once en dusuk an
        ja, jb = fi(bas - 0.06), fi(bas - 0.01)
        j = ja + int(np.argmin(db[ja:jb + 1]))
        # nefes: baslangictan onceki 0.8 s icinde duzeyi (soylenen - 32 dB) ustunde olan bolge
        na, nb = fi(bas - 0.8), fi(bas - 0.01)
        ust = np.where(db[na:nb] > sung - 32.0)[0]
        nefes = None
        if len(ust) and (ust[-1] - ust[0]) * DT > 0.08:
            n0, n1 = na + ust[0], na + ust[-1]
            # nefesten once sessiz an: n0'dan geriye soylenen - 40 dB altina inen ilk an
            q = n0
            while q > fi(bas - 1.2) and db[q] > sung - 40.0:
                q -= 1
            nefes = {"start": n0 * DT, "end": (n1 + 1) * DT, "peak_dbfs": float(db_ham[n0:n1 + 1].max()),
                     "rms_dbfs": float(10 * np.log10(np.mean(z["rms"][n0:n1 + 1] ** 2))),
                     "cut_in_with_breath": (q - fi(0.02)) * DT, "level_at_cut_in_with_breath_dbfs": float(db_ham[q - fi(0.02)])}
        r["L1"] = {"baslangic": bas, "guclu_baslangic": guclu * DT, "kesim_giris": j * DT,
                   "giris_duzey_dbfs": float(db_ham[j]), "nefes": nefes}
        # ---------------- L1 | L2
        pe = k["L1"][-1]["end"]; ns = k["L2"][0]["start"]
        tp = hi_tepe(ns - 0.05, ns + 0.07)                # 'ç' surtunmesinin tepesi
        c = cukur(pe - 0.06, tp, ESIK)
        r["L1"].update({"bitis": c["onceki_bitis"], "kesim_cikis": c["orta"], "cikis_cukuru": c})
        r["L2"] = {"baslangic": c["sonraki_baslangic"], "kesim_giris": c["orta"], "giris_cukuru": c, "c_hi_tepe": tp}
        # ---------------- L2 sonu (zor kesim a)
        a_ = l2_sonu(v, kita, sung)
        r["L2"].update({"bitis": a_["t_close"], "zor_kesim": a_})
        r["ses"] = {"baslangic": a_["animal_sound_start"], "hayvan_unlu_baslangic": a_["animal_vowel_onset"]}
        # ---------------- diye basi (zor kesim b)
        dy = k["diye"][0]
        c2 = cukur(dy["start"] - 0.15, dy["start"] + 0.04, ESIK)
        # ikinci hayvan sesinin govdesinin bittigi an: cukurdan geriye, duzeyin (soylenen - 9 dB) ustune ciktigi son an
        q = fi(c2["g"])
        while q > fi(dy["start"] - 0.6) and db[q] < sung - 9.0:
            q -= 1
        # patlama / unlu baslangici: cukurdan ileriye, duzeyin (soylenen - 9 dB) ustune ciktigi ilk an
        p = fi(c2["g"])
        while p < fi(dy["start"] + 0.15) and db[p] < sung - 9.0:
            p += 1
        r["ses"].update({"bitis": c2["onceki_bitis"], "govde_bitis": (q + 1) * DT})
        r["diye"] = {"baslangic": c2["sonraki_baslangic"], "kesim_giris": c2["orta"], "giris_cukuru": c2,
                     "guclu_baslangic": p * DT,
                     "zor_kesim": {"animal_body_end": (q + 1) * DT, "dip_t": c2["g"], "dip_center": c2["orta"],
                                   "dip_dbfs": c2["en_dusuk_dbfs"], "onset": c2["sonraki_baslangic"], "strong_onset": p * DT,
                                   "gap_body_to_strong_onset_ms": (p - q - 1) * DT * 1000,
                                   "below_threshold_ms": c2["esik_alti_ms"], "threshold_dbfs": c2["esik_dbfs"]}}
        # ---------------- diye | L4 (kesintisiz)
        pe = k["diye"][-1]["end"]; ns = k["L4"][0]["start"]
        tp = hi_tepe(ns - 0.05, ns + 0.07)
        c3 = cukur(pe - 0.06, tp, ESIK)
        r["diye"].update({"bitis": c3["onceki_bitis"], "cikis_cukuru": c3})
        r["L4"] = {"baslangic": c3["sonraki_baslangic"], "giris_cukuru": c3, "c_hi_tepe": tp}
        # ---------------- L4 sonu
        wl = k["L4"][-1]
        i0 = fi(wl["end"] - 0.12)
        sinir = fi(wl["end"] + 1.2)
        govde = i0
        while govde < sinir and db[govde] > sung - 20.0:          # son govde: soylenen - 20 dB
            govde += 1
        e = govde
        n60 = fi(0.06)
        while e < sinir and not (db[e] < sung - 24.0 and db[e:e + n60].max() < sung - 24.0):
            e += 1
        # ayrik ek ses (nefes verme / puf): e'den sonraki 400 ms icinde soylenen - 20 dB'yi >= 20 ms asan bolge
        ek = None
        ust = np.where(db[e:e + fi(0.4)] > sung - 20.0)[0]
        if len(ust) * DT >= 0.02:
            e0, e1 = e + ust[0], e + ust[-1]
            mm = (TH >= e0 * DT) & (TH < (e1 + 1) * DT)
            q = e1
            while q < sinir and not (db[q] < sung - 27.0 and db[q:q + fi(0.1)].max() < sung - 21.0):
                q += 1
            ek = {"start": e0 * DT, "end": (e1 + 1) * DT, "peak_dbfs": float(db_ham[e0:e1 + 1].max()),
                  "voiced_ratio": float((F0H[mm] > 0).mean()) if mm.any() else 0.0,
                  "gap_after_word_ms": (e0 - e) * DT * 1000, "decayed_at": q * DT}
        r["L4"].update({"govde_bitis": govde * DT, "bitis": e * DT, "kuyruk_bitis": e * DT, "ek_ses": ek,
                        "kesim_cikis": e * DT + 0.03, "cikis_duzey_dbfs": float(db_ham[e + fi(0.03)]),
                        "sonraki_300ms_rms_dbfs": float(10 * np.log10(np.mean(z["rms"][e + fi(0.03):e + fi(0.33)] ** 2)))})
        r["vurus"] = vd[v]
        out.append(r)
    return out, {"soylenen_rms_dbfs": sung, "esik_dbfs": ESIK}


if __name__ == "__main__":
    dz, sv = dizeleri_bul()
    print(sv)
    for v in range(7):
        x = dz[v]; d0 = x["vurus"]
        print("K%d vurus %.4f" % (v + 1, d0))
        n = x["L1"]["nefes"]
        print("  L1   bas %.3f (guclu %.3f, vurusa gore %+.0f ms) giris %.3f (%.0f dB) | bit %.3f cikis %.3f (%.0f dB, esik alti %.0f ms) | nefes %s" % (
            x["L1"]["baslangic"], x["L1"]["guclu_baslangic"], (x["L1"]["guclu_baslangic"] - d0) * 1000, x["L1"]["kesim_giris"], x["L1"]["giris_duzey_dbfs"],
            x["L1"]["bitis"], x["L1"]["kesim_cikis"], x["L1"]["cikis_cukuru"]["duzey_dbfs"], x["L1"]["cikis_cukuru"]["esik_alti_ms"],
            "%.2f-%.2f tepe %.0f" % (n["start"], n["end"], n["peak_dbfs"]) if n else "-"))
        a = x["L2"]["zor_kesim"]
        print("  L2   bas %.3f (cubuga gore %+.0f ms) | bit(t_close) %.3f [dik %.3f] cukur %.3f %.1f dB | ara %s %.0f ms ort %.1f min %.1f sesli %.2f sessiz %.0f ms | hayvan unlu %.3f" % (
            x["L2"]["baslangic"], (x["L2"]["baslangic"] - d0 - BAR) * 1000, a["t_close"], a["t_steepest_fall"], a["dip_t"], a["dip_dbfs"], a["between_kind"],
            a["between_ms"], a["between_mean_dbfs"], a["between_min_dbfs"], a["between_voiced_ratio"], a["silent_gap_ms"], a["animal_vowel_onset"]))
        print("       ilk 50 ms: ort %.1f dB, alcak-F2 %.1f dB, alcak-yuksek %.1f dB | hayvan sesi basi %.3f" % (a["first50ms_mean_dbfs"], a["first50ms_low_minus_f2_db"], a["first50ms_low_minus_hi_db"], a["animal_sound_start"]))
        b = x["diye"]["zor_kesim"]
        print("  ses  bas %.3f govde bit %.3f bit %.3f" % (x["ses"]["baslangic"], x["ses"]["govde_bitis"], x["ses"]["bitis"]))
        print("  diye giris %.3f (cukur %.3f %.1f dB, esik alti %.0f ms) bas %.3f guclu %.3f (2. vurusa gore %+.0f ms) bosluk %.0f ms | bit %.3f" % (
            x["diye"]["kesim_giris"], b["dip_t"], b["dip_dbfs"], b["below_threshold_ms"], x["diye"]["baslangic"], x["diye"]["guclu_baslangic"],
            (x["diye"]["guclu_baslangic"] - d0 - 2 * BAR - 2 * BEAT) * 1000, b["gap_body_to_strong_onset_ms"], x["diye"]["bitis"]))
        print("  L4   bas %.3f (cubuga gore %+.0f ms; cukur %.3f %.1f dB) | govde bit %.3f kuyruk %.3f cikis %.3f (%.0f dB; sonraki 300 ms %.0f dB)" % (
            x["L4"]["baslangic"], (x["L4"]["baslangic"] - d0 - 3 * BAR) * 1000, x["L4"]["giris_cukuru"]["g"], x["L4"]["giris_cukuru"]["en_dusuk_dbfs"],
            x["L4"]["govde_bitis"], x["L4"]["kuyruk_bitis"], x["L4"]["kesim_cikis"], x["L4"]["cikis_duzey_dbfs"], x["L4"]["sonraki_300ms_rms_dbfs"]))
        if x["L4"]["ek_ses"]:
            print("       ek ses:", {k_: round(v_, 3) for k_, v_ in x["L4"]["ek_ses"].items()})
