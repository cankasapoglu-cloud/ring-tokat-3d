#!/usr/bin/env python3
# (a) blind form check on the delivered mix: which bars are thin, which bars start with a crash (only BPM is assumed)
# (b) glockenspiel stems: note = semitone whose energy RISES most at each grid slot (blind), + how much the previous note still rings
# (c) ending: is the second answer (bar 61) harmonised (brass third above)?  (d) roll bar chords, both tempi
# usage: 05_form_glock_bitis.py <delivered folder> <work 104.96> <work 105.30> <out json>
import sys, json
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
DEL, WORK, WORK2, OUTJ = sys.argv[1:5]
P = lambda *a: print(*a, flush=True); R = {}
db = lambda v: 20 * np.log10(np.maximum(v, 1e-12)); rms = lambda x: float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']; nm = lambda m: f'{NAMES[int(m) % 12]}{int(m) // 12 - 1}'
f2m = lambda f: 69 + 12 * np.log2(np.maximum(f, 1e-6) / 440); m2f = lambda m: 440 * 2 ** ((m - 69) / 12)
KIND = ['iA', 'iANS', 'iA', 'iANS'] + ['voc', 'ans', 'voc', 'slot', 'slot', 'fill', 'voc', 'ans'] * 7 + ['ans', 'ans', 'roll', 'final']
PHA = [(0, 0), (1, 0), (2, 0), (3, -5), (4, -3), (5, -3), (6, -5)]; ANS = [(0, 4), (1, 4), (2, 2), (3, 2), (4, 0)]; DOREP = [(4, 0), (5, 0), (6, 0), (7, 0)]
sr = 44100
for key in ('G', 'C'):
    r = R[key] = {}; BPM = 104.96; BEAT = 60 / BPM; BAR = 4 * BEAT; TON = NAMES.index(key)
    x, _ = sf.read(f'{DEL}/altyapi_{key}.wav'); mono = x.mean(1)
    lv = np.array([db(rms(mono[int(b * BAR * sr):int((b + 1) * BAR * sr)])) for b in range(64)])
    quiet = [b for b in range(64) if lv[b] < np.median(lv) - 8]
    hf = sosfiltfilt(butter(4, 8000, 'high', fs=sr, output='sos'), mono)
    cr = np.array([db(rms(hf[int((b * BAR + .15) * sr):int((b * BAR + .55) * sr)])) for b in range(64)])      # sustained HF 150-550 ms after the downbeat = cymbal
    crash = [b for b in range(64) if cr[b] > np.median(cr) + 6]
    exp_quiet = [4 + 8 * v + i for v in range(7) for i in (3, 4)]; exp_start = [4 + 8 * v for v in range(7)]
    r.update(quiet_bars=quiet, quiet_bars_expected=exp_quiet, quiet_ok=quiet == exp_quiet, crash_bars=crash, verse_starts_expected=exp_start,
             all_verse_starts_have_crash=all(b in crash for b in exp_start), n_bars_with_sound=int((lv > -60).sum()),
             level_after_bar64_db=float(db(rms(mono[int(64 * BAR * sr):]))), level_bar64_to_plus1s=float(db(rms(mono[int(64 * BAR * sr):int((64 * BAR + 1) * sr)]))))
    P(f'[{key}] blind form (delivered altyapi): bars more than 8 dB below the median bar level: {quiet}  -> equals verse bars 3 and 4 of 7 verses of 8 bars after a 4-bar intro: {quiet == exp_quiet}')
    P(f'[{key}] (INCONCLUSIVE, >8 kHz is dominated by glockenspiel and trumpet, not by the crash) bars with sustained >8 kHz energy after the downbeat: {crash}')
    P(f'[{key}] bars 0..63 all carry sound: {r["n_bars_with_sound"]}/64; quietest bar {lv.min():.1f} dBFS, loudest {lv.max():.1f} dBFS (bar {int(lv.argmax())})')
    del x, mono, hf
    meta = json.load(open(f'{WORK}/{key}/meta.json')); CUT = meta['CUT']
    # ---- (b) glockenspiels
    for stem, part, lo_m, hi_m in (('glockenspiel', 'lead', 72, 91), ('glockenspiel_hafif', 'alt', 76, 94)):
        g, _ = sf.read(f'{WORK}/{key}/st_{stem}.wav'); g = g[CUT:].mean(1); n = 4096; w = np.hanning(n); fr = np.fft.rfftfreq(4 * n, 1 / sr); mm = f2m(fr)
        sems = np.arange(lo_m, hi_m + 1); masks = [(np.abs(mm - s) < .45) for s in sems]
        def en(i0):
            A = np.abs(np.fft.rfft(g[i0:i0 + n] * w, 4 * n)) ** 2; return np.array([A[k].sum() for k in masks])
        seq = {}; ring = []; tot = ok = 0; bad = []; do = None
        for b, k in enumerate(KIND):
            E = (PHA if k == 'iA' else ANS if k in ('iANS', 'ans') else []) if part == 'lead' else (PHA if k == 'voc' else DOREP if k == 'fill' else [])
            prev = None
            for s, iv in E:
                t = b * BAR + s * BEAT / 2; i0 = int(round((t + .004) * sr)); j0 = int(round((t - .004) * sr)) - n
                Ea = en(i0); Eb = en(j0) if j0 >= 0 else np.zeros(len(sems)); inc = Ea - Eb; m = int(sems[int(np.argmax(inc))])
                if do is None: do = m - iv
                tot += 1; ok += (m == do + iv)
                if m != do + iv: bad.append((b, s, nm(m), nm(do + iv)))
                seq.setdefault(k, {}).setdefault(s, set()).add(nm(m))
                if prev is not None and prev != iv:        # pitch changed: old note's fundamental vs new note's fundamental, 4..97 ms after the new attack
                    ring.append(10 * np.log10(Ea[do + prev - lo_m] / Ea[do + iv - lo_m]))
                prev = iv
        r[stem] = dict(do=nm(do), checked=tot, match=ok, mismatches=bad[:10], detected={k: ' '.join(f'{s}:{"/".join(sorted(v))}' for s, v in sorted(d.items())) for k, d in seq.items()},
                       old_note_vs_new_note_db=dict(n=len(ring), median=float(np.median(ring)), max=float(np.max(ring)), min=float(np.min(ring)), share_old_louder=float(np.mean(np.array(ring) > 0))))
        P(f'[{key}] {stem}: note = semitone ({nm(lo_m)}..{nm(hi_m)}) with the largest energy increase at the slot; do = {nm(do)}; {ok}/{tot} as in the task; exceptions {bad[:6]}')
        for k, v in r[stem]['detected'].items(): P(f'        {k:5s} {v}')
        P(f'        ring-over at pitch changes: fundamental of the PREVIOUS note relative to the NEW note in the first 93 ms after the new attack: median {np.median(ring):+.1f} dB, range {np.min(ring):+.1f} .. {np.max(ring):+.1f} dB, previous note louder in {100 * np.mean(np.array(ring) > 0):.0f} % of {len(ring)} changes')
        del g
    # ---- (c) harmonised second answer in the ending (brass): level at the third-above pitches, bar 61 vs bar 60
    br, _ = sf.read(f'{WORK}/{key}/st_brass.wav'); br = br[CUT:].mean(1); LEAD_DO = 67 if key == 'G' else 72; n = 8192; fr = np.fft.rfftfreq(4 * n, 1 / sr); out = []
    for s, iv in ANS:
        third = LEAD_DO + iv + (4 if iv == 0 else 3); f0 = m2f(third); sel = np.abs(f2m(fr) - third) < .3; row = []
        for b in (60, 61):
            t = b * BAR + s * BEAT / 2; i0 = int(round((t + .03) * sr)); A = np.abs(np.fft.rfft(br[i0:i0 + n] * np.hanning(n), 4 * n)); row.append(float(db(A[sel].max()) - db(A.max())))
        out.append((nm(third), round(row[0], 1), round(row[1], 1)))
    r['ans2_third_above'] = out; P(f'[{key}] ending, brass stem, level at the diatonic third above each answer note relative to the strongest partial (note, bar 60 plain, bar 61 harmonised): {out}')
    # final bar: hits
    dr, _ = sf.read(f'{WORK}/{key}/st_davul.wav'); dr = dr[CUT:].mean(1); e = np.sqrt(np.convolve(dr ** 2, np.ones(220) / 220, 'same'))
    hits = []
    for bt in np.arange(0, 4, .25):
        t = 63 * BAR + bt * BEAT; a = e[int((t + .002) * sr):int((t + .04) * sr)].max(); p = e[int((t - .03) * sr):int((t - .003) * sr)].mean()
        if db(a) - db(p) > 6 and db(a) > db(e.max()) - 30: hits.append((float(bt), round(float(db(a) - db(e.max())), 1)))
    r['final_bar_drum_hits'] = hits; P(f'[{key}] final bar 63, drum stem: new hits at (beat, level rel. to the loudest drum hit of the song): {hits}')
    del br, dr
# ---- (d) roll bar (bar 62) chords in the comp stems, both tempi (key G)
def chroma(x, t0, t1):
    seg = x[int(round(t0 * sr)):int(round(t1 * sr))]; n = 32768
    A = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n)) ** 2; fr = np.fft.rfftfreq(n, 1 / sr); sel = (fr > 110) & (fr < 2100)
    return np.bincount(np.round(f2m(fr[sel])).astype(int) % 12, weights=A[sel], minlength=12)
TPL = {'I': [0, 4, 7], 'IV': [5, 9, 0], 'V7': [7, 11, 2, 5]}
for lab, W, bpm in (('104.96', WORK, 104.96), ('105.30', WORK2, 105.30)):
    meta = json.load(open(f'{W}/G/meta.json')); CUT = meta['CUT']; BEAT = 60 / bpm; BAR = 4 * BEAT
    comp = sum(sf.read(f'{W}/G/st_{s}.wav', start=CUT + int(61.9 * BAR * sr), stop=CUT + int(63.1 * BAR * sr))[0].mean(1) for s in ('banjo', 'akordeon', 'piyano'))
    off = 61.9 * BAR; rows = []
    for i in range(4):
        t = 62 * BAR + i * BEAT - off; c = np.roll(chroma(comp, t + .02, t + BEAT - .01), -7); sc = {}
        for k, v in TPL.items():
            tt = np.zeros(12); tt[v] = 1; sc[k] = round(float(np.dot(c, tt) / (np.linalg.norm(c) * np.linalg.norm(tt) + 1e-20)), 3)
        rows.append(sc)
    R[f'roll_bar_scores_{lab}'] = rows; P(f'[G {lab} BPM] roll bar 62, comp stems, template scores per beat (task: IV IV V7 V7): {rows}')
json.dump(R, open(OUTJ, 'w'), indent=1, ensure_ascii=False, default=str)
