# Dinleme takımının sınanması: kusurları fark ediyor mu?

_21 Kasım 2026. Sınanan araç: `dinleme/arac/dinle.py` 1.0. Araç klasörüne dokunulmadı._

## Sonuç

Kabul edilmiş bir kayda (Ali Baba, `dinle_2.mp3`) kodla, her seferinde **tek** bir kusur eklendi ve araç o dosyada çalıştırıldı.
İstenen 14 bozuk sürümden:

- **6'sında araç kendiliğinden uyardı** (raporu tek başına okuyan biri kusuru görür): 50 ve 100 cent detone vokal, hece başına düzleştirilmiş perde, 6 dB kısık vokal, yanlış söylenen satır, 4 kHz'de kesilmiş boğuk ses.
- **6'sında araç uyarmadı ama bir sayı oynadı** (yalnız iyi sürümle yan yana ölçülünce görülür): çeyrek vuruş geç vokal, vokoderle esnetme dokusu (1,5 ve 2 kat), 6 dB fazla açık vokal, %80'e yavaşlatılmış şarkı ve — çok zayıf biçimde — sonu kesilmiş sözcükler.
- **2'sinde hiçbir şey oynamadı:** yarım vuruş geç vokal ve her 3 saniyede bir tık.

Kabul edilmiş iki kayıtta araç toplam 6 uyarı satırı verdi: 4'ü yanlış alarm (biri büyük olasılıkla), biri gerçek bir söz hatası, biri teknik bir not.

**Ne anlama geliyor:** Araç akort, uyum, vokal düzeyi, boğukluk ve (söz dosyası verilirse) yanlış söz için güvenilir bir bekçi. Zamanlama kayması, yapaylık, enerji ve küçük kurgu kusurları (tık, kesik sözcük) için bekçi değil; bunlarda en fazla "iki sürümden hangisi farklı" sorusuna cevap verir.

Bir sınır baştan söylenmeli: kusurları ben de duyamadım. Her kusurun dosyada gerçekten bulunduğunu araçtan bağımsız ölçümlerle doğruladım (`bozuk_dogrulama.json`), ama "dinleyici bunu fark eder" yargısı varsayımdır.

## Nasıl sınandı

- **Kaynak:** `ali-baba/dinle_2.mp3` ve aracın daha önce ayırdığı vokal ve altyapı kanalları. İki kanalın toplamı asıl dosyayı geri veriyor (fark −42 dB). Bozuk sürümlerde yalnız vokal kanalı (ya da bütün karışım) değiştirilip yeniden karıştırıldı.
- **Ölçüm:** her dosya için `dinle.py <dosya> --ayir`, yani bitmiş bir MP3'ü dinletir gibi; araç vokali kendisi ayırdı. Toplam 40 çalıştırma (ayrıca yeniden yapılan 2 esnetme ölçümü).
- **Gürültü:** aynı dosya iki kez ölçülünce, çalışma süreleri dışındaki 314 sayının hepsi birebir aynı çıktı. Asıl gürültü, dosya yeniden kodlanınca ortaya çıkıyor. Bunu ölçmek için kusursuz 5 kopya kullanıldı: asıl, yeniden kodlanmış MP3, WAV, yeniden karışım, 1 dB kısık ve 23 ms kaydırılmış kopya. Bir ölçünün bu 5 kopyadaki en büyük–en küçük farkı "gürültü" sayıldı.
- **Karar:** "araç uyardı" = kusurla ilgili özet satırı, kusursuz 5 kopyanın hepsinden kötü durumda. "Sayı oynadı" = kusur için önceden seçilmiş ölçülerden biri gürültünün 3 katından fazla değişti. İlgili satır ve ölçüler, bozuk sürümlerin sonuçları görülmeden önce seçildi.
- **Sözler:** ücretli döküm (Scribe) krediyi korumak için yalnız 22,5 saniyelik iki kısa parçada (7 ve 8 numaralı kusurlar) ve 18 saniyelik bir kuru vokal parçasında yapıldı. Harcanan: 346 kredi. Defter toplamı 6921 / 8000.

## Tespit tablosu

| No | Kusur | Sonuç | Aracın gördüğü | Gürültünün kaç katı |
|---|---|---|---|---|
| 1a | Vokal 50 cent tiz | ✅ araç uyardı | Akort satırı ✅ → ❌. Notaya uzaklık 9,0 → 41,8 cent; ±25 cent içinde %88 → %12; 14 uzun nota saniyesiyle işaretlendi | 82 |
| 1b | Vokal 100 cent (yarım ses) tiz | ✅ araç uyardı | "Aynı armonide mi" satırı ✅ → ❌. Armonik destek +0,249 → −0,056; "en iyi kaydırma −1"; 21 uzun notanın 21'i çakışıyor | 7 (destek), 21 (çakışan nota) |
| 2a | Vokal çeyrek vuruş (129 ms) geç | 🔶 uyarmadı, sayı oynadı | Ritim satırı ⚠️ → ✅ oldu (ters yöne). Ama aynı satırda: kayma +24 → −109 ms; 40 ms içindeki başlangıçlar %49 → %6 | 66 |
| 2b | Vokal yarım vuruş (259 ms) geç | ❌ hiçbir şey oynamadı | Kayma +24 → +22 ms; sıkılık 0,37 → 0,33 | 1 |
| 3a | Vokalde 1,5 kat vokoder esnetmesi dokusu | 🔶 uyarmadı, sayı oynadı | Yapaylık satırı "işaret yok". Zarf titremesi −8,7 → −14,2 dB; Distill-MOS 3,42 → 3,09; UTMOS22 1,49 → 1,28 | 9 (zarf), 21 (UTMOS22) |
| 3b | Vokalde 2 kat vokoder esnetmesi dokusu | 🔶 uyarmadı, sayı oynadı | Yapaylık satırı "işaret yok". Zarf titremesi −8,7 → −12,9 dB; Distill-MOS 3,42 → 3,07; UTMOS22 1,49 → 1,30 | 7 (zarf), 19 (UTMOS22) |
| 4 | Perde hece başına düzleştirilmiş (otomatik akort benzeri) | ✅ araç uyardı | Yapaylık satırı ⚠️, 2 işaret: "notaların içi çok düz", "geçişler ani". Çok düz nota oranı 0,03 → 0,41; nota içi oynaklık 11,6 → 5,6 cent | 13 |
| 5 | Her 3 saniyede bir tık (36 adet) | ❌ hiçbir şey oynamadı | Gerçek tepe 0,0 → +0,9 dBTP (gürültü 1,2 dB). Panoda da görünmüyor | 0,8 |
| 6a | Vokal 6 dB kısık | ✅ araç uyardı | Denge satırı ✅ → ⚠️. Vokal − altyapı −4,1 → −9,8 dB (eşik −6); 6 yerde "gömük vokal" | 3,8 |
| 6b | Vokal 6 dB fazla açık | 🔶 uyarmadı, sayı oynadı | Denge satırı ✅ kaldı. Vokal − altyapı −4,1 → +2,5 dB (eşik +9) | 4,4 |
| 7 | Her satırın son sözcüğü 150 ms erken kesik | 🔶 uyarmadı, sayı çok az oynadı | Sözler satırı ✅ (hata %0). Vokalli süre %58,0 → %57,1; perdeli çerçeve oranı 0,302 → 0,277 | 4,5 |
| 8 | Bir satır yerine başka satır söyleniyor | ✅ araç uyardı (söz dosyası ve Scribe ile) | Sözler satırı ✅ → ⚠️. Hata %0 → %6,7: "Koyunlar" yerine "İnekler", "meler" yerine "bağırır", saniyeleriyle | ölçülmedi (tek döküm) |
| 9 | Bütün şarkı %80 tempoya yavaşlatılmış | 🔶 uyarmadı, sayı oynadı | Enerji satırı ✅ "coşkulu yana yakın" kaldı. Tempo 116 → 92,8 BPM; hareketlilik 73 → 69; MusicCoCa coşku +0,179 → +0,093 | 232 (tempo), 10 (MusicCoCa) |
| 10 | Bütün karışım 4 kHz'de kesilmiş | ✅ araç uyardı | Yapaylık ⚠️ (2 işaret: ünsüzlerde tiz yok, vokal 4,8 kHz'de bitiyor) ve Enerji ⚠️. Üst frekans 18,8 → 5,2 kHz | 181 |

Tık konusunda üç ek deneme yapıldı (sayıma katılmadı):

| No | Ek deneme | Sonuç | Açıklama |
|---|---|---|---|
| 5b | Aynı tık, üçte bir genlikte | ❌ hiçbir şey oynamadı | Çoğu yerde müzik örter; duyulup duyulmadığı şüpheli. Aracın suçu sayılmaz. |
| 5c | 5 ms'lik çıtırtı (şüphe götürmez biçimde duyulur) | ✅ araç uyardı | "Kırpılma" ❌ ve 36 çıtırtıdan 3'ünün saniyesi. Ama yalnız çıtırtı dosyayı tam ölçeğin üstüne ittiği için (+4,4 dBTP). |
| 5d | Aynı çıtırtı, bütün dosya 6 dB kısık | 🔶 uyarmadı, sayı oynadı | Çıtırtı müziğe göre aynı yükseklikte, ama tam ölçeğe değmiyor: ilgili satırlar sustu. Yalnız tepe faktörü 14,9 → 18,4 dB (12 kat). Araç çıtırtıyı değil kırpılmayı görüyor. |

## Kör noktalar

1. **Yarım vuruş kaymış vokal.** Ritim ölçüsü vokal başlangıçlarını sekizlik ızgaraya göre ölçüyor. Tam bir sekizlik (yarım vuruş) geç kalan vokal yine ızgaranın üstüne düşer; hiçbir sayı değişmez. Kanallar elde verilince de aynı.
2. **Çeyrek vuruş kaymış vokal.** Sayı kusuru gösteriyor (kayma −109 ms, başlangıçların %6'sı yerinde) ama satırın durumu ✅ "sıkı oturuyor" çıkıyor, çünkü durum yalnız sıkılığa bakıyor. Yön de yanlış: 129 ms geç olan vokal "109 ms erken" görünüyor.
3. **Tık ve çıtırtı.** Aracın bunu arayan bir ölçüsü yok. Yalnız dosyayı kırpılmaya iten çıtırtı görünür. Tıklı ve tıksız panolar yan yana aynı.
4. **Sonu kesilmiş sözcükler.** Scribe eksik sesi tamamlayıp doğru sözcüğü yazıyor ("va" → "var", "ba" → "bak"); hata oranı %0, düşük güvenli sözcük yok. Vokal panosunda, asıl sürümle yan yana konunca satır aralarındaki beyaz boşluklar görülüyor (`pano_satir_sonu_asil_ve_kesik.png`); tek başına bakınca nefes arası sanılır.
5. **Vokoderle esnetme dokusu.** Yapaylık satırı hem karışımda hem kuru vokalde sustu. Kuru vokalde 1,5 ve 2 kat esnetme: işaret 0; zarf titremesi −9,1 → −14,5 ve −16,6 dB; Distill-MOS 3,41 → 2,61 ve 3,17. Scribe 2 kat esnetilmiş kıtayı kusursuz yazdı; hece hızı 4,0 → 2,0 hece/sn oldu ama araç yalnız hızlı söyleyişi uyarıyor.
6. **Bu sayılar için mutlak eşik konamıyor.** Kabul edilmiş El Yıkama kaydında zarf titremesi −11,7 dB, UTMOS22 1,31, MusicCoCa coşku +0,089. Esnetilmiş sürümler (−12,9 … −14,2 dB; 1,28–1,30) ve yavaşlatılmış sürüm (+0,093) bunlardan ayırt edilemiyor. Yalnız aynı şarkının iki hali karşılaştırılabilir.
7. **Fazla açık vokal.** Fark doğru ölçülüyor (+6,6 dB; gerçek +6) ama eşik +9 dB.
8. **Yanlış söz.** Yalnız beklenen söz dosyası ve ücretli döküm varsa görülür (110 saniyelik şarkı yaklaşık 606 kredi). Onlarsız çalıştırmada hiçbir sayı oynamadı.
9. **Denge ölçüsü dosyanın düzeyine duyarlı** (`--ayir` yolunda). Aynı vokal/altyapı oranı için −0,8 dB (çıtırtılı), −4,1 dB (taban), −4,9 dB (1 dB kısık) ve −6,8 dB (6 dB kısık; ⚠️ aldı) ölçüldü. Bir nedeni: ayırıcı, tepesi 0,9'u aşan kanalı tek başına kısıyor (çıtırtılı sürümde altyapı kanalı 3,6 dB kısılmış). 6 dB kısık dosyadaki kaymanın nedenini bulamadım. Gerçek belirsizlik yaklaşık ±3 dB; 6a ve 6b'deki 6 dB'lik farklar bunun üstünde ama payı dar.
10. **Sınanamayanlar.** Yabancı aksan, sesin hoşluğu, "ninni gibi" hissi. Bunlar için kodla kusur üretilemedi (konuşma sentezi bu sınamada yasaktı); araç da ölçemediğini raporunda söylüyor.

## Yanlış alarmlar

**Asıl kayıt (`ali-baba/dinle_2.mp3`), söz dosyasıyla:**

| Satır | Durum | Değer | Değerlendirme |
|---|---|---|---|
| Tepe | ⚠️ | +0,5 dBTP | Teknik olarak doğru (dosya tam ölçeği aşıyor), dinleyici şikâyeti değil. Yeniden kodlanmış kopyada −0,1'e inip kayboluyor. |
| Ritme oturma | ⚠️ | R 0,36 | Yanlış alarm. "İyi" eşiği 0,55; gerçek şarkı ayrılmış vokalde buna ulaşmıyor. |
| Sözler | ⚠️ | hata %8,3 | Yarısı doğru: 76,9. saniyede gerçek bir söz hatası var ("köpekleri" yerine "ördekleri"). Kalan 8 "fazla" sözcük, söz dosyasında yazmayan son tekrarlar. |

**İkinci kabul edilmiş kayıt (`el-yikama/coskulu_2.mp3`), söz dosyasıyla:**

| Satır | Durum | Değer | Değerlendirme |
|---|---|---|---|
| Vokal altyapıyla aynı armonide mi | ❌ | destek +0,132; en iyi kaydırma −4 | Yanlış alarm, en ağırı. Aynı raporda gam içi söyleme %100, akort ✅. |
| Çakışan uzun notalar | ⚠️ | 24 notadan 1'i (8,8. sn, F#4) | Büyük olasılıkla yanlış alarm: araç akoru "Dm" sanmış, şarkı Re majör. Doğrulayamadım. |
| Ritme oturma | ⚠️ | R 0,43 | Yanlış alarm (aynı eşik). |

Sözler satırı bu kayıtta ✅ (hata %4,3: "Köpük köpük" şarkıda bir kez fazla söyleniyor).

## Ölçüm gürültüsü

Kusursuz 5 kopya arasındaki en büyük fark:

| Ölçü | Gürültü | Not |
|---|---|---|
| Notaya uzaklık (cent) | 0,4 | 8,6 … 9,0 |
| ±25 cent içinde | 0,7 puan | |
| Armonik destek farkı | 0,04 | 0,249 … 0,290 |
| Ritim sıkılığı R | 0,04 | 0,36 … 0,40 |
| Ortalama kayma | 2 ms | 24 … 26 |
| Vokal − altyapı | 1,5 dB | 9. kör noktaya bakın: gerçekte daha geniş |
| Zarf titremesi | 0,6 dB | |
| Distill-MOS / UTMOS22 | 0,03 / 0,01 | |
| NISQA / DNSMOS | 0,07 / 0,07 | |
| Tempo | 0,1 BPM | |
| Hareketlilik puanı | 1 | |
| MusicCoCa coşku farkı | 0,009 | |
| Vokal kanalına sızıntı | 22,8 dB | Kararsız; karşılaştırmada kullanılmamalı |

Gürültü tek şarkıdan ve 5 kopyadan çıkarıldı; başka şarkıda farklı olabilir.

## Kanallar elde olunca

Yedi bozuk sürüm (ve taban ile bir denetim) ayrıca `--vokal <bozuk vokal> --altyapi <altyapı>` yoluyla ölçüldü; araç ayırma yapmadı.

- Aynı kalanlar: 50 cent detone ✅, düz perde ✅, 6 dB kısık vokal ✅ (−3,4 → −9,4 dB), çeyrek vuruş 🔶 (kayma +26 → −104 ms), yarım vuruş ❌, kesik satır sonu 🔶 zayıf.
- Değişen: 2 kat esnetme bu yolda ✅ (1 yapaylık işareti). İşaret "basamaklı perde" diyor; doğru satır, yanlış gerekçe.
- Denge ölçüsü bu yolda tam çıktı (6,0 dB fark).

## Araca öneriler

1. Ritim satırının durumuna kaymayı kat: kayma 60 ms'den büyükse ya da başlangıçların %25'inden azı 40 ms içindeyse ⚠️. Kabul edilmiş iki kayıtta +26 ve +29 ms, %48 ve %61; çeyrek vuruş geç sürümde −109 ms ve %6.
2. Sıkılık 0,30–0,55 arasını "bilgi" yap; kabul edilmiş iki kayıt (0,36 ve 0,43) bu aralıkta.
3. Yarım vuruş kaymaları için üretim planındaki satır başlangıç saniyelerini Scribe'ın sözcük saniyeleriyle karşılaştır.
4. Tık dedektörü ekle: 6–16 kHz bandında 2 ms'lik pencerelerde çevresinin 10 dB üstüne çıkan tekil patlamalar. Bu sınamadaki tık bu ölçüyle 36 yerin 23'ünde, çıtırtı 36'sında eşiği aşıyor.
5. Sözcük sonu kesikleri için vokal kanalında "dik bitişleri" say (düzeyin 10 ms içinde 30 dB düştüğü yerler).
6. `--bpm` ile hedef tempo verildiyse %5'ten fazla sapmayı uyar.
7. "Aynı armonide mi" satırında ❌ için iki koşulu birlikte ara: destek farkı +0,05'in altında **ve** en iyi kaydırma 0 değil.
8. Denge ölçüsünü ayırıcının kanal başına kısmasından bağımsız kıl ya da belirsizliği ±3 dB diye yaz.

Bu önerilerin hiçbiri denenmedi; araç klasörü bu görevde salt okunurdu.

## Bu sınamanın sınırları

- Tek şarkı, tek ses. Gürültü ve eşikler başka şarkıda kayabilir.
- Yan etkiler: asıl kayıt zaten tam ölçeğe dayandığı için vokale dokunan işlemler tepeleri oynattı; 3a, 3b, 4 ve 6b'de ilgisiz bir "Kırpılma" ❌ satırı, birçok sürümde "Tepe" ⚠️ çıktı. Bunlar yakalama sayılmadı.
- Esnetmenin ilk denemesinde vokal 5–7 dB kısılmıştı (araç bunu denge satırında gösterdi). Düzey eşitlenip yeniden ölçüldü; ilk raporlar `raporlar_eski/` altında.
- Esnetme kusuru karışımda "sıkıştır, sonra vokoderle geri esnet" yoluyla üretildi: süre ve perde aynı kaldı, yalnız doku bozuldu. Gerçek "konuşmayı ezgiye esnetme" vokali bundan daha kötüdür.
- Karar kuralında bir düzeltme yapıldı: ilk yazımda "tabandan kötü satır" yeterliydi; "Tepe" satırı her yerde çıktığı için "kusursuz 5 kopyanın hepsinden kötü" koşuluna çevrildi.
- 7 ve 8 için döküm kısa parçada yapıldı; dökümün kendi gürültüsü ölçülmedi.
- Gemini'ye dinletme yolu sınanmadı (bu görevde tek izinli ücretli uç Scribe'dı). Tık ve kesik sözcük için ikinci görüş verip vermeyeceği bilinmiyor.
- Panolara yalnız üç sürümde baktım (taban, tık, kesik satır sonu).

## Dosyalar

Hepsi `cocuk-kanali/dinleme/sinama/` altında.

| Dosya | İçerik |
|---|---|
| `sinama.json` | Bu raporun sayıları: tespit tablosu, gürültü, yanlış alarmlar, kör noktalar |
| `sinama_tablolar.md` | Her kusur için ilgili bütün ölçüler ve ilgisiz oynayanlar |
| `sinama_ham.json` | 40 çalıştırmanın bütün ölçüleri |
| `bozuklar.json` | Her bozuk sürümün kesin tanımı |
| `bozuk_dogrulama.json` | Kusurların araçtan bağımsız doğrulaması |
| `kosu_gunlugu.json` | Hangi komut, ne kadar sürdü |
| `raporlar/<ad>/rapor.json`, `rapor.md` | Aracın her dosya için ürettiği rapor (pano üretilmedi) |
| `pano_satir_sonu_asil_ve_kesik.png` | Kesik satır sonlarının panoda yan yana görünüşü |
| `kod/bozuk_uret.py` | Bozuk sürümleri üretir |
| `kod/bozuk_dogrula.py`, `kod/kosu.py`, `kod/degerlendir.py`, `kod/sonuc_yaz.py` | Doğrulama, çalıştırma, değerlendirme |

Bozuk sesler depoya yazılmadı (yaklaşık 290 MB); `~/.cache/dinleme/sinama/ses/` altında duruyor ve `kod/bozuk_uret.py` ile yeniden üretilir.
Yeniden üretilen dosyalar birebir aynı çıkmazsa `kosu.py`'nin "kisa" grubu yeniden ücretli döküm ister (yaklaşık 346 kredi).
Aracın kanal önbelleğinde bu sınamadan yaklaşık 1 GB ayrılmış kanal kaldı (`~/.cache/dinleme/kanallar/`); silinebilir.
