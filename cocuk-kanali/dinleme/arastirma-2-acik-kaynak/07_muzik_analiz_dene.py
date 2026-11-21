"""Arastirma-2 duman testi: klasik muzik analizi araclari (tempo, ton, dans edilebilirlik, ses yuksekligi, perde izleme).
Hepsinin agirligi ya yok (isaret isleme) ya da pip paketinin icinde. CPU sureleri 30 sn'lik klip icindir."""
import sys, time, os, warnings, glob
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf, librosa, torch
torch.set_num_threads(2)
import essentia; essentia.log.infoActive = False; essentia.log.warningActive = False
import essentia.standard as es
import pyloudnorm

def timed(fn):
    t = time.time(); r = fn(); return r, time.time() - t

def mix_analysis(f44):
    x, sr = sf.read(f44, dtype="float32"); assert sr == 44100
    out = {}
    (tempo_l, beats_l), dt = timed(lambda: librosa.beat.beat_track(y=x, sr=sr)); out["librosa tempo"] = (f"{float(np.atleast_1d(tempo_l)[0]):.1f} BPM", dt)
    (r), dt = timed(lambda: es.RhythmExtractor2013(method="multifeature")(x)); out["essentia tempo"] = (f"{r[0]:.1f} BPM, guven={r[2]:.2f}", dt)
    (k), dt = timed(lambda: es.KeyExtractor(profileType="edma")(x)); out["essentia ton"] = (f"{k[0]} {k[1]} guc={k[2]:.2f}", dt)
    (d), dt = timed(lambda: es.Danceability()(x)); out["essentia danceability (DFA, 0-3)"] = (f"{d[0]:.2f}", dt)
    (l), dt = timed(lambda: pyloudnorm.Meter(sr).integrated_loudness(x)); out["pyloudnorm LUFS"] = (f"{l:.1f} LUFS", dt)
    (dc), dt = timed(lambda: es.DynamicComplexity()(x)); out["essentia dinamik karmasiklik"] = (f"{dc[0]:.2f} dB", dt)
    oenv = librosa.onset.onset_strength(y=x, sr=sr); out["librosa vurus yogunlugu"] = (f"{len(librosa.onset.onset_detect(onset_envelope=oenv, sr=sr)) / (len(x)/sr):.2f} onset/sn", 0)
    return out

def pitch_analysis(f16):
    x, sr = sf.read(f16, dtype="float32"); assert sr == 16000
    out = {}
    def summ(f0, voiced):
        f = f0[voiced & (f0 > 0)]
        if len(f) < 5: return "sesli cerceve yok"
        midi = librosa.hz_to_midi(f); dev = (midi - np.round(midi)) * 100
        return f"sesli=%{100*voiced.mean():.0f} medyan={np.median(f):.0f}Hz aralik={np.percentile(midi,95)-np.percentile(midi,5):.1f} yarim ses, |cent sapma| medyan={np.median(np.abs(dev)):.0f}"
    (r), dt = timed(lambda: librosa.pyin(x, fmin=80, fmax=1000, sr=sr, frame_length=1024, hop_length=160)); out["librosa pYIN"] = (summ(np.nan_to_num(r[0]), r[1]), dt)
    import torchcrepe
    def crepe(model):
        f0, per = torchcrepe.predict(torch.from_numpy(x)[None], sr, hop_length=160, fmin=80, fmax=1000, model=model, batch_size=512, device="cpu", return_periodicity=True)
        return f0[0].numpy(), per[0].numpy() > 0.5
    (r), dt = timed(lambda: crepe("tiny")); out["torchcrepe tiny"] = (summ(*r), dt)
    (r), dt = timed(lambda: crepe("full")); out["torchcrepe full"] = (summ(*r), dt)
    from swift_f0 import SwiftF0
    det = SwiftF0(threads=2)
    (r), dt = timed(lambda: det.detect(x, sr, fmin=80, fmax=1000)); out["SwiftF0"] = (summ(np.asarray(r.pitch_hz), np.asarray(r.confidence) > 0.9), dt)
    import pyworld
    (r), dt = timed(lambda: pyworld.harvest(x.astype(np.float64), sr, f0_floor=80, f0_ceil=1000)); out["pyworld harvest"] = (summ(r[0], r[0] > 0), dt)
    return out

if __name__ == "__main__":
    T = "/tmp/dinleme-a2/test/"
    for n in ([] if os.environ.get("SADECE_VOKAL") else ["mix_coskulu", "mix_yavas_pitir", "mix_yavas", "mix_elyikama"]):
        print(f"\n== {n} (karisim, 30 sn)")
        for k, (v, dt) in mix_analysis(T + n + "_44k.wav").items(): print(f"   {k:34s} {v:40s} [{dt:.1f}s]")
    for n in ["vokal_ai", "vokal_dogal"]:
        print(f"\n== {n} (vokal kanali, 30 sn)")
        for k, (v, dt) in pitch_analysis(T + n + "_16k.wav").items(): print(f"   {k:18s} {v}  [{dt:.1f}s]")
