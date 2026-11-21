#!/usr/bin/env python3
"""Eksik kalan kanallari @kullanici adiyla tekrar arar; 'bu ay yuklenenler' sayfalarinda one cikan kanallari da ekler.
Kullanim: python3 -I kanal_bul_ek.py <klasor>"""
import csv, json, os, re, subprocess, sys, urllib.parse
K = sys.argv[1]
def metin(d):
    if not d: return ""
    if "simpleText" in d: return d["simpleText"]
    if "runs" in d: return "".join(r.get("text", "") for r in d["runs"])
    return ""
def abone_sayi(t):
    m = re.search(r"([\d.,]+)\s*(mr|mn|b)?\s*abone", (t or "").lower().replace("\xa0", " "))
    if not m: return ""
    v = float(m.group(1).replace(".", "").replace(",", ".")) if m.group(2) else float(m.group(1).replace(".", "").replace(",", ""))
    return int(v * {"b": 1e3, "mn": 1e6, "mr": 1e9, None: 1}[m.group(2)])
def ara(q):
    yol = os.path.join(K, "ham-html", "_gecici_kanal.html")
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q) + "&hl=tr&gl=TR&sp=EgIQAg%3D%3D"
    subprocess.run(["curl", "-sS", "-L", "--max-time", "30", "-A", "Mozilla/5.0", "-H", "Accept-Language: tr-TR,tr;q=0.9", url, "-o", yol], capture_output=True, text=True)
    try: h = open(yol, encoding="utf-8", errors="replace").read()
    except OSError: h = ""
    if os.path.exists(yol): os.remove(yol)
    m = re.search(r"var ytInitialData\s*=\s*(\{.*?\});\s*</script>", h, re.S)
    out = {}
    if not m: return out
    def yuru(n):
        if isinstance(n, list):
            for x in n: yuru(x)
        elif isinstance(n, dict):
            for k, v in n.items():
                if k == "channelRenderer":
                    a, b = metin(v.get("videoCountText")), metin(v.get("subscriberCountText"))
                    ab = a if "abone" in a else (b if "abone" in b else "")
                    out[v.get("channelId", "")] = (ab, abone_sayi(ab), b if b.startswith("@") else a if a.startswith("@") else "")
                else: yuru(v)
    yuru(json.loads(m.group(1)).get("contents", {})); return out
mevcut = list(csv.DictReader(open(os.path.join(K, "kanal-aboneleri.csv"), encoding="utf-8")))
bil = {r["kanal_id"]: r for r in mevcut}
ana = list(csv.DictReader(open(os.path.join(K, "rakip-arama-sonuclari.csv"), encoding="utf-8")))
ek = list(csv.DictReader(open(os.path.join(K, "ek-sorgular.csv"), encoding="utf-8")))
url = {}
for r in ana + ek:
    if r["kanal_id"] and r["kanal_url"]: url[r["kanal_id"]] = r["kanal_url"]
hedef = {}  # kanal_id -> ad
for r in mevcut:
    if r["bulundu"] != "evet": hedef[r["kanal_id"]] = r["kanal"]
for r in ek:  # ek sorgularda ilk 12 sira + kanal kimligi olanlar
    if r["tur"] == "video" and r["kanal_id"] and r["kanal_id"] not in bil and int(r["sira"]) <= 12:
        hedef.setdefault(r["kanal_id"], r["kanal"])
print("aranacak:", len(hedef))
for kid, ad in hedef.items():
    sonuc = {}
    h = url.get(kid, "")
    if h.startswith("/@"): sonuc = ara(urllib.parse.unquote(h[2:]))
    if kid not in sonuc: sonuc.update(ara(ad))
    if kid in sonuc:
        ab, n, hd = sonuc[kid]; bil[kid] = {"kanal_id": kid, "kanal": ad, "abone_metni": ab, "abone_sayi": n, "handle": hd, "bulundu": "evet"}
    else:
        bil.setdefault(kid, {"kanal_id": kid, "kanal": ad, "abone_metni": "", "abone_sayi": "", "handle": urllib.parse.unquote(h[1:]) if h else "", "bulundu": "hayir"})
    print(ad[:34], "->", bil[kid]["abone_metni"] or "BULUNAMADI", flush=True)
with open(os.path.join(K, "kanal-aboneleri.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["kanal_id", "kanal", "abone_metni", "abone_sayi", "handle", "bulundu"]); w.writeheader()
    for r in bil.values(): w.writerow(r)
print("toplam kanal:", len(bil), "| bulunan:", sum(1 for r in bil.values() if r["bulundu"] == "evet"))
