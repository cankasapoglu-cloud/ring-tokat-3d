#!/usr/bin/env python3
"""Baslik ve etiket onerilerini yazar ve kurallari denetler. Kullanim: python3 -I oneriler.py <calisma klasoru>"""
import csv, os, sys
K = sys.argv[1]
oz = {r["sorgu"]: r for r in csv.DictReader(open(os.path.join(K, "kanit-sorgu-ozeti.csv"), encoding="utf-8"))}
S = "Dudek Stüdyo"
V = [
 ("01", "Ali Baba'nın Çiftliği", "hazır", "ali babanın çiftliği", "ali babanın çiftliği hayvan sesleri", "çiftlik hayvanları şarkısı",
  "Ali Baba'nın Çiftliği | Hayvan Sesleri, Çiftlik Şarkısı | " + S,
  "ali babanın çiftliği, ali baba'nın çiftliği, ali babanın bir çiftliği var, hayvan sesleri, hayvan sesleri şarkısı, çiftlik hayvanları şarkısı, çiftlik şarkısı, çocuk şarkıları, bebek şarkıları, " + S,
  "hayvan sesleri şarkısı", "ali babanın çiftliği hayvan sesleri; ali babanın bir çiftliği var; çiftlik hayvanları şarkısı",
  "Şarkının adı aranan kelimenin kendisi. İlk sıralar 12,6 milyon aboneli bir kanalda, oraya çıkılmaz; ama sayfanın alt yarısında küçük kanallar var. 'Hayvan sesleri' eklenince ilk 10'da 3 küçük kanal görünüyor."),
 ("02", "Pıtır'ın Ailesi", "hazır", "kedi ailesi şarkısı", "aile şarkısı çocuk", "aile üyeleri şarkısı",
  "Kedi Ailesi Şarkısı | Pıtır'ın Ailesi, Aile Üyeleri | " + S,
  "kedi ailesi şarkısı, aile şarkısı, aile üyeleri şarkısı, aile bireyleri şarkısı, bebek kedi miyav miyav, kedi şarkısı, anne baba nine dede, çocuk şarkıları, bebek şarkıları, " + S,
  "kedi şarkısı (ilk sıralar 5-36 milyon izlenmeli, küçük kanal satırları çocuk videosu değil)", "kedi ailesi şarkısı; aile şarkısı çocuk; aile üyeleri şarkısı",
  "'Pıtır' adını henüz kimse aramıyor; başlık aranan kelimeyle başlamalı. 'Kedi ailesi şarkısı' sayfasında 5 aboneli, 8 günlük bir video 7. sırada. Dikkat: bu sayfalarda en üstteki videoların izlenmesi de az (9-31 bin); yani bu kelimeler az aranıyor olabilir."),
 ("03", "Parmak Ailesi", "hazır", "parmak ailesi şarkısı", "baba parmak şarkısı", "kedi parmak ailesi",
  "Parmak Ailesi Şarkısı | Baba Parmak, Kedi Parmak Ailesi | " + S,
  "parmak ailesi şarkısı, parmak ailesi, baba parmak, baba parmak nerdesin, bebek parmak, kedi parmak ailesi, parmak oyunu, çocuk şarkıları, bebek şarkıları, " + S,
  "parmak ailesi; parmak ailesi şarkısı; baba parmak şarkısı", "(yok) kedi parmak ailesi biraz daha gevşek ama ilk 10'da küçük kanal yok",
  "Aramadan izlenme beklemeyin: üç aramada da ilk 10'da küçük kanal yok, ortanca izlenme 17-28 milyon. Bu video derlemenin ve oynatma listesinin içinde iş görür. 'Kedi Parmak' sözünü yalnız videoda gerçekten kedi patisi görünüyorsa kullanın."),
 ("04", "Beş Küçük Maymun", "hazır", "beş küçük maymun", "5 küçük maymun", "beş küçük maymun yatakta zıplıyor",
  "Beş Küçük Maymun Yatakta Zıplıyor | Sayma Şarkısı | " + S,
  "beş küçük maymun, 5 küçük maymun, beş küçük maymun yatakta zıplıyor, beş küçük maymun şarkısı, maymun şarkısı, sayma şarkısı, geri sayım şarkısı, çocuk şarkıları, bebek şarkıları, " + S,
  "5 küçük maymun; sayma şarkısı; maymun şarkısı (küçük kanal satırları çocuk videosu değil)", "(yok) en iyi küçük kanal 16-17. sırada",
  "Zor. İlk 20 sonucun 10'u bir milyonun üstünde aboneli kanallardan. Başlığı şarkının ilk dizesiyle uzatmak ('yatakta zıplıyor') tek küçük kanalın 16. sıraya girdiği yol. Rakamla yazılışı ('5 küçük maymun') etikete ve açıklamaya konur."),
 ("05", "Balon Şarkısı (renkler)", "hazır", "renkler şarkısı", "balon şarkısı", "renkleri öğreniyorum",
  "Renkler Şarkısı | Balon Şarkısı, Renkleri Öğreniyorum | " + S,
  "renkler şarkısı, balon şarkısı, renkleri öğreniyorum, renkli balonlar şarkısı, renkler şarkısı okul öncesi, kırmızı sarı mavi yeşil, balonlar, çocuk şarkıları, okul öncesi şarkılar, " + S,
  "renkleri öğreniyorum (20 sonucun 10'u uzun derleme)", "renkler şarkısı (orta); renkli balonlar şarkısı (az aranır ama 13 saatlik, 2 aboneli video 13. sırada)",
  "Ebeveyn ve öğretmen 'renkler şarkısı' yazar; 'balon şarkısı' yazınca başka bir şarkı (19 milyon izlenmeli) çıkıyor. Bu yüzden başlık 'Renkler Şarkısı' ile başlamalı. Sayfada 3 haftalık, 36 izlenmeli bir video 4. sırada: yeni videolara yer açılıyor."),
 ("06", "El Yıkama Şarkısı", "hazır", "el yıkama şarkısı", "el yıkama şarkısı okul öncesi", "ellerimi yıkıyorum şarkısı",
  "El Yıkama Şarkısı | Okul Öncesi Temizlik Şarkısı | " + S,
  "el yıkama şarkısı, el yıkama şarkısı okul öncesi, ellerini yıka şarkısı, ellerimi yıkıyorum, temizlik şarkısı, el yıkama, hijyen şarkısı, çocuk şarkıları, okul öncesi şarkılar, " + S,
  "temizlik şarkısı (sayfa karışık: ev temizliği müzikleri, dizi sahneleri)", "el yıkama şarkısı; el yıkama şarkısı okul öncesi; ellerimi yıkıyorum şarkısı",
  "Yedi videonun içinde aramada en şanslı olanı. İlk 10'da 4 küçük kanal var (125 ve 30 aboneli olanlar dahil), 19 sonucun 18'i tek şarkı. Yine de üstteki küçük videolar 8-11 ayda 2-6 bin izlenmiş: sıra almak kolay, ama bu kelime çok aranmıyor."),
 ("07", "Otobüs Şarkısı", "hazır", "otobüs şarkısı", "otobüsün tekerlekleri dönüyor", "taşıtlar şarkısı",
  "Otobüs Şarkısı | Tekerlekler Dönüyor, Korna Ötüyor | " + S,
  "otobüs şarkısı, otobüsün tekerleği, otobüsün tekerlekleri dönüyor, tekerlekler dönüyor, taşıtlar şarkısı, taşıtlar, otobüs çizgi film, çocuk şarkıları, bebek şarkıları, " + S,
  "otobüs şarkısı; otobüsün tekerlekleri dönüyor; otobüs şarkısı okul öncesi", "taşıtlar şarkısı (ilk sayfada 5 küçük kanal; ama bizim şarkı yalnız otobüsü anlatıyor, başlığa yazılmaz, etikette kalır)",
  "Aramadan izlenme beklemeyin: 'otobüs şarkısı' sayfasında tek bir küçük kanal yok, ortanca izlenme 16 milyon. Bizim şarkı bilinen 'Otobüsün Tekerleği' ezgisi değil; başlıkta o adı kullanmıyoruz, yalnız şarkıda geçen sözleri yazıyoruz."),
 ("08", "Gezegenler (planlı)", "sırada", "gezegenler şarkısı", "gezegenler çocuklar için", "güneş sistemi şarkısı",
  "Gezegenler Şarkısı | Çocuklar İçin Güneş Sistemi | " + S,
  "gezegenler şarkısı, gezegenler, güneş sistemi şarkısı, güneş sistemi, çocuklar için gezegenler, gezegenleri öğreniyorum, uzay şarkısı, 8 gezegen, çocuk şarkıları, " + S,
  "gezegenler şarkısı; güneş sistemi şarkısı; gezegenler şarkısı okul öncesi; uzay şarkısı çocuk", "gezegenler çocuklar için (ilk 10'da 3 küçük kanal; bunlar şarkı değil, anlatım videosu)",
  "En kilitli konulardan biri: ilk sıradaki video 559 milyon izlenmiş ve 15 sonucun 11'i bir milyonun üstünde aboneli kanallardan. Öneri: bu videoyu sıranın sonuna alın; yapılacaksa 'çocuklar için güneş sistemi' sözü başlıkta olsun."),
 ("09", "Harfler/Alfabe (planlı)", "sırada", "alfabe şarkısı", "29 harf şarkısı", "abc şarkısı türkçe",
  "Alfabe Şarkısı | 29 Harf | Türkçe ABC Şarkısı | " + S,
  "alfabe şarkısı, 29 harf şarkısı, türkçe alfabe şarkısı, abc şarkısı türkçe, harfler şarkısı, harfleri öğreniyorum, alfabe, okul öncesi şarkılar, çocuk şarkıları, " + S,
  "alfabe şarkısı (tek başına); harfler şarkısı; harfleri öğreniyorum (18 sonucun 14'ü uzun derleme)", "29 harf şarkısı (ilk 10'da 6 küçük kanal); abc şarkısı türkçe (ilk 10'da 2 küçük kanal)",
  "Videonun adı 'Harfler Şarkısı' olmasın: o sayfadaki 19 başlığın hiçbirinde bu söz geçmiyor, herkes 'Alfabe Şarkısı' diyor. '29 harf' eklemek işe yarıyor: 3 bin aboneli bir kanalın 2 aylık videosu 2. sırada."),
 ("10", "Sayılar 1-10 (planlı)", "sırada", "1'den 10'a kadar sayılar", "sayılar şarkısı", "sayıları öğreniyorum",
  "1'den 10'a Kadar Sayılar Şarkısı | Saymayı Öğreniyorum | " + S,
  "1'den 10'a kadar sayılar, sayılar şarkısı, sayıları öğreniyorum, 1den 10a kadar sayılar, saymayı öğreniyorum, sayma şarkısı, sayılar, okul öncesi şarkılar, çocuk şarkıları, " + S,
  "sayılar şarkısı; sayıları öğreniyorum; sayı şarkısı okul öncesi; sayma şarkısı", "(yok) 1'den 10'a kadar sayılar en gevşeği: 3. sırada 2 bin aboneli bir kanal var ama o video 12 dakikalık",
  "Beş planlı konunun en kilitlisi: 'sayılar şarkısı' sayfasında en az izlenen video bile 186 bin izlenmiş, küçük kanal yok. Sayma konusu zaten Beş Küçük Maymun'da var. Öneri: sıranın sonuna alın."),
 ("11", "Banyo (planlı)", "sırada", "banyo şarkısı", "banyo zamanı şarkısı", "yıkanma şarkısı",
  "Banyo Şarkısı | Banyo Zamanı, Yıkanma Şarkısı | " + S,
  "banyo şarkısı, banyo zamanı şarkısı, yıkanma şarkısı, banyo yapıyorum, banyo zamanı, bebek banyo şarkısı, temizlik şarkısı, bebek şarkıları, çocuk şarkıları, " + S,
  "(yok)", "banyo şarkısı; banyo zamanı şarkısı; yıkanma şarkısı; banyo yapıyorum şarkısı",
  "Beş planlı konunun en umut vereni ve hem sıra hem izlenme gösteren tek sayfa: 1. sırada 2 bin aboneli bir kanalın 1 dk 42 sn'lik şarkısı var ve 10 ayda 3,1 milyon izlenmiş; 614 aboneli bir kanalın 2 aylık videosu 416 bin izlenmiş. Öneri: sıradaki ilk video bu olsun."),
 ("12", "Pazar/Meyveler (planlı)", "sonra", "meyve ve sebzeler şarkısı", "sebzeler şarkısı", "meyveler şarkısı",
  "Meyve ve Sebzeler Şarkısı | Pazarda Neler Var? | " + S,
  "meyve ve sebzeler şarkısı, sebzeler şarkısı, meyveler şarkısı, meyve sebze şarkısı, meyveleri öğreniyorum, sebzeleri öğreniyorum, pazar şarkısı, pazarda neler var, çocuk şarkıları, " + S,
  "pazar şarkısı (sayfa yetişkin müziğiyle dolu); pazara gidelim şarkısı (iki büyük kanalın şarkı adı; kullanmayın)", "sebzeler şarkısı (orta; 29 aboneli kanal 6. sırada); meyve sebze şarkısı (orta)",
  "Videonun adı 'Pazar Şarkısı' olmasın: o aramada pop şarkıları ve Shorts çıkıyor. 'Pazara Gidelim' de iki büyük kanalın şarkı adı. Şarkıda sebzeler öne çıksın: 'sebzeler şarkısı' sayfası 'meyveler şarkısı' sayfasından belirgin biçimde zayıf."),
]
def k(q):
    o = oz.get(q)
    return f"{o['karar']} (ortanca {int(o['medyan_goruntuleme']):,} izlenme; ilk 10'da {o['kucuk_kanal_ilk10']} küçük kanal; {o['uzun_derleme_10dk']}/{o['video_sayisi']} uzun derleme)".replace(",", ".") if o else "ölçülmedi"
out = []; hata = 0
for no, ad, durum, p, s1, s2, baslik, etiket, umutsuz, kazan, notu in V:
    et = [e.strip() for e in etiket.split(",")]
    low = lambda t: t.replace("İ", "i").replace("I", "ı").lower().replace("'", "")
    sorun = []
    if len(baslik) > 70: sorun.append("uzun")
    if not low(baslik).startswith(low(p)): sorun.append("birincil ifadeyle baslamiyor")
    if not baslik.endswith("| " + S): sorun.append("son ek yok")
    if len(et) != 10: sorun.append(f"etiket sayisi {len(et)}")
    if len(etiket) > 500: sorun.append("etiket 500 karakteri asiyor")
    hata += bool(sorun)
    print(no, len(baslik), len(et), len(etiket), "OK" if not sorun else sorun, "|", baslik)
    out.append({"no": no, "video": ad, "durum": durum, "birincil_ifade": p, "birincil_ilk_sayfa": k(p), "ikincil_1": s1, "ikincil_1_ilk_sayfa": k(s1), "ikincil_2": s2, "ikincil_2_ilk_sayfa": k(s2),
                "onerilen_baslik": baslik, "baslik_karakter": len(baslik), "etiketler_10": etiket, "etiket_karakter": len(etiket), "umutsuz_ifadeler": umutsuz, "kazanilabilir_ifadeler": kazan, "not": notu})
with open(os.path.join(K, "oneriler-baslik-etiket.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print("hata:", hata)
rows = list(csv.DictReader(open(os.path.join(K, "kanit-arama-sonuclari.csv"), encoding="utf-8")))
v = [r for r in rows if r["tur"] == "video"]
ab = [r for r in v if r["sorgu"].startswith("ali baba")]
print("ali baba basliklari: kesmeli", sum(1 for r in ab if "baba'n" in r["baslik"].lower() or "baba’n" in r["baslik"].lower()), "kesmesiz", sum(1 for r in ab if "babanın" in r["baslik"].replace("I", "ı").replace("İ", "i").lower()), "toplam", len(ab))
for et, f in [("kucuk kanal ilk10", lambda r: r["kanal_boyu"].startswith("kucuk") and int(r["sira"]) <= 10), ("kucuk kanal tum sayfa", lambda r: r["kanal_boyu"].startswith("kucuk")), ("dev kanal (1Mn+)", lambda r: r["kanal_boyu"].startswith("dev")), ("tum videolar", lambda r: True)]:
    g = [r for r in v if f(r)]; print(f"{et:22} n={len(g):4} sorgu baslikta: {100*sum(1 for r in g if r['sorgu_baslikta']=='evet')/len(g):.0f}%  uzun derleme: {100*sum(1 for r in g if r['uzun_derleme']=='evet')/len(g):.0f}%  son 12 ay: {100*sum(1 for r in g if r['son_12_ay']=='evet')/len(g):.0f}%")
print("sorgu", len(oz), "satir", len(rows), "video", len(v), "tekil video", len({r['video_id'] for r in v}), "kanal", len({r['kanal_id'] for r in v}))
from collections import Counter
print(Counter(o["karar"] for o in oz.values()))
