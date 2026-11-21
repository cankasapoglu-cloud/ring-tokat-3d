#!/usr/bin/env python3
"""Butun kalibrasyon raporlarindan (raporlar/<ad>/rapor.json) boyut boyut sayilari toplar -> ara/olcumler.json ve ekrana tablo."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *

def al(d, yol, vars=None):
    for k in yol.split("."):
        if not isinstance(d, dict) or k not in d:
            return vars
        d = d[k]
    return d

def topla(s):
    R = rapor(s)
    if R is None:
        return None
    m = {"ad": s["ad"], "yol": s["yol"], "karar": s["karar"], "gerekce": s["gerekce"], "boyut": s["boyut"], "sarki": s["sarki"]}
    g = lambda y, v=None: al(R, y, v)
    m["hatalar"] = [h["bolum"] + ": " + h["hata"][:120] for h in R.get("hatalar", [])]
    m["sure_sn"] = g("temel.sure_sn"); m["lufs"] = g("temel.lufs"); m["tepe_dbtp"] = g("temel.gercek_tepe_dbtp")
    # enerji
    m["enerji_puani"] = g("enerji.enerji_puani.puan_0_100"); m["tempo_bpm"] = g("enerji.tempo_bpm"); m["olay_sn"] = g("enerji.olay_yogunlugu_sn")
    m["nabiz"] = g("enerji.nabiz_netligi"); m["vurmali_armonik_db"] = g("enerji.vurmali_armonik_db"); m["aki"] = g("enerji.spektral_aki_ort")
    m["parlaklik_hz"] = g("enerji.parlaklik_agirlik_merkezi_hz"); m["duzey_oynakligi_db"] = g("enerji.duzey_oynakligi_db")
    m["coca_cosku"] = g("musiccoca.cosku.fark"); m["coca_tempo"] = g("musiccoca.tempo.fark"); m["coca_kalite"] = g("musiccoca.kayit_kalitesi.fark"); m["coca_sarki_var"] = g("musiccoca.sarki_var.fark")
    m["ced_ninni"] = g("etiket_karisim.ninni_olasiligi"); m["ced_coskulu_eksi_sakin"] = g("etiket_karisim.coskulu_eksi_sakin")
    for k_, a_ in (("Happy music", "ced_mutlu"), ("Exciting music", "ced_heyecanli"), ("Tender music", "ced_yumusak"), ("Music for children", "ced_cocuk")):
        m[a_] = g("etiket_karisim.duygu." + k_)
    m["ced_hayvan"] = g("etiket_karisim.hayvan")
    # kanallar
    m["vokal_eksi_altyapi_db"] = g("kanallar.vokal_eksi_altyapi_db_medyan"); m["vokalli_oran"] = g("kanallar.vokalli_sure_orani"); m["sizinti_db"] = g("kanallar.sizinti.fark_db")
    m["gomuk_yer"] = len(g("kanallar.vokalin_gomuldugu_yerler", []) or [])
    # armoni + uyum
    m["ton"] = g("armoni.ton"); m["ton_belirsiz"] = g("armoni.ton_belirsiz"); m["akor_guveni"] = g("armoni.akor_guveni_ort"); m["ton_degisimi"] = g("armoni.ton_degisimi_var")
    m["destek_fark"] = g("uyum.armonik_destek.fark"); m["destek_gercek"] = g("uyum.armonik_destek.gercek"); m["en_iyi_kaydirma"] = g("uyum.ton_kaydirma_denemesi.en_iyi_kaydirma_yarim_ses")
    m["sifir_kacinci"] = g("uyum.ton_kaydirma_denemesi.sifir_kacinci")
    m["gam_ici"] = g("uyum.gam_ici_sure_orani"); m["gam_guvenilir"] = g("uyum.gam_guvenilir_mi"); m["akor_sesi"] = g("uyum.akor_sesi_sure_orani"); m["gam_disi"] = g("uyum.gam_disi_orani")
    m["cent_medyan"] = g("uyum.cent_sapma_medyan_mutlak"); m["yuzde_25cent"] = g("uyum.yuzde_25cent_icinde"); m["cakisan"] = g("uyum.cakisan_uzun_nota_sayisi"); m["uzun_nota"] = g("uyum.uzun_nota_sayisi_03sn_ustu")
    m["cakisan_oran"] = (m["cakisan"] / m["uzun_nota"]) if m["uzun_nota"] else None
    # ritim
    m["ritim_R"] = g("ritim.sekizlik.sikilik_R"); m["ritim_kayma_ms"] = g("ritim.sekizlik.ortalama_kayma_ms"); m["ritim_40ms"] = g("ritim.sekizlik.yuzde_40ms_icinde"); m["ritim_tempo"] = g("ritim.tempo_bpm")
    m["ritim_R16"] = g("ritim.onaltilik.sikilik_R")
    # perde + dogallik
    m["nota_sayisi"] = g("perde.nota_sayisi"); m["ses_araligi_ys"] = g("perde.ses_araligi.yarim_ses"); m["medyan_hz"] = g("perde.ses_araligi.medyan_hz"); m["pyin_uyum"] = g("perde.izleme.pyin_ile_uyum_yuzde_50cent")
    m["sesli_cerceve"] = g("perde.izleme.sesli_cerceve_orani")
    m["nota_suresi_medyan"] = g("perde.nota_suresi_medyan_sn"); m["gecis_cerceve_orani"] = g("perde.gecis_cerceve_orani"); m["kayan_nota_orani"] = g("perde.kayan_nota_orani")
    m["alttan_giris_orani"] = g("perde.alttan_giris_orani"); m["ani_gecis_orani"] = g("dogallik_vekilleri.ani_gecis_orani_35ms_alti"); m["uzun_nota_035"] = g("perde.uzun_nota_sayisi_035sn_ustu")
    for k_ in ("nota_ici_oynaklik_cent_medyan", "cok_duz_nota_orani", "perde_izgaraya_yapisma_R", "vibratolu_uzun_nota_orani", "donmus_unlu_sayisi_045sn_ustu", "donmus_sure_orani",
               "unsuzlerde_tiz_payi_db", "vokal_ust_frekans_hz", "tiz_doku_degisim_katsayisi", "zarf_titremesi_db", "isaret_sayisi", "isaretler", "bagli_gecis_suresi_ms_medyan",
               "sesli_cercevelerde_ardisik_benzerlik_medyan"):
        m["y_" + k_] = g("dogallik_vekilleri." + k_)
    m["dnsmos"] = g("kalite_tahminleri.dnsmos.genel"); m["nisqa"] = g("kalite_tahminleri.nisqa.genel"); m["distillmos"] = g("kalite_tahminleri.distillmos.genel"); m["utmos22"] = g("kalite_tahminleri.utmos22.genel")
    m["nisqa_kesintisizlik"] = g("kalite_tahminleri.nisqa.kesintisizlik"); m["nisqa_renk"] = g("kalite_tahminleri.nisqa.renklenmezlik")
    for k_, a_ in (("Singing", "v_sarki"), ("Speech", "v_konusma"), ("Synthetic singing", "v_sentetik_sarki"), ("Speech synthesizer", "v_konusma_sentezi"), ("Female singing", "v_kadin"), ("Child singing", "v_cocuk")):
        m[a_] = g("etiket_vokal.ses_turu." + k_)
    # sozler
    m["dokum_kaynagi"] = g("sozler.dokum_kaynagi.kaynak"); m["dil_olasiligi"] = g("sozler.dil_olasiligi")
    m["wer"] = g("sozler.karsilastirma.sozcuk_hata_orani"); m["wer_kucuksuz"] = g("sozler.karsilastirma.kucuk_farklar_sayilmazsa_hata_orani")
    m["degisik"] = g("sozler.karsilastirma.degisik"); m["eksik"] = g("sozler.karsilastirma.eksik"); m["fazla"] = g("sozler.karsilastirma.fazla"); m["beklenen_sozcuk"] = g("sozler.karsilastirma.beklenen_sozcuk")
    m["yanlis_sozcukler"] = [(w["beklenen"], w["duyulan"], w["zaman"]) for w in g("sozler.karsilastirma.yanlis_sozcukler", []) or []]
    m["eksik_sozcukler"] = [(w["beklenen"], w["yaklasik_zaman"]) for w in g("sozler.karsilastirma.eksik_sozcukler", []) or []]
    m["fazla_sozcukler"] = [(w["duyulan"], w["zaman"]) for w in g("sozler.karsilastirma.fazla_sozcukler", []) or []]
    m["hece_sn_soz_ici"] = g("sozler.hece_hizi.soz_icinde_hece_sn"); m["hece_sn_obek_medyan"] = g("sozler.hece_hizi.obek_hece_sn_medyan"); m["hece_sn_en_hizli"] = g("sozler.hece_hizi.obek_hece_sn_en_hizli")
    m["cok_hizli_obek"] = len(g("sozler.hece_hizi.cok_hizli_obekler", []) or []); m["dusuk_guvenli"] = len(g("sozler.dusuk_guvenli_sozcukler", []) or [])
    m["ses_olaylari"] = [(e["etiket"], e["bas"]) for e in g("sozler.ses_olaylari", []) or []]
    m["ozet"] = {o["konu"]: o["durum"] for o in R.get("ozet", [])}
    m["sorun_sayisi"] = {}
    for so in R.get("sorunlar", []):
        m["sorun_sayisi"][so["sira"]] = m["sorun_sayisi"].get(so["sira"], 0) + 1
    m["calisma_sn"] = R.get("toplam_sure_sn")
    return m

if __name__ == "__main__":
    M = [x for x in (topla(s) for s in SET) if x]
    os.makedirs(os.path.join(KAL, "ara"), exist_ok=True)
    json.dump(M, open(os.path.join(KAL, "ara", "olcumler.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    def f(v, n=2):
        if v is None: return "-"
        if isinstance(v, bool): return "E" if v else "H"
        if isinstance(v, (int,)): return str(v)
        if isinstance(v, float): return ("%." + str(n) + "f") % v
        return str(v)
    def tablo(baslik, sutunlar):
        print("\n### " + baslik)
        print("%-30s %-8s " % ("ad", "karar") + " ".join("%10s" % c[0][:10] for c in sutunlar))
        for m in M:
            print("%-30s %-8s " % (m["ad"], m["karar"]) + " ".join("%10s" % f(m.get(c[1]), c[2] if len(c) > 2 else 2) for c in sutunlar))
    tablo("TEMEL + ENERJI", [("sure", "sure_sn", 0), ("lufs", "lufs", 1), ("puan", "enerji_puani", 0), ("bpm", "tempo_bpm", 0), ("olay/sn", "olay_sn"), ("nabiz", "nabiz"), ("vur/arm", "vurmali_armonik_db", 1),
                               ("aki", "aki"), ("parlak", "parlaklik_hz", 0), ("coca", "coca_cosku"), ("cocatempo", "coca_tempo"), ("ninni", "ced_ninni", 3), ("cos-sak", "ced_coskulu_eksi_sakin", 3)])
    tablo("UYUM + RITIM", [("v-a dB", "vokal_eksi_altyapi_db", 1), ("vokalli", "vokalli_oran"), ("sizinti", "sizinti_db", 0), ("destek", "destek_fark"), ("kaydir", "en_iyi_kaydirma"), ("0 sirasi", "sifir_kacinci"), ("gamici", "gam_ici"), ("gamguv", "gam_guvenilir"),
                             ("akorses", "akor_sesi"), ("gamdisi", "gam_disi"), ("cent", "cent_medyan", 1), ("%25c", "yuzde_25cent", 0), ("cakisan", "cakisan"), ("uzun", "uzun_nota"), ("R8", "ritim_R"), ("kayma", "ritim_kayma_ms", 0), ("akorguv", "akor_guveni")])
    tablo("DOGALLIK", [("oynak", "y_nota_ici_oynaklik_cent_medyan", 1), ("duz", "y_cok_duz_nota_orani"), ("izgaraR", "y_perde_izgaraya_yapisma_R"), ("vibr", "y_vibratolu_uzun_nota_orani"), ("donmus#", "y_donmus_unlu_sayisi_045sn_ustu"),
                         ("donmus%", "y_donmus_sure_orani", 3), ("unsuztiz", "y_unsuzlerde_tiz_payi_db", 1), ("ustHz", "y_vokal_ust_frekans_hz"), ("tizdoku", "y_tiz_doku_degisim_katsayisi"), ("zarf", "y_zarf_titremesi_db", 1),
                         ("isaret", "y_isaret_sayisi"), ("dnsmos", "dnsmos"), ("nisqa", "nisqa"), ("distill", "distillmos"), ("utmos", "utmos22"), ("v_sarki", "v_sarki"), ("v_konus", "v_konusma"), ("v_sent", "v_sentetik_sarki", 3)])
    tablo("SOZLER", [("WER", "wer", 3), ("WERkucuk", "wer_kucuksuz", 3), ("degisik", "degisik"), ("eksik", "eksik"), ("fazla", "fazla"), ("bekl", "beklenen_sozcuk"), ("hece/sn", "hece_sn_soz_ici"), ("obekmed", "hece_sn_obek_medyan"),
                       ("enhizli", "hece_sn_en_hizli"), ("hizliobek", "cok_hizli_obek"), ("dusukguv", "dusuk_guvenli"), ("dilp", "dil_olasiligi")])
    for m in M:
        print("\n", m["ad"], "| hatalar:", m["hatalar"], "| ozet:", m["ozet"])
        print("    isaretler:", m["y_isaretler"]); print("    yanlis:", m["yanlis_sozcukler"][:12]); print("    eksik:", m["eksik_sozcukler"][:12]); print("    fazla:", m["fazla_sozcukler"][:12])
        print("    ton:", m["ton"], "belirsiz" if m["ton_belirsiz"] else "", "| CED hayvan:", m["ced_hayvan"], "| ses olaylari:", m["ses_olaylari"][:12])
