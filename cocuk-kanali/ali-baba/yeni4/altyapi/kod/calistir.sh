#!/bin/bash
# Builds both keys of the yeni4 backing (v2_2 form) and verifies them.
# usage: BPM=104.96 kod/calistir.sh [scratch folder]     (the scratch folder receives ~1.5 GB of intermediate renders)
# When the exact tempo of v2_2 is known, run this again with BPM=<value>; everything is derived from it.
set -e
KOD="$(cd "$(dirname "$0")" && pwd)"; OUT="$(dirname "$KOD")"
WORK="${1:-${TMPDIR:-/tmp}/alibaba_yeni4_altyapi_work}"
BPM="${BPM:-104.96}"
mkdir -p "$WORK"
python3 "$KOD/build.py" --bpm "$BPM" --key G --out "$OUT" --work "$WORK"
python3 "$KOD/build.py" --bpm "$BPM" --key C --out "$OUT" --work "$WORK"
python3 "$KOD/dogrula.py" "$OUT" "$WORK" G C | tee "$OUT/dogrulama.txt"
# optional: python3 "$KOD/olcek_testi.py" "$OUT" "$WORK" 105.30 G    (re-render at another tempo and compare all times)
