#!/usr/bin/env python3
"""dinle_panel.py - Claude'un BAKARAK okuyacagi PNG panolari (1600 piksel genislik, panel basina en cok ~30 sn).

  genel_bakis()    butun dosya tek resimde: spektrogram, duzeyler, hareketlilik, sorun cizelgesi, vokal kalite tahminleri
  pano()           30 sn'lik dilim: karisim spektrogrami + sozcukler, vokal spektrogrami, vurus gucu + vuruslar, duzeyler
  perde_panosu()   30 sn'lik dilim: vokal perde egrisi akor seslerinin ustunde (nota adli eksen), cent sapmasi, ritim, kroma

Tasarim kurallari: her panelde TEK dusey eksen; eksenler saniye ve nota adi / Hz / dB ile etiketli; en az iki dizi varsa
gosterge (lejant) var; renk tek basina anlam tasimaz (sekil / tarama / yazi ile ikilenir); yazilar murekkep renginde.
Bu resimler kulak degildir: NE ZAMAN NE OLDUGUNU, perdeyi, ritmi, duzeyi gosterir; sesin guzel/dogal oldugunu gostermez.
"""
import os, math, warnings

warnings.filterwarnings("ignore")
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D
import librosa

SR, HOP = 22050, 512
ADLAR = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
YUZEY, INK, INK2, IZGARA = "#fcfcfb", "#0b0b0b", "#52514e", "#c3c2b7"
MAVI, TURUNCU, AQUA = "#2a78d6", "#eb6834", "#1baf7a"          # dizi renkleri: vokal, altyapi, ucuncu
IYI, UYARI, KRITIK = "#0ca30c", "#fab219", "#d03b3b"            # durum renkleri (hep sekil/tarama + yaziyla birlikte)
AKOR_ZEMIN, AKOR_KOK = "#cde2fb", "#9ec5f4"
GENISLIK = 16.0                                                # inc; dpi=100 -> 1600 piksel


def _stil():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "text.color": INK, "axes.labelcolor": INK,
                         "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": IZGARA, "axes.facecolor": YUZEY,
                         "figure.facecolor": YUZEY, "savefig.facecolor": YUZEY, "axes.titlesize": 11, "axes.titleweight": "bold",
                         "axes.titlelocation": "left", "legend.fontsize": 9, "legend.frameon": True, "legend.facecolor": YUZEY,
                         "legend.edgecolor": IZGARA, "axes.grid": False})


def _sade(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def _zaman_ekseni(ax, t0, t1, etiket=True):
    span = t1 - t0
    adim = 1.0 if span <= 36 else 2.0 if span <= 70 else 5.0 if span <= 200 else 10.0 if span <= 400 else 30.0
    ax.set_xlim(t0, t1)
    tk = np.arange(math.ceil(t0 / adim) * adim, t1 + 1e-6, adim)
    ax.set_xticks(tk)
    if etiket:
        ax.set_xticklabels([("%d" % v) for v in tk], fontsize=9)
        ax.set_xlabel("zaman (sn)")
    else:
        ax.set_xticklabels([])
    if span <= 36:
        ax.set_xticks(np.arange(math.ceil(t0 * 2) / 2, t1 + 1e-6, 0.5), minor=True)


def _vuruslar(ax, vurus, t0, t1, renk=IZGARA, lw=0.6):
    if vurus is None:
        return
    for b in vurus[(vurus >= t0) & (vurus <= t1)]:
        ax.axvline(b, color=renk, lw=lw, ls=(0, (2, 3)), zorder=1)


def _mel_ciz(ax, mel_db, t0, t1, fmin=40, fmax=11000, vmin=-70, hop=HOP, seyrek=False):
    n_mel, n = mel_db.shape
    a, b = int(max(0, t0 * SR / hop)), int(min(n, math.ceil(t1 * SR / hop)))
    M = mel_db[:, a:b] - mel_db.max()
    ax.imshow(M, origin="lower", aspect="auto", cmap="Greys", vmin=vmin, vmax=0, extent=[a * hop / SR, b * hop / SR, 0, n_mel],
              interpolation="nearest")
    mf = librosa.mel_frequencies(n_mels=n_mel, fmin=fmin, fmax=fmax)
    tik = [f for f in ((100, 400, 1600, 6400) if seyrek else (200, 400, 800, 1600, 3200, 6400)) if fmin <= f <= fmax]
    ax.set_yticks([np.interp(f, mf, np.arange(n_mel)) for f in tik])
    ax.set_yticklabels([("%d Hz" % f) if f < 1000 else ("%g kHz" % (f / 1000)) for f in tik], fontsize=9)
    ax.set_ylim(0, n_mel)


def _sozcukler(ax, veri, t0, t1, y_ust, satir_yuksekligi, yanlis_zamanlar=None):
    """Scribe sozcuklerini eksenin ustune yazar (3 satir kaydirmali). Yanlis sozcukler kirmizi cerceveli ve '≠' isaretli."""
    soz = veri.get("sozcukler") or []
    olay = veri.get("ses_olaylari") or []
    yz = set(round(z, 2) for z in (yanlis_zamanlar or []))
    k = 0
    for w in soz:
        if not (t0 <= w["bas"] <= t1):
            continue
        hatali = round(w["bas"], 2) in yz
        ax.axvline(w["bas"], color=KRITIK if hatali else MAVI, lw=0.9, alpha=0.9, ymin=0.93, ymax=1.0)
        ax.text(w["bas"], y_ust + satir_yuksekligi * (0.15 + (k % 3)), ("≠ " if hatali else "") + w["metin"], fontsize=9, color=INK, ha="left",
                va="bottom", clip_on=False, bbox=dict(boxstyle="round,pad=0.12", fc=YUZEY, ec=KRITIK, lw=1.0) if hatali else None)
        k += 1
    for w in olay:
        if w["son"] < t0 or w["bas"] > t1:
            continue
        ax.axvspan(max(t0, w["bas"]), min(t1, w["son"]), ymin=0.96, ymax=1.0, color=TURUNCU, alpha=0.8, lw=0)
        ax.text(max(t0, w["bas"]) + (t1 - t0) * 0.003, y_ust * 0.945, w["metin"], fontsize=9, color=INK, ha="left", va="top", style="italic",
                bbox=dict(boxstyle="round,pad=0.15", fc=YUZEY, ec=TURUNCU, lw=0.9))


# ----------------------------------------------------------------------------------------------------------
def genel_bakis(veri, yol):
    """Butun dosyanin tek resmi."""
    _stil()
    sure = veri["sure"]
    satirlar = [("mel", 3.2), ("duzey", 1.5), ("enerji", 1.2)]
    if veri.get("cosku_zaman"):
        satirlar.append(("cosku", 1.0))
    satirlar.append(("serit", 2.3))
    if veri.get("mos"):
        satirlar.append(("mos", 1.5))
    H = sum(h for _, h in satirlar) + 1.3
    fig, axs = plt.subplots(len(satirlar), 1, figsize=(GENISLIK, H), dpi=100,
                            gridspec_kw={"height_ratios": [h for _, h in satirlar], "hspace": 0.42})
    ax = dict(zip([a for a, _ in satirlar], np.atleast_1d(axs)))
    # 1) spektrogram
    _mel_ciz(ax["mel"], veri["mel_db"], 0, sure, seyrek=True)
    ax["mel"].set_title("Karışımın spektrogramı (koyu = güçlü). Dikey kesik çizgiler: ayrıntı panolarının (dilimlerin) sınırları")
    ax["mel"].set_ylabel("frekans")
    for s in veri.get("dilimler", [])[1:]:
        ax["mel"].axvline(s[0], color=INK, lw=1.0, ls=(0, (4, 3)))
    for i, s in enumerate(veri.get("dilimler", [])):
        ax["mel"].text(s[0] + sure * 0.004, veri["mel_db"].shape[0] * 0.97, "dilim %d: %d-%d sn" % (i + 1, s[0], round(s[1])), ha="left", va="top", fontsize=9,
                       color=INK, bbox=dict(boxstyle="round,pad=0.2", fc=YUZEY, ec=INK2, lw=0.7))
    # 2) duzey
    a = ax["duzey"]
    t = librosa.times_like(veri["rms_db"], sr=SR, hop_length=HOP)
    w = max(1, int(0.5 * SR / HOP))
    duz = np.convolve(veri["rms_db"], np.ones(w) / w, "same")
    a.plot(t, duz, color=INK, lw=1.4, label="karışım")
    if veri.get("duzey"):
        d = veri["duzey"]
        a.plot(d["t"], d["vdb"], color=MAVI, lw=1.4, label="vokal kanalı")
        a.plot(d["t"], d["adb"], color=TURUNCU, lw=1.4, label="altyapı kanalı")
        a.legend(loc="lower right", ncol=3)
    a.set_ylim(-60, 0)
    a.set_yticks([-60, -40, -20, 0])
    a.set_ylabel("düzey (dBFS)")
    a.set_title("Ses düzeyi (0,5 sn ortalama)")
    a.grid(axis="y", color=IZGARA, lw=0.5)
    # 3) hareketlilik
    a = ax["enerji"]
    bol = veri.get("bolumler_5sn") or []
    if bol:
        a.bar([b["bas"] + 2.5 for b in bol], [b["olay_sn"] for b in bol], width=4.6, color=MAVI, lw=0)
        for b in bol:
            a.text(b["bas"] + 2.5, b["olay_sn"], "%.1f" % b["olay_sn"], ha="center", va="bottom", fontsize=8, color=INK2)
        a.set_ylim(0, max(1.0, max(b["olay_sn"] for b in bol) * 1.3))
    a.set_ylabel("olay / sn")
    a.set_title("Hareketlilik: 5 sn'lik bölümlerde saniyedeki vuruş-olay sayısı (karışım)")
    # 3b) cosku (MusicCoCa)
    if "cosku" in ax:
        a = ax["cosku"]
        cz = veri["cosku_zaman"]
        v = [c["fark"] or 0 for c in cz]
        a.bar([c["bas"] + 5 for c in cz], v, width=9.4, color=[MAVI if x >= 0 else KRITIK for x in v], lw=0)
        for c, x in zip(cz, v):
            a.text(c["bas"] + 5, x, "%+.2f" % x, ha="center", va="bottom" if x >= 0 else "top", fontsize=8, color=INK2)
        a.axhline(0, color=INK2, lw=0.8)
        m = max(0.12, max(abs(x) for x in v) * 1.4)
        a.set_ylim(-m, m)
        a.set_ylabel("fark")
        a.set_title("MusicCoCa: 'coşkulu çocuk şarkısı' − 'yavaş ninni' benzerlik farkı, 10 sn'lik pencereler (artı = coşkulu yana yakın)")
    # 4) serit / sorun cizelgesi
    a = ax["serit"]
    siralar = ["ton (altyapı)", "vokal var", "ses olayı (Scribe)", "söz hatası", "çakışan / detone nota", "gömük vokal", "donmuş ünlü", "kırpılma / sessizlik"]
    yk = {ad: len(siralar) - 1 - i for i, ad in enumerate(siralar)}
    for ad, y in yk.items():
        a.axhline(y, color=IZGARA, lw=0.5, zorder=0)
    for tp in veri.get("tonlar") or []:
        y = yk["ton (altyapı)"]
        a.add_patch(Rectangle((tp["bas"], y - 0.32), tp["son"] - tp["bas"], 0.64, fc=AKOR_ZEMIN, ec=INK2, lw=0.8))
        a.text((tp["bas"] + tp["son"]) / 2, y, tp["ton"] + (" (belirsiz)" if tp.get("belirsiz") else ""), ha="center", va="center", fontsize=9)
    for b in veri.get("vokal_bolumleri") or []:
        a.add_patch(Rectangle((b["bas"], yk["vokal var"] - 0.28), b["son"] - b["bas"], 0.56, fc=MAVI, ec="none"))
    for w in veri.get("ses_olaylari") or []:
        a.add_patch(Rectangle((w["bas"], yk["ses olayı (Scribe)"] - 0.3), max(0.3, w["son"] - w["bas"]), 0.6, fc="#f6c9b6", ec=TURUNCU, lw=0.8))
        a.text(w["bas"] + sure * 0.002, yk["ses olayı (Scribe)"], w["metin"].strip("[]()"), fontsize=8, va="center", ha="left", color=INK, clip_on=True)
    for s in veri.get("sorunlar") or []:
        if s["sira"] not in yk:
            continue
        y = yk[s["sira"]]
        if s.get("son") and s["son"] - s["zaman"] > 0.4:
            a.add_patch(Rectangle((s["zaman"], y - 0.28), s["son"] - s["zaman"], 0.56, fc=KRITIK, ec="none", alpha=0.85))
        else:
            a.plot([s["zaman"]], [y], marker="X", ms=8, color=KRITIK, mec=YUZEY, mew=0.6, ls="none")
    a.set_yticks(list(yk.values()))
    a.set_yticklabels(list(yk.keys()), fontsize=9)
    a.set_ylim(-0.6, len(siralar) - 0.4)
    a.set_title("Zaman çizelgesi: ton, vokalli yerler ve bulunan sorunlar (kırmızı X / kırmızı şerit = sorun; boş satır = sorun bulunmadı)")
    # 5) mos
    if "mos" in ax:
        a = ax["mos"]
        m = veri["mos"]
        tb = np.array(m.get("pencere_baslangiclari") or []) + 5.0
        diziler = [("dnsmos", "DNSMOS", MAVI, "o"), ("nisqa", "NISQA", TURUNCU, "s"), ("distillmos", "Distill-MOS", AQUA, "^"), ("utmos22", "UTMOS22", INK2, "D")]
        for anahtar, ad, renk, isaret in diziler:
            p = (m.get(anahtar) or {}).get("pencereler_genel")
            if p and len(p) == len(tb):
                a.plot(tb, p, color=renk, lw=1.6, marker=isaret, ms=6, mec=YUZEY, mew=0.8, label=ad)
        a.set_ylim(1, 5)
        a.set_yticks([1, 2, 3, 4, 5])
        a.set_ylabel("tahmin (1-5)")
        a.grid(axis="y", color=IZGARA, lw=0.5)
        a.legend(loc="upper left", ncol=4)
        a.set_title("Vokal kanalında konuşma-kalitesi tahminleri, 10 sn'lik pencereler (şarkı için eğitilmediler: yalnızca ani düşüşlere bakın)")
    for ad, a in ax.items():
        _zaman_ekseni(a, 0, sure, etiket=(ad == satirlar[-1][0]))
        if ad != "mel":
            _sade(a)
    fig.suptitle(veri["baslik"], x=0.012, ha="left", fontsize=13, fontweight="bold", y=0.995)
    fig.subplots_adjust(left=0.115, right=0.955, top=1 - 0.62 / H, bottom=0.55 / H)
    fig.savefig(yol)
    plt.close(fig)
    return yol


# ----------------------------------------------------------------------------------------------------------
def pano(veri, t0, t1, yol, no=1):
    """30 sn'lik genel pano: karisim spektrogrami + sozcukler, vokal spektrogrami (varsa), vurus gucu, duzey."""
    _stil()
    vokal_var = veri.get("vokal_mel") is not None
    satirlar = [("mel", 4.3)] + ([("vmel", 2.6)] if vokal_var else []) + [("vurus", 1.3), ("duzey", 1.4)]
    H = sum(h for _, h in satirlar) + 1.5
    fig, axs = plt.subplots(len(satirlar), 1, figsize=(GENISLIK, H), dpi=100, gridspec_kw={"height_ratios": [h for _, h in satirlar], "hspace": 0.34})
    ax = dict(zip([a for a, _ in satirlar], np.atleast_1d(axs)))
    a = ax["mel"]
    _mel_ciz(a, veri["mel_db"], t0, t1)
    a.set_ylabel("frekans")
    _vuruslar(a, veri.get("vurus"), t0, t1, renk="#86b6ef", lw=0.5)
    nm = veri["mel_db"].shape[0]
    _sozcukler(a, veri, t0, t1, nm, nm * 0.055, veri.get("yanlis_zamanlar"))
    bas = "Karışım spektrogramı"
    if veri.get("sozcukler"):
        bas += " + Scribe'in duyduğu sözcükler (mavi çentik = sözcük başı; ≠ kırmızı çerçeve = beklenen sözle uyuşmuyor; turuncu = ses olayı)"
    a.set_title(bas, pad=4 + (46 if veri.get("sozcukler") else 0))
    if vokal_var:
        a = ax["vmel"]
        _mel_ciz(a, veri["vokal_mel"], t0, t1, fmin=80, fmax=8000, vmin=-65, hop=256)
        a.set_ylabel("frekans")
        a.set_title("Vokal kanalının spektrogramı (80 Hz - 8 kHz): yatay çizgiler = tutulan notalar, dikey bulut = ünsüz (s, ş, t, k)")
    a = ax["vurus"]
    oz = librosa.times_like(veri["oenv"], sr=SR, hop_length=HOP)
    m = (oz >= t0) & (oz <= t1)
    a.plot(oz[m], veri["oenv"][m], color=INK, lw=1.2)
    _vuruslar(a, veri.get("vurus"), t0, t1, renk=MAVI, lw=0.9)
    a.set_ylim(0, None)
    a.set_ylabel("vuruş gücü")
    a.set_title("Vuruş gücü (karışım) ve bulunan vuruşlar (mavi kesik çizgi)  |  tempo %s BPM" % veri.get("tempo_yazi", "?"))
    a = ax["duzey"]
    t = librosa.times_like(veri["rms_db"], sr=SR, hop_length=HOP)
    m = (t >= t0) & (t <= t1)
    a.plot(t[m], veri["rms_db"][m], color=INK, lw=1.3, label="karışım")
    if veri.get("duzey"):
        d = veri["duzey"]
        mm = (d["t"] >= t0) & (d["t"] <= t1)
        a.plot(d["t"][mm], d["vdb"][mm], color=MAVI, lw=1.5, label="vokal kanalı")
        a.plot(d["t"][mm], d["adb"][mm], color=TURUNCU, lw=1.5, label="altyapı kanalı")
        a.legend(loc="lower right", ncol=3)
    a.set_ylim(-60, 0)
    a.set_yticks([-60, -40, -20, 0])
    a.grid(axis="y", color=IZGARA, lw=0.5)
    a.set_ylabel("düzey (dBFS)")
    a.set_title("Ses düzeyi")
    for ad, a in ax.items():
        _zaman_ekseni(a, t0, t1, etiket=(ad == satirlar[-1][0]))
        if ad not in ("mel", "vmel"):
            _sade(a)
    fig.suptitle("%s  |  dilim %d: %.0f-%.0f sn  |  GENEL PANO" % (veri["baslik"], no, t0, t1), x=0.012, ha="left", fontsize=13, fontweight="bold", y=0.995)
    fig.subplots_adjust(left=0.065, right=0.99, top=1 - (0.75 + (0.5 if veri.get("sozcukler") else 0)) / H, bottom=0.55 / H)
    fig.savefig(yol)
    plt.close(fig)
    return yol


# ----------------------------------------------------------------------------------------------------------
def perde_panosu(veri, t0, t1, yol, no=1):
    """30 sn'lik perde panosu: vokal perdesi akor seslerinin ustunde, cent sapmasi, ritim, kroma + vokal ses sinifi."""
    _stil()
    p = veri["perde"]
    t, midi, sesli, notalar = p["t"], p["midi"], p["sesli"], p["notalar"]
    ritim_var = veri.get("ritim") is not None and veri["ritim"].get("b") is not None
    kroma_var = veri.get("kroma") is not None
    satirlar = [("rulo", 5.2), ("cent", 1.6)] + ([("ritim", 1.5)] if ritim_var else []) + ([("kroma", 2.0)] if kroma_var else [])
    H = sum(h for _, h in satirlar) + 1.6
    fig, axs = plt.subplots(len(satirlar), 1, figsize=(GENISLIK, H), dpi=100, gridspec_kw={"height_ratios": [h for _, h in satirlar], "hspace": 0.36})
    ax = dict(zip([a for a, _ in satirlar], np.atleast_1d(axs)))
    # ---- nota rulosu
    a = ax["rulo"]
    tum = np.concatenate([n["cekirdek"] for n in notalar]) if notalar else np.array([], int)
    if len(tum):
        alt, ust = int(math.floor(np.percentile(midi[tum], 1))) - 2, int(math.ceil(np.percentile(midi[tum], 99))) + 2
    else:
        alt, ust = 55, 72
    if ust - alt < 12:
        orta = (ust + alt) // 2
        alt, ust = orta - 6, orta + 6
    tonlar = veri.get("tonlar") or []

    def gam_at(z):
        g = None
        for tp in tonlar:
            if tp["bas"] <= z:
                g = tp
        return g or (tonlar[0] if tonlar else None)
    tp0 = gam_at((t0 + t1) / 2)
    olcek = set()
    if tp0:
        olcek = {(tp0["tonik"] + i) % 12 for i in ((0, 2, 4, 5, 7, 9, 11) if tp0["mod"] == "major" else (0, 2, 3, 5, 7, 8, 10))}
    for m_ in range(alt, ust + 1):
        a.axhline(m_, color=IZGARA, lw=0.9 if (m_ % 12) in olcek else 0.35, zorder=0)
    for ak in veri.get("akorlar") or []:
        if ak["son"] < t0 or ak["bas"] > t1 or ak["akor"] == "-":
            continue
        x0, x1 = max(t0, ak["bas"]), min(t1, ak["son"])
        kok = ADLAR.index(ak["akor"].rstrip("m")) if ak["akor"].rstrip("m") in ADLAR else None
        for m_ in range(alt, ust + 1):
            if (m_ % 12) in ak["sesler"]:
                a.add_patch(Rectangle((x0, m_ - 0.5), x1 - x0, 1.0, fc=AKOR_KOK if (m_ % 12) == kok else AKOR_ZEMIN, ec="none", zorder=1))
        a.axvline(x0, color=INK2, lw=0.5, zorder=2)
        if x1 - x0 >= (t1 - t0) * 0.012:
            a.text(x0 + (t1 - t0) * 0.002, ust + 0.55, ak["akor"], fontsize=9.5, fontweight="bold", va="bottom", ha="left", clip_on=False)
    _vuruslar(a, veri.get("vurus"), t0, t1, renk=INK2, lw=0.35)
    # perde egrisi
    mm = (t >= t0) & (t <= t1)
    egri = np.where(sesli, midi, np.nan)
    a.plot(t[mm], egri[mm], color=INK, lw=1.3, zorder=5)
    # nota cubuklari (sinifa gore)
    sinif_kare = {}
    ue = veri.get("uyum_egri") or {}
    if ue.get("cek") is not None:
        sinif_kare = dict(zip(ue["cek"].tolist(), ue["sinif"].tolist()))
    etiket_sayisi = 0
    for n in notalar:
        if n["son"] < t0 or n["bas"] > t1:
            continue
        ss = [sinif_kare.get(int(k), 0) for k in n["cekirdek"]]
        s_ = int(np.bincount(ss, minlength=3).argmax()) if ss else 0
        fc, hatch = [(IYI, None), (UYARI, "////"), (KRITIK, "xxxx")][s_]
        a.add_patch(Rectangle((n["bas"], n["midi"] - 0.22), n["son"] - n["bas"], 0.44, fc=fc, ec=INK, lw=0.5, hatch=hatch, alpha=0.75, zorder=4))
        if s_ == 2 and n["sure"] >= 0.25 and etiket_sayisi < 14:
            a.text(n["bas"], n["midi"] + 0.75, "✕ %s gam dışı" % n["ad"], fontsize=8.5, color=INK, va="bottom", zorder=6,
                   bbox=dict(boxstyle="round,pad=0.1", fc=YUZEY, ec=KRITIK, lw=0.9))
            etiket_sayisi += 1
    serit = max(2.2, (ust - alt + 1) * 0.17)                     # altta sozcuk seridi
    a.set_ylim(alt - 0.5 - serit, ust + 0.5)
    a.axhspan(alt - 0.5 - serit, alt - 0.5, color="#f1f0ec", zorder=0)
    a.set_yticks(range(alt, ust + 1))
    a.set_yticklabels([("%s%d" % (ADLAR[m_ % 12], m_ // 12 - 1)) for m_ in range(alt, ust + 1)], fontsize=9)
    for lab, m_ in zip(a.get_yticklabels(), range(alt, ust + 1)):
        lab.set_color(INK if (m_ % 12) in olcek else "#8a8980")
        lab.set_fontweight("bold" if (m_ % 12) in olcek else "normal")
    a.set_ylabel("nota (koyu etiket = altyapının gamındaki sesler)" if olcek else "nota")
    fig.legend(handles=[Line2D([0], [0], color=INK, lw=1.3, label="vokal perde eğrisi"),
                      Patch(fc=IYI, ec=INK, lw=0.5, alpha=0.75, label="nota: akor sesi"),
                      Patch(fc=UYARI, ec=INK, lw=0.5, hatch="////", alpha=0.75, label="nota: gam içi, akor dışı"),
                      Patch(fc=KRITIK, ec=INK, lw=0.5, hatch="xxxx", alpha=0.75, label="nota: gam dışı"),
                      Patch(fc=AKOR_ZEMIN, ec="none", label="altyapı akorunun sesleri (koyu = kök)")],
               loc="upper right", ncol=5, fontsize=8.5, bbox_to_anchor=(0.992, 0.998))
    ton_yazi = (tp0["ton"] + (" (belirsiz)" if tp0.get("belirsiz") else "")) if tp0 else "?"
    a.set_title(("Vokal perdesi, altyapının akor seslerinin üstünde  |  altyapı tonu: %s  |  üstte: bulunan akorlar" % ton_yazi) if kroma_var else
                "Vokal perdesi (altyapı verilmedi: akor / gam karşılaştırması yok; notalar 440 Hz ızgarasına göre)", pad=20)
    # sozcukler rulonun altindaki seritte, 3 satir kaydirmali
    yz = set(round(z_, 2) for z_ in (veri.get("yanlis_zamanlar") or []))
    sozler = [w for w in (veri.get("sozcukler") or []) if t0 <= w["bas"] <= t1]
    for k, w in enumerate(sozler):
        hatali = round(w["bas"], 2) in yz
        yy = alt - 0.5 - serit * (0.22 + 0.27 * (k % 3))
        a.plot([w["bas"], w["bas"]], [alt - 0.5, yy + serit * 0.10], color=KRITIK if hatali else INK2, lw=0.6, zorder=3)
        a.text(w["bas"], yy, ("≠ " if hatali else "") + w["metin"], fontsize=8.5, color=INK, ha="left", va="center", zorder=6, clip_on=True,
               bbox=dict(boxstyle="round,pad=0.1", fc=YUZEY, ec=KRITIK, lw=0.9) if hatali else None)
    if not sozler:
        a.text(t0 + (t1 - t0) * 0.004, alt - 0.5 - serit * 0.5, "söz dökümü yok (--sozler ya da --dokum ile eklenir)" if not veri.get("sozcukler") else "",
               fontsize=8.5, color=INK2, va="center")
    # ---- cent
    a = ax["cent"]
    a.axhspan(-25, 25, color="#e6f4e6", zorder=0)
    a.axhline(0, color=INK2, lw=0.7)
    xs, ys, es = [], [], []
    for n in notalar:
        if n["son"] < t0 or n["bas"] > t1 or n["sure"] < 0.12:
            continue
        xs.append((n["bas"] + n["son"]) / 2)
        ys.append(float(np.clip(n["cent"], -50, 50)))
        es.append(min(50.0, n["ic_std_cent"]))
    if xs:
        xs, ys, es = np.array(xs), np.array(ys), np.array(es)
        a.vlines(xs, 0, ys, color=INK2, lw=0.8)
        iyi = np.abs(ys) <= 25
        a.errorbar(xs, ys, yerr=es, fmt="none", ecolor=IZGARA, elinewidth=2.5, zorder=2)
        a.plot(xs[iyi], ys[iyi], "o", ms=5.5, color=MAVI, mec=YUZEY, mew=0.6, label="±25 cent içinde", zorder=3)
        a.plot(xs[~iyi], ys[~iyi], "X", ms=8, color=KRITIK, mec=YUZEY, mew=0.6, label="25 cent'ten fazla sapma", zorder=3)
        a.legend(loc="upper right", ncol=2)
    a.set_ylim(-52, 52)
    a.set_yticks([-50, -25, 0, 25, 50])
    a.set_ylabel("cent")
    a.set_title("Her notanın en yakın notaya uzaklığı (altyapının akordu esas; + tiz, − pes). Gri çubuk = nota içi oynaklık (±1 std). Yeşil bant = ±25 cent")
    # ---- ritim
    if ritim_var:
        a = ax["ritim"]
        r = veri["ritim"]
        b, sap = np.asarray(r["b"]), np.asarray(r["sap_ms"])
        a.axhspan(-40, 40, color="#e6f4e6", zorder=0)
        a.axhline(0, color=INK2, lw=0.7)
        _vuruslar(a, veri.get("ince_vurus"), t0, t1, renk=MAVI, lw=0.8)
        m2 = (b >= t0) & (b <= t1)
        if m2.any():
            sc = np.clip(sap[m2], -125, 125)
            a.vlines(b[m2], 0, sc, color=INK2, lw=0.8)
            ic = np.abs(sc) <= 40
            a.plot(b[m2][ic], sc[ic], "o", ms=5.5, color=MAVI, mec=YUZEY, mew=0.6, label="±40 ms içinde")
            a.plot(b[m2][~ic], sc[~ic], "X", ms=8, color=KRITIK, mec=YUZEY, mew=0.6, label="40 ms'den fazla")
            a.legend(loc="upper right", ncol=2)
        a.set_ylim(-130, 130)
        a.set_yticks([-120, -80, -40, 0, 40, 80, 120])
        a.set_ylabel("ms")
        a.set_title("Vokal hece/nota başlangıçlarının en yakın sekizlik vuruşa uzaklığı (+ geç, − erken). Mavi kesik çizgi = vuruşlar. Yeşil bant = ±40 ms")
    # ---- kroma
    a = ax.get("kroma")
    C, ct = (veri["kroma"], veri["kroma_t"]) if kroma_var else (None, np.array([]))
    i0, i1 = (int(np.searchsorted(ct, t0)), int(np.searchsorted(ct, t1))) if kroma_var else (0, 0)
    if i1 > i0:
        Cn = C[:, i0:i1] / (C[:, i0:i1].max(axis=0, keepdims=True) + 1e-9)
        a.imshow(Cn, origin="lower", aspect="auto", cmap="Greys", vmin=0, vmax=1, extent=[ct[i0], ct[min(i1, len(ct) - 1)], -0.5, 11.5], interpolation="nearest")
    if kroma_var and len(tum):
        k = tum[(t[tum] >= t0) & (t[tum] <= t1)]
        if len(k):
            pcf = np.mod(midi[k] + 0.5, 12) - 0.5
            a.plot(t[k], pcf, "s", ms=3.2, color=MAVI, mec="none", label="vokalin ses sınıfı", zorder=3)
            a.legend(loc="upper right")
    if kroma_var:
        a.set_yticks(range(12))
        a.set_yticklabels(ADLAR, fontsize=9)
        a.set_ylim(-0.5, 11.5)
        a.set_ylabel("ses sınıfı")
        a.set_title("Altyapının kroması (koyu = o ses sınıfında enerji var) ve vokalin söylediği ses sınıfı (mavi kare). Mavi kareler koyu şeritlerin üstündeyse uyumlu")
    for ad, a in ax.items():
        _zaman_ekseni(a, t0, t1, etiket=(ad == satirlar[-1][0]))
        if ad != "kroma":
            _sade(a)
    fig.suptitle("%s  |  dilim %d: %.0f-%.0f sn  |  PERDE PANOSU" % (veri["baslik"], no, t0, t1), x=0.012, ha="left", fontsize=13, fontweight="bold", y=0.995)
    fig.subplots_adjust(left=0.07, right=0.99, top=1 - 0.95 / H, bottom=0.55 / H)
    fig.savefig(yol)
    plt.close(fig)
    return yol
