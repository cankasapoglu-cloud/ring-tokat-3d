#!/usr/bin/env python3
"""varlik/ ve ham/ içindeki görselleri videoda kullanılacak hale getirir -> hazir/
- Pıtır pozları: hepsi aynı kutuyla kırpılır (boy ve ayak hizası sabit kalır).
- Ağız/göz varyantları: yalnızca değişen bölge taban görsele yamanır (titreme olmaz).
- Balon 6 renge boyanır, arka planlar 1920x1080 yapılır, perde ikiye bölünür."""
import os, glob, sys, colorsys
import numpy as np
from PIL import Image, ImageFilter
import subprocess

D = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(D, "hazir"), exist_ok=True)
os.makedirs(os.path.join(D, "onbellek"), exist_ok=True)


def arka_plan_sil(yol):
    """rembg'yi ayrı süreçte çalıştırır (bellek sınırı), sonucu önbelleğe alır."""
    c = os.path.join(D, "onbellek", os.path.basename(yol))
    if not os.path.exists(c) or os.path.getmtime(c) < os.path.getmtime(yol):
        subprocess.run([sys.executable, os.path.join(D, "alfa.py"), yol, c], check=True)
    return Image.open(c).convert("RGBA")

ham = lambda ad: os.path.join(D, "ham", ad + ".png")
out = lambda ad: os.path.join(D, "hazir", ad)


def hizala(taban, var, kutu, ara=10):
    """var görselini taban ile kutu içinde en iyi örtüşecek şekilde kaydır (dx, dy)."""
    x0, y0, x1, y1 = kutu
    a = np.asarray(taban.convert("L"), dtype=np.float32)[y0:y1:2, x0:x1:2]
    v = np.asarray(var.convert("L"), dtype=np.float32)
    en, kay = 1e18, (0, 0)
    for dy in range(-ara, ara + 1):
        for dx in range(-ara, ara + 1):
            b = v[y0 + dy:y1 + dy:2, x0 + dx:x1 + dx:2]
            if b.shape != a.shape:
                continue
            f = np.mean(np.abs(a - b))
            if f < en:
                en, kay = f, (dx, dy)
    return kay, en


def yama(taban_rgb, var_rgb, alfa, bolge):
    """Varyanttaki farkı (ağız ya da göz) taban görsele yamalar. bolge: 'agiz' | 'goz'."""
    ys, xs = np.where(alfa > 128)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    h = y1 - y0
    bas = (x0, y0, x1, y0 + int(h * 0.55))                 # baş bölgesi
    (dx, dy), hata = hizala(taban_rgb, var_rgb, bas)
    var = Image.new("RGB", var_rgb.size)
    var.paste(var_rgb, (-dx, -dy))
    fark = np.abs(np.asarray(taban_rgb, dtype=np.int16) - np.asarray(var, dtype=np.int16)).sum(axis=2).astype(np.float32)
    m = np.zeros_like(fark)
    cx = (x0 + x1) // 2
    if bolge == "agiz":
        ya, yb = y0 + int(h * 0.30), y0 + int(h * 0.50)
        xa, xb = cx - int(h * 0.13), cx + int(h * 0.13)
    else:
        ya, yb = y0 + int(h * 0.13), y0 + int(h * 0.36)
        xa, xb = cx - int(h * 0.24), cx + int(h * 0.24)
    m[ya:yb, xa:xb] = (fark[ya:yb, xa:xb] > 40)
    if m.sum() < 30:
        return None, (dx, dy), hata, 0
    mi = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(5))
    sonuc = Image.composite(var, taban_rgb, mi)
    return sonuc, (dx, dy), hata, int(m.sum())


# ---------- Pıtır ----------
pozlar = sorted(os.path.basename(f)[6:-4] for f in glob.glob(ham("pitir_*"))
                if not f[:-4].endswith(("_1", "_2", "_3", "_4", "_a", "_b", "_c", "_d")))
tabanlar = [p for p in pozlar if not p.endswith(("_agiz", "_goz"))]
katman, kutular = {}, []
for p in tabanlar:
    rgb = Image.open(ham("pitir_" + p)).convert("RGB")
    rgba = arka_plan_sil(ham("pitir_" + p))
    alfa = np.asarray(rgba)[..., 3]
    katman["pitir_" + p] = rgba
    ys, xs = np.where(alfa > 12)
    kutular.append((xs.min(), ys.min(), xs.max(), ys.max()))
    for ek, bolge in (("_agiz", "agiz"), ("_goz", "goz")):
        if p + ek in pozlar:
            v = Image.open(ham("pitir_" + p + ek)).convert("RGB")
            s, kay, hata, alan = yama(rgb, v, alfa, bolge)
            print(f"  {p}{ek}: kayma={kay} hata={hata:.1f} alan={alan}", "" if s else "-> YAMA YOK")
            if s:
                s = s.convert("RGBA"); s.putalpha(rgba.getchannel("A"))
                katman["pitir_" + p + ek] = s
k = np.array(kutular)
# ortak kutu: yatayda simetrik (çapa tam ortada kalsın), dikeyde tüm pozları kapsar
W0 = katman["pitir_durus"].size[0]
cx = (kutular[tabanlar.index("durus")][0] + kutular[tabanlar.index("durus")][2]) // 2
yari = max(cx - k[:, 0].min(), k[:, 2].max() - cx) + 8
kutu = (max(0, cx - yari), max(0, k[:, 1].min() - 6), min(W0, cx + yari), kutular[tabanlar.index("durus")][3] + 6)
for ad, im in katman.items():
    im.crop(kutu).save(out(ad + ".png"))
print("Pıtır kutusu:", kutu, "boy:", kutu[3] - kutu[1], "| pozlar:", ", ".join(sorted(katman)))

# ---------- balon renkleri ----------
bp = os.path.join(D, "varlik", "balon_kirmizi.png")
if os.path.exists(bp):
    b = np.asarray(Image.open(bp).convert("RGBA")).astype(np.float32) / 255
    hsv = np.array(Image.fromarray((b[..., :3] * 255).astype(np.uint8)).convert("HSV")).astype(np.float32)
    kirmizi = (hsv[..., 1] > 70) & ((hsv[..., 0] < 22) | (hsv[..., 0] > 235))   # ip ve düğüm dışı gövde
    for ad, ton, doy, par in (("kirmizi", 0, 1, 1), ("mavi", 150, 1.0, 1.0), ("sari", 36, 1.0, 1.25), ("yesil", 88, 1.0, 0.95),
                              ("turuncu", 20, 1.05, 1.15), ("mor", 200, 0.95, 0.9)):
        h2 = hsv.copy()
        h2[..., 0] = np.where(kirmizi, (hsv[..., 0] + ton) % 256, hsv[..., 0])
        h2[..., 1] = np.where(kirmizi, np.clip(hsv[..., 1] * doy, 0, 255), hsv[..., 1])
        h2[..., 2] = np.where(kirmizi, np.clip(hsv[..., 2] * par, 0, 255), hsv[..., 2])
        rgb = Image.fromarray(h2.astype(np.uint8), "HSV").convert("RGB").convert("RGBA")
        rgb.putalpha(Image.fromarray((b[..., 3] * 255).astype(np.uint8)))
        rgb.save(out(f"balon_{ad}.png"))

# ---------- arka planlar ve perde ----------
for f in glob.glob(os.path.join(D, "varlik", "bg_*.png")):
    Image.open(f).convert("RGB").resize((1920, 1080), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2)).save(
        out(os.path.basename(f)[:-4] + ".jpg"), quality=93)
pp = os.path.join(D, "varlik", "perde.png")
if os.path.exists(pp):
    p = Image.open(pp).convert("RGB")
    w, h = p.size
    p = p.crop((0, 0, w, int(h * 0.86))).resize((1920, 1080), Image.LANCZOS)
    p.crop((0, 0, 960, 1080)).save(out("perde_sol.jpg"), quality=93)
    p.crop((960, 0, 1920, 1080)).save(out("perde_sag.jpg"), quality=93)

# ---------- diğer her şey ----------
for f in glob.glob(os.path.join(D, "varlik", "*.png")):
    ad = os.path.basename(f)
    if ad.startswith(("pitir_", "bg_", "perde", "balon_")):
        continue
    Image.open(f).save(out(ad))
print("hazir/:", len(os.listdir(os.path.join(D, "hazir"))), "dosya")
