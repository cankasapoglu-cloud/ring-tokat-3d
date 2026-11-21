#!/bin/bash
# Reviewer re-renders (read-only use of the builder's build.py; nothing is written into yeni4/altyapi).
#  1) 104.96 BPM, keys G and C -> scratch folder: gives per-instrument stems + a reproducibility check against the delivered WAVs
#  2) 105.30 BPM, key G -> dogrulama/altyapi/tempo_testi_105.30 (tempo scaling test)
# usage: 00_yeniden_uret.sh <scratch folder>
set -e
KOD="$(cd "$(dirname "$0")" && pwd)"; D="$(dirname "$KOD")"; B="$(dirname "$(dirname "$D")")/altyapi/kod/build.py"
SP="$1"; mkdir -p "$SP/work" "$SP/out_10496" "$SP/work530" "$D/tempo_testi_105.30"
( time python3 "$B" --bpm 104.96 --key G --out "$SP/out_10496" --work "$SP/work" ) 2>&1
( time python3 "$B" --bpm 104.96 --key C --out "$SP/out_10496" --work "$SP/work" ) 2>&1
( time python3 "$B" --bpm 105.30 --key G --out "$D/tempo_testi_105.30" --work "$SP/work530" ) 2>&1
