#!/bin/bash
# Arastirma-2: bu ortamda (Python 3.13, CPU, kisitli ag) CALISTIGI DOGRULANAN acik kaynak "kulak yerine" araclarinin kurulumu.
# Sistem Python'una dokunmaz: /tmp/dinleme-a2/venv (sistem paketlerini gorur). Agirliklar: /tmp/dinleme-a2/modeller (depoya yazilmaz).
# Kullanilan adresler: pypi.org, files.pythonhosted.org, github.com (git + release), raw.githubusercontent.com, storage.googleapis.com
set -eu
B=/tmp/dinleme-a2; M=$B/modeller; mkdir -p "$M" "$B/repolar"
[ -d $B/venv ] || python3 -m venv --system-site-packages $B/venv
. $B/venv/bin/activate
# 1) pip paketleri (agirliklari paketin icinde olanlar dahil)
pip install --quiet torchaudio==2.11.1 torchmetrics==1.9.0 speechmos==0.0.1.1 sherpa-onnx==2.0.2 swift-f0==0.3.0 \
    ai-edge-litert==2.4.0 sentencepiece pyloudnorm essentia==2.1b6.dev1389 pretty_midi mir_eval praat-parselmouth
pip install --quiet --no-deps s3prl==0.4.18 torchcrepe==0.0.24 basic-pitch==0.4.0 distillmos==0.9.1 xls-r-sqa
pip install --quiet --no-deps "git+https://github.com/CPJKU/madmom.git"      # 0.17.dev0; PyPI'deki 0.16.1 Python 3.13'te derlenmez
# 2) kaynak kodu (torch.hub burada calismaz: codeload.github.com 403 verir -> git clone)
[ -d $B/repolar/SpeechMOS ] || git clone --quiet --depth 1 https://github.com/tarepan/SpeechMOS.git $B/repolar/SpeechMOS
[ -d $B/repolar/SingMOS ]   || git clone --quiet --depth 1 --branch v1.1.2 https://github.com/South-Twilight/SingMOS.git $B/repolar/SingMOS
# 3) agirliklar
dl(){ [ -s "$2" ] || { mkdir -p "$(dirname "$2")"; curl -sL --fail --max-time 1800 -o "$2.part" "$1" && mv "$2.part" "$2"; }; echo "ok $2"; }
G=https://github.com
dl $G/k2-fsa/sherpa-onnx/releases/download/audio-tagging-models/sherpa-onnx-ced-mini-audio-tagging-2024-04-19.tar.bz2 $M/ced/ced-mini.tar.bz2   # 46 MB
[ -d $M/ced/sherpa-onnx-ced-mini-audio-tagging-2024-04-19 ] || tar xjf $M/ced/ced-mini.tar.bz2 -C $M/ced
for f in audio_preprocessor.tflite music_encoder.tflite text_encoder.tflite spm.model; do                                                         # 8+354+400+0.5 MB
  dl https://storage.googleapis.com/magenta-rt-public/magenta-rt-2/resources/musiccoca/$f $M/musiccoca/$f; done
dl https://raw.githubusercontent.com/gabrielmittag/NISQA/master/weights/nisqa.tar $M/nisqa/nisqa.tar                                               # 1 MB (github.com/.../raw/ adresi 403 verir)
dl $G/tarepan/SpeechMOS/releases/download/v1.0.0/utmos22_strong_step7459_v1.pt $M/utmos22/utmos22_strong_step7459_v1.pt                            # 393 MB
dl $G/South-Twilight/SingMOS/releases/download/ckpt_s3prl/ft_wav2vec2_base_960_23steps.pt $M/singmos/ft_wav2vec2_base_960_23steps.pt               # 363 MB
dl $G/South-Twilight/SingMOS/releases/download/ckpt_v3/ft_wav2vec2_large_ll60k_mdf_p1_200epochs_all_192epochs.pth $M/singmos/ft_wav2vec2_large_ll60k_mdf_p1_200epochs_all_192epochs.pth  # 1.2 GB
# istege bagli: yerel Whisper (ONNX) - sozleri/dili makineye dinletmek icin
# dl $G/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-turbo.tar.bz2 $M/whisper/turbo.tar.bz2   # 538 MB
# dl $G/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-base.tar.bz2  $M/whisper/base.tar.bz2    # 198 MB
echo "Kurulum tamam. Denemeler: 02_... 12_... betikleri ($B/venv/bin/python ile)."
