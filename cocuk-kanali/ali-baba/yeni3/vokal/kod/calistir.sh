#!/bin/bash
# Dogal vokal yerlesimini bastan uretir ve dogrular.
#   kod/calistir.sh            -> vokal_dogal.wav + yerlesim.json + dogrulama.txt/json
#   kod/calistir.sh ciz        -> ayrica cizim/*.png (onarim yerlerinin once/sonra goruntuleri)
#   kod/calistir.sh kesif      -> yalniz okuyan kesif ciktilari (girdi yapisi, kesim noktasi profilleri)
# 3. kitanin son 'bak'indan sonraki fazladan sesi BIRAKMAK icin: python3 kod/03_yerlestir.py --k3-ek-ses-kalsin
set -e
K="$(cd "$(dirname "$0")" && pwd)"
V="$(dirname "$K")"
A="$(dirname "$(dirname "$V")")"
if [ "$1" = "kesif" ]; then
  python3 "$K/00_girdi_incele.py"
  python3 "$K/01_incele.py"
  python3 "$K/01_incele.py" ince
  exit 0
fi
python3 "$K/03_yerlestir.py"
python3 "$K/04_dogrula.py"
if [ "$1" = "ciz" ]; then
  mkdir -p "$V/cizim"
  S="$A/dinle_2_vokal.wav"; D="$V/vokal_dogal.wav"
  # 6. kita L2: ozgun 'ördekleri' ve yerlesmis 'köpekleri' (ayni zaman olcegi)
  python3 "$K/02_ciz.py" "$S" "$V/cizim/K6_L2_once_ordekleri.png" 76.60 77.40 76.6977 76.8374 77.0828 77.2444
  python3 "$K/02_ciz.py" "$D" "$V/cizim/K6_L2_sonra_kopekleri.png" 95.728 96.528 95.8257 95.9003 95.9183 95.9653 96.2367 96.3724
  # 6. kita L3|L4 birlesimi: yerlesmis dosya
  python3 "$K/02_ciz.py" "$D" "$V/cizim/K6_L3_L4_birlesim.png" 101.15 101.65 101.3397 101.3662
  # 3. kita L4 sonu: ozgun (fazladan sesle) ve yerlesmis (kesilmis)
  python3 "$K/02_ciz.py" "$S" "$V/cizim/K3_L4_son_once.png" 40.70 41.75 41.2463 41.3171 41.3879 41.5895
  python3 "$K/02_ciz.py" "$D" "$V/cizim/K3_L4_son_sonra.png" 53.10465 54.15465 53.7218 53.7861
fi
