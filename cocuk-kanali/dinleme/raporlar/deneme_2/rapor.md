# Dinleme raporu: deneme_2.mp3

_2026-11-21 19:16:49 — dinle.py 1.0 (2026-11-21). Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._

## Özet

| Durum | Konu | Makinenin gördüğü |
|---|---|---|
| ✅ iyi | Ses yüksekliği | -11,8 LUFS, gerçek tepe -0,4 dBTP. |
| ✅ iyi | Enerji / coşku | hareketlilik puanı 67/100 (tempo 130 BPM, saniyede 3,9 olay); MusicCoCa coşku farkı +0,11; CED 'ninni' olasılığı 0,000 → makine göstergeleri coşkulu yana yakın. Projedeki sürümlerle karşılaştırma (hareketlilik puanı: 'coşkulu' adlı 6 sürümde 66…79, 'yavaş' adlı 3 sürümde 52…61; MusicCoCa coşku farkı: 'coşkulu' adlı 6 sürümde +0,09…+0,22, 'yavaş' adlı 3 sürümde -0,10…-0,08). |
| ✅ iyi | Sözler | sözcük hata oranı %1,0 (99 beklenen sözcükten 1 farklı, 0 eksik, 0 fazla); küçük ek/harf farkları sayılmazsa %0,0. |
| ℹ️ bilgi | Söyleyiş hızı | söz öbeklerinde medyan 2,5 hece/sn (en hızlı 3,1). |

Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.

## Bu raporun SÖYLEYEMEDİKLERİ

- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; konuşma için eğitilmiş modeller şarkıda güvenilmezdir.
- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).
- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.
- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.
- **Perde, uyum, ritim, yapaylık:** bu çalıştırmada ölçülmedi (vokal kanalı yok). `--ayir` ya da `--vokal/--altyapi` ile yeniden çalıştırın.

## Ayrıntılar

**Dosya:** 95,4 sn, 2 kanal, 48000 Hz, mp3, 192 kb/sn; üst frekans sınırı 18766 Hz. Kanal kaynağı: yok (yalnızca karışım ölçüldü; perde / uyum / ritim / doğallık için --ayir ya da --vokal/--altyapi verin).

**Ses düzeyi:** -11,8 LUFS; ses yüksekliği aralığı (LRA) 2,5 LU; gerçek tepe -0,4 dBTP; tepe faktörü 15,6 dB. Stereo: olağan stereo (sol-sağ ilişkisi 0,51).

**Enerji:** tempo 129,9 BPM (otomatik tahmin; yarı/çift tempo hatası yapabilir); yerel temponun %100 kadarı ±%3 içinde; nabız netliği 0,73; olay yoğunluğu 3,9/sn; vurmalı/armonik -3,1 dB; spektral akı 1,63; parlaklık (ağırlık merkezi) 2610 Hz; düzey oynaklığı 3,9 dB.
Hareketlilik puanı bileşenleri (0-1): olay_yogunlugu_sn 0,42, nabiz_netligi 1,00, vurmali_armonik_db 0,92, spektral_aki_ort 0,46, parlaklik_agirlik_merkezi_hz 0,59.

**CED etiketleri (karışım):** Music 0,84, Music for children 0,65, Jingle (music) 0,21, Christmas music 0,15, Singing 0,10, Christian music 0,04, Exciting music 0,03, Happy music 0,02.

**Ton (karışım; vokal dahil olduğu için ton/akor daha az güvenilir):** 0–24 sn La majör (A major) (belirsiz); 24–95 sn Re majör (D major) (belirsiz). Akort kayması 4,0 cent. En çok duyulan akorlar: D 44 sn, A 27 sn, G 8 sn, Gm 7 sn, F#m 4 sn (ortalama güven 0,71).

**Makinenin duyduğu sözler (Scribe, dil tur olasılık 1,00):**

> [neşeli müzik] Bin, bin, bin. Otobüse bin. Pıtır şoför haydi yola. Hop, hop, hop. Durağa geldik. Pıtır kapıyı açtı. Hop, hop, hop. Hepimiz bindik. Hazırız, haydi Pıtır. Fır fır fır teker dönüyor. Pıtır direksiyonda. Fır fır fır hızlanıyoruz. Yollar bizi bekliyor. Bin, bin, bin. Otobüse bin. Pıtır şoför haydi yola. Düt, düt, düt. Bu ses neden? Pıtır kornaya bastı. Düt, düt, düt. Herkes duyuyor. Yol verin geliyoruz. Şıp, şıp, şıp. Yağmur yağıyor. Silecek sağa sola. Şıp, şıp, şıp. Pıtır gülüyor. Yağmur bizi durdurmaz. Bin, bin, bin. Otobüse bin. Pıtır şoför haydi yola. Otobüs durdu. Hoşça kal Pıtır. Güle güle, güle güle. [neşeli müzik]

Ses olayları: [neşeli müzik] 0,5–4,1 sn, [neşeli müzik] 91,6–95,4 sn.

**Söz farkları:**

| sn | beklenen | duyulan | tür |
|---|---|---|---|
| 50,8 | nereden | neden? | küçük fark (ek/harf) |

_Çalışma süresi: 20 sn. Bütün sayılar: `rapor.json`._
