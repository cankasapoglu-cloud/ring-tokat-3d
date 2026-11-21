# Görev: Hailuo'da ücretsiz video klibi denemesi

Bu dosya, kullanıcının bilgisayarında çalışan (Chrome'u kullanabilen) bir Claude oturumu için yazıldı.

## Amaç

"Pıtır ile Öğren" çocuk kanalı için klipler şimdiye kadar ElevenLabs kredisiyle üretildi (klip başına ~2.100 kredi).
Burada, Chrome'da **zaten giriş yapılmış olan** Hailuo AI sitesinin (hailuoai.video) ücretsiz kotasıyla aynı işi
yapıp yapamayacağımızı tek bir sahneyle deniyoruz.

## Kurallar

- Tarayıcı aracın yoksa hiçbir şeyi taklit etme; kullanıcıya söyle ve dur.
- Şifre isteme, hiçbir yere şifre yazma. Oturum kapalıysa kullanıcı kendisi giriş yapsın.
- Ücretli seçenek, abonelik ya da kredi satın alma adımı çıkarsa onaylama; dur ve kullanıcıya sor.

## Adımlar

1. Chrome'da hailuoai.video sekmesini bul (yoksa aç). Hesapta kaç ücretsiz kredi/üretim hakkı göründüğünü not et.
2. "Image to Video" modunu seç, `cocuk-kanali/ali-baba/kare/03.png` dosyasını yükle (inek yakın çekimi, 1280x720).
3. Komut alanına yaz:
   `The cow opens its mouth wide and moos twice, bobbing its head in rhythm, ears flapping. Smooth, soft 3D preschool cartoon animation, steady camera. No teeth visible. No text.`
4. Ücretsiz/varsayılan modeli ve en kısa süreyi (5–6 sn) seç, üretimi başlat, bitmesini bekle.
5. Klibi indir, `cocuk-kanali/hailuo-deneme/03-hailuo.mp4` olarak kaydet.
6. ffmpeg ile 3 kare çıkarıp bak: inek aynı mı, ağız hareketi var mı, filigran var mı, çözünürlük ve süre ne?

## Rapor

`cocuk-kanali/hailuo-deneme/SONUC.md` dosyasına kısa ve Türkçe yaz:

- Ücretsiz hakkın miktarı; bu klibin ne kadar harcadığı.
- Üretim süresi, klip süresi, çözünürlük, filigran.
- Kalite: `cocuk-kanali/ali-baba/klip/03.mp4` (aynı resimden Kling ile üretilmiş) ile karşılaştırma.
- Otomatik kullanımda takılınan yerler.
- Sonuç: 15 sahnelik bir klibi bu yolla üretmek gerçekçi mi?

Dosyaları commit edip `claude/fervent-ride-j3josu` dalına gönder. Başka dosyaları değiştirme.
