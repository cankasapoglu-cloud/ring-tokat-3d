#!/usr/bin/env bash
# ElevenLabs Scribe speech-to-text denemesi (yalnizca /v1/speech-to-text; anahtar proxy tarafindan eklenir).
# Kullanim: scribe_dene.sh <ses_dosyasi> <model_id> <cikti_json>
# Ayni dosya + model icin cikti varsa tekrar cagirmaz (kredi korumasi).
set -euo pipefail
f="$1"; model="$2"; out="$3"
if [ -s "$out" ]; then echo "onbellekte var: $out"; exit 0; fi
code=$(curl -sS -m 180 -o "$out.tmp" -w "%{http_code}" -X POST "https://api.elevenlabs.io/v1/speech-to-text" \
  -H "xi-api-key: proxy-injected" \
  -F "file=@${f}" \
  --form-string "model_id=${model}" \
  --form-string "language_code=tr" \
  --form-string "timestamps_granularity=word" \
  --form-string "tag_audio_events=true")
echo "HTTP $code"
if [ "$code" = "200" ]; then mv "$out.tmp" "$out"; else head -c 600 "$out.tmp"; echo; mv "$out.tmp" "$out.hata_$code.txt"; fi
