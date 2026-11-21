#!/usr/bin/env python3
"""4. adim: kesim.json'un bagimsiz dogrulamasi - dogrudan ham WAV orneklerinden (ozellik.npz kullanilmaz).
Cikti: dogrulama.txt (bu betigin ciktisi) + ornek/*.wav (ek yerlerinin denenmesi; KULAKLA DINLENMEDI).
Hata bulunursa cikis kodu 1."""
import os, sys, json, numpy as np, soundfile as sf

K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.dirname(os.path.dirname(os.path.dirname(K)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import kucuk, UNLU, BEKLENEN_HECE, L1, L2, L3, L4, kelimeleri_oku

d = json.load(open(os.path.join(K, "kesim.json"), encoding="utf8"))
x, fs = sf.read(os.path.join(A, "dinle_2_vokal.wav"))
if x.ndim > 1:
    x = x.mean(axis=1)
satirlar = []; hata = []


def yaz(*a):
    s = " ".join(str(q) for q in a); print(s); satirlar.append(s)


def kontrol(kosul, mesaj):
    if not kosul:
        hata.append(mesaj); yaz("  !! HATA:", mesaj)


def db(a, b):
    seg = x[max(0, int(a * fs)):int(b * fs)]
    return float(10 * np.log10(np.mean(seg ** 2) + 1e-20)) if len(seg) else -200.0


def tepe(a, b):
    seg = x[max(0, int(a * fs)):int(b * fs)]
    return float(20 * np.log10(np.abs(seg).max() + 1e-12)) if len(seg) else -200.0


V = d["verses"]
# ---------------------------------------------------------------- 1) yapi
yaz("== 1) YAPI ==")
kontrol(len(V) == 7, "7 kita degil")
nh = nk = 0
for v, kt in enumerate(V):
    kontrol(len(kt["lines"]) == 4, "K%d: 4 dize degil" % (v + 1))
    for dz, ln in enumerate(kt["lines"]):
        bek = [L1, L2[v], L3[v], L4][dz]
        kontrol(ln["text"] == bek, "K%d L%d metin" % (v + 1, dz + 1))
        b = BEKLENEN_HECE["L%d" % (dz + 1)]; b = b if isinstance(b, str) else b[v]
        bh = [kucuk(h) for w_ in b.split() for h in w_.split("-")]
        gh = [kucuk(s_["text"]) for s_ in ln["syllables"]]
        kontrol(bh == gh, "K%d L%d hece dizisi %s != %s" % (v + 1, dz + 1, gh, bh))
        for s_ in ln["syllables"]:
            kontrol(sum(c in UNLU for c in kucuk(s_["text"])) == 1, "tek unlu degil: " + s_["text"])
        nh += len(ln["syllables"]); nk += len(ln["words"])
yaz("kita %d, dize %d, kelime %d, hece %d" % (len(V), sum(len(k_["lines"]) for k_ in V), nk, nh))
kontrol(nh == 226 and nk == 108, "sayim: %d hece, %d kelime" % (nh, nk))

# ---------------------------------------------------------------- 2) zaman tutarliligi
yaz("\n== 2) ZAMAN TUTARLILIGI ==")
enkisa = (9, None); onceki_bit = 0.0
for v, kt in enumerate(V):
    for dz, ln in enumerate(kt["lines"]):
        S = ln["syllables"]
        kontrol(abs(S[0]["start"] - ln["start"]) < 1e-3 and abs(S[-1]["end"] - ln["end"]) < 1e-3, "K%d L%d hece-dize ucu" % (v + 1, dz + 1))
        kontrol(ln["start"] >= onceki_bit - 1e-3, "K%d L%d onceki dizeyle cakisiyor" % (v + 1, dz + 1)); onceki_bit = ln["end"]
        for a_, b_ in zip(S[:-1], S[1:]):
            kontrol(abs(a_["end"] - b_["start"]) < 1e-3, "K%d L%d bosluk/cakisma %s|%s" % (v + 1, dz + 1, a_["text"], b_["text"]))
        for s_ in S:
            sure = s_["end"] - s_["start"]
            kontrol(sure >= 0.05, "K%d L%d %s cok kisa (%.0f ms)" % (v + 1, dz + 1, s_["text"], sure * 1000))
            kontrol(s_["start"] - 0.012 <= s_["nucleus"] <= s_["end"] + 0.002, "cekirdek hece disinda: " + s_["text"])
            if sure < enkisa[0]:
                enkisa = (sure, "K%d L%d %s" % (v + 1, dz + 1, s_["text"]))
        W = ln["words"]
        for w_ in W:
            ws = [s_ for s_ in S if s_["word_index"] == W.index(w_)]
            kontrol(abs(ws[0]["start"] - w_["start"]) < 1e-3 and abs(ws[-1]["end"] - w_["end"]) < 1e-3, "kelime-hece ucu " + w_["text"])
yaz("en kisa hece: %.0f ms (%s)" % (enkisa[0] * 1000, enkisa[1]))
# kelime sinirlari yazi dokumundeki boslukla uyumlu mu
sap = []
for v, kt in enumerate(V):
    for dz, ln in enumerate(kt["lines"]):
        W = ln["words"]
        for a_, b_ in zip(W[:-1], W[1:]):
            t = a_["end"]; g0, g1 = a_["json_end"], b_["json_start"]
            dis = 0.0 if g0 <= t <= g1 else min(abs(t - g0), abs(t - g1))
            sap.append((dis, "K%d L%d %s|%s t=%.3f bosluk=[%.2f,%.2f]" % (v + 1, dz + 1, a_["text"], b_["text"], t, g0, g1)))
sap.sort(reverse=True)
yaz("kelime siniri - yazi dokumu boslugu: %d sinirin %d'i boslugun icinde; disarida kalanlarin en buyuk 5 sapmasi:" % (
    len(sap), sum(1 for s_ in sap if s_[0] == 0)))
for s_ in sap[:5]:
    yaz("   %.0f ms  %s" % (s_[0] * 1000, s_[1]))
kontrol(sap[0][0] <= 0.06, "kelime siniri yazi dokumunden 60 ms'den fazla sapiyor: " + sap[0][1])

# ---------------------------------------------------------------- 3) kesim noktalari (ham orneklerden)
yaz("\n== 3) KESIM NOKTALARI: +-3 ms RMS (dBFS), ham WAV ==")
sung = d["noise_floor"]["sung_rms_dbfs"]
for v, kt in enumerate(V):
    s = "K%d " % (v + 1)
    for c in kt["chunks"]:
        ci, co = c["cut_in"], c["cut_out"]
        li, lo = db(ci - 0.003, ci + 0.003), db(co - 0.003, co + 0.003)
        s += " L%s: giris %.3f (%.0f dB) cikis %.3f (%.0f dB) |" % ("+".join(map(str, c["lines"])), ci, li, co, lo)
        kontrol(ci < c["start"] and co >= c["end"] - 1e-6, "K%d parca %s kesim sirasi" % (v + 1, c["lines"]))
        kontrol(li < sung - 30 and lo < sung - 30, "K%d parca %s kesim noktasi sessiz degil (%.0f / %.0f dBFS)" % (v + 1, c["lines"], li, lo))
        # parcayi kes: ilk / son 3 ms'deki en buyuk ornek
        kontrol(tepe(ci, ci + 0.003) < -40 and tepe(co - 0.003, co) < -40, "K%d parca %s ucunda tik riski" % (v + 1, c["lines"]))
    yaz(s)
yaz("L3|L4 ic sinirlarinin duzeyi (kesim noktasi DEGIL): " + ", ".join(
    "K%d %.0f dB" % (v + 1, db(kt["lines"][3]["start"] - 0.003, kt["lines"][3]["start"] + 0.003)) for v, kt in enumerate(V)))

# ---------------------------------------------------------------- 4) perde
yaz("\n== 4) PERDE (hece cekirdegi ortancasi, MIDI; E4=64 D4=62 C4=60) ==")
import pyworld as pw
far = []
for v, kt in enumerate(V):
    s = "K%d " % (v + 1)
    for dz, ln in enumerate(kt["lines"]):
        m = [s_["f0_midi"] for s_ in ln["syllables"]]
        kontrol(all(q is not None and 56 < q < 68 for q in m), "K%d L%d perde araligi disi %s" % (v + 1, dz + 1, m))
        s += " L%d ort %.2f [%.1f..%.1f] |" % (dz + 1, np.median(m), min(m), max(m))
        for s_ in ln["syllables"]:
            if s_["f0_dio_midi"] is not None:
                far.append((abs(s_["f0_midi"] - s_["f0_dio_midi"]), "K%d L%d %s" % (v + 1, dz + 1, s_["text"])))
    yaz(s)
far.sort(reverse=True)
yaz("harvest - dio(stonemask) cekirdek ortancasi farki: ortanca %.3f, en buyuk %.2f yarim ses (%s)" % (
    np.median([f[0] for f in far]), far[0][0], far[0][1]))
# bagimsiz kontrol: bir dizeyi yalniz o parca uzerinde yeniden harvest et
ln = V[0]["lines"][0]; seg = x[int((ln["start"] - 0.1) * fs):int((ln["end"] + 0.1) * fs)]
f0, tt = pw.harvest(seg, fs, f0_floor=150.0, f0_ceil=700.0, frame_period=5.0); tt = tt + ln["start"] - 0.1
fark = []
for s_ in ln["syllables"]:
    m = (tt >= s_["core_start"]) & (tt < s_["core_end"]) & (f0 > 0)
    if m.any():
        fark.append(abs(69 + 12 * np.log2(np.median(f0[m]) / 440) - s_["f0_midi"]))
yaz("K1 L1 yeniden olcum (yalniz o dize uzerinde harvest): en buyuk fark %.3f yarim ses" % max(fark))
kontrol(max(fark) < 0.3, "perde yeniden olcumu tutmuyor")
yaz("L4 son 'bak' perdeleri: " + ", ".join("K%d %s%+d cent" % (r_["verse"], r_["final_bak_note"], round((r_["final_bak_midi"] - round(r_["final_bak_midi"])) * 100))
                                           for r_ in d["l4_comparison"]["per_verse"]))
kontrol(abs(d["l4_comparison"]["per_verse"][5]["final_bak_midi"] - 62) < 0.6, "6. kitanin son 'bak'i D4 cikmadi")

# ---------------------------------------------------------------- 5) bayraklar
yaz("\n== 5) BAYRAKLAR ==")
S_ = d["summary"]
yaz("kuralla konan sinir (FLAG): %d kelime, %d hece -> %s" % (S_["flagged_words"], S_["flagged_syllables"],
                                                              sorted(set(q.split(" ", 2)[2] for q in S_["flagged_words_list"]))))
yaz("sinir turleri:", S_["boundary_kinds"])
yaz("kor tepe sayimi tutmayan kelime: %d (bunlar orantili bolunmedi; hizalama destekli olcutlerle bolundu)" % S_["blind_peak_count_mismatch_words"])

# ---------------------------------------------------------------- 6) gurultu tabani
yaz("\n== 6) GURULTU TABANI (ham WAV) ==")
g = np.concatenate([x[int(q["start"] * fs):int(q["end"] * fs)] for q in d["noise_floor"]["gaps"]])
gdb = float(10 * np.log10(np.mean(g ** 2) + 1e-20))
yaz("bosluk RMS %.1f dBFS, soylenen RMS %.1f dBFS -> %.1f dB (json: %.1f)" % (gdb, sung, gdb - sung, d["noise_floor"]["noise_floor_db_re_sung_rms"]))
kontrol(abs((gdb - sung) - d["noise_floor"]["noise_floor_db_re_sung_rms"]) < 0.5, "gurultu tabani tutmuyor")
yaz("bosluklarin ortanca RMS'i %.1f dBFS (16 bit 1 LSB = -90.3 dBFS); en gurultulu bosluk %.1f dBFS, tepe %.1f dBFS" % (
    d["noise_floor"]["median_gap_rms_dbfs"], d["noise_floor"]["worst_gap_rms_dbfs"], d["noise_floor"]["worst_gap_peak_dbfs"]))
c = d["noise_floor"]["in_line_stop_closures"]
yaz("dize ici otumsuz kapanislar (%d adet): ortanca %.1f dBFS, ceyrekler %s, en yuksek %.1f dBFS" % (
    c["count"], c["median_level_dbfs"], c["p25_p75_dbfs"], c["max_level_dbfs"]))
yaz("son kelimeden sonra sonme suresi (ms):", d["noise_floor"]["tail_after_last_word_ms"])

# ---------------------------------------------------------------- 7) 6. kita onarimi: ek yerlerini dene
yaz("\n== 7) 6. KITA ONARIMI ==")
R = d["verse6_repair"]; sa, sb = R["splice_in_kopekler"], R["splice_in_ordekleri"]
for ad, q in (("Köpekler", sa), ("ördekleri", sb)):
    yaz("%-10s kapanis %.4f-%.4f (%.0f ms), ek ani %.4f, +-2 ms RMS %.1f dBFS, +-2 ms tepe %.1f dBFS" % (
        ad, q["closure_start"], q["closure_end"], q["closure_ms"], q["splice_t"],
        db(q["splice_t"] - 0.002, q["splice_t"] + 0.002), tepe(q["splice_t"] - 0.002, q["splice_t"] + 0.002)))
    kontrol(tepe(q["splice_t"] - 0.002, q["splice_t"] + 0.002) < -50, ad + " ek yeri sessiz degil")
yaz("'köpek' parcasi %.3f s, MIDI %.2f | 'ördek' parcasi %.3f s, MIDI %.2f | sure farki %+.0f ms" % (
    R["kopek_part"]["duration"], R["kopek_part"]["median_midi"], R["ordek_part"]["duration"], R["ordek_part"]["median_midi"],
    R["duration_change_s"] * 1000))
yaz("   hece perdeleri: " + ", ".join("%s %.2f" % (s_["text"], s_["f0_midi"]) for s_ in R["kopek_part"]["syllables"] + R["ordek_part"]["syllables"]))
yaz("on kesim (de|ör) %.4f: duzey %.1f dBFS (sessiz DEGIL, kisa sonumleme gerekir)" % (R["front_cut"]["t"], R["front_cut"]["level_dbfs"]))
os.makedirs(os.path.join(K, "ornek"), exist_ok=True)
K6 = V[5]; L2_, L3_, L4_ = K6["lines"][1], K6["lines"][2], K6["lines"][3]


def parca(a, b):
    return x[int(round(a * fs)):int(round(b * fs))].copy()


def sonumle(y, bas_ms=0.0, son_ms=0.0):
    y = y.copy()
    n = int(bas_ms / 1000 * fs)
    if n:
        y[:n] *= np.linspace(0, 1, n)
    n = int(son_ms / 1000 * fs)
    if n:
        y[-n:] *= np.linspace(1, 0, n)
    return y


# (a) "Çiftliğinde köpekleri var": [L2 cut_in .. on kesim] + sessizlik (k kapanisi) + [Kö.. ek A] + [ek B .. L2 cut_out]
KAPANIS_MS = 40.0
p1 = sonumle(parca(L2_["cut_in"], R["front_cut"]["t"]), son_ms=20)
p2 = np.zeros(int(KAPANIS_MS / 1000 * fs))
p3 = parca(R["kopek_source_cut_in"], sa["splice_t"])
p4 = parca(sb["splice_t"], L2_["cut_out"])
y = np.concatenate([p1, p2, p3, p4])
sf.write(os.path.join(K, "ornek", "k6_l2_kopekleri_deneme.wav"), y, fs, subtype="PCM_16")
ek = [len(p1) + len(p2), len(p1) + len(p2) + len(p3)]
for i, nm in zip(ek, ("kapanis->Kö", "köpe->k+leri")):
    seg = y[i - int(0.002 * fs):i + int(0.002 * fs)]
    sic = abs(y[i] - y[i - 1])
    yaz("   ek '%s': +-2 ms tepe %.1f dBFS, ornekler arasi sicrama %.5f" % (nm, 20 * np.log10(np.abs(seg).max() + 1e-12), sic))
    kontrol(np.abs(seg).max() < 10 ** (-45 / 20), "onarim ekinde tik riski: " + nm)
yaz("   deneme dosyasi: ornek/k6_l2_kopekleri_deneme.wav  (%.3f s; asil L2 parcasi %.3f s)  -- DINLENMEDI" % (
    len(y) / fs, L2_["cut_out"] - L2_["cut_in"]))
# (b) 6. kita L3 + verici kitanin L4'u
don = d["l4_comparison"]["recommended_donor_verse_for_verse6"]; DL4 = V[don - 1]["lines"][3]
XF = int(0.010 * fs)
a_ = parca(L3_["cut_in"], L3_["end"] + XF / fs / 2); b_ = parca(DL4["start"] - XF / fs / 2, DL4["cut_out"])
r = np.linspace(0, 1, XF)
y2 = np.concatenate([a_[:-XF], a_[-XF:] * (1 - r) + b_[:XF] * r, b_[XF:]])
sf.write(os.path.join(K, "ornek", "k6_l3_l4_verici_k%d_deneme.wav" % don), y2, fs, subtype="PCM_16")
yaz("L4 vericisi: K%d (puanlar: %s)" % (don, ", ".join("K%d %.2f%s" % (q["verse"], q["score"], "" if q["eligible"] else " (uygun degil)")
                                                        for q in d["l4_comparison"]["ranking"])))
yaz("   deneme dosyasi: ornek/k6_l3_l4_verici_k%d_deneme.wav (%.3f s; asil L3+L4 parcasi %.3f s; 10 ms capraz gecis) -- DINLENMEDI" % (
    don, len(y2) / fs, L4_["cut_out"] - L3_["cut_in"]))
for q in d["l4_comparison"]["per_verse"]:
    yaz("   K%d L4: kelime MIDI %s | sure %.3f s | ort. hece tepesi %.1f dBFS | fazladan ses: %s" % (
        q["verse"], q["word_median_midi"], q["duration_start_to_energy_end"], q["mean_syllable_peak_dbfs"], q["extra_voiced_sound"]))
ek3 = V[2]["lines"][3]["ending"]["extra_voiced_sound"]
if ek3:
    yaz("K3 L4 fazladan ses %.3f-%.3f s (MIDI %s, tepe %.1f dBFS); ondan onceki temiz kesim %.4f (+-3 ms RMS %.1f dBFS)" % (
        ek3["start"], ek3["end"], ek3["f0_midi"], ek3["peak_dbfs"], ek3["cut_out_before_extra_sound"],
        db(ek3["cut_out_before_extra_sound"] - 0.003, ek3["cut_out_before_extra_sound"] + 0.003)))

# ---------------------------------------------------------------- 8) tekrarlarin tutarliligi
yaz("\n== 8) TEKRAR EDEN DIZELERDE HECE SURESI TUTARLILIGI (7 kita) ==")
for ad, sec in (("L1", lambda kt: kt["lines"][0]["syllables"]), ("L4", lambda kt: kt["lines"][3]["syllables"][:5]),
                ("Çiftliğinde", lambda kt: kt["lines"][1]["syllables"][:4])):
    D = np.array([[s_["end"] - s_["start"] for s_ in sec(kt)] for kt in V]) * 1000
    yaz("%-12s ortanca sure (ms): %s | ortancadan en buyuk sapma (ms): %s" % (
        ad, [int(round(q)) for q in np.median(D, 0)], [int(round(q)) for q in np.abs(D - np.median(D, 0)).max(0)]))
O = np.array([[s_["vowel_onset"] - kt["lines"][3]["syllables"][0]["vowel_onset"] for s_ in kt["lines"][3]["syllables"]] for kt in V]) * 1000
yaz("L4 unlu baslangiclari (ilk heceye gore, ms) ortanca %s, yayilim (en buyuk-en kucuk) %s" % (
    [int(round(q)) for q in np.median(O, 0)], [int(round(q)) for q in np.ptp(O, 0)]))

yaz("\nSONUC: %s" % ("TUM KONTROLLER GECTI" if not hata else "%d HATA" % len(hata)))
yaz("Not: bu kontroller olcumdur; ses kulakla dinlenmedi.")
open(os.path.join(K, "dogrulama.txt"), "w", encoding="utf8").write("\n".join(satirlar) + "\n")
sys.exit(1 if hata else 0)
