#!/bin/bash
# Arastirma-2: acik kaynak modellerin agirliklarini ERISILEBILEN adreslerden indirir.
# (github.com release / raw.githubusercontent.com / storage.googleapis.com). Depoya degil /tmp altina yazar.
set -u
M=/tmp/dinleme-a2/modeller
mkdir -p "$M"/{utmos22,singmos,ced,musiccoca,nisqa,dnsmos,yamnet}
dl(){ # dl <url> <hedef>
  if [ -s "$2" ]; then echo "VAR  $2"; return; fi
  curl -sL --fail --max-time 1800 -o "$2.part" "$1" && mv "$2.part" "$2" && echo "OK   $2 ($(du -h "$2" | cut -f1))" || echo "HATA $1"
}
dl https://github.com/gabrielmittag/NISQA/raw/refs/heads/master/weights/nisqa.tar "$M/nisqa/nisqa.tar"
dl https://github.com/k2-fsa/sherpa-onnx/releases/download/audio-tagging-models/sherpa-onnx-ced-mini-audio-tagging-2024-04-19.tar.bz2 "$M/ced/ced-mini.tar.bz2"
dl https://github.com/k2-fsa/sherpa-onnx/releases/download/audio-tagging-models/sherpa-onnx-ced-base-audio-tagging-2024-04-19.tar.bz2 "$M/ced/ced-base.tar.bz2"
for f in audio_preprocessor.tflite music_encoder.tflite text_encoder.tflite spm.model; do
  dl "https://storage.googleapis.com/magenta-rt-public/magenta-rt-2/resources/musiccoca/$f" "$M/musiccoca/$f"
done
dl https://github.com/tarepan/SpeechMOS/releases/download/v1.0.0/utmos22_strong_step7459_v1.pt "$M/utmos22/utmos22_strong_step7459_v1.pt"
dl https://github.com/South-Twilight/SingMOS/releases/download/ckpt_s3prl/ft_wav2vec2_base_960_23steps.pt "$M/singmos/ft_wav2vec2_base_960_23steps.pt"
dl https://storage.googleapis.com/audioset/yamnet.h5 "$M/yamnet/yamnet.h5"
ls -la "$M"/*
