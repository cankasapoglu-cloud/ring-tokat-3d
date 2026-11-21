#!/bin/bash
# Tum dizelerin tani cizimlerini uretir: cizim/K{kita}_{parca}.png
cd "$(dirname "$0")"
mkdir -p ../cizim
python3 - <<'PY'
import json, os, subprocess, sys
K = os.path.dirname(os.getcwd())
kj = os.path.join(K, "kesim.json")
d = json.load(open(kj, encoding="utf8"))
for v in d["verses"]:
    L = v["lines"]
    for ad, a, b in (("L1", L[0]["start"] - 0.1, L[0]["end"] + 0.08), ("L2", L[1]["start"] - 0.06, L[1]["end"] + 0.08),
                     ("L3", L[2]["start"] - 0.06, L[2]["end"] + 0.12), ("L4", L[3]["start"] - 0.1, L[3]["end"] + 0.25)):
        subprocess.run([sys.executable, "ciz.py", "%.3f" % a, "%.3f" % b, os.path.join(K, "cizim", "K%d_%s.png" % (v["verse"], ad))], check=True, stdout=subprocess.DEVNULL)
print("cizimler tamam")
PY
