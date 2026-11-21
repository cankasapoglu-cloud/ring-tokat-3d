"""Arastirma-2: yamali SingMOS v1 + SingMOS-Pro duman testi ve bozulma duyarliligi (CPU, 2 is parcacigi)."""
import sys, os, time, glob, warnings
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf, torch, librosa, pyworld
torch.set_num_threads(2)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import singmos_yama
t = time.time(); v1 = singmos_yama.load("v1"); print(f"v1 yuklendi {time.time()-t:.1f}s")
t = time.time(); pro = singmos_yama.load("pro"); print(f"pro yuklendi {time.time()-t:.1f}s")
def wins(x, sr=16000, w=10, h=10): return [x[s:s + w * sr] for s in range(0, max(1, len(x) - w * sr // 2), h * sr)]
for f in sorted(glob.glob("/tmp/dinleme-a2/test/*_16k.wav")):
    x, sr = sf.read(f, dtype="float32"); W = wins(x)
    t = time.time(); a = [v1(w) for w in W]; ta = time.time() - t
    t = time.time(); b = [pro(w) for w in W]; tb = time.time() - t
    print(f"{os.path.basename(f):26s} v1={np.mean(a):.2f} ({ta:.1f}s)  pro={np.mean(b):.2f} [{' '.join(f'{v:.2f}' for v in b)}] ({tb:.1f}s)  ses={len(x)/sr:.0f}s")
x, sr = sf.read("/tmp/dinleme-a2/test/vokal_ai_16k.wav", dtype="float32"); x = x[: sr * 12]; rng = np.random.default_rng(0)
def snr(x, db): n = rng.standard_normal(len(x)).astype(np.float32); return x + n * np.sqrt(np.mean(x**2) / 10 ** (db / 10))
def robot(x, flat=True, jitter=0.0):
    d = x.astype(np.float64); f0, t = pyworld.harvest(d, sr); sp = pyworld.cheaptrick(d, f0, t, sr); ap = pyworld.d4c(d, f0, t, sr)
    f = f0.copy(); v = f > 0
    if flat: f[v] = np.median(f[v])
    if jitter: f[v] *= 2 ** (rng.standard_normal(v.sum()) * jitter / 12)
    return pyworld.synthesize(f, sp, ap, sr)[: len(x)].astype(np.float32)
V = {"orijinal": x, "gurultu 20dB": snr(x, 20), "gurultu 5dB": snr(x, 5), "sert kirpma": np.clip(x * 8, -0.3, 0.3).astype(np.float32),
     "WORLD yeniden sentez": robot(x, False), "robotik duz perde": robot(x, True), "perde titremesi": robot(x, False, 1.0),
     "70 cent pes kaydirma": librosa.effects.pitch_shift(x, sr=sr, n_steps=-0.7).astype(np.float32)}
print(f"\n{'bozulma':28s}  v1    pro")
for k, v in V.items(): print(f"{k:28s} {v1(v):5.2f} {pro(v):5.2f}")
