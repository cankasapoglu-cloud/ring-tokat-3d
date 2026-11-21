#!/bin/bash
# Reproduce the whole tempo / bar-line / key analysis of v2_2. Output: ../tempo.json (+ intermediate *.json). Cache: ../gecici/
set -e
cd "$(dirname "$0")"
bash 00_decode.sh
python3 02_tempo.py        > ../gecici/tempo_log.txt         # tempo + phase, methods A, B, C, 20 s windows
python3 05_phase_fine.py   > ../gecici/phase_log.txt 2>&1    # fine phase per band + librosa third opinion
python3 13_drift_fine.py   > ../gecici/drift_log.txt         # fine drift check against exact 105.000
python3 14_lattice.py      > ../gecici/lattice_log.txt       # refined lattice
python3 04_explore_lowspec.py  > ../gecici/explore_lowspec.txt   # exploration: spectral peaks 30-520 Hz per beat
python3 04b_explore_bassreg.py > ../gecici/explore_bassreg.txt   # exploration: 30-200 Hz (kick only, no bass guitar)
python3 06_downbeat.py     > ../gecici/downbeat_log.txt      # bar-line evidence
python3 10_bass_notes.py   > ../gecici/bass_notes_log.txt    # lowest pitched note per beat
python3 17_key.py          > ../gecici/key_log.txt 2>&1      # chords, key, tuning
python3 11_segments.py     > ../gecici/segments_log.txt      # the 35 segments
python3 18_pitch.py        > ../gecici/pitch_log.txt 2>&1    # rough sung pitch + key fit for the new backing
python3 15_write_json.py   > ../gecici/write_log.txt         # deliverable
python3 16_verify.py                                         # checks on the deliverable
