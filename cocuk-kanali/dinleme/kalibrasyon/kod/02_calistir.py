#!/usr/bin/env python3
"""Kalibrasyon kumesindeki her dosyada dinle.py'yi (--ayir, sozleri bilinenlerde --sozler) SIRAYLA calistirir.
Cikti: kalibrasyon/raporlar/<ad>/ (rapor.md, rapor.json, panolar). Raporu olan dosya atlanir (yeniden icin --yeniden).
Kullanim: python3 02_calistir.py [--yeniden] [ad ...]"""
import os, sys, subprocess, time, json
BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
from set import SET, KAL
SIRA = ["ali-baba__v2_2", "ali-baba__dinle_2", "ali-baba__ornek_kita1", "ali-baba__dogal_onizleme", "parmak-ailesi__duzgun_1",
        "parmak-ailesi__coskulu_1", "parmak-ailesi__yavas_2", "el-yikama__sarki_1", "el-yikama__coskulu_2", "ali-baba__sarki_birlesik",
        "parmak-ailesi__duzgun_2", "parmak-ailesi__turkce_2", "parmak-ailesi__sarki_2", "pitirin-ailesi__yavas_2",
        "ali-baba__demo_altyapi_sesli", "ali-baba__coskulu_2", "ali-baba__coskulu_1"]
arg = [a for a in sys.argv[1:] if not a.startswith("--")]
yeniden = "--yeniden" in sys.argv
ad2 = {s["ad"]: s for s in SET}
assert set(SIRA) == set(ad2), set(ad2) ^ set(SIRA)
os.makedirs(os.path.join(KAL, "gunluk"), exist_ok=True)
for ad in (arg or SIRA):
    s = ad2[ad]
    if os.path.exists(os.path.join(s["cikti"], "rapor.json")) and not yeniden:
        print("atlandi (rapor var):", ad, flush=True); continue
    komut = [sys.executable, os.path.join(BURASI, "dinle_sarici.py"), s["tam_yol"], "--ayir", "--cikti", s["cikti"]]
    if s["sozler_yol"]:
        komut += ["--sozler", s["sozler_yol"]]
    ortam = dict(os.environ)
    ortam.pop("KALIBRASYON_MEVCUT_DOKUM", None)
    if s["mevcut_dokum_yol"]:
        ortam["KALIBRASYON_MEVCUT_DOKUM"] = s["mevcut_dokum_yol"]
    t = time.time()
    with open(os.path.join(KAL, "gunluk", ad + ".log"), "w") as g:
        r = subprocess.run(komut, stdout=subprocess.DEVNULL, stderr=g, env=ortam)
    hata = ""
    try:
        R = json.load(open(os.path.join(s["cikti"], "rapor.json"), encoding="utf8"))
        hata = "; ".join(h["bolum"] for h in R.get("hatalar", []))
    except Exception as e:
        hata = "rapor okunamadi: %s" % e
    print("%-32s cikis=%d  %5.0f sn  %s" % (ad, r.returncode, time.time() - t, ("HATALAR: " + hata) if hata else "tamam"), flush=True)
