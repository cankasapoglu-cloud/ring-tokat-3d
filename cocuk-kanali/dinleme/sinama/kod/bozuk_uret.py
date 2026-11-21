#!/usr/bin/env python3
"""bozuk_uret.py - dinleme takiminin sinanmasi icin, HER BIRINDE TEK bilinen kusur olan bozuk surumler uretir.

Kaynak: cocuk-kanali/ali-baba/dinle_2.mp3 (kullanicinin kabul ettigi kayit) ve onun UVR-MDX-NET-Voc_FT ile ayrilmis kanallari
(~/.cache/dinleme/kanallar/25bfd4984538765b/ham/). Vokal + altyapi kanallarinin toplami asil karisimi -42 dB artikla geri verir
(kazanc 1,1812), bu yuzden "yeniden karisim" asil dosyayla ayni sayilir; her bozuk surum bu yeniden karisimin TEK degisiklikli halidir.

Sesler depoya YAZILMAZ (buyuk): ~/.cache/dinleme/sinama/ses/ altina yazilir; bu betik onlari yeniden uretir.
Uretilenlerin listesi ve her kusurun kesin tanimi: dinleme/sinama/bozuklar.json

Kullanim:  python3 bozuk_uret.py            (hepsini uretir; var olani atlar)
           python3 bozuk_uret.py b05_tik    (yalniz adi gecenleri)
           python3 bozuk_uret.py --kanal b01a_detone_50c ...   (karisima dokunmaz; bozuk vokal kanalini kanal/<ad>_vokal.wav yazar:
                                                                dinle.py --vokal/--altyapi yolunu sinamak icin)
"""
import os, sys, json, subprocess, tempfile, re
import warnings
warnings.filterwarnings("ignore")
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_k, "2")
import numpy as np
import soundfile as sf
import scipy.signal as ss

BURASI = os.path.dirname(os.path.abspath(__file__))
SINAMA = os.path.dirname(BURASI)
KANAL = os.path.dirname(os.path.dirname(SINAMA))                      # cocuk-kanali/
ASIL = os.path.join(KANAL, "ali-baba", "dinle_2.mp3")
SOZCUK = os.path.join(KANAL, "ali-baba", "dinle_2_words.json")
HAM = os.path.expanduser("~/.cache/dinleme/kanallar/25bfd4984538765b/ham")
CIKTI = os.environ.get("SINAMA_SES", os.path.expanduser("~/.cache/dinleme/sinama/ses"))
SR = 44100
KAZANC = 1.1812            # asil karisim = KAZANC * (vokal kanali + altyapi kanali); olculdu (artik -41,8 dB)
BPM = 115.9                # aracin buldugu tempo; kita araligi 12,42 sn = 24 vurus -> 115,9 BPM
VURUS = 60.0 / BPM         # 0,5177 sn
UNLU = set("aeıioöuüAEIİOÖUÜ")


def ffmpeg(*a):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + list(a), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg: " + r.stderr[-500:])


YALNIZ_KANAL = False        # --kanal: karisimlari yeniden yazma; yalniz bozuk VOKAL KANALLARINI kanal/<ad>_vokal.wav olarak yaz
SON_VOKAL = {}


def mp3_yaz(ad, x, sr=SR):
    """x: (n,2) float. Kayan noktali WAV uzerinden 192 kb/sn, 48 kHz MP3 (asil dosyayla ayni bicim)."""
    hedef = os.path.join(CIKTI, ad + ".mp3")
    if YALNIZ_KANAL:
        return hedef
    with tempfile.TemporaryDirectory() as g:
        w = os.path.join(g, "x.wav")
        sf.write(w, x.astype(np.float32), sr, subtype="FLOAT")
        ffmpeg("-i", w, "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "192k", hedef)
    return hedef


def wav_yaz(ad, x, sr=SR):
    hedef = os.path.join(CIKTI, ad + ".wav")
    sf.write(hedef, np.clip(x, -1, 1), sr, subtype="PCM_16")
    return hedef


def rubberband(x, sr=SR, **kw):
    """ffmpeg rubberband suzgeci (yuksek kalite). kw: tempo=..., pitch=... Donus ayni kanal sayisinda dizi."""
    with tempfile.TemporaryDirectory() as g:
        a, b = os.path.join(g, "a.wav"), os.path.join(g, "b.wav")
        sf.write(a, x.astype(np.float32), sr, subtype="FLOAT")
        f = "rubberband=" + ":".join("%s=%s" % kv for kv in kw.items())
        ffmpeg("-i", a, "-af", f, "-c:a", "pcm_f32le", b)
        y, _ = sf.read(b, always_2d=True)
    return y


def zarf(x, sr=SR, hop=64):
    m = np.abs(x.mean(axis=1) if x.ndim == 2 else x)
    n = len(m) // hop
    return m[:n * hop].reshape(n, hop).mean(axis=1)


def gecikme_bul(ref, y, sr=SR, en_cok=0.25):
    """y'nin ref'e gore gecikmesi (ornek; + = y gec). Zarf capraz iliskisiyle; 64 ornek (1,5 ms) cozunurluk."""
    hop = 64
    a, b = zarf(ref, sr, hop), zarf(y, sr, hop)
    n = min(len(a), len(b))
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    L = int(en_cok * sr / hop)
    c = ss.correlate(b, a, "full")
    orta = len(a) - 1
    k = c[orta - L: orta + L + 1].argmax() - L
    return int(k * hop)


def hizala(ref, y):
    """y'yi ref ile ayni uzunluga ve hizaya getirir."""
    g = gecikme_bul(ref, y)
    if g > 0:
        y = y[g:]
    elif g < 0:
        y = np.concatenate([np.zeros((-g,) + y.shape[1:]), y])
    n = len(ref)
    if len(y) < n:
        y = np.concatenate([y, np.zeros((n - len(y),) + y.shape[1:])])
    return y[:n], g


def kaydir(x, sn):
    d = int(round(sn * SR))
    return np.concatenate([np.zeros((d, x.shape[1])), x[:len(x) - d]]) if d > 0 else x


def satirlar():
    """Sozcuk zamanlarindan satirlar (satir sonu: . ? ! ile biten sozcuk)."""
    w = [x for x in json.load(open(SOZCUK, encoding="utf8"))["words"] if x.get("type") == "word"]
    S, cur = [], []
    for x in w:
        cur.append(x)
        if x["text"][-1] in ".?!":
            S.append(cur)
            cur = []
    if cur:
        S.append(cur)
    return S, w


def sonme(n, yukari=False):
    r = 0.5 * (1 + np.cos(np.linspace(0, np.pi, n)))
    return (r[::-1] if yukari else r)[:, None]


# ------------------------------------------------------------------------------------------------ kusurlar
def detone(V, cent):
    y = rubberband(V, pitch="%.6f" % (2 ** (cent / 1200.0)), pitchq="quality", formant="preserved")
    return hizala(V, y)


def gidis_donus_esnet(V, kat):
    """Vokali once yuksek kaliteyle 1/kat'a sikistir (rubberband), sonra FAZ VOKODERIYLE kat kadar esnet: sure ve perde
    aslinin aynisi kalir, geriye yalniz 'kat kadar vokoderle esnetilmis ses' dokusu kalir (bulanik gecisler, fazli tini)."""
    import librosa
    k = rubberband(V, tempo="%.6f" % kat)
    y = np.stack([librosa.effects.time_stretch(np.ascontiguousarray(k[:, c]).astype(np.float32), rate=1.0 / kat) for c in range(k.shape[1])], axis=1)
    return hizala(V, y.astype(float))


def world_coz(v):
    import pyworld as pw
    f0, t = pw.harvest(v.astype(np.float64), SR, f0_floor=120.0, f0_ceil=700.0, frame_period=5.0)
    sp = pw.cheaptrick(v.astype(np.float64), f0, t, SR)
    ap = pw.d4c(v.astype(np.float64), f0, t, SR)
    return f0, t, sp, ap


def duz_perde(f0, t, sozcukler):
    """Her 'hece/nota' parcasinin perdesini parcanin medyanina sabitler (otomatik akort benzeri; yarim sese YAPISTIRMAZ, yani
    akort ortalamasi degismez; yalnizca nota ici dogal oynaklik ve notalar arasi kaymalar yok olur)."""
    import scipy.ndimage as ndi
    yeni = f0.copy()
    midi = np.where(f0 > 0, 69 + 12 * np.log2(np.maximum(f0, 1e-6) / 440.0), np.nan)
    n = len(f0)
    parcalar = []
    # YALNIZ sozcuklerin icinde calis: vokal kanalinda sozcuk disinda kalan sizinti (calgi artigi) perdesine dokunma
    for wi, w in enumerate(sozcukler):
        sonraki = sozcukler[wi + 1]["start"] - 0.03 if wi + 1 < len(sozcukler) else 1e9
        a, b = max(0, int((w["start"] - 0.03) / 0.005)), min(n, int(min(w["end"] + 0.05, sonraki) / 0.005))
        i = a
        while i < b:
            if f0[i] <= 0:
                i += 1
                continue
            j = i
            while j + 1 < b and f0[j + 1] > 0:
                j += 1
            # [i, j] kesintisiz sesli kosu: notalara bol
            m = ndi.median_filter(midi[i:j + 1], size=5, mode="nearest")
            bol = [0]
            kume = [m[0]]
            for k in range(1, len(m)):
                if abs(m[k] - np.median(kume)) >= 0.7:
                    bol.append(k)
                    kume = [m[k]]
                else:
                    kume.append(m[k])
            bol.append(len(m))
            seg = [[bol[q], bol[q + 1]] for q in range(len(bol) - 1)]
            # 60 ms'den kisa parcalari (gecis cerceveleri) perdece en yakin komsuya kat
            degisti = True
            while degisti and len(seg) > 1:
                degisti = False
                for q, (s0, s1) in enumerate(seg):
                    if (s1 - s0) * 0.005 < 0.06:
                        med = np.median(m[s0:s1])
                        sol = abs(np.median(m[seg[q - 1][0]:seg[q - 1][1]]) - med) if q > 0 else 1e9
                        sag = abs(np.median(m[seg[q + 1][0]:seg[q + 1][1]]) - med) if q + 1 < len(seg) else 1e9
                        if sol <= sag:
                            seg[q - 1][1] = s1
                        else:
                            seg[q + 1][0] = s0
                        del seg[q]
                        degisti = True
                        break
            for s0, s1 in seg:
                med = float(np.median(m[s0:s1]))
                yeni[i + s0:i + s1] = 440.0 * 2 ** ((med - 69) / 12.0)
                parcalar.append((i + s0, i + s1))
            i = j + 1
    return yeni, parcalar


def world_surum(V, sozcukler, duzlestir):
    import pyworld as pw
    v = V.mean(axis=1)
    f0, t, sp, ap = world_coz(v)
    bilgi = {}
    if duzlestir:
        f0, parcalar = duz_perde(f0, t, sozcukler)
        sure = np.array([(b - a) * 0.005 for a, b in parcalar])
        bilgi = {"parca_sayisi": len(parcalar), "parca_suresi_medyan_sn": round(float(np.median(sure)), 3)}
    y = pw.synthesize(f0, sp, ap, SR, 5.0)
    y = y[:len(v)] if len(y) >= len(v) else np.concatenate([y, np.zeros(len(v) - len(y))])
    # duzey esitle
    y *= np.sqrt((v ** 2).mean() / ((y ** 2).mean() + 1e-12))
    return np.stack([y, y], axis=1), bilgi


def tik_ekle(M, aralik=3.0, ilk=2.37, genlik=0.9):
    y = M.copy()
    darbe = genlik * np.array([1.0, -1.0, 0.7, -0.5, 0.3, -0.2, 0.1, -0.05])
    zamanlar = []
    t = ilk
    while t < len(M) / SR - 1.0:
        i = int(t * SR)
        y[i:i + len(darbe)] += darbe[:, None]
        zamanlar.append(round(t, 2))
        t += aralik
    return y, zamanlar


def satir_sonu_kes(V, S, erken=0.150):
    """Her satirin SON sozcugunu, bitisinden 150 ms once keser (5 ms sonme) ve sonraki satir baslayana kadar vokali susturur."""
    y = V.copy()
    kes = []
    for k, satir in enumerate(S):
        son = satir[-1]
        c = son["end"] - erken
        if c <= son["start"] + 0.03:
            c = son["start"] + 0.03
        sonraki = S[k + 1][0]["start"] if k + 1 < len(S) else len(V) / SR
        bitis = min(sonraki - 0.03, c + 1.2)
        i0, i1 = int(c * SR), int(bitis * SR)
        f = int(0.005 * SR)
        y[i0 - f:i0] *= sonme(f)
        y[i0:i1] = 0.0
        g = int(0.005 * SR)
        if i1 + g < len(y):
            y[i1:i1 + g] *= sonme(g, yukari=True)
        kes.append({"sozcuk": son["text"], "sozcuk_bas": son["start"], "sozcuk_son": son["end"], "kesim": round(c, 3), "sessiz_son": round(bitis, 3)})
    return y, kes


def satir_degistir(V, S, hedef_no, kaynak_no):
    """hedef satirin yerine kaynak satirin SESINI koyar (ayni ezgi, baska sozler). Yerlesim: muzik izgarasina gore (24 vurus = bir kita)."""
    y = V.copy()
    ks, hs = S[kaynak_no], S[hedef_no]
    k0 = ks[0]["start"] - 0.06
    k1 = (S[kaynak_no + 1][0]["start"] - 0.03)
    h0 = hs[0]["start"] - 0.06
    h1 = (S[hedef_no + 1][0]["start"] - 0.03)
    kita = round((hs[0]["start"] - ks[0]["start"]) / VURUS / 4.0) * 4 * VURUS          # olcu katina yuvarla
    yer0 = k0 + kita
    f = int(0.008 * SR)
    # hedef araligi sustur (kaynagin kaplayacagi aralikla birlikte)
    a0, a1 = int(min(h0, yer0) * SR), int(max(h1, yer0 + (k1 - k0)) * SR)
    a1 = min(a1, int((S[hedef_no + 1][0]["start"] - 0.02) * SR))
    y[a0 - f:a0] *= sonme(f)
    y[a0:a1] = 0.0
    y[a1:a1 + f] *= sonme(f, yukari=True)
    parca = V[int(k0 * SR):int(k1 * SR)].copy()
    parca[:f] *= sonme(f, yukari=True)
    parca[-f:] *= sonme(f)
    i = int(yer0 * SR)
    parca = parca[:max(0, a1 - i)]
    y[i:i + len(parca)] += parca
    return y, {"hedef_satir": " ".join(w["text"] for w in hs), "hedef_bas": hs[0]["start"], "hedef_son": hs[-1]["end"],
               "konan_satir": " ".join(w["text"] for w in ks), "kaynak_bas": ks[0]["start"], "kaynak_son": ks[-1]["end"],
               "kaydirma_sn": round(kita, 4), "yerlesim_bas": round(yer0 + 0.06, 3)}


def alcak_geciren(M, hz=4000.0):
    sos = ss.butter(8, hz / (SR / 2), output="sos")
    return ss.sosfiltfilt(sos, M, axis=0)


# ------------------------------------------------------------------------------------------------ ana
def main():
    global YALNIZ_KANAL
    os.makedirs(CIKTI, exist_ok=True)
    if "--kanal" in sys.argv:
        YALNIZ_KANAL = True
        sys.argv.remove("--kanal")
        os.makedirs(os.path.join(CIKTI, "kanal"), exist_ok=True)
    istenen = set(sys.argv[1:])
    V, sr = sf.read(os.path.join(HAM, "dinle_2_(Vocals)_UVR-MDX-NET-Voc_FT.wav"), always_2d=True)
    B, _ = sf.read(os.path.join(HAM, "dinle_2_(Instrumental)_UVR-MDX-NET-Voc_FT.wav"), always_2d=True)
    assert sr == SR
    S, W = satirlar()
    kayit_yolu = os.path.join(SINAMA, "bozuklar.json")
    kayit = json.load(open(kayit_yolu, encoding="utf8")) if os.path.exists(kayit_yolu) else {}
    kayit["_aciklama"] = ("Her surum, 'n3_yeniden_karisim' (vokal kanali + altyapi kanali, asil dosyanin -42 dB artikla aynisi) uzerinde TEK degisiklikle "
                          "uretildi. Sesler ~/.cache/dinleme/sinama/ses altinda; bozuk_uret.py yeniden uretir.")
    kayit["_ortak"] = {"asil": ASIL, "kazanc": KAZANC, "bpm": BPM, "vurus_sn": round(VURUS, 4), "ceyrek_vurus_ms": round(250 * VURUS, 1), "yarim_vurus_ms": round(500 * VURUS, 1)}

    def karis(Vy):
        SON_VOKAL["v"] = Vy
        return KAZANC * (Vy + B)

    def yap(ad, f):
        if istenen and ad not in istenen:
            return
        yol_mp3, yol_wav = os.path.join(CIKTI, ad + ".mp3"), os.path.join(CIKTI, ad + ".wav")
        if YALNIZ_KANAL:
            if not istenen or not ad.startswith(("b", "n3")):
                return
            SON_VOKAL.clear()
            f()
            if "v" in SON_VOKAL:
                sf.write(os.path.join(CIKTI, "kanal", ad + "_vokal.wav"), np.clip(SON_VOKAL["v"], -1, 1), SR, subtype="PCM_16")   # altyapi kanaliyla ayni olcekte (KAZANC uygulanmadan)
                print("kanal yazildi:", ad)
            return
        if not istenen and (os.path.exists(yol_mp3) or os.path.exists(yol_wav)) and ad in kayit:
            print("var :", ad)
            return
        bilgi = f()
        kayit[ad] = bilgi
        json.dump(kayit, open(kayit_yolu, "w", encoding="utf8"), ensure_ascii=False, indent=1)
        print("yazildi:", ad, json.dumps({k: v for k, v in bilgi.items() if k not in ("kesimler", "tik_zamanlari")}, ensure_ascii=False)[:300])

    # ---- gurultu olcumu icin "kusursuz" kopyalar
    def n1():
        ffmpeg("-i", ASIL, "-c:a", "libmp3lame", "-b:a", "192k", os.path.join(CIKTI, "n1_yeniden_kodlama.mp3"))
        return {"tur": "gurultu", "kusur": "yok", "tanim": "asil MP3 cozulup ayni ayarla (192 kb/sn) yeniden kodlandi"}

    def n2():
        ffmpeg("-i", ASIL, "-c:a", "pcm_s16le", os.path.join(CIKTI, "n2_wav.wav"))
        return {"tur": "gurultu", "kusur": "yok", "tanim": "asil MP3 cozulup 16 bit WAV yazildi"}

    def n3():
        mp3_yaz("n3_yeniden_karisim", karis(V))
        return {"tur": "gurultu", "kusur": "yok", "tanim": "ayrilmis vokal + altyapi kanallari toplanip 192 kb/sn MP3 yazildi (butun bozuk surumlerin TABANI)"}

    def n4():
        M = karis(V) * 10 ** (-1 / 20)
        M = np.concatenate([np.zeros((int(0.023 * SR), 2)), M])
        mp3_yaz("n4_kisik_kaydirilmis", M)
        return {"tur": "gurultu", "kusur": "yok", "tanim": "yeniden karisim, 1 dB kisik ve basina 23 ms sessizlik eklenmis (duyulmaz degisiklik)"}
    yap("n1_yeniden_kodlama", n1)
    yap("n2_wav", n2)
    yap("n3_yeniden_karisim", n3)
    yap("n4_kisik_kaydirilmis", n4)

    # ---- 1) detone
    for ad, cent in (("b01a_detone_50c", 50), ("b01b_detone_100c", 100)):
        def f(cent=cent, ad=ad):
            y, g = detone(V, cent)
            mp3_yaz(ad, karis(y))
            return {"tur": "kusur", "no": 1, "kusur": "vokal %d cent tiz (altyapiya gore)" % cent, "yontem": "ffmpeg rubberband pitch (formant korunarak)", "hizalama_duzeltmesi_ornek": g}
        yap(ad, f)
    # ---- 2) gec vokal
    for ad, kesir, soz in (("b02a_gec_ceyrek", 0.25, "ceyrek vurus"), ("b02b_gec_yarim", 0.5, "yarim vurus")):
        def f(kesir=kesir, ad=ad, soz=soz):
            mp3_yaz(ad, karis(kaydir(V, kesir * VURUS)))
            return {"tur": "kusur", "no": 2, "kusur": "vokal %s (%.0f ms) gec" % (soz, 1000 * kesir * VURUS), "gecikme_ms": round(1000 * kesir * VURUS, 1)}
        yap(ad, f)
    # ---- 3) vokoderle esnetme (karisimda: gidis-donus; kuru: duz esnetme)
    for ad, kat in (("b03a_esnetme_15", 1.5), ("b03b_esnetme_20", 2.0)):
        def f(kat=kat, ad=ad):
            y, g = gidis_donus_esnet(V, kat)
            mp3_yaz(ad, karis(y))
            return {"tur": "kusur", "no": 3, "kusur": "vokal %.1f kat faz vokoderiyle esnetilmis dokuda (sure ve perde ayni)" % kat,
                    "yontem": "rubberband ile 1/%.1f'e sikistir, librosa faz vokoderiyle %.1f kat esnet" % (kat, kat), "hizalama_duzeltmesi_ornek": g}
        yap(ad, f)
    vm = V.mean(axis=1)

    def k00():
        wav_yaz("k00_kuru_vokal", vm)
        return {"tur": "kuru taban", "kusur": "yok", "tanim": "ayrilmis vokal kanali, tek kanal, degisiklik yok"}
    yap("k00_kuru_vokal", k00)
    for ad, kat in (("k03a_kuru_esnetme_15", 1.5), ("k03b_kuru_esnetme_20", 2.0)):
        def f(kat=kat, ad=ad):
            import librosa
            y = librosa.effects.time_stretch(vm.astype(np.float32), rate=1.0 / kat)
            wav_yaz(ad, y)
            return {"tur": "kusur (kuru vokal)", "no": 3, "kusur": "kuru vokal faz vokoderiyle %.1f kat esnetildi (perde ayni, sure %.1f kat)" % (kat, kat), "sure_sn": round(len(y) / SR, 1)}
        yap(ad, f)
    # kisa parcalar (1. kita) - Scribe ile hece hizi icin (az kredi)
    a0, a1 = int(5.9 * SR), int(14.8 * SR)

    def k10():
        wav_yaz("k10_kita1_kuru", vm[a0:a1])
        return {"tur": "kuru taban (kisa)", "kusur": "yok", "tanim": "kuru vokal 5,9-14,8 sn (1. kita)"}
    yap("k10_kita1_kuru", k10)
    for ad, kat in (("k13a_kita1_esnetme_15", 1.5), ("k13b_kita1_esnetme_20", 2.0)):
        def f(kat=kat, ad=ad):
            import librosa
            y = librosa.effects.time_stretch(vm[a0:a1].astype(np.float32), rate=1.0 / kat)
            wav_yaz(ad, y)
            return {"tur": "kusur (kuru vokal, kisa)", "no": 3, "kusur": "1. kita kuru vokal %.1f kat esnetildi" % kat, "sure_sn": round(len(y) / SR, 1)}
        yap(ad, f)
    # ---- 4) hece basina duz perde (WORLD) + denetim (WORLD, perde ayni)
    def b04k():
        y, _ = world_surum(V, W, False)
        mp3_yaz("b04k_world_kontrol", karis(y))
        return {"tur": "denetim", "no": 4, "kusur": "yok sayilir (vokal WORLD vokoderinden gecirildi, perde AYNI, tek kanala indi)", "yontem": "pyworld harvest + cheaptrick + d4c + synthesize"}

    def b04():
        y, bilgi = world_surum(V, W, True)
        mp3_yaz("b04_duz_perde", karis(y))
        d = {"tur": "kusur", "no": 4, "kusur": "vokalin perdesi her hece/nota parcasinda sabit (otomatik akort benzeri, yarim sese yapistirilmadan)", "yontem": "pyworld; parca medyani"}
        d.update(bilgi)
        return d
    yap("b04k_world_kontrol", b04k)
    yap("b04_duz_perde", b04)
    # ---- 5) tik
    def b05():
        y, z = tik_ekle(karis(V))
        mp3_yaz("b05_tik", y)
        return {"tur": "kusur", "no": 5, "kusur": "her 3 saniyede bir tik (0,18 ms, genlik 0,9; %d adet)" % len(z), "tik_zamanlari": z}
    yap("b05_tik", b05)
    # ---- 6) vokal duzeyi
    for ad, dbv in (("b06a_vokal_eksi6", -6.0), ("b06b_vokal_arti6", 6.0)):
        def f(dbv=dbv, ad=ad):
            M = karis(V * 10 ** (dbv / 20.0))
            taban = KAZANC * (V + B)
            g = float(np.sqrt((taban ** 2).mean() / (M ** 2).mean()))          # TEK kusur kalsin diye karisimin genel duzeyi tabana esitlenir
            mp3_yaz(ad, M * g)
            return {"tur": "kusur", "no": 6, "kusur": "vokal altyapiya gore %+.0f dB (karisimin genel duzeyi tabanla esitlendi)" % dbv, "genel_kazanc_db": round(20 * np.log10(g), 2)}
        yap(ad, f)
    # ---- 7) satir sonu kesik
    def b07():
        y, kes = satir_sonu_kes(V, S)
        mp3_yaz("b07_satir_sonu_kesik", karis(y))
        return {"tur": "kusur", "no": 7, "kusur": "her satirin son sozcugu 150 ms erken kesildi (%d satir)" % len(kes), "kesimler": kes}
    yap("b07_satir_sonu_kesik", b07)
    # ---- 8) yanlis satir
    def b08():
        y, bilgi = satir_degistir(V, S, hedef_no=6, kaynak_no=2)
        mp3_yaz("b08_yanlis_satir", karis(y))
        d = {"tur": "kusur", "no": 8, "kusur": "2. kitanin 3. satiri yerine 1. kitanin 3. satiri soyleniyor (yanlis soz, ayni ezgi)"}
        d.update(bilgi)
        return d
    yap("b08_yanlis_satir", b08)
    # ---- 7k / 8k) ayni kusurlarin KISA parcalari (1. ve 2. kita, 5,0-27,5 sn): ucretli soz dokumu (Scribe) yalniz bunlarda yapilir (kredi az)
    k0, k1 = int(5.0 * SR), int(27.5 * SR)

    def c07():
        y, kes = satir_sonu_kes(V, S)
        mp3_yaz("c07_satir_sonu_kesik_kita12", karis(y)[k0:k1])
        return {"tur": "kusur (kisa parca)", "no": 7, "kusur": "b07'nin 5,0-27,5 sn parcasi (8 satir sonu kesik)", "parca": [5.0, 27.5]}

    def c08():
        y, bilgi = satir_degistir(V, S, hedef_no=6, kaynak_no=2)
        mp3_yaz("c08_yanlis_satir_kita12", karis(y)[k0:k1])
        return {"tur": "kusur (kisa parca)", "no": 8, "kusur": "b08'in 5,0-27,5 sn parcasi (2. kitanin 3. satiri yanlis)", "parca": [5.0, 27.5]}
    yap("c07_satir_sonu_kesik_kita12", c07)
    yap("c08_yanlis_satir_kita12", c08)
    # ---- 9) tempo %80
    def b09():
        y = rubberband(karis(V), tempo="0.8")
        mp3_yaz("b09_tempo_80", y)
        return {"tur": "kusur", "no": 9, "kusur": "butun sarki %80 tempoya yavaslatildi (perde ayni)", "yontem": "ffmpeg rubberband tempo=0.8", "sure_sn": round(len(y) / SR, 1)}
    yap("b09_tempo_80", b09)
    # ---- 10) 4 kHz alcak geciren
    def b10():
        mp3_yaz("b10_alcak_geciren_4k", alcak_geciren(karis(V)))
        return {"tur": "kusur", "no": 10, "kusur": "butun karisim 4 kHz'de kesildi (8. derece Butterworth, sifir fazli)"}
    yap("b10_alcak_geciren_4k", b10)
    json.dump(kayit, open(kayit_yolu, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print("bitti ->", CIKTI)


if __name__ == "__main__":
    main()
