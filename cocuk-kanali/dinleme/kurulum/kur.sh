#!/bin/bash
# dinleme/kurulum/kur.sh : "Claude'un kulak yerine kullandigi" olcum araclarini SIFIR bir konteynere yeniden kurar.
#
#   bash cocuk-kanali/dinleme/kurulum/kur.sh          # yaklasik 1,3 GB agirlik indirir, 2-5 dakika
#
# Kurallar:
#  - Sistemde ZATEN kurulu olan hicbir paketin surumunu degistirmez: once "pip freeze" ile kisit dosyasi
#    cikarir, her kurulumu "-c kisit" ile yapar (pyworld icin setuptools<81, torch, numpy, onnxruntime korunur).
#  - Yalnizca erisilebilen adresleri kullanir: pypi.org, github.com (git + release), raw.githubusercontent.com,
#    storage.googleapis.com. Engelli adreslere (huggingface.co, dl.fbaipublicfiles.com ...) HIC gitmez.
#  - Agirliklar depoya yazilmaz: $DINLEME_MODELLER (varsayilan ~/.cache/dinleme/modeller).
#  - Yeniden calistirmak zararsizdir (var olan dosyayi yeniden indirmez).
set -u
M="${DINLEME_MODELLER:-$HOME/.cache/dinleme/modeller}"
ESKI="${DINLEME_ESKI:-/tmp/dinleme-a2/modeller}"   # arastirma asamasinda indirilenler (varsa oradan kopyalanir, yoksa indirilir)
KISIT="$(mktemp /tmp/dinleme-kisit.XXXXXX)"
mkdir -p "$M"
hata=0

echo "== 1/4 pip paketleri (mevcut surumler korunarak)"
pip freeze 2>/dev/null | grep -v -E '^(-e|#)| @ ' > "$KISIT"
pip install --quiet -c "$KISIT" \
    torchaudio==2.11.1 torchmetrics==1.9.0 speechmos==0.0.1.1 sherpa-onnx==2.0.2 swift-f0==0.3.0 \
    ai-edge-litert==2.4.0 sentencepiece==0.2.3 essentia==2.1b6.dev1389 pyloudnorm 2>&1 | grep -v "WARNING: Running pip as the 'root'" || true
# Distill-MOS: agirliklari tekerin icinde; "transformers" bagimliligi gerekmez, o yuzden --no-deps
pip install --quiet --no-deps -c "$KISIT" distillmos==0.9.1 xls-r-sqa==0.1.0 2>&1 | grep -v "WARNING: Running pip as the 'root'" || true

echo "== 2/4 kaynak kodu (torch.hub burada calismaz: codeload.github.com 403 verir, o yuzden git clone)"
if [ ! -d "$M/repolar/SpeechMOS/speechmos" ]; then
  mkdir -p "$M/repolar"
  git clone --quiet https://github.com/tarepan/SpeechMOS.git "$M/repolar/SpeechMOS" \
    && git -C "$M/repolar/SpeechMOS" checkout --quiet ed25eacbfa42b99156c36ebec67a733b5dbb9b79 || { echo "HATA SpeechMOS deposu"; hata=1; }
fi

echo "== 3/4 model agirliklari -> $M"
dl(){ # dl <url> <hedef> [<yerel kopya>]
  if [ -s "$2" ]; then echo "  var   $2"; return 0; fi
  mkdir -p "$(dirname "$2")"
  if [ -n "${3:-}" ] && [ -s "$3" ]; then cp "$3" "$2" && echo "  kopya $2" && return 0; fi
  if curl -sL --fail --retry 2 --max-time 1800 -o "$2.part" "$1"; then mv "$2.part" "$2"; echo "  indi  $2 ($(du -h "$2" | cut -f1))"
  else rm -f "$2.part"; echo "  HATA  $1"; hata=1; fi
}
G=https://github.com
# CED-mini ses etiketleyici (AudioSet 527 sinif; 46 MB)
dl $G/k2-fsa/sherpa-onnx/releases/download/audio-tagging-models/sherpa-onnx-ced-mini-audio-tagging-2024-04-19.tar.bz2 "$M/ced/ced-mini.tar.bz2" "$ESKI/ced/ced-mini.tar.bz2"
[ -s "$M/ced/sherpa-onnx-ced-mini-audio-tagging-2024-04-19/model.onnx" ] || tar xjf "$M/ced/ced-mini.tar.bz2" -C "$M/ced" || hata=1
# NISQA (1 MB; github.com/.../raw/ adresi 403 verir, raw.githubusercontent.com calisir)
dl https://raw.githubusercontent.com/gabrielmittag/NISQA/master/weights/nisqa.tar "$M/nisqa/nisqa.tar" "$ESKI/nisqa/nisqa.tar"
# UTMOS22-strong (411 MB)
dl $G/tarepan/SpeechMOS/releases/download/v1.0.0/utmos22_strong_step7459_v1.pt "$M/utmos22/utmos22_strong_step7459_v1.pt" "$ESKI/utmos22/utmos22_strong_step7459_v1.pt"
# MusicCoCa metin-muzik ortak uzayi (8,7 + 371 + 419 + 0,5 MB)
for f in audio_preprocessor.tflite music_encoder.tflite text_encoder.tflite spm.model; do
  dl https://storage.googleapis.com/magenta-rt-public/magenta-rt-2/resources/musiccoca/$f "$M/musiccoca/$f" "$ESKI/musiccoca/$f"
done
# Vokal/altyapi ayirma modeli (audio-separator; 67 MB). Yoksa github.com/TRvlvr/model_repo surumlerinden iner.
AS="${AUDIO_SEPARATOR_MODEL_DIR:-/tmp/audio-separator-models}"
if [ -s "$AS/UVR-MDX-NET-Voc_FT.onnx" ]; then echo "  var   $AS/UVR-MDX-NET-Voc_FT.onnx"
elif command -v audio-separator >/dev/null; then
  audio-separator --download_model_only -m UVR-MDX-NET-Voc_FT.onnx --log_level warning >/dev/null 2>&1 \
    && echo "  indi  $AS/UVR-MDX-NET-Voc_FT.onnx" || { echo "  HATA  UVR-MDX-NET-Voc_FT.onnx indirilemedi (--ayir calismaz)"; hata=1; }
else echo "  HATA  audio-separator kurulu degil: pip install audio-separator (--ayir icin gerekli)"; hata=1; fi

echo "== 4/4 denetim (eski paketler bozulmadi mi, yeniler aciliyor mu)"
python3 - <<'EOF' || hata=1
import importlib, warnings, sys
warnings.filterwarnings("ignore")
kotu = 0
for ad in ["pyworld", "librosa", "torch", "onnxruntime", "audio_separator", "numpy", "scipy", "soundfile", "matplotlib",
           "torchaudio", "torchmetrics", "speechmos", "sherpa_onnx", "swift_f0", "ai_edge_litert", "sentencepiece",
           "essentia", "distillmos", "pyloudnorm"]:
    try:
        m = importlib.import_module(ad); print("  tamam %-16s %s" % (ad, getattr(m, "__version__", "")))
    except Exception as e:
        kotu += 1; print("  HATA  %-16s %s: %s" % (ad, type(e).__name__, str(e)[:120]))
import setuptools
print("  setuptools", setuptools.__version__, "(pyworld icin 81'den kucuk olmali)")
if int(setuptools.__version__.split(".")[0]) >= 81: kotu += 1
sys.exit(1 if kotu else 0)
EOF
rm -f "$KISIT"
if [ $hata = 0 ]; then echo "KURULUM TAMAM. Deneme: python3 $(dirname "$0")/../arac/dinle.py <ses dosyasi> --ayir"
else echo "KURULUM EKSIK: yukaridaki HATA satirlarina bakin (arac eksik parcayi atlayip calismaya devam eder)."; exit 1; fi
