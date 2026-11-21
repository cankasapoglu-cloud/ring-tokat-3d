# Kalibrasyon: dinleme takımı kullanıcının kulağıyla ne kadar örtüşüyor?

_21.11.2026 · dinle.py 1.0 · kullanıcının kulağıyla yargıladığı 17 kayıt (5 beğenilen, 12 reddedilen)_

> **Eksik:** şu kayıtların ölçümü bu sürüm yazılırken bitmemişti: ali-baba__coskulu_1.

Claude sesi duyamıyor. Dinleme takımı (`dinleme/arac/dinle.py`) sesi sayıya, metne ve resme çeviriyor. Burada o takımı tek gerçek ölçüye, kullanıcının kendi kulağıyla verdiği kararlara vurduk: araç her kararı **doğru boyutta** açıklayabiliyor mu?

## Kısa sonuç

| Boyut | Araç kullanıcının kararını açıklıyor mu | Neden |
|---|---|---|
| Sözler: yanlış, eksik, bozuk sözcük | **Evet, güvenilir** | Kullanıcının söylediği yanlış ad / bozuk dize hatalarının hepsi dökümde, saniyesiyle bulundu. Karar için sözcük hata oranına değil, kıta kıta anahtar sözcük denetimine bakılmalı. |
| Sözler: tek hecelik söylenen hayvan sesi, küçük telaffuz bozukluğu | **Kısmen** | "Koyun mö diyor" üç kayıttan birinde, atın yanlış sesi bir kayıtta bulundu; ikisinde döküm "me" yazıyor. "atıları" bulunamadı: tanıma modeli sözcüğü düzeltip yazıyor. |
| Süre | **Evet, güvenilir** | Doğrudan ölçüm. |
| Enerji: coşkulu mu, ninni gibi mi | **Evet, güvenilir** | MusicCoCa coşku farkı ve CED "ninni" olasılığı, kullanıcının etiketlediği altı kaydı temiz ayırıyor. Hareketlilik puanı tek başına ayırmıyor; aracın özet satırı bu yüzden yanlış uyarı verebiliyor. |
| Ses doğal mı (vokoder, esnetme, perde düzleme) | **Kısmen** | İşlenmiş iki vokali ayıran tek temiz sayı, makinenin sözleri anlayıp anlamadığı. "Yapaylık" vekilleri doğal ama yavaş söylenen kayıtlarda da ötüyor; konuşma-kalitesi tahminleri hiç ayırmıyor. Panoda gözle görülüyor. |
| Vokal orkestrayla uyumlu mu | **Kısmen** | Aynı vokalin iki karışımı yan yana ölçülünce fark çok açık. Tek kayda bakarak verilen "aynı armonide mi" hükmü güvenilmez: beğenilen bir kayıt da aynı uyarıyı alıyor. |
| Söyleyiş hızı | **Kısmen** | Araç en hızlı kaydı doğru sıralıyor, ama kullanıcının "çok hızlı" dediği kayıtla seçtiği kayıt arasındaki fark ölçüm hatası kadar; uyarı yanlış kayda gidiyor. |
| Aksan ("Türkçe konuşan İngiliz gibi") | **Hayır** | Hiçbir sayı ayırmıyor: sözcük hata oranı, Scribe güveni, kalite tahminleri, denenen iki fonetik ölçü. İki kaydın ortak ölçülebilir özelliği yalnızca yavaşlık. |
| Ezgi bilinen ezgi mi | **Hayır** | Araç istenen ezgiyle karşılaştırma yapmıyor. |
| Ses hoş mu, çocuk sever mi | **Hayır** | Ölçülemiyor. Konuşma-kalitesi tahminleri kullanıcının zevkiyle ters bile düşüyor (ninni gibi kayıtlar daha yüksek puan alıyor). |

Üç şey akılda kalsın:

1. **En güçlü kulak, sözleri yazdırmak.** Kullanıcının reddettiği 12 kaydın 5'inde gerekçe dökümde açıkça görünüyor (yanlış aile adı, yanlış hayvan sesi, hiç anlaşılmayan sözler); ikisinde daha döküm başka bir kusuru gösteriyor.
2. **"Sorun bulunmadı" beğenilecek demek değil.** Aksan yüzünden reddedilen `duzgun_2` araçtan neredeyse temiz çıkıyor.
3. **Tek kayda not vermek yerine iki kaydı yan yana ölçmek** çok daha güvenilir. Aynı vokalin üç hâli (özgün, başka orkestrada, esnetilmiş) yan yana konunca farklar apaçık; tek tek bakınca eşikler tutmuyor.

## Ne yapıldı

- 17 kaydın hepsinde `dinle.py --ayir` çalıştırıldı; sözleri bilinen 16'sında `--sozler` ile. Raporlar ve panolar: `kalibrasyon/raporlar/<kayıt>/`.
- Döküm: 7 kayıtta şarkının yanındaki eski `*_words.json` dosyası kullanıldı (yeniden döküm alınmadı; bu dosyalarda sözcük güveni yok), 2'si önbellekteydi, 8'i bu çalışmada alındı (5655 kredi). Çalgısal altyapı döküme gönderilmedi. Defter toplamı: **6576 / 8000 kredi**.
- **Beklenen sözler yeniden kuruldu.** Üretim istemleri depoda yok. `kalibrasyon/sozler/` altındaki metinler, kayıtların dökümlerindeki ortak kalıptan ve kullanıcının sözlerinden ("3. kıta abi parmak olmalı", "atları") çıkarıldı; her dosyanın başında kaynağı yazıyor. Bu yüzden sözcük hata oranları birkaç puan oynayabilir; kıta denetimleri bundan etkilenmez.
- Araca dokunulmadı. Eski dökümleri verebilmek için ince bir sarıcı (`kod/dinle_sarici.py`) ve araç dışı üç küçük deney yazıldı (kıta denetimi, söylenen ünlünün tınısı, aksan izi).
- İki reddedilmiş kayıt, eldeki gerçek kanallarla (kuru vokal + orkestra) bir kez daha ölçüldü; otomatik ayırmanın payını görmek için.
- Gemini'ye canlı istek **gönderilmedi** (bu çalışmanın kuralı yalnızca ElevenLabs dökümüne izin veriyordu; kota da öteki ekiple ortak). Önbellekteki eski Gemini cevapları kanıt olarak kullanıldı.

## Ana tablo: her karar ve aracın o boyutta gördüğü

| Kayıt | Kullanıcının kararı ve gerekçesi | Aracın o boyutta gördüğü | Araç kararı açıklıyor mu |
|---|---|---|---|
| `ali-baba/v2_2` | **Beğendi**: söyleyiş iyi; ama söylenen hayvan sesleri yanlış (koyun ve at), bir sözcük bozuk ('atıları'), ezgi bilinen ezgi değil | sözcük hata oranı %4,7. Kıta denetimi: at kıtasında söylenen ses **"Me me"** (koyunun sesi): bulundu. Koyun kıtasında döküm "Me me" yazıyor, ünlü ölçümü de "e" yanında (iki hece +4,4 / +3,2 dB; ineğin "mö"sü -11,0 / -5,8 dB): koyun için söylenen bulunamadı. "atıları": döküm "atları" yazıyor, bulunamadı. Söyleyiş: yapaylık işareti yok, akort 8,1 cent, çakışan nota 0/40. Ezgi: ölçülmüyor. | **Kısmen.** Dört şikâyetten biri bulundu (at). Beğenilen söyleyişle çelişen bir uyarı yok. |
| `ali-baba/dinle_2` | **Beğendi**: 'ikincisi daha güzel', 'bu seslendirme uygun'; ezgi yine bilinen ezgi değil | Yapaylık işareti yok; akort 8,8 cent; aynı armonide (en iyi kaydırma +0); sözcük hata oranı %8,3. Araç, kullanıcının söylemediği gerçek bir söz hatası buldu (76,9. sn: "köpekleri" yerine "ördekleri"). Ezgi: ölçülmüyor. | **Kısmen.** Beğeniyle çelişen uyarı yok; ama "daha güzel"i gösteren bir sayı da yok. Ezgi karşılaştırması yok. |
| `el-yikama/coskulu_2` | **Beğendi**: el yıkama şarkısı için seçilen coşkulu kayıt | MusicCoCa coşku farkı +0,09, CED 'ninni' 0,000, hareketlilik puanı 77; özet satırı "coşkulu yana yakın". (Ayrıca "aynı armonide mi" satırı **sorun** diyor: en iyi kaydırma -4; beğenilen kayıtta yanlış alarm.) | **Evet.** Coşku göstergeleri seçimle uyumlu. |
| `parmak-ailesi/coskulu_1` | **Beğendi**: parmak ailesi için seçilen coşkulu kayıt (beş ad da doğru) | MusicCoCa coşku farkı +0,10, CED 'ninni' 0,000, hareketlilik puanı 79; beş kıtada beş ad da doğru (sözcük hata oranı %4,0). (Yanlış alarmlar: "ünsüzlerde tiz zayıf" ve "söyleyiş hızı" uyarıları.) | **Evet.** Coşku ve adlar seçimle uyumlu. |
| `ali-baba/yeni/demo_altyapi_sesli` | **Beğendi**: çalgısal altyapı (klarnet ezgisi + gerçek hayvan sesleri): 'olmuş' (daha coşkulu istendikten sonra) | MusicCoCa coşku farkı +0,26, CED 'ninni' 0,000, hareketlilik puanı 64; özet satırı: "yorum yok". Vokal yok; ayırıcı hayvan seslerini "vokal" kanalına koyuyor. | **Evet.** MusicCoCa ve CED coşkulu yanda. Hareketlilik puanı düşük kaldığı için aracın kendi özet satırı "coşkulu" diyemiyor; vokal olmadığı hâlde hayvan seslerine vokal uyarıları veriyor. |
| `ali-baba/yeni/vokal/ornek_kita1` | **Reddetti**: konuşma sentezi vokoderle ezgiye oturtuldu: 'sözler çok kötü çıktı' | sözcük hata oranı %100,0 (Scribe "Maliboku yeşil boya…" duyuyor; sözcüklerin %70 kadarında emin değil); donmuş ünlü %31. | **Evet.** "Sözler çok kötü çıktı" yargısının tam karşılığı: makine tek sözcüğü bile tanımıyor. |
| `ali-baba/yeni2/sarki_birlesik` | **Reddetti**: yapay vokal iki katına esnetilip perdesi ezgiye düzlendi; kullanıcı ardından doğal söyleyişi istedi (yapay duyuldu) | sözcük hata oranı %48,1 (aynı vokalin işlenmemiş hâli dinle_2'de %8,3); donmuş ünlü %20; panoda perde merdiven basamağı gibi. Kalite tahminleri (DNSMOS 2,39, UTMOS 1,34) doğal kayıtlardan farksız. | **Evet.** Sözlerin anlaşılmaz hâle gelmesi ve panodaki görüntü yargıyı açıklıyor; "yapaylık" sayıları tek başına yetmezdi. |
| `ali-baba/yeni3/onizleme/ali-baba-dogal-onizleme` | **Reddetti**: doğal yapay vokal (kendi ezgisi) altta başka ezgi çalan orkestranın üstüne kondu: 'olmamış' | Aynı vokal dinle_2'de: vokal − altyapı -3,4 dB, ±25 cent içinde %88, sözcük hata oranı %8,3. Burada: -13,0 dB, %68, sözcük hata oranı %19,4; "aynı armonide mi" satırı sorun (en iyi kaydırma -4). | **Kısmen.** dinle_2 ile yan yana konunca fark çok açık. Tek başına bakınca armoni sayıları ayırmıyor (beğenilen bir kayıt aynı değeri alıyor); ayıran, ayırıcının vokali temiz çıkaramaması. |
| ali-baba/coskulu_1 | **Reddetti**: 'çok kötü; koyun hâlâ mö diyor'; çok uzun (3-3,5 dk) | (ölçüm tamamlanmadı) | – |
| `ali-baba/coskulu_2` | **Reddetti**: 'çok kötü; koyun hâlâ mö diyor'; çok uzun (3-3,5 dk) | Süre 186 sn (3:06). sözcük hata oranı %13,9. Koyun kıtasında dökümde söylenen ses **"Mö mö"**: bulundu. (Ünlü ölçümü kararsız: iki hece +5,1 / -4,5 dB; ineğinki -8,7 / -8,5 dB.) Ayrıca son kıtada kedi yerine yine köpek söyleniyor. | **Evet.** İki şikâyet de (koyunun sesi, süre) görünüyor. |
| `parmak-ailesi/duzgun_1` | **Reddetti**: 'çok kötü söylüyor, Türkçe konuşan bir İngiliz gibi' (yabancı aksan) | sözcük hata oranı %8,0; hece hızı 2,4/sn; kalite tahminleri ve yapaylık vekilleri öteki kayıtlarla aynı aralıkta. Araç başka şeyler buldu: 5. kıtada "bebek" yerine "abla", bir "Merhaba" yerine "Merengim"; enerji satırı "ninni/sakin". | **Hayır.** Aksanın ölçülebilir bir izi yok. Bulunanlar başka kusurlar. |
| `parmak-ailesi/duzgun_2` | **Reddetti**: 'çok kötü söylüyor, Türkçe konuşan bir İngiliz gibi' (yabancı aksan) | sözcük hata oranı %4,0; Scribe ortalama güveni -0,007 (seçilen kayıtta -0,004); beş ad doğru; hece hızı 2,6/sn. | **Hayır.** Makine sözleri kusursuz ve emin biçimde yazıyor; aksanı gösteren hiçbir sayı yok. Tek fark yavaşlık. |
| `parmak-ailesi/turkce_2` | **Reddetti**: sözler yanlış (3. kıtada 'abi parmak' yerine 'anne parmak') | sözcük hata oranı %10,0. Kıta denetimi: 3. kıtada **"anne parmak, anne parmak"** (olması gereken "abi"): bulundu. | **Evet.** Kullanıcının söylediği hata, saniyesiyle bulundu. |
| `parmak-ailesi/yavas_2` | **Reddetti**: sözler yanlış (3. kıtada 'anne parmak') ve 'ninni gibi söylüyor, coşku yok' | sözcük hata oranı %6,0. 3. kıtada "anne parmak, abi parmak", 4. kıtada "able parmak, abi parmak": bulundu. MusicCoCa coşku farkı -0,08, CED 'ninni' 0,044, hareketlilik puanı 52; özet satırı "ninni/sakin". | **Evet.** Hem söz hatası hem "ninni gibi" yargısı sayıda görünüyor. |
| `pitirin-ailesi/yavas_2` | **Reddetti**: yavaş, sakin kayıt: 'ninni gibi, coşku yok' dönemi | MusicCoCa coşku farkı -0,09, CED 'ninni' 0,023, hareketlilik puanı 58; özet satırı: "ninni/sakin uyarısı". | **Evet.** MusicCoCa ve CED "ninni" yargıyla aynı yanda. |
| `el-yikama/sarki_1` | **Reddetti**: yavaş, sakin kayıt: 'ninni gibi, coşku yok' dönemi | MusicCoCa coşku farkı -0,04, CED 'ninni' 0,027, hareketlilik puanı 71; özet satırı "ninni/sakin". (Hareketlilik puanı tek başına yanıltırdı: seçilen coşkulu kayıt 77, bu 71.) | **Evet.** MusicCoCa ve CED "ninni" yargıyla aynı yanda; hareketlilik puanı değil. |
| `parmak-ailesi/sarki_2` | **Reddetti**: 'sözler çok hızlı geçiyor' | Hece hızı 4,8/sn (öbek medyanı), kıtadan kıtaya 10,2 sn: altı kaydın en hızlısı. Ama seçilen kayıt 4,6/sn ile hemen yanında ve aracın "çok hızlı" uyarısını o alıyor, bu değil. | **Kısmen.** Sıralama doğru (en hızlısı bu), ama fark ölçüm hatası kadar küçük; araç çizgiyi çekemiyor. |

Toplam: 10 kayıtta **evet**, 4 kayıtta **kısmen**, 2 kayıtta **hayır** (ikisi de aksan).

## Boyut boyut

Her boyutta soru aynı: kullanıcının olumlu ve olumsuz dediği kayıtların sayıları arasında **temiz boşluk** var mı? Eşik yalnızca boşluk temizse öneriliyor. Örnek sayısı çok küçük (boyut başına 1-6 kayıt); eşikler "bu kullanıcının bu kayıtlarında böyle çıktı" demektir, genel kural değildir.

### 1. Sözler

| Kayıt | Karar | Döküm | Sözcük hata oranı | Değişik / eksik / fazla | Scribe'ın emin olmadığı sözcükler | Kıta kıta yapısal denetim (✗ = uymuyor) |
|---|---|---|---|---|---|---|
| ali-baba/v2_2 | beğendi | eski dosya | %4,7 | 4 / 1 / 0 | ölçülemedi | inek: Mö mö; koyun: Me me; at: Me me ✗; horoz: Üü üü; ördek: Vak vak; köpek: Hav hav; kedi: Miyav miyav |
| ali-baba/dinle_2 | beğendi | bu çalışma | %8,3 | 1 / 0 / 8 | %0 | – |
| el-yikama/coskulu_2 | beğendi | bu çalışma | %4,3 | 0 / 0 / 2 | %0 | – |
| parmak-ailesi/coskulu_1 | beğendi | bu çalışma | %4,0 | 0 / 0 / 2 | %0 | 1. baba+baba; 2. anne+anne; 3. abi+abi; 4. abla+abla; 5. bebek+bebek |
| ali-baba/yeni/demo_altyapi_sesli | beğendi | yok | – | – | ölçülemedi | – |
| ali-baba/yeni/vokal/ornek_kita1 | reddetti | bu çalışma | %100,0 | 10 / 3 / 0 | %70 | – |
| ali-baba/yeni2/sarki_birlesik | reddetti | bu çalışma | %48,1 | 42 / 10 / 0 | %7 | – |
| ali-baba/yeni3/…/dogal-onizleme | reddetti | bu çalışma | %19,4 | 20 / 1 / 0 | %4 | – |
| ali-baba/coskulu_2 | reddetti | bu çalışma | %13,9 | 8 / 0 / 7 | %3 | inek: Mö mö; koyun: Mö mö ✗; at: İha ha ihan ha; horoz: Ü ürü ü; ördek: Vak vak; köpek: Hav hav; köpek: Hav hav |
| parmak-ailesi/duzgun_1 | reddetti | eski dosya | %8,0 | 3 / 1 / 0 | ölçülemedi | 1. baba+baba; 2. anne+anne; 3. abi+abi; 4. abla+abla; 5. abla+abla ✗ |
| parmak-ailesi/duzgun_2 | reddetti | bu çalışma | %4,0 | 2 / 0 / 0 | %0 | 1. baba+baba; 2. anne+anne; 3. abi+abi; 4. abla+abla; 5. bebek+bebek |
| parmak-ailesi/turkce_2 | reddetti | bu çalışma | %10,0 | 2 / 0 / 3 | %2 | 1. baba+baba; 2. anne+anne; 3. anne+anne ✗; 4. abla+abla; 5. bebek+bebek |
| parmak-ailesi/yavas_2 | reddetti | eski dosya | %6,0 | 3 / 0 / 0 | ölçülemedi | 1. baba+baba; 2. anne+anne; 3. anne+abi ✗; 4. able+abi ✗; 5. bebek+bebek |
| pitirin-ailesi/yavas_2 | reddetti | eski dosya | %5,4 | 0 / 3 / 1 | ölçülemedi | – |
| el-yikama/sarki_1 | reddetti | eski dosya | %0,0 | 0 / 0 / 0 | ölçülemedi | – |
| parmak-ailesi/sarki_2 | reddetti | eski dosya | %2,3 | 0 / 1 / 0 | ölçülemedi | 1. baba+baba; 2. anne+anne; 3. abi+abi; 4. abla+abla; 5. bebek ✗ |

**Araç ne buldu**

- `turkce_2`: 3. kıta "anne parmak, anne parmak". `yavas_2`: 3. kıta "anne, abi", 4. kıta "able, abi". Kullanıcının söylediği hataların ikisi de bulundu.
- `ali-baba/coskulu_2`: koyun kıtasında "Mö mö". Kullanıcının "koyun hâlâ mö diyor" sözü dökümde aynen görünüyor. Ayrıca kedi kıtası yok, köpek iki kez söyleniyor.
- `ali-baba/coskulu_1`: horoz kıtasında anlamsız dize ("diye gümler. Ben balta grupu var"); Scribe bu sözcüklerde emin değil (logprob −1,49).
- `v2_2`: at kıtasında söylenen ses "Me me", yani koyunun sesi.
- `ornek_kita1`: 13 sözcüğün hiçbiri tanınmıyor.
- Kullanıcının **söylemediği** gerçek hatalar: `dinle_2`'de "köpekleri" yerine ikinci kez "ördekleri"; `duzgun_1`'de 5. kıtada "bebek" yerine "abla"; `sarki_2`'de bir "bebek" eksik.

**Araç neyi kaçırdı**

- `v2_2`'deki "atıları": Scribe "atları" yazıyor. Tanıma modeli bozuk söylenen sözcüğü doğrusuna tamamlıyor. Eski dökümde sözcük güveni olmadığı için o yoldan da bakılamadı.
- `v2_2` ve `ali-baba/coskulu_1`'de koyunun sesi: döküm "Me me" yazıyor. Aşağıdaki ünlü ölçümü de "e" yanında. Kullanıcının kulağı ile makine burada ayrışıyor; hangisinin haklı olduğunu bu araçla söyleyemem.

Söylenen hayvan sesleri (döküm + ünlü tınısı deneyi; "ö" gibi yuvarlak ünlüde 1,8–2,8 kHz bandı zayıf, yani sayı eksi; "e"de artı):

| Kayıt | Kıta başı | Kıtanın hayvanı | Dökümde söylenen ses | Hayvana uyuyor mu (döküme göre) | Ünlü tınısı, hece hece: 1,8–2,8 kHz eksi 1,2–1,8 kHz (dB) |
|---|---|---|---|---|---|
| ali-baba/v2_2 | 9. sn | inek | Mö mö | uyuyor | -11,0 / -5,8 |
| ali-baba/v2_2 | 22. sn | koyun | Me me | uyuyor | +4,4 / +3,2 |
| ali-baba/v2_2 | 36. sn | at | Me me | **uymuyor** | +2,0 / +2,2 |
| ali-baba/v2_2 | 50. sn | horoz | Üü üü | uyuyor | +7,2 / +2,8 |
| ali-baba/v2_2 | 63. sn | ördek | Vak vak | uyuyor | -18,0 / -19,1 |
| ali-baba/v2_2 | 77. sn | köpek | Hav hav | uyuyor | -18,1 / -17,7 |
| ali-baba/v2_2 | 91. sn | kedi | Miyav miyav | uyuyor | -3,7 / -2,9 |
| ali-baba/coskulu_1 | 8. sn | inek | Mö mö | uyuyor | – |
| ali-baba/coskulu_1 | 41. sn | koyun | Me me | uyuyor | – |
| ali-baba/coskulu_1 | 74. sn | at | İha iha | uyuyor | – |
| ali-baba/coskulu_1 | 108. sn | horoz | Üü üü | uyuyor | – |
| ali-baba/coskulu_1 | 134. sn | ördek | Vak vak | uyuyor | – |
| ali-baba/coskulu_1 | 170. sn | köpek | Hav hav | uyuyor | – |
| ali-baba/coskulu_1 | 203. sn | kedi | Miyav miyav | uyuyor | – |
| ali-baba/coskulu_2 | 8. sn | inek | Mö mö | uyuyor | -8,7 / -8,5 |
| ali-baba/coskulu_2 | 33. sn | koyun | Mö mö | **uymuyor** | +5,1 / -4,5 |
| ali-baba/coskulu_2 | 60. sn | at | İha ha ihan ha | uyuyor | -8,9 / -18,4 / -9,8 / -18,8 |
| ali-baba/coskulu_2 | 87. sn | horoz | Ü ürü ü | uyuyor | +10,0 / +13,4 / +13,9 |
| ali-baba/coskulu_2 | 114. sn | ördek | Vak vak | uyuyor | -17,3 / -18,1 |
| ali-baba/coskulu_2 | 141. sn | köpek | Hav hav | uyuyor | -13,4 / -19,8 |
| ali-baba/coskulu_2 | 168. sn | köpek | Hav hav | uyuyor | -12,8 / -16,9 |

**Sözcük hata oranı karar vermeye yaramıyor.** Beğenilen kayıtlar %4,0 … %8,3 arasında; söz hatası yüzünden reddedilenler (`turkce_2`, `yavas_2`) %10,0 ve %6,0. Yani tek bir yanlış aile adı %4-10'luk bir orana sığıyor, sonda fazladan söylenen sekiz sözcük de (`dinle_2`). Kullanıcı ilkini affetmiyor, ikincisini fark etmiyor bile. **Eşik önermiyorum;** öneri bir kural: her kıtanın anahtar sözcüğü (aile adı, hayvan adı, hayvan sesi) beklenenle aynı mı? Biri bile tutmuyorsa kayıt kullanıcıya gitmeden elenir.

Tek kaba eşik temiz: makinenin sözleri **hiç anlayamadığı** kayıtlar (aşağıda, doğallık).

### 2. Enerji: coşkulu mu, ninni gibi mi

| Kayıt | Kullanıcının coşku yargısı | Hareketlilik puanı | MusicCoCa coşku farkı | CED 'ninni' | Olay/sn | Vurmalı/armonik dB | Parlaklık Hz | Hece/sn | Aracın özet satırı |
|---|---|---|---|---|---|---|---|---|---|
| ali-baba/yeni/demo_altyapi_sesli | **'olmuş'** (coşku istendikten sonra) | 64 | +0,26 | 0,000 | 4,2 | -4,6 | 2491 | – | yorum yok |
| parmak-ailesi/coskulu_1 | **coşkulu diye seçildi** | 79 | +0,10 | 0,000 | 5,5 | -1,8 | 2290 | 4,6 | coşkulu yana yakın |
| el-yikama/coskulu_2 | **coşkulu diye seçildi** | 77 | +0,09 | 0,000 | 5,1 | -3,3 | 2916 | 2,7 | coşkulu yana yakın |
| ali-baba/yeni/vokal/ornek_kita1 | yargı yok (reddetti) | 59 | +0,28 | 0,000 | 4,1 | -6,3 | 2464 | 4,5 | ninni/sakin uyarısı |
| ali-baba/yeni2/sarki_birlesik | yargı yok (reddetti) | 62 | +0,25 | 0,000 | 4,0 | -5,0 | 2554 | 3,3 | yorum yok |
| ali-baba/dinle_2 | yargı yok (beğendi) | 73 | +0,18 | 0,000 | 4,2 | +0,8 | 2684 | 3,9 | coşkulu yana yakın |
| ali-baba/coskulu_2 | yargı yok (reddetti) | 66 | +0,13 | 0,000 | 4,6 | -4,2 | 2097 | 4,0 | coşkulu yana yakın |
| ali-baba/yeni3/…/dogal-onizleme | yargı yok (reddetti) | 56 | +0,13 | 0,000 | 3,5 | -5,0 | 2429 | 4,7 | ninni/sakin uyarısı |
| parmak-ailesi/sarki_2 | yargı yok (reddetti) | 73 | +0,06 | 0,001 | 4,5 | +0,1 | 2124 | 4,8 | yorum yok |
| ali-baba/v2_2 | yargı yok (beğendi) | 75 | +0,01 | 0,000 | 4,7 | +0,9 | 2397 | 3,9 | yorum yok |
| parmak-ailesi/turkce_2 | yargı yok (reddetti) | 66 | -0,03 | 0,007 | 4,4 | -3,6 | 1894 | 3,4 | ninni/sakin uyarısı |
| parmak-ailesi/duzgun_1 | yargı yok (reddetti) | 52 | -0,05 | 0,016 | 4,2 | -9,8 | 2043 | 2,4 | ninni/sakin uyarısı |
| parmak-ailesi/duzgun_2 | yargı yok (reddetti) | 46 | -0,10 | 0,025 | 3,5 | -8,3 | 1829 | 2,6 | ninni/sakin uyarısı |
| el-yikama/sarki_1 | **'ninni gibi'** | 71 | -0,04 | 0,027 | 4,9 | -5,3 | 2539 | 2,4 | ninni/sakin uyarısı |
| parmak-ailesi/yavas_2 | **'ninni gibi'** | 52 | -0,08 | 0,044 | 3,8 | -9,7 | 1804 | 3,0 | ninni/sakin uyarısı |
| pitirin-ailesi/yavas_2 | **'ninni gibi'** | 58 | -0,09 | 0,023 | 4,5 | -9,8 | 2145 | 2,2 | ninni/sakin uyarısı |

Kullanıcının coşku üstüne açıkça konuştuğu altı kayıt var (üç "coşkulu / olmuş", üç "ninni gibi"):

- **MusicCoCa coşku farkı** — coşkulu: el-yikama/coskulu_2 +0,09, parmak/coskulu_1 +0,10, ali-baba/demo_altyapi_sesli +0,26 · ninni: parmak/yavas_2 -0,08, pitirin/yavas_2 -0,09, el-yikama/sarki_1 -0,04 → **temiz boşluk** (-0,04 ile +0,09 arası boş).
- **CED "ninni" olasılığı** — coşkulu: el-yikama/coskulu_2 0,000, parmak/coskulu_1 0,000, ali-baba/demo_altyapi_sesli 0,000 · ninni: parmak/yavas_2 0,044, pitirin/yavas_2 0,023, el-yikama/sarki_1 0,027 → **temiz boşluk** (0,000 ile 0,023 arası boş).
- **Hareketlilik puanı** — coşkulu: el-yikama/coskulu_2 77, parmak/coskulu_1 79, ali-baba/demo_altyapi_sesli 64 · ninni: parmak/yavas_2 52, pitirin/yavas_2 58, el-yikama/sarki_1 71 → **örtüşüyor**.

**MusicCoCa coşku farkı ve CED "ninni" olasılığı kullanıcının yargısını temiz ayırıyor;** iki şarkıda da aynı şarkının coşkulu ve ninni gibi kaydı doğru yana düşüyor (El Yıkama: +0,09 karşısında -0,04; Parmak Ailesi: +0,10 karşısında -0,08).

- Etiketsiz kayıtlar da tutarlı: yavaş dönemin öteki kayıtları (`duzgun_1` -0,05, `duzgun_2` -0,10, `turkce_2` -0,03) eksi yanda.
- `v2_2` (beğenildi, coşkusu hiç konuşulmadı) +0,01 ile boşluğun içinde. Eşik bıçak sırtı değil; arada kalan kayıt "kararsız" sayılmalı.
- **Hareketlilik puanı tek başına güvenilmez.** "Ninni gibi" denen `el-yikama/sarki_1` 71 puan alıyor; seçilen coşkulu kayıtlar 77 … 79. Aradaki 6 puanlık boşluğun içine etiketsiz 3 kayıt giriyor. Puan vuruş ve olay sayıyor; `sarki_1` yavaş söylenmiş ama altyapısı kıpırtılı.
- **Aracın özet satırı yanlış uyarı veriyor.** Kural "MusicCoCa eksi YA DA ninni ≥ 0,02 YA DA puan < 62". Üçüncü koşul yüzünden MusicCoCa'sı açıkça artı olan 2 kayıt "ninni/sakin" uyarısı alıyor: `ornek_kita1` (puan 59, MusicCoCa +0,28), `dogal_onizleme` (puan 56, MusicCoCa +0,13).
- Hece hızı ve otomatik tempo coşkuyu göstermiyor: seçilen `el-yikama/coskulu_2` 2,7 hece/sn ile "ninni gibi" `parmak/yavas_2`'den (3,0) yavaş; otomatik tempo "ninni gibi" kayıtlarda daha yüksek çıkıyor (156 … 160 BPM; büyük olasılıkla çift sayım).

Neyi söylemez: bu göstergeler müziğin türünü ve hareketini tanıyor; şarkıcının sesindeki neşeyi değil. Coşkulu bir altyapının üstünde isteksiz söyleyen bir ses bu sayılarla yakalanmaz.

### 3. Ses doğal mı (vokoder, esnetme, perde düzleme)

| Kayıt | Vokal | Karar | Sözcük hata oranı | Donmuş ünlü | Nota içi oynaklık (cent) | Izgaraya yapışma R | Zarf titremesi dB | Tiz doku | Ünsüzde tiz dB | Aracın işaretleri | DNSMOS | NISQA | Distill | UTMOS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ali-baba/yeni/vokal/ornek_kita1 | **konuşma sentezi + vokoder** | reddetti | %100 | %31 | 9,8 | 0,62 | -19,8 | 2,03 | -9,2 | sesli sürenin %31 kadarı 'donmuş' ünlü | 2,50 | 2,87 | 3,00 | 1,48 |
| ali-baba/yeni2/sarki_birlesik | **esnetilmiş + perdesi düzlenmiş** | reddetti | %48 | %20 | 10,6 | 0,66 | -14,8 | 2,42 | -15,4 | sesli sürenin %20 kadarı 'donmuş' ünlü; ünsüzlerde | 2,39 | 2,76 | 3,19 | 1,34 |
| ali-baba/v2_2 | doğal yapay şarkıcı | beğendi | %5 | %0 | 11,3 | 0,69 | -13,3 | 1,31 | -11,2 | yok | 2,68 | 3,33 | 3,94 | 1,44 |
| ali-baba/dinle_2 | doğal yapay şarkıcı | beğendi | %8 | %0 | 11,1 | 0,67 | -9,1 | 1,42 | -11,1 | yok | 2,71 | 2,88 | 3,41 | 1,49 |
| el-yikama/coskulu_2 | doğal yapay şarkıcı | beğendi | %4 | %0 | 11,8 | 0,63 | -11,7 | 1,16 | -9,5 | yok | 2,45 | 2,67 | 3,19 | 1,31 |
| parmak-ailesi/coskulu_1 | doğal yapay şarkıcı | beğendi | %4 | %0 | 11,5 | 0,68 | -10,8 | 1,49 | -16,1 | ünsüzlerde | 2,47 | 2,31 | 2,98 | 1,52 |
| ali-baba/yeni3/…/dogal-onizleme | doğal (dinle_2'nin vokali, başka orkestrada) | reddetti | %19 | %5 | 14,6 | 0,28 | -14,4 | 2,42 | -16,0 | ünsüzlerde | 2,56 | 2,76 | 2,97 | 1,43 |
| ali-baba/coskulu_2 | doğal yapay şarkıcı | reddetti | %14 | %0 | 12,6 | 0,55 | -12,9 | 1,34 | -12,0 | yok | 2,35 | 2,49 | 2,76 | 1,58 |
| parmak-ailesi/duzgun_1 | doğal yapay şarkıcı | reddetti | %8 | %0 | 9,1 | 0,74 | -12,0 | 1,07 | -14,1 | ünsüzlerde | 2,51 | 1,93 | 3,29 | 1,30 |
| parmak-ailesi/duzgun_2 | doğal yapay şarkıcı | reddetti | %4 | %0 | 11,2 | 0,59 | -12,5 | 1,13 | -10,6 | yok | 2,76 | 3,67 | 3,91 | 1,95 |
| parmak-ailesi/turkce_2 | doğal yapay şarkıcı | reddetti | %10 | %3 | 9,1 | 0,78 | -13,8 | 1,45 | -10,7 | yok | 2,63 | 3,37 | 3,89 | 2,00 |
| parmak-ailesi/yavas_2 | doğal yapay şarkıcı | reddetti | %6 | %19 | 9,9 | 0,74 | -13,5 | 1,28 | -9,8 | sesli sürenin %18 kadarı 'donmuş' ünlü | 2,82 | 3,71 | 3,80 | 2,15 |
| pitirin-ailesi/yavas_2 | doğal yapay şarkıcı | reddetti | %5 | %0 | 9,1 | 0,64 | -13,2 | 1,01 | -11,9 | yok | 2,21 | 1,76 | 2,71 | 1,30 |
| el-yikama/sarki_1 | doğal yapay şarkıcı | reddetti | %0 | %4 | 10,1 | 0,76 | -14,5 | 1,13 | -4,0 | yok | 2,55 | 3,56 | 3,53 | 1,85 |
| parmak-ailesi/sarki_2 | doğal yapay şarkıcı | reddetti | %2 | %0 | 10,3 | 0,75 | -13,6 | 1,11 | -16,2 | ünsüzlerde | 2,50 | 2,29 | 3,12 | 1,50 |
| ali-baba/yeni/demo_altyapi_sesli | vokal yok (çalgısal) | beğendi | – | %26 | 11,3 | 0,15 | -11,1 | 1,60 | -18,0 | sesli sürenin %26 kadarı 'donmuş' ünlü; ünsüzlerde | 2,02 | 1,43 | 1,79 | 1,44 |

Burada üç kayıt **aynı vokalden** geliyor, bu yüzden karşılaştırma temiz: `dinle_2` (özgün, beğenildi), `dogal-onizleme` (aynı vokal hiç işlenmeden başka orkestraya kondu), `sarki_birlesik` (aynı vokal iki katına esnetildi ve perdesi ezgiye çekildi). `ornek_kita1` ise konuşma sentezinin vokoderle ezgiye oturtulmuş hâli.

**Temiz ayıran tek sayı: makine sözleri anlıyor mu.**

- İşlenmemiş 12 yapay şarkıcı kaydında sözcük hata oranı %0,0 … %13,9. Aynı vokal başka orkestrada %19,4. İşlenmiş iki vokalde %48,1 ve %100,0.
- `dinle_2` → `sarki_birlesik`: aynı ses, aynı sözler; esnetme ve perde düzleme hata oranını %8,3'ten %48,1'e çıkarıyor. Scribe "Ali Baba'nın" yerine "Ülke'nin", "dinle bak" yerine "iner ya" duyuyor.
- Scribe'ın emin olmadığı sözcüklerin oranı da aynı yönde (%7 ve %70; doğal kayıtlarda en çok %3,7), ama boşluk dar; eşik önermiyorum.

**Aracın "yapaylık" vekilleri ayırmıyor.**

- **Donmuş ünlü:** işlenmiş iki vokali yakalıyor (%20 ve %31), ama doğal kayıtlardan `parmak-ailesi/yavas_2` (%19) de aynı uyarıyı alıyor. Bunlar yavaş, uzun tutulan notalarla söylenen kayıtlar; uyarı "zaman esnetme / vokoder izlenimi" diyor, oysa ölçtüğü şey uzun tutulan ünlü. Aynı vokalin iki hâli arasında işe yarıyor (`dinle_2` %0 → `sarki_birlesik` %20), tek kayda hüküm olarak yaramıyor.
- **Nota içi oynaklık, ızgaraya yapışma, vibrato:** örtüşüyor. `sarki_birlesik`'in perdesi panoda cetvelle çizilmiş gibi, ama oynaklığı 10,6 cent (doğal kayıtlar 9,1 … 12,6). Ayrılmış kanaldaki artıklar düz perdeye sahte bir titreme ekliyor.
- **"Ünsüzlerde tiz zayıf" uyarısı:** beğenilen `parmak/coskulu_1` de alıyor (-16,1 dB; eşik −14). Yanlış alarm.
- **Tiz doku:** işlenmiş vokallerde yüksek (2,03, 2,42), ama hiç işlenmemiş vokalin başka orkestradaki hâlinde de 2,42. Sesi değil, ayırma artığını ölçüyor.
- **Konuşma-kalitesi tahminleri (DNSMOS, NISQA, Distill-MOS, UTMOS22):** hiç ayırmıyor. İşlenmiş vokaller UTMOS 1,48 ve 1,34; beğenilen dört kayıt 1,31 … 1,52. Üstelik en yüksek UTMOS'u alan dört kayıt (`parmak-ailesi/yavas_2` 2,15, `parmak-ailesi/turkce_2` 2,00, `parmak-ailesi/duzgun_2` 1,95, `el-yikama/sarki_1` 1,85) hepsi reddedilmiş, yavaş dönemin kayıtları: sakin, seyrek altyapılı kayıtta ses "temiz konuşma"ya daha çok benziyor. **Bu puanlar kullanıcının zevkiyle ters düşüyor; iyi/kötü notu olarak kullanılmamalı.**
- CED'in "sentetik şarkı" ve "konuşma sentezleyici" etiketleri: ayırmıyor (sentetik şarkı: işlenmiş vokallerde 0,002 ve 0,021, doğal kayıtlarda 0,011 … 0,054).

Sonuç: araç "bu vokal bozulmuş" yargısını **sözlerin anlaşılmazlığı üzerinden** veriyor, sesin tınısı üzerinden değil. Sözleri anlaşılır kalan ama yapay tınlayan bir vokal bu sayılardan temiz çıkar.

Otomatik ayırmanın payı (aynı kayıt, gerçek kanallarla yeniden):

| Kayıt | Kanallar | Vokal − altyapı dB | En iyi kaydırma | Armonik destek | Destek farkı | Gam içi | Akor sesi | Cent sapma | ±25 cent | Çakışan / uzun | Ritim R | Ritim kayması ms | Donmuş ünlü | Oynaklık (cent) | Izgara R | Zarf dB | UTMOS | NISQA |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ali-baba/dinle_2 | otomatik ayırma (karşılaştırma için: aynı vokalin özgün kaydı) | -3,4 | +0 | 0,65 | +0,26 | %86 | %70 | 8,8 | %88 | 0 / 25 | 0,36 | +26 | %0 | 11,1 | 0,67 | -9,1 | 1,49 | 2,88 |
| ali-baba/yeni3/…/dogal-onizleme | otomatik ayırma | -13,0 | -4 | 0,28 | +0,14 | %91 | %67 | 17,0 | %68 | 4 / 31 | 0,34 | +4 | %5 | 14,6 | 0,28 | -14,4 | 1,43 | 2,76 |
| ali-baba/yeni2/sarki_birlesik | otomatik ayırma | -5,9 | +0 | 0,65 | +0,49 | %99 | %96 | 8,4 | %91 | 3 / 99 | 0,41 | +29 | %20 | 10,6 | 0,66 | -14,8 | 1,34 | 2,76 |
| ali-baba/yeni/vokal/ornek_kita1 | otomatik ayırma | -3,8 | +0 | 0,69 | +0,49 | %95 | %86 | 9,8 | %86 | 2 / 12 | 0,19 | +46 | %31 | 9,8 | 0,62 | -19,8 | 1,48 | 2,87 |
| ali-baba/yeni/vokal/ornek_kita1 | gerçek kanallar (kurucunun raporu) | -2,5 | +0 | 0,69 | +0,50 | %100 | %95 | 8,3 | %99 | 0 / 13 | 0,57 | +44 | %19 | 8,9 | 0,82 | -20,8 | 1,64 | 3,31 |

- **Ön dinleme (işlenmemiş vokal, başka orkestra):** otomatik ayırmada ±25 cent içinde %68, ızgaraya yapışma 0,28, vokal − altyapı -13,0 dB çıkmıştı. Gerçek kanallarla %–, – ve – dB. Yani "detone" ve "gömük" görünen vokal aslında öyle değil; ayırıcı bu karışımda vokali temiz çıkaramamış (klarnet ezgisi ve hayvan sesleri vokal kanalına sızmış).
- **Aynı kayıtta armoni:** gerçek kanallarla en iyi kaydırma –, armonik destek –, akor sesi –, gam içi –.
- **Esnetilmiş vokal (`sarki_birlesik`):** gerçek kanalla donmuş ünlü – (ayırmayla %20), nota içi oynaklık – cent (ayırmayla 10,6), ızgaraya yapışma – (ayırmayla 0,66). 
- **Vokoder vokali (`ornek_kita1`, kurucunun eski ölçümü):** gerçek kanalla ızgaraya yapışma 0,82 (ayırmayla 0,62), ±25 cent içinde %99 (ayırmayla %86), ritim R 0,57 (ayırmayla 0,19). Ayırma, yapaylığın en belirgin izini (perdenin ızgaraya aşırı yapışması) siliyor ve ritmi bozuk gösteriyor.

Çıkarım: **kendi ürettiğimiz kayıtlarda kanallar zaten elimizde; `--ayir` yerine `--vokal/--altyapi` kullanılmalı.** Otomatik ayırma hem yapaylık izlerini bulandırıyor hem de sahte "detone / gömük" uyarıları üretiyor.

### 4. Vokal orkestrayla uyumlu mu

| Kayıt | Karar | En iyi kaydırma (0 olmalı) | Armonik destek (kaydırmasız) | Destek farkı | Gam içi | ±25 cent içinde | Cent sapma | Çakışan / uzun nota | Ritim R | Vokal − altyapı dB | Sızıntı dB | Aracın 'aynı armonide mi' satırı |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ali-baba/yeni3/…/dogal-onizleme | reddetti | -4 | 0,28 | +0,14 | %91 | %68 | 17,0 | 4 / 31 | 0,34 | -13,0 | -15 | sorun |
| ali-baba/v2_2 | beğendi | +0 | 0,57 | +0,31 | %100 | %91 | 8,1 | 0 / 40 | 0,57 | +0,8 | -46 | iyi |
| ali-baba/dinle_2 | beğendi | +0 | 0,65 | +0,26 | %86 (ton belirsiz) | %88 | 8,8 | 0 / 25 | 0,36 | -3,4 | -21 | iyi |
| el-yikama/coskulu_2 | beğendi | -4 | 0,34 | +0,13 | %100 | %87 | 8,6 | 1 / 24 | 0,43 | -2,6 | -17 | sorun |
| parmak-ailesi/coskulu_1 | beğendi | +0 | 0,56 | +0,27 | %100 | %92 | 9,2 | 0 / 13 | 0,39 | -1,6 | -21 | iyi |
| ali-baba/yeni/vokal/ornek_kita1 | reddetti | +0 | 0,69 | +0,49 | %95 | %86 | 9,8 | 2 / 12 | 0,19 | -3,8 | -44 | iyi |
| ali-baba/yeni2/sarki_birlesik | reddetti | +0 | 0,65 | +0,49 | %99 | %91 | 8,4 | 3 / 99 | 0,41 | -5,9 | -13 | iyi |
| ali-baba/coskulu_2 | reddetti | -4 | 0,35 | +0,12 | %99 | %83 | 11,2 | 0 / 24 | 0,37 | -4,3 | -40 | sorun |
| parmak-ailesi/duzgun_1 | reddetti | +0 | 0,37 | +0,28 | %90 (ton belirsiz) | %94 | 7,1 | 8 / 59 | 0,72 | +4,4 | -51 | iyi |
| parmak-ailesi/duzgun_2 | reddetti | +5 | 0,27 | +0,19 | %98 | %85 | 8,5 | 0 / 30 | 0,64 | +4,7 | -15 | dikkat |
| parmak-ailesi/turkce_2 | reddetti | +5 | 0,21 | +0,07 | %83 (ton belirsiz) | %94 | 5,4 | 0 / 35 | 0,48 | +1,7 | -48 | dikkat |
| parmak-ailesi/yavas_2 | reddetti | +5 | 0,39 | +0,31 | %99 | %92 | 6,6 | 0 / 40 | 0,49 | +5,7 | -49 | dikkat |
| pitirin-ailesi/yavas_2 | reddetti | +0 | 0,59 | +0,51 | %99 | %87 | 9,6 | 0 / 41 | 0,14 | +2,7 | -23 | iyi |
| el-yikama/sarki_1 | reddetti | +0 | 0,37 | +0,17 | %100 | %94 | 6,3 | 1 / 49 | 0,07 | +1,2 | -52 | iyi |
| parmak-ailesi/sarki_2 | reddetti | +0 | 0,61 | +0,37 | %100 | %94 | 8,0 | 0 / 8 | 0,45 | -0,1 | -42 | iyi |
| ali-baba/yeni/demo_altyapi_sesli | beğendi | +0 | 0,55 | +0,30 | %79 | %52 | 23,7 | 3 / 7 | 0,43 | +9,4 | -16 | iyi |

Reddedilen ön dinlemede vokal, beğenilen `dinle_2`'nin vokalinin **hiç işlenmemiş** hâli; değişen yalnızca orkestra. Yani bu çift, "vokal iyi ama orkestrayla olmamış" yargısı için neredeyse deney gibi.

**Yan yana (aynı vokal, iki orkestra) fark çok açık:**

| | `dinle_2` (beğenildi) | ön dinleme ("olmamış") |
|---|---|---|
| Vokalin söylediği seste orkestranın enerjisi (armonik destek) | 0,65 | 0,28 |
| En iyi kaydırma (0 olmalı) | +0 | -4 |
| Vokal − altyapı | -3,4 dB | -13,0 dB |
| ±25 cent içinde | %88 | %68 |
| Sözcük hata oranı | %8,3 | %19,4 ("Ali Baba'nın" → "Anne babamın") |

**Tek kayda bakınca aracın armoni hükmü tutmuyor:**

- "En iyi kaydırma 0 olmalı" denetimi ön dinlemeye **sorun** diyor (-4). Ama beğenilen `el-yikama/coskulu_2` de aynı sonucu alıyor (-4; destek 0,34). En iyi kaydırması 0 olmayan başka kayıtlar da var: `ali-baba/coskulu_2` (-4), `parmak-ailesi/duzgun_2` (+5), `parmak-ailesi/turkce_2` (+5), `parmak-ailesi/yavas_2` (+5).
- Nedeni: ölçü, vokalin söylediği seste orkestranın ne kadar enerjisi olduğuna bakıyor. Vokal akorun üçlüsünde ya da beşlisinde duruyorsa (kök ses yerine), tamamen uyumlu olsa bile "kaydırsak daha iyi" çıkıyor.
- "Gam içi söyleme" ön dinlemede %91 ile **iyi** diyor; armoni kuramı açısından vokal gerçekten gamın içinde. Kullanıcının "olmamış" dediği şey kuramsal uyumsuzluk değil.

**Ön dinlemeyi öteki 14 vokalli kayıttan ayıran sayılar var, ama armoni sayıları değil:**

- ±25 cent içinde: ön dinleme %68, öteki 14 kayıt %83 … %94.
- ızgaraya yapışma R: ön dinleme 0,28, öteki 14 kayıt 0,55 … 0,78.
- vokal − altyapı dB: ön dinleme -13,0, öteki 14 kayıt -5,9 … +5,7.
- CED'in vokal kanalına "konuşma" demesi: ön dinleme 0,43, öteki 14 kayıt 0,01 … 0,29.

Bunların hepsi aynı şeyi söylüyor: **ayırıcı bu karışımdan temiz bir vokal çıkaramıyor.** Gerçek kanallarla ölçünce (yukarıdaki tablo) vokalin kendisi sağlam. Demek ki aracın yakaladığı şey dolaylı bir belirti: vokalin yerinde, onunla yarışan başka bir ezgi sesi var (vokalin altına konan klarnet) ve makine ikisini ayıramıyor. Bu, kullanıcının "altta başka ezgi çalıyor, olmamış" demesiyle uyumlu; ama tek örnek.

Ritim ölçüsü bu boyutta işe yaramadı: ön dinleme R 0,34, beğenilen `dinle_2` 0,36. Ritmi için hiçbir şikâyet olmayan `el-yikama/sarki_1` 0,07, `pitirin-ailesi/yavas_2` 0,14 çıktı (vuruş ızgarası yanlış bulunmuş olmalı).

### 5. Aksan: "Türkçe konuşan bir İngiliz gibi"

| Kayıt | Karar ve gerekçe | Sözcük hata oranı | Scribe ortalama logprob | Hece/sn | 'buradayım' süresi (sn) | 'parmak' r vekili (dB) | 'buradayım' son ünlü vekili (dB) | DNSMOS | NISQA | UTMOS |
|---|---|---|---|---|---|---|---|---|---|---|
| parmak-ailesi/coskulu_1 | beğendi: seçilen kayıt | %4 | -0,004 | 4,6 | 0,52 | +4,7 | +12,5 | 2,47 | 2,31 | 1,52 |
| parmak-ailesi/duzgun_1 | reddetti: **'İngiliz gibi'** | %8 | yok (eski döküm) | 2,4 | 1,44 | +5,1 | +3,9 | 2,51 | 1,93 | 1,30 |
| parmak-ailesi/duzgun_2 | reddetti: **'İngiliz gibi'** | %4 | -0,007 | 2,6 | 1,42 | +2,7 | +0,3 | 2,76 | 3,67 | 1,95 |
| parmak-ailesi/turkce_2 | reddetti: sözler yanlış | %10 | -0,010 | 3,4 | 1,03 | +5,3 | -9,1 | 2,63 | 3,37 | 2,00 |
| parmak-ailesi/yavas_2 | reddetti: sözler yanlış + ninni | %6 | yok (eski döküm) | 3,0 | 1,06 | +2,7 | +16,1 | 2,82 | 3,71 | 2,15 |
| parmak-ailesi/sarki_2 | reddetti: çok hızlı | %2 | yok (eski döküm) | 4,8 | 0,55 | +4,6 | +7,8 | 2,50 | 2,29 | 1,50 |

Altı Parmak Ailesi kaydı aynı sözleri söylüyor; ikisi (`duzgun_1`, `duzgun_2`) "Türkçe konuşan bir İngiliz gibi" diye reddedildi. **Hiçbir sayı bu ikisini ötekilerden ayırmıyor:**

- **Sözcük hata oranı:** aksanlı iki kayıt %4 … %8; öteki dördü %2 … %10. Scribe aksanlı söyleneni de doğru yazıyor.
- **Scribe'ın güveni:** `duzgun_2` ortalama logprob -0,007; seçilen kayıt -0,004. Fark yok. Dil olasılığı, bu çalışmada dökümü alınan kayıtların hepsinde 1,00 (Türkçe).
- **Kalite tahminleri:** aksanlı iki kayıt birbirine bile benzemiyor (NISQA 1,93 ve 3,67).
- **İki fonetik deney** (araç dışı; aynı sözcükler kayıtlar arasında karşılaştırıldı): "parmak"taki r'nin İngiliz r'sine benzeyip benzemediği (aksanlılar +2,7 … +5,1 dB, ötekiler +2,7 … +5,3 dB) ve "buradayım"ın son ünlüsünün "ı" mı "i" mi olduğu (aksanlılar +0,3 … +3,9 dB, ötekiler -9,1 … +16,1 dB). İkisinde de aksanlı kayıtlar ötekilerin aralığının içinde. Ayrıca ikinci ölçü sözcüğün süresinden etkileniyor; güvenilmez.
- **Ortak ölçülebilir tek özellik yavaşlık:** "buradayım" sözcüğü aksanlı iki kayıtta 1,42 … 1,44 sn sürüyor, öteki dördünde 0,52 … 1,06 sn; hece hızı da en düşük ikisi (2,4 … 2,6/sn). Bu bir tempo ölçüsü; yavaş ama düzgün Türkçeyle söylenen bir kayıt da aynı sayıyı verir. **Aksan dedektörü olarak önermiyorum.**
- `duzgun_1`'de bir "Merhaba" dökümde "Merengim" çıktı. Bozuk telaffuzun izi olabilir; ama tek sözcük ve `duzgun_2`'de böyle bir şey yok.

**Gemini'nin "TELAFFUZ" satırı denenmedi.** Araçta hazır (`gemini_dinle.py dinle <dosya>`), ama bu çalışmada canlı istek göndermedim. Sınamak için üç istek yeter: `duzgun_1`, `duzgun_2` ve `coskulu_1`. Önbellekteki eski cevaplar temkinli olmayı gerektiriyor: aynı iki kayıt sırası değiştirilip iki kez sorulduğunda (yeni45 / eski41) altı maddenin altısında da iki seferde **"B"**, yani sonra çalınan kazanmış. Tek yönlü A/B cevabı kanıt sayılmamalı.

Sonuç: **aksan için tek hakem hâlâ kullanıcının kulağı.** Araç bu konuda "sorun yok" derse bu hiçbir şey ifade etmez.

### 6. Söyleyiş hızı

| Kayıt | Karar ve gerekçe | Süre (sn) | Kıtadan kıtaya ortalama süre (sn) | Hece/sn (söz içi) | Hece/sn (öbek medyanı) | En hızlı öbek | Aracın 'söyleyiş hızı' satırı |
|---|---|---|---|---|---|---|---|
| parmak-ailesi/coskulu_1 | beğendi | 80 | 12,9 | 5,4 | 4,6 | 6,6 | dikkat |
| parmak-ailesi/duzgun_1 | reddetti | 91 | 16,6 | 2,7 | 2,4 | 3,0 | bilgi |
| parmak-ailesi/duzgun_2 | reddetti | 95 | 16,6 | 3,1 | 2,6 | 3,1 | bilgi |
| parmak-ailesi/turkce_2 | reddetti | 95 | 15,4 | 3,7 | 3,4 | 3,9 | bilgi |
| parmak-ailesi/yavas_2 | reddetti | 95 | 15,4 | 3,4 | 3,0 | 3,6 | bilgi |
| parmak-ailesi/sarki_2 | reddetti: **'sözler çok hızlı geçiyor'** | 65 | 10,2 | 5,2 | 4,8 | 4,9 | bilgi |

- `sarki_2` ("sözler çok hızlı geçiyor") altı kaydın en hızlısı: öbek medyanı 4,8 hece/sn, kıtadan kıtaya 10,2 sn, toplam 65 sn.
- Ama **seçilen** `coskulu_1` hemen yanında: 4,6 hece/sn, 12,9 sn. Aradaki 0,2 hece/sn'lik fark, sözcük zamanlarının ±50 ms belirsizliği kadar. Söz içi hızda seçilen kayıt daha bile hızlı (5,4 karşısında 5,2).
- Aracın "söyleyiş hızı" uyarısı ters çalışıyor: uyarıyı beğenilen `coskulu_1` alıyor (bir saniyelik "Buradayım, merhaba" parçası 6,6 hece/sn çıktığı için), reddedilen `sarki_2` almıyor.
- Görünen tek fark nefes payı: `sarki_2`'de soru ve cevap tek solukta söyleniyor ve kıtalar 10 saniyede bir geliyor; `coskulu_1`'de son iki kıtada soruyla cevap arasında bir saniyelik ara var ve kıtalar 13 saniyede bir geliyor.

**Eşik önermiyorum.** Kullanıcının kabul ettiği en hızlı kayıt ile reddettiği kayıt arasında ölçülebilir boşluk yok. Hece hızı iki sürümü sıralamaya yarar, "çok hızlı" hükmü vermeye yaramaz.

### 7. Süre

"Çok uzun" denen iki kayıt 186 sn; kabul edilen dört şarkı 70 … 110 sn; "olmuş" denen yedi kıtalık altyapı 155 sn. Arada temiz boşluk var (155 ile 186 sn arası). Doğrudan ölçüm; araç süreyi yazıyor ama uyarı vermiyor.

### 8. Ezgi bilinen ezgi mi

Kullanıcı `v2_2` ve `dinle_2` için "ezgi bilinen Ali Baba ezgisi değil" dedi. **Araç bunu ölçmüyor;** yalnızca vokalin kendi orkestrasıyla uyumuna bakıyor, ve ikisi de kendi orkestrasıyla uyumlu çıkıyor.

Tek dolaylı ipucu: `v2_2`'nin altyapı tonu **Re minör (D minor)** bulundu. Bilinen ezgi majör; ton doğru bulunduysa bu kayıt o ezgi olamaz (ama ton bulma majör / minör ayrımında yanılabiliyor). `dinle_2`'de ton belirsiz çıktığı için aynı ipucu yok. Gerçek denetim için vokalin nota dizisini bilinen ezginin notalarıyla karşılaştırmak gerekir; notalar depoda hazır (`ali-baba/yeni3/altyapi/zaman_dogal.json` içinde `ezgi_notalari`), araçta böyle bir adım yok.

## Önerilen karar eşikleri (yalnızca boşluğun temiz olduğu yerlerde)

| Boyut | Kural | Dayanak | Örnek sayısı (olumlu + olumsuz) | Not |
|---|---|---|---|---|
| Enerji | MusicCoCa coşku farkı **≥ +0,09 → coşkulu yanda**; **≤ -0,04 → ninni yanında**; arası kararsız | coşkulu denen 3 kayıt +0,09 … +0,26; ninni denen 3 kayıt -0,09 … -0,04 | 3 + 3 | `v2_2` (+0,01) arada kalıyor |
| Enerji | CED "ninni" olasılığı **≥ 0,01 → ninni yanına kayıyor** (boşluğun ortası; ninni denenlerin hepsi ≥ 0,023, coşkulu denenlerin hepsi 0,000) | coşkulu 0,000; ninni 0,023 … 0,044 | 3 + 3 | iki gösterge birlikte aynı yanı gösteriyorsa güvenilir; biri yetmez |
| Sözler | Her kıtanın anahtar sözcüğü (aile adı, hayvan adı, söylenen hayvan sesi) beklenenle aynı değilse **ele** | kullanıcının söylediği yanlış ad hatalarının ikisi de bu yolla bulundu; sözcük hata oranı ayırmıyor | 2 + 3 | eşik değil, kural; tek hecelik seslerde döküm yanılabiliyor |
| Anlaşılırlık (işlenmiş vokal) | Sözcük hata oranı **≥ %30 → makine sözleri anlamıyor**, vokal bozulmuş olabilir | işlenmemiş kayıtlar en çok %13,9; aynı vokal başka orkestrada %19,4; işlenmiş iki vokal %48,1 ve %100,0 | 12 + 2 | %30, %19 ile %48 arasındaki boşluğun içinde bir değer; altında kalmak "doğal" demek değil |
| Süre | **180 sn'den uzun → "çok uzun" uyarısı** | reddedilen 186 sn; kabul edilen en uzun 155 sn | 5 + 2 | kullanıcının sözü: "3-3,5 dakika çok uzun" |
| Uyum (geçici, tek örnek) | `--ayir` sonrası **vokal − altyapı < −8 dB** ve **±25 cent içinde < %75** birlikteyse: vokal karışımda kayboluyor, kullanıcıya göndermeden önce bak | ön dinleme -13,0 dB ve %68; öteki vokalli kayıtlar en kötü -5,9 dB ve %83 | 14 + 1 | **tek olumsuz örnek**; armoniyi değil ayırıcının zorlanmasını ölçüyor |

**Eşik önermediğim yerler** (boşluk temiz değil): hareketlilik puanı; küçük sözcük hata oranları (%30'un altı); donmuş ünlü oranı ve öteki yapaylık vekilleri; konuşma-kalitesi tahminleri; armonik destek ve "en iyi kaydırma"; ritim sıkılığı; hece hızı; aksanla ilgili her şey.

## Aracın kendi özet satırları ne dedi

✓ iyi · ! dikkat · ✗ sorun · · yorum yok

| Kayıt | Karar | Enerji | Denge | Armoni | Gam içi | Akort | Çakışan nota | Ritim | Yapaylık | Sözler | Hız | ! ve ✗ sayısı |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ali-baba/v2_2 | beğendi | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | · | 0 |
| ali-baba/dinle_2 | beğendi | ✓ | ✓ | ✓ | · | ✓ | ✓ | ! | · | ! | · | 2 |
| el-yikama/coskulu_2 | beğendi | ✓ | ✓ | ✗ | ✓ | ✓ | ! | ! | · | ✓ | · | 3 |
| parmak-ailesi/coskulu_1 | beğendi | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ! | ! | ✓ | ! | 3 |
| ali-baba/yeni/demo_altyapi_sesli | beğendi | · | ! | ✓ | ! | ! | ✗ | ! | ! | – | – | 6 |
| ali-baba/yeni/vokal/ornek_kita1 | reddetti | ! | ✓ | ✓ | ✓ | ✓ | ! | ✗ | ! | ✗ | · | 5 |
| ali-baba/yeni2/sarki_birlesik | reddetti | · | ✓ | ✓ | ✓ | ✓ | ! | ! | ! | ✗ | ! | 5 |
| ali-baba/yeni3/…/dogal-onizleme | reddetti | ! | ! | ✗ | ✓ | ! | ✗ | ! | ! | ✗ | · | 8 |
| ali-baba/coskulu_2 | reddetti | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ! | · | ! | · | 3 |
| parmak-ailesi/duzgun_1 | reddetti | ! | ✓ | ✓ | · | ✓ | ✗ | ✓ | ! | ! | · | 4 |
| parmak-ailesi/duzgun_2 | reddetti | ! | ✓ | ! | ✓ | ✓ | ✓ | ✓ | · | ✓ | · | 2 |
| parmak-ailesi/turkce_2 | reddetti | ! | ✓ | ! | · | ✓ | ✓ | ! | · | ! | · | 4 |
| parmak-ailesi/yavas_2 | reddetti | ! | ✓ | ! | ✓ | ✓ | ✓ | ! | ! | ! | · | 5 |
| pitirin-ailesi/yavas_2 | reddetti | ! | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | · | ! | · | 3 |
| el-yikama/sarki_1 | reddetti | ! | ✓ | ✓ | ✓ | ✓ | ! | ✗ | · | ✓ | · | 3 |
| parmak-ailesi/sarki_2 | reddetti | · | ✓ | ✓ | ✓ | ✓ | ✓ | ! | ! | ✓ | · | 2 |

- **Uyarı sayısı bir kalite notu değil.** Beğenilen dört şarkıda 0 ile 3 arası uyarı var; reddedilen on iki kayıtta 2 ile 8 arası. Örtüşüyor: aksan yüzünden reddedilen `duzgun_2` 2 uyarıyla, seçilen `parmak/coskulu_1` 3 uyarıyla çıkıyor.
- **Beğenilen kayıtlarda yanlış alarmlar:** `el-yikama/coskulu_2`'de "aynı armonide mi: sorun"; `parmak/coskulu_1`'de "ünsüzlerde tiz zayıf" ve "söyleyiş hızı"; üç beğenilen kayıtta "ritme oturma: dikkat" (R 0,36 … 0,43).
- **Doğru yerde öten satırlar:** "Sözler" (işlenmiş iki vokalde ve ön dinlemede ✗), "Enerji" (ninni denen üç kayıtta !), "Vokal / altyapı dengesi" ve "Akort" (vokalli kayıtlar içinde yalnızca ön dinlemede).
- Beğenilen çalgısal altyapı (`demo_altyapi_sesli`) 6 uyarı alıyor; hepsi hayvan seslerinin vokal sanılmasından.
- **Hiç işe yaramayan satır:** "Ritme oturma". Beğenilen ve reddedilen kayıtlar arasında R değerleri tamamen karışık; ritmi için şikâyet olmayan iki kayıtta R 0,07 ve 0,14 çıktı.

## Panolara bakınca: resim, sayının söylemediğini söylüyor mu?

Dokuz kaydın panolarına Read aracıyla baktım (dört beğenilen: `v2_2`, `dinle_2`, `parmak/coskulu_1`, `demo_altyapi_sesli`; beş reddedilen: `ornek_kita1`, `sarki_birlesik`, `dogal-onizleme`, `duzgun_1`, `parmak/yavas_2`). Resim, özet sayıların söylemediği dört şeyi gösterdi:

1. **Merdiven gibi perde (`sarki_birlesik`, perde panosu).** Vokal çizgisi cetvelle çizilmiş yatay çubuklar; notadan notaya dik basamakla iniyor; birkaç hece tek düz çizginin üstünde. Aynı vokalin özgün hâlinde (`dinle_2`) çizgi kıvrımlı, notalar kısa, geçişler eğik. Sayılar bunu kaçırdı (nota içi oynaklık 10,6 cent, "çok düz" uyarısı yok); göz hemen görüyor. `ornek_kita1`'de aynı görüntü var: düz çubuklar, aralarında geçiş yok.
2. **Vokal orkestranın boş bıraktığı seste (`dogal-onizleme`, perde panosunun en alt şeridi).** Mavi noktalar (vokalin söylediği ses: Mi) beyaz, boş bir satırda duruyor; orkestranın koyu şeritleri Do, Sol ve Fa'da. `dinle_2`'de aynı mavi noktalar koyu bir şeridin tam üstünde. Özet satırı "gam içi %91, iyi" diyordu; resim "şarkıcı orkestranın çalmadığı yerde söylüyor" diyor. Üst şeritte bir şey daha görünüyor: `dinle_2`'de orkestra tek akorda duruyor, ön dinlemede her ölçüde akor değişiyor ama vokal hep aynı seste kalıyor.
3. **"Çakışan nota" dediği şey hayvan sesi (`ornek_kita1`, `dogal-onizleme`, `sarki_birlesik`).** Genel panoda turuncu "[inek sesi]" şeridinin altında, aşağı doğru kayan geniş bir harmonik yığını var; perde panosunda tam orada pes, −40 centlik kırmızı X'li iki "nota". Araç ineği detone şarkıcı sanıyor. Sayıya bakınca "2 çakışan nota" bir vokal kusuru gibi; resme bakınca değil. Çalgısal `demo_altyapi_sesli`'nin genel bakışında "vokal var" şeridi yalnızca yedi hayvan sesinin olduğu yerde dolu: dosyada şarkıcı olmadığı bir bakışta anlaşılıyor, oysa özet tablosu bu dosyaya da akort ve yapaylık uyarıları yazıyor.
4. **Ninni ile coşkulu arasındaki fark tek bakışta (`parmak/yavas_2` karşısında `parmak/coskulu_1`, genel bakış).** MusicCoCa çubukları birinde baştan sona kırmızı (eksi), ötekinde baştan sona mavi. Spektrogramda coşkulu kayıt baştan aşağı sık dikey çizgilerle dolu (vurmalılar); ninni gibi olanda yatay bantlar ve altta toplanmış enerji var. Düzey şeridinde ninni kaydında altyapı vokal girince geri çekiliyor. `yavas_2`'nin "donmuş ünlü" satırındaki 11 kırmızı işaret her dizenin sonuna düzenli diziliyor: bunlar işlem artığı değil, uzatılan dize sonları.

Resmin **göstermediği**: aksan. `duzgun_1` ile `coskulu_1`'in panoları yan yana konunca görülen tek fark, `duzgun_1`'de sözcüklerin iki üç kat uzun, kaygan ve ünsüzlerin silik olması; bu yavaş söyleyişin resmi, aksanın değil. "atıları" gibi tek hecelik bir bozukluk da panoda seçilmiyor.

Sonuç: **görsel kanal gerçek bilgi ekliyor**, özellikle doğallık ve uyum boyutlarında, yani sayıların en zayıf olduğu yerde. Her yeni kayıtta en az bir perde panosuna bakmak, "yapaylık işareti yok" satırına güvenmekten iyidir.

## Araçta görülen kusurlar (araca dokunulmadı; kurucusuna not)

| Konu | Görülen | Öneri |
|---|---|---|
| Enerji özet satırı | "ninni/sakin" uyarısı hareketlilik puanı < 62 olunca tek başına ötüyor; MusicCoCa'sı açıkça artı olan kayıtlarda yanlış uyarı (`ornek_kita1`, `dogal_onizleme`). | Uyarıyı MusicCoCa < 0 ya da CED ninni ≥ 0,02 koşuluna bağlamak; puanı yalnızca bilgi olarak yazmak. |
| Hayvan sesleri vokal sanılıyor | Ayırıcı gerçek hayvan seslerini vokal kanalına koyuyor; araç bunları nota sayıp "çakışan / detone nota" ve geniş ses aralığı raporluyor. `ornek_kita1`'de işaretlenen 2 notanın 2'si, `sarki_birlesik`'te 3'ün 3'ü Scribe'ın hayvan sesi aralığının içinde; `dogal-onizleme`'de 4'ün en az 2'si (öteki ikisi horoz sesinin yerinde). Çalgısal `demo_altyapi_sesli`'de bütün "vokal" ölçümleri (donmuş ünlü %26, 3 çakışan nota) hayvan sesi. | Scribe'ın ses olayı aralıklarını ([inek sesi] …) ya da CED'in hayvan pencerelerini nota analizinden çıkarmak; vokalsiz dosyada vokal bölümlerini hiç yazmamak. |
| "Aynı armonide mi" denetimi | Beğenilen `el-yikama/coskulu_2`'ye "sorun" diyor (en iyi kaydırma -4). Vokal akorun kökünde değil üçlüsünde / beşlisinde durunca yanlış alarm. | Hükmü kaydırma sırasına değil, akor sesi oranına ve gam dışı orana bağlamak; ya da yalnızca ±1, ±2, ±6 kaydırmayı sorun saymak (şimdi −4 de sorun sayılıyor). |
| Ton belirsizken de çakışan nota hükmü | `duzgun_1`'de 8 uzun nota işaretlendi (6'sı "gam dışı" Fa); araç aynı raporda tonun belirsiz olduğunu (Sol majör?) söylüyor, vokalin kendi dağılımı Do majör gösteriyor. Hüküm "sorun" çıkıyor. | Ton belirsizse "gam dışı" notaları hükme katmamak (gam içi oranında olduğu gibi). |
| Donmuş ünlü uyarısı | Doğal ama yavaş söylenen kayıtlarda ötüyor (`parmak-ailesi/yavas_2` %19). Metni "zaman esnetme / vokoder izlenimi" diyor. | Eşiği hece hızına göre ayarlamak ya da metni "uzun tutulan ünlüler" diye yumuşatmak. |
| "Ünsüzlerde tiz zayıf" uyarısı | −14 dB eşiği doğal kayıtların ortasında: beğenilen `parmak/coskulu_1` -16,1 dB. | Eşiği düşürmek ya da uyarıyı kaldırmak. |
| Söyleyiş hızı uyarısı | Tek bir bir saniyelik öbek 6,5 hece/sn'yi geçince bütün kayda "dikkat" diyor; beğenilen kayıt uyarı alıyor, "çok hızlı" denen almıyor. | En hızlı tek öbek yerine medyanı ve kıta aralığını kullanmak. |
| Ritim satırındaki "tavan ≈ 0,65" | Gerçek kayıtlarda R 0,72 ölçüldü; 0,65 tavan değil. Ayrıca doğal bir kayıtta R 0,07 (ızgara yanlış bulunmuş). | Metni düzeltmek; otomatik ızgarada R'yi hüküm olarak değil bilgi olarak vermek. |
| Eski döküm verilemiyor | Elde `*_words.json` varken aracı yeniden kredi harcamadan çalıştırmanın yolu yok; sarıcı yazmak gerekti. | `--dokum-dosyasi` seçeneği. |
| Varsayılan çıktı klasörü çakışıyor | Klasör adı yalnızca dosya adından geliyor: `ali-baba/coskulu_1.mp3` ile `parmak-ailesi/coskulu_1.mp3` aynı `raporlar/coskulu_1/` klasörüne yazar. | Klasör adına üst klasörü ya da dosya özetini eklemek. |
| Kanal ayırma hep 0. ve 1. çekirdekte | Aynı anda çalışan bütün dinle.py kopyaları aynı iki çekirdeğe sabitleniyor; bu çalışmada ayırma, öteki ekiplerle çakıştığı için beklenenin 2-3 katı sürdü (155 sn'lik şarkı 397 sn). | Çekirdek seçimini ortam değişkenine bağlamak. |
| Beklenen sözlerdeki [hayvan sesi] etiketleri kullanılmıyor | Scribe gerçek hayvan seslerini adıyla etiketliyor ([inek sesi], [koyun sesi] …; ön dinlemede yedisi de doğru sırada), ama araç bunları beklenenle karşılaştırmıyor. | Söz dosyasındaki köşeli etiketleri Scribe'ın ses olaylarıyla sırayla eşleştirmek. Dikkat: `sarki_birlesik`'te Scribe sözleri yanlış duyunca kediyi "[tilki sesi]" diye etiketledi; etiket sözlerden bağımsız değil. |

## Bu çalışmanın sınırları

- **Örnek çok küçük.** 17 kayıt; boyut başına 1 ile 6 arası etiket. "Temiz boşluk" iki üç noktanın arasındaki boşluktur; bir sonraki kayıt onu kapatabilir.
- **Etiketler özet.** Kullanıcının sözleri bana tek cümlelik özetler olarak geldi. Bir kayıt birden çok nedenle reddedilmiş olabilir (`duzgun_1` hem aksanlı hem yavaş hem söz hatalı); hangisinin belirleyici olduğunu bilmiyorum.
- **Beğenilen kayıt kusursuz kayıt değil.** `v2_2` beğenildi ama söz hatalı; `dinle_2` beğenildi ama bir kıtada yanlış hayvan var. "Olumlu" grup, o boyutta şikâyet edilmeyen kayıtlar demek.
- **Beklenen sözler yeniden kuruldu** (üretim istemleri depoda yok); sözcük hata oranları birkaç puan oynayabilir.
- **Yedi kayıtta eski döküm kullanıldı**; bunlarda Scribe'ın sözcük güveni yok. Aksanla reddedilen `duzgun_1` bunlardan biri.
- **Bütün vokaller otomatik ayırmayla elde edildi.** Ayırma kendi artıklarını ekliyor; gerçek kanallarla ölçüm iki kayıtta bunu gösterdi. Perde, akort ve yapaylık sayıları "ayrılmış vokal" için geçerlidir.
- **Bütün doğal vokaller aynı tür yapay şarkıcıdan.** Gerçek bir insan şarkıcının ya da başka bir üreticinin kaydında sayılar başka yerde durabilir.
- **Ben hiçbir kaydı duymadım.** Bu rapor, makinelerin ürettiği sayıların ve resimlerin kullanıcının sözleriyle karşılaştırmasıdır.

## Bundan sonra ne işe yarar

1. **Her yeni kullanıcı kararını bu kümeye ekle.** `kod/set.py`'ye bir satır, sonra `02` ve `05`…`11` betikleri: tablolar ve eşikler kendiliğinden güncellenir. Kalibrasyonu güçlendirecek tek şey daha çok etiket.
2. **Kullanıcıya göndermeden önce sıra:** (1) kıta kıta anahtar sözcük denetimi, (2) MusicCoCa + CED ninni, (3) süre, (4) bir perde panosuna göz at, (5) önceki beğenilen kayıtla yan yana ölç. Aksan ve "hoş mu" için kullanıcının kulağı.
3. **Kendi ürettiğimiz karışımlarda `--vokal/--altyapi` kullan**, `--ayir` değil.
4. **Gemini'nin telaffuz satırını sına** (izin verilirse üç istek: `duzgun_1`, `duzgun_2`, `coskulu_1`). Aksanı yakalıyorsa araçtaki tek aksan göstergesi olur; yakalamıyorsa o satır rapordan çıkarılmalı.
5. **Ezgi karşılaştırması ekle:** vokalin nota dizisini bilinen ezginin notalarıyla hizalayan bir adım. Kullanıcının iki kayıtta söylediği şikâyeti şu an hiçbir şey ölçmüyor.
6. **Kullanıcının beğendiği gerçek Türkçe çocuk şarkıları** (3-5 tane) referans olarak eklenirse, "doğal ses" ve "doğru aksan" için ilk kez olumlu bir ölçüt olur.

## Dosyalar

| Yer | İçerik |
|---|---|
| `kalibrasyon/kalibrasyon.md`, `kalibrasyon.json` | bu rapor ve makinece okunur özeti |
| `kalibrasyon/raporlar/<kayıt>/` | her kayıt için `rapor.md`, `rapor.json` ve PNG panolar (`…__gercek_kanallar` = gerçek kanallarla ikinci ölçüm) |
| `kalibrasyon/sozler/` | yeniden kurulan beklenen sözler |
| `kalibrasyon/ara/` | toplanan sayılar: `olcumler.json`, `ayrisma.json`, `soz_denetimi.json`, `unlu_tinisi.json`, `aksan_deneyi.json`, `gercek_kanallar.json` |
| `kalibrasyon/kod/` | çalıştırılan betikler (`set.py` kayıt listesi; `01`…`11` sırayla) |
| `kalibrasyon/gunluk/` | çalışma günlükleri |
| `dinleme/onbellek/` | bu çalışmada alınan 8 Scribe dökümü ve kredi defteri |

