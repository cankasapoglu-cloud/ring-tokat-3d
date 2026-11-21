#!/usr/bin/env python3
"""yerlesim.json ozeti (yalniz okur): dize tablosu, onarilan dizelerin heceleri, onarim listesi."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *

Y = oku_json(CIKTI_JSON)
print(json.dumps(Y["form"], ensure_ascii=False))
print(json.dumps(Y["audio"], ensure_ascii=False))
print("dize | olcu (kita ici) | olcu basi | kaynak olcu basi | kaydirma | ofset (tempo analizi) | kaynak giris-cikis | hedef giris-cikis | onarim | metin")
for L in Y["lines"]:
    print("K%d L%d | %2d (%d) | %9.4f | %8.4f | %9.5f | %+.4f (%+.4f) | %8.4f-%8.4f | %9.4f-%9.4f | %s | %s" % (
        L["verse"], L["line"], L["dest_bar"], L["bar_in_verse"], L["dest_bar_downbeat"], L["src_downbeat"], L["shift_sec"], L["offset_used_sec"],
        L["offset_from_tempo_analysis_sec"], L["src_in"], L["src_out"], L["dest_in"], L["dest_out"], "EVET" if L["repaired"] else "-", L["text"]))
for v, l in ((6, 2), (6, 3), (6, 4), (3, 4)):
    L = [q for q in Y["lines"] if q["verse"] == v and q["line"] == l][0]
    print("--- K%d L%d %s" % (v, l, L["text"]))
    for h in L["syllables"]:
        print("   %-5s %-12s kaynak %8.4f-%8.4f (%s) hedef %9.4f-%9.4f unlu %9.4f = %.3f vurus | MIDI %s %s | %s" % (
            h["text"], h["word"], h["src_start"], h["src_end"], h["src_line"], h["dest_start"], h["dest_end"], h["dest_vowel_onset"], h["vowel_onset_beats_in_bar"],
            h["midi"], h["note"], h["note_text"] or ""))
print(json.dumps(Y["repairs"], ensure_ascii=False, indent=1))
