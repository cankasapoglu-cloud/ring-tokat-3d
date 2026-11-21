#!/usr/bin/env python3
"""dinle_olcum.py - dinle.py'nin SINYAL OLCUMLERI (model kullanmayan, tekrar edilebilir sayilar).

Bu dosyadaki her fonksiyon tek bir dar seyi olcer. Hicbiri "kulak" degildir:
  temel()            sure, ses yuksekligi (LUFS), gercek tepe, kirpilma, sessizlik, stereo, bant genisligi
  enerji()           tempo ve kararliligi, vurus yogunlugu, vurmali/armonik orani, spektral aki, parlaklik
  kanallari_ayir()   vokal / altyapi ayirma (audio-separator, UVR-MDX-NET-Voc_FT), onbellekli
  duzey_zaman()      vokal - altyapi duzeyi, vokalli sure orani, sizinti
  akor_ve_ton()      altyapinin akorlari (ucsesli sablon + Viterbi), tonu, akort kaymasi
  f0_izle(), notalara_bol()   vokal perde egrisi ve notalar (SwiftF0 + pYIN capraz denetim)
  vokal_uyum()       vokal altyapiyla ayni tonda mi, akor seslerinde mi, cakisan uzun notalar, cent sapmasi
  ritim()            vokal hece/nota baslangiclari vurus izgarasina ne kadar oturuyor
  yapaylik()         vokoder / otomatik akort / zaman esnetme izleri icin SINYAL VEKILLERI (kanit degil, isaret)
"""
import os, re, math, json, hashlib, subprocess, tempfile, warnings, shutil, glob, time

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_k, "2")
warnings.filterwarnings("ignore")
import numpy as np
import soundfile as sf
import scipy.signal as ss
import scipy.ndimage as ndi
import librosa

SR = 22050          # olcum ornekleme hizi (tek kanal)
HOP = 512           # 23,2 ms
NFFT = 2048
ADLAR = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
TR_AD = {"C": "Do", "C#": "Do diyez", "D": "Re", "D#": "Re diyez", "E": "Mi", "F": "Fa", "F#": "Fa diyez",
         "G": "Sol", "G#": "Sol diyez", "A": "La", "A#": "La diyez", "B": "Si"}
ES_AD = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
MAJ = (0, 2, 4, 5, 7, 9, 11)
MIN = (0, 2, 3, 5, 7, 8, 10)
KS_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
ONBELLEK_BUYUK = os.environ.get("DINLEME_KANALLAR", os.path.join(os.path.expanduser("~"), ".cache", "dinleme", "kanallar"))


def yuv(x, n=2):
    """JSON'a yazmak icin guvenli yuvarlama (nan/inf -> None)."""
    try:
        x = float(x)
    except Exception:
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return round(x, n)


def db(x, taban=1e-10):
    return 20.0 * np.log10(np.maximum(np.abs(x), taban))


def nota_adi(midi):
    m = int(round(midi))
    return "%s%d" % (ADLAR[m % 12], m // 12 - 1)


def ton_adi_tr(tonik, mod):
    return "%s %s (%s %s)" % (TR_AD[ADLAR[tonik]], "majör" if mod == "major" else "minör", ADLAR[tonik], "major" if mod == "major" else "minor")


def dosya_ozeti(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for p in iter(lambda: f.read(1 << 20), b""):
            h.update(p)
    return h.hexdigest()


# ----------------------------------------------------------------------------------------------------------
# cozme / yukleme
# ----------------------------------------------------------------------------------------------------------
def ffprobe(yol):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                        "stream=codec_name,sample_rate,channels,bit_rate:format=duration,bit_rate,format_name",
                        "-of", "json", yol], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        s = (d.get("streams") or [{}])[0]
        f = d.get("format", {})
        return {"kodek": s.get("codec_name"), "ornekleme_hz": int(s.get("sample_rate") or 0), "kanal": int(s.get("channels") or 0),
                "bit_hizi_kbps": yuv(float(s.get("bit_rate") or f.get("bit_rate") or 0) / 1000, 0),
                "sure_sn": yuv(float(f.get("duration") or 0), 3)}
    except Exception:
        return {}


def ses_coz(yol, sr=44100):
    """Herhangi bir ses/video dosyasini ffmpeg ile cozer -> (ornekler[n, kanal] float32, sr). Kanal sayisi korunur (en cok 2)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
        gecici = t.name
    try:
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", yol, "-map", "0:a:0", "-ar", str(sr), "-c:a", "pcm_f32le", gecici],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("ffmpeg cozemedi: " + r.stderr.strip()[:300])
        x, sr2 = sf.read(gecici, dtype="float32", always_2d=True)
    finally:
        if os.path.exists(gecici):
            os.unlink(gecici)
    if x.shape[1] > 2:
        x = x[:, :2]
    return x, sr2


def tek_kanal(x, sr, hedef=SR):
    m = x.mean(axis=1) if x.ndim > 1 else x
    if sr != hedef:
        m = librosa.resample(m.astype(np.float32), orig_sr=sr, target_sr=hedef, res_type="soxr_hq")
    return np.ascontiguousarray(m, dtype=np.float32)


def rms_egri(y, cerceve=NFFT, hop=HOP):
    return librosa.feature.rms(y=y, frame_length=cerceve, hop_length=hop, center=True)[0]


def kosular(maske):
    """Mantiksal dizideki True kosularinin (bas, son) indisleri."""
    m = np.asarray(maske, dtype=np.int8)
    d = np.diff(np.concatenate([[0], m, [0]]))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


# ----------------------------------------------------------------------------------------------------------
# a) temel
# ----------------------------------------------------------------------------------------------------------
def ebur128(yol):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", yol, "-map", "0:a:0", "-af", "ebur128=peak=true:framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True)
    s = r.stderr
    i = s.rfind("Summary:")
    blk = s[i:] if i >= 0 else ""

    def g(desen):
        m = re.search(desen, blk)
        try:
            return float(m.group(1)) if m else None
        except ValueError:
            return None
    return {"lufs": g(r"I:\s*(-?[\d.]+) LUFS"), "lra_lu": g(r"LRA:\s*(-?[\d.]+) LU"),
            "gercek_tepe_dbtp": g(r"Peak:\s*(-?[\d.]+) dBFS")}


def temel(yol, x, sr):
    """x: [n, kanal] float32 (cozulmus)."""
    bilgi = ffprobe(yol)
    n, kanal = x.shape
    mono = x.mean(axis=1)
    sure = n / sr
    c = {"dosya": os.path.basename(yol), "sure_sn": yuv(sure, 2), "kanal": kanal, **{k: v for k, v in bilgi.items() if k != "sure_sn"}}
    c.update(ebur128(yol))
    tepe = float(np.abs(x).max()) if n else 0.0
    c["ornek_tepe_dbfs"] = yuv(db(tepe), 2)
    c["rms_dbfs"] = yuv(db(np.sqrt(np.mean(mono ** 2))) if n else None, 2)
    c["tepe_faktoru_db"] = yuv(db(tepe) - db(np.sqrt(np.mean(mono ** 2)) + 1e-12), 1) if n else None
    c["dc_kaymasi"] = yuv(float(mono.mean()), 5)
    # kirpilma: tam olcege dayanmis ornekler ve ardisik kosular
    dolu = np.abs(x).max(axis=1) >= 0.999
    ks = kosular(dolu)
    uzun = [(a, b) for a, b in ks if b - a >= 3]
    c["kirpilma"] = {"tam_olcek_ornek": int(dolu.sum()), "ardisik_kosu_3ornek_ustu": len(uzun),
                     "ilk_zamanlar_sn": [yuv(a / sr, 2) for a, _ in uzun[:12]],
                     "var_mi": bool(len(uzun) >= 3)}
    # sessizlik
    hop = int(sr * 0.02)
    r = librosa.feature.rms(y=mono, frame_length=hop * 2, hop_length=hop)[0]
    rdb = db(r)
    esik = max(-50.0, float(np.percentile(rdb, 95)) - 55.0)
    aktif = rdb > esik
    if aktif.any():
        ilk = int(np.argmax(aktif))
        son = len(aktif) - int(np.argmax(aktif[::-1]))
        ic = [(a, b) for a, b in kosular(~aktif[ilk:son]) if (b - a) * hop / sr >= 0.7]
        c["sessizlik"] = {"esik_dbfs": yuv(esik, 1), "bastaki_sn": yuv(ilk * hop / sr, 2), "sondaki_sn": yuv(max(0.0, sure - son * hop / sr), 2),
                          "ic_bosluklar": [{"bas": yuv((ilk + a) * hop / sr, 2), "son": yuv((ilk + b) * hop / sr, 2)} for a, b in ic[:20]],
                          "sessiz_orani": yuv(1.0 - aktif.mean(), 3)}
    else:
        c["sessizlik"] = {"tamamen_sessiz": True, "sessiz_orani": 1.0}
    # stereo
    if kanal >= 2:
        L, R = x[:, 0].astype(np.float64), x[:, 1].astype(np.float64)
        pay = float(np.sqrt((L ** 2).sum() * (R ** 2).sum()))
        kor = float((L * R).sum() / pay) if pay > 0 else 0.0
        denge = float(db(np.sqrt(np.mean(L ** 2)) + 1e-12) - db(np.sqrt(np.mean(R ** 2)) + 1e-12))
        orta, yan = (L + R) / 2, (L - R) / 2
        yo = float(10 * np.log10(((yan ** 2).sum() + 1e-20) / ((orta ** 2).sum() + 1e-20)))
        st = {"sol_sag_korelasyon": yuv(kor, 3), "denge_db_sol_eksi_sag": yuv(denge, 2), "yan_orta_db": yuv(yo, 1)}
        if kor > 0.9995:
            st["yorum"] = "iki kanal aynı (çift mono): stereo genişlik yok, sorun değil"
        elif kor < 0.0:
            st["yorum"] = "UYARI: kanallar ters fazlı; telefonda (tek hoparlör) ses zayıflar"
        elif kor < 0.3:
            st["yorum"] = "çok geniş stereo: tek hoparlörde bazı sesler zayıflayabilir"
        else:
            st["yorum"] = "olağan stereo"
        if abs(denge) > 3:
            st["yorum"] += "; UYARI: ses bir tarafa yatık (%.1f dB)" % denge
        c["stereo"] = st
    else:
        c["stereo"] = {"yorum": "tek kanal (mono) dosya"}
    # bant genisligi: uzun sureli spektrumda enerjinin bittigi yer
    try:
        f, P = ss.welch(mono, sr, nperseg=4096)
        Pd = 10 * np.log10(P / (P.max() + 1e-30) + 1e-30)
        Pd = ndi.uniform_filter1d(Pd, 9)
        ust = f[np.where(Pd > -75)[0][-1]] if (Pd > -75).any() else 0
        c["ust_frekans_hz"] = int(ust)
    except Exception:
        c["ust_frekans_hz"] = None
    return c


# ----------------------------------------------------------------------------------------------------------
# b) enerji / cosku
# ----------------------------------------------------------------------------------------------------------
def spektrum_paketi(y):
    """Bir kez hesaplanip paylasilan STFT / HPSS / mel / vurus egri paketi."""
    D = librosa.stft(y, n_fft=NFFT, hop_length=HOP)
    S = np.abs(D)
    H, P = librosa.decompose.hpss(S, kernel_size=31)
    mel = librosa.feature.melspectrogram(S=S ** 2, sr=SR, n_mels=128, fmin=40, fmax=11000)
    mel_db = librosa.power_to_db(mel, ref=1.0, top_db=None)
    mel_db = np.maximum(mel_db, mel_db.max() - 80.0)
    oenv = librosa.onset.onset_strength(S=mel_db, sr=SR, hop_length=HOP)
    return {"D": D, "S": S, "H": H, "P": P, "mel_db": mel_db, "oenv": oenv}


def vurus_izgarasi(oenv, bpm=None, ilk_vurus=None, sure=None):
    """Vurus zamanlari (sn). bpm verilirse sabit tempo dayatilir; ilk_vurus da verilirse izgara dogrudan kurulur."""
    if bpm and ilk_vurus is not None and sure:
        adim = 60.0 / bpm
        return float(bpm), np.arange(ilk_vurus, sure, adim)
    try:
        tempo, kare = librosa.beat.beat_track(onset_envelope=oenv, sr=SR, hop_length=HOP, bpm=bpm, tightness=100, trim=False)
        tempo = float(np.atleast_1d(tempo)[0])
        return tempo, librosa.frames_to_time(kare, sr=SR, hop_length=HOP)
    except Exception:
        return 0.0, np.array([])


def enerji(y, paket=None, bpm=None, ilk_vurus=None):
    """y: tek kanal SR. Donus: sayilar + zaman egrileri (panel icin)."""
    paket = paket or spektrum_paketi(y)
    S, H, P, oenv = paket["S"], paket["H"], paket["P"], paket["oenv"]
    sure = len(y) / SR
    r = rms_egri(y)
    rdb = db(r)
    aktif = rdb > max(-50.0, np.percentile(rdb, 95) - 45.0)
    aktif_sure = max(1e-3, aktif.mean() * sure)
    c = {}
    tempo, vurus = vurus_izgarasi(oenv, bpm, ilk_vurus, sure)
    if len(vurus) > 8 and not bpm:
        tempo = 60.0 / ((vurus[-1] - vurus[0]) / (len(vurus) - 1))       # ortalama vurus araligindan (cerceve nicemlemesinden etkilenmez)
    c["tempo_bpm"] = yuv(tempo, 1)
    c["tempo_kaynagi"] = "kullanıcı verdi (--bpm)" if bpm else "otomatik tahmin; yarı/çift tempo hatası yapabilir"
    c["vurus_sayisi"] = int(len(vurus))
    # nabiz netligi: vurus egri oz-iliskisinin vurus araligindaki tepesi
    o = oenv - oenv.mean()
    ac = librosa.autocorrelate(o, max_size=int(4 * SR / HOP))
    ac = ac / (ac[0] + 1e-12)
    if tempo > 0:
        lag = 60.0 / tempo * SR / HOP

        def tepe(l):
            a, b = int(max(1, l * 0.96)), int(min(len(ac) - 1, l * 1.04) + 1)
            return float(ac[a:b].max()) if b > a else 0.0
        c["nabiz_netligi"] = yuv(max(tepe(lag), tepe(lag / 2)), 3)
        c["nabiz_netligi_aciklama"] = "0-1; vurus egri oz-iliskisinin vurus araligindaki tepesi. Yuksek = duzenli, belirgin ritim"
    else:
        c["nabiz_netligi"] = None
    # tempo kararliligi: pencere pencere tempo
    try:
        tg = librosa.feature.tempo(onset_envelope=oenv, sr=SR, hop_length=HOP, aggregate=None)
        tg = np.asarray(tg, dtype=float)[aktif[:len(tg)] if len(aktif) >= len(tg) else slice(None)]
        if tempo > 0 and len(tg):
            kat = tg.copy()
            for _ in range(3):
                kat = np.where(kat > tempo * 1.5, kat / 2, kat)
                kat = np.where(kat < tempo / 1.5, kat * 2, kat)
            c["tempo_kararliligi"] = {"yuzde_3_icinde": yuv(100 * float((np.abs(kat / tempo - 1) < 0.03).mean()), 1),
                                      "yerel_tempo_p10_p90": [yuv(np.percentile(kat, 10), 1), yuv(np.percentile(kat, 90), 1)]}
    except Exception:
        pass
    if len(vurus) > 3:
        ibi = np.diff(vurus)
        c["vurus_araligi_degiskenligi_yuzde"] = yuv(100 * float(np.std(ibi) / (np.mean(ibi) + 1e-9)), 2)
    # vurus (olay) yogunlugu
    on = librosa.onset.onset_detect(onset_envelope=oenv, sr=SR, hop_length=HOP, units="time", backtrack=False)
    c["olay_yogunlugu_sn"] = yuv(len(on) / aktif_sure, 2)
    c["spektral_aki_ort"] = yuv(float(oenv[aktif[:len(oenv)]].mean()) if aktif[:len(oenv)].any() else float(oenv.mean()), 3)
    c["vurmali_armonik_db"] = yuv(10 * np.log10(((P ** 2).sum() + 1e-12) / ((H ** 2).sum() + 1e-12)), 2)
    frek = librosa.fft_frequencies(sr=SR, n_fft=NFFT)
    guc = (S ** 2)
    top = guc.sum()
    mrk = (frek[:, None] * S).sum(axis=0) / (S.sum(axis=0) + 1e-12)
    am = aktif[:len(mrk)] if len(aktif) >= len(mrk) else np.ones(len(mrk), bool)
    c["parlaklik_agirlik_merkezi_hz"] = yuv(float(np.median(mrk[am])) if am.any() else float(np.median(mrk)), 0)
    c["tiz_payi_4khz_ustu_db"] = yuv(10 * np.log10(guc[frek >= 4000].sum() / (top + 1e-12) + 1e-12), 1)
    c["bas_payi_150hz_alti_db"] = yuv(10 * np.log10(guc[frek <= 150].sum() / (top + 1e-12) + 1e-12), 1)
    # kisa sureli duzey oynakligi (3 sn pencere)
    w = int(3 * SR / HOP)
    if len(r) > w * 2:
        kisa = db(np.sqrt(ndi.uniform_filter1d(r ** 2, w)))[w // 2::max(1, w // 3)]
        c["duzey_oynakligi_db"] = yuv(float(np.std(kisa[kisa > -50])) if (kisa > -50).any() else 0.0, 2)
    # 5 sn'lik bolum egrileri
    bol = []
    adim = 5.0
    oz = librosa.times_like(oenv, sr=SR, hop_length=HOP)
    for t0 in np.arange(0, sure, adim):
        m = (oz >= t0) & (oz < t0 + adim)
        if m.sum() < 10:
            continue
        bol.append({"bas": yuv(t0, 1), "duzey_db": yuv(db(np.sqrt(np.mean(r[:len(oz)][m] ** 2))), 1),
                    "olay_sn": yuv(float(((on >= t0) & (on < t0 + adim)).sum() / adim), 2), "aki": yuv(float(oenv[m].mean()), 3)})
    c["bolumler_5sn"] = bol
    c["enerji_puani"] = enerji_puani(c)
    egri = {"oenv": oenv, "rms_db": rdb, "vurus": vurus, "olaylar": on, "tempo": tempo}
    return c, egri


# Enerji puani bilesenleri: (anahtar, alt, ust, agirlik). alt -> 0 puan, ust -> 1 puan. Sinirlar projenin kendi
# sarkilarinda (kurulum/referans_enerji.json) gorulen araliga gore secildi; mutlak bir "cosku olcusu" DEGILDIR.
ENERJI_BILESEN = [("olay_yogunlugu_sn", 2.0, 6.5, 0.25), ("nabiz_netligi", 0.10, 0.60, 0.20), ("vurmali_armonik_db", -16.0, -2.0, 0.20),
                  ("spektral_aki_ort", 0.8, 2.6, 0.20), ("parlaklik_agirlik_merkezi_hz", 1200.0, 3600.0, 0.15)]


def enerji_puani(c):
    top, ag, ayr = 0.0, 0.0, {}
    for anahtar, alt, ust, w in ENERJI_BILESEN:
        v = c.get(anahtar)
        if v is None:
            continue
        p = float(np.clip((v - alt) / (ust - alt), 0, 1))
        ayr[anahtar] = round(p, 2)
        top += w * p
        ag += w
    if ag == 0:
        return None
    return {"puan_0_100": round(100 * top / ag, 0), "bilesenler_0_1": ayr,
            "aciklama": "Sinyal tabanli hareketlilik gostergesi (sarkilar arasi KARSILASTIRMA icin). 'Cocuk bunu sever' demek degildir."}


# ----------------------------------------------------------------------------------------------------------
# c) kanal ayirma
# ----------------------------------------------------------------------------------------------------------
def kanallari_ayir(yol, model="UVR-MDX-NET-Voc_FT.onnx", cekirdek="0,1", gunluk=print):
    """audio-separator ile vokal/altyapi ayirir; sonuc dosya ozetine gore onbelleklenir. Donus: (vokal.wav, altyapi.wav, bilgi)."""
    oz = dosya_ozeti(yol)[:16]
    kl = os.path.join(ONBELLEK_BUYUK, oz)
    ham = os.path.join(kl, "ham")
    os.makedirs(ham, exist_ok=True)

    def bul():
        v = glob.glob(os.path.join(ham, "*(Vocals)*.wav"))
        a = glob.glob(os.path.join(ham, "*(Instrumental)*.wav"))
        return (v[0], a[0]) if v and a else (None, None)
    v, a = bul()
    bilgi = {"model": model, "onbellek": kl, "onbellekten": bool(v)}
    if not v:
        if not shutil.which("audio-separator"):
            raise RuntimeError("audio-separator kurulu degil (pip install audio-separator)")
        komut = ["audio-separator", yol, "--model_filename", model, "--output_format", "WAV", "--output_dir", ham, "--log_level", "warning"]
        if shutil.which("taskset") and cekirdek:
            komut = ["taskset", "-c", cekirdek] + komut          # en cok 2 cekirdek kullan
        gunluk("  kanal ayirma basladi (105 sn'lik sarki icin yaklasik 80-100 sn) ...")
        t = time.time()
        r = subprocess.run(komut, capture_output=True, text=True)
        bilgi["sure_sn"] = round(time.time() - t, 1)
        v, a = bul()
        if not v:
            raise RuntimeError("kanal ayirma basarisiz: " + (r.stderr or r.stdout)[-400:])
    return v, a, bilgi


def duzey_zaman(v, a, f0_sesli_zaman=None):
    """v, a: tek kanal SR (vokal, altyapi). Vokal/altyapi duzeyi, vokalli sure, sizinti."""
    n = min(len(v), len(a))
    v, a = v[:n], a[:n]
    rv, ra = rms_egri(v), rms_egri(a)
    w = max(1, int(0.4 * SR / HOP))
    rv_s = np.sqrt(ndi.uniform_filter1d(rv ** 2, w))
    ra_s = np.sqrt(ndi.uniform_filter1d(ra ** 2, w))
    vdb, adb = db(rv_s), db(ra_s)
    esik = max(-48.0, float(np.percentile(vdb, 95)) - 25.0)
    aktif = vdb > esik
    t = librosa.times_like(rv, sr=SR, hop_length=HOP)
    c = {"vokal_esik_dbfs": yuv(esik, 1), "vokalli_sure_orani": yuv(float(aktif.mean()), 3),
         "vokal_rms_dbfs": yuv(db(np.sqrt(np.mean(v ** 2)) + 1e-12), 1), "altyapi_rms_dbfs": yuv(db(np.sqrt(np.mean(a ** 2)) + 1e-12), 1)}
    if aktif.any():
        fark = (vdb - adb)[aktif]
        c["vokal_eksi_altyapi_db_medyan"] = yuv(float(np.median(fark)), 1)
        c["vokal_eksi_altyapi_db_p10_p90"] = [yuv(np.percentile(fark, 10), 1), yuv(np.percentile(fark, 90), 1)]
        gomuk = aktif & ((vdb - adb) < -8.0)
        c["vokalin_gomuldugu_yerler"] = [{"bas": yuv(t[a_], 1), "son": yuv(t[min(b_, len(t) - 1)], 1)} for a_, b_ in kosular(gomuk)
                                         if (b_ - a_) * HOP / SR >= 1.0][:15]
        m = c["vokal_eksi_altyapi_db_medyan"]
        c["denge_yorumu"] = ("Vokal altyapının belirgin altında (gömük olabilir)" if m < -6 else
                             "Vokal altyapının çok üstünde (altyapı zayıf kalabilir)" if m > 9 else "Vokal-altyapı dengesi olağan aralıkta")
    # vokal bolumleri (0,6 sn'den kisa bosluklar birlestirilir)
    kapali = ndi.binary_closing(aktif, structure=np.ones(max(1, int(0.6 * SR / HOP))))
    c["vokal_bolumleri"] = [{"bas": yuv(t[a_], 2), "son": yuv(t[min(b_, len(t) - 1)], 2)} for a_, b_ in kosular(kapali) if (b_ - a_) * HOP / SR >= 0.3][:80]
    # sizinti: vokal kanalinda, perdeli ses (sarki) OLMAYAN yerlerde kalan duzey
    if f0_sesli_zaman is not None and len(f0_sesli_zaman):
        yakin = np.zeros(len(t), bool)
        idx = np.clip((np.asarray(f0_sesli_zaman) * SR / HOP).astype(int), 0, len(t) - 1)
        yakin[idx] = True
        yakin = ndi.binary_dilation(yakin, structure=np.ones(int(1.0 * SR / HOP)))
        uzak = ~yakin & (adb > -45)
        if uzak.sum() > 20:
            c["sizinti"] = {"vokal_kanali_sarkisiz_yerlerde_db": yuv(db(np.sqrt(np.mean(rv[uzak] ** 2)) + 1e-12), 1),
                            "ayni_yerlerde_altyapi_db": yuv(db(np.sqrt(np.mean(ra[uzak] ** 2)) + 1e-12), 1),
                            "fark_db": yuv(db(np.sqrt(np.mean(rv[uzak] ** 2)) + 1e-12) - db(np.sqrt(np.mean(ra[uzak] ** 2)) + 1e-12), 1),
                            "aciklama": "Sarki soylenmeyen yerlerde vokal kanalinda kalan ses, altyapiya gore. -25 dB'den yuksekse "
                                        "vokal kanalina altyapi/hayvan sesi/efekt sizmis demektir; perde ve dogallik olcumleri orada guvenilmez."}
    egri = {"t": t, "vdb": vdb, "adb": adb, "aktif": aktif}
    return c, egri


# ----------------------------------------------------------------------------------------------------------
# d) altyapi: akor, ton, akort
# ----------------------------------------------------------------------------------------------------------
def ks_ton(pch):
    """Krumhansl-Schmuckler: 12'lik ses sinifi dagilimindan ton. Donus: (tonik, 'major'|'minor', r, ikinci_r)."""
    pch = np.asarray(pch, float)
    if pch.sum() <= 0:
        return None
    sonuc = []
    for k in range(12):
        for mod, prof in (("major", KS_MAJ), ("minor", KS_MIN)):
            r = np.corrcoef(pch, np.roll(prof, k))[0, 1]
            sonuc.append((r, k, mod))
    sonuc.sort(reverse=True)
    return sonuc[0][1], sonuc[0][2], float(sonuc[0][0]), float(sonuc[1][0]), sonuc[:4]


def gam(tonik, mod):
    return {(tonik + i) % 12 for i in (MAJ if mod == "major" else MIN)}


def _akor_sablonlari():
    T, ad = [], []
    for k in range(12):
        for mod, ar in (("", (0, 4, 7)), ("m", (0, 3, 7))):
            v = np.zeros(12)
            v[[(k + i) % 12 for i in ar]] = 1.0
            T.append(v / np.linalg.norm(v))
            ad.append((ADLAR[k] + mod, frozenset((k + i) % 12 for i in ar)))
    return np.array(T), ad


def yerel_tonlar(C, t, r, pencere=24.0, adim=3.0):
    """Kromadan zaman icinde ton (ton degisimini yakalamak icin). Donus: parca listesi [{bas, son, tonik, mod, r, ...}]."""
    sure = float(t[-1]) if len(t) else 0.0
    w = (r / (r.max() + 1e-12))[None, :]
    Cw = C * w
    anahtar = [(k, mod) for k in range(12) for mod in ("major", "minor")]
    prof = np.array([np.roll(KS_MAJ if mod == "major" else KS_MIN, k) for k, mod in anahtar])
    prof = (prof - prof.mean(axis=1, keepdims=True)) / prof.std(axis=1, keepdims=True)

    def kor(pch):
        if pch.sum() <= 0:
            return np.zeros(24)
        z = (pch - pch.mean()) / (pch.std() + 1e-12)
        return prof @ z / 12.0

    def ozet(m):
        R = kor(Cw[:, m].sum(axis=1))
        sira = np.argsort(-R)
        k0 = sira[0]
        g0 = gam(*anahtar[k0])
        farkli = [R[j] for j in sira[1:] if gam(*anahtar[j]) != g0]
        return R, int(k0), float(R[k0]), float(farkli[0]) if farkli else 0.0

    if sure <= pencere * 1.5:
        R, k0, r0, r1 = ozet(np.ones(len(t), bool))
        yol, merkez = [k0], [sure / 2]
    else:
        merkez = list(np.arange(pencere / 2, sure - pencere / 2 + adim, adim))
        Rs = np.array([kor(Cw[:, (t >= m - pencere / 2) & (t < m + pencere / 2)].sum(axis=1)) for m in merkez])
        logB = Rs.T * 22.0
        ceza = 7.0
        skor = logB[:, 0].copy()
        geri = np.zeros(logB.shape, int)
        for j in range(1, logB.shape[1]):
            gecis = skor[None, :] - ceza * (1 - np.eye(24))
            geri[:, j] = gecis.argmax(axis=1)
            skor = gecis.max(axis=1) + logB[:, j]
        yol = [int(skor.argmax())]
        for j in range(logB.shape[1] - 1, 0, -1):
            yol.append(int(geri[yol[-1], j]))
        yol = yol[::-1]
    # parcalar + sinir inceltme
    parca = []
    for j, k in enumerate(yol):
        if parca and parca[-1]["k"] == k:
            parca[-1]["son_m"] = merkez[j]
        else:
            parca.append({"k": k, "bas_m": merkez[j], "son_m": merkez[j]})
    Cn = C / (C.sum(axis=0, keepdims=True) + 1e-9)
    sinirlar = [0.0]
    for i in range(1, len(parca)):
        A, B = gam(*anahtar[parca[i - 1]["k"]]), gam(*anahtar[parca[i]["k"]])
        lo, hi = parca[i - 1]["son_m"] - pencere / 2, parca[i]["bas_m"] + pencere / 2
        m = (t >= lo) & (t <= hi)
        if m.sum() < 4 or A == B:
            sinirlar.append((parca[i - 1]["son_m"] + parca[i]["bas_m"]) / 2)
            continue
        sA = Cn[sorted(A)][:, m].sum(axis=0)
        sB = Cn[sorted(B)][:, m].sum(axis=0)
        kaz = np.cumsum(sA - sB)                       # siniri j'den sonra koymanin kazanci
        sinirlar.append(float(t[m][int(np.argmax(kaz))]))
    sinirlar.append(sure + HOP / SR)
    cikti = []
    for i, pc_ in enumerate(parca):
        bas, son = sinirlar[i], sinirlar[i + 1]
        m = (t >= bas) & (t < son)
        if m.sum() < 2:
            continue
        R, k0, r0, r1 = ozet(m)
        tonik, mod = anahtar[pc_["k"]]
        cikti.append({"bas": yuv(bas, 1), "son": yuv(min(son, sure), 1), "tonik": int(tonik), "mod": mod, "ton": ton_adi_tr(tonik, mod),
                      "r": yuv(float(R[pc_["k"]]), 2), "farkli_gamli_ikinci_r": yuv(r1, 2),
                      "belirsiz": bool(R[pc_["k"]] < 0.6 or (R[pc_["k"]] - r1) < 0.06)})
    return cikti


def akor_ve_ton(a, a44=None, paket=None, vurus=None):
    """a: altyapi (ya da karisim) tek kanal SR. Donus: sozluk + egriler (kroma, akor parcalari, ton parcalari)."""
    paket = paket or spektrum_paketi(a)
    yh = librosa.istft(paket["H"] * np.exp(1j * np.angle(paket["D"])), hop_length=HOP, length=len(a))
    akort = float(librosa.estimate_tuning(y=yh, sr=SR))                    # yarim sesin kesri (-0.5..0.5)
    C = librosa.feature.chroma_cqt(y=yh, sr=SR, hop_length=HOP, tuning=akort, bins_per_octave=36,
                                   fmin=librosa.note_to_hz("C2"), n_octaves=5)
    t = librosa.times_like(C, sr=SR, hop_length=HOP)
    r = rms_egri(a)[:C.shape[1]]
    if len(r) < C.shape[1]:
        r = np.pad(r, (0, C.shape[1] - len(r)))
    c = {"akort_kaymasi_cent": yuv(akort * 100, 1),
         "akort_aciklama": "Altyapinin 440 Hz izgarasindan sapmasi. Vokal cent olcumleri bu izgaraya gore yapilir."}
    # ton: zaman icinde (ton degisimi yakalanir) + essentia capraz denetimi
    tonlar = yerel_tonlar(C, t, r)
    try:
        import essentia
        essentia.log.infoActive = False
        essentia.log.warningActive = False
        import essentia.standard as es
        sinyal = a44 if a44 is not None else librosa.resample(a, orig_sr=SR, target_sr=44100)
        for tp in tonlar:
            parca = sinyal[int(tp["bas"] * 44100):int(tp["son"] * 44100)]
            if len(parca) < 44100 * 8:
                continue
            k_, olcek, guc = es.KeyExtractor(profileType="edma", sampleRate=44100)(np.ascontiguousarray(parca, dtype=np.float32))
            tonik = ADLAR.index(ES_AD.get(k_, k_))
            tp["essentia"] = ton_adi_tr(tonik, olcek)
            tp["essentia_ayni_gam"] = bool(gam(tonik, olcek) == gam(tp["tonik"], tp["mod"]))
            if not tp["essentia_ayni_gam"]:
                tp["belirsiz"] = True
    except Exception as e:
        c["essentia_hata"] = str(e)[:120]
    c["ton_parcalari"] = tonlar
    if tonlar:
        ana = max(tonlar, key=lambda x: x["son"] - x["bas"])
        c["ton"] = ana["ton"]
        c["tonik"], c["mod"] = ana["tonik"], ana["mod"]
        c["ton_belirsiz"] = bool(any(x["belirsiz"] for x in tonlar))
        c["ton_degisimi_var"] = bool(len({(x["tonik"], x["mod"]) for x in tonlar}) > 1)
        c["ton_aciklama"] = ("Ton, kromanin Krumhansl profilleriyle iliskisinden (24 sn'lik pencereler) bulunur; essentia ile capraz denetlenir. "
                             "'belirsiz' ise (iliski zayif ya da iki yontem farkli gam buluyor) gam ici / gam disi oranlarina guvenmeyin; "
                             "etiketsiz 'armonik destek' olcusune bakin.")
    # akorlar: vurus-esli kroma + ucsesli sablonlar + Viterbi yumusatma
    if vurus is None or len(vurus) < 8:
        sinir = np.arange(0, C.shape[1], max(1, int(0.5 * SR / HOP)))
    else:
        sinir = np.unique(np.clip(librosa.time_to_frames(vurus, sr=SR, hop_length=HOP), 0, C.shape[1] - 1))
        if sinir[0] > 0:
            sinir = np.concatenate([[0], sinir])
    Cb = librosa.util.sync(C, sinir, aggregate=np.median)
    rb = librosa.util.sync(r[None, :], sinir, aggregate=np.mean)[0]
    sinir_t = np.concatenate([t[sinir], [t[-1] + HOP / SR]])
    T, adlar = _akor_sablonlari()
    Cn = Cb / (np.linalg.norm(Cb, axis=0, keepdims=True) + 1e-9)
    benz = (T @ Cn)                                                       # [24, parca]
    logB = benz * 25.0
    n_d, n_p = logB.shape
    kal, deg = math.log(0.5), math.log(0.5 / (n_d - 1))
    skor = logB[:, 0].copy()
    geri = np.zeros((n_d, n_p), int)
    for j in range(1, n_p):
        gecis = skor[None, :] + np.where(np.eye(n_d, dtype=bool), kal, deg)   # [yeni, eski]
        geri[:, j] = gecis.argmax(axis=1)
        skor = gecis.max(axis=1) + logB[:, j]
    yol = np.zeros(n_p, int)
    yol[-1] = int(skor.argmax())
    for j in range(n_p - 1, 0, -1):
        yol[j - 1] = geri[yol[j], j]
    sessiz = db(rb) < max(-50.0, np.percentile(db(rb), 95) - 35.0)
    parcalar = []
    for j in range(n_p):
        ad, sesler = ("-", frozenset()) if sessiz[j] else adlar[yol[j]]
        g = 0.0 if sessiz[j] else float(benz[yol[j], j])
        if parcalar and parcalar[-1]["akor"] == ad:
            parcalar[-1]["son"] = float(sinir_t[j + 1])
            parcalar[-1]["_g"].append(g)
        else:
            parcalar.append({"akor": ad, "bas": float(sinir_t[j]), "son": float(sinir_t[j + 1]), "sesler": sorted(sesler), "_g": [g]})
    for p in parcalar:
        p["guven"] = yuv(float(np.mean(p.pop("_g"))), 2)
        p["bas"], p["son"] = yuv(p["bas"], 2), yuv(p["son"], 2)
    c["akorlar"] = parcalar
    sayim = {}
    for p in parcalar:
        if p["akor"] != "-":
            sayim[p["akor"]] = sayim.get(p["akor"], 0.0) + (p["son"] - p["bas"])
    c["akor_sureleri_sn"] = {k: yuv(v, 1) for k, v in sorted(sayim.items(), key=lambda kv: -kv[1])[:8]}
    g = [p["guven"] for p in parcalar if p["akor"] != "-"]
    c["akor_guveni_ort"] = yuv(float(np.mean(g)) if g else 0.0, 2)
    c["akor_aciklama"] = ("Akorlar yalnizca majör/minör ucsesli sablonlarla tahmin edilir (7'li vb. yok). Ortalama guven 0,75'in altindaysa "
                          "akor adlari supheli: 'akor sesi' oranlarini ona gore okuyun.")
    return c, {"kroma": C, "kroma_t": t, "akorlar": parcalar, "akort": akort, "tonlar": tonlar}


# ----------------------------------------------------------------------------------------------------------
# d) vokal perde
# ----------------------------------------------------------------------------------------------------------
def f0_izle(v, pyin_denetim=True):
    """v: vokal tek kanal SR. SwiftF0 ile perde; pYIN ile capraz denetim. Donus: t, hz, guven, bilgi."""
    from swift_f0 import SwiftF0
    v16 = librosa.resample(v, orig_sr=SR, target_sr=16000, res_type="soxr_hq")
    r = SwiftF0(threads=2).detect(v16, 16000, fmin=70, fmax=1100)
    hz = np.asarray(r.pitch_hz, float)
    guven = np.asarray(r.confidence, float)
    t = np.asarray(r.timestamps, float)
    # duzey kapisi: cok sessiz cerceveleri sesli sayma
    rr = librosa.feature.rms(y=v16, frame_length=512, hop_length=256)[0]
    rr = np.interp(t, np.arange(len(rr)) * 256 / 16000, rr)
    kapi = db(rr) > max(-55.0, np.percentile(db(rr), 95) - 32.0)
    sesli = (guven >= 0.9) & (hz > 0) & kapi
    bilgi = {"yontem": "SwiftF0 (16 ms adim)", "sesli_cerceve_orani": yuv(float(sesli.mean()), 3)}
    if pyin_denetim:
        try:
            f2, vf, _ = librosa.pyin(v, fmin=70, fmax=1100, sr=SR, frame_length=2048, hop_length=512)
            t2 = librosa.times_like(f2, sr=SR, hop_length=512)
            f2i = np.interp(t, t2, np.nan_to_num(f2, nan=0.0))
            v2i = np.interp(t, t2, vf.astype(float)) > 0.5
            ikisi = sesli & v2i & (f2i > 0)
            if ikisi.sum() > 20:
                fark = np.abs(1200 * np.log2(hz[ikisi] / f2i[ikisi]))
                bilgi["pyin_ile_uyum_yuzde_50cent"] = yuv(100 * float((fark < 50).mean()), 1)
                bilgi["pyin_sesli_ortusme"] = yuv(float(ikisi.sum() / max(1, sesli.sum())), 2)
        except Exception as e:
            bilgi["pyin_hata"] = str(e)[:100]
    return t, hz, guven, sesli, bilgi


def notalara_bol(t, midi, sesli, esik=0.6, min_sure=0.09):
    """Perde egrisini notalara boler. Her nota icin: sure, medyan perde, cent sapmasi, nota ici oynaklik, egim, vibrato."""
    n = len(t)
    dt = float(np.median(np.diff(t))) if n > 1 else 0.016
    gruplar, cur = [], []
    for i in range(n):
        if not sesli[i]:
            if cur:
                gruplar.append(cur)
                cur = []
            continue
        if not cur:
            cur = [i]
            continue
        if t[i] - t[cur[-1]] > 2.5 * dt:
            gruplar.append(cur)
            cur = [i]
            continue
        med = np.median(midi[cur[-12:]])
        if abs(midi[i] - med) > esik:
            ileri = [j for j in range(i, min(n, i + 4)) if sesli[j]]
            if len(ileri) >= 3 and abs(np.median(midi[ileri]) - med) > esik:
                gruplar.append(cur)
                cur = [i]
                continue
        cur.append(i)
    if cur:
        gruplar.append(cur)
    notalar = []
    for g in gruplar:
        g = np.array(g)
        if len(g) * dt < min_sure:
            continue
        med = float(np.median(midi[g]))
        cek = g[np.abs(midi[g] - med) < 0.5]                # cekirdek: gecis cerceveleri atilir
        if len(cek) * dt < min_sure * 0.7:
            continue
        med = float(np.median(midi[cek]))
        tt, mm = t[cek], midi[cek]
        if len(cek) >= 4:
            egim, kesim = np.polyfit(tt - tt[0], mm, 1)
            art = mm - (egim * (tt - tt[0]) + kesim)
        else:
            egim, art = 0.0, mm - med
        nota = {"bas": float(t[g[0]]), "son": float(t[g[-1]] + dt), "sure": float(len(g) * dt), "midi": med,
                "ad": nota_adi(med), "cent": float((med - round(med)) * 100), "ic_std_cent": float(np.std(art) * 100),
                "egim_cent_sn": float(egim * 100), "cekirdek": cek}
        # giris kaymasi: ilk 60 ms'nin nota medyanina uzakligi
        ilk = g[:max(1, int(0.06 / dt))]
        nota["giris_cent"] = float((np.median(midi[ilk]) - med) * 100)
        # vibrato: 4-8 Hz
        nota["vibrato"] = None
        if len(cek) * dt >= 0.35 and len(cek) >= 16:
            x = art - art.mean()
            X = np.abs(np.fft.rfft(x * np.hanning(len(x)), 256))
            f = np.fft.rfftfreq(256, dt)
            bant = (f >= 4.0) & (f <= 8.0)
            if X[1:].sum() > 0 and bant.any():
                k = np.argmax(np.where(bant, X, 0))
                genlik = 4 * X[k] / len(x) * 100                 # yaklasik tepe genligi (cent)
                pay = float((X[bant] ** 2).sum() / ((X[1:] ** 2).sum() + 1e-12))
                nota["vibrato"] = {"hz": float(f[k]), "genlik_cent": float(genlik), "pay": pay, "var": bool(genlik >= 12 and pay >= 0.45)}
        notalar.append(nota)
    return notalar


def perde_ozeti(t, midi, sesli, notalar):
    c = {}
    if not len(notalar):
        return {"nota_sayisi": 0, "not": "vokalde olculebilir nota bulunamadi"}
    dt = float(np.median(np.diff(t)))
    sure = np.array([n["sure"] for n in notalar])
    med = np.array([n["midi"] for n in notalar])
    cek = np.concatenate([n["cekirdek"] for n in notalar])
    c["nota_sayisi"] = len(notalar)
    c["nota_suresi_medyan_sn"] = yuv(float(np.median(sure)), 2)
    c["ses_araligi"] = {"alt": nota_adi(np.percentile(midi[cek], 3)), "ust": nota_adi(np.percentile(midi[cek], 97)),
                        "yarim_ses": yuv(float(np.percentile(midi[cek], 97) - np.percentile(midi[cek], 3)), 1),
                        "medyan": nota_adi(np.median(midi[cek])), "medyan_hz": yuv(440 * 2 ** ((np.median(midi[cek]) - 69) / 12), 0)}
    uz = [n for n in notalar if n["sure"] >= 0.2]
    if uz:
        st = np.array([n["ic_std_cent"] for n in uz])
        c["nota_ici_oynaklik_cent_medyan"] = yuv(float(np.median(st)), 1)
        c["nota_ici_oynaklik_aciklama"] = ("0,2 sn'den uzun notalarda perdenin nota icindeki standart sapmasi. Insan sesinde genelde "
                                           "8-35 cent; 5 cent'in altindaysa perde 'cetvelle cizilmis' gibi duzdur.")
        c["cok_duz_nota_orani"] = yuv(float((st < 5).mean()), 2)
        c["kayan_nota_orani"] = yuv(float(np.mean([abs(n["egim_cent_sn"]) > 120 for n in uz])), 2)
    vb = [n for n in notalar if n["vibrato"]]
    if vb:
        c["uzun_nota_sayisi_035sn_ustu"] = len(vb)
        c["vibratolu_uzun_nota_orani"] = yuv(float(np.mean([n["vibrato"]["var"] for n in vb])), 2)
        var = [n["vibrato"] for n in vb if n["vibrato"]["var"]]
        if var:
            c["vibrato_hz_medyan"] = yuv(float(np.median([v["hz"] for v in var])), 1)
            c["vibrato_genlik_cent_medyan"] = yuv(float(np.median([v["genlik_cent"] for v in var])), 0)
    c["alttan_giris_orani"] = yuv(float(np.mean([n["giris_cent"] < -60 for n in notalar])), 2)
    c["gecis_cerceve_orani"] = yuv(float(1 - len(cek) / max(1, sesli.sum())), 2)
    # ses sinifi dagilimi (sure agirlikli, cekirdek cerceveler)
    pc = np.mod(np.round(midi[cek]).astype(int), 12)
    pch = np.bincount(pc, minlength=12).astype(float)
    c["ses_sinifi_dagilimi"] = {ADLAR[k]: yuv(pch[k] / pch.sum(), 3) for k in range(12)}
    ks = ks_ton(pch)
    if ks:
        c["vokal_ton_ks"] = {"ton": ton_adi_tr(ks[0], ks[1]), "tonik": int(ks[0]), "mod": ks[1], "r": yuv(ks[2], 3), "ikinci_r": yuv(ks[3], 3),
                             "adaylar": [ton_adi_tr(k, m) + " r=%.2f" % r for r, k, m in ks[4]]}
    return c, pch


def vokal_uyum(t, midi, sesli, notalar, altyapi, akor_egri):
    """Vokal altyapiyla uyumlu mu? altyapi: akor_ve_ton() sozlugu. midi: altyapinin akort izgarasina gore duzeltilmis."""
    c = {}
    tonlar = akor_egri.get("tonlar") or []
    if not notalar or not tonlar:
        return {"not": "uyum olculemedi (nota ya da altyapi tonu yok)"}, {}
    tb = np.array([x["bas"] for x in tonlar])
    gamlar = [gam(x["tonik"], x["mod"]) for x in tonlar]

    def gam_i(zaman):
        return np.clip(np.searchsorted(tb, zaman, side="right") - 1, 0, len(tonlar) - 1)
    cek = np.concatenate([n["cekirdek"] for n in notalar])
    tc = t[cek]
    pc = np.mod(np.round(midi[cek]).astype(int), 12)
    sap = (midi[cek] - np.round(midi[cek])) * 100
    c["cent_sapma_medyan_mutlak"] = yuv(float(np.median(np.abs(sap))), 1)
    c["cent_sapma_ortalama_isaretli"] = yuv(float(np.mean(sap)), 1)
    c["yuzde_25cent_icinde"] = yuv(100 * float((np.abs(sap) < 25).mean()), 1)
    # vokalin kendi akort merkezi (dairesel ortalama) ve yogunlasmasi
    z = np.exp(2j * np.pi * sap / 100.0).mean()
    c["vokal_akort_kaymasi_cent"] = yuv(float(np.angle(z) / (2 * np.pi) * 100), 1)
    c["perde_izgaraya_yapisma_R"] = yuv(float(np.abs(z)), 2)
    c["izgara_aciklama"] = ("R: sarki perdelerinin yarim ses izgarasina ne kadar siki toplandigi (0-1). Cok yuksek (>0,9) + cok duz notalar "
                            "= sert otomatik akort / sentez izlenimi. Dusuk (<0,4) = perdeler izgaraya oturmuyor (detone).")
    gi = gam_i(tc)
    gam_ici = np.array([pc[i] in gamlar[gi[i]] for i in range(len(cek))])
    c["gam_ici_sure_orani"] = yuv(float(gam_ici.mean()), 3)
    c["gam_guvenilir_mi"] = not any(x["belirsiz"] for x in tonlar)
    # etiketsiz ton kaydirma denemesi: vokali k yarim ses kaydirsak altyapinin kromasina daha mi iyi oturur?
    C = akor_egri["kroma"]
    Cn = C / (C.max(axis=0, keepdims=True) + 1e-9)
    ci = np.clip((tc * SR / HOP).astype(int), 0, C.shape[1] - 1)
    des = {k: float(Cn[(pc + k) % 12, ci].mean()) for k in range(-6, 6)}
    sirali = sorted(des, key=lambda k: -des[k])
    c["armonik_destek"] = {"gercek": yuv(des[0], 3), "yarim_ses_yukari": yuv(des[1], 3), "yarim_ses_asagi": yuv(des[-1], 3),
                           "fark": yuv(des[0] - (des[1] + des[-1]) / 2, 3),
                           "aciklama": "Vokalin soyledigi ses sinifinda altyapinin ne kadar enerjisi var; ayni olcu vokal yarim ses kaydirilmis "
                                       "gibi yeniden hesaplanir. Fark belirgin arti ise (>+0,05) vokal altyapiyla ayni armonide; sifir/eksi ise "
                                       "'iki ayri sarki ust uste' riski. Ton etiketi gerektirmez."}
    c["ton_kaydirma_denemesi"] = {"destek_kaydirmaya_gore": {("%+d" % k): yuv(des[k], 3) for k in range(-6, 6)},
                                  "en_iyi_kaydirma_yarim_ses": int(sirali[0]), "sifir_kacinci": int(sirali.index(0) + 1),
                                  "aciklama": "Vokal -6..+5 yarim ses kaydirilmis gibi armonik destek. En iyi deger 0 kaydirmada olmali. "
                                              "+5/-5/+7 (dortlu/besli) komsu tonlar oldugu icin 0'a yakin cikabilir; +-1, +-2 ya da +-6 en iyiyse "
                                              "vokal baska tonda soyluyor olabilir."}
    # akor sesleri
    akorlar = akor_egri["akorlar"]
    bas = np.array([a["bas"] for a in akorlar])
    ai = np.clip(np.searchsorted(bas, tc, side="right") - 1, 0, len(akorlar) - 1)
    sinif = np.zeros(len(cek), int)                       # 0 akor sesi, 1 gam ici (akor disi), 2 gam disi
    for i in range(len(cek)):
        ak = akorlar[ai[i]]
        if ak["akor"] != "-" and pc[i] in ak["sesler"]:
            sinif[i] = 0
        elif gam_ici[i]:
            sinif[i] = 1
        else:
            sinif[i] = 2
    c["akor_sesi_sure_orani"] = yuv(float((sinif == 0).mean()), 3)
    c["gam_ici_akor_disi_orani"] = yuv(float((sinif == 1).mean()), 3)
    c["gam_disi_orani"] = yuv(float((sinif == 2).mean()), 3)
    # cakisan uzun notalar
    cak = []
    for n in notalar:
        if n["sure"] < 0.3:
            continue
        p = int(round(n["midi"])) % 12
        orta = (n["bas"] + n["son"]) / 2
        ak = akorlar[int(np.clip(np.searchsorted(bas, orta, side="right") - 1, 0, len(akorlar) - 1))]
        olcek = gamlar[int(gam_i(orta))]
        tur = None
        if p not in olcek and not (ak["akor"] != "-" and p in ak["sesler"]):
            tur = "gam disi"
        elif ak["akor"] != "-" and p not in ak["sesler"] and n["sure"] >= 0.45 and any(((p - s_) % 12) in (1, 11) for s_ in ak["sesler"]):
            tur = "akor sesine yarim ses komsu"
        if abs(n["cent"]) > 35 and n["sure"] >= 0.4:
            tur = (tur + " + " if tur else "") + "%+.0f cent detone" % n["cent"]
        if tur:
            cak.append({"bas": yuv(n["bas"], 2), "sure": yuv(n["sure"], 2), "nota": n["ad"], "akor": ak["akor"], "tur": tur})
    c["cakisan_uzun_notalar"] = cak[:40]
    c["cakisan_uzun_nota_sayisi"] = len(cak)
    c["uzun_nota_sayisi_03sn_ustu"] = int(sum(n["sure"] >= 0.3 for n in notalar))
    return c, {"cek": cek, "sinif": sinif, "sap": sap}


# ----------------------------------------------------------------------------------------------------------
# f) ritim
# ----------------------------------------------------------------------------------------------------------
RITIM_HOP = 256          # 11,6 ms
VURUS_GECIKMESI = 0.040  # sn. librosa vurus izleyicisi vurusu gercek yerinden ~40 ms SONRA isaretliyor (dogrula.py: vuruslari bilinen
                         # altyapida 36-49 ms olculdu). Otomatik izgara bu kadar geri cekilir. Malzemeye gore +-20 ms oynayabilir.


def ince_vurus_egri(y):
    return librosa.onset.onset_strength(y=y, sr=SR, hop_length=RITIM_HOP, n_mels=96, fmax=8000)


def ince_vurus_izgarasi(y, bpm=None, ilk_vurus=None):
    """Altyapidan vurus izgarasi (11,6 ms adim). Vokal baslangiclari ayni yontemle bulundugu icin algilama gecikmeleri birbirini goturur."""
    if bpm and ilk_vurus is not None:
        return float(bpm), np.arange(ilk_vurus, len(y) / SR, 60.0 / bpm), "verilen tempo ve ilk vuruş"
    o = ince_vurus_egri(y)
    try:
        tempo, kare = librosa.beat.beat_track(onset_envelope=o, sr=SR, hop_length=RITIM_HOP, bpm=bpm, tightness=100, trim=False)
        v = librosa.frames_to_time(kare, sr=SR, hop_length=RITIM_HOP) - VURUS_GECIKMESI
        tempo = float(np.atleast_1d(tempo)[0])
        if len(v) > 8 and not bpm:
            tempo = 60.0 / ((v[-1] - v[0]) / (len(v) - 1))
        return tempo, v, "otomatik (altyapıdan)" if not bpm else "verilen tempo, otomatik faz"
    except Exception:
        return 0.0, np.array([]), "bulunamadi"


def vokal_baslangiclari(v, aktif_t=None, aktif=None):
    """Vokalde hece/nota baslangiclari (spektral aki tepeleri), 11,6 ms adimla."""
    o = ince_vurus_egri(v)
    on = librosa.onset.onset_detect(onset_envelope=o, sr=SR, hop_length=RITIM_HOP, units="time", backtrack=False, delta=0.12, wait=4)
    if aktif_t is not None and aktif is not None and len(on):
        on = on[np.interp(on, aktif_t, aktif.astype(float)) > 0.5]
    return on, o


def ritim(baslangic, vurus, tempo):
    """Vokal baslangiclarinin vurus izgarasina (sekizlik ve onaltilik) uzakligi."""
    c = {}
    baslangic = np.asarray(baslangic, float)
    vurus = np.asarray(vurus, float)
    if len(baslangic) < 8 or len(vurus) < 8:
        return {"not": "ritim olculemedi (yeterli vurus ya da vokal baslangici yok)"}, {}
    m = (baslangic > vurus[0]) & (baslangic < vurus[-1])
    b = baslangic[m]
    if len(b) < 8:
        return {"not": "ritim olculemedi (vokal baslangiclari vurus izgarasinin disinda)"}, {}
    k = np.clip(np.searchsorted(vurus, b, side="right") - 1, 0, len(vurus) - 2)
    ibi = vurus[k + 1] - vurus[k]
    faz = (b - vurus[k]) / ibi                                 # 0..1 vurus ici konum
    c["vokal_baslangic_sayisi"] = int(len(b))
    c["vurus_araligi_ms"] = yuv(float(np.median(ibi) * 1000), 0)
    sap_egri = None
    for ad, bolme in (("sekizlik", 2), ("onaltilik", 4)):
        x = faz * bolme
        sap = (x - np.round(x)) / bolme * ibi * 1000           # ms; + = gec, - = erken
        z = np.exp(2j * np.pi * (faz * bolme)).mean()
        ort_kayma = float(np.angle(z) / (2 * np.pi) / bolme * np.median(ibi) * 1000)
        kalan = sap - ort_kayma
        c[ad] = {"ortalama_kayma_ms": yuv(ort_kayma, 0), "sikilik_R": yuv(float(np.abs(z)), 2),
                 "medyan_mutlak_sapma_ms": yuv(float(np.median(np.abs(sap))), 0),
                 "kayma_duzeltilmis_medyan_ms": yuv(float(np.median(np.abs(kalan))), 0),
                 "yuzde_40ms_icinde": yuv(100 * float((np.abs(sap) < 40).mean()), 0)}
        if bolme == 2:
            sap_egri = sap
    R = c["sekizlik"]["sikilik_R"]
    rast = 1.0 / math.sqrt(len(b))
    c["rastgele_beklenen_R"] = yuv(rast, 2)
    c["kalibrasyon"] = ("dogrula.py denetimleri: notalari tam vurusta yapay sarkici R=0,65 (olcumun tavani), +-90 ms rastgele kaydirilmis "
                        "ayni sarkici R=0,15; 70 ms gec soyleyen: R ayni, ortalama kayma +75 ms.")
    c["yorum"] = ("Vokal başlangıçları sekizlik ızgaraya sıkı oturuyor" if R >= 0.55 else
                  "Vokal ızgaraya orta derecede oturuyor (serbest / konuşur gibi söyleyiş ya da ölçüm gürültüsü)" if R >= 0.3 else
                  "Vokal başlangıçları ızgarayla ilişkisiz görünüyor (ritme oturmuyor YA DA vuruş ızgarası yanlış bulundu)")
    c["aciklama"] = ("R: 0-1; baslangiclarin vurus icindeki konumlarinin ne kadar ayni yerde toplandigi. 'ortalama_kayma' sabit bir erken/gec "
                     "soylemeyi gosterir (+ gec). Vurus izgarasi otomatik bulunduysa 20-30 ms'lik sabit kayma olcum hatasi olabilir; "
                     "gercek tempo --bpm ile verilirse daha guvenilir olur.")
    return c, {"b": b, "sap_ms": sap_egri}


# ----------------------------------------------------------------------------------------------------------
# e) yapaylik icin sinyal vekilleri
# ----------------------------------------------------------------------------------------------------------
def yapaylik(v, t, midi, sesli, notalar, uyum=None, perde=None):
    """Vokalde vokoder / otomatik akort / zaman esnetme izleri icin VEKIL olcumler. Hicbiri tek basina kanit degildir."""
    c = {"uyari": "Bunlar vekil (dolayli) olcumlerdir: 'yapay duyuluyor' yargisinin yerini tutmaz; iki surumu KARSILASTIRMAK icindir."}
    isaret = []
    dt = float(np.median(np.diff(t))) if len(t) > 1 else 0.016
    uz = [n for n in notalar if n["sure"] >= 0.2]
    # 1) nota ici duzluk
    if uz:
        st = np.array([n["ic_std_cent"] for n in uz])
        c["nota_ici_oynaklik_cent_medyan"] = yuv(float(np.median(st)), 1)
        c["cok_duz_nota_orani"] = yuv(float((st < 5).mean()), 2)
        if np.median(st) < 6:
            isaret.append("notaların içi çok düz (medyan %.1f cent): sert akort düzeltme / vokoderle sabitlenmiş perde izlenimi" % np.median(st))
    # 2) basamakli (nicemlenmis) perde gecisleri: komsu notalar arasi gecis suresi
    gecis = []
    for a, b in zip(notalar[:-1], notalar[1:]):
        if b["bas"] - a["son"] < 0.03 and abs(b["midi"] - a["midi"]) >= 0.9:
            ca, cb = a["cekirdek"], b["cekirdek"]
            gecis.append(max(0.0, t[cb[0]] - t[ca[-1]]))
    if len(gecis) >= 5:
        g = np.array(gecis) * 1000
        c["bagli_gecis_sayisi"] = len(g)
        c["bagli_gecis_suresi_ms_medyan"] = yuv(float(np.median(g)), 0)
        c["ani_gecis_orani_35ms_alti"] = yuv(float((g < 35).mean()), 2)
        if np.median(g) <= 20:      # dogrula.py: gercek vokalde 32 ms, yarim seslere yapistirilmis vokalde 16 ms olculdu (olcum adimi 16 ms)
            isaret.append("bağlı notalar arası geçişler ani (%d ms medyan; aynı ölçümle doğal vokalde ~32 ms): basamaklı perde" % np.median(g))
    if uyum and uyum.get("perde_izgaraya_yapisma_R") is not None:
        c["perde_izgaraya_yapisma_R"] = uyum["perde_izgaraya_yapisma_R"]
        if uyum["perde_izgaraya_yapisma_R"] > 0.9 and uz and np.median([n["ic_std_cent"] for n in uz]) < 8:
            isaret.append("perdeler yarım ses ızgarasına aşırı sıkı yapışmış (R=%.2f): nicemlenmiş (cetvelle çizilmiş) perde" % uyum["perde_izgaraya_yapisma_R"])
    # 3) vibrato
    vb = [n for n in notalar if n["vibrato"]]
    if len(vb) >= 4:
        oran = float(np.mean([n["vibrato"]["var"] for n in vb]))
        c["vibratolu_uzun_nota_orani"] = yuv(oran, 2)
        var = [n["vibrato"] for n in vb if n["vibrato"]["var"]]
        if var:
            hz = np.array([x["hz"] for x in var])
            gn = np.array([x["genlik_cent"] for x in var])
            c["vibrato_hiz_yayilimi_hz"] = yuv(float(np.std(hz)), 2)
            if len(var) >= 4 and np.std(hz) < 0.15 and np.std(gn) < 3:
                isaret.append("vibrato her notada aynı hız ve genişlikte (%.1f Hz): makineyle eklenmiş titreşim izlenimi" % np.median(hz))
    # spektral olcumler
    hop = 256
    D = np.abs(librosa.stft(v, n_fft=1024, hop_length=hop))
    frek = librosa.fft_frequencies(sr=SR, n_fft=1024)
    tt = librosa.times_like(D, sr=SR, hop_length=hop)
    ses_i = np.interp(tt, t, sesli.astype(float)) > 0.5
    r = D.sum(axis=0)
    akt = db(np.sqrt((D ** 2).mean(axis=0))) > max(-60.0, np.percentile(db(np.sqrt((D ** 2).mean(axis=0))), 95) - 35.0)
    # 4) donmus (asiri duragan) unluler: ardisik spektrum cerceveleri neredeyse ayni
    lm = np.log(librosa.feature.melspectrogram(S=D ** 2, sr=SR, n_mels=48, fmin=100, fmax=8000) + 1e-9)
    lm = lm - lm.mean(axis=0, keepdims=True)
    nrm = np.linalg.norm(lm, axis=0) + 1e-9
    benz = (lm[:, 1:] * lm[:, :-1]).sum(axis=0) / (nrm[1:] * nrm[:-1])
    benz = np.concatenate([[0], benz])
    duragan = (benz > 0.985) & ses_i & akt
    ks = [(a, b) for a, b in kosular(duragan) if (b - a) * hop / SR >= 0.45]
    c["donmus_unlu_sayisi_045sn_ustu"] = len(ks)
    c["donmus_unluler"] = [{"bas": yuv(tt[a], 2), "sure": yuv((b - a) * hop / SR, 2)} for a, b in ks[:15]]
    if ses_i.sum() > 10:
        c["sesli_cercevelerde_ardisik_benzerlik_medyan"] = yuv(float(np.median(benz[ses_i & akt])) if (ses_i & akt).any() else None, 4)
        c["donmus_sure_orani"] = yuv(float(sum(b - a for a, b in ks) / max(1, (ses_i & akt).sum())), 3)
        if c["donmus_sure_orani"] and c["donmus_sure_orani"] > 0.10:
            isaret.append("sesli sürenin %%%d kadarı 'donmuş' ünlü (spektrum 0,45 sn'den uzun süre hiç değişmiyor): zaman esnetme / vokoderle uzatma izlenimi"
                          % (100 * c["donmus_sure_orani"]))
    # 5) unsuz (tiz) enerjisi: sessiz unsuz cercevelerinde 4 kHz ustu
    tiz = (D[frek >= 4000] ** 2).sum(axis=0)
    tum = (D ** 2).sum(axis=0) + 1e-12
    unsuz = akt & ~ses_i
    if unsuz.sum() > 10 and ses_i.sum() > 10:
        c["unsuz_cerceve_orani"] = yuv(float(unsuz.sum() / max(1, akt.sum())), 2)
        c["unsuzlerde_tiz_payi_db"] = yuv(float(10 * np.log10(tiz[unsuz].sum() / tum[unsuz].sum() + 1e-12)), 1)
        c["unlulerde_tiz_payi_db"] = yuv(float(10 * np.log10(tiz[ses_i & akt].sum() / tum[ses_i & akt].sum() + 1e-12)), 1)
        if c["unsuzlerde_tiz_payi_db"] < -14:
            isaret.append("ünsüzlerde (s, ş, ç, t, k) tiz enerji zayıf (%.0f dB): boğuk / 'ağzı kapalı' söyleyiş izlenimi" % c["unsuzlerde_tiz_payi_db"])
    P = (D ** 2).mean(axis=1)
    Pd = 10 * np.log10(P / (P.max() + 1e-30) + 1e-30)
    Pd = ndi.uniform_filter1d(Pd, 7)
    ust = frek[np.where(Pd > -60)[0][-1]] if (Pd > -60).any() else 0
    c["vokal_ust_frekans_hz"] = int(ust)
    if ust < 7000:
        isaret.append("vokalin enerjisi %d Hz'de bitiyor: bant sınırlı (telefon / düşük kaliteli sentez) tını" % ust)
    # 6) tiz doku titresimi: tutulan unlulerde 4-8 kHz bandinin zaman icindeki degisim katsayisi
    bant = (frek >= 4000) & (frek <= 8000)
    if (ses_i & akt).sum() > 40:
        B = D[bant][:, ses_i & akt]
        dk = float(np.median(B.std(axis=1) / (B.mean(axis=1) + 1e-12)))
        c["tiz_doku_degisim_katsayisi"] = yuv(dk, 2)
        c["tiz_doku_aciklama"] = ("Tutulan unlulerde 4-8 kHz'in zaman icinde ne kadar oynadigi. Duragan gurultu icin kuramsal deger ~0,52. "
                                  "Belirgin dusuk (<0,35) = fazla puruzsuz/'vizildayan' sentez dokusu; belirgin yuksek (>1,2) = "
                                  "kopuk kopuk 'muzikal gurultu' (ayirma ya da gurultu giderme artigi) olabilir.")
    # 7) zarf titremesi (15-60 Hz): zaman esnetme / cerceve tekrari izleri
    zarf = np.sqrt((D ** 2).sum(axis=0))
    fs_z = SR / hop
    ks2 = [(a, b) for a, b in kosular(ses_i & akt) if (b - a) >= int(0.3 * fs_z)]
    oranlar = []
    for a, b in ks2[:200]:
        z = zarf[a:b]
        z = z / (z.mean() + 1e-12) - 1.0
        Z = np.abs(np.fft.rfft(z * np.hanning(len(z)), 512)) ** 2
        f = np.fft.rfftfreq(512, 1 / fs_z)
        ust_b, alt_b = Z[(f >= 15) & (f <= 40)].sum(), Z[(f >= 1) & (f < 15)].sum()
        oranlar.append(10 * np.log10((ust_b + 1e-12) / (alt_b + 1e-12)))
    if oranlar:
        c["zarf_titremesi_db"] = yuv(float(np.median(oranlar)), 1)
        c["zarf_titremesi_aciklama"] = ("Tutulan seslerde 15-40 Hz genlik titresiminin 1-15 Hz'e orani (dB). dogrula.py'de: ayrilmis dogal vokal -9..-11, "
                                        "esnetilmis vokal -14, konusma sentezi -16, vokoderle ezgiye oturtulmus (reddedilen) vokal -21. Yani COK DUSUK deger "
                                        "asiri puruzsuz/duragan ses demek olabilir; tek basina karar verdirmez.")
    c["isaretler"] = isaret
    c["isaret_sayisi"] = len(isaret)
    c["neyi_yakalar"] = ("dogrula.py denetimlerinde YAKALANAN: perdesi yarim seslere yapistirilmis vokal (duzluk + izgaraya yapisma), 4 kHz'de kesilmis "
                         "vokal (tiz eksigi), hecelerı vokoderle uzatilmis vokal (donmus unlu). YAKALANMAYAN: perdesi degistirilmeden vokoderden "
                         "gecirilmis vokal, 1,6-1,8 kat esnetilmis vokal, konusma sentezi. 'Isaret yok' = 'dogal' DEGILDIR.")
    return c
