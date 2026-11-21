#!/usr/bin/env python3
"""yeni7 karışımı: boşluksuz düzenin orkestrası + ezgiye oturtulmuş vokal + gerçek hayvan sesleri (kıtanın 3. ölçüsünde iki kez,
vuruş 0 ve vuruş 2; hemen ardından "diye bağırır").

Ayarlar (ortam değişkeni):  VOKAL_USTU_DB  söylenen karelerde vokal orkestranın kaç dB üstünde (7.0)
                            EZGI_DB        vokalin altındaki klarnet ezgisine ek kazanç (-3.0)
                            YANKI_DB       ortak oda yankısının vokale göre düzeyi (-15.0);  YANKI_SN  yankı süresi RT60 (0.75)
                            HAYVAN_DB      hayvan sesinin vokale göre düzeyi (-1.0)
Kullanım: python3 02_karisim.py [vokal wav] [çıktı mp3]"""
import json, os, subprocess, sys, numpy as np, soundfile as sf, pyloudnorm
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
D = os.path.dirname(os.path.abspath(__file__)); A = os.path.dirname(D)
VOK = sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, "vokal.wav"); CIK = sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, "sarki.mp3")
E = lambda k, v: float(os.environ.get(k, v))
VU, EZ, YD, YS, HD = E("VOKAL_USTU_DB", 7.0), E("EZGI_DB", -3.0), E("YANKI_DB", -15.0), E("YANKI_SN", 0.75), E("HAYVAN_DB", -1.0)
Z = json.load(open(os.path.join(D, "altyapi", "zaman_G.json"), encoding="utf8")); BEAT = Z["vurus_sn"]
b, fs = sf.read(os.path.join(D, "altyapi", "altyapi_G.wav")); e, _ = sf.read(os.path.join(D, "altyapi", "ezgi_alti_G.wav")); v, fv = sf.read(VOK); assert fs == fv == 44100
n = len(b); v = np.pad(v, (0, max(0, n - len(v))))[:n]; band = b + e * 10 ** (EZ / 20)
db = lambda x: 10 * np.log10(np.mean(np.square(x)) + 1e-12)
T = os.path.join(D, "_gecici_")
def ff(giris, filtre, cikis): subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", giris, "-af", filtre, "-c:a", "pcm_f32le", cikis], check=True)

# ---- vokal: alt kesim + hafif sıkıştırma (düzey zincirden SONRA ölçülür) ---------------------------------------------
sf.write(T + "v0.wav", v, fs, subtype="FLOAT")
ff(T + "v0.wav", "highpass=f=110,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=120:makeup=1", T + "v1.wav")
vz, _ = sf.read(T + "v1.wav"); vz = np.pad(vz, (0, max(0, n - len(vz))))[:n]
w = int(0.05 * fs); env = np.sqrt(np.convolve(vz ** 2, np.ones(w) / w, "same")); sesli = env > env.max() * 0.1
zemin = band.mean(axis=1); vz *= 10 ** ((db(zemin[sesli]) + VU - db(vz[sesli])) / 20)

# ---- gerçek hayvan sesleri: etkin bölüm kesilir, 2 vuruşa (1,14 sn) sığmayan hafifçe hızlandırılır ------------------
SIRA = ["inek", "koyun", "at", "horoz", "ordek", "kopek", "kedi"]; YER = 2 * BEAT; hay = np.zeros(n); kayit = []
def hazirla(ad):
    s, r = sf.read(os.path.join(A, "yeni3", "ses", ad + ".wav")); s = s if s.ndim == 1 else s.mean(axis=1); assert r == fs
    ev = np.sqrt(np.convolve(s ** 2, np.ones(w) / w, "same")); et = np.where(ev > ev.max() * 10 ** (-20 / 20))[0]
    a0, b0 = max(0, et[0] - int(0.03 * fs)), min(len(s), et[-1] + int(0.06 * fs)); s = s[a0:b0]; sure = len(s) / fs; hiz = 1.0
    if sure > YER - 0.04:
        hiz = min(1.35, sure / (YER - 0.06)); sf.write(T + "h0.wav", s, fs, subtype="FLOAT"); ff(T + "h0.wav", f"atempo={hiz:.4f}", T + "h1.wav"); s, _ = sf.read(T + "h1.wav")
    m = int((YER + 0.02) * fs)
    if len(s) > m: s = s[:m].copy(); f = int(0.14 * fs); s[-f:] *= np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    f = int(0.008 * fs); s[:f] *= np.linspace(0, 1, f)
    ev = np.sqrt(np.convolve(s ** 2, np.ones(w) / w, "same")); yuk = ev > ev.max() * 10 ** (-10 / 20)
    return s, db(s[yuk]), sure, hiz
for k in range(7):
    hs = Z["kitalar"][k]["hayvan_sesi"]
    for j, t in enumerate((hs["ses1_baslangic"], hs["ses2_baslangic"])):
        s, d, sure, hiz = hazirla(f"{SIRA[k]}_{j + 1}"); g = 10 ** ((db(vz[sesli]) + HD - d) / 20); g = min(g, 0.9 / np.abs(s).max())
        p = int((t - 0.03) * fs); hay[p:p + len(s)] += s * g; kayit.append((SIRA[k], j + 1, round(sure, 2), round(hiz, 2), round(len(s) / fs, 2)))
print("hayvan sesleri (ad, sıra, özgün sn, hız, yerleşen sn):", kayit)

# ---- ortak oda yankısı: vokal ve hayvan sesleri aynı odada çalsın (orkestranın kendi yankısı var) -------------------
rg = np.random.default_rng(7); L = int((YS * 1.3) * fs); tt = np.arange(L) / fs
ir = rg.standard_normal((L, 2)) * np.exp(-6.908 * tt / YS)[:, None]                 # 60 dB düşüş YS saniyede
ir = sosfilt(butter(2, [300, 6500], "bandpass", fs=fs, output="sos"), ir, axis=0); ir = np.vstack([np.zeros((int(0.022 * fs), 2)), ir])
kuru = vz + hay * 0.7; islak = np.stack([fftconvolve(kuru, ir[:, c])[:n] for c in (0, 1)], axis=1)
islak *= 10 ** ((db(vz[sesli]) + YD - db(islak[sesli])) / 20)
mix = band + np.stack([vz + hay, vz + hay], axis=1) + islak

# ---- son işlem: hafif ortak sıkıştırma ("yapıştırıcı"), -14 LUFS, tepe en çok -1 dBTP --------------------------------
sf.write(T + "m0.wav", mix * 0.5, fs, subtype="FLOAT")
ff(T + "m0.wav", "acompressor=threshold=-20dB:ratio=1.6:attack=30:release=250:makeup=1", T + "m1.wav"); m, _ = sf.read(T + "m1.wav")
olc = pyloudnorm.Meter(fs); tp = lambda x: 20 * np.log10(np.abs(resample_poly(x, 4, 1, axis=0)).max() + 1e-12); kaz = 0.0
for _ in range(6):
    sf.write(T + "m2.wav", m * 10 ** (kaz / 20), fs, subtype="FLOAT"); ff(T + "m2.wav", "alimiter=limit=0.84:attack=4:release=60:level=disabled", T + "m3.wav"); y, _ = sf.read(T + "m3.wav")
    Lu = olc.integrated_loudness(y)
    if abs(Lu + 14.0) < 0.15: break
    kaz += -14.0 - Lu
f = int(0.5 * fs); y[-f:] *= np.linspace(1, 0, f)[:, None]
sf.write(T + "son.wav", y, fs, subtype="PCM_24"); subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", T + "son.wav", "-ar", "44100", "-b:a", "192k", CIK], check=True)
sf.write(os.path.splitext(CIK)[0] + "_vokal_islenmis.wav", np.stack([vz, vz], axis=1) + islak, fs, subtype="PCM_16")     # kapı ölçümleri için
sf.write(os.path.splitext(CIK)[0] + "_altyapi_islenmis.wav", band, fs, subtype="PCM_16")

# ---- denetim: BİTMİŞ mp3 üzerinde -----------------------------------------------------------------------------------
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", CIK, T + "k.wav"], check=True); km, _ = sf.read(T + "k.wav"); kmo = km.mean(axis=1)[:n]
ara = np.zeros(n, bool)
for k in range(7): o = Z["kitalar"][k]["olcu_baslangiclari"]; ara[int(o[5] * fs):int(o[7] * fs)] = True
print("vokal orkestranın %.1f dB üstünde (söylenen karelerde); bitmiş karışım: söylenen %.1f dB, çalgı arası %.1f dB (fark %.1f); vokal ile ilişki %.2f"
      % (db(vz[sesli]) - db(zemin[sesli]), db(kmo[sesli]), db(kmo[ara]), db(kmo[sesli]) - db(kmo[ara]), np.corrcoef(kmo[sesli], vz[sesli])[0, 1]))
print("%s: %.2f sn, %.1f LUFS, gerçek tepe %.1f dBTP" % (os.path.basename(CIK), len(km) / fs, olc.integrated_loudness(km), tp(km)))
for x in ("v0", "v1", "h0", "h1", "m0", "m1", "m2", "m3", "son", "k"):
    if os.path.exists(T + x + ".wav"): os.unlink(T + x + ".wav")
