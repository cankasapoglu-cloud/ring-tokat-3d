#!/usr/bin/env python3
"""Kalibrasyon kumesinde dokumu OLMAYAN dosyalarin Scribe dokumunu alir (aracin kendi islevi: onbellek + kredi defteri).
Her dosya en cok BIR kez gonderilir; yaninda eski *_words.json olanlar ve calgisal dosya gonderilmez.
Kullanim: python3 01_dokum_al.py [ad ...]   (ad verilmezse oncelik sirasiyla hepsi; KENDI_SINIR asilacaksa durur)"""
import os, sys, json, subprocess
BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(BURASI)), "arac"))
import dinle_sozler as z
from set import SET
KENDI_SINIR = 7700          # aracin siniri 8000; biraz pay birak
ONCELIK = ["parmak-ailesi__duzgun_2", "parmak-ailesi__coskulu_1", "parmak-ailesi__turkce_2", "el-yikama__coskulu_2",
           "ali-baba__coskulu_1", "ali-baba__dogal_onizleme", "ali-baba__sarki_birlesik", "ali-baba__coskulu_2"]
istenen = sys.argv[1:] or ONCELIK
ad2 = {s["ad"]: s for s in SET}
for ad in istenen:
    s = ad2[ad]
    assert s.get("dokum") and not s.get("mevcut_dokum"), ad
    yol = s["tam_yol"]
    sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", yol], capture_output=True, text=True).stdout)
    var, oz = z.onbellekte(yol)
    harcanan = z.defter_toplam()
    tahmin = sure / 60 * z.KREDI_DAKIKA
    if not var and harcanan + tahmin > KENDI_SINIR:
        print("DURDU: %s icin ~%.0f kredi gerek; defter %.0f; kendi sinirim %d" % (ad, tahmin, harcanan, KENDI_SINIR)); break
    sonuc, durum = z.scribe(yol, sure, gunluk=print)
    print("%-32s %6.1f sn  %s  kredi=%s  defter=%.0f" % (ad, sure, durum.get("kaynak"), durum.get("kredi"), z.defter_toplam()))
    if sonuc is None:
        print("   HATA:", json.dumps(durum, ensure_ascii=False)); break
    print("   dil=%s p=%s | %s" % (sonuc.get("language_code"), sonuc.get("language_probability"), (sonuc.get("text") or "")[:1500].replace("\n", " ")))
