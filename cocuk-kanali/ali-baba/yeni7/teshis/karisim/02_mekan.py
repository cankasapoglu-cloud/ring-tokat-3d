#!/usr/bin/env python3
"""(2) Mekân / yankı: (a) vokal cümle sonlarından sonraki enerji düşüşü (kuyruk), (b) kör düşüş hızı dağılımı (serbest sönümler),
(c) şarkı sonundaki kuyruk, (d) vokalde tek tük yankı (kepstrum).
Aynı ölçüm: reddedilen vokal (zincir sonrası ve psola çıktısı), referans vokal (MDX), orkestralar, dört karışım.
Kullanım: python3 02_mekan.py"""
import numpy as np
from ortak import *
S = {}
HOP = 0.005
def zarf_db(x, sn=0.010):
    p = kayan_guc(x, sn); h = int(HOP * FS); return dbp(p[::h])                 # 5 ms adımlı, 10 ms pencereli güç zarfı (dB)

def cumle_sonlari(v, en_az_bosluk=0.6, etiket=""):
    """Cümle sonu: sesli bölüm bitiyor ve ardından en az `en_az_bosluk` sn sesli kare yok. Dönen: her son için kuyruk eğrisi."""
    sesli = sesli_maske(v); e = zarf_db(v); h = int(HOP * FS); n = len(e); sm = sesli[::h][:n]
    d = np.diff(sm.astype(int)); bit = np.where(d == -1)[0] + 1; bas = np.where(d == 1)[0] + 1
    sonuc = []; gurultu = np.percentile(e[e > -110], 5) if (e > -110).any() else -120
    for b in bit:
        sonraki = bas[bas > b]; bosluk = ((sonraki[0] if len(sonraki) else n) - b) * HOP
        if bosluk < en_az_bosluk: continue
        a = max(0, b - int(0.30 / HOP)); L0 = np.percentile(e[a:b], 90)        # cümlenin son 300 ms'sindeki düzey (P90)
        ust = np.where(e[a:b + int(0.2 / HOP)] >= L0 - 6)[0]
        if len(ust) == 0: continue
        t0 = a + ust[-1]                                                       # notanın bittiği an: zarfın L0-6 dB üstünde olduğu son kare
        m = int(min(bosluk + (b - t0) * HOP, 1.2) / HOP); egri = e[t0:t0 + m] - L0
        sonuc.append({"t0": t0 * HOP, "bosluk": bosluk, "L0": L0, "egri": egri})
    return sonuc, gurultu
def kuyruk_ozeti(sonlar):
    def at(o, ms):
        i = int(ms / 1000 / HOP); return o["egri"][i] if i < len(o["egri"]) else np.nan
    def sure(o, db_):
        alt = np.where(o["egri"] <= db_)[0]; return alt[0] * HOP * 1000 if len(alt) else np.nan     # ms; ulaşmadıysa nan
    def enerji(o, a, b):
        i, j = int(a / HOP), int(b / HOP); s = o["egri"][i:j]; return dbp(np.mean(10 ** (s / 10))) if len(s) > 2 else np.nan
    def rt(o):
        y = o["egri"]; i = np.where(y <= -8)[0]
        if len(i) == 0: return np.nan
        i0 = i[0]; j = np.where(y[i0:] <= -35)[0]; i1 = i0 + (j[0] if len(j) else len(y) - i0)
        if i1 - i0 < 8: return np.nan                                          # 40 ms'den kısa: ölçülemeyecek kadar hızlı
        t = np.arange(i1 - i0) * HOP; k = np.polyfit(t, y[i0:i1], 1)[0]; return -60 / k if k < 0 else np.nan
    o = {"cumle_sonu_sayisi": len(sonlar)}
    for ms in (50, 100, 150, 200, 300, 450, 600): o[f"duzey_{ms}ms_db_ortanca"] = R(np.nanmedian([at(x, ms) for x in sonlar]), 1)
    for d in (-20, -30, -40):
        s = np.array([sure(x, d) for x in sonlar]); o[f"{d}dB_e_inis_ms_ortanca"] = R(np.nanmedian(s), 0); o[f"{d}dB_e_inis_ms_ceyrekler"] = [R(np.nanpercentile(s, 25), 0), R(np.nanpercentile(s, 75), 0)]
    o["kuyruk_enerjisi_60_600ms_db_ortanca(nota duzeyine gore)"] = R(np.nanmedian([enerji(x, 0.06, 0.6) for x in sonlar]), 1)
    o["kuyruk_enerjisi_150_600ms_db_ortanca"] = R(np.nanmedian([enerji(x, 0.15, 0.6) for x in sonlar]), 1)
    r = np.array([rt(x) for x in sonlar]); o["rt60_dogrusal_uyum_sn_ortanca(-8..-35 dB)"] = R(np.nanmedian(r)) if np.isfinite(r).any() else None
    o["rt60_olculebilen_son_sayisi"] = int(np.isfinite(r).sum())
    return o

def kor_dusus(x, a=500, b=4000, pencere=0.15, en_az_dusus=10.0):
    """Serbest sönümlerin dağılımı: bant içi 10 ms zarfın 150 ms boyunca doğrusala yakın (R2 >= 0.95) düştüğü her yer.
    Kuru kayıtta en hızlı sönümler çok kısadır; yankılı kayıtta en hızlı sönüm odanın sönümüyle sınırlanır."""
    e = zarf_db(bant(x, a, b)); w = int(pencere / HOP); n = len(e) - w
    if n <= 0: return {}
    t = np.arange(w) * HOP; tm = t.mean(); tv = ((t - tm) ** 2).sum()
    Y = np.lib.stride_tricks.sliding_window_view(e, w)[:n]; ym = Y.mean(axis=1); k = ((Y - ym[:, None]) * (t - tm)).sum(axis=1) / tv
    ss_res = ((Y - ym[:, None] - k[:, None] * (t - tm)) ** 2).sum(axis=1); ss_tot = ((Y - ym[:, None]) ** 2).sum(axis=1) + 1e-12; r2 = 1 - ss_res / ss_tot
    ust = np.percentile(e[e > -100], 95); ok = (r2 >= 0.95) & (k < 0) & (-k * pencere >= en_az_dusus) & (Y[:, 0] > ust - 20) & (Y[:, -1] > -85)
    # örtüşen pencereleri tek sönüm say: ardışık kabul edilenlerin en dik olanı
    idx = np.where(ok)[0]; T = []
    if len(idx):
        grup = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1); T = [60 / -k[g].min() for g in grup]
    T = np.array(T); sure_dk = len(x) / FS / 60
    return {"sonum_sayisi": int(len(T)), "dakikada": R(len(T) / sure_dk, 1), "t60_p10_sn": R(np.percentile(T, 10)) if len(T) else None, "t60_p25_sn": R(np.percentile(T, 25)) if len(T) else None,
            "t60_ortanca_sn": R(np.median(T)) if len(T) else None, "t60_lt_0.25sn_dakikada": R((T < 0.25).sum() / sure_dk, 1), "t60_lt_0.4sn_orani_yuzde": R(100 * (T < 0.4).mean(), 1) if len(T) else None}

def kepstrum_yanki(x, m=None):
    """Gerçek kepstrum ortalaması; 12-150 ms arasında tek tük yankı (tarak süzgeci) doruğu arar."""
    y = x.mean(axis=1); N = 16384; h = N // 2; w = np.hanning(N); C = np.zeros(N); say = 0
    for i in range(0, len(y) - N, h):
        s = y[i:i + N]
        if m is not None and m[i:i + N].mean() < 0.7: continue
        sp = np.abs(np.fft.fft(s * w)) + 1e-9; C += np.real(np.fft.ifft(np.log(sp))); say += 1
    if say == 0: return {}
    C /= say; q = np.arange(N) / FS; al = (q >= 0.012) & (q <= 0.150); c = C[al]; i = np.argmax(c)
    return {"pencere_sayisi": say, "en_yuksek_doruk_ms": R(q[al][i] * 1000, 1), "doruk_degeri": R(c[i], 4), "doruk_bolu_olcut_sapma": R(c[i] / (np.std(c) + 1e-12), 1)}

# ---- (a) vokal cümle sonu kuyrukları ----------------------------------------------------------------------------------
for ad in ("red_vokal", "red_vokal_yankisiz", "red_vokal_ham", "ref_vokal"):
    v = yukle(ad); sonlar, gur = cumle_sonlari(v, 0.6); o = kuyruk_ozeti(sonlar); o["zarf_taban_db"] = R(gur, 1)
    o["sonlar_sn"] = [R(x["t0"], 2) for x in sonlar][:30]
    sonlar2, _ = cumle_sonlari(v, 0.25); o["bosluk_0.25sn_ile"] = {k: kuyruk_ozeti(sonlar2)[k] for k in ("cumle_sonu_sayisi", "duzey_100ms_db_ortanca", "duzey_200ms_db_ortanca", "-20dB_e_inis_ms_ortanca", "-30dB_e_inis_ms_ortanca")}
    S["kuyruk_" + ad] = o
# referansta, aynı cümle sonlarında KARIŞIMDAKİ (vokal + çalgı) düşüş: dinleyicinin duyduğu
# ---- (b) kör düşüş hızı ----------------------------------------------------------------------------------------------
for ad in ("red_vokal", "ref_vokal", "red_altyapi", "ref_altyapi", "red_hayvan", "red_karisim", "ref_karisim", "onay_el_yikama", "onay_parmak"):
    x = yukle(ad); S["kor_" + ad] = {"500-4000Hz": kor_dusus(x, 500, 4000), "2000-8000Hz": kor_dusus(x, 2000, 8000), "150-500Hz": kor_dusus(x, 150, 500)}
# ---- (c) şarkı sonu kuyruğu -------------------------------------------------------------------------------------------
for ad in ("red_altyapi", "red_karisim", "ref_altyapi", "ref_karisim", "onay_el_yikama", "onay_parmak"):
    x = yukle(ad); e = zarf_db(x, 0.05); son = np.where(e > e.max() - 60)[0][-1]; dort = e[max(0, son - int(4 / HOP)):son + 1:int(0.25 / HOP)]
    S["son_" + ad] = {"dosya_sn": R(len(x) / FS), "son_duyulur_an_sn(-60 dB)": R(son * HOP), "son_4_sn_zarf_db_0.25sn_adim(en yuksege gore)": [R(v - e.max(), 1) for v in dort]}
# ---- (d) tek tük yankı -----------------------------------------------------------------------------------------------
for ad in ("red_vokal", "red_vokal_yankisiz", "ref_vokal"):
    v = yukle(ad); S["kepstrum_" + ad] = kepstrum_yanki(v, sesli_maske(v))
yaz("02_mekan", S); print(json.dumps(S, ensure_ascii=False, indent=1))
