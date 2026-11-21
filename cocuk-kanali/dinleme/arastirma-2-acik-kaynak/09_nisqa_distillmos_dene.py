"""Arastirma-2 duman testi: NISQA (torchmetrics uzerinden; agirlik raw.githubusercontent.com, 1 MB) ve
Distill-MOS (Microsoft; agirlik pip paketinin icinde, 17 MB). Ikisi de KONUSMA kalitesi icindir."""
import sys, os, time, glob, warnings
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf, torch
torch.set_num_threads(2)
import torchmetrics.functional.audio.nisqa as tn
tn.NISQA_DIR = "/tmp/dinleme-a2/modeller/nisqa"          # ~/.torchmetrics yerine onceden indirilen dosya
def wins(x, sr=16000, w=10, h=10): return [x[s:s + w * sr] for s in range(0, max(1, len(x) - w * sr // 2), h * sr)]
try:
    import distillmos
    dm = distillmos.ConvTransformerSQAModel(); dm.eval(); have_dm = True
except Exception as e:
    print("Distill-MOS yuklenemedi:", repr(e)[:300]); have_dm = False
print("NISQA sutunlari: MOS, gurultululuk, kesiklilik(discontinuity), renklenme, ses yuksekligi  (5=iyi)")
for f in sorted(glob.glob("/tmp/dinleme-a2/test/*_16k.wav")):
    x, sr = sf.read(f, dtype="float32"); W = wins(x)
    t = time.time(); n = np.mean([tn.non_intrusive_speech_quality_assessment(torch.from_numpy(w), sr).numpy() for w in W], axis=0); tn_ = time.time() - t
    s = f"{os.path.basename(f):26s} NISQA " + " ".join(f"{v:.2f}" for v in n) + f" ({tn_:.1f}s)"
    if have_dm:
        t = time.time()
        with torch.no_grad(): d = np.mean([float(dm(torch.from_numpy(w)[None])) for w in W])
        s += f" | DistillMOS {d:.2f} ({time.time()-t:.1f}s)"
    print(s)
