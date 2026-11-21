#!/usr/bin/env python3
"""referans_olustur.py - projenin kendi sarkilarindan ENERJI REFERANS TABLOSU cikarir (kurulum/referans_enerji.json).

dinle.py bu tabloyu okuyup "bu sarki, projedeki coskulu / yavas adli surumlerin neresinde" diye yazar.
Etiketler (coskulu / yavas / diger) dosya adindan gelen URETIM NIYETIDIR; dinleyici puani degildir. n kucuktur.
Kullanim: python3 referans_olustur.py            (yaklasik 3-4 dakika, 2 is parcacigi)
"""
import os, sys, json, time, warnings
warnings.filterwarnings("ignore")
BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
import numpy as np
import dinle_olcum as o, dinle_model as dm

K = os.path.dirname(os.path.dirname(BURASI))
DOSYALAR = {"coskulu": ["ali-baba/coskulu_1.mp3", "ali-baba/coskulu_2.mp3", "el-yikama/coskulu_1.mp3", "el-yikama/coskulu_2.mp3",
                        "parmak-ailesi/coskulu_1.mp3", "parmak-ailesi/coskulu_2.mp3"],
            "yavas": ["parmak-ailesi/yavas_2.mp3", "pitirin-ailesi/yavas_1.mp3", "pitirin-ailesi/yavas_2.mp3"],
            "diger": ["ali-baba/sarki.mp3", "ali-baba/dinle_2.mp3", "el-yikama/sarki_1.mp3", "parmak-ailesi/sarki_2.mp3", "balon-sarkisi/sarki.mp3"]}
satirlar = []
for grup, liste in DOSYALAR.items():
    for f in liste:
        yol = os.path.join(K, f)
        if not os.path.exists(yol):
            print("yok:", f); continue
        t = time.time()
        x, sr = o.ses_coz(yol)
        y = o.tek_kanal(x, sr)
        en, _ = o.enerji(y)
        x16 = o.tek_kanal(x, sr, 16000)
        ce = dm.ced_etiket(x16)
        mc = dm.musiccoca(x16)
        s = {"grup": grup, "dosya": f, "puan": en["enerji_puani"]["puan_0_100"], "tempo_bpm": en["tempo_bpm"], "olay_yogunlugu_sn": en["olay_yogunlugu_sn"],
             "nabiz_netligi": en["nabiz_netligi"], "vurmali_armonik_db": en["vurmali_armonik_db"], "spektral_aki_ort": en["spektral_aki_ort"],
             "parlaklik_agirlik_merkezi_hz": en["parlaklik_agirlik_merkezi_hz"], "ced_coskulu_eksi_sakin": ce.get("coskulu_eksi_sakin"),
             "ced_ninni": ce.get("ninni_olasiligi"), "coca_cosku": (mc.get("cosku") or {}).get("fark")}
        satirlar.append(s)
        print("%-8s %-32s puan %3.0f | olay %.2f nabiz %.2f v/a %+5.1f aki %.2f parlak %4.0f | CED %+.3f ninni %.3f | CoCa %+.3f  (%.0fs)" % (
            grup, f, s["puan"], s["olay_yogunlugu_sn"], s["nabiz_netligi"] or 0, s["vurmali_armonik_db"], s["spektral_aki_ort"],
            s["parlaklik_agirlik_merkezi_hz"], s["ced_coskulu_eksi_sakin"] or 0, s["ced_ninni"] or 0, s["coca_cosku"] or 0, time.time() - t), flush=True)
ozet = {}
for g in DOSYALAR:
    for a in ("puan", "coca_cosku", "ced_coskulu_eksi_sakin", "ced_ninni", "olay_yogunlugu_sn"):
        v = [s[a] for s in satirlar if s["grup"] == g and s[a] is not None]
        if v:
            ozet.setdefault(g, {})[a] = {"en_az": round(min(v), 3), "en_cok": round(max(v), 3), "n": len(v)}
hedef = os.path.join(os.path.dirname(BURASI), "kurulum", "referans_enerji.json")
json.dump({"aciklama": "Projedeki sarkilarin enerji gostergeleri. Grup = dosya adindaki uretim niyeti (dinleyici puani degil).", "zaman": time.strftime("%Y-%m-%d %H:%M"),
           "ozet": ozet, "satirlar": satirlar}, open(hedef, "w", encoding="utf8"), ensure_ascii=False, indent=1)
print("yazildi:", hedef); print(json.dumps(ozet, ensure_ascii=False))
