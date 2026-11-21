#!/usr/bin/env python3
"""dinle_model.py - dinle.py'nin MODEL TABANLI gostergeleri (hepsi yerel, CPU, 2 is parcacigi; anahtar gerekmez).

  ced_etiket()   CED-mini ses etiketleyici (AudioSet 527 sinif): sarki mi konusma mi, ninni mi coskulu mu, hayvan sesi var mi
  musiccoca()    MusicCoCa metin-muzik benzerligi: "coskulu cocuk sarkisi" mi "yavas ninni" mi (yalnizca TAM KARISIMDA anlamli)
  mos_tahminleri()  konusma kalitesi tahmincileri (DNSMOS, NISQA, Distill-MOS, UTMOS22): KURU VOKALDE gurultu/bozulma alarmi

Hepsi egitildigi veriye baglidir: Turkce cocuk sarkisi icin dogrulanmis DEGILDIR. Sayilar mutlak not degil,
iki surumu ayni yolla olcup KARSILASTIRMAK icindir. Agirlik dosyalari kurulum/kur.sh ile iner; eksikse o olcum atlanir.
"""
import os, sys, time, warnings

warnings.filterwarnings("ignore")
import numpy as np

MODELLER = os.environ.get("DINLEME_MODELLER", os.path.join(os.path.expanduser("~"), ".cache", "dinleme", "modeller"))
IS_PARCACIGI = 2


def _yuv(x, n=3):
    try:
        x = float(x)
        return None if (x != x or x in (float("inf"), float("-inf"))) else round(x, n)
    except Exception:
        return None


def pencereler(x, sr, pen=10.0, adim=10.0, en_az=3.0):
    """(baslangic_sn, parca) listesi; cok sessiz parcalar atilir."""
    w, h = int(pen * sr), int(adim * sr)
    cikti = []
    for s in range(0, max(1, len(x) - int(en_az * sr) + 1), h):
        p = x[s:s + w]
        if len(p) < en_az * sr:
            continue
        if np.sqrt(np.mean(p ** 2)) < 2e-3:
            continue
        cikti.append((s / sr, p))
    return cikti


# ----------------------------------------------------------------------------------------------------------
# CED ses etiketleyici
# ----------------------------------------------------------------------------------------------------------
CED_KLASOR = os.path.join(MODELLER, "ced", "sherpa-onnx-ced-mini-audio-tagging-2024-04-19")
CED_SECILI = {
    "ses_turu": ["Music", "Singing", "Child singing", "Female singing", "Male singing", "Speech", "Child speech, kid speaking",
                 "Synthetic singing", "Speech synthesizer", "Rapping", "Humming", "Chant"],
    "duygu": ["Music for children", "Happy music", "Exciting music", "Funny music", "Tender music", "Lullaby", "Sad music"],
    "hayvan": ["Animal", "Cattle, bovinae", "Moo", "Sheep", "Bleat", "Goat", "Horse", "Neigh, whinny", "Chicken, rooster",
               "Crowing, cock-a-doodle-doo", "Duck", "Quack", "Dog", "Bark", "Cat", "Meow", "Bird", "Pig", "Oink", "Frog"],
}
_ced = None


def ced_etiket(x16, pen=10.0):
    """x16: 16 kHz tek kanal. Donus: ortalama olasiliklar + pencere pencere zaman cizelgesi."""
    global _ced
    if not os.path.exists(os.path.join(CED_KLASOR, "model.onnx")):
        return {"atlandi": "CED modeli yok (kurulum/kur.sh calistirin)"}
    try:
        import sherpa_onnx
        if _ced is None:
            _ced = sherpa_onnx.AudioTagging(sherpa_onnx.AudioTaggingConfig(
                model=sherpa_onnx.AudioTaggingModelConfig(ced=os.path.join(CED_KLASOR, "model.onnx"), num_threads=IS_PARCACIGI,
                                                          debug=False, provider="cpu"),
                labels=os.path.join(CED_KLASOR, "class_labels_indices.csv"), top_k=527))
        t0 = time.time()
        top, cizelge = {}, []
        P = pencereler(x16, 16000, pen, pen)
        for bas, p in P:
            st = _ced.create_stream()
            st.accept_waveform(16000, np.ascontiguousarray(p, dtype=np.float32))
            d = {ev.name: float(ev.prob) for ev in _ced.compute(st)}
            for k, v in d.items():
                top[k] = top.get(k, 0.0) + v
            cizelge.append({"bas": round(bas, 1), **{k: round(d.get(k, 0.0), 3) for k in
                                                     ("Singing", "Speech", "Lullaby", "Exciting music", "Happy music", "Animal")}})
        n = max(1, len(P))
        ort = {k: v / n for k, v in top.items()}
        c = {"pencere_sn": pen, "pencere_sayisi": len(P), "sure_sn": round(time.time() - t0, 1),
             "en_yuksek_10": [[k, round(v, 3)] for k, v in sorted(ort.items(), key=lambda kv: -kv[1])[:10]]}
        for grup, adlar in CED_SECILI.items():
            c[grup] = {a: round(ort.get(a, 0.0), 3) for a in adlar if ort.get(a, 0.0) >= 0.001 or grup != "hayvan"}
        c["zaman_cizelgesi"] = cizelge
        coskulu = ort.get("Exciting music", 0) + ort.get("Happy music", 0) + ort.get("Funny music", 0)
        sakin = ort.get("Lullaby", 0) + ort.get("Tender music", 0) + ort.get("Sad music", 0)
        c["coskulu_eksi_sakin"] = round(coskulu - sakin, 3)
        c["ninni_olasiligi"] = round(ort.get("Lullaby", 0.0), 3)
        c["sarki_eksi_konusma"] = round(ort.get("Singing", 0) - ort.get("Speech", 0), 3)
        c["aciklama"] = ("AudioSet etiket olasiliklari (0-1), 10 sn'lik pencerelerin ortalamasi. Kucuk ve kalibre edilmemis sayilardir: "
                         "mutlak deger degil, surumler arasi fark anlamlidir. Projedeki 9 dosyalik denemede 'Lullaby' etiketi yavas "
                         "surumlerde 0,026-0,049, coskulu surumlerde 0,000 cikti (n=9, etiketler uretim niyeti).")
        return c
    except Exception as e:
        return {"hata": "%s: %s" % (type(e).__name__, str(e)[:200])}


# ----------------------------------------------------------------------------------------------------------
# MusicCoCa (metin-muzik ortak uzayi)
# ----------------------------------------------------------------------------------------------------------
COCA_KLASOR = os.path.join(MODELLER, "musiccoca")
COCA_CIFTLER = [
    ("cosku", ["energetic upbeat happy children's song", "exciting lively dance song for kids", "fast cheerful party music"],
     ["slow calm sleepy lullaby", "gentle soothing quiet bedtime song", "slow soft relaxing music"]),
    ("tempo", ["fast tempo dance music"], ["slow tempo ballad"]),
    ("kayit_kalitesi", ["professional studio recording, high quality"], ["low quality amateur recording, noisy and distorted"]),
    ("sarki_var", ["song with vocals"], ["instrumental music without vocals"]),
]
_coca = None


def _coca_yukle():
    global _coca
    if _coca is None:
        import sentencepiece
        from ai_edge_litert.interpreter import Interpreter

        def interp(ad):
            it = Interpreter(model_path=os.path.join(COCA_KLASOR, ad), num_threads=IS_PARCACIGI)
            it.allocate_tensors()
            return it
        sp = sentencepiece.SentencePieceProcessor()
        sp.Load(os.path.join(COCA_KLASOR, "spm.model"))
        _coca = {"sp": sp, "txt": interp("text_encoder.tflite"), "pre": interp("audio_preprocessor.tflite"), "enc": interp("music_encoder.tflite"), "metin": {}}
    return _coca


def coca_metin(s, L=128):
    m = _coca_yukle()
    if s in m["metin"]:
        return m["metin"][s]
    ids = [1] + m["sp"].EncodeAsIds(s.lower())[:L - 1]
    n = len(ids)
    ids = np.array(ids + [0] * (L - n), dtype=np.int32)
    pad = np.ones(L, np.float32)
    pad[:n] = 0
    for d in m["txt"].get_input_details():
        m["txt"].set_tensor(d["index"], (ids if d["dtype"] == np.int32 else pad).reshape(d["shape"]))
    m["txt"].invoke()
    e = m["txt"].get_tensor(m["txt"].get_output_details()[0]["index"]).flatten().astype(np.float32)
    e = e / np.linalg.norm(e)
    m["metin"][s] = e
    return e


def coca_ses(parca16):
    m = _coca_yukle()
    d = m["pre"].get_input_details()[0]
    buf = np.zeros(int(np.prod(d["shape"])), np.float32)
    n = min(len(parca16), len(buf))
    buf[:n] = parca16[:n]
    m["pre"].set_tensor(d["index"], buf.reshape(d["shape"]))
    m["pre"].invoke()
    oz = m["pre"].get_tensor(m["pre"].get_output_details()[0]["index"])
    m["enc"].set_tensor(m["enc"].get_input_details()[0]["index"], oz)
    m["enc"].invoke()
    e = m["enc"].get_tensor(m["enc"].get_output_details()[0]["index"]).flatten().astype(np.float32)
    return e / np.linalg.norm(e)


def musiccoca(x16, gomme_dondur=False):
    """x16: TAM KARISIM, 16 kHz tek kanal. Donus: metin ciftlerine benzerlik farklari + zaman egrisi."""
    if not all(os.path.exists(os.path.join(COCA_KLASOR, f)) for f in ("text_encoder.tflite", "audio_preprocessor.tflite", "music_encoder.tflite", "spm.model")):
        return {"atlandi": "MusicCoCa agirliklari yok (kurulum/kur.sh calistirin)"}
    try:
        t0 = time.time()
        P = pencereler(x16, 16000, 10.0, 10.0, en_az=5.0)
        if not P:
            return {"atlandi": "ses cok kisa ya da sessiz"}
        E = np.array([coca_ses(p) for _, p in P])
        ort = E.mean(axis=0)
        ort = ort / np.linalg.norm(ort)
        c = {"pencere_sayisi": len(P)}
        for ad, arti, eksi in COCA_CIFTLER:
            A = np.array([coca_metin(s) for s in arti])
            B = np.array([coca_metin(s) for s in eksi])
            c[ad] = {"fark": _yuv(float((A @ ort).mean() - (B @ ort).mean())), "arti": _yuv(float((A @ ort).mean())), "eksi": _yuv(float((B @ ort).mean())),
                     "arti_metin": arti[0], "eksi_metin": eksi[0]}
            if ad == "cosku":
                c["cosku_zaman"] = [{"bas": round(bas, 1), "fark": _yuv(float((A @ e).mean() - (B @ e).mean()))} for (bas, _), e in zip(P, E)]
        c["sure_sn"] = round(time.time() - t0, 1)
        c["aciklama"] = ("Ses ile Ingilizce tanim metinleri arasindaki benzerlik farki (arti = soldaki tanima daha yakin). Kalibre edilmemis, "
                         "goreli bir sayidir. Projedeki denemede 'cosku' farki 6 coskulu surumde +0,09..+0,23, 3 yavas surumde -0,06..-0,08 cikti "
                         "(n=9). Yalnizca tam karisimda anlamlidir; kuru vokalde ya da konusmada guvenilmez.")
        if gomme_dondur:
            c["_gomme"] = ort
        return c
    except Exception as e:
        return {"hata": "%s: %s" % (type(e).__name__, str(e)[:200])}


# ----------------------------------------------------------------------------------------------------------
# konusma kalitesi (MOS) tahmincileri - yalnizca KURU VOKAL icin
# ----------------------------------------------------------------------------------------------------------
_mos = {}


def _dnsmos(P):
    import onnxruntime as ort
    if "dnsmos" not in _mos:
        asil = ort.InferenceSession

        def oturum(yol, *a, **k):
            so = ort.SessionOptions()
            so.intra_op_num_threads = IS_PARCACIGI
            so.inter_op_num_threads = 1
            k.setdefault("providers", ["CPUExecutionProvider"])
            return asil(yol, so, *a[1:], **k) if a else asil(yol, so, **k)
        ort.InferenceSession = oturum
        try:
            from speechmos import dnsmos
            _mos["dnsmos"] = dnsmos
            dnsmos.run(np.zeros(16000, np.float32) + 1e-4, sr=16000)          # oturumlar burada kurulur
        finally:
            ort.InferenceSession = asil
    dn = _mos["dnsmos"]
    S = []
    for _, p in P:
        p = p / max(1e-9, np.abs(p).max()) * 0.95
        r = dn.run(p, sr=16000)
        S.append([r["ovrl_mos"], r["sig_mos"], r["bak_mos"], r["p808_mos"]])
    S = np.array(S)
    return {"genel": _yuv(S[:, 0].mean(), 2), "sinyal": _yuv(S[:, 1].mean(), 2), "arka_plan": _yuv(S[:, 2].mean(), 2), "p808": _yuv(S[:, 3].mean(), 2),
            "pencereler_genel": [_yuv(v, 2) for v in S[:, 0]]}


def _nisqa(P):
    import torch
    import torchmetrics.functional.audio.nisqa as tn
    klasor = os.path.join(MODELLER, "nisqa")
    if not os.path.exists(os.path.join(klasor, "nisqa.tar")):
        return {"atlandi": "NISQA agirligi yok"}
    tn.NISQA_DIR = klasor
    S = np.array([tn.non_intrusive_speech_quality_assessment(torch.from_numpy(np.ascontiguousarray(p)), 16000).numpy() for _, p in P])
    return {"genel": _yuv(S[:, 0].mean(), 2), "gurultusuzluk": _yuv(S[:, 1].mean(), 2), "kesintisizlik": _yuv(S[:, 2].mean(), 2),
            "renklenmezlik": _yuv(S[:, 3].mean(), 2), "ses_duzeyi": _yuv(S[:, 4].mean(), 2),
            "pencereler_genel": [_yuv(v, 2) for v in S[:, 0]], "pencereler_kesintisizlik": [_yuv(v, 2) for v in S[:, 2]]}


def _distill(P):
    import torch
    if "distill" not in _mos:
        import distillmos
        m = distillmos.ConvTransformerSQAModel()
        m.eval()
        _mos["distill"] = m
    m = _mos["distill"]
    with torch.no_grad():
        S = [float(m(torch.from_numpy(np.ascontiguousarray(p))[None])) for _, p in P]
    return {"genel": _yuv(np.mean(S), 2), "pencereler_genel": [_yuv(v, 2) for v in S]}


def _utmos(P):
    import torch
    agirlik = os.path.join(MODELLER, "utmos22", "utmos22_strong_step7459_v1.pt")
    depo = os.path.join(MODELLER, "repolar", "SpeechMOS")
    if not (os.path.exists(agirlik) and os.path.isdir(depo)):
        return {"atlandi": "UTMOS22 agirligi ya da kaynak kodu yok"}
    if "utmos" not in _mos:
        # Depodaki paketin adi da "speechmos" (DNSMOS'un pip paketiyle ayni ad): cakismasin diye alt paketi baska adla yukluyoruz.
        import importlib, importlib.util
        kok = os.path.join(depo, "speechmos", "utmos22")
        spec = importlib.util.spec_from_file_location("dinleme_utmos22", os.path.join(kok, "__init__.py"), submodule_search_locations=[kok])
        mod = importlib.util.module_from_spec(spec)
        sys.modules["dinleme_utmos22"] = mod
        spec.loader.exec_module(mod)
        UTMOS22Strong = importlib.import_module("dinleme_utmos22.strong.model").UTMOS22Strong
        m = UTMOS22Strong()
        m.load_state_dict(torch.load(agirlik, map_location="cpu", weights_only=True))
        m.eval()
        _mos["utmos"] = m
    m = _mos["utmos"]
    with torch.no_grad():
        S = [float(m(torch.from_numpy(np.ascontiguousarray(p))[None], 16000)) for _, p in P]
    return {"genel": _yuv(np.mean(S), 2), "pencereler_genel": [_yuv(v, 2) for v in S]}


def mos_tahminleri(v16, hangileri=("dnsmos", "nisqa", "distillmos", "utmos22")):
    """v16: KURU VOKAL (ya da ayrilmis vokal kanali), 16 kHz tek kanal."""
    try:
        import torch
        torch.set_num_threads(IS_PARCACIGI)
    except Exception:
        pass
    P = pencereler(v16, 16000, 10.0, 10.0, en_az=4.0)
    c = {"pencere_sn": 10.0, "pencere_baslangiclari": [round(b, 1) for b, _ in P]}
    if not P:
        c["atlandi"] = "vokal cok kisa ya da sessiz"
        return c
    fonk = {"dnsmos": _dnsmos, "nisqa": _nisqa, "distillmos": _distill, "utmos22": _utmos}
    for ad in hangileri:
        t0 = time.time()
        try:
            c[ad] = fonk[ad](P)
            if isinstance(c[ad], dict):
                c[ad]["sure_sn"] = round(time.time() - t0, 1)
        except Exception as e:
            c[ad] = {"hata": "%s: %s" % (type(e).__name__, str(e)[:160])}
    c["aciklama"] = ("1-5 arasi KONUSMA kalitesi tahminleri (5 = temiz). Sarki icin egitilmediler: sarki sesi, temiz konusmadan hep dusuk "
                     "puan alir; karisimda (muzikli) taban degeri verirler. Kullanim: ayni yolla elde edilmis iki vokali karsilastirmak ve "
                     "gurultu / kirpilma / kopukluk alarmi. Ayrilmis (MDX) vokal, ayirma artiklari yuzunden kuru vokalden dusuk cikar. "
                     "0,5 puandan kucuk farklar anlamsizdir.")
    return c
