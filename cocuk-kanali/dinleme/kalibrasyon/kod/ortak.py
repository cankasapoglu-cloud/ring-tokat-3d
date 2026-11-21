#!/usr/bin/env python3
"""Kalibrasyon yardimcilari: dokum yukleme (onbellekteki Scribe ya da eski *_words.json), rapor okuma."""
import os, sys, json
BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(BURASI)), "arac"))
import dinle_sozler as z
from set import SET, KAL, KOK

def dokum(s):
    """Donus: (sozcukler, olaylar, kaynak, ham). sozcuk: {metin, normal, bas, son, logprob}"""
    if s.get("mevcut_dokum_yol"):
        d = json.load(open(s["mevcut_dokum_yol"], encoding="utf8"))
        w = d["words"] if isinstance(d, dict) else d
        ham = {"words": [{"text": x["text"], "type": x.get("type", "word"), "start": x["start"], "end": x["end"]} for x in w]}
        kaynak = "eski *_words.json"
    else:
        var, oz = z.onbellekte(s["tam_yol"])
        if not var:
            return None, None, "yok", None
        ham = json.load(open(var, encoding="utf8"))
        kaynak = "Scribe (onbellek)"
    soz, olay = z.duyulanlar(ham)
    return soz, olay, kaynak, ham

def rapor(s):
    y = os.path.join(s["cikti"], "rapor.json")
    return json.load(open(y, encoding="utf8")) if os.path.exists(y) else None
