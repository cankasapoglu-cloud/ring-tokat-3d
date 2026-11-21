#!/bin/bash
# Builds both variants of the yeni3 backing and verifies them.
# usage: kod/calistir.sh [scratch folder]      (the scratch folder receives ~0.6 GB of intermediate renders)
set -e
KOD="$(cd "$(dirname "$0")" && pwd)"; OUT="$(dirname "$KOD")"
WORK="${1:-${TMPDIR:-/tmp}/alibaba_yeni3_altyapi_work}"
BPM="${BPM:-116.015}"
mkdir -p "$WORK"
python3 "$KOD/build.py" --bpm "$BPM" --key C --name dogal --out "$OUT" --work "$WORK"
python3 "$KOD/build.py" --bpm "$BPM" --key G --name ezgi  --out "$OUT" --work "$WORK"
python3 "$KOD/dogrula.py" "$OUT" "$WORK" dogal ezgi | tee "$OUT/dogrulama.txt"
