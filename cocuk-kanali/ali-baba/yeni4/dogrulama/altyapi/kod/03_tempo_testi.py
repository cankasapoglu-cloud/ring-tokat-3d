#!/usr/bin/env python3
# Tempo scaling test: my own render at another tempo (build.py --bpm 105.30 --key G) against the delivered 104.96 files.
# Every numeric leaf of the two zaman json files is classified WITHOUT looking at key names:
#   equal | scaled by old_bar/new_bar (a time on the grid) | anything else (listed and explained by hand below).
# Then the tempo is measured blind in the new audio.
# usage: 03_tempo_testi.py <delivered folder> <new folder> <key> <out json>
import sys, json
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt, find_peaks

OLD, NEW, KEY, OUTJ = sys.argv[1:5]
P = lambda *a: print(*a, flush=True)
zo = json.load(open(f'{OLD}/zaman_{KEY}.json')); zn = json.load(open(f'{NEW}/zaman_{KEY}.json'))
bo, bn = zo['tempo_bpm'], zn['tempo_bpm']; ratio = bo / bn
R = dict(old_bpm=bo, new_bpm=bn, ratio=ratio)
leaves = []
def walk(a, b, path):
    if isinstance(a, dict):
        assert isinstance(b, dict) and list(a.keys()) == list(b.keys()), path
        for k in a: walk(a[k], b[k], path + '/' + k)
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, f'{path}[{i}]')
    else: leaves.append((path, a, b))
walk(zo, zn, '')
eq = sc = 0; other = []; worst = 0.0; zero_t = 0
for p, a, b in leaves:
    num = isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float))
    if a == b: eq += 1; continue
    if num and abs(b - a * ratio) < 2e-4: sc += 1; worst = max(worst, abs(b - a * ratio)); continue
    other.append((p, a, b))
R.update(leaves=len(leaves), equal=eq, scaled=sc, scaled_max_err_ms=1000 * worst, other=[(p, a, b) for p, a, b in other])
P(f'json leaves {len(leaves)}: equal {eq}, scaled by {ratio:.8f} (old/new bpm) {sc} (largest error {1000 * worst:.3f} ms), other {len(other)}')
for p, a, b in other: P(f'    OTHER {p}: {a} -> {b}' + (f'   (old*ratio = {a * ratio:.4f})' if isinstance(a, (int, float)) else ''))
# which of the EQUAL numeric leaves look like times (keys that scale elsewhere)?  -> a time that failed to scale would hide here
import re
scaled_keys = set();
for p, a, b in leaves:
    if a != b and isinstance(a, (int, float)): scaled_keys.add(re.sub(r'\[\d+\]', '', p).split('/')[-1])
susp = [(p, a) for p, a, b in leaves if a == b and isinstance(a, (int, float)) and not isinstance(a, bool) and re.sub(r'\[\d+\]', '', p).split('/')[-1] in scaled_keys and a != 0]
R['keys_that_scale'] = sorted(scaled_keys); R['equal_leaves_under_scaling_keys_nonzero'] = susp[:20]
P('keys whose values changed:', sorted(scaled_keys)); P(f'non-zero values under those keys that did NOT change (would be unscaled times): {len(susp)} {susp[:10]}')

# ---- explicit recomputation of the grid in the new json from 105.30 --------------------------------------
BEAT = 60 / bn; BAR = 4 * BEAT; err = 0
bars = zn['giris']['olculer'] + [o for kv in zn['kitalar'] for o in kv['olculer']] + zn['bitis']['olculer']
for i, o in enumerate(bars):
    err = max(err, abs(o['baslangic'] - i * BAR), abs(o['bitis'] - (i + 1) * BAR), *[abs(t - (i * BAR + j * BEAT)) for j, t in enumerate(o['vurus_zamanlari'])])
for n in zn['ezgi_notalari']: err = max(err, abs(n['baslangic'] - (n['olcu'] * BAR + n['vurus'] * BEAT)))
for v, kv in enumerate(zn['kitalar']):
    v0 = (4 + 8 * v) * BAR
    err = max(err, abs(kv['baslangic'] - v0), abs(kv['hayvan_sesi']['ses1_baslangic'] - (v0 + 3 * BAR)), abs(kv['hayvan_sesi']['ses2_baslangic'] - (v0 + 4 * BAR)), abs(kv['diye_bagirir']['baslangic'] - (v0 + 5 * BAR + 2 * BEAT)),
              abs(kv['satir4']['baslangic'] - (v0 + 6 * BAR)), abs(kv['cevap2']['baslangic'] - (v0 + 7 * BAR)), abs(kv['hayvan_sesi']['ses_basina_yer_sn'] - BAR))
R['new_json_grid_max_err_ms'] = 1000 * err; R['new_bars'] = len(bars)
P(f'new json: {len(bars)} bars; all bar/beat/note/verse-anchor times vs my arithmetic at {bn} BPM (bar {BAR:.6f} s): max error {1000 * err:.3f} ms (json is rounded to 0.1 ms)')
inf = sf.info(f'{NEW}/altyapi_{KEY}.wav'); dur = inf.frames / inf.samplerate
exp_dur = 63 * BAR + 3 * BEAT + zn['kuyruk_sn']
R.update(new_file_s=dur, new_file_expected_s=exp_dur, new_file_json_s=zn['dosya_suresi_sn'])
P(f'new file: {dur:.4f} s; expected final hit (63 bars + 3 beats = {63 * BAR + 3 * BEAT:.4f}) + tail {zn["kuyruk_sn"]} = {exp_dur:.4f}; json says {zn["dosya_suresi_sn"]}')

# ---- blind tempo of the new audio ---------------------------------------------------------------------------
x, sr = sf.read(f'{NEW}/altyapi_{KEY}.wav'); mono = x.mean(1)
def grid(mono, lo, hi, T0):
    xb = sosfiltfilt(butter(4, [lo, hi], 'band', fs=sr, output='sos'), mono); hop, win = 64, 256
    n = (len(xb) - win) // hop; e = np.sqrt((xb[np.arange(n)[:, None] * hop + np.arange(win)[None, :]] ** 2).mean(1)); dt = hop / sr
    es = np.convolve(e, np.ones(3) / 3, 'same'); d = np.diff(es, prepend=es[0]); d[d < 0] = 0
    pk, _ = find_peaks(d, height=.15 * d.max(), distance=int(.12 / dt)); t = pk * dt + win / 2 / sr
    w = d[pk]; bpms = np.arange(90.0, 120.0, 0.002); best = (0, None)       # blind period scan (Rayleigh), eighth-note grid, no prior tempo
    for i in range(0, len(bpms), 2000):
        Tc = 30 / bpms[i:i + 2000]; sc = np.abs((w[None, :] * np.exp(2j * np.pi * t[None, :] / Tc[:, None])).sum(1)); j = int(np.argmax(sc))
        if sc[j] > best[0]: best = (float(sc[j]), float(Tc[j]))
    T = best[1]; scan_bpm = 30 / T
    for it in range(8):
        if it == 0:
            a = max(((np.sum(np.abs(t - (a0 + np.round((t - a0) / T) * T)) < .02), a0) for a0 in np.linspace(0, T, 100, endpoint=False)))[1]
        k = np.round((t - a) / T); r = t - (a + k * T); m = np.abs(r) < .02
        (a, T), *_ = np.linalg.lstsq(np.vstack([np.ones(m.sum()), k[m]]).T, t[m], rcond=None)
    k = np.round((t - a) / T); r = t - (a + k * T); m = np.abs(r) < .02
    return float(a), float(T), int(m.sum()), float(1000 * r[m].std()), scan_bpm, len(t)
out = {}
for lo, hi, lab in ((6000, 14000, '6-14 kHz onsets (hat/snare/tambourine)'), (2000, 5000, '2-5 kHz onsets')):
    a, T, n, sd, scan_bpm, nt = grid(mono, lo, hi, None); bpm = 30 / T
    out[lab] = dict(scan_bpm=scan_bpm, bpm=bpm, n_onsets=nt, n_on_grid=n, sd_ms=sd, phase_ms=1000 * ((a + T / 2) % T - T / 2), bar_s=8 * T, total_diff_ms=1000 * (8 * T - BAR) * 64)
    P(f'blind grid of the NEW audio, {lab}: scan 90-120 BPM -> {scan_bpm:.3f}; refined {bpm:.4f} BPM (bar {8 * T:.6f} s), {n}/{nt} onsets on the grid, sd {sd:.2f} ms, phase {out[lab]["phase_ms"]:+.2f} ms; difference to {bn} BPM accumulated over 64 bars: {out[lab]["total_diff_ms"]:+.2f} ms')
R['blind_grid_new_audio'] = out
# the same audio against the OLD grid: how far would the last verse be off if the tempo had not changed
R['old_vs_new_last_verse_start_ms'] = 1000 * (52 * 240 / bo - 52 * BAR)
P(f'for scale: bar 52 (verse 7) starts {52 * BAR:.4f} s in the new grid vs {52 * 240 / bo:.4f} s in the old one ({R["old_vs_new_last_verse_start_ms"]:+.1f} ms)')
json.dump(R, open(OUTJ, 'w'), indent=1, ensure_ascii=False)
