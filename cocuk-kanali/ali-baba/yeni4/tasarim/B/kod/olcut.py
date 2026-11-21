#!/usr/bin/env python3
"""The metrics of designer B. All shares are duration-weighted over the voiced sung time (5 ms frames of the table).

For every frame the chord is the one of the beat the frame is physically in, in the NEW song form
(beat = floor(position)); a frame a few ms before a bar line gets the chord of the beat before that bar line.

TASK METRICS (identical definitions to designer A's olcut.py, re-implemented here and vectorised)
  chord_tone        : the sung pitch class is a chord tone
  scale_non_chord   : in the key's scale, not a chord tone
  outside_scale     : not in the key's scale (and not a chord tone)               [these three sum to 1]
  clash_any         : not a chord tone AND (a semitone above / below a chord tone OR a tritone from the chord root)
  clash_sustained   : the part of clash_any that lies in a clash run LONGER THAN 150 ms. A run = consecutive clash
                      frames; it survives a gap of up to 60 ms without sung pitch (a consonant between two clashing
                      syllables) and up to 15 ms of sung non-clash frames (tracker jitter); length = last - first + 5 ms.
  clash_sustained_strict : the same without any bridging
  consonant_non_chord    : scale_non_chord that is not a clash

EXTRA METRICS OF DESIGNER B (they describe WHERE the chord tones are, which the shares above do not see)
  on_beat_chord_tone : chord-tone share of the syllables that START ON A BEAT (beat slots 0, 1, 2, 3 of the bar;
                       kesim.json beat_expected) = the metrically strong notes
  off_beat_chord_tone: the same for the syllables on the half beats and sixteenths
  line_end_chord_tone: chord-tone share of the LAST syllable of each line (the note a phrase comes to rest on)

The sung pitch class of a frame is by default the pitch class of the NOTE it belongs to ('note' mode: scoops and
glides count with their note); 'frame' mode rounds every frame's own pitch.
"""
import numpy as np
from ortak import *

RUN_MIN_S = 0.150
BRIDGE_SILENT_S = 0.060
BRIDGE_NONCLASH_FRAMES = 3


class Frames:
    def __init__(self, path=KARELER):
        z = np.load(path)
        o = np.lexsort((z["t_src"], z["verse"]))
        self.verse = z["verse"][o]; self.line = z["line"][o]; self.syl = z["syl"][o]
        self.t = z["t_new"][o]; self.t_src = z["t_src"][o]; self.pos = z["pos"][o]
        self.midi = z["midi"][o]; self.note_midi = z["note_midi"][o]; self.midi_dio = z["midi_dio"][o]
        self.slot = z["slot"][o]; self.last = z["last"][o]
        self.on_beat = np.abs(self.slot - np.round(self.slot)) < 1e-6
        self.pc_note = np.round(self.note_midi).astype(int) % 12
        self.pc_frame = np.round(self.midi).astype(int) % 12
        self.notes = z["notes"]
        self.n = len(self.t)
        self.total_s = self.n * FP

    def pc(self, mode="note"):
        return self.pc_note if mode == "note" else self.pc_frame


def run_mask(flag, t, verse, bridged=True):
    """-> (bool mask of the flagged frames inside runs longer than RUN_MIN_S, list of (i0, i1, length_s)).
    flag, t, verse: aligned arrays sorted by (verse, time)."""
    idx = np.flatnonzero(flag)
    keep = np.zeros(len(flag), bool)
    if len(idx) == 0:
        return keep, []
    i, j = idx[:-1], idx[1:]
    if bridged:
        cont = (verse[i] == verse[j]) & ((t[j] - t[i]) <= BRIDGE_SILENT_S + FP + 1e-9) & ((j - i - 1) <= BRIDGE_NONCLASH_FRAMES)
    else:
        cont = (verse[i] == verse[j]) & (j == i + 1) & ((t[j] - t[i]) <= FP + 1e-6)
    starts = np.concatenate(([0], np.flatnonzero(~cont) + 1))
    ends = np.concatenate((np.flatnonzero(~cont), [len(idx) - 1]))
    length = t[idx[ends]] - t[idx[starts]] + FP
    if not bridged:
        length = (ends - starts + 1) * FP
    runs = []
    for s, e, L in zip(starts, ends, length):
        if L > RUN_MIN_S + 1e-9:
            keep[idx[s:e + 1]] = True
            runs.append((int(idx[s]), int(idx[e]), float(L)))
    return keep, runs


class Plan:
    """A harmony for one verse: 32 chords (one per beat) + the chord of the beat before the verse downbeat + the scale."""

    def __init__(self, chords32, scale, pre_chord, label=""):
        assert len(chords32) == 32
        self.chords = list(chords32); self.scale = frozenset(scale); self.pre = pre_chord; self.label = label
        allc = [pre_chord] + self.chords
        self.CT = np.array([[p in c["tones"] for p in range(12)] for c in allc])                       # [33, 12]
        self.CL = np.array([[classify_pc(p, c, self.scale)[1] for p in range(12)] for c in allc])
        self.SC = np.array([p in self.scale for p in range(12)])

    def beat_index(self, pos):
        b = np.floor(pos + 1e-9).astype(int)
        assert b.min() >= -1 and b.max() <= 31, (b.min(), b.max())
        return b + 1

    def name_at(self, pos):
        b = int(np.floor(pos + 1e-9))
        return (self.pre if b < 0 else self.chords[b])["name"]


def evaluate(F, plan, mask=None, mode="note", detail=False, shift_beats=0.0):
    """Metrics of one plan over the frames F[mask].
    shift_beats: sensitivity test, the chords are evaluated as if they changed that many beats EARLIER."""
    m = np.ones(F.n, bool) if mask is None else mask
    pc = F.pc(mode)[m]; pos = F.pos[m]; t = F.t[m]; verse = F.verse[m]
    bi = plan.beat_index(np.minimum(pos + shift_beats, 31.999))
    ct = plan.CT[bi, pc]; cl = plan.CL[bi, pc]; insc = plan.SC[pc]
    n = len(pc)
    sus, runs = run_mask(cl, t, verse)
    strict, _ = run_mask(cl, t, verse, bridged=False)
    ob = F.on_beat[m]; la = F.last[m]
    out = {
        "voiced_s": r(n * FP, 3),
        "chord_tone": r(ct.mean()),
        "scale_non_chord": r((~ct & insc).mean()),
        "outside_scale": r((~ct & ~insc).mean()),
        "clash_any": r(cl.mean()),
        "clash_sustained": r(sus.mean()),
        "clash_sustained_strict": r(strict.mean()),
        "clash_short": r((cl & ~sus).mean()),
        "consonant_non_chord": r((~ct & insc & ~cl).mean()),
        "sustained_clash_runs": len(runs),
        "sustained_clash_s": r(sus.sum() * FP, 3),
        "on_beat_chord_tone": r(ct[ob].mean()) if ob.any() else None,
        "off_beat_chord_tone": r(ct[~ob].mean()) if (~ob).any() else None,
        "line_end_chord_tone": r(ct[la].mean()) if la.any() else None,
    }
    if detail:
        d = []
        for (a, b, length) in runs:
            d.append({"verse": int(verse[a]) + 1, "bar": int(np.floor(pos[a] / 4 + 1e-9)), "beat_from": r(pos[a] % 4, 2),
                      "beat_to": r((pos[b] % 4) + FP / BEAT, 2), "ms": int(round(length * 1000)),
                      "sung": "/".join(NOTE[p] for p in sorted(set(pc[a:b + 1][cl[a:b + 1]]))),
                      "chord": "/".join(dict.fromkeys(plan.name_at(pos[k]) for k in range(a, b + 1) if cl[k]))})
        out["runs"] = d
    return out


def J(e, w=2.0):
    """Fit score used for ranking (same as designer A): chord tones minus w times the 'wrong note' shares."""
    return e["chord_tone"] - w * (e["clash_sustained"] + e["outside_scale"])


def major_plan(key, bars, label=""):
    """bars = {0: [4 degrees], 2: [...], 5: [2 degrees for beats 2-3], 6: [...]}; everything else is the fixed form:
    bars 1 and 7 = I V7 I I (the loud answers), bars 3 and 4 = I (animal calls), bar 5 beats 0-1 = I (drum fill);
    the beat before the verse = I (end of the previous answer).  -> (Plan, list of 32 degrees)"""
    ton = PC[key]
    deg = [None] * 32
    for b in (1, 7):
        deg[b * 4:b * 4 + 4] = ["I", "V7", "I", "I"]
    for b in (3, 4):
        deg[b * 4:b * 4 + 4] = ["I"] * 4
    deg[20:22] = ["I", "I"]
    deg[0:4] = bars[0]; deg[8:12] = bars[2]; deg[22:24] = bars[5]; deg[24:28] = bars[6]
    ch = {d: chord_of_degree(ton, d) for d in DEGREE}
    return Plan([ch[d] for d in deg], scale_of_major(ton), ch["I"], label), deg


def original_plan():
    """The ORIGINAL band of v2_2: 2-bar loop Dm C | Gm A (two beats per chord), mapped onto the new bars by the sung line:
    L1 over Dm Dm C C, L2 and L4 over Gm Gm A A, 'diye bagirir' (beats 2-3 of the third source bar) over C C."""
    Dm, Cc, Gm, Aa = named_chord("Dm"), named_chord("C"), named_chord("Gm"), named_chord("A")
    o = [None] * 32
    o[0:4] = [Dm, Dm, Cc, Cc]; o[4:8] = [Cc] * 4          # beat 7 = what precedes L2 in the original (C)
    o[8:12] = [Gm, Gm, Aa, Aa]; o[12:20] = [Dm] * 8
    o[20:24] = [Dm, Dm, Cc, Cc]; o[24:28] = [Gm, Gm, Aa, Aa]; o[28:32] = [Dm] * 4
    return Plan(o, D_MINOR_SCALE | {PC["C#"]}, Aa, "original D minor loop")


PLAIN = {0: ["I", "I", "IV", "I"], 2: ["I", "I", "IV", "I"], 5: ["I", "I"], 6: ["I", "I", "IV", "I"]}
