#!/usr/bin/env python3
"""Step 4: full measurements. Writes olcum.json.

  A. plans: plain baseline in C / F / G, the original D minor loop, the best plan per key and rule set (03_tara.py),
     and the finalists of designer B in C. For each: the task's metrics in four readings (note mode, frame mode, second
     pitch tracker, chord changes 40 ms early), per line, per verse, and what PHYSICALLY sounds against the voice
     (band model, bant.py: a semitone away / a whole tone away in the same octave / the same pitch class).
  B. bar 0 (L1) in detail: the candidates for the verse opening, and the pitch course of the gliding syllable
     'li' of "Ali" on which their ranking depends.
  C. stage 2: the dominant of bars 2 and 6 with or without its seventh in the band.
  D. robustness: is each bar of the chosen plan still the pick in 18 readings (4 global readings, each verse left out,
     each verse alone), for both rule sets?  Per-verse check of bar 2 (do the animal words need different chords?).
  E. under-vocal policy: the Old MacDonald tune of the existing builder against the voice and against the chosen
     chords; semitone exposure with no pad / root+fifth pad / triad pad / chord pad.
"""
import sys, os, itertools, time
import mido
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
from olcut import *
from kurallar import *
from bant import Band, verse_sounding, sounding_semitone, sounding_same_octave, sounding_relations, plan8

F = Frames()
K = load_json(KESIM)
SCAN = load_json(os.path.join(ARA, "tarama.json"))
EARLY = 0.040 / BEAT
TIE = 0.005
t0 = time.time()

KEEP = ("chord_tone", "scale_non_chord", "outside_scale", "clash_any", "clash_sustained", "clash_sustained_strict",
        "consonant_non_chord", "sustained_clash_runs", "on_beat_chord_tone", "off_beat_chord_tone", "line_end_chord_tone")


def brief(e, extra=()):
    return {k: e[k] for k in KEEP + tuple(extra) if k in e}


def phys(band, bars, mask=None, mode="note", root_bass_bars=(), open3_bars=()):
    s12, _ = verse_sounding(band, bars, root_bass_bars=root_bass_bars, open3_bars=open3_bars)
    s128, _ = verse_sounding(band, bars, exact=True, root_bass_bars=root_bass_bars, open3_bars=open3_bars)
    d = sounding_semitone(F, s12, mask, mode); d.update(sounding_same_octave(F, s128, mask, mode))
    d.update(sounding_relations(F, s12, s128, mask, mode))
    return d


def B(b0, b2, b5, b6):
    return {0: b0.split(), 2: b2.split(), 5: b5.split(), 6: b6.split()}


def full(key, bars, detail=False, label=None):
    plan, deg = major_plan(key, bars)
    band = Band(key)
    out = {"label": label, "key": key, "bars": {str(b): list(v) for b, v in bars.items()},
           "chords": {str(b): [chord_of_degree(PC[key], d)["name"] for d in v] for b, v in bars.items()}}
    e = evaluate(F, plan, detail=detail)
    out["note_voiced_s"] = e["voiced_s"]
    out["note"] = {**brief(e), "J": r(J(e)), **phys(band, bars)}
    if detail:
        out["note"]["runs"] = e["runs"]
    for mode in ("frame", "dio"):
        em = evaluate(F, plan, mode=mode)
        out[mode] = {**brief(em), "J": r(J(em)), **phys(band, bars, mode=mode)}
    ee = evaluate(F, plan, shift_beats=EARLY)
    out["chords_40ms_early"] = {**brief(ee), "J": r(J(ee))}
    out["per_line"] = {}
    for ln in LINES:
        m = F.line == LINES.index(ln)
        el = evaluate(F, plan, m); ef = evaluate(F, plan, m, mode="frame")
        out["per_line"][ln] = {**brief(el), "J": r(J(el)), "J_frame": r(J(ef)), "frame_chord_tone": ef["chord_tone"],
                               "frame_clash_sustained": ef["clash_sustained"], **phys(band, bars, m)}
    out["per_verse"] = []
    for v in range(N_VERSES):
        m = F.verse == v
        ev = evaluate(F, plan, m)
        out["per_verse"].append({"verse": v + 1, "animal": ANIMALS[v], **brief(ev), "J": r(J(ev)), **phys(band, bars, m)})
    return out


def line1(name, P):
    e = P["note"]; f = P["frame"]
    return ("%-50s ct %5.1f non %5.1f out %4.1f | clash any %5.1f sus %5.1f (%2d) | on-beat %5.1f end %5.1f | band: semitone %5.1f (sus %4.1f) whole tone %5.1f doubled %5.1f | "
            "J %6.3f | frame: ct %5.1f sus %5.1f J %6.3f" % (
                name, 100 * e["chord_tone"], 100 * e["scale_non_chord"], 100 * e["outside_scale"], 100 * e["clash_any"], 100 * e["clash_sustained"],
                e["sustained_clash_runs"], 100 * e["on_beat_chord_tone"], 100 * e["line_end_chord_tone"], 100 * e["sounding_semitone"],
                100 * e["sounding_semitone_sustained"], 100 * e["whole_tone_same_octave"], 100 * e["band_same_pitch_class"], e["J"],
                100 * f["chord_tone"], 100 * f["clash_sustained"], f["J"]))


# =================================================================================================================
# A. plans
# =================================================================================================================
BEST = B("ii ii I I", "V V V V", "I I", "V V V V")
RUNNER = B("V IV I I", "V V V V", "I I", "V V V V")
FINALISTS = {
    "BEST": ("ii ii I I | V V V V | I I | V V V V  (chosen)", BEST),
    "RUNNER_UP": ("V IV I I | V V V V | I I | V V V V  (runner-up: highest fit, rule set 'turnaround')", RUNNER),
    "variant_ii_V_I": ("ii ii V I | V V V V | I I | V V V V  (the chosen plan with a full ii-V-I in bar 0)", B("ii ii V I", "V V V V", "I I", "V V V V")),
    "symbolic_optimum_strict": ("ii ii I I | V V V V7 | I I | V V V V7  (stage-1 optimum of the strict rules: seventh on the last beat)", B("ii ii I I", "V V V V7", "I I", "V V V V7")),
    "symbolic_optimum_turnaround": ("V IV I I | V V V V7 | I I | V V V V7  (stage-1 optimum of the turnaround rules)", B("V IV I I", "V V V V7", "I I", "V V V V7")),
    "seventh_everywhere": ("ii ii I I | V7 V7 V7 V7 | I I | V7 V7 V7 V7  (the band plays the seventh in all of bars 2 and 6)", B("ii ii I I", "V7 V7 V7 V7", "I I", "V7 V7 V7 V7")),
    "designer_A": ("I IV I I | V V V V | I I | V V V V  (designer A's plan as the band plays it)", B("I IV I I", "V V V V", "I I", "V V V V")),
    "tonic_first_half_bars_2_6": ("ii ii I I | I I V V | I I | I I V V", B("ii ii I I", "I I V V", "I I", "I I V V")),
    "L1_ends_on_V": ("ii ii V V | V V V V | I I | V V V V", B("ii ii V V", "V V V V", "I I", "V V V V")),
    "bar_5_on_V": ("ii ii I I | V V V V | V V | V V V V", B("ii ii I I", "V V V V", "V V", "V V V V")),
    "V_vi_I_I": ("V vi I I | V V V V | I I | V V V V  (outside both rule sets)", B("V vi I I", "V V V V", "I I", "V V V V")),
    "V_ii_I_I": ("V ii I I | V V V V | I I | V V V V  (outside both rule sets)", B("V ii I I", "V V V V", "I I", "V V V V")),
    "I_ii_V_I": ("I ii V I | V V V V | I I | V V V V", B("I ii V I", "V V V V", "I I", "V V V V")),
}
plans = {}
for key in ("C", "F", "G"):
    plans["%s plain baseline" % key] = full(key, PLAIN, detail=(key == "C"), label="I I IV I | I I IV I | I I | I I IV I")
    for kind, txt in (("rules", "strict rules"), ("turnaround", "turnaround rules"), ("free", "any sequence")):
        bars = {int(b): v for b, v in SCAN["best_per_key"][key][kind]["bars"].items()}
        plans["%s best by fit, %s" % (key, txt)] = full(key, bars, label=" | ".join(" ".join(bars[b]) for b in (0, 2, 5, 6)))
for name, (label, bars) in FINALISTS.items():
    plans["C " + name] = full("C", bars, detail=True, label=label)

ref_plan = original_plan()
ref = {"chords": {"L1 (bar 0)": "Dm Dm C C", "L2 (bar 2)": "Gm Gm A A", "diye bagirir (bar 5, beats 2-3)": "C C", "L4 (bar 6)": "Gm Gm A A"},
       "scale": "D natural minor + C# (the leading tone inside the A chord)"}
for mode in ("note", "frame", "dio"):
    e = evaluate(F, ref_plan, mode=mode, detail=(mode == "note"))
    ref[mode] = {**brief(e), "J": r(J(e))}
    if mode == "note":
        ref[mode]["runs"] = e["runs"]
ref["per_line"] = {}
for ln in LINES:
    el = evaluate(F, ref_plan, F.line == LINES.index(ln))
    ref["per_line"][ln] = {**brief(el), "J": r(J(el))}
ref["note_on_reading"] = ("chord-level metrics only (the original band is not the oom-pah band, so no 'sounding' numbers). tempo.json notes that "
                          "the A chord of the original has a weak third and a D on top in its last beat; against a plain A major triad the sung D "
                          "of 'var' / 'Baba'nin' counts as a clash here.")

print("ALL SUNG FRAMES (%.2f s voiced, 7 verses); shares in %% of the voiced sung time; note mode unless marked" % F.total_s)
for name, P in plans.items():
    print(line1(name[:50] if name.startswith("C ") and name[2:] in FINALISTS else (name + " [" + P["label"] + "]")[:50], P))
    if name.startswith("C ") and name[2:] in FINALISTS:
        print("      = " + P["label"])
e = ref["note"]
print("%-50s ct %5.1f non %5.1f out %4.1f | clash any %5.1f sus %5.1f (%2d) | on-beat %5.1f end %5.1f" % (
    "original D minor loop (reference)", 100 * e["chord_tone"], 100 * e["scale_non_chord"], 100 * e["outside_scale"], 100 * e["clash_any"],
    100 * e["clash_sustained"], e["sustained_clash_runs"], 100 * e["on_beat_chord_tone"], 100 * e["line_end_chord_tone"]))

# =================================================================================================================
# B. bar 0 in detail
# =================================================================================================================
bandC = Band("C")
mL1 = F.line == LINES.index("L1")
m01 = mL1 & (F.pos < 1.95)
bar0 = {}
print("BAR 0 (L1): the candidates for the verse opening (frames of L1; 'beats 0-1' = up to beat 1.95)")
for seq in ("I I IV I", "I IV I I", "ii ii I I", "ii ii V I", "V IV I I", "V ii I I", "V vi I I", "ii ii V V", "V V I I", "I I I I"):
    bars = B(seq, "V V V V", "I I", "V V V V")
    plan, _ = major_plan("C", bars)
    d = {"changes_inside_the_bar": changes(0, seq.split()), "passes_strict_rules": all(rules(0, seq.split()).values()),
         "passes_turnaround_rules": all(rules(0, seq.split(), turnaround=True).values())}
    for mode in ("note", "frame", "dio"):
        e = evaluate(F, plan, mL1, mode=mode)
        d[mode] = {**{k: e[k] for k in ("chord_tone", "clash_any", "clash_sustained", "on_beat_chord_tone", "off_beat_chord_tone", "line_end_chord_tone")}, "J": r(J(e))}
    ee = evaluate(F, plan, mL1, shift_beats=EARLY)
    d["chords_40ms_early"] = {"chord_tone": ee["chord_tone"], "J": r(J(ee))}
    d["band_model_L1"] = phys(bandC, bars, mL1)
    d["band_model_beats_0_1"] = phys(bandC, bars, m01)
    e01 = evaluate(F, plan, m01)
    d["beats_0_1"] = {"sung_s": r(m01.sum() * FP, 2), "chord_tone": e01["chord_tone"], "on_beat_chord_tone": e01["on_beat_chord_tone"]}
    bar0[seq] = d
    print("  %-10s chg %d rules %s/%s | note: ct %5.1f on-beat %5.1f off-beat %5.1f J %.3f | frame: ct %5.1f J %.3f | dio J %.3f | early J %.3f | "
          "band, beats 0-1: doubled %5.1f unison %5.1f whole tone %5.1f (sus %4.1f) semitone %4.1f" % (
              seq, d["changes_inside_the_bar"], "y" if d["passes_strict_rules"] else "n", "y" if d["passes_turnaround_rules"] else "n",
              100 * d["note"]["chord_tone"], 100 * d["note"]["on_beat_chord_tone"], 100 * d["note"]["off_beat_chord_tone"], d["note"]["J"],
              100 * d["frame"]["chord_tone"], d["frame"]["J"], d["dio"]["J"], d["chords_40ms_early"]["J"],
              100 * d["band_model_beats_0_1"]["band_same_pitch_class"], 100 * d["band_model_beats_0_1"]["band_unison"],
              100 * d["band_model_beats_0_1"]["whole_tone_same_octave"], 100 * d["band_model_beats_0_1"]["whole_tone_same_octave_sustained"],
              100 * d["band_model_beats_0_1"]["sounding_semitone"]))

# the gliding syllable 'li' of "Ali" (2nd syllable of L1)
ms = mL1 & (F.syl == 1)
mi = F.midi[ms]
glide = {"what": "2nd syllable of line 1 ('li' of 'Ali'), all 7 verses; kesim.json files it as ONE note G4 with a glide of +2.5 semitones",
         "voiced_ms_per_verse": r(ms.sum() * FP / 7 * 1000, 0),
         "ms_per_verse_by_pitch": {"below G4 (scoop up from D4)": r((mi < 66.5).sum() * FP / 7 * 1000, 0),
                                   "G4 +-50 cents": r(((mi >= 66.5) & (mi < 67.5)).sum() * FP / 7 * 1000, 0),
                                   "G#4 (in transit)": r(((mi >= 67.5) & (mi < 68.5)).sum() * FP / 7 * 1000, 0),
                                   "A4 +-50 cents": r((mi >= 68.5).sum() * FP / 7 * 1000, 0)},
         "beat_at_which_the_voice_reaches_A4_per_verse": [r(F.pos[ms & (F.verse == v)][np.flatnonzero(F.midi[ms & (F.verse == v)] >= 68.5)[0]], 2) for v in range(7)],
         "median_pitch_per_0.05_beat": {("%.2f" % a): r(np.median(F.midi[ms & (F.pos >= a) & (F.pos < a + 0.05)]), 2)
                                        for a in np.arange(0.45, 0.90, 0.05) if (ms & (F.pos >= a) & (F.pos < a + 0.05)).sum() > 10},
         "reading": "the voice holds G4 from about beat 0.52 to 0.75 (while the band's off-beat strum sounds, 0.50-0.78) and is on A4 from about "
                    "beat 0.78, a sixteenth before the A4 of 'Baba'nin'. Note mode counts the whole syllable as G; frame mode counts only the "
                    "frames that are really within 50 cents of G."}
print("GLIDE 'li':", glide["ms_per_verse_by_pitch"], "| reaches A4 at beat", glide["beat_at_which_the_voice_reaches_A4_per_verse"])

# =================================================================================================================
# C. stage 2: the seventh of the dominant in the band (bars 2 and 6)
# =================================================================================================================
stage2 = {}
OPTS = ["V V V V", "V V V V7", "V V V7 V7", "V7 V7 V7 V7"]
print("STAGE 2 - the dominant of bars 2 / 6 with or without its seventh (frames of that line; the other bars as chosen)")
for bar, ln in ((2, "L2"), (6, "L4")):
    stage2[ln] = {}
    m = F.line == LINES.index(ln)
    for o in OPTS:
        bars = B("ii ii I I", "V V V V", "I I", "V V V V"); bars[bar] = o.split()
        plan, _ = major_plan("C", bars)
        d = {}
        for mode in ("note", "frame", "dio"):
            e = evaluate(F, plan, m, mode=mode)
            d[mode] = {**{k: e[k] for k in ("chord_tone", "clash_any", "clash_sustained", "sustained_clash_runs", "outside_scale", "on_beat_chord_tone")}, "J": r(J(e)),
                       **phys(bandC, bars, m, mode)}
        ee = evaluate(F, plan, m, shift_beats=EARLY)
        d["chords_40ms_early"] = {**{k: ee[k] for k in ("chord_tone", "clash_any", "clash_sustained")}, "J": r(J(ee))}
        m3 = m & (np.floor(F.pos - 4 * bar + 1e-9) == 3)
        e3 = evaluate(F, plan, m3)
        d["beat_3_only"] = {"sung_s": r(m3.sum() * FP, 2), "chord_tone": e3["chord_tone"], "clash_any": e3["clash_any"], **phys(bandC, bars, m3)}
        stage2[ln][o] = d
        print("  bar %d %-13s note: ct %5.1f on-beat %5.1f clash any %5.1f sus %5.1f J %.3f band semitone %5.1f (sus %4.1f) | frame: ct %5.1f sus %5.1f J %.3f band semitone %5.1f (sus %4.1f) | dio: J %.3f | early: J %.3f" % (
            bar, o, 100 * d["note"]["chord_tone"], 100 * d["note"]["on_beat_chord_tone"], 100 * d["note"]["clash_any"], 100 * d["note"]["clash_sustained"], d["note"]["J"],
            100 * d["note"]["sounding_semitone"], 100 * d["note"]["sounding_semitone_sustained"],
            100 * d["frame"]["chord_tone"], 100 * d["frame"]["clash_sustained"], d["frame"]["J"], 100 * d["frame"]["sounding_semitone"],
            100 * d["frame"]["sounding_semitone_sustained"], d["dio"]["J"], d["chords_40ms_early"]["J"]))

# =================================================================================================================
# D. robustness of the choice (key C)
# =================================================================================================================
VALID = {tr: {bar: [c for c in itertools.product(DEGS, repeat=len(PLAIN[bar])) if all(rules(bar, c, turnaround=tr).values())] for bar in BAR_LINE}
         for tr in (False, True)}
print("sequences inside the rules per bar: strict", {b: len(v) for b, v in VALID[False].items()}, "| turnaround", {b: len(v) for b, v in VALID[True].items()})


def score_all(bar, vmask, mode="note", shift=0.0, turnaround=False):
    ln = BAR_LINE[bar]
    m = (F.line == LINES.index(ln)) & vmask
    rows = {}
    for combo in VALID[True][bar] if turnaround else VALID[False][bar]:
        bars = dict(PLAIN); bars[bar] = list(combo)
        plan, _ = major_plan("C", bars)
        e = evaluate(F, plan, m, mode=mode, shift_beats=shift)
        rows[" ".join(combo)] = (J(e), e["on_beat_chord_tone"] or 0.0)
    return rows


def pick_from(bar, rows):
    top = max(q[0] for q in rows.values())
    tied = [k for k, q in rows.items() if q[0] >= top - TIE]
    tied.sort(key=lambda k: (changes(bar, k.split()), odd_changes(bar, k.split()), -rows[k][1]))
    return tied[0], tied, top


ALLV = np.ones(F.n, bool)
READINGS = [("note mode", ALLV, "note", 0.0), ("frame mode", ALLV, "frame", 0.0), ("second tracker (dio)", ALLV, "dio", 0.0),
            ("chord changes 40 ms early", ALLV, "note", EARLY)]
READINGS += [("without verse %d" % (v + 1), F.verse != v, "note", 0.0) for v in range(N_VERSES)]
READINGS += [("verse %d alone" % (v + 1), F.verse == v, "note", 0.0) for v in range(N_VERSES)]
CH_STRICT = {0: "ii ii I I", 2: "V V V V", 5: "I I", 6: "V V V V"}
CH_TURN = {0: "V IV I I", 2: "V V V V", 5: "I I", 6: "V V V V"}
rob = {"readings": []}
cnt = {"strict": {b: 0 for b in BAR_LINE}, "turnaround": {b: 0 for b in BAR_LINE}}
worst = {"strict": {b: 0.0 for b in BAR_LINE}, "turnaround": {b: 0.0 for b in BAR_LINE}}
worst_dom = {"strict": {2: 0.0, 6: 0.0}, "turnaround": {2: 0.0, 6: 0.0}}
for (name, vm, mode, sh) in READINGS:
    row = {"reading": name}
    for rs, tr, CH in (("strict", False, CH_STRICT), ("turnaround", True, CH_TURN)):
        row[rs] = {}
        for bar in BAR_LINE:
            rows = score_all(bar, vm, mode, sh, tr)
            p, tied, top = pick_from(bar, rows)
            same = (set(p.split()) <= set(DOM)) if bar in (2, 6) else (p == CH[bar])
            cnt[rs][bar] += int(same)
            deficit = top - rows[CH[bar]][0]
            worst[rs][bar] = max(worst[rs][bar], deficit)
            row[rs][str(bar)] = {"pick": p, "tied_with": tied[1:6], "J_of_the_pick": r(top), "J_deficit_of_the_chosen_sequence": r(deficit)}
            if bar in (2, 6):
                dom_best = max(q[0] for k, q in rows.items() if set(k.split()) <= set(DOM))
                row[rs][str(bar)]["J_deficit_of_the_best_dominant_only_sequence"] = r(top - dom_best)
                worst_dom[rs][bar] = max(worst_dom[rs][bar], top - dom_best)
    rob["readings"].append(row)
rob["agreement"] = {rs: {str(b): {"same_harmony_as_chosen": "%d of %d" % (cnt[rs][b], len(READINGS)),
                                  "largest_J_deficit_of_the_chosen_sequence_in_any_reading": r(worst[rs][b])} for b in BAR_LINE}
                    for rs in ("strict", "turnaround")}
for rs in ("strict", "turnaround"):
    for b in (2, 6):
        rob["agreement"][rs][str(b)]["largest_J_deficit_of_the_best_dominant_only_sequence_in_any_reading"] = r(worst_dom[rs][b])
rob["how_to_read"] = ("For each reading the best sequence inside the rule set is searched again (J on the frames of that bar's line, ties as in "
                      "03_tara.py). 'same harmony as chosen': strict rules: bar 0 = ii ii I I; turnaround rules: bar 0 = V IV I I; both: bar 5 = I I, "
                      "bars 2 and 6 = the dominant on all four beats (V or V7 on each beat; whether the band plays the seventh is stage 2). "
                      "J_deficit = J of the reading's pick minus J of the chosen sequence in the same reading (0 = the chosen sequence is the pick). "
                      "For bars 2 and 6 the deficit of the chosen V V V V is mostly the stage-2 question (a sung F counts as a chord tone only when the "
                      "symbol is V7); J_deficit_of_the_best_dominant_only_sequence shows what the HARMONY 'dominant on all four beats' loses against "
                      "the reading's pick (0 in 16 of 18 readings).")
print("ROBUSTNESS (18 readings):")
for rs in ("strict", "turnaround"):
    print("  %-10s %s" % (rs, {b: (v["same_harmony_as_chosen"], v["largest_J_deficit_of_the_chosen_sequence_in_any_reading"]) for b, v in rob["agreement"][rs].items()}))
for row in rob["readings"]:
    print("   %-26s strict %s | turnaround bar 0: %s" % (row["reading"], {b: v["pick"] for b, v in row["strict"].items()}, row["turnaround"]["0"]["pick"]))
print("(%.0f s)" % (time.time() - t0))

# ---- per verse: the animal word (bar 2) -------------------------------------------------------------------------
per_verse_L2 = []
for v in range(N_VERSES):
    vm = F.verse == v
    m = vm & (F.line == LINES.index("L2"))
    p, tied, _top = pick_from(2, score_all(2, vm))
    res_v = {}
    for o in ("V V V V", "V V V V7", "I I IV I"):
        plan, _ = major_plan("C", B("ii ii I I", o, "I I", "V V V V"))
        e = evaluate(F, plan, m)
        res_v[o] = {k: e[k] for k in ("chord_tone", "clash_any", "clash_sustained")}
    word = [s for s in K["verses"][v]["lines"][1]["syllables"] if s["kept"] and not s["excise"]][4:-1]
    per_verse_L2.append({"verse": v + 1, "animal": ANIMALS[v],
                         "animal_word_notes": " ".join("%s:%s" % (s["text"], "+".join(n["note"] for n in s["notes"])) for s in word),
                         "best_sequence_for_this_verse_alone": p, "tied_with": tied[1:6], **res_v})
    print("  verse %d %-6s %-40s best alone: %-12s | V V V V: ct %5.1f clash any %4.1f sus %4.1f | plain I I IV I: ct %5.1f sus %5.1f" % (
        v + 1, ANIMALS[v], per_verse_L2[-1]["animal_word_notes"], p, 100 * res_v["V V V V"]["chord_tone"], 100 * res_v["V V V V"]["clash_any"],
        100 * res_v["V V V V"]["clash_sustained"], 100 * res_v["I I IV I"]["chord_tone"], 100 * res_v["I I IV I"]["clash_sustained"]))

# =================================================================================================================
# E. under-vocal policy
# =================================================================================================================
mid = mido.MidiFile(MIDI_ALT_C)
tpb = mid.ticks_per_beat; tt = 0; on = {}; tune = []
for msg in mid.tracks[0]:
    tt += msg.time
    if msg.type == "note_on" and msg.velocity > 0:
        on[(msg.channel, msg.note)] = tt
    elif msg.type in ("note_off", "note_on") and (msg.channel, msg.note) in on:
        a = on.pop((msg.channel, msg.note))
        if msg.channel == 7:                                    # clarinet = the tune itself (the glockenspiel doubles it an octave up)
            tune.append((a / tpb, (tt - a) / tpb, msg.note))
v0 = INTRO_BARS * 4
tune_v1 = [(b - v0, d, n) for (b, d, n) in tune if v0 <= b < v0 + 32]
for v in range(1, N_VERSES):                                   # the stem is identical in every verse
    tv = [(round(b - v0 - 32 * v, 4), round(d, 4), n) for (b, d, n) in tune if v0 + 32 * v <= b < v0 + 32 * (v + 1)]
    assert tv == [(round(b, 4), round(d, 4), n) for (b, d, n) in tune_v1], "tune differs between verses"
nfr = int(np.ceil(32 * BEAT / FP)) + 2
tune_note = np.full(nfr, -1)
for (b, d, n) in tune_v1:
    tune_note[int(np.floor(b * BEAT / FP + 1e-6)):int(np.ceil((b + d) * BEAT / FP - 1e-6))] = n
fi = np.clip(np.floor(F.pos * BEAT / FP + 1e-6).astype(int), 0, nfr - 1)
tn = np.where(F.pos >= 0, tune_note[fi], -1)
vn = np.round(F.note_midi).astype(int)
has = tn >= 0
ic = np.where(has, np.minimum((vn - tn) % 12, (tn - vn) % 12), -1)
IC = {0: "same note (unison / octave)", 1: "semitone / major 7th", 2: "whole tone / minor 7th", 3: "minor 3rd / major 6th",
      4: "major 3rd / minor 6th", 5: "4th / 5th", 6: "tritone"}
second = (ic == 1) | (ic == 2)
sus2, runs2 = run_mask(second, F.t, F.verse)
close2 = has & (np.abs(vn - tn) <= 2) & (vn != tn)


def tune_vs(bars):
    plan, _ = major_plan("C", bars)
    tot = 0.0; ct = 0.0; cl = 0.0
    for (b, d, n) in tune_v1:
        k = 0.0
        while k < d - 1e-9:                                     # split at beat boundaries
            step = min(d - k, np.floor(b + k + 1e-9) + 1 - (b + k))
            bi = int(np.floor(b + k + 1e-9)) + 1
            tot += step; ct += step * plan.CT[bi, n % 12]; cl += step * plan.CL[bi, n % 12]
            k += step
    return {"chord_tone": r(ct / tot), "clash": r(cl / tot)}


def exposure(extra_pcs_per_beat=None, bars=BEST, mode="note"):
    """share of the sung time one semitone (pitch class) from a sounding band note; extra = a sustained pad: pitch classes
    held through each beat of the verse (list of 32 sets)."""
    s12, _ = verse_sounding(bandC, bars)
    s = s12.copy()
    if extra_pcs_per_beat is not None:
        fpb1 = BEAT / FP
        off = int(round(4 * fpb1))
        for bt, pcs in enumerate(extra_pcs_per_beat):
            a = off + int(round(bt * fpb1)); b = off + int(round((bt + 1) * fpb1))
            for p in pcs:
                s[a:b, p] = True
    d = sounding_semitone(F, s, mode=mode)
    return {"one_semitone_from_a_sounding_note": d["sounding_semitone"], "in_runs_over_150ms": d["sounding_semitone_sustained"]}


def pad(bars, what):
    deg = [d for bar in plan8(bars) for d in bar]
    out = []
    for i, dg in enumerate(deg):
        sung_bar = (i // 4 in (0, 2, 6)) or (i // 4 == 5 and i % 4 >= 2)
        if not sung_bar:
            out.append(set()); continue
        c = chord_of_degree(PC["C"], dg); root = c["root"]
        if what == "root_fifth":
            out.append({root, (root + 7) % 12})
        elif what == "triad":
            out.append({root, (root + (3 if dg in ("ii", "iii", "vi") else 4)) % 12, (root + 7) % 12})
        else:
            out.append(set(c["tones"]))
    return out


B7 = B("ii ii I I", "V7 V7 V7 V7", "I I", "V7 V7 V7 V7")
alt = {
    "tune_under_the_voice": {
        "what": "the soft Old MacDonald tune of the existing builder (clarinet C5 C5 C5 G4 A4 A4 G4 in bars 0, 2, 6; repeated C5 on beats 2-3 of bar 5)",
        "share_of_sung_time_by_interval_between_voice_and_tune": {**{IC[i]: r(np.mean(ic == i)) for i in range(7)}, "no tune note sounding": r(np.mean(~has))},
        "different_note_than_the_voice": r(np.mean(has & (ic != 0))),
        "a_second_or_seventh_apart": r(np.mean(second)), "of_which_in_runs_over_150ms": r(np.mean(sus2)), "runs_over_150ms": len(runs2),
        "a_second_apart_in_the_same_octave": r(np.mean(close2)),
        "tune_against_the_plain_harmony": tune_vs(PLAIN),
        "tune_against_the_chosen_harmony": tune_vs(BEST),
        "tune_against_the_runner_up_harmony": tune_vs(RUNNER),
        "note": "voice against tune: shares of the voiced sung time (note mode). tune against chords: share of the tune's own sounding time; "
                "clash = a semitone from a chord tone or a tritone from the root."},
    "one_semitone_from_a_sounding_note": {
        "none (chords, bass, drums only) - chosen harmony": exposure(),
        "none - runner-up harmony": exposure(bars=RUNNER),
        "none - chosen harmony with the seventh in the band on all of bars 2 and 6": exposure(bars=B7),
        "soft pad: root + fifth of every chord - chosen harmony": exposure(pad(BEST, "root_fifth")),
        "soft pad: full triads - chosen harmony": exposure(pad(BEST, "triad")),
        "soft pad: full chords with the seventh on the dominant": exposure(pad(B7, "chord"), bars=B7),
        "none - plain baseline harmony": exposure(bars=PLAIN),
        "frame mode: none - chosen harmony": exposure(mode="frame"),
        "frame mode: soft pad: full triads - chosen harmony": exposure(pad(BEST, "triad"), mode="frame"),
        "note": "band model (note-on .. note-off + 30 ms) plus, for the pad rows, the pad's pitch classes held through every sung beat; "
                "shares of the voiced sung time, note mode unless marked"}}
print("UNDER-VOCAL: voice vs tune:", alt["tune_under_the_voice"]["share_of_sung_time_by_interval_between_voice_and_tune"])
print("   different note %.1f %%, a second/seventh apart %.1f %% (runs > 150 ms: %.1f %%, %d runs), second in the same octave %.1f %%" % (
    100 * alt["tune_under_the_voice"]["different_note_than_the_voice"], 100 * np.mean(second), 100 * np.mean(sus2), len(runs2), 100 * np.mean(close2)))
print("   tune vs plain harmony", alt["tune_under_the_voice"]["tune_against_the_plain_harmony"], "| vs chosen", alt["tune_under_the_voice"]["tune_against_the_chosen_harmony"],
      "| vs runner-up", alt["tune_under_the_voice"]["tune_against_the_runner_up_harmony"])
for k, v in alt["one_semitone_from_a_sounding_note"].items():
    if isinstance(v, dict):
        print("   %-75s %5.1f %%  (in runs > 150 ms %4.1f %%)" % (k, 100 * v["one_semitone_from_a_sounding_note"], 100 * v["in_runs_over_150ms"]))

# optional voicing refinements, band model (the rendered-audio numbers are in ses_olcumu.json)
refine = {}
for nm_, rb, o3 in (("as planned", (), ()), ("bass on the root on beat 2 of bars 2 and 6", (2, 6), ()),
                    ("on-beat strum of beat 3 without the third in bars 0 and 5", (), (0, 5)), ("both", (2, 6), (0, 5))):
    refine[nm_] = {"note": phys(bandC, BEST, root_bass_bars=rb, open3_bars=o3), "frame": phys(bandC, BEST, mode="frame", root_bass_bars=rb, open3_bars=o3)}

save_json(os.path.join(T, "olcum.json"), {
    "about": "Chord-fit measurements of the unprocessed sung melody of v2_2 for harmony designer B ('serbest': I ii iii IV V V7 vi, keys C F G). "
             "All shares are fractions of the voiced sung time (%.2f s = %d frames of 5 ms in the kept syllables of 7 verses), evaluated at "
             "each frame's own time in the new song form (placement shifts of kesim.json, no time-stretch)." % (F.total_s, F.n),
    "metric_definitions": {
        "chord_tone": "sung pitch class is a chord tone of the chord on that beat",
        "scale_non_chord": "in the key's scale but not a chord tone",
        "outside_scale": "not in the key's scale (and not a chord tone); chord_tone + scale_non_chord + outside_scale = 1",
        "clash_any": "not a chord tone AND (a semitone above or below a chord tone OR a tritone from the chord root)",
        "clash_sustained": "the part of clash_any inside a clash run longer than 150 ms; a run survives up to 60 ms without sung pitch "
                           "(a consonant) and up to 15 ms of non-clash frames; run length = last - first frame + 5 ms",
        "clash_sustained_strict": "same without any bridging (consecutive 5 ms frames only)",
        "consonant_non_chord": "scale_non_chord that is not a clash",
        "on_beat_chord_tone": "chord-tone share of the syllables that start ON a beat (the metrically strong notes)",
        "off_beat_chord_tone": "chord-tone share of the syllables on half beats and sixteenths",
        "line_end_chord_tone": "chord-tone share of the last syllable of each line (the note the phrase rests on)",
        "sounding_semitone": "PHYSICAL, from the band model (bant.py; its I / IV / V7 part is checked note for note against midi/altyapi_C.mid, the "
                             "ii / iii / vi / V voicings are proposals of designer B): share of the sung time during which a band note one semitone "
                             "away in pitch class is really sounding (note-on .. note-off + 30 ms)",
        "sounding_semitone_sustained": "the part of sounding_semitone in runs longer than 150 ms",
        "semitone_same_octave": "the same for a band note exactly one semitone above or below the sung note (same octave)",
        "whole_tone_same_octave": "band model: a band note exactly two semitones above or below the sung note is sounding (a major second against the voice)",
        "band_same_pitch_class": "band model: a band note of the sung pitch class is sounding (the voice is doubled by the band)",
        "band_unison": "band model: a band note of exactly the sung pitch is sounding",
        "J": "ranking score = chord_tone - 2 * (clash_sustained + outside_scale) (the same score designer A uses)",
        "V_and_V7": "V = the dominant triad (the band plays no seventh; a sung F is then a non-chord tone that rubs nothing), "
                    "V7 = with the seventh (a sung F is a chord tone, a sung E lies a semitone below it)",
        "readings": "'note' (primary): a frame carries the pitch class of the note it belongs to (kesim.json syllable.notes; scoops and glides count "
                    "with their note). 'frame': every 5 ms frame is rounded on its own. 'dio': the same with a second pitch tracker. "
                    "'chords_40ms_early': note mode with all chord changes 40 ms earlier."},
    "rule_sets": {"strict": "G1-G4 of kod/kurallar.py (the dominant only goes to the tonic)",
                  "turnaround": "the same, but the plain V may step down to IV when that IV goes straight to I (V - IV - I)",
                  "any sequence": "no rule at all (only to show what the rules cost)"},
    "plans": plans,
    "reference_original_d_minor_loop": ref,
    "best_per_key_from_the_search": SCAN["best_per_key"],
    "key_ranking_weight_robustness": {"about": "score and bars of the best plan per key for weights w = 1, 2, 4 in J = chord_tone - w * (clash_sustained + outside_scale)",
                                      **SCAN["weight_robustness"]},
    "bar_0_verse_opening": {"about": "frames of line 1 only; band_model_beats_0_1 = what sounds against the voice up to beat 1.95 ('Ali Baba'nin')",
                            "candidates": bar0, "gliding_syllable_li": glide},
    "stage_2_seventh_of_the_dominant": {"about": "bars 2 (L2) and 6 (L4): the dominant with or without its seventh, measured on the frames of that line; "
                                                 "the other bars as in the chosen plan. beat_3_only = the frames of beat 3 of that bar.", **stage2},
    "robustness_of_the_choice": rob,
    "bar_2_per_verse": {"about": "do the animal words need different chords? Best sequence inside the strict rules for each verse alone, and the chosen bar per verse", "verses": per_verse_L2},
    "under_vocal": alt,
    "optional_voicing_refinements_band_model": {"about": "chosen plan; what sounds against the voice with two optional changes of the strum pattern (rendered-audio numbers: ses_olcumu.json)", **refine},
})
print("written: olcum.json (%.0f s)" % (time.time() - t0))
