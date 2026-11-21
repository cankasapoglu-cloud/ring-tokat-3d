#!/usr/bin/env python3
"""Kalibrasyon kumesi: kullanicinin kulagiyla yargiladigi kayitlar (yollar cocuk-kanali/ klasorune goredir).
karar: 'begendi' | 'reddetti'.  boyut: kullanicinin gerekcesinin oturdugu boyut(lar).
mevcut_dokum: sarkinin yanindaki eski *_words.json (varsa yeniden dokum ALINMAZ).  dokum: Scribe dokumu gerekli mi."""
import os
KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # cocuk-kanali/
KAL = os.path.join(KOK, "dinleme", "kalibrasyon")
SOZ = os.path.join(KAL, "sozler")

SET = [
    # ---- BEGENILEN / KABUL EDILEN
    dict(ad="ali-baba__v2_2", yol="ali-baba/v2_2.mp3", karar="begendi", sarki="ali-baba",
         gerekce="söyleyiş iyi; ama söylenen hayvan sesleri yanlış (koyun ve at), bir sözcük bozuk ('atıları'), ezgi bilinen ezgi değil",
         boyut=["sozler", "dogallik"], sozler="ali_baba_v2.txt", mevcut_dokum="ali-baba/v2_2_words.json"),
    dict(ad="ali-baba__dinle_2", yol="ali-baba/dinle_2.mp3", karar="begendi", sarki="ali-baba",
         gerekce="'ikincisi daha güzel', 'bu seslendirme uygun'; ezgi yine bilinen ezgi değil",
         boyut=["dogallik", "sozler"], sozler="ali_baba_dinle_bak.txt"),
    dict(ad="el-yikama__coskulu_2", yol="el-yikama/coskulu_2.mp3", karar="begendi", sarki="el-yikama",
         gerekce="el yıkama şarkısı için seçilen coşkulu kayıt", boyut=["enerji"], sozler="el_yikama.txt", dokum=True),
    dict(ad="parmak-ailesi__coskulu_1", yol="parmak-ailesi/coskulu_1.mp3", karar="begendi", sarki="parmak-ailesi",
         gerekce="parmak ailesi için seçilen coşkulu kayıt (beş ad da doğru)", boyut=["enerji", "sozler", "aksan"], sozler="parmak_ailesi.txt", dokum=True),
    dict(ad="ali-baba__demo_altyapi_sesli", yol="ali-baba/yeni/demo_altyapi_sesli.mp3", karar="begendi", sarki="ali-baba",
         gerekce="çalgısal altyapı (klarnet ezgisi + gerçek hayvan sesleri): 'olmuş' (daha coşkulu istendikten sonra)", boyut=["enerji"], sozler=None),
    # ---- REDDEDILEN
    dict(ad="ali-baba__ornek_kita1", yol="ali-baba/yeni/vokal/ornek_kita1.mp3", karar="reddetti", sarki="ali-baba",
         gerekce="konuşma sentezi vokoderle ezgiye oturtuldu: 'sözler çok kötü çıktı'", boyut=["dogallik", "sozler"], sozler="ali_baba_kita1.txt"),
    dict(ad="ali-baba__sarki_birlesik", yol="ali-baba/yeni2/sarki_birlesik.mp3", karar="reddetti", sarki="ali-baba",
         gerekce="yapay vokal iki katına esnetilip perdesi ezgiye düzlendi; kullanıcı ardından doğal söyleyişi istedi (yapay duyuldu)",
         boyut=["dogallik"], sozler="ali_baba_dinle_bak.txt", dokum=True),
    dict(ad="ali-baba__dogal_onizleme", yol="ali-baba/yeni3/onizleme/ali-baba-dogal-onizleme.mp3", karar="reddetti", sarki="ali-baba",
         gerekce="doğal yapay vokal (kendi ezgisi) altta başka ezgi çalan orkestranın üstüne kondu: 'olmamış'",
         boyut=["uyum"], sozler="ali_baba_dinle_bak.txt", dokum=True),
    dict(ad="ali-baba__coskulu_1", yol="ali-baba/coskulu_1.mp3", karar="reddetti", sarki="ali-baba",
         gerekce="'çok kötü; koyun hâlâ mö diyor'; çok uzun (3-3,5 dk)", boyut=["sozler", "sure"], sozler="ali_baba_coskulu.txt", dokum=True),
    dict(ad="ali-baba__coskulu_2", yol="ali-baba/coskulu_2.mp3", karar="reddetti", sarki="ali-baba",
         gerekce="'çok kötü; koyun hâlâ mö diyor'; çok uzun (3-3,5 dk)", boyut=["sozler", "sure"], sozler="ali_baba_coskulu.txt", dokum=True),
    dict(ad="parmak-ailesi__duzgun_1", yol="parmak-ailesi/duzgun_1.mp3", karar="reddetti", sarki="parmak-ailesi",
         gerekce="'çok kötü söylüyor, Türkçe konuşan bir İngiliz gibi' (yabancı aksan)", boyut=["aksan"], sozler="parmak_ailesi.txt",
         mevcut_dokum="parmak-ailesi/duzgun_1_words.json"),
    dict(ad="parmak-ailesi__duzgun_2", yol="parmak-ailesi/duzgun_2.mp3", karar="reddetti", sarki="parmak-ailesi",
         gerekce="'çok kötü söylüyor, Türkçe konuşan bir İngiliz gibi' (yabancı aksan)", boyut=["aksan"], sozler="parmak_ailesi.txt", dokum=True),
    dict(ad="parmak-ailesi__turkce_2", yol="parmak-ailesi/turkce_2.mp3", karar="reddetti", sarki="parmak-ailesi",
         gerekce="sözler yanlış (3. kıtada 'abi parmak' yerine 'anne parmak')", boyut=["sozler"], sozler="parmak_ailesi.txt", dokum=True),
    dict(ad="parmak-ailesi__yavas_2", yol="parmak-ailesi/yavas_2.mp3", karar="reddetti", sarki="parmak-ailesi",
         gerekce="sözler yanlış (3. kıtada 'anne parmak') ve 'ninni gibi söylüyor, coşku yok'", boyut=["sozler", "enerji"], sozler="parmak_ailesi.txt",
         mevcut_dokum="parmak-ailesi/yavas_2_words.json"),
    dict(ad="pitirin-ailesi__yavas_2", yol="pitirin-ailesi/yavas_2.mp3", karar="reddetti", sarki="pitirin-ailesi",
         gerekce="yavaş, sakin kayıt: 'ninni gibi, coşku yok' dönemi", boyut=["enerji"], sozler="pitirin_ailesi.txt",
         mevcut_dokum="pitirin-ailesi/yavas_2_words.json"),
    dict(ad="el-yikama__sarki_1", yol="el-yikama/sarki_1.mp3", karar="reddetti", sarki="el-yikama",
         gerekce="yavaş, sakin kayıt: 'ninni gibi, coşku yok' dönemi", boyut=["enerji"], sozler="el_yikama.txt",
         mevcut_dokum="el-yikama/sarki_1_words.json"),
    dict(ad="parmak-ailesi__sarki_2", yol="parmak-ailesi/sarki_2.mp3", karar="reddetti", sarki="parmak-ailesi",
         gerekce="'sözler çok hızlı geçiyor'", boyut=["hiz"], sozler="parmak_ailesi_kisa.txt", mevcut_dokum="parmak-ailesi/sarki_2_words.json"),
]
for s in SET:
    s["tam_yol"] = os.path.join(KOK, s["yol"])
    s["cikti"] = os.path.join(KAL, "raporlar", s["ad"])
    s["sozler_yol"] = os.path.join(SOZ, s["sozler"]) if s.get("sozler") else None
    s["mevcut_dokum_yol"] = os.path.join(KOK, s["mevcut_dokum"]) if s.get("mevcut_dokum") else None
