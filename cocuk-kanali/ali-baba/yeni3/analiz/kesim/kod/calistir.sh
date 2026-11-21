#!/bin/bash
# Tum adimlari sirayla calistirir (yaklasik 1 dakika). Uzak servis / indirme YOK.
#   1) ozellik.py  : zarflar, log-mel, f0  -> ara/ozellik.npz
#   2) hizala.py   : kendi kendine egitilen harf hizalamasi -> ara/hizalama.json   (dize.py'yi kullanir)
#   3) kesim.py    : dize + hece + perde + onarim + gurultu -> kesim.json
#   4) dogrula.py  : ham WAV'dan bagimsiz kontroller -> dogrulama.txt, ornek/*.wav
#   5) ciz_ek.py   : 6. kita ek yerlerinin yakin cizimi -> cizim/K6_ek_yerleri.png
#   6) cizhepsi.sh : (istege bagli, "ciz" argumaniyla; 16 MB) 28 dizenin tani cizimi -> cizim/K*_L*.png
set -e
cd "$(dirname "$0")"
python3 ozellik.py
python3 hizala.py | tail -3
python3 kesim.py
python3 dogrula.py
python3 ciz_ek.py
if [ "$1" = "ciz" ]; then ./cizhepsi.sh; fi
