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
