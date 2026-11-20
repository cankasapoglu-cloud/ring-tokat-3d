# Pıtır 3D — ortak stil ve üretim kuralları (tüm ajanlar için)

## Stil cümlesi (her prompt'un SONUNA aynen ekle)
High-quality 3D CGI render in the style of modern 3D preschool nursery-rhyme cartoons, soft rounded toy-like shapes, smooth plush/vinyl toy materials, vivid saturated colors, soft studio lighting from the upper left, gentle ambient occlusion. Single object, centered, entirely visible with margin around it, isolated on a plain flat light-grey background, no ground shadow, no text, no letters, no watermark.

(Arka plan görsellerinde "Single object … light-grey background, no ground shadow" kısmı KULLANILMAZ; onun yerine sahne tarifi yazılır.)

## Üretim
- Araç: mcp__ElevenLabs__creative_generate_image, model_id "gpt-image-2.5-sunburst", generations_count 2.
- Aynı flow_id'yi kullan (ilk çağrının döndürdüğünü ya da görevde verileni).
- Bitene kadar mcp__ElevenLabs__creative_get_flow_run_status ile yokla (poll_after_seconds bekle).
- Her "generation" için content_url'yi indir: curl -sS -f -o ham/<ad>_1.png "<url>"  (ikincisi _2).
- İki denemeyi Read ile GÖR, iyi olanı seç. Ölçüt: tek nesne, tamamı görünür, 3D oyuncak tarzı, istenen renk/bakış yönü, yazı yok.
- İkisi de kullanılamazsa promptu düzeltip EN FAZLA bir kez daha üret. Sonra hâlâ kötüyse raporla, devam et.
- Asla aynı çağrıyı "yeniden deneme" diye tekrarlama: her çağrı kredi harcar.

## Kesme (arka planlı görsellerde YOK)
cd /home/user/ring-tokat-3d/cocuk-kanali/3d && python3 kes.py ham/<ad>_N.png varlik/<ad>.png
Sonra onizle/<ad>.jpg dosyasını Read ile gör: kenarlar temiz mi, parça eksik mi?

## Klasörler
- ham/     : indirilen ham görseller
- varlik/  : kesilmiş, şeffaf zeminli son görseller (dosya adları görevde verilen adlarla birebir)
- onizle/  : kontrol önizlemeleri

## Rapor
Sadece: üretilen dosya adları, her biri için tek satır not (varsa kusur), başarısız olanlar, harcanan toplam kredi. 40 satırı geçme.
