#!/usr/bin/env python3
"""Model of what the band really plays (pitched notes only) in one bar, as a function of the chord on each beat.
Adapted from yeni4/tasarim/A/kod/bant.py (which mirrors groove() and the 'slot' / 'fillin' branches of
yeni4/altyapi/kod/build.py) and EXTENDED to the chord vocabulary of designer B: ii, iii, vi and the plain V triad.

The oom-pah pattern of build.py:
    bass      : root (or fifth) on the beat, root an octave up on the off-beat
    banjo     : single roll notes on the beat and the off-beat, the top chord note on the 16ths in between,
                the full chord ON beats 1 and 3
    piano     : root octaves ON beats 0 and 2 ("oom"), the full chord on every OFF-beat ("pah")
    accordion : the full chord ON beats 1 and 3 and on every off-beat
    brass     : off-beat chord stab on beats 2-3 of the "diye bagirir" half bar
So the third (and seventh) of a chord sounds on the off-beats and on beats 1 and 3, NOT on beats 0 and 2.

VOICINGS. I, IV, V7 are build.py's (written in G, moved by AS). The new ones are PROPOSED by designer B in the same
convention (close position in the same register, same roll shape as I: fifth - root - third - root):
    ii  (written Am): chord A3 C4 E4,  roll E4 A4 C4 A4      -> in C: D3 F3 A3,  roll A3 D4 F3 D4
    iii (written Bm): chord F#3 B3 D4, roll D4 F#4 B3 F#4    -> in C: B2 E3 G3,  roll G3 B3 E3 B3
    vi  (written Em): chord G3 B3 E4,  roll E4 G4 B3 G4      -> in C: C3 E3 A3,  roll A3 C4 E3 C4
    V   (written D ): chord F#3 A3 D4, roll D4 F#4 A3 F#4    -> in C: B2 D3 G3,  roll G3 B3 D3 B3   (V7 without its seventh;
                                                               the same voicing designer A uses)
02_bant_dogrula.py checks the I / IV / V7 part of this model note for note against midi/altyapi_C.mid.
"""
import numpy as np
from ortak import NOTE, PC, BEAT, FP

BASS, BANJO, ACC, PNO, BRS = 0, 1, 2, 3, 6
_CH = {"I": [55, 59, 62], "IV": [55, 60, 64], "V7": [54, 57, 60, 62], "V": [54, 57, 62],
       "ii": [57, 60, 64], "iii": [54, 59, 62], "vi": [55, 59, 64]}
_ROLL = {"I": [62, 67, 59, 67, 62, 67, 59, 67], "IV": [64, 67, 60, 67, 64, 67, 60, 67],
         "V7": [62, 66, 60, 66, 62, 66, 57, 66], "V": [62, 66, 57, 66, 62, 66, 57, 66],
         "ii": [64, 69, 60, 69, 64, 69, 60, 69], "iii": [62, 66, 59, 66, 62, 66, 59, 66],
         "vi": [64, 67, 59, 67, 64, 67, 59, 67]}
_DEG = {"I": 0, "ii": 2, "iii": 4, "IV": 5, "V7": 7, "V": 7, "vi": 9}


def note_name(m):
    return "%s%d" % (NOTE[m % 12], m // 12 - 1)


class Band:
    def __init__(self, key):
        self.key = key
        ton = PC[key]
        d = (ton - 7) % 12
        self.AS = d if d <= 3 else d - 12                       # build.py: the arrangement is written in G and moved
        self.CH = {k: [n + self.AS for n in v] for k, v in _CH.items()}
        self.ROLL = {k: [n + self.AS for n in v] for k, v in _ROLL.items()}
        self.ROOT = {k: 36 + (ton + v) % 12 for k, v in _DEG.items()}
        self.FIFTH = {k: 36 + (ton + v + 7) % 12 for k, v in _DEG.items()}
        self._cache = {}

    def groove(self, ch, beats=range(4), stab=False, fifth_on_beat2=True, open_on_beat=()):
        """-> list of (beat in bar, duration in beats, channel, midi note, velocity); ch = chord degree per beat.
        open_on_beat: beats on which the ON-BEAT strum leaves out the THIRD of the chord (optional refinement of
        designer B: accordion + banjo chord strike root and fifth only, the banjo roll note on that beat becomes the
        fifth; the off-beat strum half a beat later is the full chord again)."""
        ev = []
        for bt in beats:
            c = ch[bt]
            third = (self.ROOT[c] + (3 if c in ("ii", "iii", "vi") else 4)) % 12
            low = self.FIFTH[c] if (fifth_on_beat2 and bt == 2 and c == ch[0] == ch[1]) else self.ROOT[c]
            ev += [(bt, .45, BASS, low, 116), (bt + .5, .38, BASS, self.ROOT[c] + 12, 104)]
            for e in range(2):
                n = self.ROLL[c][bt * 2 + e]
                if e == 0 and bt in open_on_beat and n % 12 == third:
                    n = self.CH[c][-1] if self.CH[c][-1] % 12 != third else self.CH[c][0]
                ev.append((bt + e * .5, .45, BANJO, n, 100 if e == 0 else 90))
            ev += [(bt + .25, .2, BANJO, self.CH[c][-1], 70), (bt + .75, .2, BANJO, self.CH[c][-1], 70)]
            for n in self.CH[c]:
                ev.append((bt + .5, .28, PNO, n + 12, 100))
                if bt in (1, 3) and not (bt in open_on_beat and n % 12 == third):
                    ev += [(bt, .45, ACC, n + 12, 92), (bt, .3, BANJO, n, 82)]
                ev.append((bt + .5, .25, ACC, n + 12, 74))
            if bt in (0, 2):
                ev += [(bt, .4, PNO, self.ROOT[c] + 12, 92), (bt, .4, PNO, self.ROOT[c] + 24, 84)]
            if stab and bt in (1, 3):
                for n in self.CH[c][-3:]:
                    ev.append((bt + .5, .22, BRS, n + 12, 96))
        return ev

    def bar(self, kind, ch, root_bass=False, open3=False):
        """kind: 'voc' (bars 0, 2, 6 and the accompaniment of the answers 1, 7), 'slot' (bars 3, 4), 'fillin' (bar 5:
        beats 0-1 bass only, beats 2-3 groove + brass stab). root_bass: the bass stays on the root on beat 2.
        open3: the on-beat strum of beat 3 leaves out the third (see groove)."""
        op = (3,) if open3 else ()
        if kind == "voc":
            return self.groove(ch, fifth_on_beat2=not root_bass, open_on_beat=op)
        if kind == "slot":
            return [(0, .9, BASS, self.ROOT["I"], 80), (2, .9, BASS, self.FIFTH["I"], 74)]
        if kind == "fillin":
            return ([(0, .9, BASS, self.ROOT["I"], 104), (1, .45, BASS, self.FIFTH["I"], 108), (1.5, .45, BASS, self.FIFTH["I"], 112)]
                    + self.groove(ch, beats=(2, 3), stab=True, open_on_beat=op))
        raise ValueError(kind)

    def sounding(self, kind, ch, release_s=0.03, exact=False, root_bass=False, open3=False):
        """bool[n_frames of one bar + one beat, 12 or 128]: pitch class (exact=False) or MIDI note (exact=True) sounds in
        frame i (note-on .. note-off + release). Frame i covers bar time i * FP .. (i + 1) * FP."""
        key = (kind, tuple(ch), release_s, exact, root_bass, open3)
        if key not in self._cache:
            n = int(round(5 * BEAT / FP))
            m = np.zeros((n, 128 if exact else 12), bool)
            for (bt, dur, _c, note, _v) in self.bar(kind, ch, root_bass, open3):
                a = int(np.floor(bt * BEAT / FP + 1e-6)); b = int(np.ceil((bt + dur) * BEAT / FP + release_s / FP - 1e-6))
                m[a:min(b, n), note if exact else note % 12] = True
            self._cache[key] = m
        return self._cache[key]


KINDS = ["voc", "voc", "voc", "slot", "slot", "fillin", "voc", "voc"]
ANSWER = ["I", "V7", "I", "I"]


def plan8(bars):
    """bars = {0: [4], 2: [4], 5: [2 degrees for beats 2-3], 6: [4]} -> 8 lists of 4 degrees (the whole verse)."""
    return [list(bars[0]), ANSWER, list(bars[2]), ["I"] * 4, ["I"] * 4, ["I", "I"] + list(bars[5]), list(bars[6]), ANSWER]


def verse_sounding(band, bars, release_s=0.03, exact=False, root_bass_bars=(), open3_bars=()):
    """-> (bool[frames, 12 or 128], frames per bar) for the stretch from one bar BEFORE the verse (the answer bar) to its
    end. Frame index of verse position pos (beats): floor((pos + 4) * BEAT / FP).
    root_bass_bars / open3_bars: verse bars that use the two optional voicing refinements (see Band.bar)."""
    fpb = 4 * BEAT / FP
    total = int(np.ceil(10 * fpb)) + 2
    out = np.zeros((total, 128 if exact else 12), bool)
    seq = [("voc", ANSWER, False, False)] + [(k, ch, i in root_bass_bars, i in open3_bars) for i, (k, ch) in enumerate(zip(KINDS, plan8(bars)))]
    for i, (kind, ch, rb, o3) in enumerate(seq):
        m = band.sounding(kind, ch, release_s, exact, rb, o3)
        a = int(round(i * fpb))
        k = max(0, min(len(m), total - a))
        out[a:a + k] |= m[:k]
    return out, fpb


def sounding_semitone(F, snd, mask=None, mode="note"):
    """Share of the sung time during which a band note one semitone away in PITCH CLASS (minor 2nd, major 7th, minor
    9th) is really sounding, and the part of it in runs longer than 150 ms.  snd = verse_sounding(...)[0] (12 columns)."""
    from olcut import run_mask
    m = np.ones(F.n, bool) if mask is None else mask
    pc = F.pc(mode)[m]; pos = F.pos[m]
    fi = np.floor((pos + 4.0) * BEAT / FP + 1e-6).astype(int)
    ss = snd[fi, (pc + 1) % 12] | snd[fi, (pc - 1) % 12]
    sus, runs = run_mask(ss, F.t[m], F.verse[m])
    return {"sounding_semitone": round(float(ss.mean()), 4), "sounding_semitone_sustained": round(float(sus.mean()), 4),
            "sounding_semitone_runs": len(runs)}


def sounding_same_octave(F, snd128, mask=None, mode="note"):
    """Stricter, register-aware variant: a band note exactly ONE SEMITONE above or below the sung NOTE (same octave)."""
    from olcut import run_mask
    m = np.ones(F.n, bool) if mask is None else mask
    nt = np.round(F.note_midi if mode == "note" else F.midi).astype(int)[m]; pos = F.pos[m]
    fi = np.floor((pos + 4.0) * BEAT / FP + 1e-6).astype(int)
    ss = snd128[fi, nt + 1] | snd128[fi, nt - 1]
    sus, runs = run_mask(ss, F.t[m], F.verse[m])
    return {"semitone_same_octave": round(float(ss.mean()), 4), "semitone_same_octave_sustained": round(float(sus.mean()), 4),
            "semitone_same_octave_runs": len(runs)}


def sounding_relations(F, s12, s128, mask=None, mode="note"):
    """Exact relations between the sung note and the band notes that sound at the same time (band model, no filter
    leakage). Shares of the sung time:
      band_same_pitch_class    : a band note of the SAME pitch class sounds (any octave) = the voice is doubled
      band_unison              : a band note of exactly the sung pitch sounds
      whole_tone_same_octave   : a band note exactly two semitones above or below the sung note sounds (major second)
      whole_tone_..._sustained : the part of it in runs longer than 150 ms"""
    from olcut import run_mask
    m = np.ones(F.n, bool) if mask is None else mask
    pc = F.pc(mode)[m]; nt = np.round(F.note_midi if mode == "note" else F.midi).astype(int)[m]; pos = F.pos[m]
    fi = np.floor((pos + 4.0) * BEAT / FP + 1e-6).astype(int)
    same = s12[fi, pc]; uni = s128[fi, nt]
    whole = s128[fi, nt + 2] | s128[fi, nt - 2]
    sus, runs = run_mask(whole, F.t[m], F.verse[m])
    return {"band_same_pitch_class": round(float(same.mean()), 4), "band_unison": round(float(uni.mean()), 4),
            "whole_tone_same_octave": round(float(whole.mean()), 4), "whole_tone_same_octave_sustained": round(float(sus.mean()), 4)}
