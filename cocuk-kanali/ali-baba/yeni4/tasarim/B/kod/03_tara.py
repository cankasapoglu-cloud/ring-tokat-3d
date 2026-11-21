#!/usr/bin/env python3
"""Step 3: exhaustive search. Every chord sequence from I ii iii IV V V7 vi (one chord per beat) for each vocal bar,
in C, F and G major: 7^4 = 2401 sequences for bars 0, 2, 6 and 7^2 = 49 for beats 2-3 of bar 5, per key = 21 756
measured sequences. Writes adaylar.json (the top of every list) and ara/tarama.json (what 04_olcum.py needs).

The four sung stretches never share a beat (checked below: the per-bar numbers add up to the full-plan numbers),
so each bar is searched on the frames of its own line and the full plan is the combination of the bars. Only the
progression rule G3 couples bar 5 to bar 6; that junction is searched jointly.

FIT (the task's metrics, see olcut.py):   J = chord_tone - 2 * (clash_sustained + outside_scale)
  measured in three readings: 'note' (primary: each frame carries the pitch class of its note), 'frame' (every 5 ms
  frame rounded on its own) and 'early' (note mode, chord changes 40 ms early).

PROGRESSION RULES of designer B ("serbest": any diatonic triad may be used, but the result must be a major-key song):
  G1  bar 6 ends on V, V7 or I                                                     (given by the task)
  G2  the chord right before a bar that is NOT sung (bars 1, 3, 7: loud answer / animal call, all starting on I)
      is I, IV, V or V7: the tonic is always reached by staying, by an authentic or by a plagal step, never from a
      minor chord (ii -> I, iii -> I, vi -> I at a bar line would make the loud answer sound like a change of key)
  G3  the dominant goes home: V / V7 is followed by V, V7 or I (never by IV, ii, iii, vi); V7 does not drop its seventh
      G3t (second rule set "turnaround", searched as well): as G3, but the plain V may also step down to IV when
      that IV goes straight to I: V - IV - I, the turnaround of country / bluegrass / rock bands
  G4  every fully sung bar has at least two beats of primary chords (I, IV, V, V7): the major key stays in charge
PREFERENCE (ties): candidates within TIE of the best J -> fewer chord changes inside the bar -> fewer changes on
  beats 1 / 3 (two-beat chords) -> higher on_beat_chord_tone -> higher J in frame mode.
"""
import sys, os, itertools, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
from olcut import *
from kurallar import *

F = Frames()
TIE = 0.005
EARLY = 0.040 / BEAT
TOP_N = 40


def brief(e):
    return {k: e[k] for k in ("chord_tone", "scale_non_chord", "outside_scale", "clash_any", "clash_sustained",
                              "clash_sustained_strict", "sustained_clash_runs", "on_beat_chord_tone", "line_end_chord_tone")}


t0 = time.time()
cands = {}; raw = {}
for key in ("C", "F", "G"):
    cands[key] = {}; raw[key] = {}
    for bar, ln in BAR_LINE.items():
        mask = F.line == LINES.index(ln)
        rows = []
        for combo in itertools.product(DEGS, repeat=len(PLAIN[bar])):
            bars = dict(PLAIN); bars[bar] = list(combo)
            plan, _deg = major_plan(key, bars)
            e = evaluate(F, plan, mask)
            ef = evaluate(F, plan, mask, mode="frame")
            ee = evaluate(F, plan, mask, shift_beats=EARLY)
            rl = rules(bar, combo)
            rows.append({"chords": list(combo), "J": r(J(e)), "J_frame": r(J(ef)), "J_early": r(J(ee)),
                         "changes": changes(bar, combo), "odd_beat_changes": odd_changes(bar, combo),
                         "rules": rl, "valid": all(rl.values()), "valid_turnaround": all(rules(bar, combo, turnaround=True).values()), **brief(e),
                         "frame_mode": {k: ef[k] for k in ("chord_tone", "clash_sustained", "outside_scale")}})
        rows.sort(key=lambda q: (-q["J"], q["changes"], q["odd_beat_changes"], -q["on_beat_chord_tone"], -q["J_frame"]))
        raw[key][bar] = rows
        valid = [q for q in rows if q["valid"]]
        cands[key][str(bar)] = {"sequences_measured": len(rows), "sequences_passing_the_rules": len(valid),
                                "sequences_passing_the_turnaround_rules": sum(1 for q in rows if q["valid_turnaround"]),
                                "top_by_fit_any_sequence": rows[:TOP_N], "top_passing_the_rules": valid[:TOP_N],
                                "top_passing_the_turnaround_rules": [q for q in rows if q["valid_turnaround"]][:TOP_N]}
    print("key %s searched (%.0f s)" % (key, time.time() - t0))


def is_valid(q, mode):
    return True if mode == "free" else q["valid_turnaround" if mode == "turnaround" else "valid"]


def pick_bar(rows, mode="rules", extra=lambda q: True):
    ok = [q for q in rows if is_valid(q, mode) and extra(q)]
    top = max(q["J"] for q in ok)
    tied = [q for q in ok if q["J"] >= top - TIE]
    tied.sort(key=lambda q: (q["changes"], q["odd_beat_changes"], -q["on_beat_chord_tone"], -q["J_frame"], -q["J"]))
    return tied[0], tied


def best_plan(key, mode="rules"):
    """bars 0 and 2 on their own; bars 5 and 6 jointly (G3 across the junction bar 5 beat 3 -> bar 6 beat 0)."""
    out = {}; ties = {}
    tr = mode == "turnaround"
    for bar in (0, 2):
        b, t = pick_bar(raw[key][bar], mode)
        out[bar] = b["chords"]; ties[str(bar)] = [q["chords"] for q in t]
    n5 = (F.line == LINES.index("diye")).sum(); n6 = (F.line == LINES.index("L4")).sum()
    best = None
    for q5 in raw[key][5]:
        if not is_valid(q5, mode):
            continue
        def comp(q6, last=q5["chords"][-1]):
            return mode == "free" or all(rules(6, q6["chords"], before=last, turnaround=tr).values())
        try:
            b6, t6 = pick_bar(raw[key][6], mode, comp)
        except ValueError:
            continue
        tot = (q5["J"] * n5 + b6["J"] * n6) / (n5 + n6)
        keyq = (round(tot, 4), -(q5["changes"] + b6["changes"]), -(q5["odd_beat_changes"] + b6["odd_beat_changes"]),
                q5["on_beat_chord_tone"] + b6["on_beat_chord_tone"])
        if best is None or keyq > best[0]:
            best = (keyq, q5, b6, t6)
    _, q5, b6, t6 = best
    t5 = [q for q in raw[key][5] if is_valid(q, mode) and q["J"] >= q5["J"] - TIE
          and (mode == "free" or all(rules(6, b6["chords"], before=q["chords"][-1], turnaround=tr).values()))]
    out[5] = q5["chords"]; out[6] = b6["chords"]
    ties["5"] = [q["chords"] for q in t5]; ties["6"] = [q["chords"] for q in t6]
    return out, ties


def weighted(key, bars, field="J"):
    tot = 0.0
    for bar, ln in BAR_LINE.items():
        q = next(x for x in raw[key][bar] if x["chords"] == list(bars[bar]))
        tot += q[field] * (F.line == LINES.index(ln)).sum()
    return tot / F.n


res = {}
for key in ("C", "F", "G"):
    res[key] = {}
    for kind in ("rules", "turnaround", "free"):
        bars, ties = best_plan(key, kind)
        plan, _ = major_plan(key, bars)
        e = evaluate(F, plan)
        # additivity check: per-bar numbers must add up to the full-plan number
        assert abs(weighted(key, bars, "chord_tone") - e["chord_tone"]) < 2e-4, (key, kind)
        assert abs(weighted(key, bars, "clash_sustained") - e["clash_sustained"]) < 2e-4, (key, kind)
        res[key][kind] = {"bars": {str(b): v for b, v in bars.items()}, "ties": ties, "J": r(J(e)),
                          "J_frame": r(J(evaluate(F, plan, mode="frame"))), "J_early": r(J(evaluate(F, plan, shift_beats=EARLY))),
                          **brief(e)}
        print("  %s best (%s): %s | J %.3f (frame %.3f) ct %.1f %% sus %.1f %% out %.1f %% on-beat %.1f %% line-end %.1f %%" % (
            key, kind, " | ".join(" ".join(bars[b]) for b in (0, 2, 5, 6)), res[key][kind]["J"], res[key][kind]["J_frame"],
            100 * e["chord_tone"], 100 * e["clash_sustained"], 100 * e["outside_scale"], 100 * e["on_beat_chord_tone"], 100 * e["line_end_chord_tone"]))
        print("        ties:", {b: len(t) for b, t in ties.items()}, {b: [" ".join(x) for x in t[:6]] for b, t in ties.items()})

# robustness of the key ranking and of the chosen bars to the weight of the 'wrong note' terms
rob = {}
for w in (1.0, 2.0, 4.0):
    rob[str(w)] = {}
    for kind in ("rules", "turnaround", "free"):
        sc = {}; ch = {}
        for key in ("C", "F", "G"):
            # re-rank with weight w (per bar; bar 6 is restricted to what may follow the bar 5 pick)
            tot = 0.0; bars = {}
            val = lambda q: q["chord_tone"] - w * (q["clash_sustained"] + q["outside_scale"])
            for bar, ln in BAR_LINE.items():
                rows = [q for q in raw[key][bar] if is_valid(q, kind)]
                if kind != "free" and bar == 6:
                    rows = [q for q in rows if all(rules(6, q["chords"], before=bars[5][-1], turnaround=(kind == "turnaround")).values())]
                top = max(val(q) for q in rows)
                b = sorted([q for q in rows if val(q) >= top - TIE], key=lambda q: (q["changes"], q["odd_beat_changes"], -q["on_beat_chord_tone"], -q["J_frame"]))[0]
                bars[bar] = b["chords"]; tot += val(b) * (F.line == LINES.index(ln)).sum()
            sc[key] = r(tot / F.n); ch[key] = {str(b): " ".join(v) for b, v in bars.items()}
        rob[str(w)][kind] = {"score": sc, "bars": ch}
print("key ranking, best plan per key, J with weight w:")
for w, d in rob.items():
    print("   w = %s: rules %s | turnaround %s | free %s" % (w, d["rules"]["score"], d["turnaround"]["score"], d["free"]["score"]))
    print("            C rules bars %s | C turnaround bars %s" % (d["rules"]["bars"]["C"], d["turnaround"]["bars"]["C"]))

save_json(os.path.join(T, "adaylar.json"), {
    "about": "Designer B: every chord sequence from I ii iii IV V V7 vi (one chord per beat) for each vocal bar, in C, F and G major. "
             "Bar 0 = L1, bar 2 = L2, bar 5 = beats 2-3 ('diye bagirir'), bar 6 = L4. Measured over the sung frames of that line in all "
             "7 verses. Only the top %d of each list are stored (2401 / 49 sequences were measured per bar and key). "
             "Sorted by J = chord_tone - 2 * (clash_sustained + outside_scale) in note mode, then fewer chord changes, fewer changes on "
             "beats 1 / 3, higher on_beat_chord_tone. J_frame / J_early = the same score in frame mode / with chord changes 40 ms early. "
             "rules = G1..G4 of 03_tara.py (bar-internal part; the bar 5 -> bar 6 junction is checked when plans are combined); "
             "valid = passes G1-G4, valid_turnaround = passes them with G3t instead of G3. "
             "Metric definitions: olcum.json." % TOP_N,
    "rules": {"G1": "bar 6 ends on V, V7 or I (task)",
              "G2": "the chord right before a bar that is not sung (bars 1, 3, 7, all starting on I) is I, IV, V or V7",
              "G3": "V / V7 is followed by V, V7 or I; V7 is not followed by plain V",
              "G3t": "second rule set 'turnaround': as G3, but the plain V may step down to IV when that IV goes straight to I (V - IV - I)",
              "G4": "every fully sung bar has at least two beats of primary chords (I, IV, V, V7)",
              "ties": "J within %.3f: fewer chord changes, fewer changes on beats 1 / 3, higher on-beat chord-tone share, higher J in frame mode" % TIE},
    "candidates": cands})
save_json(os.path.join(ARA, "tarama.json"), {
    "best_per_key": res, "weight_robustness": rob,
    "sequences_measured_per_key": {k: sum(len(raw[k][b]) for b in raw[k]) for k in raw},
    "rows_of_interest": {key: {str(bar): [q for q in raw[key][bar] if q["valid_turnaround"]][:12] for bar in raw[key]} for key in raw}})
print("written: adaylar.json, ara/tarama.json (%.0f s)" % (time.time() - t0))
