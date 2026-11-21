#!/usr/bin/env python3
"""KABUL DENETİMİ (bir sonraki karışım için; yalnız okur): vokal stemi + orkestranın zaman/nota dosyası + hece hedefleri verilir,
perde/armoni ölçütleri tek tabloda çıkar.
Kullanım:
  python3 08_denetim.py --vokal <vokal.wav> --zaman <zaman.json> --heceler <heceler.json> [--on 0.0] [--etiket ad]
     heceler.json: {"heceler": [{"kita","satir","hece","t0","t1","hedef_midi","ozgun_midi"}...]}   (yeni7/heceler.json biçimi)
  python3 08_denetim.py --yeni6        (reddedilen karışım: yeni6/vokal_psola.wav + yeni4 zaman_G.json + hedefler.json, --on 0.100)
--on: orkestranın karışımda kaç saniye geç başladığı (vokal zaman çizgisine göre).
Ölçütler: (1) hedef notadan sapma (sent), (2) söylenen nota o vuruşun akorunun sesi mi, (3) vokalin altındaki ezgi (klarnet) aynı perde sınıfını mı çalıyor,
(4) uygulanan kaydırma büyüklüğü."""
import argparse, json, os, numpy as np, parselmouth
from parselmouth.praat import call
from ortak import *

ap = argparse.ArgumentParser(); ap.add_argument("--vokal"); ap.add_argument("--zaman"); ap.add_argument("--heceler"); ap.add_argument("--on", type=float, default=0.0); ap.add_argument("--etiket", default=None); ap.add_argument("--yeni6", action="store_true"); ap.add_argument("--ezgi", default=None, help="vokalin altındaki ezginin stemi (wav); verilirse klarnetin notası stemden ölçülür (json'da nota yoksa gerekir)")
P = ap.parse_args()
if P.yeni6:
    Y, S, Z = yukle(); P.vokal = RED_VOK; P.on = ON; P.etiket = P.etiket or "yeni6_reddedilen"; P.ezgi = P.ezgi or RED_EZGI
    H = [{"kita": s["verse"], "satir": s["line"], "sira": s["index"], "hece": s["text"], "t0": s["dest_start"], "t1": s["dest_end"], "hedef_midi": s["hedef"], "ozgun_midi": s["midi"]} for s in S]
else:
    Z = json.load(open(P.zaman, encoding="utf8")); H = json.load(open(P.heceler, encoding="utf8"))["heceler"]; P.etiket = P.etiket or os.path.basename(os.path.dirname(os.path.abspath(P.vokal)))
    say = {}
    for h in H: k = (h["kita"], h["satir"]); h["sira"] = say.get(k, 0); say[k] = h["sira"] + 1


def akor_sesleri(a):
    kok = NOTA.index(a[:2]) if len(a) > 1 and a[1] == "#" else NOTA.index(a[0]); tur = a[2:] if len(a) > 1 and a[1] == "#" else a[1:]
    s = {kok, (kok + (3 if tur.startswith("m") and not tur.startswith("maj") else 4)) % 12, (kok + 7) % 12}
    if "7" in tur: s.add((kok + 10) % 12)
    return s


V = Z["vurus_sn"]; vurus = []
for bolum in [Z["giris"]["olculer"]] + [k["olculer"] for k in Z["kitalar"]] + [Z["bitis"]["olculer"]]:
    for o in bolum:
        for i, a in enumerate(o["akorlar"]):
            t0 = o["vurus_zamanlari"][i] if "vurus_zamanlari" in o and i < len(o["vurus_zamanlari"]) else o["baslangic"] + i * V
            vurus.append((t0 + P.on, t0 + V + P.on, a))
klar = sorted((n["baslangic"] + P.on, n["baslangic"] + n["sure"] + P.on, n["midi"]) for n in Z["ezgi_notalari"] if n["parti"] == "ezgi_alti" and n["enstruman"] == "klarnet")
klar = [(a, (klar[i + 1][0] if i + 1 < len(klar) and klar[i + 1][0] - b < 0.1 else b), m) for i, (a, b, m) in enumerate(klar)]
t, f0 = f0_izi(P.vokal, "denetim_" + P.etiket)
te, fe = f0_izi(P.ezgi, "denetim_ezgi_" + P.etiket, taban=400, tavan=1100) if P.ezgi else (None, None)        # klarnet G5..B5 bölgesi


def ort(a, b, L):
    r = {}
    for x0, x1, v in L:
        o = min(b, x1) - max(a, x0)
        if o > 0: r[v] = r.get(v, 0) + o
    return r


xv = oku_mono(P.vokal); snd = parselmouth.Sound(xv, sampling_frequency=FS)
har = snd.to_harmonicity_cc(time_step=0.01, minimum_pitch=150, silence_threshold=0.1, periods_per_window=1.0); th = har.xs(); hv = har.values[0]


def nitelik(ca, cb):
    """03_psola_hasar.py ile aynı tanımlar: çekirdek = sesli bölümün orta %70'i."""
    k = (cb - ca) * 0.15; a, b = ca + k, cb - k; hm = (th >= a) & (th < b) & (hv > -100); mm = (t >= a) & (t < b) & (f0 > 0); d = {"hnr": float(np.mean(hv[hm])) if hm.sum() else np.nan}
    try:
        part = snd.extract_part(from_time=max(0, a - 0.01), to_time=b + 0.01); pp = call(part, "To PointProcess (periodic, cc)", 150, 720); d["jitter"] = 100 * call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
    except Exception: d["jitter"] = np.nan
    d["f0_ss"] = float(np.std(hz2midi(f0[mm])) * 100) if mm.sum() > 2 else np.nan; seg = xv[int(ca * FS):int(cb * FS)]; d["duzey"] = float(10 * np.log10(np.mean(seg ** 2) + 1e-20)); return d


sat = []
for h in H:
    m, n = hece_perdesi(t, f0, h["t0"], h["t1"]); sm = (t >= h["t0"]) & (t < h["t1"]) & (f0 > 0)
    if np.isnan(m): sat.append({**h, "olculen": None}); continue
    ca, cb = t[sm][0], t[sm][-1] + 0.005; top = cb - ca; pc = int(round(m)) % 12; ak = ort(ca, cb, vurus); kl = ort(ca, cb, klar)
    stem = None
    if te is not None:
        em = (te >= ca - P.on) & (te < cb - P.on) & (fe > 0)
        if em.sum() >= 4:
            sm_ = np.round(hz2midi(fe[em])).astype(int) % 12; stem = {"ayni": float((sm_ == pc).mean()), "nota": NOTA[int(np.bincount(sm_, minlength=12).argmax())], "kapsama": float(em.sum() * 0.005 / top)}
    q = nitelik(ca, cb) if sm.sum() >= 6 else {"hnr": np.nan, "jitter": np.nan, "f0_ss": np.nan, "duzey": np.nan}
    sat.append({**h, **q, "stem": stem, "olculen": m, "sent": (m - h["hedef_midi"]) * 100, "akor": max(ak, key=ak.get) if ak else None, "akor_sesi": (sum(v for k, v in ak.items() if pc in akor_sesleri(k)) / top) if ak else None,
                "klarnet": ad(max(kl, key=kl.get)) if kl else None, "klarnet_ayni": (sum(v for k, v in kl.items() if k % 12 == pc) / top) if kl else None,
                "aralik": (min((pc - max(kl, key=kl.get)) % 12, (max(kl, key=kl.get) - pc) % 12) if kl else None), "cekirdek_ms": top * 1000, "kaydirma": h["hedef_midi"] - h["ozgun_midi"] if h.get("ozgun_midi") else None})
o = [x for x in sat if x.get("olculen") is not None]; n = len(o); se = np.abs([x["sent"] for x in o]); kay = np.abs([x["kaydirma"] for x in o if x["kaydirma"] is not None])
ad_ = [x for x in o if x["akor_sesi"] is not None and x["akor_sesi"] < 0.5]; kf = [x for x in o if x["klarnet_ayni"] is not None and x["klarnet_ayni"] < 0.5]; kyok = [x for x in o if x["klarnet_ayni"] is None]
iki = [x for x in kf if x["aralik"] in (1, 2)]
oz = {"etiket": P.etiket, "hece": len(H), "olculen_hece": n, "hedeften_sapma_ortanca_sent": round(float(np.median(se)), 1), "hedeften_sapma_p90_sent": round(float(np.percentile(se, 90)), 1), "25_sentten_fazla_hece": int((se > 25).sum()),
      "akor_sesi_olmayan_hece": len(ad_), "akor_sesi_olmayan_%": round(100 * len(ad_) / n, 1), "klarnetten_farkli_hece": len(kf), "klarnetten_farkli_%": round(100 * len(kf) / n, 1), "klarnetle_1-2_yarim_ses_hece": len(iki),
      "klarnetsiz_hece": len(kyok), "kaydirma_ortalama_mutlak": round(float(kay.mean()), 2) if len(kay) else None, "kaydirma_3.5_ustu_hece": int((kay >= 3.5).sum()) if len(kay) else None, "kaydirma_5.5_ustu_hece": int((kay >= 5.5).sum()) if len(kay) else None,
      "kaydirma_en_cok": round(float(kay.max()), 2) if len(kay) else None}
med = lambda L, k: round(float(np.nanmedian([x[k] for x in L])), 2) if L else None
agir = [x for x in o if x["kaydirma"] is not None and abs(x["kaydirma"]) >= 3.5]; asagi = [x for x in o if x["kaydirma"] is not None and x["kaydirma"] <= -3.5]
bas = [x for x in o if x["sira"] == 0 and x["satir"] in ("L1", "L2", "L4")]; dig = [x for x in o if not (x["sira"] == 0 and x["satir"] in ("L1", "L2", "L4"))]
oz.update({"HNR_ortanca_dB (işlenmemiş ses: 18.0)": med(o, "hnr"), "HNR_ortanca_agir_kaydirilan(|k|>=3.5)": med(agir, "hnr"), "HNR_ortanca_agir_asagi(k<=-3.5)": med(asagi, "hnr"), "jitter_ortanca_% (işlenmemiş: 0.36)": med(o, "jitter"),
           "hece_ici_f0_ss_ortanca_sent (işlenmemiş: 20.6)": med(o, "f0_ss"), "satir_basi_hecesi_duzey_farki_dB (diğer hecelere göre)": round(float(np.nanmean([x["duzey"] for x in bas]) - np.nanmean([x["duzey"] for x in dig])), 1) if bas else None})
if te is not None:
    so = [x for x in o if x["stem"] is not None]; sf_ = [x for x in so if x["stem"]["ayni"] < 0.5]
    oz.update({"stemden: klarnetin caldigi hece": len(so), "stemden: klarnet farkli perde sinifi (hece)": len(sf_), "stemden: farkli_%": round(100 * len(sf_) / max(1, len(so)), 1),
               "stemden: farkli ornekler": [("K%d %s #%d %s söylenen %s klarnet %s" % (x["kita"], x["satir"], x["sira"], x["hece"], ad(x["olculen"]), x["stem"]["nota"])) for x in sf_[:12]]})
print(json.dumps(oz, ensure_ascii=False, indent=1))
print(" satır/sıra bazında (kıta sayısı içinde): klarnetten farklı | akor dışı")
g = {}
for x in o: g.setdefault((x["satir"], x["sira"]), []).append(x)
for (satir, sira), L in sorted(g.items(), key=lambda q: (["L1", "L2", "diye", "L4"].index(q[0][0]) if q[0][0] in ("L1", "L2", "diye", "L4") else 9, q[0][1])):
    a = sum(1 for x in L if x["klarnet_ayni"] is not None and x["klarnet_ayni"] < 0.5); b = sum(1 for x in L if x["akor_sesi"] is not None and x["akor_sesi"] < 0.5)
    if a or b: print("   %-5s #%d %-5s söylenen %-3s akor %-3s klarnet %-4s: klarnet≠ %d/%d, akor dışı %d/%d, kaydırma ort %+.1f" % (satir, sira, L[0]["hece"], ad(L[0]["olculen"]), L[0]["akor"], L[0]["klarnet"], a, len(L), b, len(L), np.mean([x["kaydirma"] or 0 for x in L])))
json.dump({"ozet": oz, "heceler": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()} for x in sat]}, open(os.path.join(ARA, "08_denetim_%s.json" % P.etiket), "w", encoding="utf8"), ensure_ascii=False, indent=1)
