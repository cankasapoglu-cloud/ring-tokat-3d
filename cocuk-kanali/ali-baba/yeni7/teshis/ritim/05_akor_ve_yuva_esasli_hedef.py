#!/usr/bin/env python3
"""Soru 2'nin devamı: (a) vokalin hedef notası, bulunduğu vuruşun AKORUNA uyuyor mu (akor sesi mi)?  RED (eski hedefler) / RED (yuva esaslı öneri) / REF (özgün söyleyiş, v2_2 akorları).
(b) Öneri: her hecenin hedefi = hecenin sekizlik yuvasında orkestra ezgisinin çaldığı nota. ara/hedefler_yuva_esasli.json'a yazılır (mevcut hedefler.json'a dokunulmaz).
(c) Önerinin PSOLA'ya maliyeti: özgün perdeden kaç yarım ses kaydırma gerekiyor (eski / yeni)."""
import json, os, numpy as np
from collections import Counter
from ortak import *

Z = json.load(open(ZAMAN, encoding="utf8")); H = json.load(open(HEDEF, encoding="utf8")); Y = json.load(open(YERLESIM, encoding="utf8"))
KC = json.load(open(os.path.join(A, "yeni4", "analiz", "tempo", "key_chords.json")))
AD = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
AKOR = {"G": {7, 11, 2}, "C": {0, 4, 7}, "D7": {2, 6, 9, 0}}
yuva = {(L["verse"], L["line"], s["index"]): (s["dest_bar"], s["beat_in_bar"], s["src_start"], s["midi"]) for L in Y["lines"] for s in L["syllables"]}
klar = [n for n in Z["ezgi_notalari"] if n["parti"] == "ezgi_alti" and n["enstruman"] == "klarnet"]
EZGI = {}                                    # (ölçü, sekizlik yuva) -> klarnet notasının perde sınıfı
for n in klar: EZGI[(n["olcu"], int(round(n["vurus"] * 2)))] = n["midi"] % 12
def ezgi_notasi(olcu, sek):
    s = int(np.floor(sek + 1e-6))
    while s >= 0:
        if (olcu, s) in EZGI: return EZGI[(olcu, s)]
        s -= 1
    return None
def en_yakin_midi(ps, ozgun_ps_hedef_bolgesi=(62, 67)):
    return [m for m in range(60, 72) if m % 12 == ps and 62 <= m <= 67][0] if any(m % 12 == ps and 62 <= m <= 67 for m in range(60, 72)) else 60 + ps

tablo = []; yeni_hedef = []
for h in H:
    olcu, bib, src, ozgun = yuva[(h["verse"], h["line"], h["index"])]
    kita = Z["kitalar"][h["verse"] - 1]; ko = olcu - kita["ilk_olcu"]; akor = kita["akorlar"][ko][int(np.floor(bib + 1e-6))]
    eps = ezgi_notasi(olcu, bib * 2); yeni = en_yakin_midi(eps)                     # D4 / E4 / G4 (vokalin şimdiki ses alanı)
    # REF: aynı hecenin özgün perdesi ve v2_2'deki vuruşunun akoru
    n = int(np.floor((src + 0.06 - REF_FAZ) / REF_VURUS + 1e-6)); poz = (n - 15) % 24; p = KC["positions"][poz]
    kok = AD.index(p["chord"].rstrip("m")); ref_akor = {kok, (kok + 3) % 12, (kok + 4) % 12, (kok + 7) % 12}      # majör/minör belirsiz -> ikisi de kabul
    tablo.append({"kita": h["verse"], "satir": h["line"], "hece": h["text"], "vurus": bib, "akor": akor, "eski_hedef": h["hedef_midi"], "yeni_hedef": yeni, "ozgun_midi": ozgun,
                  "eski_akor_sesi": h["hedef_midi"] % 12 in AKOR[akor], "yeni_akor_sesi": yeni % 12 in AKOR[akor], "ref_akor": p["chord"], "ref_akor_sesi": int(round(ozgun)) % 12 in ref_akor,
                  "ref_poz_vurus": poz % 4, "eski_kaydirma": h["hedef_midi"] - ozgun, "yeni_kaydirma": yeni - ozgun})
    yeni_hedef.append(dict(h, hedef_midi_eski=h["hedef_midi"], hedef_midi=yeni, sekizlik_yuva=bib * 2))
def pay(anahtar, f=lambda r: True):
    s = [r[anahtar] for r in tablo if f(r)]; return {"akor_sesi": int(sum(s)), "toplam": len(s), "yuzde": round(100 * float(np.mean(s)), 1)}
vurus_ustu = lambda r: r["vurus"] % 1 == 0
sonuc = {"tanim": __doc__,
    "akor_sesi_orani": {
        "RED_eski_hedef": {"tum_heceler": pay("eski_akor_sesi"), "vurus_ustundeki_heceler": pay("eski_akor_sesi", vurus_ustu),
                           "vurusa_gore": {str(b): pay("eski_akor_sesi", lambda r, b=b: r["vurus"] == b) for b in (0, 1, 2, 3)}},
        "RED_yuva_esasli_oneri": {"tum_heceler": pay("yeni_akor_sesi"), "vurus_ustundeki_heceler": pay("yeni_akor_sesi", vurus_ustu),
                           "vurusa_gore": {str(b): pay("yeni_akor_sesi", lambda r, b=b: r["vurus"] == b) for b in (0, 1, 2, 3)}},
        "REF_ozgun_soyleyis": {"tum_heceler": pay("ref_akor_sesi"), "vurus_ustundeki_heceler": pay("ref_akor_sesi", vurus_ustu),
                           "vurusa_gore": {str(b): pay("ref_akor_sesi", lambda r, b=b: r["vurus"] == b) for b in (0, 1, 2, 3)},
                           "not": "v2_2 akorları key_chords.json kestirimidir (majör/minör belirsiz olduğundan kök üstünde iki üçlü de akor sesi sayıldı)"}},
    "degisen_hece": int(sum(r["eski_hedef"] != r["yeni_hedef"] for r in tablo)),
    "PSOLA_kaydirma_yarim_ses": {"eski": ozet([abs(r["eski_kaydirma"]) for r in tablo]), "yeni": ozet([abs(r["yeni_kaydirma"]) for r in tablo]),
                                 "eski_4_yarim_sesten_fazla": int(sum(abs(r["eski_kaydirma"]) > 4 for r in tablo)), "yeni_4_yarim_sesten_fazla": int(sum(abs(r["yeni_kaydirma"]) > 4 for r in tablo)),
                                 "yeni_6_yarim_sesten_fazla": int(sum(abs(r["yeni_kaydirma"]) > 6 for r in tablo)),
                                 "yeni_en_buyukler": sorted([(round(r["yeni_kaydirma"], 1), r["kita"], r["satir"], r["hece"]) for r in tablo], key=lambda x: -abs(x[0]))[:10]},
    "kural": "hedef(hece) = ezgi[floor(sekizlik yuva)],  ezgi (ölçü içi sekizlikler 0..7) = G G G D E E D D;  'diye bağırır' = G.  10 heceli 1. dize: G G G G D E E D D D;  9 heceli 2./4. dize: G G G D E E D D D"}
json.dump(sonuc, open(os.path.join(ARA, "05_akor_ve_oneri.json"), "w"), ensure_ascii=False, indent=1)
json.dump(yeni_hedef, open(os.path.join(ARA, "hedefler_yuva_esasli.json"), "w"), ensure_ascii=False, indent=1)
json.dump(tablo, open(os.path.join(ARA, "05_hece_akor_tablosu.json"), "w"), ensure_ascii=False, indent=0)
print(json.dumps({k: v for k, v in sonuc.items() if k != "tanim"}, ensure_ascii=False, indent=1))
for r in tablo[:19]: print("  %-4s %-5s vuruş %-4s akor %-2s eski %s%s yeni %s%s | özgün %.1f -> kaydırma eski %+.1f yeni %+.1f | REF akor %s %s" % (r["satir"], r["hece"], r["vurus"], r["akor"], AD[r["eski_hedef"] % 12], "" if r["eski_akor_sesi"] else "(x)", AD[r["yeni_hedef"] % 12], "" if r["yeni_akor_sesi"] else "(x)", r["ozgun_midi"], r["eski_kaydirma"], r["yeni_kaydirma"], r["ref_akor"], "" if r["ref_akor_sesi"] else "(x)"))
