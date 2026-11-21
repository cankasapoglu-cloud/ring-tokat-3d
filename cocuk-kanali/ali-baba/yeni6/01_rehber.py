#!/usr/bin/env python3
"""Rehber vokal: ilk kaydın ayrılmış ve yerleştirilmiş sesi (yeni4/vokal/vokal_dogal.wav) zamanlaması değişmeden,
yalnızca perdesi kaydırılarak Old MacDonald ezgisine (Sol majör, do = G4) çekilir (WORLD). Bu rehber, ElevenLabs'te
şarkıcının ses kopyasına yeniden söyletilecek; o yüzden burada önemli olan doğru nota ve temiz geçişlerdir.
Hece -> nota: 1. dize: do x5, sol(alt), la(alt) x3, sol(alt).  2. dize: do x4, sol(alt), ..., la(alt), "var" sol(alt).
"diye bağırır": do x5.  4. dize: do x4, sol(alt), la(alt) x3, sol(alt)."""
import json, os, numpy as np, soundfile as sf, pyworld as pw
D = os.path.dirname(os.path.abspath(__file__)); A = os.path.dirname(D)
Y = json.load(open(os.path.join(A, "yeni4", "vokal", "yerlesim.json"), encoding="utf8"))
x, fs = sf.read(os.path.join(A, "yeni4", "vokal", "vokal_dogal.wav")); x = x.astype(np.float64)
DO, SOL, LA = 67, 62, 64; FP = 5.0
heceler = Y["syllables_flat"]
def hedef(h, satir):
    i, n = h["index"], len(satir)
    if h["line"] == "L1": return [DO] * 5 + [SOL] + [LA] * 3 + [SOL] if n != 10 else ([DO] * 5 + [SOL] + [LA] * 3 + [SOL])[i]
    if h["line"] == "diye": return DO
    if i < 4: return DO                       # çift-li-ğin-de
    if i == 4: return SOL
    if i == n - 1: return SOL                 # "var" / "nın"
    return LA
satirlar = {}
for h in heceler: satirlar.setdefault((h["verse"], h["line"]), []).append(h)
for (v, l), s in satirlar.items():
    for h in s:
        t = hedef(h, s); h["hedef"] = t if not isinstance(t, list) else t[h["index"]]
    assert l != "L1" or len(s) == 10, (v, l, len(s))
cikti = np.zeros_like(x); tablo = []
for p in Y["pieces"]:
    a, b = int((p["dest_in"] - 0.06) * fs), int((p["dest_out"] + 0.06) * fs)
    seg = x[a:b]
    f0, t = pw.harvest(seg, fs, f0_floor=150, f0_ceil=720, frame_period=FP)
    f0 = pw.stonemask(seg, f0, t, fs); sp = pw.cheaptrick(seg, f0, t, fs); ap = pw.d4c(seg, f0, t, fs)
    ta = t + a / fs; sesli = f0 > 0
    lf = np.where(sesli, np.log2(np.maximum(f0, 1e-6)), np.nan)
    # yavaş ezgi hareketini çıkar (120 ms'lik kayan ortanca), hızlı doğal titreşimi koru
    w = int(0.12 / (FP / 1000)) | 1; yavas = lf.copy()
    for i in np.where(sesli)[0]:
        k = lf[max(0, i - w // 2):i + w // 2 + 1]; yavas[i] = np.nanmedian(k)
    hizli = np.nan_to_num(lf - yavas); hizli = np.clip(hizli, -0.5 / 12, 0.5 / 12)
    hs = [h for h in heceler if h["piece"] == p["id"]]
    basamak = np.full(len(f0), np.nan)
    for h in hs:
        m = (ta >= h["dest_start"]) & (ta < h["dest_end"]); basamak[m] = np.log2(440.0 * 2 ** ((h["hedef"] - 69) / 12))
    # hece dışı kareleri en yakın hece değeriyle doldur, sonra 50 ms'lik yumuşak geçiş
    idx = np.where(~np.isnan(basamak))[0]; basamak = np.interp(np.arange(len(basamak)), idx, basamak[idx])
    cek = np.hanning(11); cek /= cek.sum(); basamak = np.convolve(np.pad(basamak, 5, "edge"), cek, "valid")
    f0y = np.where(sesli, 2 ** (basamak + hizli), 0.0)
    y = pw.synthesize(f0y, sp, ap, fs, FP)[:len(seg)]
    y *= np.sqrt(np.mean(seg ** 2) / (np.mean(y ** 2) + 1e-12))
    r = int(0.02 * fs); y[:r] *= np.linspace(0, 1, r); y[-r:] *= np.linspace(1, 0, r)
    cikti[a:a + len(y)] += y
    for h in hs:
        m = (ta >= h["dest_start"]) & (ta < h["dest_end"]) & sesli
        if m.sum() > 3: tablo.append((h["verse"], h["line"], h["text"], h["midi"], h["hedef"], 69 + 12 * np.log2(np.median(f0y[m]) / 440)))
sf.write(os.path.join(D, "rehber.wav"), cikti, fs, subtype="PCM_24")
json.dump([{"verse": h["verse"], "line": h["line"], "index": h["index"], "text": h["text"], "piece": h["piece"], "dest_start": h["dest_start"], "dest_end": h["dest_end"],
            "ozgun_midi": h["midi"], "hedef_midi": h["hedef"]} for h in heceler], open(os.path.join(D, "hedefler.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
kay = np.array([abs(t[3] - t[4]) for t in tablo if t[3]]); sap = np.array([abs(t[5] - t[4]) * 100 for t in tablo])
print("hece %d | uygulanan kaydırma: ortalama %.1f, %%90 %.1f, en çok %.1f yarım ses | rehberde hedeften sapma: ortanca %.0f, en çok %.0f sent" % (len(tablo), kay.mean(), np.percentile(kay, 90), kay.max(), np.median(sap), sap.max()))
for t in tablo[:10] + tablo[19:24]: print("  K%d %-4s %-5s özgün %.1f -> hedef %d (rehber %.2f)" % t)
