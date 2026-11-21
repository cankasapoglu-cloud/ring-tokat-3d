#!/usr/bin/env python3
"""Step 5: audio check on RENDERED band audio (adapted from yeni4/tasarim/A/kod/04_ses_olcumu.py).

The chord-level metrics assume that a chord sounds during its whole beat; the oom-pah band does not do that, and
reverb / release tails are not in the band model either. So the finalists are rendered and measured:

  1. the pitched accompaniment (bass, banjo, accordion, piano, brass stab; no drums, no lead) of one verse cycle
     (the answer bar before the verse + the 8 verse bars) is rendered with FluidSynth for each plan, with the patches,
     volumes, pans, reverb sends, track delays and gain of yeni4/altyapi/kod/build.py; the ii / V voicings are the
     ones proposed in bant.py;
  2. the band signal is split into semitone bands (+-50 cents, zero-phase Butterworth); their envelopes are read at
     the time of every sung frame (all 7 verses are laid over the same band cycle);
  3. per sung frame (pitch = the note the frame belongs to):
       rub      = band power in the two semitone bands NEXT TO the sung note (same octave)
       support  = band power in the band OF the sung note and of the octave below it
     both in dB relative to ONE CHORD NOTE OF A STRUM (peak of the E4 band in the first off-beat strum of the
     answer bar before the verse, which is the same I chord in every plan).

Nothing here is listened to. The semitone bands also catch overtones of consonant band notes and the attack noise of
every strum, so only large differences and the runs above -6 dB are meaningful.
"""
import sys, os, subprocess
import numpy as np, mido, soundfile as sf
from scipy.signal import butter, sosfiltfilt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
from olcut import Frames, run_mask
from bant import Band, BASS, BANJO, ACC, PNO, BRS, KINDS, ANSWER, plan8

SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
SES = os.path.join(ARA, "ses"); os.makedirs(SES, exist_ok=True)
sr = 44100; TPB = 480; PRE = 1.0; LAT = 82
TEMPO_US = int(round(60e6 / BPM)); BEAT_MIDI = TEMPO_US / 1e6
PROG = {BASS: 33, BANJO: 105, ACC: 21, PNO: 1, BRS: 61}
VOL = {BASS: 113, BANJO: 104, ACC: 86, PNO: 100, BRS: 102}
PAN = {BASS: 64, BANJO: 36, ACC: 94, PNO: 54, BRS: 70}
REV = {BASS: 8}
ADV = {BASS: 19, ACC: 19, BRS: 7}


def B(b0, b2, b5, b6, **kw):
    d = {0: b0.split(), 2: b2.split(), 5: b5.split(), 6: b6.split()}
    d.update(kw)
    return d


PLANS = {
    "taban_I-I-IV-I": B("I I IV I", "I I IV I", "I I", "I I IV I"),
    "SECILEN_ii-ii-I-I_V-V-V-V": B("ii ii I I", "V V V V", "I I", "V V V V"),
    "SECILEN_kok_bas": B("ii ii I I", "V V V V", "I I", "V V V V", root_bass_bars=(2, 6)),
    "SECILEN_acik3": B("ii ii I I", "V V V V", "I I", "V V V V", open3_bars=(0, 5)),
    "SECILEN_kok_bas_acik3": B("ii ii I I", "V V V V", "I I", "V V V V", open3_bars=(0, 5), root_bass_bars=(2, 6)),
    "IKINCI_V-IV-I-I_V-V-V-V": B("V IV I I", "V V V V", "I I", "V V V V"),
    "IKINCI_kok_bas": B("V IV I I", "V V V V", "I I", "V V V V", root_bass_bars=(2, 6)),
    "varyant_ii-ii-V-I": B("ii ii V I", "V V V V", "I I", "V V V V"),
    "V7_son_vurus_V-V-V-V7": B("ii ii I I", "V V V V7", "I I", "V V V V7"),
    "V7_tum_olcu": B("ii ii I I", "V7 V7 V7 V7", "I I", "V7 V7 V7 V7"),
    "tasarimci_A_I-IV-I-I_V-V-V-V": B("I IV I I", "V V V V", "I I", "V V V V"),
    "olcu5_V-V": B("ii ii I I", "V V V V", "V V", "V V V V"),
}
NAMES_EN = {
    "taban_I-I-IV-I": "plain baseline", "SECILEN_ii-ii-I-I_V-V-V-V": "CHOSEN plan",
    "SECILEN_kok_bas": "chosen + bass on the root on beat 2 of bars 2 and 6",
    "SECILEN_acik3": "chosen + on-beat strum of beat 3 without the third in bars 0 and 5",
    "SECILEN_kok_bas_acik3": "chosen + both refinements", "IKINCI_V-IV-I-I_V-V-V-V": "RUNNER-UP plan",
    "IKINCI_kok_bas": "runner-up + bass on the root on beat 2 of bars 2 and 6",
    "varyant_ii-ii-V-I": "chosen with ii ii V I in bar 0", "V7_son_vurus_V-V-V-V7": "chosen with V7 on the last beat of bars 2 and 6",
    "V7_tum_olcu": "chosen with V7 in all of bars 2 and 6", "tasarimci_A_I-IV-I-I_V-V-V-V": "designer A's plan as the band plays it",
    "olcu5_V-V": "chosen with V V on beats 2-3 of bar 5",
}


def render(name, bars, band):
    rb = bars.get("root_bass_bars", ()); o3 = bars.get("open3_bars", ())
    seq = [("voc", ANSWER, False, False)] + [(k, ch, i in rb, i in o3) for i, (k, ch) in enumerate(zip(KINDS, plan8(bars)))]
    mid = mido.MidiFile(ticks_per_beat=TPB); tr = mido.MidiTrack(); mid.tracks.append(tr)
    msgs = [(0, 0, mido.MetaMessage("set_tempo", tempo=TEMPO_US))]
    for c in PROG:
        msgs += [(0, 1, mido.Message("program_change", channel=c, program=PROG[c])),
                 (0, 1, mido.Message("control_change", channel=c, control=10, value=PAN[c])),
                 (0, 1, mido.Message("control_change", channel=c, control=7, value=VOL[c])),
                 (0, 1, mido.Message("control_change", channel=c, control=91, value=REV.get(c, 40)))]
    for i, (kind, ch, r_, o_) in enumerate(seq):
        for (bt, dur, c, n, vel) in band.bar(kind, ch, r_, o_):
            b = i * 4 + bt; adv = ADV.get(c, 0)
            msgs.append((round((PRE + b) * TPB) - adv, 3, mido.Message("note_on", channel=c, note=n, velocity=vel)))
            msgs.append((round((PRE + b + dur) * TPB) - adv, 2, mido.Message("note_off", channel=c, note=n, velocity=0)))
    msgs.append((round((PRE + len(seq) * 4 + 8) * TPB), 4, mido.Message("control_change", channel=15, control=7, value=100)))
    msgs.sort(key=lambda m: (m[0], m[1])); t = 0
    for (tk, _, m) in msgs:
        tr.append(m.copy(time=tk - t)); t = tk
    pm = os.path.join(SES, name + ".mid"); pw_ = os.path.join(SES, name + ".wav")
    mid.save(pm)
    subprocess.run(["fluidsynth", "-ni", "-q", "-g", "0.22", "-r", str(sr), "-O", "float", "-F", pw_, SF2, pm], check=True, capture_output=True)
    x, r_ = sf.read(pw_, dtype="float64"); assert r_ == sr
    x = x[int(round(PRE * BEAT_MIDI * sr)) + LAT:]
    os.remove(pw_)                                          # the 11 MB renders are not kept (the .mid is; re-rendering takes seconds)
    return x.mean(axis=1)                                   # time 0 = downbeat of the answer bar before the verse


def envelopes(x, notes):
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
NOTES = list(range(44, 75))
si = np.round((F.pos + 4.0) * BEAT * sr).astype(int)                             # sample of every sung frame in the band cycle
nf = np.round(F.note_midi).astype(int)
assert nf.min() >= 57 and nf.max() <= 72, (nf.min(), nf.max())
nff = np.clip(np.round(F.midi).astype(int), 57, 72)                             # frame mode: every frame's own pitch
bar_of = np.floor(F.pos / 4 + 1e-9).astype(int); beat_in = F.pos - 4 * bar_of
STRETCH = (("all_sung_frames", np.ones(F.n, bool)),
           ("L1_bar_0", bar_of == 0), ("bar_0_beats_0_1", (bar_of <= 0) & (beat_in < 1.95) | (F.pos < 0)), ("bar_0_beat_3", (bar_of == 0) & (beat_in >= 2.95)),
           ("L2_and_L4_bars_2_6", np.isin(bar_of, (2, 6))), ("bars_2_6_beat_2", np.isin(bar_of, (2, 6)) & (beat_in >= 1.9) & (beat_in < 2.95)),
           ("bars_2_6_beat_3", np.isin(bar_of, (2, 6)) & (beat_in >= 2.95)),
           ("diye_bar_5", bar_of == 5), ("bar_5_beat_3", (bar_of == 5) & (beat_in >= 2.95)))
res = {}
for name, bars in PLANS.items():
    x = render(name, bars, band)
    env = envelopes(x, NOTES)
    a = int(0.5 * BEAT * sr); b = int(0.80 * BEAT * sr)                          # first off-beat strum of the answer bar (I chord)
    ref = env[64][a:b].max()
    lo = np.array([env[n - 1][i] for n, i in zip(nf, si)]); hi = np.array([env[n + 1][i] for n, i in zip(nf, si)])
    un = np.array([env[n][i] for n, i in zip(nf, si)]); ob = np.array([env[n - 12][i] for n, i in zip(nf, si)])
    w2 = np.array([env[n - 2][i] ** 2 + env[n + 2][i] ** 2 for n, i in zip(nf, si)])
    rub = 10 * np.log10((lo ** 2 + hi ** 2) / ref ** 2 + 1e-12)
    sup = 10 * np.log10((un ** 2 + ob ** 2) / ref ** 2 + 1e-12)
    sec = 10 * np.log10(w2 / ref ** 2 + 1e-12)
    # the same support / rub read with every frame's OWN pitch (frame mode): is the band on the pitch the voice is on right now?
    supf = 10 * np.log10(np.array([env[n][i] ** 2 + env[n - 12][i] ** 2 for n, i in zip(nff, si)]) / ref ** 2 + 1e-12)
    rubf = 10 * np.log10(np.array([env[n - 1][i] ** 2 + env[n + 1][i] ** 2 for n, i in zip(nff, si)]) / ref ** 2 + 1e-12)
    e = {"reference_E4_strum_peak_dbfs": r(20 * np.log10(ref), 1), "options": {k: list(v) for k, v in bars.items() if isinstance(k, str)}}
    for nm_, m in STRETCH:
        d = {"sung_s": r(m.sum() * FP, 2),
             "rub_mean_power_db": r(10 * np.log10(np.mean(10 ** (rub[m] / 10))), 1), "rub_median_db": r(np.median(rub[m]), 1),
             "support_mean_power_db": r(10 * np.log10(np.mean(10 ** (sup[m] / 10))), 1), "support_median_db": r(np.median(sup[m]), 1),
             "whole_tone_neighbours_mean_power_db": r(10 * np.log10(np.mean(10 ** (sec[m] / 10))), 1)}
        for th_ in (-6, -12):
            flag = (rub > th_) & m
            sus, runs = run_mask(flag, F.t, F.verse)
            d["rub_share_above_%d_db" % th_] = r(flag.sum() / m.sum())
            d["rub_share_above_%d_db_in_runs_over_150ms" % th_] = r(sus.sum() / m.sum())
            d["rub_runs_over_150ms_above_%d_db" % th_] = len(runs)
        d["support_share_above_-6_db"] = r(((sup > -6) & m).sum() / m.sum())
        d["frame_pitch_support_share_above_-6_db"] = r(((supf > -6) & m).sum() / m.sum())
        d["frame_pitch_support_mean_power_db"] = r(10 * np.log10(np.mean(10 ** (supf[m] / 10))), 1)
        d["frame_pitch_rub_share_above_-6_db"] = r(((rubf > -6) & m).sum() / m.sum())
        e[nm_] = d
    res[name] = e

print("rub = band power one semitone from the sung note; support = band power on the sung note (same octave + octave below); dB re one strummed chord note")
for nm_, _m in STRETCH:
    print(" ", nm_, "(%.2f s)" % res["taban_I-I-IV-I"][nm_]["sung_s"])
    for name in PLANS:
        d = res[name][nm_]
        print("    %-32s rub: mean %6.1f dB median %6.1f | above -6 dB %5.1f %% (runs>150ms %5.1f %%, %2d) | above -12 dB %5.1f %% (%5.1f %%, %2d) || support: mean %6.1f dB, above -6 dB %5.1f %% || whole-tone neighbours mean %6.1f dB" % (
            name, d["rub_mean_power_db"], d["rub_median_db"], 100 * d["rub_share_above_-6_db"], 100 * d["rub_share_above_-6_db_in_runs_over_150ms"],
            d["rub_runs_over_150ms_above_-6_db"], 100 * d["rub_share_above_-12_db"], 100 * d["rub_share_above_-12_db_in_runs_over_150ms"],
            d["rub_runs_over_150ms_above_-12_db"], d["support_mean_power_db"], 100 * d["support_share_above_-6_db"], d["whole_tone_neighbours_mean_power_db"]))

save_json(os.path.join(T, "ses_olcumu.json"), {
    "about": "Audio check on rendered band audio (pitched accompaniment only, FluidSynth, settings of build.py; ii and V voiced as proposed in "
             "kod/bant.py). rub = band power in the two semitone bands (+-50 cents) next to the sung note, same octave; support = band power "
             "in the band of the sung note and of the octave below; whole_tone_neighbours = band power two semitones above and below the "
             "sung note. All in dB relative to one chord note of a strum (peak of the E4 band in the first off-beat strum of the answer bar "
             "before the verse, the same I chord in every plan). Shares are fractions of the sung time of the stretch; runs follow the "
             "150 ms rule of olcum.json. The semitone bands also catch overtones of consonant band notes and the attack noise of every "
             "strum: only large differences and the runs above -6 dB are meaningful.",
    "pitch_mode": "note (a frame carries the pitch of the note it belongs to); the frame_pitch_* fields use every frame's own rounded pitch instead "
                  "(for the rub this counts every glide into a unison with the band as a rub, so frame_pitch_rub is an upper bound)",
    "plans": {k: {"what": NAMES_EN[k], **{str(b): list(v) for b, v in p.items()}} for k, p in PLANS.items()},
    "options": {"open3_bars": "verse bars in which the on-beat strum of beat 3 leaves out the third of the chord (accordion + banjo strike root and "
                              "fifth, the banjo roll note is the fifth); the off-beat strum half a beat later is the full chord",
                "root_bass_bars": "verse bars in which the bass stays on the root on beat 2 (the builder plays the fifth there when beats 0-2 share a chord)"},
    "stretches": {"bar_0_beats_0_1": "L1 up to beat 1.95 ('Ali Baba'nin')", "bar_0_beat_3": "L1 from beat 2.95 ('-ligi var': G F E)",
                  "bars_2_6_beat_2": "beat position 1.9 .. 2.95 of bars 2 and 6 (F on the beat, E on the off-beat)",
                  "bars_2_6_beat_3": "2.95 .. 4.0 of bars 2 and 6 (F E D)", "bar_5_beat_3": "bar 5 from beat 2.95 ('-gi-rir': G F E)"},
    "results": res,
    "not_verified_by_ear": "This is a measurement of spectral energy next to / on the sung pitch; nobody listened."})
print("written: ses_olcumu.json")
