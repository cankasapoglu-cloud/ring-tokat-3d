#!/bin/bash
# Dogal vokal yerlesimini (v2_2) bastan uretir ve dogrular. Hicbir ucretli / uzak servis kullanmaz.
#   kod/calistir.sh         -> ara/dogal_baslangic.json, vokal_dogal.wav, yerlesim.json, dogrulama.txt/json, cizim/*.png
#   kod/calistir.sh kesif   -> yalniz okuyan kesif ciktilari (kesim noktalarinin kendi olcumu, kaynak spektrogramlari)
set -e
K="$(cd "$(dirname "$0")" && pwd)"
export PYTHONWARNINGS=ignore
if [ "$1" = "kesif" ]; then
  python3 "$K/01_incele.py"
  python3 "$K/02_ciz_kaynak.py"
  exit 0
fi
python3 "$K/01b_dogal_baslangic.py" > /dev/null     # 3. kita giris gecisinin dayanagi (ara/dogal_baslangic.json)
python3 "$K/03_yerlestir.py"
python3 "$K/04_dogrula.py"
python3 "$K/05_ciz.py"
