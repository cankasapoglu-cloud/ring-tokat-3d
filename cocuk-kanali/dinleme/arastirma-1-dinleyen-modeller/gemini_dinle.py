#!/usr/bin/env python3
"""
gemini_dinle.py - bir ses dosyasini (veya A/B icin iki dosyayi) Google Gemini API'ye
dinletip yapilandirilmis (JSON) bir dinleme raporu ister.

DURUM: Bu betik CANLI ANAHTARLA DENENMEDI. Yazildigi gun (2026-11-21) bu ortamda
Gemini anahtari yoktu; istek Google'a ulasiyor ve "API key not valid" donuyor.
Anahtar ortam ayarlarina eklendiginde (host: generativelanguage.googleapis.com,
baslik: x-goog-api-key) degisiklik gerekmeden calismasi beklenir.

Anahtar bu betige VERILMEZ: baslik degeri her zaman "proxy-injected" yazilir,
gercek anahtari ag vekili (proxy) ekler. Betik hicbir sir okumaz/yazmaz.

Kullanim:
  python3 gemini_dinle.py sarki.mp3
  python3 gemini_dinle.py a.mp3 --ikinci b.mp3            # A/B karsilastirma
  python3 gemini_dinle.py sarki.mp3 --soru-dosyasi s.txt  # kendi sorularin
  python3 gemini_dinle.py --modeller                      # anahtarin gordugu modeller

Sinirlar (durustce): Bu bir "kulak" degil, ikinci bir gorus. Perde (detone) ve
ince zamanlama yargilari guvenilmez; onlar icin olcum araclari (pyworld/librosa)
kullanilmali. Ayni soruyu iki kez (A/B'de sirayi degistirerek) sormadan sonuca guvenme.
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile

BASE = "https://generativelanguage.googleapis.com"
KEY_HEADER = "x-goog-api-key: proxy-injected"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "onbellek")
INLINE_LIMIT = 15 * 1024 * 1024  # daha buyuk dosyalar Files API ile yuklenir

# Tercih sirasi: once ucretsiz katmanda gunluk kotasi genis olan, sonra daha guclu olanlar.
# Bu adlar Google'in resmi cookbook'undaki (Kasim 2026) listeden; gecerli olan ilk model secilir.
MODEL_PREFERENCE = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.1-pro-preview",
    "gemini-2.5-pro",
]

MIME = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".flac": "audio/flac",
        ".ogg": "audio/ogg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".aiff": "audio/aiff"}

DEFAULT_PROMPT = """You are an audio reviewer for a Turkish children's song channel.
Listen to the audio. Answer ONLY from what you hear; if you cannot hear something, say "cannot tell".
Do not be polite or encouraging: report defects plainly.

Return JSON with these fields:
1. "heard_description": 3-5 sentences: language, kind of voice (child/adult, male/female, human-like or synthetic), instruments, tempo feel, non-musical sounds (animals etc).
2. "lyrics_as_heard": the words exactly as sung, in the original language. Do NOT correct mispronounced words; write "[unclear]" where you cannot understand.
3. "structure": list of {"start":"MM:SS","end":"MM:SS","what":"..."} sections.
4. "ratings": for each item give {"choice": one of the listed options, "evidence": concrete moments as MM:SS, "confidence": "low"|"medium"|"high"}:
   - "accent": "native Turkish" | "slight foreign accent" | "strong foreign accent" | "cannot tell"
   - "vocal_naturalness": "sounds like a real singer" | "slightly synthetic" | "clearly synthetic/robotic" | "cannot tell"
   - "energy": "lullaby/sleepy" | "calm" | "moderate" | "lively" | "very energetic"
   - "singing_vs_speaking": "clearly sung melody" | "half spoken" | "mostly spoken/rap-like"
   - "vocal_in_time_with_beat": "yes" | "sometimes off" | "often off" | "cannot tell"
   - "vocal_in_tune_with_backing": "yes" | "sometimes off" | "often off" | "cannot tell"
   - "mix_balance": "vocal too quiet" | "balanced" | "vocal too loud"
   - "child_appeal": "boring" | "ok" | "catchy and fun"
5. "worst_moments": up to 5 items {"time":"MM:SS","problem":"..."}.
6. "one_line_verdict": one sentence.
"""

AB_PROMPT = """You will hear two versions of the same Turkish children's song: first clip A, then clip B.
Compare them ONLY from what you hear. Do not be polite. A tie is allowed only if you truly hear no difference.

Return JSON:
{"differences_heard": "2-4 sentences on what actually differs between A and B",
 "comparisons": {
   "accent_more_native_turkish": {"winner":"A"|"B"|"tie","evidence":"MM:SS moments","confidence":"low"|"medium"|"high"},
   "vocal_more_natural":         {...same shape...},
   "more_energetic_and_fun":     {...},
   "better_in_time_with_beat":   {...},
   "better_in_tune":             {...},
   "clearer_words":              {...},
   "better_mix_balance":         {...}},
 "overall_winner": "A"|"B"|"tie",
 "why": "one sentence"}
"""


def curl(args, data_file=None, timeout=300):
    cmd = ["curl", "-sS", "-m", str(timeout)] + args
    if data_file:
        cmd += ["--data-binary", "@" + data_file]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit("curl hatasi: " + p.stderr.strip()[:500])
    return p.stdout


def api_json(text):
    try:
        d = json.loads(text)
    except json.JSONDecodeError:
        sys.exit("Beklenmeyen yanit (JSON degil): " + text[:400])
    if isinstance(d, dict) and "error" in d:
        e = d["error"]
        msg = e.get("message", "")
        if "API key not valid" in msg or e.get("status") in ("PERMISSION_DENIED", "UNAUTHENTICATED"):
            sys.exit("GEMINI ANAHTARI YOK/GECERSIZ: ortam ayarlarina generativelanguage.googleapis.com icin "
                     "x-goog-api-key basligiyla bir ag sirri eklenmeli. (Google yaniti: %s)" % msg)
        if e.get("code") == 429:
            sys.exit("KOTA DOLDU (429): ucretsiz katman gunluk/dakikalik siniri. Yanit: " + msg[:300])
        sys.exit("API hatasi %s: %s" % (e.get("code"), msg[:500]))
    return d


def list_models():
    names, token = [], ""
    while True:
        url = BASE + "/v1beta/models?pageSize=200" + ("&pageToken=" + token if token else "")
        d = api_json(curl([url, "-H", KEY_HEADER]))
        for m in d.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                names.append(m["name"].split("/", 1)[1])
        token = d.get("nextPageToken", "")
        if not token:
            return names


def pick_model(explicit):
    if explicit:
        return explicit
    available = list_models()
    for m in MODEL_PREFERENCE:
        if m in available:
            return m
    flash = [m for m in available if "flash" in m and not any(x in m for x in ("tts", "image", "live", "audio", "embedding"))]
    if flash:
        return sorted(flash)[-1]
    sys.exit("Uygun model bulunamadi. Gorunen modeller: " + ", ".join(available[:40]))


def upload_file(path, mime):
    """Files API (resumable): 2 GB'a kadar; dosya 48 saat sonra silinir."""
    size = os.path.getsize(path)
    with tempfile.NamedTemporaryFile("w+", suffix=".hdr", delete=False) as h:
        hdr = h.name
    curl([BASE + "/upload/v1beta/files", "-D", hdr, "-o", os.devnull, "-H", KEY_HEADER,
          "-H", "X-Goog-Upload-Protocol: resumable", "-H", "X-Goog-Upload-Command: start",
          "-H", "X-Goog-Upload-Header-Content-Length: %d" % size,
          "-H", "X-Goog-Upload-Header-Content-Type: " + mime,
          "-H", "Content-Type: application/json",
          "-d", json.dumps({"file": {"display_name": os.path.basename(path)}})])
    upload_url = ""
    for line in open(hdr, encoding="utf-8", errors="replace"):
        if line.lower().startswith("x-goog-upload-url:"):
            upload_url = line.split(":", 1)[1].strip()
    os.unlink(hdr)
    if not upload_url:
        sys.exit("Yukleme adresi alinamadi (anahtar eksik olabilir).")
    info = api_json(curl([upload_url, "-H", KEY_HEADER, "-H", "Content-Length: %d" % size,
                          "-H", "X-Goog-Upload-Offset: 0", "-H", "X-Goog-Upload-Command: upload, finalize"],
                         data_file=path))
    f = info.get("file", info)
    import time
    while f.get("state") == "PROCESSING":
        time.sleep(3)
        f = api_json(curl([f["uri"], "-H", KEY_HEADER]))
    if f.get("state") not in (None, "ACTIVE"):
        sys.exit("Dosya islenemedi: " + json.dumps(f)[:300])
    return {"file_data": {"mime_type": mime, "file_uri": f["uri"]}}


def audio_part(path):
    ext = os.path.splitext(path)[1].lower()
    mime = MIME.get(ext)
    if not mime:
        sys.exit("Desteklenmeyen uzanti: %s (once ffmpeg ile mp3/wav yap)" % ext)
    if os.path.getsize(path) > INLINE_LIMIT:
        return upload_file(path, mime)
    with open(path, "rb") as fh:
        return {"inline_data": {"mime_type": mime, "data": base64.b64encode(fh.read()).decode()}}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ses", nargs="?")
    ap.add_argument("--ikinci", help="A/B karsilastirma icin ikinci dosya (B)")
    ap.add_argument("--soru-dosyasi", help="ozel soru metni (yoksa varsayilan rubrik)")
    ap.add_argument("--model")
    ap.add_argument("--modeller", action="store_true", help="anahtarin gordugu modelleri listele")
    ap.add_argument("--yeniden", action="store_true", help="onbellegi yok say")
    a = ap.parse_args()

    if a.modeller:
        print("\n".join(list_models()))
        return
    if not a.ses:
        ap.error("ses dosyasi gerekli")

    prompt = open(a.soru_dosyasi, encoding="utf-8").read() if a.soru_dosyasi else (AB_PROMPT if a.ikinci else DEFAULT_PROMPT)
    model = pick_model(a.model)
    key = "__".join(["gemini", model, sha(a.ses)] + ([sha(a.ikinci)] if a.ikinci else [])
                    + [hashlib.sha256(prompt.encode()).hexdigest()[:8]])
    os.makedirs(CACHE_DIR, exist_ok=True)
    out = os.path.join(CACHE_DIR, key + ".json")
    if os.path.exists(out) and not a.yeniden:
        print(open(out, encoding="utf-8").read())
        return

    parts = []
    if a.ikinci:
        parts += [{"text": "Clip A:"}, audio_part(a.ses), {"text": "Clip B:"}, audio_part(a.ikinci)]
    else:
        parts += [audio_part(a.ses)]
    parts.append({"text": prompt})  # soru sesten SONRA gelir
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json"}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(body, fh)
        req = fh.name
    try:
        resp = api_json(curl([BASE + "/v1beta/models/%s:generateContent" % model, "-H", KEY_HEADER,
                              "-H", "Content-Type: application/json"], data_file=req))
    finally:
        os.unlink(req)
    try:
        text = "".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"] if not p.get("thought"))
    except (KeyError, IndexError):
        sys.exit("Yanit bos/engellendi: " + json.dumps(resp)[:500])
    record = {"model": model, "files": [a.ses] + ([a.ikinci] if a.ikinci else []),
              "usage": resp.get("usageMetadata"), "answer_raw": text}
    try:
        record["answer"] = json.loads(text)
    except json.JSONDecodeError:
        pass
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=1)
    print(json.dumps(record, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
