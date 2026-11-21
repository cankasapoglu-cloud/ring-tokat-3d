#!/usr/bin/env python3
"""vokal_dogal.wav + yerlesim.json dogrulamasi (yalniz olcum; kulakla dinleme YOK).
Cikti: ekrana rapor, yeni3/vokal/dogrulama.txt ve dogrulama.json.
Cikis kodu 0 = butun kontroller gecti."""
import sys, os, json, numpy as np, soundfile as sf, scipy.signal as ss
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *

satirlar, sonuc, hatalar = [], {}, []


def yaz(*a):
    t = " ".join(str(q) for q in a)
    print(t)
    satirlar.append(t)


def kontrol(ad, kosul, ayrinti=""):
    yaz(("  [GECTI] " if kosul else "  [KALDI] ") + ad + ((" -- " + ayrinti) if ayrinti else ""))
    if not kosul:
        hatalar.append(ad)
    return kosul


def kucuk(t):
    t = t.replace("İ", "i").replace("I", "ı").lower()
    return "".join(ch for ch in t if ch.isalpha() or ch == " ")


BEKLENEN_L2 = ["Çiftliğinde inekleri var", "Çiftliğinde koyunları var", "Çiftliğinde bir de atı var", "Çiftliğinde horozları var",
               "Çiftliğinde ördekleri var", "Çiftliğinde köpekleri var", "Çiftliğinde bir kedisi var"]
BEKLENEN_L3 = ["İnekler nasıl bağırır", "Koyunlar nasıl meler", "Atı nasıl kişner", "Horozlar nasıl öter",
               "Ördekler nasıl bağırır", "Köpekler nasıl havlar", "Kedisi nasıl miyavlar"]
BEKLENEN_HECE = {
    1: "A li Ba ba nın bir çift li ği var",
    2: ["Çift li ğin de i nek le ri var", "Çift li ğin de ko yun la rı var", "Çift li ğin de bir de a tı var", "Çift li ğin de ho roz la rı var",
        "Çift li ğin de ör dek le ri var", "Çift li ğin de kö pek le ri var", "Çift li ğin de bir ke di si var"],
    3: ["İ nek ler na sıl ba ğı rır", "Ko yun lar na sıl me ler", "A tı na sıl kiş ner", "Ho roz lar na sıl ö ter",
        "Ör dek ler na sıl ba ğı rır", "Kö pek ler na sıl hav lar", "Ke di si na sıl mi yav lar"],
    4: "Din le bak din le bak"}


def main():
    x = oku_vokal()
    Y = oku_json(CIKTI_JSON)
    K = oku_json(KESIM)
    T = oku_json(TEMPO)
    info = sf.info(CIKTI_WAV)
    yi, sr = sf.read(CIKTI_WAV, dtype="int16")
    y = yi.astype(np.float64) / 32768.0
    F = Y["form"]
    BAR, BEAT = 240.0 / F["bpm"], 60.0 / F["bpm"]
    g = 10 ** (Y["audio"]["global_gain_db"] / 20.0)
    g = 10 ** (-3.0 / 20.0) / (10 ** (Y["audio"]["peak_before_gain_dbfs"] / 20.0)) if False else g
    lines, chunks = Y["lines"], Y["chunks"]
    S = lambda t: int(round(t * SR))

    # ------------------------------------------------------------ 1) bicim
    yaz("== 1) DOSYA BICIMI ==")
    beklenen_n = int(round((64 * BAR + 2.5) * SR))
    kontrol("mono, 44.1 kHz", info.channels == 1 and sr == SR, "%d kanal, %d Hz, %s" % (info.channels, sr, info.subtype))
    kontrol("uzunluk = 64 olcu + 2.5 s", len(y) == beklenen_n, "%d ornek = %.4f s (beklenen %d)" % (len(y), len(y) / SR, beklenen_n))
    tepe = float(np.max(np.abs(y)))
    tepe_db = 20 * np.log10(tepe)
    kontrol("tepe = -3 dBFS (+-0.01)", abs(tepe_db + 3.0) < 0.01, "%.4f dBFS, ornek %d (%.4f s)" % (tepe_db, int(np.argmax(np.abs(y))), np.argmax(np.abs(y)) / SR))
    sonuc["format"] = dict(channels=info.channels, sample_rate=sr, subtype=info.subtype, samples=len(y), duration_sec=round(len(y) / SR, 4), peak_dbfs=round(tepe_db, 4))

    # ------------------------------------------------------------ 2) 7 x 4 dize, sira, olcu
    yaz("== 2) DIZELER: 7 x 4, SIRA, OLCU ==")
    ok_n = len(lines) == 28 and [(L["verse"], L["line"]) for L in lines] == [(v, l) for v in range(1, 8) for l in range(1, 5)]
    kontrol("28 dize, kita/dize sirasi dogru", ok_n)
    olcu_ok, metin_ok, hece_ok = True, True, True
    for L in lines:
        v, l = L["verse"], L["line"]
        bek = 4 + 8 * (v - 1) + {1: 0, 2: 2, 3: 4, 4: 5}[l]
        if L["dest_bar"] != bek or abs(L["dest_bar_downbeat"] - bek * BAR) > 2e-5:
            olcu_ok = False
        bt = {1: "Ali Baba'nın bir çiftliği var", 2: BEKLENEN_L2[v - 1], 3: BEKLENEN_L3[v - 1], 4: "Dinle bak dinle bak"}[l]
        if kucuk(L["text"]) != kucuk(bt):
            metin_ok = False
            yaz("     metin farkli:", v, l, L["text"], "|", bt)
        bh = BEKLENEN_HECE[l] if isinstance(BEKLENEN_HECE[l], str) else BEKLENEN_HECE[l][v - 1]
        if [kucuk(h["text"]) for h in L["syllables"]] != [kucuk(q) for q in bh.split()]:
            hece_ok = False
            yaz("     hece farkli:", v, l, [h["text"] for h in L["syllables"]])
    kontrol("her dize dogru olcude (kita basi 4+8v; L1=0, L2=2, L3=4, L4=5)", olcu_ok)
    kontrol("dize metinleri beklenen sozlerle ayni (6. kita L2 = 'köpekleri')", metin_ok)
    kontrol("hece listeleri beklenenle ayni (toplam %d hece)" % sum(len(L["syllables"]) for L in lines), hece_ok)
    sirali = all(lines[i]["dest_sound_start"] < lines[i + 1]["dest_sound_start"] and lines[i]["dest_sound_end"] <= lines[i + 1]["dest_sound_start"] + 1e-9 for i in range(27))
    kontrol("dizeler hedef zamaninda sirali ve ust uste binmiyor", sirali)
    # hece doseme / kayma tutarliligi
    dos, kay_ok, midi_ok = 0.0, True, True
    for L in lines:
        hs = L["syllables"]
        for a, b in zip(hs[:-1], hs[1:]):
            dos = max(dos, abs(a["dest_end"] - b["dest_start"]))
        for h in hs:
            if h["midi"] is None:
                midi_ok = False
            if not (L["verse"] == 6 and L["line"] == 2):
                if abs((h["dest_start"] - h["src_start"]) - L["shift_sec"]) > 1.5e-4 or abs((h["dest_end"] - h["src_end"]) - L["shift_sec"]) > 1.5e-4:
                    kay_ok = False
    kontrol("heceler diziyi kesintisiz doser (en buyuk bosluk/ortusme %.2f ms)" % (dos * 1000), dos < 2e-4)
    kontrol("hece hedef zamani = kaynak + dizenin kaydirmasi (K6 L2 haric, o parca parca)", kay_ok)
    kontrol("her hecede ozgun MIDI perdesi var", midi_ok)

    # ------------------------------------------------------------ 3) parcalar ornek-ornek kaynakla ayni (perde/sure islemi yok)
    yaz("== 3) ISLEM YOK KANITI: yerlesen ses = kaynak ornekleri x tek kazanc, tam sayili kaydirma ==")
    en_fark, ic_ornek = 0.0, 0
    parcalar = [p for c in chunks for p in c["pieces"]]
    kaplama = np.zeros(len(y), dtype=np.int16)
    for p in parcalar:
        kaplama[p["dest_in_sample"]:p["dest_out_sample"]] += 1
    for p in parcalar:
        a, b, d = p["src_in_sample"], p["src_out_sample"], p["dest_in_sample"]
        ia, ib = a + p["fade_in_samples"], b - p["fade_out_samples"]
        seg_k = np.round(x[ia:ib] * g * 32768.0) / 32768.0
        seg_y = y[d + (ia - a): d + (ib - a)]
        tek = kaplama[d + (ia - a): d + (ib - a)] == 1          # baska parcayla ortusmeyen yerler
        fark = np.abs(seg_k - seg_y)[tek]
        en_fark = max(en_fark, float(fark.max()) * 32768.0)
        ic_ornek += int(tek.sum())
    kontrol("gecis disi butun ornekler kaynakla birebir (en buyuk fark %.2f LSB, %d ornek karsilastirildi)" % (en_fark, ic_ornek), en_fark <= 1.0)
    kazanclar = sorted(set(round(Y["audio"]["global_gain_db"], 3) for _ in parcalar))
    yaz("     tek genel kazanc: %.3f dB (kazanc oncesi tepe %.3f dBFS); dize basina kazanc yok" % (Y["audio"]["global_gain_db"], Y["audio"]["peak_before_gain_dbfs"]))
    # tepe nerede? kaynakta ayni ornek tepe mi?
    it = int(np.argmax(np.abs(y)))
    pt = [p for p in parcalar if p["dest_in_sample"] <= it < p["dest_out_sample"]]
    src_it = pt[0]["src_in_sample"] + (it - pt[0]["dest_in_sample"])
    kontrol("tepe ornegi dogal kaynak ornegi (ortusme toplami degil)", len(pt) == 1 and abs(abs(x[src_it]) * g - tepe) < 2 / 32768.0,
            "%s icinde, kaynak %.4f s, kaynak degeri %.4f" % (pt[0]["label"], src_it / SR, x[src_it]))
    sonuc["identity"] = dict(max_abs_diff_lsb=round(en_fark, 3), samples_compared=ic_ornek, global_gain_db=Y["audio"]["global_gain_db"])

    # ------------------------------------------------------------ 4) ortusme yok, baska yer sessiz
    yaz("== 4) PARCALAR ARASI ORTUSME / SESSIZLIK ==")
    cs = sorted(chunks, key=lambda c: c["dest_in_sample"])
    bosluk = [(cs[i + 1]["dest_in_sample"] - cs[i]["dest_out_sample"]) / SR for i in range(len(cs) - 1)]
    kontrol("21 parca (7 x [L1],[L2],[L3+L4]) ust uste binmiyor", len(cs) == 21 and min(bosluk) > 0, "en kisa ara %.3f s, en uzun %.3f s" % (min(bosluk), max(bosluk)))
    maske = np.zeros(len(y), bool)
    for c in cs:
        maske[c["dest_in_sample"]:c["dest_out_sample"]] = True
    dis = int(np.count_nonzero(yi[~maske]))
    kontrol("parcalarin disinda her ornek tam sifir", dis == 0, "sifir olmayan %d ornek; parcalarin toplam suresi %.2f s / %.2f s" % (dis, maske.sum() / SR, len(y) / SR))
    ilk = cs[0]["dest_in"]
    kontrol("ilk ses giris bolumunden (4 olcu = %.4f s) sonra degil, hemen once baslar" % (4 * BAR), 4 * BAR - 0.2 < ilk < 4 * BAR, "ilk parca %.4f s" % ilk)
    sonuc["overlap"] = dict(chunks=len(cs), min_gap_sec=round(min(bosluk), 4), nonzero_outside=dis)

    # ------------------------------------------------------------ 5) kesim kenarlari
    yaz("== 5) KESIM KENARLARINDA ENERJI ==")
    yaz("   parca       | kenar: ilk/son 3 ms RMS (yerlesmis dosya, dBFS -> dize RMS'ine gore dB) | kaynakta kesim aninda +-3 ms RMS (dBFS -> dize RMS'ine gore) | ilk/son ornek (LSB)")
    en_kotu_yer, en_kotu_ham, kenarlar = -999.0, -999.0, []
    n3 = S(0.003)
    for c in chunks:
        Ls = [L for L in lines if L["chunk"] == c["id"]]
        r_in, r_out = Ls[0]["src_rms_dbfs"], Ls[-1]["src_rms_dbfs"]
        a, b = c["dest_in_sample"], c["dest_out_sample"]
        e_in = db(np.sqrt(np.mean(y[a:a + n3] ** 2))) - Y["audio"]["global_gain_db"]
        e_out = db(np.sqrt(np.mean(y[b - n3:b] ** 2))) - Y["audio"]["global_gain_db"]
        h_in = rms_db(x, c["src_cut_in"] - 0.003, c["src_cut_in"] + 0.003)
        cut_out_src = c["src_cut_out"]
        h_out = rms_db(x, cut_out_src - 0.003, cut_out_src + 0.003)
        # gecis penceresinin dis ucundaki ham duzey (yerlesen sesin basladigi / bittigi an)
        u_in = rms_db(x, c["fade_in"]["src_from"] - 0.003, c["fade_in"]["src_from"] + 0.003)
        u_out = rms_db(x, c["fade_out"]["src_to"] - 0.003, c["fade_out"]["src_to"] + 0.003)
        kenarlar.append(dict(chunk=c["id"], placed_edge_in_db_re_line=round(e_in - r_in, 1), placed_edge_out_db_re_line=round(e_out - r_out, 1),
                             raw_at_cut_in_dbfs=round(h_in, 1), raw_at_cut_out_dbfs=round(h_out, 1),
                             raw_at_cut_in_db_re_line=round(h_in - r_in, 1), raw_at_cut_out_db_re_line=round(h_out - r_out, 1),
                             first_sample_lsb=int(yi[a]), last_sample_lsb=int(yi[b - 1])))
        en_kotu_yer = max(en_kotu_yer, e_in - r_in, e_out - r_out)
        en_kotu_ham = max(en_kotu_ham, h_in - r_in, h_out - r_out)
        yaz("   %-9s giris %6.1f dBFS (%6.1f dB) cikis %6.1f dBFS (%6.1f dB) | ham giris %6.1f (%6.1f) cikis %6.1f (%6.1f) | %d / %d" % (
            c["id"], e_in, e_in - r_in, e_out, e_out - r_out, h_in, h_in - r_in, h_out, h_out - r_out, yi[a], yi[b - 1]))
    kontrol("yerlesmis dosyada her parca kenari (ilk/son 3 ms) dize RMS'inin en az 40 dB altinda", en_kotu_yer <= -40.0, "en kotu %.1f dB" % en_kotu_yer)
    taban = K["noise_floor"]["gap_rms_dbfs"]
    ham_ok = [k for k in kenarlar if k["raw_at_cut_in_db_re_line"] > -40 or k["raw_at_cut_out_db_re_line"] > -40]
    yaz("     kaynakta (gecis uygulanmadan once) kesim anindaki ham duzey: en kotu %.1f dB (dize RMS'ine gore); -40 dB'yi saglamayan parca kenari olan parcalar: %s"
        % (en_kotu_ham, ", ".join(k["chunk"] for k in ham_ok) or "yok"))
    yaz("     (bu dar bosluklarda ham duzey -40 dB'ye inmiyor; gecis uygulandiktan sonra yerlesmis dosyadaki kenar yukaridaki gibi)")
    ilk_son = max(max(abs(k["first_sample_lsb"]), abs(k["last_sample_lsb"])) for k in kenarlar)
    kontrol("parcalarin ilk ve son ornegi sifira yakin (tik yok)", ilk_son <= 2, "en buyuk |deger| %d LSB" % ilk_son)
    sz = max(max(c["fade_in"]["leak_db_re_line_rms"], c["fade_out"]["leak_db_re_line_rms"]) for c in chunks)
    ks = max(max(c["fade_in"]["loss_db_re_line_rms"], c["fade_out"]["loss_db_re_line_rms"]) for c in chunks)
    fmin = min(min(c["fade_in"]["ms"], c["fade_out"]["ms"]) for c in chunks)
    fmax = max(max(c["fade_in"]["ms"], c["fade_out"]["ms"]) for c in chunks)
    kontrol("kenar gecisleri 15-30 ms", fmin >= 14.95 and fmax <= 30.05, "en kisa %.1f ms, en uzun %.1f ms" % (fmin, fmax))
    kontrol("komsu dizeden sizan enerji dize RMS'inin en az 40 dB altinda", sz <= -40, "en kotu %.1f dB" % sz)
    kontrol("gecisin kendi dizesinden kistigi enerji dize RMS'inin en az 35 dB altinda (kelime kirpilmiyor)", ks <= -35, "en kotu %.1f dB" % ks)
    # kelime kirpilmadi: her dizenin ses araligindaki enerji kaynakla ayni
    en_e = 0.0
    for L in lines:
        if L["verse"] == 6 and L["line"] == 2:
            continue
        a0, a1 = S(L["src_sound_start"]), S(L["src_sound_end"])
        d0 = a0 + L["shift_samples"]
        ek = db(np.sqrt(np.mean((x[a0:a1] * g) ** 2)))
        ey = db(np.sqrt(np.mean(y[d0:d0 + (a1 - a0)] ** 2)))
        en_e = max(en_e, abs(ek - ey))
    kontrol("her dizenin ses araligindaki RMS kaynakla ayni (kelime eksigi yok; K6 L2 ayrica)", en_e < 0.05, "en buyuk fark %.3f dB" % en_e)
    sonuc["edges"] = dict(worst_placed_edge_db_re_line_rms=round(en_kotu_yer, 1), worst_raw_cut_level_db_re_line_rms=round(en_kotu_ham, 1),
                          worst_leak_db_re_line_rms=sz, worst_loss_db_re_line_rms=ks, fade_ms_min=fmin, fade_ms_max=fmax,
                          stem_noise_floor_dbfs=taban, max_first_last_sample_lsb=ilk_son, per_chunk=kenarlar)

    # ------------------------------------------------------------ 6) baslangic anlari: olculen - amaclanan
    yaz("== 6) BASLANGIC ANLARI (yerlesmis dosyada olculen - amaclanan) ==")
    NFv, HPv = 512, 32

    def ozellik(sig):
        f, t, Z = ss.stft(sig, SR, window="hann", nperseg=NFv, noverlap=NFv - HPv, boundary="zeros", padded=True)
        Sm = np.abs(Z)
        band = (f >= 90) & (f <= 8000)
        Lg = np.log1p(100.0 * Sm[band])
        fl = np.maximum(np.diff(Lg, axis=1, prepend=Lg[:, :1]), 0).sum(0)
        k5 = np.hanning(9); k5 /= k5.sum()
        sm = np.convolve(fl, k5, mode="same"); sm /= np.percentile(sm, 99.5)
        n = int(SR * 5.0 / 1000)
        eb5 = 20 * np.log10(np.sqrt(np.convolve(sig ** 2, np.ones(n) / n, mode="same")) + 1e-7)
        sos = ss.butter(4, [90, 1200], btype="band", fs=SR, output="sos")
        ev = 20 * np.log10(np.sqrt(np.convolve(ss.sosfiltfilt(sos, sig) ** 2, np.ones(n) / n, mode="same")) + 1e-7)
        return t, sm, eb5, ev

    def akustik_baslangic(oz, t0, pre=0.09, post=0.03):
        """tempo analizindeki (11_lines.py) acoustic_onset ile ayni tanim."""
        t, sm, eb5, ev = oz
        a, b = int((t0 - pre) * SR), int((t0 + post) * SR)
        seg = eb5[a:b]; mn = seg.min()
        idx = np.where((seg <= mn + 1.0) | (seg <= -70.0))[0]; t_dip = (a + idx[-1]) / SR
        w = (t >= t_dip) & (t <= t_dip + 0.08); tw = t[w]; sw = sm[w]
        thr = 0.5 * sw.max()
        for k in range(1, len(sw) - 1):
            if sw[k] >= thr and sw[k] >= sw[k - 1] and sw[k] >= sw[k + 1]:
                y0, y1, y2 = sw[k - 1], sw[k], sw[k + 1]
                d = 0.0 if (y0 - 2 * y1 + y2) == 0 else 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
                return float(tw[k] + d * HPv / SR)
        return float(tw[int(np.argmax(sw))])

    def unlu_baslangic(oz, t_on):
        t, sm, eb5, ev = oz
        a, b = int(t_on * SR), int((t_on + 0.15) * SR); pk = ev[a:b].max()
        return float((a + np.where(ev[a:b] >= pk - 6.0)[0][0]) / SR)

    oz_k, oz_y = ozellik(x), ozellik(y / g)
    tl = {(L["verse"], L["line"]): L for L in T["lines"]}
    # once: tasinan algilayici kaynakta tempo.json degerlerini veriyor mu?
    port = max(abs(akustik_baslangic(oz_k, q["word_start_from_words_file"]) - q["onset"]) for q in T["lines"])
    kontrol("algilayici kaynakta tempo.json 'onset' degerlerini yeniden uretiyor", port < 3e-4, "en buyuk fark %.3f ms" % (port * 1000))
    yaz("   dize   amaclanan   olculen   fark(ms) | unlu: amaclanan  olculen  fark(ms) | olcu basina gore ofset: kullanilan / tempo analizi (ms)")
    farklar, ufark, of_fark, tablo = [], [], [], []
    for L in lines:
        t0 = L["src_first_word_start_words_file"] + L["shift_sec"]
        m = akustik_baslangic(oz_y, t0)
        mv = unlu_baslangic(oz_y, m)
        f1, f2 = (m - L["dest_onset"]) * 1000, (mv - L["dest_first_vowel_onset"]) * 1000
        farklar.append(f1); ufark.append(f2)
        of_fark.append((L["offset_used_sec"] - L["offset_from_tempo_analysis_sec"]) * 1000)
        tablo.append(dict(verse=L["verse"], line=L["line"], intended_onset=L["dest_onset"], measured_onset=round(m, 5), error_ms=round(f1, 3),
                          intended_vowel_onset=L["dest_first_vowel_onset"], measured_vowel_onset=round(mv, 5), vowel_error_ms=round(f2, 3),
                          measured_offset_from_bar_ms=round((m - L["dest_bar_downbeat"]) * 1000, 2)))
        yaz("   K%d L%d  %9.4f  %9.4f  %+6.2f   |      %9.4f  %9.4f  %+6.2f   | %+6.1f / %+6.1f" % (
            L["verse"], L["line"], L["dest_onset"], m, f1, L["dest_first_vowel_onset"], mv, f2, L["offset_used_sec"] * 1000, L["offset_from_tempo_analysis_sec"] * 1000))
    mx, mxv, mxo = max(abs(q) for q in farklar), max(abs(q) for q in ufark), max(abs(q) for q in of_fark)
    kontrol("olculen baslangic - amaclanan: en buyuk hata 2 ms'nin altinda", mx < 2.0, "en buyuk %.3f ms (akustik baslangic), %.3f ms (ilk unlu)" % (mx, mxv))
    kontrol("kullanilan ofset = tempo analizinin dize ofseti (yarim ornek + 4 basamak yuvarlama icinde)", mxo < 0.15, "en buyuk fark %.3f ms" % mxo)
    # capraz korelasyonla kayma: yerlesen dize kaynaga gore tam amaclanan kadar kaymis mi?
    en_kay = 0
    for L in lines:
        if L["verse"] == 6 and L["line"] == 2:
            continue
        a0 = S(L["src_first_vowel_onset"]); n = S(0.25)
        ref = x[a0:a0 + n]
        d0 = a0 + L["shift_samples"]
        ara = y[d0 - 400:d0 + n + 400]
        cc = np.correlate(ara, ref, mode="valid")
        en_kay = max(en_kay, abs(int(np.argmax(cc)) - 400))
    kontrol("capraz korelasyon: her dize amaclanan konumda (0 ornek sapma)", en_kay == 0, "en buyuk sapma %d ornek" % en_kay)
    sonuc["onsets"] = dict(max_abs_error_ms=round(mx, 3), max_abs_vowel_error_ms=round(mxv, 3), max_abs_offset_vs_tempo_analysis_ms=round(mxo, 3),
                           xcorr_max_lag_error_samples=en_kay, detector_port_check_ms=round(port * 1000, 3), per_line=tablo)

    # ------------------------------------------------------------ 7) 6. kita onarimlari
    yaz("== 7) 6. KITA ONARIMLARI ==")
    import pyworld as pw

    def f0_midi(sig, t0, t1):
        """[t0,t1] araliginda harvest f0 ortancasi (MIDI) ve sesli cerceve orani."""
        a, b = S(t0 - 0.05), S(t1 + 0.05)
        f0, tt = pw.harvest(np.ascontiguousarray(sig[a:b]), SR, f0_floor=150.0, f0_ceil=700.0, frame_period=5.0)
        tt = tt + a / SR
        m = (tt >= t0) & (tt <= t1)
        v = f0[m]; v = v[v > 0]
        if len(v) == 0:
            return None, 0.0
        return float(69 + 12 * np.log2(np.median(v) / 440.0)), float(len(v) / max(1, m.sum()))

    def sicrama(t0, t1):
        a, b = S(t0), S(t1)
        return float(np.max(np.abs(np.diff(y[a:b]))))

    L2 = [L for L in lines if L["verse"] == 6 and L["line"] == 2][0]
    L3 = [L for L in lines if L["verse"] == 6 and L["line"] == 3][0]
    L4 = [L for L in lines if L["verse"] == 6 and L["line"] == 4][0]
    hs = {h["text"] + str(i): h for i, h in enumerate(L2["syllables"])}
    de, ko, pek, le = L2["syllables"][3], L2["syllables"][4], L2["syllables"][5], L2["syllables"][6]
    rp = {r["id"]: r for r in Y["repairs"]}
    ra = rp["K6_L2_kopekleri"]
    sh2 = L2["shift_sec"]
    # --- (a) ek yerleri
    t_dek = ra["de_fade_out"]["src_to"] + sh2                    # 'de' sonumlemesinin bitisi = 'kö' parcasinin girisi
    t_ek = ra["splice"]["centre_dest_time"]
    j1 = sicrama(t_dek - 0.030, t_dek + 0.012)
    j2 = sicrama(t_ek - 0.008, t_ek + 0.008)
    dogal = sicrama(L2["dest_sound_start"], L2["dest_sound_end"])
    yaz("   (a) L2 'köpekleri':")
    kontrol("    'de' -> kapanis -> 'kö' birlesiminde ornek sicramasi < 0.05", j1 < 0.05, "en buyuk |fark| %.5f (tam olcek); dizenin dogal en buyuk ornek farki %.4f" % (j1, dogal))
    kontrol("    'pek' | 'le' capraz gecisinde ornek sicramasi < 0.05", j2 < 0.05, "en buyuk |fark| %.6f" % j2)
    lv_k1 = db(np.sqrt(np.mean(y[S(t_dek + 0.001):S(t_dek + 0.010)] ** 2))) - Y["audio"]["global_gain_db"]
    lv_k2 = db(np.sqrt(np.mean(y[S(t_ek - 0.004):S(t_ek + 0.004)] ** 2))) - Y["audio"]["global_gain_db"]
    yaz("     kapanis duzeyleri (kaynak olceginde): 'de' ile 'kö' arasi %.1f dBFS, 'pek' ile 'le' arasi (capraz gecis) %.1f dBFS" % (lv_k1, lv_k2))
    kontrol("    iki ek de sessiz /k/ kapanisinin icinde (< -55 dBFS)", lv_k1 < -55 and lv_k2 < -55)
    # RMS ve perde: iki yan
    def cek(h):
        return h["dest_core_start"], h["dest_core_end"]
    olc = {}
    for ad, h in (("de", de), ("kö", ko), ("pek", pek), ("le", le)):
        c0, c1 = cek(h)
        m, vr = f0_midi(y, c0, c1)
        olc[ad] = dict(rms_dbfs=round(db(np.sqrt(np.mean(y[S(c0):S(c1)] ** 2))) - Y["audio"]["global_gain_db"], 1), midi=None if m is None else round(m, 2),
                       core_ms=round((c1 - c0) * 1000, 0), json_midi=h["midi"])
    yaz("     hece cekirdekleri (yerlesmis dosyada olculdu; RMS kaynak olceginde): " + "; ".join(
        "%s %.1f dBFS, MIDI %s (json %s), cekirdek %d ms" % (k, v["rms_dbfs"], v["midi"], v["json_midi"], v["core_ms"]) for k, v in olc.items()))
    kontrol("    'de'|'kö' iki yaninda RMS benzer (fark < 3 dB)", abs(olc["de"]["rms_dbfs"] - olc["kö"]["rms_dbfs"]) < 3.0, "fark %.1f dB" % (olc["kö"]["rms_dbfs"] - olc["de"]["rms_dbfs"]))
    kontrol("    'pek'|'le' iki yaninda RMS benzer (fark < 3 dB)", abs(olc["pek"]["rms_dbfs"] - olc["le"]["rms_dbfs"]) < 3.0, "fark %.1f dB" % (olc["le"]["rms_dbfs"] - olc["pek"]["rms_dbfs"]))
    kontrol("    'pek'|'le' iki yaninda perde benzer (fark < 1.5 yarim ses)", abs(olc["pek"]["midi"] - olc["le"]["midi"]) < 1.5, "pek %.2f -> le %.2f (ozgun 'dek' 63.99 -> 'le' 65.04)" % (olc["pek"]["midi"], olc["le"]["midi"]))
    pd = olc["kö"]["midi"] - olc["de"]["midi"]
    yaz("     [BILGI] 'de' %.2f -> 'kö' %.2f: %.2f yarim ses (BILINEN: 'kö' D4'te soylenmis; bu adimda perde islemi yok, duzeltilmedi)" % (olc["de"]["midi"], olc["kö"]["midi"], pd))
    kontrol("    olculen perdeler json'daki ozgun perdelerle ayni (+-0.3 yarim ses): perde degismedi", all(abs(v["midi"] - v["json_midi"]) < 0.3 for v in olc.values()))
    # zamanlama: 'leri var' yerinde mi?
    var = L2["syllables"][-1]
    kontrol("    'leri var' ozgun yerinde (kayma 0)", abs((var["dest_start"] - var["src_start"]) - sh2) < 1e-4 and abs((le["dest_end"] - le["src_end"]) - sh2) < 1e-4,
            "'var' unlu baslangici olcu icinde %.3f vurus (diger kitalarda 2.996-3.053)" % var["vowel_onset_beats_in_bar"])
    yaz("     vurus konumlari (unlu baslangici): de %.3f, kö %.3f (ozgun 'ör' 1.557), pek %.3f (ozgun 'dek' 2.032; diger kitalarda 2. hece 1.919-2.046), le %.3f, ri %.3f, var %.3f"
        % (de["vowel_onset_beats_in_bar"], ko["vowel_onset_beats_in_bar"], pek["vowel_onset_beats_in_bar"], le["vowel_onset_beats_in_bar"],
           L2["syllables"][7]["vowel_onset_beats_in_bar"], var["vowel_onset_beats_in_bar"]))
    yaz("     kelime suresi: ozgun 'ördekleri' %.4f s, yeni 'köpekleri' %.4f s (/k/ patlamasi unluden 47 ms once basladigi icin); 'de' hecesi %.0f ms (ozgun 140 ms)"
        % (ra["word_duration"]["old_ordekleri_sec"], ra["word_duration"]["new_kopekleri_sec"], (de["dest_end"] - de["dest_start"]) * 1000))
    sonuc["repair_K6_L2"] = dict(max_sample_jump_de_ko=round(j1, 5), max_sample_jump_pek_le=round(j2, 6), natural_max_sample_diff_in_line=round(dogal, 4),
                                 closure_level_de_ko_dbfs=round(lv_k1, 1), closure_level_pek_le_dbfs=round(lv_k2, 1), syllables=olc,
                                 pitch_step_de_to_ko_semitones=round(pd, 2), tail_shift_ms=0.0,
                                 vowel_onset_beats=dict(de=de["vowel_onset_beats_in_bar"], ko=ko["vowel_onset_beats_in_bar"], pek=pek["vowel_onset_beats_in_bar"],
                                                        le=le["vowel_onset_beats_in_bar"], var=var["vowel_onset_beats_in_bar"]))
    # --- (b) L4
    rb = [r for r in Y["repairs"] if r["id"].startswith("K6_L4")][0]
    tj = rb["crossfade"]["centre_dest_time"]
    j3 = sicrama(tj - 0.010, tj + 0.010)
    yaz("   (b) L4 <- %d. kitanin L4'u:" % rb["donor_verse"])
    kontrol("    L3 | verici L4 capraz gecisinde ornek sicramasi < 0.05", j3 < 0.05, "en buyuk |fark| %.5f" % j3)
    lar, din = L3["syllables"][-1], L4["syllables"][0]
    r_once = db(np.sqrt(np.mean(y[S(tj - 0.035):S(tj - 0.005)] ** 2))) - Y["audio"]["global_gain_db"]
    r_sonra = db(np.sqrt(np.mean(y[S(tj + 0.005):S(tj + 0.035)] ** 2))) - Y["audio"]["global_gain_db"]
    r_orta = db(np.sqrt(np.mean(y[S(tj - 0.005):S(tj + 0.005)] ** 2))) - Y["audio"]["global_gain_db"]
    m_once, v_once = f0_midi(y, tj - 0.060, tj - 0.008)
    m_sonra, v_sonra = f0_midi(y, tj + 0.008, tj + 0.034)
    m_lar, _ = f0_midi(y, lar["dest_core_start"], lar["dest_core_end"])
    m_din, _ = f0_midi(y, din["dest_core_start"], din["dest_core_end"])
    e_lar = db(np.sqrt(np.mean(y[S(lar["dest_core_start"]):S(lar["dest_core_end"])] ** 2))) - Y["audio"]["global_gain_db"]
    e_din = db(np.sqrt(np.mean(y[S(din["dest_core_start"]):S(din["dest_core_end"])] ** 2))) - Y["audio"]["global_gain_db"]
    yaz("     gecisin 30 ms oncesi (K6 /r/ mirildanmasi) %.1f dBFS, ortasi (10 ms) %.1f dBFS, 30 ms sonrasi (verici /d/ kapanisi) %.1f dBFS" % (r_once, r_orta, r_sonra))
    yaz("     perde: gecis oncesi mirildanma MIDI %s (sesli oran %.2f), sonrasi %s (sesli oran %.2f)" % (
        None if m_once is None else round(m_once, 2), v_once, None if m_sonra is None else round(m_sonra, 2), v_sonra))
    yaz("     hece cekirdekleri: 'lar' %.1f dBFS MIDI %.2f -> 'Din' %.1f dBFS MIDI %.2f" % (e_lar, m_lar, e_din, m_din))
    # dogal karsilastirma: diger kitalarda L3 son hece -> L4 ilk hece
    dg = []
    for v in range(1, 8):
        a = [L for L in lines if L["verse"] == v and L["line"] == 3][0]["syllables"][-1]
        b = K["verses"][v - 1]["lines"][3]["syllables"][0]
        dg.append((v, a["midi"], b["f0_midi"], K["verses"][v - 1]["lines"][2]["rms_dbfs"], K["verses"][v - 1]["lines"][3]["rms_dbfs"]))
    yaz("     dogal ornekler (ozgun kayit) L3 son hece -> L4 'Din' MIDI: " + ", ".join("K%d %.2f->%.2f" % (q[0], q[1], q[2]) for q in dg))
    yaz("     dogal ornekler L3 RMS -> L4 RMS (dBFS): " + ", ".join("K%d %.1f->%.1f" % (q[0], q[3], q[4]) for q in dg))
    adim = m_din - m_lar
    dogal_adim = [q[2] - q[1] for q in dg]
    kontrol("    'lar' -> 'Din' perde adimi dogal araligin icinde", min(dogal_adim) - 0.3 <= adim <= max(dogal_adim) + 0.3,
            "%.2f yarim ses (ozgun kitalarda %.2f .. %.2f)" % (adim, min(dogal_adim), max(dogal_adim)))
    kontrol("    'lar' -> 'Din' RMS farki < 3 dB", abs(e_din - e_lar) < 3.0, "%.1f dB" % (e_din - e_lar))
    kontrol("    gecisin iki yanindaki mirildanma duzeyi benzer (fark < 12 dB) ve gecis ortasi iki yandan yuksek degil",
            abs(r_once - r_sonra) < 12.0 and r_orta <= max(r_once, r_sonra) + 1.0, "once %.1f, orta %.1f, sonra %.1f dBFS" % (r_once, r_orta, r_sonra))
    son_bak = L4["syllables"][-1]
    m_bak, _ = f0_midi(y, son_bak["dest_core_start"], son_bak["dest_core_end"])
    kontrol("    yeni L4'un son 'bak'i C4'te (+-0.5 yarim ses)", abs(m_bak - 60.0) < 0.5, "MIDI %.2f (6. kitanin kendi son 'bak'i 62.11 = D4 idi)" % m_bak)
    kontrol("    verici L4, K6'nin L4 olcu cizgisinde (ofset vericinin kendi ofseti)", abs(L4["offset_used_sec"] - tl[(rb["donor_verse"], 4)]["offset_sec"]) < 2e-4,
            "ofset %.1f ms (K6'nin kendi L4'u %.1f ms idi)" % (L4["offset_used_sec"] * 1000, tl[(6, 4)]["offset_sec"] * 1000))
    # K6'nin kendi L4'u dosyada yok mu? (kendi /d/ patlamasi ve sonrasi kullanilmadi)
    c6 = [c for c in chunks if c["id"] == "K6_L3+4"][0]
    kontrol("    K6'nin kendi L4'unden ornek kullanilmadi", c6["pieces"][0]["src_out"] <= 80.1481, "K6 parcasi kaynakta %.4f s'de bitiyor (kendi /d/ patlamasi 80.150)" % c6["pieces"][0]["src_out"])
    sonuc["repair_K6_L4"] = dict(max_sample_jump=round(j3, 5), rms_before_dbfs=round(r_once, 1), rms_centre_dbfs=round(r_orta, 1), rms_after_dbfs=round(r_sonra, 1),
                                 murmur_midi_before=None if m_once is None else round(m_once, 2), murmur_midi_after=None if m_sonra is None else round(m_sonra, 2),
                                 lar_midi=round(m_lar, 2), din_midi=round(m_din, 2), lar_rms_dbfs=round(e_lar, 1), din_rms_dbfs=round(e_din, 1),
                                 final_bak_midi=round(m_bak, 2), natural_L3last_to_L4first=[dict(verse=q[0], from_midi=q[1], to_midi=q[2]) for q in dg])

    # ------------------------------------------------------------ 8) 3. kita ek sesi
    yaz("== 8) 3. KITA L4 SONUNDAKI FAZLADAN SES ==")
    if not Y["options"]["k3_after_sound_kept"]:
        ex = K["verses"][2]["lines"][3]["ending"]["extra_voiced_sound"]
        L34 = [L for L in lines if L["verse"] == 3 and L["line"] == 4][0]
        a, b = S(ex["start"] + L34["shift_sec"]), S(ex["end"] + L34["shift_sec"])
        kontrol("fazladan sesin hedefteki yeri tam sessiz", int(np.count_nonzero(yi[a:b])) == 0, "%.4f-%.4f s (olcu 6'nin basi %.4f s)" % (a / SR, b / SR, (L34["dest_bar"] + 1) * BAR))
        kontrol("son 'bak'in unlusu eksiksiz (kesim sessiz /k/ kapanisinin icinde)", L34["src_out"] > ex["silent_gap_before"][0] + 0.03 and L34["src_out"] < ex["start"],
                "kaynak kesim %.4f; unlu sonu %.4f; ek ses %.4f" % (L34["src_out"], ex["silent_gap_before"][0], ex["start"]))
    else:
        yaz("  (ek ses bilerek birakildi)")

    # ------------------------------------------------------------ ozet
    yaz("")
    yaz("SONUC: " + ("TUM KONTROLLER GECTI" if not hatalar else "KALAN KONTROLLER: " + "; ".join(hatalar)))
    yaz("Not: bunlarin hepsi olcumdur; ses kulakla DINLENMEDI. 'de|kö' eki ile L3|L4 ekinin kulaga dogal gelip gelmedigi dogrulanmadi.")
    sonuc["all_passed"] = not hatalar
    sonuc["failed"] = hatalar
    with open(os.path.join(V, "dogrulama.txt"), "w", encoding="utf8") as f:
        f.write("\n".join(satirlar) + "\n")
    with open(os.path.join(V, "dogrulama.json"), "w", encoding="utf8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=1)
    return 0 if not hatalar else 1


if __name__ == "__main__":
    sys.exit(main())
