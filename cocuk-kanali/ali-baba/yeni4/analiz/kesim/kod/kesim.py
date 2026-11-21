#!/usr/bin/env python3
"""3. adim (ana betik): v2_2 ayrilmis vokalinin kesimi.
Girdi : yeni4/vokal/kaynak/v2_2_vokal.wav, v2_2_words.json, yeni4/analiz/tempo/{tempo,lattice}.json, ara/ozellik.npz
Cikti : kesim.json (anahtarlar Ingilizce)

Icerik
  1) kita basina 5 bolum (L1, L2, ses, diye, L4) + saklanacak 3 parca icin kesim noktalari ve sonumleme sureleri;
     iki zor kesimin (L2 sonu -> soylenen hayvan sesi, soylenen hayvan sesi -> "diye") olcumleri
  2) heceler: sinir, perde (ortanca / bas-orta-son / notalar), sesli orani
  3) 3. kita "atları" denetimi + diger kelimelerin taramasi
  4) soylenen notalarin tablosu (dize basina, vurus basina, perde sinifi dagilimlari)
  5) gurultu tabani
yeni3/analiz/kesim/kod/kesim.py'den uyarlandi (harf-HMM'i yerine vurus izgarasi sablonu: bkz. izgara.py)."""
import os, json, collections, numpy as np
import hece, perde, atlari
from zarf import (z, x, fs, t, DT, fi, E12, E30, ELOW8, F2B, EHI, R5, th, f0h, f0s, FP, midi, db_ham, nota_adi, NOTA, r4, r1, r2)
from ortak import (K, A, VOKAL, HAYVAN, HAYVAN_KELIME, SAKLANAN, SOYLENEN, kelimeleri_oku, kitalari_esle, kucuk, hecele,
                   bolum_sozu, beklenen_hece, kita_vuruslari, tempo_oku, BEAT, BAR)
from izgara import kita_heceleri, BEAT_OLC, SABLON
from dize import dizeleri_bul

kita = kitalari_esle(kelimeleri_oku())
vd = kita_vuruslari()
DZ, SEV = dizeleri_bul(kita)
SUNG = SEV["soylenen_rms_dbfs"]
hece.SUNG = SUNG
hece.VOIG = (np.interp(t, th, (f0h > 0).astype(float)) > 0.5) & (ELOW8 > SUNG - perde.KAPI_DB)     # sesli ve alcak bandi guclu
perde.kur(SUNG)
TEMPO = tempo_oku()
BAR_OLC = 4 * BEAT_OLC
SRC_BAR = {"L1": 0, "L2": 1, "ses": 2, "diye": 2, "L4": 3}            # kaynak kayitta kita icindeki olcu
HEDEF_BAR = {"L1": 0, "L2": 2, "diye": 5, "L4": 6}                    # yeni sarki biciminde kita icindeki olcu
LEAD_IN = 0.100


def rms_db(a, b):
    seg = x[max(0, int(a * fs)):int(b * fs)]
    return float(10 * np.log10(np.mean(seg ** 2) + 1e-20)) if len(seg) else -200.0


def tepe_db(a, b):
    seg = x[max(0, int(a * fs)):int(b * fs)]
    return float(20 * np.log10(np.abs(seg).max() + 1e-12)) if len(seg) else -200.0


def kosinus_cikis(n):
    return np.cos(np.linspace(0, np.pi / 2, n, endpoint=False)) ** 2


def sonum_degerlendir(f0_, f1_, var_bas, var_bit):
    """Yukseltilmis kosinus cikis sonumlemesi [f0_, f1_] (f1_'den sonra sifir). 'var' kaybi ve var_bit'ten sonra kalan artik."""
    i0, i1 = int(round(f0_ * fs)), int(round(f1_ * fs))
    vb, ve = int(round(var_bas * fs)), int(round(var_bit * fs))
    g = np.ones(max(i1, ve) - vb + 1)
    g[i0 - vb:i1 - vb] = kosinus_cikis(i1 - i0); g[i1 - vb:] = 0.0
    seg = x[vb:vb + len(g)]
    E0 = float(np.sum(seg[:ve - vb] ** 2)); Ef = float(np.sum((seg[:ve - vb] * g[:ve - vb]) ** 2))
    art = seg[ve - vb:] * g[ve - vb:]
    Er = float(np.sum(art ** 2))
    yari = f0_ + (f1_ - f0_) * 0.5                    # kazancin 0.5 oldugu an (-6 dB)
    return {"fade_start": r4(f0_), "cut_out": r4(f1_), "fade_ms": round((f1_ - f0_) * 1000, 1),
            "var_energy_loss_db": round(10 * np.log10(Ef / E0 + 1e-12), 2),
            "var_shortened_ms_at_minus6db": round(max(0.0, var_bit - yari) * 1000, 1),
            "residual_after_var_end_ms": round(max(0.0, f1_ - var_bit) * 1000, 1),
            "residual_energy_db_re_var": None if Er <= 0 else round(10 * np.log10(Er / E0), 1),
            "residual_peak_dbfs": None if Er <= 0 else round(float(20 * np.log10(np.abs(art).max() + 1e-12)), 1)}


# ====================================================================================== kitalar
verses = []; TUM = []            # TUM: (v, bolum, hece sozlugu) - ic kullanim
for v in range(7):
    H = kita_heceleri(kita, v, vd[v])
    dz = DZ[v]
    for adlar in (["L1"], ["L2"], ["diye", "L4"]):
        hs = [h for ad in adlar for h in H[ad]]
        hece.parca_sinirlari(hs, dz[adlar[0]]["baslangic"], dz[adlar[-1]]["bitis"])
    # ---------------- 3. kita "atları": dort cekirdek -> at | (atilacak) | la | rı
    atl = None
    if v in SOYLENEN:
        w = [h for h in H["L2"] if h["word_i"] == 1]
        assert [h["text"] for h in w] == ["a", "tı", "la", "rı"], [h["text"] for h in w]
        var_h = [h for h in H["L2"] if h["word_i"] == 2][0]
        atl = atlari.atlari_olc(w[0], w[1], w[2], w[3], var_h, SUNG)
        TUTULAN_L = 0.055                                   # "la"nin onunde birakilan l suresi (s)
        kes_bas = atl["quiet_instant"]; kes_bit = atl["second_a"]["onset"] - TUTULAN_L
        atl["excision"] = {"start": kes_bas, "end": kes_bit, "kept_l_ms": TUTULAN_L * 1000}
        atl["as_sung"] = [{"text": h["text"], "start": h["start"], "end": h["end"], "nuc": h["nuc"], "beat": h["beat"]} for h in w]
        # hece tablosunu yeniden kur: "at" = a + t kapanisi + t salinimi ; atilan ; "la" ; "rı"
        w[0]["end"] = kes_bas; w[0]["text"] = "at"; w[0]["coda"] = "t"
        w[0]["end_boundary"] = {"consonants": "t|", "t": kes_bas, "kind": "dip", "where": "quiet_instant_after_t_release",
                                "depth_db": None, "level_dbfs": round(atl["quiet_level_dbfs"], 1)}
        w[1]["start"] = kes_bas; w[1]["end"] = kes_bit; w[1]["text"] = "(tı)"; w[1]["excise"] = True
        w[1]["end_boundary"] = {"consonants": "|l", "t": kes_bit, "kind": "splice", "where": "inside_sustained_l",
                                "depth_db": None}
        w[2]["start"] = kes_bit
    for ad in SAKLANAN:
        for h in H[ad]:
            TUM.append((v, ad, h))
    verses.append({"H": H, "atl": atl})

# ====================================================================================== hece / kelime / dize ciktisi
BLIND_NOT = "blind envelope peak picking found %d nuclei, expected %d"


def hece_cikti(v, ad, h):
    a, b = h["start"], h["end"]
    ip, cs, ce = perde.cekirdek_ic(a, b, hece.VOIG)
    h["nuc2"], h["cs2"], h["ce2"] = ip, cs, ce
    pp = perde.hece_perdesi(a, b, cs, ce)
    eb = h.get("end_boundary")
    sd = {"text": h["text"], "word": h["word"], "word_index": h["word_i"], "index_in_word": h["syl_i"], "line": ad,
          "kept": not h.get("excise", False), "excise": bool(h.get("excise", False)),
          "beat_expected": h["beat"], "t_expected": r4(h["t_exp"]),
          "start": r4(a), "end": r4(b), "duration": r4(b - a),
          "nucleus": r4(ip), "core_start": r4(cs), "core_end": r4(ce)}
    for k_ in ("f0_hz", "f0_midi", "note", "cents_from_note", "f0_iqr_semitones", "f0_dio_midi", "voiced_ratio",
               "pitch_start_midi", "pitch_mid_midi", "pitch_end_midi", "pitch_start_note", "pitch_mid_note", "pitch_end_note",
               "glide_semitones", "is_glide"):
        sd[k_] = pp.get(k_)
    sd["notes"] = [{"note": n_["note"], "midi": n_["midi"], "start": r4(n_["start"]), "end": r4(n_["end"]),
                    "duration_ms": int(round((n_["end"] - n_["start"]) * 1000)), "plateau_ms": n_["plateau_ms"],
                    "no_plateau": n_["no_plateau"]} for n_ in pp["notes"]]
    ia, ib = fi(a), fi(b)
    sd["peak_dbfs"] = round(float(db_ham[ia:ib + 1].max()), 1)
    sd["rms_dbfs"] = round(rms_db(a, b), 1)
    sd["end_boundary"] = None if eb is None else {k_: (r4(val) if k_ == "t" else val) for k_, val in eb.items()}
    if eb is not None:
        sd["end_boundary"]["level_at_t_dbfs"] = round(float(R5[fi(eb["t"])]), 1)
        sd["end_boundary"]["voiced_at_t"] = bool(hece.VOIG[fi(eb["t"])])       # sesli VE alcak bant > soylenen - 11 dB
    return sd


out_verses = []
tum_kelime = []; tum_hece = []
for v in range(7):
    H = verses[v]["H"]; dz = DZ[v]; atl = verses[v]["atl"]
    lines = []
    for ad in SAKLANAN:
        hs = H[ad]
        syls = [hece_cikti(v, ad, h) for h in hs]
        words = []
        for j, q in enumerate(kita[v][ad]):
            wi = [i for i, h in enumerate(hs) if h["word_i"] == j]
            wh = [hs[i] for i in wi]; ws_ = [syls[i] for i in wi]
            ws, we = wh[0]["start"], wh[-1]["end"]
            tep, ksin = hece.kor_cekirdek(ws, we)
            bek = len(hecele(q["soz"]))
            ic = [h["end_boundary"] for h in wh[:-1]]
            turler = [s_["kind"] for s_ in ic]
            kural = [i for i, k_ in enumerate(turler) if k_ == "grid"]
            neden = []
            if kural:
                neden.append("no acoustic boundary at %s (same vowel, same pitch): placed on the beat grid" % (
                    ",".join(wh[i]["text"] + "|" + wh[i + 1]["text"] for i in kural)))
            sapma = v in SOYLENEN and ad == "L2" and j == 1
            if sapma:
                neden.append("lyric deviation: sung with %d syllable nuclei (%s), expected %d (%s); the extra nucleus is marked excise=true"
                             % (len(wh), "-".join(hecele(SOYLENEN[v])), bek, "-".join(hecele(q["soz"]))))
            pm = perde.ortanca(ws, we)
            wd = {"text": q["soz"], "start": r4(ws), "end": r4(we), "json_start": q["json_bas"], "json_end": q["json_bit"],
                  "syllables_expected": bek, "syllable_nuclei_sung": len(wh),
                  "flag": bool(kural or sapma), "flag_reason": "; ".join(neden) if neden else None,
                  "boundary_kinds": turler,
                  "blind_check": {"nuclei_detected": len(tep), "count_matches": len(tep) == bek,
                                  "note": None if len(tep) == bek else BLIND_NOT % (len(tep), bek)},
                  "f0_all_midi": None if pm is None else round(pm, 2)}
            if sapma:
                wd["text_as_sung"] = SOYLENEN[v]
            words.append(wd); tum_kelime.append((v + 1, ad, wd))
            for i in wi:
                eb = hs[i].get("end_boundary"); onc = hs[i - 1].get("end_boundary") if i > 0 else None
                kr = [b_ for b_ in (onc, eb) if b_ is not None and b_["kind"] == "grid"]
                syls[i]["flag"] = bool(kr)
                syls[i]["flag_reason"] = "start or end boundary has no acoustic evidence (placed on the beat grid)" if kr else None
        for sd in syls:
            tum_hece.append((v + 1, ad, sd))
        L_start, L_end = hs[0]["start"], hs[-1]["end"]
        bar_db = vd[v] + SRC_BAR[ad] * BAR_OLC
        ld = {"name": ad, "text": bolum_sozu(v, ad), "start": r4(L_start), "end": r4(L_end), "duration": r4(L_end - L_start),
              "source_bar_in_verse": SRC_BAR[ad], "source_bar_downbeat": r4(bar_db),
              "rms_dbfs": round(rms_db(L_start, L_end), 1), "peak_dbfs": round(tepe_db(L_start, L_end), 1),
              "words": words, "syllables": syls}
        lines.append(ld)
    out_verses.append({"verse": v + 1, "animal": HAYVAN[v], "downbeat": r4(vd[v]), "lines": lines})

# ====================================================================================== bolumler, parcalar, zor kesimler
for v in range(7):
    dz = DZ[v]; ov = out_verses[v]; LN = {l_["name"]: l_ for l_ in ov["lines"]}; k = kita[v]
    a_ = dz["L2"]["zor_kesim"]; b_ = dz["diye"]["zor_kesim"]
    vdb = vd[v]
    seg = collections.OrderedDict()
    seg["L1"] = {"keep": True, "text": bolum_sozu(v, "L1"), "start": r4(dz["L1"]["baslangic"]), "end": r4(dz["L1"]["bitis"]),
                 "strong_onset": r4(dz["L1"]["guclu_baslangic"])}
    seg["L2"] = {"keep": True, "text": bolum_sozu(v, "L2"), "start": r4(dz["L2"]["baslangic"]), "end": r4(dz["L2"]["bitis"])}
    seg["ses"] = {"keep": False, "text": " ".join(q["text"] for q in k["ses"]), "start": r4(dz["ses"]["baslangic"]),
                  "end": r4(dz["ses"]["bitis"]), "body_end": r4(dz["ses"]["govde_bitis"]),
                  "first_vowel_onset": r4(dz["ses"]["hayvan_unlu_baslangic"]),
                  "json_start": k["ses"][0]["start"], "json_end": k["ses"][-1]["end"],
                  "note": "sung animal sound: REMOVE. The words-file end is up to 0.3 s too early: the second sound is held until 'body_end'."}
    seg["diye"] = {"keep": True, "text": bolum_sozu(v, "diye"), "start": r4(dz["diye"]["baslangic"]), "end": r4(dz["diye"]["bitis"]),
                   "strong_onset": r4(dz["diye"]["guclu_baslangic"])}
    seg["L4"] = {"keep": True, "text": bolum_sozu(v, "L4"), "start": r4(dz["L4"]["baslangic"]), "end": r4(dz["L4"]["bitis"]),
                 "body_end": r4(dz["L4"]["govde_bitis"])}
    for ad in seg:
        bd = vdb + SRC_BAR[ad] * BAR_OLC
        seg[ad]["source_bar_downbeat"] = r4(bd)
        seg[ad]["start_offset_from_bar_downbeat_ms"] = round((seg[ad]["start"] - bd) * 1000, 1)
        seg[ad]["duration"] = r4(seg[ad]["end"] - seg[ad]["start"])
    ov["segments"] = seg
    # ---------------------------------------------------------------- zor kesim (a): L2 sonu
    var_s = LN["L2"]["syllables"][-1]
    var_bas, var_bit = var_s["start"], a_["t_close"]
    kind = a_["between_kind"]
    if kind == "pause":
        # gercek duraklama: "var" kendiliginden sonuyor -> sonumleme var bittikten sonra, sessizligin icinde biter
        f_bit = min(var_bit + 0.025, a_["animal_sound_start"] - 0.015)
        onerilen = sonum_degerlendir(var_bit - 0.005, f_bit, var_bas, var_bit)
        oneri_not = ("real pause: 'var' releases by itself. The fade starts 5 ms before var_end and ends inside the pause, %.0f ms before the "
                     "sung animal sound starts; what remains after var_end is the decay of 'var' itself" % ((a_["animal_sound_start"] - f_bit) * 1000))
    else:
        # ses kesilmiyor: sonumleme TAM var_end'de biter -> hayvan sesinden hicbir ornek kalmaz
        onerilen = sonum_degerlendir(var_bit - 0.025, var_bit, var_bas, var_bit)
        oneri_not = ("no pause: the fade ends exactly at var_end, so not one sample of the sung animal sound remains. Cost: 'var' (%.0f ms long) is %.1f ms "
                     "shorter at the -6 dB point and loses %.2f dB of its energy" % ((var_bit - var_bas) * 1000, onerilen["var_shortened_ms_at_minus6db"],
                                                                                   -onerilen["var_energy_loss_db"]))
    tablo = [dict(sonum_degerlendir(var_bit - F / 1000.0, var_bit, var_bas, var_bit), family="ends_at_var_end") for F in (5, 10, 15, 20, 25, 30)]
    tablo += [dict(sonum_degerlendir(var_bit - 0.005, var_bit - 0.005 + F / 1000.0, var_bas, var_bit), family="starts_5ms_before_var_end")
              for F in (10, 15, 20, 25, 30)]
    if kind == "nasal_murmur":
        ac = ("no gap: the voice never stops. 'var' (vowel + r at the same pitch D4) runs straight into the nasal /m/ of the sung "
              "animal sound; at the join the level is only %.1f dB below the sung RMS" % (SUNG - a_["dip_dbfs"]))
    elif kind == "fricative":
        ac = ("no gap: the /h/ of the sung animal sound starts as soon as 'var' ends; lowest level at the join %.1f dB below the sung RMS"
              % (SUNG - a_["dip_dbfs"]))
    else:
        ac = "real pause of %.0f ms (level below sung RMS - 12 dB) between 'var' and the sung animal sound" % a_["silent_gap_ms"]
    hard_a = {
        "var_end": r4(var_bit), "var_end_check_steepest_f2_fall": r4(a_["t_steepest_fall"]),
        "what_follows": kind, "statement": ac,
        "gap_ms": round(a_["silent_gap_ms"], 1),
        "silent_gap": None if a_["silent_gap"] is None else [r4(a_["silent_gap"][0]), r4(a_["silent_gap"][1])],
        "animal_sound_start": r4(a_["animal_sound_start"]),
        "animal_sound_starts_before_var_has_decayed": bool(kind != "pause"),
        "level_at_join_dbfs": round(a_["dip_dbfs"], 1), "level_at_join_db_re_sung": round(a_["dip_dbfs"] - SUNG, 1),
        "lowest_level_var_end_to_animal_vowel_dbfs": round(a_["between_min_dbfs"], 1), "lowest_level_t": r4(a_["between_min_t"]),
        "animal_first_vowel_onset": r4(a_["animal_vowel_onset"]),
        "ms_from_var_end_to_animal_vowel": round(a_["between_ms"], 1),
        "first_50ms_after_var_end": {"mean_dbfs": round(a_["first50ms_mean_dbfs"], 1),
                                     "low_band_minus_f2_band_db": round(a_["first50ms_low_minus_f2_db"], 1),
                                     "low_band_minus_high_band_db": round(a_["first50ms_low_minus_hi_db"], 1),
                                     "voiced_ratio_until_animal_vowel": round(a_["between_voiced_ratio"], 2)},
        "var_end_before_next_bar_line_ms": round((vdb + 2 * BAR_OLC - var_bit) * 1000, 1),
        "recommended": dict(onerilen, shape="raised cosine (cos^2), gain 1 at fade_start, 0 at cut_out", why=oneri_not,
                            margin_cut_out_to_animal_vowel_ms=round((a_["animal_vowel_onset"] - onerilen["cut_out"]) * 1000, 1),
                            margin_cut_out_to_animal_sound_start_ms=round((a_["animal_sound_start"] - onerilen["cut_out"]) * 1000, 1)),
        "fade_table_note": "family 'ends_at_var_end': nothing of the animal sound remains, 'var' is shortened by half the fade length; family "
                           "'starts_5ms_before_var_end': 'var' is untouched, the first (fade_ms - 5) ms after var_end remain, faded (residual_* columns)",
        "fade_table": tablo}
    # ---------------------------------------------------------------- zor kesim (b): diye basi
    c2 = dz["diye"]["giris_cukuru"]
    onset = c2["sonraki_baslangic"]; onceki = c2["onceki_bitis"]
    fin = float(np.clip(round(min(15.0, 0.6 * (onset - onceki) * 1000)), 5, 15))
    cut_in_d = onset - 0.002 - fin / 1000.0
    # sonumlemeli giris bolgesindeki artik (hayvan sesinin kuyrugu + d kapanisi)
    i0, i1 = int(round(cut_in_d * fs)), int(round((onset - 0.002) * fs))
    g = 1 - kosinus_cikis(i1 - i0)
    art = x[i0:i1] * g
    # -15 dB penceresi: duzeyin soylenen - 15 dB altinda kaldigi bitisik bolge (cukur cevresinde)
    gi = fi(c2["g"]); L_ = gi
    while L_ > gi - fi(0.3) and db_ham[L_] < SUNG - 15.0:
        L_ -= 1
    R_ = gi
    while R_ < gi + fi(0.3) and db_ham[R_] < SUNG - 15.0:
        R_ += 1
    hard_b = {
        "animal_sound_body_end": r4(b_["animal_body_end"]), "animal_sound_end": r4(onceki),
        "dip_t": r4(c2["g"]), "dip_dbfs": round(c2["en_dusuk_dbfs"], 1), "dip_db_re_sung": round(c2["en_dusuk_dbfs"] - SUNG, 1),
        "diye_onset": r4(onset), "diye_strong_onset": r4(b_["strong_onset"]),
        "gap_ms": round((onset - onceki) * 1000, 1),
        "gap_definition": "time during which the level stays below dip + 6 dB, between the end of the second sung animal sound and the /d/ of 'diye'",
        "window_below_sung_minus_15db_ms": round((R_ - L_ - 1) * DT * 1000, 1),
        "words_file_gap_ms": round((k["diye"][0]["start"] - k["ses"][-1]["end"]) * 1000, 1),
        "cut_in": r4(cut_in_d), "fade_in_ms": fin, "fade_in_end": r4(onset - 0.002),
        "level_at_cut_in_dbfs": round(float(R5[fi(cut_in_d)]), 1),
        "residual_peak_inside_fade_dbfs": round(float(20 * np.log10(np.abs(art).max() + 1e-12)), 1),
        "residual_rms_inside_fade_dbfs": round(float(10 * np.log10(np.mean(art ** 2) + 1e-20)), 1),
        "pitch_inside_dip_midi": (lambda m: None if m.sum() < 2 else round(float(np.median(midi(f0h[m]))), 2))(
            (th >= onceki) & (th < onset) & (f0h > 0)),
        "diye_strong_onset_after_beat2_ms": round((b_["strong_onset"] - (vdb + 2 * BAR_OLC + 2 * BEAT_OLC)) * 1000, 1)}
    ov["hard_cuts"] = {"L2_end": hard_a, "diye_start": hard_b}
    # ---------------------------------------------------------------- parcalar
    L1e, L2s = dz["L1"]["bitis"], dz["L2"]["baslangic"]
    p1_in = dz["L1"]["kesim_giris"]; p1_fin = float(min(30, round((dz["L1"]["baslangic"] - p1_in) * 1000)))
    p1_out = min(L2s - 0.004, L1e + 0.030); p1_fout = float(min(30, round((p1_out - (L1e - 0.005)) * 1000)))
    p2_in = max(L1e + 0.004, L2s - 0.014); p2_fin = float(max(3, round((L2s - 0.002 - p2_in) * 1000)))
    p2_out = onerilen["cut_out"]; p2_fout = onerilen["fade_ms"]
    e4 = dz["L4"]["bitis"]; p3_out = e4 + 0.03
    p3_fout = float(np.clip(round((p3_out - dz["L4"]["govde_bitis"]) * 1000), 20, 60))
    ek = dz["L4"]["ek_ses"]; nf = dz["L1"]["nefes"]

    def yer(ad, bas_ad=None):
        sb = vdb + SRC_BAR[ad] * BAR_OLC
        hb = LEAD_IN + (4 + 8 * v + HEDEF_BAR[ad]) * BAR
        return {"source_bar_downbeat": r4(sb), "target_bar_in_verse": HEDEF_BAR[ad], "target_bar_index_in_song": 4 + 8 * v + HEDEF_BAR[ad],
                "target_bar_downbeat": r4(hb), "shift_s": round(hb - sb, 5),
                "note": "target time = source time + shift_s (105.000 BPM form, 0.100 s lead-in, verse v at bar 4 + 8 v); no time-stretch"}

    P = []
    P.append({"piece": 1, "segments": ["L1"], "text": bolum_sozu(v, "L1"),
              "cut_in": r4(p1_in), "fade_in_ms": p1_fin, "start": r4(dz["L1"]["baslangic"]), "strong_onset": r4(dz["L1"]["guclu_baslangic"]),
              "end": r4(L1e), "cut_out": r4(p1_out), "fade_out_ms": p1_fout,
              "level_at_cut_in_dbfs": round(float(R5[fi(p1_in)]), 1), "level_at_cut_out_dbfs": round(float(R5[fi(p1_out)]), 1),
              "cut_out_note": "'var,' is followed after %.0f ms by the 'ç' of line 2: the fade-out must end before %.4f" % ((L2s - L1e) * 1000, L2s),
              "breath_before": None if nf is None else {"start": r4(nf["start"]), "end": r4(nf["end"]), "peak_dbfs": round(nf["peak_dbfs"], 1),
                                                        "rms_dbfs": round(nf["rms_dbfs"], 1), "cut_in_with_breath": r4(nf["cut_in_with_breath"]),
                                                        "note": "breath / pre-phonation before the verse; NOT included by the default cut_in"},
              "placement": yer("L1")})
    P.append({"piece": 2, "segments": ["L2"], "text": bolum_sozu(v, "L2"),
              "cut_in": r4(p2_in), "fade_in_ms": p2_fin, "start": r4(L2s), "end": r4(dz["L2"]["bitis"]),
              "cut_out": r4(p2_out), "fade_out_ms": p2_fout, "fade_out_start": onerilen["fade_start"],
              "level_at_fade_out_start_dbfs": round(float(R5[fi(onerilen["fade_start"])]), 1),
              "level_at_cut_in_dbfs": round(float(R5[fi(p2_in)]), 1), "level_at_cut_out_dbfs": round(float(R5[fi(p2_out)]), 1),
              "cut_out_note": "HARD CUT (a): see hard_cuts.L2_end", "placement": yer("L2")})
    p3 = {"piece": 3, "segments": ["diye", "L4"], "text": bolum_sozu(v, "diye") + " " + bolum_sozu(v, "L4"),
          "cut_in": r4(cut_in_d), "fade_in_ms": fin, "start": r4(onset), "strong_onset": r4(b_["strong_onset"]),
          "end": r4(e4), "cut_out": r4(p3_out), "fade_out_ms": p3_fout,
          "level_at_cut_in_dbfs": round(float(R5[fi(cut_in_d)]), 1), "level_at_cut_out_dbfs": round(float(R5[fi(p3_out)]), 1),
          "cut_in_note": "HARD CUT (b): see hard_cuts.diye_start",
          "internal_join_diye_L4": {"t": r4(dz["L4"]["giris_cukuru"]["g"]), "level_dbfs": round(dz["L4"]["giris_cukuru"]["en_dusuk_dbfs"], 1),
                                    "L4_start": r4(dz["L4"]["baslangic"]),
                                    "note": "sung without a break ('bağırır' -> closure of 'ç' -> 'çiftliğinde'): keep as one chunk"},
          "rms_300ms_after_cut_out_dbfs": round(rms_db(p3_out, p3_out + 0.3), 1),
          "after_sound": None if ek is None else {"start": r4(ek["start"]), "end": r4(ek["end"]), "peak_dbfs": round(ek["peak_dbfs"], 1),
                                                  "voiced_ratio": round(ek["voiced_ratio"], 2), "gap_after_word_ms": round(ek["gap_after_word_ms"], 1),
                                                  "cut_out_including_after_sound": r4(ek["decayed_at"] + 0.03),
                                                  "note": "separate puff / breath-out after the last word; EXCLUDED by the default cut_out"},
          "placement": yer("diye")}
    P.append(p3)
    for p in P:
        p["fade_shape"] = "raised cosine"
        p["duration_cut"] = r4(p["cut_out"] - p["cut_in"])
    ov["pieces"] = P
    if verses[v]["atl"] is not None:
        ex = verses[v]["atl"]["excision"]
        P[1]["internal_excision"] = {"start": r4(ex["start"]), "end": r4(ex["end"]), "see": "atlari_check"}

# ====================================================================================== nota tablosu
SLOT = {"L1": ["A", "li", "Ba", "ba", "nın", "bir", "çift", "li", "ği", "var"],
        "L2": ["çift", "li", "ğin", "de", "h1", "h2", "h3", "h4", "var"],
        "diye": ["di", "ye", "ba", "ğı", "rır"],
        "L4": ["çift", "li", "ğin", "de", "A", "li", "Ba", "ba", "nın"]}
SLOT_VURUS = {"L1": SABLON["L1"], "L2": SABLON["L2_on"] + SABLON["L2_hayvan"][4] + SABLON["L2_var"], "diye": SABLON["diye"], "L4": SABLON["L4"]}


def pc_ekle(d, m_, sure):
    d[NOTA[int(round(m_)) % 12]] += sure


hist_duragan = {ad: collections.Counter() for ad in SAKLANAN}; hist_tum = {ad: collections.Counter() for ad in SAKLANAN}
hist_vurus = {ad: [collections.Counter() for _ in range(4)] for ad in SAKLANAN}
slot_nota = {ad: collections.defaultdict(list) for ad in SAKLANAN}
slot_perde = {ad: collections.defaultdict(list) for ad in SAKLANAN}
for v in range(7):
    ov = out_verses[v]
    for ln in ov["lines"]:
        ad = ln["name"]; bd = ln["source_bar_downbeat"]
        notes = []
        vur = SLOT_VURUS[ad]
        for sd in ln["syllables"]:
            if not sd["kept"]:
                continue
            for n_ in sd["notes"]:
                nd = {"syllable": sd["text"], "word": sd["word"], "note": n_["note"], "midi": n_["midi"], "start": n_["start"], "end": n_["end"],
                      "duration_ms": n_["duration_ms"], "duration_beats": round((n_["end"] - n_["start"]) / BEAT_OLC, 3),
                      "onset_beat_in_bar": round((n_["start"] - bd) / BEAT_OLC, 3), "no_plateau": n_["no_plateau"]}
                notes.append(nd)
            # sablon yuvasi (vurusa gore)
            si = int(np.argmin([abs(sd["beat_expected"] - b_) for b_ in vur]))
            slot_nota[ad][si].append((v + 1, sd["text"], [n_["note"] for n_ in sd["notes"]], [n_["midi"] for n_ in sd["notes"]],
                                      [(n_["end"] - n_["start"]) / BEAT_OLC for n_ in sd["notes"]]))
            if sd["f0_midi"] is not None:
                slot_perde[ad][si].append((v + 1, sd["text"], sd["f0_midi"], sd["pitch_start_midi"], sd["pitch_mid_midi"], sd["pitch_end_midi"]))
            # dagilimlar (5 ms kareler)
            idx, g = perde.kareler(sd["start"], sd["end"])
            mm = midi(np.where(f0h[idx] > 0, f0h[idx], 1.0))
            dur = np.zeros(len(idx), bool)
            for a0, b0, _, _ in perde.platolar(sd["start"], sd["end"]):
                dur |= (th[idx] >= a0 - 1e-9) & (th[idx] < b0 - 1e-9)
            for k_ in range(len(idx)):
                if not g[k_]:
                    continue
                pc_ekle(hist_tum[ad], mm[k_], FP)
                if dur[k_]:
                    pc_ekle(hist_duragan[ad], mm[k_], FP)
                    bi = int(np.floor((th[idx[k_]] - bd) / BEAT_OLC))
                    if 0 <= bi < 4:
                        pc_ekle(hist_vurus[ad][bi], mm[k_], FP)
        ln["notes"] = notes
        ln["note_sequence"] = " ".join("%s(%.2f)" % (n_["note"], n_["duration_beats"]) for n_ in notes)


def hist_cikti(c):
    top = sum(c.values())
    return {"seconds": {k_: round(c[k_], 3) for k_ in NOTA if c[k_] > 0},
            "share": {k_: round(c[k_] / top, 4) for k_ in NOTA if c[k_] > 0}, "total_seconds": round(top, 3)}


def uzlasi(ad):
    out = []
    for si, etiket in enumerate(SLOT[ad]):
        gir = slot_nota[ad].get(si, [])
        if not gir:
            continue
        diz = collections.Counter(tuple(g_[2]) for g_ in gir)
        en, say = diz.most_common(1)[0]
        ayni = [g_ for g_ in gir if tuple(g_[2]) == en]
        mid = np.median(np.array([g_[3] for g_ in ayni]), axis=0); sur = np.median(np.array([g_[4] for g_ in ayni]), axis=0)
        pp_ = np.array([g_[2:] for g_ in slot_perde[ad].get(si, [])], dtype=float)
        ps_ = [round(float(q_), 2) for q_ in np.median(pp_, axis=0)] if len(pp_) else [None] * 4
        out.append({"slot": etiket, "beat_in_bar": SLOT_VURUS[ad][si] - 4 * SRC_BAR[ad], "notes": list(en),
                    "median_f0_midi": ps_[0], "median_pitch_start_mid_end_midi": ps_[1:],
                    "glide": None if ps_[1] is None or abs(ps_[3] - ps_[1]) < 0.7 else "%s -> %s" % (nota_adi(ps_[1]), nota_adi(ps_[3])),
                    "median_midi": [round(float(m_), 2) for m_ in mid], "median_duration_beats": [round(float(s_), 3) for s_ in sur],
                    "verses_agreeing": "%d/%d" % (say, len(gir)),
                    "other_readings": [{"verse": g_[0], "syllable": g_[1], "notes": g_[2]} for g_ in gir if tuple(g_[2]) != en]})
    return out


toplam_d = collections.Counter(); toplam_t = collections.Counter()
for ad in SAKLANAN:
    toplam_d.update(hist_duragan[ad]); toplam_t.update(hist_tum[ad])
# akort: plato karelerinin en yakin yarim sese gore ortanca sapmasi
sap = []
for (v, ad, sd) in tum_hece:
    if sd["kept"]:
        for a0, b0, m0, n0 in perde.platolar(sd["start"], sd["end"]):
            sap += [(m0 - round(m0)) * 100] * n0
sapan = []
for ad in SAKLANAN:
    for si, L_ in slot_perde[ad].items():
        med_ = float(np.median([g_[2] for g_ in L_]))
        for g_ in L_:
            if abs(g_[2] - med_) >= 0.5:
                sapan.append({"verse": g_[0], "line": ad, "syllable": g_[1], "f0_midi": g_[2], "note": nota_adi(g_[2]),
                              "slot_median_midi": round(med_, 2), "deviation_semitones": round(g_[2] - med_, 2)})
notes_table = {
    "about": "Sung notes measured on the separated vocal (kept syllables only; the sung animal sounds and the excised extra nucleus of verse 3 are not included). "
             "Durations in beats of the measured grid (%.7f s). A note lasts from its start to the start of the next note / end of the syllable (consonants included)." % BEAT_OLC,
    "tuning_cents_re_A440_median_of_plateau_frames": round(float(np.median(sap)), 1),
    "consensus_per_line": {ad: uzlasi(ad) for ad in SAKLANAN},
    "consensus_text": {},
    "pitch_outliers": sapan,
    "pitch_outliers_note": "kept syllables whose core pitch differs by 0.5 semitone or more from the median of the same template slot over the 7 verses",
    "per_verse": [{"verse": v + 1, **{ln["name"]: ln["note_sequence"] for ln in out_verses[v]["lines"]}} for v in range(7)],
    "pitch_class_histogram_stable_notes": dict({ad: hist_cikti(hist_duragan[ad]) for ad in SAKLANAN}, overall=hist_cikti(toplam_d)),
    "pitch_class_histogram_all_voiced_frames": dict({ad: hist_cikti(hist_tum[ad]) for ad in SAKLANAN}, overall=hist_cikti(toplam_t)),
    "pitch_class_seconds_per_beat_of_the_bar": {ad: [{"beat": b_, **{k_: round(c[k_], 3) for k_ in NOTA if c[k_] > 0.02}}
                                                      for b_, c in enumerate(hist_vurus[ad])] for ad in SAKLANAN},
    "histogram_note": "duration-weighted: 5 ms frames, gated (voiced, 100-1000 Hz envelope above sung RMS - 11 dB), summed over the 7 verses. "
                      "'stable_notes' counts only frames inside note plateaus (glides between notes excluded); "
                      "'per_beat' is for the bar of each line (diye: beats 2-3 of its bar), stable frames only.",
}
for ad in SAKLANAN:
    notes_table["consensus_text"][ad] = " | ".join(
        "%s: %s%s" % (u_["slot"], "-".join("%s(%.2f)" % (n_, d_) for n_, d_ in zip(u_["notes"], u_["median_duration_beats"])),
                      "" if not u_["glide"] else " [glide %s]" % u_["glide"])
        for u_ in notes_table["consensus_per_line"][ad])

# ====================================================================================== atları denetimi + tarama
ATL = verses[2]["atl"]
orn = atlari.ornek_topla(TUM, haric=(2, "L2", 1))
zk = atlari.ZarfKarsilastir(orn)
ev = ATL["extra_vowel"]; dl = ATL["dark_l"]; a2 = ATL["second_a"]
w3 = [h for h in verses[2]["H"]["L2"] if h["word_i"] == 1]
ilk_a = (w3[0]["cs2"], w3[0]["ce2"]) if "cs2" in w3[0] else (w3[0]["cs"], w3[0]["ce"])
bolgeler = collections.OrderedDict([
    ("first_a", (ATL["as_sung"][0]["nuc"] - 0.04, ATL["a_end"] - 0.02)),
    ("extra_vowel", (ev["start"] + 0.005, ev["end"] - 0.005)),
    ("dark_l", (dl["start"] + 0.01, dl["end"] - 0.01)),
    ("second_a", (a2["onset"] + 0.01, a2["onset"] + 0.07)),
    ("final_i", (w3[3]["cs2"] + 0.005, w3[3]["ce2"] - 0.005)),
])
spek = {}
for ad_, (a0, b0) in bolgeler.items():
    uz, en = zk.uzaklik(a0, b0)
    env, _m = atlari.zarf_ornek(a0, b0)
    spek[ad_] = {"interval": [r4(a0), r4(b0)], "level_dbfs": round(rms_db(a0, b0), 1),
                 "f0_midi": (lambda m_: None if m_ is None else round(m_, 2))(perde.ortanca(a0, b0)),
                 "band_levels_db_re_200_3400": atlari.bant_profili(a0, b0), "harmonics": atlari.harmonikler(a0, b0),
                 "envelope_db_at_fixed_hz": None if env is None else [round(float(q_), 1) for q_ in env],
                 "envelope_distance_to_pitch_matched_classes": uz, "nearest_class": en,
                 "lpc_formants_hz_rough": atlari.lpc_bicim(a0, b0)}
# "-ları" eklerindeki 'a' (2. ve 4. kita) ile 3. kitadaki 'la'nin a'si ayni mi
la_kars = []
e3, _ = atlari.zarf_ornek(*bolgeler["second_a"])
for v_ in (1, 3):
    lah = [h for h in verses[v_]["H"]["L2"] if h["text"] == "la"][0]
    a0_, b0_ = lah["cs2"] + 0.02, lah["ce2"] - 0.01
    ee, mm_ = atlari.zarf_ornek(a0_, b0_)
    uz_, en_ = zk.uzaklik(a0_, b0_)
    la_kars.append({"verse": v_ + 1, "word": kita[v_]["L2"][1]["soz"], "interval": [r4(a0_), r4(b0_)], "f0_midi": round(mm_, 2),
                    "envelope_db_at_fixed_hz": [round(float(q_), 1) for q_ in ee],
                    "rms_distance_db_to_verse3_la": round(float(np.sqrt(np.mean((ee - e3) ** 2))), 1), "nearest_class": en_})
# referans sinif zarflari (E4-F4 cevresi: 64.5 +- 1.5 yarim ses)
ref = {"envelope_hz": atlari.ZARF_HZ, "classes_near_E4_F4": zk.sinif_zarfi(64.5),
       "reference_intervals_total": {k_: len(v_) for k_, v_ in zk.orn.items()}}
# kontrol: ayni olcut, bilinen seslere uygulaninca dogru sinifi buluyor mu (birini disarida birak)
kontrol = {}
for ad_, L_ in zk.orn.items():
    dogru = say = 0
    for i_, (m_, e_) in enumerate(L_):
        en_iyi = None
        for ad2, L2_ in zk.orn.items():
            yakin = [q_ for j_, (mm_, q_) in enumerate(L2_) if abs(mm_ - m_) <= 1.5 and not (ad2 == ad_ and j_ == i_)]
            if len(yakin) >= 2:
                dd = float(np.sqrt(np.mean((e_ - np.mean(yakin, axis=0)) ** 2)))
                if en_iyi is None or dd < en_iyi[0]:
                    en_iyi = (dd, ad2)
        if en_iyi is not None:
            say += 1; dogru += int(en_iyi[1] == ad_)
    kontrol[ad_] = {"n": say, "correct": dogru}
ref["leave_one_out_check_of_the_measure"] = kontrol
# unsuz + l + unlu baglamlarinda akici unsuz suresi (karsilastirma)
kars = []
for v in range(7):
    hs = verses[v]["H"]["L2"]
    for i in range(len(hs) - 1):
        L_, R_ = hs[i], hs[i + 1]
        if R_["onset"] == "l" and L_["coda"] and L_["coda"][-1] in "tkpz" and not L_.get("excise") and not R_.get("excise") and v != 2:
            u_ = atlari.unsuz_l_suresi(L_, R_)
            kars.append({"verse": v + 1, "context": L_["text"] + "|" + R_["text"], "voiced_before_vowel_ms": round(u_["sonorant_ms"], 1)})
for v in range(7):
    for ad in ("L1", "L4"):
        hs = verses[v]["H"][ad]
        for i in range(len(hs) - 1):
            L_, R_ = hs[i], hs[i + 1]
            if R_["onset"] == "l" and L_["coda"] and L_["coda"][-1] == "t":
                u_ = atlari.unsuz_l_suresi(L_, R_)
                kars.append({"verse": v + 1, "context": ad + " " + L_["text"] + "|" + R_["text"], "voiced_before_vowel_ms": round(u_["sonorant_ms"], 1)})
kars_ms = [k_["voiced_before_vowel_ms"] for k_ in kars]
# kor sayim ve yuva sayimi (hayvan kelimeleri)
yuva = []
for v in range(7):
    hs = [h for h in verses[v]["H"]["L2"] if h["word_i"] == 1]
    q = kita[v]["L2"][1]
    ws, we = hs[0]["start"], hs[-1]["end"]
    tep, _ = hece.kor_cekirdek(ws, we)
    # 4 yuvanin her birinde yeni hece baslangici var mi: yuvanin +-70 ms cevresinde bir hece siniri (cukur / kapanis)
    bas = [h["start"] for h in hs]
    dolu = []
    for b_ in SABLON["L2_hayvan"][4]:
        te = vd[v] + b_ * BEAT_OLC
        yakin = [s_ for s_ in bas if -0.20 <= s_ - te <= 0.07]
        dolu.append(bool(yakin))
    yuva.append({"verse": v + 1, "word": q["soz"], "expected_syllables": len(hecele(q["soz"])),
                 "syllable_onsets_found_at_slots_6_6.5_7_7.25": dolu, "onsets_found": int(sum(dolu)),
                 "blind_envelope_peaks": len(tep),
                 "note_plateaus": int(sum(len(perde.platolar(h["start"], h["end"])) for h in hs)),
                 "matches_expected": int(sum(dolu)) == len(hecele(q["soz"]))})
exc = ATL["excision"]
at_h, ti_h, la_h, ri_h = w3
var3 = [h for h in verses[2]["H"]["L2"] if h["word_i"] == 2][0]
bos = exc["end"] - exc["start"]
min_exc = (ATL["voicing_onset"], ev["end"])
atlari_check = {
    "verdict": "FOUR syllable nuclei were sung (a - tı - la - rı), not three (at - la - rı): the user's impression 'atıları' is confirmed.",
    "verdict_detail": ("After the /t/ release the voice re-enters %.0f ms before the 'a' of 'la'. That stretch is its own note (E4 on beat 6.5, "
                       "like the second syllable of the four-syllable animal words): a short bright vowel-like part (%.0f ms, %.1f dBFS RMS; the two 'a' vowels of the word: %.1f and %.1f dBFS) "
                       "followed by a sustained dark /l/ (%.0f ms). In the other consonant + l + vowel words the voiced part before "
                       "the vowel lasts %.0f-%.0f ms (median %.0f ms, n = %d)." % (
                           ATL["voiced_stretch_before_second_a_ms"], ev["duration_ms"], spek["extra_vowel"]["level_dbfs"], spek["first_a"]["level_dbfs"],
                           spek["second_a"]["level_dbfs"], dl["duration_ms"],
                           min(kars_ms), max(kars_ms), float(np.median(kars_ms)), len(kars_ms))),
    "nuclei": [
        {"n": 1, "label": "a", "start": r4(ATL["as_sung"][0]["start"]), "vowel_end": r4(ATL["a_end"]), "note": spek["first_a"]["f0_midi"], "beat_slot": 6.0},
        {"n": 2, "label": "ı (extra) + sustained l", "start": r4(ev["start"]), "vowel_end": r4(ev["end"]), "l_end": r4(dl["end"]),
         "vowel_ms": round(ev["duration_ms"], 1), "l_ms": round(dl["duration_ms"], 1), "note": spek["extra_vowel"]["f0_midi"], "beat_slot": 6.5,
         "onset_after_slot_ms": round((ev["start"] - (vd[2] + 6.5 * BEAT_OLC)) * 1000, 1)},
        {"n": 3, "label": "a (of 'la')", "start": r4(a2["onset"]), "end": r4(la_h["end"]), "note": spek["second_a"]["f0_midi"], "beat_slot": 7.0,
         "onset_after_slot_ms": round((a2["onset"] - (vd[2] + 7.0 * BEAT_OLC)) * 1000, 1)},
        {"n": 4, "label": "ı (of 'rı')", "start": r4(ri_h["start"]), "end": r4(ri_h["end"]), "note": spek["final_i"]["f0_midi"], "beat_slot": 7.25},
    ],
    "landmarks": {"first_a_end_t_closure_start": r4(ATL["a_end"]), "t_burst_onset": r4(ATL["t_burst_onset"]),
                  "t_frication_end": r4(ATL["t_frication_end"]), "t_closure_ms": round(ATL["t_closure_ms"], 1),
                  "t_frication_ms": round(ATL["t_frication_ms"], 1), "voicing_onset_after_t": r4(ATL["voicing_onset"]),
                  "quiet_instant_between_release_and_voicing": r4(ATL["quiet_instant"]), "quiet_level_dbfs": round(ATL["quiet_level_dbfs"], 1),
                  "extra_vowel_end_l_onset": r4(ev["end"]), "second_a_onset": r4(a2["onset"]),
                  "voiced_stretch_before_second_a_ms": round(ATL["voiced_stretch_before_second_a_ms"], 1)},
    "duration_comparison_consonant_l_vowel": {"other_words": kars, "min_ms": min(kars_ms), "median_ms": round(float(np.median(kars_ms)), 1),
                                               "max_ms": max(kars_ms), "atlari_ms": round(ATL["voiced_stretch_before_second_a_ms"], 1)},
    "spectral_evidence": {"segments": spek, "reference_classes_same_singer": ref, "la_vowel_in_the_other_lari_words": la_kars,
                          "measure": "spectral envelope sampled at 350 ... 2800 Hz (interpolated between the harmonic peaks, dB re strongest, floor -35 dB); "
                                     "RMS distance in dB to the mean envelope of each class, using only reference sounds of the same singer within +-1.5 semitones "
                                     "(verse 3 'atları' excluded from the references)",
                          "note": "f0 is 330-350 Hz, so the envelope is only visible at the harmonics and LPC formants lock onto them: the harmonic levels are the main evidence"},
    "nucleus_count_all_animal_words": yuva,
    "excision": {
        "start": r4(exc["start"]), "end": r4(exc["end"]), "removed_ms": round(bos * 1000, 1),
        "start_definition": "quietest instant between the end of the /t/ frication and the onset of voicing (5 ms RMS %.1f dBFS)" % ATL["quiet_level_dbfs"],
        "end_definition": "%.0f ms before the onset of the 'a' of 'la' (F2-band rise): keeps a normal-length /l/ in front of 'a'" % exc["kept_l_ms"],
        "level_at_end_dbfs": round(float(R5[fi(exc["end"])]), 1), "voiced_at_end": bool(hece.VOIG[fi(exc["end"])]),
        "recommended_fades": {"fade_out_before_start_ms": 5, "fade_in_after_end_ms": 10,
                              "note": "the splice-in point lies inside the sustained /l/ (voiced, about %.0f dBFS): a 10 ms fade-in is needed" % float(R5[fi(exc["end"])])},
        "what_remains": {"at": [r4(at_h["start"]), r4(exc["start"])], "at_ms": round((exc["start"] - at_h["start"]) * 1000, 1),
                         "lari": [r4(exc["end"]), r4(ri_h["end"])], "lari_ms": round((ri_h["end"] - exc["end"]) * 1000, 1),
                         "resulting_word_duration_ms_if_gap_closed": round((ri_h["end"] - at_h["start"] - bos) * 1000, 1),
                         "word_span_ms_if_left_in_place": round((ri_h["end"] - at_h["start"]) * 1000, 1)},
        "minimal_alternative": {"start": r4(min_exc[0]), "end": r4(min_exc[1]), "removed_ms": round((min_exc[1] - min_exc[0]) * 1000, 1),
                                "note": "removes only the bright vowel-like part and keeps the whole sustained /l/ (%.0f ms on E4): NOT recommended, "
                                        "a sustained l on its own note still reads as a syllable ('atılları')" % dl["duration_ms"]}},
    "rhythm_options": [
        {"option": "A (recommended)", "what": "leave a gap: every remaining sample stays at its original time",
         "consequence_ms": {"shift_of_a": 0, "shift_of_lari": 0, "shift_of_var": 0, "silent_gap_inside_word": round(bos * 1000, 1)},
         "result": "'at' on beat 6 (vowel %.0f ms + /t/ closure and release), rest on beat 6.5, 'la' on beat 7, 'rı' on beat 7.25, 'var' on beat 7.5 as sung" % (
             (ATL["a_end"] - ATL["as_sung"][0]["nuc"] + 0.02) * 1000)},
        {"option": "B", "what": "close the gap by moving 'ları var' earlier",
         "consequence_ms": {"shift_of_a": 0, "shift_of_lari": -round(bos * 1000, 1), "shift_of_var": -round(bos * 1000, 1), "silent_gap_inside_word": 0},
         "result": "'var' would land %.2f beats before its beat (off the grid) and line 2 would end %.0f ms early: not recommended" % (bos / BEAT_OLC, bos * 1000)},
        {"option": "C", "what": "close the gap by moving 'at' later",
         "consequence_ms": {"shift_of_a": round(bos * 1000, 1), "shift_of_lari": 0, "shift_of_var": 0, "silent_gap_inside_word": 0},
         "result": "the vowel of 'at' would start %.2f beats after beat 6 (off the grid): not recommended" % (bos / BEAT_OLC)},
    ],
    "not_verified_by_ear": "The verdict rests on measurements (timing, level, spectrum, pitch). Whether the repaired word sounds natural was not checked by listening.",
}

# ---------------- butun kelimelerin taramasi (fazla / eksik hece)
tarama = []
for (vv, ad, wd) in tum_kelime:
    hs = [h for h in verses[vv - 1]["H"][ad] if h["word"] == wd["text"] and h["q"]["json_bas"] == wd["json_start"]]
    sy = [sd for (v2, a2_, sd) in tum_hece if v2 == vv and a2_ == ad and sd["word"] == wd["text"] and wd["start"] - 1e-3 <= sd["start"] <= wd["end"] + 1e-3]
    kept = [s_ for s_ in sy if s_["kept"]]
    eksik = [s_["text"] for s_ in kept if s_["voiced_ratio"] < 0.3 or (s_["core_end"] - s_["core_start"]) < 0.03]
    grid_sap = [round((s_["core_start"] - s_["t_expected"]) * 1000) for s_ in kept]
    tarama.append({"verse": vv, "line": ad, "word": wd["text"], "expected": wd["syllables_expected"], "nuclei_on_grid_slots": wd["syllable_nuclei_sung"],
                   "blind_envelope_peaks": wd["blind_check"]["nuclei_detected"],
                   "syllables_with_weak_or_missing_nucleus": eksik,
                   "extra_syllable": wd["syllable_nuclei_sung"] > wd["syllables_expected"],
                   "missing_syllable": bool(eksik) or wd["syllable_nuclei_sung"] < wd["syllables_expected"]})
# tekrarlanan kelimelerde hece suresi tutarliligi
tutar = {}
for ad in SAKLANAN:
    for si, etiket in enumerate(SLOT[ad]):
        if etiket in ("h1", "h2", "h3", "h4"):
            continue
        sur = []
        for v in range(7):
            ss = [sd for sd in [l_ for l_ in out_verses[v]["lines"] if l_["name"] == ad][0]["syllables"] if sd["kept"]]
            idx_ = si if ad != "L2" or si < 4 else None
            if ad == "L2" and si == 8:
                sd = ss[-1]
            else:
                sd = ss[idx_]
            sur.append(sd["duration"] * 1000)
        med = float(np.median(sur))
        tutar["%s %d %s" % (ad, si, etiket)] = {"median_ms": round(med), "min_ms": round(min(sur)), "max_ms": round(max(sur)),
                                                "max_abs_dev_ms": round(max(abs(s_ - med) for s_ in sur))}
syllable_scan = {
    "method": "For every kept word: (1) each expected syllable has a voiced nucleus at its beat-grid slot (voiced ratio >= 0.3, core >= 30 ms); "
              "(2) no additional nucleus between the slots (verse 3 'atları' is the only word where one was found); "
              "(3) blind envelope peak count (no grid) as an independent cross-check; (4) syllable durations of the repeated words across the 7 verses.",
    "words_with_extra_syllable": [{"verse": t_["verse"], "line": t_["line"], "word": t_["word"]} for t_ in tarama if t_["extra_syllable"]],
    "words_with_missing_syllable": [{"verse": t_["verse"], "line": t_["line"], "word": t_["word"], "syllables": t_["syllables_with_weak_or_missing_nucleus"]}
                                    for t_ in tarama if t_["missing_syllable"]],
    "blind_count_mismatches": [{"verse": t_["verse"], "line": t_["line"], "word": t_["word"], "expected": t_["expected"], "blind": t_["blind_envelope_peaks"]}
                               for t_ in tarama if t_["blind_envelope_peaks"] != t_["expected"]],
    "blind_count_note": "A blind mismatch alone is not an error: 'li-ği' / 'li-ğin' are one continuous vowel (no dip), and a soft /l/, /n/ or /y/ between vowels "
                        "often makes no 3 dB dip. These words were NOT split proportionally; the nuclei were anchored on the beat grid and the boundaries found acoustically.",
    "repeated_word_syllable_duration_ms": tutar,
    "per_word": tarama,
}

# ====================================================================================== gurultu tabani
bosluklar = []
onceki_son = 0.3
for v in range(7):
    dz = DZ[v]
    bas = dz["L1"]["baslangic"] - 0.65
    if bas - onceki_son > 0.3:
        bosluklar.append({"before_verse": v + 1, "start": r4(onceki_son), "end": r4(bas), "rms_dbfs": round(rms_db(onceki_son, bas), 1),
                          "peak_dbfs": round(tepe_db(onceki_son, bas), 1)})
    ek = dz["L4"]["ek_ses"]
    onceki_son = (ek["decayed_at"] if ek else dz["L4"]["bitis"]) + 0.25
bosluklar.append({"before_verse": None, "start": r4(onceki_son), "end": 104.5, "rms_dbfs": round(rms_db(onceki_son, 104.5), 1),
                  "peak_dbfs": round(tepe_db(onceki_son, 104.5), 1)})
gap_pow = np.concatenate([x[int(b_["start"] * fs):int(b_["end"] * fs)] ** 2 for b_ in bosluklar])
gap_db = float(10 * np.log10(np.mean(gap_pow) + 1e-20))
# verse arasi bosluklarin ilk 1 s'si (L4'ten hemen sonra: eski bandin sizintisi burada en yuksek)
ilk1 = [{"after_verse": v + 1, "rms_dbfs_first_1s_after_cut_out": round(rms_db(out_verses[v]["pieces"][2]["cut_out"], out_verses[v]["pieces"][2]["cut_out"] + 1.0), 1)}
        for v in range(7)]
kapanis = [sd["end_boundary"]["level_at_t_dbfs"] for (_, _, sd) in tum_hece
           if sd["end_boundary"] and sd["end_boundary"]["kind"] == "dip" and sd["end_boundary"]["consonants"].strip("|")[-1:] in set("bdkptç")
           and sd["end_boundary"]["where"] in ("deepest", "closure_after_sonorant", "last_low")]
kesim_duzey = []
for v in range(7):
    P = out_verses[v]["pieces"]
    kesim_duzey.append({"verse": v + 1, "L1_cut_in": P[0]["level_at_cut_in_dbfs"], "L1_cut_out": P[0]["level_at_cut_out_dbfs"],
                        "L2_cut_in": P[1]["level_at_cut_in_dbfs"], "L2_join_var_to_animal": out_verses[v]["hard_cuts"]["L2_end"]["level_at_join_dbfs"],
                        "diye_cut_in": P[2]["level_at_cut_in_dbfs"], "L4_cut_out": P[2]["level_at_cut_out_dbfs"]})
noise_floor = {
    "sung_rms_dbfs": round(SUNG, 1),
    "between_verses_rms_dbfs": round(gap_db, 1), "between_verses_db_re_sung": round(gap_db - SUNG, 1),
    "between_verses_definition": "instrumental stretches of the stem: from 0.25 s after the end of line 4 (after-sound included) to 0.65 s before the next verse "
                                 "(the breath before the verse is left out); this is what the separator left of the old band",
    "gaps": bosluklar, "first_second_after_each_L4_cut_out": ilk1,
    "levels_at_cut_points_dbfs_5ms_rms": kesim_duzey,
    "inside_phrases_stop_closures_dbfs": {"n": len(kapanis), "median": round(float(np.median(kapanis)), 1),
                                           "quartiles": [round(float(np.percentile(kapanis, 25)), 1), round(float(np.percentile(kapanis, 75)), 1)],
                                           "max": round(float(np.max(kapanis)), 1)},
    "note": "The stem is NOT digitally silent between segments. Inside the phrases the stop closures sit around the stated median; the cut points of the kept "
            "pieces are listed per verse. Only the join 'var' -> sung animal sound has no low point at all in verses with /m/ or /h/ (see hard_cuts.L2_end).",
}

# ====================================================================================== izgara denetimi
izg = {}
for ad in SAKLANAN:
    for si, etiket in enumerate(SLOT[ad]):
        d_ = []
        for (v, a2_, h) in TUM:
            if a2_ != ad or h.get("excise"):
                continue
            if abs(h["beat"] - SLOT_VURUS[ad][si]) < 1e-6:
                d_.append((h["start"] - h["t_exp"]) * 1000)
        if d_:
            izg["%s %s@%.2f" % (ad, etiket, SLOT_VURUS[ad][si])] = {"n": len(d_), "median_ms": round(float(np.median(d_))), "min_ms": round(min(d_)), "max_ms": round(max(d_))}
grid_check = {
    "about": "syllable start (boundary found on the audio) minus the expected vowel onset on the beat grid, per template slot, over the 7 verses. "
             "Negative = the syllable (its consonant) starts before the beat, as it should; a constant, narrow range confirms the template.",
    "beat_period_s": BEAT_OLC, "verse_downbeats": [r4(q) for q in vd], "per_slot": izg,
}

# ====================================================================================== ozet
sinir_turleri = collections.Counter(sd["end_boundary"]["kind"] + "/" + str(sd["end_boundary"].get("where")) for (_, _, sd) in tum_hece
                                    if sd["end_boundary"] is not None)
flag_kelime = [(vv, ad, wd["text"], wd["flag_reason"]) for (vv, ad, wd) in tum_kelime if wd["flag"]]
kept_hece = [sd for (_, _, sd) in tum_hece if sd["kept"]]
summary = {
    "verses": 7, "kept_segments": 28, "kept_pieces": 21, "kept_words": len(tum_kelime), "kept_syllables": len(kept_hece),
    "excised_syllable_nuclei": int(sum(1 for (_, _, sd) in tum_hece if sd["excise"])),
    "flagged_words": len(flag_kelime),
    "flagged_words_by_reason": dict(collections.Counter(
        "lyric deviation (extra syllable)" if "lyric deviation" in f_[3] else
        ("boundary on the beat grid: li|ğin (one vowel, one pitch)" if "li|ğin" in f_[3] else "boundary on the beat grid: " + f_[3].split(" at ")[1].split(" (")[0])
        for f_ in flag_kelime)),
    "flagged_word_list": ["K%d %s %s" % (f_[0], f_[1], f_[2]) for f_ in flag_kelime],
    "blind_count_mismatch_words": int(sum(1 for (_, _, wd) in tum_kelime if not wd["blind_check"]["count_matches"])),
    "boundary_kinds": dict(sinir_turleri),
    "hard_cut_a_L2_end": [{"verse": v + 1, "what_follows": out_verses[v]["hard_cuts"]["L2_end"]["what_follows"],
                           "gap_ms": out_verses[v]["hard_cuts"]["L2_end"]["gap_ms"],
                           "level_at_join_db_re_sung": out_verses[v]["hard_cuts"]["L2_end"]["level_at_join_db_re_sung"],
                           "ms_to_animal_vowel": out_verses[v]["hard_cuts"]["L2_end"]["ms_from_var_end_to_animal_vowel"],
                           "cut_out": out_verses[v]["pieces"][1]["cut_out"], "fade_out_ms": out_verses[v]["pieces"][1]["fade_out_ms"]} for v in range(7)],
    "hard_cut_b_diye_start": [{"verse": v + 1, "gap_ms": out_verses[v]["hard_cuts"]["diye_start"]["gap_ms"],
                               "dip_dbfs": out_verses[v]["hard_cuts"]["diye_start"]["dip_dbfs"],
                               "cut_in": out_verses[v]["hard_cuts"]["diye_start"]["cut_in"],
                               "fade_in_ms": out_verses[v]["hard_cuts"]["diye_start"]["fade_in_ms"]} for v in range(7)],
    "atlari": {"verdict": "four nuclei (a-tı-la-rı)", "excision": [atlari_check["excision"]["start"], atlari_check["excision"]["end"]],
               "removed_ms": atlari_check["excision"]["removed_ms"]},
    "note_sequence_consensus": notes_table["consensus_text"],
    "pitch_classes_overall_share": notes_table["pitch_class_histogram_stable_notes"]["overall"]["share"],
}

out = collections.OrderedDict([
    ("description", "Segmentation of the separated vocal of v2_2 (first AI take): 7 verses x 5 segments, cut points and fades for the 3 kept pieces per verse, "
                    "syllables with pitch, the 'atları' check, the table of sung notes, noise floor."),
    ("source", {"vocal": os.path.relpath(VOKAL, A), "sample_rate": int(fs), "duration_s": round(len(x) / fs, 4),
                "words": "v2_2_words.json", "tempo": "yeni4/analiz/tempo/tempo.json + lattice.json",
                "timeline": "all times are seconds on the timeline of the separated vocal = timeline of v2_2.mp3 decoded by ffmpeg (measured lag 0 samples)"}),
    ("levels", {"sung_rms_dbfs": round(SUNG, 2), "definition": "RMS over the word intervals of the kept words (words file)"}),
    ("definitions", collections.OrderedDict([
        ("segments", "L1, L2, ses (the two sung animal-sound words: REMOVE), diye ('diye bağırır'), L4. start / end from the vocal's own 10 ms RMS envelope."),
        ("pieces", "the three chunks to keep per verse: 1 = L1, 2 = L2, 3 = diye + L4 (one continuous chunk). cut_in = instant where the fade-in starts (gain 0); "
                   "the fade-in lasts fade_in_ms. cut_out = instant where the fade-out has reached 0; it starts fade_out_ms earlier. Raised-cosine fades."),
        ("placement", "piece.placement.shift_s moves the piece from the source timeline to the new song form (no time-stretch; the source grid is 105.003 BPM, "
                      "the new form 105.000 BPM: the difference is 0.06 ms per bar)."),
        ("syllable.start/end", "boundaries from the audio; kind / where of each boundary in end_boundary (see method.boundary_kinds)."),
        ("syllable.kept / excise", "excise = true only for the extra nucleus of verse 3 'atları' (to be cut out); every other syllable is kept."),
        ("syllable.f0_*", "median over the syllable core (voiced frames within 6 dB of the 300-3400 Hz envelope peak); pyworld harvest, 5 ms."),
        ("syllable.pitch_start/mid/end", "medians over the first quarter / middle half / last quarter of the core frames; is_glide if |end - start| >= 0.7 semitone."),
        ("syllable.notes", "stable note plateaus inside the syllable (>= 40 ms within one semitone, slope <= 0.35 st per 20 ms); they partition the syllable in time."),
        ("syllable.voiced_ratio", "share of the 5 ms frames of the syllable that are voiced (harvest) with the 100-1000 Hz envelope above sung RMS - 11 dB "
                                  "(the gate keeps the tracker's false pitches in fricatives and bursts out)."),
        ("word.flag", "true if (a) a boundary inside the word has no acoustic evidence and was placed on the beat grid, or (b) the sung syllables deviate from the lyric."),
        ("word.blind_check", "independent count of envelope peaks without the grid; a mismatch is reported but is not by itself a flag (see syllable_scan.blind_count_note)."),
    ])),
    ("method", collections.OrderedDict([
        ("features", "10 ms and 5 ms RMS, band envelopes 100-1000 / 300-3400 / 1000-3400 / 4000-12000 Hz, log-mel flux, pyworld harvest f0 (cross-check dio+stonemask)"),
        ("nuclei", "expected vowel onsets from the beat grid template (izgara.py: every syllable sits on the sixteenth-note grid of the 105 BPM machine tempo); "
                   "the nucleus is the envelope peak near the expected place. The self-trained letter HMM of the earlier take was tried and discarded (unreliable on this take)."),
        ("boundary_kinds", hece.__doc__.split("SINIR")[1].strip() if "SINIR" in hece.__doc__ else ""),
        ("hard_cut_a", "end of 'var' = first instant after the vowel where the 1-3.4 kHz band has fallen 12 dB below its peak in the vowel and stays there >= 20 ms "
                       "(cross-check: steepest 10 ms fall). What follows is classified from the next 50 ms: pause (>= 30 ms below sung RMS - 12 dB), nasal murmur "
                       "(voiced, energy only below 1 kHz), fricative."),
        ("hard_cut_b", "deepest point of the 10 ms RMS between the body of the second sung animal sound and the /d/ burst of 'diye'; the fade-in ends 2 ms before the "
                       "level rises 6 dB above that dip."),
    ])),
    ("summary", summary),
    ("verses", out_verses),
    ("atlari_check", atlari_check),
    ("syllable_scan", syllable_scan),
    ("notes_table", notes_table),
    ("noise_floor", noise_floor),
    ("grid_check", grid_check),
    ("not_verified_by_ear", "Nothing in this file was checked by listening. Unverified by ear: that the recommended fades are inaudible, that the L2 endings "
                            "(cut at full level in 5 of 7 verses) do not sound clipped, that the 'atları' repair sounds natural, and the syllable boundaries placed on the beat grid."),
])


class Enc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return super().default(o)


json.dump(out, open(os.path.join(K, "kesim.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1, cls=Enc)
print("yazildi: kesim.json  (%d kelime, %d saklanan hece, %d bayrakli kelime, kor sayimi tutmayan %d)" % (
    len(tum_kelime), len(kept_hece), len(flag_kelime), summary["blind_count_mismatch_words"]))
print("sinir turleri:", dict(sinir_turleri))
print("atlari:", atlari_check["verdict_detail"])
print("kesip atma:", atlari_check["excision"]["start"], atlari_check["excision"]["end"], atlari_check["excision"]["removed_ms"], "ms")
for ad in SAKLANAN:
    print(ad, ":", notes_table["consensus_text"][ad])
print("perde siniflari:", summary["pitch_classes_overall_share"])
print("perde sapanlari:", [(s_["verse"], s_["line"], s_["syllable"], s_["note"], s_["deviation_semitones"]) for s_ in sapan])
print("gurultu tabani: %.1f dBFS (%.1f dB)" % (gap_db, gap_db - SUNG))
