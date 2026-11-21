#!/usr/bin/env python3
"""Step 7: independent verification of plan.json. Writes dogrulama.txt; exits with status 1 if a check fails.

Nothing from olcut.py (the metric code) is imported here: the numbers are recomputed with separate, literal code.
  A. exact recomputation from the frame table: chord tone / non-chord / outside / clash / sustained clash for the chosen
     plan (as played and read as V7) and for the plain baseline; chords written out as note names.
  B. a second data route that does not use the frame table at all: the syllable notes of kesim.json, weighted by
     note duration x voiced ratio of the syllable (approximate by construction; must agree within 3 points).
  C. the plan itself: chord set, shape, bar 6 ending, band notes (no F in the band in bars 2 and 6, F kept in the answers).
  D. semitone coincidences recomputed from the MIDI file that was rendered for the audio check (not from the band model).
  E. the fixed form: every sung frame of a line lies in its own bar of the new form.
"""
import sys, os, json
import numpy as np, mido

T = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.dirname(os.path.dirname(os.path.dirname(T)))
plan = json.load(open(os.path.join(T, "plan.json"), encoding="utf8"))
kes = json.load(open(os.path.join(A, "yeni4", "analiz", "kesim", "kesim.json"), encoding="utf8"))
z = np.load(os.path.join(T, "ara", "kareler.npz"))
BEAT = 60.0 / 105.0; FP = 0.005
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
pc_of = {n: i for i, n in enumerate(NAMES)}
CHORD = {"C": "C E G", "F": "F A C", "G": "G B D", "G7": "G B D F"}
CHORD = {k: {pc_of[x] for x in v.split()} for k, v in CHORD.items()}
ROOT = {"C": 0, "F": 5, "G": 7, "G7": 7}
SCALE = {pc_of[x] for x in "C D E F G A B".split()}
out = []; fails = 0


def check(ok, text):
    global fails
    fails += (not ok)
    out.append(("PASS  " if ok else "FAIL  ") + text)


def verse_chords(bars0, bars2, bars5, bars6):
    """32 chord names of a verse; fixed bars: 1 and 7 = C G7 C C, 3 and 4 = C"""
    v = [None] * 32
    v[0:4] = bars0; v[4:8] = ["C", "G7", "C", "C"]; v[8:12] = bars2; v[12:20] = ["C"] * 8
    v[20:24] = bars5; v[24:28] = bars6; v[28:32] = ["C", "G7", "C", "C"]
    return v


def is_clash(p, ch):
    if p in CHORD[ch]:
        return False
    return any((p - t) % 12 in (1, 11) for t in CHORD[ch]) or (p - ROOT[ch]) % 12 == 6


# ---- A. exact recomputation -------------------------------------------------------------------------------------------
order = np.lexsort((z["t_src"], z["verse"]))
verse = z["verse"][order]; pos = z["pos"][order]; tnew = z["t_new"][order]
pcn = (np.round(z["note_midi"][order]).astype(int)) % 12


def measure(chords):
    n = len(pos); ct = nc = ou = cl = 0
    flag = []
    for k in range(n):
        b = int(np.floor(pos[k] + 1e-9))
        ch = "C" if b < 0 else chords[b]
        p = int(pcn[k])
        if p in CHORD[ch]:
            ct += 1
        elif p in SCALE:
            nc += 1
        else:
            ou += 1
        c = is_clash(p, ch); cl += c; flag.append(c)
    # sustained clash: runs longer than 150 ms; bridge <= 60 ms without sung pitch and <= 3 non-clash frames
    sus = 0; runs = 0; i = 0; idx = [k for k in range(n) if flag[k]]
    start = 0
    for j in range(1, len(idx) + 1):
        brk = True
        if j < len(idx):
            a, b = idx[j - 1], idx[j]
            brk = not (verse[a] == verse[b] and tnew[b] - tnew[a] <= 0.060 + FP + 1e-9 and b - a - 1 <= 3)
        if brk:
            if tnew[idx[j - 1]] - tnew[idx[start]] + FP > 0.150 + 1e-9:
                sus += j - start; runs += 1
            start = j
    return {"chord_tone": ct / n, "scale_non_chord": nc / n, "outside_scale": ou / n, "clash_any": cl / n, "clash_sustained": sus / n,
            "sustained_clash_runs": runs}


M = plan["metrics"]
hp = plan["harmony_plan"]
played = hp["band_plays_per_beat"]; sym = hp["chord_names_per_beat"]
cases = {
    "chosen plan as played": (verse_chords(played["bar_0_L1"], played["bar_2_L2"], played["bar_5_diye_bagirir"], played["bar_6_L4"]),
                              M["chosen_plan_as_the_band_plays_it"]["all_sung_frames"]),
    "chosen plan read as V7": (verse_chords(sym["bar_0_L1"], sym["bar_2_L2"], sym["bar_5_diye_bagirir"], sym["bar_6_L4"]),
                               [v for k, v in M.items() if k.startswith("chosen_plan_read_as_V7")][0]["all_sung_frames"]),
    "plain baseline C": (verse_chords(["C", "C", "F", "C"], ["C", "C", "F", "C"], ["C"] * 4, ["C", "C", "F", "C"]),
                         [v for k, v in M.items() if k.startswith("plain_baseline_C")][0]["all_sung_frames"]),
}
out.append("A. exact recomputation from the frame table (%d frames = %.2f s)" % (len(pos), len(pos) * FP))
for name, (chords, ref) in cases.items():
    m = measure(chords)
    worst = max(abs(m[k] - ref[k]) for k in ("chord_tone", "scale_non_chord", "outside_scale", "clash_any", "clash_sustained"))
    check(worst < 2e-4 and m["sustained_clash_runs"] == ref["sustained_clash_runs"],
          "%-24s chord tone %.4f, non-chord %.4f, outside %.4f, clash any %.4f, sustained %.4f (%d runs)  | plan.json differs by at most %.5f" % (
              name, m["chord_tone"], m["scale_non_chord"], m["outside_scale"], m["clash_any"], m["clash_sustained"], m["sustained_clash_runs"], worst))
    check(abs(m["chord_tone"] + m["scale_non_chord"] + m["outside_scale"] - 1) < 1e-9, "%-24s the three exclusive shares sum to 1" % name)

# ---- B. second route: syllable notes of kesim.json, no frame table -----------------------------------------------------
LEAD = 0.100; BAR = 4 * BEAT
LINE_BAR = {"L1": 0, "L2": 2, "diye": 5, "L4": 6}


def route_b(chords):
    w_ct = w_cl = w_all = 0.0
    for v, V in enumerate(kes["verses"]):
        piece_of = {seg: P for P in V["pieces"] for seg in P["segments"]}
        v0 = LEAD + (4 + 8 * v) * BAR
        for L in V["lines"]:
            sh = piece_of[L["name"]]["placement"]["shift_s"]
            for S in L["syllables"]:
                if not S["kept"] or S["excise"] or S["f0_midi"] is None:
                    continue
                for N in S["notes"]:
                    a = (N["start"] + sh - v0) / BEAT; b = (N["end"] + sh - v0) / BEAT
                    p = int(round(N["midi"])) % 12
                    x = a
                    while x < b - 1e-9:                         # split the note at the beat boundaries
                        y = min(np.floor(x + 1e-9) + 1, b)
                        bi = int(np.floor(x + 1e-9)); ch = "C" if bi < 0 else chords[bi]
                        w = (y - x) * S["voiced_ratio"]
                        w_all += w; w_ct += w * (p in CHORD[ch]); w_cl += w * is_clash(p, ch)
                        x = y
    return w_ct / w_all, w_cl / w_all


out.append("B. second route: syllable notes of kesim.json weighted by duration x voiced ratio (approximate; tolerance 3 points)")
for name, (chords, ref) in cases.items():
    ct, cl = route_b(chords)
    check(abs(ct - ref["chord_tone"]) < 0.03 and abs(cl - ref["clash_any"]) < 0.03,
          "%-24s chord tone %.3f (plan.json %.3f), clash any %.3f (plan.json %.3f)" % (name, ct, ref["chord_tone"], cl, ref["clash_any"]))
ctc, _ = route_b(cases["chosen plan as played"][0]); ctb, _ = route_b(cases["plain baseline C"][0])
check(ctc > ctb, "second route also ranks the chosen plan above the baseline in chord-tone share (%.3f > %.3f)" % (ctc, ctb))

# ---- C. the plan itself ----------------------------------------------------------------------------------------------
out.append("C. the plan")
deg = hp["degrees_per_beat"]
check(plan["key"] == "C major", "key is C major")
check(all(c in ("I", "IV", "V7") for v in deg.values() for c in v), "only I, IV and V7 are used as chord symbols: %s" % {k: " ".join(v) for k, v in deg.items()})
check(all(len(v) == 4 for v in deg.values()) and set(deg) == {"bar_0_L1", "bar_2_L2", "bar_5_diye_bagirir", "bar_6_L4"}, "four vocal bars, four beats each")
check(deg["bar_6_L4"][-1] in ("V7", "I"), "bar 6 ends on %s, so the loud answer of bar 7 arrives on I" % deg["bar_6_L4"][-1])
check(deg["bar_0_L1"][0] == "I", "the verse opens on I")
check(deg["bar_5_diye_bagirir"][:2] == ["I", "I"], "bar 5 beats 0-1 stay on I (drum fill)")
seq = deg["bar_0_L1"] + ["I", "V7", "I", "I"] + deg["bar_2_L2"] + ["I"] * 8 + deg["bar_5_diye_bagirir"] + deg["bar_6_L4"] + ["I", "V7", "I", "I"] + ["I"]
check(not any(a == "V7" and b == "IV" for a, b in zip(seq[:-1], seq[1:])), "the dominant never moves to IV anywhere in the verse")
nm = {"I": "C", "IV": "F", "V7": "G7"}
check(all([nm[c] for c in deg[k]] == sym[k] for k in deg), "chord names match the degrees in C")
check(all([("G" if c == "G7" else c) for c in sym[k]] == played[k] for k in ("bar_2_L2", "bar_6_L4")) and played["bar_0_L1"] == sym["bar_0_L1"],
      "band_plays_per_beat = the same chords with the dominant as a plain triad in bars 2 and 6")
nb = plan["notes_for_the_builder_key_C"]
vnotes = " ".join([nb["V_under_the_vocal_bars_2_and_6"][k] for k in ("banjo_chord", "piano_accordion_chord", "banjo_roll_8_eighths", "bass_root", "bass_fifth")])
check("F" not in {x[:-1] for x in vnotes.split()}, "the dominant under the vocal contains no F: %s" % vnotes)
check({x[:-1] for x in vnotes.split()} == {"G", "B", "D"}, "it contains exactly the pitch classes G, B, D")
check("F3" in nb["V7_answers_intro_ending_unchanged"]["banjo_chord"], "the V7 of the answers keeps its seventh")
check(plan["under_vocal_policy"]["policy"] == "none", "under-vocal policy: none")
check(plan["harmony_plan"]["same_plan_for_all_7_verses"] is True and
      all(v["clash_sustained"] == 0 for v in M["chosen_plan_as_the_band_plays_it"]["L2_per_verse"]),
      "one plan for all verses: line 2 (animal word) has no sustained clash in any of the 7 verses")

# ---- D. semitone coincidences from the rendered MIDI -------------------------------------------------------------------
out.append("D. semitone coincidences recomputed from the MIDI rendered for the audio check")
mp = os.path.join(T, "ara", "ses", "Ay_V-V-V-V_SECILEN.mid")
if os.path.exists(mp):
    mid = mido.MidiFile(mp); tk = 0; on = {}; notes = []
    for msg in mid.tracks[0]:
        tk += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            on.setdefault((msg.channel, msg.note), []).append(tk)
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            st = on.get((msg.channel, msg.note))
            if st:
                notes.append((st.pop(0) / mid.ticks_per_beat - 1.0, tk / mid.ticks_per_beat - 1.0, msg.note))   # -1: pre-roll beat
    # time 0 of the MIDI (after the pre-roll) = downbeat of the answer bar before the verse  ->  verse position = beat - 4
    hit = 0
    for k in range(len(pos)):
        b = pos[k] + 4.0; p = int(pcn[k])
        hit += any(a <= b < e + 0.030 / BEAT and (n - p) % 12 in (1, 11) for (a, e, n) in notes)
    share = hit / len(pos); ref = M["chosen_plan_as_the_band_plays_it"]["all_sung_frames"]["sounding_semitone"]
    check(abs(share - ref) < 0.01, "share of the sung time one semitone from a sounding band note: %.4f from the MIDI (%d notes), %.4f in plan.json" % (share, len(notes), ref))
    check(not any(n % 12 == 5 for (a, e, n) in notes if 12 <= a < 16 or 28 <= a < 32), "the rendered MIDI has no F in verse bars 2 and 6")
    check(any(n % 12 == 5 for (a, e, n) in notes if 8 <= a < 12), "the rendered MIDI keeps the F of V7 in the answer bar")
else:
    check(False, "ara/ses/Ay_V-V-V-V_SECILEN.mid is missing (run 04_ses_olcumu.py first)")

# ---- E. the form ---------------------------------------------------------------------------------------------------------
out.append("E. the form")
line = z["line"][order]
rng = {0: (-0.1, 4.0), 1: (8.0, 12.0), 2: (22.0, 24.0), 3: (24.0, 28.0)}
okf = all(((pos[line == li] >= a) & (pos[line == li] < b)).all() for li, (a, b) in rng.items())
check(okf, "every sung frame lies in its own bar: L1 %.2f..%.2f, L2 %.2f..%.2f, diye %.2f..%.2f, L4 %.2f..%.2f beats from the verse downbeat" % (
    pos[line == 0].min(), pos[line == 0].max(), pos[line == 1].min(), pos[line == 1].max(), pos[line == 2].min(), pos[line == 2].max(),
    pos[line == 3].min(), pos[line == 3].max()))
check(abs(len(pos) * FP - 44.85) < 0.01, "voiced sung time %.2f s" % (len(pos) * FP))

out.append("")
out.append("%d checks, %d failed.  Nothing was listened to; these checks concern numbers and structure only." % (sum(1 for o in out if o.startswith(("PASS", "FAIL"))), fails))
txt = "\n".join(out)
open(os.path.join(T, "dogrulama.txt"), "w", encoding="utf8").write(txt + "\n")
print(txt)
sys.exit(1 if fails else 0)
