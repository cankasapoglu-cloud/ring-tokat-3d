#!/usr/bin/env python3
"""Ilk sayfadaki kanallarin abone sayisi: once onceki arastirmanin tablosu (rakipler/kanal-aboneleri.csv),
bulunmayanlar icin kanal adiyla 'yalnizca kanal' aramasi (kanal_id eslesirse kabul).
Kullanim: python3 -I kanal_abone.py <arama csv> <onceki kanal csv> <gecici klasor> <cikti csv>"""
import csv, json, os, re, subprocess, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor
def metin(d):
    if not d: return ""
    if "simpleText" in d: return d["simpleText"]
    if "runs" in d: return "".join(r.get("text", "") for r in d["runs"])
    return ""
def abone_sayi(t):
    s = (t or "").lower().replace("\xa0", " ")
    m = re.search(r"([\d.,]+)\s*(mr|mn|b)?\s*abone", s)
    if not m: return ""
    v = float(m.group(1).replace(".", "").replace(",", ".")) if m.group(2) else float(m.group(1).replace(".", "").replace(",", ""))
    return int(v * {"b": 1e3, "mn": 1e6, "mr": 1e9, None: 1}[m.group(2)])
def kanallar(html):
    m = re.search(r"var ytInitialData\s*=\s*(\{.*?\});\s*</script>", html, re.S)
    if not m: return []
    d = json.loads(m.group(1)); out = []
    def yuru(n):
        if isinstance(n, list):
            for x in n: yuru(x)
        elif isinstance(n, dict):
            for k, v in n.items():
                if k == "channelRenderer":
                    a, b = metin(v.get("videoCountText")), metin(v.get("subscriberCountText"))
                    abone = a if "abone" in a else (b if "abone" in b else "")
                    out.append({"kanal_id": v.get("channelId", ""), "abone_metni": abone, "abone_sayi": abone_sayi(abone)})
                else: yuru(v)
    yuru(d.get("contents", {})); return out
kaynak, onceki, gecici, cikti = sys.argv[1:5]
os.makedirs(gecici, exist_ok=True)
adlar = {}
for r in csv.DictReader(open(kaynak, encoding="utf-8")):
    if r["tur"] == "video" and r["kanal_id"]: adlar.setdefault(r["kanal_id"], r["kanal"])
bil = {r["kanal_id"]: (r["abone_metni"], r["abone_sayi"], "onceki-arastirma") for r in csv.DictReader(open(onceki, encoding="utf-8")) if r["abone_sayi"]}
def ara(kv):
    kid, ad = kv; yol = os.path.join(gecici, kid + ".html")
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(ad) + "&hl=tr&gl=TR&sp=EgIQAg%3D%3D"
    subprocess.run(["curl", "-sS", "-L", "--max-time", "30", "-A", "Mozilla/5.0", "-H", "Accept-Language: tr-TR,tr;q=0.9", url, "-o", yol], capture_output=True, text=True)
    try: h = open(yol, encoding="utf-8", errors="replace").read()
    except OSError: h = ""
    if os.path.exists(yol): os.remove(yol)
    return kanallar(h)
if os.path.exists(cikti):
    for r in csv.DictReader(open(cikti, encoding="utf-8")):
        if r["abone_sayi"]: bil[r["kanal_id"]] = (r["abone_metni"], r["abone_sayi"], r["kaynak"])
eksik = [(k, a) for k, a in adlar.items() if k not in bil]
with ThreadPoolExecutor(4) as ex:
    for ks in ex.map(ara, eksik):
        for k in ks:
            if k["kanal_id"] in adlar and k["kanal_id"] not in bil and k["abone_sayi"] != "": bil[k["kanal_id"]] = (k["abone_metni"], k["abone_sayi"], "kanal-aramasi")
with open(cikti, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["kanal_id", "kanal", "abone_metni", "abone_sayi", "kaynak"])
    for kid, ad in adlar.items():
        b = bil.get(kid, ("", "", "bulunamadi")); w.writerow([kid, ad, b[0], b[1], b[2]])
print("kanal", len(adlar), "bulunan", sum(1 for k in adlar if k in bil), "aranan", len(eksik))
