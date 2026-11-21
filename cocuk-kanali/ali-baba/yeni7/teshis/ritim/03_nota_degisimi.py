#!/usr/bin/env python3
"""Soru 2: Vokalin NOTA DEĞİŞTİRDİĞİ anlar, orkestranın aynı ölçülerde vokalin altında çaldığı ezginin (ezgi_alti: klarnet + çan) nota
değiştirdiği anlarla aynı mı?
 A) Kâğıt üstünde: hedefler.json (hece -> hedef nota, hece zamanı) ile zaman_G.json "ezgi_notalari" (parti = ezgi_alti, klarnet) karşılaştırılır.
 B) Seste doğrulama: vokal_psola.wav ve ezgi_alti_G.wav'ın f0 izleri (Praat) -> kare kare perde sınıfı uyumu ve en iyi uyumu veren kayma.
Zamanlar reddedilen karışımın zaman eksenindedir (orkestra + 0.100 s)."""
import json, os, numpy as np, parselmouth
from collections import Counter, defaultdict
from ortak import *

Z = json.load(open(ZAMAN, encoding="utf8")); H = json.load(open(HEDEF, encoding="utf8")); Y = json.load(open(YERLESIM, encoding="utf8"))
UNLU = {(h["verse"], h["line"], h["index"]): h for h in json.load(open(os.path.join(ARA, "02_hece_unlu_girisleri.json")))["heceler"]}
AD = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
klar = sorted([n for n in Z["ezgi_notalari"] if n["parti"] == "ezgi_alti" and n["enstruman"] == "klarnet"], key=lambda n: n["baslangic"])
yuva = {(L["verse"], L["line"], s["index"]): (s["dest_bar"], s["beat_in_bar"], s["dest_grid_time"], L["dest_bar_downbeat"]) for L in Y["lines"] for s in L["syllables"]}

def klarnet_notasi(t):
    """t anında (karışım zamanı) çalan / en son çalmış klarnet notası (aynı ölçü içinde)."""
    son = None
    for n in klar:
        a = n["baslangic"] + ON
        if a <= t + 1e-6: son = n
        else: break
    return son

satirlar = defaultdict(list)
for h in H: satirlar[(h["verse"], h["line"])].append(h)
sonuc = {"tanim": __doc__, "satirlar": []}
hece_tablo = []; degisimler = []
for (v, l), hs in satirlar.items():
    olcu_basi = yuva[(v, l, 0)][3] if l != "diye" else yuva[(v, l, 0)][3]
    # --- hece hece: hecenin yuvasında klarnet hangi notayı çalıyor? ---
    for h in hs:
        bar, bib, tg, ob = yuva[(v, l, h["index"])]
        kn = klarnet_notasi(tg + 0.005)
        u = UNLU[(v, l, h["index"])]
        ayni_olcu = kn is not None and kn["olcu"] == bar
        aralik = (h["hedef_midi"] - kn["midi"]) % 12 if ayni_olcu else None
        hece_tablo.append({"kita": v, "satir": l, "hece": h["text"], "sekizlik_yuva": bib * 2, "yuva_zamani": round(tg, 4), "hece_basi": h["dest_start"], "unlu_girisi": u["red_unlu"],
                           "vokal_hedef": AD[h["hedef_midi"] % 12], "vokal_hedef_midi": h["hedef_midi"], "klarnet": kn["nota"] if ayni_olcu else None, "klarnet_midi": kn["midi"] if ayni_olcu else None,
                           "aralik_yarim_ses_mod12": aralik, "ayni_perde_sinifi": aralik == 0 if aralik is not None else None})
    # --- nota DEĞİŞİMİ anları ---
    kb = [n for n in klar if n["olcu"] == yuva[(v, l, 0)][0]]
    kd = [(kb[i]["baslangic"] + ON, kb[i - 1]["midi"] % 12, kb[i]["midi"] % 12, kb[i]["vurus"] * 2) for i in range(1, len(kb)) if kb[i]["midi"] != kb[i - 1]["midi"]]
    vd = [(hs[i]["dest_start"], UNLU[(v, l, hs[i]["index"])]["red_unlu"], hs[i - 1]["hedef_midi"] % 12, hs[i]["hedef_midi"] % 12, yuva[(v, l, hs[i]["index"])][1] * 2, hs[i]["text"]) for i in range(1, len(hs)) if hs[i]["hedef_midi"] != hs[i - 1]["hedef_midi"]]
    for j, (tk, a, b, yk) in enumerate(kd):
        # vokalde aynı değişim (aynı önceki -> sonraki perde sınıfı), sırayla eşlenir
        es = vd[j] if j < len(vd) and (vd[j][2], vd[j][3]) == (a, b) else None
        degisimler.append({"kita": v, "satir": l, "klarnet_degisim": "%s->%s" % (AD[a], AD[b]), "klarnet_zamani": round(tk, 4), "klarnet_sekizlik_yuva": yk,
                           "vokal_hece": es[5] if es else None, "vokal_sekizlik_yuva": es[4] if es else None,
                           "vokal_hece_basi_eksi_klarnet_ms": round((es[0] - tk) * 1000, 1) if es else None, "vokal_unlu_girisi_eksi_klarnet_ms": round((es[1] - tk) * 1000, 1) if es else None})
    sonuc["satirlar"].append({"kita": v, "satir": l, "klarnet_degisim_sayisi": len(kd), "vokal_degisim_sayisi": len(vd)})

T = [h for h in hece_tablo if h["klarnet"] is not None]
say = Counter(h["aralik_yarim_ses_mod12"] for h in T)
sonuc["A_hece_yuvasinda_vokal_hedefi_ile_klarnet"] = {
    "hece_sayisi": len(hece_tablo), "klarnetin_caldigi_olcudeki_hece": len(T), "ayni_perde_sinifi": sum(h["ayni_perde_sinifi"] for h in T),
    "farkli": sum(not h["ayni_perde_sinifi"] for h in T), "farkli_yuzde": round(100 * np.mean([not h["ayni_perde_sinifi"] for h in T]), 1),
    "aralik_dagilimi_yarim_ses_mod12": {str(k): int(n) for k, n in sorted(say.items())},
    "buyuk_ikili_catisma(2_veya_10)": int(say.get(2, 0) + say.get(10, 0)), "dortlu_besli(5_veya_7)": int(say.get(5, 0) + say.get(7, 0)),
    "yuvaya_gore_farkli": {str(k): "%d/%d" % (sum(1 for h in T if h["sekizlik_yuva"] == k and not h["ayni_perde_sinifi"]), sum(1 for h in T if h["sekizlik_yuva"] == k)) for k in sorted({h["sekizlik_yuva"] for h in T})},
    "satira_gore_farkli": {l: "%d/%d" % (sum(1 for h in T if h["satir"] == l and not h["ayni_perde_sinifi"]), sum(1 for h in T if h["satir"] == l)) for l in ("L1", "L2", "diye", "L4")}}
D_ = [d for d in degisimler if d["vokal_hece"] is not None]
sonuc["A_nota_degisimi_anlari"] = {"klarnet_nota_degisimi": len(degisimler), "vokalde_esi_bulunan": len(D_),
    "vokal_hece_basi_eksi_klarnet_ms": ozet([d["vokal_hece_basi_eksi_klarnet_ms"] for d in D_]), "vokal_unlu_girisi_eksi_klarnet_ms": ozet([d["vokal_unlu_girisi_eksi_klarnet_ms"] for d in D_]),
    "yuva_farki_sekizlik": dict(Counter(str(d["vokal_sekizlik_yuva"] - d["klarnet_sekizlik_yuva"]) for d in D_)),
    "degisime_gore": {k: ozet([d["vokal_unlu_girisi_eksi_klarnet_ms"] for d in D_ if d["klarnet_degisim"] == k]) for k in sorted({d["klarnet_degisim"] for d in D_})},
    "40ms_icinde_ayni_anda_olan": int(sum(abs(d["vokal_unlu_girisi_eksi_klarnet_ms"]) <= 40 for d in D_)),
    "200ms_den_gec": int(sum(d["vokal_unlu_girisi_eksi_klarnet_ms"] > 200 for d in D_))}

# ---------------- B) seste doğrulama ----------------
def f0_izi(x, lo, hi, adim=0.005):
    p = parselmouth.Sound(x, sampling_frequency=FS).to_pitch_ac(time_step=adim, pitch_floor=lo, pitch_ceiling=hi)
    f = p.selected_array["frequency"]; t = p.xs(); return t, f
vok = oku_mono(RED_VOK); ezg = np.concatenate([np.zeros(int(ON * FS)), oku_mono(RED_EZGI)])
tv, fv = f0_izi(vok, 150, 720); te, fe = f0_izi(bant(ezg, 400, 1100), 450, 950)
ortak_t = np.arange(0.2, min(len(vok), len(ezg)) / FS - 0.2, 0.005)
def ornekle(t, f, tt):
    i = np.clip(np.searchsorted(t, tt), 1, len(t) - 1); i = np.where(np.abs(t[i - 1] - tt) < np.abs(t[i] - tt), i - 1, i); return f[i]
V = ornekle(tv, fv, ortak_t); E = ornekle(te, fe, ortak_t)
mv = np.where(V > 0, 69 + 12 * np.log2(np.maximum(V, 1) / 440), np.nan); me = np.where(E > 0, 69 + 12 * np.log2(np.maximum(E, 1) / 440), np.nan)
# ölçülen hece perdesi (hece çekirdeğinde ortanca) hedefle aynı mı? (PSOLA gerçekten o notaya çekmiş mi)
sap = []
for L in Y["lines"]:
    for s in L["syllables"]:
        m = (ortak_t >= s["dest_core_start"]) & (ortak_t <= s["dest_core_end"]) & ~np.isnan(mv)
        hed = next(h["hedef_midi"] for h in H if h["verse"] == L["verse"] and h["line"] == L["line"] and h["index"] == s["index"])
        if m.sum() >= 3: sap.append((np.median(mv[m]) - hed) * 100)
sonuc["B_seste_vokal_perdesi_eksi_hedef_sent"] = ozet(sap)
def uyum(kayma_ms):
    k = int(round(kayma_ms / 5)); a = mv[max(0, k):len(mv) + min(0, k)]; b = me[max(0, -k):len(me) + min(0, -k)]      # a(t) = vokal(t + kayma)
    m = ~np.isnan(a) & ~np.isnan(b)
    if m.sum() < 100: return np.nan, 0
    d = np.abs(((a[m] - b[m]) + 6) % 12 - 6); return float((d < 0.6).mean()), int(m.sum())
egri = {int(k): uyum(k) for k in range(-600, 601, 5)}
en = max(egri, key=lambda k: egri[k][0])
sonuc["B_seste_perde_sinifi_uyumu"] = {"aciklama": "vokal ile klarnet aynı anda sesliyken perde sınıfı aynı olan karelerin oranı; kayma = vokalin kaç ms GERİDE olduğu varsayımı (vokal(t+kayma) ile klarnet(t) karşılaştırılır)",
    "kayma_0ms": round(egri[0][0], 3), "ortak_sesli_sure_sn": round(egri[0][1] * 0.005, 1), "en_iyi_kayma_ms": en, "en_iyi_kaymada_uyum": round(egri[en][0], 3),
    "kayma_+285ms": round(egri[285][0], 3), "kayma_-285ms": round(egri[-285][0], 3), "egri_her_50ms": {str(k): round(egri[k][0], 3) for k in range(-600, 601, 50)}}
# kare kare aralık dağılımı (kayma 0)
m = ~np.isnan(mv) & ~np.isnan(me); ar = np.round(((mv[m] - me[m]) % 12)).astype(int) % 12
sonuc["B_seste_aralik_dagilimi_kayma0_yuzde"] = {str(k): round(100 * float((ar == k).mean()), 1) for k in range(12)}
json.dump(sonuc, open(os.path.join(ARA, "03_nota_degisimi.json"), "w"), ensure_ascii=False, indent=1)
json.dump({"heceler": hece_tablo, "degisimler": degisimler}, open(os.path.join(ARA, "03_hece_nota_tablosu.json"), "w"), ensure_ascii=False, indent=0)
print(json.dumps({k: v for k, v in sonuc.items() if k not in ("tanim", "satirlar")}, ensure_ascii=False, indent=1))
print("--- kıta 1, satır 1-2 ---")
for h in hece_tablo[:19]: print("  %-4s %-5s yuva %.1f  vokal %-2s  klarnet %-3s  aralık %s" % (h["satir"], h["hece"], h["sekizlik_yuva"], h["vokal_hedef"], h["klarnet"], h["aralik_yarim_ses_mod12"]))
for d in degisimler[:6]: print(" ", d)
