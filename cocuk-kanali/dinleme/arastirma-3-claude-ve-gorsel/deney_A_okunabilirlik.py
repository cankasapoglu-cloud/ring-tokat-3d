#!/usr/bin/env python3
"""Deney A: Claude'un Read araciyla gordugu PNG'de en kucuk okunabilir yazi boyu
ve en kucuk ayirt edilebilir dikey kayma (piksel) kac? Kor test: dogru cevaplar
gizli/ klasorune yazilir, once resim okunur, sonra karsilastirilir.
Kullanim: python3 deney_A_okunabilirlik.py <genislik> <yukseklik> <tohum>
"""
import sys, json, random, os
from PIL import Image, ImageDraw, ImageFont

W, H, SEED = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "deney-A-okunabilirlik", f"okuma_{W}x{H}.png")
TRUTH = os.path.join(BASE, "gizli", f"A_dogru_{W}x{H}.json")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
rnd = random.Random(SEED)

NOTES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
def token():
    k = rnd.choice(["nota", "sayi", "sure"])
    if k == "nota":
        return rnd.choice(NOTES) + str(rnd.randint(2, 6))
    if k == "sayi":
        return str(rnd.randint(100, 999))
    return f"{rnd.randint(0, 59)}.{rnd.randint(10, 99)}"

img = Image.new("RGB", (W, H), "#fcfcfb")
d = ImageDraw.Draw(img)
truth = {"boyut": [W, H], "satirlar": {}, "kaymalar": {}}

# --- Bolum 1: yazi boylari (font piksel boyu; buyuk harf yuksekligi ~0.73x) ---
y = 10
big = ImageFont.truetype(FONT, 26)
for px in [7, 9, 11, 13, 16, 20, 26]:
    f = ImageFont.truetype(FONT, px)
    toks = [token() for _ in range(8)]
    truth["satirlar"][str(px)] = toks
    d.text((10, y), f"S{px}:", font=big, fill="#0b0b0b")
    x = 130
    for t in toks:
        d.text((x, y + (26 - px) // 2), t, font=f, fill="#0b0b0b")
        x += int((W - 150) / 8)
    y += 40

# --- Bolum 2: dikey kayma testi (yari-ton izgarasi gibi) ---
# Her hucrede gri referans cizgisi + mavi 3px kalin kisa cizgi; mavi cizgi
# referansin k piksel ustunde (+) veya altinda (-) ya da tam ustunde (0).
y0 = y + 30
d.text((10, y0 - 28), "KAYMA: her hucrede mavi cizgi gri cizgiye gore yukari(+) / asagi(-) / ustunde(0)?", font=ImageFont.truetype(FONT, 20), fill="#0b0b0b")
cols, rows = 10, 3
cw = (W - 20) // cols
ch = max(60, (H - y0 - 20) // rows)
offs_pool = [0, 2, -2, 3, -3, 5, -5, 8, -8, 12, -12]
idx = 0
for r in range(rows):
    for c in range(cols):
        idx += 1
        off = rnd.choice(offs_pool)
        cx, cy = 10 + c * cw, y0 + r * ch
        d.rectangle([cx + 2, cy + 2, cx + cw - 4, cy + ch - 4], outline="#c3c2b7")
        d.text((cx + 6, cy + 4), f"K{idx}", font=ImageFont.truetype(FONT, 18), fill="#0b0b0b")
        ry = cy + ch // 2 + 8
        d.line([cx + 10, ry, cx + cw - 12, ry], fill="#52514e", width=1)
        by = ry - off  # + = yukari
        d.line([cx + cw // 4, by, cx + 3 * cw // 4, by], fill="#2a78d6", width=3)
        truth["kaymalar"][f"K{idx}"] = off

img.save(OUT)
os.makedirs(os.path.dirname(TRUTH), exist_ok=True)
json.dump(truth, open(TRUTH, "w"), ensure_ascii=False, indent=1)
print("yazildi:", OUT, "(dogru cevaplar gizli/ altinda; once resmi oku)")
