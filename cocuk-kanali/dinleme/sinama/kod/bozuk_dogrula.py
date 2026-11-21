#!/usr/bin/env python3
"""bozuk_dogrula.py - uretilen bozuk surumlerde kusurun GERCEKTEN var oldugunu, dinleme aracindan BAGIMSIZ basit olcumlerle dogrular.
(Arac bir kusuru kacirirsa, "kusur zaten yoktu" denemesin diye.)  Cikti: dinleme/sinama/bozuk_dogrulama.json"""
import os, sys, json, subprocess, warnings
warnings.filterwarnings("ignore")
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_k, "2")
import numpy as np
import soundfile as sf
import scipy.signal as ss

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
import bozuk_uret as b

SR = 44100


def coz(yol):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", yol, "-ar", str(SR), "-ac", "2", "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(float)


def db(x):
    return float(10 * np.log10(np.mean(np.asarray(x) ** 2) + 1e-20))


def f0_medyan_cent_farki(v1, v2, t0=6.0, t1=27.0):
    import librosa
    a, c = v1[int(t0 * SR):int(t1 * SR)].mean(axis=1), v2[int(t0 * SR):int(t1 * SR)].mean(axis=1)
    a, c = librosa.resample(a, orig_sr=SR, target_sr=16000), librosa.resample(c, orig_sr=SR, target_sr=16000)
    fa, va, _ = librosa.pyin(a, fmin=150, fmax=600, sr=16000, frame_length=1024, hop_length=160)
    fc, vc, _ = librosa.pyin(c, fmin=150, fmax=600, sr=16000, frame_length=1024, hop_length=160)
    ok = va & vc & np.isfinite(fa) & np.isfinite(fc)
    d = 1200 * np.log2(fc[ok] / fa[ok])
    d = d[np.abs(d) < 300]
    return round(float(np.median(d)), 1), int(ok.sum()), fa, fc, ok


def main():
    S, W = b.satirlar()
    K = os.path.join(b.CIKTI, "kanal")
    V0, _ = sf.read(os.path.join(K, "n3_yeniden_karisim_vokal.wav"), always_2d=True)
    M0 = coz(os.path.join(b.CIKTI, "n3_yeniden_karisim.mp3"))
    asil = coz(b.ASIL)
    n = min(len(M0), len(asil))
    R = {"_aciklama": "Her kusurun varligi, dinleme aracindan bagimsiz olcumle. 'taban' = n3_yeniden_karisim."}
    R["n3_yeniden_karisim"] = {"asil_dosyadan_fark_db": round(db(M0[:n] - asil[:n]) - db(asil[:n]), 1), "yorum": "yeniden karisim asil dosyanin aynisi sayilir (fark gurultu duzeyinde)"}
    # 1) detone
    v, _ = sf.read(os.path.join(K, "b01a_detone_50c_vokal.wav"), always_2d=True)
    c, m, *_ = f0_medyan_cent_farki(V0, v)
    R["b01a_detone_50c"] = {"vokal_perde_farki_cent_medyan": c, "karsilastirilan_cerceve": m, "beklenen": 50}
    # 2) gecikme
    for ad, bek in (("b02a_gec_ceyrek", 129.4), ("b02b_gec_yarim", 258.8)):
        v, _ = sf.read(os.path.join(K, ad + "_vokal.wav"), always_2d=True)
        g = b.gecikme_bul(V0, v, en_cok=0.4)
        R[ad] = {"vokal_gecikmesi_ms": round(1000 * g / SR, 1), "beklenen": bek}
    # 3) esnetme (gidis-donus): sure ayni, perde ayni, ama dalga bicimi farkli; baslangic keskinligi azalir
    v, _ = sf.read(os.path.join(K, "b03b_esnetme_20_vokal.wav"), always_2d=True)
    c, m, *_ = f0_medyan_cent_farki(V0, v)

    def keskinlik(x):
        e = b.zarf(x, hop=256)
        d = np.diff(np.log(e + 1e-4))
        return float(np.percentile(d, 99))
    R["b03b_esnetme_20"] = {"vokal_perde_farki_cent_medyan": c, "gecikme_ms": round(1000 * b.gecikme_bul(V0, v) / SR, 1),
                            "fark_sinyali_db_vokale_gore": round(db(v - V0) - db(V0), 1),
                            "baslangic_keskinligi_p99_taban": round(keskinlik(V0), 3), "baslangic_keskinligi_p99_bozuk": round(keskinlik(v), 3),
                            "yorum": "perde ve zamanlama ayni; dalga bicimi tumuyle degismis (fark sinyali vokal kadar guclu), ani baslangiclar yumusamis"}
    # 4) duz perde
    for ad in ("b04k_world_kontrol", "b04_duz_perde"):
        v, _ = sf.read(os.path.join(K, ad + "_vokal.wav"), always_2d=True)
        c, m, fa, fc, ok = f0_medyan_cent_farki(V0, v)

        def yerel_oynaklik(x16):
            """WORLD (dio+stonemask, 5 ms) perdesinin 80 ms'lik pencerelerdeki standart sapmasinin medyani (cent): nota ici oynaklik."""
            import pyworld as pw
            f, t = pw.dio(x16.astype(np.float64), 16000, f0_floor=150, f0_ceil=600, frame_period=5.0)
            f = pw.stonemask(x16.astype(np.float64), f, t, 16000)
            mc = np.where(f > 0, 1200 * np.log2(np.maximum(f, 1e-6) / 440.0), np.nan)
            st = [np.std(mc[i:i + 16]) for i in range(0, len(mc) - 16, 8) if np.isfinite(mc[i:i + 16]).all()]
            return round(float(np.median(st)), 1), len(st)
        import librosa
        seg = lambda x: librosa.resample(x[int(6 * SR):int(55 * SR)].mean(axis=1), orig_sr=SR, target_sr=16000)
        o1, n1 = yerel_oynaklik(seg(v))
        o0, n0 = yerel_oynaklik(seg(V0))
        R[ad] = {"vokal_perde_farki_cent_medyan": c, "80ms_pencerede_perde_oynakligi_cent_medyan": o1, "ayni_olcum_tabanda": o0, "pencere_sayisi": n1,
                 "fark_sinyali_db_vokale_gore": round(db(v - V0) - db(V0), 1)}
    # 5) tik
    M = coz(os.path.join(b.CIKTI, "b05_tik.mp3"))
    d = np.abs((M - M0[:len(M)]).mean(axis=1))
    tepe, _ = ss.find_peaks(d, height=0.2, distance=SR)
    R["b05_tik"] = {"bulunan_tik_sayisi": int(len(tepe)), "ilk_zamanlar_sn": [round(float(x) / SR, 2) for x in tepe[:5]], "tik_tepe_genligi_medyan": round(float(np.median(d[tepe])), 2),
                    "karisimin_tepe_genligi": round(float(np.abs(M0).max()), 2), "beklenen": "36 tik, 2,37 sn'den baslayarak 3 sn arayla"}
    # 5b) kisik tik + her iki tik icin "duyulurluk" olcusu: tik aninda 6-16 kHz bandinda, ayni andaki muzige gore kac dB fazlalik var
    sos = ss.butter(6, [6000 / (SR / 2), 16000 / (SR / 2)], btype="band", output="sos")
    zamanlar = json.load(open(os.path.join(b.SINAMA, "bozuklar.json"), encoding="utf8"))["b05_tik"]["tik_zamanlari"]

    def tiz_fazlalik(M):
        hm, h0 = ss.sosfilt(sos, M.mean(axis=1)), ss.sosfilt(sos, M0[:len(M)].mean(axis=1))
        f = []
        for t in zamanlar:
            i = int(t * SR)
            f.append(db(hm[i - 110:i + 330]) - db(h0[i - 110:i + 330]))            # 10 ms pencere
        return round(float(np.median(f)), 1), round(float(np.min(f)), 1)
    med, enaz = tiz_fazlalik(coz(os.path.join(b.CIKTI, "b05_tik.mp3")))
    R["b05_tik"].update({"tik_aninda_6_16khz_fazlalik_db_medyan": med, "en_az": enaz})
    if os.path.exists(os.path.join(b.CIKTI, "b05b_tik_kisik.mp3")):
        M = coz(os.path.join(b.CIKTI, "b05b_tik_kisik.mp3"))
        d = np.abs((M - M0[:len(M)]).mean(axis=1))
        tepe, _ = ss.find_peaks(d, height=0.07, distance=SR)
        med, enaz = tiz_fazlalik(M)
        R["b05b_tik_kisik"] = {"bulunan_tik_sayisi": int(len(tepe)), "tik_tepe_genligi_medyan": round(float(np.median(d[tepe])), 2),
                               "tik_aninda_6_16khz_fazlalik_db_medyan": med, "en_az": enaz,
                               "yorum": "tik aninda tiz bantta muzigin 10 dB'den fazla ustune cikan bir patlama, kulaklikta 'cit' diye duyulur"}
    # 6) duzey
    v, _ = sf.read(os.path.join(K, "b06a_vokal_eksi6_vokal.wav"), always_2d=True)
    R["b06a_vokal_eksi6"] = {"vokal_duzey_farki_db": round(db(v) - db(V0), 2), "beklenen": -6.0}
    M = coz(os.path.join(b.CIKTI, "b06b_vokal_arti6.mp3"))
    R["b06b_vokal_arti6"] = {"karisim_duzey_farki_db": round(db(M) - db(M0), 2), "karisim_tepe_genligi": round(float(np.abs(M).max()), 2), "taban_tepe_genligi": round(float(np.abs(M0).max()), 2)}
    # 7) satir sonu
    v, _ = sf.read(os.path.join(K, "b07_satir_sonu_kesik_vokal.wav"), always_2d=True)
    fark = []
    for satir in S:
        e = satir[-1]["end"]
        i0, i1 = int((e - 0.15) * SR), int((e + 0.10) * SR)
        fark.append(db(v[i0:i1]) - db(V0[i0:i1]))
    R["b07_satir_sonu_kesik"] = {"satir_sayisi": len(S), "son_150ms_ve_kuyrukta_duzey_farki_db_medyan": round(float(np.median(fark)), 1),
                                 "kesilen_bolgede_tabandaki_vokal_duzeyi_dbfs_medyan": round(float(np.median([db(V0[int((s_[-1]["end"] - 0.15) * SR):int(s_[-1]["end"] * SR)]) for s_ in S])), 1),
                                 "vokalin_genel_duzeyi_dbfs": round(db(V0), 1)}
    # 8) yanlis satir
    kayit = json.load(open(os.path.join(b.SINAMA, "bozuklar.json"), encoding="utf8"))["b08_yanlis_satir"]
    M = coz(os.path.join(b.CIKTI, "b08_yanlis_satir.mp3"))
    d = (M - M0[:len(M)]).mean(axis=1)
    e = b.zarf(d, hop=4410)
    degisen = np.where(e > 0.01)[0]
    R["b08_yanlis_satir"] = {"degisen_aralik_sn": [round(float(degisen.min()) * 0.1, 1), round(float(degisen.max() + 1) * 0.1, 1)] if len(degisen) else None,
                             "beklenen_aralik_sn": [kayit["hedef_bas"], kayit["hedef_son"]], "konan": kayit["konan_satir"], "yerine": kayit["hedef_satir"]}
    # 9) tempo
    M = coz(os.path.join(b.CIKTI, "b09_tempo_80.mp3"))
    R["b09_tempo_80"] = {"sure_orani": round(len(M) / len(M0), 4), "beklenen": 1.25}
    # 10) alcak geciren
    M = coz(os.path.join(b.CIKTI, "b10_alcak_geciren_4k.mp3"))

    def ust_pay(x, hz):
        f, p = ss.welch(x.mean(axis=1), SR, nperseg=4096)
        return float(10 * np.log10(p[f >= hz].sum() / p.sum()))
    R["b10_alcak_geciren_4k"] = {"5khz_ustu_enerji_payi_db": round(ust_pay(M, 5000), 1), "ayni_olcum_tabanda": round(ust_pay(M0, 5000), 1)}
    json.dump(R, open(os.path.join(b.SINAMA, "bozuk_dogrulama.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
