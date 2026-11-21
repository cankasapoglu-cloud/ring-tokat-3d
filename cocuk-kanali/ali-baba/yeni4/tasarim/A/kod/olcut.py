#!/usr/bin/env python3
"""The metrics. All shares are duration-weighted over the voiced sung time (5 ms frames of the frame table).

For every frame the chord is the one sounding at the frame's own time in the NEW song form (beat = floor(position));
frames a few ms before a bar line get the chord of the beat they are physically in.

  chord_tone        : the sung pitch class is a chord tone
  scale_non_chord   : in the key's scale, not a chord tone
  outside_scale     : not in the key's scale (and not a chord tone)          [these three sum to 1]
  clash_any         : not a chord tone AND (a semitone above/below a chord tone OR a tritone from the chord root)
  clash_sustained   : the part of clash_any that lies in a clash run LONGER THAN 150 ms.
                      A run = consecutive clash frames; it survives a gap of up to 60 ms without sung pitch (a consonant
                      between two clashing syllables) and up to 15 ms of non-clash frames (tracker jitter); its length
                      is last frame - first frame + 5 ms. 'strict' variant: no bridging at all.
  consonant_non_chord: scale_non_chord without clash (seconds, sixths, ninths that rub nothing by a semitone)
  sounding_semitone : (physical, uses the band model) share of sung time during which a band note a semitone away
                      in pitch class (minor 2nd, major 7th, minor 9th) is really sounding (note-on .. note-off + 30 ms)
  sounding_semitone_sustained: the part of it in runs longer than 150 ms (same run rule)

The sung pitch class of a frame is by default the pitch class of the NOTE it belongs to ('note' mode, the musical
reading: scoops and glides count with their note); 'frame' mode rounds every frame's own pitch (the literal reading).
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
        self.pc_note = np.round(self.note_midi).astype(int) % 12
        self.pc_frame = np.round(self.midi).astype(int) % 12
        self.n = len(self.t)
        self.total_s = self.n * FP

    def pc(self, mode="note"):
        return self.pc_note if mode == "note" else self.pc_frame


def run_mask(flag, t, verse):
    """-> (bool mask of the flagged frames that lie in runs longer than RUN_MIN_S, list of runs (i0, i1, length_s)),
    bridged rule (see module doc). flag, t, verse are aligned arrays sorted by (verse, time)."""
    idx = np.flatnonzero(flag)
    keep = np.zeros(len(flag), bool); runs = []
    if len(idx) == 0:
        return keep, runs
    start = 0
    for k in range(1, len(idx) + 1):
        brk = True
        if k < len(idx):
            i, j = idx[k - 1], idx[k]
            brk = not (verse[i] == verse[j] and (t[j] - t[i]) <= BRIDGE_SILENT_S + FP + 1e-9 and (j - i - 1) <= BRIDGE_NONCLASH_FRAMES)
        if brk:
            a, b = idx[start], idx[k - 1]
            length = t[b] - t[a] + FP
            if length > RUN_MIN_S + 1e-9:
                keep[idx[start:k]] = True
                runs.append((int(a), int(b), float(length)))
            start = k
    return keep, runs


def run_mask_strict(flag, t, verse):
    idx = np.flatnonzero(flag)
    keep = np.zeros(len(flag), bool)
    if len(idx) == 0:
        return keep
    start = 0
    for k in range(1, len(idx) + 1):
        if k == len(idx) or idx[k] != idx[k - 1] + 1 or verse[idx[k]] != verse[idx[k - 1]] or t[idx[k]] - t[idx[k - 1]] > FP + 1e-6:
            if (k - start) * FP > RUN_MIN_S + 1e-9:
                keep[idx[start:k]] = True
            start = k
    return keep


class Plan:
    """A harmony for one verse: 32 chords (one per beat), plus the chord before the verse downbeat and the scale."""

    def __init__(self, chords32, scale, pre_chord, label=""):
        assert len(chords32) == 32
        self.chords = list(chords32); self.scale = frozenset(scale); self.pre = pre_chord; self.label = label
        uniq = {}
        self.ids = np.zeros(33, int)
        for i, c in enumerate([pre_chord] + self.chords):
            key = (c["name"], c["root"], tuple(sorted(c["tones"])))
            if key not in uniq:
                uniq[key] = (len(uniq), c)
            self.ids[i] = uniq[key][0]
        cl = [c for _, c in sorted(uniq.values(), key=lambda q: q[0])]
        self.CT = np.array([[p in c["tones"] for p in range(12)] for c in cl])
        self.CL = np.array([[classify_pc(p, c, self.scale)[1] for p in range(12)] for c in cl])
        self.SC = np.array([p in self.scale for p in range(12)])

    def chord_ids(self, pos):
        b = np.floor(pos + 1e-9).astype(int)
        assert b.min() >= -1 and b.max() <= 31, (b.min(), b.max())
        return self.ids[b + 1]


def evaluate(F, plan, mask=None, mode="note", sounding=None, detail=False, shift_beats=0.0):
    """Metrics of one plan over the frames F[mask]. sounding = (bool[frames, 12], frames_per_bar) from bant.verse_sounding.
    shift_beats: sensitivity test, the chords are evaluated as if they changed that many beats EARLIER."""
    m = np.ones(F.n, bool) if mask is None else mask
    pc = F.pc(mode)[m]; pos = F.pos[m]; t = F.t[m]; verse = F.verse[m]
    cid = plan.chord_ids(np.minimum(pos + shift_beats, 31.999))
    ct = plan.CT[cid, pc]; cl = plan.CL[cid, pc]; insc = plan.SC[pc]
    n = len(pc)
    sus, runs = run_mask(cl, t, verse)
    out = {
        "voiced_s": r(n * FP, 3),
        "chord_tone": r(ct.mean()),
        "scale_non_chord": r((~ct & insc).mean()),
        "outside_scale": r((~ct & ~insc).mean()),
        "clash_any": r(cl.mean()),
        "clash_sustained": r(sus.mean()),
        "clash_sustained_strict": r(run_mask_strict(cl, t, verse).mean()),
        "clash_short": r((cl & ~sus).mean()),
        "consonant_non_chord": r((~ct & insc & ~cl).mean()),
        "sustained_clash_runs": len(runs),
        "sustained_clash_s": r(sus.sum() * FP, 3),
    }
    if sounding is not None:
        S, fpb = sounding
        fi = np.floor((pos + 4.0) * BEAT / FP + 1e-6).astype(int)
        ss = S[fi, (pc + 1) % 12] | S[fi, (pc - 1) % 12]
        ssus, sruns = run_mask(ss, t, verse)
        out["sounding_semitone"] = r(ss.mean())
        out["sounding_semitone_sustained"] = r(ssus.mean())
        out["sounding_semitone_runs"] = len(sruns)
    if detail:
        d = []
        for (a, b, length) in runs:
            d.append({"verse": int(verse[a]) + 1, "bar": int(np.floor(pos[a] / 4 + 1e-9)), "beat_from": r(pos[a] % 4, 2),
                      "beat_to": r((pos[b] % 4) + FP / BEAT, 2), "ms": int(round(length * 1000)),
                      "sung": "/".join(NOTE[p] for p in sorted(set(pc[a:b + 1][cl[a:b + 1]]))),
                      "chord": "/".join(dict.fromkeys(plan_chord_name(plan, pos[k]) for k in range(a, b + 1) if cl[k]))})
        out["runs"] = d
    return out


def plan_chord_name(plan, pos):
    b = int(np.floor(pos + 1e-9))
    return (plan.pre if b < 0 else plan.chords[b])["name"]


def major_plan(key, bars, label=""):
    """bars = {0: [4 degrees], 2: [...], 5: [2 degrees for beats 2-3], 6: [...]}; everything else is the fixed form:
    bars 1 and 7 = I V7 I I, bars 3 and 4 = I, bar 5 beats 0-1 = I; the beat before the verse = I."""
    ton = PC[key]
    deg = [None] * 32
    for b in (1, 7):
        deg[b * 4:b * 4 + 4] = ['I', 'V7', 'I', 'I']
    for b in (3, 4):
        deg[b * 4:b * 4 + 4] = ['I'] * 4
    deg[20:22] = ['I', 'I']
    deg[0:4] = bars[0]; deg[8:12] = bars[2]; deg[22:24] = bars[5]; deg[24:28] = bars[6]
    ch = {d: chord_of_degree(ton, d) for d in DEGREE}
    return Plan([ch[d] for d in deg], scale_of_major(ton), ch['I'], label), deg


def plan8_of(deg32):
    return [deg32[b * 4:b * 4 + 4] for b in range(8)]
