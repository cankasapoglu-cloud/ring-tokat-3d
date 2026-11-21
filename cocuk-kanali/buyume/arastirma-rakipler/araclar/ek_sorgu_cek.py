#!/usr/bin/env python3
"""Ek (uzun kuyruk / son bir ay filtreli) sorgulari ceker. Kullanim: python3 -I ek_sorgu_cek.py <cikti klasoru> <harita.json>"""
import json, os, subprocess, sys, urllib.parse
AY = "EgQIBBAB"  # yukleme tarihi: bu ay + tur: video
SORGU = [
    ("e01_ali_baba_gercek_hayvan_sesleri", "ali babanın çiftliği gerçek hayvan sesleri", ""),
    ("e02_hayvan_sesleri_sarkisi", "hayvan sesleri şarkısı", ""),
    ("e03_balon_sarkisi", "balon şarkısı", ""),
    ("e04_kedi_sarkisi_cocuk", "kedi şarkısı çocuk", ""),
    ("e05_aile_bireyleri_sarkisi", "aile bireyleri şarkısı", ""),
    ("e06_parmak_ailesi_kedi", "parmak ailesi kedi", ""),
    ("e07_el_yikama_okul_oncesi", "el yıkama şarkısı okul öncesi", ""),
    ("e08_otobusun_tekerlegi", "otobüsün tekerleği", ""),
    ("e09_pitir_kedi", "pıtır kedi çocuk şarkıları", ""),
    ("e10_dudek_studyo", "dudek stüdyo", ""),
    ("e11_cocuk_sarkilari_2026", "çocuk şarkıları 2026", ""),
    ("a01_cocuk_sarkilari_buay", "çocuk şarkıları [bu ay yüklenenler]", AY),
    ("a02_ali_baba_buay", "ali babanın çiftliği [bu ay yüklenenler]", AY),
    ("a03_el_yikama_buay", "el yıkama şarkısı [bu ay yüklenenler]", AY),
    ("a04_parmak_ailesi_buay", "parmak ailesi şarkısı [bu ay yüklenenler]", AY),
    ("a05_otobus_buay", "otobüs şarkısı [bu ay yüklenenler]", AY),
    ("a06_bes_kucuk_maymun_buay", "beş küçük maymun [bu ay yüklenenler]", AY),
]
hedef, harita = sys.argv[1], sys.argv[2]
os.makedirs(hedef, exist_ok=True)
m = {}
for ad, q, sp in SORGU:
    temiz = q.split(" [")[0]
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(temiz) + "&hl=tr&gl=TR" + ("&sp=" + sp if sp else "")
    yol = os.path.join(hedef, ad + ".html")
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "40", "-A", "Mozilla/5.0", "-H", "Accept-Language: tr-TR,tr;q=0.9",
                        url, "-o", yol, "-w", "%{http_code} %{size_download}"], capture_output=True, text=True)
    print(ad, r.stdout, r.stderr[:200])
    m[ad] = q
json.dump(m, open(harita, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
