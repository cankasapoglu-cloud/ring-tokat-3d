#!/usr/bin/env python3
"""dinle.py - Claude'un "kulak yerine" kullandigi dinleme araci.

Claude ses DUYAMAZ. Bu arac bir ses dosyasini olcer, makine modellerine dinletir ve Claude'un okuyabilecegi
uc sey uretir:  rapor.md (kisa, duz Turkce ozet)  |  rapor.json (butun sayilar)  |  PNG panolar (bakilarak okunur).
Hicbiri insan kulaginin yerini tutmaz; her bolumde "neyi soyleyemez" notu vardir.

KULLANIM
  python3 dinle.py <ses dosyasi> [--sozler beklenen_sozler.txt] [--cikti klasor] [--ayir]

  --ayir                 vokal / altyapi ayir (UVR-MDX-NET-Voc_FT; ~90 sn, sonucu onbelleklenir). Perde, uyum, ritim,
                         dogallik olcumleri icin GEREKLI (ya da asagidaki --vokal/--altyapi).
  --vokal F --altyapi F  elinizde kuru vokal ve altyapi AYRI dosya olarak varsa (ayni zaman ekseni): ayirmadan daha guvenilir.
  --kuru                 verilen dosyanin kendisi kuru vokal (altyapisiz): perde / dogallik olculur, uyum ve ritim olculmez.
  --sozler DOSYA         beklenen sozler (duz metin). ElevenLabs Scribe ile dokum alinir (dosya basina BIR kez, onbellekli,
                         kredi defterli) ve sozcuk sozcuk karsilastirilir. # ile baslayan satirlar, [..] ve (..) yok sayilir.
  --dokum                beklenen soz olmadan da Scribe dokumu al (sozcuk zamanlari, hece hizi, hayvan sesi etiketleri).
  --bpm N [--ilk-vurus S]  gercek tempo (ve ilk vurusun saniyesi) biliniyorsa verin: ritim olcumu cok daha guvenilir olur.
  --gemini               ses girisli dil modeline (Google Gemini) de dinlet (anahtar ag vekilinde tanimliysa; yoksa atlar).
  --hizli                model tabanli tahminleri (CED, MusicCoCa, MOS) atla.
  --panelsiz             PNG uretme.

CIKTI  (varsayilan: dinleme/raporlar/<dosya adi>/)
  rapor.md, rapor.json, 00_genel_bakis.png, NN_pano_<bas>-<son>sn.png, NN_perde_<bas>-<son>sn.png
"""
import os, sys, json, time, argparse, math, traceback

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
BURASI = os.path.dirname(os.path.abspath(__file__))
if BURASI not in sys.path:
    sys.path.insert(0, BURASI)
import numpy as np

SURUM = "1.0 (2026-11-21)"


def gunluk(*a):
    print(*a, file=sys.stderr, flush=True)


class Sayac:
    def __init__(self):
        self.t = time.time()
        self.sureler = {}

    def gec(self, ad):
        s = time.time() - self.t
        self.sureler[ad] = round(self.sureler.get(ad, 0) + s, 1)
        self.t = time.time()
        gunluk("  [%-22s %5.1f sn]" % (ad, s))


def json_temiz(o):
    if isinstance(o, dict):
        return {str(k): json_temiz(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [json_temiz(v) for v in o]
    if isinstance(o, np.ndarray):
        return json_temiz(o.tolist()) if o.size <= 64 else "<dizi %s>" % (o.shape,)
    if isinstance(o, (np.floating,)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    return o


def tr(x, n=1):
    """Sayiyi Turkce ondalik virgulle yazar."""
    if x is None:
        return "?"
    if isinstance(x, bool):
        return "evet" if x else "hayır"
    if isinstance(x, int):
        return str(x)
    return (("%." + str(n) + "f") % x).replace(".", ",")


# ==========================================================================================================
def calistir(a):
    import dinle_olcum as o
    S = Sayac()
    R = {"arac": "dinle.py " + SURUM, "dosya": os.path.abspath(a.ses), "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
         "uyari": "Bu rapor olcum ve makine tahminidir; insan kulagi degildir. Son karar dinleyen insanindir.", "hatalar": []}
    P = {}                                                     # panel verisi

    def dene(ad, f):
        try:
            return f()
        except Exception as e:
            R["hatalar"].append({"bolum": ad, "hata": "%s: %s" % (type(e).__name__, str(e)[:300])})
            gunluk("  !! %s atlandi: %s: %s" % (ad, type(e).__name__, str(e)[:200]))
            if a.ayikla:
                traceback.print_exc()
            return None

    # ---------------- a) temel
    x, sr = o.ses_coz(a.ses)
    sure = len(x) / sr
    R["temel"] = o.temel(a.ses, x, sr)
    y = o.tek_kanal(x, sr)
    S.gec("cozme + temel")
    if sure < 1.0:
        R["hatalar"].append({"bolum": "genel", "hata": "dosya 1 saniyeden kisa"})
        return R, P
    # ---------------- b) enerji
    pk = o.spektrum_paketi(y)
    en, en_egri = o.enerji(y, pk, bpm=a.bpm, ilk_vurus=a.ilk_vurus)
    R["enerji"] = en
    S.gec("enerji")
    P.update({"sure": sure, "mel_db": pk["mel_db"], "oenv": en_egri["oenv"], "rms_db": en_egri["rms_db"], "vurus": en_egri["vurus"],
              "bolumler_5sn": en.get("bolumler_5sn"), "tempo_yazi": tr(en.get("tempo_bpm"), 1),
              "baslik": os.path.basename(a.ses)})
    x16 = o.tek_kanal(x, sr, 16000)
    if not a.hizli:
        import dinle_model as dm
        R["etiket_karisim"] = dene("CED (karisim)", lambda: dm.ced_etiket(x16))
        S.gec("CED etiket (karisim)")
        if not a.kuru:
            R["musiccoca"] = dene("MusicCoCa", lambda: dm.musiccoca(x16))
            S.gec("MusicCoCa")
            if R.get("musiccoca") and R["musiccoca"].get("cosku_zaman"):
                P["cosku_zaman"] = R["musiccoca"]["cosku_zaman"]

    # ---------------- c) kanallar
    v = alt = alt44 = None
    kaynak = None
    if a.vokal:
        vx, vsr = o.ses_coz(a.vokal)
        v = o.tek_kanal(vx, vsr)
        kaynak = "verilen dosyalar (--vokal%s)" % (" / --altyapi" if a.altyapi else "")
        if a.altyapi:
            ax_, asr = o.ses_coz(a.altyapi)
            alt = o.tek_kanal(ax_, asr)
            alt44 = ax_.mean(axis=1) if asr == 44100 else None
    elif a.kuru:
        v, kaynak = y, "dosyanin kendisi (--kuru)"
    elif a.ayir:
        def ayir():
            vy, ay, bilgi = o.kanallari_ayir(a.ses, gunluk=gunluk)
            vx, vsr = o.ses_coz(vy)
            ax_, asr = o.ses_coz(ay)
            return o.tek_kanal(vx, vsr), o.tek_kanal(ax_, asr), ax_.mean(axis=1), bilgi
        sonuc = dene("kanal ayirma", ayir)
        if sonuc:
            v, alt, alt44, bilgi = sonuc
            kaynak = "otomatik ayırma (%s%s)" % (bilgi["model"], ", önbellekten" if bilgi.get("onbellekten") else "")
            R["kanal_ayirma"] = bilgi
    R["kanal_kaynagi"] = kaynak or "yok (yalnızca karışım ölçüldü; perde / uyum / ritim / doğallık için --ayir ya da --vokal/--altyapi verin)"
    if v is not None and alt is not None:
        n = min(len(v), len(alt))
        v, alt = v[:n], alt[:n]
    S.gec("kanallar")

    # ---------------- d) altyapi (ya da karisim): ton, akor, vurus
    armoni_kaynagi = alt if alt is not None else (None if a.kuru else y)
    akor = akor_egri = None
    ince_vurus = None
    if armoni_kaynagi is not None:
        def armoni():
            pka = o.spektrum_paketi(armoni_kaynagi) if alt is not None else pk
            tempo_a, vurus_a = o.vurus_izgarasi(pka["oenv"], a.bpm, a.ilk_vurus, len(armoni_kaynagi) / o.SR)
            ak, eg = o.akor_ve_ton(armoni_kaynagi, alt44 if alt is not None else None, pka, vurus_a)
            ak["kaynak"] = "altyapı kanalı" if alt is not None else "karışım; vokal dahil olduğu için ton/akor daha az güvenilir"
            return ak, eg
        s_ = dene("ton ve akor", armoni)
        if s_:
            akor, akor_egri = s_
            R["armoni"] = akor
            P.update({"tonlar": akor_egri["tonlar"], "akorlar": akor_egri["akorlar"], "kroma": akor_egri["kroma"], "kroma_t": akor_egri["kroma_t"]})
        S.gec("ton + akor")

    # ---------------- vokal olcumleri
    notalar = []
    sorunlar = []
    if v is not None:
        duz_egri = None
        t, hz, guven, sesli, f0b = o.f0_izle(v)
        akort = akor_egri["akort"] if akor_egri else 0.0
        midi = 69 + 12 * np.log2(np.where(hz > 0, hz, 440.0) / 440.0) - akort
        notalar = o.notalara_bol(t, midi, sesli)
        S.gec("perde izleme")
        if alt is not None:
            s_ = dene("duzey", lambda: o.duzey_zaman(v, alt, t[sesli]))
            if s_:
                R["kanallar"], duz_egri = s_
                P["duzey"] = duz_egri
                P["vokal_bolumleri"] = R["kanallar"].get("vokal_bolumleri")
                for g in R["kanallar"].get("vokalin_gomuldugu_yerler", []):
                    sorunlar.append({"sira": "gömük vokal", "zaman": g["bas"], "son": g["son"], "metin": "vokal altyapının 8 dB'den fazla altında"})
        po = dene("perde ozeti", lambda: o.perde_ozeti(t, midi, sesli, notalar))
        R["perde"] = {"izleme": f0b}
        if po and isinstance(po, tuple):
            R["perde"].update(po[0])
        elif po:
            R["perde"].update(po)
        uyum = None
        uyum_egri = {}
        if akor_egri and alt is not None and notalar:
            s_ = dene("vokal-altyapi uyumu", lambda: o.vokal_uyum(t, midi, sesli, notalar, akor, akor_egri))
            if s_:
                uyum, uyum_egri = s_
                R["uyum"] = uyum
                for c_ in uyum.get("cakisan_uzun_notalar", []):
                    sorunlar.append({"sira": "çakışan / detone nota", "zaman": c_["bas"], "son": c_["bas"] + c_["sure"],
                                     "metin": "%s (%s akorunda): %s" % (c_["nota"], c_["akor"], c_["tur"])})
        P["perde"] = {"t": t, "midi": midi, "sesli": sesli, "notalar": notalar}
        P["uyum_egri"] = uyum_egri
        S.gec("nota + uyum")
        # ritim
        if alt is not None:
            def rit():
                tempo_i, vur_i, kay = o.ince_vurus_izgarasi(alt, a.bpm, a.ilk_vurus)
                on, _ = o.vokal_baslangiclari(v, duz_egri["t"] if duz_egri else None, duz_egri["aktif"] if duz_egri else None)
                c, eg = o.ritim(on, vur_i, tempo_i)
                c["vurus_izgarasi_kaynagi"] = kay
                c["tempo_bpm"] = o.yuv(tempo_i, 1)
                return c, eg, vur_i
            s_ = dene("ritim", rit)
            if s_:
                R["ritim"], rit_egri, ince_vurus = s_
                P["ritim"] = rit_egri if rit_egri else None
                P["ince_vurus"] = ince_vurus
            S.gec("ritim")
        # yapaylik vekilleri
        yp = dene("yapaylik vekilleri", lambda: o.yapaylik(v, t, midi, sesli, notalar, uyum, R.get("perde")))
        if yp:
            R["dogallik_vekilleri"] = yp
            for d_ in yp.get("donmus_unluler", []):
                sorunlar.append({"sira": "donmuş ünlü", "zaman": d_["bas"], "son": d_["bas"] + d_["sure"], "metin": "spektrum %.2f sn hiç değişmiyor" % d_["sure"]})
        S.gec("yapaylik vekilleri")
        if not a.hizli:
            import dinle_model as dm
            v16 = o.tek_kanal(v[:, None], o.SR, 16000)
            R["etiket_vokal"] = dene("CED (vokal)", lambda: {k: w for k, w in dm.ced_etiket(v16).items() if k in ("ses_turu", "sarki_eksi_konusma", "hata", "atlandi")})
            R["kalite_tahminleri"] = dene("MOS tahminleri", lambda: dm.mos_tahminleri(v16))
            if R.get("kalite_tahminleri") and not R["kalite_tahminleri"].get("atlandi"):
                P["mos"] = R["kalite_tahminleri"]
            S.gec("MOS tahminleri (vokal)")
        # vokal spektrogrami (pano icin)
        import librosa
        vm = librosa.feature.melspectrogram(y=v, sr=o.SR, n_fft=1024, hop_length=256, n_mels=128, fmin=80, fmax=8000)
        vdb = librosa.power_to_db(vm, ref=1.0, top_db=None)
        P["vokal_mel"] = np.maximum(vdb, vdb.max() - 80)

    # ---------------- g) sozler
    import dinle_sozler as z
    sonuc = None
    durum = None
    var, _oz = z.onbellekte(a.ses)
    if var or a.sozler or a.dokum:
        sonuc, durum = z.scribe(a.ses, sure, gunluk=gunluk)
    if a.sozler and not os.path.exists(a.sozler):
        R["hatalar"].append({"bolum": "sozler", "hata": "soz dosyasi bulunamadi: " + a.sozler})
        a.sozler = None
    if durum:
        R["sozler"] = {"dokum_kaynagi": durum}
    if sonuc:
        soz, olay = z.duyulanlar(sonuc)
        R["sozler"].update({"dil": sonuc.get("language_code"), "dil_olasiligi": sonuc.get("language_probability"),
                            "duyulan_metin": sonuc.get("text"), "duyulan_sozcuk_sayisi": len(soz),
                            "ses_olaylari": [{"etiket": w["metin"], "bas": round(w["bas"], 2), "son": round(w["son"], 2)} for w in olay],
                            "dusuk_guvenli_sozcukler": z.dusuk_guvenli(soz), "hece_hizi": z.hece_hizi(soz)})
        P["sozcukler"] = soz
        P["ses_olaylari"] = olay
        if a.sozler:
            bek = z.beklenen_sozcukler(open(a.sozler, encoding="utf8").read())
            if bek:
                k = z.karsilastir(bek, soz)
                k.pop("eslesme", None)
                R["sozler"]["karsilastirma"] = k
                P["yanlis_zamanlar"] = [w["zaman"] for w in k["yanlis_sozcukler"]] + [w["zaman"] for w in k["fazla_sozcukler"]]
                for w in k["yanlis_sozcukler"]:
                    sorunlar.append({"sira": "söz hatası", "zaman": w["zaman"], "metin": "beklenen '%s', duyulan '%s'" % (w["beklenen"], w["duyulan"])})
                for w in k["eksik_sozcukler"]:
                    sorunlar.append({"sira": "söz hatası", "zaman": w["yaklasik_zaman"], "metin": "eksik: '%s'" % w["beklenen"]})
                for w in k["fazla_sozcukler"]:
                    sorunlar.append({"sira": "söz hatası", "zaman": w["zaman"], "metin": "fazla: '%s'" % w["duyulan"]})
            else:
                R["hatalar"].append({"bolum": "sozler", "hata": "soz dosyasinda sozcuk bulunamadi"})
    elif a.sozler or a.dokum:
        R.setdefault("sozler", {})["not"] = "Dokum alinamadi: %s" % ((durum or {}).get("neden") or "bilinmeyen neden")
    S.gec("sozler")

    # temel sorunlar
    kp = R["temel"].get("kirpilma", {})
    if kp.get("var_mi"):
        for z_ in kp.get("ilk_zamanlar_sn", [])[:8]:
            sorunlar.append({"sira": "kırpılma / sessizlik", "zaman": z_, "metin": "kırpılma"})
    for b in (R["temel"].get("sessizlik") or {}).get("ic_bosluklar", []):
        sorunlar.append({"sira": "kırpılma / sessizlik", "zaman": b["bas"], "son": b["son"], "metin": "iç sessizlik"})
    R["sorunlar"] = sorted(sorunlar, key=lambda s: s["zaman"])
    P["sorunlar"] = sorunlar

    # nota listesi (json icin sade)
    if notalar:
        R["notalar"] = [{"bas": round(n["bas"], 2), "sure": round(n["sure"], 2), "nota": n["ad"], "cent": round(n["cent"]),
                         "ic_std_cent": round(n["ic_std_cent"], 1), "vibrato": bool(n["vibrato"] and n["vibrato"]["var"])} for n in notalar]

    # ---------------- h) Gemini (istege bagli)
    if a.gemini:
        def gem():
            import gemini_dinle as g
            return g.dinle(a.ses, sure=min(sure, 180.0))
        R["gemini"] = dene("Gemini", gem)
        S.gec("Gemini")

    R["calisma_sureleri_sn"] = S.sureler
    R["_sayac"] = S
    return R, P


# ==========================================================================================================
def panolari_ciz(R, P, cikti):
    import dinle_panel as dp
    sure = P["sure"]
    n = max(1, int(math.ceil(sure / 30.0 - 1e-6)))
    uz = sure / n
    dilimler = [(round(i * uz, 2), round(min(sure, (i + 1) * uz), 2)) for i in range(n)]
    P["dilimler"] = dilimler
    dosyalar = []
    yol = os.path.join(cikti, "00_genel_bakis.png")
    dp.genel_bakis(P, yol)
    dosyalar.append({"dosya": os.path.basename(yol), "tur": "genel bakis", "bas": 0, "son": round(sure, 1)})
    for i, (t0, t1) in enumerate(dilimler, 1):
        yol = os.path.join(cikti, "%02d_pano_%03d-%03dsn.png" % (i, int(t0), int(round(t1))))
        dp.pano(P, t0, t1, yol, i)
        dosyalar.append({"dosya": os.path.basename(yol), "tur": "genel pano", "bas": t0, "son": t1})
        if P.get("perde") and P["perde"]["notalar"]:
            yol = os.path.join(cikti, "%02d_perde_%03d-%03dsn.png" % (i, int(t0), int(round(t1))))
            dp.perde_panosu(P, t0, t1, yol, i)
            dosyalar.append({"dosya": os.path.basename(yol), "tur": "perde panosu", "bas": t0, "son": t1})
    return dosyalar


# ==========================================================================================================
def referans_cumlesi(puan, coca):
    """Projedeki sarkilarin referans tablosuna (kurulum/referans_enerji.json) gore konum cumlesi."""
    yol = os.path.join(os.path.dirname(BURASI), "kurulum", "referans_enerji.json")
    try:
        oz = json.load(open(yol, encoding="utf8"))["ozet"]
    except Exception:
        return ""
    parca = []
    for anahtar, ad, deger in (("puan", "hareketlilik puanı", puan), ("coca_cosku", "MusicCoCa coşku farkı", coca)):
        c_, y_ = (oz.get("coskulu") or {}).get(anahtar), (oz.get("yavas") or {}).get(anahtar)
        if deger is None or not c_ or not y_:
            continue
        bic = (lambda v: "%d" % round(v)) if anahtar == "puan" else (lambda v: ("%+.2f" % v).replace(".", ","))
        parca.append("%s: 'coşkulu' adlı %d sürümde %s…%s, 'yavaş' adlı %d sürümde %s…%s" % (
            ad, c_["n"], bic(c_["en_az"]), bic(c_["en_cok"]), y_["n"], bic(y_["en_az"]), bic(y_["en_cok"])))
    return ("Projedeki sürümlerle karşılaştırma (" + "; ".join(parca) + ").") if parca else ""


def rapor_md(R):
    """Kisa, duz Turkce dinleme raporu."""
    L = []
    T = R["temel"]
    ek = L.append
    ek("# Dinleme raporu: %s" % T.get("dosya"))
    ek("")
    ek("_%s — %s. Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._" % (R["zaman"], R["arac"]))
    ek("")
    ozet = []          # (durum, bolum, cumle)

    def o_(durum, bolum, cumle):
        ozet.append((durum, bolum, cumle))
    # ---- temel
    lufs, tp_ = T.get("lufs"), T.get("gercek_tepe_dbtp")
    if lufs is not None:
        d = "iyi" if -17.5 <= lufs <= -11.5 else "dikkat"
        ek_ = "" if d == "iyi" else (" (YouTube yaklaşık -14 LUFS'e çeker; %s)" % ("kısık kalır" if lufs < -17.5 else "çok sıkıştırılmış olabilir"))
        o_(d, "Ses yüksekliği", "%s LUFS, gerçek tepe %s dBTP%s." % (tr(lufs), tr(tp_), ek_))
    if tp_ is not None and tp_ > 0.0:
        o_("dikkat", "Tepe", "gerçek tepe 0 dBTP'nin üstünde (%s): bazı cihazlarda cızırtı yapabilir; -1 dBTP'ye indirin." % tr(tp_))
    if (T.get("kirpilma") or {}).get("var_mi"):
        o_("sorun", "Kırpılma", "%d yerde ardışık tam ölçek örnek var (ilk: %s sn)." % (T["kirpilma"]["ardisik_kosu_3ornek_ustu"], T["kirpilma"]["ilk_zamanlar_sn"][:3]))
    ss = T.get("sessizlik") or {}
    if ss.get("bastaki_sn", 0) > 1.0 or ss.get("sondaki_sn", 0) > 3.0 or ss.get("ic_bosluklar"):
        o_("dikkat", "Sessizlik", "başta %s sn, sonda %s sn, içeride %d boşluk." % (tr(ss.get("bastaki_sn")), tr(ss.get("sondaki_sn")), len(ss.get("ic_bosluklar", []))))
    st = (T.get("stereo") or {}).get("yorum", "")
    if "UYARI" in st:
        o_("dikkat", "Stereo", st)
    # ---- enerji
    E = R.get("enerji") or {}
    ep = (E.get("enerji_puani") or {}).get("puan_0_100")
    mc = (R.get("musiccoca") or {}).get("cosku") or {}
    ce = R.get("etiket_karisim") or {}
    if ep is not None:
        parca = ["hareketlilik puanı %d/100 (tempo %s BPM, saniyede %s olay)" % (ep, tr(E.get("tempo_bpm"), 0), tr(E.get("olay_yogunlugu_sn")))]
        durum = "bilgi"
        if mc.get("fark") is not None:
            parca.append("MusicCoCa coşku farkı %s" % ("%+.2f" % mc["fark"]).replace(".", ","))
        if ce.get("ninni_olasiligi") is not None:
            parca.append("CED 'ninni' olasılığı %s" % tr(ce["ninni_olasiligi"], 3))
        # esikler kurulum/referans_enerji.json'daki proje surumlerinden: 'yavas' adlilar puan<=61, CoCa<0, ninni>=0,023; 'coskulu' adlilar puan>=66, CoCa>=+0,09, ninni=0
        sakin = (mc.get("fark") is not None and mc["fark"] < 0.0) or (ce.get("ninni_olasiligi") or 0) >= 0.02 or ep < 62
        canli = (mc.get("fark") is None or mc["fark"] >= 0.08) and (ce.get("ninni_olasiligi") or 0) < 0.01 and ep >= 66
        durum = "dikkat" if sakin else ("iyi" if canli and (mc.get("fark") is not None) else "bilgi")
        yorum = {"dikkat": " → **ninni/sakin yana kayıyor olabilir**.", "iyi": " → makine göstergeleri coşkulu yana yakın.", "bilgi": "."}[durum]
        ref = referans_cumlesi(ep, mc.get("fark"))
        o_(durum, "Enerji / coşku", "; ".join(parca) + yorum + (" " + ref if ref else ""))
    # ---- kanallar
    K = R.get("kanallar") or {}
    if K.get("vokal_eksi_altyapi_db_medyan") is not None:
        m = K["vokal_eksi_altyapi_db_medyan"]
        o_("iyi" if -6 <= m <= 9 else "dikkat", "Vokal / altyapı dengesi",
           "vokal altyapıdan %s dB (medyan); sürenin %%%d kadarında vokal var. %s." % (("%+.1f" % m).replace(".", ","), round(100 * K.get("vokalli_sure_orani", 0)), K.get("denge_yorumu", "")))
    # ---- uyum
    U = R.get("uyum") or {}
    A = R.get("armoni") or {}
    if U.get("armonik_destek"):
        ad_ = U["armonik_destek"]
        tk = U.get("ton_kaydirma_denemesi", {})
        eniyi = tk.get("en_iyi_kaydirma_yarim_ses")
        iyi_kay = eniyi in (0, 5, -5, 7, -7)
        durum = "iyi" if (ad_["fark"] is not None and ad_["fark"] > 0.05 and eniyi == 0) else ("dikkat" if (ad_["fark"] or 0) > 0.0 and iyi_kay else "sorun")
        o_(durum, "Vokal altyapıyla aynı armonide mi",
           "armonik destek farkı %s (artı = uyumlu); en iyi kaydırma %+d yarım ses (0 olmalı)." % (("%+.3f" % ad_["fark"]).replace(".", ","), eniyi))
        gi = U.get("gam_ici_sure_orani")
        if gi is not None:
            guv = U.get("gam_guvenilir_mi")
            durum = ("iyi" if gi >= 0.9 else "dikkat" if gi >= 0.75 else "sorun") if guv else "bilgi"
            o_(durum, "Gam içi söyleme", "söylenen sürenin %%%d kadarı altyapının gamında (%s)%s; akor sesi %%%d, gam dışı %%%d." % (
                round(100 * gi), A.get("ton", "?"), "" if guv else " — ton belirsiz, bu oran güvenilmez",
                round(100 * (U.get("akor_sesi_sure_orani") or 0)), round(100 * (U.get("gam_disi_orani") or 0))))
        cm, y25 = U.get("cent_sapma_medyan_mutlak"), U.get("yuzde_25cent_icinde")
        if cm is not None:
            durum = "iyi" if (cm <= 18 and y25 >= 70) else ("dikkat" if (cm <= 28 and y25 >= 50) else "sorun")
            o_(durum, "Akort (detone mi)", "notalara uzaklık medyan %s cent; söylenen sürenin %%%d kadarı ±25 cent içinde; vokalin genel kayması %s cent." % (
                tr(cm), round(y25), ("%+.0f" % (U.get("vokal_akort_kaymasi_cent") or 0))))
        nc, nu = U.get("cakisan_uzun_nota_sayisi", 0), U.get("uzun_nota_sayisi_03sn_ustu", 0)
        o_("iyi" if nc == 0 else ("dikkat" if nc <= max(2, 0.1 * nu) else "sorun"), "Çakışan uzun notalar", "%d / %d uzun nota (0,3 sn üstü) altyapıyla çakışıyor ya da detone." % (nc, nu))
    elif R.get("perde") and R["perde"].get("nota_sayisi"):
        o_("bilgi", "Uyum", "altyapı olmadığı için vokal-altyapı uyumu ölçülmedi (yalnızca vokalin kendi perdesi ölçüldü).")
    # ---- ritim
    Rt = R.get("ritim") or {}
    if Rt.get("sekizlik"):
        s8 = Rt["sekizlik"]
        r_ = s8["sikilik_R"]
        o_("iyi" if r_ >= 0.55 else "dikkat" if r_ >= 0.3 else "sorun", "Ritme oturma",
           "sıkılık R=%s (ölçümün tavanı ≈0,65; rastgele ≈0,15); başlangıçların %%%d kadarı en yakın sekizliğe 40 ms içinde; ortalama kayma %+d ms (+ geç). %s (vuruş ızgarası: %s)." % (
               tr(r_, 2), s8["yuzde_40ms_icinde"], s8["ortalama_kayma_ms"], Rt.get("yorum", ""), Rt.get("vurus_izgarasi_kaynagi", "?")))
    # ---- dogallik
    Y = R.get("dogallik_vekilleri") or {}
    if Y:
        n_i = Y.get("isaret_sayisi", 0)
        o_("bilgi" if n_i == 0 else "dikkat", "Yapaylık işaretleri (vekil)",
           ("işaret bulunmadı — bu 'doğal' demek DEĞİLDİR, yalnızca bilinen kaba izler yok" if n_i == 0 else "%d işaret: %s" % (n_i, "; ".join(Y["isaretler"]))) + ".")
    # ---- sozler
    Sz = R.get("sozler") or {}
    Kr = Sz.get("karsilastirma")
    if Kr:
        w = Kr["sozcuk_hata_orani"]
        o_("iyi" if w <= 0.05 else "dikkat" if w <= 0.15 else "sorun", "Sözler",
           "sözcük hata oranı %%%s (%d beklenen sözcükten %d farklı, %d eksik, %d fazla); küçük ek/harf farkları sayılmazsa %%%s." % (
               tr(100 * w), Kr["beklenen_sozcuk"], Kr["degisik"], Kr["eksik"], Kr["fazla"], tr(100 * Kr["kucuk_farklar_sayilmazsa_hata_orani"])))
    elif Sz.get("not"):
        o_("ölçülemedi", "Sözler", Sz["not"])
    hh = Sz.get("hece_hizi") or {}
    if hh.get("obek_hece_sn_medyan") is not None:
        hz_ = hh["obek_hece_sn_medyan"]
        o_("dikkat" if (hz_ > 6.0 or hh.get("cok_hizli_obekler")) else "bilgi", "Söyleyiş hızı",
           "söz öbeklerinde medyan %s hece/sn (en hızlı %s)." % (tr(hz_), tr(hh.get("obek_hece_sn_en_hizli"))))

    im = {"iyi": "✅ iyi", "dikkat": "⚠️ dikkat", "sorun": "❌ sorun", "bilgi": "ℹ️ bilgi", "ölçülemedi": "➖ ölçülemedi"}
    ek("## Özet")
    ek("")
    ek("| Durum | Konu | Makinenin gördüğü |")
    ek("|---|---|---|")
    for durum, bolum, cumle in ozet:
        ek("| %s | %s | %s |" % (im[durum], bolum, cumle.replace("|", "/")))
    ek("")
    ek("Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.")
    ek("")
    ek("## Bu raporun SÖYLEYEMEDİKLERİ")
    ek("")
    ek("- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; "
       "konuşma için eğitilmiş modeller şarkıda güvenilmezdir.")
    ek("- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).")
    ek("- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.")
    ek("- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.")
    if not R.get("perde"):
        ek("- **Perde, uyum, ritim, yapaylık:** bu çalıştırmada ölçülmedi (vokal kanalı yok). `--ayir` ya da `--vokal/--altyapi` ile yeniden çalıştırın.")
    ek("")
    # ---- ayrintilar
    ek("## Ayrıntılar")
    ek("")
    ek("**Dosya:** %s sn, %s kanal, %s Hz, %s, %s kb/sn; üst frekans sınırı %s Hz. Kanal kaynağı: %s." % (
        tr(T.get("sure_sn")), T.get("kanal"), T.get("ornekleme_hz"), T.get("kodek"), tr(T.get("bit_hizi_kbps"), 0), T.get("ust_frekans_hz"), R.get("kanal_kaynagi")))
    ek("")
    ek("**Ses düzeyi:** %s LUFS; ses yüksekliği aralığı (LRA) %s LU; gerçek tepe %s dBTP; tepe faktörü %s dB. Stereo: %s (sol-sağ ilişkisi %s)." % (
        tr(lufs), tr(T.get("lra_lu")), tr(tp_), tr(T.get("tepe_faktoru_db")), (T.get("stereo") or {}).get("yorum"), tr((T.get("stereo") or {}).get("sol_sag_korelasyon"), 2)))
    ek("")
    if E:
        tk_ = E.get("tempo_kararliligi") or {}
        ek("**Enerji:** tempo %s BPM (%s); yerel temponun %%%s kadarı ±%%3 içinde; nabız netliği %s; olay yoğunluğu %s/sn; vurmalı/armonik %s dB; "
           "spektral akı %s; parlaklık (ağırlık merkezi) %s Hz; düzey oynaklığı %s dB." % (
               tr(E.get("tempo_bpm")), E.get("tempo_kaynagi"), tr(tk_.get("yuzde_3_icinde"), 0), tr(E.get("nabiz_netligi"), 2), tr(E.get("olay_yogunlugu_sn")),
               tr(E.get("vurmali_armonik_db")), tr(E.get("spektral_aki_ort"), 2), tr(E.get("parlaklik_agirlik_merkezi_hz"), 0), tr(E.get("duzey_oynakligi_db"))))
        if (E.get("enerji_puani") or {}).get("bilesenler_0_1"):
            ek("Hareketlilik puanı bileşenleri (0-1): " + ", ".join("%s %s" % (k, tr(v, 2)) for k, v in E["enerji_puani"]["bilesenler_0_1"].items()) + ".")
        ek("")
    if ce and ce.get("en_yuksek_10"):
        ek("**CED etiketleri (karışım):** " + ", ".join("%s %s" % (k, tr(v, 2)) for k, v in ce["en_yuksek_10"][:8]) + ".")
        if ce.get("hayvan"):
            ek("Hayvan sınıfları: " + (", ".join("%s %s" % (k, tr(v, 3)) for k, v in sorted(ce["hayvan"].items(), key=lambda kv: -kv[1])[:8]) or "yok") + ".")
        ek("")
    if A.get("ton_parcalari"):
        ek("**Ton (%s):** " % A.get("kaynak", "") + "; ".join("%s–%s sn %s%s" % (tr(x["bas"], 0), tr(x["son"], 0), x["ton"], " (belirsiz)" if x.get("belirsiz") else "") for x in A["ton_parcalari"])
           + ". Akort kayması %s cent. En çok duyulan akorlar: %s (ortalama güven %s)." % (
               tr(A.get("akort_kaymasi_cent")), ", ".join("%s %s sn" % (k, tr(v, 0)) for k, v in list((A.get("akor_sureleri_sn") or {}).items())[:5]), tr(A.get("akor_guveni_ort"), 2)))
        ek("")
    Pd = R.get("perde") or {}
    if Pd.get("nota_sayisi"):
        sa = Pd.get("ses_araligi") or {}
        ek("**Vokal perdesi:** %d nota; ses aralığı %s–%s (%s yarım ses), medyan %s; nota içi oynaklık medyan %s cent; çok düz nota oranı %s; "
           "vibratolu uzun nota oranı %s; geçiş çerçevesi oranı %s. Perde izleyici denetimi: pYIN ile %%%s uyum." % (
               Pd["nota_sayisi"], sa.get("alt"), sa.get("ust"), tr(sa.get("yarim_ses")), sa.get("medyan"), tr(Pd.get("nota_ici_oynaklik_cent_medyan")),
               tr(Pd.get("cok_duz_nota_orani"), 2), tr(Pd.get("vibratolu_uzun_nota_orani"), 2), tr(Pd.get("gecis_cerceve_orani"), 2),
               tr((Pd.get("izleme") or {}).get("pyin_ile_uyum_yuzde_50cent"), 0)))
        if Pd.get("vokal_ton_ks"):
            ek("Vokalin kendi ses dağılımından ton tahmini: %s (r=%s)." % (Pd["vokal_ton_ks"]["ton"], tr(Pd["vokal_ton_ks"]["r"], 2)))
        ek("")
    if U.get("cakisan_uzun_notalar"):
        ek("**Çakışan / detone uzun notalar:**")
        ek("")
        ek("| sn | süre | nota | akor | tür |")
        ek("|---|---|---|---|---|")
        for c_ in U["cakisan_uzun_notalar"][:20]:
            ek("| %s | %s | %s | %s | %s |" % (tr(c_["bas"], 1), tr(c_["sure"], 2), c_["nota"], c_["akor"], c_["tur"]))
        ek("")
    if Y:
        ek("**Yapaylık için vekil ölçümler (kanıt değil):** nota içi oynaklık %s cent; ızgaraya yapışma R %s; donmuş ünlü %s adet (sesli sürenin %%%s kadarı); "
           "ünsüzlerde tiz payı %s dB; vokalin üst frekansı %s Hz; tiz doku değişim katsayısı %s (durağan gürültü ≈0,52); zarf titremesi %s dB." % (
               tr(Y.get("nota_ici_oynaklik_cent_medyan")), tr(Y.get("perde_izgaraya_yapisma_R"), 2), Y.get("donmus_unlu_sayisi_045sn_ustu"),
               tr(100 * (Y.get("donmus_sure_orani") or 0), 0), tr(Y.get("unsuzlerde_tiz_payi_db")), Y.get("vokal_ust_frekans_hz"),
               tr(Y.get("tiz_doku_degisim_katsayisi"), 2), tr(Y.get("zarf_titremesi_db"))))
        ek("")
    Q = R.get("kalite_tahminleri") or {}
    if Q and not Q.get("atlandi"):
        def g(a_, b_="genel"):
            return tr((Q.get(a_) or {}).get(b_), 2)
        ek("**Konuşma-kalitesi tahminleri (vokal kanalı, 1-5; şarkı için eğitilmediler):** DNSMOS %s (sinyal %s, arka plan %s); NISQA %s "
           "(gürültüsüzlük %s, kesintisizlik %s, renklenmezlik %s); Distill-MOS %s; UTMOS22 %s. Yalnızca aynı yolla elde edilmiş iki vokali karşılaştırmak için." % (
               g("dnsmos"), g("dnsmos", "sinyal"), g("dnsmos", "arka_plan"), g("nisqa"), g("nisqa", "gurultusuzluk"), g("nisqa", "kesintisizlik"),
               g("nisqa", "renklenmezlik"), g("distillmos"), g("utmos22")))
        ev = (R.get("etiket_vokal") or {}).get("ses_turu") or {}
        if ev:
            ek("CED, vokal kanalını şöyle etiketliyor: şarkı %s, konuşma %s, sentetik şarkı %s, konuşma sentezleyici %s." % (
                tr(ev.get("Singing"), 2), tr(ev.get("Speech"), 2), tr(ev.get("Synthetic singing"), 3), tr(ev.get("Speech synthesizer"), 3)))
        ek("")
    if Sz.get("duyulan_metin"):
        ek("**Makinenin duyduğu sözler (Scribe, dil %s olasılık %s):**" % (Sz.get("dil"), tr(Sz.get("dil_olasiligi"), 2)))
        ek("")
        ek("> " + Sz["duyulan_metin"].replace("\n", " "))
        ek("")
        if Sz.get("ses_olaylari"):
            ek("Ses olayları: " + ", ".join("%s %s–%s sn" % (e_["etiket"], tr(e_["bas"], 1), tr(e_["son"], 1)) for e_ in Sz["ses_olaylari"][:20]) + ".")
            ek("")
        if Sz.get("dusuk_guvenli_sozcukler"):
            ek("Makinenin emin olamadığı sözcükler (belirsiz söylenmiş olabilir): " + ", ".join("'%s' %s sn" % (w["sozcuk"], tr(w["zaman"], 1)) for w in Sz["dusuk_guvenli_sozcukler"][:15]) + ".")
            ek("")
    if Kr and (Kr["yanlis_sozcukler"] or Kr["eksik_sozcukler"] or Kr["fazla_sozcukler"]):
        ek("**Söz farkları:**")
        ek("")
        ek("| sn | beklenen | duyulan | tür |")
        ek("|---|---|---|---|")
        for w in Kr["yanlis_sozcukler"][:40]:
            ek("| %s | %s | %s | %s |" % (tr(w["zaman"], 1), w["beklenen"], w["duyulan"], w["tur"]))
        for w in Kr["eksik_sozcukler"][:25]:
            ek("| ~%s | %s | — | eksik |" % (tr(w["yaklasik_zaman"], 1), w["beklenen"]))
        for w in Kr["fazla_sozcukler"][:25]:
            ek("| %s | — | %s | fazla |" % (tr(w["zaman"], 1), w["duyulan"]))
        ek("")
    G = R.get("gemini")
    if G:
        ek("**Ses girişli dil modelinin (Gemini%s) görüşü — ikinci görüş, ölçüm değil; perde/ritim/doğallık yargıları güvenilmezdir:**" % (
            ", " + G["model"] if G.get("model") else ""))
        ek("")
        if G.get("tamam") and G.get("rubrik"):
            adlar = {"DUYDUGUM": "Duyduğu", "SOZLER": "Yazdığı sözler", "SES": "Ses", "AKORT": "Akort", "RITIM": "Ritim", "ENERJI": "Enerji",
                     "TELAFFUZ": "Telaffuz", "SARKI_MI": "Şarkı mı konuşma mı", "DENGE": "Denge", "TUHAF": "Tuhaf bulduğu yerler", "OZET": "Özet"}
            ek("| Soru | Cevap | Gerekçe |")
            ek("|---|---|---|")
            for k_, ad_ in adlar.items():
                v_ = G["rubrik"].get(k_)
                if v_:
                    ek("| %s | %s | %s |" % (ad_, (v_.get("secim") or v_.get("metin") or "").replace("|", "/"), (v_.get("gerekce") or "").replace("|", "/")))
            ek("")
        elif G.get("tamam"):
            ek(G.get("yanit", ""))
            ek("")
        else:
            ek("_Alınamadı: %s_ %s" % (G.get("yanit", ""), G.get("eksik") or ""))
            ek("")
    if R.get("panolar"):
        ek("## Panolar (Read aracıyla bakın)")
        ek("")
        ek("| Dosya | Ne gösterir | Neye bakmalı |")
        ek("|---|---|---|")
        ne = {"genel bakis": ("bütün dosya: spektrogram, düzeyler, hareketlilik, sorun çizelgesi", "kırmızı X / şeritlerin toplandığı yer; hareketliliğin düştüğü bölümler"),
              "genel pano": ("30 sn: spektrogram + sözcükler, vokal spektrogramı, vuruşlar, düzey", "≠ işaretli sözcükler; vokal çizgisinin altyapının altında kaldığı yerler"),
              "perde panosu": ("30 sn: vokal perdesi akor seslerinin üstünde, cent, ritim, kroma", "kırmızı çapraz taralı notalar (gam dışı), ±25 cent bandının dışındaki X'ler, ±40 ms dışındaki başlangıçlar")}
        for p in R["panolar"]:
            ek("| `%s` | %s (%s–%s sn) | %s |" % (p["dosya"], ne[p["tur"]][0], tr(p["bas"], 0), tr(p["son"], 0), ne[p["tur"]][1]))
        ek("")
    if R.get("hatalar"):
        ek("## Atlanan / başarısız bölümler")
        ek("")
        for h in R["hatalar"]:
            ek("- %s: %s" % (h["bolum"], h["hata"]))
        ek("")
    ek("_Çalışma süresi: %s sn. Bütün sayılar: `rapor.json`._" % tr(sum((R.get("calisma_sureleri_sn") or {}).values()), 0))
    return "\n".join(L) + "\n", ozet


def main():
    ap = argparse.ArgumentParser(description="Claude icin dinleme araci (olcum + makine tahmini + PNG panolar)", epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ses")
    ap.add_argument("--sozler")
    ap.add_argument("--cikti")
    ap.add_argument("--ayir", action="store_true")
    ap.add_argument("--vokal")
    ap.add_argument("--altyapi")
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--dokum", action="store_true")
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--ilk-vurus", dest="ilk_vurus", type=float)
    ap.add_argument("--gemini", action="store_true")
    ap.add_argument("--hizli", action="store_true")
    ap.add_argument("--panelsiz", action="store_true")
    ap.add_argument("--ayikla", action="store_true", help="hata izini goster")
    a = ap.parse_args()
    if not os.path.isfile(a.ses):
        sys.exit("ses dosyasi bulunamadi: " + a.ses)
    if a.altyapi and not a.vokal:
        sys.exit("--altyapi yalnizca --vokal ile birlikte kullanilir")
    ad = os.path.splitext(os.path.basename(a.ses))[0]
    cikti = a.cikti or os.path.join(os.path.dirname(BURASI), "raporlar", ad)
    os.makedirs(cikti, exist_ok=True)
    t0 = time.time()
    gunluk("dinle.py: %s -> %s" % (a.ses, cikti))
    R, P = calistir(a)
    S = R.pop("_sayac", None)
    if not a.panelsiz and P.get("mel_db") is not None:
        try:
            for eski in os.listdir(cikti):
                if eski.endswith(".png") and eski[:2].isdigit():
                    os.unlink(os.path.join(cikti, eski))
            R["panolar"] = panolari_ciz(R, P, cikti)
        except Exception as e:
            R["hatalar"].append({"bolum": "panolar", "hata": "%s: %s" % (type(e).__name__, str(e)[:300])})
            if a.ayikla:
                traceback.print_exc()
        if S:
            S.gec("panolar")
            R["calisma_sureleri_sn"] = S.sureler
    R["toplam_sure_sn"] = round(time.time() - t0, 1)
    md, ozet = rapor_md(R)
    R["ozet"] = [{"durum": d, "konu": b, "bulgu": c} for d, b, c in ozet]
    json.dump(json_temiz(R), open(os.path.join(cikti, "rapor.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    open(os.path.join(cikti, "rapor.md"), "w", encoding="utf8").write(md)
    gunluk("bitti: %.0f sn. Rapor: %s" % (time.time() - t0, os.path.join(cikti, "rapor.md")))
    print(md)


if __name__ == "__main__":
    main()
