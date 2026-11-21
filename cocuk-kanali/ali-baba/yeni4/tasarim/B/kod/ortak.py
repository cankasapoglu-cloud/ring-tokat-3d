#!/usr/bin/env python3
"""Shared definitions of harmony designer B ("serbest"): paths, the song form, the chord vocabulary, the categories.

Everything is READ from outside this folder (kesim.json, tempo.json, the separated vocal, the placed vocal, the
backing MIDI); everything is WRITTEN only inside yeni4/tasarim/B/.

Chord vocabulary of designer B: every diatonic triad of the major key except the diminished one, plus the dominant
seventh:  I  ii  iii  IV  V  V7  vi.   Keys: C, F, G.
The category definitions are the ones of the task (and identical to designer A's, so the numbers can be compared).
"""
import os, json
import numpy as np

T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # .../yeni4/tasarim/B
A = os.path.dirname(os.path.dirname(os.path.dirname(T)))                 # .../ali-baba
KESIM = os.path.join(A, "yeni4", "analiz", "kesim", "kesim.json")
TEMPO = os.path.join(A, "yeni4", "analiz", "tempo", "tempo.json")
VOKAL = os.path.join(A, "yeni4", "vokal", "kaynak", "v2_2_vokal.wav")     # separated stem, source timeline
VOKAL_DOGAL = os.path.join(A, "yeni4", "vokal", "vokal_dogal.wav")        # the stem placed on the new form (cross-check only)
MIDI_C = os.path.join(A, "yeni4", "altyapi", "midi", "altyapi_C.mid")
MIDI_ALT_C = os.path.join(A, "yeni4", "altyapi", "midi", "ezgi_alti_C.mid")
A_OLCUM = os.path.join(A, "yeni4", "tasarim", "A", "olcum.json")          # designer A's numbers (cross-check only)
ARA = os.path.join(T, "ara")
KARELER = os.path.join(ARA, "kareler.npz")
os.makedirs(ARA, exist_ok=True)

# ---- the song form (fixed) ------------------------------------------------------------------------------
BPM = 105.0
BEAT = 60.0 / BPM            # 0.571429 s
BAR = 4 * BEAT               # 2.285714 s
LEAD_IN = 0.100              # every file: downbeat of bar n at LEAD_IN + n * BAR
INTRO_BARS = 4
VERSE_BARS = 8
N_VERSES = 7
FP = 0.005                   # pitch frame period (s)

NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PC = {n: i for i, n in enumerate(NOTE)}
LINES = ["L1", "L2", "diye", "L4"]
LINE_BAR = {"L1": 0, "L2": 2, "diye": 5, "L4": 6}       # verse bar of every sung line in the new form
BAR_LINE = {0: "L1", 2: "L2", 5: "diye", 6: "L4"}
ANIMALS = ["inek", "koyun", "at", "horoz", "ördek", "köpek", "kedi"]

# ---- chords -----------------------------------------------------------------------------------------------
# degree -> (root offset from the tonic, chord-tone offsets from the ROOT, suffix of the chord name, function)
DEGREE = {
    "I":   (0, (0, 4, 7), "", "T"),
    "ii":  (2, (0, 3, 7), "m", "S"),
    "iii": (4, (0, 3, 7), "m", "T"),
    "IV":  (5, (0, 4, 7), "", "S"),
    "V":   (7, (0, 4, 7), "", "D"),
    "V7":  (7, (0, 4, 7, 10), "7", "D"),
    "vi":  (9, (0, 3, 7), "m", "T"),
}
DEGS = list(DEGREE)
PRIMARY = ("I", "IV", "V", "V7")
MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)


def chord_of_degree(tonic_pc, deg):
    r, tones, suf, fn = DEGREE[deg]
    root = (tonic_pc + r) % 12
    return {"name": NOTE[root] + suf, "degree": deg, "root": root, "function": fn,
            "tones": frozenset((root + t) % 12 for t in tones)}


def named_chord(name):
    """'Dm', 'C', 'Gm', 'A', 'G7' -> dict(name, root, tones)"""
    if name.endswith("m"):
        root = PC[name[:-1]]; tones = (0, 3, 7)
    elif name.endswith("7"):
        root = PC[name[:-1]]; tones = (0, 4, 7, 10)
    else:
        root = PC[name]; tones = (0, 4, 7)
    return {"name": name, "degree": None, "root": root, "function": None, "tones": frozenset((root + t) % 12 for t in tones)}


def scale_of_major(tonic_pc):
    return frozenset((tonic_pc + s) % 12 for s in MAJOR_SCALE)


D_MINOR_SCALE = frozenset(PC[n] for n in ["D", "E", "F", "G", "A", "A#", "C"])     # D natural minor


def classify_pc(pc, chord, scale):
    """Category of ONE sung pitch class against ONE chord (the task's definitions).
    chord tone : the pitch class is a chord tone
    clash      : not a chord tone AND (a semitone above or below a chord tone OR a tritone from the chord ROOT)
    outside    : not in the scale of the key and not a chord tone
    -> (is_chord_tone, is_clash, is_outside_scale)"""
    ct = pc in chord["tones"]
    clash = (not ct) and (any(((pc - t) % 12) in (1, 11) for t in chord["tones"]) or ((pc - chord["root"]) % 12) == 6)
    out = (pc not in scale) and not ct
    return ct, clash, out


def load_json(p):
    with open(p, encoding="utf8") as f:
        return json.load(f)


def save_json(p, obj):
    with open(p, "w", encoding="utf8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def r(x, n=4):
    return None if x is None else round(float(x), n)


def pct(x, n=1):
    return None if x is None else round(100.0 * float(x), n)
