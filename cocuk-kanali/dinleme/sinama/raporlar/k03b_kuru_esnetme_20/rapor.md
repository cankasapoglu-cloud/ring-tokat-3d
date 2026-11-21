# Dinleme raporu: k03b_kuru_esnetme_20.wav

_2026-11-21 17:38:55 — dinle.py 1.0 (2026-11-21). Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._

## Özet

| Durum | Konu | Makinenin gördüğü |
|---|---|---|
| ⚠️ dikkat | Ses yüksekliği | -19,8 LUFS, gerçek tepe -3,7 dBTP (YouTube yaklaşık -14 LUFS'e çeker; kısık kalır). |
| ⚠️ dikkat | Sessizlik | başta 12,3 sn, sonda 1,9 sn, içeride 9 boşluk. |
| ⚠️ dikkat | Enerji / coşku | hareketlilik puanı 47/100 (tempo 117 BPM, saniyede 3,0 olay); CED 'ninni' olasılığı 0,022 → **ninni/sakin yana kayıyor olabilir**. Projedeki sürümlerle karşılaştırma (hareketlilik puanı: 'coşkulu' adlı 6 sürümde 66…79, 'yavaş' adlı 3 sürümde 52…61). |
| ℹ️ bilgi | Uyum | altyapı olmadığı için vokal-altyapı uyumu ölçülmedi (yalnızca vokalin kendi perdesi ölçüldü). |
| ℹ️ bilgi | Yapaylık işaretleri (vekil) | işaret bulunmadı — bu 'doğal' demek DEĞİLDİR, yalnızca bilinen kaba izler yok. |

Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.

## Bu raporun SÖYLEYEMEDİKLERİ

- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; konuşma için eğitilmiş modeller şarkıda güvenilmezdir.
- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).
- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.
- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.

## Ayrıntılar

**Dosya:** 220,2 sn, 1 kanal, 44100 Hz, pcm_s16le, 706 kb/sn; üst frekans sınırı 17635 Hz. Kanal kaynağı: dosyanin kendisi (--kuru).

**Ses düzeyi:** -19,8 LUFS; ses yüksekliği aralığı (LRA) 8,0 LU; gerçek tepe -3,7 dBTP; tepe faktörü 19,2 dB. Stereo: tek kanal (mono) dosya (sol-sağ ilişkisi ?).

**Enerji:** tempo 116,6 BPM (otomatik tahmin; yarı/çift tempo hatası yapabilir); yerel temponun %31 kadarı ±%3 içinde; nabız netliği 0,38; olay yoğunluğu 3,0/sn; vurmalı/armonik -8,5 dB; spektral akı 1,69; parlaklık (ağırlık merkezi) 2753 Hz; düzey oynaklığı 4,4 dB.
Hareketlilik puanı bileşenleri (0-1): olay_yogunlugu_sn 0,21, nabiz_netligi 0,57, vurmali_armonik_db 0,54, spektral_aki_ort 0,49, parlaklik_agirlik_merkezi_hz 0,65.

**CED etiketleri (karışım):** Music 0,33, Female singing 0,20, Silence 0,12, Synthetic singing 0,08, Singing 0,07, Male singing 0,06, A capella 0,04, Child singing 0,04.
Hayvan sınıfları: Meow 0,004.

**Vokal perdesi:** 179 nota; ses aralığı C4–F4 (5,0 yarım ses), medyan E4; nota içi oynaklık medyan 9,5 cent; çok düz nota oranı 0,11; vibratolu uzun nota oranı 0,12; geçiş çerçevesi oranı 0,08. Perde izleyici denetimi: pYIN ile %99 uyum.
Vokalin kendi ses dağılımından ton tahmini: Mi minör (E minor) (r=0,64).

**Yapaylık için vekil ölçümler (kanıt değil):** nota içi oynaklık 9,5 cent; ızgaraya yapışma R ?; donmuş ünlü 4 adet (sesli sürenin %3 kadarı); ünsüzlerde tiz payı -11,2 dB; vokalin üst frekansı 10723 Hz; tiz doku değişim katsayısı 1,55 (durağan gürültü ≈0,52); zarf titremesi -16,6 dB.

**Konuşma-kalitesi tahminleri (vokal kanalı, 1-5; şarkı için eğitilmediler):** DNSMOS 2,42 (sinyal 3,07, arka plan 3,00); NISQA 3,06 (gürültüsüzlük 2,96, kesintisizlik 4,36, renklenmezlik 3,49); Distill-MOS 3,17; UTMOS22 1,38. Yalnızca aynı yolla elde edilmiş iki vokali karşılaştırmak için.
CED, vokal kanalını şöyle etiketliyor: şarkı 0,07, konuşma 0,04, sentetik şarkı 0,078, konuşma sentezleyici 0,001.

_Çalışma süresi: 69 sn. Bütün sayılar: `rapor.json`._
