#!/usr/bin/env python3
"""Step 7: verification of plan.json by routes that do not use the code that produced it. Writes dogrulama.txt.

  R1  PLACED VOCAL. yeni4/vokal/vokal_dogal.wav (the stem already cut and placed on the new form) is pitch-tracked on
      its own; every gated frame gets its bar and beat from its TIME alone (0.100 s lead-in, 105 BPM), the chord from a
      plain table, the category from a few lines of code written here. This uses neither kesim.json's placement
      shifts, nor the frame table, nor olcut.py. Compared with the frame-mode numbers of plan.json.
  R2  NAIVE RECOUNT on the frame table, note mode: loops instead of the vectorised code of olcut.py (own run
      detection). Must reproduce plan.json to four decimals.
  R3  DESIGNER A. For the plans both designers measured (plain baselines, original loop, A's own plan) the numbers
      of tasarim/A/olcum.json must be the same.
  R4  CONSISTENCY of plan.json itself (chord names, sums, the rules, the fixed bars).
"""
import sys, os, json
import numpy as np, soundfile as sf, pyworld as pw
from scipy.signal import butter, sosfiltfilt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import T, A, ARA, KESIM, VOKAL_DOGAL, A_OLCUM, KARELER, load_json

OUT = []
FAIL = [0]


def say(s=""):
    OUT.append(s); print(s)


def check(ok, text):
    if not ok:
        FAIL[0] += 1
    say("  %s  %s" % ("PASS" if ok else "FAIL", text))


PLAN = load_json(os.path.join(T, "plan.json"))
OLC = load_json(os.path.join(T, "olcum.json"))
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
TRIADS = {"C": (0, 4, 7), "Dm": (2, 5, 9), "Em": (4, 7, 11), "F": (5, 9, 0), "G": (7, 11, 2), "G7": (7, 11, 2, 5), "Am": (9, 0, 4),
          "Gm": (7, 10, 2), "A": (9, 1, 4)}
ROOTS = {"C": 0, "Dm": 2, "Em": 4, "F": 5, "G": 7, "G7": 7, "Am": 9, "Gm": 7, "A": 9}
C_SCALE = {0, 2, 4, 5, 7, 9, 11}
DM_SCALE = {2, 4, 5, 7, 9, 10, 0, 1}
BEAT = 60.0 / 105.0


def verse_chords(b0, b2, b5, b6):
    """32 chord names of one verse from the four sung bars (bar 5: all four beats)"""
    return b0 + ["C", "G7", "C", "C"] + b2 + ["C"] * 8 + b5 + b6 + ["C", "G7", "C", "C"]


PL = PLAN["harmony_plan"]["chord_names_per_beat"]; RU = PLAN["runner_up"]["chord_names_per_beat"]
TABLES = {
    "chosen": (verse_chords(PL["bar_0_L1"], PL["bar_2_L2"], PL["bar_5_diye_bagirir"], PL["bar_6_L4"]), C_SCALE, "C"),
    "runner_up": (verse_chords(RU["bar_0_L1"], RU["bar_2_L2"], RU["bar_5_diye_bagirir"], RU["bar_6_L4"]), C_SCALE, "C"),
    "baseline": (verse_chords(["C", "C", "F", "C"], ["C", "C", "F", "C"], ["C"] * 4, ["C", "C", "F", "C"]), C_SCALE, "C"),
    "original": (["Dm", "Dm", "C", "C"] + ["C"] * 4 + ["Gm", "Gm", "A", "A"] + ["Dm"] * 8 + ["Dm", "Dm", "C", "C"] + ["Gm", "Gm", "A", "A"] + ["Dm"] * 4, DM_SCALE, "A"),
}


def category(pc, chord, scale):
    tones = TRIADS[chord]
    if pc in tones:
        return "ct", False
    clash = any((pc - t) % 12 in (1, 11) for t in tones) or (pc - ROOTS[chord]) % 12 == 6
    return ("non" if pc in scale else "out"), clash


def count(pcs, beats, times, verses, table, scale, pre):
    """naive duration-weighted recount -> dict; runs: bridged rule (gap <= 60 ms without pitch, <= 3 non-clash frames)"""
    n = len(pcs); ct = non = out = cl = 0
    flags = []
    for pc, b in zip(pcs, beats):
        chord = pre if b < 0 else table[b]
        c, clash = category(int(pc), chord, scale)
        ct += c == "ct"; non += c == "non"; out += c == "out"; cl += clash
        flags.append(clash)
    sus = 0; strict = 0; i = 0; nruns = 0
    idx = [k for k, f in enumerate(flags) if f]
    j = 0
    while j < len(idx):
        k = j
        while k + 1 < len(idx) and verses[idx[k + 1]] == verses[idx[k]] and times[idx[k + 1]] - times[idx[k]] <= 0.065 + 1e-9 and idx[k + 1] - idx[k] - 1 <= 3:
            k += 1
        if times[idx[k]] - times[idx[j]] + 0.005 > 0.150 + 1e-9:
            sus += k - j + 1; nruns += 1
        j = k + 1
    j = 0
    while j < len(idx):
        k = j
        while k + 1 < len(idx) and idx[k + 1] == idx[k] + 1 and verses[idx[k + 1]] == verses[idx[k]] and times[idx[k + 1]] - times[idx[k]] <= 0.005 + 1e-6:
            k += 1
        if (k - j + 1) * 0.005 > 0.150 + 1e-9:
            strict += k - j + 1
        j = k + 1
    return {"chord_tone": ct / n, "scale_non_chord": non / n, "outside_scale": out / n, "clash_any": cl / n, "clash_sustained": sus / n,
            "clash_sustained_strict": strict / n, "sustained_clash_runs": nruns, "voiced_s": n * 0.005}


# ======================================================================================================================
say("R1  placed vocal (vokal_dogal.wav), frame mode, position from time alone")
if os.path.exists(VOKAL_DOGAL):
    K = load_json(KESIM)
    Y = load_json(os.path.join(A, "yeni4", "vokal", "yerlesim.json"))
    gain = Y["audio"]["global_gain_db"]
    x, fs = sf.read(VOKAL_DOGAL); x = x.astype(np.float64)
    f0, t = pw.harvest(x, fs, f0_floor=150.0, f0_ceil=700.0, frame_period=5.0)
    sos = butter(4, [100, 1000], btype="band", fs=fs, output="sos")
    y = sosfiltfilt(sos, x)
    nwin = int(8 / 1000 * fs) | 1
    h = np.hanning(nwin + 2)[1:-1]; h /= h.sum()
    env = 10 * np.log10(np.convolve(y ** 2, h, "same")[np.minimum((t * fs).astype(int), len(x) - 1)] + 1e-12)
    gate = (f0 > 0) & (env > K["levels"]["sung_rms_dbfs"] + gain - 11.0)
    tt = t[gate]; midi = 69 + 12 * np.log2(f0[gate] / 440.0)
    song_beat = (tt - 0.100) / BEAT
    verse = np.floor((song_beat - 16) / 32 + 1e-9).astype(int)
    vb = song_beat - 16 - 32 * verse
    # a frame just before a verse downbeat belongs to the NEXT verse (beat -1 = the I of the previous answer)
    late = vb > 31.5
    verse = np.where(late, verse + 1, verse); vb = np.where(late, vb - 32, vb)
    beat = np.floor(vb + 1e-9).astype(int)
    sung_beats = (beat < 4) | ((beat >= 8) & (beat < 12)) | ((beat >= 22) & (beat < 28))
    say("  gated frames: %d = %.2f s (frame table: %.2f s); in verses %d..%d; frames outside the sung bars: %d" % (
        len(tt), len(tt) * 0.005, PLAN["metrics"]["chosen_plan"]["all_sung_frames"].get("voiced_s", OLC["plans"]["C BEST"]["note_voiced_s"]),
        verse.min() + 1, verse.max() + 1, int((~sung_beats).sum())))
    check(verse.min() == 0 and verse.max() == 6 and (~sung_beats).sum() == 0, "every gated frame of the placed vocal lies in a sung bar of verses 1-7")
    pcs = np.round(midi).astype(int) % 12
    order = np.lexsort((tt, verse))
    ref = {"chosen": OLC["plans"]["C BEST"]["frame"], "runner_up": OLC["plans"]["C RUNNER_UP"]["frame"], "baseline": OLC["plans"]["C plain baseline"]["frame"],
           "original": OLC["reference_original_d_minor_loop"]["frame"]}
    for name, (table, scale, pre) in TABLES.items():
        d = count(pcs[order], beat[order], tt[order], verse[order], table, scale, pre)
        r_ = ref[name]
        worst = max(abs(d[k] - r_[k]) for k in ("chord_tone", "outside_scale", "clash_any", "clash_sustained"))
        say("    %-10s placed file: ct %.4f out %.4f clash any %.4f sus %.4f | olcum.json frame mode: ct %.4f out %.4f clash any %.4f sus %.4f | largest difference %.4f" % (
            name, d["chord_tone"], d["outside_scale"], d["clash_any"], d["clash_sustained"], r_["chord_tone"], r_["outside_scale"], r_["clash_any"], r_["clash_sustained"], worst))
        check(worst < 0.012, "%s: the placed vocal gives the frame-mode numbers within 1.2 points" % name)
    pf = PLAN["metrics"]["chosen_plan"]["frame_mode"]
    check(all(abs(pf[k] - ref["chosen"][k]) < 1e-9 for k in ("chord_tone", "clash_sustained", "outside_scale")), "plan.json frame_mode block = olcum.json")
else:
    say("  SKIPPED: vokal_dogal.wav does not exist")

# ======================================================================================================================
say("R2  naive recount on the frame table, note mode")
z = np.load(KARELER)
o = np.lexsort((z["t_src"], z["verse"]))
pcs = np.round(z["note_midi"][o]).astype(int) % 12
beat = np.floor(z["pos"][o] + 1e-9).astype(int)
tt = z["t_new"][o]; vv = z["verse"][o]
slot = z["slot"][o]; last = z["last"][o]
onb = np.abs(slot - np.round(slot)) < 1e-6
refn = {"chosen": PLAN["metrics"]["chosen_plan"]["all_sung_frames"], "runner_up": PLAN["runner_up"]["metrics"]["all_sung_frames"],
        "baseline": PLAN["metrics"]["plain_baseline_C (I I IV I | I I IV I | I I | I I IV I)"]["all_sung_frames"],
        "original": PLAN["metrics"]["original_d_minor_loop_reference (Dm Dm C C | Gm Gm A A | C C | Gm Gm A A)"]["all_sung_frames"]}
for name, (table, scale, pre) in TABLES.items():
    d = count(pcs, beat, tt, vv, table, scale, pre)
    isct = np.array([int(p) in TRIADS[pre if b < 0 else table[b]] for p, b in zip(pcs, beat)])
    d["on_beat_chord_tone"] = isct[onb].mean(); d["line_end_chord_tone"] = isct[last].mean()
    r_ = refn[name]
    keys = ("chord_tone", "scale_non_chord", "outside_scale", "clash_any", "clash_sustained", "clash_sustained_strict", "on_beat_chord_tone", "line_end_chord_tone")
    worst = max(abs(d[k] - r_[k]) for k in keys)
    say("    %-10s recount: ct %.4f non %.4f out %.4f clash any %.4f sus %.4f (%d runs) on-beat %.4f end %.4f | largest difference to plan.json %.5f" % (
        name, d["chord_tone"], d["scale_non_chord"], d["outside_scale"], d["clash_any"], d["clash_sustained"], d["sustained_clash_runs"],
        d["on_beat_chord_tone"], d["line_end_chord_tone"], worst))
    check(worst < 6e-5 and d["sustained_clash_runs"] == r_["sustained_clash_runs"], "%s: plan.json reproduced by the naive recount" % name)
J = lambda e: e["chord_tone"] - 2 * (e["clash_sustained"] + e["outside_scale"])
check(abs(J(refn["chosen"]) - refn["chosen"]["J"]) < 1e-3, "J of the chosen plan = chord_tone - 2 (clash_sustained + outside_scale)")

# ======================================================================================================================
say("R3  the same plans as measured by designer A (tasarim/A/olcum.json)")
if os.path.exists(A_OLCUM):
    AO = load_json(A_OLCUM)
    pairs = [("C plain baseline", AO["plans"]["C plain baseline"]["note"], OLC["plans"]["C plain baseline"]["note"]),
             ("F plain baseline", AO["plans"]["F plain baseline"]["note"], OLC["plans"]["F plain baseline"]["note"]),
             ("G plain baseline", AO["plans"]["G plain baseline"]["note"], OLC["plans"]["G plain baseline"]["note"]),
             ("original D minor loop", AO["reference_original_d_minor_loop"]["note"], OLC["reference_original_d_minor_loop"]["note"])]
    ka = [k for k in AO["plans"] if "A* " in k]
    if ka:
        pairs.append(("designer A's plan (I IV I I | V V V V | I I | V V V V)", AO["plans"][ka[0]]["note"], OLC["plans"]["C designer_A"]["note"]))
    ke = [k for k in AO["plans"] if "E* " in k]
    if ke:
        pairs.append(("V IV I I | V V V V | I I | V V V V (A's alternative E* = B's runner-up)", AO["plans"][ke[0]]["note"], OLC["plans"]["C RUNNER_UP"]["note"]))
    for name, a, b in pairs:
        keys = ("chord_tone", "scale_non_chord", "outside_scale", "clash_any", "clash_sustained", "clash_sustained_strict", "sounding_semitone", "sounding_semitone_sustained")
        keys = [k for k in keys if k in a and k in b]
        worst = max(abs(a[k] - b[k]) for k in keys)
        check(worst < 6e-5 and a["sustained_clash_runs"] == b["sustained_clash_runs"],
              "%s: %d shared numbers agree (largest difference %.5f)" % (name, len(keys) + 1, worst))
else:
    say("  SKIPPED: tasarim/A/olcum.json does not exist")

# ======================================================================================================================
say("R4  consistency of plan.json")
DEG2NAME = {"I": "C", "ii": "Dm", "iii": "Em", "IV": "F", "V": "G", "V7": "G7", "vi": "Am"}
for who, blk in (("chosen", PLAN["harmony_plan"]), ("runner-up", PLAN["runner_up"])):
    ok = all([DEG2NAME[d] for d in blk["degrees_per_beat"][b]] == blk["chord_names_per_beat"][b] for b in blk["degrees_per_beat"])
    check(ok, "%s: chord names match the degrees in C major" % who)
    wv = blk["whole_verse_per_beat"]
    check(len(wv) == 8 and all(len(wv["bar_%d" % i]["degrees"]) == 4 for i in range(8)), "%s: the verse has 8 bars of 4 beats" % who)
    check(wv["bar_1"]["degrees"] == ["I", "V7", "I", "I"] and wv["bar_7"]["degrees"] == ["I", "V7", "I", "I"]
          and wv["bar_3"]["degrees"] == ["I"] * 4 and wv["bar_4"]["degrees"] == ["I"] * 4 and wv["bar_5"]["degrees"][:2] == ["I", "I"],
          "%s: the fixed bars (answers I V7 I I, animal calls I, drum fill I) are untouched" % who)
    check(wv["bar_6"]["degrees"][-1] in ("V", "V7", "I"), "%s: bar 6 ends on V, V7 or I" % who)
    seq = [d for i in range(8) for d in wv["bar_%d" % i]["degrees"]]
    ch = sum(1 for i in (0, 2, 5, 6) for a, b in zip(wv["bar_%d" % i]["degrees"][:-1], wv["bar_%d" % i]["degrees"][1:]) if a != b)
    say("    %s: chord changes inside the sung bars: %d; beats on I / V / V7: %d of 32" % (who, ch, sum(1 for d in seq if d in ("I", "V", "V7"))))
from kurallar import rules
hp = PLAN["harmony_plan"]["degrees_per_beat"]; rp = PLAN["runner_up"]["degrees_per_beat"]
check(all(all(rules(b, hp[k] if b != 5 else hp[k][2:]).values()) for b, k in ((0, "bar_0_L1"), (2, "bar_2_L2"), (5, "bar_5_diye_bagirir"), (6, "bar_6_L4"))),
      "chosen plan passes the strict progression rules G1-G4")
check(not all(rules(0, rp["bar_0_L1"]).values()) and all(rules(0, rp["bar_0_L1"], turnaround=True).values()),
      "runner-up: bar 0 fails the strict rule G3 and passes the turnaround rule set")
for who, e in (("chosen", PLAN["metrics"]["chosen_plan"]["all_sung_frames"]), ("runner-up", PLAN["runner_up"]["metrics"]["all_sung_frames"])):
    check(abs(e["chord_tone"] + e["scale_non_chord"] + e["outside_scale"] - 1) < 2e-4, "%s: chord_tone + scale_non_chord + outside_scale = 1" % who)
check(PLAN["under_vocal_policy"]["policy"] == "none", "under-vocal policy is 'none'")
scan = load_json(os.path.join(ARA, "tarama.json"))
check(scan["best_per_key"]["C"]["rules"]["bars"]["0"] == hp["bar_0_L1"] and scan["best_per_key"]["C"]["turnaround"]["bars"]["0"] == rp["bar_0_L1"],
      "bar 0 of the chosen plan / runner-up = the search result of the strict / turnaround rule set")
check(all(set(scan["best_per_key"]["C"]["rules"]["bars"][b]) <= {"V", "V7"} for b in ("2", "6")) and scan["best_per_key"]["C"]["rules"]["bars"]["5"] == ["I", "I"],
      "bars 2 and 6 of the search result are the dominant on all four beats, bar 5 is I I")

say()
say("RESULT: %s" % ("all checks passed" if FAIL[0] == 0 else "%d CHECK(S) FAILED" % FAIL[0]))
say("Nothing was listened to: these checks verify the arithmetic and the bookkeeping, not how the harmony sounds.")
with open(os.path.join(T, "dogrulama.txt"), "w", encoding="utf8") as f:
    f.write("\n".join(OUT) + "\n")
sys.exit(1 if FAIL[0] else 0)
