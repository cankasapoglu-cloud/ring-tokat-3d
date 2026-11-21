#!/usr/bin/env python3
"""Ozet istatistikler. Kullanim: python3 -I analiz.py <klasor>"""
import csv, re, statistics as st, sys, os
from collections import Counter, defaultdict
K = sys.argv[1]
oku = lambda f: list(csv.DictReader(open(os.path.join(K, f), encoding="utf-8")))
ana, ek, kan = oku("rakip-arama-sonuclari.csv"), oku("ek-sorgular.csv"), oku("kanal-aboneleri.csv")
abone = {r["kanal_id"]: (int(r["abone_sayi"]) if r["abone_sayi"] else None) for r in kan}
I = lambda x: int(float(x)) if x not in ("", None) else None
F = lambda x: float(x) if x not in ("", None) else None
def kisa(n):
    if n is None: return "?"
    return f"{n/1e6:.1f}Mn" if n >= 1e6 else (f"{n/1e3:.0f}B" if n >= 1e3 else str(n))
def ozet(rows, baslik):
    v = [r for r in rows if r["tur"] == "video"]
    sn = [I(r["sure_saniye"]) for r in v if r["sure_saniye"]]
    gs = [I(r["goruntuleme_sayi"]) for r in v if r["goruntuleme_sayi"]]
    ya = [F(r["yas_ay"]) for r in v if r["yas_ay"]]
    short = sum(1 for s in sn if s <= 60); tek = sum(1 for s in sn if 60 < s < 300); orta = sum(1 for s in sn if 300 <= s < 600); der = sum(1 for s in sn if s >= 600)
    kc = Counter(r["kanal"] for r in v)
    print(f"{baslik[:44]:44} n={len(v):2} short={short:2} tek={tek:2} 5-10dk={orta:2} 10dk+={der:2} medSure={st.median(sn) if sn else 0:6.0f}s medGor={kisa(int(st.median(gs))) if gs else '?':>7} medYas={st.median(ya)/12 if ya else 0:4.1f}y <=12ay={sum(1 for a in ya if a<=12):2} kanal={len(kc):2} enCok={kc.most_common(1)[0][0][:16]}x{kc.most_common(1)[0][1]}")
print("== A. SORGU OZETI (ana 9 sorgu)")
gr = defaultdict(list)
for r in ana: gr[r["sorgu"]].append(r)
for q, rows in gr.items(): ozet(rows, q)
print("== A2. EK SORGULAR")
ge = defaultdict(list)
for r in ek: ge[r["sorgu"]].append(r)
for q, rows in ge.items(): ozet(rows, q)
av = [r for r in ana if r["tur"] == "video"]
print("\n== B. KANAL HAKIMIYETI (9 sorgu, 136+ video satiri): kanal | satir | sorgu sayisi | abone")
kc = Counter(r["kanal_id"] for r in av); ad = {r["kanal_id"]: r["kanal"] for r in av}
ks = defaultdict(set)
for r in av: ks[r["kanal_id"]].add(r["sorgu"])
for kid, n in kc.most_common(16): print(f"  {ad[kid][:40]:40} {n:3} {len(ks[kid])}/9 abone={kisa(abone.get(kid))}")
tot = len(av); print("  toplam video satiri", tot, "| farkli kanal", len(kc), "| ilk1 payi %.0f%% | ilk5 payi %.0f%%" % (100*kc.most_common(1)[0][1]/tot, 100*sum(n for _, n in kc.most_common(5))/tot))
print("  abone dagilimi (farkli kanal):", Counter(("bilinmiyor" if abone.get(k) is None else "<1B" if abone[k] < 1e3 else "1B-10B" if abone[k] < 1e4 else "10B-100B" if abone[k] < 1e5 else "100B-1Mn" if abone[k] < 1e6 else "1Mn+") for k in kc))
print("\n== C. AYNI VIDEONUN BIRDEN FAZLA SORGUDA CIKMASI")
vq = defaultdict(set)
for r in av: vq[r["video_id"]].add(r["sorgu"])
for vid, qs in sorted(vq.items(), key=lambda x: -len(x[1])):
    if len(qs) > 1:
        r = next(x for x in av if x["video_id"] == vid); print(f"  {len(qs)} sorgu | {r['baslik'][:60]} | {r['kanal'][:20]} | {r['sure_metni']}")
print("\n== D. BASLIK KALIPLARI (ana 9 sorgu videolari)")
T = [r["baslik"] for r in av]; n = len(T)
def pay(f): return f"{100*sum(1 for t in T if f(t))/n:.0f}%"
low = lambda t: t.replace("İ", "i").replace("I", "ı").lower()
for etiket, f in [
    ("'|' ayirici", lambda t: "|" in t), ("' - ' ayirici", lambda t: " - " in t or " – " in t), ("'·' ayirici", lambda t: "·" in t), ("'/' ayirici", lambda t: " / " in t),
    ("emoji var", lambda t: bool(re.search("[\U0001F300-\U0001FAFF☀-➿]", t))), ("hashtag", lambda t: "#" in t),
    ("'çocuk şarkı' gecen", lambda t: "çocuk şarkı" in low(t)), ("'bebek şarkı' gecen", lambda t: "bebek şarkı" in low(t)),
    ("'bebek ve çocuk şarkı'", lambda t: "bebek ve çocuk şark" in low(t)), ("'çizgi film'", lambda t: "çizgi film" in low(t) or "çizgifilm" in low(t)),
    ("'eğitici'", lambda t: "eğitici" in low(t)), ("'eğlenceli'", lambda t: "eğlenceli" in low(t)), ("'en sevilen/en güzel/en popüler/en iyi'", lambda t: bool(re.search(r"en (sevilen|güzel|popüler|iyi)", low(t)))),
    ("yil (20xx)", lambda t: bool(re.search(r"\b20(1\d|2\d)\b", t))), ("'yeni'", lambda t: bool(re.search(r"\byeni\b", low(t)))), ("'okul öncesi'", lambda t: "okul öncesi" in low(t)),
    ("sure ifadesi (dk/dakika)", lambda t: bool(re.search(r"\d+\s*(dk|dakika)", low(t)))), ("'öğren'", lambda t: "öğren" in low(t)), ("TAMAMI BUYUK harfli kelime (4+ harf)", lambda t: bool(re.search(r"\b[A-ZÇĞİÖŞÜ]{4,}\b", t))),
    ("kanal adi baslikta", None)]:
    if f is None:
        print(f"  {etiket:42} {100*sum(1 for r in av if low(r['kanal'].split(' - ')[0].strip())[:12] in low(r['baslik']))/n:.0f}%")
    else: print(f"  {etiket:42} {pay(f)}")
L = [len(t) for t in T]; print("  baslik uzunlugu: medyan", st.median(L), "min", min(L), "max", max(L), "| 60 karakterden uzun:", f"{100*sum(1 for x in L if x>60)/n:.0f}%")
yil = Counter(m for t in T for m in re.findall(r"\b20(?:1\d|2\d)\b", t)); print("  yillar:", dict(yil))
print("  sorgu kelimesi basligin basinda (ilk 25 karakterde ilk sorgu kelimesi):")
for q, rows in gr.items():
    v = [r for r in rows if r["tur"] == "video"]; k = low(q.split()[0])[:5]
    print(f"    {q:24} {sum(1 for r in v if k in low(r['baslik'])[:25])}/{len(v)}  (herhangi yerde: {sum(1 for r in v if k in low(r['baslik']))}/{len(v)})")
print("\n== E. SURE / GORUNTULEME (9 sorgu, tekil video)")
uniq = {r["video_id"]: r for r in av}.values()
for et, lo, hi in [("short <=60s", 0, 60), ("tek sarki 1-5dk", 61, 299), ("5-10 dk", 300, 599), ("10-30 dk", 600, 1799), ("30 dk+", 1800, 10**7)]:
    g = [I(r["goruntuleme_sayi"]) for r in uniq if r["sure_saniye"] and lo <= I(r["sure_saniye"]) <= hi and r["goruntuleme_sayi"]]
    print(f"  {et:16} adet={len(g):3} medyanGor={kisa(int(st.median(g))) if g else '?'} toplamGor={kisa(sum(g))}")
print("  ilk 3 sirada sure:", Counter(("10dk+" if I(r["sure_saniye"]) >= 600 else "5-10dk" if I(r["sure_saniye"]) >= 300 else "tek") for r in av if r["sure_saniye"] and I(r["sira"]) <= 3))
print("\n== F. KUCUK KANALLAR ILK SAYFADA (abone < 10B) - ana sorgular")
for r in av:
    a = abone.get(r["kanal_id"])
    if a is not None and a < 10000:
        print(f"  [{r['sorgu'][:20]:20}] #{r['sira']:>2} {r['kanal'][:24]:24} abone={kisa(a):>5} gor={kisa(I(r['goruntuleme_sayi'])):>7} {r['sure_metni']:>7} {r['yas_metni']:12} | {r['baslik'][:50]}")
print("  sorgu basina: <10B abone / 10B-100B / bilinmeyen / <=12 ay yasli video")
for q, rows in gr.items():
    v = [r for r in rows if r["tur"] == "video"]
    a = [abone.get(r["kanal_id"]) for r in v]
    print(f"    {q:24} <10B={sum(1 for x in a if x is not None and x<1e4):2} 10B-100B={sum(1 for x in a if x is not None and 1e4<=x<1e5):2} ?={sum(1 for x in a if x is None):2} <=12ay={sum(1 for r in v if r['yas_ay'] and F(r['yas_ay'])<=12):2} gor<100B={sum(1 for r in v if r['goruntuleme_sayi'] and I(r['goruntuleme_sayi'])<1e5):2}")
