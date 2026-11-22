#!/usr/bin/env python3
"""Kontrol sayfası: videodan belirli saniyelerde kare alıp tek resimde dizer.
Kullanım: python3 kontrol.py <video> <çıktı jpg> [saniye ...]   (saniye verilmezse 18 eşit aralık)"""
import subprocess, sys, os, tempfile
from PIL import Image, ImageDraw
v, cikti = sys.argv[1], sys.argv[2]
sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], capture_output=True, text=True).stdout)
zaman = [float(x) for x in sys.argv[3:]] or [sure * (i + 0.5) / 18 for i in range(18)]
g = tempfile.mkdtemp(); sutun = 3; im = Image.new("RGB", (sutun * 640, ((len(zaman) + sutun - 1) // sutun) * 360))
for i, t in enumerate(zaman):
    y = os.path.join(g, f"{i}.jpg"); subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", v, "-frames:v", "1", "-vf", "scale=640:360", y], check=True)
    f = Image.open(y); d = ImageDraw.Draw(f); d.rectangle((0, 0, 62, 20), fill=(0, 0, 0)); d.text((5, 4), f"{t:.1f} sn", fill=(255, 255, 0)); im.paste(f, ((i % sutun) * 640, (i // sutun) * 360))
im.save(cikti, quality=85)
