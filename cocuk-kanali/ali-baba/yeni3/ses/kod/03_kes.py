# -*- coding: utf-8 -*-
"""Hayvan cagrilarini keser, esit algilanan duzeye getirir, yazar ve sesler.json uretir.

Kurallar (gorev tanimi):
 - her cagri kendi olcusune (~2.07 s) oturur: en cok 1.85 s (dogal kuyruk dahil)
 - dosya, ses baslangicinin en cok 20 ms oncesinde baslar; 5 ms fade-in
 - dogal sonus 1.85 s'ye sigiyorsa dogal biter (yalniz gurultu tabaninda kisa yumusatma),
   sigmiyorsa 150-250 ms fade-out
 - 14 dosyanin "yuksek bolum" duzeyi esitlenir (K-agirlikli RMS), tepe <= -1 dBFS
 - islem YOK: zaman/perde degistirme, sikistirma, limitleme, filtre yok. Yalniz kirpma + kazanc + fade.

Calistirma: python3 03_kes.py
"""
import os, json, wave, numpy as np
from scipy import signal
from ortak import *

MAKS = 1.85          # s, bir cagrinin en uzun suresi
ON_PAY = 0.012       # s, baslangictan (tepe-25 dB) onceki pay (<= 20 ms olmali)
ON_PAY20 = 0.017     # s, tepe-20 dB noktasindan onceki en buyuk pay
FADE_IN = 0.005
YUMUSATMA = 0.030    # s, dogal bitiste gurultu tabanindaki kapanis
TEPE_HEDEF = -1.0    # dBFS
FADE_OUT = 0.200     # s, sigmayan cagrida fade-out (150-250 ms araliginda)
KAPANIS = 0.040      # s, dogal dususu sinira denk gelen cagrida kapanis

# hayvan, no, kaynak varyasyon, arama penceresi (s), aciklama
SECIM = [
    ('inek', 1, 'inek_2', (0.50, 2.60), 'birinci möö'),
    ('inek', 2, 'inek_2', (3.50, 5.60), 'ikinci (farklı) möö, aynı kayıt'),
    ('koyun', 1, 'koyun_1', (0.95, 2.60), 'meleme (kayıtta tek meleme var)'),
    ('koyun', 2, 'koyun_1', (0.95, 2.60), 'aynı meleme tekrar (kayıtta tek meleme var)'),
    ('at', 1, 'at_4', (0.00, 2.45), 'kişneme (kayıtta tek kişneme var)'),
    ('at', 2, 'at_4', (0.00, 2.45), 'aynı kişneme tekrar (kayıtta tek kişneme var)'),
    ('horoz', 1, 'horoz_4', (0.00, 2.60), 'ötüş (kayıtta tek ötüş var)'),
    ('horoz', 2, 'horoz_4', (0.00, 2.60), 'aynı ötüş tekrar (kayıtta tek ötüş var)'),
    ('ordek', 1, 'ordek_2', (0.20, 1.90), 'vak vak: 1. ve 2. vaklama'),
    ('ordek', 2, 'ordek_2', (1.85, 3.45), 'vak vak: 3. ve 4. vaklama (farklı çift, aynı kayıt)'),
    ('kopek', 1, 'kopek_1', (0.00, 1.50), 'hav hav: 1. ve 2. havlama'),
    ('kopek', 2, 'kopek_1', (1.70, 2.95), 'hav hav: 3. ve 4. havlama (farklı çift, aynı kayıt)'),
    ('kedi', 1, 'kedi_1', (0.00, 1.60), 'birinci miyav'),
    ('kedi', 2, 'kedi_1', (1.55, 2.58), 'ikinci (farklı) miyav, aynı kayıt'),
]


# ---------------------------------------------------------------- yardimcilar
def k_agirlik(x, sr=SR):
    """ITU-R BS.1770 K-agirlik suzgeci (pyloudnorm ile ayni katsayi formulleri)."""
    def shelf(G, Q, fc):
        A_ = 10 ** (G / 40.0); w0 = 2 * np.pi * fc / sr; al = np.sin(w0) / (2 * Q)
        b = [A_ * ((A_ + 1) + (A_ - 1) * np.cos(w0) + 2 * np.sqrt(A_) * al),
             -2 * A_ * ((A_ - 1) + (A_ + 1) * np.cos(w0)),
             A_ * ((A_ + 1) + (A_ - 1) * np.cos(w0) - 2 * np.sqrt(A_) * al)]
        a = [(A_ + 1) - (A_ - 1) * np.cos(w0) + 2 * np.sqrt(A_) * al,
             2 * ((A_ - 1) - (A_ + 1) * np.cos(w0)),
             (A_ + 1) - (A_ - 1) * np.cos(w0) - 2 * np.sqrt(A_) * al]
        return np.array(b) / a[0], np.array(a) / a[0]

    def hp(Q, fc):
        w0 = 2 * np.pi * fc / sr; al = np.sin(w0) / (2 * Q)
        b = [(1 + np.cos(w0)) / 2, -(1 + np.cos(w0)), (1 + np.cos(w0)) / 2]
        a = [1 + al, -2 * np.cos(w0), 1 - al]
        return np.array(b) / a[0], np.array(a) / a[0]
    b1, a1 = shelf(4.0, 1 / np.sqrt(2), 1500.0)
    b2, a2 = hp(0.5, 38.0)
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x))


def yuksek_bolum(x, win=0.050, esik=10.0):
    """'Yuksek bolum' maskesi: 50 ms RMS zarfi, en yuksek degerin `esik` dB altina kadar olan kareler.
    Donus: (ham RMS dBFS, K-agirlikli RMS dB, yuksek bolumun toplam suresi s)."""
    xk = k_agirlik(np.concatenate([np.zeros(SR // 2), x]))[SR // 2:]   # suzgec gecisi icin on dolgu
    t, d = zarf(x, hop=0.005, win=win)
    tk, dk = zarf(xk, hop=0.005, win=win)
    m = d >= d.max() - esik
    mk = dk >= dk.max() - esik
    ham = 10 * np.log10(np.mean(10 ** (d[m] / 10)))
    kw = 10 * np.log10(np.mean(10 ** (dk[mk] / 10)))
    return float(ham), float(kw), float(m.sum() * 0.005)


def anlik_maks(x):
    """En yuksek 'momentary' duzey (400 ms pencere, K-agirlikli, LUFS olcegi: -0.691 + 10log10)."""
    xk = k_agirlik(np.concatenate([np.zeros(SR // 2), x, np.zeros(int(0.4 * SR))]))[SR // 2:]
    t, d = zarf(xk, hop=0.010, win=0.400)
    return float(d.max() - 0.691)


def maks_pencere(x, win=0.200):
    """K-agirlikli sinyalin `win` saniyelik pencerede en yuksek RMS'i (dB). Bilgi amacli capraz olcu."""
    xk = k_agirlik(np.concatenate([np.zeros(SR // 2), x, np.zeros(int(win * SR))]))[SR // 2:]
    t, d = zarf(xk, hop=0.005, win=win)
    return float(d.max())


def telefon_bandi(x):
    """300 Hz - 8 kHz bant (telefon hoparlorunun asagi yukari verdigi bolge) RMS'i, yuksek bolumde."""
    sos = signal.butter(4, [300, 8000], btype='band', fs=SR, output='sos')
    y = signal.sosfilt(sos, x)
    t, d = zarf(x, hop=0.005, win=0.050)
    t2, d2 = zarf(y, hop=0.005, win=0.050)
    m = d >= d.max() - 10
    return float(10 * np.log10(np.mean(10 ** (d2[m] / 10))))


def algilama(x):
    """Sinir bulmak icin kullanilan sinyal: 150 Hz ustu (sifir fazli). Kayitlardaki <100 Hz ugultu
    cagri sinirlarini bozmasin diye. YALNIZ olcum icindir; yazilan ses suzulmez."""
    sos = signal.butter(4, 150, btype='high', fs=SR, output='sos')
    return signal.sosfiltfilt(sos, x)


def sinir_bul(x, pencere):
    """Zarf analizi ile bir cagrinin sinirlari.
    ince zarf: 150 Hz ustu sinyalin 10 ms pencere / 1 ms adim RMS'i. Donus: kaynak zaman ekseninde s."""
    hop = 0.001
    t, d = zarf(algilama(x), hop=hop, win=0.010)
    w0, w1 = pencere
    i0 = int(round(w0 / hop)); i1 = min(int(round(w1 / hop)), len(t))
    dw = d[i0:i1]
    P = float(dw.max())
    taban = float(np.percentile(dw, 10))            # pencere icindeki gurultu tabani
    esik20 = max(P - 20.0, taban + 10.0)            # "yuksek" bolge
    esik_on = max(P - 25.0, taban + 8.0)            # baslangic esigi
    ust = np.where(dw > esik20)[0]
    a20, b20 = ust[0], ust[-1]
    # baslangic: a20'den geriye, zarf en az 5 ms boyunca esik_on altinda kalana dek
    k = a20
    while k > 0:
        if dw[k - 1] <= esik_on and np.all(dw[max(0, k - 5):k] <= esik_on):
            break
        k -= 1
    t_on = t[i0 + k]
    # dogal bitis: b20'den ileri, zarf en az 20 ms boyunca esik_son altinda kalana dek
    son_taban = float(np.percentile(dw[b20:min(len(dw), b20 + 600)], 20)) if b20 + 50 < len(dw) else taban
    esik_son = max(P - 40.0, son_taban + 5.0)
    j = b20
    while j < len(dw) - 1:
        if dw[j + 1] <= esik_son and np.all(dw[j + 1:j + 21] <= esik_son):
            break
        j += 1
    t_off = t[i0 + j] + hop
    return dict(P=P, taban=taban, t20a=float(t[i0 + a20]), t20b=float(t[i0 + b20] + hop), t_on=float(t_on),
                t_off=float(t_off), esik_on=esik_on, esik_son=esik_son, zarf=(t, d))


def ic_baslangiclar(c, P_rel=-20.0, min_bosluk=0.10):
    """Kirpilmis cagri icindeki alt-seslerin (vak/hav) baslangic zamanlari."""
    t, d = zarf(c, hop=0.001, win=0.010)
    P = d.max()
    seg = bolutler_ms(t, d, P + P_rel, min_bosluk)
    return [round(float(s), 3) for s, e in seg], [round(float(e), 3) for s, e in seg]


def bolutler_ms(t, d, esik, min_bosluk):
    on = d > esik
    seg = []
    i = 0
    while i < len(on):
        if on[i]:
            j = i
            while j + 1 < len(on) and on[j + 1]:
                j += 1
            if seg and t[i] - seg[-1][1] < min_bosluk:
                seg[-1][1] = t[j]
            else:
                seg.append([t[i], t[j]])
            i = j + 1
        else:
            i += 1
    return [s for s in seg if s[1] - s[0] >= 0.02]


def spektral(c):
    """Hayvan-disi icerik icin basit spektral istatistikler (kirpilmis cagri uzerinde)."""
    n_fft, hop = 2048, 256
    f, tt, Z = signal.stft(c, fs=SR, nperseg=n_fft, noverlap=n_fft - hop, window='hann', padded=False, boundary=None)
    S = np.abs(Z) ** 2
    band = (f >= 100) & (f <= 8000)
    Sb = S[band] + 1e-16
    fb = f[band]
    en = 10 * np.log10(Sb.sum(0))
    P = en.max()
    loud = en >= P - 20
    duz = np.exp(np.mean(np.log(Sb), 0)) / np.mean(Sb, 0)       # spektral duzluk 0..1
    agirlik = (fb[:, None] * Sb).sum(0) / Sb.sum(0)             # agirlik merkezi (Hz)
    # baskin tepe frekansi (parabolik ara degerleme)
    k = np.argmax(Sb, 0)
    kk = np.clip(k, 1, Sb.shape[0] - 2)
    a, b_, g = np.log(Sb[kk - 1, np.arange(Sb.shape[1])]), np.log(Sb[kk, np.arange(Sb.shape[1])]), np.log(Sb[kk + 1, np.arange(Sb.shape[1])])
    kay = 0.5 * (a - g) / (a - 2 * b_ + g + 1e-12)
    fpk = (kk + kay) * (SR / n_fft) + fb[0]
    dt = hop / SR

    def en_uzun(mask):
        en_u = 0; cur = 0
        for v in mask:
            cur = cur + 1 if v else 0
            en_u = max(en_u, cur)
        return en_u * dt

    # sabit ton: baskin tepe +-30 cent ve duzey +-2 dB icinde kalan en uzun kosu (yuksek karelerde)
    en_sabit = 0.0
    i = 0
    N = len(fpk)
    while i < N:
        if not loud[i]:
            i += 1; continue
        j = i
        while j + 1 < N and loud[j + 1] and abs(1200 * np.log2(fpk[j + 1] / fpk[i])) <= 30 and abs(en[j + 1] - en[i]) <= 2.0:
            j += 1
        en_sabit = max(en_sabit, (j - i + 1) * dt)
        i += 1
    genisbant = en_uzun(loud & (duz > 0.30))
    # sessizlik: 20 ms zarf, tepe-45 dB alti (veya -70 dBFS alti) en uzun kosu
    t, d = zarf(c, hop=0.005, win=0.020)
    ses_mask = d < max(d.max() - 45, -200)
    cur = 0; en_ses = 0
    for v in ses_mask:
        cur = cur + 1 if v else 0
        en_ses = max(en_ses, cur)
    return dict(duzluk_medyan=round(float(np.median(duz[loud])), 3),
                agirlik_merkezi_hz=int(round(float(np.median(agirlik[loud])))),
                baskin_tepe_medyan_hz=int(round(float(np.median(fpk[loud])))),
                sabit_ton_en_uzun_sn=round(float(en_sabit), 3),
                genisbant_gurultu_en_uzun_sn=round(float(genisbant), 3),
                sessizlik_en_uzun_sn=round(en_ses * 0.005, 3),
                sessizlik_orani=round(float(ses_mask.mean()), 3))


def gercek_tepe_db(x):
    """Ornekler arasi tepeyi de gormek icin 4x asiri ornekleme ile tepe (dBTP benzeri)."""
    y = signal.resample_poly(x, 4, 1)
    return 20 * np.log10(max(float(np.max(np.abs(y))), float(np.max(np.abs(x))), 1e-7))


def yaz(yol, x):
    w = wave.open(yol, 'w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(np.round(np.clip(x, -1, 1) * 32767).astype('<i2').tobytes()); w.close()


# ---------------------------------------------------------------- 1) sinirlar + kirpma
kaynaklar = {}
cagri = []
print('ZARF ANALIZI (ince zarf: 150 Hz ustu sinyal, 10 ms pencere / 1 ms adim; duzeyler dBFS, zamanlar kaynak dosyada s)')
print('%-8s %-8s %6s %6s | %7s %7s | %7s %7s | %6s %6s %6s | %s' % (
    'dosya', 'kaynak', 'tepeZ', 'taban', '-20bas', '-20son', 'baslng', 'dogSon', 'dogSur', 'kesBas', 'kesSon', 'bitis'))
for hayvan, no, kay, pencere, acik in SECIM:
    if kay not in kaynaklar:
        kaynaklar[kay] = oku(os.path.join(ALT, kay + '.mp3'))
    x = kaynaklar[kay]
    b = sinir_bul(x, pencere)
    t, d = b['zarf']
    # dosya basi: tepe-25 dB esigi en cok 12 ms, tepe-20 dB esigi en cok 17 ms sonra gelsin (hangisi gecse)
    bas = max(0.0, b['t_on'] - ON_PAY, b['t20a'] - ON_PAY20)
    dogal_son = b['t_off'] + YUMUSATMA
    dogal_sure = dogal_son - bas
    not_ek = []
    if dogal_sure <= MAKS:
        son = dogal_son; fade = False; fo = YUMUSATMA; tur = 'dogal'
    else:
        son = bas + MAKS
        # sinirdan sonra kalan kuyrugun duzeyi (cagri tepesine gore)
        i_a = int(round(son / 0.001)); i_b = int(round(b['t_off'] / 0.001))
        kalan = float(d[i_a:max(i_b, i_a + 1)].max() - b['P'])
        if kalan <= -25.0:
            # yuksek bolum bitmis, yalniz -25 dB altindaki kuyruk disarida kaliyor: dogal dusus + kisa kapanis
            fade = False; fo = KAPANIS; tur = 'dogal*'
            not_ek.append('doğal düşüş 1.85 sn içinde tamamlanıyor (yüksek bölüm %.2f sn\'de bitiyor); yalnız tepeye göre %.0f dB ve altındaki %.0f ms\'lik kuyruk dışarıda kaldı, son %d ms yumuşatıldı'
                          % (b['t20b'] - bas, kalan, (b['t_off'] - son) * 1000, KAPANIS * 1000))
        else:
            fade = True; fo = FADE_OUT; tur = 'fade'
            not_ek.append('doğal uzunluk %.2f sn (1.85 sn sınırını aşıyor): son %.0f ms fade-out; kaynağın son %.0f ms\'si kesildi (kesim noktasında düzey tepeye göre %.0f dB)'
                          % (b['t_off'] - bas, fo * 1000, (b['t_off'] - son) * 1000, kalan))
    s0 = int(round(bas * SR)); s1 = min(int(round(son * SR)), len(x))
    c = x[s0:s1].copy()
    nfi = int(round(FADE_IN * SR)); nfo = int(round(fo * SR))
    c[:nfi] *= np.linspace(0, 1, nfi, endpoint=False)
    c[-nfo:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, nfo)))      # yukseltilmis kosinus kapanis
    print('%-8s %-8s %6.1f %6.1f | %7.3f %7.3f | %7.3f %7.3f | %6.3f %6.3f %6.3f | %s' % (
        '%s_%d' % (hayvan, no), kay, b['P'], b['taban'], b['t20a'], b['t20b'], b['t_on'], b['t_off'], b['t_off'] - b['t_on'], bas, son, tur))
    # kaynakta cagri disindaki arka plan duzeyi (cagriya bitisik +-0.6 s, cagri haric), yuksek bolume gore
    tz, dz = zarf(x, hop=0.005, win=0.020)
    tz2, dz2 = zarf(algilama(x), hop=0.005, win=0.020)
    cev = ((tz >= b['t_on'] - 0.6) & (tz < b['t_on'] - 0.03)) | ((tz > b['t_off'] + 0.03) & (tz <= b['t_off'] + 0.6))
    arka = float(np.percentile(dz[cev], 25)) if cev.sum() >= 10 else float('nan')          # tam bant
    arka_hp = float(np.percentile(dz2[cev], 25)) if cev.sum() >= 10 else float('nan')      # 150 Hz ustu
    cagri.append(dict(hayvan=hayvan, no=no, kaynak=kay, acik=acik, bas=s0 / SR, son=s1 / SR, s0=s0, s1=s1, fade=fade, fo=fo, tur=tur,
                      c=c, b=b, not_ek=not_ek, arka=arka, arka_hp=arka_hp))

# ---------------------------------------------------------------- 2) duzey esitleme
for q in cagri:
    q['ham'], q['kw'], q['yb_sure'] = yuksek_bolum(q['c'])
    q['tepe'] = gercek_tepe_db(q['c'])        # ornek tepesi ve 4x asiri orneklenmis tepenin buyugu
    q['crestK'] = q['tepe'] - q['kw']
# ortak hedef: hicbir dosyada tepe -1 dBFS'yi asmayacak en yuksek ortak K-agirlikli "yuksek bolum" duzeyi
HEDEF_KW = min(TEPE_HEDEF - q['crestK'] for q in cagri)
print('\nDUZEY ESITLEME: ortak hedef (K-agirlikli yuksek-bolum RMS) = %.2f dB; sinirlayici yok, yalniz kazanc' % HEDEF_KW)
print('%-8s %6s %7s %7s %6s | %6s | %7s %7s %7s %7s %7s %6s | %6s %6s' % ('dosya', 'sure', 'tepeOnc', 'kwOnc', 'crest', 'kazanc', 'tepe', 'rmsYB', 'kwYB', 'anlik', 'telBnd', 'ybSure', 'basl', 'vurgu') + ' %7s' % 'K200ms')
sonuc = {}
for q in cagri:
    g = HEDEF_KW - q['kw']
    y = q['c'] * 10 ** (g / 20)
    ad = '%s_%d' % (q['hayvan'], q['no'])
    yol = os.path.join(OUT, ad + '.wav')
    yaz(yol, y)
    # yazilan dosyayi geri oku ve olc
    w = wave.open(yol); z = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64) / 32768; w.close()
    ham, kw, ybs = yuksek_bolum(z)
    tp = tepe_db(z); gtp = gercek_tepe_db(z)
    am = anlik_maks(z)
    m200 = maks_pencere(z, 0.200)
    tb = telefon_bandi(z)
    sp = spektral(z)
    ib, ibs = ic_baslangiclar(z)
    tz, dz = zarf(algilama(z), hop=0.001, win=0.010)
    Pz = dz.max()
    onset = float(tz[np.argmax(dz > max(Pz - 25.0, q['b']['esik_on'] - q['b']['P'] + Pz))])
    vurgu = float(tz[np.argmax(dz > Pz - 6.0)])
    arka_rel = q['arka_hp'] + g - ham                  # 150 Hz ustu arka plan, yuksek bolume gore (dB)
    arka_tam = q['arka'] + g - ham                     # tam bant (ugultu dahil)
    print('%-8s %6.3f %7.1f %7.1f %6.1f | %+6.1f | %7.2f %7.2f %7.2f %7.2f %7.2f %6.2f | %6.3f %6.3f %7.2f' % (
        ad, len(z) / SR, q['tepe'], q['kw'], q['crestK'], g, tp, ham, kw, am, tb, ybs, onset, vurgu, m200))
    # ---- bayraklar
    bayrak = []
    if sp['sabit_ton_en_uzun_sn'] > 0.40:
        bayrak.append('sabit-ton: baskın tepe frekansı %.2f sn boyunca ±30 cent/±2 dB içinde sabit (müzik benzeri sabit ton olabilir; uzun, düz bir hayvan sesi de bunu verir)' % sp['sabit_ton_en_uzun_sn'])
    if sp['genisbant_gurultu_en_uzun_sn'] > 0.40:
        bayrak.append('genişbant-gürültü: %.2f sn boyunca spektral düzlük > 0.30' % sp['genisbant_gurultu_en_uzun_sn'])
    if sp['sessizlik_en_uzun_sn'] > 0.50:
        bayrak.append('uzun-sessizlik: %.2f sn (tepe-45 dB altı)' % sp['sessizlik_en_uzun_sn'])
    if arka_rel > -35.0:
        bayrak.append('arka-plan: kaynakta çağrının hemen yanındaki zemin (150 Hz üstü) yüksek bölümün yalnız %.0f dB altında (hışırtı/ortam sesi duyulabilir)' % (-arka_rel))
    if arka_tam > -40.0 and arka_tam - arka_rel > 6.0:
        bayrak.append('uğultu: kaynakta 150 Hz altı uğultu var; tam bant zemin yüksek bölümün %.0f dB altında (150 Hz üstünde %.0f dB altında). Çağrının kendi enerjisinin 100 Hz altındaki payı çok küçük (ölçülen: toplamın 27-41 dB altı); istenirse miks sırasında ~120 Hz yüksek geçiren süzgeçle temizlenebilir' % (-arka_tam, -arka_rel))
    notlar = [q['acik']] + q['not_ek']
    if q['tur'] == 'dogal':
        notlar.append('doğal bitiş: zarf eşiğin (%.0f dBFS, kaynakta) altına düştükten sonra 30 ms yumuşatma' % q['b']['esik_son'])
    sonuc[ad + '.wav'] = dict(
        hayvan=q['hayvan'], cagri_no=q['no'],
        kaynak_dosya='yeni/ses/alternatif/%s.mp3' % q['kaynak'],
        kirpma_sn=[round(q['bas'], 4), round(q['son'], 4)],
        kirpma_ornek=[int(q['s0']), int(q['s1'])],
        sure_sn=round(len(z) / SR, 3),
        tepe_dBFS=round(tp, 2),
        gercek_tepe_4x_dBTP=round(gtp, 2),
        rms_yuksek_bolum_dBFS=round(ham, 2),
        rms_yuksek_bolum_K_agirlikli_dB=round(kw, 2),
        anlik_maks_LUFS=round(am, 2),
        en_yuksek_200ms_K_agirlikli_dB=round(m200, 2),
        rms_telefon_bandi_300_8000Hz_dBFS=round(tb, 2),
        yuksek_bolum_suresi_sn=round(ybs, 3),
        kazanc_dB=round(g, 4),
        sonu_fade=bool(q['fade']),
        bitis_turu={'dogal': 'doğal bitiş', 'dogal*': 'doğal düşüş + %d ms kapanış' % (KAPANIS * 1000), 'fade': 'fade-out'}[q['tur']],
        fade_in_ms=int(FADE_IN * 1000), fade_out_ms=int(round(q['fo'] * 1000)),
        ses_baslangici_sn=round(onset, 3),
        vurgu_sn=round(vurgu, 3),
        ic_baslangiclar_sn=ib, ic_bitisler_sn=ibs,
        dogal_uzunluk_sn=round(q['b']['t_off'] - q['b']['t_on'], 3),
        arka_plan_150Hz_ustu_yuksek_bolume_gore_dB=round(arka_rel, 1),
        arka_plan_tam_bant_yuksek_bolume_gore_dB=round(arka_tam, 1),
        spektral=sp,
        bayraklar=bayrak,
        notlar=notlar)

# kisa patlamali seslerde (havlama) capraz olcu notu
med200 = float(np.median([r['en_yuksek_200ms_K_agirlikli_dB'] for r in sonuc.values()]))
for ad, r in sonuc.items():
    f = med200 - r['en_yuksek_200ms_K_agirlikli_dB']
    if f > 2.0:
        r['notlar'].append('kısa patlamalı ses: yüksek-bölüm RMS\'i diğerleriyle eşit, ama 200 ms pencerede en yüksek düzeyi ortancadan %.1f dB düşük (400 ms anlık düzeyde %.1f LUFS). Mikste zayıf kalırsa +1..+3 dB verilebilir; tepe payı %.1f dB' % (
            f, r['anlik_maks_LUFS'], -r['tepe_dBFS']))
    if r['sonu_fade']:
        r['notlar'].append('tam (kırpılmamış) doğal uzunluk için dosya %.2f sn olurdu; istenirse 03_kes.py içinde MAKS büyütülerek yeniden üretilebilir' % (r['dogal_uzunluk_sn'] + ON_PAY + YUMUSATMA))

cikti = dict(
    aciklama='Ali Baba\'nın Çiftliği - yeni3: her hayvan için 2 çağrı; her çağrı kendi ölçüsüne (~2.07 sn) oturur.',
    ornekleme_hz=SR, kanal=1, bicim='WAV PCM 16 bit mono',
    en_uzun_sure_sn=MAKS,
    islem='yalnız kırpma + sabit kazanç + fade (zaman/perde değişikliği, sıkıştırma, limitleme, filtre YOK)',
    duzey_esitleme=dict(
        olcu='yüksek bölüm = 50 ms RMS zarfında en yüksek değerin 10 dB altına kadar olan kareler; K-ağırlıklı (BS.1770 süzgeci) RMS eşitlendi',
        hedef_K_agirlikli_dB=round(HEDEF_KW, 2), tepe_siniri_dBFS=TEPE_HEDEF,
        tepe_olcusu='örnek tepesi ile 4x aşırı örneklenmiş (gerçek) tepenin büyüğü; en yüksek dosya tam sınırda, diğerleri altında'),
    alanlar=dict(
        kirpma_sn='kaynak dosyada [başlangıç, bitiş] saniye',
        kirpma_ornek='aynı aralık örnek numarası olarak (44100 Hz, mono indirgenmiş kaynak); çıktı = kaynak[örnekler] x 10^(kazanc_dB/20), yalnız baş/son fade farklı',
        ses_baslangici_sn='çıktı dosyasında sesin başladığı an (zarf tepe-25 dB eşiğini geçer); <= 0.020 olmalı',
        vurgu_sn='çıktı dosyasında zarfın tepenin 6 dB altına ilk ulaştığı an (yumuşak başlayan seslerde asıl vurgu buradadır)',
        ic_baslangiclar_sn='çağrı içindeki ayrı seslerin (vak/hav, hece) başlangıçları (tepe-20 dB)',
        sonu_fade='true = çağrı 1.85 sn sınırına sığmadığı için sonu fade-out ile kısaltıldı',
        bayraklar='basit spektral istatistiklerle işaretlenen olası hayvan-dışı içerik (kulakla doğrulanmadı)'),
    dosyalar=sonuc)
json.dump(cikti, open(os.path.join(OUT, 'sesler.json'), 'w'), ensure_ascii=False, indent=1)

print('\nSPEKTRAL ISTATISTIK / BAYRAKLAR')
print('%-8s %6s %7s %7s %7s %7s %7s %7s %7s | %s' % ('dosya', 'duzluk', 'agMrkHz', 'tepeHz', 'sabTon', 'gnsBnt', 'sessiz', 'arka>150', 'arkaTam', 'bayrak'))
for ad, r in sonuc.items():
    sp = r['spektral']
    print('%-8s %6.3f %7d %7d %7.2f %7.2f %7.2f %7.1f %7.1f | %s' % (
        ad[:-4], sp['duzluk_medyan'], sp['agirlik_merkezi_hz'], sp['baskin_tepe_medyan_hz'], sp['sabit_ton_en_uzun_sn'],
        sp['genisbant_gurultu_en_uzun_sn'], sp['sessizlik_en_uzun_sn'], r['arka_plan_150Hz_ustu_yuksek_bolume_gore_dB'], r['arka_plan_tam_bant_yuksek_bolume_gore_dB'],
        '; '.join(b.split(':')[0] for b in r['bayraklar']) or '-'))
print('\nyazildi:', os.path.join(OUT, 'sesler.json'))
