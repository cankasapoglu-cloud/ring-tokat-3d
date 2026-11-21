#!/usr/bin/env python3
"""Kesif (yalniz okur): tempo.json ve kesim.json'un yapisi + bu adimin kullandigi alanlar. Hicbir dosya yazmaz."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *


def goster(o, derinlik=0, en=3):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)):
                print("  " * derinlik + "%s: %s len=%d" % (k, type(v).__name__, len(v)))
                if derinlik < en:
                    goster(v, derinlik + 1, en)
            else:
                print("  " * derinlik + "%s: %s" % (k, repr(v)[:300]))
    elif isinstance(o, list) and o:
        print("  " * derinlik + "[0] / %d: %s" % (len(o), type(o[0]).__name__))
        if isinstance(o[0], (dict, list)):
            if derinlik < en:
                goster(o[0], derinlik + 1, en)
        else:
            print("  " * derinlik + repr(o[:8])[:300])


if __name__ == "__main__":
    T, K = oku_json(TEMPO), oku_json(KESIM)
    print("=== tempo.json yapisi ==="); goster(T, en=2)
    print("=== kesim.json yapisi ==="); goster(K, en=4)
    beat = T["summary"]["beat_sec"]
    db_ = {(L["verse"], L["line"]): L["downbeat"] for L in T["lines"]}
    print("=== tempo.json dizeler ===")
    for L in T["lines"]:
        print(L["verse"], L["line"], L["first_word"], "onset", L["onset"], "unlu", L["vowel_onset"], "olcu basi", L["downbeat"], "ofset", L["offset_sec"],
              "unlu ofseti", L["vowel_offset_sec"], "sessiz nokta", L["quietest_point_before_line"], L["quietest_level_db_re_line_peak"])
    print("=== kesim.json dizeler / parcalar ===")
    for v in K["verses"]:
        for L in v["lines"]:
            print(" K%d L%d" % (v["verse"], L["line"]), repr(L["text"]), "bas", L["start"], "son", L["end"], "guclu baslangic", L["onset_strong"], "kesim", L["cut_in"], L["cut_out"],
                  "rms", L["rms_dbfs"], "kuyruk", L.get("tail_end"))
            if "ending" in L:
                print("    bitis:", json.dumps(L["ending"], ensure_ascii=False))
        for c in v["chunks"]:
            print("  parca", json.dumps(c, ensure_ascii=False))
    print("=== heceler: butun L2'ler, K6 L3, K2 L3 (vurus konumlariyla) ===")
    for vi, li in [(v, 2) for v in range(1, 8)] + [(6, 3), (2, 3)]:
        L = K["verses"][vi - 1]["lines"][li - 1]
        d = db_[(vi, li)]
        print("--- K%d L%d %s (olcu basi %.4f)" % (vi, li, L["text"], d))
        for h in L["syllables"]:
            eb = h.get("end_boundary") or {}
            print("  %-5s %-12s %.4f-%.4f (%3.0f ms) unlu %.4f = %.3f vurus | MIDI %s | sinir %s %s dBFS" % (
                h["text"], h["word"], h["start"], h["end"], h["duration"] * 1000, h["vowel_onset"], (h["vowel_onset"] - d) / beat, h["f0_midi"], eb.get("kind"), eb.get("min_level_dbfs")))
    print("=== verse6_repair ==="); print(json.dumps(K["verse6_repair"], ensure_ascii=False, indent=1))
    print("=== l4_comparison (ozet) ===")
    for r in K["l4_comparison"]["ranking"]:
        print(r)
