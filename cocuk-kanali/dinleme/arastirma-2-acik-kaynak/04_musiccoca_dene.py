"""Arastirma-2 duman testi: MusicCoCa (Google Magenta RT 2) - metin ve muzigi ayni uzaya gomen model (CLAP benzeri).
Agirliklar: storage.googleapis.com/magenta-rt-public/magenta-rt-2/resources/musiccoca/ (TFLite, CC-BY 4.0).
Calistirici: ai-edge-litert (pip). 16 kHz mono, 10 sn'lik klipler. Sifir-ornekli (zero-shot) metin-ses benzerligi verir."""
import sys, time, glob, os
import numpy as np, soundfile as sf, sentencepiece
from ai_edge_litert.interpreter import Interpreter
R = "/tmp/dinleme-a2/modeller/musiccoca"
def interp(name):
    it = Interpreter(model_path=f"{R}/{name}", num_threads=2); it.allocate_tensors(); return it
sp = sentencepiece.SentencePieceProcessor(); sp.Load(f"{R}/spm.model")
t0 = time.time(); TXT = interp("text_encoder.tflite"); PRE = interp("audio_preprocessor.tflite"); ENC = interp("music_encoder.tflite")
print(f"models loaded in {time.time()-t0:.1f}s")

def embed_text(s, L=128):
    ids = [1] + sp.EncodeAsIds(s.lower())[:L - 1]; n = len(ids)
    ids = np.array(ids + [0] * (L - n), dtype=np.int32); pad = np.ones(L, np.float32); pad[:n] = 0
    for d in TXT.get_input_details():
        TXT.set_tensor(d["index"], (ids if d["dtype"] == np.int32 else pad).reshape(d["shape"]))
    TXT.invoke(); e = TXT.get_tensor(TXT.get_output_details()[0]["index"]).flatten().astype(np.float32)
    return e / np.linalg.norm(e)

def embed_clip(clip):
    d = PRE.get_input_details()[0]; buf = np.zeros(int(np.prod(d["shape"])), np.float32)
    n = min(len(clip), len(buf)); buf[:n] = clip[:n]
    PRE.set_tensor(d["index"], buf.reshape(d["shape"])); PRE.invoke()
    feat = PRE.get_tensor(PRE.get_output_details()[0]["index"])
    ENC.set_tensor(ENC.get_input_details()[0]["index"], feat); ENC.invoke()
    e = ENC.get_tensor(ENC.get_output_details()[0]["index"]).flatten().astype(np.float32)
    return e / np.linalg.norm(e)

PAIRS = [  # (olumlu, karsit) metin ciftleri
    ("energetic upbeat happy children's song", "slow calm sleepy lullaby"),
    ("fast tempo dance music", "slow tempo ballad"),
    ("a child singing", "a robot voice, text to speech"),
    ("singing voice with melody", "spoken word, talking"),
    ("song with vocals", "instrumental music without vocals"),
    ("professional studio recording, high quality", "low quality amateur recording, noisy and distorted"),
    ("farm animal sounds, cow, sheep, dog", "no animal sounds"),
]
t = time.time(); T = {s: embed_text(s) for p in PAIRS for s in p}; print(f"{len(T)} text prompts embedded in {time.time()-t:.1f}s")
files = sys.argv[1:] or sorted(glob.glob("/tmp/dinleme-a2/test/*_16k.wav"))
for f in files:
    x, sr = sf.read(f, dtype="float32"); assert sr == 16000
    t = time.time()
    E = np.mean([embed_clip(x[s:s + 160000]) for s in range(0, max(1, len(x) - 80000), 160000)], axis=0); E /= np.linalg.norm(E)
    dt = time.time() - t
    print(f"\n== {os.path.basename(f)}  ({dt:.1f}s for {len(x)/sr:.0f}s audio)")
    for a, b in PAIRS:
        sa, sb = float(E @ T[a]), float(E @ T[b])
        p = 1 / (1 + np.exp(-(sa - sb) * 20))      # gosterim amacli olcekleme; kalibre degildir
        print(f"   {p:5.2f}  [{sa:+.3f} vs {sb:+.3f}]  '{a}'  <->  '{b}'")
