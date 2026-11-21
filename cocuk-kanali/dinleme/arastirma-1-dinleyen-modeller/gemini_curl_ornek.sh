#!/usr/bin/env bash
# En kisa ornek: bir mp3'u Gemini Files API'ye yukle ve hakkinda soru sor (yalnizca curl + jq).
# Kaynak: Google'in resmi cookbook'u (quickstarts/rest/Audio_REST.ipynb) + API kesif belgesi (v1beta).
# Anahtar: bu ortamda ag vekili ekler -> baslik degeri "proxy-injected". (Baska bir bilgisayarda
# buraya kendi anahtarini tasiyan bir ortam degiskeni konur; anahtar asla dosyaya yazilmaz.)
# CANLI ANAHTARLA DENENMEDI (2026-11-21'de ortamda anahtar yoktu).
set -euo pipefail
AUDIO="${1:?kullanim: gemini_curl_ornek.sh sarki.mp3 [model]}"
MODEL="${2:-gemini-3.5-flash-lite}"     # gecerli adlar: GET $BASE/v1beta/models
BASE="https://generativelanguage.googleapis.com"
KEY="x-goog-api-key: proxy-injected"
MIME="audio/mpeg"
BYTES=$(wc -c < "$AUDIO")
HDR=$(mktemp); trap 'rm -f "$HDR"' EXIT

# 1) Yuklemeyi baslat (resumable); yukleme adresi yanit basliginda gelir
curl -sS "$BASE/upload/v1beta/files" -D "$HDR" -o /dev/null \
  -H "$KEY" \
  -H "X-Goog-Upload-Protocol: resumable" \
  -H "X-Goog-Upload-Command: start" \
  -H "X-Goog-Upload-Header-Content-Length: $BYTES" \
  -H "X-Goog-Upload-Header-Content-Type: $MIME" \
  -H "Content-Type: application/json" \
  -d '{"file": {"display_name": "sarki"}}'
UPLOAD_URL=$(grep -i '^x-goog-upload-url:' "$HDR" | cut -d' ' -f2 | tr -d '\r' || true)
[ -n "$UPLOAD_URL" ] || { echo "Yukleme adresi yok: anahtar tanimli degil ya da gecersiz." >&2; exit 2; }

# 2) Baytlari gonder; yanit dosyanin URI'sini verir (dosya 48 saat sonra silinir)
FILE_URI=$(curl -sS "$UPLOAD_URL" -H "$KEY" \
  -H "Content-Length: $BYTES" \
  -H "X-Goog-Upload-Offset: 0" \
  -H "X-Goog-Upload-Command: upload, finalize" \
  --data-binary "@$AUDIO" | jq -r '.file.uri')

# 3) Soru sor (soru sesten SONRA gelir)
curl -sS "$BASE/v1beta/models/$MODEL:generateContent" \
  -H "$KEY" -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [
      {"file_data": {"mime_type": "'"$MIME"'", "file_uri": "'"$FILE_URI"'"}},
      {"text": "Listen to this song. 1) Write the lyrics exactly as sung (do not correct mistakes). 2) Does the singer sound like a native Turkish speaker? Give MM:SS examples. 3) Is the song energetic or lullaby-like? Answer only from what you hear."}
    ]}]
  }' | jq -r '.candidates[0].content.parts[] | select(.thought != true) | .text'
