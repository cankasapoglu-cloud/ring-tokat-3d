#!/usr/bin/env python3
"""Step 6: write plan.json (the harmony plan of designer B for the 'dogal' version) from the measurements.
Every number in the file is read from olcum.json / ses_olcumu.json / ara/tarama.json; nothing is typed in by hand."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
from bant import Band, note_name

M = load_json(os.path.join(T, "olcum.json"))
S = load_json(os.path.join(T, "ses_olcumu.json"))["results"]
SCAN = load_json(os.path.join(ARA, "tarama.json"))
PCS = load_json(os.path.join(ARA, "kareler_dogrulama.json"))["pitch_class_share_note_mode"]
P = M["plans"]
best = P["C BEST"]; ru = P["C RUNNER_UP"]; base = P["C plain baseline"]; desA = P["C designer_A"]; ref = M["reference_original_d_minor_loop"]
b0 = M["bar_0_verse_opening"]["candidates"]; gl = M["bar_0_verse_opening"]["gliding_syllable_li"]
st2 = M["stage_2_seventh_of_the_dominant"]; rob = M["robustness_of_the_choice"]["agreement"]
uv = M["under_vocal"]; tune = uv["tune_under_the_voice"]; expo = uv["one_semitone_from_a_sounding_note"]
KEYS = ("chord_tone", "scale_non_chord", "outside_scale", "clash_any", "clash_sustained", "clash_sustained_strict", "consonant_non_chord",
        "sustained_clash_runs", "on_beat_chord_tone", "off_beat_chord_tone", "line_end_chord_tone", "J")
PHYS = ("sounding_semitone", "sounding_semitone_sustained", "whole_tone_same_octave", "band_same_pitch_class")


def p1(x):
    return "%.1f" % (100.0 * x)


def pick(e, keys=KEYS + PHYS):
    return {k: e[k] for k in keys if k in e}


def block(Pn):
    return {"all_sung_frames": pick(Pn["note"]),
            "per_line": {ln: pick(Pn["per_line"][ln]) for ln in LINES},
            "frame_mode": pick(Pn["frame"]), "second_pitch_tracker": pick(Pn["dio"]),
            "chord_changes_40ms_early": pick(Pn["chords_40ms_early"]),
            "per_verse": [pick(v, ("verse", "animal") + KEYS + PHYS) for v in Pn["per_verse"]]}


def names(key, degs):
    return [chord_of_degree(PC[key], d)["name"] for d in degs]


def verse32(bars):
    v = [bars["0"], ["I", "V7", "I", "I"], bars["2"], ["I"] * 4, ["I"] * 4, ["I", "I"] + bars["5"], bars["6"], ["I", "V7", "I", "I"]]
    return v


def plan_block(Pn):
    bars = Pn["bars"]
    v = verse32(bars)
    return {"degrees_per_beat": {"bar_0_L1": bars["0"], "bar_2_L2": bars["2"], "bar_5_diye_bagirir": ["I", "I"] + bars["5"], "bar_6_L4": bars["6"]},
            "chord_names_per_beat": {"bar_0_L1": names("C", bars["0"]), "bar_2_L2": names("C", bars["2"]),
                                     "bar_5_diye_bagirir": names("C", ["I", "I"] + bars["5"]), "bar_6_L4": names("C", bars["6"])},
            "whole_verse_per_beat": {"bar_%d" % i: {"degrees": v[i], "chords": names("C", v[i]),
                                                    "role": ["vocal L1", "loud answer (fixed)", "vocal L2", "animal call 1 (fixed)", "animal call 2 (fixed)",
                                                             "beats 0-1 drum fill (fixed), beats 2-3 vocal 'diye bagirir'", "vocal L4", "loud answer (fixed)"][i]}
                                     for i in range(8)}}


def aud(name, stretch, keys=("rub_mean_power_db", "rub_share_above_-6_db", "rub_share_above_-6_db_in_runs_over_150ms", "rub_runs_over_150ms_above_-6_db",
                             "support_mean_power_db", "support_share_above_-6_db", "frame_pitch_support_share_above_-6_db",
                             "whole_tone_neighbours_mean_power_db")):
    return {k: S[name][stretch][k] for k in keys}


CH, RU_, A_, BASE = "SECILEN_ii-ii-I-I_V-V-V-V", "IKINCI_V-IV-I-I_V-V-V-V", "tasarimci_A_I-IV-I-I_V-V-V-V", "taban_I-I-IV-I"
band = Band("C")


def voicing(deg):
    return {"banjo_chord": " ".join(note_name(n) for n in band.CH[deg]), "piano_accordion_chord": " ".join(note_name(n + 12) for n in band.CH[deg]),
            "banjo_roll_8_eighths": " ".join(note_name(n) for n in band.ROLL[deg]), "bass_root": note_name(band.ROOT[deg]),
            "bass_fifth": note_name(band.FIFTH[deg])}


bn = best["note"]; rn = ru["note"]; an = desA["note"]; ban = base["note"]; orn = ref["note"]
L = best["per_line"]
diff = lambda a, b, k: round(100 * (a[k] - b[k]), 1)
s2 = lambda ln, o, mode, k: st2[ln][o][mode][k]

plan = {
    "designer": "B (serbest: any diatonic triad I ii iii IV V vi or V7; keys C, F, G searched)",
    "version": "dogal (the vocal exactly as sung; no pitch or time processing)",
    "key": "C major", "tonic": "C",
    "chords_of_the_key_used": {"I": "C (C E G)", "ii": "Dm (D F A)", "V": "G (G B D), the dominant as a plain triad",
                               "V7": "G7 (G B D F), only in the loud answers, intro and ending (unchanged)",
                               "IV": "F (F A C), only in the runner-up, the intro and the ending"},
    "harmony_plan": {
        "same_plan_for_all_7_verses": True,
        **plan_block(best),
        "band_plays_per_beat": "exactly the chords written (V = G B D without the seventh)",
        "in_words": "Bar 0 (L1): D minor on beats 0-1 (under 'Ali Baba'nin'), C on beats 2-3 (under 'bir ciftligi var'). Bar 2 (L2) and bar 6 (L4): "
                    "the dominant G for the whole bar, as a plain triad. Bar 5: C (beats 0-1 drum fill, beats 2-3 'diye bagirir'). Everything else "
                    "stays as built: bars 1 and 7 = C G7 C C with the loud Old MacDonald answer, bars 3 and 4 = C under the animal calls, intro and "
                    "ending unchanged. Every chord lasts two beats or more inside the sung bars; the only change inside a sung bar is ii -> I on beat 2 of bar 0.",
        "dominant_under_the_vocal": {
            "rule": "In bars 2 and 6 the band plays the dominant WITHOUT its seventh (G B D, no F). The singer sings that seventh herself (F on beats 2 "
                    "and 3) with E right next to it; with F in the band her E lies one semitone from a sounding band note. The loud answers, the "
                    "intro and the ending keep their V7.",
            "fallback": "If the builder cannot voice it, V7 on the LAST beat only (V V V V7) is the least harmful place for the seventh; the measured "
                        "cost is under metrics.seventh_of_the_dominant."},
        "bar_5_beats_0_1": "unchanged: drum fill with bass on I (fixed by the form)",
        "fixed_by_the_form": {"bars_1_and_7": ["I", "V7", "I", "I"], "bars_3_and_4": ["I", "I", "I", "I"]},
        "verse_bar_to_song_bar": "verse v (0..6), bar b (0..7) = song bar 4 + 8 v + b; downbeat at 0.100 + bar * 2.285714 s",
        "per_verse_differences": "none. The animal words differ in syllable count (verse 3 'atlari' after its repair: F . F E; verse 7 'kedisi': F E F+E), "
                                 "but for every verse alone the best bar 2 is the dominant on all four beats, and the chosen bar has no clash in any verse "
                                 "(olcum.json bar_2_per_verse)."},
    "runner_up": {
        "name": "V IV I I in bar 0 (the country / bluegrass turnaround), everything else as the chosen plan",
        **plan_block(ru),
        "band_plays_per_beat": "exactly the chords written (V = G B D without the seventh)",
        "what_it_gains": "Line 1 opens on G (the sung D and G are its fifth and root), F under the held A, C from beat 2: only major chords under the "
                         "voice. Chord tones of line 1 %s %% against %s %% (note mode; frame mode %s against %s), of the whole vocal %s %% against %s %%. "
                         "Band model, beats 0-1: a band note a whole tone from the voice sounds for %s %% of the sung time against %s %%."
                         % (p1(b0["V IV I I"]["note"]["chord_tone"]), p1(b0["ii ii I I"]["note"]["chord_tone"]), p1(b0["V IV I I"]["frame"]["chord_tone"]),
                            p1(b0["ii ii I I"]["frame"]["chord_tone"]), p1(rn["chord_tone"]), p1(bn["chord_tone"]),
                            p1(b0["V IV I I"]["band_model_beats_0_1"]["whole_tone_same_octave"]), p1(b0["ii ii I I"]["band_model_beats_0_1"]["whole_tone_same_octave"])),
        "why_it_is_second": "It needs a chord change on every beat of the first half bar (the task prefers two-beat chords), every verse then opens on "
                            "the dominant, and the dominant steps down to the subdominant (outside the strict progression rules; it is the best plan of "
                            "the rule set 'turnaround'). Its advantage rests on reading the gliding syllable 'li' as one note G: in frame mode the two "
                            "plans are level (J %s against %s for the whole vocal)." % (ru["frame"]["J"], best["frame"]["J"]),
        "when_to_prefer_it": "If the two beats of D minor at the start of every verse are judged too dark for this song, or if the highest measured "
                             "fit is wanted regardless of the harmonic rhythm. Bars 2, 5 and 6 are identical, so the two plans differ only in beats 0-1 of bar 0.",
        "metrics": block(ru)},
    "notes_for_the_builder_key_C": {
        "I": voicing("I"), "ii_NEW": voicing("ii"), "V_NEW_the_dominant_without_its_seventh": voicing("V"),
        "IV_only_for_the_runner_up": voicing("IV"), "V7_answers_intro_ending_unchanged": voicing("V7"),
        "in_build_py_terms": "the arrangement is written in G and moved by AS (C: -7). Add DEG['ii'] = 2, CH['ii'] = [57, 60, 64], "
                             "ROLL['ii'] = [64, 69, 60, 69, 64, 69, 60, 69]; DEG['V'] = 7, CH['V'] = [54, 57, 62], ROLL['V'] = [62, 66, 57, 66, 62, 66, 57, 66] "
                             "(V7 without its seventh; the same voicing designer A uses); ROOT / FIFTH / CHNAME follow from DEG. Verse bars: 0 -> "
                             "['ii','ii','I','I'], 2 and 6 -> ['V','V','V','V'], 5 -> I as now; bars 1, 3, 4, 7 unchanged. No alt_notes() in the sung bars (policy 'none').",
        "voicings_are_proposals": "The ii voicing is new (close position in the register of the existing chords, same roll shape as I: fifth - root - "
                                  "third - root). It was used for the band model and for the rendered-audio check; any close-position D minor triad in that register serves.",
        "recommended_detail": {
            "what": "in bars 2 and 6 keep the bass on the root G on beat 2 (the builder plays the fifth D there when beats 0-2 share a chord)",
            "why": "the 5th harmonic of the bass D2 lies at F#4, one semitone above the F the singer holds on that beat (found by designer A; "
                   "confirmed here on an independent render)",
            "measured_on_rendered_audio_beat_2_of_bars_2_and_6": {
                "with_the_fifth_D": {k: S[CH]["bars_2_6_beat_2"][k] for k in ("rub_mean_power_db", "rub_share_above_-6_db", "rub_share_above_-12_db_in_runs_over_150ms")},
                "with_the_root_G": {k: S["SECILEN_kok_bas"]["bars_2_6_beat_2"][k] for k in ("rub_mean_power_db", "rub_share_above_-6_db", "rub_share_above_-12_db_in_runs_over_150ms")}}},
        "measured_but_not_recommended": {
            "what": "on beat 3 of bars 0 and 5 strike the on-beat strum without the third E (root and fifth only), so that the passing F of '-gi' / '-gi-' has no E next to it",
            "band_model": {"semitone_exposure_as_planned": M["optional_voicing_refinements_band_model"]["as planned"]["note"]["sounding_semitone"],
                           "with_the_open_strum": M["optional_voicing_refinements_band_model"]["on-beat strum of beat 3 without the third in bars 0 and 5"]["note"]["sounding_semitone"]},
            "rendered_audio": {"bar_0_beat_3_as_planned": {k: S[CH]["bar_0_beat_3"][k] for k in ("rub_mean_power_db", "rub_share_above_-6_db")},
                               "bar_0_beat_3_open_strum": {k: S["SECILEN_acik3"]["bar_0_beat_3"][k] for k in ("rub_mean_power_db", "rub_share_above_-6_db")},
                               "bar_5_beat_3_as_planned": {k: S[CH]["bar_5_beat_3"][k] for k in ("rub_mean_power_db", "rub_share_above_-6_db")},
                               "bar_5_beat_3_open_strum": {k: S["SECILEN_acik3"]["bar_5_beat_3"][k] for k in ("rub_mean_power_db", "rub_share_above_-6_db")}},
            "verdict": "the model removes the whole remaining semitone exposure, but on rendered audio the mean rub power falls by only 2-3 dB while "
                       "the share above -6 dB rises slightly: inconclusive, so it is NOT part of the plan"}},
    "under_vocal_policy": {
        "policy": "none",
        "meaning": "Under the vocal (bars 0, 2, 6 and beats 2-3 of bar 5) the band plays chords, bass and drums only. No clarinet / glockenspiel tune "
                   "(the ezgi_alti stem is not used in 'dogal'), no pad, no counter-line. The Old MacDonald tune is heard only in the intro, the loud "
                   "answers (bars 1 and 7) and the ending.",
        "why_no_tune": {
            "voice_and_tune_on_a_different_note": tune["different_note_than_the_voice"],
            "a_second_or_seventh_apart": tune["a_second_or_seventh_apart"], "of_which_in_runs_over_150ms": tune["of_which_in_runs_over_150ms"],
            "a_second_apart_in_the_same_octave": tune["a_second_apart_in_the_same_octave"],
            "tune_against_the_chosen_chords": tune["tune_against_the_chosen_harmony"],
            "text": "shares of the sung time: the soft tune would sound a different note than the voice %s %% of the time and a second or seventh away "
                    "from it %s %% of the time (two melodies at once, what the user rejected). It also does not fit the chords that support the "
                    "voice: only %s %% of the tune's own time is on chord tones of the chosen harmony and %s %% clashes (its 'do do do' lies a "
                    "semitone above the third of the dominant in bars 2 and 6)."
                    % (p1(tune["different_note_than_the_voice"]), p1(tune["a_second_or_seventh_apart"]),
                       p1(tune["tune_against_the_chosen_harmony"]["chord_tone"]), p1(tune["tune_against_the_chosen_harmony"]["clash"]))},
        "why_no_pad": {
            "share_of_sung_time_one_semitone_from_a_sounding_note": {k: v for k, v in expo.items() if isinstance(v, dict)},
            "text": "With chords, bass and drums only, a band note one semitone from the voice sounds for %s %% of the sung time (%s %% in runs "
                    "over 150 ms). A sustained pad cannot lower that (root + fifth %s %%, full triads %s %%) and a pad that holds the dominant "
                    "seventh would triple it (%s %%). The oom-pah already states every chord on each off-beat and on beats 1 and 3, so a pad adds "
                    "nothing the voice needs." % (
                        p1(expo["none (chords, bass, drums only) - chosen harmony"]["one_semitone_from_a_sounding_note"]),
                        p1(expo["none (chords, bass, drums only) - chosen harmony"]["in_runs_over_150ms"]),
                        p1(expo["soft pad: root + fifth of every chord - chosen harmony"]["one_semitone_from_a_sounding_note"]),
                        p1(expo["soft pad: full triads - chosen harmony"]["one_semitone_from_a_sounding_note"]),
                        p1(expo["soft pad: full chords with the seventh on the dominant"]["one_semitone_from_a_sounding_note"]))},
        "allowed_fallback_if_the_mix_step_finds_the_vocal_bars_too_thin": "a very soft sustained pad of root + fifth or of the plain triads of the plan "
                                                                          "(never the seventh of the dominant, never a moving line). Its level is not decided here."},
    "metrics": {
        "units": "fractions of the voiced sung time (%.2f s in 7 verses), note mode unless a block says otherwise; definitions in olcum.json" % best["note_voiced_s"],
        "chosen_plan": block(best),
        "remaining_sustained_clash_runs_of_the_chosen_plan": bn["runs"],
        "plain_baseline_C (I I IV I | I I IV I | I I | I I IV I)": {"all_sung_frames": pick(ban), "per_line": {ln: pick(base["per_line"][ln]) for ln in LINES},
                                                                     "frame_mode": pick(base["frame"])},
        "original_d_minor_loop_reference (Dm Dm C C | Gm Gm A A | C C | Gm Gm A A)": {"all_sung_frames": pick(orn), "per_line": {ln: pick(ref["per_line"][ln]) for ln in LINES},
                                                                                      "frame_mode": pick(ref["frame"])},
        "chosen_against_baseline_in_points": {
            "chord_tone": diff(bn, ban, "chord_tone"), "on_beat_chord_tone": diff(bn, ban, "on_beat_chord_tone"),
            "line_end_chord_tone": diff(bn, ban, "line_end_chord_tone"), "clash_any": diff(bn, ban, "clash_any"),
            "clash_sustained": diff(bn, ban, "clash_sustained"), "sustained_clash_runs_in_the_song": [bn["sustained_clash_runs"], ban["sustained_clash_runs"]],
            "outside_scale": diff(bn, ban, "outside_scale"), "sounding_semitone": diff(bn, ban, "sounding_semitone"),
            "sounding_semitone_sustained": diff(bn, ban, "sounding_semitone_sustained"), "J": round(bn["J"] - ban["J"], 3),
            "frame_mode_chord_tone": diff(best["frame"], base["frame"], "chord_tone"), "frame_mode_clash_sustained": diff(best["frame"], base["frame"], "clash_sustained")},
        "chosen_against_the_original_loop_in_points": {"chord_tone": diff(bn, orn, "chord_tone"), "clash_any": diff(bn, orn, "clash_any"),
                                                       "clash_sustained": diff(bn, orn, "clash_sustained"),
                                                       "sustained_clash_runs_in_the_song": [bn["sustained_clash_runs"], orn["sustained_clash_runs"]],
                                                       "line_end_chord_tone": diff(bn, orn, "line_end_chord_tone")},
        "bar_0_verse_opening_compared": {
            "about": "frames of line 1 only (12.79 s). band_model_beats_0_1 = what sounds against the voice under 'Ali Baba'nin'. "
                     "rendered_audio: share of the sung time with band energy ON the sung pitch above -6 dB re one strummed chord note "
                     "(note pitch / every frame's own pitch), and one semitone next to it.",
            **{("%s (%s)" % (seq, who)): {
                "chord_changes_inside_the_bar": b0[seq]["changes_inside_the_bar"], "inside_strict_rules": b0[seq]["passes_strict_rules"],
                "inside_turnaround_rules": b0[seq]["passes_turnaround_rules"],
                "note_mode": b0[seq]["note"], "frame_mode": b0[seq]["frame"],
                "band_model_beats_0_1": {k: b0[seq]["band_model_beats_0_1"][k] for k in ("band_same_pitch_class", "band_unison", "whole_tone_same_octave", "sounding_semitone")},
                "rendered_audio_beats_0_1": {"support_share_above_-6_db": S[an_]["bar_0_beats_0_1"]["support_share_above_-6_db"],
                                             "frame_pitch_support_share_above_-6_db": S[an_]["bar_0_beats_0_1"]["frame_pitch_support_share_above_-6_db"],
                                             "rub_share_above_-6_db": S[an_]["bar_0_beats_0_1"]["rub_share_above_-6_db"]}}
               for seq, who, an_ in (("ii ii I I", "chosen", CH), ("V IV I I", "runner-up", RU_), ("I IV I I", "designer A", A_), ("I I IV I", "plain baseline", BASE))},
            "gliding_syllable_li": gl},
        "seventh_of_the_dominant": {
            "about": "bars 2 and 6 with the seventh in the band; chord-level numbers on the frames of that line, band model and rendered audio",
            "bar_2_L2": {o: {"chord_tone": s2("L2", o, "note", "chord_tone"), "on_beat_chord_tone": s2("L2", o, "note", "on_beat_chord_tone"),
                             "clash_any": s2("L2", o, "note", "clash_any"), "clash_sustained": s2("L2", o, "note", "clash_sustained"),
                             "J_note": s2("L2", o, "note", "J"), "J_frame": s2("L2", o, "frame", "J"), "J_second_tracker": s2("L2", o, "dio", "J"),
                             "sounding_semitone": s2("L2", o, "note", "sounding_semitone"), "sounding_semitone_sustained": s2("L2", o, "note", "sounding_semitone_sustained")}
                         for o in st2["L2"]},
            "bar_6_L4": {o: {"chord_tone": s2("L4", o, "note", "chord_tone"), "on_beat_chord_tone": s2("L4", o, "note", "on_beat_chord_tone"),
                             "clash_any": s2("L4", o, "note", "clash_any"), "clash_sustained": s2("L4", o, "note", "clash_sustained"),
                             "J_note": s2("L4", o, "note", "J"), "J_frame": s2("L4", o, "frame", "J"), "J_second_tracker": s2("L4", o, "dio", "J"),
                             "sounding_semitone": s2("L4", o, "note", "sounding_semitone"), "sounding_semitone_sustained": s2("L4", o, "note", "sounding_semitone_sustained")}
                         for o in st2["L4"]},
            "rendered_audio_beat_3_of_bars_2_and_6": {"V V V V (chosen)": aud(CH, "bars_2_6_beat_3"), "V V V V7": aud("V7_son_vurus_V-V-V-V7", "bars_2_6_beat_3")},
            "rendered_audio_bars_2_and_6": {"V V V V (chosen)": aud(CH, "L2_and_L4_bars_2_6"), "V V V V7": aud("V7_son_vurus_V-V-V-V7", "L2_and_L4_bars_2_6"),
                                            "V7 V7 V7 V7": aud("V7_tum_olcu", "L2_and_L4_bars_2_6")}},
        "rendered_audio_check": {
            "what": "pitched accompaniment rendered with FluidSynth (settings of build.py, ii and V voiced as above); rub = band power one semitone "
                    "next to the sung note, support = band power on the sung note (same octave and octave below), dB re one strummed chord note; "
                    "shares of the sung time. Details and every stretch: ses_olcumu.json.",
            "all_sung_frames": {"chosen": aud(CH, "all_sung_frames"), "runner_up": aud(RU_, "all_sung_frames"),
                                "designer_A_plan": aud(A_, "all_sung_frames"), "plain_baseline": aud(BASE, "all_sung_frames")},
            "L1_bar_0": {"chosen": aud(CH, "L1_bar_0"), "runner_up": aud(RU_, "L1_bar_0"), "designer_A_plan": aud(A_, "L1_bar_0"), "plain_baseline": aud(BASE, "L1_bar_0")},
            "bar_5_beats_2_3": {"I I (chosen)": aud(CH, "diye_bar_5"), "V V": aud("olcu5_V-V", "diye_bar_5")},
            "caveat": "the semitone bands also catch overtones of consonant band notes and the attack noise of every strum; only the large "
                      "differences and the runs above -6 dB are meaningful."}},
    "key_comparison": {
        "about": "best plan per key from I ii iii IV V V7 vi; J = chord_tone - 2 * (clash_sustained + outside_scale). 'strict' / 'turnaround' = the two "
                 "rule sets, 'free' = no rule at all (what the rules cost).",
        "per_key": {k: {"plain_baseline": pick(P["%s plain baseline" % k]["note"], KEYS),
                        "best_strict_rules": {"bars": P["%s best by fit, strict rules" % k]["bars"], **pick(P["%s best by fit, strict rules" % k]["note"], KEYS)},
                        "best_turnaround_rules": {"bars": P["%s best by fit, turnaround rules" % k]["bars"], **pick(P["%s best by fit, turnaround rules" % k]["note"], KEYS)},
                        "best_any_sequence": {"bars": P["%s best by fit, any sequence" % k]["bars"], **pick(P["%s best by fit, any sequence" % k]["note"], KEYS)}}
                    for k in ("C", "F", "G")},
        "score_by_weight": {w: {rs: d[rs]["score"] for rs in ("rules", "turnaround", "free")} for w, d in SCAN["weight_robustness"].items()},
        "why_C": "All five sung pitch classes (D E F G A) are in C major. In G major the sung F natural is outside the scale for %s %% of the sung time. "
                 "F major reaches the same chord tones only when no rule applies (the search then picks the very same triads); as soon as the loud "
                 "answer has to be reached from I, IV or V and bar 6 has to end on V7 or I, the last note of lines 2 and 4 (D) is in neither chord: "
                 "the phrase ends are chord tones for %s %% of their time in F against %s %% in C, and sustained clashes rise to %s %%. C is first "
                 "inside the rules for the weights 1, 2 and 4. In C the triad that fits lines 2 and 4 (G B D) is the DOMINANT, so every sung phrase "
                 "that ends on it is answered by the tonic." % (
                     p1(P["G plain baseline"]["note"]["outside_scale"]), p1(P["F best by fit, strict rules"]["note"]["line_end_chord_tone"]),
                     p1(P["C best by fit, strict rules"]["note"]["line_end_chord_tone"]), p1(P["F best by fit, strict rules"]["note"]["clash_sustained"]))},
    "alternatives_measured": {name[2:]: {"plan": Pn["label"], "bars": Pn["bars"], **pick(Pn["note"]), "J_frame": Pn["frame"]["J"],
                                         "frame_chord_tone": Pn["frame"]["chord_tone"], "frame_clash_sustained": Pn["frame"]["clash_sustained"]}
                              for name, Pn in P.items() if name.startswith("C ") and name[2:] in (
                                  "variant_ii_V_I", "symbolic_optimum_strict", "symbolic_optimum_turnaround", "seventh_everywhere", "designer_A",
                                  "tonic_first_half_bars_2_6", "L1_ends_on_V", "bar_5_on_V", "V_vi_I_I", "V_ii_I_I", "I_ii_V_I")},
    "how_the_plan_was_chosen": {
        "step_1": "Every sequence of I ii iii IV V V7 vi (one chord per beat) was measured for each sung bar in C, F and G: 3 x (3 x 2401 + 49) = "
                  "%d sequences (adaylar.json). Ranking J = chord_tone - 2 * (clash_sustained + outside_scale), the score designer A uses." % sum(SCAN["sequences_measured_per_key"].values()),
        "step_2": "Progression rules (kod/kurallar.py): bar 6 ends on V, V7 or I; the chord before a bar that is not sung is I, IV, V or V7; the "
                  "dominant only goes to the tonic; at least two beats of I, IV, V per sung bar. Ties within 0.005: fewer chord changes, two-beat "
                  "chords, more on-beat chord tones. Result in C: ii ii I I | V V V V7 | I I | V V V V7. A second rule set that also allows the "
                  "turnaround V - IV - I gives V IV I I in bar 0 (the runner-up).",
        "step_3": "The seventh of the dominant, decided by what really sounds (band model checked against the builder's MIDI, and rendered audio): "
                  "the symbolic optimum puts V7 on the last beat of bars 2 and 6 because a sung F then counts as a chord tone; in the band that F "
                  "sounds while the singer's E is next to it. Without the seventh nothing sounds a semitone from the voice in bars 2 and 6.",
        "robustness": {"strict_rules": rob["strict"], "turnaround_rules_bar_0": rob["turnaround"]["0"],
                       "note": M["robustness_of_the_choice"]["how_to_read"],
                       "weights": "bar 0 = ii ii I I for the weights 1, 2 and 4 (strict rules) and V IV I I for all three (turnaround rules); bars 2 and 6 "
                                  "stay on the dominant for all three; with weight 4 bar 5 flips to V V (see trade-offs)."},
        "cross_checks": "The frame table reproduces the pitch-class histogram of kesim.json and matches an independent pitch track of the PLACED vocal "
                        "(vokal_dogal.wav). The metric code is an independent re-implementation of designer A's and gives the same numbers for the "
                        "baselines, the original loop and A's plan. kod/07_dogrula.py recomputes the numbers of this file by two separate routes."},
    "reasoning": [
        "The sung melody is not the Old MacDonald tune. Its notes are D E F G A, G alone is %s %% of the sung time. Under the plain harmony "
        "I I IV I only %s %% of the sung time is on chord tones, %s %% is in sustained clashes (%d runs) and the last note of a line is a chord "
        "tone only %s %% of its time." % (p1(PCS["G"]), p1(ban["chord_tone"]), p1(ban["clash_sustained"]), ban["sustained_clash_runs"], p1(ban["line_end_chord_tone"])),
        "Line 1 (D on beat 0, G on the half beat, A A A on beat 1 | G G | G F E). The two strong notes of the first half are D and A; D minor is the "
        "only diatonic triad of C major that holds both, so ii carries beats 0-1 as ONE two-beat chord: on-beat chord tones of the line %s %% "
        "against %s %% for I IV and %s %% for the plain harmony. The G on the half beat is short (%d ms on G, the voice is on A from beat 0.78). "
        "Beats 2-3 rest on I: G and the final E are chord tones, the F in between passes. These are the very chords this vocal was made over in "
        "the original take (Dm Dm C C), now heard as ii - I of C major." % (
            p1(b0["ii ii I I"]["note"]["on_beat_chord_tone"]), p1(b0["I IV I I"]["note"]["on_beat_chord_tone"]), p1(b0["I I IV I"]["note"]["on_beat_chord_tone"]),
            gl["ms_per_verse_by_pitch"]["G4 +-50 cents"]),
        "Lines 2 and 4 (D G | G G | F E | F E D). The first half is G: I, iii and V all hold it. In the second half F (on the beat) and E (off the "
        "beat) alternate: every triad with an F rubs the E and every triad with an E rubs the F; G B D is the only diatonic triad with neither, "
        "and it holds the final D. So V for the whole bar: no clash at all in line 2 (%s %%), %s %% in line 4 (the mis-pitched first syllable of verses 3 and 7), against "
        "%s %% and %s %% sustained under the plain harmony. The phrase closes on the fifth of the dominant and the band answers on the tonic." % (
            p1(L["L2"]["clash_any"]), p1(L["L4"]["clash_any"]), p1(base["per_line"]["L2"]["clash_sustained"]), p1(base["per_line"]["L4"]["clash_sustained"])),
        "'diye bagirir' (G G | G F E) stays on I, as in the original take: %s %% chord tones, the final E is the third of the tonic. On rendered "
        "audio V V does not lower the rub there and supports the voice less (%s %% against %s %% of the time)." % (
            p1(L["diye"]["chord_tone"]), p1(S["olcu5_V-V"]["diye_bar_5"]["support_share_above_-6_db"]), p1(S[CH]["diye_bar_5"]["support_share_above_-6_db"])),
        "No minor chord other than ii helps, and no chord of F or G major does better inside the rules: with all seven chords free on every beat "
        "the search returns the tonic and the dominant for bars 2, 5 and 6, exactly what designer A found with three chords. The freedom of this "
        "design changes one thing, the first half of bar 0.",
        "Result against the plain harmony: chord tones %s -> %s %%, sustained clash %s -> %s %% (%d -> %d runs in the whole song), on-beat chord "
        "tones %s -> %s %%, phrase ends on a chord tone %s -> %s %%, a band note a semitone from the voice %s -> %s %% of the sung time. Against the "
        "ORIGINAL D minor loop the plan has about the same chord tones (%s against %s %%) and a fraction of its sustained clashes (%s against %s %%)." % (
            p1(ban["chord_tone"]), p1(bn["chord_tone"]), p1(ban["clash_sustained"]), p1(bn["clash_sustained"]), ban["sustained_clash_runs"], bn["sustained_clash_runs"],
            p1(ban["on_beat_chord_tone"]), p1(bn["on_beat_chord_tone"]), p1(ban["line_end_chord_tone"]), p1(bn["line_end_chord_tone"]),
            p1(ban["sounding_semitone"]), p1(bn["sounding_semitone"]), p1(bn["chord_tone"]), p1(orn["chord_tone"]), p1(bn["clash_sustained"]), p1(orn["clash_sustained"])),
        "Sense of key: 30 of the 32 beats of a verse are on I or V(7); the only other chord is ii for two beats, and it resolves to the tonic "
        "inside its own bar, so each loud answer is entered from I (bar 0) or from V (bar 6)."],
    "trade_offs_stated_plainly": [
        "The chosen plan is not the highest-scoring one. The runner-up (V IV I I in bar 0) has %s points more chord tones in note mode (%s in frame "
        "mode) and fewer major seconds between band and voice in beats 0-1; it was placed second for the harmonic rhythm and the progression, "
        "not for its fit." % (diff(rn, bn, "chord_tone"), diff(ru["frame"], best["frame"], "chord_tone")),
        "Every verse opens on a minor chord for two beats. Whether that colour suits the cheerful band was not heard by anyone.",
        "On the half beat of beat 0 the sung G sits between the F and the A of the D minor strum (two major seconds, about %d ms per verse). "
        "The runner-up and designer A's bar double that G instead; designer A's bar leaves the D on the downbeat a major second above the piano's C." % gl["ms_per_verse_by_pitch"]["G4 +-50 cents"],
        "In bars 2 and 6 the band plays no seventh, so the F and E of the animal word and of 'Ali Baba'nin' float above the G triad as seventh and "
        "sixth: chord tones %s / %s %% there, below the plain harmony's %s / %s %%, and a band note a whole tone from the voice sounds for about a "
        "third of those lines. That is the price of having no semitone rub at all in them." % (
            p1(L["L2"]["chord_tone"]), p1(L["L4"]["chord_tone"]), p1(base["per_line"]["L2"]["chord_tone"]), p1(base["per_line"]["L4"]["chord_tone"])),
        "What remains: the passing F of '-ligi var' and 'bagirir' over the C chord (%s %% of the sung time a semitone from a sounding band note; "
        "%d runs just over 150 ms in the whole song)." % (p1(bn["sounding_semitone"]), bn["sustained_clash_runs"]),
        "Bar 5 is the least certain bar: I I wins in note mode (J %s against %s) and V V in frame mode, where the glide G - F sharp - F counts as "
        "one long clash against C. I I was kept because the line ends on E, the third of the tonic, and because the rendered audio shows no gain for V V." % (
            P["C BEST"]["per_line"]["diye"]["J"], P["C bar_5_on_V"]["per_line"]["diye"]["J"]),
        "The chord-level metrics treat every chord as sounding for its whole beat; the band model and the rendered audio correct for that, but the "
        "ii voicing they use is a proposal, not something the builder has rendered in the full mix."],
    "not_verified_by_ear": "Nobody listened. Verified by code: the frame table reproduces kesim.json and matches the placed vocal, the band model "
                           "reproduces the builder's MIDI for I, IV and V7, the tune model reproduces the stem's MIDI, the metric code reproduces "
                           "designer A's numbers, and 07_dogrula.py recomputes this file by separate routes. Unverified by ear: that ii at the verse "
                           "opening sounds right in the cheerful band, that the dominant without its seventh is full enough, that the remaining "
                           "passing F is harmless, and the ranking of the chosen plan against the runner-up.",
    "files": {"all_candidates": "adaylar.json", "measurements": "olcum.json", "audio_check": "ses_olcumu.json", "verification": "dogrulama.txt",
              "scripts": "kod/ (kod/calistir.sh reruns everything in about 4 minutes)", "intermediate": "ara/ (frame table, search summary, MIDI of the rendered checks, logs)"},
}
save_json(os.path.join(T, "plan.json"), plan)
print("written: plan.json")
print("chosen:", plan["harmony_plan"]["chord_names_per_beat"])
print("runner-up:", plan["runner_up"]["chord_names_per_beat"])
print("chosen vs baseline (points):", plan["metrics"]["chosen_against_baseline_in_points"])
