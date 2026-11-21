# Claude'un "kulağı": dinleme takımı

_21 Kasım 2026. Bu sayfa hem kanalın sahibine hem de Claude'un sonraki oturumlarına yazıldı. Komutlar depo kökünden (`ring-tokat-3d/`) çalıştırılır._

## Kısaca

- Claude sesi hâlâ **duyamıyor**. Kurulan şey kulak değil, kulağın yerine kullanılan bir ölçüm takımı: şarkıyı sayıya, yazıya ve resme çeviriyor, Claude da bunları okuyor.
- **Güvenilir yakaladıkları:** yanlış ya da anlaşılmayan sözler, "ninni gibi mi, coşkulu mu", süre. Bilerek eklenen kusur denemelerinde ayrıca detone ya da yanlış tonda vokal, kısık kalan vokal ve boğuk ses.
- **Yakalayamadıkları:** yabancı aksan, sesin hoş olup olmadığı, ezginin bilinen ezgi olup olmadığı, çocukların sevip sevmeyeceği. Bunlarda tek ölçü sizin kulağınız.
- "Araç sorun bulmadı" demek "şarkı iyi" demek değildir. Aksan yüzünden reddettiğiniz bir kayıt araçtan neredeyse temiz çıktı.
- Sizden gerekenler 3. bölümün sonunda, öncelik sırasıyla yazılı.

## 1. Şimdi ne var

Bitmiş bir şarkıyı incelemek için tek komut:

```bash
A=cocuk-kanali/dinleme/arac
python3 $A/dinle.py sarki.mp3 --ayir --sozler sozler.txt
```

`sozler.txt` söylenmesi gereken sözlerdir (düz yazı). 110 saniyelik bir şarkı ilk seferde yaklaşık 3 dakika, sonraki seferlerde 75 saniye sürer. Çıktı `cocuk-kanali/dinleme/raporlar/<dosya adı>/` klasörüne yazılır: `rapor.md` (kısa Türkçe özet), `rapor.json` (bütün sayılar) ve PNG panolar. Claude panolara resim olarak bakar.

| Raporun parçası | Ne yapar | Ne kadar güvenilir |
|---|---|---|
| Sözler | ElevenLabs'in yazıya çevirme servisi (Scribe) şarkıdaki sözleri saniyesiyle yazar; araç bunu söz dosyasıyla sözcük sözcük karşılaştırır. Ücretli: dakikası yaklaşık 330 kredi. | En güçlü parça. |
| Enerji | İki yerel model (MusicCoCa ve CED) şarkının "coşkulu çocuk şarkısı"na mı "ninni"ye mi benzediğini ölçer. | İkisi aynı yanı gösteriyorsa güvenilir. |
| Temel ölçümler | Süre, ses yüksekliği, kırpılma, sessizlik, boğukluk. | Kesin ölçüm. |
| Vokal ve altyapı | Vokali altyapıdan ayırır, ikisinin ses düzeyini karşılaştırır. | Ayrı dosyalar eldeyse tam; otomatik ayırmada ±3 dB oynar. |
| Perde, akort, armoni | Vokalin notalarını altyapının akorlarıyla karşılaştırır. | Detone ve yanlış ton için güvenilir. "Aynı armonide mi" satırı tek kayıtta yanlış alarm verebiliyor. |
| Ritim | Vokal başlangıçlarını vuruşlarla karşılaştırır. | İki sürüm yan yana konunca kayma sayısı işe yarıyor; satırın kendi hükmü yaramıyor. |
| Yapaylık işaretleri, kalite tahminleri | Sert otomatik akort, boğukluk, donmuş ünlü gibi kaba izleri arar. | Zayıf. "İşaret yok" doğal demek değildir. |
| Panolar (resim) | Spektrogram, vokalin perde çizgisi, sözcükler, vuruşlar. | Sayıların kaçırdığını gösterebiliyor (örneğin merdiven gibi düz perde). |
| Gemini (`--gemini`, isteğe bağlı) | Google'ın ses dinleyip soruya cevap veren modeli. Buradaki tek "dinleyen" model. | İkinci görüş. Sözlerde işe yarıyor; akort, ritim ve doğallık hükümlerine güvenilmez. |

Öteki kullanımlar:

```bash
# Vokal ve altyapı ayrı dosya olarak eldeyse (kendi ürettiğimiz karışımlarda hep böyle): en güvenilir yol
python3 $A/dinle.py sarki.mp3 --vokal vokal.wav --altyapi altyapi.wav --bpm 134 --ilk-vurus 0 --sozler sozler.txt
# İki raporu yan yana koy; yalnızca kalibre edilmiş hükümleri ve ölçüm gürültüsünü aşan farkları gösterir
python3 $A/yan_yana.py cocuk-kanali/dinleme/raporlar/begenilen cocuk-kanali/dinleme/raporlar/yeni
# Gemini'ye iki kaydı karşılaştırt; sırayı değiştirip iki kez sorar, yalnız tutarlı cevapları kabul eder
python3 $A/gemini_dinle.py karsilastir yeni.mp3 eski.mp3 --iki-yon
python3 $A/gemini_dinle.py durum      # Gemini erişimi var mı (ücretsiz denetim)
```

## 2. Neye güvenilir, neye güvenilmez

Takım üç ayrı yoldan sınandı. Hiçbirinde ses dinlenmedi; hepsi sayıların cevabı bilinen örneklerle karşılaştırılmasıdır.

**a) Cevabı bilinen yapay örnekler.** Notaları tam yerinde yapay bir "kusursuz şarkıcı" üretildi, sonra bilerek bozuldu. Yedi denetimin yedisi doğru çıktı: altyapının temposu ve tonu, kusursuz şarkıcı, yarım ses tiz, iki yarım ses pes, 40 cent detone, 70 ms geç, dağınık zamanlama. Altı "yapay ses" denetiminin ikisi yakalandı, biri kısmen, üçü kaçtı.

**b) Beğendiğiniz bir kayda tek tek kusur eklendi (14 bozuk sürüm, Ali Baba `dinle_2.mp3`).**

| Sonuç | Sayı | Hangi kusurlar |
|---|---|---|
| Araç kendiliğinden uyardı | 6 | vokal 50 cent tiz; vokal yarım ses tiz; perdesi düzleştirilmiş (otomatik akort gibi); vokal 6 dB kısık; yanlış söylenen satır (söz dosyası ve Scribe ile); boğuk ses |
| Uyarmadı, yalnız iyi sürümle yan yana konunca görüldü | 6 | vokal çeyrek vuruş geç; vokoderle esnetme dokusu (iki sürüm); vokal 6 dB fazla açık; şarkı %80 hıza yavaşlatılmış; sözcük sonları kesik (çok zayıf) |
| Hiçbir şey oynamadı | 2 | vokal yarım vuruş geç; her 3 saniyede bir tık |

Beğenilmiş iki kayıtta araç 6 uyarı satırı verdi: 4'ü yanlış alarm, biri gerçek bir söz hatası, biri teknik not.

**c) Sizin kulağınızla karar verdiğiniz 17 kayıt (5 beğenilen, 12 reddedilen).** Araç kararınızı doğru nedenle 10 kayıtta açıklıyor, 5 kayıtta kısmen, 2 kayıtta hiç (ikisi de aksan).

| Sizin şikâyetiniz | Takımın o konuda gördüğü | Güven |
|---|---|---|
| "Sözler yanlış", "sözler çok kötü çıktı" | Yanlış aile adı, yanlış hayvan, anlaşılmayan söz: hepsi yazıda saniyesiyle bulundu. Makine sözlerin %30'undan fazlasını tanıyamıyorsa vokal bozulmuştur. | Güvenilir |
| "Ninni gibi, coşku yok" | MusicCoCa ve CED birlikte, etiketlediğiniz altı kaydın altısını doğru yana koyuyor. | Güvenilir |
| "Çok uzun" | Süre. "Çok uzun" dedikleriniz 186 ve 213 saniye; kabul ettiğiniz şarkılar 70-110, "olmuş" dediğiniz altyapı 155 saniye. | Güvenilir |
| "Koyun mö diyor", "atıları" | Tek heceli söylenen ses ve küçük telaffuz bozukluğu. Yazıya çeviren model sözcüğü çoğu zaman düzeltip yazıyor. | Kısmen |
| "Yapay duyuluyor" | En iyi iz: makine aynı vokalin sözlerini artık anlayamıyor; perde panosunda çizgi merdiven gibi. "Yapaylık" sayıları yetmiyor. | Kısmen |
| "Olmamış" (vokal orkestraya oturmuyor) | Aynı vokalin iki karışımı yan yana ölçülünce fark açık. Tek kayda bakınca beğendiğiniz bir kayıt da aynı uyarıyı alıyor. | Kısmen |
| "Sözler çok hızlı geçiyor" | En hızlı kaydı doğru sıralıyor ama fark ölçüm hatası kadar. | Kısmen |
| "Türkçe konuşan bir İngiliz gibi" | Hiçbir sayı ayırmıyor. İki kaydın ölçülebilir tek ortak yanı yavaşlık. | Yok |
| "Ezgi bilinen ezgi değil" | Ölçülmüyor. | Yok |
| Ses hoş mu, çocuk sever mi | Ölçülemiyor. Kalite tahminleri zevkinizle ters bile düşüyor. | Yok |

Temiz ayrışan eşikler (her biri yalnızca 1-6 kayda dayanıyor, bir sonraki kararınız yerlerini değiştirebilir): MusicCoCa coşku farkı +0,09 ve üstü coşkulu, −0,04 ve altı ninni; CED "ninni" olasılığı 0,01 ve üstü ninni yanı; sözcük hata oranı %30 ve üstü "makine sözleri anlamıyor"; 180 saniyeden uzun "çok uzun". `yan_yana.py` bu kuralları uygular.

**Bilinen kör noktalar:** yarım vuruş kaymış vokal; tık ve çıtırtı; sonu kesilmiş sözcük (Scribe eksik sesi tamamlayıp doğru sözcüğü yazıyor); vokoder dokusu; fazla açık vokal (+9 dB'ye kadar uyarmıyor); hedef tempo bilinmiyorsa yavaşlık.

**Aracın kendi özetinde güvenilmeyecek satırlar:** "Ritme oturma" (beğenilen kayıtlar da uyarı alıyor; bugün beğendiğiniz El Yıkama kaydının 20 saniyelik bir parçası "sorun" aldı), tek kayıtta "aynı armonide mi", `--ayir` yolunda "gömük vokal", "söyleyiş hızı", "donmuş ünlü" (yavaş söylenen doğal kayıtta da ötüyor), hareketlilik puanına dayanan "ninni/sakin" uyarısı. Gerçek hayvan sesleri vokal sanılıp "çakışan nota" diye sayılabiliyor. Uyarı sayısı bir kalite notu değildir: beğendiğiniz kayıtlar 0-3, reddettikleriniz 2-8 uyarı aldı.

**Resim kanalı:** Claude panoları okuyabiliyor. Küçük kör denemelerde yapay bir ezgiye gizlenen 9 hatanın 9'unu resimden buldu (emin olduğu işaretlerde yanlış alarm yok), 24 hayvan sesinin 24'ünü spektrogramdan tanıdı; ama sese uygulanan işlemi (doğal mı, vokoder mi) 8 denemenin 4'ünde bilebildi. Yani düz ve basamaklı perde resimde görünür, vokoder dokusu ve aksan görünmez.

## 3. Gerçek dinlemeye en yakın şey ve sizden gerekenler

Bu ortamdan ulaşılabilen ve sesi gerçekten alıp soruya cevap veren tek model **Google Gemini**. Öteki dinleyen modellerin adresleri (OpenAI, Qwen, NVIDIA ve benzerleri) ağda kapalı; Claude'un kendisi ses girdisi alamıyor.

**Gemini bugün bağlı ve çalışıyor.** Anahtar ortamda kayıtlı, yeni bir şey yapmanız gerekmiyor. Şimdiye kadar gördüklerimiz:

- Beğendiğiniz kayıttaki gerçek söz hatasını (01:16, "köpekleri" yerine "ördekleri") Scribe'dan bağımsız olarak buldu.
- Bir cevabında `v2_2` kaydında koyunun "mö mö", atın "ne ne" dediğini yazdı; bu sizin şikâyetinizle örtüşüyor ve Scribe'ın kaçırdığı bir şey. Ama aynı kayda sorulan başka bir soruda "hayvan sesleri hiç söylenmiyor" dedi. Tekrarlanmadan güvenilmez.
- İki kaydı karşılaştırırken bir çiftte, sıra ne olursa olsun altı maddenin altısında "B" dedi. Yani sıraya göre cevap veriyor; `--iki-yon` bu yüzden var ve o çifti "tutarsız" diye eledi.
- Önbellekteki sekiz değerlendirmenin sekizinde akort, ritim, enerji, telaffuz ve denge için aynı olumlu cevabı verdi; ayırt edici değil. "Ses doğal mı" sorusunda aynı kaydın iki yarısına farklı cevap verdi. Araştırmalar da bu tür modellerin perde ve doğallık yargılarının güvenilmez olduğunu gösteriyor.
- **Aksan satırı hiç sınanmadı.** Aksan yüzünden reddettiğiniz iki kayıt ve seçtiğiniz kayıtla üç istek bunu çözer.

Bilmeniz gereken iki şey: anahtar ücretsiz katmandaysa (ana oturumun notu böyle diyor, doğrulanmadı) Google gönderilen sesi ürünlerini geliştirmek için kullanabilir ve günlük istek sayısı küçüktür. İstemezseniz Google AI Studio'da faturalandırmayı açmak yeter; bir şarkıyı dinletmenin maliyeti bir ABD sentinin altındadır (fiyat tablosu değişiyor, açmadan önce bakın).

**Anahtar bir gün yeniden gerekirse (yeni ortam, silinen anahtar):**

1. `https://aistudio.google.com/app/apikey` adresine Google hesabınızla girin.
2. "Create API key" düğmesine basın, anahtarı kopyalayın.
3. Claude'a "Gemini anahtarını ekleyeceğim" deyin. Claude güvenli bir form açar; anahtarı **yalnızca o forma** yazın, sohbete asla. Aynı şey Claude bulut ortamının ayarlarından da yapılabilir.
4. Formdaki adres: `generativelanguage.googleapis.com`. Başlık: bugün çalışan ayar `Authorization`, ön ek `Bearer` (formun varsayılanı; araç bunu kullanıyor). Google'ın kendi uç noktalarının beklediği başlık ise `x-goog-api-key`, ön ek yok; araç bu yolu bugün kullanmıyor, o yüzden gerekmiyor.

**Ağda açılırsa yeni ölçüm getirecek adresler** (hepsi şu an kapalı, bugün yeniden denendi; hiçbiri aksanı ölçmez ve hepsinin ayrıca sizin kararlarınızla kalibre edilmesi gerekir):

| Açılacak adres | Getireceği | Ne işe yarar |
|---|---|---|
| `dl.fbaipublicfiles.com` | Meta Audiobox Aesthetics | Bütün şarkıya üretim kalitesi ve beğeni puanı |
| `download.pytorch.org` | MMS hizalayıcı | İstenen her sözcüğün söylendiği an ve sese ne kadar uyduğu; ElevenLabs'in ücretli hizalamasının ücretsiz karşılığı |
| `huggingface.co`, `cdn-lfs.hf.co`, `cas-bridge.xethub.hf.co` | SongEval, CLAP | Şarkıya beş boyutlu beğeni puanı (lisansı ticari kullanıma kapalı) |
| `essentia.upf.edu` | Essentia sınıflandırıcıları | Ruh hali ve dans edilebilirlik etiketi |

**Sizden gerekenler, öncelik sırasıyla:**

1. **Dinlemeye devam edin ve her kararınızı bir cümlelik nedeniyle söyleyin.** Takımı keskinleştiren tek şey bu. Aksan, hoşluk ve ezgi için başka ölçü yok.
2. **Beğendiğiniz 3-5 gerçek Türkçe çocuk şarkısını ses dosyası olarak verin.** Yalnızca ölçüm için kullanılır, yayınlanmaz. "Doğal ses" ve "doğru Türkçe" için ilk kez olumlu bir örnek olur.
3. **Gemini için iki karar:** aksan sınaması için üç isteğe izin; ve seslerin Google'a ücretsiz katmanda gitmesi sizin için sorun mu.
4. **ElevenLabs kredi bütçesi.** Her şarkının söz denetimi yaklaşık 600 kredi. Bu araştırmanın 8000 kredilik sınırının 6921'i harcandı; araç sınırı aşacak çağrıyı yapmaz. Devam için onayınız ve yeni bir sınır gerekir.
5. İsteğe bağlı: ElevenLabs'in sözleri sesle hizalayan ücretli servisine izin (maliyeti burada ölçülmedi).
6. İsteğe bağlı: yukarıdaki tablodaki adreslerin ağda açılması. Claude bunu bir onay penceresiyle önerebilir.

## 4. Yeniden kurulum

Konteyner sıfırlanınca:

```bash
bash cocuk-kanali/dinleme/kurulum/kur.sh       # paketleri kurar, 1,3 GB model indirir
python3 cocuk-kanali/dinleme/arac/sinama.py    # 22 birim sınaması; ağ ve kredi gerektirmez
```

`kur.sh` mevcut paketlerin sürümünü değiştirmez ve yeniden çalıştırmak zararsızdır. ffmpeg, torch, librosa ve audio-separator'ın konteynerde hazır olduğunu varsayar; eksikse söyler. Modeller depoya değil `~/.cache/dinleme/modeller` klasörüne iner. Ayrıntı ve lisans notları: `kurulum/kurulum.md`.

Bugün çalıştırılıp doğrulananlar: `kur.sh` (modellerin boş klasöre gerçek indirilmesi 22 saniye; yeniden çalıştırma 8 saniye), 11 paketin bu Python sürümü için hâlâ indirilebildiği (paketler zaten kurulu olduğu için sıfırdan kurulum yeniden denenmedi), vokal ayırma modelinin yeniden indirilmesi (5 saniye), `sinama.py` (22 sınama geçti), bu sayfadaki bütün `dinle.py` biçimleri (tam inceleme 77 saniye, yalnız karışım 12 saniye, ayrı kanallarla 31 saniye, önbelleksiz ayırma 20 saniyelik parçada 55 saniye), `yan_yana.py`, `gemini_dinle.py durum`. Gemini'nin dinleme ve karşılaştırma komutları önbellekteki cevaplarla çalıştırıldı; yeni istek gönderilmedi, kredi harcanmadı.

## 5. Kullanım kuralı

1. Bunların hepsi **vekil ölçümdür**. Son karar dinleyen insanındır.
2. Takım bir **bekçidir**, hakem değil: kaba hataları size gelmeden yakalar, "güzel olmuş" diyemez.
3. Claude size bir kayıt gönderirken neyi denetlediğini ve neyi denetleyemediğini açıkça yazar. "Dinledim, güzel olmuş" demez.
4. Tek kayda not verilmez; yeni kayıt, beğendiğiniz bir kayıtla yan yana ölçülür.
5. Sizin kararınız araçla çelişirse siz haklısınızdır; araç ona göre düzeltilir.

## Claude'un sonraki oturumları için

Kullanıcıya göndermeden önce sıra:

1. `dinle.py`'yi çalıştır. Kendi karışımında `--vokal/--altyapi/--bpm` kullan, `--ayir` değil: otomatik ayırma "gömük vokal −13 dB" dediği kayıtta gerçek fark +4 dB çıktı. Her zaman `--sozler` ver.
2. Söz farkları tablosunu kıta kıta oku: hayvan adı, aile adı, söylenen ses. Yüzdeye değil sözcüklere bak.
3. `yan_yana.py` ile son beğenilen kayıtla karşılaştır; enerji, süre ve "OYNADI" satırlarına bak.
4. En az bir perde panosuna ve genel bakışa Read aracıyla bak.
5. İstersen Gemini'ye `karsilastir --iki-yon` ile sor (kotadan 2 istek harcar; `--gemini` 1 istek); yalnız tutarlı maddeleri ve söz dökümünü kullan.
6. Kullanıcının her yeni kararını `kalibrasyon/kod/set.py` listesine ekle.

Bilinmesi gerekenler:

- Aynı adlı dosyalar aynı rapor klasörüne yazar (iki `coskulu_1.mp3`); `--cikti` ver.
- Scribe önbelleği dosya içeriğine göredir; aynı dosya ikinci kez ücretlenmez. Defter: `onbellek/kredi_defteri.json`. Sınır `DINLEME_KREDI_SINIRI` ile değişir; kullanıcı onayı olmadan yükseltme.
- `gemini_dinle.py` yalnızca `Authorization: Bearer` yolunu kullanır; `x-goog-api-key` yolu komut satırından seçilemiyor.
- Araçta 14 kusur ve 8 öneri kayıtlı, düzeltilmedi: `kalibrasyon/kalibrasyon.md` ("Araçta görülen kusurlar") ve `sinama/sinama.md` ("Araca öneriler"). En değerli eksikler: bilinen ezgiyle karşılaştırma, tık dedektörü, hayvan seslerini nota analizinden çıkarma.
- NISQA modeli ve SongEval ticari olmayan lisanslıdır; şarkının içine girmezler, yalnız ölçerler. İstenirse kaldırılabilir.

| Nerede | Ne var |
|---|---|
| `arac/` | `dinle.py`, `yan_yana.py`, `gemini_dinle.py`, `dogrula.py`, `sinama.py` ve yardımcıları |
| `kurulum/` | `kur.sh`, kurulum kaydı, yapay örneklerle doğrulama |
| `kalibrasyon/` | 17 kayıtlık karşılaştırma, tablolar, panolar |
| `sinama/` | 14 bozuk sürümle sınama, kör noktalar |
| `raporlar/` | örnek raporlar (`dinle_2` beğenilen, `ornek_kita1` reddedilen) |
| `onbellek/` | Scribe ve Gemini cevapları, kredi defteri |
| `arastirma-1…3/` | dinleyen modeller, açık kaynak modeller ve resim kanalı üzerine deneyler |
