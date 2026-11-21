#!/usr/bin/env python3
"""gemini_dinle.py - ses dosyalarini ses girisli bir dil modeline (Google Gemini) dinletir; sabit sorularla Turkce gorus alir.

Bu bir IKINCI GORUSTUR, olcum degildir. Arastirmalar (PitchBench, VocalCoachBench, SpeechJudge, 2026) bu tur modellerin:
  + iki kaydi karsilastirmada, sozleri yazmada, genel enerji/tur tarifinde ise yaradigini,
  - perde (detone), ince zamanlama ve "dogallik" yargilarinda GUVENILMEZ oldugunu, sorunun metnine gore cevap uydurabildigini gosteriyor.
Bu yuzden: tek kayda not verdirmeyin; IKI KAYDI KARSILASTIRTIN, sirayi degistirip yeniden sorun (--iki-yon), saniyeli kanit isteyin.

KIMLIK (anahtar bu koda hic verilmez; aramayin, yazdirmayin):
  Ag vekili anahtari kendisi ekler. Bu ortamda 21 Kasim 2026'da gorulen durum:
   - OpenAI uyumlu uc nokta  /v1beta/openai/chat/completions  +  "Authorization: Bearer proxy-injected"  -> CALISTI (ana oturumda dogrulandi).
   - Yerel uc noktalar (/v1beta/models, :generateContent) "x-goog-api-key" basligi ister; vekil bu basligi EKLEMIYOR (401).
     Model listesi (her iki yoldan) bu yuzden alinamiyor; anahtarin calistigini yalnizca kucuk bir canli istek gosterir (durum --canli).
  Vekil ileride x-goog-api-key eklerse yerel yol da kendiliginden kullanilir (yol="otomatik").
  Ucretsiz katmanda Google, gonderilen sesi urunlerini gelistirmek icin kullanabilir; kota kucuktur (gunde onlarca istek).

KULLANIM
  python3 gemini_dinle.py durum [--canli]                 # anahtar / erisim var mi? (--canli: 1 kucuk metin istegi harcar)
  python3 gemini_dinle.py dinle <ses> [--bas S --sure S]  # sabit degerlendirme sorulari (RUBRIK)
  python3 gemini_dinle.py karsilastir <A> <B> [--iki-yon] # A/B; --iki-yon: sirayi degistirip iki kez sorar, yalnizca tutarli maddeleri kabul eder
  python3 gemini_dinle.py sor <ses> "<soru>"              # serbest soru
Cevaplar dinleme/onbellek/gemini/ altinda saklanir (ayni ses + ayni soru yeniden gonderilmez).
"""
import base64, hashlib, json, os, re, subprocess, sys, tempfile, time

TABAN = "https://generativelanguage.googleapis.com"
UC = TABAN + "/v1beta/openai/chat/completions"                # OpenAI uyumlu katman (bu ortamda calisan yol)
UC_YEREL = TABAN + "/v1beta/models/%s:generateContent"        # yerel yol (x-goog-api-key gerekir)
MODELLER = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash"]
ONBELLEK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "onbellek", "gemini")
BASLIK_OPENAI = "Authorization: Bearer proxy-injected"
BASLIK_YEREL = "x-goog-api-key: proxy-injected"

RUBRIK_ANAHTARLARI = ["DUYDUGUM", "SOZLER", "SES", "AKORT", "RITIM", "ENERJI", "TELAFFUZ", "SARKI_MI", "DENGE", "TUHAF", "OZET"]
RUBRIK = """Bir Türkçe çocuk şarkısı kaydını denetliyorsun. Kaydı dikkatle dinle. YALNIZCA gerçekten duyduklarına dayan; duyamadığın ya da emin olmadığın yerde "emin değilim" de, uydurma. Kibar olma: kusurları açıkça yaz. Şarkının ne olması gerektiğini bilmiyorsun; tahmin yürütme.

Cevabını TAM OLARAK aşağıdaki 11 satırla ver (başka hiçbir şey yazma). Seçenekli satırlarda önce seçeneklerden BİRİNİ aynen yaz, sonra " | " koyup bir cümlelik gerekçeyi ve varsa dakika:saniye (MM:SS) örneklerini yaz.

DUYDUGUM: <2-3 cümle: dil, şarkıcının sesi (çocuk/yetişkin, kadın/erkek), çalgılar, hayvan sesi ya da efekt var mı>
SOZLER: <duyduğun sözleri olduğu gibi yaz; yanlış söylenen sözcüğü DÜZELTME; anlamadığın yere [anlaşılmıyor] yaz>
SES: doğal insan sesi | biraz yapay | belirgin yapay/robotik | emin değilim
AKORT: müzikle uyumlu | ara sıra bozuk | sık sık bozuk | emin değilim
RITIM: ritme oturuyor | ara sıra kaçıyor | sık sık kaçıyor | emin değilim
ENERJI: ninni gibi | sakin | orta | canlı | çok coşkulu
TELAFFUZ: doğal Türkçe | hafif yabancı aksan | belirgin yabancı aksan | emin değilim
SARKI_MI: ezgiyle söylüyor | yarı konuşur gibi | konuşuyor
DENGE: vokal kısık kalıyor | dengeli | vokal fazla yüksek
TUHAF: <rahatsız eden, hatalı ya da tuhaf duyulan en çok 5 şey, "MM:SS - sorun" biçiminde, noktalı virgülle ayır; yoksa "yok">
OZET: <tek cümle: bu kaydın en belirgin kusuru ne>"""

# Eski (ilk surum) serbest degerlendirme sorulari: onbellekteki eski cevaplar bu metinle saklidir.
DEGERLENDIRME = RUBRIK

KARSILASTIRMA = """Sana iki ses kaydı veriyorum: önce A, sonra B. İkisini de dikkatle dinle ve yalnızca duyduklarına dayanarak Türkçe, kısa ve somut cevap ver; emin değilsen söyle.
Her madde için "A", "B" ya da "fark yok" de ve bir cümleyle neden:
1. Hangisinde şarkıcının sesi daha doğal?
2. Hangisinde şarkıcı arkadaki müzikle daha uyumlu (akort ve armoni)?
3. Hangisinde şarkıcı ritme daha iyi oturuyor?
4. Hangisi daha coşkulu / enerjik?
5. Hangisinde sözler daha anlaşılır ve Türkçesi daha doğal?
6. Bir çocuk şarkısı olarak hangisi daha iyi? Diğerindeki en belirgin kusur ne, hangi saniyede?"""
AB_MADDELERI = {1: "ses daha doğal", 2: "müzikle daha uyumlu", 3: "ritme daha iyi oturuyor", 4: "daha coşkulu", 5: "sözler daha anlaşılır / Türkçesi daha doğal",
                6: "çocuk şarkısı olarak daha iyi"}


# ----------------------------------------------------------------------------------------------------------
# istek kurma / cevap cozme (ag gerektirmez; sinama.py bunlari dener)
# ----------------------------------------------------------------------------------------------------------
def _kucult(dosya, bas=None, sure=None):
    """Dosyayi (ya da bir bolumunu) 96 kb/sn tek kanal mp3'e indirir; base64 metnini dondurur."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as t:
        hedef = t.name
    komut = ["ffmpeg", "-y", "-v", "error"]
    if bas is not None:
        komut += ["-ss", str(bas)]
    if sure is not None:
        komut += ["-t", str(sure)]
    komut += ["-i", dosya, "-ac", "1", "-ar", "44100", "-b:a", "96k", hedef]
    try:
        subprocess.run(komut, check=True)
        with open(hedef, "rb") as f:
            veri = f.read()
    finally:
        if os.path.exists(hedef):
            os.unlink(hedef)
    return base64.b64encode(veri).decode()


def istek_govdesi(sesler_b64, soru, model, max_tokens=6000):
    """OpenAI uyumlu govde: soru metni + sirayla sesler (base64 mp3)."""
    icerik = [{"type": "text", "text": soru}]
    for b in sesler_b64:
        icerik.append({"type": "input_audio", "input_audio": {"data": b, "format": "mp3"}})
    return {"model": model, "messages": [{"role": "user", "content": icerik}], "max_tokens": max_tokens}


def yerel_istek_govdesi(sesler_b64, soru, etiketler=None):
    """Yerel generateContent govdesi: once sesler (A/B ise 'Kayıt A:' etiketleriyle), soru EN SONDA."""
    parcalar = []
    for i, b in enumerate(sesler_b64):
        if etiketler:
            parcalar.append({"text": etiketler[i]})
        parcalar.append({"inline_data": {"mime_type": "audio/mpeg", "data": b}})
    parcalar.append({"text": soru})
    return {"contents": [{"role": "user", "parts": parcalar}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 6000}}


def _hata_coz(d):
    if isinstance(d, list) and d:
        d = d[0]
    if isinstance(d, dict) and "error" in d:
        e = d["error"]
        if isinstance(e, dict):
            return str(e.get("message", e))[:400], int(e.get("code", 0) or 0)
        return str(e)[:400], 0
    return None


def yaniti_coz(metin):
    """OpenAI uyumlu cevap -> (tamam mi, yanit ya da hata metni, http benzeri kod)."""
    try:
        d = json.loads(metin)
    except Exception:
        return False, "yanıt JSON değil: " + (metin or "")[:300], 0
    h = _hata_coz(d)
    if h:
        return False, h[0], h[1]
    try:
        return True, d["choices"][0]["message"]["content"] or "", 200
    except Exception:
        return False, "beklenmeyen yanıt: " + json.dumps(d, ensure_ascii=False)[:300], 0


def yerel_yaniti_coz(metin):
    """Yerel generateContent cevabi -> (tamam mi, yanit ya da hata metni, kod). Dusunme (thought) parcalari atlanir."""
    try:
        d = json.loads(metin)
    except Exception:
        return False, "yanıt JSON değil: " + (metin or "")[:300], 0
    h = _hata_coz(d)
    if h:
        return False, h[0], h[1]
    try:
        aday = d["candidates"][0]
        yazi = "".join(p.get("text", "") for p in aday["content"]["parts"] if not p.get("thought"))
        if not yazi:
            return False, "boş yanıt (bitiş nedeni: %s)" % aday.get("finishReason"), 0
        return True, yazi, 200
    except Exception:
        neden = (d.get("promptFeedback") or {}).get("blockReason") if isinstance(d, dict) else None
        return False, "yanıt yok" + (" (engellendi: %s)" % neden if neden else ": " + json.dumps(d, ensure_ascii=False)[:200]), 0


def hata_aciklamasi(kod, mesaj):
    """Hata kodunu 'ne eksik' cumlesine cevirir."""
    m = (mesaj or "").lower()
    if kod in (401, 403) or "api key" in m or "auth" in m or "credential" in m:
        return ("Gemini anahtarı yok ya da bu uç nokta için eklenmiyor. Gerekli: ortam ayarlarında generativelanguage.googleapis.com için bir ağ sırrı "
                "(başlık: Authorization, önek: Bearer — OpenAI uyumlu yol; ya da başlık: x-goog-api-key — yerel yol). Anahtar aistudio.google.com/app/apikey "
                "adresinden alınır ve SOHBETE YAZILMAZ; güvenli formdan girilir.")
    if kod == 429 or "quota" in m or "rate" in m:
        return "Kota doldu (ücretsiz katman dakikalık/günlük sınırı). Bekleyip yeniden deneyin ya da başka model seçin."
    if kod in (500, 503) or "overloaded" in m or "unavailable" in m:
        return "Google tarafı yoğun (geçici). Biraz sonra yeniden deneyin."
    if kod == 404 or "not found" in m:
        return "Model adı geçersiz/kaldırılmış. MODELLER listesini güncelleyin."
    if kod == 400:
        return "İstek reddedildi (400): gövde çok büyük (20 MB sınırı) ya da biçim hatalı olabilir."
    return "Bilinmeyen hata."


def rubrik_coz(yanit):
    """RUBRIK cevabini sozluge cevirir: {ANAHTAR: {"secim": ..., "gerekce": ...}} (serbest satirlarda yalnizca "metin")."""
    c = {}
    desen = re.compile(r"^\s*\**\s*(%s)\s*\**\s*:\s*(.*)$" % "|".join(RUBRIK_ANAHTARLARI))
    son = None
    for satir in (yanit or "").splitlines():
        m = desen.match(satir)
        if m:
            son = m.group(1)
            c[son] = m.group(2).strip().strip("*").strip()
        elif son and satir.strip():
            c[son] += " " + satir.strip()
    cikti = {}
    for k, v in c.items():
        if k in ("DUYDUGUM", "SOZLER", "TUHAF", "OZET"):
            cikti[k] = {"metin": v}
        else:
            sec, _, ger = v.partition("|")
            cikti[k] = {"secim": sec.strip().strip(".").lower(), "gerekce": ger.strip()}
    cikti["_eksik"] = [k for k in RUBRIK_ANAHTARLARI if k not in cikti]
    return cikti


def ab_coz(yanit):
    """KARSILASTIRMA cevabindan madde -> 'A' | 'B' | 'fark yok' | None."""
    c = {}
    for m in re.finditer(r"(?m)^\s*(\d)\s*[.)]\s*\**\s*(A|B|[Ff]ark yok)\b", yanit or ""):
        c[int(m.group(1))] = "fark yok" if m.group(2).lower().startswith("fark") else m.group(2)
    return {k: c.get(k) for k in AB_MADDELERI}


def iki_yon_birlestir(ilk, ters):
    """ilk: (X,Y) sirasiyla sorulan cevabin ab_coz'u; ters: (Y,X) sirasiyla. Donus: madde -> 'X' | 'Y' | 'fark yok' | 'TUTARSIZ' | None.
    Ters sorudaki 'A' aslinda Y, 'B' aslinda X demektir. Yalnizca iki sorguda da ayni kayit kazanirsa kabul edilir (konum yanliligina karsi)."""
    cevir = {"A": "Y", "B": "X", "fark yok": "fark yok", None: None}
    duz = {"A": "X", "B": "Y", "fark yok": "fark yok", None: None}
    c = {}
    for k in AB_MADDELERI:
        a, b = duz[ilk.get(k)], cevir[ters.get(k)]
        c[k] = None if (a is None or b is None) else (a if a == b else "TUTARSIZ")
    return c


# ----------------------------------------------------------------------------------------------------------
# ag
# ----------------------------------------------------------------------------------------------------------
def _curl(adres, baslik, govde=None, sure=300):
    komut = ["curl", "-sS", "-m", str(sure), "-w", "\n%{http_code}", adres, "-H", baslik]
    gecici = None
    if govde is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t:
            json.dump(govde, t)
            gecici = t.name
        komut += ["-X", "POST", "-H", "Content-Type: application/json", "-d", "@" + gecici]
    try:
        r = subprocess.run(komut, capture_output=True, text=True)
    finally:
        if gecici and os.path.exists(gecici):
            os.unlink(gecici)
    cikti = r.stdout or ""
    govde_m, _, kod = cikti.rpartition("\n")
    try:
        kod = int(kod)
    except ValueError:
        govde_m, kod = cikti, 0
    return kod, (govde_m if govde_m or kod else (r.stderr or "")[:300])


def anahtar_durumu(canli=False):
    """Erisim denetimi. Model listesi istekleri ucretsizdir. canli=True ise ayrica 1 kucuk metin istegi gonderir (kotadan 1 dusurur)."""
    d = {"zaman": time.strftime("%Y-%m-%d %H:%M:%S")}
    kod, govde = _curl(TABAN + "/v1beta/models?pageSize=50", BASLIK_YEREL, sure=40)
    tamam = kod == 200 and '"models"' in govde
    d["yerel_yol_model_listesi"] = {"http": kod, "tamam": tamam, "not": "x-goog-api-key başlığıyla (vekil ekliyorsa çalışır)"}
    if not tamam:
        d["yerel_yol_model_listesi"]["hata"] = (_hata_coz(_json(govde)) or ("ağ hatası: " + govde[:120], 0))[0][:160]
    kod, govde = _curl(TABAN + "/v1beta/openai/models", BASLIK_OPENAI, sure=40)
    tamam2 = kod == 200 and '"data"' in govde
    d["openai_yolu_model_listesi"] = {"http": kod, "tamam": tamam2}
    if not tamam2:
        d["openai_yolu_model_listesi"]["hata"] = (_hata_coz(_json(govde)) or ("ağ hatası: " + govde[:120], 0))[0][:160]
    d["yerel_yol_kullanilabilir"] = tamam
    if canli:
        son = None
        for model in MODELLER:
            kod, govde = _curl(UC, BASLIK_OPENAI, {"model": model, "messages": [{"role": "user", "content": "Yalnızca TAMAM yaz."}], "max_tokens": 200}, sure=60)
            ok, yanit, k2 = yaniti_coz(govde)
            son = {"model": model, "http": kod, "tamam": ok, "yanit": yanit[:120]}
            if ok or (k2 or kod) in (401, 403):
                break
        d["canli_deneme"] = son
        d["kullanilabilir"] = bool(son and son["tamam"])
        if not d["kullanilabilir"]:
            d["eksik"] = hata_aciklamasi(son["http"] if son else 0, son["yanit"] if son else "")
    else:
        d["kullanilabilir"] = True if (tamam or tamam2) else None
        if d["kullanilabilir"] is None:
            d["not"] = ("Model listesi alınamadı. Bu ortamda liste alınamadığı halde sohbet uç noktası çalışabiliyor: kesin bilgi için "
                        "'durum --canli' (1 küçük istek harcar) ya da doğrudan 'dinle' deneyin.")
    return d


def _json(metin):
    try:
        return json.loads(metin)
    except Exception:
        return {}


def sor(dosyalar, soru, bas=None, sure=None, modeller=None, onbellek=True, yol="otomatik", yerel_mi=None):
    """dosyalar: ses dosyasi yollari (sirayla dinletilir). Donus: {"tamam", "yanit", "model", ...}. Hata durumunda "eksik" aciklamasi eklenir."""
    sesler = [_kucult(d, bas, sure) for d in dosyalar]
    anahtar = hashlib.sha1(("|".join(hashlib.sha1(s.encode()).hexdigest() for s in sesler) + soru).encode()).hexdigest()
    onb = os.path.join(ONBELLEK, anahtar + ".json")
    if onbellek and os.path.exists(onb):
        c = json.load(open(onb, encoding="utf8"))
        c["onbellekten"] = True
        return c
    toplam_mb = sum(len(s) for s in sesler) / 1e6
    if toplam_mb > 18:
        return {"tamam": False, "yanit": "ses çok büyük (%.1f MB base64; sınır ~20 MB). --bas/--sure ile kısaltın." % toplam_mb, "model": None}
    if yerel_mi is None:
        yerel_mi = (yol == "yerel")
    son, son_kod = "", 0
    for model in (modeller or MODELLER):
        for deneme in range(3):
            if yerel_mi:
                etiket = ["Kayıt A:", "Kayıt B:"] if len(sesler) == 2 else None
                kod, govde = _curl(UC_YEREL % model, BASLIK_YEREL, yerel_istek_govdesi(sesler, soru, etiket))
                tamam, yanit, k2 = yerel_yaniti_coz(govde)
            else:
                kod, govde = _curl(UC, BASLIK_OPENAI, istek_govdesi(sesler, soru, model))
                tamam, yanit, k2 = yaniti_coz(govde)
            kod = k2 or kod
            if tamam:
                sonuc = {"tamam": True, "yanit": yanit, "model": model, "dosyalar": [os.path.basename(d) for d in dosyalar], "bas": bas, "sure": sure,
                         "yol": "yerel" if yerel_mi else "openai-uyumlu", "zaman": time.strftime("%Y-%m-%d %H:%M:%S")}
                os.makedirs(ONBELLEK, exist_ok=True)
                json.dump(sonuc, open(onb, "w", encoding="utf8"), ensure_ascii=False, indent=1)
                return sonuc
            son, son_kod = "%s: %s %s" % (model, kod, yanit), kod
            if kod in (503, 500):
                time.sleep(8 * (deneme + 1))                   # yogunluk: bekle, yeniden dene
                continue
            break                                               # 429 (kota) ve digerleri: siradaki model
        if son_kod in (401, 403):
            break                                               # kimlik sorunu: baska model denemek anlamsiz
    return {"tamam": False, "yanit": "Gemini yanıt vermedi. Son hata: " + son, "model": None, "eksik": hata_aciklamasi(son_kod, son)}


def dinle(dosya, **kw):
    s = sor([dosya], RUBRIK, **kw)
    if s.get("tamam"):
        s["rubrik"] = rubrik_coz(s["yanit"])
    return s


def karsilastir(a, b, ek="", **kw):
    s = sor([a, b], KARSILASTIRMA + ("\n" + ek if ek else ""), **kw)
    if s.get("tamam"):
        s["secimler"] = ab_coz(s["yanit"])
    return s


def karsilastir_iki_yon(x, y, **kw):
    """Konum yanliligina karsi: (X,Y) ve (Y,X) sirasiyla iki kez sorar; yalnizca tutarli maddeleri kabul eder."""
    ilk = karsilastir(x, y, **kw)
    ters = karsilastir(y, x, **kw)
    c = {"tamam": bool(ilk.get("tamam") and ters.get("tamam")), "ilk": ilk, "ters": ters, "X": os.path.basename(x), "Y": os.path.basename(y)}
    if c["tamam"]:
        b = iki_yon_birlestir(ilk["secimler"], ters["secimler"])
        c["tutarli_sonuc"] = {AB_MADDELERI[k]: v for k, v in b.items()}
        c["yanit"] = "\n".join("%d. %s: %s" % (k, AB_MADDELERI[k], {"X": c["X"], "Y": c["Y"]}.get(v, v)) for k, v in b.items())
    else:
        c["yanit"] = (ilk if not ilk.get("tamam") else ters).get("yanit", "")
        c["eksik"] = (ilk if not ilk.get("tamam") else ters).get("eksik")
    return c


def main(arg=None):
    arg = list(sys.argv[1:] if arg is None else arg)
    kw = {}
    for ad in ("--bas", "--sure"):
        if ad in arg:
            i = arg.index(ad)
            kw[ad[2:]] = float(arg[i + 1])
            del arg[i:i + 2]
    iki_yon = "--iki-yon" in arg
    canli = "--canli" in arg
    arg = [x for x in arg if x not in ("--iki-yon", "--canli")]
    if not arg:
        sys.exit(__doc__)
    if arg[0] == "durum":
        d = anahtar_durumu(canli)
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return 0 if d.get("kullanilabilir") else 1
    if len(arg) < 2:
        sys.exit(__doc__)
    if arg[0] == "dinle":
        s = dinle(arg[1], **kw)
    elif arg[0] == "sor" and len(arg) >= 3:
        s = sor([arg[1]], arg[2], **kw)
    elif arg[0] == "karsilastir" and len(arg) >= 3:
        s = karsilastir_iki_yon(arg[1], arg[2], **kw) if iki_yon else karsilastir(arg[1], arg[2], arg[3] if len(arg) > 3 else "", **kw)
    else:
        sys.exit(__doc__)
    if s.get("tamam"):
        print("[%s%s]" % (s.get("model") or "iki yön", ", önbellekten" if s.get("onbellekten") else ""))
        print(s["yanit"])
        return 0
    print(s.get("yanit", ""))
    if s.get("eksik"):
        print("EKSİK: " + s["eksik"])
    return 1


if __name__ == "__main__":
    sys.exit(main())
