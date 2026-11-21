"""Arastirma-2 akil sagligi testi: MOS tahmincileri bozulmaya tepki veriyor mu?
Ayni vokal klibini kasitli bozup (gurultu, dar bant, kirpma, robotik duz perde, konusma hizinda) puanlari karsilastirir."""
import sys, os, warnings
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf, torch, librosa, pyworld
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib; m = importlib.import_module("05_mos_dene")
sing, utm = m.load_singmos_v1(), m.load_utmos22()
x, sr = sf.read(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dinleme-a2/test/vokal_ai_16k.wav", dtype="float32")
x = x[: sr * 12]
rng = np.random.default_rng(0)
def snr(x, db): n = rng.standard_normal(len(x)).astype(np.float32); return x + n * np.sqrt(np.mean(x**2) / 10 ** (db / 10))
def narrow(x): return librosa.resample(librosa.resample(x, orig_sr=sr, target_sr=4000), orig_sr=4000, target_sr=sr)[: len(x)].astype(np.float32)
def clip(x): return np.clip(x * 8, -0.3, 0.3).astype(np.float32)
def robot(x, flat=True, jitter=0.0):
    f0, t = pyworld.harvest(x.astype(np.float64), sr); sp = pyworld.cheaptrick(x.astype(np.float64), f0, t, sr); ap = pyworld.d4c(x.astype(np.float64), f0, t, sr)
    f = f0.copy(); v = f > 0
    if flat: f[v] = np.median(f[v])
    if jitter: f[v] *= 2 ** (rng.standard_normal(v.sum()) * jitter / 12)
    return pyworld.synthesize(f, sp, ap, sr)[: len(x)].astype(np.float32)
def detune(x, cents): return librosa.effects.pitch_shift(x, sr=sr, n_steps=cents / 100).astype(np.float32)
V = {"orijinal": x, "gurultu 20dB": snr(x, 20), "gurultu 5dB": snr(x, 5), "dar bant 2kHz": narrow(x), "sert kirpma": clip(x),
     "WORLD yeniden sentez": robot(x, flat=False), "robotik duz perde": robot(x, flat=True), "perde titremesi (1 yarim ses rastgele)": robot(x, flat=False, jitter=1.0),
     "tum sarki 70 cent pes (akortsuz)": detune(x, -70)}
print(f"{'bozulma':42s} SingMOSv1  UTMOS22")
for k, v in V.items(): print(f"{k:42s} {sing(v):8.2f} {utm(v):8.2f}")
