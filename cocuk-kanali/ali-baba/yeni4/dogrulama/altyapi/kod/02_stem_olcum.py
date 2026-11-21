#!/usr/bin/env python3
# Reviewer measurements on per-instrument stems of MY OWN re-render (same build.py, my scratch folder).
# Expectations are written here from the task text (NEW SONG FORM), not taken from the builder's note list.
# usage: 02_stem_olcum.py <folder with altyapi_<K>.wav etc. of the re-render> <work folder with <K>/st_*.wav> <K> <delivered folder or -> <out json>
import sys, json
import numpy as np, soundfile as sf, librosa
from scipy.signal import butter, sosfiltfilt

OUTD, WORK, KEY, DELIV, OUTJ = sys.argv[1:6]
P = lambda *a: print(*a, flush=True)
db = lambda v: 20 * np.log10(np.maximum(v, 1e-12))
rms = lambda x: float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
nm = lambda m: f'{NAMES[int(round(m)) % 12]}{int(round(m)) // 12 - 1}'
f2m = lambda f: 69 + 12 * np.log2(np.maximum(f, 1e-6) / 440)
R = {'key': KEY}
Z = json.load(open(f'{OUTD}/zaman_{KEY}.json'))
BPM = Z['tempo_bpm']; BEAT = 60 / BPM; BAR = 4 * BEAT; sr = 44100; TON = NAMES.index(KEY)
S = f'{WORK}/{KEY}'
P(f'===== key {KEY}, {BPM} BPM, bar {BAR:.6f} s (render in {OUTD}) =====')

# ---------- 0. is my re-render the delivered file? --------------------------------------------------------
if DELIV != '-':
    for n in ('altyapi', 'ezgi_alti', 'rehber'):
        a, _ = sf.read(f'{OUTD}/{n}_{KEY}.wav', dtype='int16'); b, _ = sf.read(f'{DELIV}/{n}_{KEY}.wav', dtype='int16')
        d = int(np.abs(a.astype(np.int32) - b.astype(np.int32)).max()) if a.shape == b.shape else None
        R[f'rerender_vs_delivered_{n}_max_lsb'] = d; P(f'[0] my re-render vs delivered {n}_{KEY}.wav: shapes equal {a.shape == b.shape}, max difference {d} LSB')
    za = json.load(open(f'{DELIV}/zaman_{KEY}.json')); R['rerender_json_identical'] = (za == Z); P(f'[0] zaman_{KEY}.json identical to the delivered one: {za == Z}')

# ---------- stems, aligned by my own cross-correlation against the delivered-format altyapi ----------------
alt_del, _ = sf.read(f'{OUTD}/altyapi_{KEY}.wav'); N = len(alt_del)
band_raw, _ = sf.read(f'{S}/band.wav')
TEMPO_US = int(round(60e6 / BPM)); CUT_BUILDER = int(round(TEMPO_US / 1e6 * sr)) + 82
seg = slice(int(20 * sr), int(26 * sr)); ref = alt_del[seg].mean(1); best = (None, -1)
for lag in range(CUT_BUILDER - 400, CUT_BUILDER + 401):
    c = float(np.dot(ref, band_raw[seg.start + lag:seg.stop + lag].mean(1)))
    if c > best[1]: best = (lag, c)
CUT = best[0]; R['cut_xcorr'] = CUT; R['cut_builder'] = CUT_BUILDER
P(f'[0] stem alignment by cross-correlation with altyapi: lag {CUT} samples (builder formula {CUT_BUILDER}; pre-roll {int(round(TEMPO_US / 1e6 * sr))} + latency 82)')
def rd(name):
    x, r = sf.read(f'{S}/{name}.wav'); assert r == sr
    x = x[CUT:CUT + N]
    if len(x) < N: x = np.vstack([x, np.zeros((N - len(x), 2))])
    return x
ST = {n: rd('st_' + n) for n in ('davul', 'bas', 'banjo', 'akordeon', 'piyano', 'glockenspiel', 'trompet', 'brass', 'klarnet', 'glockenspiel_hafif')}
band = band_raw[CUT:CUT + N].copy(); del band_raw
BANDN = ('davul', 'bas', 'banjo', 'akordeon', 'piyano', 'glockenspiel', 'trompet', 'brass')
res = band - sum(ST[n] for n in BANDN)
R['band_minus_stems_db'] = float(db(rms(res)) - db(rms(band))); P(f'[0] band render minus sum of the 8 band stems: {R["band_minus_stems_db"]:.1f} dB relative to the band')
# drum start: first audible sample of the kick at t=0
dr0 = np.abs(ST['davul']).max(1); first = int(np.argmax(dr0 > 1e-4)); pk0 = int(np.argmax(dr0[:2000]))
R['first_drum_sample_ms'] = 1000 * first / sr; P(f'[0] drum stem: first sample above -80 dBFS at {1000 * first / sr:.2f} ms after file start (t=0 should be the downbeat)')

# ---------- form from the task text ------------------------------------------------------------------------
KIND = ['iA', 'iANS', 'iA', 'iANS'] + ['voc', 'ans', 'voc', 'slot', 'slot', 'fill', 'voc', 'ans'] * 7 + ['ans', 'ans', 'roll', 'final']
DEGS = {'iA': 'I I IV I', 'iANS': 'I V7 I I', 'voc': 'I I IV I', 'ans': 'I V7 I I', 'slot': 'I I I I', 'fill': 'I I I I', 'roll': 'IV IV V7 V7', 'final': 'I I I I'}
PHA = {0: (0, 1), 1: (0, 1), 2: (0, 1), 3: (-5, 1), 4: (-3, 1), 5: (-3, 1), 6: (-5, 1), 7: (-5, 0)}       # slot (eighth) -> (semitones from do, new attack)
ANS = {0: (4, 1), 1: (4, 1), 2: (2, 1), 3: (2, 1), 4: (0, 1), 5: (0, 0), 6: (0, 0)}
DOREP = {4: (0, 1), 5: (0, 1), 6: (0, 1), 7: (0, 1)}
def expected(part):
    E = {}
    for b, k in enumerate(KIND):
        if part == 'lead': E[b] = PHA if k == 'iA' else ANS if k in ('iANS', 'ans') else None if k in ('roll', 'final') else {}
        else: E[b] = PHA if k == 'voc' else DOREP if k == 'fill' else {}
    return E

def yin_track(x, fmin, fmax, fl):
    f = librosa.yin(x, fmin=fmin, fmax=fmax, sr=sr, frame_length=fl, hop_length=256)
    return f, np.arange(len(f)) * 256 / sr
def dip_db(x, t):
    # re-articulation depth: loudest 5 ms window in [t, t+90 ms] minus quietest 5 ms window in [t-50 ms, t+10 ms]
    a = int(round((t - .05) * sr)); b = int(round((t + .09) * sr))
    if a < 0: return 99.0
    e = np.sqrt(np.convolve(x[a:b] ** 2, np.ones(220) / 220, 'valid')); k = int(.06 * sr)
    return float(db(e[k - 220:].max()) - db(e[:k].min()))
def slot_table(x, f, tf):
    T = []
    for b in range(64):
        for s in range(8):
            t = b * BAR + s * BEAT / 2; i = lambda u: max(0, int(round(u * sr)))
            lev = rms(x[i(t + .05):i(t + .20)])
            m = (tf >= t + .06) & (tf <= t + .20); T.append((b, s, lev, dip_db(x, t), float(np.median(f2m(f[m])))))
    return T
def peak_table(x, lo, hi, rel_db, wide=(350, 8000)):
    # blind note estimate from the plain spectrum of the 93 ms after each grid slot:
    #   rel_db > 0: LOWEST spectral peak within rel_db of the strongest one in lo..hi;  rel_db = 0: STRONGEST peak in lo..hi
    # also returns the strongest partial in the wide band (to show where the energy of the instrument really sits)
    n = 4096; w = np.hanning(n); fr = np.fft.rfftfreq(4 * n, 1 / sr); T = []; sel = (fr > lo) & (fr < hi); selw = (fr > wide[0]) & (fr < wide[1])
    for b in range(64):
        for s in range(8):
            t = b * BAR + s * BEAT / 2; i0 = int(round((t + .004) * sr))
            A0 = np.abs(np.fft.rfft(x[i0:i0 + n] * w, 4 * n)) if i0 + n <= len(x) else np.zeros(len(fr))
            A = np.where(sel, A0, 0); W = np.where(selw, A0, 0); mx = A.max(); kw = int(np.argmax(W))
            if mx <= 0: pk = []
            elif rel_db == 0: pk = [int(np.argmax(A))]
            else: pk = np.where((A[1:-1] > A[:-2]) & (A[1:-1] >= A[2:]) & (A[1:-1] > mx * 10 ** (-rel_db / 20)))[0] + 1
            lev = rms(x[int(round((t + .05) * sr)):int(round((t + .20) * sr))])
            T.append((b, s, lev, dip_db(x, t), float(f2m(fr[pk[0]])) if len(pk) else 0.0, float(f2m(fr[kw])) if W[kw] > 0 else 0.0, float(db(A[pk[0]]) - db(W[kw])) if len(pk) else 0.0))
    return T
def check_mono(name, part, table, check_held=True):
    T = table
    E = expected(part); ref = np.percentile([t[2] for t in T], 97)
    b0, s0 = next((b, s) for b in range(64) if E[b] for s, (iv, a) in sorted(E[b].items()) if iv == 0)
    do = int(round(next(t[4] for t in T if t[0] == b0 and t[1] == s0)))       # "do" octave: detected pitch of the first expected do
    snd, sil, bad, cents, seqs, free, rep_dip, strongest, fund_rel = [], [], [], [], {}, {}, [], [], []
    prev = {}
    for row in T:
        b, s, lev, dip, m = row[:5]
        L = db(lev) - db(ref)
        if E[b] is None:
            if L > -25: free.setdefault(b, []).append((s, nm(m), round(float(L), 1)))
            continue
        if s in E[b]:
            iv, a = E[b][s]
            if not a and not check_held: continue
            snd.append(L); err = m - (do + iv); cents.append(100 * err)
            repeated = a and (s - 1) in E[b] and E[b][s - 1][0] == iv
            if repeated: rep_dip.append(dip)
            if len(row) > 5 and a: strongest.append(round(row[5] - m)); fund_rel.append(row[6])
            ok = abs(err) < 0.35 and L > -25 and (dip > 2.5 if repeated else True)
            if not ok: bad.append((b, s, nm(m), round(float(100 * err)), round(float(L), 1), round(float(dip), 1), 'expected ' + nm(do + iv) + (' re-attack' if repeated else ' attack' if a else ' held')))
            seqs.setdefault(KIND[b], {}).setdefault(s, set()).add(nm(m) + ('' if a else '~'))
        else:
            sil.append((float(L), b, s, round(float(dip), 1)))
    sil.sort(reverse=True)
    out = dict(do=nm(do), expected_note_slots=len(snd), mismatches=bad, min_level_expected_db=float(min(snd)), max_level_elsewhere_db=float(sil[0][0]),
               loudest_elsewhere=[(round(l, 1), b, KIND[b], s, r) for l, b, s, r in sil[:6]], attacks_elsewhere=[(b, KIND[b], s, round(l, 1), r) for l, b, s, r in sil if r > 8 and l > -20][:10],
               pitch_err_cents_mean=float(np.mean(cents)), pitch_err_cents_maxabs=float(np.max(np.abs(cents))),
               repeated_note_reattack_dip_db=dict(n=len(rep_dip), min=float(min(rep_dip)), median=float(np.median(rep_dip))),
               detected={k: ' '.join(f'{s}:{"/".join(sorted(v))}' for s, v in sorted(d.items())) for k, d in seqs.items()}, free_bars=free)
    if strongest:
        u, c = np.unique(strongest, return_counts=True); out['strongest_partial_semitones_above_detected_lowest'] = {int(a): int(b) for a, b in zip(u, c)}
        out['lowest_peak_rel_to_strongest_db'] = dict(min=float(min(fund_rel)), median=float(np.median(fund_rel)))
    R[name] = out
    P(f'[1] {name}: do = {out["do"]}; {len(snd)} expected note slots, {len(bad)} mismatches; pitch error mean {out["pitch_err_cents_mean"]:+.1f} cents, max |err| {out["pitch_err_cents_maxabs"]:.1f}; '
      f'weakest expected slot {min(snd):.1f} dB, loudest slot where silence is expected {sil[0][0]:.1f} dB (rel. to the 97th pct slot level); '
      f're-attack depth of repeated notes (dip before the note): min {min(rep_dip):.1f} dB, median {np.median(rep_dip):.1f} dB, n = {len(rep_dip)}')
    for k, v in out['detected'].items(): P(f'       {k:5s} detected per eighth slot (~ = held): {v}')
    if strongest: P(f'       strongest partial in the wide band lies N semitones above the detected note {{N: count}}: {out["strongest_partial_semitones_above_detected_lowest"]}; level of the note itself vs the strongest partial: median {np.median(fund_rel):.1f} dB, min {min(fund_rel):.1f} dB')
    if bad: P('       MISMATCHES (bar, slot, detected, cents, level, dip, expectation):', bad[:12])
    P('       loudest slots outside the expected notes (dB, bar, kind, slot, dip dB):', out['loudest_elsewhere'])
    if out['attacks_elsewhere']: P('       NEW ATTACKS where silence is expected (bar, kind, slot, level, dip):', out['attacks_elsewhere'])
    if free: P('       ending bars 62/63 (free, reported only):', {b: v for b, v in free.items()})
    return do

def yin_table(x, fmin, fmax, fl=2048):
    f, tf = yin_track(x, fmin, fmax, fl); return slot_table(x, f, tf)
do_lead = check_mono('lead_trompet', 'lead', yin_table(ST['trompet'].mean(1), 150, 2000))
do_alt = check_mono('ezgi_alti_klarnet', 'alt', yin_table(ST['klarnet'].mean(1), 150, 2000))
ez, _ = sf.read(f'{OUTD}/ezgi_alti_{KEY}.wav')
check_mono('ezgi_alti_DELIVERED_FILE (clarinet+glockenspiel; lowest strong spectral peak 200-3000 Hz)', 'alt', peak_table(ez.mean(1), 200, 3000, 15, wide=(200, 8000)), check_held=False)
do_g = check_mono('lead_glockenspiel (strongest spectral peak in 500-1500 Hz)', 'lead', peak_table(ST['glockenspiel'].mean(1), 500, 1500, 0), check_held=False)
do_g2 = check_mono('ezgi_alti_glockenspiel_hafif (strongest spectral peak in 700-1700 Hz)', 'alt', peak_table(ST['glockenspiel_hafif'].mean(1), 700, 1700, 0), check_held=False)
R['octaves'] = dict(lead_trumpet_do=nm(do_lead), lead_glock_do=nm(do_g), glock_minus_trumpet=int(do_g - do_lead), alt_clarinet_do=nm(do_alt), alt_glock_do=nm(do_g2), alt_glock_minus_clarinet=int(do_g2 - do_alt),
                    lead_do_pitch_class_is_tonic=bool(do_lead % 12 == TON), alt_do_pitch_class_is_tonic=bool(do_alt % 12 == TON))
P('[1] octaves:', R['octaves'])
# brass doubling in the lead bars: lowest strong spectral peak
def low_peak(x, t):
    n = 8192; i0 = int(round((t + .03) * sr)); seg = x[i0:i0 + n]
    if len(seg) < n: return 0.0
    A = np.abs(np.fft.rfft(seg * np.hanning(n), 4 * n)); fr = np.fft.rfftfreq(4 * n, 1 / sr); A[fr < 80] = 0
    pk = np.where((A[1:-1] > A[:-2]) & (A[1:-1] > A[2:]) & (A[1:-1] > A.max() * 10 ** (-22 / 20)))[0] + 1
    return float(f2m(fr[pk[0]])) if len(pk) else 0.0
bm = ST['brass'].mean(1); okb = 0; nb = 0; badb = []
for b, k in enumerate(KIND):
    E = PHA if k == 'iA' else ANS if k in ('iANS', 'ans') else {}
    for s, (iv, a) in E.items():
        if not a: continue
        m = low_peak(bm, b * BAR + s * BEAT / 2); nb += 1
        if abs(m - (do_lead + iv - 12)) < 0.4: okb += 1
        else: badb.append((b, s, nm(m), nm(do_lead + iv - 12)))
R['brass_octave_below'] = dict(checked=nb, ok=okb, bad=badb[:10]); P(f'[1] brass stem, lowest strong partial at each lead attack = lead note one octave below: {okb}/{nb}; exceptions {badb[:6]}')

# ---------- 2. bass notes per beat and chords per beat -----------------------------------------------------
bmono = ST['bas'].mean(1); f, tf = yin_track(bmono, 50, 320, 4096)
bass = {}
for b, k in enumerate(KIND):
    row = []
    for s in range(8):
        t = b * BAR + s * BEAT / 2; lev = rms(bmono[int((t + .04) * sr):int((t + .2) * sr)]); m = (tf >= t + .05) & (tf <= t + .2)
        row.append((float(np.median(f2m(f[m]))), lev, dip_db(bmono, t) if t > .06 else 99.0))
    bass.setdefault(k, []).append(row)
bref = np.percentile([c[1] for rows in bass.values() for r_ in rows for c in r_], 90)
DEGN = {0: '1', 2: '2', 4: '3', 5: '4', 7: '5', 9: '6', 11: '7'}
ROOTPC = {'I': 0, 'IV': 5, 'V7': 7}
R['bass'] = {}
P('[2] bass stem, detected scale degree (1 = tonic) on each eighth slot per bar kind (all bars of that kind agree unless listed; "-" = no new note):')
for k, rows in bass.items():
    seqs = set();
    for r_ in rows:
        seqs.add(' '.join((DEGN.get(int(round(m - TON)) % 12, '?') + f'({nm(m)})') if (db(l) - db(bref) > -18 and (rise > 3 or (j > 0 and abs(m - r_[j - 1][0]) > .5))) else '-' for j, (m, l, rise) in enumerate(r_)))
    exp = [ROOTPC[d] for d in DEGS[k].split()]
    onbeat = [[int(round(r_[2 * i][0] - TON)) % 12 for i in range(4)] for r_ in rows]
    on_att = [[(db(r_[2 * i][1]) - db(bref) > -18 and (r_[2 * i][2] > 3 or (i > 0 and abs(r_[2 * i][0] - r_[2 * i - 1][0]) > .5))) for i in range(4)] for r_ in rows]
    dev = sorted({(i, DEGN.get(o[i], '?')) for o, a in zip(onbeat, on_att) for i in range(4) if a[i] and o[i] != exp[i]})
    R['bass'][k] = dict(patterns=sorted(seqs), expected_root_degrees=DEGS[k], on_beat_not_root=[f'beat {i}: degree {d}' for i, d in dev])
    P(f'    {k:5s} [{DEGS[k]:12s}] bars {len(rows):2d}: ' + ' || '.join(sorted(seqs)) + (f'   <-- on-beat bass note is NOT the chord root at {R["bass"][k]["on_beat_not_root"]}' if dev else ''))
bl = [db(c[1]) for k in ('slot',) for r_ in bass[k] for c in (r_[0], r_[4])]; bn = [db(c[1]) for k in ('voc', 'ans') for r_ in bass[k] for c in (r_[0], r_[4])]
R['bass_slot_vs_normal_db'] = float(np.mean(bl) - np.mean(bn)); P(f'    bass level in slot bars (beats 0, 2) vs normal bars: {R["bass_slot_vs_normal_db"]:+.1f} dB')

def chroma(x, t0, t1):
    seg = x[int(round(t0 * sr)):int(round(t1 * sr))]; n = 32768
    A = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n)) ** 2; fr = np.fft.rfftfreq(n, 1 / sr); sel = (fr > 110) & (fr < 2100)
    pc = np.round(f2m(fr[sel])).astype(int) % 12; c = np.bincount(pc, weights=A[sel], minlength=12)
    return c
TPL = {'I': [0, 4, 7], 'IV': [5, 9, 0], 'V7': [7, 11, 2, 5]}
def best_chord(c):
    c = np.roll(c, -TON); sc = {}
    for k, v in TPL.items():
        t = np.zeros(12); t[v] = 1; sc[k] = float(np.dot(c, t) / (np.linalg.norm(c) * np.linalg.norm(t) + 1e-20))
    return max(sc, key=sc.get), sc
comp = (ST['banjo'] + ST['akordeon'] + ST['piyano']).mean(1); cref = rms(comp)
for label, sig in (('comp stems (banjo+accordion+piano)', comp), ('full altyapi mix', alt_del.mean(1))):
    tot = 0; ok = 0; bad = {}; skipped = 0
    for b, k in enumerate(KIND):
        for i, d in enumerate(DEGS[k].split()):
            t = b * BAR + i * BEAT
            if label.startswith('comp') and rms(comp[int(t * sr):int((t + BEAT) * sr)]) < cref * 10 ** (-25 / 20): skipped += 1; continue
            if not label.startswith('comp') and k in ('slot',): skipped += 1; continue
            ch, sc = best_chord(chroma(sig, t + .02, t + BEAT - .01)); tot += 1
            if ch == d: ok += 1
            else: bad.setdefault(f'{k} beat {i}: expected {d}, detected {ch}', []).append(b)
    R['chords_' + label.split()[0]] = dict(beats_checked=tot, match=ok, skipped_quiet=skipped, mismatches={k: len(v) for k, v in bad.items()})
    P(f'[2] chord per beat by chroma template (I / IV / V7), {label}: {ok}/{tot} beats match the task; skipped {skipped} (no chord instrument / slot bars); mismatches: {{' + ', '.join(f"{k}: {len(v)}x" for k, v in bad.items()) + '}')

# ---------- 3. thin bars and the fill -----------------------------------------------------------------------
MEL = ('banjo', 'akordeon', 'piyano', 'glockenspiel', 'trompet', 'brass')
g = float(np.dot(alt_del[int(18.4 * sr):int(20 * sr)].ravel(), band[int(18.4 * sr):int(20 * sr)].ravel()) / np.dot(band[int(18.4 * sr):int(20 * sr)].ravel(), band[int(18.4 * sr):int(20 * sr)].ravel()))
R['master_gain_estimated_db'] = float(db(g)); P(f'[3] master gain estimated in a quiet slot bar (delivered / raw band): {db(g):.2f} dB')
def lv(x, t0, t1): return float(db(rms(x[int(round(t0 * sr)):int(round(t1 * sr))]) * g))
rows = {}
for v in range(7):
    v0 = (4 + 8 * v) * BAR
    W = {'slot bar 3, first 250 ms': (v0 + 3 * BAR, v0 + 3 * BAR + .25), 'slot bar 3, 0.25 s .. end': (v0 + 3 * BAR + .25, v0 + 4 * BAR), 'slot bar 4, whole': (v0 + 4 * BAR, v0 + 5 * BAR),
         'bar 5 beats 0-1': (v0 + 5 * BAR, v0 + 5 * BAR + 2 * BEAT - .03), 'bar 5 beats 2-3': (v0 + 5 * BAR + 2 * BEAT, v0 + 6 * BAR), 'normal bar 0': (v0, v0 + BAR)}
    for wn, (t0, t1) in W.items():
        rows.setdefault(wn, []).append([lv(sum(ST[n] for n in MEL), t0, t1), lv(ST['davul'], t0, t1), lv(ST['bas'], t0, t1), lv(band, t0, t1)] + [lv(ST[n], t0, t1) for n in MEL])
R['windows_db'] = {}
P('[3] levels after master gain, dBFS RMS, max over the 7 verses: [chord+melody stems together | drums | bass | whole band | ' + ' '.join(MEL) + ']')
for wn, v in rows.items():
    mx = np.max(v, 0); R['windows_db'][wn] = [round(float(x), 1) for x in mx]; P(f'    {wn:26s} ' + ' '.join(f'{x:7.1f}' for x in mx))
# drum content of the thin bars: band-limited levels of the drum stem per beat (kick < 120 Hz, snare/clap 180-400 Hz + 2-5 kHz, hats > 7 kHz)
def bp(x, lo, hi):
    sos = butter(4, [lo, hi], 'band', fs=sr, output='sos') if lo else butter(4, hi, 'low', fs=sr, output='sos'); return sosfiltfilt(sos, x)
dm = ST['davul'].mean(1) * g; bands_ = {'<120 Hz': bp(dm, None, 120), '180-400 Hz': bp(dm, 180, 400), '2-5 kHz': bp(dm, 2000, 5000), '7-14 kHz': bp(dm, 7000, 14000)}
P('[3] drum stem per beat (first 150 ms), mean over bars of a kind, dBFS: beats 0 1 2 3')
R['drum_bands'] = {}
for k in ('voc', 'slot', 'fill'):
    for bn_, xb in bands_.items():
        v = np.mean([[db(rms(xb[int((b * BAR + i * BEAT) * sr):int((b * BAR + i * BEAT + .15) * sr)])) for i in range(4)] for b, kk in enumerate(KIND) if kk == k], 0)
        R['drum_bands'][f'{k} {bn_}'] = [round(float(x), 1) for x in v]; P(f'    {k:5s} {bn_:11s} ' + ' '.join(f'{x:7.1f}' for x in v))
# sixteenth-note onsets of the fill (beats 0-1 of bar 5) in the drum stem
e = np.sqrt(np.convolve(bp(ST['davul'].mean(1), 150, 6000) ** 2, np.ones(88) / 88, 'same')); cnt = []
for b, k in enumerate(KIND):
    if k != 'fill': continue
    hits = 0
    for i in range(8):
        t = b * BAR + i * BEAT / 4; a = e[int((t + .002) * sr):int((t + .04) * sr)].max(); p = e[int((t - .03) * sr):int((t - .003) * sr)].mean()
        hits += (db(a) - db(p) > 6)
    cnt.append(int(hits))
R['fill_sixteenth_hits_per_bar5'] = cnt; P(f'[3] drum fill: sixteenth slots in beats 0-1 of bar 5 with a new drum hit (of 8), per verse: {cnt}')

# ---------- 4. onset timing of each stem against the grid --------------------------------------------------
def half_onsets(x, slots, lo=None, hi=None, frac=.5):
    m = x.mean(1); m = bp(m, lo, hi) if hi else m
    e = np.sqrt(np.convolve(m ** 2, np.ones(132) / 132, 'same')); out = []
    for t in slots:
        a = int(round((t - .045) * sr)); b_ = int(round((t + .11) * sr))
        if a < 0: continue
        w = e[a:b_]; base = e[max(0, a - 400):a + 1].mean(); pk = w.max()
        if pk < 4 * base or pk < 1e-4: continue
        i = int(np.argmax(w >= base + frac * (pk - base))); out.append(1000 * (a + i - 66) / sr - 1000 * t + 1000 * 66 / sr)
    return np.array(out)
beats_full = [b * BAR + i * BEAT for b, k in enumerate(KIND) if k in ('voc', 'ans', 'iA', 'iANS') for i in range(4)]
on_lead = [b * BAR + s * BEAT / 2 for b, k in enumerate(KIND) for s, (iv, a) in (PHA if k == 'iA' else ANS if k in ('iANS', 'ans') else {}).items() if a and b > 0]
on_alt = [b * BAR + s * BEAT / 2 for b, k in enumerate(KIND) for s, (iv, a) in (PHA if k == 'voc' else DOREP if k == 'fill' else {}).items() if a]
R['onsets_ms'] = {}
P('[4] onset minus my grid, ms (10 % rise point | 50 % rise point: median, min, max, n):')
for name, x, slots, lo, hi in (('kick (drums < 150 Hz)', ST['davul'], beats_full[4:], None, 150), ('drums 2-12 kHz (hat/snare)', ST['davul'], beats_full[4:], 2000, 12000), ('bass', ST['bas'], beats_full[4:], None, None), ('bass < 250 Hz', ST['bas'], beats_full[4:], None, 250),
                               ('banjo', ST['banjo'], beats_full[4:], None, None), ('piano (beats 0, 2)', ST['piyano'], beats_full[4::2], None, None), ('accordion (beats 1, 3)', ST['akordeon'], beats_full[5::2], None, None),
                               ('trumpet', ST['trompet'], on_lead, None, None), ('brass', ST['brass'], on_lead, None, None), ('glockenspiel', ST['glockenspiel'], on_lead, None, None),
                               ('clarinet (under-vocal)', ST['klarnet'], on_alt, None, None), ('light glockenspiel (under-vocal)', ST['glockenspiel_hafif'], on_alt, None, None)):
    o10 = half_onsets(x, slots, lo, hi, .1); o50 = half_onsets(x, slots, lo, hi, .5)
    R['onsets_ms'][name] = dict(n=len(o50), p10_median=float(np.median(o10)), p50_median=float(np.median(o50)), p50_min=float(o50.min()), p50_max=float(o50.max()))
    P(f'    {name:34s} 10 %: {np.median(o10):+6.1f} | 50 %: {np.median(o50):+6.1f} ({o50.min():+6.1f} .. {o50.max():+6.1f}), n = {len(o50)}')
# drift of the kick over the whole song
ok_ = half_onsets(ST['davul'], [b * BAR for b in range(1, 63)], None, 150, .5)
R['kick_downbeat_first8_ms'] = float(ok_[:8].mean()); R['kick_downbeat_last8_ms'] = float(ok_[-8:].mean())
P(f'    kick on bar downbeats: first 8 bars {ok_[:8].mean():+.2f} ms, last 8 bars {ok_[-8:].mean():+.2f} ms (difference = drift over the song {ok_[-8:].mean() - ok_[:8].mean():+.2f} ms)')

# ---------- 5. limiter action: delivered altyapi vs gain-only band ------------------------------------------
w = int(.01 * sr); nb_ = N // w
ed = np.sqrt((alt_del[:nb_ * w].reshape(nb_, w, 2) ** 2).mean((1, 2))); eb = np.sqrt(((band[:nb_ * w] * g).reshape(nb_, w, 2) ** 2).mean((1, 2)))
gr = db(eb) - db(ed); gr[eb < 10 ** (-40 / 20)] = 0; tt = np.arange(nb_) * .01
per = {}
for b, k in enumerate(KIND):
    m = (tt >= b * BAR) & (tt < (b + 1) * BAR); per.setdefault(k, []).append((float(gr[m].max()), float((gr[m] > 1).mean()), float((gr[m] > 3).mean())))
R['limiter'] = {k: dict(max_gr_db=round(max(x[0] for x in v), 2), mean_frac_gt1db=round(float(np.mean([x[1] for x in v])), 3), mean_frac_gt3db=round(float(np.mean([x[2] for x in v])), 3)) for k, v in per.items()}
P('[5] limiter gain reduction (10 ms windows) per bar kind: max dB, share of time > 1 dB, > 3 dB')
for k, v in R['limiter'].items(): P(f'    {k:5s} max {v["max_gr_db"]:5.2f} dB, >1 dB {100 * v["mean_frac_gt1db"]:5.1f} %, >3 dB {100 * v["mean_frac_gt3db"]:5.1f} %')
json.dump(R, open(OUTJ, 'w'), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
