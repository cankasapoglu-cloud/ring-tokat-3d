# Dinleme raporu: b04_duz_perde.mp3

_2026-11-21 17:43:47 — dinle.py 1.0 (2026-11-21). Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._

## Özet

| Durum | Konu | Makinenin gördüğü |
|---|---|---|
| ✅ iyi | Ses yüksekliği | -12,8 LUFS, gerçek tepe 1,1 dBTP. |
| ⚠️ dikkat | Tepe | gerçek tepe 0 dBTP'nin üstünde (1,1): bazı cihazlarda cızırtı yapabilir; -1 dBTP'ye indirin. |
| ❌ sorun | Kırpılma | 3 yerde ardışık tam ölçek örnek var (ilk: [12.98, 38.85, 63.65] sn). |
| ℹ️ bilgi | Enerji / coşku | hareketlilik puanı 74/100 (tempo 116 BPM, saniyede 4,3 olay). Projedeki sürümlerle karşılaştırma (hareketlilik puanı: 'coşkulu' adlı 6 sürümde 66…79, 'yavaş' adlı 3 sürümde 52…61). |
| ✅ iyi | Vokal / altyapı dengesi | vokal altyapıdan -3,4 dB (medyan); sürenin %58 kadarında vokal var. Vokal-altyapı dengesi olağan aralıkta. |
| ✅ iyi | Vokal altyapıyla aynı armonide mi | armonik destek farkı +0,231 (artı = uyumlu); en iyi kaydırma +0 yarım ses (0 olmalı). |
| ℹ️ bilgi | Gam içi söyleme | söylenen sürenin %84 kadarı altyapının gamında (La majör (A major)) — ton belirsiz, bu oran güvenilmez; akor sesi %66, gam dışı %13. |
| ✅ iyi | Akort (detone mi) | notalara uzaklık medyan 8,6 cent; söylenen sürenin %89 kadarı ±25 cent içinde; vokalin genel kayması -8 cent. |
| ⚠️ dikkat | Çakışan uzun notalar | 1 / 38 uzun nota (0,3 sn üstü) altyapıyla çakışıyor ya da detone. |
| ❌ sorun | Ritme oturma | sıkılık R=0,29 (ölçümün tavanı ≈0,65; rastgele ≈0,15); başlangıçların %49 kadarı en yakın sekizliğe 40 ms içinde; ortalama kayma +19 ms (+ geç). Vokal başlangıçları ızgarayla ilişkisiz görünüyor (ritme oturmuyor YA DA vuruş ızgarası yanlış bulundu) (vuruş ızgarası: otomatik (altyapıdan)). |
| ⚠️ dikkat | Yapaylık işaretleri (vekil) | 2 işaret: notaların içi çok düz (medyan 5.3 cent): sert akort düzeltme / vokoderle sabitlenmiş perde izlenimi; bağlı notalar arası geçişler ani (16 ms medyan; aynı ölçümle doğal vokalde ~32 ms): basamaklı perde. |

Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.

## Bu raporun SÖYLEYEMEDİKLERİ

- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; konuşma için eğitilmiş modeller şarkıda güvenilmezdir.
- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).
- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.
- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.

## Ayrıntılar

**Dosya:** 110,1 sn, 2 kanal, 48000 Hz, mp3, 192 kb/sn; üst frekans sınırı 18733 Hz. Kanal kaynağı: verilen dosyalar (--vokal / --altyapi).

**Ses düzeyi:** -12,8 LUFS; ses yüksekliği aralığı (LRA) 3,0 LU; gerçek tepe 1,1 dBTP; tepe faktörü 16,1 dB. Stereo: olağan stereo (sol-sağ ilişkisi 0,89).

**Enerji:** tempo 116,0 BPM (otomatik tahmin; yarı/çift tempo hatası yapabilir); yerel temponun %100 kadarı ±%3 içinde; nabız netliği 0,83; olay yoğunluğu 4,3/sn; vurmalı/armonik 0,5 dB; spektral akı 1,89; parlaklık (ağırlık merkezi) 2612 Hz; düzey oynaklığı 1,7 dB.
Hareketlilik puanı bileşenleri (0-1): olay_yogunlugu_sn 0,51, nabiz_netligi 1,00, vurmali_armonik_db 1,00, spektral_aki_ort 0,61, parlaklik_agirlik_merkezi_hz 0,59.

**Ton (altyapı kanalı):** 0–110 sn La majör (A major) (belirsiz). Akort kayması 5,0 cent. En çok duyulan akorlar: A 52 sn, Am 51 sn, C#m 2 sn, F 2 sn, Em 1 sn (ortalama güven 0,68).

**Vokal perdesi:** 144 nota; ses aralığı C4–F4 (4,9 yarım ses), medyan E4; nota içi oynaklık medyan 5,3 cent; çok düz nota oranı 0,47; vibratolu uzun nota oranı 0,00; geçiş çerçevesi oranı 0,11. Perde izleyici denetimi: pYIN ile %96 uyum.
Vokalin kendi ses dağılımından ton tahmini: Mi minör (E minor) (r=0,62).

**Çakışan / detone uzun notalar:**

| sn | süre | nota | akor | tür |
|---|---|---|---|---|
| 65,4 | 0,51 | D4 | A | akor sesine yarim ses komsu |

**Yapaylık için vekil ölçümler (kanıt değil):** nota içi oynaklık 5,3 cent; ızgaraya yapışma R 0,76; donmuş ünlü 0 adet (sesli sürenin %0 kadarı); ünsüzlerde tiz payı -10,4 dB; vokalin üst frekansı 10723 Hz; tiz doku değişim katsayısı 1,48 (durağan gürültü ≈0,52); zarf titremesi -11,2 dB.

_Çalışma süresi: 22 sn. Bütün sayılar: `rapor.json`._
