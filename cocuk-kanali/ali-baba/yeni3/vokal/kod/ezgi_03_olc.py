#!/usr/bin/env python3
"""ezgi_03: uc adayi nesnel olcutlerle karsilastirir ve birini secer (ezgi_ara/karsilastirma.json).

Secim kurali (olcumlerden ONCE yazildi):
 1) Elemeler: kaydirilan hecelerde > 50 cent hata sayisi, seslilik uyumu >= %95, dize gecikmesi <= 5 ms,
    tik sayisi 0, planli gecisler disinda yeni f0 sicramasi. Eleme ihlali az olan one gecer.
 2) Esitlikte bozulma puani (dusuk iyi), hepsi dB:
      puan = pay_kaydirilmayan * (kaydirilmayan bolgelerde mel tayf uzakligi)
           + pay_kaydirilan   * (kaydirilan unlulerde zarf uzakligi + 0.5 * kaba bant dengesi uzakligi)
           + 0.5 * |HNR farki| + 0.5 * |HNR(2-8 kHz) farki| + 0.5 * |tepe faktoru farki|
    pay_* = sarkilan orneklerin kaydirilmayan / kaydirilan orani (B ve C'nin degistirme maskesinden)."""
import os, json, numpy as np, soundfile as sf
import ezgi_ortak as o, ezgi_olcum as ol

x, Y = o.oku()
plan = json.load(open(os.path.join(o.ARA, "egri.json"), encoding="utf8"))
adlar = ["A_dunya_tam", "B_dunya_karma", "C_psola"]
akt = np.zeros(len(x), dtype=bool)
for c in o.parcalar(Y):
    akt[c["a"]:c["b"]] = True
modB = np.load(os.path.join(o.ARA, "mod_B_dunya_karma.npy"))
pay_kaydirilan = float(np.mean(modB[akt])); pay_kaydirilmayan = 1.0 - pay_kaydirilan
sonuc = {}
for ad in adlar:
    y, sr = sf.read(os.path.join(o.ARA, "aday_%s.wav" % ad), dtype="float64")
    r = ol.tam_olcum(x, y, Y, plan, ad)
    ih = dict(pitch_over_50_both_detectors=r["pitch"]["over_50_confirmed_by_both"],
              voicing_below_95=int(r["voicing_agreement"]["pyin_percent"] < 95.0) + int(r["voicing_agreement"]["harvest_percent"] < 95.0),
              lag_over_5ms=int(sum(abs(q["lag_ms"]) > 5.0 for q in r["timing"]["lines"])),
              clicks=r["clicks"]["count"], new_f0_jumps=r["f0_jumps"]["new_away_from_transitions"])
    sp, pe = r["spectral"], r["periodicity"]
    puan = (pay_kaydirilmayan * sp["unshifted_all_lsd_db"] + pay_kaydirilan * (sp["shifted_envelope_dist_db"] + 0.5 * sp["shifted_coarse_band_dist_db"])
            + 0.5 * pe["hnr_diff_db_mean_abs"] + 0.5 * pe["hnr_2_8k_diff_db_mean_abs"] + 0.5 * pe["crest_diff_db_mean_abs"])
    r["gate_violations"] = ih; r["gate_violation_total"] = int(sum(ih.values())); r["distortion_score_db"] = round(float(puan), 3)
    sonuc[ad] = r
    print("== %s" % ad)
    print("  perde (kaydirilan heceler): pYIN ort %.1f en buyuk %.1f cent (>50: %d) | harvest ort %.1f en buyuk %.1f (>50: %d)" % (
        r["pitch"]["shifted_syllables"]["pyin"]["mean_abs"], r["pitch"]["shifted_syllables"]["pyin"]["max_abs"], r["pitch"]["shifted_syllables"]["pyin"]["over_50"],
        r["pitch"]["shifted_syllables"]["harvest"]["mean_abs"], r["pitch"]["shifted_syllables"]["harvest"]["max_abs"], r["pitch"]["shifted_syllables"]["harvest"]["over_50"]))
    print("  seslilik uyumu: pYIN %.2f%% harvest %.2f%% | gecikme en buyuk %.2f ms | duzey %+.2f dB (dize en buyuk %.2f, hece cekirdegi ort %.2f / en buyuk %.2f) LUFS farki %+.2f tepe %.2f" % (
        r["voicing_agreement"]["pyin_percent"], r["voicing_agreement"]["harvest_percent"], r["timing"]["max_abs_lag_ms"], r["level"]["rms_db_re_dogal"],
        r["level"]["line_rms_db_max_abs"], r["level"]["syllable_core_level_db_mean_abs"], r["level"]["syllable_core_level_db_max_abs"], r["level"]["lufs_diff"], r["level"]["peak_dbfs"]))
    print("  tik %d (en buyuk ornek sicramasi %.4f; ozgun %.4f) | f0 sicramasi >2 (iki bulucu): toplam %d, planli geciste %d, ozgunde de var %d, YENI %d | ham sayilar %s" % (
        r["clicks"]["count"], r["clicks"]["max_sample_jump"], r["clicks"]["max_sample_jump_dogal"], r["f0_jumps"]["confirmed_total"],
        r["f0_jumps"]["near_planned_transitions"], r["f0_jumps"]["also_in_original"], r["f0_jumps"]["new_away_from_transitions"], r["f0_jumps"]["raw_counts"]))
    print("  kaydirma denetimi (cikti - ozgun - plan): pYIN ort %.1f en buyuk %.1f | harvest ort %.1f en buyuk %.1f cent | >50 (iki bulucu birden): %d" % (
        r["pitch"]["applied_shift_check"]["pyin"]["mean_abs"], r["pitch"]["applied_shift_check"]["pyin"]["max_abs"],
        r["pitch"]["applied_shift_check"]["harvest"]["mean_abs"], r["pitch"]["applied_shift_check"]["harvest"]["max_abs"], r["pitch"]["over_50_confirmed_by_both"]))
    print("  egri sadakati (kare kare): harvest RMS %.1f / p95 %.1f / >100c %%%.2f | pYIN RMS %.1f / p95 %.1f / >100c %%%.2f" % (
        r["contour"]["harvest"]["rms"], r["contour"]["harvest"]["p95_abs"], r["contour"]["harvest"]["over_100_cents_percent"],
        r["contour"]["pyin"]["rms"], r["contour"]["pyin"]["p95_abs"], r["contour"]["pyin"]["over_100_cents_percent"]))
    q = r.pop("_per_syllable_quality")
    siniflar = (("L4 (+7)", lambda h: h["line"] == 4), ("L3 (+3)", lambda h: h["line"] == 3),
                ("L1/L2 yukari", lambda h: h["line"] in (1, 2) and h["shift"] > 0), ("L1/L2 asagi", lambda h: h["line"] in (1, 2) and h["shift"] < 0))
    r["by_class"] = {}
    for nm, fn in siniflar:
        hh = [h for h in q if fn(h)]
        hl = [t_ for t_ in r.get("syllables", [])]
        r["by_class"][nm] = dict(n=len(hh), envelope_dist_db=round(float(np.mean([h["env"] for h in hh])), 2), coarse_band_dist_db=round(float(np.mean([h["coarse"] for h in hh])), 2),
                                 hnr_diff_db=round(float(np.mean([h["hnr"] for h in hh])), 2), hnr_2_8k_diff_db=round(float(np.mean([h["hnr_hf"] for h in hh])), 2),
                                 crest_diff_db=round(float(np.mean([h["crest"] for h in hh])), 2))
        print("    %-13s n=%3d zarf %.2f kaba %.2f HNR %+.2f HNR(2-8k) %+.2f tepe %+.2f" % (nm, len(hh), r["by_class"][nm]["envelope_dist_db"], r["by_class"][nm]["coarse_band_dist_db"],
              r["by_class"][nm]["hnr_diff_db"], r["by_class"][nm]["hnr_2_8k_diff_db"], r["by_class"][nm]["crest_diff_db"]))
    print("  tayf: kaydirilmayan otumsuz %.2f dB, kaydirilmayan sesli %.2f dB, hepsi %.2f dB | kaydirilan zarf %.2f dB (p90 %.2f), kaba bant %.2f dB" % (
        sp["unvoiced_lsd_db"], sp["voiced_unshifted_lsd_db"], sp["unshifted_all_lsd_db"], sp["shifted_envelope_dist_db"], sp["shifted_envelope_dist_db_p90"], sp["shifted_coarse_band_dist_db"]))
    print("  HNR farki %+.2f (|.| %.2f) dB, 2-8 kHz %+.2f (|.| %.2f) dB, tepe faktoru %+.2f (|.| %.2f) dB" % (
        pe["hnr_diff_db_mean"], pe["hnr_diff_db_mean_abs"], pe["hnr_2_8k_diff_db_mean"], pe["hnr_2_8k_diff_db_mean_abs"], pe["crest_diff_db_mean"], pe["crest_diff_db_mean_abs"]))
    print("  eleme ihlalleri", ih, "| bozulma puani %.3f dB" % puan, flush=True)
sira = sorted(adlar, key=lambda a: (sonuc[a]["gate_violation_total"], sonuc[a]["distortion_score_db"]))
kars = dict(rule=__doc__, share_shifted=round(pay_kaydirilan, 4), share_unshifted=round(pay_kaydirilmayan, 4), ranking=sira, chosen=sira[0], candidates=sonuc)
with open(os.path.join(o.ARA, "karsilastirma.json"), "w", encoding="utf8") as f:
    json.dump(kars, f, ensure_ascii=False, indent=1, default=float)
print("SIRALAMA:", sira, "-> SECILEN:", sira[0])
