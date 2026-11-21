# Dinleme takımı: kurulum kaydı ve kullanım notları

_21 Kasım 2026. Ortam: bulut Linux konteyneri, Python 3.13.18, 4 çekirdek, ekran kartı yok._

**Tek cümle:** Claude sesi duyamaz. Bu takım, bir ses dosyasını ölçer, makine modellerine dinletir ve Claude'un
okuyabileceği sayı, metin ve resimlere çevirir. İnsan kulağının yerini tutmaz; her çıktıda "neyi söyleyemez" notu vardır.

## 1. Yeniden kurulum (konteyner sıfırlanınca)

```bash
bash cocuk-kanali/dinleme/kurulum/kur.sh      # 1,3 GB ağırlık indirir; bu ortamda 28 saniye sürdü
python3 cocuk-kanali/dinleme/arac/sinama.py   # 22 birim sınaması (ağ gerektirmez, kredi harcamaz)
```

`kur.sh` boş bir model klasörüne gerçek indirmeyle denendi (dosyalar öncekilerle birebir aynı çıktı). Yeniden çalıştırmak zararsızdır.
Mevcut paketlerin sürümünü değiştirmez: önce `pip freeze` ile kısıt dosyası çıkarır, her kurulumu `-c kısıt` ile yapar.

## 2. Kurulanlar (hepsi yerel, CPU; anahtar gerekmez)

### pip paketleri

| Komut | Sürüm | Ne için |
|---|---|---|
| `pip install -c kısıt torchaudio==2.11.1` | 2.11.1 | UTMOS22 ve Distill-MOS'un ses katmanı (torch 2.15'e dokunmaz) |
| `pip install -c kısıt torchmetrics==1.9.0` | 1.9.0 (+ lightning-utilities 0.15.3) | NISQA konuşma kalitesi tahmini |
| `pip install -c kısıt speechmos==0.0.1.1` | 0.0.1.1 | DNSMOS (ağırlıklar paketin içinde) |
| `pip install -c kısıt sherpa-onnx==2.0.2` | 2.0.2 (+ sherpa-onnx-core 2.0.2) | CED ses etiketleyiciyi çalıştırır |
| `pip install -c kısıt swift-f0==0.3.0` | 0.3.0 | vokal perde izleme (ağırlık paketin içinde) |
| `pip install -c kısıt ai-edge-litert==2.4.0 sentencepiece==0.2.3` | 2.4.0 / 0.2.3 (+ backports.strenum 1.2.8) | MusicCoCa'yı çalıştırır |
| `pip install -c kısıt essentia==2.1b6.dev1389` | 2.1b6.dev1389 | ton bulmada çapraz denetim |
| `pip install --no-deps -c kısıt distillmos==0.9.1 xls-r-sqa==0.1.0` | 0.9.1 / 0.1.0 | Distill-MOS (ağırlık paketin içinde) |

Zaten kurulu olup kullanılanlar: ffmpeg 6.1.1, audio-separator 0.48.0, librosa 1.0.1, pyloudnorm 0.2.0, pyworld 0.3.5, torch 2.15.0, onnxruntime 1.29.0,
numpy 2.5.3, scipy 1.18.1, matplotlib 3.11.2, soundfile 0.14.0.

Denetim (kurulumdan sonra): pyworld, librosa, torch, onnxruntime, audio-separator açılıyor; setuptools 80.10.2 (81'in altında) kaldı.
`pip check` tek bir uyarı verir: "xls-r-sqa requires transformers". Bilerek kurulmadı: Distill-MOS onsuz çalışıyor, transformers büyük ve gereksiz.

### Model ağırlıkları (depoya yazılmaz)

Yer: `~/.cache/dinleme/modeller` (değiştirmek için `DINLEME_MODELLER`). Ayrılmış kanallar: `~/.cache/dinleme/kanallar`.

| Model | Boyut | Kaynak (erişilebilen adres) | Lisans |
|---|---|---|---|
| CED-mini ses etiketleyici (AudioSet, 527 sınıf) | 46 MB | github.com/k2-fsa/sherpa-onnx (sürüm dosyası) | Apache-2.0 |
| MusicCoCa (metin-müzik ortak uzayı; 4 dosya) | 762 MB | storage.googleapis.com/magenta-rt-public | ağırlık CC-BY 4.0 |
| UTMOS22-strong + kaynak kodu (tarepan/SpeechMOS, sabit sürüm `ed25eac`) | 393 MB | github.com/tarepan/SpeechMOS | MIT |
| NISQA | 1 MB | raw.githubusercontent.com/gabrielmittag/NISQA | ağırlık CC BY-NC-SA (ticari değil) |
| UVR-MDX-NET-Voc_FT (vokal / altyapı ayırma) | 67 MB | github.com/TRvlvr/model_repo (audio-separator indirir) | — |
| DNSMOS, Distill-MOS, SwiftF0 | paket içinde | pypi.org | MIT / Microsoft |

Lisans notu (para kazanan kanal için): bu modeller şarkının içine girmez, yalnızca ölçüm yapar. NISQA ağırlıkları "ticari olmayan kullanım" lisanslıdır, essentia AGPL'dir;
istenirse ikisi de kaldırılabilir (araç eksik parçayı atlayıp çalışır).

### Kurulmayanlar ve nedeni

| Araç | Neden kurulmadı | Açmak için gereken |
|---|---|---|
| Meta Audiobox Aesthetics (bütün şarkıya üretim kalitesi / beğeni puanı) | ağırlık engelli adreste | `dl.fbaipublicfiles.com` izni |
| MMS zorlamalı hizalayıcı (sözcük sözcük zamanlama + güven) | ağırlık engelli adreste | `download.pytorch.org` izni |
| SongEval, LAION-CLAP, UTMOSv2, MERT | Hugging Face engelli | `huggingface.co` ve dosya adresleri (`cdn-lfs.hf.co`, `cas-bridge.xethub.hf.co` …) izni |
| Essentia hazır sınıflandırıcıları (ruh hali, dans edilebilirlik) | ağırlık engelli adreste | `essentia.upf.edu` izni |
| SingMOS-Pro (1,27 GB), yerel Whisper (564 MB) | erişilebilir ama bilerek kurulmadı: araştırmada şarkıda güvenilmez çıktılar (SingMOS düz perdeli robot sese de yüksek puan verdi; Whisper uydurma metin yazdı) | — |
| ElevenLabs zorlamalı hizalama (`/v1/forced-alignment`) | bu çalışmanın kuralı yalnızca konuşma dökümüne izin veriyordu | kullanıcı izni |

## 3. Araçlar (`cocuk-kanali/dinleme/arac/`)

| Dosya | İş |
|---|---|
| `dinle.py` | TEK komut: ölçer, dinletir, rapor ve panoları yazar |
| `dinle_olcum.py` | sinyal ölçümleri (ses düzeyi, enerji, ton/akor, perde, uyum, ritim, yapaylık vekilleri) |
| `dinle_model.py` | yerel modeller (CED, MusicCoCa, DNSMOS, NISQA, Distill-MOS, UTMOS22) |
| `dinle_sozler.py` | ElevenLabs Scribe dökümü (önbellek + kredi defteri), beklenen sözle hizalama, hece hızı |
| `dinle_panel.py` | PNG panolar (1600 piksel genişlik, dilim başına en çok 30 sn) |
| `gemini_dinle.py` | ses girişli dil modeli (Google Gemini) kancası: sabit sorular, A/B, iki yönlü A/B |
| `dogrula.py` | cevabı bilinen denetim sesleriyle kalibrasyon → `kurulum/dogrulama.json` |
| `referans_olustur.py` | projenin kendi şarkılarından enerji referans tablosu → `kurulum/referans_enerji.json` |
| `sinama.py` | birim sınamaları |

### Kullanım

```bash
A=cocuk-kanali/dinleme/arac
python3 $A/dinle.py sarki.mp3 --ayir --sozler sozler.txt        # tam inceleme (ilk seferde ~2,5 dk, sonra ~70 sn)
python3 $A/dinle.py sarki.mp3                                   # yalnızca karışım: ses düzeyi, enerji, ton, panolar (~15 sn)
python3 $A/dinle.py sarki.mp3 --vokal kuru_vokal.wav --altyapi altyapi.wav --bpm 134 --ilk-vurus 0   # kanallar elde varsa: en güvenilir yol
python3 $A/dinle.py vokal.wav --kuru                            # yalnızca kuru vokal
python3 $A/dinle.py sarki.mp3 --ayir --gemini                   # + Gemini'nin görüşü (kotadan 1 istek harcar)
python3 $A/gemini_dinle.py karsilastir yeni.mp3 eski.mp3 --iki-yon   # A/B, sırayı değiştirip iki kez sorar
python3 $A/gemini_dinle.py durum                                # Gemini erişimi var mı (ücretsiz denetim)
```

Çıktı klasörü (varsayılan `cocuk-kanali/dinleme/raporlar/<dosya adı>/`): `rapor.md` (kısa Türkçe özet), `rapor.json` (bütün sayılar),
`00_genel_bakis.png`, her 30 sn'lik dilim için `NN_pano_…png` ve (vokal varsa) `NN_perde_…png`. **Panolara Read aracıyla bakılır.**

Söz dosyası kuralı: yalnızca söylenen sözler yazılır; `#` ile başlayan satırlar, `[köşeli]` ve `(yuvarlak)` parantez içleri, "1. KITA …" gibi başlık satırları yok sayılır.
Örnekler: `cocuk-kanali/dinleme/ornek/`.

### Kredi ve kota

- **ElevenLabs Scribe:** yalnızca `--sozler` ya da `--dokum` verilince çağrılır; aynı dosya ikinci kez gönderilmez (`onbellek/scribe_v1__…json`).
  Defter: `onbellek/kredi_defteri.json`. Bu çalışmada harcanan: **yaklaşık 921 kredi / 8000 sınır** (3 dosya: 30 sn, 110 sn, 27 sn). Sınır `DINLEME_KREDI_SINIRI` ile değişir;
  aşılacaksa çağrı yapılmaz.
- **Gemini:** anahtar ortamda tanımlı ve çalışıyor (OpenAI uyumlu uç nokta; `Authorization: Bearer` başlığını ağ vekili ekliyor). Bu çalışmada 1 canlı istek yapıldı
  (dinle_2.mp3, sabit sorular); cevaplar `onbellek/gemini/` altında saklanır. Yerel uç noktalar (`x-goog-api-key`) bu ortamda çalışmıyor; gerek de yok.
  Anahtarın ücretsiz katmanda olduğu ana oturumun notundan biliniyor (kendim doğrulamadım): ücretsiz katmanda Google gönderilen sesi ürünlerini geliştirmek için kullanabilir ve günlük istek sayısı küçüktür.

## 4. Doğrulama: araç doğru ölçüyor mu? (`dogrula.py`, sonuçlar `dogrulama.json`)

Kulak olmadığı için aracı cevabı bilinen seslerle sınadık. Altyapı: `ali-baba/yeni/altyapi.wav` (gerçek: 134 BPM; Sol majör, 85,97. saniyede La majöre geçiş).
Üstüne, notaları tam yerinde ve tam akortlu **yapay bir "kusursuz şarkıcı"** sentezlendi, sonra bilerek bozuldu.

| Denetim | Aracın bulduğu | Sonuç |
|---|---|---|
| Altyapının temposu ve tonu | 133,95 BPM; Sol majör 0–85,3 sn, La majör 85,3–154,7 sn | doğru |
| Kusursuz şarkıcı | armonik destek +0,48; en iyi kaydırma 0; gam içi %100; akor sesi %96; 1,8 cent; çakışan nota 0; ritim R 0,64–0,65, kayma +4…+6 ms | doğru |
| Yarım ses yukarı söyleyen | destek −0,27; "en iyi kaydırma −1"; gam içi %0; 66 çakışan nota | yakalandı |
| İki yarım ses aşağı söyleyen | destek −0,05; "en iyi kaydırma +2"; 53 çakışan nota | yakalandı |
| 40 cent tiz (detone) | 37,4 cent; 113 detone nota | yakalandı |
| 70 ms geç söyleyen | ortalama kayma +75…+77 ms | yakalandı |
| Rastgele ±90 ms zamanlama | ritim sıkılığı R 0,15 (kusursuzda 0,65) | yakalandı |

Yapaylık vekilleri (gerçek bir vokal kanalı bilerek bozuldu):

| Bozulma | Yakalandı mı |
|---|---|
| Perdesi yarım seslere yapıştırılmış (sert otomatik akort) | **evet** (nota içi oynaklık 11,8 → 5,4 cent; ızgaraya yapışma 0,62 → 0,90; 3 işaret) |
| 4 kHz'de kesilmiş (boğuk) | **evet** (ünsüzlerde tiz −11 → −27 dB) |
| Kullanıcının reddettiği "konuşmayı vokoderle ezgiye oturtma" vokali (`kita1_ham.wav`) | **kısmen** (sesli sürenin %18'i "donmuş ünlü"; doğal vokallerde %0–2) |
| Perdesi değiştirilmeden vokoderden geçirilmiş | **hayır** |
| 1,6–1,8 kat esnetilmiş | **hayır** |
| Konuşma sentezi (TTS) | **hayır** (yapaylık işareti yok; ama perdeler nota ızgarasına oturmuyor: R 0,21) |

Sonuç: **uyum, akort ve ritim ölçümleri denetimlerde güvenilir çıktı; "yapaylık" vekilleri yalnızca kaba izleri yakalıyor.** "İşaret yok", "doğal" demek değildir.

Enerji referansı (`referans_enerji.json`; etiket = dosya adındaki üretim niyeti, dinleyici puanı değil, n=9):

| Gösterge | "coşkulu" adlı 6 sürüm | "yavaş" adlı 3 sürüm |
|---|---|---|
| Hareketlilik puanı (0-100) | 66 … 79 | 52 … 61 |
| MusicCoCa coşku farkı | +0,09 … +0,22 | −0,10 … −0,08 |
| CED "ninni" olasılığı | 0,000 | 0,023 … 0,044 |

Bilinen ölçüm sınırları: vuruş izleyicisi vuruşu ~40 ms geç işaretliyor (araç bunu düzeltir; ±20 ms belirsizlik kalır, gerçek tempo `--bpm` ile verilirse kalmaz);
ton bulma gürültülü altyapıda "belirsiz" diyebilir (dinle_2.mp3'te La majör / La minör arasında kararsız); akorlar yalnızca majör/minör üçsesli olarak tahmin edilir;
ayrılmış (MDX) vokalde kalite tahminleri kuru vokalden düşük çıkar.

## 5. Duman testleri (bu çalışmada üretilen raporlar)

| Rapor | Ne çıktı |
|---|---|
| `raporlar/dinle_2/` (`--ayir --sozler --gemini`, 110 sn şarkı) | coşkulu yana yakın; vokal altyapıyla aynı armonide, akortlu; ritim orta; **söz hatası 76,9. saniyede: "köpekleri" yerine "ördekleri"** (Scribe ve Gemini ayrı ayrı buldu); sonda 8 fazla sözcük |
| `raporlar/ornek_kita1/` (yalnızca karışım, `--sozler`) | makine sözleri **hiç anlamıyor** (sözcük hata oranı %100: "Maliboku yeşil boya…"); inek sesi etiketlendi |
| `raporlar/ornek_kita1_kanalli/` (`--vokal --altyapi --bpm`) | perde ve akort kusursuz (zaten notaya zorlanmıştı), ama "donmuş ünlü" işareti ve %100 söz hatası: kullanıcının "olmamış" dediği kaydın makine resmi |

Çalışma süreleri (2 çekirdek): 110 sn'lik şarkı, ayırma önbellekteyken 69 sn (kalite tahminleri 28 sn, MusicCoCa 10 sn, ton/akor 8 sn, enerji 7 sn, panolar 6 sn);
ilk seferde kanal ayırma +98 sn, Scribe +2 sn, Gemini +1…80 sn. 27 sn'lik parça: 12 sn (kanalsız), 28 sn (kanallı).

## 6. Daha fazlasını açacak şeyler

1. `dl.fbaipublicfiles.com` izni → Meta Audiobox Aesthetics (bütün şarkıya üretim kalitesi puanı; kodu burada denendi, ~15 sn/şarkı).
2. `download.pytorch.org` izni → MMS zorlamalı hizalayıcı (istenen sözlerin her biri için zaman ve uyum puanı).
3. `huggingface.co` (+ dosya adresleri) izni → SongEval (şarkıya beş boyutlu beğeni puanı; ticari olmayan lisans) ve standart CLAP.
4. `essentia.upf.edu` izni → ruh hali / dans edilebilirlik sınıflandırıcıları.
5. ElevenLabs zorlamalı hizalama için kullanıcı izni (ücretli uç nokta).
6. Gemini için: ücretli katman (ses Google'ın ürün geliştirmesinde kullanılmaz, kota büyür) — isteğe bağlı.
7. En değerlisi yazılım değil: **kullanıcının beğendiği 3-5 gerçek Türkçe çocuk şarkısı** ve reddettiği kayıtlar "referans rafı" olarak verilirse, bütün göstergeler onlara göre kalibre edilebilir.
