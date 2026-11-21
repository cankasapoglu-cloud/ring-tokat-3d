#!/usr/bin/env python3
"""Ali Baba'nın Çiftliği — ilk kaydın (v2_2) YERİNDE düzeltilmesi.
Şarkıya (aynı şarkıcı, aynı orkestra, aynı ezgi) dokunulmaz; yalnızca:
  1. şarkıcının söylediği hayvan sesleri ("mö mö" vb.) çıkarılır,
  2. her kıtaya, orkestranın kendi çalgı ölçülerinden iki ölçü eklenir ve gerçek hayvan sesi iki kez konur
     (… var.  MÖÖ  MÖÖ  diye bağırır, çiftliğinde Ali Baba'nın),
  3. at kıtasındaki fazladan hece ("a-tı-la-rı" -> "at-la-rı") kesilir.
Bütün kesmeler orkestranın ölçü çizgilerindedir (105 vuruş/dk'lık sabit döngü); ses uzatılmaz, perdesi değişmez.
Girdi: ../v2_2.mp3, ayrılmış saplar (MDX: vokal + çalgı, toplamları özgün kayda eşittir), ../yeni4/vokal/yerlesim.json
(kesme noktaları), ../yeni3/ses/ (gerçek hayvan sesleri). Çıktı: sarki_duzeltilmis.wav/.mp3, zaman.json."""
import json, os, subprocess, sys, numpy as np, soundfile as sf
D = os.path.dirname(os.path.abspath(__file__)); A = os.path.dirname(D)
SAP = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/-home-user-ring-tokat-3d/bd9d6832-1bf0-57ca-8544-ce6f4befd453/scratchpad/sep/out_mdx"
FS = 44100
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(A, "v2_2.mp3"), "-ar", str(FS), "-ac", "2", os.path.join(D, "_mix.wav")], check=True)
mix, fs = sf.read(os.path.join(D, "_mix.wav")); assert fs == FS
vok, _ = sf.read(os.path.join(SAP, "v2_2_(Vocals)_UVR-MDX-NET-Voc_FT.wav")); cal, _ = sf.read(os.path.join(SAP, "v2_2_(Instrumental)_UVR-MDX-NET-Voc_FT.wav"))
n = min(len(mix), len(vok), len(cal)); mix, vok, cal = mix[:n], vok[:n], cal[:n]
db = lambda x: 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-12)
print("sap toplamı - özgün kayıt farkı: %.1f dB (özgün %.1f dB)" % (db(vok + cal - mix), db(mix)))
Y = json.load(open(os.path.join(A, "yeni4", "vokal", "yerlesim.json"), encoding="utf8")); P = {p["id"]: p for p in Y["pieces"]}
BS = 2.285653                                   # kaynak ölçü süresi (ölçülen ızgara)
s = lambda t: int(round(t * FS))
XF = int(0.008 * FS)                            # ek yerlerinde 8 ms çapraz geçiş


def rampa(m, yukari=True):
    w = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, m)); return (w if yukari else 1 - w)[:, None]


def olcu(kaynak, t0, sure=BS):
    """kaynak[t0 : t0+sure] ve çapraz geçiş için iki uçta XF kadar fazlası."""
    a = s(t0) - XF; b = s(t0) + int(round(sure * FS)) + XF
    return kaynak[a:b].copy()


parcalar, zaman = [], {"olcu_sn": BS, "kitalar": []}     # parcalar: (ses dizisi [XF payı dahil], açıklama)
SIRA = ["inek", "koyun", "at", "horoz", "ordek", "kopek", "kedi"]
d0 = P["K1_P1"]["src_bar_downbeat"]
giris = mix[:s(d0) + XF].copy(); giris = np.concatenate([np.zeros((XF, 2)), giris])   # baş tarafa XF dolgu (kırpılacak)
parcalar.append((giris, "giriş"))
for k in range(1, 8):
    p1, p2, p3 = P[f"K{k}_P1"], P[f"K{k}_P2"], P[f"K{k}_P3"]
    sb = [p1["src_bar_downbeat"] + i * BS for i in range(6)]
    assert abs(sb[1] - p2["src_bar_downbeat"]) < 0.005 and abs(sb[2] - p3["src_bar_downbeat"]) < 0.005, (k, sb, p2["src_bar_downbeat"])
    # n0: 1. dize (özgün kayıt)
    parcalar.append((olcu(mix, sb[0]), f"K{k} ö0 dize 1"))
    # n1: 2. dize; "var"ın bitişinde söylenen hayvan sesine geçmeden çalgıya dön
    a0 = s(sb[1]) - XF
    if k == 3:                                   # at kıtası: çalgı sapı + düzeltilmiş vokal sapı (fazla hece kesilir)
        v = vok[a0:a0 + len(olcu(mix, sb[1]))].copy(); kazanc = np.ones((len(v), 1))
        on = Y["repairs"][0]
        f0a, f0b = s(on["fade_out_before"]["src_from"]) - a0, s(on["fade_out_before"]["src_to"]) - a0
        f1a, f1b = s(on["fade_in_after"]["src_from"]) - a0, s(on["fade_in_after"]["src_to"]) - a0
        kazanc[f0a:f0b] = rampa(f0b - f0a, False); kazanc[f0b:f1a] = 0; kazanc[f1a:f1b] = rampa(f1b - f1a, True)
        e0, e1 = s(p2["src_out"] - 0.030) - a0, s(p2["src_out"]) - a0
        kazanc[e0:e1] *= rampa(e1 - e0, False); kazanc[e1:] = 0
        bar = cal[a0:a0 + len(v)] + v * kazanc
    else:
        bar = olcu(mix, sb[1]); c = cal[a0:a0 + len(bar)]
        e0, e1 = s(p2["src_out"] - 0.030) - a0, s(p2["src_out"]) - a0
        w = rampa(e1 - e0, False); bar[e0:e1] = bar[e0:e1] * w + c[e0:e1] * (1 - w); bar[e1:] = c[e1:]
    parcalar.append((bar, f"K{k} ö1 dize 2"))
    # n2, n3: orkestranın kendi çalgı ölçüleri (gerçek hayvan sesi buraya gelecek)
    parcalar.append((olcu(mix, sb[4]), f"K{k} ö2 hayvan sesi 1")); parcalar.append((olcu(mix, sb[5]), f"K{k} ö3 hayvan sesi 2"))
    # n4: söylenen hayvan sesi yerine çalgı; "diye bağırır" özgün kayıttan
    a0 = s(sb[2]) - XF; bar = cal[a0:a0 + len(olcu(mix, sb[2]))].copy(); m = mix[a0:a0 + len(bar)]
    g0 = s(p3["src_in"]) - a0; g1 = g0 + int(0.015 * FS); w = rampa(g1 - g0, True)
    bar[g0:g1] = bar[g0:g1] * (1 - w) + m[g0:g1] * w; bar[g1:] = m[g1:]
    parcalar.append((bar, f"K{k} ö4 diye bağırır"))
    # n5: 4. dize; n6, n7: çalgı arası (özgün)
    parcalar.append((olcu(mix, sb[3]), f"K{k} ö5 dize 4")); parcalar.append((olcu(mix, sb[4]), f"K{k} ö6 ara")); parcalar.append((olcu(mix, sb[5]), f"K{k} ö7 ara"))
son_t = P["K7_P1"]["src_bar_downbeat"] + 6 * BS
bitis = mix[s(son_t) - XF:].copy(); bitis = np.concatenate([bitis, np.zeros((XF, 2))])
parcalar.append((bitis, "bitiş"))
# ek yerlerinde 8 ms çapraz geçişle birleştir
cikti = np.zeros((sum(len(p) - 2 * XF for p, _ in parcalar) + 2 * XF, 2)); yer = 0; baslar = []
for ses, ad in parcalar:
    ses = ses.copy(); ses[:2 * XF] *= rampa(2 * XF, True); ses[-2 * XF:] *= rampa(2 * XF, False)
    cikti[yer:yer + len(ses)] += ses; baslar.append((ad, (yer + XF - XF) / FS)); yer += len(ses) - 2 * XF
cikti = cikti[XF:-XF]                                   # baştaki ve sondaki dolguyu at
bas_sn = {ad: t for ad, t in baslar}
# gerçek hayvan sesleri: ö2 ve ö3'ün 3. vuruşundan 40 ms önce; o sırada orkestra 3 dB kısılır
w50 = int(0.05 * FS); hay = np.zeros_like(cikti); kis = np.ones((len(cikti), 1))
for k in range(1, 8):
    kayit = {"kita": k, "hayvan": SIRA[k - 1], "sesler": []}
    for j, ad in enumerate((f"K{k} ö2 hayvan sesi 1", f"K{k} ö3 hayvan sesi 2")):
        t = bas_sn[ad] + BS / 2 - 0.04
        x, f2 = sf.read(os.path.join(A, "yeni3", "ses", f"{SIRA[k - 1]}_{j + 1}.wav")); assert f2 == FS; x = x if x.ndim == 1 else x.mean(axis=1)
        ev = np.sqrt(np.convolve(x ** 2, np.ones(w50) / w50, "same")); yuk = ev > ev.max() * 10 ** (-10 / 20)
        p = s(t); zemin = cikti[p:p + len(x)].mean(axis=1)
        g = min(10 ** ((-13.5 - db(x[yuk])) / 20), 1.0 / np.abs(x).max())     # sesin yüksek bölümü -13,5 dBFS: dize düzeyinin yaklaşık 2 dB üstü
        hay[p:p + len(x)] += (x * g)[:, None]
        r = int(0.03 * FS); kis[p - r:p] = np.minimum(kis[p - r:p], 1 - (1 - 0.708) * rampa(r, True)); kis[p:p + len(x)] = 0.708
        kis[p + len(x):p + len(x) + r] = np.minimum(kis[p + len(x):p + len(x) + r], 0.708 + (1 - 0.708) * rampa(r, True))
        kayit["sesler"].append({"baslangic": round(t, 3), "bitis": round(t + len(x) / FS, 3), "kazanc_dB": round(20 * np.log10(g), 1)})
    kayit["diye_bagirir"] = round(bas_sn[f"K{k} ö4 diye bağırır"] + (P[f"K{k}_P3"]["src_in"] - P[f"K{k}_P3"]["src_bar_downbeat"]), 3)
    kayit["olcu_baslari"] = [round(bas_sn[a], 3) for a in (f"K{k} ö0 dize 1", f"K{k} ö1 dize 2", f"K{k} ö2 hayvan sesi 1", f"K{k} ö3 hayvan sesi 2", f"K{k} ö4 diye bağırır", f"K{k} ö5 dize 4", f"K{k} ö6 ara", f"K{k} ö7 ara")]
    assert kayit["sesler"][1]["bitis"] < kayit["diye_bagirir"] - 0.1, (k, kayit)
    zaman["kitalar"].append(kayit)
son = cikti * kis + hay
zaman["sure_sn"] = round(len(son) / FS, 3); zaman["giris_bitis"] = round(bas_sn["K1 ö0 dize 1"], 3); zaman["bitis_baslangic"] = round(bas_sn["bitiş"], 3)
tepe = np.abs(son).max(); print("süre %.2f sn, tepe %.2f dBFS, özgün tepe %.2f dBFS" % (len(son) / FS, 20 * np.log10(tepe), 20 * np.log10(np.abs(mix).max())))
sf.write(os.path.join(D, "_ham.wav"), son, FS, subtype="FLOAT")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(D, "_ham.wav"), "-af", "alimiter=limit=0.89:attack=5:release=60:level=disabled", "-ar", str(FS),
                os.path.join(D, "sarki_duzeltilmis.wav")], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(D, "sarki_duzeltilmis.wav"), "-b:a", "192k", os.path.join(D, "sarki_duzeltilmis.mp3")], check=True)
json.dump(zaman, open(os.path.join(D, "zaman.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
for f in ("_mix.wav", "_ham.wav"): os.unlink(os.path.join(D, f))
for kt in zaman["kitalar"][:2]: print(kt)
