#!/usr/bin/env python3
"""Step 3: measure every I / IV / V7 harmony of the vocal bars in C, F and G major, the plain baseline and the
original D minor loop. Writes olcum.json (summary, rankings, references) and adaylar.json (every candidate).

Search space per key: bar 0 (L1) 3^4 = 81, bar 2 (L2) 81, bar 5 beats 2-3 ("diye bagirir") 9, bar 6 (L4) 81.
The four sung stretches never share a beat (measured: no sung frame of L2, 'diye' or L4 lies before its own bar
line / half bar; L1 starts at most 0.04 beat before the verse downbeat, where the band is on I), so the bars are
independent and the best full plan is the combination of the best bars.

STEP 1 - harmony (chord symbols from I, IV, V7), ranked by the task's chord-level metrics:
    J = chord_tone - 2 * (clash_sustained + outside_scale)            (weights 1 and 4 are checked as well)
  "sade" shape rules of designer A (close to the traditional harmony):
    T1  the verse (bar 0) opens on I
    T2  the dominant resolves: V7 is followed by V7 or I, never by IV
    T3  bar 6 ends on V7 or I (given by the task)
  ties (J within 0.005): fewer chord changes, then fewer changes on beats 1 / 3.
STEP 2 - voicing of the dominant under the vocal: V7 as the builder plays it (with its seventh) or without the seventh
  in the band ("V": the singer sings that seventh herself). Decided by what really sounds: sounding_semitone here,
  rendered audio in 04_ses_olcumu.py.
CROSS-CHECK - the same search with the chords AS PLAYED (I, IV and the dominant triad V) must give the same bars.
"""
import sys, os, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
from olcut import *
from bant import Band, verse_sounding

F = Frames()
SET_TASK = ['I', 'IV', 'V7']
SET_PLAYED = ['I', 'IV', 'V']
DOM = ('V7', 'V')
PLAIN = {0: ['I', 'I', 'IV', 'I'], 2: ['I', 'I', 'IV', 'I'], 5: ['I', 'I'], 6: ['I', 'I', 'IV', 'I']}
BAR_LINE = {0: 'L1', 2: 'L2', 5: 'diye', 6: 'L4'}
KEEP = ("chord_tone", "scale_non_chord", "outside_scale", "clash_any", "clash_sustained", "clash_sustained_strict",
        "consonant_non_chord", "sustained_clash_runs", "sounding_semitone", "sounding_semitone_sustained")
TIE = 0.005


def score(e, w=2.0):
    return e["chord_tone"] - w * (e["clash_sustained"] + e["outside_scale"])


def whole(bar, seq):
    return (['I', 'I'] + list(seq)) if bar == 5 else list(seq)             # bar 5 beats 0-1 are I (drum fill + bass)


def changes(bar, seq):
    full = whole(bar, seq)
    return sum(1 for a, b in zip(full[:-1], full[1:]) if a != b)


def odd_changes(bar, seq):
    full = whole(bar, seq)
    return sum(1 for i in (1, 3) if full[i] != full[i - 1])


def allowed(bar, seq):
    return not (bar == 6 and seq[-1] not in DOM + ('I',))                  # T3 (task)


def shape_ok(bar, seq):
    full = whole(bar, seq)
    if bar == 0 and full[0] != 'I':
        return False                                                       # T1
    nxt = full[1:] + ['I']                                                 # the next bar always starts on I
    if any(a in DOM and b == 'IV' for a, b in zip(full, nxt)):
        return False                                                       # T2
    return allowed(bar, seq)


def full_metrics(key, bars, band=None, detail=False):
    plan, deg = major_plan(key, bars)
    snd = verse_sounding(band or Band(key), plan8_of(deg))
    out = {"note": evaluate(F, plan, sounding=snd, detail=detail), "frame": evaluate(F, plan, mode="frame", sounding=snd),
           "chords_40ms_early": evaluate(F, plan, shift_beats=0.040 / BEAT)}
    out["per_line"] = {ln: evaluate(F, plan, F.line == LINES.index(ln), sounding=snd) for ln in LINES}
    out["per_verse"] = [evaluate(F, plan, F.verse == v, sounding=snd) for v in range(N_VERSES)]
    out["per_verse_and_line"] = [{ln: brief(evaluate(F, plan, (F.verse == v) & (F.line == LINES.index(ln)), sounding=snd)) for ln in LINES}
                                 for v in range(N_VERSES)]
    return out


def brief(e):
    return {k: e[k] for k in KEEP if k in e}


def bar_rows(key, bar, degs, band=None, extra=None, mode="note", shift=0.0):
    """all choices of one bar from the chord set degs, measured over the sung frames of its line"""
    mask = F.line == LINES.index(BAR_LINE[bar])
    if extra is not None:
        mask = mask & extra
    rows = []
    for combo in itertools.product(degs, repeat=len(PLAIN[bar])):
        bars = dict(PLAIN); bars[bar] = list(combo)
        plan, deg = major_plan(key, bars)
        e = evaluate(F, plan, mask, mode=mode, shift_beats=shift, sounding=None if band is None else verse_sounding(band, plan8_of(deg)))
        rows.append({"chords": list(combo), "J": r(score(e)), "changes": changes(bar, combo), "odd_beat_changes": odd_changes(bar, combo),
                     "sade_shape": shape_ok(bar, combo), "allowed": allowed(bar, combo), **brief(e)})
    rows.sort(key=lambda q: (-q["J"], q["changes"], q["odd_beat_changes"]))
    return rows


def pick(rows, need_shape):
    """best row by J among the allowed ones; ties within TIE -> fewer changes, then fewer changes on odd beats"""
    ok = [q for q in rows if q["allowed"] and (q["sade_shape"] or not need_shape)]
    top = max(q["J"] for q in ok)
    tied = sorted([q for q in ok if q["J"] >= top - TIE], key=lambda q: (q["changes"], q["odd_beat_changes"], -q["J"]))
    return tied[0], [q["chords"] for q in tied]


# ---------------------------------------------------------------------------------------------------------------
# 1. every candidate of the task's chord set, per key and bar
# ---------------------------------------------------------------------------------------------------------------
cands = {}; best = {}; ties = {}
for key in ("C", "F", "G"):
    band = Band(key)
    cands[key] = {}; best[key] = {"free": {}, "sade": {}}; ties[key] = {"free": {}, "sade": {}}
    for bar in BAR_LINE:
        rows = bar_rows(key, bar, SET_TASK, band)
        cands[key][str(bar)] = rows
        for kind, need in (("free", False), ("sade", True)):
            b, t = pick(rows, need)
            best[key][kind][bar] = b["chords"]; ties[key][kind][str(bar)] = t
STEP1 = best["C"]["sade"]

# cross-check: the same search in C with the chords as played (dominant = plain triad)
bandC = Band("C")
played = {str(bar): bar_rows("C", bar, SET_PLAYED, bandC) for bar in BAR_LINE}
PLAYED_BEST = {}; played_ties = {}
for bar in BAR_LINE:
    b, t = pick(played[str(bar)], True)
    PLAYED_BEST[bar] = b["chords"]; played_ties[str(bar)] = t

save_json(os.path.join(T, "adaylar.json"), {
    "about": "Every choice for the vocal bars, per verse bar (bar 0 = L1, bar 2 = L2, bar 5 = beats 2-3 'diye bagirir', bar 6 = L4), measured over "
             "the sung frames of that line in all 7 verses (note mode). Sorted by J = chord_tone - 2 * (clash_sustained + outside_scale), then "
             "fewer chord changes. allowed = false: bar 6 would not end on the dominant or I. sade_shape = the bar obeys the shape rules T1-T3. "
             "changes = chord changes inside the bar (bar 5: counted from the I of its beats 0-1). Metric definitions: see olcum.json.",
    "task_chord_set_I_IV_V7": cands,
    "chords_as_played_I_IV_V_in_C": {"about": "the same search with the dominant as a plain triad V (= V7 without its seventh in the band)", "candidates": played}})

# ---------------------------------------------------------------------------------------------------------------
# 2. full plans
# ---------------------------------------------------------------------------------------------------------------
plans = {}
for key in ("C", "F", "G"):
    band = Band(key)
    plans["%s plain baseline" % key] = {"key": key, "bars": PLAIN, **full_metrics(key, PLAIN, band)}
    plans["%s best, free I/IV/V7 per beat" % key] = {"key": key, "bars": best[key]["free"], **full_metrics(key, best[key]["free"], band)}
    plans["%s best, sade shape" % key] = {"key": key, "bars": best[key]["sade"], **full_metrics(key, best[key]["sade"], band)}


def no7(bars):                                                      # same harmony, dominant without its seventh in the band
    return {b: ['V' if c == 'V7' else c for c in ch] for b, ch in bars.items()}


CHOSEN = no7(STEP1)
assert CHOSEN == PLAYED_BEST, ("cross-check failed: as-played search gives", PLAYED_BEST)
L1BAR = ['I', 'IV', 'I', 'I']
ALTS = {
    "A  : I IV I I | V7 V7 V7 V7 | I I | V7 V7 V7 V7  (step-1 harmony, seventh IN the band)": STEP1,
    "A* : I IV I I | V V V V | I I | V V V V  (CHOSEN: step-1 harmony, band plays the dominant without its seventh)": CHOSEN,
    "B  : I IV I I | I I V7 V7 | I I | I I V7 V7": {0: L1BAR, 2: ['I', 'I', 'V7', 'V7'], 5: ['I', 'I'], 6: ['I', 'I', 'V7', 'V7']},
    "B* : I IV I I | I I V V | I I | I I V V  (B without the seventh in the band)": {0: L1BAR, 2: ['I', 'I', 'V', 'V'], 5: ['I', 'I'], 6: ['I', 'I', 'V', 'V']},
    "C  : I IV I I | I I I V7 | I I | I I I V7": {0: L1BAR, 2: ['I', 'I', 'I', 'V7'], 5: ['I', 'I'], 6: ['I', 'I', 'I', 'V7']},
    "C* : I IV I I | I I I V | I I | I I I V  (C without the seventh in the band)": {0: L1BAR, 2: ['I', 'I', 'I', 'V'], 5: ['I', 'I'], 6: ['I', 'I', 'I', 'V']},
    "D  : I IV I I | I I IV V7 | I I | I I IV V7": {0: L1BAR, 2: ['I', 'I', 'IV', 'V7'], 5: ['I', 'I'], 6: ['I', 'I', 'IV', 'V7']},
    "E* : V IV I I | V V V V | I I | V V V V  (as A*, but the verse opens on the dominant: breaks T1 and T2)":
        {0: ['V', 'IV', 'I', 'I'], 2: ['V'] * 4, 5: ['I', 'I'], 6: ['V'] * 4},
}
for name, bars in ALTS.items():
    plans["C " + name] = {"key": "C", "bars": bars, **full_metrics("C", bars, bandC, detail=name.startswith(("A ", "A*")))}

# ---------------------------------------------------------------------------------------------------------------
# 3. reference: the ORIGINAL band of v2_2 (D minor loop Dm C | Gm A, two beats per chord)
#    original bars: L1 over Dm C, L2 over Gm A, "diye bagirir" (beats 2-3 of the third bar) over C, L4 over Gm A
# ---------------------------------------------------------------------------------------------------------------
Dm, Cc, Gm, Aa = named_chord("Dm"), named_chord("C"), named_chord("Gm"), named_chord("A")
orig = [None] * 32
orig[0:4] = [Dm, Dm, Cc, Cc]; orig[4:8] = [Cc] * 4          # beats 4-7 are not sung; beat 7 = what precedes L2 in the original (C)
orig[8:12] = [Gm, Gm, Aa, Aa]; orig[12:20] = [Dm] * 8
orig[20:24] = [Dm, Dm, Cc, Cc]; orig[24:28] = [Gm, Gm, Aa, Aa]; orig[28:32] = [Dm] * 4
ref_plan = Plan(orig, D_MINOR_SCALE | {PC["C#"]}, Aa, "original D minor loop")
ref = {"note": evaluate(F, ref_plan, detail=True), "frame": evaluate(F, ref_plan, mode="frame"),
       "per_line": {ln: evaluate(F, ref_plan, F.line == LINES.index(ln)) for ln in LINES},
       "chords": {"L1": "Dm Dm C C", "L2": "Gm Gm A A", "diye (beats 2-3)": "C C", "L4": "Gm Gm A A"},
       "scale": "D natural minor + C# (the leading tone inside the A chord)",
       "note_on_reading": "chord-level metrics only (the original band is not the oom-pah band, so no 'sounding' numbers). "
                          "tempo.json notes that the A chord of the original has a weak third and a D on top in its last beat (Asus4 / anticipation); "
                          "against a plain A major triad the sung D of 'var' / 'Baba'nin' counts as a clash here."}

# ---------------------------------------------------------------------------------------------------------------
# 4. tables
# ---------------------------------------------------------------------------------------------------------------
def line(name, P):
    e = P["note"]
    return "%-112s ct %5.1f  non-chord %5.1f  outside %4.1f | clash any %5.1f  sustained %5.1f (%2d runs) | sounding semitone %5.1f  sustained %5.1f | J %6.3f" % (
        name, 100 * e["chord_tone"], 100 * e["scale_non_chord"], 100 * e["outside_scale"], 100 * e["clash_any"], 100 * e["clash_sustained"],
        e["sustained_clash_runs"], 100 * e.get("sounding_semitone", float("nan")), 100 * e.get("sounding_semitone_sustained", float("nan")), score(e))


print("ALL SUNG FRAMES (%.2f s voiced, 7 verses), note mode; shares in %% of the voiced sung time" % F.total_s)
for name, P in plans.items():
    nm_ = name if name[2:4] in ("A ", "A*", "B ", "B*", "C ", "C*", "D ", "E*") else name + "  [" + " | ".join(" ".join(P["bars"][b]) for b in (0, 2, 5, 6)) + "]"
    print(line(nm_, P))
e = ref["note"]
print("%-112s ct %5.1f  non-chord %5.1f  outside %4.1f | clash any %5.1f  sustained %5.1f (%2d runs)" % (
    "original D minor loop (reference)", 100 * e["chord_tone"], 100 * e["scale_non_chord"], 100 * e["outside_scale"], 100 * e["clash_any"],
    100 * e["clash_sustained"], e["sustained_clash_runs"]))
print("step 1 (I, IV, V7; C; sade shape):", {b: " ".join(c) for b, c in STEP1.items()}, "| ties:", ties["C"]["sade"])
print("cross-check (chords as played I, IV, V):", {b: " ".join(c) for b, c in PLAYED_BEST.items()}, "| ties:", played_ties)

# robustness of the key ranking to the weight of the 'wrong note' terms
rob = {}
for w in (1.0, 2.0, 4.0):
    rob[str(w)] = {}
    for kind in ("free", "sade"):
        sc = {}; chosen = {}
        for key in ("C", "F", "G"):
            tot = 0.0; ch = {}
            for bar, ln in BAR_LINE.items():
                rows = [q for q in cands[key][str(bar)] if q["allowed"] and (kind == "free" or q["sade_shape"])]
                val = lambda q: q["chord_tone"] - w * (q["clash_sustained"] + q["outside_scale"])
                top = max(val(q) for q in rows)
                b = sorted([q for q in rows if val(q) >= top - TIE], key=lambda q: (q["changes"], q["odd_beat_changes"]))[0]
                tot += val(b) * (F.line == LINES.index(ln)).sum(); ch[str(bar)] = " ".join(b["chords"])
            sc[key] = r(tot / F.n); chosen[key] = ch
        rob[str(w)][kind] = {"score": sc, "best_bars": chosen}
print("key ranking, best plan per key, J with weight w:")
for w, d in rob.items():
    print("   w = %s: free %s | sade %s | C sade bars %s" % (w, d["free"]["score"], d["sade"]["score"], d["sade"]["best_bars"]["C"]))


# robustness of the chosen bars in C: other pitch readings, earlier chord changes, each verse left out, each verse alone;
# for both chord sets (the task's symbols I IV V7, and the chords as played I IV V)
def choice(bar, degs, extra=None, mode="note", shift=0.0):
    return " ".join(pick(bar_rows("C", bar, degs, None, extra, mode, shift), True)[0]["chords"])


def robustness(degs):
    out = {"note mode (primary)": {str(b): choice(b, degs) for b in BAR_LINE},
           "frame mode": {str(b): choice(b, degs, mode="frame") for b in BAR_LINE},
           "chord changes 40 ms early": {str(b): choice(b, degs, shift=0.040 / BEAT) for b in BAR_LINE}}
    keep = F.pc_frame.copy()                      # second pitch tracker: frames rounded on the dio / stonemask pitch
    ok = F.midi_dio > 0
    F.pc_frame = np.where(ok, np.round(np.where(ok, F.midi_dio, 60)).astype(int) % 12, F.pc_frame)
    out["frame mode, dio/stonemask pitch"] = {str(b): choice(b, degs, mode="frame") for b in BAR_LINE}
    F.pc_frame = keep
    for v in range(N_VERSES):
        out["verse %d left out" % (v + 1)] = {str(b): choice(b, degs, F.verse != v) for b in BAR_LINE}
    for v in range(N_VERSES):
        out["verse %d alone" % (v + 1)] = {str(b): choice(b, degs, F.verse == v) for b in BAR_LINE}
    return out


robs = {"task_chord_set_I_IV_V7": robustness(SET_TASK), "chords_as_played_I_IV_V": robustness(SET_PLAYED)}
for nm_, R in robs.items():
    ref_choice = R["note mode (primary)"]
    print("chosen bars under other readings, %s (same = identical to the primary choice %s):" % (nm_, list(ref_choice.values())))
    stable = {b: 0 for b in ref_choice}
    for k, v in R.items():
        diff = {b: c for b, c in v.items() if c != ref_choice[b]}
        for b in ref_choice:
            stable[b] += v[b] == ref_choice[b]
        print("   %-34s %s" % (k, "same" if not diff else "DIFFERENT: %s" % diff))
    R["readings_agreeing_with_primary_per_bar"] = {b: "%d of %d" % (n, len(R) ) for b, n in stable.items()}
    print("   agreeing readings per bar:", R["readings_agreeing_with_primary_per_bar"])

save_json(os.path.join(T, "olcum.json"), {
    "about": "Chord-fit measurements of the unprocessed sung melody of v2_2 for harmony designer A (I, IV, V7 only). "
             "All shares are fractions of the voiced sung time (44.85 s = 8970 frames of 5 ms in the kept syllables of 7 verses), "
             "evaluated at each frame's own time in the new song form (placement shifts of kesim.json, no time-stretch).",
    "metric_definitions": {
        "chord_tone": "sung pitch class is a chord tone of the chord on that beat",
        "scale_non_chord": "in the key's scale but not a chord tone",
        "outside_scale": "not in the key's scale (and not a chord tone); chord_tone + scale_non_chord + outside_scale = 1",
        "clash_any": "not a chord tone AND (a semitone above or below a chord tone OR a tritone from the chord root)",
        "clash_sustained": "the part of clash_any inside a clash run longer than 150 ms; a run survives up to 60 ms without sung pitch "
                           "(a consonant) and up to 15 ms of non-clash frames; run length = last - first frame + 5 ms",
        "clash_sustained_strict": "same without any bridging (consecutive 5 ms frames only)",
        "consonant_non_chord": "scale_non_chord that is not a clash",
        "sounding_semitone": "PHYSICAL, from the band model (bant.py, checked note for note against midi/altyapi_C.mid): share of the sung time during "
                             "which a band note one semitone away in pitch class is really sounding (note-on .. note-off + 30 ms). In the oom-pah "
                             "pattern the third and seventh of a chord sound on the off-beats and on beats 1 and 3, not on beats 0 and 2.",
        "sounding_semitone_sustained": "the part of sounding_semitone in runs longer than 150 ms (same run rule)",
        "J": "ranking score = chord_tone - 2 * (clash_sustained + outside_scale)",
        "V": "the dominant as a plain triad = the V7 of the task with its seventh left out of the BAND (the singer sings that seventh). "
             "Chord-level numbers of a plan written with V treat the seventh as a non-chord tone; the same plan written with V7 treats it as a chord tone.",
        "modes": "'note' (primary): a frame carries the pitch class of the note it belongs to (kesim.json syllable.notes; scoops and glides count "
                 "with their note). 'frame': every 5 ms frame is rounded on its own (16.9 % of the frames are then in transit between notes). "
                 "'chords_40ms_early': note mode with all chord changes 40 ms earlier (the singer starts syllables 20-70 ms before the beat)."},
    "sade_shape_rules": {"T1": "the verse (bar 0) opens on I", "T2": "the dominant is followed by the dominant or I, never by IV", "T3": "bar 6 ends on the dominant or I",
                         "ties": "J within 0.005: fewer chord changes, then fewer changes on beats 1 / 3"},
    "step1_harmony_C_sade": {str(b): c for b, c in STEP1.items()},
    "step1_ties": ties["C"]["sade"],
    "cross_check_chords_as_played": {"best_bars": {str(b): c for b, c in PLAYED_BEST.items()}, "ties": played_ties,
                                     "agrees_with_step1_harmony_played_without_the_seventh": CHOSEN == PLAYED_BEST},
    "chosen_bars_as_played": {str(b): c for b, c in CHOSEN.items()},
    "plans": plans,
    "reference_original_d_minor_loop": ref,
    "best_bars": {k: {kind: {str(b): v for b, v in d.items()} for kind, d in best[k].items()} for k in best},
    "robustness_of_the_chosen_bars": {"about": "the best sade-shaped bars of key C recomputed under other pitch readings, with chord changes 40 ms "
                                               "earlier, with each verse left out and for each verse alone", **robs},
    "key_ranking_robustness": {"about": "score and bars of the best plan per key for weights w = 1, 2, 4 in J = chord_tone - w * (clash_sustained + outside_scale)", **rob},
})
print("written: olcum.json, adaylar.json")
