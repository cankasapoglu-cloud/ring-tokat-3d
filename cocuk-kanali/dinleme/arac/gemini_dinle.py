#!/usr/bin/env python3
"""Ses dosyalarını Google Gemini'ye (ses girişi kabul eden dil modeli) dinletir ve Türkçe yorum alır.

DOĞRULANMIŞ ÇALIŞMA BİÇİMİ (21 Kasım 2026, bu ortamda denendi ve çalıştı):
- Uç nokta: https://generativelanguage.googleapis.com/v1beta/openai/chat/completions  (OpenAI uyumlu katman)
- Kimlik: ağ vekili "Authorization: Bearer <anahtar>" başlığını kendisi ekler; biz yalnızca
  "Authorization: Bearer proxy-injected" göndeririz. Anahtarı aramayın, yazdırmayın.
- Yerel Gemini uç noktaları (/v1beta/models, :generateContent) BU ORTAMDA ÇALIŞMAZ: onlar
  "x-goog-api-key" başlığı ister, vekil ise bu başlığı eklemez (401 döner).
- Ses, mesajın içinde base64 olarak gider: {"type": "input_audio", "input_audio": {"data": ..., "format": "mp3"|"wav"}}.
  İstek gövdesi toplam 20 MB'ı geçmemeli: uzun dosyaları 96 kb/sn tek kanal mp3'e indirerek gönderin (2,5 dk ~ 1,8 MB).
- Ücretsiz katmanda çalışan model: gemini-3.5-flash. "pro" modellerin ücretsiz kotası 0 (429 döner);
  gemini-flash-latest ve gemini-3.8-flash zaman zaman 503 (yoğunluk) döndürür: MODELLER listesi sırayla denenir.
- Model iyimser puan verir (reddedilmiş bir kayda 8/10 verdi): mutlak puana güvenmeyin; iki kaydı
  KARŞILAŞTIRTIN (karsilastir) ve saniyeli, somut gözlem isteyin. Bu bir vekil ölçüdür, insan kulağı değildir.

Kullanım:
  python3 gemini_dinle.py dinle  <ses>                      # sabit değerlendirme soruları
  python3 gemini_dinle.py sor    <ses> "<soru>"             # serbest soru
  python3 gemini_dinle.py karsilastir <sesA> <sesB> ["<ek soru>"]
  (isteğe bağlı: --bas 0 --sure 60  -> dosyanın yalnızca o bölümünü gönderir)
"""
import base64, hashlib, json, os, subprocess, sys, tempfile, time

UC = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
MODELLER = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash"]
ONBELLEK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "onbellek", "gemini")

DEGERLENDIRME = """Bu ses kaydını dikkatle dinle ve yalnızca gerçekten duyduklarına dayanarak Türkçe, kısa ve somut cevap ver. Emin olmadığın yerde "emin değilim" de; uydurma.
1. Ne duyuyorsun? (çalgılar, şarkıcı sesi, dil, tür)
2. Söylenen sözleri duyduğun gibi yaz.
3. Şarkıcının sesi doğal mı, yapay/işlenmiş mi? Neden?
4. Şarkıcının söylediği ezgi ile arkadaki müzik birbirine uyuyor mu (akort, armoni)? İki ayrı şarkı üst üste binmiş gibi bir his var mı? Varsa hangi saniyelerde?
5. Şarkıcı ritme oturuyor mu?
6. Enerji / coşku düzeyi 1-10 arasında kaç? Bir çocuk şarkısı olarak neşeli mi, ninni gibi mi?
7. Türkçe telaffuz doğal mı, yabancı aksan var mı? Yanlış söylenen kelime var mı?
8. Rahatsız eden, tuhaf ya da hatalı duyulan bir şey var mı? Saniyesiyle yaz.
9. Genel puan (1-10) ve tek cümlelik gerekçe."""

KARSILASTIRMA = """Sana iki ses kaydı veriyorum: önce A, sonra B. İkisini de dikkatle dinle ve yalnızca duyduklarına dayanarak Türkçe, kısa ve somut cevap ver; emin değilsen söyle.
Her madde için "A", "B" ya da "fark yok" de ve bir cümleyle neden:
1. Hangisinde şarkıcının sesi daha doğal?
2. Hangisinde şarkıcı arkadaki müzikle daha uyumlu (akort ve armoni)?
3. Hangisinde şarkıcı ritme daha iyi oturuyor?
4. Hangisi daha coşkulu / enerjik?
5. Hangisinde sözler daha anlaşılır ve Türkçesi daha doğal?
6. Bir çocuk şarkısı olarak hangisi daha iyi? Diğerindeki en belirgin kusur ne, hangi saniyede?"""


def _kucult(dosya, bas=None, sure=None):
    """Dosyayı (ya da bir bölümünü) 96 kb/sn tek kanal mp3'e indirir; base64 metnini döndürür."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as t:
        hedef = t.name
    komut = ["ffmpeg", "-y", "-v", "error"]
    if bas is not None: komut += ["-ss", str(bas)]
    if sure is not None: komut += ["-t", str(sure)]
    komut += ["-i", dosya, "-ac", "1", "-ar", "44100", "-b:a", "96k", hedef]
    subprocess.run(komut, check=True)
    veri = open(hedef, "rb").read(); os.unlink(hedef)
    return base64.b64encode(veri).decode()


def istek_govdesi(sesler_b64, soru, model, max_tokens=6000):
    icerik = [{"type": "text", "text": soru}]
    for b in sesler_b64:
        icerik.append({"type": "input_audio", "input_audio": {"data": b, "format": "mp3"}})
    return {"model": model, "messages": [{"role": "user", "content": icerik}], "max_tokens": max_tokens}


def yaniti_coz(metin):
    """(tamam mı, yanıt ya da hata metni, http benzeri kod) döndürür."""
    try:
        d = json.loads(metin)
    except Exception:
        return False, "yanıt JSON değil: " + metin[:300], 0
    if isinstance(d, list) and d: d = d[0]
    if "error" in d:
        return False, str(d["error"].get("message", d["error"]))[:400], int(d["error"].get("code", 0) or 0)
    try:
        return True, d["choices"][0]["message"]["content"] or "", 200
    except Exception:
        return False, "beklenmeyen yanıt: " + json.dumps(d, ensure_ascii=False)[:300], 0


def sor(dosyalar, soru, bas=None, sure=None, modeller=None, onbellek=True):
    """dosyalar: ses dosyası yolları (sırayla dinletilir). Dönüş: {"tamam", "yanit", "model"}."""
    sesler = [_kucult(d, bas, sure) for d in dosyalar]
    anahtar = hashlib.sha1(("|".join(hashlib.sha1(s.encode()).hexdigest() for s in sesler) + soru).encode()).hexdigest()
    yol = os.path.join(ONBELLEK, anahtar + ".json")
    if onbellek and os.path.exists(yol):
        return json.load(open(yol, encoding="utf8"))
    son = ""
    for model in (modeller or MODELLER):
        for deneme in range(3):
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t:
                json.dump(istek_govdesi(sesler, soru, model), t); govde = t.name
            r = subprocess.run(["curl", "-sS", "-m", "300", "-X", "POST", UC, "-H", "Authorization: Bearer proxy-injected",
                                "-H", "Content-Type: application/json", "-d", "@" + govde], capture_output=True, text=True)
            os.unlink(govde)
            tamam, yanit, kod = yaniti_coz(r.stdout or r.stderr)
            if tamam:
                sonuc = {"tamam": True, "yanit": yanit, "model": model, "dosyalar": [os.path.basename(d) for d in dosyalar], "bas": bas, "sure": sure}
                os.makedirs(ONBELLEK, exist_ok=True)
                json.dump(sonuc, open(yol, "w", encoding="utf8"), ensure_ascii=False, indent=1)
                return sonuc
            son = f"{model}: {kod} {yanit}"
            if kod in (503, 500): time.sleep(8 * (deneme + 1)); continue      # yoğunluk: bekle, yeniden dene
            break                                                             # 429 (kota) ve diğerleri: sıradaki model
    return {"tamam": False, "yanit": "Gemini yanıt vermedi. Son hata: " + son, "model": None}


def dinle(dosya, **kw): return sor([dosya], DEGERLENDIRME, **kw)
def karsilastir(a, b, ek="", **kw): return sor([a, b], KARSILASTIRMA + ("\n" + ek if ek else ""), **kw)


if __name__ == "__main__":
    arg = sys.argv[1:]; kw = {}
    for ad in ("--bas", "--sure"):
        if ad in arg:
            i = arg.index(ad); kw[ad[2:]] = float(arg[i + 1]); del arg[i:i + 2]
    if len(arg) < 2: sys.exit(__doc__)
    if arg[0] == "dinle": s = dinle(arg[1], **kw)
    elif arg[0] == "sor": s = sor([arg[1]], arg[2], **kw)
    elif arg[0] == "karsilastir": s = karsilastir(arg[1], arg[2], arg[3] if len(arg) > 3 else "", **kw)
    else: sys.exit(__doc__)
    print(("[" + str(s.get("model")) + "]\n" if s.get("tamam") else "") + s["yanit"])
