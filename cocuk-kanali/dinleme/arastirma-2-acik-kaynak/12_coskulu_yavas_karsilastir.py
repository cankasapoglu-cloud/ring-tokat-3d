"""Arastirma-2 kucuk gecerlilik denemesi: projedeki 'coskulu_*' ve 'yavas_*' adli surumleri hangi olcutler ayiriyor?
(Etiket = uretim niyeti; insan dinleme puani degil.) Olcutler: MusicCoCa sifir-ornekli, CED etiketleri, essentia, librosa."""
import sys, os, time, json, warnings, subprocess, tempfile
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf, librosa, sentencepiece, sherpa_onnx
from ai_edge_litert.interpreter import Interpreter
import essentia; essentia.log.infoActive = False; essentia.log.warningActive = False
import essentia.standard as es
K = "/home/user/ring-tokat-3d/cocuk-kanali/"
FILES = {"coskulu": ["ali-baba/coskulu_1.mp3", "ali-baba/coskulu_2.mp3", "el-yikama/coskulu_1.mp3", "el-yikama/coskulu_2.mp3", "parmak-ailesi/coskulu_1.mp3", "parmak-ailesi/coskulu_2.mp3"],
         "yavas": ["parmak-ailesi/yavas_2.mp3", "pitirin-ailesi/yavas_1.mp3", "pitirin-ailesi/yavas_2.mp3"],
         "diger": ["ali-baba/sarki.mp3", "el-yikama/sarki_1.mp3", "parmak-ailesi/sarki_2.mp3", "balon-sarkisi/sarki.mp3"]}
R = "/tmp/dinleme-a2/modeller/musiccoca"
def interp(n): it = Interpreter(model_path=f"{R}/{n}", num_threads=2); it.allocate_tensors(); return it
sp = sentencepiece.SentencePieceProcessor(); sp.Load(f"{R}/spm.model"); TXT, PRE, ENC = interp("text_encoder.tflite"), interp("audio_preprocessor.tflite"), interp("music_encoder.tflite")
def etext(s, L=128):
    ids = [1] + sp.EncodeAsIds(s.lower())[:L - 1]; n = len(ids); ids = np.array(ids + [0] * (L - n), np.int32); pad = np.ones(L, np.float32); pad[:n] = 0
    for d in TXT.get_input_details(): TXT.set_tensor(d["index"], (ids if d["dtype"] == np.int32 else pad).reshape(d["shape"]))
    TXT.invoke(); e = TXT.get_tensor(TXT.get_output_details()[0]["index"]).flatten(); return e / np.linalg.norm(e)
def eclip(c):
    d = PRE.get_input_details()[0]; b = np.zeros(int(np.prod(d["shape"])), np.float32); n = min(len(c), len(b)); b[:n] = c[:n]
    PRE.set_tensor(d["index"], b.reshape(d["shape"])); PRE.invoke(); ENC.set_tensor(ENC.get_input_details()[0]["index"], PRE.get_tensor(PRE.get_output_details()[0]["index"])); ENC.invoke()
    e = ENC.get_tensor(ENC.get_output_details()[0]["index"]).flatten(); return e / np.linalg.norm(e)
POS = [etext(s) for s in ["energetic upbeat happy children's song", "exciting lively dance song for kids", "fast cheerful party music"]]
NEG = [etext(s) for s in ["slow calm sleepy lullaby", "gentle soothing quiet bedtime song", "slow soft relaxing music"]]
C = "/tmp/dinleme-a2/modeller/ced/sherpa-onnx-ced-mini-audio-tagging-2024-04-19"
tagger = sherpa_onnx.AudioTagging(sherpa_onnx.AudioTaggingConfig(model=sherpa_onnx.AudioTaggingModelConfig(ced=C + "/model.onnx", num_threads=2, provider="cpu"), labels=C + "/class_labels_indices.csv", top_k=527))
rows = []
for grp, fl in FILES.items():
    for f in fl:
        if not os.path.exists(K + f): continue
        tmp = tempfile.mktemp(suffix=".wav"); subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", K + f, "-ac", "1", "-ar", "16000", tmp], check=True)
        x, sr = sf.read(tmp, dtype="float32"); os.remove(tmp); x = x[: sr * 120]
        W = [x[s:s + 160000] for s in range(0, len(x) - 80000, 160000)]
        E = np.array([eclip(w) for w in W]); mc = float(np.mean([[E @ p for p in POS]]) - np.mean([[E @ n for n in NEG]]))
        acc = {}
        for w in W:
            st = tagger.create_stream(); st.accept_waveform(sr, w)
            for ev in tagger.compute(st): acc[ev.name] = acc.get(ev.name, 0) + ev.prob / len(W)
        x44 = librosa.resample(x, orig_sr=sr, target_sr=44100)
        bpm = es.RhythmExtractor2013(method="multifeature")(x44)[0]; dance = es.Danceability()(x44)[0]
        on = len(librosa.onset.onset_detect(y=x, sr=sr)) / (len(x) / sr); cen = float(np.mean(librosa.feature.spectral_centroid(y=x, sr=sr)))
        rows.append((grp, f, mc, acc.get("Exciting music", 0), acc.get("Happy music", 0), acc.get("Lullaby", 0), acc.get("Tender music", 0), acc.get("Music for children", 0), bpm, dance, on, cen))
print(f"{'grup':8s} {'dosya':30s} {'MCoCa':>6s} {'Excit':>6s} {'Happy':>6s} {'Lullab':>6s} {'Tender':>6s} {'Child':>6s} {'BPM':>6s} {'Dance':>5s} {'on/s':>5s} {'centr':>6s}")
for r in rows: print(f"{r[0]:8s} {r[1]:30s} {r[2]:+6.3f} {r[3]:6.3f} {r[4]:6.3f} {r[5]:6.3f} {r[6]:6.3f} {r[7]:6.3f} {r[8]:6.1f} {r[9]:5.2f} {r[10]:5.2f} {r[11]:6.0f}")
json.dump(rows, open("/tmp/dinleme-a2/coskulu_yavas.json", "w"))
