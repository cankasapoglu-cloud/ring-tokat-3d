#!/usr/bin/env python3
"""Dogal vokal yerlesimi (v2_2): ayrilmis vokaldeki korunan parcalari HICBIR perde / sure islemi yapmadan
(yalniz kesme + yukseltilmis kosinus gecis + tam sayili ornek kaydirma + tek genel kazanc) yeni sarki formuna dizer.
(yeni3/vokal/kod/03_yerlestir.py'den uyarlandi.)

Girdi : yeni4/vokal/kaynak/v2_2_vokal.wav, yeni4/analiz/kesim/kesim.json, yeni4/analiz/tempo/lattice.json (+ tempo.json capraz kontrol)
Cikti : yeni4/vokal/vokal_dogal.wav (mono, 44.1 kHz, PCM_24), yeni4/vokal/yerlesim.json

Form  : 105.000 BPM, 0.100 s on bosluk; n. olcunun vurus-1'i = 0.100 + n * 2.285714 s (= 4410 + n * 100800 ornek);
        giris 4 olcu, 7 kita x 8 olcu, bitis 4 olcu, 2.5 s kuyruk. Kita v (0..6) = olcu 4 + 8 v.
Yerlesim: parca 1 (L1) -> kitanin 0. olcusu; parca 2 (L2) -> 2. olcu; parca 3 ('diye bagirir' + L4, tek parca) -> 'diye'yi iceren
        kaynak olcusunun cizgisi 5. olcunun vurus-1'ine (boylece 'diye' 5. olcunun 2. vurusuna, L4 6. olcuye duser).
        hedef_zaman = hedef_olcu_basi + (kaynak_zaman - kaynak_olcu_basi); kaydirma tam sayili ornek.
Kesimler ve gecisler kesim.json'dan. Soylenen hayvan sesleri (L2 sonu -> 'diye' basi) TAMAMEN atilir.
3. kita onarimi: 'atlari' 4 heceli soylenmis (a-ti-la-ri); fazladan cekirdek (ek unlu + uzatilmis l) kesilip atilir, bosluk
        KAPATILMAZ ('at' 6. vurusta, 'la' 7., 'ri' 7.25, 'var' 7.5'te kalir: 0 ms kayma).
"""
import sys, os, json, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortak import *

# ------------------------------------------------------------------ 3. kita onarim sabitleri (gerekceler: ara/dogal_baslangic.json, 01_incele.py)
# Kesim.json onerisi: [39.7537, 39.9660] atilsin; oncesinde 5 ms cikis, sonrasinda 10 ms giris gecisi.
# Burada iki gecis, ayni kesip atma araligi korunarak, olcume dayali olarak uzatildi:
#  - cikis gecisi 15 ms, 39.7537'de biter: /t/ surtunmesi 39.7357'de bitmistir; gecis yalniz -36..-41 dBFS'lik artik gurultuyu kapsar.
#  - giris gecisi 30 ms, 39.9660'i ORTALAR (yari genlik noktasi = onerilen ek yeri): bu sarkicinin otumsuz unsuzden sonraki dogal
#    otumlu baslangiclarinin %10-%90 yukselme suresi medyan 18 ms (24 ornek; ceyrekler 15-23 ms) = 31 ms'lik yukseltilmis kosinus.
#    10 ms'lik gecis (yukselme 6 ms) bu dagilimin en sert ucunda kalirdi. /l/'nin yari genlikten 'a'ya kadar suresi onerilen 55 ms olarak kalir.
ATLARI_CIKIS_GECIS = 0.015
ATLARI_GIRIS_GECIS = 0.030

# L2 cikis gecisi, 'var'in soylenen hayvan sesine ARALIKSIZ baglandigi kitalarda (1, 2, 3, 6, 7).
# Kesim.json onerisi 25 ms; burada 30 ms (gorevin verdigi 20-30 ms araliginin ust ucu) kullanilir. Dayanak (04_dogrula.py, bolum 6):
# zarfin -3 -> -15 dB dusus suresi 25 ms'lik geciste medyan 11.3 ms, 30 ms'de 14.0 ms; bu sarkicinin dogal kelime sonlari
# (7 x L1 'var,') 15.5-27.3 ms. 40 ms'de 2. kitanin 'var'i en kisa dogal 'var,'dan kisa kalir (198 ms < 206 ms), o yuzden 30.
# Bedel: 'var' yari genlik noktasinda 2.5 ms daha kisa (15 ms), enerji kaybi 0.16-0.24 dB (25 ms'de 0.13-0.20 dB).
# Gecis her durumda var_end'de biter (hayvan sesinden ornek kalmaz). Secenek: --l2-gecis-ms X (ornegin 25 = kesim.json onerisi).
L2_GECIS_VARSAYILAN_MS = 30.0
L2_GECIS_MS = float(sys.argv[sys.argv.index("--l2-gecis-ms") + 1]) if "--l2-gecis-ms" in sys.argv else L2_GECIS_VARSAYILAN_MS


def s(t):
    return int(round(t * SR))


def main():
    x = oku_vokal()
    K = oku_json(KESIM)
    T = oku_json(TEMPO)
    kafes = oku_json(KAFES)
    DB_ = oku_json(os.path.join(ARA, "dogal_baslangic.json"))        # 01b_dogal_baslangic.py'nin olcumu (giris gecisi uzunlugunun dayanagi)
    out = np.zeros(N_OUT)
    R = lambda v, n=5: round(float(v), n)
    SUNG = K["levels"]["sung_rms_dbfs"]
    tseg = {(g["verse"], g["name"]): g for g in T["segments"]}

    parcalar = []

    def parca(etiket, src_a, src_b, dst_a, n_in, n_out):
        n = src_b - src_a
        assert n > n_in + n_out > 0, (etiket, n, n_in, n_out)
        g = np.ones(n)
        if n_in:
            g[:n_in] = kos_yuksel(n_in)
        if n_out:
            g[n - n_out:] *= kos_alcal(n_out)
        assert dst_a >= 0 and dst_a + n <= N_OUT, etiket
        assert not np.any(out[dst_a:dst_a + n]), "ortusme: " + etiket
        out[dst_a:dst_a + n] += x[src_a:src_b] * g
        parcalar.append(dict(label=etiket, src_in_sample=src_a, src_out_sample=src_b, dest_in_sample=dst_a,
                             dest_out_sample=dst_a + n, fade_in_samples=n_in, fade_out_samples=n_out,
                             src_in=R(src_a / SR), src_out=R(src_b / SR), dest_in=R(dst_a / SR), dest_out=R((dst_a + n) / SR)))

    pieces_out, lines_out, removed, repairs, slots = [], [], [], [], []
    ex = K["atlari_check"]["excision"]
    atlari_var = K["atlari_check"]["verdict"].startswith("FOUR")
    k3 = {}

    for vi, V_ in enumerate(K["verses"]):
        v = V_["verse"]
        assert v == vi + 1
        bar0 = INTRO + KITA_OLCU * vi
        Ls = {L["name"]: L for L in V_["lines"]}
        piece_rec = {}
        for P in V_["pieces"]:
            p = P["piece"]
            src_bar = kaynak_olcu_basi(kafes, v, PARCA_KAYNAK_OLCUSU[p])
            # capraz kontrol: kesim.json ve tempo.json ayni olcu cizgisini soyluyor mu (4 hane yuvarlama payi 0.1 ms)
            assert abs(src_bar - P["placement"]["source_bar_downbeat"]) < 1.5e-4, (v, p, src_bar, P["placement"]["source_bar_downbeat"])
            assert abs(src_bar - tseg[(v, P["segments"][0])]["bar_downbeat"]) < 1.5e-4, (v, p)
            hedef_olcu = bar0 + PARCA_OLCUSU[p]
            assert hedef_olcu == P["placement"]["target_bar_index_in_song"]
            D_n = olcu_basi_n(hedef_olcu)
            kay = D_n - s(src_bar)                                   # tam sayili ornek kaydirma (hedef - kaynak)
            assert abs(kay / SR - P["placement"]["shift_s"]) < 2e-4, (v, p, kay / SR, P["placement"]["shift_s"])
            a, b = s(P["cut_in"]), s(P["cut_out"])
            n_in, n_out = s(P["fade_in_ms"] / 1000.0), s(P["fade_out_ms"] / 1000.0)
            if "fade_out_start" in P and P["fade_out_start"] is not None:
                assert abs((P["cut_out"] - P["fade_out_start"]) * 1000 - P["fade_out_ms"]) < 0.11, (v, p)
            if p == 2:
                hc = V_["hard_cuts"]["L2_end"]
                assert abs(P["cut_out"] - hc["recommended"]["cut_out"]) < 1e-6 and abs(P["fade_out_ms"] - hc["recommended"]["fade_ms"]) < 1e-6, (v, "L2 kesimi oneriyle ayni degil")
                if hc["recommended"]["residual_after_var_end_ms"] == 0.0:
                    n_out = s(L2_GECIS_MS / 1000.0)
            cid = "K%d_P%d" % (v, p)
            ilk = len(parcalar)
            if v == 3 and p == 2 and atlari_var:
                assert P["internal_excision"]["start"] == ex["start"] and P["internal_excision"]["end"] == ex["end"]
                e0, e1 = s(ex["start"]), s(ex["end"])
                nA, nB = s(ATLARI_CIKIS_GECIS), s(ATLARI_GIRIS_GECIS)
                b1 = e0                                             # 1. alt parca: cikis gecisi e0'da SIFIRA iner
                a2 = e1 - nB // 2                                   # 2. alt parca: giris gecisi e1'i ortalar
                parca(cid + "_a(ciftliginde at)", a, b1, a + kay, n_in, nA)
                parca(cid + "_b(lari var)", a2, b, a2 + kay, nB, n_out)
                k3 = dict(e0=e0, e1=e1, nA=nA, nB=nB, b1=b1, a2=a2, kay=kay, cid=cid)
            else:
                parca(cid, a, b, a + kay, n_in, n_out)
            prt = parcalar[ilk:]
            seg_ilk, seg_son = V_["segments"][P["segments"][0]], V_["segments"][P["segments"][-1]]
            rec = dict(
                id=cid, verse=v, piece=p, animal=V_["animal"], segments=P["segments"], text=P["text"],
                dest_bar=hedef_olcu, bar_in_verse=PARCA_OLCUSU[p], dest_bar_downbeat=R(D_n / SR, 6), dest_bar_downbeat_sample=D_n,
                src_bar_in_verse=PARCA_KAYNAK_OLCUSU[p], src_bar_downbeat=R(src_bar, 6),
                shift_samples=kay, shift_sec=R(kay / SR, 6),
                src_in=prt[0]["src_in"], src_out=prt[-1]["src_out"], dest_in=prt[0]["dest_in"], dest_out=prt[-1]["dest_out"],
                src_in_sample=prt[0]["src_in_sample"], src_out_sample=prt[-1]["src_out_sample"],
                dest_in_sample=prt[0]["dest_in_sample"], dest_out_sample=prt[-1]["dest_out_sample"],
                dest_in_minus_bar_downbeat_ms=R((prt[0]["dest_in_sample"] - D_n) / SR * 1000, 2),
                fade_in=dict(ms=R(n_in / SR * 1000, 2), samples=n_in, src_from=R(a / SR), src_to=R((a + n_in) / SR),
                             src_level_at_cut_dbfs=P.get("level_at_cut_in_dbfs")),
                fade_out=dict(ms=R(n_out / SR * 1000, 2), samples=n_out, src_from=R((b - n_out) / SR), src_to=R(b / SR),
                              src_level_at_cut_dbfs=P.get("level_at_cut_out_dbfs"), recommended_by_segmentation_ms=P["fade_out_ms"]),
                fade_shape="raised cosine",
                src_sound_start=seg_ilk["start"], src_sound_end=seg_son["end"],
                dest_sound_start=R(seg_ilk["start"] + kay / SR, 5), dest_sound_end=R(seg_son["end"] + kay / SR, 5),
                src_rms_dbfs=R(rms_db(x, seg_ilk["start"], seg_son["end"]), 2),
                parts=prt, repaired=bool(v == 3 and p == 2 and atlari_var),
                note=P.get("cut_out_note") if p == 2 else P.get("cut_in_note") if p == 3 else None)
            pieces_out.append(rec)
            piece_rec[p] = rec

        # ---------------- atilan soylenen hayvan sesi + gercek hayvan sesi yuvalari
        h = V_["hard_cuts"]
        p2, p3 = piece_rec[2], piece_rec[3]
        b3, b4 = olcu_basi_n(bar0 + 3), olcu_basi_n(bar0 + 4)
        removed.append(dict(
            verse=v, animal=V_["animal"], what="sung animal sound (two words) between line 2 and 'diye'", text=V_["segments"]["ses"]["text"],
            src_from=p2["src_out"], src_to=p3["src_in"], src_removed_sec=R(p3["src_in"] - p2["src_out"], 4),
            src_sound=[V_["segments"]["ses"]["start"], V_["segments"]["ses"]["end"]],
            what_follows_var=h["L2_end"]["what_follows"], var_end=h["L2_end"]["var_end"], src_gap_var_to_animal_ms=h["L2_end"]["gap_ms"],
            l2_fade_out_ms=p2["fade_out"]["ms"],
            source_samples_after_var_end_kept=max(0, p2["src_out_sample"] - s(h["L2_end"]["var_end"])),
            dest_silence_from=p2["dest_out"], dest_silence_to=p3["dest_in"],
            dest_silence_sec=R(p3["dest_in"] - p2["dest_out"], 4)))
        slots.append(dict(
            verse=v, animal=V_["animal"],
            call_1=dict(bar=bar0 + 3, bar_downbeat=R(b3 / SR, 6), start=R(b3 / SR - 0.040, 6),
                        silence_between_L2_end_and_call_start_ms=R((b3 / SR - 0.040 - p2["dest_out_sample"] / SR) * 1000, 1)),
            call_2=dict(bar=bar0 + 4, bar_downbeat=R(b4 / SR, 6), start=R(b4 / SR - 0.040, 6)),
            diye_vocal_in=p3["dest_in"],
            free_window_for_call_2_sec=R(p3["dest_in"] - (b4 / SR - 0.040), 4),
            note="vocal is digital silence from L2's dest_out to 'diye' dest_in; a negative silence_between value means L2's faded tail overlaps the call start"))

        # ---------------- dize ve hece kayitlari
        for name, p, olcu_kita, vurus_kay in (("L1", 1, 0, 0), ("L2", 2, 2, 4), ("diye", 3, 5, 8), ("L4", 3, 6, 12)):
            L = Ls[name]
            rec = piece_rec[p]
            kay = rec["shift_samples"]
            olcu = bar0 + olcu_kita
            Dl_n = olcu_basi_n(olcu)
            sg = V_["segments"][name]
            syl = []
            for h_ in L["syllables"]:
                if h_.get("excise") or not h_["kept"]:
                    continue
                st, en = h_["start"], h_["end"]
                bib = h_["beat_expected"] - vurus_kay                  # hedef olcu icindeki vurus (izgara yuvasi)
                t_izg = Dl_n / SR + bib * BEAT
                d = lambda t: R(t + kay / SR, 5)
                syl.append(dict(
                    index=len(syl), text=h_["text"], word=h_["word"],
                    src_start=R(st, 4), src_end=R(en, 4), dest_start=d(st), dest_end=d(en), duration=R(en - st, 4),
                    midi=h_["f0_midi"], note=h_["note"], cents_from_note=h_["cents_from_note"],
                    pitch_start=h_["pitch_start_midi"], pitch_mid=h_["pitch_mid_midi"], pitch_end=h_["pitch_end_midi"],
                    glide_semitones=h_["glide_semitones"], is_glide=h_["is_glide"], f0_iqr_semitones=h_["f0_iqr_semitones"],
                    voiced_ratio=h_["voiced_ratio"],
                    src_nucleus=R(h_["nucleus"], 4), dest_nucleus=d(h_["nucleus"]),
                    src_core_start=R(h_["core_start"], 4), src_core_end=R(h_["core_end"], 4),
                    dest_core_start=d(h_["core_start"]), dest_core_end=d(h_["core_end"]),
                    dest_bar=olcu, bar_in_verse=olcu_kita, beat_in_bar=bib, dest_grid_time=R(t_izg, 5),
                    start_minus_grid_ms=R((st + kay / SR - t_izg) * 1000, 1),
                    notes=[dict(note=q["note"], midi=q["midi"], src_start=R(q["start"], 4), src_end=R(q["end"], 4),
                                dest_start=d(q["start"]), dest_end=d(q["end"]), plateau_ms=q.get("plateau_ms"), no_plateau=q.get("no_plateau"))
                           for q in h_.get("notes", [])],
                    rms_dbfs=h_.get("rms_dbfs"), peak_dbfs=h_.get("peak_dbfs"),
                    boundary_flag=h_["flag"], flag_reason=h_.get("flag_reason"),
                    end_boundary_kind=(h_.get("end_boundary") or {}).get("kind"), end_boundary_where=(h_.get("end_boundary") or {}).get("where")))
            src_bar_own = kaynak_olcu_basi(kafes, v, dict(L1=0, L2=1, diye=2, L4=3)[name])
            beklenen_vurus = 2.0 if name == "diye" else 0.0
            lines_out.append(dict(
                verse=v, line=name, animal=V_["animal"], text=L["text"], piece=rec["id"],
                repaired=bool(v == 3 and name == "L2" and atlari_var),
                dest_bar=olcu, bar_in_verse=olcu_kita, dest_bar_downbeat=R(Dl_n / SR, 6), src_bar_downbeat=R(src_bar_own, 6),
                shift_samples=kay, shift_sec=R(kay / SR, 6),
                src_start=sg["start"], src_end=sg["end"], dest_start=R(sg["start"] + kay / SR, 5), dest_end=R(sg["end"] + kay / SR, 5),
                expected_beat_in_bar=beklenen_vurus,
                onset_minus_expected_beat_ms=R((sg["start"] + kay / SR - Dl_n / SR - beklenen_vurus * BEAT) * 1000, 1),
                src_rms_dbfs=L["rms_dbfs"], src_peak_dbfs=L["peak_dbfs"],
                note_sequence=L.get("note_sequence"),
                syllables=syl))

    # ------------------------------------------------------------------ tek genel kazanc + yazma
    tepe = float(np.max(np.abs(out)))
    kazanc = 10 ** (TEPE_DBFS / 20.0) / tepe
    y = out * kazanc
    sf.write(CIKTI_WAV, y, SR, subtype="PCM_24")

    # ------------------------------------------------------------------ onarim: 3. kita 'atlari'
    if k3:
        q = k3
        ac = K["atlari_check"]
        lm = ac["landmarks"]
        L2 = K["verses"][2]["lines"][1]
        atilan = [h_ for h_ in L2["syllables"] if h_.get("excise")][0]
        w = [w_ for w_ in L2["words"] if w_["text"] == "atları"][0]
        kay = q["kay"]
        d = lambda t: R(t + kay / SR, 5)
        var = [h_ for h_ in L2["syllables"] if h_["text"] == "var"][0]
        repairs.append(dict(
            id="K3_L2_atlari", verse=3, line="L2", type="excision of an extra sung syllable (no pitch or time processing)",
            what="the singer sang 'a-tı-la-rı' (four nuclei); the extra nucleus (a bright vowel of 82 ms + a sustained /l/ of 180 ms on its own note E4, on beat 6.5) is cut out; what remains is 'at' + rest + 'ları'",
            evidence=dict(verdict=ac["verdict"], voiced_stretch_before_second_a_ms=lm["voiced_stretch_before_second_a_ms"],
                          same_stretch_in_24_other_words_ms=[ac["duration_comparison_consonant_l_vowel"]["min_ms"], ac["duration_comparison_consonant_l_vowel"]["max_ms"]],
                          excised_nucleus=dict(text=atilan["text"], src_start=atilan["start"], src_end=atilan["end"], midi=atilan["f0_midi"], note=atilan["note"],
                                               rms_dbfs=atilan["rms_dbfs"], peak_dbfs=atilan["peak_dbfs"])),
            excision=dict(src_from=ex["start"], src_to=ex["end"], removed_ms=ex["removed_ms"],
                          dest_from=d(ex["start"]), dest_to=d(ex["end"]),
                          start_definition=ex["start_definition"], end_definition=ex["end_definition"]),
            fade_out_before=dict(ms=R(q["nA"] / SR * 1000, 2), src_from=R((q["b1"] - q["nA"]) / SR), src_to=R(q["b1"] / SR),
                                 dest_from=R((q["b1"] - q["nA"] + kay) / SR), dest_to=R((q["b1"] + kay) / SR),
                                 recommended_by_segmentation_ms=ex["recommended_fades"]["fade_out_before_start_ms"],
                                 why="15 ms instead of 5 ms: it starts after the end of the /t/ frication (%.4f) and only covers the residual noise at -36..-41 dBFS; reaches exact zero at the excision start" % lm["t_frication_end"]),
            fade_in_after=dict(ms=R(q["nB"] / SR * 1000, 2), src_from=R(q["a2"] / SR), src_to=R((q["a2"] + q["nB"]) / SR),
                               dest_from=R((q["a2"] + kay) / SR), dest_to=R((q["a2"] + q["nB"] + kay) / SR),
                               half_amplitude_point_src=R(q["e1"] / SR),
                               recommended_by_segmentation_ms=ex["recommended_fades"]["fade_in_after_end_ms"],
                               natural_onset_rise_10_90_ms=dict(n=len(DB_["rows"]), median=R(DB_["median_ms"], 1), q25=R(DB_["q25_ms"], 1), q75=R(DB_["q75_ms"], 1),
                                                                equivalent_raised_cosine_ms=R(DB_["equivalent_raised_cosine_ms"]["median"], 1),
                                                                definition="100-1000 Hz band, 3 ms RMS envelope, rise from 10 % to 90 % of the level 15-35 ms after voicing starts, at this singer's voicing onsets after voiceless consonants (çift|li, nek|le, ...)"),
                               why="30 ms centred on the recommended splice point instead of 10 ms after it: this singer's own voiced onsets after voiceless consonants rise (10-90 %%) in %.0f ms median (n=%d, quartiles %.0f-%.0f ms), which equals a %.0f ms raised cosine; a 10 ms fade (6 ms rise) would be at the hardest end of that range. The /l/ still lasts 55 ms from the half-amplitude point to the vowel 'a'."
                                   % (DB_["median_ms"], len(DB_["rows"]), DB_["q25_ms"], DB_["q75_ms"], DB_["equivalent_raised_cosine_ms"]["median"])),
            silence_inside_word=dict(dest_from=R((q["b1"] + kay) / SR), dest_to=R((q["a2"] + kay) / SR), ms=R((q["a2"] - q["b1"]) / SR * 1000, 2),
                                     note="exact digital zero; from the end of the vowel 'a' of 'at' (%.4f) to the half-amplitude point of the /l/ there are %.0f ms without voicing, with the /t/ release (%.4f-%.4f) in between"
                                          % (lm["first_a_end_t_closure_start"], (ex["end"] - lm["first_a_end_t_closure_start"]) * 1000, lm["t_burst_onset"], lm["t_frication_end"])),
            rhythm=dict(option="A (gap left open, recommended by the segmentation)", shift_of_at_ms=0.0, shift_of_lari_ms=0.0, shift_of_var_ms=0.0,
                        beats_in_dest_bar=dict(at=2.0, rest=2.5, la=3.0, ri=3.25, var=3.5),
                        var_dest_start=d(var["start"]), var_dest_nucleus=d(var["nucleus"]),
                        note="every remaining sample keeps its original time; 'var' stays exactly in time"),
            durations=dict(
                before=dict(word_src=[w["start"], w["end"]], word_ms=R((w["end"] - w["start"]) * 1000, 1), nuclei=4,
                            sounding_ms=R((w["end"] - w["start"]) * 1000, 1)),
                after=dict(at_ms=ex["what_remains"]["at_ms"], rest_ms=ex["removed_ms"], lari_ms=ex["what_remains"]["lari_ms"], nuclei=3,
                           word_span_ms=ex["what_remains"]["word_span_ms_if_left_in_place"],
                           sounding_ms=R(ex["what_remains"]["at_ms"] + ex["what_remains"]["lari_ms"], 1))),
            pieces=[p_ for p_ in parcalar if p_["label"].startswith(q["cid"])],
            not_verified_by_ear="that 'at' + an eighth-note rest + 'ları' sounds natural was not checked by listening"))

    # ------------------------------------------------------------------ yerlesim.json
    nf = K["noise_floor"]
    outl = K["notes_table"]["pitch_outliers"]
    yer = dict(
        description="Natural placement of the v2_2 vocal (first AI take, separated stem) on the new song form: cut, raised-cosine fades, integer-sample shifts and ONE global gain only. No pitch processing, no time processing, no resampling.",
        not_verified_by_ear="Everything here is measured by code; nobody listened to the result.",
        schema={
            "time_base": "src_* = seconds on the timeline of yeni4/vokal/kaynak/v2_2_vokal.wav (= v2_2.mp3); dest_* = seconds on the timeline of vokal_dogal.wav (0.100 s lead-in, bar n downbeat at 0.100 + n * 2.285714)",
            "pieces[]": "the 21 placed chunks (3 per verse: P1 = L1, P2 = L2, P3 = 'diye bağırır' + L4). src_in/src_out, dest_in/dest_out = extent of the audio INCLUDING the fades; dest_bar_downbeat = bar line the piece is anchored to; parts[] = the contiguous audio parts actually copied (two for the repaired K3_P2); fade_* = raised-cosine fades at the piece edges",
            "lines[]": "the 28 sung lines (L1, L2, diye, L4 per verse). dest_bar = the bar the line is sung in (L4 = the bar after 'diye'); src_start/src_end = acoustic start / end from the segmentation; onset_minus_expected_beat_ms = where the first sound falls relative to its beat (negative = before)",
            "lines[].syllables[]": {
                "text, word": "kept syllables only (229); the excised extra nucleus of verse 3 is listed under repairs",
                "src_start/src_end, dest_start/dest_end": "syllable boundaries from the segmentation (dest = src + shift of the piece)",
                "midi": "ORIGINAL sung pitch: median f0 over the syllable core (MIDI, A4 = 69 = 440 Hz)",
                "pitch_start / pitch_mid / pitch_end": "medians over the first quarter / middle half / last quarter of the core frames (MIDI)",
                "dest_nucleus, dest_core_start/end": "nucleus = instant of the envelope PEAK of the vowel (not its onset); core = the voiced core used for the pitch medians; both on the destination timeline",
                "dest_bar, beat_in_bar, dest_grid_time": "the grid slot of the syllable in the new form (sixteenth-note grid of the segmentation) and its time",
                "start_minus_grid_ms": "syllable start (its consonant) against the grid slot; negative = starts before the beat so that the vowel lands on it",
                "notes[]": "stable note plateaus inside the syllable",
                "boundary_flag": "true = a boundary of this syllable was placed on the beat grid by the segmentation (li|ğin, di|ye)"},
            "syllables_flat[]": "the same 229 kept syllables as one flat table (verse, line, piece, text, src/dest start and end, median MIDI, start / mid / end pitch, bar and beat slot); lines[].syllables[] has the full detail",
            "removed_animal_sounds[]": "per verse the source range that was dropped (sung animal sounds) and the resulting digital silence in the destination",
            "animal_call_slots[]": "where the real animal calls go (40 ms before the downbeats of bars 3 and 4 of the verse) and the margins to the vocal",
            "repairs[]": "edits other than plain cutting and shifting", "open_questions[]": "things measured but deliberately NOT changed"},
        form=dict(bpm=BPM, beat_sec=R(BEAT, 6), bar_sec=R(BAR, 6), beat_samples=BEAT_N, bar_samples=BAR_N, lead_in_sec=GIRIS, lead_in_samples=GIRIS_N,
                  meter="4/4", intro_bars=INTRO, verse_bars=KITA_OLCU, verses=N_KITA, ending_bars=SON, total_bars=TOPLAM_OLCU, tail_sec=KUYRUK_N / SR,
                  duration_sec=R(N_OUT / SR, 6), samples=N_OUT, sample_rate=SR,
                  bar_downbeat_formula="t(bar n) = 0.100 + n * 2.285714 s = (4410 + n * 100800) samples",
                  verse_start_bars=[INTRO + KITA_OLCU * i for i in range(N_KITA)],
                  verse_start_sec=[R(olcu_basi_n(INTRO + KITA_OLCU * i) / SR, 6) for i in range(N_KITA)],
                  bars_in_verse={"0": "vocal L1", "1": "instrumental answer", "2": "vocal L2", "3": "real animal call 1", "4": "real animal call 2",
                                 "5": "drum fill (beats 0-1), vocal 'diye bağırır' (beats 2-3)", "6": "vocal L4", "7": "instrumental answer"}),
        audio=dict(file="vokal_dogal.wav", channels=1, sample_rate=SR, subtype="PCM_24",
                   global_gain_db=R(20 * np.log10(kazanc), 4), global_gain_linear=float(kazanc), peak_dbfs_target=TEPE_DBFS,
                   peak_before_gain_dbfs=R(20 * np.log10(tepe), 4), per_piece_gain="none",
                   sung_rms_dbfs_source=SUNG, sung_rms_dbfs_dest=R(SUNG + 20 * np.log10(kazanc), 2),
                   silence="exact digital zero outside the placed parts",
                   processing="cut + raised-cosine fades + integer-sample shift + one global gain; no pitch shift, no time stretch, no resampling",
                   source="yeni4/vokal/kaynak/v2_2_vokal.wav (mono 44.1 kHz 24-bit, UVR-MDX-NET-Voc_FT stem, sample-aligned with v2_2.mp3)"),
        placement_rule=dict(
            how="the source bar line (constant machine lattice of the mp3: lattice.json, %.6f BPM, beat n at %.8f + n * %.10f s; verse v downbeat = beat 15 + 24 (v-1)) is mapped onto the destination bar line: dest_time = dest_bar_downbeat + (src_time - src_bar_downbeat), rounded to whole samples"
                % (kafes["bpm"], kafes["phase_first_beat_s"], kafes["beat_period_s"]),
            anchors="P1: source bar 0 of the verse -> bar 0 of the verse; P2: source bar 1 -> bar 2; P3: source bar 2 (the bar that contains 'diye') -> bar 5, so 'diye' lands on beat 2 of bar 5 and L4 on bar 6",
            tempo_difference="source lattice %.6f BPM, destination 105.000 BPM: %.3f ms per bar; no stretch is applied, so L4 (one bar after P3's anchor) sits %.3f ms early against its own bar line"
                             % (kafes["bpm"], (BAR - kafes["bar_period_s"]) * 1000, (BAR - kafes["bar_period_s"]) * 1000),
            fades="all cut points are the segmentation's (kesim.json pieces[]) and so are the fade lengths, with two measured exceptions: the line-2 fade-out in verses 1, 2, 3, 6, 7 (see options) and the two fades at the verse-3 excision (see repairs)",
            pickup="pieces that begin with a consonant before the bar line begin before the destination bar line by the same amount (dest_in_minus_bar_downbeat_ms)"),
        summary=dict(
            pieces=len(pieces_out), parts=len(parcalar), lines=len(lines_out), syllables=sum(len(l["syllables"]) for l in lines_out),
            repairs=[r["id"] for r in repairs],
            first_vocal_sample_sec=pieces_out[0]["dest_in"], last_vocal_sample_sec=pieces_out[-1]["dest_out"],
            noise_floor=dict(stem_between_verses_dbfs_source=nf["between_verses_rms_dbfs"], stem_between_verses_db_re_sung=nf["between_verses_db_re_sung"],
                             in_this_file="digital zero between the pieces (the stem's residual between the verses is not copied)")),
        options=dict(l2_fade_out_ms_no_gap_verses=L2_GECIS_MS, l2_fade_out_ms_default=L2_GECIS_VARSAYILAN_MS, l2_fade_out_ms_recommended_by_segmentation=25.0,
                     note="line-2 fade-out in the verses where 'var' runs into the sung animal sound without a gap (1, 2, 3, 6, 7): 30 ms instead of the segmentation's 25 ms, because the envelope then falls (-3 -> -15 dB) in 14 ms median instead of 11 ms, closer to this singer's natural word endings (15.5-27.3 ms at the seven 'var,' of line 1); cost: 'var' is 2.5 ms shorter at the half-amplitude point. The fade always ends at var_end. Rebuild with --l2-gecis-ms 25 for the segmentation's value."),
        pieces=pieces_out, lines=lines_out, removed_animal_sounds=removed, animal_call_slots=slots, repairs=repairs,
        open_questions=[
            dict(id="K7_L4_cift_low", what="verse 7 line 4 'çift' is sung on %s (MIDI %.2f), %.1f semitones below the other verses (80 ms vowel)" % (
                [o for o in outl if o["verse"] == 7 and o["line"] == "L4"][0]["note"], [o for o in outl if o["verse"] == 7 and o["line"] == "L4"][0]["f0_midi"],
                -[o for o in outl if o["verse"] == 7 and o["line"] == "L4"][0]["deviation_semitones"]),
                 decision="NOT changed: no pitch processing is allowed in this step and the segmentation did not recommend a repair; a short low pickup into the leap to G4. The pitch step ('ezgi') retunes it anyway."),
            dict(id="K7_L1_nin_sag", what="verse 7 line 1 'nın' sags from A4 to about F4 (median G4, 1.8 semitones below the other verses)", decision="NOT changed (as sung)"),
            dict(id="K3_L4_cift_sag", what="verse 3 line 4 'çift' sags from MIDI 61.9 to 59.9 inside the syllable", decision="NOT changed (as sung)"),
            dict(id="L2_endings_full_level", what="in verses 1, 2, 3, 6, 7 'var' runs into the sung animal sound without any low point: line 2 is cut at full level with a %.0f ms fade ending exactly at var_end" % L2_GECIS_MS,
                 decision="cut point as recommended by the segmentation; nothing after var_end is kept. In the mix the real animal call starts 20-37 ms after the cut, and a light reverb on the vocal bus would give these endings a tail. Whether they sound clipped was not checked by ear."),
            dict(id="breaths", what="breaths / pre-phonation before line 1 of verses 1-3 (peak -35 .. -46 dBFS) and a puff after the last word of verse 2 (31.45-31.60 s, peak -31 dBFS)",
                 decision="NOT included (default cuts of the segmentation); alternatives are in kesim.json (breath_before.cut_in_with_breath, after_sound.cut_out_including_after_sound)"),
            dict(id="grid_boundaries", what="16 syllable boundaries have no acoustic mark and sit on the beat grid (14 x li|ğin in 'çiftliğinde', 2 x di|ye in verses 4 and 7)",
                 decision="no audio consequence here (nothing is cut there); it only matters for per-syllable pitch processing in the 'ezgi' step"),
            dict(id="stem_residue", what="the pieces are continuous stretches of the separated stem, so whatever the separator left of the old D-minor band inside the sung bars is still inside them",
                 decision="not treated here (no filtering or gating inside the pieces)")])
    # duz hece tablosu (ayni veriler; kolay okunsun diye): her korunan hece bir satir
    yer["syllables_flat"] = [dict(verse=L["verse"], line=L["line"], piece=L["piece"], index=h["index"], text=h["text"], word=h["word"],
                                  src_start=h["src_start"], src_end=h["src_end"], dest_start=h["dest_start"], dest_end=h["dest_end"],
                                  midi=h["midi"], pitch_start=h["pitch_start"], pitch_mid=h["pitch_mid"], pitch_end=h["pitch_end"],
                                  dest_bar=h["dest_bar"], beat_in_bar=h["beat_in_bar"])
                             for L in lines_out for h in L["syllables"]]
    with open(CIKTI_JSON, "w", encoding="utf8") as f:
        json.dump(yer, f, ensure_ascii=False, indent=1)
    print("yazildi:", CIKTI_WAV, "%.6f s, %d ornek" % (N_OUT / SR, N_OUT))
    print("genel kazanc %.4f dB (kazanc oncesi tepe %.4f dBFS)" % (20 * np.log10(kazanc), 20 * np.log10(tepe)))
    print("parca: %d | alt parca: %d | dize: %d | hece: %d" % (len(pieces_out), len(parcalar), len(lines_out), sum(len(l["syllables"]) for l in lines_out)))
    for c in pieces_out:
        print("  %-6s olcu %2d (cizgi %9.4f)  kaynak %8.4f-%8.4f -> hedef %9.4f-%9.4f  giris %4.1f ms, cikis %4.1f ms  kaydirma %d ornek" % (
            c["id"], c["dest_bar"], c["dest_bar_downbeat"], c["src_in"], c["src_out"], c["dest_in"], c["dest_out"], c["fade_in"]["ms"], c["fade_out"]["ms"], c["shift_samples"]))


if __name__ == "__main__":
    main()
