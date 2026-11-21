#!/usr/bin/env python3
"""Shared definitions for harmony designer A ("sade"): paths, the song form, chords, metric definitions.

Everything is READ from outside this folder (kesim.json, tempo.json, the separated vocal, the backing MIDI);
everything is WRITTEN only inside yeni4/tasarim/A/.
"""
import os, json
import numpy as np

T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # .../yeni4/tasarim/A
A = os.path.dirname(os.path.dirname(os.path.dirname(T)))                 # .../ali-baba
KESIM = os.path.join(A, "yeni4", "analiz", "kesim", "kesim.json")
TEMPO = os.path.join(A, "yeni4", "analiz", "tempo", "tempo.json")
VOKAL = os.path.join(A, "yeni4", "vokal", "kaynak", "v2_2_vokal.wav")
MIDI_C = os.path.join(A, "yeni4", "altyapi", "midi", "altyapi_C.mid")
MIDI_ALT_C = os.path.join(A, "yeni4", "altyapi", "midi", "ezgi_alti_C.mid")
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
# verse bar of every sung line in the new form, and the beats of that bar it is expected to occupy
LINE_BAR = {"L1": 0, "L2": 2, "diye": 5, "L4": 6}
VOCAL_BEATS = {0: [0, 1, 2, 3], 2: [0, 1, 2, 3], 5: [2, 3], 6: [0, 1, 2, 3]}

# ---- chords -----------------------------------------------------------------------------------------------
# degree -> (root offset from the tonic, chord-tone offsets from the tonic)
# "V" = the dominant as a plain triad (the V7 of the task with its seventh left out of the band)
DEGREE = {"I": (0, (0, 4, 7)), "IV": (5, (5, 9, 0)), "V7": (7, (7, 11, 2, 5)), "V": (7, (7, 11, 2))}
MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)


def chord_of_degree(tonic_pc, deg):
    """-> dict(name, root pc, set of chord-tone pcs)"""
    r, tones = DEGREE[deg]
    root = (tonic_pc + r) % 12
    return {"name": NOTE[root] + ("7" if deg == "V7" else ""), "degree": deg, "root": root,
            "tones": frozenset((tonic_pc + t) % 12 for t in tones)}


def named_chord(name):
    """'Dm', 'C', 'Gm', 'A', 'G7' -> dict(name, root, tones)"""
    if name.endswith("m"):
        root = PC[name[:-1]]; tones = (0, 3, 7)
    elif name.endswith("7"):
        root = PC[name[:-1]]; tones = (0, 4, 7, 10)
    else:
        root = PC[name]; tones = (0, 4, 7)
    return {"name": name, "degree": None, "root": root, "tones": frozenset((root + t) % 12 for t in tones)}


def scale_of_major(tonic_pc):
    return frozenset((tonic_pc + s) % 12 for s in MAJOR_SCALE)


D_MINOR_SCALE = frozenset(PC[n] for n in ["D", "E", "F", "G", "A", "A#", "C"])     # D natural minor


def classify_pc(pc, chord, scale):
    """Category of ONE sung pitch class against ONE chord.
    chord tone      : the pitch class is a chord tone
    clash           : not a chord tone AND (a semitone above or below a chord tone OR a tritone from the root)
    outside         : not in the scale of the key (independent of 'clash': both flags can be true)
    Returns (is_chord_tone, is_clash, is_outside_scale)."""
    ct = pc in chord["tones"]
    clash = (not ct) and (any(((pc - t) % 12) in (1, 11) for t in chord["tones"]) or ((pc - chord["root"]) % 12) == 6)
    out = (pc not in scale) and not ct
    return ct, clash, out


def clash_table(chord):
    """bool[12]: clash flag for every pitch class against this chord."""
    return np.array([classify_pc(p, chord, range(12))[1] for p in range(12)])


def load_json(p):
    with open(p, encoding="utf8") as f:
        return json.load(f)


def save_json(p, obj):
    with open(p, "w", encoding="utf8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def r(x, n=4):
    return None if x is None else round(float(x), n)
