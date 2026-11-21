"""Arastirma-2 duman testi: sarki/konusma dogallik (MOS) tahmincileri, CPU, 2 is parcacigi.
 - SingMOS v1 (sarki sesi icin egitilmis; agirlik: github.com/South-Twilight/SingMOS/releases, 380 MB)
   YAMA: resmi kod s3prl uzerinden huggingface.co'dan wav2vec2 indirmek ister (engelli). Burada mimari s3prl'in
   wav2vec2_model.py dosyasindan kurulur ve ince-ayarli agirliklar dogrudan yuklenir; indirme gerekmez.
 - UTMOS22-strong (konusma icin; agirlik: github.com/tarepan/SpeechMOS/releases, 411 MB), kod: git clone.
Pencereli calisir (10 sn, 5 sn kayma): ortalama + zaman egirisi verir. Hicbiri insan kulagi degildir."""
import sys, time, glob, os, warnings
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf, torch
torch.set_num_threads(2)
M = "/tmp/dinleme-a2/modeller"

def load_singmos_v1():
    from s3prl.upstream.wav2vec2.wav2vec2_model import Wav2Vec2Config, Wav2Vec2Model
    sd = torch.load(f"{M}/singmos/ft_wav2vec2_base_960_23steps.pt", map_location="cpu", weights_only=True)
    P = "ssl_model.ssl_model.upstream.model."
    w2v = Wav2Vec2Model(Wav2Vec2Config(quantize_targets=True, final_dim=256))
    missing = w2v.load_state_dict({k[len(P):]: v for k, v in sd.items() if k.startswith(P)}, strict=True)
    w2v.feature_grad_mult = 0.0; w2v.encoder.layerdrop = 0.0
    lin = torch.nn.Linear(768, 1); lin.load_state_dict({"weight": sd["linear.weight"], "bias": sd["linear.bias"]})
    w2v.eval(); lin.eval()
    def predict(wav16k):                                   # (T,) float32, 16 kHz
        with torch.no_grad():
            x = w2v.extract_features(torch.from_numpy(wav16k)[None], None)["x"]
            return float(lin(x).squeeze(-1).mean())
    return predict

def load_utmos22():
    sys.path.insert(0, "/tmp/dinleme-a2/repolar/SpeechMOS")
    from speechmos.utmos22.strong.model import UTMOS22Strong
    m = UTMOS22Strong(); m.load_state_dict(torch.load(f"{M}/utmos22/utmos22_strong_step7459_v1.pt", map_location="cpu", weights_only=True)); m.eval()
    def predict(wav16k):
        with torch.no_grad(): return float(m(torch.from_numpy(wav16k)[None], 16000))
    return predict

def windows(x, sr=16000, win=10.0, hop=5.0):
    w, h = int(win * sr), int(hop * sr)
    if len(x) <= w: return [(0.0, x)]
    return [(s / sr, x[s:s + w]) for s in range(0, len(x) - w // 2, h)]

if __name__ == "__main__":
    t = time.time(); sing = load_singmos_v1(); print(f"SingMOS v1 loaded {time.time()-t:.1f}s")
    t = time.time(); utm = load_utmos22(); print(f"UTMOS22 loaded {time.time()-t:.1f}s")
    files = sys.argv[1:] or sorted(glob.glob("/tmp/dinleme-a2/test/*_16k.wav"))
    for f in files:
        x, sr = sf.read(f, dtype="float32"); assert sr == 16000
        ws = [(t0, seg) for t0, seg in windows(x) if np.sqrt(np.mean(seg ** 2)) > 1e-3]
        t = time.time(); s = [sing(seg) for _, seg in ws]; ts = time.time() - t
        t = time.time(); u = [utm(seg) for _, seg in ws]; tu = time.time() - t
        print(f"{os.path.basename(f):26s} SingMOS={np.mean(s):.2f} [{' '.join(f'{v:.1f}' for v in s)}] ({ts:.1f}s) | UTMOS22={np.mean(u):.2f} [{' '.join(f'{v:.1f}' for v in u)}] ({tu:.1f}s)  audio={len(x)/sr:.0f}s")
