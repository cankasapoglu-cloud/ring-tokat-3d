# Şarkı klibi üretim betikleri

Bir şarkı klibi için bir klasör açılır (örnek: `banyo-sarkisi/`) ve içine iki dosya yazılır:

- `sozler.json`: başlık, bölümler (satırlar, süre, her satırın sahnesi ve ekran yazısı), ekran yazılarının metin ve renkleri.
- `sahneler.json`: her sahnenin resim tarifi (`prompt`) ve hareket tarifi (`video`), ortak stil ve referans resimler.

Sıra (komutlar `cocuk-kanali/` içinden):

```bash
python3 uretim/sarki_uret.py <klasör> deneme_1 en+     # şarkı (en+ = sozler.json'daki ek_stil eklenir, en = yalnız ortak stil)
python3 uretim/soz_denetle.py <klasör> deneme_1        # sözleri yazıya döküp söz dosyasıyla karşılaştırır
python3 uretim/kare_uret.py <klasör> <ilk sahne>       # önce ana kare (öbür karelerin referansı olur)
python3 uretim/kare_uret.py <klasör> hepsi             # kalan kareler
python3 uretim/klip_uret.py <klasör> hepsi             # karelerden 6 saniyelik klipler
node uretim/yazi.mjs <klasör>                          # ekran yazıları (şeffaf PNG)
python3 uretim/kurgu.py <klasör> deneme_1 <çıktı adı>  # video (1080p); kesimler sözcük zamanlarından çıkar
python3 uretim/kontrol.py <video> <çıktı.jpg> [saniyeler]   # kontrol sayfası
```

Bilinen sınırlar:

- ElevenLabs hesabı aynı anda en çok 2 şarkı isteğine izin veriyor.
- MiniMax dakikalık istek sınırı var; `klip_uret.py` sınıra takılınca bekleyip yeniden dener. Aynı anda birden çok klasör çalıştırılabilir.
- Var olan kare ve klipler yeniden üretilmez; yenilemek için dosya silinir (klipte `klip/gorevler.json` içindeki kayıt da).
- Nesnelerin üstüne etiket (rakam, ad) konacaksa o satırda `efekt` "kare" ya da "duz" olmalı; konumlar 1920x1080 üzerinden verilir.

Klip sağlayıcısı (`klip_uret.py --saglayici=oto|minimax|eleven`):

- `oto` (varsayılan): önce MiniMax Hailuo (klip başına yaklaşık 0,19 dolar); bakiye bitince kendiliğinden ElevenLabs video modeline geçer.
- `eleven`: ElevenLabs video (varsayılan model Veo 3.1 Fast, 6 sn, 720p, sessiz). 23 Kasım 2026 ölçümü: klip başına yaklaşık 3.600 kredi. 16 klipli bir video yaklaşık 58.000 kredi tutar; Hailuo'ya göre çok pahalıdır.
- Hesapta ByteDance (Seedance) modelleri kapalı: "model_access_denied"; açtırmak için ElevenLabs desteğine yazmak gerekiyor.
- Kredi tasarrufu: sozler.json içinde satırın `efekt` değeri "kare+" yapılırsa o satır klip üretmeden, yavaş yakınlaşan duran kareyle kurulur.
- Video modeli bazen sahneye kendiliğinden yazılı ambalaj ya da marka benzeri nesne ekliyor; kliplerin kenarlarına bakılmalı (bkz. Diş Fırçalama: üç klip yeniden üretildi).
- Model klibin sonunda hareketi bitirip durabiliyor; kurgu son sahnede klibin yalnız ilk 4,4 saniyesini kullanır (`son_klip_sn` ile değişir).
- Ölçülen örnek (23 Kasım, Orman Hayvanları): 16 kare, 7 klip ve yeniden üretilen 1 klip, 2 şarkı denemesi = toplam 42.600 kredi. Bu videonun gönderim notundaki "yaklaşık 28.000" tahmini yanlıştı; doğrusu budur.
- Aynı video sahibinin isteğiyle tümü hareketli hâle getirildi (9 klip daha): toplam yaklaşık 75.000 kredi. ElevenLabs kredisi aylık 610.000; 21 Aralık 2026'da yenileniyor.
- Ölçülen örnek (23 Kasım, Oyuncakları Toplama; klipler Hailuo ile): 17 kare ve 4 şarkı denemesi = 17.100 kredi; 16 klip = yaklaşık 3 dolar. Bütün sahneler hareketli.
