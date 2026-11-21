#!/bin/bash
# Reproduces the choice of the vocal source for v2_2.  Nothing here calls a paid or remote service.
#   usage: kod/calistir.sh <mdx|rof>      (the candidate named in kod/karar.json)
set -e
K="$(cd "$(dirname "$0")" && pwd)"
SEP=/tmp/claude-0/-home-user-ring-tokat-3d/bd9d6832-1bf0-57ca-8544-ce6f4befd453/scratchpad/sep
SEC="${1:-mdx}"
# 01: wait (at most 12 min) for the BS-Roformer file; skipped when it is already there
[ -n "$(ls "$SEP"/out_rof/*Vocals*.wav 2>/dev/null)" ] || python3 "$K/01_bekle_rof.py"
# 03: lag / clock of every candidate against the ffmpeg-decoded mix (the mix is decoded on demand by common.py)
python3 "$K/03_hizala.py" mdx "$(ls "$SEP"/out_mdx/*Vocals*.wav)" "$(ls "$SEP"/out_mdx/*Instrumental*.wav)"
if [ -n "$(ls "$SEP"/out_rof/*Vocals*.wav 2>/dev/null)" ]; then
  python3 "$K/03_hizala.py" rof "$(ls "$SEP"/out_rof/*Vocals*.wav)" "$(ls "$SEP"/out_rof/*Instrumental*.wav 2>/dev/null)"
fi
# 02: objective comparison (bleed, completeness, agreement)
python3 "$K/02_karsilastir.py"
# 05: bleed of the band inside the sung frames (harmonic comb + loop template)
python3 "$K/05_sarki_ici_sizinti.py"
# 04: write v2_2_vokal.wav, verify it, assemble rapor.json (reads the decision text from kod/karar.json)
python3 "$K/04_yaz.py" "$SEC"
