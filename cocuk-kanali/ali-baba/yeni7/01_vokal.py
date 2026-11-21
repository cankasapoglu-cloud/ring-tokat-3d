#!/usr/bin/env python3
"""yeni7 vokali: ilk kaydın (v2_2) ayrılmış doğal vokali BOŞLUKSUZ düzene yerleştirilir ve Old MacDonald ezgisine çekilir.

Kıta (26 vuruş): ö0 satır 1 | ö1 satır 2 | ö2 iki gerçek hayvan sesi (vokal yok) | 2/4 "diye bağırır" | ö4 satır 4 | 2 ölçü ara.
Satır 1 ile satır 2 kaynak kayıtta da art ardadır; "diye bağırır" ile satır 4 de öyle. Yani şarkıcının kendi akışı korunur.

Ezgi, hecenin ZAMANINA göre verilir (orkestranın o anda çaldığı nota), böylece ses ile çalgı aynı anda nota değiştirir:
  satır 1   A-li-Ba-ba = do | nın = sol | bir-çift = la | li-ği-var = sol          (do do do sol, la la sol)
  satır 2/4 çift-li = mi | ğin-de = re | geri kalan heceler = do                     (mi mi re re do)
  "diye bağırır"  di-ye = la | ba-ğı-rır = sol                                       (la la sol)

Perde kaydırma Praat PSOLA (zaman düzlemi) ile yapılır; hecenin doğal titreşimi korunur.
Kullanım: python3 01_vokal.py [--do 67] [--zaman altyapi/zaman_G.json] [--cikti vokal.wav]"""
import argparse, json, os, numpy as np, soundfile as sf, pyworld as pw, parselmouth
from parselmouth.praat import call
D = os.path.dirname(os.path.abspath(__file__)); A = os.path.dirname(D)
ap = argparse.ArgumentParser()
ap.add_argument("--do", type=int, default=67); ap.add_argument("--zaman", default=os.path.join(D, "altyapi", "zaman_G.json"))
ap.add_argument("--cikti", default=os.path.join(D, "vokal.wav")); ap.add_argument("--yalniz-tablo", action="store_true")
P = ap.parse_args()
Y = json.load(open(os.path.join(A, "yeni4", "vokal", "yerlesim.json"), encoding="utf8")); Z = json.load(open(P.zaman, encoding="utf8"))
x, fs = sf.read(os.path.join(A, "yeni4", "vokal", "vokal_dogal.wav")); x = x.astype(np.float64); BEAT = Z["vurus_sn"]
N = int(round(Z["dosya_suresi_sn"] * fs)); FP = 5.0

# ---- yerleşim: her parçanın eski ölçü başı yeni ölçü başına taşınır --------------------------------------------
kayma = {}
for p in Y["pieces"]:
    ob = Z["kitalar"][p["verse"] - 1]["olcu_baslangiclari"]
    yeni = {1: ob[0], 2: ob[1], 3: ob[3] - 2 * BEAT}[p["piece"]]          # P3 "diye" ile başlar: eski ölçünün 2. vuruşu = yeni 2/4 ölçünün başı
    kayma[p["id"]] = int(round((yeni - p["dest_bar_downbeat"]) * fs))

# ---- hedef notalar ------------------------------------------------------------------------------------------------
DESEN = {"L1": [0, 0, 0, 0, -5, -3, -3, -5, -5, -5], "diye": [-3, -3, -5, -5, -5], "L4": [4, 4, 2, 2, 0, 0, 0, 0, 0]}
def zamana_gore(line, t):                                                 # t: ölçü başından (ya da "diye" başından) vuruş cinsinden
    if line == "L1": return 0 if t < 1.5 else (-5 if t < 2 else (-3 if t < 3 else -5))
    if line == "diye": return -3 if t < 1 else -5
    return 4 if t < 1 else (2 if t < 2 else 0)
grup = {}
for s in Y["syllables_flat"]: grup.setdefault((s["verse"], s["line"]), []).append(s)
heceler, uyusmayan = [], []
for (v, line), hs in grup.items():
    hs.sort(key=lambda s: s["index"]); ob = Z["kitalar"][v - 1]["olcu_baslangiclari"]
    bas = {"L1": ob[0], "L2": ob[1], "diye": ob[3], "L4": ob[4]}[line]
    desen = DESEN.get(line) if line != "L2" else [4, 4, 2, 2] + [0] * (len(hs) - 4)
    assert len(desen) == len(hs), (v, line, len(hs))
    for s, iv in zip(hs, desen):
        k = kayma[s["piece"]] / fs; t0, t1 = s["dest_start"] + k, s["dest_end"] + k
        zg = zamana_gore(line, (t0 + 0.3 * (t1 - t0) - bas) / BEAT)
        if zg != iv: uyusmayan.append((v, line, s["text"], round((t0 - bas) / BEAT, 2), iv, zg))
        heceler.append({"kita": v, "satir": line, "hece": s["text"], "parca": s["piece"], "t0": round(t0, 4), "t1": round(t1, 4),
                        "ozgun_midi": s["midi"], "hedef_midi": P.do + iv, "kayma_yarim_ses": round(P.do + iv - s["midi"], 2)})
print("hece %d; dizilişle zaman kuralı uyuşmayan: %d %s" % (len(heceler), len(uyusmayan), uyusmayan[:8]))
for do in range(62, 70):
    k = np.array([do - P.do + h["kayma_yarim_ses"] for h in heceler]); w = np.array([h["t1"] - h["t0"] for h in heceler])
    print("  do=%d: ağırlıklı ort |kayma| %.2f, en çok %.1f, 5 yarım sesten fazla hece %d%s" % (do, (np.abs(k) * w).sum() / w.sum(), np.abs(k).max(), (np.abs(k) > 5).sum(), "   <-- seçilen" if do == P.do else ""))
if P.yalniz_tablo: raise SystemExit

# ---- PSOLA: her parça kendi tamponunda işlenir (komşu parçalar birbirine karışmasın) -----------------------------
cikti = np.zeros(N); sapma = []; dolgu = int(0.06 * fs)
for p in Y["pieces"]:
    ham = x[p["dest_in_sample"]:p["dest_out_sample"]]; seg = np.concatenate([np.zeros(dolgu), ham, np.zeros(dolgu)])
    a = p["dest_in_sample"] + kayma[p["id"]] - dolgu                      # tamponun yeni zaman çizgisindeki ilk örneği
    f0, t = pw.harvest(seg, fs, f0_floor=150, f0_ceil=720, frame_period=FP); f0 = pw.stonemask(seg, f0, t, fs)
    ta = t + a / fs; sesli = f0 > 0; lf = np.where(sesli, np.log2(np.maximum(f0, 1e-6)), np.nan)
    w = int(0.12 / (FP / 1000)) | 1; yavas = lf.copy()
    for i in np.where(sesli)[0]: yavas[i] = np.nanmedian(lf[max(0, i - w // 2):i + w // 2 + 1])
    hizli = np.clip(np.nan_to_num(lf - yavas), -0.5 / 12, 0.5 / 12)      # doğal titreşim (en çok yarım ses) korunur
    hs = [h for h in heceler if h["parca"] == p["id"]]; basamak = np.full(len(f0), np.nan)
    for h in hs:
        m = (ta >= h["t0"]) & (ta < h["t1"]); basamak[m] = np.log2(440.0 * 2 ** ((h["hedef_midi"] - 69) / 12))
    idx = np.where(~np.isnan(basamak))[0]; basamak = np.interp(np.arange(len(basamak)), idx, basamak[idx])
    cek = np.hanning(11); cek /= cek.sum(); basamak = np.convolve(np.pad(basamak, 5, "edge"), cek, "valid")
    hedef = 2 ** (basamak + hizli)
    snd = parselmouth.Sound(seg, sampling_frequency=fs)
    man = call(snd, "To Manipulation", 0.005, 150, 720)
    pt = call(man, "Extract pitch tier"); call(pt, "Remove points between", 0, snd.duration)
    for i in range(len(t)): call(pt, "Add point", float(t[i]), float(hedef[i]))          # sessiz sayılan karelerde de hedef verilir (kısa ünlüler komşu hecenin notasına kaymasın)
    call([pt, man], "Replace pitch tier")
    y = call(man, "Get resynthesis (overlap-add)").values[0]; y = np.pad(y, (0, max(0, len(seg) - len(y))))[:len(seg)]
    y *= np.sqrt(np.mean(seg ** 2) / (np.mean(y ** 2) + 1e-12))
    cikti[a:a + len(y)] += y
    pr = parselmouth.Sound(y, sampling_frequency=fs).to_pitch_ac(time_step=0.005, pitch_floor=150, pitch_ceiling=720); f1 = pr.selected_array["frequency"]; t1 = pr.xs() + a / fs
    for h in hs:
        m = (t1 >= h["t0"]) & (t1 < h["t1"]) & (f1 > 0)
        if m.sum() > 3: h["olculen_sent"] = round(float((69 + 12 * np.log2(np.median(f1[m]) / 440) - h["hedef_midi"]) * 100), 1); sapma.append(abs(h["olculen_sent"]))
tepe = np.abs(cikti).max(); cikti *= 10 ** (-3 / 20) / tepe
sf.write(P.cikti, cikti, fs, subtype="PCM_24")
json.dump({"do": P.do, "vurus_sn": BEAT, "heceler": heceler}, open(os.path.join(D, "heceler.json"), "w", encoding="utf8"), ensure_ascii=False, indent=0)
e = np.array(sapma); print("%s | hedeften |sapma|: ortanca %.0f, %%90 %.0f, en çok %.0f sent; 50 sentten fazla %d / %d hece" % (os.path.basename(P.cikti), np.median(e), np.percentile(e, 90), e.max(), (e > 50).sum(), len(e)))
