#!/usr/bin/env python3
"""Dogal vokal yerlesimi: dinle_2_vokal.wav'daki dizeleri HICBIR perde / sure islemi yapmadan
(yalniz kesme + yukseltilmis kosinus gecis + tam sayili ornek kaydirma) yeni sarki formuna dizer.

Girdi : dinle_2_vokal.wav, yeni3/analiz/tempo/tempo.json, yeni3/analiz/kesim/kesim.json
Cikti : yeni3/vokal/vokal_dogal.wav (mono, 44.1 kHz, PCM_16), yeni3/vokal/yerlesim.json

Yerlesim kurali: her dizenin KENDI olcu cizgisi (tempo.json lines[].downbeat) yeni formdaki olcu
cizgisine oturur; yani hedef_zaman = hedef_olcu_basi + (kaynak_zaman - kaynak_olcu_basi). Boylece her dizenin
olculen kendi ofseti (onset - downbeat) aynen korunur. L3+L4 tek parcadir, L3'e gore demirlenir.

Secenek: --k3-ek-ses-kalsin  -> 3. kitanin son 'bak'indan sonraki fazladan sesli ek kesilmez.
"""
import sys, os, json, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *

K3_EK_SES_KALSIN = "--k3-ek-ses-kalsin" in sys.argv

# ------------------------------------------------------------------ form
BPM = 116.015
BEAT = 60.0 / BPM
BAR = 240.0 / BPM
INTRO, KITA_OLCU, N_KITA, SON = 4, 8, 7, 4
TOPLAM_OLCU = INTRO + KITA_OLCU * N_KITA + SON           # 64
KUYRUK = 2.5
N_OUT = int(round((TOPLAM_OLCU * BAR + KUYRUK) * SR))
TEPE_DBFS = -3.0
DIZE_OLCUSU = {1: 0, 2: 2, 3: 4, 4: 5}                    # kita icindeki olcu

F_MIN, F_MAX = 0.015, 0.030                               # kenar gecis suresi sinirlari (s)

# ------------------------------------------------------------------ 6. kita onarim sabitleri
# (a) L2 'ördekleri' -> 'köpekleri'. Olculen anlar (1 ms RMS zarfi, 01_incele / 02_ciz ile bakildi):
KO_PATLAMA = 78.0575        # K6 L3 'Kö' /k/ patlamasinin basladigi an
KO_KAYNAK_BAS = 78.0400     # 'Kö' parcasinin kaynak baslangici: patlamadan onceki sessizligin ici (-66..-76 dBFS)
KO_GIRIS = 0.008            # bu parcanin giris gecisi (sessizlikte)
K_KAPANIS = 0.020           # 'pek' ile 'le' arasinda birakilan /k/ kapanisi (dogal ornekler: de|ko 20 ms, nek|le 24 ms)
DE_D_PATLAMA = 76.698       # K6 L2 'de' hecesinin /d/ patlamasi (unlu 76.713'te tam duzeye cikar)
DE_SONUM = 0.022            # 'de' unlusunun sonumlemesi (kesim onerisi 15-25 ms)
DE_BOSLUK = 0.018           # 'de' sonumlemesinin bitisi ile 'Kö' patlamasi arasi (kapanis sessizligi; dogal ornek K2 'de|ko': 20 ms)
EK_GECIS = 0.008            # /k/ kapanisi icindeki capraz gecis (istenen 5-10 ms)
EK_ORTA_PATLAMADAN_ONCE = 0.0099   # capraz gecisin ortasi, 'le' patlamasindan (closure_end) bu kadar once
# (b) L4 <- verici kitanin L4'u
L4_GECIS = 0.010            # L3 sonu ile verici L4 basi arasindaki capraz gecis
K6_L3_KESIM = 80.1480       # K6 L3'un son /r/ mirildanmasinin en dusuk oldugu an (-46..-50 dBFS), kendi /d/ patlamasindan hemen once


def s(t):
    return int(round(t * SR))


def giris_penceresi(c, hi, lo):
    """Giris gecisi [a, b]. c = kesim noktasi, hi = kendi sesinin basi, lo = onceki dizenin ses sonu (yoksa None)."""
    marj = hi - c
    if marj >= F_MIN:
        F = min(F_MAX, marj)
        return c, c + F, "kesim noktasindan baslar"
    F = F_MIN
    a = hi - F
    if lo is not None and a < lo:
        a = 0.5 * (lo + hi) - 0.5 * F
        return a, a + F, "bosluk 15 ms'den dar: boslugun ortasina yerlesti"
    return a, a + F, "kendi ses basinda biter (boslugun icinde)"


def cikis_penceresi(c, lo, hi):
    """Cikis gecisi [a, b]. c = kesim noktasi, lo = kendi ses sonu, hi = sonraki dizenin ses basi (yoksa None)."""
    marj = c - lo
    if marj >= F_MIN:
        F = min(F_MAX, marj)
        return c - F, c, "kesim noktasinda biter"
    F = F_MIN
    b = lo + F
    if hi is not None and b > hi:
        b = 0.5 * (lo + hi) + 0.5 * F
        return b - F, b, "bosluk 15 ms'den dar: boslugun ortasina yerlesti"
    return b - F, b, "kendi ses sonunda baslar (boslugun icinde)"


def kenar_olcum(x, a, b, c, yon, dize_rms_db):
    """Gecisin bedeli. yon='giris': c'den onceki (komsu taraf) sizan enerji + c'den sonraki (kendi) kisilan enerji.
    Donus dB (10 ms'lik pencereye yayilmis esdeger RMS) ve dize RMS'ine gore."""
    ia, ib, ic = s(a), s(b), s(c)
    n = ib - ia
    g = kos_yuksel(n) if yon == "giris" else kos_alcal(n)
    seg = x[ia:ib]
    idx = np.arange(ia, ib)
    komsu = idx < ic if yon == "giris" else idx >= ic
    sizan = np.sum((g[komsu] * seg[komsu]) ** 2)
    kisilan = np.sum(((1 - g[~komsu]) * seg[~komsu]) ** 2)
    ref = 0.010 * SR
    sz, ks = 10 * np.log10(sizan / ref + 1e-20), 10 * np.log10(kisilan / ref + 1e-20)
    return dict(leak_dbfs=round(float(sz), 1), loss_dbfs=round(float(ks), 1),
                leak_db_re_line_rms=round(float(sz - dize_rms_db), 1), loss_db_re_line_rms=round(float(ks - dize_rms_db), 1))


def main():
    x = oku_vokal()
    K = oku_json(KESIM)
    T = oku_json(TEMPO)
    tl = {(L["verse"], L["line"]): L for L in T["lines"]}
    out = np.zeros(N_OUT)
    R = lambda v, n=5: round(float(v), n)

    parcalar = []      # (etiket, src_a, src_b, dst_a, n_giris, n_cikis)

    def parca(etiket, src_a, src_b, dst_a, n_in, n_out):
        n = src_b - src_a
        assert n > n_in + n_out > 0, (etiket, n, n_in, n_out)
        g = np.ones(n)
        if n_in:
            g[:n_in] = kos_yuksel(n_in)
        if n_out:
            g[n - n_out:] *= kos_alcal(n_out)
        assert dst_a >= 0 and dst_a + n <= N_OUT, etiket
        out[dst_a:dst_a + n] += x[src_a:src_b] * g
        parcalar.append(dict(label=etiket, src_in_sample=src_a, src_out_sample=src_b, dest_in_sample=dst_a,
                             dest_out_sample=dst_a + n, fade_in_samples=n_in, fade_out_samples=n_out,
                             src_in=R(src_a / SR), src_out=R(src_b / SR), dest_in=R(dst_a / SR), dest_out=R((dst_a + n) / SR)))

    lines_out, chunks_out, repairs = [], [], []
    rep = K["verse6_repair"]
    donor_v = K["l4_comparison"]["recommended_donor_verse_for_verse6"]

    for vi, V in enumerate(K["verses"]):
        v = V["verse"]
        bar0 = INTRO + KITA_OLCU * vi
        Ls = {L["line"]: L for L in V["lines"]}
        ch = V["chunks"]
        for ci, C in enumerate(ch):
            l_ilk = C["lines"][0]
            l_son = C["lines"][-1]
            tL = tl[(v, l_ilk)]
            hedef_olcu = bar0 + DIZE_OLCUSU[l_ilk]
            D = hedef_olcu * BAR
            kay = s(D) - s(tL["downbeat"])               # tam sayili ornek kaydirma (hedef - kaynak)
            # --- kenar pencereleri
            lo_in = ch[ci - 1]["end"] if ci > 0 else None
            hi_out = ch[ci + 1]["start"] if ci + 1 < len(ch) else None
            a_in, b_in, not_in = giris_penceresi(C["cut_in"], C["start"], lo_in)
            c_out, lo_out, ek_not = C["cut_out"], C["end"], None
            if v == 3 and l_son == 4 and not K3_EK_SES_KALSIN:
                ex = Ls[4]["ending"]["extra_voiced_sound"]
                c_out = ex["cut_out_before_extra_sound"]
                lo_out = ex["silent_gap_before"][0]
                ek_not = "fazladan sesli ek kesildi"
            a_out, b_out, not_out = cikis_penceresi(c_out, lo_out, hi_out)
            rms_ilk = Ls[l_ilk]["rms_dbfs"]
            rms_son = Ls[l_son]["rms_dbfs"]
            kenar_in = kenar_olcum(x, a_in, b_in, C["cut_in"], "giris", rms_ilk)
            kenar_out = kenar_olcum(x, a_out, b_out, c_out, "cikis", rms_son)
            n_in, n_out = s(b_in) - s(a_in), s(b_out) - s(a_out)
            cid = "K%d_L%s" % (v, "+".join(str(q) for q in C["lines"]))
            ilk_parca = len(parcalar)
            esle = {}                                     # dize -> [(src_lo, src_hi, kaydirma_ornek, kaynak_etiketi)]

            if v == 6 and l_ilk == 2:
                # ---------- (a) 'ördekleri' -> 'köpekleri'
                kop, ordk = rep["splice_in_kopekler"], rep["splice_in_ordekleri"]
                dP = s(ordk["closure_end"] - K_KAPANIS) - s(kop["closure_start"])      # K6-L3 zamani -> K6-L2 zamani (ornek)
                t_pat = KO_PATLAMA + dP / SR                                             # 'Kö' patlamasinin L2 zamanindaki yeri
                t_de = t_pat - DE_BOSLUK                                                 # 'de' sonumlemesinin bitisi
                n_de = s(DE_SONUM)
                parca(cid + "_a(Ciftliginde)", s(a_in), s(t_de), s(a_in) + kay, n_in, n_de)
                n_x = s(EK_GECIS)
                t_ek = ordk["closure_end"] - EK_ORTA_PATLAMADAN_ONCE                     # capraz gecisin ortasi (L2 zamani)
                T_a = s(t_ek) - n_x // 2                                                 # kuyruk parcasinin kaynak basi
                P_a, P_b = s(KO_KAYNAK_BAS), T_a + n_x - dP
                parca(cid + "_b(kopek<-K6_L3)", P_a, P_b, P_a + dP + kay, s(KO_GIRIS), n_x)
                parca(cid + "_c(leri var)", T_a, s(b_out), T_a + kay, n_x, n_out)
                t_ek_c = (T_a + n_x / 2) / SR                                            # gercek gecis ortasi
                esle[2] = [(-1e9, t_de, kay, "K6 L2"), ("kopek", (P_a + s(KO_GIRIS)) / SR, t_ek_c - dP / SR, dP + kay, "K6 L3"),
                           (t_ek_c, 1e9, kay, "K6 L2")]
                k6a = dict(dP=dP, t_pat=t_pat, t_de=t_de, t_ek=t_ek_c, P_a=P_a, P_b=P_b, T_a=T_a, n_x=n_x, n_de=n_de, kay=kay)
            elif v == 6 and l_ilk == 3:
                # ---------- (b) L4 <- verici kita
                DV = K["verses"][donor_v - 1]
                dL4 = DV["lines"][3]
                dC = DV["chunks"][2]
                n_j = s(L4_GECIS)
                dD = s(tl[(6, 4)]["downbeat"]) - s(tl[(donor_v, 4)]["downbeat"])        # verici zamani -> K6 zamani (ornek)
                C_b = s(K6_L3_KESIM)
                parca(cid + "_a(L3)", s(a_in), C_b, s(a_in) + kay, n_in, n_j)
                dn_a = C_b - n_j - dD
                da_out, db_out, not_out = cikis_penceresi(dC["cut_out"], dC["end"], None)
                kenar_out = kenar_olcum(x, da_out, db_out, dC["cut_out"], "cikis", dL4["rms_dbfs"])
                n_out = s(db_out) - s(da_out)
                parca(cid + "_b(L4<-K%d_L4)" % donor_v, dn_a, s(db_out), dn_a + dD + kay, n_j, n_out)
                t_j6 = (C_b - n_j / 2) / SR                                              # gecis ortasi, K6 zamani
                t_jd = (dn_a + n_j / 2) / SR                                             # gecis ortasi, verici zamani
                esle[3] = [(-1e9, t_j6, kay, "K6 L3")]
                esle[4] = [(t_jd, 1e9, dD + kay, "K%d L4" % donor_v)]
                k6b = dict(dD=dD, t_j6=t_j6, t_jd=t_jd, dn_a=dn_a, C_b=C_b, n_j=n_j, kay=kay, db_out=db_out)
                a_out, b_out, c_out = da_out, db_out, dC["cut_out"]
            else:
                parca(cid, s(a_in), s(b_out), s(a_in) + kay, n_in, n_out)
                for l in C["lines"]:
                    esle[l] = [(-1e9, 1e9, kay, "K%d L%d" % (v, l))]

            chunks_out.append(dict(
                id=cid, verse=v, lines=C["lines"], dest_bar=hedef_olcu, dest_bar_downbeat=R(D), shift_samples=kay, shift_sec=R(kay / SR, 6),
                src_cut_in=C["cut_in"], src_cut_out=c_out,
                fade_in=dict(src_from=R(a_in), src_to=R(b_in), ms=R((b_in - a_in) * 1000, 1), rule=not_in, **kenar_in),
                fade_out=dict(src_from=R(a_out), src_to=R(b_out), ms=R((b_out - a_out) * 1000, 1), rule=not_out, **kenar_out),
                pieces=parcalar[ilk_parca:], note=ek_not,
                dest_in=parcalar[ilk_parca]["dest_in"], dest_out=parcalar[-1]["dest_out"],
                dest_in_sample=parcalar[ilk_parca]["dest_in_sample"], dest_out_sample=parcalar[-1]["dest_out_sample"]))

            # --- dize ve hece kayitlari
            for l in C["lines"]:
                L = Ls[l]
                tLl = tl[(v, l)]
                donor = (v == 6 and l == 4)
                srcL = K["verses"][donor_v - 1]["lines"][3] if donor else L
                src_t = tl[(donor_v, 4)] if donor else tLl
                olcu = bar0 + DIZE_OLCUSU[l]
                Dl = olcu * BAR
                seg = esle[l]

                def hedef(t, hece=None):
                    """kaynak zamani -> hedef zamani (s). Onarilan L2'de hece hangi parcadaysa onun kaydirmasi."""
                    for q in seg:
                        if q[0] == "kopek":
                            if hece == "kopek":
                                return t + q[3] / SR
                            continue
                        if hece == "kopek":
                            continue
                        if q[0] <= t <= q[1]:
                            return t + q[2] / SR
                    raise ValueError((v, l, t, hece))

                heceler = []
                if v == 6 and l == 2:
                    # onarimdan SONRAKI heceler: Çift li ğin de | kö pek (K6 L3'ten) | le ri var
                    q = k6a
                    l3s = {h["text"]: h for h in Ls[3]["syllables"][:2]}
                    for h in L["syllables"]:
                        hh = dict(h)
                        if h["text"] == "ör":
                            k = l3s["Kö"]
                            hh = dict(k, text="kö", word="köpekleri", word_index=h["word_index"], index_in_word=0)
                            hh["_src"] = "K6 L3"; hh["_tip"] = "kopek"
                            hh["start"] = q["t_de"] - q["dP"] / SR           # 'de' bitisine bitisik (kapanis sessizligi dahil)
                            hh["_not"] = "K6 L3 'Köpekler'den; basinda %.0f ms'lik /k/ kapanis sessizligi var; D4'te soylenmis (perde duzeltilmedi)" % (DE_BOSLUK * 1000)
                        elif h["text"] == "dek":
                            k = l3s["pek"]
                            hh = dict(k, text="pek", word="köpekleri", word_index=h["word_index"], index_in_word=1)
                            hh["_src"] = "K6 L3"; hh["_tip"] = "kopek"
                            hh["end"] = q["t_ek"] - q["dP"] / SR
                            hh["_not"] = "K6 L3 'Köpekler'den; sonu /k/ kapanisinin icindeki capraz gecisin ortasi"
                        elif h["text"] == "de" and h["word"] == "Çiftliğinde":
                            hh["end"] = q["t_de"]
                            hh["core_end"] = min(hh["core_end"], q["t_de"] - DE_SONUM)
                            hh["_not"] = "sonu kisaltildi: unlu %.0f ms'lik sonumleme ile /k/ kapanisina baglandi" % (DE_SONUM * 1000)
                        elif h["text"] == "le":
                            hh["start"] = q["t_ek"]
                            hh["word"] = "köpekleri"
                        elif h["text"] == "ri":
                            hh["word"] = "köpekleri"
                        heceler.append(hh)
                else:
                    for h in srcL["syllables"]:
                        heceler.append(dict(h))
                    if v == 6 and l == 3:
                        heceler[-1]["end"] = k6b["t_j6"]
                        heceler[-1]["_not"] = "sonuna kadar korundu (kesim 'end' %.4f); %.0f ms'lik capraz gecisle verici L4'e baglandi" % (L["end"], L4_GECIS * 1000)
                    if donor:
                        heceler[0]["start"] = k6b["t_jd"]
                    if v == 3 and l == 4 and not K3_EK_SES_KALSIN:
                        heceler[-1]["end"] = min(heceler[-1]["end"], c_out)

                syl = []
                for i, h in enumerate(heceler):
                    tip = h.get("_tip")
                    d0, d1, dv = hedef(h["start"], tip), hedef(h["end"], tip), hedef(h["vowel_onset"], tip)
                    syl.append(dict(
                        index=i, text=h["text"], word=h["word"],
                        src_start=R(h["start"], 4), src_end=R(h["end"], 4), dest_start=R(d0, 4), dest_end=R(d1, 4),
                        src_vowel_onset=R(h["vowel_onset"], 4), dest_vowel_onset=R(dv, 4),
                        vowel_onset_beats_in_bar=R((dv - Dl) / BEAT, 3),
                        src_core_start=R(h["core_start"], 4), src_core_end=R(h["core_end"], 4),
                        dest_core_start=R(hedef(h["core_start"], tip), 4), dest_core_end=R(hedef(h["core_end"], tip), 4),
                        midi=h["f0_midi"], midi_all_voiced=h["f0_all_midi"], note=h["note"], cents_from_note=h["cents_from_note"],
                        voiced_ratio=h["voiced_ratio"], boundary_flag=h["flag"],
                        src_line=h.get("_src", seg[0][-1] if seg[0][0] != "kopek" else "K6 L2"), note_text=h.get("_not")))
                # dize sinirlari
                if l == l_ilk:
                    s_in = parcalar[ilk_parca]["src_in"]
                else:
                    s_in = srcL["start"] if not donor else k6b["t_jd"]
                if l == l_son:
                    s_out = parcalar[-1]["src_out"]
                else:
                    s_out = L["end"] if not (v == 6 and l == 3) else k6b["t_j6"]
                d_in = hedef(s_in) if not (l == l_ilk) else parcalar[ilk_parca]["dest_in"]
                d_out = parcalar[-1]["dest_out"] if l == l_son else hedef(s_out)
                kayL = seg[0][2] if seg[0][0] != "kopek" else kay
                onset_src = src_t["onset"]
                metin = L["text"]
                if v == 6 and l == 2:
                    metin = "Çiftliğinde köpekleri var"
                snd0 = srcL["start"] if not donor else k6b["t_jd"]
                snd1 = srcL["end"]
                if v == 3 and l == 4 and not K3_EK_SES_KALSIN:
                    snd1 = lo_out
                if v == 6 and l == 3:
                    snd1 = k6b["t_j6"]
                lines_out.append(dict(
                    verse=v, line=l, animal=V["animal"], text=metin, chunk=cid, repaired=bool((v == 6 and l in (2, 4)) or (v == 3 and l == 4 and not K3_EK_SES_KALSIN)),
                    src_verse=donor_v if donor else v,
                    dest_bar=olcu, bar_in_verse=DIZE_OLCUSU[l], dest_bar_downbeat=R(Dl), src_downbeat=src_t["downbeat"],
                    shift_samples=kayL, shift_sec=R(kayL / SR, 6),
                    offset_used_sec=R(onset_src + kayL / SR - Dl, 5), offset_used_beats=R((onset_src + kayL / SR - Dl) / BEAT, 4),
                    offset_from_tempo_analysis_sec=src_t["offset_sec"],
                    vowel_offset_sec=R(src_t["vowel_onset"] + kayL / SR - Dl, 5),
                    src_onset=onset_src, dest_onset=R(onset_src + kayL / SR), src_first_vowel_onset=src_t["vowel_onset"],
                    dest_first_vowel_onset=R(src_t["vowel_onset"] + kayL / SR),
                    src_in=R(s_in), src_out=R(s_out), dest_in=R(d_in), dest_out=R(d_out),
                    src_sound_start=R(snd0, 4), src_sound_end=R(snd1, 4), dest_sound_start=R(snd0 + kayL / SR, 4), dest_sound_end=R(snd1 + kayL / SR, 4),
                    src_rms_dbfs=srcL["rms_dbfs"], src_peak_dbfs=srcL["peak_dbfs"],
                    src_first_word_start_words_file=src_t["word_start_from_words_file"],
                    syllables=syl))

    # ------------------------------------------------------------------ tek genel kazanc + yazma
    tepe = float(np.max(np.abs(out)))
    kazanc = 10 ** (TEPE_DBFS / 20.0) / tepe
    y = out * kazanc
    y16 = np.clip(np.round(y * 32768.0), -32768, 32767).astype(np.int16)
    sf.write(CIKTI_WAV, y16, SR, subtype="PCM_16")

    # ------------------------------------------------------------------ onarim listesi
    q = k6a
    L2 = K["verses"][5]["lines"][1]
    d2 = tl[(6, 2)]["downbeat"]
    repairs.append(dict(
        id="K6_L2_kopekleri", verse=6, line=2, type="word splice",
        what="sung 'ördekleri' replaced by 'köpek' (from verse 6 line 3 'Köpekler') + the original /k/ burst + 'leri'",
        pieces=[p for p in parcalar if p["label"].startswith("K6_L2")],
        de_fade_out=dict(src_from=R(q["t_de"] - DE_SONUM, 4), src_to=R(q["t_de"], 4), ms=DE_SONUM * 1000,
                         note="'de' ran straight into 'ör' (vowel to vowel); its vowel is faded out here to form the /k/ closure"),
        kopek_source=dict(src_from=R(q["P_a"] / SR, 4), src_to=R(q["P_b"] / SR, 4), fade_in_ms=KO_GIRIS * 1000,
                          k_burst_src=KO_PATLAMA, k_burst_in_line2_time=R(q["t_pat"], 4),
                          shift_into_line2_sec=R(q["dP"] / SR, 5)),
        silence_before_k_burst_ms=R(DE_BOSLUK * 1000, 1),
        splice=dict(where="inside the /k/ closure between 'pek' and 'le'", crossfade_ms=EK_GECIS * 1000,
                    centre_line2_time=R(q["t_ek"], 4), centre_kopek_source_time=R(q["t_ek"] - q["dP"] / SR, 4),
                    centre_dest_time=R(q["t_ek"] + q["kay"] / SR, 4),
                    k_closure_ms_after_repair=K_KAPANIS * 1000, k_closure_ms_original_ordekleri=rep["splice_in_ordekleri"]["closure_ms"],
                    k_closure_ms_in_kopekler=rep["splice_in_kopekler"]["closure_ms"]),
        timing=dict(
            tail_leri_var_shift_ms=0.0,
            note="everything from the /k/ burst of 'leri' on ('leri var') is untouched and stays at its original position, so 'var' is exactly in time",
            vowel_onset_old_or_beats=R((76.8374 - d2) / BEAT, 3), vowel_onset_new_ko_beats=R((78.1045 + q["dP"] / SR - d2) / BEAT, 3),
            vowel_onset_old_dek_beats=R((77.0828 - d2) / BEAT, 3), vowel_onset_new_pek_beats=R((78.3759 + q["dP"] / SR - d2) / BEAT, 3),
            pek_vowel_later_than_dek_ms=R((78.3759 + q["dP"] / SR - 77.0828) * 1000, 1),
            de_d_burst_to_k_burst_ms=R((q["t_pat"] - DE_D_PATLAMA) * 1000, 1),
            de_sound_ms=R((q["t_de"] - DE_D_PATLAMA) * 1000, 1),
            de_note="'de' is shorter than sung (it ran for 140 ms straight into the 'ö'; now %.0f ms of sound, then the closure) because the inserted /k/ closure + burst + aspiration need about 65 ms before the vowel; natural reference: verse 2 'de|ko' has about 55 ms of full vowel and a 20 ms closure"
                    % ((q["t_de"] - DE_D_PATLAMA) * 1000)),
        pitch=dict(ko_midi=62.06, pek_midi=63.89, neighbours_midi=dict(de=63.98, le=65.04),
                   note="'kö' was sung on D4 (it is the first syllable of line 3), about 1.9 semitones below the E4 around it. NOT corrected here (no pitch processing in this step)."),
        word_duration=dict(old_ordekleri_sec=R(L2["syllables"][7]["end"] - 76.8374, 4), new_kopekleri_sec=R(L2["syllables"][7]["end"] - q["t_pat"], 4),
                           note="measured from the first sound of the word (old: vowel 'ö'; new: /k/ burst, 47 ms before its vowel) to the end of 'ri'; the vowel onsets coincide within 0.2 ms")))
    b = k6b
    dvL4 = K["verses"][donor_v - 1]["lines"][3]
    repairs.append(dict(
        id="K6_L4_verici_K%d" % donor_v, verse=6, line=4, type="line replacement",
        what="verse 6 line 4 (its last 'bak' ends on D4) replaced by verse %d line 4 (same words, ends on C4)" % donor_v,
        donor_verse=donor_v,
        pieces=[p for p in parcalar if p["label"].startswith("K6_L3+4")],
        position="the donor's own bar line (downbeat %.4f) is put on verse 6 line 4's bar line (downbeat %.4f): the donor keeps the metric position it had in its own verse"
                 % (tl[(donor_v, 4)]["downbeat"], tl[(6, 4)]["downbeat"]),
        donor_shift_to_verse6_time_sec=R(b["dD"] / SR, 5),
        crossfade=dict(ms=L4_GECIS * 1000, centre_verse6_time=R(b["t_j6"], 4), centre_donor_time=R(b["t_jd"], 4),
                       centre_dest_time=R(b["t_j6"] + b["kay"] / SR, 4),
                       note="verse 6's line 3 is kept up to the lowest point of its final /r/ murmur (just before its own /d/ burst); the donor enters inside its voiced /d/ closure, %.1f ms after the donor's own L3|L4 junction (%.4f), so nothing of the donor's line 3 is included"
                            % ((b["t_jd"] - dvL4["start"]) * 1000, dvL4["start"])),
        level=dict(donor_l4_rms_dbfs=dvL4["rms_dbfs"], verse6_l4_rms_dbfs=K["verses"][5]["lines"][3]["rms_dbfs"], verse6_l3_rms_dbfs=K["verses"][5]["lines"][2]["rms_dbfs"],
                   gain_suggested_by_segmentation_db=K["l4_comparison"]["ranking"][0]["gain_to_match_db"], gain_applied_db=0.0,
                   note="no per-line gain was applied (task rule: one global gain only); the mixer may apply the suggested gain to this line if wanted"),
        onset_offset=dict(donor_sec=tl[(donor_v, 4)]["offset_sec"], verse6_own_sec=tl[(6, 4)]["offset_sec"])))
    if not K3_EK_SES_KALSIN:
        ex = K["verses"][2]["lines"][3]["ending"]["extra_voiced_sound"]
        d34 = tl[(3, 4)]["downbeat"]
        repairs.append(dict(
            id="K3_L4_ek_ses", verse=3, line=4, type="trim (NOT in the task's repair list; defect reported by the segmentation)",
            what="the voiced after-sound that follows the last 'bak' after a silent gap (%.4f-%.4f s, MIDI %.2f, peak %.1f dBFS; not part of the lyric) is dropped"
                 % (ex["start"], ex["end"], ex["f0_midi"], ex["peak_dbfs"]),
            cut_out=ex["cut_out_before_extra_sound"], silent_gap_before=ex["silent_gap_before"],
            why="in the new form it would start %.0f ms after the downbeat of bar 6 of the verse, i.e. on top of the first animal call"
                % ((ex["start"] - d34 - BAR) * 1000),
            consequence="the final 'bak' ends in an unreleased /k/ (the closure silence is kept for %.0f ms, then faded); verse 2's 'bak' also ends without a release"
                        % ((ex["cut_out_before_extra_sound"] - ex["silent_gap_before"][0]) * 1000),
            undo="run 03_yerlestir.py --k3-ek-ses-kalsin to keep the after-sound"))

    # ------------------------------------------------------------------ yerlesim.json
    yer = dict(
        description="Natural placement of the dinle_2 vocal lines on the new song form (no pitch or time processing: cut, raised-cosine fades, integer-sample shifts only)",
        not_verified_by_ear="Everything here is measured by code; nobody listened to the result.",
        schema={
            "time_base": "src_* = seconds on the timeline of dinle_2_vokal.wav; dest_* = seconds on the timeline of vokal_dogal.wav (bar 0 starts at 0.0)",
            "form": "bars are 0-based; verse v (0..6) starts at bar 4 + 8*v; bar downbeat time = bar * bar_sec",
            "lines[]": {
                "dest_bar_downbeat": "time of the bar line the line belongs to",
                "offset_used_sec": "dest_onset - dest_bar_downbeat (= the line's own measured offset from the tempo analysis, up to half a sample of rounding); negative = the first sound starts before the bar line",
                "src_onset / dest_onset": "acoustic onset of the first syllable (tempo analysis definition, includes initial consonants)",
                "src_in/src_out, dest_in/dest_out": "extent of the line's audio including fades; inside the L3+L4 chunk the L3|L4 boundary is the junction between the two lines",
                "src_sound_start/end": "energy onset / decay of the sung line from the segmentation (10 ms RMS crossing sung_rms - 45 dB)",
                "shift_sec": "dest time - src time for this line's audio (constant inside a line except verse 6 line 2, see its syllables and repairs)",
                "src_verse": "verse the audio was taken from (differs from 'verse' only for the reused verse-6 line 4)"},
            "lines[].syllables[]": {
                "src_start/src_end, dest_start/dest_end": "contiguous tiling of the line (segmentation boundaries shifted to the destination)",
                "dest_vowel_onset": "beat-alignment point of the syllable; vowel_onset_beats_in_bar = (dest_vowel_onset - dest_bar_downbeat) / beat",
                "midi": "ORIGINAL sung pitch: median f0 of the vowel core (segmentation f0_midi); midi_all_voiced = median over all voiced frames of the syllable",
                "src_line": "where the syllable's audio comes from",
                "boundary_flag": "true = a boundary of this syllable was placed by rule in the segmentation (çift-li-ği / Çift-li-ğin-de)"},
            "chunks[]": "the 21 placed pieces of audio ([L1], [L2], [L3+L4] per verse) with their fades; fade_*.leak/loss = energy admitted from beyond the cut point / removed from the line's own side by the fade, as equivalent RMS over 10 ms",
            "repairs[]": "edits other than plain cutting and shifting"},
        form=dict(bpm=BPM, beat_sec=R(BEAT, 6), bar_sec=R(BAR, 6), meter="4/4", intro_bars=INTRO, verse_bars=KITA_OLCU, verses=N_KITA, ending_bars=SON,
                  total_bars=TOPLAM_OLCU, tail_sec=KUYRUK, duration_sec=R(N_OUT / SR, 6), samples=N_OUT, sample_rate=SR,
                  verse_start_bars=[INTRO + KITA_OLCU * i for i in range(N_KITA)],
                  verse_start_sec=[R((INTRO + KITA_OLCU * i) * BAR) for i in range(N_KITA)],
                  bars_in_verse={"0": "vocal L1", "1": "instrumental answer", "2": "vocal L2", "3": "instrumental answer", "4": "vocal L3", "5": "vocal L4", "6": "animal call 1", "7": "animal call 2"}),
        audio=dict(file="vokal_dogal.wav", channels=1, sample_rate=SR, subtype="PCM_16",
                   global_gain_db=R(20 * np.log10(kazanc), 3), global_gain_linear=float(kazanc), peak_dbfs_target=TEPE_DBFS, peak_before_gain_dbfs=R(20 * np.log10(tepe), 3),
                   per_line_gain="none", silence="exact digital zero outside the placed chunks",
                   processing="cut + raised-cosine fades + integer-sample shift; one global gain; no pitch shift, no time stretch, no resampling"),
        placement_rule=dict(
            offset_used="per-line offset",
            how="each line's own bar line (tempo.json lines[].downbeat, a point of the constant 116.015 BPM machine grid) is mapped onto the destination bar line: dest_time = dest_bar_downbeat + (src_time - src_downbeat), rounded to whole samples",
            why="the tempo analysis rates the grid as high confidence (phase deviation at most 1.7 ms) and all 28 lines as on-the-beat; mapping bar line to bar line reproduces each line's measured offset exactly and does not depend on the onset detector, so no onset-detection noise enters the placement. The per-line-number median offset was therefore not used.",
            l3_l4="L3+L4 is one chunk anchored on L3's bar line; L4 lands on the next bar line because the source tempo equals the destination tempo (bar-to-bar difference at most 0.1 ms, from the 4-decimal rounding of the downbeats)",
            fades="chunk edges: 15-30 ms raised cosine. Where the quiet gap between two sung lines is wider than 15 ms the fade lies inside it; where the gap is narrower the 15 ms fade is centred on the gap (see chunks[].fade_*.rule and leak/loss)"),
        summary=dict(
            lines=len(lines_out), syllables=sum(len(l["syllables"]) for l in lines_out), chunks=len(chunks_out), pieces=len(parcalar),
            repairs=[r["id"] for r in repairs], first_vocal_sample_sec=chunks_out[0]["dest_in"], last_vocal_sample_sec=chunks_out[-1]["dest_out"],
            verses=[dict(
                verse=vv + 1, animal=K["verses"][vv]["animal"], start_bar=INTRO + KITA_OLCU * vv,
                bar_downbeats_sec=[R((INTRO + KITA_OLCU * vv + i) * BAR) for i in range(KITA_OLCU)],
                l4_sound_end_after_bar6_downbeat_ms=R((lines_out[4 * vv + 3]["dest_sound_end"] - (INTRO + KITA_OLCU * vv + 6) * BAR) * 1000, 1),
                vocal_chunk_end_after_bar6_downbeat_ms=R((lines_out[4 * vv + 3]["dest_out"] - (INTRO + KITA_OLCU * vv + 6) * BAR) * 1000, 1))
                for vv in range(N_KITA)],
            note="l4_sound_end_after_bar6_downbeat_ms = how far the sung sound of line 4 (down to sung RMS - 45 dB) reaches into the first animal-call bar; vocal_chunk_end... = where the faded tail reaches digital silence"),
        lines=lines_out, chunks=chunks_out, repairs=repairs,
        options=dict(k3_after_sound_kept=K3_EK_SES_KALSIN))
    with open(CIKTI_JSON, "w", encoding="utf8") as f:
        json.dump(yer, f, ensure_ascii=False, indent=1)
    print("yazildi:", CIKTI_WAV, "%.3f s, %d ornek" % (N_OUT / SR, N_OUT))
    print("genel kazanc %.3f dB (kazanc oncesi tepe %.3f dBFS)" % (20 * np.log10(kazanc), 20 * np.log10(tepe)))
    print("parca sayisi:", len(parcalar), "| dize:", len(lines_out), "| hece:", sum(len(l["syllables"]) for l in lines_out))
    for c in chunks_out:
        print("  %-8s olcu %2d  hedef %.4f-%.4f  giris %4.1f ms (sizan %6.1f, kisilan %6.1f dB)  cikis %4.1f ms (sizan %6.1f, kisilan %6.1f dB)" % (
            c["id"], c["dest_bar"], c["dest_in"], c["dest_out"], c["fade_in"]["ms"], c["fade_in"]["leak_db_re_line_rms"], c["fade_in"]["loss_db_re_line_rms"],
            c["fade_out"]["ms"], c["fade_out"]["leak_db_re_line_rms"], c["fade_out"]["loss_db_re_line_rms"]))


if __name__ == "__main__":
    main()
