#!/usr/bin/env python3
"""Derleme videosu: yükleme paketindeki şarkıları tek videoda birleştirir (tek ffmpeg komutu, tek kodlama).

Her şarkının girişi ilk sözden yaklaşık 2 saniye öncesine kısaltılır, sonu son sesten hemen sonra kesilir;
parçalar arasında kısa bir beyaza geçiş ve ses yumuşatması vardır. Başta açılış (acilis.mp4), sonda kapanış (kapanis.mp4).

Kullanım (cocuk-kanali/derleme-01 içinden ya da herhangi bir yerden):
    python derle.py                 # tam kalite (crf 20), çıktı: cikti/12-cocuk-sarkilari-derlemesi.mp4
    python derle.py --deneme        # hızlı ve düşük kaliteli deneme çıktısı
    python derle.py --yaz           # yalnızca derle.ps1 dosyasını yeniden yazar (Python olmayan Windows için aynı komut)
Gereken: ffmpeg (PATH'te). Kaynak videolar: ../buyume/yukleme-paketi/
Bölüm zamanları derleme.json içindeki kesim noktalarından hesaplanır ve bolumler.txt dosyasına yazılır."""
import json, os, subprocess, sys
D = os.path.dirname(os.path.abspath(__file__)); P = os.path.join("..", "buyume", "yukleme-paketi")
R = json.load(open(os.path.join(D, "derleme.json"), encoding="utf8"))
DENEME = "--deneme" in sys.argv
CIKTI = os.path.join("cikti", "deneme.mp4" if DENEME else R["cikti"])

def komut(deneme=False, cikti=None):
    girdi, filtre, n = [], [], len(R["parcalar"])
    for i, p in enumerate(R["parcalar"]):
        sure = round(p["bit"] - p["bas"], 3); yol = p["dosya"] if p.get("yerel") else P + "/" + p["dosya"]
        girdi += ["-ss", f"{p['bas']:.3f}", "-t", f"{sure:.3f}", "-i", yol]
        g = [] if i == 0 else ["fade=t=in:st=0:d=0.2:color=white"]
        c = [] if i == n - 1 else [f"fade=t=out:st={sure - 0.25:.3f}:d=0.25:color=white"]
        filtre.append(f"[{i}:v]fps=24,scale=1920:1080:flags=lanczos,setsar=1,format=yuv420p," + ",".join(g + c + [f"trim=0:{sure:.3f}", "setpts=PTS-STARTPTS"]) + f"[v{i}]")
        filtre.append(f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={p.get('kazanc_db', 0)}dB,"
                      f"afade=t=in:st=0:d={p.get('ses_giris', 0.25)},afade=t=out:st={sure - p.get('ses_cikis', 0.5):.3f}:d={p.get('ses_cikis', 0.5)},apad,atrim=0:{sure:.3f},asetpts=PTS-STARTPTS[a{i}]")
    filtre.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
    kalite = ["-preset", "veryfast", "-crf", "30"] if deneme else ["-preset", "medium", "-crf", "20"]
    return ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats", *girdi, "-filter_complex", ";".join(filtre), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", *kalite, "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", cikti or CIKTI]

def bolumler():
    t, satir = 0.0, []
    for p in R["parcalar"]:
        if p.get("baslik"):
            b = 0.0 if not satir else t            # ilk bölüm 0:00'da başlamalı (açılış ilk şarkıyla aynı bölümde)
            satir.append(f"{int(b // 60)}:{int(b % 60):02d} {p['baslik']}")
        t += p["bit"] - p["bas"]
    return satir, t

def ps1():
    k = komut(False, os.path.join("cikti", R["cikti"]))
    satirlar = ["# derle.py ile aynı komut (Python yoksa): PowerShell'de bu klasörde  .\\derle.ps1  diye çalıştırılır. Bu dosya derle.py --yaz ile üretilir, elle düzenlenmez.",
                "Set-Location $PSScriptRoot", "New-Item -ItemType Directory -Force cikti | Out-Null", "$a = @("]
    satirlar += ["  '" + x.replace("'", "''") + "'" for x in k[1:]]
    satirlar += [")", "& ffmpeg @a", "if ($LASTEXITCODE -ne 0) { Write-Error 'ffmpeg hata verdi'; exit 1 }", "Get-Item (Join-Path cikti '" + R["cikti"] + "') | Select-Object Name, Length"]
    open(os.path.join(D, "derle.ps1"), "w", encoding="utf-8-sig", newline="\r\n").write("\n".join(satirlar) + "\n")

if __name__ == "__main__":
    os.chdir(D); os.makedirs("cikti", exist_ok=True)
    satir, toplam = bolumler(); open("bolumler.txt", "w", encoding="utf8").write("\n".join(satir) + "\n"); ps1()
    print(f"toplam {int(toplam // 60)} dk {toplam % 60:.0f} sn, {len(R['parcalar'])} parça"); print("\n".join(satir))
    if "--yaz" in sys.argv: sys.exit(0)
    subprocess.run(komut(DENEME), check=True)
    s = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", CIKTI], capture_output=True, text=True).stdout)
    print(f"çıktı: {CIKTI}  {os.path.getsize(CIKTI) / 1e6:.0f} MB, {s:.1f} sn (beklenen {toplam:.1f})")
