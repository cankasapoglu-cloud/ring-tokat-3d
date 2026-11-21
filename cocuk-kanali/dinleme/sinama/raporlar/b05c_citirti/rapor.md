# Dinleme raporu: b05c_citirti.mp3

_2026-11-21 17:55:56 — dinle.py 1.0 (2026-11-21). Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._

## Özet

| Durum | Konu | Makinenin gördüğü |
|---|---|---|
| ✅ iyi | Ses yüksekliği | -12,6 LUFS, gerçek tepe 4,4 dBTP. |
| ⚠️ dikkat | Tepe | gerçek tepe 0 dBTP'nin üstünde (4,4): bazı cihazlarda cızırtı yapabilir; -1 dBTP'ye indirin. |
| ❌ sorun | Kırpılma | 3 yerde ardışık tam ölçek örnek var (ilk: [23.37, 68.37, 107.37] sn). |
| ✅ iyi | Enerji / coşku | hareketlilik puanı 75/100 (tempo 116 BPM, saniyede 4,4 olay); MusicCoCa coşku farkı +0,18; CED 'ninni' olasılığı 0,000 → makine göstergeleri coşkulu yana yakın. Projedeki sürümlerle karşılaştırma (hareketlilik puanı: 'coşkulu' adlı 6 sürümde 66…79, 'yavaş' adlı 3 sürümde 52…61; MusicCoCa coşku farkı: 'coşkulu' adlı 6 sürümde +0,09…+0,22, 'yavaş' adlı 3 sürümde -0,10…-0,08). |
| ✅ iyi | Vokal / altyapı dengesi | vokal altyapıdan -0,8 dB (medyan); sürenin %58 kadarında vokal var. Vokal-altyapı dengesi olağan aralıkta. |
| ✅ iyi | Vokal altyapıyla aynı armonide mi | armonik destek farkı +0,493 (artı = uyumlu); en iyi kaydırma +0 yarım ses (0 olmalı). |
| ℹ️ bilgi | Gam içi söyleme | söylenen sürenin %76 kadarı altyapının gamında (Mi majör (E major)) — ton belirsiz, bu oran güvenilmez; akor sesi %72, gam dışı %19. |
| ✅ iyi | Akort (detone mi) | notalara uzaklık medyan 8,3 cent; söylenen sürenin %89 kadarı ±25 cent içinde; vokalin genel kayması -4 cent. |
| ✅ iyi | Çakışan uzun notalar | 0 / 25 uzun nota (0,3 sn üstü) altyapıyla çakışıyor ya da detone. |
| ⚠️ dikkat | Ritme oturma | sıkılık R=0,36 (ölçümün tavanı ≈0,65; rastgele ≈0,15); başlangıçların %48 kadarı en yakın sekizliğe 40 ms içinde; ortalama kayma +29 ms (+ geç). Vokal ızgaraya orta derecede oturuyor (serbest / konuşur gibi söyleyiş ya da ölçüm gürültüsü) (vuruş ızgarası: otomatik (altyapıdan)). |
| ℹ️ bilgi | Yapaylık işaretleri (vekil) | işaret bulunmadı — bu 'doğal' demek DEĞİLDİR, yalnızca bilinen kaba izler yok. |

Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.

## Bu raporun SÖYLEYEMEDİKLERİ

- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; konuşma için eğitilmiş modeller şarkıda güvenilmezdir.
- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).
- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.
- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.

## Ayrıntılar

**Dosya:** 110,1 sn, 2 kanal, 48000 Hz, mp3, 192 kb/sn; üst frekans sınırı 18981 Hz. Kanal kaynağı: otomatik ayırma (UVR-MDX-NET-Voc_FT.onnx, önbellekten).

**Ses düzeyi:** -12,6 LUFS; ses yüksekliği aralığı (LRA) 3,0 LU; gerçek tepe 4,4 dBTP; tepe faktörü 18,7 dB. Stereo: olağan stereo (sol-sağ ilişkisi 0,87).

**Enerji:** tempo 116,0 BPM (otomatik tahmin; yarı/çift tempo hatası yapabilir); yerel temponun %100 kadarı ±%3 içinde; nabız netliği 0,79; olay yoğunluğu 4,4/sn; vurmalı/armonik 0,9 dB; spektral akı 1,89; parlaklık (ağırlık merkezi) 2694 Hz; düzey oynaklığı 1,6 dB.
Hareketlilik puanı bileşenleri (0-1): olay_yogunlugu_sn 0,54, nabiz_netligi 1,00, vurmali_armonik_db 1,00, spektral_aki_ort 0,60, parlaklik_agirlik_merkezi_hz 0,62.

**CED etiketleri (karışım):** Music 0,82, Dance music 0,09, Pop music 0,08, Afrobeat 0,07, Happy music 0,07, Rhythm and blues 0,05, Exciting music 0,05, Singing 0,05.
Hayvan sınıfları: Animal 0,001.

**Ton (altyapı kanalı):** 0–79 sn Mi majör (E major) (belirsiz); 79–110 sn La majör (A major) (belirsiz). Akort kayması 4,0 cent. En çok duyulan akorlar: Am 52 sn, A 49 sn, G# 3 sn, C#m 2 sn, F 2 sn (ortalama güven 0,68).

**Vokal perdesi:** 125 nota; ses aralığı C4–F4 (5,0 yarım ses), medyan E4; nota içi oynaklık medyan 10,9 cent; çok düz nota oranı 0,03; vibratolu uzun nota oranı 0,20; geçiş çerçevesi oranı 0,18. Perde izleyici denetimi: pYIN ile %94 uyum.
Vokalin kendi ses dağılımından ton tahmini: Mi minör (E minor) (r=0,64).

**Yapaylık için vekil ölçümler (kanıt değil):** nota içi oynaklık 10,9 cent; ızgaraya yapışma R 0,67; donmuş ünlü 0 adet (sesli sürenin %0 kadarı); ünsüzlerde tiz payı -11,4 dB; vokalin üst frekansı 10723 Hz; tiz doku değişim katsayısı 1,42 (durağan gürültü ≈0,52); zarf titremesi -8,9 dB.

**Konuşma-kalitesi tahminleri (vokal kanalı, 1-5; şarkı için eğitilmediler):** DNSMOS 2,65 (sinyal 3,25, arka plan 3,29); NISQA 2,79 (gürültüsüzlük 3,32, kesintisizlik 4,42, renklenmezlik 3,37); Distill-MOS 3,36; UTMOS22 1,49. Yalnızca aynı yolla elde edilmiş iki vokali karşılaştırmak için.
CED, vokal kanalını şöyle etiketliyor: şarkı 0,08, konuşma 0,07, sentetik şarkı 0,022, konuşma sentezleyici 0,006.

_Çalışma süresi: 60 sn. Bütün sayılar: `rapor.json`._
