# -*- coding: utf-8 -*-
"""Kulakla denetim icin on izleme: 14 cagri, sarkidaki gibi olcu izgarasinda (116 BPM, olcu 2.069 s).
Her hayvan: 1. olcu = cagri 1, 2. olcu = cagri 2, 3. olcu = bosluk. Muzik yok, yalniz hayvan sesleri.
Cikti: ../onizleme_14_cagri.mp3"""
import os, subprocess, wave, numpy as np
OUT = '/home/user/ring-tokat-3d/cocuk-kanali/ali-baba/yeni3/ses'
SR = 44100; BAR = 240.0 / 116.0
H = ['inek', 'koyun', 'at', 'horoz', 'ordek', 'kopek', 'kedi']
y = np.zeros(int((len(H) * 3 * BAR + 0.5) * SR))
for i, h in enumerate(H):
    for n in (1, 2):
        w = wave.open(os.path.join(OUT, '%s_%d.wav' % (h, n)))
        x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64) / 32768; w.close()
        p = int(round((i * 3 + (n - 1)) * BAR * SR))
        y[p:p + len(x)] += x
        print('%-6s cagri %d  %6.2f - %6.2f s' % (h, n, p / SR, (p + len(x)) / SR))
tmp = os.path.join(OUT, 'ara', 'onizleme.wav')
w = wave.open(tmp, 'w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes(np.round(np.clip(y, -1, 1) * 32767).astype('<i2').tobytes()); w.close()
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-c:a', 'libmp3lame', '-b:a', '192k', os.path.join(OUT, 'onizleme_14_cagri.mp3')], check=True)
os.remove(tmp)
print('tepe %.2f dBFS, sure %.1f s' % (20 * np.log10(np.abs(y).max()), len(y) / SR))
