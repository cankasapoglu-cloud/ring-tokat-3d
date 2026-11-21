#!/usr/bin/env python3
"""Model of what the band really plays (pitched notes only) in one bar, as a function of the chord on each beat.

It mirrors groove() and the 'slot' / 'fillin' branches of yeni4/altyapi/kod/build.py (the oom-pah pattern):
    bass      : root (or fifth) on the beat, root an octave up on the off-beat
    banjo     : single roll notes on the beat and the off-beat, the top chord note on the 16ths in between,
                the full chord ON beats 1 and 3
    piano     : root octaves ON beats 0 and 2 ("oom"), the full chord on every OFF-beat ("pah")
    accordion : the full chord ON beats 1 and 3 and on every off-beat
    brass     : off-beat chord stab on beat 3 of the "diye bagirir" half bar
So the THIRD (and the seventh) of a chord sounds on the off-beats and on beats 1 and 3, but NOT on beats 0 and 2.
02_bant_dogrula.py checks this model note for note against the MIDI file the builder wrote (midi/altyapi_C.mid).
"""
import numpy as np
from ortak import NOTE, PC, BEAT, FP

BASS, BANJO, ACC, PNO, BRS = 0, 1, 2, 3, 6
# 'V' is NOT in build.py: it is the V7 voicing without its seventh (written in G: F#3 A3 D4; the banjo roll of V7 has
# its seventh only on beat 1, so on beats 0, 2 and 3 the roll of V7 can be used unchanged).
_CH = {'I': [55, 59, 62], 'IV': [55, 60, 64], 'V7': [54, 57, 60, 62], 'V': [54, 57, 62]}
_ROLL = {'I': [62, 67, 59, 67, 62, 67, 59, 67], 'IV': [64, 67, 60, 67, 64, 67, 60, 67], 'V7': [62, 66, 60, 66, 62, 66, 57, 66],
         'V': [62, 66, 57, 66, 62, 66, 57, 66]}
_DEG = {'I': 0, 'IV': 5, 'V7': 7, 'V': 7}


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

    def groove(self, ch, beats=range(4), stab=False, fifth_on_beat2=True):
        """-> list of (beat in bar, duration in beats, channel, midi note, velocity); ch = chord degree on each of the 4 beats.
        fifth_on_beat2=False: the bass stays on the root on beat 2 (build.py plays the fifth there when beats 0-2 share a chord)."""
        ev = []
        for bt in beats:
            c = ch[bt]
            low = self.FIFTH[c] if (fifth_on_beat2 and bt == 2 and c == ch[0] == ch[1]) else self.ROOT[c]
            ev += [(bt, .45, BASS, low, 116), (bt + .5, .38, BASS, self.ROOT[c] + 12, 104)]
            for e in range(2):
                ev.append((bt + e * .5, .45, BANJO, self.ROLL[c][bt * 2 + e], 100 if e == 0 else 90))
            ev += [(bt + .25, .2, BANJO, self.CH[c][-1], 70), (bt + .75, .2, BANJO, self.CH[c][-1], 70)]
            for n in self.CH[c]:
                ev.append((bt + .5, .28, PNO, n + 12, 100))
                if bt in (1, 3):
                    ev += [(bt, .45, ACC, n + 12, 92), (bt, .3, BANJO, n, 82)]
                ev.append((bt + .5, .25, ACC, n + 12, 74))
            if bt in (0, 2):
                ev += [(bt, .4, PNO, self.ROOT[c] + 12, 92), (bt, .4, PNO, self.ROOT[c] + 24, 84)]
            if stab and bt in (1, 3):
                for n in self.CH[c][-3:]:
                    ev.append((bt + .5, .22, BRS, n + 12, 96))
        return ev

    def bar(self, kind, ch):
        """kind: 'voc' (bars 0, 2, 6, and the answers 1, 7 without the lead), 'voc_root' (the same with the bass on the
        root on beat 2), 'slot' (bars 3, 4), 'fillin' (bar 5)."""
        if kind == 'voc':
            return self.groove(ch)
        if kind == 'voc_root':
            return self.groove(ch, fifth_on_beat2=False)
        if kind == 'slot':
            return [(0, .9, BASS, self.ROOT['I'], 80), (2, .9, BASS, self.FIFTH['I'], 74)]
        if kind == 'fillin':
            return ([(0, .9, BASS, self.ROOT['I'], 104), (1, .45, BASS, self.FIFTH['I'], 108), (1.5, .45, BASS, self.FIFTH['I'], 112)]
                    + self.groove(ch, beats=(2, 3), stab=True))
        raise ValueError(kind)

    def sounding(self, kind, ch, release_s=0.03):
        """bool[n_frames of one bar, 12]: pitch class p sounds in frame i (note-on .. note-off + release).
        Frame i covers bar time i * FP .. (i + 1) * FP; the matrix is one bar + one beat long (ring-over)."""
        key = (kind, tuple(ch), release_s)
        if key not in self._cache:
            n = int(round(5 * BEAT / FP))
            m = np.zeros((n, 12), bool)
            for (bt, dur, _, note, _v) in self.bar(kind, ch):
                a = int(np.floor(bt * BEAT / FP + 1e-6)); b = int(np.ceil((bt + dur) * BEAT / FP + release_s / FP - 1e-6))
                m[a:min(b, n), note % 12] = True
            self._cache[key] = m
        return self._cache[key]


def verse_sounding(band, plan8, release_s=0.03):
    """plan8 = chord degrees per beat for the 8 bars of a verse (list of 8 lists of 4).
    -> bool[frames, 12] for the stretch from one bar BEFORE the verse (the answer bar, I V7 I I) to its end."""
    kinds = ['voc', 'voc', 'voc', 'slot', 'slot', 'fillin', 'voc', 'voc']
    nb = int(round(BEAT * 4 / FP * 1000)) / 1000.0            # frames per bar (not an integer: 457.14)
    fpb = 4 * BEAT / FP
    total = int(np.ceil(10 * fpb)) + 2
    out = np.zeros((total, 12), bool)
    seq = [('voc', ['I', 'V7', 'I', 'I'])] + list(zip(kinds, plan8))
    for i, (kind, ch) in enumerate(seq):
        m = band.sounding(kind, ch, release_s)
        a = int(round(i * fpb))
        out[a:a + len(m)] |= m[:max(0, min(len(m), total - a))]
    return out, fpb                                             # frame index of verse position pos (beats): (pos + 4) * BEAT / FP


def note_name(m):
    return "%s%d" % (NOTE[m % 12], m // 12 - 1)
