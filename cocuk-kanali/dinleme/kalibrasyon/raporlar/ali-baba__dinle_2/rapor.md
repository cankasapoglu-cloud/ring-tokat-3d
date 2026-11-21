# Dinleme raporu: dinle_2.mp3

_2026-11-21 16:13:03 — dinle.py 1.0 (2026-11-21). Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._

## Özet

| Durum | Konu | Makinenin gördüğü |
|---|---|---|
| ✅ iyi | Ses yüksekliği | -12,4 LUFS, gerçek tepe 0,5 dBTP. |
| ⚠️ dikkat | Tepe | gerçek tepe 0 dBTP'nin üstünde (0,5): bazı cihazlarda cızırtı yapabilir; -1 dBTP'ye indirin. |
| ✅ iyi | Enerji / coşku | hareketlilik puanı 73/100 (tempo 116 BPM, saniyede 4,2 olay); MusicCoCa coşku farkı +0,18; CED 'ninni' olasılığı 0,000 → makine göstergeleri coşkulu yana yakın. Projedeki sürümlerle karşılaştırma (hareketlilik puanı: 'coşkulu' adlı 6 sürümde 66…79, 'yavaş' adlı 3 sürümde 52…61; MusicCoCa coşku farkı: 'coşkulu' adlı 6 sürümde +0,09…+0,22, 'yavaş' adlı 3 sürümde -0,10…-0,08). |
| ✅ iyi | Vokal / altyapı dengesi | vokal altyapıdan -3,4 dB (medyan); sürenin %58 kadarında vokal var. Vokal-altyapı dengesi olağan aralıkta. |
| ✅ iyi | Vokal altyapıyla aynı armonide mi | armonik destek farkı +0,260 (artı = uyumlu); en iyi kaydırma +0 yarım ses (0 olmalı). |
| ℹ️ bilgi | Gam içi söyleme | söylenen sürenin %86 kadarı altyapının gamında (La majör (A major)) — ton belirsiz, bu oran güvenilmez; akor sesi %70, gam dışı %11. |
| ✅ iyi | Akort (detone mi) | notalara uzaklık medyan 8,8 cent; söylenen sürenin %88 kadarı ±25 cent içinde; vokalin genel kayması -5 cent. |
| ✅ iyi | Çakışan uzun notalar | 0 / 25 uzun nota (0,3 sn üstü) altyapıyla çakışıyor ya da detone. |
| ⚠️ dikkat | Ritme oturma | sıkılık R=0,36 (ölçümün tavanı ≈0,65; rastgele ≈0,15); başlangıçların %48 kadarı en yakın sekizliğe 40 ms içinde; ortalama kayma +26 ms (+ geç). Vokal ızgaraya orta derecede oturuyor (serbest / konuşur gibi söyleyiş ya da ölçüm gürültüsü) (vuruş ızgarası: otomatik (altyapıdan)). |
| ℹ️ bilgi | Yapaylık işaretleri (vekil) | işaret bulunmadı — bu 'doğal' demek DEĞİLDİR, yalnızca bilinen kaba izler yok. |
| ⚠️ dikkat | Sözler | sözcük hata oranı %8,3 (108 beklenen sözcükten 1 farklı, 0 eksik, 8 fazla); küçük ek/harf farkları sayılmazsa %7,4. |
| ℹ️ bilgi | Söyleyiş hızı | söz öbeklerinde medyan 3,9 hece/sn (en hızlı 4,1). |

Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.

## Bu raporun SÖYLEYEMEDİKLERİ

- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; konuşma için eğitilmiş modeller şarkıda güvenilmezdir.
- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).
- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.
- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.

## Ayrıntılar

**Dosya:** 110,1 sn, 2 kanal, 48000 Hz, mp3, 192 kb/sn; üst frekans sınırı 18744 Hz. Kanal kaynağı: otomatik ayırma (UVR-MDX-NET-Voc_FT.onnx, önbellekten).

**Ses düzeyi:** -12,4 LUFS; ses yüksekliği aralığı (LRA) 3,1 LU; gerçek tepe 0,5 dBTP; tepe faktörü 15,2 dB. Stereo: olağan stereo (sol-sağ ilişkisi 0,87).

**Enerji:** tempo 116,0 BPM (otomatik tahmin; yarı/çift tempo hatası yapabilir); yerel temponun %100 kadarı ±%3 içinde; nabız netliği 0,82; olay yoğunluğu 4,2/sn; vurmalı/armonik 0,8 dB; spektral akı 1,86; parlaklık (ağırlık merkezi) 2684 Hz; düzey oynaklığı 1,7 dB.
Hareketlilik puanı bileşenleri (0-1): olay_yogunlugu_sn 0,50, nabiz_netligi 1,00, vurmali_armonik_db 1,00, spektral_aki_ort 0,59, parlaklik_agirlik_merkezi_hz 0,62.

**CED etiketleri (karışım):** Music 0,87, Dance music 0,10, Pop music 0,09, Happy music 0,07, Afrobeat 0,07, Singing 0,06, Exciting music 0,06, Rhythm and blues 0,05.

**Ton (altyapı kanalı):** 0–110 sn La majör (A major) (belirsiz). Akort kayması 5,0 cent. En çok duyulan akorlar: A 52 sn, Am 51 sn, C#m 2 sn, F 2 sn, Em 1 sn (ortalama güven 0,68).

**Vokal perdesi:** 128 nota; ses aralığı C4–F4 (5,0 yarım ses), medyan E4; nota içi oynaklık medyan 11,1 cent; çok düz nota oranı 0,03; vibratolu uzun nota oranı 0,15; geçiş çerçevesi oranı 0,18. Perde izleyici denetimi: pYIN ile %94 uyum.
Vokalin kendi ses dağılımından ton tahmini: Mi minör (E minor) (r=0,64).

**Yapaylık için vekil ölçümler (kanıt değil):** nota içi oynaklık 11,1 cent; ızgaraya yapışma R 0,67; donmuş ünlü 0 adet (sesli sürenin %0 kadarı); ünsüzlerde tiz payı -11,1 dB; vokalin üst frekansı 10723 Hz; tiz doku değişim katsayısı 1,42 (durağan gürültü ≈0,52); zarf titremesi -9,1 dB.

**Konuşma-kalitesi tahminleri (vokal kanalı, 1-5; şarkı için eğitilmediler):** DNSMOS 2,71 (sinyal 3,29, arka plan 3,38); NISQA 2,88 (gürültüsüzlük 3,49, kesintisizlik 4,41, renklenmezlik 3,42); Distill-MOS 3,41; UTMOS22 1,49. Yalnızca aynı yolla elde edilmiş iki vokali karşılaştırmak için.
CED, vokal kanalını şöyle etiketliyor: şarkı 0,08, konuşma 0,07, sentetik şarkı 0,021, konuşma sentezleyici 0,005.

**Makinenin duyduğu sözler (Scribe, dil tur olasılık 1,00):**

> [müzik] Ali Baba'nın bir çiftliği var. Çiftliğinde inekleri var. İnekler nasıl bağırır? Dinle bak, dinle bak. [müzik] Ali Baba'nın bir çiftliği var. Çiftliğinde koyunları var. Koyunlar nasıl meler? Dinle bak, dinle bak. [müzik] Ali Baba'nın bir çiftliği var. Çiftliğinde bir de atı var. Atı nasıl kişner? Dinle bak, dinle bak. [müzik] Ali Baba'nın bir çiftliği var. Çiftliğinde horozları var. Horozlar nasıl öter? Dinle bak, dinle bak. [müzik] Ali Baba'nın bir çiftliği var. Çiftliğinde ördekleri var. Ördekler nasıl bağırır? Dinle bak, dinle bak. [müzik] Ali Baba'nın bir çiftliği var. Çiftliğinde ördekleri var. Köpekler nasıl havlar? Dinle bak, dinle bak. [müzik] Ali Baba'nın bir çiftliği var. Çiftliğinde bir kedisi var. Kedisi nasıl miyavlar? Dinle bak, dinle bak. [müzik] Dinle bak, dinle bak. [müzik] Dinle bak, dinle bak.

Ses olayları: [müzik] 2,0–6,1 sn, [müzik] 14,5–18,5 sn, [müzik] 26,9–33,0 sn, [müzik] 41,2–46,5 sn, [müzik] 54,8–59,4 sn, [müzik] 67,7–73,9 sn, [müzik] 82,2–86,3 sn, [müzik] 94,5–100,8 sn, [müzik] 102,9–107,0 sn.

**Söz farkları:**

| sn | beklenen | duyulan | tür |
|---|---|---|---|
| 76,9 | köpekleri | ördekleri | küçük fark (ek/harf) |
| 100,8 | — | Dinle | fazla |
| 101,4 | — | bak, | fazla |
| 101,9 | — | dinle | fazla |
| 102,4 | — | bak. | fazla |
| 107,0 | — | Dinle | fazla |
| 107,6 | — | bak, | fazla |
| 108,1 | — | dinle | fazla |
| 108,6 | — | bak. | fazla |

## Panolar (Read aracıyla bakın)

| Dosya | Ne gösterir | Neye bakmalı |
|---|---|---|
| `00_genel_bakis.png` | bütün dosya: spektrogram, düzeyler, hareketlilik, sorun çizelgesi (0–110 sn) | kırmızı X / şeritlerin toplandığı yer; hareketliliğin düştüğü bölümler |
| `01_pano_000-028sn.png` | 30 sn: spektrogram + sözcükler, vokal spektrogramı, vuruşlar, düzey (0–28 sn) | ≠ işaretli sözcükler; vokal çizgisinin altyapının altında kaldığı yerler |
| `01_perde_000-028sn.png` | 30 sn: vokal perdesi akor seslerinin üstünde, cent, ritim, kroma (0–28 sn) | kırmızı çapraz taralı notalar (gam dışı), ±25 cent bandının dışındaki X'ler, ±40 ms dışındaki başlangıçlar |
| `02_pano_027-055sn.png` | 30 sn: spektrogram + sözcükler, vokal spektrogramı, vuruşlar, düzey (28–55 sn) | ≠ işaretli sözcükler; vokal çizgisinin altyapının altında kaldığı yerler |
| `02_perde_027-055sn.png` | 30 sn: vokal perdesi akor seslerinin üstünde, cent, ritim, kroma (28–55 sn) | kırmızı çapraz taralı notalar (gam dışı), ±25 cent bandının dışındaki X'ler, ±40 ms dışındaki başlangıçlar |
| `03_pano_055-083sn.png` | 30 sn: spektrogram + sözcükler, vokal spektrogramı, vuruşlar, düzey (55–83 sn) | ≠ işaretli sözcükler; vokal çizgisinin altyapının altında kaldığı yerler |
| `03_perde_055-083sn.png` | 30 sn: vokal perdesi akor seslerinin üstünde, cent, ritim, kroma (55–83 sn) | kırmızı çapraz taralı notalar (gam dışı), ±25 cent bandının dışındaki X'ler, ±40 ms dışındaki başlangıçlar |
| `04_pano_082-110sn.png` | 30 sn: spektrogram + sözcükler, vokal spektrogramı, vuruşlar, düzey (83–110 sn) | ≠ işaretli sözcükler; vokal çizgisinin altyapının altında kaldığı yerler |
| `04_perde_082-110sn.png` | 30 sn: vokal perdesi akor seslerinin üstünde, cent, ritim, kroma (83–110 sn) | kırmızı çapraz taralı notalar (gam dışı), ±25 cent bandının dışındaki X'ler, ±40 ms dışındaki başlangıçlar |

_Çalışma süresi: 64 sn. Bütün sayılar: `rapor.json`._
