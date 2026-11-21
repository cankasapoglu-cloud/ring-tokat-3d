"""Arastirma-2 prototip: vokal, altyapi ile AKORTLU mu? (hazir bir acik kaynak olcut yok; isaret islemeyle kuruldu)
Girdi: vokal kanali + altyapi (ayni zaman ekseni). Cikti: sayilar + PNG (Claude PNG'ye bakabilir).
 1) Vokal perdesi: SwiftF0 (ONNX, paket ici).   2) Altyapinin tonu ve akort frekansi: essentia.
 3) cent sapmasi: sabit (tutulan) notalarda vokalin, altyapinin akort izgarasina uzakligi.
 4) gam ici orani: tutulan nota suresinin ne kadari altyapinin gamindaki seslerde (Hsieh ve ark. 2025 fikri).
 5) armonik destek: vokalin soyledigi ses sinifinda altyapi kromasi ne kadar guclu; ayni olcu vokal +1/-1 yarim ses
    kaydirilmis gibi hesaplanir -> fark buyukse vokal altyapiyla uyumlu (kendi kendini kalibre eden karsilastirma).
Sinirlar: 'guzel soyluyor mu' demez; sadece perde-ton tutarliligini olcer. Kayan/suslu sesler elenir."""
import sys, os, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf, librosa
import essentia; essentia.log.infoActive = False; essentia.log.warningActive = False
import essentia.standard as es
from swift_f0 import SwiftF0
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

MAJ = [0, 2, 4, 5, 7, 9, 11]; MIN = [0, 2, 3, 5, 7, 8, 10]; NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ALIAS = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}

def analyse(voc, bak, sr, shift_cents=0.0, label="", png=None):
    hop = 256                                                     # 16 kHz'de 16 ms (SwiftF0 cercevesi)
    v16 = librosa.resample(voc, orig_sr=sr, target_sr=16000)
    r = SwiftF0(threads=2).detect(v16, 16000, fmin=80, fmax=1000)
    f0 = np.asarray(r.pitch_hz, float) * 2 ** (shift_cents / 1200); conf = np.asarray(r.confidence); tt = np.asarray(r.timestamps)
    key, scale, kstr = es.KeyExtractor(profileType="edma")(bak.astype(np.float32))
    tune = float(librosa.estimate_tuning(y=bak, sr=sr)) * 100     # altyapinin 440 Hz izgarasindan sapmasi (cent)
    midi = librosa.hz_to_midi(np.where(f0 > 0, f0, 1.0)) - tune / 100
    voiced = (conf > 0.9) & (f0 > 0)
    d = np.abs(np.gradient(midi)); stable = voiced & (d < 0.25)   # tutulan nota: perde hizi < 0.25 yarim ses/cerceve
    dev = (midi - np.round(midi)) * 100
    pc = np.mod(np.round(midi).astype(int), 12)
    tonic = NAMES.index(ALIAS.get(key, key)); sc = {(tonic + i) % 12 for i in (MAJ if scale == "major" else MIN)}
    in_scale = np.isin(pc[stable], list(sc)).mean() if stable.any() else float("nan")
    C = librosa.feature.chroma_cqt(y=bak, sr=sr, hop_length=512, tuning=tune / 100); C = C / (C.max(0, keepdims=True) + 1e-9)
    ci = np.clip((tt * sr / 512).astype(int), 0, C.shape[1] - 1)
    def support(k): return float(C[(pc[stable] + k) % 12, ci[stable]].mean()) if stable.any() else float("nan")
    s0, sp, sm = support(0), support(1), support(-1)
    res = dict(etiket=label, altyapi_ton=f"{key} {scale}", ton_guveni=round(float(kstr), 2), altyapi_akort_cent=round(tune, 1),
               sesli_orani=round(float(voiced.mean()), 2), tutulan_nota_orani=round(float(stable.mean()), 2),
               cent_sapma_medyan=round(float(np.median(np.abs(dev[stable]))), 1), cent_sapma_ortalama_isaretli=round(float(np.mean(dev[stable])), 1),
               yuzde_25cent_icinde=round(float((np.abs(dev[stable]) < 25).mean() * 100), 1), gam_ici_orani=round(float(in_scale), 3),
               armonik_destek=round(s0, 3), destek_plus1=round(sp, 3), destek_minus1=round(sm, 3), destek_farki=round(s0 - (sp + sm) / 2, 3))
    if png:
        fig, ax = plt.subplots(3, 1, figsize=(14, 9), gridspec_kw=dict(height_ratios=[3, 2, 1.4]))
        T = len(bak) / sr
        ax[0].imshow(C, origin="lower", aspect="auto", extent=[0, T, -0.5, 11.5], cmap="Greys", vmin=0, vmax=1)
        ax[0].scatter(tt[stable], pc[stable] + dev[stable] / 100, s=5, c=np.where(np.isin(pc[stable], list(sc)), "tab:green", "tab:red"), label="vokal (yesil: gam ici, kirmizi: gam disi)")
        ax[0].set_yticks(range(12)); ax[0].set_yticklabels(NAMES); ax[0].set_title(f"{label}: altyapi kromasi (gri) + vokal ses sinifi | altyapi tonu {key} {scale}"); ax[0].legend(loc="upper right", fontsize=8)
        ax[1].axhspan(-25, 25, color="tab:green", alpha=0.12); ax[1].scatter(tt[stable], dev[stable], s=4, c="tab:blue"); ax[1].axhline(0, c="k", lw=0.5)
        ax[1].set_ylim(-50, 50); ax[1].set_xlim(0, T); ax[1].set_ylabel("cent sapma"); ax[1].set_title("tutulan notalarda en yakin notaya uzaklik (yesil bant: +-25 cent)")
        ax[2].hist(dev[stable], bins=np.arange(-50, 51, 5), color="tab:blue"); ax[2].set_xlabel("cent"); ax[2].set_title(f"medyan |sapma|={res['cent_sapma_medyan']} cent, gam ici=%{100*in_scale:.0f}, armonik destek farki={res['destek_farki']}")
        fig.tight_layout(); fig.savefig(png, dpi=80); plt.close(fig)
    return res

if __name__ == "__main__":
    vf, bf = sys.argv[1], sys.argv[2]; out = sys.argv[3] if len(sys.argv) > 3 else "/tmp/dinleme-a2/akort"
    t0, dur = float(os.environ.get("BAS", 20)), float(os.environ.get("SURE", 60))
    voc, sr = librosa.load(vf, sr=22050, mono=True, offset=t0, duration=dur); bak, _ = librosa.load(bf, sr=22050, mono=True, offset=t0, duration=dur)
    n = min(len(voc), len(bak)); voc, bak = voc[:n], bak[:n]; os.makedirs(out, exist_ok=True)
    import time
    rows = []
    for lab, sh in [("gercek", 0), ("kontrol +50 cent", 50), ("kontrol +100 cent (yarim ses)", 100), ("kontrol -30 cent", -30)]:
        t = time.time(); r = analyse(voc, bak, sr, sh, lab, png=os.path.join(out, f"akort_{sh:+d}.png") if sh in (0, 50) else None); r["sure_sn"] = round(time.time() - t, 1); rows.append(r)
    print(json.dumps(rows, ensure_ascii=False, indent=1))
