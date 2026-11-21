"""Scribe JSON ozetleyici: metin, dil olasiligi, ses olaylari, dusuk guvenli kelimeler."""
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print("keys:", sorted(d.keys()))
print("language:", d.get("language_code"), "prob:", d.get("language_probability"))
print("text:", d.get("text"))
ws = d.get("words", [])
types = {}
for w in ws:
    types[w.get("type")] = types.get(w.get("type"), 0) + 1
print("word types:", types)
for w in ws:
    if w.get("type") != "spacing":
        print(f"{w.get('start'):7.2f}-{w.get('end'):7.2f} {w.get('type'):11s} logprob={w.get('logprob')} {w.get('text')!r}")
