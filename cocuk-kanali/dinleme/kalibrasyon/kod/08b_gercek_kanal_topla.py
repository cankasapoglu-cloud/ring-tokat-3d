#!/usr/bin/env python3
"""Otomatik ayirma (--ayir) ile gercek kanallarla (--vokal/--altyapi) yapilan olcumleri yan yana toplar -> ara/gercek_kanallar.json
Ucuncu ornek: aracin kurucusunun daha once urettigi dinleme/raporlar/ornek_kita1_kanalli (salt okunur)."""
import os, sys, json, importlib.util
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from set import SET, KAL, KOK
spec = importlib.util.spec_from_file_location("topla", os.path.join(os.path.dirname(os.path.abspath(__file__)), "05_olcumleri_topla.py"))
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)
ad2 = {s["ad"]: s for s in SET}
C = {}
def al(ad, etiket, klasor):
    s = dict(ad2[ad]); s["cikti"] = klasor
    m = t.topla(s)
    if m:
        C.setdefault(ad, {})[etiket] = {k: v for k, v in m.items() if not isinstance(v, (list, dict)) or k in ("y_isaretler",)}
al("ali-baba__dinle_2", "otomatik ayırma (karşılaştırma için: aynı vokalin özgün kaydı)", ad2["ali-baba__dinle_2"]["cikti"])
for ad in ("ali-baba__dogal_onizleme", "ali-baba__sarki_birlesik"):
    al(ad, "otomatik ayırma", ad2[ad]["cikti"]); al(ad, "gerçek kanallar", ad2[ad]["cikti"] + "__gercek_kanallar")
al("ali-baba__ornek_kita1", "otomatik ayırma", ad2["ali-baba__ornek_kita1"]["cikti"])
al("ali-baba__ornek_kita1", "gerçek kanallar (kurucunun raporu)", os.path.join(KOK, "dinleme", "raporlar", "ornek_kita1_kanalli"))
json.dump(C, open(os.path.join(KAL, "ara", "gercek_kanallar.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
for ad, g in C.items():
    for e, m in g.items():
        print("%-28s %-40s v-a %s kaydir %s destek %s fark %s gamici %s akor %s cent %s 25c %s cak %s/%s R %s kayma %s donmus %s oynak %s izg %s zarf %s isaret %s" % (
            ad, e[:40], m.get("vokal_eksi_altyapi_db"), m.get("en_iyi_kaydirma"), m.get("destek_gercek"), m.get("destek_fark"), m.get("gam_ici"), m.get("akor_sesi"), m.get("cent_medyan"), m.get("yuzde_25cent"),
            m.get("cakisan"), m.get("uzun_nota"), m.get("ritim_R"), m.get("ritim_kayma_ms"), m.get("y_donmus_sure_orani"), m.get("y_nota_ici_oynaklik_cent_medyan"), m.get("y_perde_izgaraya_yapisma_R"), m.get("y_zarf_titremesi_db"), m.get("y_isaret_sayisi")))
