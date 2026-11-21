"""Arastirma-2 ek deneme: yerel Whisper (ONNX, sherpa-onnx; agirlik github.com/k2-fsa/sherpa-onnx/releases, asr-models).
Ucretsiz ve sinirsiz 'makine bu vokalde hangi dili / hangi sozleri duyuyor' kontrolu. Sarkida hata orani konusmadan yuksektir."""
import sys, time, glob, os, soundfile as sf, sherpa_onnx
D = "/tmp/dinleme-a2/modeller/whisper/sherpa-onnx-whisper-turbo"
enc, dec, tok = f"{D}/turbo-encoder.int8.onnx", f"{D}/turbo-decoder.int8.onnx", f"{D}/turbo-tokens.txt"
lid = sherpa_onnx.SpokenLanguageIdentification(sherpa_onnx.SpokenLanguageIdentificationConfig(
    whisper=sherpa_onnx.SpokenLanguageIdentificationWhisperConfig(encoder=enc, decoder=dec), num_threads=2, provider="cpu"))
asr = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=enc, decoder=dec, tokens=tok, language="tr", task="transcribe", num_threads=2)
for f in sys.argv[1:] or ["/tmp/dinleme-a2/test/vokal_ai_16k.wav", "/tmp/dinleme-a2/test/vokal_dogal_16k.wav", "/tmp/dinleme-a2/test/tts_16k.wav"]:
    x, sr = sf.read(f, dtype="float32"); x = x[: sr * 28]
    t = time.time(); s = lid.create_stream(); s.accept_waveform(sr, x); lang = lid.compute(s); t1 = time.time() - t
    t = time.time(); s = asr.create_stream(); s.accept_waveform(sr, x); asr.decode_stream(s); t2 = time.time() - t
    print(f"{os.path.basename(f):22s} dil={lang} ({t1:.1f}s) | yazi ({t2:.1f}s): {s.result.text.strip()[:260]}")
