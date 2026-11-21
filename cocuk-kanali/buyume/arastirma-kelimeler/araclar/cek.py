#!/usr/bin/env python3
"""YouTube arama sonuc sayfalarini (ilk sayfa, hl=tr gl=TR, oturumsuz) indirir.
Kullanim: python3 -I cek.py <sorgu-haritasi.json> <ham-html klasoru>
Yalnizca curl ve standart kutuphane; ucretli API yok."""
import json, os, subprocess, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
harita = json.load(open(sys.argv[1], encoding="utf-8")); hedef = sys.argv[2]
os.makedirs(hedef, exist_ok=True)
def cek(kv):
    ad, q = kv; yol = os.path.join(hedef, ad + ".html")
    if os.path.exists(yol) and os.path.getsize(yol) > 200000: return ad, "var", os.path.getsize(yol)
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q) + "&hl=tr&gl=TR"
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "40", "-A", "Mozilla/5.0", "-H", "Accept-Language: tr-TR,tr;q=0.9", url, "-o", yol, "-w", "%{http_code}"], capture_output=True, text=True)
    time.sleep(0.5)
    return ad, r.stdout.strip() or r.stderr.strip()[:80], os.path.getsize(yol) if os.path.exists(yol) else 0
with ThreadPoolExecutor(3) as ex:
    for ad, kod, boyut in ex.map(cek, harita.items()): print(ad, kod, boyut, flush=True)
