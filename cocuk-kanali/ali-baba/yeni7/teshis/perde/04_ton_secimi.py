#!/usr/bin/env python3
"""SORU 4: Hangi ton (do = MIDI 60..71) kaydırmaları en aza indirir?
Ezgi (görev tanımındaki gibi; sol ve la HEP do'nun ALTINDA: sol = do-5, la = do-3, re = do+2, mi = do+4):
   L1  (10 hece): do do do do sol la la sol sol sol
   L2  ( 9 hece): mi mi re re do do do do do      (8 heceli kıtalarda: mi mi re re do do do do)
   diye( 5 hece): la la sol sol sol
   L4  ( 9 hece): mi mi re re do do do do do
Özgün perde: yerlesim.json syllables_flat[].midi. Çıktı: ara/04_ton_secimi.json + ekrana tablo."""
import json, os, numpy as np
from ortak import *

Y, S, Z = yukle()
DERECE = {"L1": [0, 0, 0, 0, -5, -3, -3, -5, -5, -5], "L2": [4, 4, 2, 2, 0, 0, 0, 0, 0], "diye": [-3, -3, -5, -5, -5], "L4": [4, 4, 2, 2, 0, 0, 0, 0, 0]}
AD = {0: "do", -5: "sol,", -3: "la,", 2: "re", 4: "mi"}
sayi = {}
for s in S: sayi[(s["verse"], s["line"])] = sayi.get((s["verse"], s["line"]), 0) + 1
for (k, l), n in sayi.items(): assert n <= len(DERECE[l]), (k, l, n)
og = np.array([s["midi"] for s in S]); der = np.array([DERECE[s["line"]][s["index"]] for s in S]); sure = np.array([s["dest_end"] - s["dest_start"] for s in S])
cik = {"ezgi": {k: [AD[d] for d in v] for k, v in DERECE.items()}, "tonlar": []}
print(" do    ton  ort|k|  ortanca  p90   en çok yukarı  en çok aşağı  |k|>=2.5  |k|>=3.5  |k|>=4.5  süre ağırlıklı ort|k|  ort k^2   aşağı<=-3.5")
for T in range(60, 72):
    k = T + der - og; a = np.abs(k)
    d = {"do_midi": T, "do": ad(T), "ortalama_mutlak": round(float(a.mean()), 2), "ortanca_mutlak": round(float(np.median(a)), 2), "p90": round(float(np.percentile(a, 90)), 2), "en_cok_yukari": round(float(k.max()), 2), "en_cok_asagi": round(float(k.min()), 2),
         "hece_2.5_ustu": int((a >= 2.5).sum()), "hece_3.5_ustu": int((a >= 3.5).sum()), "hece_4.5_ustu": int((a >= 4.5).sum()), "sure_agirlikli_ortalama": round(float((a * sure).sum() / sure.sum()), 2), "kare_ortalama": round(float((k ** 2).mean()), 2),
         "asagi_3.5_ustu": int((k <= -3.5).sum()), "yukari_3.5_ustu": int((k >= 3.5).sum()), "ezgi_araligi": "%s - %s" % (ad(T - 5), ad(T + 4))}
    cik["tonlar"].append(d)
    print(" %-4s %2d   %5.2f   %5.2f  %5.2f    %+6.2f        %+6.2f       %4d      %4d      %4d          %5.2f           %6.2f      %4d" % (d["do"], T, d["ortalama_mutlak"], d["ortanca_mutlak"], d["p90"], d["en_cok_yukari"], d["en_cok_asagi"], d["hece_2.5_ustu"], d["hece_3.5_ustu"], d["hece_4.5_ustu"], d["sure_agirlikli_ortalama"], d["kare_ortalama"], d["asagi_3.5_ustu"]))
sirali = sorted(cik["tonlar"], key=lambda d: d["ortalama_mutlak"]); sirali2 = sorted(cik["tonlar"], key=lambda d: d["kare_ortalama"])
print("\n ortalama |k| sırası:", [(d["do"], d["ortalama_mutlak"]) for d in sirali[:4]], " | k^2 sırası:", [(d["do"], d["kare_ortalama"]) for d in sirali2[:4]])
cik["en_iyi_iki_(ortalama_mutlak)"] = [d["do"] for d in sirali[:2]]; cik["en_iyi_iki_(kare)"] = [d["do"] for d in sirali2[:2]]
# reddedilen karışımın yaptığı (hedefler.json) ile kıyas
kr = np.array([s["hedef"] for s in S]) - og
cik["reddedilen_hedefler"] = {"ortalama_mutlak": round(float(np.abs(kr).mean()), 2), "kare_ortalama": round(float((kr ** 2).mean()), 2), "hece_3.5_ustu": int((np.abs(kr) >= 3.5).sum()), "en_cok_yukari": round(float(kr.max()), 2), "en_cok_asagi": round(float(kr.min()), 2)}
print(" kıyas - reddedilen karışımdaki hedefler (do=G4, başka ezgi eşlemesi):", cik["reddedilen_hedefler"])
cik["tablolar"] = {}
for T in sorted({d["do_midi"] for d in sirali[:2]} | {d["do_midi"] for d in sirali2[:2]}):
    print("\n KAYDIRMA TABLOSU do = %s (MIDI %d); ezgi aralığı %s - %s; 7 kıtanın ortalaması [en küçük .. en büyük], yarım ses" % (ad(T), T, ad(T - 5), ad(T + 4)))
    tb = []
    for satir in ("L1", "L2", "diye", "L4"):
        for i in range(len(DERECE[satir])):
            g = [(s, T + DERECE[satir][i] - s["midi"]) for s in S if s["line"] == satir and s["index"] == i and not (satir == "L2" and sayi[(s["verse"], "L2")] == 8)]
            if not g: continue
            k = np.array([x[1] for x in g]); s0 = g[0][0]
            tb.append({"satir": satir, "sira": i, "hece_K1": s0["text"], "derece": AD[DERECE[satir][i]], "hedef": ad(T + DERECE[satir][i]), "ozgun_ort_midi": round(float(np.mean([x[0]["midi"] for x in g])), 2), "kaydirma_ort": round(float(k.mean()), 2), "en_kucuk": round(float(k.min()), 2), "en_buyuk": round(float(k.max()), 2)})
            print("   %-5s #%d %-5s %-4s -> %-3s  özgün %.2f (%s)   kaydırma %+5.2f  [%+.2f .. %+.2f]%s" % (satir, i, s0["text"], AD[DERECE[satir][i]], ad(T + DERECE[satir][i]), tb[-1]["ozgun_ort_midi"], ad(tb[-1]["ozgun_ort_midi"]), k.mean(), k.min(), k.max(), "   <<< AĞIR" if abs(k.mean()) >= 3.5 else ""))
    # 8 heceli L2 (kıta 3 ve 7)
    for s in S:
        if s["line"] == "L2" and sayi[(s["verse"], "L2")] == 8:
            k = T + DERECE["L2"][s["index"]] - s["midi"]; tb.append({"satir": "L2(8 hece) K%d" % s["verse"], "sira": s["index"], "hece_K1": s["text"], "derece": AD[DERECE["L2"][s["index"]]], "hedef": ad(T + DERECE["L2"][s["index"]]), "ozgun_ort_midi": s["midi"], "kaydirma_ort": round(float(k), 2)})
    cik["tablolar"][ad(T)] = tb
# satır bazında en iyi ton (tek ton yerine satır satır farklı kaynak hecesi seçilemediği için yalnız bilgi)
print("\n satır bazında ortalama |k| (hangi satır hangi tonu istiyor):")
for satir in ("L1", "L2", "diye", "L4"):
    m = np.array([s["line"] == satir for s in S]); r = [(float(np.abs(T + der[m] - og[m]).mean()), T) for T in range(60, 72)]; r.sort()
    print("   %-5s en iyi: %s" % (satir, ", ".join("%s %.2f" % (ad(T), v) for v, T in r[:3])), "| en kötü: %s %.2f" % (ad(r[-1][1]), r[-1][0]))
json.dump(cik, open(os.path.join(ARA, "04_ton_secimi.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
