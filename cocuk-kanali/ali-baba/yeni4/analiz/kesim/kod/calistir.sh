#!/bin/bash
# v2_2 ayrilmis vokalinin kesimi - tum adimlar (yaklasik 2 dakika). Uzak servis / indirme YOK.
#   1) ozellik.py : zarflar, log-mel, f0 (pyworld)                       -> ara/ozellik.npz (onbellek; silinebilir)
#   2) dize.py    : bolum sinirlari + iki zor kesimin olcumu (ekrana)    (kesim.py icinden de cagrilir)
#   3) kesim.py   : hece cekirdekleri (izgara.py), hece sinirlari (hece.py), perde / nota (perde.py),
#                   'atları' denetimi (atlari.py), nota tablosu, gurultu tabani  -> kesim.json
#   4) dogrula.py : ham WAV'dan bagimsiz kontroller -> dogrulama.txt, ornek/*.wav   (hata varsa cikis kodu 1)
#   5) ciz.py     : tani cizimleri -> cizim/*.png
# Tani araclari (ciktiya girmez): iz.py (zaman araligi icin zarf / perde dokumu), dene_hece.py, dene_tablo.py
# (sinirlarin izgaraya gore yeri, 7 kita yan yana).
set -e
cd "$(dirname "$0")"
python3 ozellik.py
python3 dize.py > ../ara/dize_cikti.txt
python3 kesim.py
python3 dogrula.py > /dev/null || { tail -5 ../dogrulama.txt; exit 1; }
tail -3 ../dogrulama.txt
python3 ciz.py
