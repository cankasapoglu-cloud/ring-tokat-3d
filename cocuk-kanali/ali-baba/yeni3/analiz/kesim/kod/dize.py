#!/usr/bin/env python3
"""Dize (satir) sinirlari ve guvenli kesim noktalari - yalniz vokalin kendi enerji zarfindan.
10 ms pencereli RMS zarfi (2 ms adim) kullanilir.
Tanimlar
  soylenen_rms_db : 7 kitanin kelime araliklarindaki RMS (dBFS)
  ESIK            : soylenen_rms - 45 dB  -> 'enerji basladi / sondu' esigi
  TABAN           : kitalar arasi bosluklarin RMS'i (dBFS)  (ayrilmis vokalde dijital sessizlik duzeyi)
  L1|L2 ve L2|L3  : iki dize arasindaki enerji cukuru g bulunur (kelime zamanlarinin cevresinde);
                    onceki dizenin bitisi = g'den geriye esigi asan son an, sonraki dizenin baslangici =
                    g'den ileriye esigi asan ilk an; esik = max(ESIK, cukur + 6 dB). Kesim noktasi = g.
  L3|L4           : kesintisiz soyleniyor (derin cukur yok) -> ic sinir yalniz bilgi icin verilir.
  L4 sonu         : enerji ESIK altina dusup en az 150 ms orada kaldigi an (bitis) ve taban + 6 dB
                    altina dusup orada kaldigi an (kuyruk_bitis)."""
import numpy as np
from ortak import kelimeleri_oku, kitalari_esle, ozellik

z = ozellik(); t = z["t"]; DT = float(t[1] - t[0])
db_ham = 20 * np.log10(z["rms"] + 1e-9)
db = np.convolve(db_ham, np.ones(3) / 3, "same")          # 6 ms hafif yumusatma


def fi(x):
    return int(round(x / DT))


def seviyeler(kita):
    p = []
    for v in kita:
        for d in v:
            for q in d:
                p.append(z["rms"][fi(q["start"]):fi(q["end"])] ** 2)
    soylenen = 10 * np.log10(np.mean(np.concatenate(p)))
    return float(soylenen)


def sessiz_pencere(i, esik):
    """i karesi cevresinde db < esik olan bitisik araligin (bas, bit) zamani."""
    L = i
    while L > 0 and db[L - 1] < esik:
        L -= 1
    R = i
    while R < len(db) - 1 and db[R + 1] < esik:
        R += 1
    return L * DT, (R + 1) * DT


def kalici_dusus(i0, i1, esik, sure=0.15):
    """i0'dan sonra db'nin esik altina dusup en az `sure` kadar orada kaldigi ilk kare (yoksa i1)."""
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
    soylenen = seviyeler(kita)
    ESIK = soylenen - 45.0
    # taban: kitalar arasi bosluklar (onceki kita sonundan 1.2 s sonra .. sonraki kitadan 0.4 s once)
    bos = []
    for v in range(6):
        a = kita[v][3][-1]["end"] + 1.2; b = kita[v + 1][0][0]["start"] - 0.4
        bos.append(z["rms"][fi(a):fi(b)] ** 2)
    TABAN = float(10 * np.log10(np.mean(np.concatenate(bos)) + 1e-20))
    out = []
    for v in range(7):
        dz = [dict() for _ in range(4)]
        # --- L1 baslangici ---
        w0 = kita[v][0][0]
        i = fi(w0["start"] + 0.02)
        while i > 0 and not np.all(db[i - 5:i] < ESIK):
            i -= 1
        dz[0]["baslangic"] = i * DT
        # kesim_giris: baslangictan >= 30 ms once, cevresi (20 ms) ESIK - 6 dB altinda olan en yakin an
        j = i - fi(0.030)
        while j > i - fi(0.4) and db[j - fi(0.02):j + 3].max() > ESIK - 6:
            j -= 1
        dz[0]["kesim_giris"] = j * DT
        # --- L1|L2, L2|L3 cukurlari ---
        for d in (1, 2):
            pe = kita[v][d - 1][-1]["end"]; ns = kita[v][d][0]["start"]
            a, b = fi(pe - 0.05), fi(ns + 0.03)
            g = a + int(np.argmin(db[a:b]))
            esik = max(ESIK, db[g] + 6.0)
            L = g
            while L > a - fi(0.2) and db[L] < esik:
                L -= 1
            R = g
            while R < b + fi(0.2) and db[R] < esik:
                R += 1
            # cukurun en derin 6 dB'lik bolumunun ortasi (genis sessizlikte tam ortaya gelsin)
            sp = sessiz_pencere(g, max(db[g] + 6.0, min(ESIK, TABAN + 6.0)))
            gm = (sp[0] + sp[1]) / 2 if (sp[1] - sp[0]) < 0.2 else g * DT
            dz[d - 1]["bitis"] = (L + 1) * DT
            dz[d]["baslangic"] = R * DT
            dz[d - 1]["kesim_cikis"] = gm; dz[d]["kesim_giris"] = gm
            bilgi = {"an": round(gm, 4), "duzey_dbfs": round(float(db_ham[fi(gm)]), 1),
                     "en_dusuk_dbfs": round(float(db_ham[a:b].min()), 1),
                     "esik_alti_pencere_ms": round((R - L - 1) * DT * 1000, 1)}
            dz[d - 1]["cikis_cukuru"] = bilgi; dz[d]["giris_cukuru"] = bilgi
        # --- L3|L4 ic sinir (kesintisiz): kelime zamanlari cevresindeki en dusuk enerji ---
        pe = kita[v][2][-1]["end"]; ns = kita[v][3][0]["start"]
        a, b = fi(pe - 0.04), fi(ns + 0.03)
        g = a + int(np.argmin(db[a:b]))
        dz[2]["bitis"] = g * DT; dz[3]["baslangic"] = g * DT
        dz[2]["kesim_cikis"] = None; dz[3]["kesim_giris"] = None
        ic = {"an": round(g * DT, 4), "duzey_dbfs": round(float(db_ham[g]), 1),
              "not": "L3 ile L4 arasi kesintisiz; burasi guvenli kesim noktasi DEGIL"}
        dz[2]["cikis_cukuru"] = ic; dz[3]["giris_cukuru"] = ic
        # --- L4 sonu ---
        wl = kita[v][3][-1]
        sinir = fi(kita[v + 1][0][0]["start"] - 0.3) if v < 6 else fi(wl["end"] + 2.0)
        i0 = fi(wl["start"] + 0.08)
        e1 = kalici_dusus(i0, sinir, ESIK)
        e2 = kalici_dusus(i0, sinir, TABAN + 6.0)
        dz[3]["bitis"] = e1 * DT; dz[3]["kuyruk_bitis"] = e2 * DT
        dz[3]["kesim_cikis"] = e2 * DT + 0.02
        dz[3]["cikis_cukuru"] = {"an": round(e2 * DT + 0.02, 4), "duzey_dbfs": round(float(db_ham[e2 + fi(0.02)]), 1),
                                 "esik_alti_pencere_ms": None}
        dz[0]["giris_cukuru"] = {"an": round(dz[0]["kesim_giris"], 4),
                                 "duzey_dbfs": round(float(db_ham[fi(dz[0]["kesim_giris"])]), 1), "esik_alti_pencere_ms": None}
        out.append(dz)
    return out, {"soylenen_rms_dbfs": soylenen, "esik_dbfs": ESIK, "taban_dbfs": TABAN}


if __name__ == "__main__":
    dz, sv = dizeleri_bul()
    print(sv)
    for v in range(7):
        for d in range(4):
            x = dz[v][d]
            print("K%d L%d  bas %.3f  bit %.3f  giris %s  cikis %s  %s" % (
                v + 1, d + 1, x["baslangic"], x["bitis"],
                "%.3f" % x["kesim_giris"] if x["kesim_giris"] is not None else "-",
                "%.3f" % x["kesim_cikis"] if x["kesim_cikis"] is not None else "-",
                x.get("cikis_cukuru")))
