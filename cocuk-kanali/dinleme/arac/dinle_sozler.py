#!/usr/bin/env python3
"""dinle_sozler.py - sozleri makineye dinletip beklenen sozlerle karsilastirir.

  scribe()        ElevenLabs Scribe (yalnizca POST /v1/speech-to-text). Sonuc dinleme/onbellek/ altinda saklanir:
                  ayni dosya ikinci kez GONDERILMEZ. Kredi defteri (onbellek/kredi_defteri.json) sinir asilirsa cagriyi reddeder.
                  Anahtar bu koda verilmez: baslik degeri hep "proxy-injected" yazilir, gercek anahtari ag vekili ekler.
  karsilastir()   beklenen sozler ile duyulan sozcukleri hizalar: sozcuk hata orani, yanlis / eksik / fazla sozcukler (saniyeli)
  hece_hizi()     saniyede hece (Turkcede hece sayisi = unlu sayisi)

Neyi SOYLEMEZ: Bir konusma tanima modeli, aksanli ya da bozuk soylenmis sozcugu de cogu zaman DOGRU yazar. Temiz bir dokum
"Turkcesi dogal" demek degildir; yalnizca "sozcukler anlasilir ve yerinde" demektir.
"""
import os, re, json, time, hashlib, subprocess, glob, difflib

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # dinleme/
ONBELLEK = os.path.join(KOK, "onbellek")
DEFTER = os.path.join(ONBELLEK, "kredi_defteri.json")
KREDI_SINIRI = int(os.environ.get("DINLEME_KREDI_SINIRI", "8000"))
KREDI_DAKIKA = 330.0                                                       # Scribe: dakikada yaklasik 330 kredi
UC = "https://api.elevenlabs.io/v1/speech-to-text"
UNLULER = set("aeıioöuü")


# ----------------------------------------------------------------------------------------------------------
# metin yardimcilari
# ----------------------------------------------------------------------------------------------------------
def kucult_tr(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def normalle(s):
    """Karsilastirma icin: Turkce kucuk harf, sapkali harfler sade, noktalama ve kesme isareti yok."""
    s = kucult_tr(s)
    for a, b in (("â", "a"), ("î", "i"), ("û", "u"), ("’", "'"), ("`", "'")):
        s = s.replace(a, b)
    s = s.replace("'", "")
    return re.sub(r"[^0-9a-zçğıöşü]+", "", s)


def hece_say(sozcuk):
    return sum(1 for ch in kucult_tr(sozcuk) if ch in UNLULER)


def beklenen_sozcukler(metin):
    """Soz dosyasini sozcuk listesine cevirir. # ile baslayan satirlar, [koseli] ve (yuvarlak) parantez icleri yok sayilir.
    Donus: [(sozcuk, normal, satir_no)]"""
    cikti = []
    for no, satir in enumerate(metin.splitlines(), 1):
        if satir.strip().startswith("#"):
            continue
        if re.match(r"^\s*(\d+\s*[.)]\s*)?(KITA|NAKARAT|GİRİŞ|BİTİŞ|KÖPRÜ)\b", satir):      # "1. KITA — inek" gibi baslik satirlari
            continue
        satir = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", satir)
        for w in satir.split():
            n = normalle(w)
            if n:
                cikti.append((w.strip(".,;:!?\"“”…-—"), n, no))
    return cikti


# ----------------------------------------------------------------------------------------------------------
# Scribe (onbellek + kredi defteri)
# ----------------------------------------------------------------------------------------------------------
def _ozet(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for p in iter(lambda: f.read(1 << 20), b""):
            h.update(p)
    return h.hexdigest()[:16]


def defter_oku():
    if os.path.exists(DEFTER):
        try:
            return json.load(open(DEFTER, encoding="utf8"))
        except Exception:
            pass
    return {"aciklama": "ElevenLabs Scribe cagri defteri. Kredi tahmini: sure_sn / 60 * 330.", "kayitlar": []}


def defter_toplam(d=None):
    d = d or defter_oku()
    return round(sum(k.get("tahmini_kredi", 0) for k in d.get("kayitlar", [])), 1)


def onbellekte(yol, model="scribe_v1"):
    oz = _ozet(yol)
    bul = sorted(glob.glob(os.path.join(ONBELLEK, "%s__*__%s.json" % (model, oz))))
    return (bul[0] if bul else None), oz


def scribe(yol, sure_sn, model="scribe_v1", dil="tr", gunluk=print):
    """Donus: (sonuc_sozlugu ya da None, durum_sozlugu). Onbellekte varsa cagri yapmaz."""
    os.makedirs(ONBELLEK, exist_ok=True)
    var, oz = onbellekte(yol, model)
    if var:
        return json.load(open(var, encoding="utf8")), {"kaynak": "onbellek", "dosya": var, "kredi": 0}
    tahmin = round(sure_sn / 60.0 * KREDI_DAKIKA, 1)
    d = defter_oku()
    harcanan = defter_toplam(d)
    if harcanan + tahmin > KREDI_SINIRI:
        return None, {"kaynak": "reddedildi", "neden": "kredi siniri: simdiye kadar ~%.0f, bu dosya ~%.0f, sinir %d (DINLEME_KREDI_SINIRI)"
                                                       % (harcanan, tahmin, KREDI_SINIRI)}
    if sure_sn > 600:
        return None, {"kaynak": "reddedildi", "neden": "dosya 10 dakikadan uzun; once kesin (ffmpeg -ss -t)"}
    ad = re.sub(r"[^0-9A-Za-z_.-]+", "_", os.path.splitext(os.path.basename(yol))[0])[:60]
    hedef = os.path.join(ONBELLEK, "%s__%s__%s.json" % (model, ad, oz))
    gunluk("  Scribe cagrisi: %.0f sn ses, tahmini %.0f kredi (toplam %.0f / %d)" % (sure_sn, tahmin, harcanan + tahmin, KREDI_SINIRI))
    gecici = hedef + ".tmp"
    # curl -F dosya adindaki ozel karakterleri (; , ") yorumlar: dosyayi guvenli adla gecici klasore baglayip oradan yukluyoruz
    import tempfile, shutil
    gk = tempfile.mkdtemp(prefix="dinle_scribe_")
    guvenli = os.path.join(gk, "ses" + (os.path.splitext(yol)[1].lower() if re.fullmatch(r"\.[A-Za-z0-9]{1,5}", os.path.splitext(yol)[1]) else ".bin"))
    try:
        try:
            os.symlink(os.path.abspath(yol), guvenli)
        except OSError:
            shutil.copyfile(yol, guvenli)
        r = subprocess.run(["curl", "-sS", "-m", "300", "-o", gecici, "-w", "%{http_code}", "-X", "POST", UC,
                            "-H", "xi-api-key: proxy-injected", "-F", "file=@" + guvenli,
                            "--form-string", "model_id=" + model, "--form-string", "language_code=" + dil,
                            "--form-string", "timestamps_granularity=word"], capture_output=True, text=True)
    finally:
        shutil.rmtree(gk, ignore_errors=True)
    kod = r.stdout.strip()[-3:]
    if kod != "200":
        govde = ""
        if os.path.exists(gecici):
            govde = open(gecici, encoding="utf8", errors="replace").read()[:300]
            os.unlink(gecici)
        neden = {"401": "anahtar yok ya da gecersiz (ag vekili xi-api-key eklemiyor)", "403": "erisim engelli (ag kurali ya da yetki)",
                 "429": "kota / hiz siniri", "402": "kredi bitti"}.get(kod, "HTTP " + kod)
        return None, {"kaynak": "hata", "neden": neden, "http": kod, "yanit": govde or r.stderr.strip()[:200]}
    os.replace(gecici, hedef)
    sonuc = json.load(open(hedef, encoding="utf8"))
    gercek = float(sonuc.get("audio_duration_secs") or sure_sn)
    d["kayitlar"].append({"zaman": time.strftime("%Y-%m-%d %H:%M:%S"), "dosya": os.path.basename(yol), "ozet": oz, "model": model,
                          "sure_sn": round(gercek, 2), "tahmini_kredi": round(gercek / 60.0 * KREDI_DAKIKA, 1)})
    d["toplam_tahmini_kredi"] = defter_toplam(d)
    d["sinir"] = KREDI_SINIRI
    json.dump(d, open(DEFTER, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    return sonuc, {"kaynak": "canli cagri", "dosya": hedef, "kredi": round(gercek / 60.0 * KREDI_DAKIKA, 1)}


def duyulanlar(sonuc):
    """Scribe sonucundan (sozcukler, ses_olaylari). sozcuk: {metin, normal, bas, son, logprob}"""
    soz, olay = [], []
    for w in sonuc.get("words", []):
        tur = w.get("type", "word")
        if tur == "spacing":
            continue
        kayit = {"metin": w.get("text", "").strip(), "bas": float(w.get("start", 0) or 0), "son": float(w.get("end", 0) or 0),
                 "logprob": w.get("logprob")}
        if tur == "audio_event" or (kayit["metin"].startswith(("[", "(")) and kayit["metin"].endswith(("]", ")"))):
            olay.append(kayit)
            continue
        kayit["normal"] = normalle(kayit["metin"])
        if kayit["normal"]:
            soz.append(kayit)
    return soz, olay


# ----------------------------------------------------------------------------------------------------------
# hizalama ve sozcuk hata orani
# ----------------------------------------------------------------------------------------------------------
def benzerlik(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def hizala(bek, duy):
    """bek, duy: normal sozcuk listeleri. Donus: islem listesi [(tur, i, j)], tur: 'ayni' | 'degisik' | 'eksik' | 'fazla'."""
    n, m = len(bek), len(duy)
    INF = 1e9
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        D[i][0] = float(i)
    for j in range(1, m + 1):
        D[0][j] = float(j)
    for i in range(1, n + 1):
        bi = bek[i - 1]
        for j in range(1, m + 1):
            dj = duy[j - 1]
            deg = 0.0 if bi == dj else 1.0 - 0.3 * benzerlik(bi, dj)      # yakin sozcukler eslestirilmeye yeglenir
            D[i][j] = min(D[i - 1][j - 1] + deg, D[i - 1][j] + 1.0, D[i][j - 1] + 1.0)
    isl = []
    i, j = n, m
    while i > 0 or j > 0:
        # esitlikte once "fazla": sondan geriye gelirken tekrar edilen sozlerin SONRAKI soylenisi fazla sayilir, ilki eslesir
        if j > 0 and abs(D[i][j] - (D[i][j - 1] + 1.0)) < 1e-9:
            isl.append(("fazla", None, j - 1))
            j -= 1
            continue
        if i > 0 and j > 0:
            deg = 0.0 if bek[i - 1] == duy[j - 1] else 1.0 - 0.3 * benzerlik(bek[i - 1], duy[j - 1])
            if abs(D[i][j] - (D[i - 1][j - 1] + deg)) < 1e-9:
                isl.append(("ayni" if deg == 0.0 else "degisik", i - 1, j - 1))
                i, j = i - 1, j - 1
                continue
        isl.append(("eksik", i - 1, None))
        i -= 1
    return isl[::-1]


def karsilastir(beklenen, soz):
    """beklenen: beklenen_sozcukler() ciktisi; soz: duyulanlar() sozcukleri. Donus: rapor sozlugu."""
    bek_n = [b[1] for b in beklenen]
    duy_n = [s["normal"] for s in soz]
    isl = hizala(bek_n, duy_n)
    S = sum(1 for t, _, _ in isl if t == "degisik")
    Dl = sum(1 for t, _, _ in isl if t == "eksik")
    I = sum(1 for t, _, _ in isl if t == "fazla")
    N = max(1, len(bek_n))
    yanlis, eksik, fazla = [], [], []
    son_zaman = 0.0
    eslesme = {}                                           # beklenen indis -> duyulan indis
    for tur, i, j in isl:
        if j is not None:
            son_zaman = soz[j]["bas"]
        if tur in ("ayni", "degisik"):
            eslesme[i] = j
        if tur == "degisik":
            b = benzerlik(bek_n[i], duy_n[j])
            yanlis.append({"beklenen": beklenen[i][0], "duyulan": soz[j]["metin"], "zaman": round(soz[j]["bas"], 2), "satir": beklenen[i][2],
                           "benzerlik": round(b, 2), "tur": "küçük fark (ek/harf)" if b >= 0.75 else "başka sözcük"})
        elif tur == "eksik":
            eksik.append({"beklenen": beklenen[i][0], "yaklasik_zaman": round(son_zaman, 2), "satir": beklenen[i][2]})
        elif tur == "fazla":
            fazla.append({"duyulan": soz[j]["metin"], "zaman": round(soz[j]["bas"], 2)})
    c = {"beklenen_sozcuk": len(bek_n), "duyulan_sozcuk": len(duy_n), "degisik": S, "eksik": Dl, "fazla": I,
         "sozcuk_hata_orani": round((S + Dl + I) / N, 3), "dogru_sozcuk_orani": round((len(bek_n) - S - Dl) / N, 3),
         "yanlis_sozcukler": yanlis, "eksik_sozcukler": eksik, "fazla_sozcukler": fazla}
    kucuk = sum(1 for y in yanlis if y["benzerlik"] >= 0.75)
    c["kucuk_farklar_sayilmazsa_hata_orani"] = round((S - kucuk + Dl + I) / N, 3)
    # satir bazinda ozet
    satir = {}
    for (w, nrm, no), k in zip(beklenen, range(len(beklenen))):
        s_ = satir.setdefault(no, {"satir": no, "sozcuk": 0, "dogru": 0, "bas": None})
        s_["sozcuk"] += 1
        j = eslesme.get(k)
        if j is not None:
            if s_["bas"] is None:
                s_["bas"] = round(soz[j]["bas"], 2)
            if duy_n[j] == nrm:
                s_["dogru"] += 1
    c["hatali_satirlar"] = [s_ for s_ in satir.values() if s_["dogru"] < s_["sozcuk"]][:60]
    c["eslesme"] = {str(k): v for k, v in eslesme.items()}
    return c


def hece_hizi(soz, bosluk=0.6):
    """Sozcuk zamanlarindan saniyede hece. Donus: genel + cumle (kesintisiz soz obegi) bazinda."""
    if not soz:
        return {}
    hece = [hece_say(s["metin"]) for s in soz]
    sure = [max(0.02, s["son"] - s["bas"]) for s in soz]
    obek, cur = [], [0]
    for k in range(1, len(soz)):
        if soz[k]["bas"] - soz[k - 1]["son"] > bosluk:
            obek.append(cur)
            cur = []
        cur.append(k)
    obek.append(cur)
    satirlar = []
    for g in obek:
        t0, t1 = soz[g[0]]["bas"], soz[g[-1]]["son"]
        h = sum(hece[k] for k in g)
        if t1 - t0 >= 0.4 and h >= 2:
            satirlar.append({"bas": round(t0, 2), "son": round(t1, 2), "hece": h, "hece_sn": round(h / (t1 - t0), 2),
                             "soz": " ".join(soz[k]["metin"] for k in g)[:80]})
    hiz = sorted(s_["hece_sn"] for s_ in satirlar)
    c = {"toplam_hece": int(sum(hece)), "soz_icinde_hece_sn": round(sum(hece) / sum(sure), 2), "obek_sayisi": len(satirlar)}
    if hiz:
        c["obek_hece_sn_medyan"] = hiz[len(hiz) // 2]
        c["obek_hece_sn_en_hizli"] = hiz[-1]
        c["cok_hizli_obekler"] = [s_ for s_ in satirlar if s_["hece_sn"] > 6.5][:10]
        c["cok_yavas_obekler"] = [s_ for s_ in satirlar if s_["hece_sn"] < 1.5][:10]
    c["obekler"] = satirlar[:120]
    c["aciklama"] = ("Saniyede hece. Cocuk sarkilarinda soylenen sozde genelde 2-5 hece/sn; 6,5'in ustu tekerleme hizidir (cocuk eslik edemez), "
                     "1,5'in alti cok uzatilmis hecelerdir. Zamanlar Scribe'in sozcuk sinirlarindan gelir (+-50 ms).")
    return c


def dusuk_guvenli(soz, esik=-0.6):
    return [{"sozcuk": s["metin"], "zaman": round(s["bas"], 2), "logprob": round(float(s["logprob"]), 2)}
            for s in soz if isinstance(s.get("logprob"), (int, float)) and s["logprob"] < esik][:40]
