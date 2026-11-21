#!/usr/bin/env python3
"""dinle.py'yi DEGISTIRMEDEN calistiran ince sarici (kalibrasyon icin).
Tek farki: KALIBRASYON_MEVCUT_DOKUM ortam degiskeni bir *_words.json dosyasini gosteriyorsa, Scribe'a gitmek yerine o eski
dokum kullanilir (kredi harcanmaz). Eski dokumlerde sozcuk guveni (logprob) ve dil olasiligi YOKTUR; raporda bu belirtilir.
Bunun disinda dinle.py aynen calisir (ayni olcumler, ayni panolar, ayni onbellek ve kredi defteri)."""
import os, sys, json
ARAC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "arac")
sys.path.insert(0, ARAC)
import dinle_sozler as z

MEVCUT = os.environ.get("KALIBRASYON_MEVCUT_DOKUM")
if MEVCUT:
    def _yukle():
        d = json.load(open(MEVCUT, encoding="utf8"))
        w = d["words"] if isinstance(d, dict) else d
        words = [{"text": x["text"], "type": x.get("type", "word"), "start": x["start"], "end": x["end"]} for x in w]
        return {"language_code": None, "language_probability": None, "text": " ".join(x["text"] for x in words if x["type"] != "spacing"),
                "words": words, "kaynak_notu": "sarkinin yanindaki eski *_words.json (bu calismadan once alinmis Scribe dokumu); logprob yok"}
    z.onbellekte = lambda yol, model="scribe_v1": (MEVCUT, z._ozet(yol))
    z.scribe = lambda yol, sure_sn, **k: (_yukle(), {"kaynak": "mevcut *_words.json (yeniden dokum alinmadi; sozcuk guveni yok)", "dosya": MEVCUT, "kredi": 0})
else:
    # guvenlik: kalibrasyon kosusunda CANLI cagri yapilmasin; dokumler 01_dokum_al.py ile onceden alindi (onbellekte olmali)
    _asil = z.scribe
    def _yalniz_onbellek(yol, sure_sn, **k):
        var, oz = z.onbellekte(yol)
        if not var:
            return None, {"kaynak": "reddedildi", "neden": "kalibrasyon sarici: onbellekte dokum yok, canli cagri kapali"}
        return _asil(yol, sure_sn, **k)
    z.scribe = _yalniz_onbellek
import dinle
dinle.main()
