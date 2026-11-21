#!/bin/bash
# Harmony designer A ("sade"): reruns everything (about 1.5 minutes). Writes only inside yeni4/tasarim/A/, except the
# scratch WAV renders of step 04, which go to $ALIBABA_WORK (default: <system temp>/alibaba_yeni4_tasarimA_work).
#   01 frame table of the sung melody (pyworld harvest, gate and syllable notes of kesim.json)   -> ara/kareler.npz
#   02 band model checked against the builder's MIDI
#   03 every I / IV / V7 harmony in C, F, G + baseline + original D minor loop                   -> olcum.json, adaylar.json
#   04 audio check on rendered band audio (FluidSynth)                                            -> ses_olcumu.json, ara/ses/*.mid
#   05 under-vocal policy numbers                                                                 -> alt_politika.json
#   06 the plan                                                                                   -> plan.json
#   07 independent verification                                                                   -> dogrulama.txt
set -e
cd "$(dirname "$0")"
python3 01_kareler.py 2>&1 | grep -v pkg_resources
python3 02_bant_dogrula.py
python3 03_olcum.py
python3 04_ses_olcumu.py > ../ara/ses_cikti.txt
tail -n 16 ../ara/ses_cikti.txt
python3 05_alt_politika.py
python3 06_plan.py
python3 07_dogrula.py
