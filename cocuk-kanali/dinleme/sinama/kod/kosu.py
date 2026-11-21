#!/usr/bin/env python3
"""kosu.py - sinama kosulari: dinle.py'yi asil dosyada, gurultu kopyalarinda ve her bozuk surumde SIRAYLA calistirir.

- dinle.py DEGISTIRILMEDEN, komut satirindan cagrilir (arac klasoru salt okunur).
- Islemci: baska bir ekip ayni anda calistigi icin her sey 2 cekirdege (2,3) baglanir. Kanal ayirma, aracin kendi
  kanallari_ayir() fonksiyonuyla (ayni komut, yalniz cekirdek secimi farkli) ONCEDEN yapilir; dinle.py sonucu onbellekten bulur.
- Ucretli Scribe cagrisi YALNIZ 'sozler'/'dokum' verilen kosularda olur; dosya onbellekteyse cagri yapilmaz.
- Pano (PNG) uretilmez (--panelsiz); sayilar raporlar/<ad>/rapor.json icindedir.

Kullanim: python3 kosu.py [grup ...]     gruplar: asil gurultu kusur ikinci kuru kisa kanalli
"""
import os, sys, json, time, subprocess

BURASI = os.path.dirname(os.path.abspath(__file__))
SINAMA = os.path.dirname(BURASI)
DINLEME = os.path.dirname(SINAMA)
KANAL = os.path.dirname(DINLEME)
ARAC = os.path.join(DINLEME, "arac")
SES = os.environ.get("SINAMA_SES", os.path.expanduser("~/.cache/dinleme/sinama/ses"))
ASIL = os.path.join(KANAL, "ali-baba", "dinle_2.mp3")
SOZ_ALI = os.path.join(DINLEME, "ornek", "ali_baba_dinle_bak_sozler.txt")
SOZ_K12 = os.path.join(SINAMA, "sozler", "ali_baba_kita12.txt")
SOZ_EL = os.path.join(SINAMA, "sozler", "el_yikama.txt")
HAM = os.path.expanduser("~/.cache/dinleme/kanallar/25bfd4984538765b/ham")
CEKIRDEK = os.environ.get("SINAMA_CEKIRDEK", "2,3")


def s(ad):
    for u in (".mp3", ".wav"):
        if os.path.exists(os.path.join(SES, ad + u)):
            return os.path.join(SES, ad + u)
    raise FileNotFoundError(ad)


def kosular():
    K = []
    K.append(("asil", "00_asil_a", ASIL, ["--ayir", "--sozler", SOZ_ALI]))
    K.append(("asil", "00_asil_b", ASIL, ["--ayir", "--sozler", SOZ_ALI]))
    for ad in ("n3_yeniden_karisim", "n1_yeniden_kodlama", "n2_wav", "n4_kisik_kaydirilmis"):
        K.append(("gurultu", ad, s(ad), ["--ayir"]))
    for ad in ("b01a_detone_50c", "b01b_detone_100c", "b02a_gec_ceyrek", "b02b_gec_yarim", "b03a_esnetme_15", "b03b_esnetme_20",
               "b04k_world_kontrol", "b04_duz_perde", "b05_tik", "b05b_tik_kisik", "b06a_vokal_eksi6", "b06b_vokal_arti6", "b07_satir_sonu_kesik",
               "b08_yanlis_satir", "b09_tempo_80", "b10_alcak_geciren_4k"):
        K.append(("kusur", ad, s(ad), ["--ayir"]))
    K.append(("ikinci", "e1_el_yikama_coskulu_2", os.path.join(KANAL, "el-yikama", "coskulu_2.mp3"), ["--ayir", "--sozler", SOZ_EL]))
    for ad in ("k00_kuru_vokal", "k03a_kuru_esnetme_15", "k03b_kuru_esnetme_20"):
        K.append(("kuru", ad, s(ad), ["--kuru"]))
    # kisa parcalar: ucretli dokum yalniz burada (c07, c08: ~124 kredi; k13b: ~98 kredi)
    K.append(("kisa", "c07_satir_sonu_kesik_kita12", s("c07_satir_sonu_kesik_kita12"), ["--ayir", "--sozler", SOZ_K12]))
    K.append(("kisa", "c08_yanlis_satir_kita12", s("c08_yanlis_satir_kita12"), ["--ayir", "--sozler", SOZ_K12]))
    K.append(("kisa", "k13b_kita1_esnetme_20", s("k13b_kita1_esnetme_20"), ["--kuru", "--dokum", "--hizli"]))
    # kanallar ELDE (ayirma yok): bozuk vokal kanali + altyapi kanali dogrudan verilir (Claude kendi urettigi sarkida bu yolu kullanabilir)
    for ad in ("n3_yeniden_karisim", "b01a_detone_50c", "b02a_gec_ceyrek", "b02b_gec_yarim", "b03b_esnetme_20", "b04_duz_perde", "b04k_world_kontrol",
               "b06a_vokal_eksi6", "b07_satir_sonu_kesik"):
        v = os.path.join(SES, "kanal", ad + "_vokal.wav")
        if os.path.exists(v):
            K.append(("kanalli", "v_" + ad, s(ad), ["--vokal", v, "--altyapi", os.path.join(HAM, "dinle_2_(Instrumental)_UVR-MDX-NET-Voc_FT.wav"), "--hizli"]))
    return K


def main():
    istenen = set(sys.argv[1:])
    sys.path.insert(0, ARAC)
    gunluk_yolu = os.path.join(SINAMA, "kosu_gunlugu.json")
    G = json.load(open(gunluk_yolu, encoding="utf8")) if os.path.exists(gunluk_yolu) else {}
    for grup, ad, dosya, arg in kosular():
        if istenen and grup not in istenen and ad not in istenen:
            continue
        cikti = os.path.join(SINAMA, "raporlar", ad)
        if os.path.exists(os.path.join(cikti, "rapor.json")):
            print("var   :", ad, flush=True)
            continue
        t0 = time.time()
        ayirma = None
        if "--ayir" in arg:
            import dinle_olcum as o
            _, _, bilgi = o.kanallari_ayir(dosya, cekirdek=CEKIRDEK, gunluk=lambda *a: None)
            ayirma = bilgi.get("sure_sn")
        t1 = time.time()
        komut = ["taskset", "-c", CEKIRDEK, sys.executable, os.path.join(ARAC, "dinle.py"), dosya] + arg + ["--panelsiz", "--cikti", cikti]
        r = subprocess.run(komut, capture_output=True, text=True)
        G[ad] = {"grup": grup, "dosya": dosya, "arg": [a.replace(DINLEME, "dinleme") for a in arg], "ayirma_sn": ayirma, "dinle_sn": round(time.time() - t1, 1),
                 "donus": r.returncode, "zaman": time.strftime("%H:%M:%S")}
        if r.returncode != 0 or not os.path.exists(os.path.join(cikti, "rapor.json")):
            G[ad]["hata"] = r.stderr[-800:]
        json.dump(G, open(gunluk_yolu, "w", encoding="utf8"), ensure_ascii=False, indent=1)
        scr = [x for x in r.stderr.splitlines() if "Scribe" in x]
        print("bitti :", ad, "ayirma", ayirma, "dinle %.0f sn" % (time.time() - t1), "donus", r.returncode, " | ".join(scr), flush=True)
    print("TAMAM", flush=True)


if __name__ == "__main__":
    main()
