#!/usr/bin/env python3
"""vokal_dogal.wav + yerlesim.json dogrulamasi (yalniz olcum; kulakla dinleme YOK).
Cikti: ekrana rapor, yeni4/vokal/dogrulama.txt ve dogrulama.json. Cikis kodu 0 = butun kontroller gecti.
(yeni3/vokal/kod/04_dogrula.py'den uyarlandi; olcumler yerlestirme betiginden BAGIMSIZ: WAV, kaynak WAV, kafes ve kesim.json'dan yeniden hesaplanir.)"""
import sys, os, json, numpy as np, soundfile as sf, scipy.signal as ss
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *
import warnings; warnings.filterwarnings("ignore")

satirlar, sonuc, hatalar = [], {}, []


def yaz(*a):
    t = " ".join(str(q) for q in a)
    print(t)
    satirlar.append(t)


def kontrol(ad, kosul, ayrinti=""):
    yaz(("  [GECTI] " if kosul else "  [KALDI] ") + ad + ((" -- " + ayrinti) if ayrinti else ""))
    if not kosul:
        hatalar.append(ad)
    return bool(kosul)


BEKLENEN = {
    "L1": "a li ba ba nın bir çift li ği var",
    "L2": ["çift li ğin de i nek le ri var", "çift li ğin de ko yun la rı var", "çift li ğin de at la rı var", "çift li ğin de ho roz la rı var",
           "çift li ğin de ör dek le ri var", "çift li ğin de kö pek le ri var", "çift li ğin de ke di si var"],
    "diye": "di ye ba ğı rır",
    "L4": "çift li ğin de a li ba ba nın"}
BEKLENEN_VURUS = {"L1": [0, .5, 1, 1.25, 1.5, 2, 2.5, 3, 3.25, 3.5], "diye": [2, 2.5, 3, 3.25, 3.5], "L4": [0, .5, 1, 1.5, 2, 2.5, 3, 3.25, 3.5]}


def kucuk(t):
    return t.replace("İ", "i").replace("I", "ı").lower()


def kos(n):                       # dogrulamanin KENDI yukseltilmis kosinusu (0 -> 1)
    return 0.5 - 0.5 * np.cos(np.pi * (np.arange(n) + 0.5) / n)


def main():
    x = oku_vokal()
    Y = oku_json(CIKTI_JSON)
    K = oku_json(KESIM)
    T = oku_json(TEMPO)
    kafes = oku_json(KAFES)
    info = sf.info(CIKTI_WAV)
    y, sr = sf.read(CIKTI_WAV, dtype="float64")
    g = Y["audio"]["global_gain_linear"]
    gdb = 20 * np.log10(g)
    pieces, lines = Y["pieces"], Y["lines"]
    S = lambda t: int(round(t * SR))
    SUNG = K["levels"]["sung_rms_dbfs"]
    NF = K["noise_floor"]["between_verses_rms_dbfs"]
    LSB = 2.0 ** -23

    # ------------------------------------------------------------ 1) bicim
    yaz("== 1) DOSYA BICIMI ==")
    kontrol("mono, 44.1 kHz, PCM_24", info.channels == 1 and sr == SR and info.subtype == "PCM_24", "%d kanal, %d Hz, %s" % (info.channels, sr, info.subtype))
    bek_n = int(round((0.100 + 64 * 240.0 / 105.0 + 2.5) * SR))
    kontrol("uzunluk = 0.100 + 64 olcu + 2.5 s", len(y) == bek_n == Y["form"]["samples"], "%d ornek = %.6f s (beklenen %d)" % (len(y), len(y) / SR, bek_n))
    tepe = 20 * np.log10(np.max(np.abs(y)))
    kontrol("tepe -3 dBFS (tek genel kazanc)", abs(tepe + 3.0) < 0.01, "tepe %.4f dBFS, genel kazanc %+.4f dB" % (tepe, gdb))
    sonuc["format"] = dict(channels=info.channels, sample_rate=sr, subtype=info.subtype, samples=len(y), duration_sec=round(len(y) / SR, 6), peak_dbfs=round(tepe, 4), global_gain_db=round(gdb, 4))

    # ------------------------------------------------------------ 2) 7 x 3 parca, sira, ortusme
    yaz("== 2) 7 x 3 PARCA, SIRA, ORTUSME ==")
    kontrol("21 parca (7 kita x 3)", len(pieces) == 21 and [(p["verse"], p["piece"]) for p in pieces] == [(v, q) for v in range(1, 8) for q in (1, 2, 3)])
    bars_ok = all(p["dest_bar"] == 4 + 8 * (p["verse"] - 1) + {1: 0, 2: 2, 3: 5}[p["piece"]] for p in pieces)
    kontrol("hedef olculer: P1 -> kita olcusu 0, P2 -> 2, P3 -> 5 (kita v = olcu 4 + 8 v)", bars_ok, str([p["dest_bar"] for p in pieces]))
    db_ok = all(p["dest_bar_downbeat_sample"] == 4410 + p["dest_bar"] * 100800 and abs(p["dest_bar_downbeat"] - (0.100 + p["dest_bar"] * 240.0 / 105.0)) < 1e-6 for p in pieces)
    kontrol("olcu cizgileri: t(n) = 0.100 + n * 2.285714 s", db_ok)
    parts = [q for p in pieces for q in p["parts"]]
    sirali = all(parts[i]["dest_out_sample"] <= parts[i + 1]["dest_in_sample"] for i in range(len(parts) - 1))
    bosluklar = [(parts[i + 1]["dest_in_sample"] - parts[i]["dest_out_sample"]) / SR for i in range(len(parts) - 1)]
    kontrol("parcalar zaman sirasinda, ORTUSME YOK", sirali, "%d alt parca; en dar aralik %.1f ms (3. kita onarim boslugu), sonraki en dar %.3f s" % (len(parts), min(bosluklar) * 1000, sorted(bosluklar)[1]))
    # WAV'in kendisinden: sifir olmayan kosular
    nz = np.flatnonzero(y != 0)
    kes = np.flatnonzero(np.diff(nz) > int(0.005 * SR))
    kosu = [(nz[0] if i == 0 else nz[kes[i - 1] + 1], nz[kes[i]] + 1 if i < len(kes) else nz[-1] + 1) for i in range(len(kes) + 1)]
    es = len(kosu) == len(parts) and all(0 <= a - q["dest_in_sample"] <= 44 and 0 <= q["dest_out_sample"] - b <= 44 for (a, b), q in zip(kosu, parts))
    kontrol("WAV'daki sesli kosular = yerlesim.json'daki alt parcalar (sinirlar parcanin icinde, en cok 1 ms)", es, "%d kosu (5 ms'den uzun sifir araliklariyla ayrilmis); sinir farki en cok %d ornek (gecisin ilk/son ornekleri 24 bitte tam sifira yuvarlanir)" % (
        len(kosu), max(max(abs(a - q["dest_in_sample"]), abs(b - q["dest_out_sample"])) for (a, b), q in zip(kosu, parts)) if len(kosu) == len(parts) else -1))
    maske = np.zeros(len(y), bool)
    for q in parts:
        maske[q["dest_in_sample"]:q["dest_out_sample"]] = True
    kontrol("parcalarin disinda TAM dijital sessizlik", not np.any(y[~maske]), "parca disi ornek %d, sifir olmayan %d" % (int((~maske).sum()), int(np.count_nonzero(y[~maske]))))
    sonuc["structure"] = dict(pieces=len(pieces), parts=len(parts), runs_in_wav=len(kosu), no_overlap=bool(sirali), min_gap_ms=round(min(bosluklar) * 1000, 2),
                              second_smallest_gap_sec=round(sorted(bosluklar)[1], 4))

    # ------------------------------------------------------------ 3) ornek-ornek kaynakla ayni (perde / sure islemi yok)
    yaz("== 3) PERDE / SURE ISLEMI YOK: her alt parca = kaynak x gecis penceresi x genel kazanc ==")
    enb, kor_min = 0.0, 1.0
    for q in parts:
        n = q["src_out_sample"] - q["src_in_sample"]
        w = np.ones(n)
        w[:q["fade_in_samples"]] = kos(q["fade_in_samples"])
        w[n - q["fade_out_samples"]:] *= kos(q["fade_out_samples"])[::-1]
        bek = x[q["src_in_sample"]:q["src_out_sample"]] * w * g
        ger = y[q["dest_in_sample"]:q["dest_out_sample"]]
        enb = max(enb, float(np.max(np.abs(bek - ger))))
        # gecissiz ic bolge: kaynakla ilinti ve +-40 ornek icinde en iyi gecikme
        a, b = q["fade_in_samples"], n - q["fade_out_samples"]
        ic, kay = ger[a:b], x[q["src_in_sample"] + a:q["src_in_sample"] + b]
        kor_min = min(kor_min, float(np.dot(ic, kay) / np.sqrt(np.dot(ic, ic) * np.dot(kay, kay))))
    kontrol("butun alt parcalar kaynakla ornek-ornek ayni", enb <= 1.01 * LSB, "en buyuk fark %.3g (= %.2f x 24-bit adimi); ic bolgelerde en dusuk ilinti %.9f" % (enb, enb / LSB, kor_min))
    # iki yarida ayri gecikme olcumu (sure islemi olsaydi yarilar farkli gecikme verirdi)
    gec = []
    for q in parts:
        n = q["src_out_sample"] - q["src_in_sample"]
        for h0, h1 in ((0.1, 0.45), (0.55, 0.9)):
            a, b = int(n * h0), int(n * h1)
            ger = y[q["dest_in_sample"] + a:q["dest_in_sample"] + b]
            en, eni = -1, None
            for L in range(-40, 41):
                kay = x[q["src_in_sample"] + a + L:q["src_in_sample"] + b + L]
                c = float(np.dot(ger, kay))
                if c > en:
                    en, eni = c, L
            gec.append(eni)
    kontrol("capraz ilinti gecikmesi her alt parcanin iki yarisinda da 0 ornek", all(q_ == 0 for q_ in gec), "olculen gecikmeler: %s" % sorted(set(gec)))
    sonuc["sample_exact"] = dict(max_abs_error=enb, max_abs_error_lsb24=round(enb / LSB, 3), min_correlation=kor_min, xcorr_lags=sorted(set(gec)))

    # ------------------------------------------------------------ 4) yerlesim hesabi (kafesten bagimsiz yeniden)
    yaz("== 4) YERLESIM: hedef = hedef_olcu_basi + (kaynak - kaynak_olcu_basi) ==")
    enh = 0.0
    for p in pieces:
        v = p["verse"]
        vurus = 15 + 24 * (v - 1) + 4 * {1: 0, 2: 1, 3: 2}[p["piece"]]
        src_bar = kafes["phase_first_beat_s"] + vurus * kafes["beat_period_s"]
        hedef = 0.100 + p["dest_bar"] * 240.0 / 105.0
        for q in p["parts"]:
            ideal = hedef + (q["src_in_sample"] / SR - src_bar)
            enh = max(enh, abs(q["dest_in_sample"] / SR - ideal))
        # tempo.json'daki olcu cizgisiyle de karsilastir
        tb = [s_ for s_ in T["segments"] if s_["verse"] == v and s_["name"] == p["segments"][0]][0]["bar_downbeat"]
        assert abs(tb - src_bar) < 1.5e-4
    kontrol("butun parcalar olcu cizgisine gore yerinde (tam sayili ornek yuvarlamasi)", enh < 0.6 / SR, "en buyuk sapma %.4f ms (yarim ornek = 0.0113 ms)" % (enh * 1000))
    sonuc["placement"] = dict(max_abs_error_ms=round(enh * 1000, 4), rule="dest = dest_bar_downbeat + (src - src_bar_downbeat), integer samples")

    # ------------------------------------------------------------ 5) kesim kenarlari
    yaz("== 5) KESIM KENARLARI (her alt parcanin iki ucu) ==")
    sos_hf = ss.butter(6, 6000, btype="high", fs=SR, output="sos")
    kenar, en_kotu, en_kotu_hf = [], -999, -999
    yaz("  kenar                     | kaynak 5 ms RMS (gecissiz) | ciktida en distaki 2 ms / 1 ms (parca RMS'ine gore) | ilk-son ornek | >6 kHz enerji: cikti - kaynak")
    for p in pieces:
        pr = 20 * np.log10(np.sqrt(np.mean(y[S(p["dest_sound_start"]):S(p["dest_sound_end"])] ** 2)))      # parca RMS (ciktida)
        for q in p["parts"]:
            for uc in ("giris", "cikis"):
                if uc == "giris":
                    d0, nF, sc = q["dest_in_sample"], q["fade_in_samples"], q["src_in_sample"]
                    d2, d1 = y[d0:d0 + 88], y[d0:d0 + 44]
                    uc_ornek = y[d0]
                    fa, fb = d0, d0 + nF
                else:
                    d0, nF, sc = q["dest_out_sample"], q["fade_out_samples"], q["src_out_sample"]
                    d2, d1 = y[d0 - 88:d0], y[d0 - 44:d0]
                    uc_ornek = y[d0 - 1]
                    fa, fb = d0 - nF, d0
                e2 = 20 * np.log10(np.sqrt(np.mean(d2 ** 2)) + 1e-12) - pr
                e1 = 20 * np.log10(np.sqrt(np.mean(d1 ** 2)) + 1e-12) - pr
                ham = rms_db(x, sc / SR - 0.0025, sc / SR + 0.0025)
                # tiklama olcusu: gecis penceresinde (+-5 ms) 6 kHz ustu enerji, ciktida kaynaktakinden fazla mi?
                a_, b_ = fa - 220, fb + 220
                ks = sc - d0                                           # hedef -> kaynak ornek farki
                hy = ss.sosfilt(sos_hf, y[a_ - 2000:b_ + 2000])               # ciktinin KENDI baglami (parca ici ses / parca disi sifir)
                hx = ss.sosfilt(sos_hf, x[a_ + ks - 2000:b_ + ks + 2000]) * g
                hf = 10 * np.log10((np.sum(hy[2000:-2000] ** 2) + 1e-20) / (np.sum(hx[2000:-2000] ** 2) + 1e-20))
                mutlak2 = e2 + pr
                gecti = (e2 <= -40.0) or (mutlak2 <= NF + gdb)
                en_kotu = max(en_kotu, e2)
                en_kotu_hf = max(en_kotu_hf, hf)
                kenar.append(dict(part=q["label"], edge="in" if uc == "giris" else "out", fade_ms=round(nF / SR * 1000, 1), src_level_at_cut_dbfs=round(ham, 1),
                                  out_outer_2ms_db_re_piece_rms=round(e2, 1), out_outer_1ms_db_re_piece_rms=round(e1, 1), piece_rms_dbfs_out=round(pr, 1),
                                  edge_sample_dbfs=round(20 * np.log10(abs(uc_ornek) + 1e-12), 1), hf_excess_db=round(hf, 1), passed=bool(gecti)))
                yaz("  %-26s %-5s gecis %4.1f ms | %6.1f dBFS | %6.1f dB / %6.1f dB | %7.1f dBFS | %+5.1f dB %s" % (
                    q["label"][:26], uc, nF / SR * 1000, ham, e2, e1, 20 * np.log10(abs(uc_ornek) + 1e-12), hf, "" if gecti else "  <-- KALDI"))
    kontrol("her kesim kenarinda enerji parca RMS'inin en az 40 dB altinda (en distaki 2 ms) ya da gurultu tabaninda", all(k["passed"] for k in kenar),
            "%d kenar; en kotusu %.1f dB (2 ms), 1 ms penceresiyle en kotusu %.1f dB" % (len(kenar), en_kotu, max(k["out_outer_1ms_db_re_piece_rms"] for k in kenar)))
    kontrol("gecisler tiklama uretmiyor (gecis penceresi +-5 ms'de >6 kHz enerji ciktida kaynaktakinden fazla degil)", en_kotu_hf <= 0.5, "en buyuk fark %+.2f dB" % en_kotu_hf)
    ham_l2 = [k["src_level_at_cut_dbfs"] for k in kenar if k["edge"] == "out" and ("_P2" in k["part"]) and "_a(" not in k["part"]]
    ham_l2 = [float(q_) for q_ in ham_l2]
    yaz("  not: L2 sonlarinda kaynak, kesim aninda YUKSEK duzeydedir (%s dBFS): 'var' soylenen hayvan sesine araliksiz baglanir; kenar enerjisi gecisle sifira iner." % ham_l2)
    sonuc["cut_edges"] = dict(n=len(kenar), worst_outer_2ms_db_re_piece_rms=round(en_kotu, 1), worst_outer_1ms_db_re_piece_rms=max(k["out_outer_1ms_db_re_piece_rms"] for k in kenar),
                              worst_hf_excess_db=round(en_kotu_hf, 2), source_level_at_cut_dbfs_range=[min(k["src_level_at_cut_dbfs"] for k in kenar), max(k["src_level_at_cut_dbfs"] for k in kenar)],
                              source_level_at_L2_cut_out_dbfs=ham_l2, edges=kenar)

    # ------------------------------------------------------------ 6) L2 kesimi: hayvan sesi kaldi mi
    yaz("== 6) L2 SONU: soylenen hayvan sesi TAMAMEN gitti mi ==")
    sos_f2 = ss.butter(4, [1000, 3400], btype="band", fs=SR, output="sos")
    ef2 = zarf(ss.sosfiltfilt(sos_f2, x), 5)
    e5 = zarf(x, 5)
    l2 = []
    yaz("  kita | kesimden sonraki 300 ms (cikti) | 'diye'ye kadar sessizlik | kaynakta ayni 300 ms | bagimsiz F2 dususu - var_end (en dik dusus) | bagimsiz hayvan sesi baslangici - kesim | kesimden once kalan hayvan sesi (bagimsiz olcute gore) | 'var' kaybi | 'var' suresi L2 (yari genlik) / L1 | -3 -> -15 dB dusus L2 (kesilmis) / L1 (dogal)")
    for vi, V_ in enumerate(K["verses"]):
        v = V_["verse"]
        p2 = [p for p in pieces if p["verse"] == v and p["piece"] == 2][0]
        p3 = [p for p in pieces if p["verse"] == v and p["piece"] == 3][0]
        q = p2["parts"][-1]
        d_out, s_out, nF = q["dest_out_sample"], q["src_out_sample"], q["fade_out_samples"]
        son300 = y[d_out:d_out + S(0.300)]
        sifir_disi = int(np.count_nonzero(son300))
        ara = y[d_out:p3["dest_in_sample"]]
        kaynak300 = rms_db(x, s_out / SR, s_out / SR + 0.300)
        # bagimsiz olcut: 'var' unlusunde 1-3.4 kHz bandinin tepesinden 12 dB dusup >= 20 ms orada kaldigi ilk an (kendi uygulamam)
        var = [h for h in V_["lines"][1]["syllables"] if h["text"] == "var"][0]
        a, b = S(var["core_start"]), S(var["end"] + 0.12)
        seg = 20 * np.log10(ef2[a:b] + 1e-10)
        ipk = int(np.argmax(seg[:S(var["core_end"]) - a]))
        t_bag = None
        for i in range(ipk, len(seg) - S(0.02)):
            if seg[i] < seg[ipk] - 12 and np.all(seg[i:i + S(0.02)] < seg[ipk] - 12):
                t_bag = (a + i) / SR
                break
        # en dik dusus (ikinci bagimsiz olcut)
        d = seg[S(0.004):] - seg[:-S(0.004)]
        j0 = max(0, S(var["end"] - 0.05) - a)
        t_dik = (a + j0 + int(np.argmin(d[j0:S(var["end"] + 0.03) - a])) + S(0.002)) / SR
        # BAGIMSIZ hayvan sesi baslangici: araliksiz kitalarda F2 dususu (dudak kapanisi / /h/ basi);
        # aralikli kitalarda (4, 5) 'var' sondukten sonraki cukurun dibinden itibaren duzeyin 6 dB yukseldigi ilk an
        hc = V_["hard_cuts"]["L2_end"]
        aralikli = hc["gap_ms"] > 0
        if aralikli:
            i0_, i1_ = S(t_bag), S(hc["animal_first_vowel_onset"])
            sg5 = 20 * np.log10(e5[i0_:i1_] + 1e-10)
            im = int(np.argmin(sg5))
            ir = next((i for i in range(im, len(sg5)) if sg5[i] > sg5[im] + 6.0), len(sg5) - 1)
            t_hayvan = (i0_ + ir) / SR
            cukur_db = float(sg5[im])
        else:
            t_hayvan, cukur_db = t_bag, None
        # kesimden once, bagimsiz hayvan sesi baslangicinin SONRASINDA kalan (gecisle agirliklanmis) enerji
        w = np.ones(s_out - q["src_in_sample"]); w[len(w) - nF:] = kos(nF)[::-1]
        i_b = S(t_hayvan) - q["src_in_sample"]
        kalan = x[q["src_in_sample"] + i_b:s_out] * w[i_b:] if i_b < len(w) else np.zeros(0)
        var_seg = x[S(var["start"]):S(var["end"])]
        var_rms = 20 * np.log10(np.sqrt(np.mean(var_seg ** 2)))
        kalan_db = 10 * np.log10(np.sum(kalan ** 2) / (0.010 * SR) + 1e-20) if len(kalan) else -200.0     # 10 ms'ye yayilmis esdeger RMS
        kalan_tepe = 20 * np.log10(np.max(np.abs(kalan)) + 1e-12) if len(kalan) else -200.0
        # 'var' kaybi: var araliginda gecisin goturdugu enerji
        i0 = S(var["start"]) - q["src_in_sample"]; i1 = min(len(w), S(var["end"]) - q["src_in_sample"])
        seg_v = x[S(var["start"]):q["src_in_sample"] + i1]
        kayip = 10 * np.log10(np.sum((seg_v * w[i0:i1]) ** 2) / np.sum(x[S(var["start"]):S(var["end"])] ** 2))
        yari = (s_out - nF / 2) / SR                                    # gecisin yari genlik ani
        var_l2 = (yari - var["start"]) * 1000
        var1 = [h for h in V_["lines"][0]["syllables"] if h["text"] == "var"][0]
        var_l1 = (var1["end"] - var1["start"]) * 1000
        # dogal dusus suresi (L1 'var,') ile kesilmis L2 'var' dusus suresi: 3 ms RMS, unlu duzeyinden -3 dB -> -15 dB
        def dusus(sig, t_son, ref_t0, ref_t1, olcek=1.0):
            e = zarf(sig[S(ref_t0) - 2000:S(t_son + 0.08) + 2000], 3)[2000:-2000] / olcek
            ref = np.median(e[:S(ref_t1) - S(ref_t0)])
            i15 = next((i for i in range(S(ref_t1) - S(ref_t0), len(e)) if e[i] <= ref * 10 ** (-15 / 20)), None)
            if i15 is None:
                return None
            i3 = i15
            while i3 > 0 and e[i3] < ref * 10 ** (-3 / 20):
                i3 -= 1
            return (i15 - i3) / SR * 1000
        kay = p2["shift_samples"] / SR
        f_l2 = dusus(y, var["end"] + kay, var["core_start"] + kay, var["core_end"] + kay - 0.03)
        p1 = [p for p in pieces if p["verse"] == v and p["piece"] == 1][0]
        k1 = p1["shift_samples"] / SR
        f_l1 = dusus(y, var1["end"] + k1, var1["core_start"] + k1, var1["core_end"] + k1 - 0.03)
        b3 = 0.100 + (4 + 8 * vi + 3) * 240.0 / 105.0
        rec = dict(verse=v, what_follows=V_["hard_cuts"]["L2_end"]["what_follows"], fade_out_ms=round(nF / SR * 1000, 1),
                   out_rms_300ms_after_cut_dbfs=None if sifir_disi == 0 else round(20 * np.log10(np.sqrt(np.mean(son300 ** 2))), 1),
                   out_nonzero_samples_300ms_after_cut=sifir_disi, out_silence_until_diye_sec=round(len(ara) / SR, 4), out_nonzero_until_diye=int(np.count_nonzero(ara)),
                   src_rms_same_300ms_dbfs=round(kaynak300, 1), src_rms_same_300ms_db_above_noise_floor=round(kaynak300 - NF, 1),
                   var_end_segmentation=V_["hard_cuts"]["L2_end"]["var_end"], cut_out_src=round(s_out / SR, 5),
                   independent_f2_drop_t=round(t_bag, 4), independent_f2_drop_minus_cut_ms=round((t_bag - s_out / SR) * 1000, 1),
                   independent_f2_drop_minus_var_end_ms=round((t_bag - hc["var_end"]) * 1000, 1),
                   independent_steepest_fall_minus_var_end_ms=round((t_dik - hc["var_end"]) * 1000, 1),
                   independent_animal_onset_t=round(t_hayvan, 4), independent_animal_onset_minus_cut_ms=round((t_hayvan - s_out / SR) * 1000, 1),
                   pause_minimum_dbfs=None if cukur_db is None else round(cukur_db, 1),
                   kept_after_independent_drop_ms=round(max(0.0, s_out / SR - t_hayvan) * 1000, 1),
                   kept_after_independent_drop_equiv_rms_10ms_dbfs=round(kalan_db, 1), kept_after_independent_drop_db_re_var_rms=round(kalan_db - var_rms, 1),
                   kept_after_independent_drop_peak_dbfs=round(kalan_tepe, 1),
                   var_energy_loss_db=round(kayip, 2), var_ms_to_half_amplitude_L2=round(var_l2, 1), var_ms_L1_natural=round(var_l1, 1),
                   fall_time_3_to_15db_ms_L2_after_cut=None if f_l2 is None else round(f_l2, 1), fall_time_3_to_15db_ms_L1_natural=None if f_l1 is None else round(f_l1, 1),
                   silence_before_animal_call_ms=round((b3 - 0.040 - d_out / SR) * 1000, 1))
        l2.append(rec)
        yaz("  K%d (%s) | %s | %.3f s, sifir olmayan %d | %.1f dBFS (taban + %.0f dB) | %+.1f ms (%+.1f ms) | %+.1f ms%s | %.1f ms%s | %.2f dB | %.0f / %.0f ms | %s / %s ms" % (
            v, rec["what_follows"][:5], "TAM SIFIR (0 ornek)" if sifir_disi == 0 else "%.1f dBFS" % rec["out_rms_300ms_after_cut_dbfs"],
            rec["out_silence_until_diye_sec"], rec["out_nonzero_until_diye"], kaynak300, kaynak300 - NF, rec["independent_f2_drop_minus_var_end_ms"], rec["independent_steepest_fall_minus_var_end_ms"],
            rec["independent_animal_onset_minus_cut_ms"], "" if cukur_db is None else " (aradaki cukur %.1f dBFS)" % cukur_db,
            rec["kept_after_independent_drop_ms"], "" if not len(kalan) else ", 10 ms'ye esdeger %.1f dBFS = var RMS %+.1f dB, tepe %.1f dBFS" % (kalan_db, kalan_db - var_rms, kalan_tepe),
            kayip, var_l2, var_l1, rec["fall_time_3_to_15db_ms_L2_after_cut"], rec["fall_time_3_to_15db_ms_L1_natural"]))
    kontrol("her L2 kesiminden sonraki 300 ms TAM dijital sessizlik (gurultu tabaninin da altinda)", all(r["out_nonzero_samples_300ms_after_cut"] == 0 for r in l2),
            "kaynakta ayni 300 ms: %s dBFS; stem gurultu tabani %.1f dBFS" % ([float(r["src_rms_same_300ms_dbfs"]) for r in l2], NF))
    kontrol("L2 kesiminden 'diye' girisine kadar hic ses yok (soylenen hayvan sesi tamamen cikarildi)", all(r["out_nonzero_until_diye"] == 0 for r in l2),
            "sessizlik %s s" % [r["out_silence_until_diye_sec"] for r in l2])
    en_kalan = max(r["kept_after_independent_drop_db_re_var_rms"] for r in l2)
    kontrol("kesimden ONCE kalan olasi hayvan sesi artigi (bagimsiz baslangic olcutune gore) 'var' RMS'inin en az 40 dB altinda", en_kalan <= -40.0,
            "en kotusu %.1f dB (10 ms'ye esdeger RMS); bagimsiz hayvan sesi baslangici - kesim: %s ms (eksi = kesimden once)" % (en_kalan, [r["independent_animal_onset_minus_cut_ms"] for r in l2]))
    kontrol("segmentasyonun var_end'i bagimsiz F2 olcutuyle tutarli (+-5 ms)", all(abs(r["independent_f2_drop_minus_var_end_ms"]) <= 5.0 for r in l2),
            "bagimsiz - var_end: %s ms" % [r["independent_f2_drop_minus_var_end_ms"] for r in l2])
    kontrol("'var' duyulur bicimde kisalmadi: enerji kaybi 0.5 dB'den az", all(r["var_energy_loss_db"] > -0.5 for r in l2), "kayip %s dB" % [float(r["var_energy_loss_db"]) for r in l2])
    l1_min = min(r["var_ms_L1_natural"] for r in l2)
    kontrol("kesilmis L2 'var' (yari genlik noktasina kadar) bu sarkicinin en kisa dogal L1 'var,'indan kisa degil (5 ms pay)", all(r["var_ms_to_half_amplitude_L2"] >= l1_min - 5 for r in l2),
            "L2 %s ms; dogal L1 %s ms (en kisa %.0f)" % ([r["var_ms_to_half_amplitude_L2"] for r in l2], [r["var_ms_L1_natural"] for r in l2], l1_min))
    f_kes = [r["fall_time_3_to_15db_ms_L2_after_cut"] for r in l2 if r["what_follows"] != "pause"]
    f_dog = [r["fall_time_3_to_15db_ms_L1_natural"] for r in l2] + [r["fall_time_3_to_15db_ms_L2_after_cut"] for r in l2 if r["what_follows"] == "pause"]
    yaz("  bilgi: kesilmis 5 L2 sonunda -3 -> -15 dB dusus %s ms; bu sarkicinin DOGAL kelime sonlari (7 x L1 'var,' + aralikli K4, K5 L2) %s ms (aralik %.1f - %.1f)" % (f_kes, f_dog, min(f_dog), max(f_dog)))
    kontrol("kesilmis L2 sonlarinin dusus hizi sarkicinin kendi dogal kelime sonlarinin araliginda", all(min(f_dog) <= f <= max(f_dog) for f in f_kes),
            "kesilmis %.1f - %.1f ms (medyan %.1f); dogal %.1f - %.1f ms (medyan %.1f)" % (min(f_kes), max(f_kes), float(np.median(f_kes)), min(f_dog), max(f_dog), float(np.median(f_dog))))
    sonuc["l2_cuts_fall_times"] = dict(cut_l2_endings_ms=f_kes, natural_endings_ms=f_dog, definition="time for the 3 ms RMS envelope to fall from -3 dB to -15 dB re the vowel level")
    sonuc["l2_cuts"] = dict(noise_floor_stem_dbfs=NF, per_verse=l2)

    # ------------------------------------------------------------ 6b) 'diye' girisi: hayvan sesinin SONU kaldi mi
    yaz("== 6b) 'DIYE' GIRISI: soylenen hayvan sesinin sonundan bir sey kaldi mi ==")
    kap = K["noise_floor"]["inside_phrases_stop_closures_dbfs"]
    dg = []
    for V_ in K["verses"]:
        v = V_["verse"]
        hd = V_["hard_cuts"]["diye_start"]
        p3 = [p for p in pieces if p["verse"] == v and p["piece"] == 3][0]
        q = p3["parts"][0]
        nF, d_in, s_in = q["fade_in_samples"], q["dest_in_sample"], q["src_in_sample"]
        ic = y[d_in:d_in + nF] / g                                   # gecis penceresi, kaynak olceginde
        gecisli = 20 * np.log10(np.sqrt(np.mean(ic ** 2)) + 1e-12)
        ham = rms_db(x, s_in / SR, (s_in + nF) / SR)
        # 'diye' baslangicindan (d patlamasi) ONCE ciktiya giren enerji, 10 ms'ye esdeger RMS
        n_on = max(0, min(len(y), S(hd["diye_onset"]) - s_in))
        once_ = y[d_in:d_in + n_on] / g
        giren = 10 * np.log10(np.sum(once_ ** 2) / (0.010 * SR) + 1e-20)
        atilan = rms_db(x, hd["animal_sound_body_end"] - 0.10, hd["animal_sound_body_end"])     # atilan hayvan sesinin son 100 ms'si
        dg.append(dict(verse=v, cut_in_src=round(s_in / SR, 5), fade_in_ms=round(nF / SR * 1000, 1), animal_sound_end_segmentation=hd["animal_sound_end"],
                       cut_in_minus_animal_sound_end_ms=round((s_in / SR - hd["animal_sound_end"]) * 1000, 1), diye_onset=hd["diye_onset"],
                       raw_rms_in_fade_window_dbfs=round(ham, 1), faded_rms_in_fade_window_dbfs=round(gecisli, 1), faded_rms_db_re_sung=round(gecisli - SUNG, 1),
                       admitted_before_diye_onset_equiv_rms_10ms_dbfs=round(giren, 1), admitted_before_diye_onset_db_re_sung=round(giren - SUNG, 1),
                       removed_animal_sound_last_100ms_dbfs=round(atilan, 1)))
        yaz("  K%d kesim %.4f (hayvan sesi sonundan %+.1f ms sonra), gecis %.1f ms | pencere ici ham %.1f dBFS, gecisle %.1f dBFS (soylenen RMS %+.1f dB) | 'diye' basindan once giren: 10 ms'ye esdeger %.1f dBFS (%+.1f dB) | atilan hayvan sesinin son 100 ms'si %.1f dBFS" % (
            v, s_in / SR, dg[-1]["cut_in_minus_animal_sound_end_ms"], nF / SR * 1000, ham, gecisli, gecisli - SUNG, giren, giren - SUNG, atilan))
    kontrol("'diye' kesimi soylenen hayvan sesinin bitisinden SONRA", all(d_["cut_in_minus_animal_sound_end_ms"] >= 0 for d_ in dg), "kesim - hayvan sesi sonu: %s ms" % [d_["cut_in_minus_animal_sound_end_ms"] for d_ in dg])
    kontrol("'diye'den once giren artik, bu stemin dize ICINDEKI siradan durak kapanislarindan yuksek degil (ust ceyrek %.1f dBFS)" % kap["quartiles"][1],
            all(d_["faded_rms_in_fade_window_dbfs"] <= kap["quartiles"][1] for d_ in dg),
            "gecis penceresi (gecisle) %s dBFS; dize ici kapanislar medyan %.1f, ceyrekler %s dBFS" % ([float(d_["faded_rms_in_fade_window_dbfs"]) for d_ in dg], kap["median"], kap["quartiles"]))
    sonuc["diye_cut_in"] = dict(stop_closures_inside_phrases_dbfs=kap, per_verse=dg)

    # ------------------------------------------------------------ 7) baslangic anlari
    yaz("== 7) BASLANGIC ANLARI: olculen - amaclanan ==")
    yaz("  olcu: tempo analizinin tanimi (bant zarfinin ilk hecenin tepesinin %25'ine ulastigi ilk an; unlu baslangiclari 300-3400 Hz, 'c' baslangiclari 2-7 kHz), burada CIKTI dosyasinda olculdu.")
    sos_v = ss.butter(4, [300, 3400], btype="band", fs=SR, output="sos")
    sos_c = ss.butter(4, [2000, 7000], btype="band", fs=SR, output="sos")
    env = dict(v=(zarf(ss.sosfiltfilt(sos_v, y), 5), zarf(ss.sosfiltfilt(sos_v, x), 5)), c=(zarf(ss.sosfiltfilt(sos_c, y), 5), zarf(ss.sosfiltfilt(sos_c, x), 5)))

    def bas25(e, t_ara0, t_tepe0, t_tepe1):
        """t_ara0'dan itibaren zarfin, [t_tepe0, t_tepe1] icindeki tepesinin %25'ine ulastigi ilk an.
        Kalicilik sarti: sonraki 15 ms boyunca tepenin %20'sinin altina inmemeli (kapanis icindeki 5 ms'lik kucuk patlamalar
        baslangic sayilmaz; 3. kita L4'te 'rır' ile 'c' arasinda boyle bir patlama var)."""
        tepe_ = float(np.max(e[S(t_tepe0):S(t_tepe1)]))
        a = S(t_ara0)
        for i in range(a, S(t_tepe1)):
            if e[i] >= 0.25 * tepe_ and np.all(e[i:i + S(0.015)] >= 0.2 * tepe_):
                return i / SR
        return None

    ons = []
    tsg = {(s_["verse"], s_["name"]): s_ for s_ in T["segments"]}
    pid_ = {p["id"]: p for p in pieces}
    for L in lines:
        v, ad = L["verse"], L["line"]
        kay = L["shift_samples"] / SR
        ilk = L["syllables"][0]
        ts = tsg[(v, ad)]
        tur = "c" if ad in ("L2", "L4") else "v"
        P = pid_[L["piece"]]
        # arama baslangici = 'onceki enerji cukuru' (tempo analizinin tanimi): parcanin giris kesiminden (L4 icin: 'rır' cekirdeginin
        # sonundan) ilk hecenin tepesine kadar, KAYNAK bant zarfinin en dusuk oldugu an; cikti icin ayni an + kaydirma
        tepe0, tepe1 = ilk["src_start"], ilk["src_end"]
        if ad == "L4":
            onceki = [q_ for q_ in lines if q_["verse"] == v and q_["line"] == "diye"][0]["syllables"][-1]
            lo = onceki["src_core_end"]
        else:
            lo = P["src_in"]
        ex_ = env[tur][1]
        i_tepe = S(tepe0) + int(np.argmax(ex_[S(tepe0):S(tepe1)]))
        ara0 = (S(lo) + int(np.argmin(ex_[S(lo):i_tepe]))) / SR
        t_src = bas25(env[tur][1], ara0, tepe0, tepe1)
        t_out = bas25(env[tur][0], ara0 + kay, tepe0 + kay, tepe1 + kay)
        vurus = L["dest_bar_downbeat"] + L["expected_beat_in_bar"] * 60.0 / 105.0
        amac_tempo = ts["onset"] + kay                                   # tempo analizinin (mix) buldugu baslangic, yeni forma tasinmis
        ons.append(dict(verse=v, line=ad, dest_bar=L["dest_bar"], expected_beat_in_bar=L["expected_beat_in_bar"], beat_time=round(vurus, 5), band="300-3400 Hz" if tur == "v" else "2-7 kHz",
                        measured_onset_out=round(t_out, 5), measured_onset_minus_beat_ms=round((t_out - vurus) * 1000, 1),
                        measured_out_minus_source_plus_shift_ms=round((t_out - (t_src + kay)) * 1000, 3),
                        intended_onset_tempo_analysis=round(amac_tempo, 5), tempo_onset_minus_beat_ms=round((amac_tempo - vurus) * 1000, 1), tempo_refined_reliable=ts["refined_reliable"],
                        measured_minus_intended_ms=round((t_out - amac_tempo) * 1000, 1),
                        segmentation_start_minus_beat_ms=L["onset_minus_expected_beat_ms"]))
    yaz("  kita dize | olcu vurus | olculen baslangic - vurus (cikti) | tempo analizi (mix) - vurus | OLCULEN - AMACLANAN | kesim 'start' - vurus | cikti - (kaynak + kaydirma)")
    for o in ons:
        yaz("  K%d %-4s | %2d  %.1f | %+6.1f ms | %+6.1f ms%s | %+6.1f ms | %+6.1f ms | %+.3f ms" % (
            o["verse"], o["line"], o["dest_bar"], o["expected_beat_in_bar"], o["measured_onset_minus_beat_ms"], o["tempo_onset_minus_beat_ms"], "  " if o["tempo_refined_reliable"] else " *",
            o["measured_minus_intended_ms"], o["segmentation_start_minus_beat_ms"], o["measured_out_minus_source_plus_shift_ms"]))
    yaz("  (* = tempo analizinde bu baslangic inceltilemedi; 20 ms'lik sozcuk dosyasi izgarasindan, +-25 ms)")
    eny = max(abs(o["measured_out_minus_source_plus_shift_ms"]) for o in ons)
    kontrol("yerlestirme ve gecisler baslangiclari kaydirmadi: ciktida olculen = kaynakta olculen + kaydirma", eny <= 0.05, "en buyuk fark %.3f ms (28 dize)" % eny)
    guv = np.array([o["measured_minus_intended_ms"] for o in ons if o["tempo_refined_reliable"]])
    hep = np.array([o["measured_minus_intended_ms"] for o in ons])
    kontrol("olculen baslangiclar amaclanan anlarda (tempo analizinin mix uzerinde buldugu baslangic + kaydirma; inceltilmis olanlar +-15 ms)", float(np.max(np.abs(guv))) <= 15.0,
            "inceltilmis %d dize: en buyuk |hata| %.1f ms, medyan %+.1f ms | 28 dizenin tumu: en buyuk |hata| %.1f ms, medyan %+.1f ms" % (
                len(guv), float(np.max(np.abs(guv))), float(np.median(guv)), float(np.max(np.abs(hep))), float(np.median(hep))))
    kontrol("hicbir dize yanlis vurusta degil (tum hatalar onaltilik notanin yarisindan kucuk: 71 ms)", float(np.max(np.abs(hep))) < 71.0)
    ozet = {}
    for ad in ("L1", "L2", "diye", "L4"):
        q = np.array([o["measured_onset_minus_beat_ms"] for o in ons if o["line"] == ad])
        ozet[ad] = dict(median_ms=round(float(np.median(q)), 1), min_ms=round(float(q.min()), 1), max_ms=round(float(q.max()), 1))
        yaz("  %-4s olculen baslangic - vurus: medyan %+.1f ms, aralik %+.1f .. %+.1f ms  (tempo analizinin mix'te buldugu tipik deger: %+.1f ms)" % (
            ad, np.median(q), q.min(), q.max(), T["summary"]["typical_offset_ms"][ad]))
    sonuc["onsets"] = dict(definition="first instant the band envelope (5 ms RMS; 300-3400 Hz for L1 and 'diye', 2-7 kHz for the 'ç' of L2 and L4) reaches 25 % of the first syllable's peak, measured on vokal_dogal.wav; intended = onset found by the tempo analysis on the full mix + the piece's shift",
                           max_abs_placement_error_ms=round(eny, 3),
                           refined_segments=dict(n=int(len(guv)), max_abs_error_ms=round(float(np.max(np.abs(guv))), 1), median_error_ms=round(float(np.median(guv)), 1)),
                           all_segments=dict(n=int(len(hep)), max_abs_error_ms=round(float(np.max(np.abs(hep))), 1), median_error_ms=round(float(np.median(hep)), 1)),
                           measured_onset_minus_beat_per_line_type=ozet, typical_offset_ms_tempo_analysis=T["summary"]["typical_offset_ms"], per_line=ons)

    # ------------------------------------------------------------ 8) 3. kita onarimi
    yaz("== 8) 3. KITA ONARIMI: 'atlari' ==")
    rep = [r for r in Y["repairs"] if r["id"] == "K3_L2_atlari"]
    kontrol("onarim listede (kesim.json dort cekirdek buldu)", len(rep) == 1 and K["atlari_check"]["verdict"].startswith("FOUR"))
    r3 = {}
    if rep:
        r = rep[0]
        pa, pb = r["pieces"]
        ex = K["atlari_check"]["excision"]
        lm = K["atlari_check"]["landmarks"]
        kay_n = pa["dest_in_sample"] - pa["src_in_sample"]
        kontrol("iki alt parca AYNI kaydirmayla yerlesti ('lari var' 0 ms kaydi, 'var' zamaninda)", pb["dest_in_sample"] - pb["src_in_sample"] == kay_n, "kaydirma %d ornek" % kay_n)
        kontrol("kesip atma araligi kesim.json onerisiyle ayni", abs(pa["src_out_sample"] / SR - ex["start"]) < 1 / SR and abs((pb["src_in_sample"] + pb["fade_in_samples"] / 2) / SR - ex["end"]) < 1.5 / SR,
                "atilan %.4f - %.4f s (yari genlik noktasi); cikis gecisi %.1f ms, giris gecisi %.1f ms" % (pa["src_out_sample"] / SR, (pb["src_in_sample"] + pb["fade_in_samples"] / 2) / SR,
                                                                                                         pa["fade_out_samples"] / SR * 1000, pb["fade_in_samples"] / SR * 1000))
        bos = y[pa["dest_out_sample"]:pb["dest_in_sample"]]
        kontrol("aradaki bosluk tam dijital sessizlik", not np.any(bos), "%.1f ms" % (len(bos) / SR * 1000))
        # cekirdek sayimi: 300-3400 Hz zarfi (12 ms), kelime araliginda; once = kaynak, sonra = cikti
        def cekirdek_say(sig, t0, t1, olcek=1.0):
            e = zarf(ss.sosfiltfilt(sos_v, sig[S(t0) - 4000:S(t1) + 4000]), 12)[4000:-4000] / olcek
            ed = 20 * np.log10(e + 1e-9)
            esik = SUNG - 12
            tep = []
            i = 0
            usta = False
            # esigin ustundeki bolgeler; aralarinda en az 6 dB'lik cukur varsa ayri cekirdek
            pk, _ = ss.find_peaks(ed, height=esik, prominence=6.0, distance=S(0.06))
            return [round(float(t0 + q / SR), 4) for q in pk]
        w = [w_ for w_ in K["verses"][2]["lines"][1]["words"] if w_["text"] == "atları"][0]
        kay = kay_n / SR
        once = cekirdek_say(x, w["start"], w["end"])
        sonra = cekirdek_say(y, w["start"] + kay, w["end"] + kay, g)
        yaz("  cekirdek tepeleri (300-3400 Hz zarfi, 6 dB belirginlik): ONCE %d: %s | SONRA %d: %s (kaynak zamanina cevrilmis)" % (len(once), once, len(sonra), [round(float(t - kay), 4) for t in sonra]))
        kontrol("onarimdan sonra kelimede 3 cekirdek (once daha fazla)", len(sonra) == 3 and len(once) > 3, "once %d, sonra %d" % (len(once), len(sonra)))
        # sesli sureler
        def sesli_ms(sig, t0, t1, olcek=1.0, esik_db=-45.0):
            e = zarf(sig[S(t0) - 2000:S(t1) + 2000], 5)[2000:-2000] / olcek
            return float(np.sum(20 * np.log10(e + 1e-12) > esik_db) / SR * 1000)
        s_once = sesli_ms(x, w["start"], w["end"]); s_sonra = sesli_ms(y, w["start"] + kay, w["end"] + kay, g)
        # otumsuz aralik: 'a' unlusunun bitisinden /l/'nin yari genlik noktasina
        otumsuz = (ex["end"] - lm["first_a_end_t_closure_start"]) * 1000
        yaz("  sureler: kelime araligi %.1f ms (degismedi) | -45 dBFS ustu ses: once %.0f ms, sonra %.0f ms | 'at' %.1f ms + sus %.1f ms + 'lari' %.1f ms | 'a' bitisi -> /l/ yari genlik: %.0f ms (icinde /t/ patlamasi)" % (
            (w["end"] - w["start"]) * 1000, s_once, s_sonra, ex["what_remains"]["at_ms"], ex["removed_ms"], ex["what_remains"]["lari_ms"], otumsuz))
        # ek yerinde sureklilik
        import pyworld as pw
        a_, b_ = S(39.30 + kay), S(40.60 + kay)
        f0, tt = pw.harvest(y[a_:b_] / g, SR, f0_floor=150, f0_ceil=600, frame_period=5.0)
        tt = tt + a_ / SR - kay                                           # kaynak zamani
        mm = np.where(f0 > 0, 69 + 12 * np.log2(np.maximum(f0, 1) / 440), np.nan)
        med = lambda t0, t1: float(np.nanmedian(mm[(tt >= t0) & (tt < t1)]))
        f_at, f_l, f_la = med(39.41, 39.57), med(ex["end"] + 0.012, lm["second_a_onset"]), med(lm["second_a_onset"], 40.13)
        sesli_bosluk = int(np.sum(np.isfinite(mm[(tt >= ex["start"] + 0.005) & (tt < ex["end"] - 0.02)])))
        d_a = np.max(np.abs(np.diff(y[pa["dest_out_sample"] - 90:pa["dest_out_sample"] + 2])))
        d_b = np.max(np.abs(np.diff(y[pb["dest_in_sample"] - 2:pb["dest_in_sample"] + 90])))
        d_ic = np.percentile(np.abs(np.diff(y[pb["dest_in_sample"] + pb["fade_in_samples"]:pb["dest_in_sample"] + pb["fade_in_samples"] + 4410])), 99)
        ham_a = rms_db(x, ex["start"] - 0.015, ex["start"]); ham_b = rms_db(x, ex["end"] - 0.0025, ex["end"] + 0.0025)
        yaz("  ek yeri (a) cikis: kaynak son 15 ms %.1f dBFS (soylenen RMS %+.1f dB); son 2 ms'de en buyuk ornek adimi %.2g" % (ham_a, ham_a - SUNG, d_a))
        yaz("  ek yeri (b) giris: /l/ icinde, kaynak duzeyi %.1f dBFS; ilk 2 ms'de en buyuk ornek adimi %.2g (parca ici %%99 adim %.2g)" % (ham_b, d_b, d_ic))
        yaz("  perde: 'at' unlusu %.2f | kalan /l/ %.2f | 'la' %.2f MIDI; susun icinde otumlu cerceve: %d" % (f_at, f_l, f_la, sesli_bosluk))
        kontrol("ek yerlerinde sicrama yok (kenar adimi parca ici %99 adimin altinda)", d_a < d_ic and d_b < d_ic, "cikis %.2g, giris %.2g, parca ici %.2g" % (d_a, d_b, d_ic))
        kontrol("atilan cekirdekten ses kalmadi (susun icinde otumlu cerceve yok)", sesli_bosluk == 0)
        kontrol("'at' ve 'la' ayni notada (F4), kalan /l/ 'la'ya 1 yarim sesten az kayarak baglaniyor", abs(f_at - f_la) < 0.3 and abs(f_l - f_la) < 1.0, "%.2f / %.2f / %.2f" % (f_at, f_l, f_la))
        var = [h for h in K["verses"][2]["lines"][1]["syllables"] if h["text"] == "var"][0]
        l2k3 = [L for L in lines if L["verse"] == 3 and L["line"] == "L2"][0]
        var_h = [h for h in l2k3["syllables"] if h["text"] == "var"][0]
        var_vurus = (var_h["dest_start"] - l2k3["dest_bar_downbeat"]) / (60.0 / 105.0)
        kontrol("'var' zamaninda: hedef = kaynak + parca kaydirmasi (0 ms ek kayma)", abs(var_h["dest_start"] - (var["start"] + kay)) < 1e-4, "'var' hece basi vurus %.3f (izgara yuvasi 3.5), cekirdek basi vurus %.3f" % (
            var_vurus, (var_h["dest_core_start"] - l2k3["dest_bar_downbeat"]) / (60.0 / 105.0)))
        r3 = dict(nuclei_before=len(once), nuclei_after=len(sonra), nuclei_before_t=once, nuclei_after_t_src_time=[round(float(t - kay), 4) for t in sonra],
                  word_span_ms=round((w["end"] - w["start"]) * 1000, 1), sounding_ms_before=round(s_once, 1), sounding_ms_after=round(s_sonra, 1),
                  at_ms=ex["what_remains"]["at_ms"], rest_ms=ex["removed_ms"], digital_silence_ms=round(len(bos) / SR * 1000, 1), lari_ms=ex["what_remains"]["lari_ms"],
                  unvoiced_stretch_a_end_to_l_half_amplitude_ms=round(otumsuz, 1),
                  fade_out_ms=round(pa["fade_out_samples"] / SR * 1000, 1), fade_in_ms=round(pb["fade_in_samples"] / SR * 1000, 1),
                  src_level_last_15ms_before_excision_dbfs=round(ham_a, 1), src_level_at_splice_in_dbfs=round(ham_b, 1),
                  max_sample_step_at_fade_out_edge=float(d_a), max_sample_step_at_fade_in_edge=float(d_b), p99_sample_step_inside=float(d_ic),
                  f0_at_midi=round(f_at, 2), f0_kept_l_midi=round(f_l, 2), f0_la_midi=round(f_la, 2), voiced_frames_inside_rest=sesli_bosluk,
                  shift_of_var_ms=0.0, var_start_beat_in_bar=round(var_vurus, 3))
    sonuc["verse3_repair"] = r3

    # ------------------------------------------------------------ 9) heceler
    yaz("== 9) HECELER ==")
    n_hece = sum(len(L["syllables"]) for L in lines)
    kontrol("28 dize, 229 korunan hece", len(lines) == 28 and n_hece == 229 == K["summary"]["kept_syllables"], "%d dize, %d hece" % (len(lines), n_hece))
    metin_ok, ic_ok, kay_ok, alan_ok, vurus_ok = True, True, True, True, True
    pid = {p["id"]: p for p in pieces}
    for L in lines:
        bek = BEKLENEN[L["line"]] if L["line"] != "L2" else BEKLENEN["L2"][L["verse"] - 1]
        if " ".join(kucuk(h["text"]) for h in L["syllables"]) != bek:
            metin_ok = False; yaz("    metin farkli:", L["verse"], L["line"], " ".join(h["text"] for h in L["syllables"]))
        p = pid[L["piece"]]
        son = None
        for h in L["syllables"]:
            if not (p["dest_in"] - 1e-4 <= h["dest_start"] < h["dest_end"] <= p["dest_out"] + 1e-4) or (son is not None and h["dest_start"] < son - 1e-4):
                ic_ok = False; yaz("    parca disi / sirasiz hece:", L["verse"], L["line"], h["text"])
            son = h["dest_end"]
            if abs((h["dest_start"] - h["src_start"]) - p["shift_sec"]) > 1e-4 or abs((h["dest_end"] - h["src_end"]) - p["shift_sec"]) > 1e-4:
                kay_ok = False
            if any(h.get(k_) is None for k_ in ("text", "src_start", "src_end", "dest_start", "dest_end", "midi", "pitch_start", "pitch_mid", "pitch_end")):
                alan_ok = False
            # hece hicbir alt parcanin disinda (atilan aralikta) kalmasin
            if not any(q["dest_in"] - 1e-4 <= h["dest_core_start"] and h["dest_core_end"] <= q["dest_out"] + 1e-4 for q in p["parts"]):
                ic_ok = False; yaz("    cekirdegi alt parca disinda:", L["verse"], L["line"], h["text"])
        if L["line"] in BEKLENEN_VURUS and [h["beat_in_bar"] for h in L["syllables"]] != BEKLENEN_VURUS[L["line"]]:
            vurus_ok = False; yaz("    vurus yuvalari farkli:", L["verse"], L["line"], [h["beat_in_bar"] for h in L["syllables"]])
    duz = Y["syllables_flat"]
    ic_ice = [h for L in lines for h in L["syllables"]]
    duz_ok = len(duz) == len(ic_ice) and all(all(d_[k_] == h[k_] for k_ in ("text", "src_start", "src_end", "dest_start", "dest_end", "midi", "pitch_start", "pitch_mid", "pitch_end")) for d_, h in zip(duz, ic_ice))
    kontrol("duz hece tablosu (syllables_flat) ic ice kayitlarla ayni", duz_ok, "%d satir" % len(duz))
    kontrol("hece metinleri beklenen sozlerle ayni (3. kita: 'at la rı', fazladan hece yok)", metin_ok)
    kontrol("heceler kendi parcasinin icinde, sirali; cekirdekleri atilan aralikta degil", ic_ok)
    kontrol("hece hedef zamani = kaynak zamani + parca kaydirmasi", kay_ok)
    kontrol("her hecede metin, kaynak/hedef bas-son, medyan MIDI, bas/orta/son perde var", alan_ok)
    kontrol("hece vurus yuvalari forma uygun (L1: olcu 0; diye: olcu 5 vurus 2-3.5; L4: olcu 6)", vurus_ok)
    # ciktidan bagimsiz perde olcumu: hece cekirdeginde medyan f0 (pyworld harvest) ile yerlesim.json'daki MIDI
    import pyworld as pw
    farklar, sapanlar = [], []
    for p in pieces:
        a_, b_ = p["dest_in_sample"] - 2205, p["dest_out_sample"] + 2205
        f0, tt = pw.harvest(y[a_:b_] / g, SR, f0_floor=150, f0_ceil=650, frame_period=5.0)
        tt = tt + a_ / SR
        mm = np.where(f0 > 0, 69 + 12 * np.log2(np.maximum(f0, 1) / 440), np.nan)
        for L in [L for L in lines if L["piece"] == p["id"]]:
            for h in L["syllables"]:
                i = (tt >= h["dest_core_start"]) & (tt <= h["dest_core_end"]) & np.isfinite(mm)
                if i.sum() < 3:
                    continue
                dlt = float(np.median(mm[i])) - h["midi"]
                farklar.append(dlt)
                if abs(dlt) > 0.3:
                    sapanlar.append("K%d %s %s %+.2f" % (L["verse"], L["line"], h["text"], dlt))
    farklar = np.array(farklar)
    kontrol("ciktida olculen hece perdesi = yerlesim.json'daki ozgun perde (perde islemi yok, tablo sesle hizali)", np.median(np.abs(farklar)) < 0.05 and len(sapanlar) <= 5,
            "%d hece olculdu; |fark| medyan %.3f, %%95 %.2f, en buyuk %.2f yarim ses; 0.3'u asan %d: %s" % (
                len(farklar), np.median(np.abs(farklar)), np.percentile(np.abs(farklar), 95), np.max(np.abs(farklar)), len(sapanlar), sapanlar))
    midis = [h["midi"] for L in lines for h in L["syllables"]]
    yaz("  ozgun perde araligi: MIDI %.2f .. %.2f" % (min(midis), max(midis)))
    sonuc["syllables"] = dict(lines=len(lines), syllables=n_hece, pitch_check_n=int(len(farklar)), pitch_abs_diff_median=round(float(np.median(np.abs(farklar))), 3),
                              pitch_abs_diff_p95=round(float(np.percentile(np.abs(farklar), 95)), 2), pitch_abs_diff_max=round(float(np.max(np.abs(farklar))), 2),
                              pitch_diff_over_0_3=sapanlar, midi_range=[min(midis), max(midis)])

    # ------------------------------------------------------------ 10) gercek hayvan sesi yuvalari
    yaz("== 10) GERCEK HAYVAN SESI YUVALARI ==")
    for sl in Y["animal_call_slots"]:
        yaz("  K%d %-6s 1. ses %.4f s (olcu %d cizgisi - 40 ms), L2 kesimi ile arasi %+.1f ms | 2. ses %.4f s | 'diye' vokali %.4f s (2. ses icin %.3f s bos)" % (
            sl["verse"], sl["animal"], sl["call_1"]["start"], sl["call_1"]["bar"], sl["call_1"]["silence_between_L2_end_and_call_start_ms"], sl["call_2"]["start"], sl["diye_vocal_in"], sl["free_window_for_call_2_sec"]))
    kontrol("2. hayvan sesi (en cok 1.85 s) 'diye' vokalinden once biter", all(sl["free_window_for_call_2_sec"] > 1.85 for sl in Y["animal_call_slots"]),
            "en dar pencere %.3f s" % min(sl["free_window_for_call_2_sec"] for sl in Y["animal_call_slots"]))
    sonuc["animal_call_slots"] = dict(silence_between_L2_cut_and_call_1_ms=[sl["call_1"]["silence_between_L2_end_and_call_start_ms"] for sl in Y["animal_call_slots"]],
                                      min_free_window_for_call_2_sec=min(sl["free_window_for_call_2_sec"] for sl in Y["animal_call_slots"]))

    # ------------------------------------------------------------ ozet
    yaz("")
    yaz("== OZET: %d kontrol KALDI ==" % len(hatalar) if hatalar else "== OZET: butun kontroller GECTI ==")
    for h_ in hatalar:
        yaz("  KALDI:", h_)
    yaz("Kulakla DOGRULANMADI: gecislerin duyulmadigi, L2 sonlarinin (5 kitada tam duzeyde kesim) kirpik duyulmadigi, 3. kitadaki 'at' + sus + 'lari'nin dogal durdugu.")
    sonuc["failed"] = hatalar
    sonuc["not_verified_by_ear"] = "fades inaudible; L2 endings (cut at full level in 5 verses) not sounding clipped; verse 3 'at' + rest + 'ları' sounding natural"
    with open(os.path.join(V, "dogrulama.json"), "w", encoding="utf8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=1)
    with open(os.path.join(V, "dogrulama.txt"), "w", encoding="utf8") as f:
        f.write("\n".join(satirlar) + "\n")
    sys.exit(1 if hatalar else 0)


if __name__ == "__main__":
    main()
