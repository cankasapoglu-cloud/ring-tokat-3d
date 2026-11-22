# Hailuo web sitesi (ücretsiz kota) denemesi: sonuç

Tarih: 22.11.2026. Kullanıcının Chrome'unda, açık olan hailuoai.video oturumuyla yapıldı.
Klip: `03-hailuo.mp4`. Başlangıç karesi: `../ali-baba/kare/03.png`. Komut: GOREV.md'deki İngilizce metin.

## Kota ve harcama
- Hesap **Ücretsiz** planda. Başlangıçta **80 kredi** vardı.
- Bu klip **35 kredi** harcadı, **45 kredi** kaldı. Kalan krediyle ancak 1 klip daha üretilir.
- Ücret ayara göre değişiyor. Varsayılan 21:9, 2K, 5 sn klip 60 kredi. 16:9, 768p, 5 sn klip 35 kredi.
- Kredilerin her gün yenilenip yenilenmediğini doğrulamadım.

## Model ve ayarlar
- Ücretsiz hesapta açık olan **tek model MiniMax H3**. Hailuo 2.3, 2.3-Hızlı, 2.0, Veo ve Sora menüde gri, seçilemiyor.
- Ayarlar: Başlangıç/Bitiş Karesi modu, oran otomatik (16:9), 768p, 5 saniye.
- Ödeme, abonelik ya da kredi satın alma adımı çıkmadı.

## Üretim ve dosya
- Üretim yaklaşık **2–2,5 dakika** sürdü. Kuyrukta bekleme olmadı: 75. saniyede %47, 2. dakikada %95'ti.
- Klip **5,17 sn**, **1344x768**, 24 fps, H.264, yaklaşık 1 MB.
- Klipte **ses de var**: AAC stereo, ortalama -15 dB. H3 kendi sesini ekliyor. Şarkıya eklerken sesi kapatmak gerekir.

## Filigran
- **Var.** Sağ alt köşede, bütün klip boyunca "MINIMAX | Hailuo AI" yazıyor: beyaz, yarı saydam, karenin genişliğinin yaklaşık %25'i.
- Filigransız indirme ücretli planda. Ücretsiz hesapta bu seçenek denenmedi.

## Kalite: `ali-baba/klip/03.mp4` (Kling, ElevenLabs) ile karşılaştırma
| | Hailuo web (H3) | Kling (`klip/03.mp4`) | MiniMax API, Hailuo 2.3 Fast (`minimax-deneme-inek.mp4`) |
|---|---|---|---|
| Çözünürlük, süre | 1344x768, 5,17 sn | 1920x1080, 5,04 sn | 1364x768, 5,88 sn |
| Karakter tutarlılığı | İnek aynı kaldı, sahne aynı | İnek aynı kaldı | İnek aynı ama sahneye iki kedi ekledi |
| Ağız, "möö" hareketi | Ağız 2 kez geniş açılıp kapanıyor, istenen buydu | Ağız yalnızca sonda bir kez açılıyor | Sonda ağız açık gülüyor |
| Dişler | Görünmüyor | Üst dişler hafifçe görünüyor | Üst dişler görünüyor |
| Kafa, kulak | Kafa sallanıyor, kulaklar oynuyor, kamera hafifçe yaklaşıyor | Kafa eğiliyor, gözler kısılıyor | Kamera geri çekiliyor |
| Kusur | Başta bir göz kırpma var, filigran var | Belirgin kusur yok | Komutta olmayan karakterler |
| Filigran | Var | Yok | Yok |

Kısaca: hareket ve komuta uyum açısından H3 klibi bu sahnede Kling'den daha iyi. Ama klip filigranlı ve 768p. Kling klibi 1080p ve temiz.

## Otomatik kullanımda takılınan yerler
- Menüler (model, mod, oran/süre) tıklayınca değil, **fare üzerine gelince** açılıyor. Önce farenin başka yere götürülmesi gerekiyor. JavaScript ile tıklama ayarları değiştirmedi, gerçek fare tıklaması gerekti.
- Varsayılan "Omni Referans" modunda diğer modeller kapalı. "Başlangıç/Bitiş Çerçevesi" moduna geçince de ücretsiz hesapta açılmadılar.
- **Dosya yükleme sorunsuz.** Gizli dosya alanına doğrudan yüklendi.
- **İndirme:** Chrome dosyayı `İndirilenler` klasörüne `.tmp` adıyla indirdi ve orada bekletti (muhtemelen bir kaydetme onayı bekliyor). Dosya eksiksizdi, buradan kopyalandı.
- Robot doğrulaması ya da giriş ekranı çıkmadı.
- Site, komutu ekranda Türkçeye çevirerek gösteriyor. Modele hangi dilde gittiği belli değil.

## Sonuç: 15 sahnelik bir klip bu yolla üretilebilir mi?
**Ücretsiz kotayla hayır.** 15 sahne × 35 kredi = 525 kredi gerekir, ücretsiz hesapta 80 kredi var. Ayrıca her klip filigranlı.
Kalite yeterli, hatta bu sahnede komuta daha iyi uyuyor. Ama düzenli üretim için iki yol var:
- Sitede ücretli plan almak: filigransız indirme ve daha çok kredi. Tarayıcı otomasyonu yine gerekir.
- **MiniMax API'yi kullanmak**: hesapta 25 $ var. Filigran yok, tarayıcı gerekmez. Fiyat sayfasına göre H3 768P saniyesi 0,08 $, yani 5 sn sahne 0,40 $ ve 15 sahne yaklaşık 6 $. Hailuo 2.3 Fast ile 15 sahne yaklaşık 2,9 $, ama bu model önceki denemede fazladan karakter ekledi. H3'ün API'de hangi model adıyla çağrıldığı henüz doğrulanmadı.
