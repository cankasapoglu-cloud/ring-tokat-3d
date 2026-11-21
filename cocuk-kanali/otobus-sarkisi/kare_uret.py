#!/usr/bin/env python3
"""Otobüs Şarkısı sahne kareleri: ElevenLabs çizim arayüzü (gpt-image-2.5-sunburst), referans resimlerle (Pıtır ve otobüs aynı kalsın).
sahneler.json okunur; var olan kare YENİDEN ÜRETİLMEZ (her üretim kredi harcar).
Kullanım: python3 kare_uret.py <sahne adı> [<sahne adı> ...]   |   python3 kare_uret.py hepsi
API anahtarı ağ geçidinde eklenir (başlıktaki değer yer tutucudur)."""
import base64, io, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
D = os.path.dirname(os.path.abspath(__file__)); A = os.path.dirname(D)
S = json.load(open(os.path.join(D, "sahneler.json"), encoding="utf8"))
os.makedirs(os.path.join(D, "kare"), exist_ok=True)
istenen = [s["ad"] for s in S["sahneler"]] if sys.argv[1:] == ["hepsi"] else sys.argv[1:]

def curl(*a):
    r = subprocess.run(["curl", "-sS", "-m", "120", *a], capture_output=True, text=True); return r.stdout

def b64(yol):                                                 # referans: 1024 px JPEG (istek küçük kalsın)
    im = Image.open(yol if os.path.isabs(yol) else os.path.join(A, yol)).convert("RGB"); im.thumbnail((1024, 1024)); t = io.BytesIO(); im.save(t, "JPEG", quality=90)
    return {"type": "inline_base64", "mime_type": "image/jpeg", "content_base64": base64.b64encode(t.getvalue()).decode()}

def uret(s):
    cikti = os.path.join(D, "kare", s["ad"] + ".png")
    if os.path.exists(cikti): return s["ad"], "var (atlandı)"
    refs = [r for r in s.get("ref", S["ref"]) if os.path.exists(r if os.path.isabs(r) else os.path.join(A, r))]
    istek = {"model_id": "gpt-image-2.5-sunburst", "prompt": s["prompt"] + " " + S["stil"], "aspect_ratio": "16:9", "resolution": "1K",
             "quality": S.get("kalite", "high"), "images": [b64(r) for r in refs]}
    yol = os.path.join(D, "kare", "_" + s["ad"] + ".json"); json.dump(istek, open(yol, "w"))
    y = curl("-X", "POST", "https://api.elevenlabs.io/v1/flows/image", "-H", "xi-api-key: proxy-injected", "-H", "Content-Type: application/json", "--data-binary", "@" + yol)
    os.unlink(yol)
    try: gid = json.loads(y)["id"]
    except Exception: return s["ad"], "HATA (istek): " + y[:300]
    for _ in range(90):
        time.sleep(4); d = json.loads(curl("https://api.elevenlabs.io/v1/flows/image/" + gid, "-H", "xi-api-key: proxy-injected") or "{}")
        if d.get("status") == "completed":
            subprocess.run(["curl", "-sS", "-f", "-m", "120", "-o", cikti, d["content_url"]], check=True)
            return s["ad"], "tamam %s %dx%d" % (gid, *Image.open(cikti).size)
        if d.get("status") == "failed": return s["ad"], "HATA (üretim): " + json.dumps(d, ensure_ascii=False)[:300]
    return s["ad"], "HATA: zaman aşımı " + gid

with ThreadPoolExecutor(4) as ex:
    for ad, sonuc in ex.map(uret, [s for s in S["sahneler"] if s["ad"] in istenen]): print(ad, "->", sonuc, flush=True)
