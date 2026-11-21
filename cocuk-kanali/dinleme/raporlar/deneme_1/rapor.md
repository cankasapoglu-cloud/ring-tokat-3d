# Dinleme raporu: deneme_1.mp3

_2026-11-21 19:15:31 — dinle.py 1.0 (2026-11-21). Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._

## Özet

| Durum | Konu | Makinenin gördüğü |
|---|---|---|
| ✅ iyi | Ses yüksekliği | -13,4 LUFS, gerçek tepe -1,3 dBTP. |
| ⚠️ dikkat | Sessizlik | başta 2,0 sn, sonda 1,9 sn, içeride 0 boşluk. |
| ℹ️ bilgi | Enerji / coşku | hareketlilik puanı 66/100 (tempo 120 BPM, saniyede 4,8 olay); MusicCoCa coşku farkı +0,01; CED 'ninni' olasılığı 0,006. Projedeki sürümlerle karşılaştırma (hareketlilik puanı: 'coşkulu' adlı 6 sürümde 66…79, 'yavaş' adlı 3 sürümde 52…61; MusicCoCa coşku farkı: 'coşkulu' adlı 6 sürümde +0,09…+0,22, 'yavaş' adlı 3 sürümde -0,10…-0,08). |
| ✅ iyi | Sözler | sözcük hata oranı %2,0 (99 beklenen sözcükten 1 farklı, 0 eksik, 1 fazla); küçük ek/harf farkları sayılmazsa %2,0. |
| ℹ️ bilgi | Söyleyiş hızı | söz öbeklerinde medyan 3,0 hece/sn (en hızlı 4,1). |

Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.

## Bu raporun SÖYLEYEMEDİKLERİ

- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; konuşma için eğitilmiş modeller şarkıda güvenilmezdir.
- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).
- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.
- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.
- **Perde, uyum, ritim, yapaylık:** bu çalıştırmada ölçülmedi (vokal kanalı yok). `--ayir` ya da `--vokal/--altyapi` ile yeniden çalıştırın.

## Ayrıntılar

**Dosya:** 95,4 sn, 2 kanal, 48000 Hz, mp3, 192 kb/sn; üst frekans sınırı 16397 Hz. Kanal kaynağı: yok (yalnızca karışım ölçüldü; perde / uyum / ritim / doğallık için --ayir ya da --vokal/--altyapi verin).

**Ses düzeyi:** -13,4 LUFS; ses yüksekliği aralığı (LRA) 6,2 LU; gerçek tepe -1,3 dBTP; tepe faktörü 13,8 dB. Stereo: olağan stereo (sol-sağ ilişkisi 0,83).

**Enerji:** tempo 120,1 BPM (otomatik tahmin; yarı/çift tempo hatası yapabilir); yerel temponun %100 kadarı ±%3 içinde; nabız netliği 0,66; olay yoğunluğu 4,8/sn; vurmalı/armonik -5,5 dB; spektral akı 1,71; parlaklık (ağırlık merkezi) 1959 Hz; düzey oynaklığı 5,2 dB.
Hareketlilik puanı bileşenleri (0-1): olay_yogunlugu_sn 0,63, nabiz_netligi 1,00, vurmali_armonik_db 0,75, spektral_aki_ort 0,51, parlaklik_agirlik_merkezi_hz 0,32.

**CED etiketleri (karışım):** Music 0,86, Disco 0,25, Jingle (music) 0,13, Choir 0,11, Electronic music 0,10, Gospel music 0,09, Christmas music 0,08, Dance music 0,08.

**Ton (karışım; vokal dahil olduğu için ton/akor daha az güvenilir):** 0–95 sn Do diyez minör (C# minor) (belirsiz). Akort kayması -11,0 cent. En çok duyulan akorlar: Cm 48 sn, A 20 sn, G# 8 sn, Bm 8 sn, F# 8 sn (ortalama güven 0,57).

**Makinenin duyduğu sözler (Scribe, dil tur olasılık 1,00):**

> [müzik] Bin bin bin otobüse bin. Pıtır şoför haydi yola. Hop hop hop. Durağa geldik. Pıtır kapıyı açtı. Hop hop hop. Hepimiz bindik. Hazırız haydi pıtıııv. Fır fır fır teker dönüyor. Pıtır direksiyonda. Fır fır fır hızlanıyoruz. Yollar bizi bekliyor. Bin bin bin otobüse bin. Pıtır şoför haydi yola. Düt düt düt. Bu ses nereden? Pıtır kornaya bastı. Düt düt düt herkes duyuyor. Yol verin geliyoruz. Şıp şıp şıp. Yağmur yağıyor. Silecek sağa sola. Şıp şıp şıp şıp. Pıtır gülüyor. Yağmur bizi durdurmaz. Bin bin bin otobüse bin. Pıtır şoför haydi yola. Otobüs durdu. Hoşça kal Pıtır. Güle güle. Güle güle.

Ses olayları: [müzik] 2,0–3,9 sn.

Makinenin emin olamadığı sözcükler (belirsiz söylenmiş olabilir): 'herkes' 57,0 sn.

**Söz farkları:**

| sn | beklenen | duyulan | tür |
|---|---|---|---|
| 24,2 | Pıtır | pıtıııv. | başka sözcük |
| 70,5 | — | şıp. | fazla |

_Çalışma süresi: 77 sn. Bütün sayılar: `rapor.json`._
