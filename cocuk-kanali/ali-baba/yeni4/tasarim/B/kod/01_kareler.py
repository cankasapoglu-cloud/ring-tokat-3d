#!/usr/bin/env python3
"""Step 1: the frame table of the sung melody (adapted from yeni4/tasarim/A/kod/01_kareler.py, same tracker and gate
as yeni4/analiz/kesim/kod: pyworld harvest 150-700 Hz, 5 ms; gate = voiced AND 100-1000 Hz envelope > sung RMS - 11 dB).

One row per 5 ms frame that is voiced, loud enough and inside a KEPT syllable of kesim.json (the sung animal sounds and
the excised extra nucleus of verse 3 "atlari" are not kept) and inside the cut range of its piece:
  verse, line, syllable index, source time, time in the NEW song form (source time + placement.shift_s of the piece:
  no time-stretch), position in beats from the verse downbeat, the frame's own pitch, and the NOTE it belongs to
  (kesim.json syllable.notes: the stable plateaus partition every syllable, so a scoop or glide belongs to its note).
Extra columns of designer B:
  note_on_beat  : beat slot of the syllable (beat_expected of kesim.json), to weigh metrically strong notes
  last_of_line  : the frame belongs to the last syllable of its line (the phrase-final note)

Checks at the end: (1) the pitch-class histogram of kesim.json is reproduced; (2) INDEPENDENT cross-check on the PLACED
vocal (yeni4/vokal/vokal_dogal.wav, if it exists): that file is pitch-tracked on its own and the pitch found at
t_new of every frame is compared with the table (verifies the placement shift AND the kept / cut bookkeeping).
"""
import sys, os
import numpy as np, soundfile as sf, pyworld as pw
from scipy.signal import butter, sosfiltfilt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *

K = load_json(KESIM)
SUNG = K["levels"]["sung_rms_dbfs"]
GATE_DB = 11.0


def track(path):
    x, fs = sf.read(path)
    if x.ndim > 1:
        x = x.mean(axis=1)
    x = x.astype(np.float64)
    assert fs == 44100
    f0h, th = pw.harvest(x, fs, f0_floor=150.0, f0_ceil=700.0, frame_period=FP * 1000)
    f0d, td = pw.dio(x, fs, f0_floor=150.0, f0_ceil=700.0, frame_period=FP * 1000)
    f0s = pw.stonemask(x, f0d, td, fs)
    sos = butter(4, [100, 1000], btype="band", fs=fs, output="sos")
    y = sosfiltfilt(sos, x)
    n = int(8 / 1000 * fs) | 1
    h = np.hanning(n + 2)[1:-1]; h /= h.sum()
    p = np.convolve(y ** 2, h, "same")
    HOP = 88
    tg = np.arange(1 + len(x) // HOP) * HOP / fs
    env = 10 * np.log10(p[np.minimum(np.arange(len(tg)) * HOP, len(x) - 1)] + 1e-12)
    lvl = np.interp(th, tg, env)
    mh = np.where(f0h > 0, 69 + 12 * np.log2(np.maximum(f0h, 1e-6) / 440.0), np.nan)
    md = np.where(f0s > 0, 69 + 12 * np.log2(np.maximum(f0s, 1e-6) / 440.0), np.nan)
    return th, mh, md, lvl, f0h > 0


th, midi_h, midi_d, lvl, voiced = track(VOKAL)
gate = voiced & (lvl > SUNG - GATE_DB)


def frames(a, b):
    i0 = int(np.ceil(a / FP - 1e-9)); i1 = int(np.ceil(b / FP - 1e-9))
    return np.arange(i0, max(i0, i1))


rows = []; note_rows = []
hist_check = {ln: np.zeros(12) for ln in LINES}
for v, V in enumerate(K["verses"]):
    piece_of = {}
    for P in V["pieces"]:
        for seg in P["segments"]:
            piece_of[seg] = P
    verse_bar0 = LEAD_IN + (INTRO_BARS + VERSE_BARS * v) * BAR
    for L in V["lines"]:
        ln = L["name"]; P = piece_of[ln]; shift = P["placement"]["shift_s"]
        assert P["placement"]["target_bar_index_in_song"] == INTRO_BARS + VERSE_BARS * v + (5 if ln in ("diye", "L4") else LINE_BAR[ln])
        kept = [S for S in L["syllables"] if S["kept"] and not S["excise"]]
        for si, S in enumerate(L["syllables"]):
            if not S["kept"] or S["excise"]:
                continue
            idx = frames(S["start"], S["end"])
            g = gate[idx]
            for k in idx[g]:
                hist_check[ln][int(round(midi_h[k])) % 12] += FP
            inside = (th[idx] >= P["cut_in"]) & (th[idx] < P["cut_out"])
            nts = S["notes"]
            assert abs(nts[0]["start"] - S["start"]) < 1e-6 and abs(nts[-1]["end"] - S["end"]) < 1e-6
            slot = float(S["beat_expected"])                       # beats from the SOURCE verse downbeat (0..16)
            last = S is kept[-1]
            for k in idx[g & inside]:
                pos = (th[k] + shift - verse_bar0) / BEAT
                nm_ = [N["midi"] for N in nts if N["start"] - 1e-9 <= th[k] < N["end"] + 1e-9]
                assert len(nm_) >= 1, (v, ln, S["text"], th[k])
                rows.append((v, LINES.index(ln), si, th[k], th[k] + shift, pos, midi_h[k],
                             midi_d[k] if np.isfinite(midi_d[k]) else -1.0, nm_[0], slot, float(last)))
            for N in nts:
                note_rows.append((v, LINES.index(ln), si, N["start"], N["end"], N["midi"],
                                  (N["start"] + shift - verse_bar0) / BEAT, (N["end"] + shift - verse_bar0) / BEAT,
                                  float(N["no_plateau"]), slot, float(last)))

rows = np.array(rows); note_rows = np.array(note_rows)
np.savez_compressed(KARELER, verse=rows[:, 0].astype(int), line=rows[:, 1].astype(int), syl=rows[:, 2].astype(int),
                    t_src=rows[:, 3], t_new=rows[:, 4], pos=rows[:, 5], midi=rows[:, 6], midi_dio=rows[:, 7],
                    note_midi=rows[:, 8], slot=rows[:, 9], last=rows[:, 10].astype(bool), notes=note_rows, sung_rms_dbfs=SUNG)

# ---- check 1: kesim.json's histogram ---------------------------------------------------------------------------
ref = K["notes_table"]["pitch_class_histogram_all_voiced_frames"]
worst = 0.0
for ln in LINES:
    for i, nme in enumerate(NOTE):
        worst = max(worst, abs(hist_check[ln][i] - ref[ln]["seconds"].get(nme, 0.0)))
tot = sum(h.sum() for h in hist_check.values())
print("gated frames of kept syllables: %.3f s (kesim.json: %.3f s); largest pitch-class difference to kesim.json: %.3f s"
      % (tot, ref["overall"]["total_seconds"], worst))
assert abs(tot - ref["overall"]["total_seconds"]) < 0.05 and worst < 0.03, "frame table does not reproduce kesim.json"
print("frames kept after the cuts: %d = %.3f s" % (len(rows), len(rows) * FP))
for li, ln in enumerate(LINES):
    m = rows[:, 1] == li
    b0 = LINE_BAR[ln] * 4
    print("  %-4s %.2f s; position in its bar: %.3f .. %.3f beats" % (ln, m.sum() * FP, rows[m, 5].min() - b0, rows[m, 5].max() - b0))
pcf = np.round(rows[:, 6]).astype(int) % 12; pcn = np.round(rows[:, 8]).astype(int) % 12
print("pitch-class shares, note of the frame  :", " ".join("%s %.1f%%" % (NOTE[i], 100 * np.mean(pcn == i)) for i in range(12) if np.mean(pcn == i) > 0.0005))
print("pitch-class shares, per-frame rounding :", " ".join("%s %.1f%%" % (NOTE[i], 100 * np.mean(pcf == i)) for i in range(12) if np.mean(pcf == i) > 0.0005))
print("frames whose own pitch rounds to the pitch class of their note: %.1f %%" % (100 * np.mean(pcf == pcn)))

# ---- check 2: the placed vocal, tracked on its own -----------------------------------------------------------------
chk = {"placed_file_checked": False}
if os.path.exists(VOKAL_DOGAL):
    t2, m2, _d2, lvl2, v2 = track(VOKAL_DOGAL)
    x2, fs2 = sf.read(VOKAL_DOGAL)
    gain_db = 20 * np.log10(np.sqrt(np.mean(x2[np.abs(x2) > 0] ** 2)) + 1e-12)      # only informative
    k2 = np.round(rows[:, 4] / FP).astype(int)
    ok = (k2 >= 0) & (k2 < len(t2))
    found = ok & v2[np.clip(k2, 0, len(t2) - 1)]
    d = np.abs(m2[np.clip(k2, 0, len(t2) - 1)] - rows[:, 6])
    close = found & (d < 0.5)
    # the other direction: voiced, loud frames of the placed file that are NOT covered by the table (should be few)
    g2 = v2 & (lvl2 > SUNG + 0.87 - GATE_DB)                                          # the placed file has +0.87 dB global gain
    cov = np.zeros(len(t2), bool); cov[np.clip(k2[ok], 0, len(t2) - 1)] = True
    cov = cov | np.roll(cov, 1) | np.roll(cov, -1)
    chk = {"placed_file_checked": True,
           "frames_of_the_table_voiced_in_the_placed_file": r(found.mean()),
           "frames_within_half_a_semitone_of_the_placed_file": r(close.mean()),
           "median_abs_pitch_difference_semitones": r(np.nanmedian(d[found]), 3),
           "gated_frames_of_the_placed_file": int(g2.sum()), "of_which_not_in_the_table": int((g2 & ~cov).sum()),
           "note": "the table is built from the SOURCE stem + the placement shifts of kesim.json; this compares it with an independent "
                   "pitch track of vokal_dogal.wav at the same destination times (frame grids differ by up to 2.5 ms; fades change the gate at the edges)"}
    print("cross-check on vokal_dogal.wav: %.1f %% of the table's frames are voiced there, %.1f %% within 0.5 semitone (median |diff| %.3f st); "
          "gated frames of the placed file not in the table: %d of %d"
          % (100 * found.mean(), 100 * close.mean(), np.nanmedian(d[found]), (g2 & ~cov).sum(), g2.sum()))
    assert close.mean() > 0.95, "the frame table does not match the placed vocal"
else:
    print("vokal_dogal.wav not found: the placement cross-check is skipped")
save_json(os.path.join(ARA, "kareler_dogrulama.json"), {
    "voiced_sung_s": r(len(rows) * FP, 3), "kesim_json_total_s": ref["overall"]["total_seconds"],
    "largest_pitch_class_difference_to_kesim_json_s": r(worst, 3),
    "pitch_class_share_note_mode": {NOTE[i]: r(np.mean(pcn == i)) for i in range(12) if np.mean(pcn == i) > 0},
    "pitch_class_share_frame_mode": {NOTE[i]: r(np.mean(pcf == i)) for i in range(12) if np.mean(pcf == i) > 0},
    "frames_whose_own_pitch_rounds_to_their_note": r(np.mean(pcf == pcn)),
    "placed_vocal_cross_check": chk})
