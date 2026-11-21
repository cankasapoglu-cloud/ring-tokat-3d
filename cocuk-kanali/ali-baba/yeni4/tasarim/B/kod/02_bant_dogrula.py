#!/usr/bin/env python3
"""Step 2: check the band model (bant.py) against the MIDI file written by the backing builder (key C, plain harmony),
adapted from yeni4/tasarim/A/kod/02_bant_dogrula.py.

For verses 1, 4 and 7 every note-on of the pitched accompaniment channels (bass, banjo, accordion, piano, brass stab)
in the MIDI must be produced by the model and vice versa (the loud lead of the answer bars is not part of the model;
brass is therefore compared only in bar 5). This verifies the I / IV / V7 part; the ii / iii / vi / V voicings are
PROPOSALS of designer B and are only printed here (what would sound on each beat).
"""
import sys, os, collections
import mido
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
from bant import Band, BASS, BANJO, ACC, PNO, BRS, note_name

mid = mido.MidiFile(MIDI_C)
tpb = mid.ticks_per_beat
ons = collections.Counter()
t = 0
for msg in mid.tracks[0]:
    t += msg.time
    if msg.type == "note_on" and msg.velocity > 0:
        ons[(round(t / tpb, 4), msg.channel, msg.note, msg.velocity)] += 1

band = Band("C")
PA = ["I", "I", "IV", "I"]; AN = ["I", "V7", "I", "I"]; II = ["I"] * 4
plan = [("voc", PA), ("voc", AN), ("voc", PA), ("slot", II), ("slot", II), ("fillin", II), ("voc", PA), ("voc", AN)]
bad = 0; n_model = 0
for v in (0, 3, 6):
    for b, (kind, ch) in enumerate(plan):
        bar = INTRO_BARS + VERSE_BARS * v + b
        chans = (BASS, BANJO, ACC, PNO) + ((BRS,) if b == 5 else ())
        model = collections.Counter((round(bar * 4 + bt, 4), c, n, vel) for (bt, dur, c, n, vel) in band.bar(kind, ch) if c in chans)
        real = collections.Counter({k: c for k, c in ons.items() if bar * 4 <= k[0] < bar * 4 + 4 and k[1] in chans})
        n_model += sum(model.values())
        if model != real:
            bad += 1
            print("MISMATCH verse %d bar %d: only in model %s | only in MIDI %s" % (v + 1, b, list((model - real).items())[:6], list((real - model).items())[:6]))
print("band model vs midi/altyapi_C.mid: %d note-ons (time, channel, pitch, velocity) compared in 3 verses x 8 bars, %d bars differ" % (n_model, bad))
assert bad == 0

out = {"model_vs_builder_midi": {"note_ons_compared": n_model, "bars_that_differ": bad}, "what_sounds_key_C": {}}
for ch in (["ii", "ii", "I", "I"], ["V", "V", "V", "V"], ["V", "V", "V", "V7"], ["I", "IV", "I", "I"], ["vi", "vi", "iii", "iii"]):
    print("chords", ch)
    ev = band.groove(ch)
    rows = {}
    for q in (0, .25, .5, .75, 1, 1.5, 2, 2.25, 2.5, 3, 3.5):
        names = sorted({note_name(n) for (bt, dur, c, n, vel) in ev if abs(bt - q) < 1e-9}, key=lambda s: (int(s[-1]), PC[s[:-1]]))
        rows[str(q)] = " ".join(names)
        print("   beat %-4s: %s" % (q, " ".join(names)))
    out["what_sounds_key_C"][" ".join(ch)] = rows
save_json(os.path.join(ARA, "bant_dogrulama.json"), out)
