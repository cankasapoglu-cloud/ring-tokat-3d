#!/usr/bin/env python3
"""4. adim: kesim.json'un BAGIMSIZ dogrulamasi - dogrudan ham WAV orneklerinden (ozellik.npz, pyworld, zarf.py kullanilmaz).
Cikti: dogrulama.txt (bu betigin ciktisi) + ornek/*.wav (onerilen kesimlerin uygulanmis hali; KULAKLA DINLENMEDI).
Hata bulunursa cikis kodu 1."""
import os, sys, json, numpy as np, soundfile as sf
from scipy.signal import stft, butter, sosfiltfilt

K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.dirname(os.path.dirname(os.path.dirname(K)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import kucuk, UNLU, BEKLENEN_HECE, L1, L2, DIYE, L4, SAKLANAN, kelimeleri_oku, kitalari_esle, BEAT, BAR

d = json.load(open(os.path.join(K, "kesim.json"), encoding="utf8"))
x, fs = sf.read(os.path.join(A, d["source"]["vocal"]))
if x.ndim > 1:
    x = x.mean(axis=1)
SUNG = d["levels"]["sung_rms_dbfs"]
satirlar = []; hata = []


def yaz(*a):
    s = " ".join(str(q) for q in a); print(s); satirlar.append(s)


def kontrol(kosul, mesaj):
    if not kosul:
        hata.append(mesaj); yaz("  !! HATA:", mesaj)


def db(a, b):
    seg = x[max(0, int(round(a * fs))):int(round(b * fs))]
    return float(10 * np.log10(np.mean(seg ** 2) + 1e-20)) if len(seg) else -200.0


def tepe(a, b):
    seg = x[max(0, int(round(a * fs))):int(round(b * fs))]
    return float(20 * np.log10(np.abs(seg).max() + 1e-12)) if len(seg) else -200.0


def otokor(a, b, fmin=150.0, fmax=700.0):
    """[a,b] icin temel frekans (Hz) ve normallestirilmis otokorelasyon tepesi - pyworld'den bagimsiz."""
    seg = x[int(round(a * fs)):int(round(b * fs))].copy()
    if len(seg) < int(fs / fmin) * 2:
        return None, 0.0
    seg -= seg.mean(); seg *= np.hanning(len(seg))
    n = len(seg); F = np.fft.rfft(seg, 2 * n); ac = np.fft.irfft(np.abs(F) ** 2)[:n]
    if ac[0] <= 0:
        return None, 0.0
    w = np.hanning(2 * n)[n:]; wc = np.correlate(np.hanning(n), np.hanning(n), "full")[n - 1:]
    ac = ac / (wc + 1e-9) * wc[0] / ac[0]
    lo, hi = int(fs / fmax), min(n - 2, int(fs / fmin))
    k = lo + int(np.argmax(ac[lo:hi]))
    y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
    kk = k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-12)
    return fs / kk, float(y1)


midi = lambda f: 69 + 12 * np.log2(f / 440.0)
# 300-3400 Hz zarfi (bagimsiz: Butterworth + 12 ms kare ortalama)
sos = butter(4, [300, 3400], btype="band", fs=fs, output="sos"); xm = sosfiltfilt(sos, x)
cm = np.concatenate([[0.0], np.cumsum(xm ** 2)])


def mid_db(a, b):
    i0, i1 = max(0, int(round(a * fs))), int(round(b * fs))
    return float(10 * np.log10((cm[i1] - cm[i0]) / max(1, i1 - i0) + 1e-20))


def mid_tepe(a, b, w=0.012):
    """[a,b] icinde 12 ms'lik pencerelerin en yuksek 300-3400 Hz duzeyi"""
    n = int(w * fs); i0, i1 = int(round(a * fs)), int(round(b * fs))
    if i1 - i0 <= n:
        return mid_db(a, b)
    v = (cm[i0 + n:i1:64] - cm[i0:i1 - n:64]) / n
    return float(10 * np.log10(v.max() + 1e-20))


def logspek(a, b):
    seg = x[int(round(a * fs)):int(round(b * fs))]
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 4096)) ** 2
    f = np.fft.rfftfreq(4096, 1 / fs)
    kn = np.array([200, 400, 600, 800, 1000, 1300, 1600, 2000, 2500, 3200, 4000])
    return np.array([10 * np.log10(S[(f >= lo) & (f < hi)].sum() + 1e-20) for lo, hi in zip(kn[:-1], kn[1:])])


V = d["verses"]
# ---------------------------------------------------------------- 1) yapi
yaz("== 1) YAPI ==")
kontrol(len(V) == 7, "7 kita degil")
nh = nk = nseg = natilan = 0
for v, kt in enumerate(V):
    kontrol([l_["name"] for l_ in kt["lines"]] == SAKLANAN, "K%d: dizeler %s" % (v + 1, [l_["name"] for l_ in kt["lines"]]))
    kontrol(list(kt["segments"].keys()) == ["L1", "L2", "ses", "diye", "L4"], "K%d: bolumler" % (v + 1))
    kontrol(len(kt["pieces"]) == 3 and [p["segments"] for p in kt["pieces"]] == [["L1"], ["L2"], ["diye", "L4"]], "K%d: parcalar" % (v + 1))
    kontrol(kt["segments"]["ses"]["keep"] is False and all(kt["segments"][a_]["keep"] for a_ in SAKLANAN), "K%d: keep isaretleri" % (v + 1))
    for ln in kt["lines"]:
        ad = ln["name"]; nseg += 1
        bek = {"L1": L1, "L2": L2[v], "diye": DIYE, "L4": L4}[ad]
        kontrol(ln["text"] == bek, "K%d %s metin" % (v + 1, ad))
        b = BEKLENEN_HECE[ad]; b = b if isinstance(b, str) else b[v]
        bh = [kucuk(h) for w_ in b.split() for h in w_.split("-")]
        gh = [kucuk(s_["text"]) for s_ in ln["syllables"] if s_["kept"]]
        kontrol(bh == gh, "K%d %s hece dizisi %s != %s" % (v + 1, ad, gh, bh))
        for s_ in ln["syllables"]:
            if s_["kept"]:
                kontrol(sum(c in UNLU for c in kucuk(s_["text"])) == 1, "tek unlu degil: " + s_["text"])
                kontrol(s_["f0_midi"] is not None and s_["voiced_ratio"] * s_["duration"] >= 0.04,
                        "K%d %s %s: perde yok / sesli sure %.0f ms" % (v + 1, ad, s_["text"], s_["voiced_ratio"] * s_["duration"] * 1000))
            else:
                natilan += 1
        nh += sum(1 for s_ in ln["syllables"] if s_["kept"]); nk += len(ln["words"])
yaz("kita %d, saklanan bolum %d (7 x 4), parca %d, kelime %d, saklanan hece %d, atilacak cekirdek %d" % (len(V), nseg, sum(len(k_["pieces"]) for k_ in V), nk, nh, natilan))
kontrol(nseg == 28 and nh == 229 and nk == 91 and natilan == 1, "sayim: %d bolum, %d hece, %d kelime, %d atilan" % (nseg, nh, nk, natilan))

# ---------------------------------------------------------------- 2) zaman tutarliligi
yaz("\n== 2) ZAMAN TUTARLILIGI ==")
enkisa = (9, None); onceki = 0.0
for v, kt in enumerate(V):
    sg = kt["segments"]; P = kt["pieces"]
    sira = [sg["L1"]["start"], sg["L1"]["end"], sg["L2"]["start"], sg["L2"]["end"], sg["ses"]["start"], sg["ses"]["end"],
            sg["diye"]["start"], sg["diye"]["end"], sg["L4"]["start"], sg["L4"]["end"]]
    kontrol(all(b_ >= a_ - 1e-6 for a_, b_ in zip(sira[:-1], sira[1:])) and sira[0] > onceki, "K%d bolum sirasi %s" % (v + 1, sira))
    onceki = sira[-1]
    for p in P:
        kontrol(p["cut_in"] < p["start"] <= p["end"] <= p["cut_out"] + 1e-6, "K%d parca %d: cut_in < start <= end <= cut_out degil" % (v + 1, p["piece"]))
        kontrol(p["cut_in"] + p["fade_in_ms"] / 1000 <= p["start"] + 1e-6, "K%d parca %d: giris sonumlemesi baslangici asiyor" % (v + 1, p["piece"]))
        kontrol(3 <= p["fade_in_ms"] <= 30 and 5 <= p["fade_out_ms"] <= 60, "K%d parca %d: sonumleme sureleri" % (v + 1, p["piece"]))
    kontrol(P[0]["cut_out"] <= P[1]["cut_in"] + 1e-6, "K%d: parca 1 ve 2 ust uste" % (v + 1))
    kontrol(P[1]["cut_out"] <= sg["ses"]["first_vowel_onset"] - 0.03, "K%d: parca 2 hayvan sesinin unlusune 30 ms'den yakin" % (v + 1))
    kontrol(P[2]["cut_in"] >= sg["ses"]["body_end"], "K%d: parca 3 hayvan sesinin govdesinden once basliyor" % (v + 1))
    kontrol(5 <= P[1]["fade_out_ms"] <= 30, "K%d: L2 cikis sonumlemesi 5-30 ms disinda" % (v + 1))
    for ln in kt["lines"]:
        S = ln["syllables"]
        kontrol(abs(S[0]["start"] - ln["start"]) < 1e-3 and abs(S[-1]["end"] - ln["end"]) < 1e-3, "K%d %s hece-dize ucu" % (v + 1, ln["name"]))
        for a_, b_ in zip(S[:-1], S[1:]):
            kontrol(abs(a_["end"] - b_["start"]) < 1e-3, "K%d %s bosluk/cakisma %s|%s" % (v + 1, ln["name"], a_["text"], b_["text"]))
        for s_ in S:
            sure = s_["end"] - s_["start"]
            kontrol(sure >= 0.06, "K%d %s %s cok kisa (%.0f ms)" % (v + 1, ln["name"], s_["text"], sure * 1000))
            kontrol(s_["start"] - 0.002 <= s_["nucleus"] <= s_["end"] + 0.002, "cekirdek hece disinda: K%d %s %s" % (v + 1, ln["name"], s_["text"]))
            for n_ in s_["notes"]:
                kontrol(s_["start"] - 1e-3 <= n_["start"] < n_["end"] <= s_["end"] + 1e-3, "nota hece disinda: K%d %s %s" % (v + 1, ln["name"], s_["text"]))
            kontrol(abs(sum(n_["end"] - n_["start"] for n_ in s_["notes"]) - sure) < 2e-3, "notalar heceyi bolmuyor: K%d %s %s" % (v + 1, ln["name"], s_["text"]))
            if s_["kept"] and sure < enkisa[0]:
                enkisa = (sure, "K%d %s %s" % (v + 1, ln["name"], s_["text"]))
        for wi, w_ in enumerate(ln["words"]):
            ws = [s_ for s_ in S if s_["word_index"] == wi]
            kontrol(abs(ws[0]["start"] - w_["start"]) < 1e-3 and abs(ws[-1]["end"] - w_["end"]) < 1e-3, "kelime-hece ucu " + w_["text"])
    # diye + L4 kesintisiz
    kontrol(abs(kt["lines"][2]["end"] - kt["lines"][3]["start"]) < 1e-3, "K%d: diye / L4 hece tablosu bitisik degil" % (v + 1))
yaz("en kisa saklanan hece: %.0f ms (%s)" % (enkisa[0] * 1000, enkisa[1]))
# kelime baslangiclari yazi dokumuyle karsilastir (20 ms izgara)
sap = []
for v, kt in enumerate(V):
    for ln in kt["lines"]:
        for w_ in ln["words"]:
            sap.append((w_["start"] - w_["json_start"], "K%d %s %s" % (v + 1, ln["name"], w_["text"])))
ss = np.array([s_[0] for s_ in sap]) * 1000
yaz("kelime baslangici - yazi dokumu: ortanca %+.0f ms, %%5-%%95 [%+.0f, %+.0f] ms, en buyuk |sapma| %.0f ms (%s)" % (
    np.median(ss), np.percentile(ss, 5), np.percentile(ss, 95), np.abs(ss).max(), sap[int(np.argmax(np.abs(ss)))][1]))
kontrol(np.abs(ss).max() < 150, "kelime baslangici yazi dokumunden 150 ms'den fazla sapiyor")

# ---------------------------------------------------------------- 3) kesim noktalari
yaz("\n== 3) KESIM NOKTALARI: +-3 ms RMS (dBFS), ham WAV ==")
for v, kt in enumerate(V):
    P = kt["pieces"]; r = "K%d " % (v + 1)
    lv = {}
    for p in P:
        lv[p["piece"]] = (db(p["cut_in"] - 0.003, p["cut_in"] + 0.003), db(p["cut_out"] - 0.003, p["cut_out"] + 0.003))
    hc = kt["hard_cuts"]
    yaz("K%d  L1: giris %.3f (%.0f dB) cikis %.3f (%.0f dB) | L2: giris %.3f (%.0f dB) cikis %.3f [%s, sonumleme %.0f ms, bosluk %.0f ms] | diye+L4: giris %.3f (%.0f dB, bosluk %.0f ms) cikis %.3f (%.0f dB)" % (
        v + 1, P[0]["cut_in"], lv[1][0], P[0]["cut_out"], lv[1][1], P[1]["cut_in"], lv[2][0], P[1]["cut_out"], hc["L2_end"]["what_follows"],
        P[1]["fade_out_ms"], hc["L2_end"]["gap_ms"], P[2]["cut_in"], lv[3][0], hc["diye_start"]["gap_ms"], P[2]["cut_out"], lv[3][1]))
    kontrol(lv[1][0] < SUNG - 20, "K%d L1 giris kesimi sessiz degil (%.0f dB)" % (v + 1, lv[1][0]))
    kontrol(lv[1][1] < SUNG - 10 and lv[2][0] < SUNG - 10, "K%d L1 cikis / L2 giris kesimi cukurda degil" % (v + 1))
    kontrol(lv[3][0] < SUNG - 12, "K%d diye giris kesimi cukurda degil (%.0f dB)" % (v + 1, lv[3][0]))
    kontrol(lv[3][1] < SUNG - 22, "K%d L4 cikis kesimi sessiz degil (%.0f dB)" % (v + 1, lv[3][1]))


def kos_cikis(n):
    return np.cos(np.linspace(0, np.pi / 2, n, endpoint=False)) ** 2


def parca_uygula(p):
    """Onerilen kesim ve sonumlemeler uygulanmis parca (ham WAV'dan)."""
    i0, i1 = int(round(p["cut_in"] * fs)), int(round(p["cut_out"] * fs))
    y = x[i0:i1].copy()
    nf = int(round(p["fade_in_ms"] / 1000 * fs)); y[:nf] *= 1 - kos_cikis(nf)
    nf = int(round(p["fade_out_ms"] / 1000 * fs)); y[-nf:] *= kos_cikis(nf)
    return y


yaz("\n== 4) HAYVAN SESI GERCEKTEN GIDIYOR MU (onerilen kesimler uygulaninca) ==")
os.makedirs(os.path.join(K, "ornek"), exist_ok=True)
for v, kt in enumerate(V):
    P = kt["pieces"]; sg = kt["segments"]; hc = kt["hard_cuts"]
    y2 = parca_uygula(P[1]); y3 = parca_uygula(P[2])
    # parca 2'nin son 30 ms'si ve parca 3'un ilk 30 ms'si: hayvan sesinden kalan
    ve = hc["L2_end"]["var_end"]
    n_art = max(0, int(round((P[1]["cut_out"] - ve) * fs)))
    art2 = y2[len(y2) - n_art:] if n_art > 0 else np.zeros(1)
    a2 = 10 * np.log10(np.mean(art2 ** 2) + 1e-20) if n_art > 0 else -200.0
    on = hc["diye_start"]["diye_onset"]
    n_on = int(round((on - P[2]["cut_in"]) * fs))
    art3 = y3[:n_on]
    a3 = 10 * np.log10(np.mean(art3 ** 2) + 1e-20)
    # atilan bolgenin (var_end .. diye cut_in) ham enerjisi
    ham = db(ve, P[2]["cut_in"])
    yaz("K%d  atilan hayvan sesi %.3f-%.3f (%.0f ms, ham RMS %.1f dBFS) | L2'de var_end'den sonra kalan: %s | diye onunde kalan (%.0f ms): RMS %.1f dBFS = soylenen %+.1f dB, tepe %.1f dBFS" % (
        v + 1, ve, P[2]["cut_in"], (P[2]["cut_in"] - ve) * 1000, ham,
        "yok" if n_art == 0 else "%.0f ms, RMS %.1f dBFS (soylenen %+.1f dB) [duraklama: 'var'in kendi sonmesi]" % (n_art / fs * 1000, a2, a2 - SUNG),
        n_on / fs * 1000, a3, a3 - SUNG, 20 * np.log10(np.abs(art3).max() + 1e-12)))
    if hc["L2_end"]["what_follows"] != "pause":
        kontrol(n_art == 0, "K%d: L2 kesimi var_end'den sonra ornek birakiyor" % (v + 1))
    else:
        kontrol(a2 < SUNG - 12, "K%d: duraklamada kalan artik yuksek (%.1f dBFS)" % (v + 1, a2))
        kontrol(P[1]["cut_out"] <= hc["L2_end"]["animal_sound_start"] - 0.01, "K%d: L2 kesimi hayvan sesinin basina 10 ms'den yakin" % (v + 1))
    kontrol(a3 < SUNG - 12, "K%d: diye onunde kalan artik yuksek (%.1f dBFS)" % (v + 1, a3))
# ornek dosyalar (dinlenmedi)
bos = np.zeros(int(0.4 * fs))
sf.write(os.path.join(K, "ornek", "L2_sonlari_7_kita.wav"), np.concatenate([np.concatenate([parca_uygula(kt["pieces"][1])[-int(1.2 * fs):], bos]) for kt in V]), fs, subtype="PCM_16")
sf.write(os.path.join(K, "ornek", "diye_baslari_7_kita.wav"), np.concatenate([np.concatenate([parca_uygula(kt["pieces"][2])[:int(1.5 * fs)], bos]) for kt in V]), fs, subtype="PCM_16")
yaz("ornek/: L2_sonlari_7_kita.wav (her kitanin L2 parcasinin son 1.2 s'si), diye_baslari_7_kita.wav (3. parcanin ilk 1.5 s'si): onerilen kesim + sonumleme uygulanmis, 16 bit; DINLENMEDI")

# ---------------------------------------------------------------- 5) hece sinirlari unlunun ortasinda mi
yaz("\n== 5) HECE SINIRLARI: UNLU ORTASINDA SINIR VAR MI (ham WAV, bagimsiz olcum) ==")
say = {"sessiz_ya_da_kapanis": 0, "sesli_cukur": 0, "spektral_gecis": 0, "perde_adimi": 0, "izgara_FLAG": 0, "ek_yeri": 0}
ihlal = []; cukur_der = []; izg_list = []
for v, kt in enumerate(V):
    for ln in kt["lines"]:
        S = ln["syllables"]
        for a_, b_ in zip(S[:-1], S[1:]):
            eb = a_["end_boundary"]; tt = eb["t"]
            kind = eb["kind"]
            if kind == "splice" or not a_["kept"] or not b_["kept"]:
                say["ek_yeri"] += 1
                continue
            sv = mid_db(tt - 0.006, tt + 0.006)
            pL = mid_tepe(a_["start"], tt - 0.006); pR = mid_tepe(tt + 0.006, b_["end"])
            der = min(pL, pR) - sv
            f0, r = otokor(tt - 0.02, tt + 0.02)
            tam = db(tt - 0.005, tt + 0.005)
            sesli = r >= 0.5 and tam > SUNG - 20.0
            if kind == "grid":
                say["izgara_FLAG"] += 1; izg_list.append("K%d %s %s|%s" % (v + 1, ln["name"], a_["text"], b_["text"]))
                continue
            if not sesli:
                say["sessiz_ya_da_kapanis"] += 1
                continue
            if der >= 3.0:
                say["sesli_cukur"] += 1; cukur_der.append(der)
                continue
            # sesli ve cukur yok: spektral gecis ya da perde adimi olmali
            sa = logspek(tt - 0.05, tt - 0.008); sb = logspek(tt + 0.008, tt + 0.05)
            sa -= sa.mean(); sb -= sb.mean()
            sd_ = float(np.sqrt(np.mean((sa - sb) ** 2)))
            fa, ra = otokor(max(a_["start"], tt - 0.07), tt - 0.01); fb, rb = otokor(tt + 0.01, min(b_["end"], tt + 0.07))
            pd_ = abs(midi(fa) - midi(fb)) if fa and fb else 0.0
            if pd_ >= 0.6:
                say["perde_adimi"] += 1
            elif sd_ >= 3.0:
                say["spektral_gecis"] += 1
            else:
                ihlal.append("K%d %s %s|%s t=%.3f tur=%s cukur=%.1f dB spektral=%.1f dB perde=%.2f" % (v + 1, ln["name"], a_["text"], b_["text"], tt, kind, der, sd_, pd_))
yaz("sinir sayisi (dize ici):", sum(say.values()), "->", say)
yaz("sesli cukurlarin derinligi (300-3400 Hz, dB): ortanca %.1f, en sig %.1f" % (np.median(cukur_der), np.min(cukur_der)))
yaz("izgaraya konan (FLAG) sinirlar:", ", ".join(izg_list))
for i_ in ihlal:
    yaz("   unlu ortasi olabilir:", i_)
kontrol(len(ihlal) == 0, "%d sinir unlunun ortasinda olabilir (cukur yok, spektral gecis yok, perde adimi yok)" % len(ihlal))
kontrol(say["izgara_FLAG"] == d["summary"]["boundary_kinds"].get("grid/expected_onset_on_beat_grid", 0), "izgara sinir sayisi ozetle uyusmuyor")

# ---------------------------------------------------------------- 6) perde (bagimsiz otokorelasyon)
yaz("\n== 6) PERDE: hece cekirdegi, pyworld (json) ile bagimsiz otokorelasyon ==")
fark = []
for v, kt in enumerate(V):
    for ln in kt["lines"]:
        for s_ in ln["syllables"]:
            a_, b_ = s_["core_start"], s_["core_end"]
            if b_ - a_ < 0.03:
                continue
            m0 = (a_ + b_) / 2
            f0, r = otokor(max(a_, m0 - 0.03), min(b_, m0 + 0.03))
            if f0 and r > 0.5 and s_["pitch_mid_midi"] is not None:
                fark.append((midi(f0) - s_["pitch_mid_midi"], "K%d %s %s" % (v + 1, ln["name"], s_["text"]), s_["f0_midi"], s_.get("f0_dio_midi")))
ff = np.array([f_[0] for f_ in fark])
yaz("karsilastirilan hece %d; fark (yarim ses): ortanca %+.3f, |fark| ortanca %.3f, %%95 %.2f, en buyuk %.2f (%s); |fark| > 0.5: %d" % (
    len(ff), np.median(ff), np.median(np.abs(ff)), np.percentile(np.abs(ff), 95), np.abs(ff).max(), fark[int(np.argmax(np.abs(ff)))][1], int((np.abs(ff) > 0.5).sum())))
for f_ in fark:
    if abs(f_[0]) > 0.5:
        okt = abs(abs(f_[0]) - 12) < 0.3
        yaz("   fark %+.2f: %s | json (harvest) %.2f, dio %s%s" % (f_[0], f_[1], f_[2], f_[3],
            " -> basit otokorelasyonun oktav hatasi (harvest ve dio ayni perdeyi veriyor)" if okt and f_[3] is not None and abs(f_[3] - f_[2]) < 0.3 else ""))
kontrol(np.median(np.abs(ff)) < 0.1 and (np.abs(ff) > 0.5).sum() <= 5, "perde olcumleri bagimsiz yontemle uyusmuyor")
dd = np.array([(s_["f0_dio_midi"] - s_["f0_midi"]) for kt in V for ln in kt["lines"] for s_ in ln["syllables"] if s_.get("f0_dio_midi") is not None])
yaz("harvest - dio(stonemask) cekirdek ortancasi farki: |fark| ortanca %.3f, en buyuk %.2f yarim ses; > 0.3: %d / %d" % (np.median(np.abs(dd)), np.abs(dd).max(), int((np.abs(dd) > 0.3).sum()), len(dd)))
nt = d["notes_table"]
for ad in SAKLANAN + ["overall"]:
    sh = nt["pitch_class_histogram_stable_notes"][ad]["share"]
    kontrol(abs(sum(sh.values()) - 1) < 0.01, "perde sinifi paylari 1 etmiyor: " + ad)
    yaz("%-7s %5.1f s  " % (ad, nt["pitch_class_histogram_stable_notes"][ad]["total_seconds"]) + "  ".join("%s %.1f%%" % (k_, 100 * v_) for k_, v_ in sh.items() if v_ >= 0.005))
for ad in SAKLANAN:
    yaz("%-5s: %s" % (ad, nt["consensus_text"][ad]))
yaz("akort (plato karelerinin ortanca sapmasi): %+.1f cent" % nt["tuning_cents_re_A440_median_of_plateau_frames"])
yaz("perde sapanlari:", "; ".join("K%d %s %s %s (%+.2f)" % (s_["verse"], s_["line"], s_["syllable"], s_["note"], s_["deviation_semitones"]) for s_ in nt["pitch_outliers"]))

# ---------------------------------------------------------------- 7) atları
yaz("\n== 7) 3. KITA 'atları' ==")
ac = d["atlari_check"]; ex = ac["excision"]; lm = ac["landmarks"]
yaz(ac["verdict"])
# bagimsiz: t salinimindan sonra 'la'nin a'sina kadar sesli ve guclu sure (20 ms pencereler)
tt = np.arange(lm["t_burst_onset"], lm["second_a_onset"], 0.005)
ses = []
for q in tt:
    f0, r = otokor(q - 0.015, q + 0.015)
    ses.append(r >= 0.6 and db(q - 0.01, q + 0.01) > SUNG - 8.0)
ses = np.array(ses)
sure = float(ses.sum() * 5)
yaz("t patlamasi (%.3f) ile 'la'nin a'si (%.3f) arasinda sesli ve guclu (> soylenen - 8 dB) sure: %.0f ms (json: %.0f ms; diger unsuz+l+unlu: en cok %.0f ms)" % (
    lm["t_burst_onset"], lm["second_a_onset"], sure, lm["voiced_stretch_before_second_a_ms"], ac["duration_comparison_consonant_l_vowel"]["max_ms"]))
kontrol(sure >= 150, "atlari: ek cekirdek icin beklenen uzun sesli bolum bulunamadi")
yaz("kesip atma %.4f - %.4f (%.0f ms): bastaki an +-2 ms RMS %.1f dBFS, tepe %.1f dBFS | sondaki an +-2 ms RMS %.1f dBFS (sesli l'nin icinde: 10 ms giris sonumlemesi gerekir)" % (
    ex["start"], ex["end"], ex["removed_ms"], db(ex["start"] - 0.002, ex["start"] + 0.002), tepe(ex["start"] - 0.002, ex["start"] + 0.002),
    db(ex["end"] - 0.002, ex["end"] + 0.002)))
kontrol(db(ex["start"] - 0.002, ex["start"] + 0.002) < SUNG - 15, "atlari: kesim basi sessiz degil")
s3 = [s_ for s_ in V[2]["lines"][1]["syllables"] if s_["word"] == "atları"]
kontrol([s_["text"] for s_ in s3] == ["at", "(tı)", "la", "rı"] and s3[1]["excise"] and abs(s3[1]["start"] - ex["start"]) < 1e-3 and abs(s3[1]["end"] - ex["end"]) < 1e-3,
        "atlari: hece tablosu ile kesip atma araligi uyusmuyor")
f_la, r_la = otokor(ex["end"], ex["end"] + 0.04)
yaz("kalan parcalar: 'at' %.3f-%.3f (%.0f ms), 'ları' %.3f-%.3f (%.0f ms); 'ları'nin ilk 40 ms'sinde perde %.2f (otokor %.2f)" % (
    s3[0]["start"], s3[0]["end"], s3[0]["duration"] * 1000, s3[2]["start"], s3[3]["end"], (s3[3]["end"] - s3[2]["start"]) * 1000, midi(f_la), r_la))
# onarilmis L2 (secenek A: bosluk birakilir) ve ham hali
p2 = V[2]["pieces"][1]
i0, i1 = int(round(p2["cut_in"] * fs)), int(round(p2["cut_out"] * fs))
y = x[i0:i1].copy()
nf = int(round(p2["fade_in_ms"] / 1000 * fs)); y[:nf] *= 1 - kos_cikis(nf)
nf = int(round(p2["fade_out_ms"] / 1000 * fs)); y[-nf:] *= kos_cikis(nf)
ham3 = y.copy()
e0, e1 = int(round(ex["start"] * fs)) - i0, int(round(ex["end"] * fs)) - i0
n5 = int(0.005 * fs); n10 = int(0.010 * fs)
y[e0 - n5:e0] *= kos_cikis(n5); y[e0:e1] = 0.0; y[e1:e1 + n10] *= 1 - kos_cikis(n10)
kap = np.concatenate([y[:e0], y[e1:]])
sf.write(os.path.join(K, "ornek", "K3_L2_ham.wav"), ham3, fs, subtype="PCM_16")
sf.write(os.path.join(K, "ornek", "K3_L2_onarilmis_A_bosluklu.wav"), y, fs, subtype="PCM_16")
sf.write(os.path.join(K, "ornek", "K3_L2_onarilmis_B_bosluk_kapatilmis.wav"), kap, fs, subtype="PCM_16")
yaz("ornek/: K3_L2_ham.wav, K3_L2_onarilmis_A_bosluklu.wav (onerilen; zamanlama ayni), K3_L2_onarilmis_B_bosluk_kapatilmis.wav (%.0f ms kisa; onerilmez) -- DINLENMEDI" % ex["removed_ms"])
yaz("diger kelimelerde fazla hece: %s | eksik hece: %s" % (
    [(w_["verse"], w_["word"]) for w_ in d["syllable_scan"]["words_with_extra_syllable"]], d["syllable_scan"]["words_with_missing_syllable"]))
kontrol(d["syllable_scan"]["words_with_extra_syllable"] == [{"verse": 3, "line": "L2", "word": "atları"}], "fazla heceli kelime listesi beklenenden farkli")
kontrol(d["syllable_scan"]["words_with_missing_syllable"] == [], "eksik heceli kelime var")

# ---------------------------------------------------------------- 8) yerlestirme (yeni sarki bicimi)
yaz("\n== 8) YENI BICIMDE YERLER (105.000 BPM, 0.100 s on bosluk; zaman uzatma yok) ==")
for v, kt in enumerate(V):
    P = kt["pieces"]; sg = kt["segments"]; r = []
    for p, ad, vur in ((P[0], "L1", 0), (P[1], "L2", 0), (P[2], "diye", 2)):
        hb = 0.100 + (4 + 8 * v + p["placement"]["target_bar_in_verse"]) * BAR
        kontrol(abs(hb - p["placement"]["target_bar_downbeat"]) < 1e-3, "K%d %s hedef olcu zamani" % (v + 1, ad))
        on = p.get("strong_onset", p["start"]) + p["placement"]["shift_s"]
        r.append("%s %+.0f ms" % (ad, (on - hb - vur * BEAT) * 1000))
    l4 = sg["L4"]["start"] + P[2]["placement"]["shift_s"]; hb4 = 0.100 + (4 + 8 * v + 6) * BAR
    r.append("L4 %+.0f ms" % ((l4 - hb4) * 1000))
    cik2 = P[1]["cut_out"] + P[1]["placement"]["shift_s"]; hay = 0.100 + (4 + 8 * v + 3) * BAR - 0.040
    son3 = P[2]["cut_out"] + P[2]["placement"]["shift_s"]; b7 = 0.100 + (4 + 8 * v + 7) * BAR
    yaz("K%d  baslangiclar (olcu / vurus cizgisine gore): %s | L2 kesimi ile gercek hayvan sesi (olcu cizgisi - 40 ms) arasi %+.0f ms | parca 3 sonu, 7. olcu cizgisinden %+.0f ms" % (
        v + 1, ", ".join(r), (hay - cik2) * 1000, (son3 - b7) * 1000))
    kontrol(abs((hay - cik2) * 1000 - kt["hard_cuts"]["L2_end"]["silence_between_cut_out_and_real_animal_call_ms"]) < 1.0, "K%d: L2 kesimi - hayvan sesi arasi json ile uyusmuyor" % (v + 1))

# ---------------------------------------------------------------- 9) gurultu tabani
yaz("\n== 9) GURULTU TABANI (ham WAV) ==")
nf_ = d["noise_floor"]
gp = np.concatenate([x[int(g_["start"] * fs):int(g_["end"] * fs)] ** 2 for g_ in nf_["gaps"]])
gdb = 10 * np.log10(np.mean(gp) + 1e-20)
yaz("kitalar arasi (eski bandin sizintisi) RMS %.1f dBFS, soylenen RMS %.1f dBFS -> %.1f dB (json: %.1f)" % (gdb, SUNG, gdb - SUNG, nf_["between_verses_db_re_sung"]))
kontrol(abs(gdb - nf_["between_verses_rms_dbfs"]) < 0.3, "gurultu tabani json ile uyusmuyor")
yaz("bosluklar (dBFS): " + ", ".join("%.1f" % g_["rms_dbfs"] for g_ in nf_["gaps"]) + " | L4 kesiminden sonraki ilk 1 s: " +
    ", ".join("%.1f" % g_["rms_dbfs_first_1s_after_cut_out"] for g_ in nf_["first_second_after_each_L4_cut_out"]))
yaz("dize ici patlamali kapanislari (%d adet): ortanca %.1f dBFS, ceyrekler %s, en yuksek %.1f dBFS" % (
    nf_["inside_phrases_stop_closures_dbfs"]["n"], nf_["inside_phrases_stop_closures_dbfs"]["median"], nf_["inside_phrases_stop_closures_dbfs"]["quartiles"],
    nf_["inside_phrases_stop_closures_dbfs"]["max"]))

yaz("\n== 10) BAYRAKLAR ==")
yaz("bayrakli kelime: %d -> %s" % (d["summary"]["flagged_words"], d["summary"]["flagged_words_by_reason"]))
yaz("kor zarf tepesi sayimi tutmayan kelime: %d (bunlar orantili BOLUNMEDI; cekirdekler vurus izgarasindan, sinirlar sesten bulundu)" % d["summary"]["blind_count_mismatch_words"])
yaz("sinir turleri:", d["summary"]["boundary_kinds"])

yaz("\nSONUC:", "TUM KONTROLLER GECTI" if not hata else "%d HATA" % len(hata))
yaz("Not: bu kontroller olcumdur; hicbir ses kulakla dinlenmedi.")
open(os.path.join(K, "dogrulama.txt"), "w", encoding="utf8").write("\n".join(satirlar) + "\n")
sys.exit(1 if hata else 0)
