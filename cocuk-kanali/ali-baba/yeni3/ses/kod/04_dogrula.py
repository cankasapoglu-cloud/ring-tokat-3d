# -*- coding: utf-8 -*-
"""Yazilan 14 WAV dosyasinin BAGIMSIZ dogrulamasi (03_kes.py'deki olcum kodunu kullanmaz):
bicim, sure, tepe, baslangic, bitis, kaynakla ornek-ornek esleme (zaman/perde islemi yok kaniti),
duzey esitligi (pyloudnorm'un K-agirlik suzgeci ile), cift dosyalarin ayniligi/farkliligi.
Cikis kodu 0 = tum zorunlu denetimler gecti."""
import os, sys, json, subprocess, numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy import signal

A = '/home/user/ring-tokat-3d/cocuk-kanali/ali-baba'
OUT = os.path.join(A, 'yeni3', 'ses')
SR = 44100
J = json.load(open(os.path.join(OUT, 'sesler.json'), encoding='utf-8'))
HAYVAN = ['inek', 'koyun', 'at', 'horoz', 'ordek', 'kopek', 'kedi']
hata = []


def env(x, win=0.010, hop=0.001):
    w = int(win * SR); h = int(hop * SR)
    xp = np.concatenate([np.zeros(w // 2), x, np.zeros(w // 2)])
    c = np.concatenate([[0], np.cumsum(xp ** 2)])
    i = np.arange(0, len(x), h)
    return i / SR, 10 * np.log10(np.maximum((c[i + w] - c[i]) / w, 1e-14))


def kw_filter(x):
    """pyloudnorm olcerinin K-agirlik suzgecleri (bagimsiz uygulama)."""
    m = pyln.Meter(SR)
    y = np.concatenate([np.zeros(SR // 2), x])
    for f in m._filters.values():
        y = signal.lfilter(f.b, f.a, y)
    return y[SR // 2:]


def loud_rms(x, k=False):
    y = kw_filter(x) if k else x
    t, d = env(y, win=0.050, hop=0.005)
    m = d >= d.max() - 10
    return 10 * np.log10(np.mean(10 ** (d[m] / 10)))


# 0) K-agirlik saglamasi: 997 Hz tam olcek sinus -> -3.01 LUFS
tt = np.arange(SR * 5) / SR
s = np.sin(2 * np.pi * 997 * tt)
lk = -0.691 + 10 * np.log10(np.mean(kw_filter(s)[SR:] ** 2))
print('K-agirlik saglamasi: 997 Hz 0 dBFS sinus = %.2f LUFS (beklenen -3.01)' % lk)
if abs(lk + 3.01) > 0.1: hata.append('K-agirlik suzgeci beklenen degeri vermiyor')

hp = signal.butter(4, 150, btype='high', fs=SR, output='sos')
print('\n%-8s %5s %6s %6s %6s | %5s %5s %5s | %6s %6s %7s | %7s %7s %6s | %8s %s' % (
    'dosya', 'sure', 'tepe', 'gTepe', 'ilkOrn', 'b-30', 'b-25', 'b-20', 'sonOrn', 'son10', 'kapOnc', 'rmsYB', 'kwYB', 'LUFS-I', 'kaynFark', 'bitis'))
olcum = {}
veri = {}
for h in HAYVAN:
    for n in (1, 2):
        ad = '%s_%d.wav' % (h, n)
        yol = os.path.join(OUT, ad)
        if not os.path.exists(yol):
            hata.append(ad + ' yok'); continue
        info = sf.info(yol)
        x, sr = sf.read(yol, dtype='float64', always_2d=True)
        if sr != 44100: hata.append('%s: ornekleme %d' % (ad, sr))
        if x.shape[1] != 1: hata.append('%s: kanal %d' % (ad, x.shape[1]))
        if info.subtype != 'PCM_16': hata.append('%s: bicim %s' % (ad, info.subtype))
        x = x[:, 0]; veri[ad] = x
        r = J['dosyalar'][ad]
        sure = len(x) / SR
        if sure > 1.85 + 1.5 / SR: hata.append('%s: sure %.4f > 1.85' % (ad, sure))
        tepe = 20 * np.log10(np.abs(x).max())
        gt = 20 * np.log10(max(np.abs(signal.resample_poly(x, 4, 1)).max(), np.abs(x).max()))
        if tepe > -1.0 + 1e-6: hata.append('%s: tepe %.2f dBFS > -1' % (ad, tepe))
        # baslangic: 150 Hz ustu zarf, tepe-30/-25/-20 dB esiklerinin ilk asildigi an
        xh = signal.sosfiltfilt(hp, x)
        t, d = env(xh); P = d.max()
        b30, b25, b20 = [float(t[np.argmax(d > P - k)]) for k in (30, 25, 20)]
        if b25 > 0.020: hata.append('%s: baslangic (tepe-25 dB) %.3f s > 20 ms' % (ad, b25))
        if abs(x[0]) > 1e-3: hata.append('%s: ilk ornek sifir degil (%.4f)' % (ad, x[0]))
        if abs(x[-1]) > 1e-3: hata.append('%s: son ornek sifir degil (%.4f)' % (ad, x[-1]))
        son10 = 10 * np.log10(np.mean(x[-441:] ** 2) + 1e-14) - tepe          # son 10 ms RMS, tepeye gore
        fo = r['fade_out_ms'] / 1000.0
        i0 = int(round((sure - fo - 0.020) / 0.001)); i1 = int(round((sure - fo) / 0.001))
        kap_once = float(d[i0:i1].max() - P)                                  # kapanis baslamadan onceki 20 ms, tepeye gore
        # kaynakla esleme: ayni ornekler x sabit kazanc mi? (fade bolgeleri haric)
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(A, r['kaynak_dosya']), '-ac', '1', '-ar', '44100', '-f', 'f32le', '-'],
                             check=True, capture_output=True).stdout
        src = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
        s0 = r['kirpma_ornek'][0]
        if r['kirpma_ornek'][1] - s0 != len(x): hata.append('%s: kirpma_ornek uzunlugu dosya uzunluguna esit degil' % ad)
        seg = src[s0:s0 + len(x)] * 10 ** (r['kazanc_dB'] / 20)
        a = int(0.006 * SR); b = len(x) - int((fo + 0.001) * SR)
        fark = 20 * np.log10(np.abs(seg[a:b] - x[a:b]).max() + 1e-12)          # dBFS; 16 bit nicemleme ~ -90
        kor = float(np.corrcoef(seg[a:b], x[a:b])[0, 1])
        if fark > -80: hata.append('%s: kaynakla ornek-ornek eslesmiyor (fark %.1f dBFS)' % (ad, fark))
        rh = loud_rms(x); rk = loud_rms(x, True)
        try:
            li = pyln.Meter(SR).integrated_loudness(x)
        except Exception:
            li = float('nan')
        olcum[ad] = dict(sure_sn=round(sure, 4), tepe_dBFS=round(tepe, 2), gercek_tepe_dBTP=round(gt, 2), baslangic_m30_sn=b30, baslangic_m25_sn=b25,
                         baslangic_m20_sn=b20, son10ms_tepeye_gore_dB=round(son10, 1), kapanis_oncesi_tepeye_gore_dB=round(kap_once, 1),
                         rms_yuksek_bolum_dBFS=round(rh, 2), rms_yuksek_bolum_K_dB=round(rk, 2), butunlesik_LUFS=round(li, 2),
                         kaynak_fark_dBFS=round(fark, 1), kaynak_korelasyon=round(kor, 6))
        print('%-8s %5.3f %6.2f %6.2f %6.4f | %5.3f %5.3f %5.3f | %6.4f %6.1f %7.1f | %7.2f %7.2f %6.2f | %8.1f %s' % (
            ad[:-4], sure, tepe, gt, abs(x[0]), b30, b25, b20, abs(x[-1]), son10, kap_once, rh, rk, li, fark,
            'FADE %d ms' % r['fade_out_ms'] if r['sonu_fade'] else 'dogal (%d ms kapanis)' % r['fade_out_ms']))
        # JSON ile tutarlilik
        for alan, deger, tol in (('sure_sn', sure, 0.001), ('tepe_dBFS', tepe, 0.02), ('rms_yuksek_bolum_dBFS', rh, 0.05), ('rms_yuksek_bolum_K_agirlikli_dB', rk, 0.05)):
            if abs(r[alan] - deger) > tol: hata.append('%s: sesler.json %s=%.3f ama olculen %.3f' % (ad, alan, r[alan], deger))
        if r['sonu_fade'] and not (150 <= r['fade_out_ms'] <= 250): hata.append('%s: fade-out %d ms aralik disi' % (ad, r['fade_out_ms']))

kw = [v['rms_yuksek_bolum_K_dB'] for v in olcum.values()]
rm = [v['rms_yuksek_bolum_dBFS'] for v in olcum.values()]
li = [v['butunlesik_LUFS'] for v in olcum.values()]
tp = [v['tepe_dBFS'] for v in olcum.values()]
print('\nDuzey yayilimi (14 dosya): K-agirlikli yuksek-bolum RMS %.2f..%.2f (fark %.2f dB) | duz RMS %.2f..%.2f (fark %.2f dB) | butunlesik LUFS %.2f..%.2f (fark %.2f dB) | tepe %.2f..%.2f dBFS' % (
    min(kw), max(kw), max(kw) - min(kw), min(rm), max(rm), max(rm) - min(rm), np.nanmin(li), np.nanmax(li), np.nanmax(li) - np.nanmin(li), min(tp), max(tp)))
if max(kw) - min(kw) > 0.2: hata.append('K-agirlikli duzey farki %.2f dB > 0.2' % (max(kw) - min(kw)))

print('\nCiftler:')
for h in HAYVAN:
    a, b = veri['%s_1.wav' % h], veri['%s_2.wav' % h]
    ayni = len(a) == len(b) and np.array_equal(a, b)
    k1, k2 = J['dosyalar']['%s_1.wav' % h]['kirpma_sn'], J['dosyalar']['%s_2.wav' % h]['kirpma_sn']
    n = min(len(a), len(b)); kr = float(np.corrcoef(a[:n], b[:n])[0, 1])
    print('  %-6s %s (kirpma %s / %s, dalga korelasyonu %.3f)' % (h, 'AYNI cagri iki kez' if ayni else 'iki FARKLI cagri', k1, k2, kr))
    if ayni != (k1 == k2): hata.append('%s: ayni/farkli bilgisi tutarsiz' % h)

json.dump(dict(olcum=olcum, hatalar=hata), open(os.path.join(OUT, 'ara', 'dogrulama.json'), 'w'), ensure_ascii=False, indent=1)
print('\nSONUC:', 'TUM ZORUNLU DENETIMLER GECTI' if not hata else 'HATALAR:\n  ' + '\n  '.join(hata))
sys.exit(1 if hata else 0)
