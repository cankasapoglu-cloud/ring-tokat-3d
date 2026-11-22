#!/usr/bin/env python3
"""Klipler (genel): kullanım: python3 klip_uret.py <şarkı klasörü> <sahne adı ...|hepsi>. her sahne karesi MiniMax (Hailuo 2.3 Fast) ile 6 saniyelik videoya çevrilir.
sahneler.json'daki 'video' tarifi kullanılır. Var olan klip YENİDEN ÜRETİLMEZ (klip başına yaklaşık 0,19 dolar).
Kullanım: python3 klip_uret.py <sahne adı> [...]   |   python3 klip_uret.py hepsi
API anahtarı ağ geçidinde eklenir (başlıktaki değer yer tutucudur)."""
import base64, io, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
D = os.path.abspath(sys.argv[1]); S = json.load(open(os.path.join(D, "sahneler.json"), encoding="utf8"))
os.makedirs(os.path.join(D, "klip"), exist_ok=True); GY = os.path.join(D, "klip", "gorevler.json")
G = json.load(open(GY, encoding="utf8")) if os.path.exists(GY) else {}
istenen = [s["ad"] for s in S["sahneler"]] if sys.argv[2:] == ["hepsi"] else sys.argv[2:]
H = ["-H", "Authorization: Bearer proxy-injected"]

def curl(*a):
    return subprocess.run(["curl", "-sS", "-m", "120", *a], capture_output=True, text=True).stdout

def uret(s):
    ad = s["ad"]; cikti = os.path.join(D, "klip", ad + ".mp4"); kare = os.path.join(D, "kare", ad + ".png")
    if os.path.exists(cikti): return ad, "var (atlandı)"
    if not os.path.exists(kare): return ad, "HATA: kare yok"
    g = G.get(ad, {})
    if not g.get("task_id"):
        im = Image.open(kare).convert("RGB"); im.thumbnail((1366, 768)); t = io.BytesIO(); im.save(t, "JPEG", quality=92)
        istek = {"model": "MiniMax-Hailuo-2.3-Fast", "prompt": s["video"], "duration": 6, "resolution": "768P",
                 "first_frame_image": "data:image/jpeg;base64," + base64.b64encode(t.getvalue()).decode()}
        yol = os.path.join(D, "klip", "_" + ad + ".json"); json.dump(istek, open(yol, "w"))
        for deneme in range(30):                              # dakikalık istek sınırına takılırsa bekleyip yeniden dener
            y = curl("-X", "POST", "https://api.minimax.io/v1/video_generation", *H, "-H", "Content-Type: application/json", "--data-binary", "@" + yol)
            if "rate limit" not in y: break
            time.sleep(20)
        os.unlink(yol)
        try: d = json.loads(y); g = {"prompt": s["video"], "task_id": d["task_id"], "resp": d.get("base_resp")}
        except Exception: return ad, "HATA (istek): " + y[:300]
        if not g["task_id"]: return ad, "HATA (istek): " + y[:300]
        G[ad] = g; json.dump(G, open(GY, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    for _ in range(120):
        time.sleep(8); d = json.loads(curl("https://api.minimax.io/v1/query/video_generation?task_id=" + g["task_id"], *H) or "{}")
        if d.get("status") == "Success":
            f = json.loads(curl("https://api.minimax.io/v1/files/retrieve?file_id=" + d["file_id"], *H))
            subprocess.run(["curl", "-sS", "-f", "-m", "300", "-o", cikti, f["file"]["download_url"]], check=True)
            g.update(status="done", file_id=d["file_id"]); json.dump(G, open(GY, "w", encoding="utf8"), ensure_ascii=False, indent=1)
            return ad, "tamam"
        if d.get("status") == "Fail": g["status"] = "fail"; return ad, "HATA (üretim): " + json.dumps(d, ensure_ascii=False)[:300]
    return ad, "HATA: zaman aşımı"

with ThreadPoolExecutor(4) as ex:
    for ad, sonuc in ex.map(uret, [s for s in S["sahneler"] if s["ad"] in istenen]): print(ad, "->", sonuc, flush=True)
