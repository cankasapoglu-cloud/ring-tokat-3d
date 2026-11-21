#!/usr/bin/env python3
"""dogrula.py - dinle.py'nin olcumlerini CEVABI BILINEN denetim sesleriyle sinar ("kulak yerine" aracin kalibrasyonu).

Insan kulagi olmadigi icin aracin dogru olctugunu ancak boyle gosterebiliriz:
  1) Uyum ve ritim: projenin kendi altyapisi (ali-baba/yeni/altyapi.wav; tonu, temposu, notalari zaman.json'da yazili) ustune,
     notalari TAM yerinde ve TAM akortlu yapay bir "kusursuz sarkici" sentezlenir. Sonra bilerek bozulur:
     yarim ses yukari, 40 cent tiz, 70 ms gec, rastgele zamanlama. Arac her bozulmayi dogru adlandirmali.
  2) Yapaylik vekilleri: gercek bir vokal kanali alinir ve bilerek bozulur (perdesi cetvelle duzlestirilir, 1,6 kat
     esnetilir, 4 kHz'de kesilir). Hangi vekil hangi bozulmaya tepki veriyor, hangisi vermiyor?
Sonuc: dinleme/kurulum/dogrulama.json ve ekrana ozet tablo.

Kullanim: python3 dogrula.py [--vokal gercek_vokal.wav]
"""
import os, sys, json, glob, argparse, warnings

warnings.filterwarnings("ignore")
BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
import numpy as np
import librosa
import dinle_olcum as o

KOK = os.path.dirname(os.path.dirname(BURASI))                      # cocuk-kanali/
YENI = os.path.join(KOK, "ali-baba", "yeni")
SR = o.SR


def sarkici(notalar, sure, kaydir_yarim_ses=0.0, gecikme=0.0, titreme=0.0, tohum=1):
    """Notalari tam yerinde soyleyen yapay ses: 8 armonik, 15 ms giris, hafif cikis."""
    rng = np.random.default_rng(tohum)
    y = np.zeros(int(sure * SR), np.float32)
    for n in notalar:
        bas = n["baslangic"] + gecikme + (rng.uniform(-titreme, titreme) if titreme else 0.0)
        uz = max(0.08, n["sure"] * 0.92)
        f = 440.0 * 2 ** ((n["midi"] + kaydir_yarim_ses - 69) / 12)
        t = np.arange(int(uz * SR)) / SR
        s = sum(np.sin(2 * np.pi * f * h * t) / h for h in range(1, 9))
        z = np.minimum(1.0, t / 0.015) * np.minimum(1.0, (uz - t) / 0.04)
        i = int(bas * SR)
        if i < 0 or i >= len(y):
            continue
        s = (0.2 * s * z).astype(np.float32)[:len(y) - i]
        y[i:i + len(s)] += s
    return y


def uyum_ve_ritim():
    z = json.load(open(os.path.join(YENI, "zaman.json"), encoding="utf8"))
    notalar = [n for k in z["kitalar"] for n in k["notalar"]]
    ax, asr = o.ses_coz(os.path.join(YENI, "altyapi.wav"))
    alt = o.tek_kanal(ax, asr)
    pk = o.spektrum_paketi(alt)
    tempo, vurus = o.vurus_izgarasi(pk["oenv"])
    ak, eg = o.akor_ve_ton(alt, ax.mean(axis=1), pk, vurus)
    tempo_i, vur_i, _ = o.ince_vurus_izgarasi(alt)
    bilinen = {"tempo_bpm": z["tempo_bpm"], "ton": z["ton"], "ton_degisimi_sn": z["ton_degisimi"]["zaman_sn"]}
    bulunan = {"tempo_bpm": round(tempo_i, 2), "ton_parcalari": [(x["bas"], x["son"], x["ton"], x["belirsiz"]) for x in ak["ton_parcalari"]],
               "akor_sureleri": ak["akor_sureleri_sn"]}
    satirlar = []
    denetimler = [("kusursuz (tam yerinde, tam akortlu)", {}),
                  ("yarim ses yukari (yanlis ton)", {"kaydir_yarim_ses": 1.0}),
                  ("iki yarim ses asagi (yanlis ton)", {"kaydir_yarim_ses": -2.0}),
                  ("40 cent tiz (detone)", {"kaydir_yarim_ses": 0.4}),
                  ("70 ms gec", {"gecikme": 0.07}),
                  ("rastgele +-90 ms zamanlama", {"titreme": 0.09})]
    for ad, kw in denetimler:
        v = sarkici(notalar, len(alt) / SR, **kw)
        t, hz, gv, sesli, fb = o.f0_izle(v, pyin_denetim=False)
        midi = 69 + 12 * np.log2(np.where(hz > 0, hz, 440.0) / 440.0) - eg["akort"]
        nt = o.notalara_bol(t, midi, sesli)
        uy, _ = o.vokal_uyum(t, midi, sesli, nt, ak, eg)
        dz, dzeg = o.duzey_zaman(v, alt, t[sesli])
        on, _ = o.vokal_baslangiclari(v, dzeg["t"], dzeg["aktif"])
        rt, _ = o.ritim(on, vur_i, tempo_i)
        rt2, _ = o.ritim(on, np.arange(0, len(alt) / SR, 60.0 / z["tempo_bpm"]), z["tempo_bpm"])
        satirlar.append({"denetim": ad, "nota_sayisi": len(nt), "gercek_nota_sayisi": len(notalar),
                         "armonik_destek_farki": uy["armonik_destek"]["fark"], "en_iyi_kaydirma": uy["ton_kaydirma_denemesi"]["en_iyi_kaydirma_yarim_ses"],
                         "gam_ici": uy["gam_ici_sure_orani"], "akor_sesi": uy["akor_sesi_sure_orani"], "cent_medyan": uy["cent_sapma_medyan_mutlak"],
                         "vokal_akort_kaymasi_cent": uy["vokal_akort_kaymasi_cent"], "cakisan_uzun_nota": uy["cakisan_uzun_nota_sayisi"],
                         "ritim_R_otomatik_izgara": rt.get("sekizlik", {}).get("sikilik_R"), "kayma_ms_otomatik_izgara": rt.get("sekizlik", {}).get("ortalama_kayma_ms"),
                         "ritim_R_gercek_izgara": rt2.get("sekizlik", {}).get("sikilik_R"), "kayma_ms_gercek_izgara": rt2.get("sekizlik", {}).get("ortalama_kayma_ms"),
                         "yuzde_40ms_gercek_izgara": rt2.get("sekizlik", {}).get("yuzde_40ms_icinde")})
    return {"bilinen": bilinen, "bulunan": bulunan, "denetimler": satirlar}


def vekil_olc(sinyal):
    t, hz, gv, sesli, fb = o.f0_izle(sinyal, pyin_denetim=False)
    midi = 69 + 12 * np.log2(np.where(hz > 0, hz, 440.0) / 440.0)
    nt = o.notalara_bol(t, midi, sesli)
    if not nt:
        return {"not": "nota yok"}
    cek = np.concatenate([n["cekirdek"] for n in nt])
    sap = (midi[cek] - np.round(midi[cek])) * 100
    uy = {"perde_izgaraya_yapisma_R": float(np.abs(np.exp(2j * np.pi * sap / 100).mean()))}
    y = o.yapaylik(sinyal, t, midi, sesli, nt, uy)
    return {k: y.get(k) for k in ("nota_ici_oynaklik_cent_medyan", "cok_duz_nota_orani", "bagli_gecis_suresi_ms_medyan", "perde_izgaraya_yapisma_R",
                                  "vibratolu_uzun_nota_orani", "donmus_unlu_sayisi_045sn_ustu", "donmus_sure_orani",
                                  "sesli_cercevelerde_ardisik_benzerlik_medyan", "unsuzlerde_tiz_payi_db", "vokal_ust_frekans_hz",
                                  "tiz_doku_degisim_katsayisi", "zarf_titremesi_db", "isaret_sayisi", "isaretler")}


def yapaylik_denetimi(vokal_yolu):
    import pyworld as pw
    vx, vsr = o.ses_coz(vokal_yolu)
    v = o.tek_kanal(vx, vsr)[:int(60 * SR)]                          # ilk 60 sn yeter
    olc = vekil_olc
    sonuc = {"asil": olc(v)}
    # (1) perdesi cetvelle duzlestirilmis (WORLD): her nota tek frekans
    x = v.astype(np.float64)
    f0, tt = pw.harvest(x, SR, f0_floor=80, f0_ceil=1000, frame_period=5.0)
    sp = pw.cheaptrick(x, f0, tt, SR)
    ap = pw.d4c(x, f0, tt, SR)
    sonuc["WORLD yeniden sentez (perde ayni)"] = olc(pw.synthesize(f0, sp, ap, SR, 5.0).astype(np.float32))
    duz = f0.copy()
    m = 69 + 12 * np.log2(np.where(f0 > 0, f0, 440.0) / 440.0)
    duz[f0 > 0] = 440.0 * 2 ** ((np.round(m[f0 > 0]) - 69) / 12)        # en yakin yarim sese yapistir
    sonuc["perde yarim seslere yapistirilmis (sert akort)"] = olc(pw.synthesize(duz, sp, ap, SR, 5.0).astype(np.float32))
    # (2) 1,6 kat esnetilmis (faz vokoderi)
    sonuc["1,6 kat esnetilmis (faz vokoderi)"] = olc(librosa.effects.time_stretch(v, rate=1 / 1.6))
    # (3) WORLD ile 1,8 kat esnetilmis (spektrum cerceveleri tekrar edilerek)
    idx = np.minimum(len(f0) - 1, (np.arange(int(len(f0) * 1.8)) / 1.8).astype(int))
    sonuc["WORLD ile 1,8 kat esnetilmis (cerceve tekrari)"] = olc(pw.synthesize(f0[idx], np.ascontiguousarray(sp[idx]), np.ascontiguousarray(ap[idx]), SR, 5.0).astype(np.float32))
    # (4) 4 kHz alcak geciren
    import scipy.signal as ss
    b, a_ = ss.butter(8, 4000 / (SR / 2))
    sonuc["4 kHz'de kesilmis (boguk)"] = olc(ss.filtfilt(b, a_, v).astype(np.float32))
    return sonuc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vokal", help="yapaylik denetimi icin gercek bir vokal kanali (yoksa onbellekteki ilk ayrilmis vokal)")
    ap.add_argument("--ek-vokal", nargs="*", default=[], help="yalnizca olculup tabloya eklenecek baska vokaller (ornek: reddedilmis bir surum)")
    a = ap.parse_args()
    R = {}
    if os.path.exists(os.path.join(YENI, "altyapi.wav")):
        R["uyum_ve_ritim"] = uyum_ve_ritim()
        print("\n== UYUM VE RITIM denetimi (bilinen: %s)" % json.dumps(R["uyum_ve_ritim"]["bilinen"], ensure_ascii=False))
        print("   bulunan: %s" % json.dumps(R["uyum_ve_ritim"]["bulunan"], ensure_ascii=False))
        for s in R["uyum_ve_ritim"]["denetimler"]:
            print("  %-38s destek %+.3f | en iyi kaydirma %+d | gam ici %.2f | akor sesi %.2f | cent %5.1f (kayma %+5.1f) | cakisan %3d | "
                  "R oto %.2f (%+4d ms) | R gercek %.2f (%+4d ms, %%%d)" % (
                      s["denetim"], s["armonik_destek_farki"], s["en_iyi_kaydirma"], s["gam_ici"], s["akor_sesi"], s["cent_medyan"], s["vokal_akort_kaymasi_cent"],
                      s["cakisan_uzun_nota"], s["ritim_R_otomatik_izgara"] or 0, s["kayma_ms_otomatik_izgara"] or 0, s["ritim_R_gercek_izgara"] or 0,
                      s["kayma_ms_gercek_izgara"] or 0, s["yuzde_40ms_gercek_izgara"] or 0))
    vokal = a.vokal
    if not vokal:
        bul = sorted(glob.glob(os.path.join(o.ONBELLEK_BUYUK, "*", "ham", "*(Vocals)*.wav")))
        vokal = bul[0] if bul else None
    if vokal:
        R["yapaylik"] = {"kaynak": vokal, "denetimler": yapaylik_denetimi(vokal)}
        for ek in a.ek_vokal:
            vx, vsr = o.ses_coz(ek)
            R["yapaylik"]["denetimler"]["EK: " + os.path.basename(ek)] = vekil_olc(o.tek_kanal(vx, vsr)[:int(60 * SR)])
        print("\n== YAPAYLIK VEKILLERI denetimi (kaynak: %s)" % vokal)
        for ad, s in R["yapaylik"]["denetimler"].items():
            if not s:
                continue
            print("  %-48s %s" % (ad, json.dumps({k: v for k, v in s.items() if k != "isaretler"}, ensure_ascii=False)))
            for i in s.get("isaretler") or []:
                print("      isaret: " + i)
    hedef = os.path.join(os.path.dirname(BURASI), "kurulum", "dogrulama.json")
    os.makedirs(os.path.dirname(hedef), exist_ok=True)
    json.dump(R, open(hedef, "w", encoding="utf8"), ensure_ascii=False, indent=1, default=lambda x: float(x) if isinstance(x, (np.floating,)) else str(x))
    print("\nyazildi:", hedef)


if __name__ == "__main__":
    main()
