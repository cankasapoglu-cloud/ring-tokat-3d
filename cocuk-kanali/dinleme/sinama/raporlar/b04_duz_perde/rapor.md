# Dinleme raporu: b04_duz_perde.mp3

_2026-11-21 17:07:24 — dinle.py 1.0 (2026-11-21). Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._

## Özet

| Durum | Konu | Makinenin gördüğü |
|---|---|---|
| ✅ iyi | Ses yüksekliği | -12,8 LUFS, gerçek tepe 1,1 dBTP. |
| ⚠️ dikkat | Tepe | gerçek tepe 0 dBTP'nin üstünde (1,1): bazı cihazlarda cızırtı yapabilir; -1 dBTP'ye indirin. |
| ❌ sorun | Kırpılma | 3 yerde ardışık tam ölçek örnek var (ilk: [12.98, 38.85, 63.65] sn). |
| ✅ iyi | Enerji / coşku | hareketlilik puanı 74/100 (tempo 116 BPM, saniyede 4,3 olay); MusicCoCa coşku farkı +0,19; CED 'ninni' olasılığı 0,000 → makine göstergeleri coşkulu yana yakın. Projedeki sürümlerle karşılaştırma (hareketlilik puanı: 'coşkulu' adlı 6 sürümde 66…79, 'yavaş' adlı 3 sürümde 52…61; MusicCoCa coşku farkı: 'coşkulu' adlı 6 sürümde +0,09…+0,22, 'yavaş' adlı 3 sürümde -0,10…-0,08). |
| ✅ iyi | Vokal / altyapı dengesi | vokal altyapıdan -2,5 dB (medyan); sürenin %58 kadarında vokal var. Vokal-altyapı dengesi olağan aralıkta. |
| ✅ iyi | Vokal altyapıyla aynı armonide mi | armonik destek farkı +0,277 (artı = uyumlu); en iyi kaydırma +0 yarım ses (0 olmalı). |
| ℹ️ bilgi | Gam içi söyleme | söylenen sürenin %83 kadarı altyapının gamında (La majör (A major)) — ton belirsiz, bu oran güvenilmez; akor sesi %65, gam dışı %13. |
| ✅ iyi | Akort (detone mi) | notalara uzaklık medyan 7,7 cent; söylenen sürenin %91 kadarı ±25 cent içinde; vokalin genel kayması -7 cent. |
| ⚠️ dikkat | Çakışan uzun notalar | 1 / 41 uzun nota (0,3 sn üstü) altyapıyla çakışıyor ya da detone. |
| ❌ sorun | Ritme oturma | sıkılık R=0,28 (ölçümün tavanı ≈0,65; rastgele ≈0,15); başlangıçların %43 kadarı en yakın sekizliğe 40 ms içinde; ortalama kayma +25 ms (+ geç). Vokal başlangıçları ızgarayla ilişkisiz görünüyor (ritme oturmuyor YA DA vuruş ızgarası yanlış bulundu) (vuruş ızgarası: otomatik (altyapıdan)). |
| ⚠️ dikkat | Yapaylık işaretleri (vekil) | 2 işaret: notaların içi çok düz (medyan 5.6 cent): sert akort düzeltme / vokoderle sabitlenmiş perde izlenimi; bağlı notalar arası geçişler ani (16 ms medyan; aynı ölçümle doğal vokalde ~32 ms): basamaklı perde. |

Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.

## Bu raporun SÖYLEYEMEDİKLERİ

- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; konuşma için eğitilmiş modeller şarkıda güvenilmezdir.
- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).
- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.
- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.

## Ayrıntılar

**Dosya:** 110,1 sn, 2 kanal, 48000 Hz, mp3, 192 kb/sn; üst frekans sınırı 18733 Hz. Kanal kaynağı: otomatik ayırma (UVR-MDX-NET-Voc_FT.onnx, önbellekten).

**Ses düzeyi:** -12,8 LUFS; ses yüksekliği aralığı (LRA) 3,0 LU; gerçek tepe 1,1 dBTP; tepe faktörü 16,1 dB. Stereo: olağan stereo (sol-sağ ilişkisi 0,89).

**Enerji:** tempo 116,0 BPM (otomatik tahmin; yarı/çift tempo hatası yapabilir); yerel temponun %100 kadarı ±%3 içinde; nabız netliği 0,83; olay yoğunluğu 4,3/sn; vurmalı/armonik 0,5 dB; spektral akı 1,89; parlaklık (ağırlık merkezi) 2612 Hz; düzey oynaklığı 1,7 dB.
Hareketlilik puanı bileşenleri (0-1): olay_yogunlugu_sn 0,51, nabiz_netligi 1,00, vurmali_armonik_db 1,00, spektral_aki_ort 0,61, parlaklik_agirlik_merkezi_hz 0,59.

**CED etiketleri (karışım):** Music 0,88, Afrobeat 0,12, Dance music 0,10, Pop music 0,07, Happy music 0,06, Music of Africa 0,05, Exciting music 0,05, Rhythm and blues 0,05.

**Ton (altyapı kanalı):** 0–110 sn La majör (A major) (belirsiz). Akort kayması 4,0 cent. En çok duyulan akorlar: A 56 sn, Am 47 sn, C#m 2 sn, F 2 sn, Fm 1 sn (ortalama güven 0,69).

**Vokal perdesi:** 140 nota; ses aralığı C4–F4 (4,9 yarım ses), medyan E4; nota içi oynaklık medyan 5,6 cent; çok düz nota oranı 0,41; vibratolu uzun nota oranı 0,00; geçiş çerçevesi oranı 0,08. Perde izleyici denetimi: pYIN ile %97 uyum.
Vokalin kendi ses dağılımından ton tahmini: Mi minör (E minor) (r=0,62).

**Çakışan / detone uzun notalar:**

| sn | süre | nota | akor | tür |
|---|---|---|---|---|
| 52,5 | 0,53 | D4 | A | akor sesine yarim ses komsu |

**Yapaylık için vekil ölçümler (kanıt değil):** nota içi oynaklık 5,6 cent; ızgaraya yapışma R 0,77; donmuş ünlü 0 adet (sesli sürenin %0 kadarı); ünsüzlerde tiz payı -10,3 dB; vokalin üst frekansı 10723 Hz; tiz doku değişim katsayısı 1,69 (durağan gürültü ≈0,52); zarf titremesi -11,6 dB.

**Konuşma-kalitesi tahminleri (vokal kanalı, 1-5; şarkı için eğitilmediler):** DNSMOS 2,49 (sinyal 3,00, arka plan 3,39); NISQA 3,39 (gürültüsüzlük 3,90, kesintisizlik 4,26, renklenmezlik 3,51); Distill-MOS 3,33; UTMOS22 1,50. Yalnızca aynı yolla elde edilmiş iki vokali karşılaştırmak için.
CED, vokal kanalını şöyle etiketliyor: şarkı 0,06, konuşma 0,06, sentetik şarkı 0,054, konuşma sentezleyici 0,017.

_Çalışma süresi: 96 sn. Bütün sayılar: `rapor.json`._
