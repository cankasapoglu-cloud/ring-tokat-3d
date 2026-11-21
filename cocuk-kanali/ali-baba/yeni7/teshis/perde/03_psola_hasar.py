#!/usr/bin/env python3
"""SORU 3: Hece başına uygulanan perde kaydırması ne kadar; bu büyüklükteki TD-PSOLA kaydırması stemde ölçülebilir ne hasar bırakmış?
Üç stem, AYNI ölçümler, AYNI heceler:
   ONCE  = yeni4/vokal/vokal_dogal.wav   (aynı yerleşim, perde işlemi yok)
   SONRA = yeni6/vokal_psola.wav          (reddedilen karışımdaki vokal)
   REF   = sevilen referansın ayrılmış vokali (kaynak zamanlarında; ONCE'nin kesilmeden önceki hali)
Ölçümler (hece çekirdeği = sesli karelerin orta %70'i): HNR (Praat, cc), jitter(local), shimmer(local) (Praat PointProcess cc),
CPP (kendi hesabım: 40 ms Hann, kepstrum tepe - doğrusal eğilim, dB), 300-4000 Hz spektral düzlük, hece içi f0 standart sapması (sent),
en yakın yarım sese +-10 sent içinde kalan sesli kare oranı ("makine düzlüğü"), hedeften >80 sent sapan kare (kaydırılamamış artık).
Çıktı: ara/03_psola_hasar.json + ekrana özet."""
import json, os, numpy as np, parselmouth
from parselmouth.praat import call
from ortak import *

Y, S, Z = yukle(); cik = {}
rms = {}
for L in Y["lines"]:
    for h in L["syllables"]: rms[(L["verse"], L["line"], h["index"])] = (h.get("rms_dbfs"), h.get("is_glide"), h.get("glide_semitones"), h.get("f0_iqr_semitones"))


def cpp_db(seg, fs=FS, f_lo=150, f_hi=720):
    n = int(0.04 * fs); h = int(0.01 * fs); r = []
    if len(seg) < n: return np.nan
    for a in range(0, len(seg) - n + 1, h):
        x = seg[a:a + n] * np.hanning(n); N = 4096
        ls = 20 * np.log10(np.abs(np.fft.rfft(x, N)) + 1e-9); ls = ls[: int(5000 / (fs / N))]          # 0-5 kHz
        c = np.abs(np.fft.irfft(ls)); q = np.arange(len(c)) / (2 * 5000.0)                               # kefrens ekseni (s)
        cd = 20 * np.log10(c + 1e-9); m = (q >= 1.0 / f_hi) & (q <= 1.0 / f_lo); g = (q >= 0.001) & (q <= 0.02)
        p = np.polyfit(q[g], cd[g], 1); i = np.where(m)[0][np.argmax(cd[m])]; r.append(cd[i] - np.polyval(p, q[i]))
    return float(np.mean(r)) if r else np.nan


def duzluk(seg, fs=FS):
    n = len(seg)
    if n < 1024: return np.nan
    sp = np.abs(np.fft.rfft(seg * np.hanning(n))) ** 2; fr = np.fft.rfftfreq(n, 1 / fs); m = (fr >= 300) & (fr <= 4000); p = sp[m] + 1e-20
    return float(10 * np.log10(np.exp(np.mean(np.log(p))) / np.mean(p)))


def olc(yol, ad_, zaman):
    x = oku_mono(yol); snd = parselmouth.Sound(x, sampling_frequency=FS); t, f0 = f0_izi(yol, ad_)
    har = snd.to_harmonicity_cc(time_step=0.01, minimum_pitch=150, silence_threshold=0.1, periods_per_window=1.0); th = har.xs(); hv = har.values[0]
    r = []
    for s in S:
        a, b = zaman(s); m = (t >= a) & (t < b) & (f0 > 0); d = {}
        if m.sum() < 6: r.append(None); continue
        tv = t[m]; k = int(len(tv) * 0.15); ca, cb = tv[k], tv[len(tv) - 1 - k] + 0.005; cm = (t >= ca) & (t < cb) & (f0 > 0); mid = hz2midi(f0[cm])
        hm = (th >= ca) & (th < cb) & (hv > -100); d["hnr_db"] = float(np.mean(hv[hm])) if hm.sum() else np.nan
        seg = x[int(ca * FS):int(cb * FS)]; d["cpp_db"] = cpp_db(seg); d["duzluk_db"] = duzluk(seg)
        try:
            part = snd.extract_part(from_time=max(0, ca - 0.01), to_time=cb + 0.01); pp = call(part, "To PointProcess (periodic, cc)", 150, 720)
            d["jitter_%"] = 100 * call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3); d["shimmer_%"] = 100 * call([part, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        except Exception: d["jitter_%"] = np.nan; d["shimmer_%"] = np.nan
        d["f0_ss_sent"] = float(np.std(mid) * 100); d["f0_ortanca_midi"] = float(np.median(mid)); d["cekirdek_ms"] = (cb - ca) * 1000
        allm = hz2midi(f0[m]); d["yarim_sese_10sent_ici_%"] = float((np.abs(allm - np.round(allm)) <= 0.10).mean() * 100)
        d["kare"] = int(m.sum()); d["tum_midi"] = allm; d["tum_t"] = t[m] - a
        d["sicrama_%"] = float((np.abs(np.diff(allm)) > 1.0).mean() * 100) if len(allm) > 1 else 0.0
        r.append(d)
    return r


once = olc(DOGAL_VOK, "dogal", lambda s: (s["dest_start"], s["dest_end"]))
sonra = olc(RED_VOK, "red_psola", lambda s: (s["dest_start"], s["dest_end"]))
ref = olc(REF_VOK, "ref_vokal", lambda s: (s["src_start"], s["src_end"]))
OLCUT = ["hnr_db", "cpp_db", "duzluk_db", "jitter_%", "shimmer_%", "f0_ss_sent", "yarim_sese_10sent_ici_%", "sicrama_%"]
kay = np.array([s["hedef"] - s["midi"] for s in S]); ak = np.abs(kay)
cik["kaydirma"] = {"hece": len(kay), "ortalama_mutlak": round(float(ak.mean()), 2), "ortanca_mutlak": round(float(np.median(ak)), 2), "p90": round(float(np.percentile(ak, 90)), 2), "en_cok_yukari": round(float(kay.max()), 2), "en_cok_asagi": round(float(kay.min()), 2),
                   "dagilim_hece": {"<0.5": int((ak < 0.5).sum()), "0.5-1.5": int(((ak >= 0.5) & (ak < 1.5)).sum()), "1.5-2.5": int(((ak >= 1.5) & (ak < 2.5)).sum()), "2.5-3.5": int(((ak >= 2.5) & (ak < 3.5)).sum()),
                                    "3.5-4.5": int(((ak >= 3.5) & (ak < 4.5)).sum()), ">=4.5": int((ak >= 4.5).sum())},
                   "yukari_hece": int((kay > 0.5).sum()), "asagi_hece": int((kay < -0.5).sum()), "oran_araligi": [round(float(2 ** (kay.min() / 12)), 3), round(float(2 ** (kay.max() / 12)), 3)]}
print("KAYDIRMA (hedef - özgün, yarım ses):", json.dumps(cik["kaydirma"], ensure_ascii=False))
# satır x sıra ortalama kaydırma
print("\n satır/sıra ortalama kaydırma (7 kıta):")
for satir in ("L1", "L2", "diye", "L4"):
    g = {}
    for s, k in zip(S, kay): 
        if s["line"] == satir: g.setdefault(s["index"], []).append(k)
    print("  %-5s" % satir, "  ".join("%d:%+.1f" % (i, np.mean(v)) for i, v in sorted(g.items())))

def ozet(L, anahtar):
    v = np.array([d[anahtar] for d in L if d is not None and not np.isnan(d[anahtar])]); return (round(float(np.median(v)), 2), round(float(np.mean(v)), 2), int(len(v))) if len(v) else (None, None, 0)
gruplar = {"hafif |k|<1.5": ak < 1.5, "orta 1.5-3.5": (ak >= 1.5) & (ak < 3.5), "agir |k|>=3.5": ak >= 3.5, "agir yukari k>=+3.5": kay >= 3.5, "agir asagi k<=-3.5": kay <= -3.5, "hepsi": ak >= 0}
cik["gruplar"] = {}
print("\n ÖLÇÜMLER (ortanca; ÖNCE = işlenmemiş yerleşim, SONRA = PSOLA, REF = sevilen referansın vokal stemi; fark = aynı hecede SONRA-ÖNCE ortancası)")
for gad, gm in gruplar.items():
    idx = np.where(gm)[0]; cik["gruplar"][gad] = {"hece": int(len(idx))}
    print("  [%s] hece %d" % (gad, len(idx)))
    for o in OLCUT:
        a = ozet([once[i] for i in idx], o); b = ozet([sonra[i] for i in idx], o); c = ozet([ref[i] for i in idx], o)
        f = np.array([sonra[i][o] - once[i][o] for i in idx if once[i] is not None and sonra[i] is not None and not np.isnan(once[i][o]) and not np.isnan(sonra[i][o])])
        kotu = None
        cik["gruplar"][gad][o] = {"once": a[0], "sonra": b[0], "ref": c[0], "fark_ortanca": round(float(np.median(f)), 2) if len(f) else None, "fark_p10": round(float(np.percentile(f, 10)), 2) if len(f) else None, "fark_p90": round(float(np.percentile(f, 90)), 2) if len(f) else None}
        print("     %-26s önce %8s  sonra %8s  ref %8s   fark ortanca %+7.2f (p10 %+.2f, p90 %+.2f)" % (o, a[0], b[0], c[0], np.median(f), np.percentile(f, 10), np.percentile(f, 90)))

# kaydırma büyüklüğü ile hasar ilişkisi (Spearman)
from scipy.stats import spearmanr
cik["iliski_spearman"] = {}
for o in ("hnr_db", "cpp_db", "jitter_%", "shimmer_%"):
    v = [(ak[i], kay[i], sonra[i][o] - once[i][o]) for i in range(len(S)) if once[i] is not None and sonra[i] is not None and not np.isnan(once[i][o]) and not np.isnan(sonra[i][o])]
    v = np.array(v); r1 = spearmanr(v[:, 0], v[:, 2]); r2 = spearmanr(v[:, 1], v[:, 2]); cik["iliski_spearman"][o] = {"mutlak_kaydirma": [round(float(r1[0]), 2), float(r1[1])], "isaretli_kaydirma": [round(float(r2[0]), 2), float(r2[1])]}
print("\n Spearman (fark ~ |kaydırma| ; fark ~ işaretli kaydırma):", json.dumps(cik["iliski_spearman"]))

# kaydırılamamış artıklar: hece içinde (kenarlardan 35 ms içeride) hedeften >80 sent sapan sesli kareler
art = []; topk = 0; kotuk = 0
for s, d in zip(S, sonra):
    if d is None: continue
    sure = s["dest_end"] - s["dest_start"]; ic = (d["tum_t"] >= 0.035) & (d["tum_t"] <= sure - 0.035); sap = (d["tum_midi"][ic] - s["hedef"]) * 100
    topk += len(sap); kk = int((np.abs(sap) > 80).sum()); kotuk += kk
    if kk >= 4: art.append({"kita": s["verse"], "satir": s["line"], "sira": s["index"], "hece": s["text"], "zaman": round(s["dest_start"], 2), "kotu_ms": kk * 5, "en_cok_sent": round(float(np.abs(sap).max())), "kaydirma": round(float(s["hedef"] - s["midi"]), 1)})
cik["hedeften_80sent_sapan"] = {"kare_orani_%": round(100 * kotuk / topk, 2), "toplam_ms": kotuk * 5, "hece_(>=20ms)": len(art), "liste": sorted(art, key=lambda x: -x["kotu_ms"])[:20]}
print("\n hedeften >80 sent sapan iç kareler: %%%.2f (%d ms), 20 ms ve üzeri olan hece %d" % (100 * kotuk / topk, kotuk * 5, len(art)))
for x in cik["hedeften_80sent_sapan"]["liste"][:12]: print("    K%d %-4s #%d %-5s t=%.2f  %d ms, en çok %d sent, kaydırma %+.1f" % (x["kita"], x["satir"], x["sira"], x["hece"], x["zaman"], x["kotu_ms"], x["en_cok_sent"], x["kaydirma"]))

# düzey - perde ilişkisi (doğal söyleyişte yüksek nota = daha gür); özgün perde ve hedef perde ile
lv = np.array([rms[(s["verse"], s["line"], s["index"])][0] for s in S], float); og = np.array([s["midi"] for s in S]); hd = np.array([s["hedef"] for s in S], float)
cik["duzey_perde_iliskisi"] = {"ozgun_perde_ile_r": round(float(np.corrcoef(lv, og)[0, 1]), 2), "hedef_perde_ile_r": round(float(np.corrcoef(lv, hd)[0, 1]), 2),
                               "en_yuksek_hedefte(G4)_ort_dBFS": round(float(lv[hd == 67].mean()), 1), "en_alcak_hedefte(D4)_ort_dBFS": round(float(lv[hd == 62].mean()), 1),
                               "ozgunde_ust_ucte_bir(>=66.5)_ort_dBFS": round(float(lv[og >= 66.5].mean()), 1), "ozgunde_alt(<=62.5)_ort_dBFS": round(float(lv[og <= 62.5].mean()), 1)}
print("\n düzey-perde:", json.dumps(cik["duzey_perde_iliskisi"], ensure_ascii=False))
# kayma (glide) düzleşmesi
gl = np.array([bool(rms[(s["verse"], s["line"], s["index"])][1]) for s in S]); 
ss_o = np.array([d["f0_ss_sent"] if d else np.nan for d in once]); ss_s = np.array([d["f0_ss_sent"] if d else np.nan for d in sonra])
cik["kayma"] = {"ozgunde_kaymali_hece": int(gl.sum()), "kaymali_hecelerde_f0_ss_once": round(float(np.nanmedian(ss_o[gl])), 1), "kaymali_hecelerde_f0_ss_sonra": round(float(np.nanmedian(ss_s[gl])), 1)}
print(" kayma:", json.dumps(cik["kayma"], ensure_ascii=False))
# en çok hasar gören heceler (HNR düşüşü)
dh = [(sonra[i]["hnr_db"] - once[i]["hnr_db"], i) for i in range(len(S)) if once[i] and sonra[i] and not np.isnan(once[i]["hnr_db"]) and not np.isnan(sonra[i]["hnr_db"])]
dh.sort(); cik["en_cok_hnr_dusen"] = []
print("\n HNR'si en çok düşen 15 hece:")
for f, i in dh[:15]:
    s = S[i]; cik["en_cok_hnr_dusen"].append({"kita": s["verse"], "satir": s["line"], "sira": s["index"], "hece": s["text"], "zaman": round(s["dest_start"], 2), "kaydirma": round(float(kay[i]), 1), "hnr_once": round(once[i]["hnr_db"], 1), "hnr_sonra": round(sonra[i]["hnr_db"], 1)})
    print("    K%d %-4s #%d %-5s t=%.2f  kaydırma %+.1f  HNR %.1f -> %.1f dB (%.1f)" % (s["verse"], s["line"], s["index"], s["text"], s["dest_start"], kay[i], once[i]["hnr_db"], sonra[i]["hnr_db"], f))
cik["hece_bazli"] = [{"kita": s["verse"], "satir": s["line"], "sira": s["index"], "hece": s["text"], "kaydirma": round(float(k), 2),
                      **{("once_" + o): (None if a is None or np.isnan(a[o]) else round(a[o], 2)) for o in OLCUT}, **{("sonra_" + o): (None if b is None or np.isnan(b[o]) else round(b[o], 2)) for o in OLCUT},
                      **{("ref_" + o): (None if c is None or np.isnan(c[o]) else round(c[o], 2)) for o in OLCUT}} for s, k, a, b, c in zip(S, kay, once, sonra, ref)]
json.dump(cik, open(os.path.join(ARA, "03_psola_hasar.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
