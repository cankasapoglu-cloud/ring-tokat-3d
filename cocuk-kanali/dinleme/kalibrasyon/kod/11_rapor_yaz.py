#!/usr/bin/env python3
"""kalibrasyon.md ve kalibrasyon.json'u yazar. Sayilar ara/*.json dosyalarindan gelir (elle kopyalanmaz); yorum metni bu dosyadadir.
Once: 03_soz_denetimi.py, 04_unlu_tinisi.py, 05_olcumleri_topla.py, 06_ayrisma.py, 07_aksan_deneyi.py, 08b_gercek_kanal_topla.py, 10_tablolar.py"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from set import SET, KAL, KOK

def oku(ad, vars=None):
    y = os.path.join(KAL, "ara", ad)
    return json.load(open(y, encoding="utf8")) if os.path.exists(y) else (vars if vars is not None else {})

M = {m["ad"]: m for m in oku("olcumler.json", [])}
SD, AY, T, AK, UT, GK = oku("soz_denetimi.json"), oku("ayrisma.json"), oku("tablolar.json"), oku("aksan_deneyi.json"), oku("unlu_tinisi.json"), oku("gercek_kanallar.json")
DEFTER = json.load(open(os.path.join(KOK, "dinleme", "onbellek", "kredi_defteri.json"), encoding="utf8"))
EKSIK = [s["ad"] for s in SET if s["ad"] not in M]
P, A, E = "parmak-ailesi__", "ali-baba__", "el-yikama__"


def s(v, n=1, isaret=False, yuzde=False):
    if v is None:
        return "–"
    if yuzde:
        return ("%%%.*f" % (n, 100 * v)).replace(".", ",")
    if isinstance(v, int) and not isaret:
        return str(v)
    return (("%+.*f" if isaret else "%.*f") % (n, v)).replace(".", ",")


def m(ad, k):
    return (M.get(ad) or {}).get(k)


def aralik(adlar, k, n=2, isaret=False, yuzde=False):
    v = [m(a, k) for a in adlar if m(a, k) is not None]
    if not v:
        return "–"
    return s(min(v), n, isaret, yuzde) if min(v) == max(v) else "%s … %s" % (s(min(v), n, isaret, yuzde), s(max(v), n, isaret, yuzde))


def olcu(boyut, anahtar):
    for r in (AY.get(boyut) or {}).get("olculer", []):
        if r["olcu"] == anahtar:
            return r
    return {}


def sure_yaz(ad):
    v = m(ad, "sure_sn")
    return "–" if v is None else "%d sn (%d:%02d)" % (round(v), v // 60, round(v) % 60)


def kita(ad, i, alan):
    k = (SD.get(ad) or {}).get("kitalar") or []
    return k[i].get(alan) if len(k) > i else None


def unlu(ad, hayvan):
    """Soylenen hayvan sesi hecelerinin unlu tinisi (dB), hece hece: '+4,4 / +3,2' (o hayvanin ILK kitasi)."""
    k = (SD.get(ad) or {}).get("kitalar") or []
    aday = [x for x in k if x.get("hayvan") == hayvan]
    if not aday or not aday[0].get("ses_zamani"):
        return "–"
    z0, z1 = aday[0]["ses_zamani"]
    u = [r["bant_1800_2800_eksi_1200_1800_db"] for r in UT.get(ad, []) if z0 - 0.01 <= r["bas"] <= z1]
    return " / ".join(s(v, 1, True) for v in u) if u else "–"


DOGAL = [A + "v2_2", A + "dinle_2", E + "coskulu_2", P + "coskulu_1", A + "coskulu_1", A + "coskulu_2", P + "duzgun_1", P + "duzgun_2", P + "turkce_2", P + "yavas_2", "pitirin-ailesi__yavas_2",
         E + "sarki_1", P + "sarki_2"]
ISLENMIS = [A + "ornek_kita1", A + "sarki_birlesik"]
COSKULU, NINNI = [E + "coskulu_2", P + "coskulu_1", A + "demo_altyapi_sesli"], [P + "yavas_2", "pitirin-ailesi__yavas_2", E + "sarki_1"]
gk = lambda ad, e, k: ((GK.get(ad) or {}).get(e) or {}).get(k)

# ---------------------------------------------------------------------------------------------------------------------------------
# ANA TABLO: her kayit icin (aracin o boyutta gordugu, hukum, neden)
# ---------------------------------------------------------------------------------------------------------------------------------
def en(ad):
    return "MusicCoCa coşku farkı %s, CED 'ninni' %s, hareketlilik puanı %s" % (s(m(ad, "coca_cosku"), 2, True), s(m(ad, "ced_ninni"), 3), s(m(ad, "enerji_puani"), 0))


def sz(ad):
    return "sözcük hata oranı %s" % s(m(ad, "wer"), 1, yuzde=True)


ANA = {
 A + "v2_2": (lambda a: "%s. Kıta denetimi: at kıtasında söylenen ses **\"%s\"** (koyunun sesi): bulundu. Koyun kıtasında döküm \"%s\" yazıyor, ünlü ölçümü de \"e\" yanında (iki hece %s dB; ineğin \"mö\"sü %s dB): "
              "koyun için söylenen bulunamadı. \"atıları\": döküm \"atları\" yazıyor, bulunamadı. Söyleyiş: yapaylık işareti yok, akort %s cent, çakışan nota %s/%s. Ezgi: ölçülmüyor."
              % (sz(a), kita(a, 2, "soylenen_ses"), kita(a, 1, "soylenen_ses"), unlu(a, "koyun"), unlu(a, "inek"), s(m(a, "cent_medyan"), 1), s(m(a, "cakisan")), s(m(a, "uzun_nota"))),
              "kısmen", "Dört şikâyetten biri bulundu (at). Beğenilen söyleyişle çelişen bir uyarı yok."),
 A + "dinle_2": (lambda a: "Yapaylık işareti yok; akort %s cent; aynı armonide (en iyi kaydırma %s); %s. Araç, kullanıcının söylemediği gerçek bir söz hatası buldu (76,9. sn: \"köpekleri\" yerine \"ördekleri\"). Ezgi: ölçülmüyor."
                 % (s(m(a, "cent_medyan"), 1), s(m(a, "en_iyi_kaydirma"), 0, True), sz(a)),
                 "kısmen", "Beğeniyle çelişen uyarı yok; ama \"daha güzel\"i gösteren bir sayı da yok. Ezgi karşılaştırması yok."),
 E + "coskulu_2": (lambda a: en(a) + "; özet satırı \"coşkulu yana yakın\". (Ayrıca \"aynı armonide mi\" satırı **sorun** diyor: en iyi kaydırma %s; beğenilen kayıtta yanlış alarm.)" % s(m(a, "en_iyi_kaydirma"), 0, True),
                   "evet", "Coşku göstergeleri seçimle uyumlu."),
 P + "coskulu_1": (lambda a: en(a) + "; beş kıtada beş ad da doğru (%s). (Yanlış alarmlar: \"ünsüzlerde tiz zayıf\" ve \"söyleyiş hızı\" uyarıları.)" % sz(a),
                   "evet", "Coşku ve adlar seçimle uyumlu."),
 A + "demo_altyapi_sesli": (lambda a: en(a) + "; özet satırı: \"%s\". Vokal yok; ayırıcı hayvan seslerini \"vokal\" kanalına koyuyor." % {"iyi": "coşkulu yana yakın", "dikkat": "ninni/sakin uyarısı", "bilgi": "yorum yok"}.get((m(a, "ozet") or {}).get("Enerji / coşku"), "–"),
                            "evet", "MusicCoCa ve CED coşkulu yanda. Hareketlilik puanı düşük kaldığı için aracın kendi özet satırı \"coşkulu\" diyemiyor; vokal olmadığı hâlde hayvan seslerine vokal uyarıları veriyor."),
 A + "ornek_kita1": (lambda a: "%s (Scribe \"Maliboku yeşil boya…\" duyuyor; sözcüklerin %s kadarında emin değil); donmuş ünlü %s." % (sz(a), s(((SD.get(a) or {}).get("guven") or {}).get("oran_-0.3_alti"), 0, yuzde=True), s(m(a, "y_donmus_sure_orani"), 0, yuzde=True)),
                     "evet", "\"Sözler çok kötü çıktı\" yargısının tam karşılığı: makine tek sözcüğü bile tanımıyor."),
 A + "sarki_birlesik": (lambda a: "%s (aynı vokalin işlenmemiş hâli dinle_2'de %s); donmuş ünlü %s; panoda perde merdiven basamağı gibi. Kalite tahminleri (DNSMOS %s, UTMOS %s) doğal kayıtlardan farksız."
                        % (sz(a), s(m(A + "dinle_2", "wer"), 1, yuzde=True), s(m(a, "y_donmus_sure_orani"), 0, yuzde=True), s(m(a, "dnsmos"), 2), s(m(a, "utmos22"), 2)),
                        "evet", "Sözlerin anlaşılmaz hâle gelmesi ve panodaki görüntü yargıyı açıklıyor; \"yapaylık\" sayıları tek başına yetmezdi."),
 A + "dogal_onizleme": (lambda a: "Aynı vokal dinle_2'de: %s, armonik destek %s. Burada: %s (her kıtada \"Ali Baba'nın\" yerine \"Anne babamın\"), destek %s; \"aynı armonide mi\" satırı sorun (en iyi kaydırma %s). "
                        "Aracın \"gömük vokal\" (%s dB) ve \"akort\" uyarıları ise karışımı değil ölçüm yolunu anlatıyor: gerçek kanallarla vokal %s dB."
                        % (sz(A + "dinle_2"), s(m(A + "dinle_2", "destek_gercek"), 2), sz(a), s(m(a, "destek_gercek"), 2), s(m(a, "en_iyi_kaydirma"), 0, True), s(m(a, "vokal_eksi_altyapi_db"), 1, True),
                           s(next((mm.get("vokal_eksi_altyapi_db") for ee, mm in (GK.get(a) or {}).items() if ee.startswith("gerçek")), None), 1, True)),
                        "kısmen", "dinle_2 ile yan yana konunca fark açık (makine aynı vokali bu orkestrada iki kattan fazla hatayla yazıyor). Tek başına bakınca armoni sayıları ayırmıyor: beğenilen bir kayıt aynı değeri alıyor."),
 A + "coskulu_1": (lambda a: "Süre %s. %s. Koyun kıtasında döküm \"%s\" yazıyor; ünlü ölçümü iki hecede %s dB (ineğin \"mö\"sü %s dB). Ayrıca horoz kıtasında bozuk dize bulundu (\"diye gümler. Ben balta grupu var\")."
                   % (sure_yaz(a), sz(a), kita(a, 1, "soylenen_ses"), unlu(a, "koyun"), unlu(a, "inek")),
                   "kısmen", "\"Çok uzun\" ve bozuk bir dize bulundu; \"koyun mö diyor\" dökümde görünmüyor."),
 A + "coskulu_2": (lambda a: "Süre %s. %s. Koyun kıtasında dökümde söylenen ses **\"%s\"**: bulundu. (Ünlü ölçümü kararsız: iki hece %s dB; ineğinki %s dB.) Ayrıca son kıtada kedi yerine yine köpek söyleniyor."
                   % (sure_yaz(a), sz(a), kita(a, 1, "soylenen_ses"), unlu(a, "koyun"), unlu(a, "inek")),
                   "evet", "İki şikâyet de (koyunun sesi, süre) görünüyor."),
 P + "duzgun_1": (lambda a: "%s; hece hızı %s/sn; kalite tahminleri ve yapaylık vekilleri öteki kayıtlarla aynı aralıkta. Araç başka şeyler buldu: 5. kıtada \"bebek\" yerine \"abla\", bir \"Merhaba\" yerine \"Merengim\"; enerji satırı \"ninni/sakin\"."
                  % (sz(a), s(m(a, "hece_sn_obek_medyan"), 1)),
                  "hayır", "Aksanın ölçülebilir bir izi yok. Bulunanlar başka kusurlar."),
 P + "duzgun_2": (lambda a: "%s; Scribe ortalama güveni %s (seçilen kayıtta %s); beş ad doğru; hece hızı %s/sn."
                  % (sz(a), s(((SD.get(a) or {}).get("guven") or {}).get("ortalama_logprob"), 3, True), s(((SD.get(P + "coskulu_1") or {}).get("guven") or {}).get("ortalama_logprob"), 3, True), s(m(a, "hece_sn_obek_medyan"), 1)),
                  "hayır", "Makine sözleri kusursuz ve emin biçimde yazıyor; aksanı gösteren hiçbir sayı yok. Tek fark yavaşlık."),
 P + "turkce_2": (lambda a: "%s. Kıta denetimi: 3. kıtada **\"anne parmak, anne parmak\"** (olması gereken \"abi\"): bulundu." % sz(a), "evet", "Kullanıcının söylediği hata, saniyesiyle bulundu."),
 P + "yavas_2": (lambda a: "%s. 3. kıtada \"anne parmak, abi parmak\", 4. kıtada \"able parmak, abi parmak\": bulundu. %s; özet satırı \"ninni/sakin\"." % (sz(a), en(a)),
                 "evet", "Hem söz hatası hem \"ninni gibi\" yargısı sayıda görünüyor."),
 "pitirin-ailesi__yavas_2": (lambda a: en(a) + "; özet satırı: \"%s\"." % {"iyi": "coşkulu yana yakın", "dikkat": "ninni/sakin uyarısı", "bilgi": "yorum yok"}.get((m(a, "ozet") or {}).get("Enerji / coşku"), "–"),
                             "evet", "MusicCoCa ve CED \"ninni\" yargıyla aynı yanda."),
 E + "sarki_1": (lambda a: en(a) + "; özet satırı \"ninni/sakin\". (Hareketlilik puanı tek başına yanıltırdı: seçilen coşkulu kayıt %s, bu %s.)" % (s(m(E + "coskulu_2", "enerji_puani"), 0), s(m(a, "enerji_puani"), 0)),
                 "evet", "MusicCoCa ve CED \"ninni\" yargıyla aynı yanda; hareketlilik puanı değil."),
 P + "sarki_2": (lambda a: "Hece hızı %s/sn (öbek medyanı), kıtadan kıtaya %s sn: altı kaydın en hızlısı. Ama seçilen kayıt %s/sn ile hemen yanında ve aracın \"çok hızlı\" uyarısını o alıyor, bu değil."
                 % (s(m(a, "hece_sn_obek_medyan"), 1), s(_kita_araligi(a), 1), s(m(P + "coskulu_1", "hece_sn_obek_medyan"), 1)),
                 "kısmen", "Sıralama doğru (en hızlısı bu), ama fark ölçüm hatası kadar küçük; araç çizgiyi çekemiyor."),
}


def _kita_araligi(a):
    k = (SD.get(a) or {}).get("kitalar") or []
    b = [x["bas_sn"] for x in k]
    d = [b[i + 1] - b[i] for i in range(len(b) - 1)]
    return (sum(d) / len(d)) if d else None


KISA = {x["ad"]: x["yol"].replace(".mp3", "") for x in SET}
KISA[A + "dogal_onizleme"] = "ali-baba/yeni3/onizleme/ali-baba-dogal-onizleme"


def ana_tablo():
    L = ["| Kayıt | Kullanıcının kararı ve gerekçesi | Aracın o boyutta gördüğü | Araç kararı açıklıyor mu |", "|---|---|---|---|"]
    for x in SET:
        a = x["ad"]
        if a not in M:
            L.append("| %s | %s: %s | (ölçüm tamamlanmadı) | – |" % (KISA[a], "**Beğendi**" if x["karar"] == "begendi" else "**Reddetti**", x["gerekce"]))
            continue
        f, hukum, neden = ANA[a]
        L.append("| `%s` | %s: %s | %s | **%s.** %s |" % (KISA[a], "**Beğendi**" if x["karar"] == "begendi" else "**Reddetti**", x["gerekce"], f(a).replace("|", "/"), hukum.capitalize(), neden))
    return "\n".join(L)


# ---------------------------------------------------------------------------------------------------------------------------------
# BOYUT HUKUMLERI (json icin de)
# ---------------------------------------------------------------------------------------------------------------------------------
kullanilan = round(sum(k.get("tahmini_kredi", 0) for k in DEFTER.get("kayitlar", [])))
benim = round(sum(k.get("tahmini_kredi", 0) for k in DEFTER.get("kayitlar", []) if k["dosya"] in ("duzgun_2.mp3", "coskulu_1.mp3", "turkce_2.mp3", "coskulu_2.mp3", "ali-baba-dogal-onizleme.mp3", "sarki_birlesik.mp3")))
e_coca, e_ninni, e_puan = olcu("enerji", "coca_cosku"), olcu("enerji", "ced_ninni"), olcu("enerji", "enerji_puani")
d_wer, d_donmus = olcu("dogallik", "wer"), olcu("dogallik", "y_donmus_sure_orani")
sure_r = olcu("sure", "sure_sn")

BOYUTLAR = [
 dict(ad="Sözler: yanlış, eksik, bozuk sözcük", hukum="güvenilir",
      ozet="Kullanıcının söylediği yanlış aile adı hataları (iki kayıt) ve hiç anlaşılmayan sözler (bir kayıt) dökümde saniyesiyle bulundu; araç kullanıcının söylemediği gerçek hatalar da buldu. Karar için sözcük hata oranına değil, kıta kıta anahtar sözcük denetimine bakılmalı."),
 dict(ad="Sözler: tek hecelik söylenen hayvan sesi, küçük telaffuz bozukluğu", hukum="kısmen",
      ozet="\"Koyun mö diyor\" üç kayıttan birinde, atın yanlış sesi bir kayıtta bulundu; ikisinde döküm \"me\" yazıyor. \"atıları\" bulunamadı: tanıma modeli sözcüğü düzeltip yazıyor."),
 dict(ad="Süre", hukum="güvenilir", ozet="Doğrudan ölçüm."),
 dict(ad="Enerji: coşkulu mu, ninni gibi mi", hukum="güvenilir",
      ozet="MusicCoCa coşku farkı ve CED \"ninni\" olasılığı, kullanıcının etiketlediği altı kaydı temiz ayırıyor. Hareketlilik puanı tek başına ayırmıyor; aracın özet satırı bu yüzden yanlış uyarı verebiliyor."),
 dict(ad="Ses doğal mı (vokoder, esnetme, perde düzleme)", hukum="kısmen",
      ozet="İşlenmiş iki vokali ayıran tek temiz sayı, makinenin sözleri anlayıp anlamadığı. \"Yapaylık\" vekilleri doğal ama yavaş söylenen kayıtlarda da ötüyor; konuşma-kalitesi tahminleri hiç ayırmıyor. Panoda gözle görülüyor."),
 dict(ad="Vokal orkestrayla uyumlu mu", hukum="kısmen",
      ozet="Aynı vokalin iki karışımı yan yana ölçülünce fark çok açık. Tek kayda bakarak verilen \"aynı armonide mi\" hükmü güvenilmez: beğenilen bir kayıt da aynı uyarıyı alıyor. \"Gömük vokal\" ve \"akort\" uyarıları ise ölçüm yoluna bağlı çıktı."),
 dict(ad="Söyleyiş hızı", hukum="kısmen", ozet="Araç en hızlı kaydı doğru sıralıyor, ama kullanıcının \"çok hızlı\" dediği kayıtla seçtiği kayıt arasındaki fark ölçüm hatası kadar; uyarı yanlış kayda gidiyor."),
 dict(ad="Aksan (\"Türkçe konuşan İngiliz gibi\")", hukum="hayır", ozet="Hiçbir sayı ayırmıyor: sözcük hata oranı, Scribe güveni, kalite tahminleri, denenen iki fonetik ölçü. İki kaydın ortak ölçülebilir özelliği yalnızca yavaşlık."),
 dict(ad="Ezgi bilinen ezgi mi", hukum="hayır", ozet="Araç istenen ezgiyle karşılaştırma yapmıyor."),
 dict(ad="Ses hoş mu, çocuk sever mi", hukum="hayır", ozet="Ölçülemiyor. Konuşma-kalitesi tahminleri kullanıcının zevkiyle ters bile düşüyor (en yüksek puanları reddedilen yavaş kayıtlar alıyor)."),
]
IM = {"güvenilir": "**Evet, güvenilir**", "kısmen": "**Kısmen**", "hayır": "**Hayır**"}

# ---------------------------------------------------------------------------------------------------------------------------------
# METIN
# ---------------------------------------------------------------------------------------------------------------------------------
L = []
ek = L.append
ek("# Kalibrasyon: dinleme takımı kullanıcının kulağıyla ne kadar örtüşüyor?")
ek("")
ek("_%s · dinle.py 1.0 · kullanıcının kulağıyla yargıladığı 17 kayıt (5 beğenilen, 12 reddedilen)_" % time.strftime("%d.%m.%Y"))
ek("")
if EKSIK:
    ek("> **Eksik:** şu kayıtların ölçümü bu sürüm yazılırken bitmemişti: %s." % ", ".join(EKSIK))
    ek("")
ek("Claude sesi duyamıyor. Dinleme takımı (`dinleme/arac/dinle.py`) sesi sayıya, metne ve resme çeviriyor. Burada o takımı tek gerçek ölçüye, kullanıcının kendi kulağıyla verdiği kararlara vurduk: "
   "araç her kararı **doğru boyutta** açıklayabiliyor mu?")
ek("")
ek("## Kısa sonuç")
ek("")
ek("| Boyut | Araç kullanıcının kararını açıklıyor mu | Neden |")
ek("|---|---|---|")
for b in BOYUTLAR:
    ek("| %s | %s | %s |" % (b["ad"], IM[b["hukum"]], b["ozet"]))
ek("")
ek("Üç şey akılda kalsın:")
ek("")
ek("1. **En güçlü kulak, sözleri yazdırmak.** Kullanıcının reddettiği 12 kaydın 5'inde gerekçe dökümde açıkça görünüyor (yanlış aile adı, yanlış hayvan sesi, hiç anlaşılmayan sözler); "
   "ikisinde daha döküm başka bir kusuru gösteriyor.")
ek("2. **\"Sorun bulunmadı\" beğenilecek demek değil.** Aksan yüzünden reddedilen `duzgun_2` araçtan neredeyse temiz çıkıyor.")
ek("3. **Tek kayda not vermek yerine iki kaydı yan yana ölçmek** çok daha güvenilir. Aynı vokalin üç hâli (özgün, başka orkestrada, esnetilmiş) yan yana konunca farklar apaçık; tek tek bakınca eşikler tutmuyor.")
ek("")
ek("## Ne yapıldı")
ek("")
ek("- 17 kaydın hepsinde `dinle.py --ayir` çalıştırıldı; sözleri bilinen 16'sında `--sozler` ile. Raporlar ve panolar: `kalibrasyon/raporlar/<kayıt>/`.")
ek("- Döküm: 7 kayıtta şarkının yanındaki eski `*_words.json` dosyası kullanıldı (yeniden döküm alınmadı; bu dosyalarda sözcük güveni yok), 2'si önbellekteydi, "
   "8'i bu çalışmada alındı (%d kredi). Çalgısal altyapı döküme gönderilmedi. Defter toplamı: **%d / 8000 kredi**." % (benim, kullanilan))
ek("- **Beklenen sözler yeniden kuruldu.** Üretim istemleri depoda yok. `kalibrasyon/sozler/` altındaki metinler, kayıtların dökümlerindeki ortak kalıptan ve kullanıcının sözlerinden "
   "(\"3. kıta abi parmak olmalı\", \"atları\") çıkarıldı; her dosyanın başında kaynağı yazıyor. Bu yüzden sözcük hata oranları birkaç puan oynayabilir; kıta denetimleri bundan etkilenmez.")
ek("- Araca dokunulmadı. Eski dökümleri verebilmek için ince bir sarıcı (`kod/dinle_sarici.py`) ve araç dışı üç küçük deney yazıldı (kıta denetimi, söylenen ünlünün tınısı, aksan izi).")
ek("- İki reddedilmiş kayıt, eldeki gerçek kanallarla (kuru vokal + orkestra) bir kez daha ölçüldü; otomatik ayırmanın payını görmek için. Çıkan bir tutarsızlığın izi sürüldü (`kod/08c_vokal_perde_karsilastir.py`).")
ek("- Gemini'ye canlı istek **gönderilmedi** (bu çalışmanın kuralı yalnızca ElevenLabs dökümüne izin veriyordu; kota da öteki ekiple ortak). Önbellekteki eski Gemini cevapları kanıt olarak kullanıldı.")
ek("")
ek("## Ana tablo: her karar ve aracın o boyutta gördüğü")
ek("")
ek(ana_tablo())
ek("")
n_evet = sum(1 for x in SET if x["ad"] in M and ANA[x["ad"]][1] == "evet")
n_kismen = sum(1 for x in SET if x["ad"] in M and ANA[x["ad"]][1] == "kısmen")
n_hayir = sum(1 for x in SET if x["ad"] in M and ANA[x["ad"]][1] == "hayır")
ek("Toplam: %d kayıtta **evet**, %d kayıtta **kısmen**, %d kayıtta **hayır** (ikisi de aksan)." % (n_evet, n_kismen, n_hayir))
ek("")

# ------------------------------------------------------------------ SOZLER
ek("## Boyut boyut")
ek("")
ek("Her boyutta soru aynı: kullanıcının olumlu ve olumsuz dediği kayıtların sayıları arasında **temiz boşluk** var mı? Eşik yalnızca boşluk temizse öneriliyor. "
   "Örnek sayısı çok küçük (boyut başına 1-6 kayıt); eşikler \"bu kullanıcının bu kayıtlarında böyle çıktı\" demektir, genel kural değildir.")
ek("")
ek("### 1. Sözler")
ek("")
ek(T.get("sozler", ""))
ek("")
ek("**Araç ne buldu**")
ek("")
ek("- `turkce_2`: 3. kıta \"anne parmak, anne parmak\". `yavas_2`: 3. kıta \"anne, abi\", 4. kıta \"able, abi\". Kullanıcının söylediği hataların ikisi de bulundu.")
ek("- `ali-baba/coskulu_2`: koyun kıtasında \"Mö mö\". Kullanıcının \"koyun hâlâ mö diyor\" sözü dökümde aynen görünüyor. Ayrıca kedi kıtası yok, köpek iki kez söyleniyor.")
ek("- `ali-baba/coskulu_1`: horoz kıtasında anlamsız dize (\"diye gümler. Ben balta grupu var\"); Scribe bu sözcüklerde emin değil (logprob −1,49).")
ek("- `v2_2`: at kıtasında söylenen ses \"Me me\", yani koyunun sesi.")
ek("- `ornek_kita1`: 13 sözcüğün hiçbiri tanınmıyor.")
ek("- Kullanıcının **söylemediği** gerçek hatalar: `dinle_2`'de \"köpekleri\" yerine ikinci kez \"ördekleri\"; `duzgun_1`'de 5. kıtada \"bebek\" yerine \"abla\"; `sarki_2`'de bir \"bebek\" eksik.")
ek("")
ek("**Araç neyi kaçırdı**")
ek("")
ek("- `v2_2`'deki \"atıları\": Scribe \"atları\" yazıyor. Tanıma modeli bozuk söylenen sözcüğü doğrusuna tamamlıyor. Eski dökümde sözcük güveni olmadığı için o yoldan da bakılamadı.")
ek("- `v2_2` ve `ali-baba/coskulu_1`'de koyunun sesi: döküm \"Me me\" yazıyor. Aşağıdaki ünlü ölçümü de \"e\" yanında. Kullanıcının kulağı ile makine burada ayrışıyor; hangisinin haklı olduğunu bu araçla söyleyemem.")
ek("")
ek("Söylenen hayvan sesleri (döküm + ünlü tınısı deneyi; \"ö\" gibi yuvarlak ünlüde 1,8–2,8 kHz bandı zayıf, yani sayı eksi; \"e\"de artı):")
ek("")
ek(T.get("hayvan_sesi", ""))
ek("")
ek("**Sözcük hata oranı karar vermeye yaramıyor.** Beğenilen kayıtlar %s arasında; söz hatası yüzünden reddedilenler (`turkce_2`, `yavas_2`) %s ve %s. Yani tek bir yanlış aile adı %%4-10'luk bir orana sığıyor, "
   "sonda fazladan söylenen sekiz sözcük de (`dinle_2`). Kullanıcı ilkini affetmiyor, ikincisini fark etmiyor bile. **Eşik önermiyorum;** öneri bir kural: "
   "her kıtanın anahtar sözcüğü (aile adı, hayvan adı, hayvan sesi) beklenenle aynı mı? Biri bile tutmuyorsa kayıt kullanıcıya gitmeden elenir."
   % (aralik([P + "coskulu_1", E + "coskulu_2", A + "dinle_2", A + "v2_2"], "wer", 1, yuzde=True), s(m(P + "turkce_2", "wer"), 1, yuzde=True), s(m(P + "yavas_2", "wer"), 1, yuzde=True)))
ek("")
ek("Tek kaba eşik temiz: makinenin sözleri **hiç anlayamadığı** kayıtlar (aşağıda, doğallık).")
ek("")

# ------------------------------------------------------------------ ENERJI
ek("### 2. Enerji: coşkulu mu, ninni gibi mi")
ek("")
ek(T.get("enerji", ""))
ek("")
def boslukyaz(r, n=2, isaret=False):
    if not r:
        return "veri yok"
    po = ", ".join("%s %s" % (a, s(float(v), n, isaret)) for a, v in r.get("olumlu", []))
    ne = ", ".join("%s %s" % (a, s(float(v), n, isaret)) for a, v in r.get("olumsuz", []))
    return "coşkulu: %s · ninni: %s → %s" % (po, ne, ("**temiz boşluk** (%s ile %s arası boş)" % (s(r["bosluk"][0], n, isaret), s(r["bosluk"][1], n, isaret))) if r.get("temiz_bosluk") else "**örtüşüyor**")
ek("Kullanıcının coşku üstüne açıkça konuştuğu altı kayıt var (üç \"coşkulu / olmuş\", üç \"ninni gibi\"):")
ek("")
ek("- **MusicCoCa coşku farkı** — %s." % boslukyaz(e_coca, 2, True))
ek("- **CED \"ninni\" olasılığı** — %s." % boslukyaz(e_ninni, 3))
ek("- **Hareketlilik puanı** — %s." % boslukyaz(e_puan, 0))
ek("")
return_placeholder = None
ek("{ENERJI_YORUM}")
ek("")

# ------------------------------------------------------------------ DOGALLIK
ek("### 3. Ses doğal mı (vokoder, esnetme, perde düzleme)")
ek("")
ek(T.get("dogallik", ""))
ek("")
ek("{DOGALLIK_YORUM}")
ek("")
if T.get("gercek_kanallar"):
    ek("Otomatik ayırmanın payı (aynı kayıt, gerçek kanallarla yeniden):")
    ek("")
    ek(T["gercek_kanallar"])
    ek("")
    ek("{GERCEK_KANAL_YORUM}")
    ek("")

# ------------------------------------------------------------------ UYUM
ek("### 4. Vokal orkestrayla uyumlu mu")
ek("")
ek(T.get("uyum", ""))
ek("")
ek("{UYUM_YORUM}")
ek("")

# ------------------------------------------------------------------ AKSAN
ek("### 5. Aksan: \"Türkçe konuşan bir İngiliz gibi\"")
ek("")
ek(T.get("aksan", ""))
ek("")
ek("{AKSAN_YORUM}")
ek("")

# ------------------------------------------------------------------ HIZ + SURE
ek("### 6. Söyleyiş hızı")
ek("")
ek(T.get("hiz", ""))
ek("")
ek("{HIZ_YORUM}")
ek("")
ek("### 7. Süre")
ek("")
ek("{SURE_YORUM}")
ek("")
ek("### 8. Ezgi bilinen ezgi mi")
ek("")
ek("{EZGI_YORUM}")
ek("")
ek("## Önerilen karar eşikleri (yalnızca boşluğun temiz olduğu yerlerde)")
ek("")
ek("{ESIKLER}")
ek("")
ek("## Aracın kendi özet satırları ne dedi")
ek("")
ek("✓ iyi · ! dikkat · ✗ sorun · · yorum yok")
ek("")
ek(T.get("ozet_satirlari", ""))
ek("")
ek("{OZET_SATIRI_YORUM}")
ek("")
ek("## Panolara bakınca: resim, sayının söylemediğini söylüyor mu?")
ek("")
ek("{PANO_YORUM}")
ek("")
ek("## Araçta görülen kusurlar (araca dokunulmadı; kurucusuna not)")
ek("")
ek("{KUSURLAR}")
ek("")
ek("## Bu çalışmanın sınırları")
ek("")
ek("{SINIRLAR}")
ek("")
ek("## Bundan sonra ne işe yarar")
ek("")
ek("{SONRA}")
ek("")
ek("## Dosyalar")
ek("")
ek("| Yer | İçerik |")
ek("|---|---|")
ek("| `kalibrasyon/kalibrasyon.md`, `kalibrasyon.json` | bu rapor ve makinece okunur özeti |")
ek("| `kalibrasyon/raporlar/<kayıt>/` | her kayıt için `rapor.md`, `rapor.json` ve PNG panolar (`…__gercek_kanallar` = gerçek kanallarla ikinci ölçüm) |")
ek("| `kalibrasyon/sozler/` | yeniden kurulan beklenen sözler |")
ek("| `kalibrasyon/ara/` | toplanan sayılar: `olcumler.json`, `ayrisma.json`, `soz_denetimi.json`, `unlu_tinisi.json`, `aksan_deneyi.json`, `gercek_kanallar.json` |")
ek("| `kalibrasyon/kod/` | çalıştırılan betikler (`set.py` kayıt listesi; `01`…`11` sırayla) |")
ek("| `kalibrasyon/gunluk/` | çalışma günlükleri |")
ek("| `dinleme/onbellek/` | bu çalışmada alınan 8 Scribe dökümü ve kredi defteri |")
ek("")

metin = "\n".join(L)
YORUM = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "yorumlar.json"), encoding="utf8")) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "yorumlar.json")) else {}
for k, v in YORUM.items():
    if isinstance(v, str):
        metin = metin.replace("{" + k + "}", v)
open(os.path.join(KAL, "kalibrasyon.md"), "w", encoding="utf8").write(metin + "\n")

# ---------------------------------------------------------------------------------------------------------------------------------
J = {
 "tarih": time.strftime("%Y-%m-%d %H:%M"), "arac": "dinle.py 1.0 (2026-11-21)", "kayit_sayisi": len(SET), "olcumu_eksik": EKSIK,
 "uyari": "Kucuk ornek (17 kayit, boyut basina 1-6 etiket). Esikler bu kullanicinin bu kayitlari icindir; genel kural degildir. Hicbir olcum insan kulagi degildir.",
 "kredi": {"scribe_defter_toplami": kullanilan, "sinir": 8000, "bu_calismada_alinan_dokum": 8, "bu_calismada_harcanan": benim, "gemini_canli_istek": 0},
 "boyutlar": [{"boyut": b["ad"], "hukum": b["hukum"], "ozet": b["ozet"]} for b in BOYUTLAR],
 "kayitlar": [{"ad": x["ad"], "yol": x["yol"], "karar": x["karar"], "gerekce": x["gerekce"], "boyut": x["boyut"],
               "arac_aciklıyor_mu": (ANA[x["ad"]][1] if x["ad"] in M else None), "neden": (ANA[x["ad"]][2] if x["ad"] in M else None),
               "aracin_gordugu": (ANA[x["ad"]][0](x["ad"]) if x["ad"] in M else None),
               "olcumler": {k: v for k, v in (M.get(x["ad"]) or {}).items() if k not in ("ad", "yol", "karar", "gerekce", "boyut", "sarki")}} for x in SET],
 "ozet": {"guvenilir": [b["ad"] for b in BOYUTLAR if b["hukum"] == "güvenilir"], "kismen": [b["ad"] for b in BOYUTLAR if b["hukum"] == "kısmen"], "hayir": [b["ad"] for b in BOYUTLAR if b["hukum"] == "hayır"],
          "kayit_bazinda": {"evet": n_evet, "kismen": n_kismen, "hayir": n_hayir}},
 "ayrisma": AY, "soz_denetimi": SD, "unlu_tinisi_deneyi": UT, "aksan_deneyi": AK, "gercek_kanallar": GK,
 "ayni_vokalin_dort_hali_perde_karsilastirmasi": oku("vokal_perde_karsilastirma.json"), "cakisan_nota_hayvan_sesi_denetimi": oku("cakisan_hayvan.json"),
 "bakilan_panolar": ["ali-baba__v2_2/00_genel_bakis.png", "ali-baba__v2_2/02_perde_026-052sn.png", "ali-baba__v2_2/02_pano_026-052sn.png", "ali-baba__dinle_2/01_perde_000-028sn.png", "ali-baba__dinle_2/01_pano_000-028sn.png",
                     "parmak-ailesi__coskulu_1/00_genel_bakis.png", "parmak-ailesi__coskulu_1/01_pano_000-027sn.png", "ali-baba__demo_altyapi_sesli/00_genel_bakis.png",
                     "ali-baba__ornek_kita1/01_perde_000-027sn.png", "ali-baba__ornek_kita1/01_pano_000-027sn.png", "ali-baba__sarki_birlesik/01_perde_000-026sn.png", "ali-baba__sarki_birlesik/01_pano_000-026sn.png",
                     "ali-baba__dogal_onizleme/01_perde_000-027sn.png", "parmak-ailesi__duzgun_1/01_pano_000-023sn.png", "parmak-ailesi__yavas_2/00_genel_bakis.png"],
 "esik_onerileri": YORUM.get("_esikler_json", []), "arac_kusurlari": YORUM.get("_kusurlar_json", []), "gorsel_kanal": YORUM.get("_gorsel_json", []), "sinirlar": YORUM.get("_sinirlar_json", []),
 "gereksinimler": YORUM.get("_gereksinim_json", []),
}
json.dump(J, open(os.path.join(KAL, "kalibrasyon.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
print("yazildi:", os.path.join(KAL, "kalibrasyon.md"), len(metin), "karakter; eksik:", EKSIK, "| doldurulmamis:", [k for k in ("ENERJI_YORUM", "DOGALLIK_YORUM", "UYUM_YORUM") if "{" + k + "}" in metin])
