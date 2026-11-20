#!/usr/bin/env python3
"""Ham görselin arka planını siler, kenarlarını kırpar, önizleme üretir.
Kullanım: python3 kes.py ham/elma_1.png varlik/elma.png
Önizleme: onizle/<ad>.jpg (mavi zemin üzerinde, kontrol için)."""
import sys, os
from PIL import Image
import numpy as np
from rembg import new_session, remove

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
out = remove(im, session=new_session("birefnet-general-lite"))
a = np.array(out)
ys, xs = np.where(a[..., 3] > 12)
if len(xs) == 0:
    sys.exit("HATA: nesne bulunamadı")
p = 10
box = (max(0, xs.min() - p), max(0, ys.min() - p), min(a.shape[1], xs.max() + p), min(a.shape[0], ys.max() + p))
out = out.crop(box)
os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
out.save(dst)
bg = Image.new("RGBA", out.size, (120, 190, 255, 255))
bg.alpha_composite(out)
D = os.path.dirname(os.path.abspath(__file__))
on = os.path.join(D, "onizle", os.path.splitext(os.path.basename(dst))[0] + ".jpg")
bg.convert("RGB").save(on, quality=85)
print(f"{dst}: {out.size[0]}x{out.size[1]}  önizleme: {on}")
