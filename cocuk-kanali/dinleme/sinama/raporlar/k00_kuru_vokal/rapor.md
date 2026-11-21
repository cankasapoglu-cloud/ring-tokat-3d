# Dinleme raporu: k00_kuru_vokal.wav

_2026-11-21 17:37:12 — dinle.py 1.0 (2026-11-21). Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._

## Özet

| Durum | Konu | Makinenin gördüğü |
|---|---|---|
| ⚠️ dikkat | Ses yüksekliği | -20,0 LUFS, gerçek tepe -3,9 dBTP (YouTube yaklaşık -14 LUFS'e çeker; kısık kalır). |
| ⚠️ dikkat | Sessizlik | başta 6,2 sn, sonda 1,0 sn, içeride 8 boşluk. |
| ℹ️ bilgi | Enerji / coşku | hareketlilik puanı 64/100 (tempo 117 BPM, saniyede 4,8 olay); CED 'ninni' olasılığı 0,000. Projedeki sürümlerle karşılaştırma (hareketlilik puanı: 'coşkulu' adlı 6 sürümde 66…79, 'yavaş' adlı 3 sürümde 52…61). |
| ℹ️ bilgi | Uyum | altyapı olmadığı için vokal-altyapı uyumu ölçülmedi (yalnızca vokalin kendi perdesi ölçüldü). |
| ℹ️ bilgi | Yapaylık işaretleri (vekil) | işaret bulunmadı — bu 'doğal' demek DEĞİLDİR, yalnızca bilinen kaba izler yok. |

Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.

## Bu raporun SÖYLEYEMEDİKLERİ

- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; konuşma için eğitilmiş modeller şarkıda güvenilmezdir.
- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).
- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.
- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.

## Ayrıntılar

**Dosya:** 110,1 sn, 1 kanal, 44100 Hz, pcm_s16le, 706 kb/sn; üst frekans sınırı 17635 Hz. Kanal kaynağı: dosyanin kendisi (--kuru).

**Ses düzeyi:** -20,0 LUFS; ses yüksekliği aralığı (LRA) 9,5 LU; gerçek tepe -3,9 dBTP; tepe faktörü 18,9 dB. Stereo: tek kanal (mono) dosya (sol-sağ ilişkisi ?).

**Enerji:** tempo 116,7 BPM (otomatik tahmin; yarı/çift tempo hatası yapabilir); yerel temponun %49 kadarı ±%3 içinde; nabız netliği 0,32; olay yoğunluğu 4,8/sn; vurmalı/armonik -5,7 dB; spektral akı 2,17; parlaklık (ağırlık merkezi) 2794 Hz; düzey oynaklığı 4,0 dB.
Hareketlilik puanı bileşenleri (0-1): olay_yogunlugu_sn 0,63, nabiz_netligi 0,44, vurmali_armonik_db 0,74, spektral_aki_ort 0,76, parlaklik_agirlik_merkezi_hz 0,66.

**CED etiketleri (karışım):** Music 0,46, Silence 0,12, Echo 0,09, Singing 0,08, Speech 0,07, Sound effect 0,05, A capella 0,04, Female singing 0,03.

**Vokal perdesi:** 128 nota; ses aralığı C4–F4 (5,0 yarım ses), medyan E4; nota içi oynaklık medyan 11,2 cent; çok düz nota oranı 0,03; vibratolu uzun nota oranı 0,15; geçiş çerçevesi oranı 0,18. Perde izleyici denetimi: pYIN ile %94 uyum.
Vokalin kendi ses dağılımından ton tahmini: Mi minör (E minor) (r=0,64).

**Yapaylık için vekil ölçümler (kanıt değil):** nota içi oynaklık 11,2 cent; ızgaraya yapışma R ?; donmuş ünlü 0 adet (sesli sürenin %0 kadarı); ünsüzlerde tiz payı -11,1 dB; vokalin üst frekansı 10723 Hz; tiz doku değişim katsayısı 1,42 (durağan gürültü ≈0,52); zarf titremesi -9,1 dB.

**Konuşma-kalitesi tahminleri (vokal kanalı, 1-5; şarkı için eğitilmediler):** DNSMOS 2,72 (sinyal 3,30, arka plan 3,39); NISQA 2,88 (gürültüsüzlük 3,48, kesintisizlik 4,41, renklenmezlik 3,42); Distill-MOS 3,41; UTMOS22 1,49. Yalnızca aynı yolla elde edilmiş iki vokali karşılaştırmak için.
CED, vokal kanalını şöyle etiketliyor: şarkı 0,08, konuşma 0,07, sentetik şarkı 0,021, konuşma sentezleyici 0,005.

_Çalışma süresi: 42 sn. Bütün sayılar: `rapor.json`._
