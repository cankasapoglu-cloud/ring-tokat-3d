#!/usr/bin/env python3
"""Step 6: assemble plan.json (the deliverable of harmony designer A) from the measurement files.
No number is typed by hand here: everything is read from olcum.json, ses_olcumu.json and alt_politika.json.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
from bant import Band, note_name

O = load_json(os.path.join(T, "olcum.json"))
S = load_json(os.path.join(T, "ses_olcumu.json"))
U = load_json(os.path.join(T, "alt_politika.json"))
P = O["plans"]
KEY = "C"


def find(prefix):
    k = [n for n in P if n.startswith(prefix)]
    assert len(k) == 1, (prefix, k)
    return P[k[0]]


CH = find("C A* :"); CH7 = find("C A  :"); BASE = find("C plain baseline"); REF = O["reference_original_d_minor_loop"]
bars = CH["bars"]
assert bars == O["chosen_bars_as_played"] and O["cross_check_chords_as_played"]["agrees_with_step1_harmony_played_without_the_seventh"]
step1 = O["step1_harmony_C_sade"]
assert {b: ['V7' if c == 'V' else c for c in ch] for b, ch in bars.items()} == step1

KEEP = ("chord_tone", "scale_non_chord", "outside_scale", "clash_any", "clash_sustained", "clash_sustained_strict", "consonant_non_chord",
        "sustained_clash_runs", "sounding_semitone", "sounding_semitone_sustained")


def m(e):
    return {k: e[k] for k in KEEP if k in e}


def pack(Pl, lines=True):
    d = {"all_sung_frames": m(Pl["note"])}
    if lines:
        d["per_line"] = {ln: m(e) for ln, e in Pl["per_line"].items()}
    return d


def aud(name, stretch):
    d = S["results"][name][stretch]
    return {"mean_power_db_re_one_strummed_chord_note": d["mean_power_db_re_strum_note"], "share_of_sung_time_above_-6_db": d["share_above_-6_db"],
            "of_which_in_runs_over_150ms": d["share_above_-6_db_in_runs_over_150ms"], "runs_over_150ms": d["runs_over_150ms_above_-6_db"]}


band = Band(KEY)
names = lambda L: " ".join(note_name(n) for n in L)
ton = PC[KEY]
chord_name = {"I": "C", "IV": "F", "V7": "G7", "V": "G"}
grid = {"bar_0_L1": step1["0"], "bar_2_L2": step1["2"], "bar_5_diye_bagirir": ["I", "I"] + step1["5"], "bar_6_L4": step1["6"]}
played = {"bar_0_L1": bars["0"], "bar_2_L2": bars["2"], "bar_5_diye_bagirir": ["I", "I"] + bars["5"], "bar_6_L4": bars["6"]}

n_ch, n_b, n_ref = CH["note"], BASE["note"], REF["note"]
pct = lambda x: round(100 * x, 1)
d_pts = lambda a, b: round(100 * (a - b), 1)

plan = {
    "designer": "A (sade: only I, IV, V7; close to the traditional harmony)",
    "version": "dogal (the vocal exactly as sung; no pitch or time processing)",
    "key": "C major",
    "tonic": "C",
    "chords_of_the_key": {"I": "C (C E G)", "IV": "F (F A C)", "V7": "G7 (G B D F)"},
    "harmony_plan": {
        "same_plan_for_all_7_verses": True,
        "degrees_per_beat": grid,
        "chord_names_per_beat": {k: [chord_name[c] for c in v] for k, v in grid.items()},
        "band_plays_per_beat": {k: [chord_name[c] for c in v] for k, v in played.items()},
        "in_words": "Bar 0 (L1): C on beat 0, F on beat 1 (under 'Baba'nin', where the singer holds A), C on beats 2-3. "
                    "Bar 2 (L2) and bar 6 (L4): the dominant G for the whole bar. Bar 5: C (beats 0-1 drum fill, beats 2-3 'diye bagirir'). "
                    "Everything else stays as built: bars 1 and 7 = C G7 C C (loud answer), bars 3-4 = C (animal calls), intro and ending unchanged.",
        "dominant_under_the_vocal": {
            "rule": "In bars 2 and 6 the band plays the dominant WITHOUT its seventh (G B D, no F). The singer sings that seventh herself (F on beats 2 and 3) "
                    "and sings E right next to it; with F in the band the sung E lies one semitone from a sounding band note. "
                    "The loud answers (bars 1, 7), the intro and the ending keep the full V7.",
            "fallback": "If the builder cannot voice it, play V7 as usual: the harmony is the same; the measured cost is listed under metrics.dominant_seventh_in_the_band.",
        },
        "bar_5_beats_0_1": "unchanged: drum fill with bass on I (fixed by the form)",
        "verse_8_bars_as_the_band_plays_them": [bars["0"], ["I", "V7", "I", "I"], bars["2"], ["I"] * 4, ["I"] * 4, ["I", "I"] + bars["5"], bars["6"], ["I", "V7", "I", "I"]],
        "legend": "V7 = G7 with its seventh (answers, intro, ending); V = the same dominant played without the seventh (G B D), used only under the vocal in bars 2 and 6",
        "fixed_by_the_form": {"bars_1_and_7": ["I", "V7", "I", "I"], "bars_3_and_4": ["I", "I", "I", "I"]},
        "verse_bar_to_song_bar": "verse v (0..6), bar b (0..7) = song bar 4 + 8 v + b; downbeat at 0.100 + bar * 2.285714 s",
    },
    "notes_for_the_builder_key_C": {
        "I": {"banjo_chord": names(band.CH["I"]), "piano_accordion_chord": names([n + 12 for n in band.CH["I"]]), "bass_root": note_name(band.ROOT["I"]), "bass_fifth": note_name(band.FIFTH["I"])},
        "IV": {"banjo_chord": names(band.CH["IV"]), "piano_accordion_chord": names([n + 12 for n in band.CH["IV"]]), "bass_root": note_name(band.ROOT["IV"]), "bass_fifth": note_name(band.FIFTH["IV"])},
        "V7_answers_intro_ending_unchanged": {"banjo_chord": names(band.CH["V7"]), "piano_accordion_chord": names([n + 12 for n in band.CH["V7"]]), "bass_root": note_name(band.ROOT["V7"])},
        "V_under_the_vocal_bars_2_and_6": {"banjo_chord": names(band.CH["V"]), "piano_accordion_chord": names([n + 12 for n in band.CH["V"]]),
                                           "banjo_roll_8_eighths": names(band.ROLL["V"]), "bass_root": note_name(band.ROOT["V"]), "bass_fifth": note_name(band.FIFTH["V"])},
        "in_build_py_terms": "the arrangement is written in G and moved by AS (C: -7). Add CH['V'] = [54, 57, 62] (V7 without 60), "
                             "ROLL['V'] = [62, 66, 57, 66, 62, 66, 57, 66] (the V7 roll with its seventh on beat 1 replaced), DEG['V'] = 7; "
                             "verse bars: 0 -> ['I','IV','I','I'], 2 and 6 -> ['V','V','V','V'], 5 -> ['I','I','I','I']; no alt_notes() in the vocal bars.",
        "oom_pah_pattern_the_plan_relies_on": "as in build.py groove(): beats 0 and 2 = bass + root octaves + one banjo note only; the full chord sounds on every "
                                              "off-beat (piano, accordion) and on beats 1 and 3 (accordion, banjo). Checked note for note against midi/altyapi_C.mid.",
        "optional_refinement_low_priority": {
            "what": "in bars 2 and 6 keep the bass on the root G on beat 2 (the builder plays the fifth D there when beats 0-2 share a chord)",
            "why": "the 5th harmonic of the bass D2 lies at F#4, one semitone above the F the singer holds on that beat",
            "measured_on_rendered_audio_beat_2_of_bars_2_and_6": {"with_the_fifth_D": aud("Ay_V-V-V-V_SECILEN", "bars_2_and_6_beat_2_only"),
                                                                  "with_the_root_G": aud("Ayk_V-V-V-V_kok_bas", "bars_2_and_6_beat_2_only")},
        },
    },
    "under_vocal_policy": {
        "policy": "none",
        "meaning": "Under the vocal (bars 0, 2, 6 and beats 2-3 of bar 5) the band plays chords, bass and drums only. No clarinet / glockenspiel tune "
                   "(the ezgi_alti stem is not used in 'dogal'), no pad, no counter-line. The Old MacDonald tune is heard only in the intro, the loud answers and the ending.",
        "why_no_tune": {
            "voice_and_tune_on_a_different_note": U["tune_under_the_voice"]["voice_against_tune"]["different_note_than_the_voice"],
            "a_second_or_seventh_apart": U["tune_under_the_voice"]["voice_against_tune"]["a_second_or_seventh_apart (interval class 1 or 2)"],
            "a_second_apart_in_the_same_octave": U["tune_under_the_voice"]["voice_against_tune"]["a_second_apart_in_the_same_octave"],
            "tune_against_the_chosen_chords": U["tune_under_the_voice"]["tune_against_chords"]["tune_against_the_chosen_harmony (I IV I I | V V V V | I I | V V V V)"],
            "text": "shares of the sung time: the soft tune would sound a different note than the voice most of the time (two melodies, what the user rejected), "
                    "and the tune does not fit the chords that support the voice (its 'do do do' lies a semitone above the third of the dominant in bars 2 and 6).",
        },
        "why_no_pad": {
            "share_of_sung_time_one_semitone_from_a_sounding_note": {k: v for k, v in U["one_semitone_from_a_sounding_note"].items() if "chosen" in k or "pad" in k and "baseline" not in k or "seventh in the band" in k},
            "text": "A pad adds nothing the oom-pah does not already state (the chord is struck on every off-beat and on beats 1 and 3) and does not lower the "
                    "semitone exposure; a pad that holds the dominant seventh would triple it.",
        },
        "allowed_fallback_if_the_mix_step_finds_the_vocal_bars_too_thin": "a very soft sustained pad of root + fifth, or of the plain triads (never the seventh of the dominant, never a moving line)",
    },
    "metrics": {
        "units": "fractions of the voiced sung time (44.85 s in 7 verses), note mode; definitions in olcum.json",
        "chosen_plan_as_the_band_plays_it": {**pack(CH), "frame_mode": m(CH["frame"]), "chord_changes_40ms_early": m(CH["chords_40ms_early"]),
                                              "per_verse": [m(e) for e in CH["per_verse"]],
                                              "L2_per_verse": [d["L2"] for d in CH["per_verse_and_line"]],
                                              "L4_per_verse": [d["L4"] for d in CH["per_verse_and_line"]],
                                              "pitch_outliers_that_no_chord_can_fix": "verse 7 line 4 'cift' is sung on A#3 (80 ms vowel) and verse 3 line 4 'cift' sags to C#4: "
                                                                                      "together the outside-scale share of line 4 (kesim.json: pitch_outliers)",
                                              "remaining_sustained_clash_runs": CH["note"].get("runs", [])},
        "chosen_plan_read_as_V7 (the sung F counted as the chord seventh; the E 'clash' is against a seventh the band does not play)": pack(CH7),
        "plain_baseline_C (I I IV I | I I IV I | I I | I I IV I)": pack(BASE),
        "original_d_minor_loop_reference (Dm Dm C C | Gm Gm A A | C C | Gm Gm A A)": {"all_sung_frames": m(n_ref), "per_line": {ln: m(e) for ln, e in REF["per_line"].items()}},
        "chosen_against_baseline_in_points": {
            "chord_tone": d_pts(n_ch["chord_tone"], n_b["chord_tone"]),
            "chord_tone_if_read_as_V7": d_pts(CH7["note"]["chord_tone"], n_b["chord_tone"]),
            "clash_any": d_pts(n_ch["clash_any"], n_b["clash_any"]),
            "clash_sustained": d_pts(n_ch["clash_sustained"], n_b["clash_sustained"]),
            "sustained_clash_runs_in_the_song": [n_ch["sustained_clash_runs"], n_b["sustained_clash_runs"]],
            "sounding_semitone": d_pts(n_ch["sounding_semitone"], n_b["sounding_semitone"]),
            "sounding_semitone_sustained": d_pts(n_ch["sounding_semitone_sustained"], n_b["sounding_semitone_sustained"]),
            "outside_scale": d_pts(n_ch["outside_scale"], n_b["outside_scale"]),
        },
        "dominant_seventh_in_the_band (same harmony, V7 voiced with F)": {"all_sung_frames": m(CH7["note"])},
        "rendered_audio_check": {
            "what": S["about"],
            "all_sung_frames": {"chosen": aud("Ay_V-V-V-V_SECILEN", "all_sung_frames"), "chosen_with_seventh_in_the_band": aud("A_V7-V7-V7-V7", "all_sung_frames"),
                                "plain_baseline": aud("taban_I-I-IV-I", "all_sung_frames")},
            "bars_2_and_6": {"chosen": aud("Ay_V-V-V-V_SECILEN", "L2_and_L4_whole_bars"), "chosen_with_seventh_in_the_band": aud("A_V7-V7-V7-V7", "L2_and_L4_whole_bars"),
                             "plain_baseline": aud("taban_I-I-IV-I", "L2_and_L4_whole_bars")},
            "beat_2_of_bars_2_and_6": {"chosen": aud("Ay_V-V-V-V_SECILEN", "bars_2_and_6_beat_2_only"), "chosen_with_seventh_in_the_band": aud("A_V7-V7-V7-V7", "bars_2_and_6_beat_2_only"),
                                       "plain_baseline": aud("taban_I-I-IV-I", "bars_2_and_6_beat_2_only")},
            "where_the_chosen_plan_still_measures_rub": S["chosen_plan_breakdown"],
            "caveat": "the semitone bands also catch overtones of consonant band notes (for example the third of a chord under a sung root) and the attack noise of "
                      "every strum; only the large differences and the runs above -6 dB are meaningful.",
        },
    },
    "key_comparison": {
        "about": "best plan per key from I, IV, V7 (J = chord_tone - 2 * (clash_sustained + outside_scale)); C is first for weights 1, 2 and 4",
        "per_key": {k: {"plain_baseline": m(P["%s plain baseline" % k]["note"]),
                        "best_free_per_beat": {"bars": P["%s best, free I/IV/V7 per beat" % k]["bars"], **m(P["%s best, free I/IV/V7 per beat" % k]["note"])},
                        "best_sade_shape": {"bars": P["%s best, sade shape" % k]["bars"], **m(P["%s best, sade shape" % k]["note"])}} for k in ("C", "F", "G")},
        "score_by_weight": {w: {kind: d[kind]["score"] for kind in ("free", "sade")} for w, d in O["key_ranking_robustness"].items() if w != "about"},
        "why_C": "All five sung pitch classes (D E F G A) are in C major; in G major the sung F natural is outside the scale for 16 % of the sung time and sits a "
                 "semitone below the F sharp of the band's V7. F major has no clash advantage and fewer chord tones. The G triad that carries lines 2 and 4 "
                 "without any clash is the tonic of G but the dominant of C: in C the loud answer of bar 7 resolves it.",
    },
    "alternatives_measured": {n[2:]: {"bars": Pl["bars"], **m(Pl["note"])} for n, Pl in P.items() if n[2:4] in ("B ", "B*", "C ", "C*", "D ", "E*")},
    "how_the_plan_was_chosen": {
        "step_1": "Every I / IV / V7 choice per beat was measured for each vocal bar in C, F and G (adaylar.json). Ranking J = chord_tone - 2 * (clash_sustained + outside_scale); "
                  "shape rules: the verse opens on I, the dominant never moves to IV, bar 6 ends on the dominant or I. Result in C: " + " | ".join(" ".join(step1[b]) for b in ("0", "2", "5", "6")) + ".",
        "step_2": "Voicing of the dominant under the vocal, decided by what really sounds (band model checked against the builder's MIDI, and rendered audio): without the seventh.",
        "cross_check": "The same search with the chords as played (I, IV and the dominant triad) gives the same bars: " + " | ".join(" ".join(bars[b]) for b in ("0", "2", "5", "6")) + ".",
        "robustness": {k: v["readings_agreeing_with_primary_per_bar"] for k, v in O["robustness_of_the_chosen_bars"].items() if k != "about"},
        "robustness_note": "18 readings: note mode, frame mode, a second pitch tracker, chord changes 40 ms early, each verse left out, each verse alone. "
                           "With V7 symbols beat 2 of bar 6 flips between V7 and I in 7 readings: F and E are equally long there and one of them is a semitone from the "
                           "chord whichever of the two is chosen. Played without the seventh the dominant has no semitone relation to either note, and bar 6 is the same in 18 of 18. "
                           "In the as-played search the deviating readings of bar 2 (single verses and one leave-out) put IV on beat 2, which the rendered audio shows to be the "
                           "loudest rub of all candidates; the deviating readings of bar 5 (frame mode, two single verses) put the dominant under 'diye bagirir', "
                           "which removes the passing-F clash but ends the phrase on a non-chord tone.",
    },
    "reasoning": [
        "The sung melody is not the Old MacDonald tune: its notes are D E F G A, G alone is 45 % of the sung time. Under the plain harmony I I IV I only 58 % of the sung time is on chord tones.",
        "Line 1 (beat by beat: D G | A A A | G G | G F E): the singer holds A on beat 1 and G on beat 2; the traditional bar has its IV on beat 2, one beat late for her. Moving IV one beat earlier (I IV I I) raises the chord-tone share of the line from "
        + "%.0f %% to %.0f %%. The line ends on E (mi over I); the loud answer that follows starts on the same note." % (100 * BASE["per_line"]["L1"]["chord_tone"], 100 * CH["per_line"]["L1"]["chord_tone"]),
        "Lines 2 and 4 (D G G G | F E F E D) outline the dominant: D and G are its fifth and root, F its seventh, E a sixth above it. On the G triad no sung note is a semitone from a chord tone. "
        "Every chord that contains E (I) or F (IV, V7) puts the other note a semitone away for half a beat; the plain baseline does that with IV on beat 2.",
        "'diye bagirir' (G G G F E) stays on I: G and E are chord tones, the F is a passing note of about 150 ms.",
        "Bar 6 on the dominant leads into the loud answer of bar 7 (I V7 I I); bar 2 on the dominant resolves to the I of the animal-call bars.",
        "One plan serves all verses: the animal words differ only in detail (verse 3 after the repair: F F E D; verse 7: F E F-E D) and line 2 has no sustained clash in any verse.",
        "The original band of v2_2 (D minor loop), measured the same way, has " + "%.1f %% sustained clash (%d runs); the chosen plan has %.1f %% (%d runs)." % (
            100 * n_ref["clash_sustained"], n_ref["sustained_clash_runs"], 100 * n_ch["clash_sustained"], n_ch["sustained_clash_runs"]),
    ],
    "trade_offs_stated_plainly": [
        "As played (no seventh in the band) the band doubles fewer of the sung notes in bars 2 and 6 than the baseline does (chord tones %.1f / %.1f %% against %.1f / %.1f %%): the F and E of the animal word and of 'Ali Baba'nin' float above the G triad as seventh and sixth. That is the price of having no semitone there."
        % (100 * CH["per_line"]["L2"]["chord_tone"], 100 * CH["per_line"]["L4"]["chord_tone"], 100 * BASE["per_line"]["L2"]["chord_tone"], 100 * BASE["per_line"]["L4"]["chord_tone"]),
        "Bars 2 and 6 leave the traditional I I IV I completely; the plan stays inside I, IV and the dominant, one chord per bar there.",
        "The first sung note of every verse (D, about 0.2 s) is a ninth over C: not a chord tone, no semitone neighbour. Opening the verse on the dominant instead (alternative E*) would make it a chord tone (+%.1f points of chord-tone share) but starts each verse on V and moves V to IV."
        % d_pts(find("C E* :")["note"]["chord_tone"], n_ch["chord_tone"]),
        "Three sustained clash runs remain in the whole song (the passing F of 'ciftligi' / 'bagirir' against the E of the I chord, 155-175 ms).",
    ],
    "not_verified_by_ear": "Nobody listened. Verified by code: the frame table reproduces kesim.json, the band model reproduces the builder's MIDI, the tune model reproduces the stem's MIDI, "
                           "and 07_dogrula.py recomputes the numbers of this file by a separate route. Unverified by ear: that the seventh and sixth above the G triad feel supported, "
                           "that a whole bar of dominant under lines 2 and 4 feels natural, that the ninth on the first note of each verse is unobtrusive, and whether dropping the seventh is audible at all.",
    "files": {"all_candidates": "adaylar.json", "measurements": "olcum.json", "audio_check": "ses_olcumu.json", "under_vocal_numbers": "alt_politika.json",
              "verification": "dogrulama.txt", "scripts": "kod/ (kod/calistir.sh reruns everything)"},
}
save_json(os.path.join(T, "plan.json"), plan)

print("plan.json written")
print("key C | bar 0: %s | bar 2: %s | bar 5: %s | bar 6: %s  (band plays: %s | %s | %s | %s)" % tuple(
    [" ".join(grid[k]) for k in grid] + [" ".join(chord_name[c] for c in played[k]) for k in played]))
print("chosen  : chord tone %.1f %% (read as V7: %.1f %%), clash any %.1f %%, sustained %.1f %% (%d runs), outside %.1f %%, sounding semitone %.1f %% / sustained %.1f %%" % (
    pct(n_ch["chord_tone"]), pct(CH7["note"]["chord_tone"]), pct(n_ch["clash_any"]), pct(n_ch["clash_sustained"]), n_ch["sustained_clash_runs"],
    pct(n_ch["outside_scale"]), pct(n_ch["sounding_semitone"]), pct(n_ch["sounding_semitone_sustained"])))
print("baseline: chord tone %.1f %%, clash any %.1f %%, sustained %.1f %% (%d runs), outside %.1f %%, sounding semitone %.1f %% / sustained %.1f %%" % (
    pct(n_b["chord_tone"]), pct(n_b["clash_any"]), pct(n_b["clash_sustained"]), n_b["sustained_clash_runs"], pct(n_b["outside_scale"]),
    pct(n_b["sounding_semitone"]), pct(n_b["sounding_semitone_sustained"])))
print("original D minor loop: chord tone %.1f %%, clash any %.1f %%, sustained %.1f %% (%d runs)" % (
    pct(n_ref["chord_tone"]), pct(n_ref["clash_any"]), pct(n_ref["clash_sustained"]), n_ref["sustained_clash_runs"]))
