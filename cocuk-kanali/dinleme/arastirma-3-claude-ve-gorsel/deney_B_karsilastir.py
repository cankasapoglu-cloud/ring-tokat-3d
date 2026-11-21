#!/usr/bin/env python3
"""Deney B sonucu: (1) Claude'un yalniz resme bakarak buldugu hatalar,
(2) sayisal olcumden esik kuraliyla bulunan hatalar, (3) gizli dogru cevap."""
import json, os
B = os.path.dirname(os.path.abspath(__file__))
gorsel = json.load(open(os.path.join(B, "deney-B-ezgi-hata", "claude_gorsel_okuma.json")))
sonuc = {}
def sinif(tur):  # hata turunu kaba sinifa indir
    if tur in ("+50c", "-40c"): return "detone(<=50c)"
    if tur in ("+100c", "-200c"): return "yanlis_nota"
    if tur in ("gec180ms", "erken120ms"): return "zamanlama"
    return tur
for ad in ("kisa", "uzun"):
    dogru = {int(k): v for k, v in json.load(open(os.path.join(B, "gizli", f"B_dogru_{ad}.json")))["hatalar"].items()}
    olcum = json.load(open(os.path.join(B, "deney-B-ezgi-hata", f"{ad}_olcum.json")))
    # sayisal kural (esikler onceden sabit): eksik: sesli_oran<0.3 ; yanlis nota: |sapma|>=75c ;
    # detone: 30c<=|sapma|<75c ; zamanlama: |giris farki|>=90ms ; duz: oynaklik std<4c
    sayisal = {}
    for o in olcum:
        if o["sesli_oran"] < 0.3: sayisal[o["i"]] = "eksik"; continue
        s, g, v = o["medyan_sapma_cent"], o["giris_farki_ms"], o["perde_oynakligi_cent_std"]
        if s is not None and abs(s) >= 75: sayisal[o["i"]] = "yanlis_nota"
        elif s is not None and abs(s) >= 30: sayisal[o["i"]] = "detone(<=50c)"
        elif g is not None and abs(g) >= 90: sayisal[o["i"]] = "zamanlama"
        elif v is not None and v < 4: sayisal[o["i"]] = "duz"
    dsinif = {k: sinif(v) for k, v in dogru.items()}
    def puan(bulunan):
        tp = sum(1 for k, v in bulunan.items() if dsinif.get(k) == v)
        return {"bulunan": len(bulunan), "dogru_bulunan": tp, "yanlis_alarm": len(bulunan) - tp,
                "kacan": sorted(set(dsinif) - {k for k, v in bulunan.items() if dsinif.get(k) == v})}
    g = gorsel[ad]
    g_emin = {int(k): sinif(v) for k, v in g["emin"].items()}
    g_emin_olasi = {**g_emin, **{int(k): sinif(v) for k, v in g["olasi"].items()}}
    g_hepsi = {**g_emin_olasi, **{int(k): sinif(v) for k, v in g["zayif"].items()}}
    print(f"\n== {ad}: gizli hatalar ({len(dogru)}) = {dict(sorted(dogru.items()))}")
    r = {"gizli_hata_sayisi": len(dogru),
         "gorsel_emin": puan(g_emin), "gorsel_emin+olasi": puan(g_emin_olasi), "gorsel_hepsi(zayif dahil)": puan(g_hepsi),
         "sayisal_kural": puan(sayisal)}
    for k, v in r.items(): print("  ", k, v)
    print("   sayisal bulgular:", dict(sorted(sayisal.items())))
    print("   olcum tablosu (hatali ya da isaretlenen notalar):")
    for o in olcum:
        if o["i"] in dogru or o["i"] in sayisal or o["i"] in g_hepsi:
            print("     ", o, "| gizli:", dogru.get(o["i"], "-"), "| gorsel:", g_hepsi.get(o["i"], "-"))
    sonuc[ad] = r
json.dump(sonuc, open(os.path.join(B, "deney-B-ezgi-hata", "sonuc.json"), "w"), ensure_ascii=False, indent=1)
