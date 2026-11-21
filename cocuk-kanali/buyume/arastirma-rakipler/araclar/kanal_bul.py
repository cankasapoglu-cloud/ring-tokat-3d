#!/usr/bin/env python3
"""Ilk sayfada gorunen kanallarin abone sayisini, kanal adiyla 'yalnizca kanal' aramasi yaparak bulur.
Kullanim: python3 -I kanal_bul.py <rakip csv> <gecici klasor> <cikti csv>
Ham sayfalar islenince silinir (yer kaplamasin)."""
import csv, json, os, re, subprocess, sys, urllib.parse

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
                    handle = b if b.startswith("@") else (a if a.startswith("@") else "")
                    out.append({"kanal": metin(v.get("title")), "kanal_id": v.get("channelId", ""), "abone_metni": abone,
                                "abone_sayi": abone_sayi(abone), "handle": handle})
                else: yuru(v)
    yuru(d.get("contents", {})); return out

def cek(q, yol):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q) + "&hl=tr&gl=TR&sp=EgIQAg%3D%3D"
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "30", "-A", "Mozilla/5.0", "-H", "Accept-Language: tr-TR,tr;q=0.9", url, "-o", yol, "-w", "%{http_code}"], capture_output=True, text=True)
    try:
        h = open(yol, encoding="utf-8", errors="replace").read()
    except OSError:
        h = ""
    if os.path.exists(yol): os.remove(yol)
    return r.stdout, kanallar(h)

kaynak, gecici, cikti = sys.argv[1:4]
os.makedirs(gecici, exist_ok=True)
rows = [r for r in csv.DictReader(open(kaynak, encoding="utf-8")) if r["tur"] == "video" and r["kanal_id"]]
adlar = {}
for r in rows: adlar.setdefault(r["kanal_id"], r["kanal"])
bulunan = {}
# 1) genel 'yalnizca kanal' aramalari: ust siradaki kanallar
genel = []
for q in ["çocuk şarkıları", "bebek şarkıları", "çocuk şarkıları çizgi film"]:
    kod, ks = cek(q, os.path.join(gecici, "g.html"))
    print("genel", q, kod, len(ks))
    for i, k in enumerate(ks, 1):
        genel.append(dict(k, sorgu=q, sira=i)); bulunan.setdefault(k["kanal_id"], k)
# 2) ilk sayfadaki her kanal icin adla arama
for i, (kid, ad) in enumerate(adlar.items(), 1):
    if kid in bulunan: continue
    kod, ks = cek(ad, os.path.join(gecici, "k.html"))
    for k in ks: bulunan.setdefault(k["kanal_id"], k)
    print(i, len(adlar), kod, ad[:30], "->", bulunan.get(kid, {}).get("abone_metni", "BULUNAMADI"), flush=True)
with open(cikti, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["kanal_id", "kanal", "abone_metni", "abone_sayi", "handle", "bulundu"])
    for kid, ad in adlar.items():
        k = bulunan.get(kid)
        w.writerow([kid, ad, k["abone_metni"] if k else "", k["abone_sayi"] if k else "", k["handle"] if k else "", "evet" if k else "hayir"])
with open(cikti.replace(".csv", "-genel-kanal-aramasi.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["sorgu", "sira", "kanal", "kanal_id", "abone_metni", "abone_sayi", "handle"])
    for k in genel: w.writerow([k["sorgu"], k["sira"], k["kanal"], k["kanal_id"], k["abone_metni"], k["abone_sayi"], k["handle"]])
print("yazildi", cikti)
