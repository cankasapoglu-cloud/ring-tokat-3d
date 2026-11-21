#!/usr/bin/env python3
"""Rehber vokali (rehber.wav) kıta kıta ElevenLabs "ses değiştirici"ye (speech-to-speech) gönderir: şarkıcının ses kopyası
(ilk kayıttan oluşturulan "Ali Baba sarkici (ilk kayit)") rehberin notalarını ve zamanlamasını izleyerek yeniden söyler.
Anahtar ağ vekilince eklenir. Her kıta bir kez gönderilir; sonuçlar sts/ altında saklanır (yeniden çalıştırınca ücret kesilmez)."""
import json, os, subprocess, numpy as np, soundfile as sf
D = os.path.dirname(os.path.abspath(__file__)); A = os.path.dirname(D)
Y = json.load(open(os.path.join(A, "yeni4", "vokal", "yerlesim.json"), encoding="utf8"))
SES_ID = "9juXtB8zq1YyqAZFElnW"; PAY, ARA = 0.06, 0.35
x, fs = sf.read(os.path.join(D, "rehber.wav")); os.makedirs(os.path.join(D, "sts"), exist_ok=True)
cikti = np.zeros_like(x); rapor = []
for k in range(1, 8):
    ps = [p for p in Y["pieces"] if p["verse"] == k]; parcalar, yerler, yer = [], [], 0
    for p in ps:
        a, b = int((p["dest_in"] - PAY) * fs), int((p["dest_out"] + PAY) * fs)
        parcalar.append(x[a:b]); yerler.append((yer, b - a, a)); yer += (b - a) + int(ARA * fs)
        parcalar.append(np.zeros(int(ARA * fs)))
    giris = np.concatenate(parcalar[:-1]); gy = os.path.join(D, "sts", f"k{k}_giris.wav"); cy = os.path.join(D, "sts", f"k{k}_cikis.mp3")
    sf.write(gy, giris, fs, subtype="PCM_16")
    if not os.path.exists(cy) or os.path.getsize(cy) < 5000:
        r = subprocess.run(["curl", "-sS", "-m", "300", "-o", cy, "-w", "%{http_code}", "-X", "POST",
                            f"https://api.elevenlabs.io/v1/speech-to-speech/{SES_ID}?output_format=mp3_44100_192", "-H", "xi-api-key: proxy-injected",
                            "--form-string", "model_id=eleven_multilingual_sts_v2", "--form-string", "remove_background_noise=false",
                            "--form-string", 'voice_settings={"stability":0.55,"similarity_boost":0.9,"style":0.0,"use_speaker_boost":true}',
                            "-F", f"audio=@{gy};type=audio/wav"], capture_output=True, text=True)
        if r.stdout.strip() != "200":
            print("HATA kıta", k, r.stdout, open(cy, "rb").read()[:300]); os.unlink(cy); raise SystemExit(1)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", cy, "-ac", "1", "-ar", str(fs), cy[:-4] + ".wav"], check=True)
    y, _ = sf.read(cy[:-4] + ".wav"); y = np.pad(y, (0, max(0, len(giris) - len(y))))
    # genel gecikme: zarf çapraz ilişkisi
    w = int(0.02 * fs); ea = np.sqrt(np.convolve(giris ** 2, np.ones(w) / w, "same"))[::441]; eb = np.sqrt(np.convolve(y[:len(giris)] ** 2, np.ones(w) / w, "same"))[::441]
    c = np.correlate(eb - eb.mean(), ea - ea.mean(), "full"); gec = (np.argmax(c) - (len(ea) - 1)) * 441
    for (o, n, a) in yerler:
        s = y[max(0, o + gec):o + gec + n].copy(); s = np.pad(s, (0, n - len(s)))
        s *= np.sqrt(np.mean(giris[o:o + n] ** 2) / (np.mean(s ** 2) + 1e-12))                 # parça düzeyini rehberle eşitle
        r_ = int(0.02 * fs); s[:r_] *= np.linspace(0, 1, r_); s[-r_:] *= np.linspace(1, 0, r_)
        cikti[a:a + n] += s
    rapor.append({"kita": k, "giris_sn": round(len(giris) / fs, 2), "cikis_sn": round(len(y) / fs, 2), "gecikme_ms": round(gec / fs * 1000, 1)})
    print(rapor[-1])
cikti *= 0.708 / np.abs(cikti).max()
sf.write(os.path.join(D, "vokal_sts.wav"), cikti, fs, subtype="PCM_24")
json.dump(rapor, open(os.path.join(D, "sts", "rapor.json"), "w"), indent=1)
print("toplam gönderilen süre %.1f sn" % sum(r["giris_sn"] for r in rapor))
