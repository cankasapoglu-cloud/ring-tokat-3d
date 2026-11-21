"""Arastirma-2 duman testi: CED ses etiketleyici (AudioSet 527 sinif), sherpa-onnx ile, CPU.
Agirliklar: github.com/k2-fsa/sherpa-onnx/releases (audio-tagging-models). 10 sn'lik pencerelerle calisir."""
import sys, time, glob, os
import numpy as np, soundfile as sf, sherpa_onnx
D = "/tmp/dinleme-a2/modeller/ced/sherpa-onnx-ced-%s-audio-tagging-2024-04-19"
size = os.environ.get("CED", "mini")
cfg = sherpa_onnx.AudioTaggingConfig(
    model=sherpa_onnx.AudioTaggingModelConfig(ced=(D % size) + "/model.onnx", num_threads=2, debug=False, provider="cpu"),
    labels=(D % size) + "/class_labels_indices.csv", top_k=527)
tagger = sherpa_onnx.AudioTagging(cfg)
KEY = ["Music", "Singing", "Child singing", "Female singing", "Male singing", "Synthetic singing", "Speech synthesizer",
       "Speech", "Music for children", "Lullaby", "Happy music", "Exciting music", "Tender music", "Sad music", "Funny music"]
files = sys.argv[1:] or sorted(glob.glob("/tmp/dinleme-a2/test/*_16k.wav"))
for f in files:
    x, sr = sf.read(f, dtype="float32")
    if x.ndim > 1: x = x.mean(1)
    t = time.time(); acc = {}; n = 0
    for s in range(0, max(1, len(x) - sr * 5), sr * 10):          # 10 sn pencere
        st = tagger.create_stream(); st.accept_waveform(sr, x[s:s + sr * 10])
        for ev in tagger.compute(st): acc[ev.name] = acc.get(ev.name, 0.0) + ev.prob
        n += 1
    dt = time.time() - t
    acc = {k: v / n for k, v in acc.items()}
    top = sorted(acc.items(), key=lambda kv: -kv[1])[:8]
    print(f"\n== {os.path.basename(f)}  ({dt:.1f}s for {len(x)/sr:.0f}s audio, model={size})")
    print("  top8: " + ", ".join(f"{k} {v:.2f}" for k, v in top))
    print("  key : " + ", ".join(f"{k} {acc.get(k, 0):.3f}" for k in KEY[4:]))
