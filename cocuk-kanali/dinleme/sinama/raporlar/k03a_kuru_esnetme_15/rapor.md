# Dinleme raporu: k03a_kuru_esnetme_15.wav

_2026-11-21 17:37:56 — dinle.py 1.0 (2026-11-21). Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._

## Özet

| Durum | Konu | Makinenin gördüğü |
|---|---|---|
| ⚠️ dikkat | Ses yüksekliği | -19,9 LUFS, gerçek tepe -4,7 dBTP (YouTube yaklaşık -14 LUFS'e çeker; kısık kalır). |
| ⚠️ dikkat | Sessizlik | başta 9,2 sn, sonda 1,4 sn, içeride 8 boşluk. |
| ⚠️ dikkat | Enerji / coşku | hareketlilik puanı 53/100 (tempo 146 BPM, saniyede 3,5 olay); CED 'ninni' olasılığı 0,010 → **ninni/sakin yana kayıyor olabilir**. Projedeki sürümlerle karşılaştırma (hareketlilik puanı: 'coşkulu' adlı 6 sürümde 66…79, 'yavaş' adlı 3 sürümde 52…61). |
| ℹ️ bilgi | Uyum | altyapı olmadığı için vokal-altyapı uyumu ölçülmedi (yalnızca vokalin kendi perdesi ölçüldü). |
| ℹ️ bilgi | Yapaylık işaretleri (vekil) | işaret bulunmadı — bu 'doğal' demek DEĞİLDİR, yalnızca bilinen kaba izler yok. |

Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.

## Bu raporun SÖYLEYEMEDİKLERİ

- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; konuşma için eğitilmiş modeller şarkıda güvenilmezdir.
- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).
- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.
- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.

## Ayrıntılar

**Dosya:** 165,2 sn, 1 kanal, 44100 Hz, pcm_s16le, 706 kb/sn; üst frekans sınırı 17635 Hz. Kanal kaynağı: dosyanin kendisi (--kuru).

**Ses düzeyi:** -19,9 LUFS; ses yüksekliği aralığı (LRA) 8,8 LU; gerçek tepe -4,7 dBTP; tepe faktörü 18,3 dB. Stereo: tek kanal (mono) dosya (sol-sağ ilişkisi ?).

**Enerji:** tempo 146,3 BPM (otomatik tahmin; yarı/çift tempo hatası yapabilir); yerel temponun %15 kadarı ±%3 içinde; nabız netliği 0,37; olay yoğunluğu 3,5/sn; vurmalı/armonik -7,1 dB; spektral akı 1,76; parlaklık (ağırlık merkezi) 2810 Hz; düzey oynaklığı 5,3 dB.
Hareketlilik puanı bileşenleri (0-1): olay_yogunlugu_sn 0,34, nabiz_netligi 0,53, vurmali_armonik_db 0,64, spektral_aki_ort 0,53, parlaklik_agirlik_merkezi_hz 0,67.

**CED etiketleri (karışım):** Music 0,37, Female singing 0,22, Silence 0,12, Speech 0,08, Singing 0,06, Synthetic singing 0,06, Male singing 0,05, Child singing 0,05.
Hayvan sınıfları: Meow 0,008.

**Vokal perdesi:** 149 nota; ses aralığı C4–F4 (5,0 yarım ses), medyan E4; nota içi oynaklık medyan 8,2 cent; çok düz nota oranı 0,13; vibratolu uzun nota oranı 0,19; geçiş çerçevesi oranı 0,07. Perde izleyici denetimi: pYIN ile %99 uyum.
Vokalin kendi ses dağılımından ton tahmini: Mi minör (E minor) (r=0,64).

**Yapaylık için vekil ölçümler (kanıt değil):** nota içi oynaklık 8,2 cent; ızgaraya yapışma R ?; donmuş ünlü 0 adet (sesli sürenin %0 kadarı); ünsüzlerde tiz payı -11,7 dB; vokalin üst frekansı 10723 Hz; tiz doku değişim katsayısı 1,49 (durağan gürültü ≈0,52); zarf titremesi -14,5 dB.

**Konuşma-kalitesi tahminleri (vokal kanalı, 1-5; şarkı için eğitilmediler):** DNSMOS 2,15 (sinyal 2,72, arka plan 2,82); NISQA 2,47 (gürültüsüzlük 2,75, kesintisizlik 3,87, renklenmezlik 3,09); Distill-MOS 2,61; UTMOS22 1,35. Yalnızca aynı yolla elde edilmiş iki vokali karşılaştırmak için.
CED, vokal kanalını şöyle etiketliyor: şarkı 0,06, konuşma 0,08, sentetik şarkı 0,057, konuşma sentezleyici 0,003.

_Çalışma süresi: 56 sn. Bütün sayılar: `rapor.json`._
