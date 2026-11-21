#!/usr/bin/env python3
"""Step 1: the frame table of the sung melody.

For every 5 ms frame of the separated vocal that is (a) voiced, (b) loud enough (gate) and (c) inside a KEPT
syllable of kesim.json (the sung animal sounds and the excised extra nucleus of verse 3 "atlari" are not kept),
store: verse, line, source time, pitch (MIDI, pyworld harvest), the dio/stonemask pitch (cross-check), and its
position in the NEW song form (beats from the downbeat of the verse; the placement shift of its piece from
kesim.json is applied, nothing is time-stretched).

Pitch tracker and gate are the ones of yeni4/analiz/kesim/kod (ozellik.py, zarf.py, perde.py), re-implemented here
so that nothing is written outside this folder:
    f0   = pyworld harvest, 150-700 Hz, 5 ms            (dio + stonemask as a second opinion)
    gate = voiced AND (100-1000 Hz band, 8 ms Hann power envelope) > sung RMS - 11 dB
The script ends with a check against the pitch-class histogram published in kesim.json.
"""
import sys, os
import numpy as np, soundfile as sf, pyworld as pw
from scipy.signal import butter, sosfiltfilt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *

K = load_json(KESIM)
SUNG = K["levels"]["sung_rms_dbfs"]
GATE_DB = 11.0

x, fs = sf.read(VOKAL)
if x.ndim > 1:
    x = x.mean(axis=1)
x = x.astype(np.float64)
assert fs == 44100

# ---- pitch ------------------------------------------------------------------------------------------------
f0h, th = pw.harvest(x, fs, f0_floor=150.0, f0_ceil=700.0, frame_period=FP * 1000)
f0d, td = pw.dio(x, fs, f0_floor=150.0, f0_ceil=700.0, frame_period=FP * 1000)
f0s = pw.stonemask(x, f0d, td, fs)
assert len(th) == len(td) and abs(th[1] - th[0] - FP) < 1e-9

# ---- gate envelope: exactly zarf.py's ELOW8 (computed on its 88-sample grid, then interpolated to the frames) --
sos = butter(4, [100, 1000], btype="band", fs=fs, output="sos")
y = sosfiltfilt(sos, x)
n = int(8 / 1000 * fs) | 1
h = np.hanning(n + 2)[1:-1]; h /= h.sum()
p = np.convolve(y ** 2, h, "same")
HOP = 88
tg = np.arange(1 + len(x) // HOP) * HOP / fs
env = 10 * np.log10(p[np.minimum(np.arange(len(tg)) * HOP, len(x) - 1)] + 1e-12)
lvl = np.interp(th, tg, env)
gate = (f0h > 0) & (lvl > SUNG - GATE_DB)
midi_h = np.where(f0h > 0, 69 + 12 * np.log2(np.maximum(f0h, 1e-6) / 440.0), np.nan)
midi_d = np.where(f0s > 0, 69 + 12 * np.log2(np.maximum(f0s, 1e-6) / 440.0), np.nan)


def frames(a, b):
    i0 = int(np.ceil(a / FP - 1e-9)); i1 = int(np.ceil(b / FP - 1e-9))
    return np.arange(i0, max(i0, i1))


rows = []          # one row per gated frame of a kept syllable
syl_rows = []      # one row per kept syllable (for the note-based cross-check in 05_dogrula.py)
hist_check = {ln: np.zeros(12) for ln in LINES}
for v, V in enumerate(K["verses"]):
    piece_of = {}
    for P in V["pieces"]:
        for seg in P["segments"]:
            piece_of[seg] = P
    verse_bar0 = LEAD_IN + (INTRO_BARS + VERSE_BARS * v) * BAR          # downbeat of the verse in the new form
    for L in V["lines"]:
        ln = L["name"]; P = piece_of[ln]; shift = P["placement"]["shift_s"]
        assert P["placement"]["target_bar_index_in_song"] == INTRO_BARS + VERSE_BARS * v + (5 if ln in ("diye", "L4") else LINE_BAR[ln])
        for si, S in enumerate(L["syllables"]):
            if not S["kept"] or S["excise"]:
                continue
            idx = frames(S["start"], S["end"])
            g = gate[idx]
            # histogram check: every gated frame of the kept syllable (as kesim.py: 'all voiced frames')
            for k in idx[g]:
                hist_check[ln][int(round(midi_h[k])) % 12] += FP
            # frames that survive the cut of the piece (inside cut_in .. cut_out)
            inside = (th[idx] >= P["cut_in"]) & (th[idx] < P["cut_out"])
            for k in idx[g & inside]:
                pos = (th[k] + shift - verse_bar0) / BEAT              # beats from the verse downbeat (new form)
                rows.append((v, LINES.index(ln), si, th[k], th[k] + shift, pos, midi_h[k],
                             midi_d[k] if np.isfinite(midi_d[k]) else -1.0))
            for N in S["notes"]:
                syl_rows.append((v, LINES.index(ln), si, N["start"], N["end"], N["midi"],
                                 (N["start"] + shift - verse_bar0) / BEAT, (N["end"] + shift - verse_bar0) / BEAT,
                                 float(N["no_plateau"])))

rows = np.array(rows); syl_rows = np.array(syl_rows)
np.savez_compressed(KARELER, verse=rows[:, 0].astype(int), line=rows[:, 1].astype(int), syl=rows[:, 2].astype(int),
                    t_src=rows[:, 3], t_new=rows[:, 4], pos=rows[:, 5], midi=rows[:, 6], midi_dio=rows[:, 7],
                    notes=syl_rows, sung_rms_dbfs=SUNG)

# ---- checks -------------------------------------------------------------------------------------------------
ref = K["notes_table"]["pitch_class_histogram_all_voiced_frames"]
worst = 0.0
for ln in LINES:
    for i, nme in enumerate(NOTE):
        a = hist_check[ln][i]; b = ref[ln]["seconds"].get(nme, 0.0)
        worst = max(worst, abs(a - b))
tot = sum(h.sum() for h in hist_check.values())
print("gated frames of kept syllables: %.3f s (kesim.json: %.3f s); largest pitch-class difference to kesim.json: %.3f s"
      % (tot, ref["overall"]["total_seconds"], worst))
assert abs(tot - ref["overall"]["total_seconds"]) < 0.05 and worst < 0.03, "frame table does not reproduce kesim.json"
print("frames kept after the cuts: %d = %.3f s" % (len(rows), len(rows) * FP))
for li, ln in enumerate(LINES):
    m = rows[:, 1] == li
    b0 = LINE_BAR[ln] * 4
    print("  %-4s %.2f s; position in its bar: %.2f .. %.2f beats" % (ln, m.sum() * FP, rows[m, 5].min() - b0, rows[m, 5].max() - b0))
dd = rows[:, 7] > 0
print("dio/stonemask agrees within 0.5 semitone on %.1f %% of the frames where both are voiced (%.1f %% of all frames)"
      % (100 * np.mean(np.abs(rows[dd, 6] - rows[dd, 7]) < 0.5), 100 * dd.mean()))
