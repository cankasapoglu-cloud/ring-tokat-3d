# Dinleme raporu: ornek_kita1.mp3

_2026-11-21 15:57:09 — dinle.py 1.0 (2026-11-21). Bu rapor ölçüm ve makine tahminidir; **insan kulağı değildir**. Son karar dinleyen insanındır._

## Özet

| Durum | Konu | Makinenin gördüğü |
|---|---|---|
| ✅ iyi | Ses yüksekliği | -14,6 LUFS, gerçek tepe -1,4 dBTP. |
| ⚠️ dikkat | Enerji / coşku | hareketlilik puanı 59/100 (tempo 134 BPM, saniyede 4,1 olay); MusicCoCa coşku farkı +0,28; CED 'ninni' olasılığı 0,000 → **ninni/sakin yana kayıyor olabilir**. Projedeki sürümlerle karşılaştırma (hareketlilik puanı: 'coşkulu' adlı 6 sürümde 66…79, 'yavaş' adlı 3 sürümde 52…61; MusicCoCa coşku farkı: 'coşkulu' adlı 6 sürümde +0,09…+0,22, 'yavaş' adlı 3 sürümde -0,10…-0,08). |
| ❌ sorun | Sözler | sözcük hata oranı %100,0 (13 beklenen sözcükten 10 farklı, 3 eksik, 0 fazla); küçük ek/harf farkları sayılmazsa %100,0. |
| ℹ️ bilgi | Söyleyiş hızı | söz öbeklerinde medyan 4,5 hece/sn (en hızlı 5,9). |

Eşikler kabadır (kalibre edilmedi): **iki sürümü aynı araçla ölçüp karşılaştırmak**, tek sürüme not vermekten daha güvenilirdir.

## Bu raporun SÖYLEYEMEDİKLERİ

- **Ses kulağa hoş / doğal mı?** Ölçülemez. Aşağıdaki 'yapaylık işaretleri' ve kalite tahminleri yalnızca kaba izleri yakalar; konuşma için eğitilmiş modeller şarkıda güvenilmezdir.
- **Türkçe doğal mı, yabancı aksan var mı?** Ölçülemez. Döküm temiz çıksa bile aksan olabilir (tanıma modeli doğru sözcüğü yazar).
- **Çocuk sever mi, coşku 'gerçek' mi?** Ölçülemez. Enerji göstergeleri hareketliliği sayar, duyguyu değil.
- **Ezgi doğru ezgi mi?** Bu araç vokalin altyapıyla uyumunu ölçer; 'istenen ezgi' ile karşılaştırma yapmaz.
- **Perde, uyum, ritim, yapaylık:** bu çalıştırmada ölçülmedi (vokal kanalı yok). `--ayir` ya da `--vokal/--altyapi` ile yeniden çalıştırın.

## Ayrıntılar

**Dosya:** 27,3 sn, 1 kanal, 48000 Hz, mp3, 192 kb/sn; üst frekans sınırı 20456 Hz. Kanal kaynağı: yok (yalnızca karışım ölçüldü; perde / uyum / ritim / doğallık için --ayir ya da --vokal/--altyapi verin).

**Ses düzeyi:** -14,6 LUFS; ses yüksekliği aralığı (LRA) 1,7 LU; gerçek tepe -1,4 dBTP; tepe faktörü 13,3 dB. Stereo: tek kanal (mono) dosya (sol-sağ ilişkisi ?).

**Enerji:** tempo 134,5 BPM (otomatik tahmin; yarı/çift tempo hatası yapabilir); yerel temponun %100 kadarı ±%3 içinde; nabız netliği 0,58; olay yoğunluğu 4,1/sn; vurmalı/armonik -6,3 dB; spektral akı 1,43; parlaklık (ağırlık merkezi) 2464 Hz; düzey oynaklığı 0,5 dB.
Hareketlilik puanı bileşenleri (0-1): olay_yogunlugu_sn 0,46, nabiz_netligi 0,96, vurmali_armonik_db 0,69, spektral_aki_ort 0,35, parlaklik_agirlik_merkezi_hz 0,53.

**CED etiketleri (karışım):** Cattle, bovinae 0,59, Moo 0,59, Livestock, farm animals, working animals 0,57, Music 0,37, Jingle, tinkle 0,14, Music for children 0,12, Ding 0,09, Singing 0,03.
Hayvan sınıfları: Cattle, bovinae 0,591, Moo 0,587, Animal 0,001.

**Ton (karışım; vokal dahil olduğu için ton/akor daha az güvenilir):** 0–27 sn Sol majör (G major). Akort kayması 5,0 cent. En çok duyulan akorlar: G 18 sn, C 4 sn, D 3 sn, Gm 1 sn, D# 0 sn (ortalama güven 0,80).

**Makinenin duyduğu sözler (Scribe, dil tur olasılık 1,00):**

> [müzik] Maliboku yeşil boya. Çimdikle inek yürü. [inek sesi] Bir yağıdır çimdikle maliboku

Ses olayları: [müzik] 0,0–2,7 sn, [inek sesi] 15,6–21,4 sn.

Makinenin emin olamadığı sözcükler (belirsiz söylenmiş olabilir): 'Maliboku' 7,2 sn, 'Çimdikle' 12,6 sn, 'inek' 14,4 sn, 'Bir' 21,5 sn, 'yağıdır' 21,7 sn.

**Söz farkları:**

| sn | beklenen | duyulan | tür |
|---|---|---|---|
| 7,2 | Ali | Maliboku | başka sözcük |
| 9,1 | çiftliği | yeşil | başka sözcük |
| 9,6 | var | boya. | başka sözcük |
| 12,6 | Çiftliğinde | Çimdikle | başka sözcük |
| 14,4 | inekleri | inek | başka sözcük |
| 15,0 | var | yürü. | başka sözcük |
| 21,5 | diye | Bir | başka sözcük |
| 21,7 | bağırır | yağıdır | başka sözcük |
| 23,3 | Çiftliğinde | çimdikle | başka sözcük |
| 25,1 | Ali | maliboku | başka sözcük |
| ~7,2 | Baba'nın | — | eksik |
| ~7,2 | bir | — | eksik |
| ~25,1 | Baba'nın | — | eksik |

## Panolar (Read aracıyla bakın)

| Dosya | Ne gösterir | Neye bakmalı |
|---|---|---|
| `00_genel_bakis.png` | bütün dosya: spektrogram, düzeyler, hareketlilik, sorun çizelgesi (0–27 sn) | kırmızı X / şeritlerin toplandığı yer; hareketliliğin düştüğü bölümler |
| `01_pano_000-027sn.png` | 30 sn: spektrogram + sözcükler, vokal spektrogramı, vuruşlar, düzey (0–27 sn) | ≠ işaretli sözcükler; vokal çizgisinin altyapının altında kaldığı yerler |

_Çalışma süresi: 10 sn. Bütün sayılar: `rapor.json`._
