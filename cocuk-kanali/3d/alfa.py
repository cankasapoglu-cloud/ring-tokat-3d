#!/usr/bin/env python3
"""Tek görselin arka planını siler (kırpmadan). Bellek için ayrı süreçte çalıştırılır.
Kullanım: python3 alfa.py giris.png cikis.png"""
import sys
from PIL import Image
from rembg import new_session, remove
remove(Image.open(sys.argv[1]).convert("RGB"), session=new_session("birefnet-general-lite")).save(sys.argv[2])
