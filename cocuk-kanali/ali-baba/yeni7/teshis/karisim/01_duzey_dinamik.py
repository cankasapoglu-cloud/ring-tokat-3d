#!/usr/bin/env python3
"""(1) Vokal / orkestra düzeyi (söylenen karelerde) ve söylenen - çalgısal bölümler arası ses yüksekliği sıçraması;
(5) dinamikler: tepe çarpanı, PLR, LRA, anlık yükseklik yayılımı, vokalin kendi düzey oynaklığı.
Aynı ölçüm: reddedilen (kendi parçaları), referans (MDX parçaları), onaylı iki şarkı (yalnız karışım).
Kullanım: python3 01_duzey_dinamik.py"""
import numpy as np
from ortak import *
S = {}
def karisim_olcum(ad, mix):
    k = kagirlik(mix); mo, t = anlik(k, 0.4, 0.1); st, _ = anlik(k, 3.0, 0.1); L = butunlesik(mix); tp = gercek_tepe(mix)
    gec = mo > max(-70, L - 20)                                            # müzik çalan pencereler (göreli kapı)
    kisa_crest = []
    w = 3 * FS
    for i in range(0, len(mix) - w, w):
        s = mix[i:i + w]; r = np.sqrt(np.mean(s ** 2))
        if 20 * np.log10(r + 1e-12) > -45: kisa_crest.append(20 * np.log10(np.abs(s).max() / r))
    return {"butunlesik_lufs": R(L), "gercek_tepe_dbtp": R(tp), "plr_db": R(tp - L), "ornek_tepe_dbfs": R(20 * np.log10(np.abs(mix).max())),
            "rms_dbfs": R(duzey(mix)), "tepe_carpani_db": R(20 * np.log10(np.abs(mix).max()) - duzey(mix)),
            "tepe_carpani_3sn_ortanca_db": R(np.median(kisa_crest)), "lra_lu": R(lra(k)),
            "anlik_p95_eksi_p10_lu": R(np.percentile(mo[gec], 95) - np.percentile(mo[gec], 10)), "anlik_p50_lufs": R(np.median(mo[gec])),
            "anlik_olcut_sapma_lu": R(np.std(mo[gec]))}, (mo, t, gec, L)
def enerji_ort(x): return float(dbp(np.mean(10 ** (x / 10)))) if len(x) else float("nan")

for etiket, vad, bad, mad, had in (("red", "red_vokal", "red_altyapi", "red_karisim", "red_hayvan"), ("ref", "ref_vokal", "ref_altyapi", "ref_karisim", None)):
    v, b, mix = esitle(yukle(vad), yukle(bad), yukle(mad)); h = yukle(had)[:len(v)] if had else None
    sesli = sesli_maske(v); vk, bk = kagirlik(v), kagirlik(b)
    o, (mo, t, gec, L) = karisim_olcum(etiket, mix)
    oran = pencere_orani(sesli)[:len(mo)]; mo = mo[:len(oran)]; gec = gec[:len(oran)]; t = t[:len(oran)]
    hm = (np.abs(h).max(axis=1) > 10 ** (-50 / 20)) if h is not None else np.zeros(len(v), bool); horan = pencere_orani(hm)[:len(mo)]
    soy = (oran >= 0.6); cal = (oran <= 0.02) & gec & (horan <= 0.02); hay = (oran <= 0.02) & (horan >= 0.5)
    # orkestra yalnız başına: söylenen ve çalgısal pencerelerde düzeyi
    bmo, _ = anlik(bk, 0.4, 0.1); bmo = bmo[:len(oran)]; vmo, _ = anlik(vk, 0.4, 0.1); vmo = vmo[:len(oran)]
    o.update({
        "soylenen_kare_orani_yuzde": R(100 * sesli.mean()),
        "vokal_eksi_orkestra_db_soylenen": {"agirliksiz_kanal_gucu": R(duzey(v, sesli) - duzey(b, sesli)),
                                              "agirliksiz_orkestra_mono_toplam(04_karisim tanimi)": R(dbp(np.mean(v.mean(1)[sesli] ** 2)) - dbp(np.mean(b.mean(1)[sesli] ** 2))),
                                              "k_agirlikli": R(duzey(vk, sesli) - duzey(bk, sesli))},
        "vokal_eksi_orkestra_k_400ms_pencerelerde": {"ortanca": R(np.median((vmo - bmo)[soy])), "p10": R(np.percentile((vmo - bmo)[soy], 10)), "p90": R(np.percentile((vmo - bmo)[soy], 90))},
        "karisim_anlik_lufs": {"soylenen_enerji_ort": R(enerji_ort(mo[soy])), "calgisal_enerji_ort": R(enerji_ort(mo[cal])), "hayvan_sesi_enerji_ort": R(enerji_ort(mo[hay])) if hay.any() else None,
                               "soylenen_eksi_calgisal_lu": R(enerji_ort(mo[soy]) - enerji_ort(mo[cal])),
                               "hayvan_eksi_calgisal_lu": R(enerji_ort(mo[hay]) - enerji_ort(mo[cal])) if hay.any() else None,
                               "pencere_sayisi": {"soylenen": int(soy.sum()), "calgisal": int(cal.sum()), "hayvan": int(hay.sum())}},
        "orkestra_tek_basina_anlik_lufs": {"soylenen_pencereler": R(enerji_ort(bmo[soy])), "calgisal_pencereler": R(enerji_ort(bmo[cal])),
                                           "soylenen_eksi_calgisal_lu": R(enerji_ort(bmo[soy]) - enerji_ort(bmo[cal]))},
        "vokal": {"tepe_carpani_db_soylenen": R(20 * np.log10(np.abs(v[sesli]).max()) - duzey(v, sesli)),
                  "anlik_400ms_p90_eksi_p10_lu": R(np.percentile(vmo[soy], 90) - np.percentile(vmo[soy], 10)), "anlik_400ms_olcut_sapma_lu": R(np.std(vmo[soy])),
                  "butunlesik_lufs": R(butunlesik(v))},
        "orkestra": {"tepe_carpani_db": R(20 * np.log10(np.abs(b).max()) - duzey(b, gec.repeat(1)[:0] if False else None)), "butunlesik_lufs": R(butunlesik(b)), "lra_lu": R(lra(bk)),
                     "anlik_p95_eksi_p10_lu": R(np.percentile(bmo[gec], 95) - np.percentile(bmo[gec], 10))}})
    if h is not None:
        hk = kagirlik(h); o["hayvan_sesleri"] = {"eksi_vokal_k_db(yuksek_kisimlar)": R(duzey(hk, hm) - duzey(vk, sesli)), "eksi_orkestra_k_db": R(duzey(hk, hm) - duzey(bk, hm)),
                                                  "agirliksiz_eksi_vokal_db": R(duzey(h, hm) - duzey(v, sesli))}
    S[etiket] = o
for etiket, mad in (("onay_el_yikama", "onay_el_yikama"), ("onay_parmak", "onay_parmak")):
    S[etiket], _ = karisim_olcum(etiket, yukle(mad))
# yeni7 denemesi (istenmedi; yalnız aynı ölçümle karşılaştırma için, dosyalar varsa)
import os, subprocess, soundfile as sf
y7 = os.path.join(A, "yeni7")
for ad in ("sarki_OM", "sarki_T"):
    try:
        v, _ = sf.read(os.path.join(y7, ad + "_vokal_islenmis.wav"), always_2d=True); b, _ = sf.read(os.path.join(y7, ad + "_altyapi_islenmis.wav"), always_2d=True)
        tmp = os.path.join(ARA, "_y7.wav"); subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(y7, ad + ".mp3"), "-ar", "44100", "-c:a", "pcm_f32le", tmp], check=True)
        mix, _ = sf.read(tmp, always_2d=True); os.unlink(tmp); v, b, mix = esitle(v, b, mix)
        sesli = sesli_maske(v); vk, bk = kagirlik(v), kagirlik(b); o, (mo, t, gec, L) = karisim_olcum(ad, mix)
        oran = pencere_orani(sesli)[:len(mo)]; mo = mo[:len(oran)]; gec = gec[:len(oran)]; soy = oran >= 0.6; cal = (oran <= 0.02) & gec
        o["vokal_eksi_orkestra_k_db_soylenen"] = R(duzey(vk, sesli) - duzey(bk, sesli)); o["soylenen_eksi_calgisal_lu(hayvan dahil)"] = R(enerji_ort(mo[soy]) - enerji_ort(mo[cal]))
        S["yeni7_" + ad] = o
    except Exception as ex: S["yeni7_" + ad] = {"hata": str(ex)}
yaz("01_duzey_dinamik", S); print(json.dumps(S, ensure_ascii=False, indent=1))
