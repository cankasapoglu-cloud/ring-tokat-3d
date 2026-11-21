#!/usr/bin/env python3
"""Ortak yollar ve yardımcılar (perde / armoni / ses niteliği teşhisi). Hiçbir mevcut dosyayı değiştirmez; yalnız okur.
Ara dosyalar yalnız bu klasörün altındaki ara/ içine yazılır."""
import json, os, numpy as np, soundfile as sf
from scipy import signal

D = os.path.dirname(os.path.abspath(__file__))
A = os.path.abspath(os.path.join(D, "..", "..", ".."))          # ali-baba
KOK = os.path.dirname(A)                                         # cocuk-kanali
ARA = os.path.join(D, "ara"); os.makedirs(ARA, exist_ok=True)
SEP = "/tmp/claude-0/-home-user-ring-tokat-3d/bd9d6832-1bf0-57ca-8544-ce6f4befd453/scratchpad/sep/out_mdx"

RED_MP3 = os.path.join(A, "yeni6", "sarki_A_ozgun_ses.mp3")
RED_VOK = os.path.join(A, "yeni6", "vokal_psola.wav")            # perdesi kaydırılmış vokal (reddedilen karışımdaki)
DOGAL_VOK = os.path.join(A, "yeni4", "vokal", "vokal_dogal.wav")  # aynı yerleşim, perde işlemi YOK
RED_BAND = os.path.join(A, "yeni4", "altyapi", "altyapi_G.wav")
RED_EZGI = os.path.join(A, "yeni4", "altyapi", "ezgi_alti_G.wav")
ZAMAN = os.path.join(A, "yeni4", "altyapi", "zaman_G.json")
YERLESIM = os.path.join(A, "yeni4", "vokal", "yerlesim.json")
HEDEF = os.path.join(A, "yeni6", "hedefler.json")
REF_MP3 = os.path.join(A, "v2_2.mp3")
REF_VOK = os.path.join(SEP, "v2_2_(Vocals)_UVR-MDX-NET-Voc_FT.wav")
REF_ENS = os.path.join(SEP, "v2_2_(Instrumental)_UVR-MDX-NET-Voc_FT.wav")

FS = 44100
ON = 0.100                       # reddedilen karışımda orkestranın başına eklenen sessizlik (vokalde zaten var)
VURUS = 60.0 / 105.0
OLCU = 4 * VURUS
NOTA = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
AKOR = {"G": {7, 11, 2}, "C": {0, 4, 7}, "D7": {2, 6, 9, 0}}


def ad(m):
    m = int(round(m)); return "%s%d" % (NOTA[m % 12], m // 12 - 1)


def hz2midi(f):
    return 69 + 12 * np.log2(np.asarray(f, float) / 440.0)


def oku_mono(yol, fs=FS):
    x, f = sf.read(yol, always_2d=True); x = x.mean(axis=1)
    if f != fs: x = signal.resample_poly(x, fs, f)
    return x.astype(np.float64)


def f0_izi(yol, ad_, taban=150, tavan=720, adim=0.005):
    """Praat (özilinti) ile f0 izi; ara/ içine saklanır. Döner: t (s), f0 (Hz, sessiz = 0)."""
    import parselmouth
    onb = os.path.join(ARA, "f0_%s.npz" % ad_)
    if os.path.exists(onb):
        z = np.load(onb); return z["t"], z["f0"]
    x = oku_mono(yol)
    p = parselmouth.Sound(x, sampling_frequency=FS).to_pitch_ac(time_step=adim, pitch_floor=taban, pitch_ceiling=tavan)
    t = p.xs(); f0 = p.selected_array["frequency"]
    np.savez(onb, t=t, f0=f0); return t, f0


def hece_perdesi(t, f0, bas, bit, orta=0.6):
    """Hecenin sesli karelerinin orta %60'ının ortancası (MIDI) ve sesli kare sayısı."""
    m = (t >= bas) & (t < bit) & (f0 > 0); k = f0[m]
    if len(k) < 4: return np.nan, int(len(k))
    a = int(len(k) * (1 - orta) / 2); c = k[a:len(k) - a] if len(k) - 2 * a >= 3 else k
    return float(np.median(hz2midi(c))), int(len(k))


def yukle():
    Y = json.load(open(YERLESIM, encoding="utf8")); H = json.load(open(HEDEF, encoding="utf8")); Z = json.load(open(ZAMAN, encoding="utf8"))
    S = Y["syllables_flat"]
    for s, h in zip(S, H):
        assert (s["verse"], s["line"], s["index"]) == (h["verse"], h["line"], h["index"]); s["hedef"] = h["hedef_midi"]
    return Y, S, Z
