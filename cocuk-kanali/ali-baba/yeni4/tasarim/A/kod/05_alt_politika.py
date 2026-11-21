#!/usr/bin/env python3
"""Step 5: the UNDER-VOCAL POLICY of the "dogal" version, in numbers. Writes alt_politika.json.

Three things could sound under the unprocessed vocal besides chords, bass and drums:
  (a) the Old MacDonald tune, soft (the existing ezgi_alti stem: clarinet + glockenspiel, phrase A in bars 0, 2, 6 and a
      repeated do under "diye bagirir"). Measured: which interval the sung note forms with the tune note sounding at the
      same time, and how the tune itself fits the chords that support the voice.
  (b) a soft sustained pad of chord tones (full chord with / without the seventh, or root + fifth only). Measured: share of
      the sung time one semitone away from a pad tone.
  (c) nothing ("none"): only what the oom-pah band strikes (the band model of bant.py).
The tune model is checked note for note against midi/ezgi_alti_C.mid.
"""
import sys, os, collections
import mido
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
from olcut import *
from bant import Band, verse_sounding

KEY = "C"
CHOSEN = {0: ['I', 'IV', 'I', 'I'], 2: ['V'] * 4, 5: ['I', 'I'], 6: ['V'] * 4}
CHOSEN_V7 = {b: ['V7' if c == 'V' else c for c in ch] for b, ch in CHOSEN.items()}
PLAIN = {0: ['I', 'I', 'IV', 'I'], 2: ['I', 'I', 'IV', 'I'], 5: ['I', 'I'], 6: ['I', 'I', 'IV', 'I']}
F = Frames()
band = Band(KEY)

# ---- (a) the soft tune of the existing builder (build.py: ALT_PHA, ALT_DOREP, ALT_DO) ---------------------------------
ALT_DO = 69 + (PC[KEY] - 9) % 12                                   # C -> C5 (72)
PHA = [(0, 0, .42), (0, .5, .42), (0, 1, .42), (-5, 1.5, .42), (-3, 2, .42), (-3, 2.5, .42), (-5, 3, .9)]
ALT_PHA = [(iv, bt, .46 if dur < .5 else .95) for (iv, bt, dur) in PHA]
ALT_DOREP = [(0, 2 + i * .5, .44) for i in range(4)]
tune = []                                                           # (verse beat, duration, midi) of the clarinet line
for b in (0, 2, 6):
    tune += [(b * 4 + bt, dur, ALT_DO + iv) for (iv, bt, dur) in ALT_PHA]
tune += [(5 * 4 + bt, dur, ALT_DO + iv) for (iv, bt, dur) in ALT_DOREP]

# check against the MIDI of the builder (clarinet = channel 7), verse 1 = bars 4..11
mid = mido.MidiFile(MIDI_ALT_C); t = 0; real = collections.Counter()
for msg in mid.tracks[0]:
    t += msg.time
    if msg.type == "note_on" and msg.velocity > 0 and msg.channel == 7:
        real[(round(t / mid.ticks_per_beat, 4), msg.note)] += 1
for v in range(N_VERSES):
    b0 = (INTRO_BARS + VERSE_BARS * v) * 4
    model = collections.Counter((round(b0 + bt, 4), n) for (bt, dur, n) in tune)
    sub = collections.Counter({k: c for k, c in real.items() if b0 <= k[0] < b0 + 32})
    assert model == sub, (v, (model - sub), (sub - model))
print("tune model = clarinet of midi/ezgi_alti_C.mid in all 7 verses (%d notes per verse)" % len(tune))

tn = np.full(F.n, -1)                                               # tune note sounding at each sung frame (-1: none)
for (bt, dur, n) in tune:
    tn[(F.pos >= bt - 1e-9) & (F.pos < bt + dur)] = n
sn = np.round(F.note_midi).astype(int)
has = tn >= 0
ic = np.where(has, np.minimum((sn - tn) % 12, (tn - sn) % 12), -1)
IC_NAME = {0: "same note (unison / octave)", 1: "semitone / major 7th", 2: "whole tone / minor 7th", 3: "minor 3rd / major 6th",
           4: "major 3rd / minor 6th", 5: "4th / 5th", 6: "tritone"}
interval = {IC_NAME[k]: r(np.mean(ic == k)) for k in range(7)}
interval["no tune note sounding"] = r(np.mean(~has))
close2 = has & (np.abs(sn - tn) <= 2) & (sn != tn)                  # a second in the SAME register (voice and tune next to each other)
sus2, runs2 = run_mask(has & np.isin(ic, (1, 2)), F.t, F.verse)
tune_vs_voice = {
    "share_of_sung_time_by_interval_between_voice_and_tune": interval,
    "different_note_than_the_voice": r(np.mean(has & (ic != 0))),
    "a_second_or_seventh_apart (interval class 1 or 2)": r(np.mean(has & np.isin(ic, (1, 2)))),
    "of_which_in_runs_over_150ms": r(sus2.mean()), "runs_over_150ms": len(runs2),
    "a_second_apart_in_the_same_octave": r(close2.mean()),
    "where": "beats 1.5-2 (voice A4 over tune G4) and beats 2-3.2 (voice G4 under tune A4): the two lines swap the notes G and A in the same octave",
}


def tune_vs_chords(bars):
    plan, deg = major_plan(KEY, bars)
    tot = 0.0; ct = 0.0; cl = 0.0
    for (bt, dur, n) in tune:
        # split the note at beat boundaries
        a = bt
        while a < bt + dur - 1e-9:
            b = min(np.floor(a + 1e-9) + 1, bt + dur)
            ch = plan.chords[int(np.floor(a + 1e-9))]
            isct, iscl, _ = classify_pc(n % 12, ch, plan.scale)
            tot += b - a; ct += (b - a) * isct; cl += (b - a) * iscl
            a = b
    return {"chord_tone": r(ct / tot), "clash": r(cl / tot)}


tune_fit = {"tune_against_the_plain_harmony (I I IV I | I)": tune_vs_chords(PLAIN),
            "tune_against_the_chosen_harmony (I IV I I | V V V V | I I | V V V V)": tune_vs_chords(CHOSEN),
            "note": "share of the tune's own sounding time; clash = a semitone from a chord tone or a tritone from the root. "
                    "In bars 2 and 6 the tune's three 'do' (C) sit a semitone above the third (B) of the dominant."}

# ---- (b) pads and (c) none: share of the sung time one semitone from something that sounds ----------------------------
def pad_matrix(deg32, tones_of):
    """bool[frames, 12] aligned like bant.verse_sounding: pad tones held through every beat of the vocal stretches only."""
    S0, fpb = verse_sounding(band, plan8_of(deg32))
    S = np.zeros_like(S0)
    ton = PC[KEY]
    for b in list(range(0, 4)) + list(range(8, 12)) + [22, 23] + list(range(24, 28)):
        a = int(round((b + 4) * BEAT / FP)); e = int(round((b + 5) * BEAT / FP))
        for pc in tones_of(deg32[b], ton):
            S[a:e, pc] = True
    return S, fpb


def tones_full(deg, ton):
    return [(ton + x) % 12 for x in DEGREE[deg][1]]


def tones_triad(deg, ton):
    return [(ton + x) % 12 for x in DEGREE[deg][1][:3]]


def tones_root_fifth(deg, ton):
    rt = (ton + DEGREE[deg][0]) % 12
    return [rt, (rt + 7) % 12]


def semis(bars, pad=None):
    plan, deg = major_plan(KEY, bars)
    S, fpb = verse_sounding(band, plan8_of(deg))
    if pad is not None:
        P, _ = pad_matrix(deg, pad)
        S = S | P
    e = evaluate(F, plan, sounding=(S, fpb))
    return {"one_semitone_from_a_sounding_note": e["sounding_semitone"], "in_runs_over_150ms": e["sounding_semitone_sustained"]}


under = {
    "none (chords, bass, drums only) - chosen harmony, dominant without the seventh": semis(CHOSEN),
    "none - same harmony with the seventh in the band (V7)": semis(CHOSEN_V7),
    "soft pad: root + fifth of every chord": semis(CHOSEN, tones_root_fifth),
    "soft pad: full triads (dominant without its seventh)": semis(CHOSEN, tones_triad),
    "soft pad: full chords with the seventh on the dominant": semis(CHOSEN_V7, tones_full),
    "none - plain baseline harmony (I I IV I | I)": semis(PLAIN),
    "soft pad: full triads - plain baseline harmony": semis(PLAIN, tones_triad),
}
# the soft tune, as pitch classes that sound (clarinet line; the glockenspiel doubles it an octave up)
plan, deg = major_plan(KEY, CHOSEN)
S, fpb = verse_sounding(band, plan8_of(deg)); S = S.copy()
for (bt, dur, n) in tune:
    a = int(round((bt + 4) * BEAT / FP)); e = int(round((bt + 4 + dur) * BEAT / FP)); S[a:e, n % 12] = True
e = evaluate(F, plan, sounding=(S, fpb))
under["soft Old MacDonald tune under the voice (existing stem) - chosen harmony"] = {
    "one_semitone_from_a_sounding_note": e["sounding_semitone"], "in_runs_over_150ms": e["sounding_semitone_sustained"]}

print("voice against the soft tune (share of the sung time):")
for k, v in interval.items():
    print("   %-28s %5.1f %%" % (k, 100 * v))
print("   different note than the voice %.1f %%; a second / seventh apart %.1f %% (%.1f %% in %d runs over 150 ms); a second apart in the same octave %.1f %%" % (
    100 * tune_vs_voice["different_note_than_the_voice"], 100 * tune_vs_voice["a_second_or_seventh_apart (interval class 1 or 2)"],
    100 * tune_vs_voice["of_which_in_runs_over_150ms"], len(runs2), 100 * tune_vs_voice["a_second_apart_in_the_same_octave"]))
print("tune against the chords:", json.dumps({k: v for k, v in tune_fit.items() if k != "note"}))
print("share of the sung time one semitone (pitch class) from something that sounds:")
for k, v in under.items():
    print("   %-82s %5.1f %%   (runs over 150 ms: %4.1f %%)" % (k, 100 * v["one_semitone_from_a_sounding_note"], 100 * v["in_runs_over_150ms"]))

save_json(os.path.join(T, "alt_politika.json"), {
    "about": "Numbers behind the under-vocal policy of the 'dogal' version (key C). Shares are fractions of the voiced sung time (44.85 s), note mode.",
    "tune_under_the_voice": {"what": "the soft Old MacDonald tune of the existing builder (clarinet C5 C5 C5 G4 A4 A4 G4 in bars 0, 2, 6; repeated C5 on beats 2-3 of bar 5)",
                             "voice_against_tune": tune_vs_voice, "tune_against_chords": tune_fit},
    "one_semitone_from_a_sounding_note": under,
    "definition": "one_semitone_from_a_sounding_note = share of the sung time during which a band / pad / tune note one semitone away in pitch class "
                  "sounds (band: note-on .. note-off + 30 ms from the band model; pad: held through every beat of the vocal stretches).",
})
print("written: alt_politika.json")
