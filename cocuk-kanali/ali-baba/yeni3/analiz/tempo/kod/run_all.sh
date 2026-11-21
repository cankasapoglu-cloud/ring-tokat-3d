#!/bin/bash
# Reproduce the whole tempo-grid analysis. Output: ../tempo.json (+ intermediate *.json). Temporary data: ../gecici/
set -e
cd "$(dirname "$0")"
bash 00_decode.sh
python3 01_align.py            # coarse mix/vocal timeline check
python3 02_tempo.py            # step 1: tempo + phase, methods A and B, 20 s windows
python3 03_explore_grid.py > ../gecici/explore_eighths.txt     # exploration table (per eighth note)
python3 04_harmony.py  > ../gecici/explore_harmony.txt         # exploration table (per beat bass/chord)
python3 05_phase_fine.py       # fine phase per band + librosa third opinion
python3 13_drift_fine.py       # fine drift check against exact 116.000
python3 14_lattice.py          # refined lattice
python3 07_vocal_onsets_explore.py > ../gecici/explore_vocal_onsets.txt   # also writes lines_words.json
python3 08_vocal_trace.py L4 > ../gecici/explore_vocal_traces_L4.txt
python3 09_align_fine.py       # mix <-> vocal lag per line (envelope)
python3 12_align_spectro.py    # mix <-> vocal lag per line (spectro-temporal)
python3 06_downbeat.py > ../gecici/downbeat_log.txt            # step 2: bar-line evidence
python3 10_bass_notes.py > ../gecici/bass_notes_log.txt
python3 11_lines.py            # step 3: the 28 lines
python3 15_write_json.py       # deliverable
python3 16_verify.py           # checks on the deliverable
