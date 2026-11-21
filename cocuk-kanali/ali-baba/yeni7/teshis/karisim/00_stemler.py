#!/usr/bin/env python3
"""Reddedilen karışımın (yeni6/sarki_A_ozgun_ses.mp3) parçalarını 04_karisim.py ile AYNI zincirden geçirip ayrı ayrı
ara/ klasörüne yazar (hiçbir mevcut dosyaya dokunmaz):
  ara/red_vokal.wav   işlenmiş vokal (yüksek geçiren + sıkıştırma + 38 ms yankı + kazanç), karışımdaki son düzeyinde (-4,1 dB dahil)
  ara/red_altyapi.wav orkestra + ezgi (-4 dB), son düzeyinde
  ara/red_hayvan.wav  hayvan sesleri, son düzeyinde
  ara/red_karisim.wav bitmiş mp3'ün çözülmüş hali (44,1 kHz)
Ayrıca beğenilen referansı ve onaylı iki şarkıyı 44,1 kHz wav olarak çözer ve yeniden kurulan toplamın bitmiş mp3 ile
örtüştüğünü (ilişki, düzey farkı) ve sınırlayıcının ne kadar çalıştığını ölçer.
Kullanım: python3 00_stemler.py"""
import json, os, subprocess, numpy as np, soundfile as sf
from scipy.signal import fftconvolve
D = os.path.dirname(os.path.abspath(__file__)); ARA = os.path.join(D, "ara")
KOK = os.path.abspath(os.path.join(D, "..", "..", "..", ".."))          # cocuk-kanali
A = os.path.join(KOK, "ali-baba"); Y4 = os.path.join(A, "yeni4"); Y6 = os.path.join(A, "yeni6")
SEP = "/tmp/claude-0/-home-user-ring-tokat-3d/bd9d6832-1bf0-57ca-8544-ce6f4befd453/scratchpad/sep/out_mdx/"
ON, B = 0.100, 240 / 105.0
db = lambda x: 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-12)
def ff(*a): subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)

b, fs = sf.read(os.path.join(Y4, "altyapi", "altyapi_G.wav")); e, _ = sf.read(os.path.join(Y4, "altyapi", "ezgi_alti_G.wav"))
v, fv = sf.read(os.path.join(Y6, "vokal_psola.wav")); assert fs == fv == 44100
pad = np.zeros((int(ON * fs), 2)); band = np.concatenate([pad, b]); ezgi = np.concatenate([pad, e]) * 10 ** (-4 / 20)
n = max(len(band), len(v)); band = np.pad(band, ((0, n - len(band)), (0, 0))); ezgi = np.pad(ezgi, ((0, n - len(ezgi)), (0, 0))); v = np.pad(v, (0, n - len(v)))
w = int(0.05 * fs); env = np.sqrt(np.convolve(v ** 2, np.ones(w) / w, "same")); sesli = env > env.max() * 0.1
zemin = (band + ezgi).mean(axis=1)
hay = np.zeros((n, 2)); SIRA = ["inek", "koyun", "at", "horoz", "ordek", "kopek", "kedi"]; hay_yer = []
for k in range(7):
    ob = [ON + (4 + 8 * k + i) * B for i in range(9)]
    for j, t in enumerate((ob[3], ob[4])):
        s, sr_h = sf.read(os.path.join(A, "yeni3", "ses", f"{SIRA[k]}_{j + 1}.wav")); s = s if s.ndim == 1 else s.mean(axis=1)
        ev = np.sqrt(np.convolve(s ** 2, np.ones(w) / w, "same")); yuk = ev > ev.max() * 10 ** (-10 / 20)
        g = min(10 ** ((-12.5 - db(s[yuk])) / 20), 1.0 / np.abs(s).max()); p = int((t - 0.04) * fs); hay[p:p + len(s)] += (s * g)[:, None]
        hay_yer.append({"hayvan": SIRA[k], "sira": j + 1, "bas_sn": round(p / fs, 3), "sure_sn": round(len(s) / fs, 3), "ornekleme": sr_h,
                        "yuksek_kisim_rms_db": round(float(db((s * g)[yuk])), 2)})
T = os.path.join(ARA, "_")
sf.write(T + "v0.wav", v, fs, subtype="FLOAT")
ff("-i", T + "v0.wav", "-af", "highpass=f=130,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=120:makeup=1,aecho=1.0:1.0:38:0.14", "-c:a", "pcm_f32le", T + "v1.wav")
ff("-i", T + "v0.wav", "-af", "highpass=f=130,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=120:makeup=1", "-c:a", "pcm_f32le", T + "v1k.wav")   # yankısız (karşılaştırma)
vz, _ = sf.read(T + "v1.wav"); vz = np.pad(vz, (0, max(0, n - len(vz))))[:n]
vk, _ = sf.read(T + "v1k.wav"); vk = np.pad(vk, (0, max(0, n - len(vk))))[:n]
gv = 10 ** ((db(zemin[sesli]) + 8.5 - db(vz[sesli])) / 20); vz = vz * gv; vk = vk * gv
bz = band + ezgi; vs = np.stack([vz, vz], axis=1); top = bz + vs + hay
sf.write(T + "top.wav", top, fs, subtype="FLOAT")
ff("-i", T + "top.wav", "-af", "alimiter=limit=0.89:attack=5:release=60:level=disabled,volume=-4.1dB", "-c:a", "pcm_f32le", T + "lim.wav")
lim, _ = sf.read(T + "lim.wav"); lim = lim[:n]
S = 10 ** (-4.1 / 20)
# sınırlayıcının kazanç azaltması: (çıkış / (giriş * S)) 5 ms zarf oranı, gecikme çapraz ilişki ile bulunur
a = top.mean(1) * S; c = lim.mean(1); seg = slice(20 * fs, 40 * fs)
xc = fftconvolve(c[seg], a[seg][::-1]); gecik = int(np.argmax(xc) - (seg.stop - seg.start - 1))
a2 = np.roll(a, gecik); k5 = int(0.005 * fs); z = lambda x: np.sqrt(np.convolve(x ** 2, np.ones(k5) / k5, "same"))
za, zc = z(a2), z(c); m = za > 10 ** (-40 / 20); gr = 20 * np.log10(zc[m] / za[m])
# bitmiş mp3 ile karşılaştırma
ff("-i", os.path.join(Y6, "sarki_A_ozgun_ses.mp3"), "-ar", "44100", "-c:a", "pcm_f32le", os.path.join(ARA, "red_karisim.wav"))
km, _ = sf.read(os.path.join(ARA, "red_karisim.wav")); kmm = km.mean(1); L = min(len(kmm), n)
xc = fftconvolve(kmm[seg], c[seg][::-1]); g2 = int(np.argmax(xc) - (seg.stop - seg.start - 1)); c2 = np.roll(c, g2)
rapor = {"vokal_kazanci_db": round(float(20 * np.log10(gv)), 2), "sinirlayici_gecikme_ornek": gecik,
         "sinirlayici": {"azaltma_db_en_cok": round(float(-gr.min()), 2), "azaltma_gt_0.5dB_sure_yuzde": round(float(100 * (gr < -0.5).mean()), 2),
                         "azaltma_gt_2dB_sure_yuzde": round(float(100 * (gr < -2).mean()), 2), "pre_tepe_dbfs": round(float(20 * np.log10(np.abs(top).max())), 2)},
         "mp3_ile": {"gecikme_ornek": g2, "iliski": round(float(np.corrcoef(kmm[fs:L - fs], c2[fs:L - fs])[0, 1]), 4), "duzey_farki_db": round(float(db(kmm[fs:L - fs]) - db(c2[fs:L - fs])), 3)},
         "soylenen_karelerde_db": {"vokal": round(float(db(vz[sesli] * S)), 2), "orkestra_mono": round(float(db(zemin[sesli] * S)), 2)},
         "hayvan": hay_yer}
for ad, x in (("red_vokal", vs * S), ("red_altyapi", bz * S), ("red_hayvan", hay * S), ("red_vokal_yankisiz", np.stack([vk, vk], 1) * S)):
    sf.write(os.path.join(ARA, ad + ".wav"), x, fs, subtype="PCM_24")
sf.write(os.path.join(ARA, "red_vokal_ham.wav"), v, fs, subtype="PCM_24")        # zincirden ÖNCE (psola çıktısı, kazançsız)
for x in ("v0", "v1", "v1k", "top", "lim"): os.unlink(T + x + ".wav")
# referans ve onaylı şarkılar
for ad, yol in (("ref_karisim", os.path.join(A, "v2_2.mp3")), ("onay_el_yikama", os.path.join(KOK, "el-yikama", "coskulu_2.mp3")),
                ("onay_parmak", os.path.join(KOK, "parmak-ailesi", "coskulu_1.mp3"))):
    ff("-i", yol, "-ar", "44100", "-c:a", "pcm_f32le", os.path.join(ARA, ad + ".wav"))
for ad, yol in (("ref_vokal", SEP + "v2_2_(Vocals)_UVR-MDX-NET-Voc_FT.wav"), ("ref_altyapi", SEP + "v2_2_(Instrumental)_UVR-MDX-NET-Voc_FT.wav")):
    x, r = sf.read(yol); rapor[ad] = {"ornekleme": r, "kanal": x.shape[1] if x.ndim > 1 else 1, "sure": round(len(x) / r, 3)}
    if r != 44100: ff("-i", yol, "-ar", "44100", "-c:a", "pcm_f32le", os.path.join(ARA, ad + ".wav"))
    else: sf.write(os.path.join(ARA, ad + ".wav"), x, r, subtype="PCM_24")
# ayrıştırma denetimi: vokal + çalgı = karışım mı?
rk, _ = sf.read(os.path.join(ARA, "ref_karisim.wav")); rv, _ = sf.read(os.path.join(ARA, "ref_vokal.wav")); ra, _ = sf.read(os.path.join(ARA, "ref_altyapi.wav"))
L = min(len(rk), len(rv), len(ra)); t = (rv[:L] + ra[:L]).mean(1); k = rk[:L].mean(1); seg = slice(20 * fs, 40 * fs)
xc = fftconvolve(k[seg], t[seg][::-1]); g3 = int(np.argmax(xc) - (seg.stop - seg.start - 1))
rapor["ref_ayristirma"] = {"toplam_ile_karisim_gecikme_ornek": g3, "iliski": round(float(np.corrcoef(np.roll(t, g3)[fs:L - fs], k[fs:L - fs])[0, 1]), 4),
                           "duzey_farki_db": round(float(db(k[fs:L - fs]) - db(t[fs:L - fs])), 3)}
json.dump(rapor, open(os.path.join(ARA, "00_stemler.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in rapor.items() if k != "hayvan"}, ensure_ascii=False, indent=1)); print(rapor["hayvan"][:3])
