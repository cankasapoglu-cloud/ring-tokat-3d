#!/usr/bin/env python3
"""Dokumlerden yapisal soz denetimleri (aracin sozcuk hata oranina EK; aracin kendi dokum/hizalama islevleri kullanilir):
  a) Ali Baba 'diye bagirir' kayitlari: her kitada hangi hayvan, hangi ses SOYLENMIS (dokume gore) ve ses o hayvana uyuyor mu
  b) Parmak Ailesi: her kitada soylenen aile adlari (beklenen sira: baba, anne, abi, abla, bebek)
  c) Scribe sozcuk guveni (logprob) ozetleri (yalnizca bu calismada alinan dokumlerde var)
Cikti: kalibrasyon/ara/soz_denetimi.json"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
import numpy as np

HAYVAN = [("inek", ["inek"]), ("koyun", ["koyun"]), ("at", ["at"]), ("horoz", ["horoz"]), ("ördek", ["ördek", "ordek"]), ("köpek", ["köpek", "kopek"]), ("kedi", ["kedi"])]
SES = {"inek": r"^m[öo]+$", "koyun": r"^(m|b)e+$", "at": r"^(i+h?a+|iha(ha)*|ha|ihan|hii+)$", "horoz": r"^(ü+|ürü|ü+rü+ü*|kukuriku)$",
       "ördek": r"^vak$", "köpek": r"^hav$", "kedi": r"^m[iı]yav$"}

def hayvan_bul(n):
    for ad, kokler in HAYVAN:
        for k in kokler:
            if n.startswith(z.normalle(k)) and (ad != "at" or re.match(r"^at(ı|i|lar|ları|ılar|ıları)?$", n)):
                return ad
    return None

def ali_baba(soz):
    """Kitalar 'ali' sozcuguyle baslayan obeklere bolunur; 'var' ile 'diye' arasindaki sozcukler soylenen sestir."""
    n = [w["normal"] for w in soz]
    kitalar, i = [], 0
    bas = [k for k in range(len(n)) if n[k] == "ali" and k + 2 < len(n) and n[k + 2] == "bir"]
    for b, s in zip(bas, bas[1:] + [len(n)]):
        dilim = list(range(b, s))
        hay = None
        for k in dilim:
            if n[k].startswith("çiftli") and k + 1 < s:
                for kk in range(k + 1, min(k + 4, s)):
                    hay = hayvan_bul(n[kk]) or hay
                if hay:
                    break
        ses = []
        for k in dilim:
            if n[k] == "diye":
                j = k - 1
                while j >= b and n[j] != "var":
                    ses.append(k and soz[j]); j -= 1
                break
        ses = ses[::-1]
        sesler = [w["metin"].strip('".,“” ') for w in ses]
        uyan = [bool(re.match(SES[hay], w["normal"])) for w in ses] if hay else []
        hangi = sorted({h for w in ses for h, d in SES.items() if re.match(d, w["normal"])})
        kitalar.append({"bas_sn": round(soz[b]["bas"], 1), "hayvan": hay, "soylenen_ses": " ".join(sesler), "ses_zamani": [round(ses[0]["bas"], 2), round(ses[-1]["son"], 2)] if ses else None,
                        "ses_hayvana_uyuyor": (all(uyan) if uyan else None), "ses_hangi_hayvanin": hangi,
                        "ses_logprob": [round(w["logprob"], 2) for w in ses if w.get("logprob") is not None]})
    return kitalar

def parmak(soz):
    n = [w["normal"] for w in soz]
    adlar = {"baba", "anne", "abi", "abla", "bebek", "able", "ağabey", "dede", "nine"}
    kitalar, cur = [], None
    for k, w in enumerate(n):
        if w in adlar and k + 1 < len(n) and n[k + 1] == "parmak":
            if cur is None or soz[k]["bas"] - cur["son"] > 4.0:
                cur = {"bas_sn": round(soz[k]["bas"], 1), "adlar": [], "son": soz[k]["bas"]}
                kitalar.append(cur)
            cur["adlar"].append(w); cur["son"] = soz[k]["bas"]
        elif w == "parmak" and cur is not None and soz[k]["bas"] - cur["son"] < 4.0:
            cur["son"] = soz[k]["bas"]
    bek = ["baba", "anne", "abi", "abla", "bebek"]
    for i, kt in enumerate(kitalar):
        kt.pop("son")
        kt["beklenen"] = bek[i] if i < 5 else None
        kt["dogru"] = (kt["adlar"] == [bek[i]] * 2) if i < 5 else None
    return kitalar

def guven(soz):
    lp = np.array([w["logprob"] for w in soz if isinstance(w.get("logprob"), (int, float))], float)
    if not len(lp):
        return None
    return {"sozcuk": int(len(lp)), "ortalama_logprob": round(float(lp.mean()), 3), "medyan": round(float(np.median(lp)), 3), "en_dusuk": round(float(lp.min()), 2),
            "oran_-0.1_alti": round(float((lp < -0.1).mean()), 3), "oran_-0.3_alti": round(float((lp < -0.3).mean()), 3),
            "en_dusuk_5": sorted([(round(w["logprob"], 2), w["metin"], round(w["bas"], 1)) for w in soz if isinstance(w.get("logprob"), (int, float))])[:5]}

C = {}
for s in SET:
    soz, olay, kaynak, ham = dokum(s)
    if soz is None:
        C[s["ad"]] = {"dokum": "yok"}; continue
    c = {"dokum_kaynagi": kaynak, "sozcuk": len(soz), "metin": " ".join(w["metin"] for w in soz), "ses_olaylari": [(o["metin"], round(o["bas"], 1)) for o in olay],
         "dil_olasiligi": (ham or {}).get("language_probability"), "guven": guven(soz)}
    if s["sozler"] in ("ali_baba_v2.txt", "ali_baba_coskulu.txt"):
        c["kitalar"] = ali_baba(soz)
    if s["sarki"] == "parmak-ailesi":
        c["kitalar"] = parmak(soz)
    C[s["ad"]] = c
os.makedirs(os.path.join(KAL, "ara"), exist_ok=True)
json.dump(C, open(os.path.join(KAL, "ara", "soz_denetimi.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
for ad, c in C.items():
    print("==", ad, c.get("dokum_kaynagi"), "| guven:", {k: v for k, v in (c.get("guven") or {}).items() if k != "en_dusuk_5"} or "-")
    if c.get("guven"):
        print("     en dusuk:", c["guven"]["en_dusuk_5"])
    for k in c.get("kitalar", []):
        print("    ", json.dumps(k, ensure_ascii=False))
