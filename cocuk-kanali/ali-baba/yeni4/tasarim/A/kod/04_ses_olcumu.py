#!/usr/bin/env python3
"""Step 4: audio check of the decisive question (which chord on beat 2 of bars 2 and 6?), on RENDERED band audio.

The chord-level clash metric assumes that a chord sounds during its whole beat. In the oom-pah band it does not: on
beats 0 and 2 only bass, root octaves and one banjo note are struck. Reverb and release tails could still carry the
third of the previous strum, so this is measured on audio instead of being assumed:

  1. the pitched accompaniment (bass, banjo, accordion, piano, brass stab; no drums, no lead) of one verse cycle
     (the answer bar before the verse + the 8 verse bars) is rendered with FluidSynth for each finalist plan, with the
     patches, volumes, pans, reverb sends, track delays and gain of yeni4/altyapi/kod/build.py;
  2. the band signal is split into semitone bands (+-50 cents, zero-phase Butterworth) and their envelopes are read
     at the time of every sung frame (all 7 verses are laid over the same band cycle; the pitched band parts are
     identical in every verse);
     (pitch of a sung frame = the note it belongs to, as in olcum.json);
  3. "rub level" of a sung frame = power of the band in the two semitone bands next to the sung pitch (same octave),
     in dB relative to ONE CHORD NOTE OF A STRUM (peak of the E4 band in the first off-beat strum of the verse).

Nothing here is listened to; it measures how much band energy sits one semitone from the voice while it sings.
"""
import sys, os, subprocess
import numpy as np, mido, soundfile as sf
from scipy.signal import butter, sosfiltfilt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
from olcut import Frames, run_mask
from bant import Band, BASS, BANJO, ACC, PNO, BRS

SF2 = '/usr/share/sounds/sf2/FluidR3_GM.sf2'
import tempfile
SES = os.path.join(ARA, "ses"); os.makedirs(SES, exist_ok=True)            # the MIDI of every rendered plan stays here
# the rendered WAVs (12 MB per plan) are scratch: they go to a work folder outside the project, as build.py does
WORK = os.environ.get("ALIBABA_WORK") or os.path.join(tempfile.gettempdir(), "alibaba_yeni4_tasarimA_work")
os.makedirs(WORK, exist_ok=True)
sr = 44100; TPB = 480; PRE = 1.0; LAT = 82
TEMPO_US = int(round(60e6 / BPM)); BEAT_MIDI = TEMPO_US / 1e6
PROG = {BASS: 33, BANJO: 105, ACC: 21, PNO: 1, BRS: 61}
VOL = {BASS: 113, BANJO: 104, ACC: 86, PNO: 100, BRS: 102}
PAN = {BASS: 64, BANJO: 36, ACC: 94, PNO: 54, BRS: 70}
REV = {BASS: 8}
ADV = {BASS: 19, ACC: 19, BRS: 7}
KINDS = ['voc', 'voc', 'voc', 'slot', 'slot', 'fillin', 'voc', 'voc']
ANSWER = ['I', 'V7', 'I', 'I']

L1BAR = ['I', 'IV', 'I', 'I']
PLANS = {                                             # names as in olcum.json; "V" = the dominant without its seventh in the band
    "taban_I-I-IV-I": {0: ['I', 'I', 'IV', 'I'], 2: ['I', 'I', 'IV', 'I'], 5: ['I', 'I'], 6: ['I', 'I', 'IV', 'I']},
    "A_V7-V7-V7-V7": {0: L1BAR, 2: ['V7'] * 4, 5: ['I', 'I'], 6: ['V7'] * 4},
    "Ay_V-V-V-V_SECILEN": {0: L1BAR, 2: ['V'] * 4, 5: ['I', 'I'], 6: ['V'] * 4},
    "Ayk_V-V-V-V_kok_bas": {0: L1BAR, 2: ['V'] * 4, 5: ['I', 'I'], 6: ['V'] * 4, "root_bass_bars": (2, 6)},
    "B_I-I-V7-V7": {0: L1BAR, 2: ['I', 'I', 'V7', 'V7'], 5: ['I', 'I'], 6: ['I', 'I', 'V7', 'V7']},
    "By_I-I-V-V": {0: L1BAR, 2: ['I', 'I', 'V', 'V'], 5: ['I', 'I'], 6: ['I', 'I', 'V', 'V']},
    "C_I-I-I-V7": {0: L1BAR, 2: ['I', 'I', 'I', 'V7'], 5: ['I', 'I'], 6: ['I', 'I', 'I', 'V7']},
    "Cy_I-I-I-V": {0: L1BAR, 2: ['I', 'I', 'I', 'V'], 5: ['I', 'I'], 6: ['I', 'I', 'I', 'V']},
    "D_I-I-IV-V7": {0: L1BAR, 2: ['I', 'I', 'IV', 'V7'], 5: ['I', 'I'], 6: ['I', 'I', 'IV', 'V7']},
}


def plan8(bars):
    p = [None] * 8
    p[0] = bars[0]; p[1] = ANSWER; p[2] = bars[2]; p[3] = ['I'] * 4; p[4] = ['I'] * 4
    p[5] = ['I', 'I'] + bars[5]; p[6] = bars[6]; p[7] = ANSWER
    return p


def render(name, bars, band):
    kinds = ['voc_root' if (k == 'voc' and i in bars.get("root_bass_bars", ())) else k for i, k in enumerate(KINDS)]
    seq = [('voc', ANSWER)] + list(zip(kinds, plan8(bars)))                    # bar -1 (answer) + the verse
    mid = mido.MidiFile(ticks_per_beat=TPB); tr = mido.MidiTrack(); mid.tracks.append(tr)
    msgs = [(0, 0, mido.MetaMessage('set_tempo', tempo=TEMPO_US))]
    for c in PROG:
        msgs += [(0, 1, mido.Message('program_change', channel=c, program=PROG[c])),
                 (0, 1, mido.Message('control_change', channel=c, control=10, value=PAN[c])),
                 (0, 1, mido.Message('control_change', channel=c, control=7, value=VOL[c])),
                 (0, 1, mido.Message('control_change', channel=c, control=91, value=REV.get(c, 40)))]
    for i, (kind, ch) in enumerate(seq):
        for (bt, dur, c, n, vel) in band.bar(kind, ch):
            b = i * 4 + bt; adv = ADV.get(c, 0)
            msgs.append((round((PRE + b) * TPB) - adv, 3, mido.Message('note_on', channel=c, note=n, velocity=vel)))
            msgs.append((round((PRE + b + dur) * TPB) - adv, 2, mido.Message('note_off', channel=c, note=n, velocity=0)))
    msgs.append((round((PRE + len(seq) * 4 + 8) * TPB), 4, mido.Message('control_change', channel=15, control=7, value=100)))
    msgs.sort(key=lambda m: (m[0], m[1])); t = 0
    for (tk, _, m) in msgs:
        tr.append(m.copy(time=tk - t)); t = tk
    pm = os.path.join(SES, name + ".mid"); pw_ = os.path.join(WORK, name + ".wav")
    mid.save(pm)
    subprocess.run(['fluidsynth', '-ni', '-q', '-g', '0.22', '-r', str(sr), '-O', 'float', '-F', pw_, SF2, pm], check=True, capture_output=True)
    x, r_ = sf.read(pw_, dtype='float64'); assert r_ == sr
    x = x[int(round(PRE * BEAT_MIDI * sr)) + LAT:]
    return x.mean(axis=1)                                                       # time 0 = downbeat of the answer bar before the verse


def envelopes(x, notes):
    """-> dict note -> amplitude envelope (per sample) of the +-50 cent band around the note"""
    out = {}
    n = int(0.020 * sr) | 1
    h = np.hanning(n + 2)[1:-1]; h /= h.sum()
    for m in notes:
        f = 440.0 * 2 ** ((m - 69) / 12)
        sos = butter(4, [f * 2 ** (-1 / 24), f * 2 ** (1 / 24)], btype="band", fs=sr, output="sos")
        y = sosfiltfilt(sos, x)
        out[m] = np.sqrt(np.convolve(y ** 2, h, "same") * 2)                    # *2: sine amplitude
    return out


F = Frames()
band = Band("C")
NOTES = list(range(56, 74))
tcyc = (F.pos + 4.0) * BEAT                                                      # time of every sung frame in the band cycle
si = np.round(tcyc * sr).astype(int)
# Pitch of a sung frame = the NOTE it belongs to (as in olcum.json, note mode). Rounding every frame on its own would
# count the 20-40 ms of a glide INTO a note the band also plays as "one semitone from the band" and so punish unisons.
MODE = sys.argv[1] if len(sys.argv) > 1 else "note"
nf = np.round(F.note_midi if MODE == "note" else F.midi).astype(int)
assert nf.min() >= 57 and nf.max() <= 72, (nf.min(), nf.max())
bar_of = np.floor(F.pos / 4 + 1e-9).astype(int); beat_in = F.pos - 4 * bar_of
focus = np.isin(bar_of, (2, 6)) & (beat_in >= 1.9)                              # the F-E-F-E-D figure of L2 and L4

beat2 = focus & (beat_in < 2.95)                                                # ... its first half: F on the beat, E on the off-beat
beat3 = focus & (beat_in >= 2.95)                                               # ... its second half: F E D
STRETCH = (("all_sung_frames", np.ones(F.n, bool)), ("L2_and_L4_whole_bars", np.isin(bar_of, (2, 6))),
           ("bars_2_and_6_beat_2_only", beat2), ("bars_2_and_6_beat_3_only", beat3),
           ("L1_bar_0", bar_of == 0), ("diye_bar_5", bar_of == 5))
CHOSEN_NAME = "Ay_V-V-V-V_SECILEN"
res = {}; course = {}
for name, bars in PLANS.items():
    x = render(name, bars, band)
    env = envelopes(x, NOTES)
    # reference: one chord note of a strum = peak of the E4 band in the first off-beat strum of the verse (bar 0, beat 0.5 .. 0.78)
    a = int((4 + 0.5) * BEAT * sr); b = int((4 + 0.80) * BEAT * sr)
    ref = env[64][a:b].max()
    lo = np.array([env[n - 1][i] for n, i in zip(nf, si)]); hi = np.array([env[n + 1][i] for n, i in zip(nf, si)])
    rub = 10 * np.log10((lo ** 2 + hi ** 2) / ref ** 2 + 1e-12)
    if name == CHOSEN_NAME:
        chosen_rub = (rub.copy(), lo > hi)
    e = {"reference_E4_strum_peak_dbfs": r(20 * np.log10(ref), 1)}
    for nm_, m in STRETCH:
        d = {"sung_s": r(m.sum() * FP, 2), "mean_power_db_re_strum_note": r(10 * np.log10(np.mean(10 ** (rub[m] / 10))), 1),
             "median_db_re_strum_note": r(np.median(rub[m]), 1)}
        for th_ in (-6, -12, -20):
            flag = (rub > th_) & m
            sus, runs = run_mask(flag, F.t, F.verse)
            d["share_above_%d_db" % th_] = r(flag.sum() / m.sum())
            d["share_above_%d_db_in_runs_over_150ms" % th_] = r(sus.sum() / m.sum())
            d["runs_over_150ms_above_%d_db" % th_] = len(runs)
        e[nm_] = d
    res[name] = e
    # time course of the E4 and F4 bands through verse bar 2 and bar 6 (dB re the strum note), 1/8-beat steps
    tc = {}
    for bar in (2, 6):
        rows = []
        for q in np.arange(1.5, 4.0, 0.125):
            a = int(((bar + 1) * 4 + q) * BEAT * sr); b = int(((bar + 1) * 4 + q + 0.125) * BEAT * sr)
            rows.append({"beat": float(q), "E4_db": r(20 * np.log10(np.sqrt(np.mean(env[64][a:b] ** 2)) / ref + 1e-9), 1),
                         "F4_db": r(20 * np.log10(np.sqrt(np.mean(env[65][a:b] ** 2)) / ref + 1e-9), 1),
                         "D4_db": r(20 * np.log10(np.sqrt(np.mean(env[62][a:b] ** 2)) / ref + 1e-9), 1)})
        tc[str(bar)] = rows
    course[name] = tc

print("rub level = band power one semitone from the sung pitch, dB re one strummed chord note; shares of the sung time of the stretch")
for nm_, _m in STRETCH:
    print(" ", nm_)
    for name in PLANS:
        d = res[name][nm_]
        print("    %-20s mean %6.1f dB  median %6.1f dB | above -6 dB: %5.1f %% (runs>150ms %5.1f %%, %2d) | above -12 dB: %5.1f %% (%5.1f %%, %2d) | above -20 dB: %5.1f %% (%5.1f %%, %2d)" % (
            name, d["mean_power_db_re_strum_note"], d["median_db_re_strum_note"],
            100 * d["share_above_-6_db"], 100 * d["share_above_-6_db_in_runs_over_150ms"], d["runs_over_150ms_above_-6_db"],
            100 * d["share_above_-12_db"], 100 * d["share_above_-12_db_in_runs_over_150ms"], d["runs_over_150ms_above_-12_db"],
            100 * d["share_above_-20_db"], 100 * d["share_above_-20_db_in_runs_over_150ms"], d["runs_over_150ms_above_-20_db"]))
print("band level of E4 / F4 in verse bar 2 (dB re one strummed chord note), per 1/8 beat:")
for name in ("Ay_V-V-V-V_SECILEN", "Ayk_V-V-V-V_kok_bas", "A_V7-V7-V7-V7", "C_I-I-I-V7", "taban_I-I-IV-I"):
    print("  %s" % name)
    print("     beat " + " ".join("%6.2f" % q["beat"] for q in course[name]["2"]))
    print("     E4   " + " ".join("%6.1f" % q["E4_db"] for q in course[name]["2"]))
    print("     F4   " + " ".join("%6.1f" % q["F4_db"] for q in course[name]["2"]))

# ---- where the rub of the chosen plan comes from: per bar / half beat / sung note, with the band notes struck there (model) ----
import collections
rub_c, lower_c = chosen_rub
cnt = collections.Counter(); tot = collections.Counter()
half = np.round(np.floor(beat_in * 2 + 1e-9) / 2, 1)
for k in range(F.n):
    key = (int(bar_of[k]), float(half[k]), NOTE[nf[k] % 12])
    tot[key] += 1
    if rub_c[k] > -6:
        cnt[key + ("below" if lower_c[k] else "above",)] += 1
p8 = plan8(PLANS[CHOSEN_NAME])
where = []
for key, c in sorted(cnt.items(), key=lambda q: -q[1])[:12]:
    b_, q_, nm_, side = key
    snd_ = sorted({n for (t0, d, ch, n, v) in band.bar(KINDS[b_], p8[b_]) if t0 < q_ + 0.5 and t0 + d > q_})
    target = (PC[nm_] + (-1 if side == "below" else 1)) % 12
    real = any(n % 12 == target for n in snd_)
    where.append({"bar": b_, "half_beat_from": q_, "sung": nm_, "seconds_above_-6_db": r(c * FP, 2), "share_of_all_sung_time": r(c / F.n),
                  "band_energy_is": "a semitone %s the voice (%s)" % (side, NOTE[target]),
                  "band_notes_struck_there": " ".join("%s%d" % (NOTE[n % 12], n // 12 - 1) for n in snd_),
                  "a_band_note_of_that_pitch_class_is_struck": bool(real)})
print("where the rub above -6 dB of the chosen plan comes from (top 12 of %.1f %%):" % (100 * np.mean(rub_c > -6)))
for w in where:
    print("   bar %d beat %.1f sung %-2s %5.2f s (%4.1f %%)  %-34s struck: %-28s %s" % (
        w["bar"], w["half_beat_from"], w["sung"], w["seconds_above_-6_db"], 100 * w["share_of_all_sung_time"], w["band_energy_is"],
        w["band_notes_struck_there"], "REAL NOTE" if w["a_band_note_of_that_pitch_class_is_struck"] else "overtone / attack noise"))
real_share = sum(w["share_of_all_sung_time"] for w in where if w["a_band_note_of_that_pitch_class_is_struck"])

save_json(os.path.join(T, "ses_olcumu.json" if MODE == "note" else "ses_olcumu_kare_modu.json"), {
    "chosen_plan_breakdown": {"about": "the 12 largest contributions to the sung time with rub above -6 dB in the chosen plan. Only rows where a band note of the "
                                       "neighbouring pitch class is really struck are semitone coincidences; the others are overtones of consonant notes "
                                       "(the 5th harmonic of the bass D2 = F#4 under a sung F, the 3rd harmonic of B2 = F#4 under a sung G) and attack noise.",
                              "share_above_-6_db": r(np.mean(rub_c > -6)), "of_which_real_struck_notes_in_the_top_12": r(real_share), "rows": where},
    "pitch_mode": MODE + (" (a frame carries the pitch of the note it belongs to)" if MODE == "note" else " (every frame rounded on its own; glides into a unison with the band count as a rub)"),
    "about": "Audio check on rendered band audio (pitched accompaniment only, FluidSynth, settings of build.py): how much band energy lies one "
             "semitone from the sung pitch while the voice sings. rub level = power in the two semitone bands (+-50 cents) next to the sung "
             "pitch, same octave, in dB relative to one chord note of a strum (peak of the E4 band in the first off-beat strum of the verse). "
             "Shares are fractions of the sung time of the named stretch; runs follow the 150 ms rule of olcum.json. "
             "L2_and_L4_whole_bars = verse bars 2 and 6; beat_2_only = beat position 1.9 .. 2.95 of those bars (F on the beat, E on the off-beat); "
             "beat_3_only = 2.95 .. 4.0 (F E D). The semitone bands also catch the attack noise of every strum, so levels below about -12 dB are not "
             "evidence of a sounding note; the -6 dB rows are the robust ones.",
    "plans": {k: {str(b): list(v) for b, v in p.items()} for k, p in PLANS.items()},
    "results": res,
    "band_level_time_course": {"about": "RMS of the E4, F4 and D4 semitone bands in 1/8-beat steps through verse bars 2 and 6, dB re the strum note",
                               **course},
    "not_verified_by_ear": "This is a measurement of spectral energy next to the sung pitch; nobody listened."})
print("written: ses_olcumu%s.json" % ("" if MODE == "note" else "_kare_modu"))
