"""Arastirma-2 duman testi: DNSMOS (speechmos paketi, ONNX agirliklari paketin icinde).
Konusma icin egitilmis bir kalite tahmincisidir; sarki icin sadece kaba bir 'ses temiz mi' gostergesi."""
import sys, time, glob, os
import numpy as np, soundfile as sf
import onnxruntime as ort
_orig = ort.InferenceSession
def _sess(path, *a, **k):            # CPU'yu 2 is parcacigi ile sinirla
    so = ort.SessionOptions(); so.intra_op_num_threads = 2; so.inter_op_num_threads = 1
    k.setdefault("providers", ["CPUExecutionProvider"])
    return _orig(path, so, *a[1:], **k) if a else _orig(path, so, **k)
ort.InferenceSession = _sess
from speechmos import dnsmos
files = sys.argv[1:] or sorted(glob.glob("/tmp/dinleme-a2/test/*_16k.wav"))
for f in files:
    x, sr = sf.read(f, dtype="float32")
    if x.ndim > 1: x = x.mean(1)
    x = x / max(1e-9, np.abs(x).max()) * 0.95
    t = time.time()
    r = dnsmos.run(x, sr=sr)
    dt = time.time() - t
    print(f"{os.path.basename(f):28s} OVRL={r['ovrl_mos']:.2f} SIG={r['sig_mos']:.2f} BAK={r['bak_mos']:.2f} P808={r['p808_mos']:.2f}  ({dt:.1f}s for {len(x)/sr:.0f}s audio)")
