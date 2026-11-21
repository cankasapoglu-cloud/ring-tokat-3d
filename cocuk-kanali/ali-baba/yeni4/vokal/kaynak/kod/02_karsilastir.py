# Objective comparison of the separated-vocal candidates of v2_2 (nobody can listen here).
#   usage: python3 02_karsilastir.py            -> gecici/karsilastir.json (+ printed tables)
# All stems are first divided by the separator's input gain g (from 03_hizala.py, sum check), so that
# "stem / mix" ratios are true attenuations.  Mono = (L+R)/2 everywhere.
# (a) bleed        : level in the purely instrumental stretches; beat-synchronous kick / hi-hat residue in sung bars
# (b) completeness : consonant high-frequency retention, long-term spectrum / band holes, vocal energy left behind in
#                    the instrumental (against a loop template of the band), short isolated tonal peaks (musical noise)
# (c) agreement    : candidate against candidate in the sung parts (only when two candidates exist)
import sys, json, numpy as np, scipy.signal as ss, scipy.ndimage as ndi
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *

P = stem_paths()
names = list(P.keys())
x = load_mix(); N = len(x)
R = regions()
words = load_words()
segs = TEMPO['segments']
C = {}; G = {}
for nm in names:
    hz = json.load(open(f'{CACHE}/hizala_{nm}.json'))
    g = hz['sum_check']['gain_stems_over_mix'] if 'sum_check' in hz else None
    v = load_stem(P[nm]['vocals'])[:N]
    if g is None:           # no instrumental stem: least-squares gain is meaningless for a vocal stem -> use 1
        g = 1.0
    G[nm] = g; C[nm] = v / g
print('candidates:', names, 'gains', G)
m_sw = mask_from(R['sung_words'], N); m_sb = mask_from(R['sung_bars'], N); m_in = mask_from(R['inst'], N); m_tl = mask_from(R['tails'], N); m_pre = mask_from(R['pre'], N)
BANDS = [(40, 120), (120, 300), (300, 1000), (1000, 3000), (3000, 6000), (6000, 10000), (10000, 16000)]
bn = lambda b: f'{b[0]}-{b[1]}'
out = dict(candidates={nm: dict(file=P[nm]['vocals'], separator_gain=G[nm]) for nm in names},
           regions={k: [[round(a, 4), round(b, 4)] for a, b in v] for k, v in R.items() if k != 'sung_words'},
           notes=dict(scale='all stems divided by the separator gain (stems are on the scale of the ffmpeg mix, mono = (L+R)/2)',
                      sung='sung = the 105 word intervals of v2_2_words.json', inst='inst = purely instrumental stretches with margins (see regions)'))

# ------------------------------------------------------------------ (a1) levels
print('\n(a1) LEVELS  (dB; "rel" = relative to the candidate\'s own full-band RMS over the sung word intervals)')
A1 = {}
mixb = {bn(b): bandpass(x, *b) for b in BANDS}
for nm in names + ['mix']:
    v = C[nm] if nm != 'mix' else x
    d = dict(sung_rms_dbfs=rms_db(v[m_sw]), inst_rms_dbfs=rms_db(v[m_in]), tail_rms_dbfs=rms_db(v[m_tl]), pre_rms_dbfs=rms_db(v[m_pre]))
    d['pre_rel_sung_db'] = d['pre_rms_dbfs'] - d['sung_rms_dbfs']
    d['pre_per_verse_rel_sung_db'] = [rms_db(v[int(a * SR):int(b * SR)]) - d['sung_rms_dbfs'] for a, b in R['pre']]
    d['inst_rel_sung_db'] = d['inst_rms_dbfs'] - d['sung_rms_dbfs']
    d['tail_rel_sung_db'] = d['tail_rms_dbfs'] - d['sung_rms_dbfs']
    d['per_stretch'] = []
    for a, b in R['inst']:
        s = v[int(a * SR):int(b * SR)]
        # worst 50 ms burst
        w = int(0.05 * SR); p = np.convolve(s ** 2, np.ones(w) / w, mode='valid'); k = int(np.argmax(p))
        d['per_stretch'].append(dict(t0=round(a, 3), t1=round(b, 3), rms_dbfs=rms_db(s), rel_sung_db=rms_db(s) - d['sung_rms_dbfs'],
                                     worst_50ms_rel_sung_db=float(db(p[k]) - d['sung_rms_dbfs']), worst_50ms_t=round(a + (k + w / 2) / SR, 3)))
    d['bands'] = {}
    for b in BANDS:
        vb = bandpass(v, *b) if nm != 'mix' else mixb[bn(b)]
        e = dict(inst_rel_sung_db=rms_db(vb[m_in]) - d['sung_rms_dbfs'], sung_band_rel_sung_db=rms_db(vb[m_sw]) - d['sung_rms_dbfs'])
        if nm != 'mix':
            e['inst_attenuation_vs_mix_db'] = rms_db(vb[m_in]) - rms_db(mixb[bn(b)][m_in])
            e['sung_ratio_vs_mix_db'] = rms_db(vb[m_sw]) - rms_db(mixb[bn(b)][m_sw])
        d['bands'][bn(b)] = e
    if nm != 'mix':
        d['inst_attenuation_vs_mix_db'] = d['inst_rms_dbfs'] - rms_db(x[m_in])
    A1[nm] = d
    print(f"  {nm:4s}: sung {d['sung_rms_dbfs']:6.1f} dBFS | inst {d['inst_rms_dbfs']:6.1f} dBFS = {d['inst_rel_sung_db']:6.1f} rel | tail {d['tail_rel_sung_db']:6.1f} rel | breath zone {d['pre_rel_sung_db']:6.1f} rel"
          + (f" | attenuation of the band in the inst stretches {d['inst_attenuation_vs_mix_db']:6.1f} dB" if nm != 'mix' else ''))
    print('        per stretch rel dB:', ' '.join(f"{s['rel_sung_db']:6.1f}" for s in d['per_stretch']),
          '| worst 50 ms:', ' '.join(f"{s['worst_50ms_rel_sung_db']:5.1f}@{s['worst_50ms_t']:.1f}" for s in d['per_stretch']))
    if nm != 'mix':
        print('        bands inst rel sung :', ' '.join(f"{bn(b)}:{d['bands'][bn(b)]['inst_rel_sung_db']:6.1f}" for b in BANDS))
        print('        bands inst att vs mix:', ' '.join(f"{bn(b)}:{d['bands'][bn(b)]['inst_attenuation_vs_mix_db']:6.1f}" for b in BANDS))
out['a1_levels'] = A1

# ------------------------------------------------------------------ (a2) beat-synchronous residue in sung bars
print('\n(a2) BEAT-SYNCHRONOUS RESIDUE IN THE SUNG BARS (median over the 112 beats of the 28 sung bars; folds at the beat period)')
beats_sung = []
for d0 in VERSE_DB:
    for k in range(16):
        beats_sung.append(d0 + k * BEAT)
beats_inst = []
for d0 in VERSE_DB[:-1]:
    for k in range(17, 23):          # beats of the instrumental bars 4,5 well inside the 'inst' stretch
        beats_inst.append(d0 + k * BEAT)
PHS = np.arange(0, BEAT, 0.004)


def env(y, smooth_ms):
    sos = ss.butter(2, 1000.0 / smooth_ms / (2 * np.pi), btype='low', fs=SR, output='sos')
    return np.sqrt(np.maximum(ss.sosfiltfilt(sos, y ** 2), 0))


def fold(e, beats):
    t = np.arange(len(e)) / SR
    M = np.array([np.interp(b + PHS, t, e) for b in beats])
    return M


A2 = {}
for label, band, sm in (('kick_40_120', (40, 120), 12.0), ('hat_8k_16k', (8000, 16000), 5.0)):
    A2[label] = {}
    em = env(bandpass(x, *band), sm)
    Fm = fold(em, beats_sung); pm = np.median(Fm, 0)
    Fmi = fold(em, beats_inst); pmi = np.median(Fmi, 0)
    kpk = int(np.argmax(pmi))                    # phase of the drum hit, taken from the mix in the instrumental bars
    A2[label]['mix'] = dict(peak_phase_ms_inst_bars=float(PHS[kpk] * 1000), profile_peak_sung_bars=float(pm.max()),
                            mod_depth_db_sung_bars=float(20 * np.log10(pm.max() / np.percentile(pm, 20))),
                            mod_depth_db_inst_bars=float(20 * np.log10(pmi.max() / np.percentile(pmi, 20))))
    print(f"  {label}: drum hit in the mix at {PHS[kpk]*1000:.0f} ms after the beat; mix modulation depth {A2[label]['mix']['mod_depth_db_inst_bars']:.1f} dB (inst bars)")
    for nm in names:
        v = C[nm]; e = env(bandpass(v, *band), sm)
        F = fold(e, beats_sung); p = np.median(F, 0); Fi = fold(e, beats_inst); pi_ = np.median(Fi, 0)
        sung = 10 ** (A1[nm]['sung_rms_dbfs'] / 20)
        win = (np.abs(PHS - PHS[kpk]) <= 0.03)                      # +-30 ms around the hit
        if label.startswith('hat'):                                 # hats: beat and off-beat eighth
            win |= (np.abs(PHS - (PHS[kpk] + BEAT / 2) % BEAT) <= 0.03)
        pk = float(p[win].max()); fl = float(np.percentile(p, 20))
        pkm = float(pm[win].max())
        # complex modulation index at the beat rate and twice the beat rate over the sung bars (mean over beats)
        ph = np.exp(-2j * np.pi * PHS / BEAT); ph2 = np.exp(-4j * np.pi * PHS / BEAT)
        mi1 = float(np.abs((F * ph).sum()) / F.sum()); mi2 = float(np.abs((F * ph2).sum()) / F.sum())
        mim1 = float(np.abs((Fm * ph).sum()) / Fm.sum()); mim2 = float(np.abs((Fm * ph2).sum()) / Fm.sum())
        d = dict(peak_at_hit_rel_sung_db=float(20 * np.log10(pk / sung)), floor_rel_sung_db=float(20 * np.log10(fl / sung)),
                 mod_depth_db=float(20 * np.log10(pk / fl)), attenuation_of_hit_vs_mix_db=float(20 * np.log10(pk / pkm)),
                 band_rms_in_sung_bars_rel_sung_db=float(rms_db(bandpass(v, *band)[m_sb]) - A1[nm]['sung_rms_dbfs']),
                 modulation_index_beat_rate=mi1, modulation_index_2x_beat_rate=mi2,
                 mix_modulation_index_beat_rate=mim1, mix_modulation_index_2x_beat_rate=mim2,
                 inst_bars_peak_rel_sung_db=float(20 * np.log10(pi_.max() / sung)),
                 profile_db_rel_sung=[round(float(20 * np.log10(max(q, 1e-9) / sung)), 1) for q in p[::5]])
        A2[label][nm] = d
        print(f"    {nm:4s}: median hit level {d['peak_at_hit_rel_sung_db']:6.1f} dB rel sung, floor {d['floor_rel_sung_db']:6.1f}, depth {d['mod_depth_db']:5.1f} dB, "
              f"attenuation vs mix {d['attenuation_of_hit_vs_mix_db']:6.1f} dB | band RMS in sung bars {d['band_rms_in_sung_bars_rel_sung_db']:6.1f} | "
              f"mod index 1x/2x {mi1:.3f}/{mi2:.3f} (mix {mim1:.3f}/{mim2:.3f})")
out['a2_beat_residue'] = A2

# (a2b) transient at the drum instants.  The voice has nothing at 40-120 Hz, so the kick fold above is already a clean
# bleed measure.  Above 8 kHz the voice has its own energy (air, sibilants) and syllables start on the same eighth grid,
# so the hat residue is measured as the RISE of the 8-16 kHz envelope at the hat instants (hit minus the point just
# before it), for all eighths (upper bound: syllable onsets add to it) and for the eighths where the voice itself is
# steady (300-3000 Hz envelope of the stems changes < 6 dB / < 3 dB within -50..+40 ms around the hit).
# A positive rise = hat bleed; a negative one = the separator carved a dip into the voice at the hat instant.
print('\n(a2b) TRANSIENT AT THE DRUM INSTANTS (envelope at the hit minus envelope just before it; median over hits)')
A2b = {}
vref = np.mean([C[nm] for nm in names], 0)
e_lf = env(bandpass(vref, 300, 3000), 8.0)
tt_all = np.arange(N) / SR
rng = np.random.default_rng(1)
TAU = np.array([-0.060, -0.040, -0.025, -0.014, -0.006, 0.0, 0.006, 0.012, 0.020, 0.030, 0.045, 0.060, 0.080])


def rise_stats(e, hits, php, phm):
    r = np.interp(np.array(hits) + php, tt_all, e) - np.interp(np.array(hits) + phm, tt_all, e)
    bs = [np.median(rng.choice(r, len(r))) for _ in range(400)]
    return float(np.median(r)), float(np.std(bs)), float(np.mean(r)), int(len(r))


def rel_profile(e, hits, php):
    """median over hits of the envelope around the hit, each hit normalised by its own mean over -80..+120 ms; dB"""
    rows = []
    for h in hits:
        i0, i1 = int((h + php - 0.08) * SR), int((h + php + 0.12) * SR)
        mloc = e[i0:i1].mean() + 1e-12
        rows.append(np.interp(h + php + TAU, tt_all, e) / mloc)
    return [round(float(v), 2) for v in 20 * np.log10(np.median(np.array(rows), 0) + 1e-12)]


for label, band, sm, per, pre in (('kick_40_120', (40, 120), 12.0, BEAT, (0.12, 0.02)), ('hat_8k_16k', (8000, 16000), 3.0, BEAT / 2, (0.07, 0.012))):
    em = env(bandpass(x, *band), sm)
    hits_inst = [d0 + k * per for d0 in VERSE_DB[:-1] for k in np.arange(int(round(4.25 * 4 * BEAT / per)), int(round(5.6 * 4 * BEAT / per)))]
    hits_sung = [d0 + k * per for d0 in VERSE_DB for k in range(int(round(16 * BEAT / per)))]
    phs = np.arange(0, per, 0.001)
    prof = np.median(np.array([np.interp(h + phs, tt_all, em) for h in hits_inst]), 0)
    kp = int(np.argmax(prof)); php = phs[kp]
    if php > per / 2: php -= per                       # hit phase as a small offset around the grid point
    cand = [(kp - int(d * 1000)) % len(phs) for d in np.arange(pre[1], pre[0], 0.001)]
    km = cand[int(np.argmin(prof[cand]))]; phm = php - ((kp - km) % len(phs)) * 0.001
    var = []
    for h in hits_sung:
        i0, i1 = int((h + php - 0.05) * SR), int((h + php + 0.04) * SR)
        sgm = e_lf[i0:i1]; var.append(20 * np.log10((sgm.max() + 1e-7) / (sgm.min() + 1e-7)))
    var = np.array(var)
    subsets = dict(all=list(hits_sung))
    if label.startswith('hat'):
        subsets['steady6'] = [h for h, q in zip(hits_sung, var) if q < 6.0]
        subsets['steady3'] = [h for h, q in zip(hits_sung, var) if q < 3.0]
    mi = rise_stats(em, hits_inst, php, phm)
    A2b[label] = dict(hit_phase_ms=float(php * 1000), pre_phase_ms=float(phm * 1000), n_hits_inst=mi[3], tau_ms=[float(t * 1000) for t in TAU],
                      mix=dict(median_rise_inst_bars=mi[0], rel_profile_db_inst_bars=rel_profile(em, hits_inst, php)))
    print(f"  {label}: hit at {php*1000:+.0f} ms from the grid point, reference point {phm*1000:+.0f} ms; mix profile in the instrumental bars (dB re local mean, tau = {[int(t*1000) for t in TAU]} ms):")
    print('        ', A2b[label]['mix']['rel_profile_db_inst_bars'])
    for nm in names:
        e = env(bandpass(C[nm], *band), sm); sung = 10 ** (A1[nm]['sung_rms_dbfs'] / 20)
        i_ = rise_stats(e, hits_inst, php, phm)
        A2b[label][nm] = dict(inst_bars_rise_vs_mix_db=float(20 * np.log10(max(i_[0], 1e-9) / mi[0])))
        for sub, hs in subsets.items():
            s_ = rise_stats(e, hs, php, phm); ms_ = rise_stats(em, hs, php, phm)
            d = dict(n_hits=s_[3], median_rise=s_[0], bootstrap_se=s_[1], mean_rise=s_[2],
                     median_rise_rel_sung_rms_db=float(20 * np.log10(abs(s_[0]) / sung + 1e-12)), sign=int(np.sign(s_[0])),
                     rise_vs_mix_inst_rise_db=float(20 * np.log10(max(s_[0], 1e-9) / mi[0])),
                     upper_bound_2se_vs_mix_db=float(20 * np.log10(max(s_[0] + 2 * s_[1], 1e-9) / mi[0])),
                     significant_positive=bool(s_[0] > 2 * s_[1]), significant_negative=bool(s_[0] < -2 * s_[1]),
                     mix_rise_same_hits_vs_inst_db=float(20 * np.log10(max(ms_[0], 1e-9) / mi[0])),
                     rel_profile_db=rel_profile(e, hs, php))
            A2b[label][nm][sub] = d
            print(f"    {nm:4s} {sub:8s} n={s_[3]:3d}: median rise {s_[0]:+.2e} (se {s_[1]:.1e}) -> {d['rise_vs_mix_inst_rise_db']:6.1f} dB vs the mix's drum rise "
                  f"(2 se upper bound {d['upper_bound_2se_vs_mix_db']:6.1f} dB; pos {d['significant_positive']}, neg {d['significant_negative']}); mix on the same hits {d['mix_rise_same_hits_vs_inst_db']:+.1f} dB")
            print(f"         profile dB: {d['rel_profile_db']}")
out['a2b_transient'] = A2b

# ------------------------------------------------------------------ bar-aligned power spectrograms + loop template
NF, HP = 2048, 512
nfr = int(np.ceil(BAR * SR / HP))
wn = ss.get_window('hann', NF)
fax = np.fft.rfftfreq(NF, 1 / SR)


def bar_spec(y, t_bar):
    s0 = int(round(t_bar * SR)); idx = s0 + np.arange(nfr)[:, None] * HP + np.arange(-NF // 2, NF // 2)[None, :]
    idx = np.clip(idx, 0, len(y) - 1)
    return (np.abs(np.fft.rfft(y[idx] * wn, axis=1)) ** 2 / (wn ** 2).sum()).astype(np.float32)      # [frame, bin] power


bars = [(vi, j, d0 + j * BAR) for vi, d0 in enumerate(VERSE_DB) for j in range(6)]
SPEC = {}
for nm in names + ['mix']:
    y = C[nm] if nm != 'mix' else x
    SPEC[nm] = np.array([bar_spec(y, t) for (_, _, t) in bars]).reshape(7, 6, nfr, len(fax))
for nm in names:
    SPEC['inst_' + nm] = np.array([bar_spec(x - C[nm], t) for (_, _, t) in bars]).reshape(7, 6, nfr, len(fax))
fr_t = np.arange(nfr) * HP / SR
bidx = [(fax >= b[0]) & (fax < b[1]) for b in BANDS]
# template of the band: median over the instrumental bars 4 (Dm C) and 5 (Gm A) of verses 1..6 (verse 7 = ending, left out)
TPL = {0: np.median(SPEC['mix'][:6, 4], 0), 1: np.median(SPEC['mix'][:6, 5], 0)}
loo = {bn(b): [] for b in BANDS}
for typ, jb in ((0, 4), (1, 5)):
    for vi in range(6):
        oth = [k for k in range(6) if k != vi]
        tp = np.median(SPEC['mix'][oth, jb], 0)
        for b, bi in zip(BANDS, bidx):
            e = db(SPEC['mix'][vi, jb][:, bi].sum(1) + 1e-12) - db(tp[:, bi].sum(1) + 1e-12)
            loo[bn(b)].append(e)
TPLQ = {k: dict(leave_one_out_mean_db=float(np.mean(np.concatenate(v))), leave_one_out_sd_db=float(np.std(np.concatenate(v))),
                p90_abs_db=float(np.percentile(np.abs(np.concatenate(v)), 90))) for k, v in loo.items()}
print('\nLOOP TEMPLATE of the band (median of the instrumental bars 4/5 of verses 1-6): leave-one-out error per frame, dB')
print('   ', ' '.join(f"{k}: sd {v['leave_one_out_sd_db']:.1f} (p90 {v['p90_abs_db']:.1f})" for k, v in TPLQ.items()))
out['template'] = dict(definition='power spectrogram (2048/512, frames aligned to the bar line) median over instrumental bars 4 and 5 of verses 1-6; '
                                  'sung bars 0 and 2 are compared with bar 4 (Dm C), sung bars 1 and 3 with bar 5 (Gm A)',
                       leave_one_out=TPLQ,
                       caveat='the template only describes the band if the accompaniment under the voice is the same loop as in the instrumental bars')

# frame masks inside sung bars
def frame_mask(vi, j, intervals, pad=0.0):
    t = VERSE_DB[vi] + j * BAR + fr_t; m = np.zeros(nfr, bool)
    for a, b in intervals:
        m |= (t >= a - pad) & (t <= b + pad)
    return m


sw = [(w['start'], w['end']) for w in words]
FM = np.array([[frame_mask(vi, j, sw) for j in range(4)] for vi in range(7)])       # sung-word frames [7,4,nfr]
TP4 = np.array([TPL[j % 2] for j in range(4)])                                      # template per sung bar [4,nfr,bin]
# does the template describe the band under the voice?  -> compare the instrumental stems with it in the sung bars
print('\n(b1) VOCAL ENERGY LEFT BEHIND: instrumental stem (mix - vocal stem) against the loop template, sung-word frames only')
B1 = {}
for nm in names:
    Pi = SPEC['inst_' + nm][:, :4]; Pv = SPEC[nm][:, :4]; Pm = SPEC['mix'][:, :4]
    d = {}
    for b, bi in zip(BANDS, bidx):
        pi_ = Pi[..., bi].sum(-1); pv = Pv[..., bi].sum(-1); pt = np.broadcast_to(TP4[..., bi].sum(-1), pi_.shape); pm_ = Pm[..., bi].sum(-1)
        ex = np.maximum(pi_ - pt, 0)[FM].sum(); vv = pv[FM].sum(); vexp = np.maximum(pm_ - pt, 0)[FM].sum()
        ratio_db = db(pi_[FM] + 1e-12) - db(pt[FM] + 1e-12)
        d[bn(b)] = dict(inst_over_template_median_db=float(np.median(ratio_db)), inst_over_template_p90_db=float(np.percentile(ratio_db, 90)),
                        excess_energy_rel_vocal_stem_db=float(db(ex) - db(vv)),
                        vocal_stem_energy_rel_mix_minus_template_db=float(db(vv) - db(vexp)))
    B1[nm] = d
    print(f"  {nm:4s} inst/template median dB :", ' '.join(f"{k}:{v['inst_over_template_median_db']:5.1f}" for k, v in d.items()))
    print(f"       inst/template p90 dB    :", ' '.join(f"{k}:{v['inst_over_template_p90_db']:5.1f}" for k, v in d.items()))
    print(f"       excess rel vocal stem dB:", ' '.join(f"{k}:{v['excess_energy_rel_vocal_stem_db']:5.1f}" for k, v in d.items()))
    print(f"       vocal stem / (mix-tpl) dB:", ' '.join(f"{k}:{v['vocal_stem_energy_rel_mix_minus_template_db']:5.1f}" for k, v in d.items()))
out['b1_left_behind'] = B1

# ------------------------------------------------------------------ (b2) consonants: high-frequency retention
print('\n(b2) CONSONANT HIGH-FREQUENCY RETENTION')
HB = [(2000, 4000), (4000, 8000), (8000, 12000), (12000, 16000)]
hidx = [(fax >= b[0]) & (fax < b[1]) for b in HB]
hf = (fax >= 4000) & (fax < 12000)
# (i) automatic fricative frames, candidate independent: mix HF well above the band template, inside a word (+-60 ms)
FMp = np.array([[frame_mask(vi, j, sw, 0.06) for j in range(4)] for vi in range(7)])
Pm = SPEC['mix'][:, :4]; pmh = Pm[..., hf].sum(-1); pth = np.broadcast_to(TP4[..., hf].sum(-1), pmh.shape)
sung_pow = 10 ** (A1['mix']['sung_rms_dbfs'] / 10)
lfb = (fax >= 300) & (fax < 3000)
exh = np.maximum(pmh - pth, 0); exl = np.maximum(Pm[..., lfb].sum(-1) - np.broadcast_to(TP4[..., lfb].sum(-1), pmh.shape), 0)
fric = FMp & (pmh > 4 * pth) & (pmh > 10 ** (-3.2) * sung_pow) & (exh > 0.5 * exl)
print(f"  fricative frames (mix 4-12 kHz > 4x band template, > -32 dB re mix sung power, and the 4-12 kHz excess at least half the "
      f"300-3000 Hz excess, i.e. unvoiced / noisy): {int(fric.sum())} frames = {fric.sum()*HP/SR:.2f} s")
B2 = dict(auto=dict(n_frames=int(fric.sum()), seconds=float(fric.sum() * HP / SR)))
for nm in names:
    Pv = SPEC[nm][:, :4]; Pi = SPEC['inst_' + nm][:, :4]; d = {}
    for b, bi in zip(HB, hidx):
        pv = Pv[..., bi].sum(-1)[fric].sum(); pm_ = Pm[..., bi].sum(-1)[fric].sum()
        pt = np.broadcast_to(TP4[..., bi].sum(-1), fric.shape)[fric].sum()
        pex = np.maximum(Pm[..., bi].sum(-1) - np.broadcast_to(TP4[..., bi].sum(-1), fric.shape), 0)[fric].sum()
        pi_ = Pi[..., bi].sum(-1)[fric].sum()
        d[bn(b)] = dict(stem_vs_mix_db=float(db(pv) - db(pm_)), stem_vs_mix_minus_template_db=float(db(pv) - db(pex)),
                        inst_stem_vs_template_db=float(db(pi_) - db(pt)))
    B2['auto'][nm] = d
    print(f"    {nm:4s} stem/mix dB:", ' '.join(f"{k}:{v['stem_vs_mix_db']:5.1f}" for k, v in d.items()),
          '| stem/(mix-template):', ' '.join(f"{k}:{v['stem_vs_mix_minus_template_db']:5.1f}" for k, v in d.items()),
          '| inst stem/template:', ' '.join(f"{k}:{v['inst_stem_vs_template_db']:5.1f}" for k, v in d.items()))
# (ii) explicit instants: the 21 "c" of ciftligi / ciftliginde (full-length STFT, window = 90 ms around the HF peak of the mix)
f_, t_, Sx = stft(x, 1024, 128); PX = np.abs(Sx) ** 2
SV = {nm: np.abs(stft(C[nm], 1024, 128)[2]) ** 2 for nm in names}
hf2 = (f_ >= 4000) & (f_ < 12000); HB2 = [(f_ >= b[0]) & (f_ < b[1]) for b in HB]
inst_list = []
for w in words:
    tx = w['text'].lower()
    key = None
    if tx.startswith('çiftli'): key = 'c'
    if tx.startswith('kedisi'): key = 's'
    if key is None: continue
    if key == 'c':
        a, b = w['start'] - 0.09, w['start'] + 0.12
    else:
        a, b = w['start'] + 0.15, w['end'] + 0.02
    sel = (t_ >= a) & (t_ <= b); e = PX[hf2][:, sel].sum(0)
    wl = int(round(0.09 * SR / 128)); cs = np.convolve(e, np.ones(wl), mode='valid'); k = int(np.argmax(cs))
    i0 = np.where(sel)[0][0] + k; i1 = i0 + wl
    row = dict(word=w['text'], kind=key, t0=float(t_[i0]), t1=float(t_[i1 - 1]))
    for nm in names:
        row[nm] = {bn(b): float(db(SV[nm][bi][:, i0:i1].sum()) - db(PX[bi][:, i0:i1].sum())) for b, bi in zip(HB, HB2)}
    inst_list.append(row)
B2['explicit'] = inst_list
for nm in names:
    cc = [r for r in inst_list if r['kind'] == 'c']
    med = {bn(b): float(np.median([r[nm][bn(b)] for r in cc])) for b in HB}
    mn = {bn(b): float(np.min([r[nm][bn(b)] for r in cc])) for b in HB}
    B2.setdefault('explicit_summary', {})[nm] = dict(n_c=len(cc), median_stem_vs_mix_db=med, min_stem_vs_mix_db=mn,
                                                     s_kedisi=[r[nm] for r in inst_list if r['kind'] == 's'])
    print(f"  {nm:4s} the {len(cc)} 'c' onsets, stem/mix dB median:", ' '.join(f"{k}:{v:5.1f}" for k, v in med.items()),
          '| worst:', ' '.join(f"{k}:{v:5.1f}" for k, v in mn.items()),
          "| 's' of kedisi:", [{k: round(v, 1) for k, v in r[nm].items()} for r in inst_list if r['kind'] == 's'])
out['b2_consonants'] = B2

# ------------------------------------------------------------------ (b3) long-term spectrum, band limits, holes
print('\n(b3) LONG-TERM SPECTRUM over the sung word frames (2048/512), stem relative to mix, and band holes')
f3, t3, Sx3 = stft(x, 2048, 512); PX3 = np.abs(Sx3) ** 2
fm_sw = np.array([m_sw[min(N - 1, int(tt * SR))] for tt in t3]); fm_in = np.array([m_in[min(N - 1, int(tt * SR))] for tt in t3])
lt_mix = PX3[:, fm_sw].mean(1)
B3 = {}; SV3 = {}
edges = 2 ** np.arange(np.log2(80), np.log2(21000), 1 / 6)          # 1/6-octave bands
for nm in names:
    S = np.abs(stft(C[nm], 2048, 512)[2]) ** 2; SV3[nm] = S
    lt = S[:, fm_sw].mean(1)
    rel = db(lt + 1e-20) - db(lt.max())
    above = np.where(rel > -70)[0]
    f_hi = float(f3[above.max()]); f_lo = float(f3[above.min()])
    # band ratio stem/mix in 1/6-octave bands; a hole = a band more than 8 dB below the median of its +-3 neighbours (200 Hz .. cutoff)
    rb = []; fc = []
    for a, b in zip(edges[:-1], edges[1:]):
        bi = (f3 >= a) & (f3 < b)
        if bi.sum() == 0: continue
        rb.append(float(db(lt[bi].sum() + 1e-20) - db(lt_mix[bi].sum() + 1e-20))); fc.append(float(np.sqrt(a * b)))
    rb = np.array(rb); fc = np.array(fc); holes = []
    for i in range(len(rb)):
        if fc[i] < 200 or fc[i] > min(f_hi, 16000): continue
        nb = np.r_[rb[max(0, i - 3):i], rb[i + 1:i + 4]]
        if rb[i] < np.median(nb) - 8: holes.append(dict(fc_hz=round(fc[i]), ratio_db=round(rb[i], 1), neighbours_median_db=round(float(np.median(nb)), 1)))
    # fine notch scan: stem LTAS smoothed over 5 bins against its own 61-bin median envelope
    lts = ndi.uniform_filter1d(db(lt + 1e-20), 5); envl = ndi.median_filter(lts, 61)
    rng = (f3 >= 200) & (f3 <= min(f_hi - 500, 16000)); dip = envl - lts
    notch = [dict(f_hz=float(f3[i]), depth_db=round(float(dip[i]), 1)) for i in np.where(rng & (dip > 12))[0]]
    B3[nm] = dict(ltas_70db_bandwidth_hz=[f_lo, f_hi], sixth_octave_fc_hz=[round(v) for v in fc], sixth_octave_stem_vs_mix_db=[round(float(v), 1) for v in rb],
                  band_holes=holes, narrow_notches_gt12db=notch[:40], n_narrow_notches=len(notch),
                  energy_above_16k_rel_total_db=float(db(lt[f3 >= 16000].sum() + 1e-20) - db(lt.sum())),
                  energy_8k_16k_rel_total_db=float(db(lt[(f3 >= 8000) & (f3 < 16000)].sum() + 1e-20) - db(lt.sum())))
    print(f"  {nm:4s}: band where the sung LTAS is within 70 dB of its maximum: {f_lo:.0f} .. {f_hi:.0f} Hz; 1/6-oct holes: {holes}; narrow notches >12 dB: {len(notch)}; "
          f"8-16 kHz share {B3[nm]['energy_8k_16k_rel_total_db']:.1f} dB, >16 kHz share {B3[nm]['energy_above_16k_rel_total_db']:.1f} dB")
    print('        stem/mix dB by octave-ish:', ' '.join(f"{fc[i]:.0f}:{rb[i]:.1f}" for i in range(0, len(rb), 3)))
rel = db(lt_mix + 1e-20) - db(lt_mix.max()); ab = np.where(rel > -70)[0]
B3['mix'] = dict(ltas_70db_bandwidth_hz=[float(f3[ab.min()]), float(f3[ab.max()])])
print(f"  mix : {f3[ab.min()]:.0f} .. {f3[ab.max()]:.0f} Hz")
out['b3_spectrum'] = B3

# ------------------------------------------------------------------ (b4) musical noise: short isolated tonal peaks
print('\n(b4) SHORT ISOLATED TONAL PEAKS (2048/512): spectral peak >= 12 dB over the median of +-8 bins, absent (>= 12 dB lower within +-2 bins)')
print('     both 4 frames (46 ms) before and after; levels above -60 dB re the loudest sung bin; 200 Hz - 16 kHz')
def isolated_peaks(Pw, ref):
    L = db(Pw + 1e-20)
    med = ndi.median_filter(L, size=(17, 1))
    loc = (L > np.roll(L, 1, 0)) & (L >= np.roll(L, -1, 0)) & (L - med >= 12) & (L > ref - 60)
    Lmx = ndi.maximum_filter(L, size=(5, 1))
    prev = np.roll(Lmx, 4, 1); nxt = np.roll(Lmx, -4, 1)
    iso = loc & (prev < L - 12) & (nxt < L - 12)
    iso[:, :4] = False; iso[:, -4:] = False
    fr = (f3 >= 200) & (f3 <= 16000)
    iso[~fr] = False; loc[~fr] = False
    return iso, loc


B4 = {}
for nm in names + ['mix']:
    Pw = SV3[nm] if nm != 'mix' else PX3
    ref = db(Pw[:, fm_sw].max())
    iso, loc = isolated_peaks(Pw, ref)
    d = {}
    for lab, fm in (('sung', fm_sw), ('inst', fm_in)):
        dur = fm.sum() * 512 / SR
        d[lab] = dict(isolated_per_s=float(iso[:, fm].sum() / dur), all_peaks_per_s=float(loc[:, fm].sum() / dur),
                      isolated_fraction_of_peaks=float(iso[:, fm].sum() / max(1, loc[:, fm].sum())),
                      isolated_energy_rel_region_db=float(db(Pw[:, fm][iso[:, fm]].sum() + 1e-20) - db(Pw[:, fm].sum())))
    # the same with a floating reference (relative to each frame's own maximum) to see flicker in the quiet stretches
    B4[nm] = d
    print(f"  {nm:4s}: sung: {d['sung']['isolated_per_s']:7.1f} isolated/s of {d['sung']['all_peaks_per_s']:7.1f} peaks/s ({100*d['sung']['isolated_fraction_of_peaks']:.1f} %), "
          f"energy {d['sung']['isolated_energy_rel_region_db']:.1f} dB | inst stretches: {d['inst']['isolated_per_s']:7.1f} isolated/s of {d['inst']['all_peaks_per_s']:7.1f} peaks/s")
# frame-to-frame flicker of the residue in the instrumental stretches: mean |dL| between consecutive non-overlapping frames (4 hops)
for nm in names + ['mix']:
    Pw = SV3[nm] if nm != 'mix' else PX3
    L = db(Pw + 1e-14); fr = (f3 >= 200) & (f3 <= 16000)
    dL = np.abs(L[:, 4:] - L[:, :-4])[fr]
    B4[nm]['flicker_mean_abs_dL_db'] = dict(inst=float(dL[:, fm_in[4:] & fm_in[:-4]].mean()), sung=float(dL[:, fm_sw[4:] & fm_sw[:-4]].mean()))
    print(f"  {nm:4s}: mean |level change| over 46 ms per bin: sung {B4[nm]['flicker_mean_abs_dL_db']['sung']:.2f} dB, inst {B4[nm]['flicker_mean_abs_dL_db']['inst']:.2f} dB")
out['b4_musical_noise'] = B4

# ------------------------------------------------------------------ (c) agreement of two candidates
if len(names) >= 2:
    a, b = names[0], names[1]
    print(f'\n(c) AGREEMENT {a} <-> {b} in the sung parts')
    va, vb = C[a], C[b]; d = va - vb
    Cc = dict(pair=[a, b], diff_rms_rel_sung_db=dict(sung_words=rms_db(d[m_sw]) - rms_db(va[m_sw]), sung_bars=rms_db(d[m_sb]) - rms_db(va[m_sw]),
                                                     inst=rms_db(d[m_in]) - rms_db(va[m_sw])),
              corr_sung_words=float((va[m_sw] * vb[m_sw]).sum() / np.sqrt((va[m_sw] ** 2).sum() * (vb[m_sw] ** 2).sum())),
              level_diff_sung_db=rms_db(va[m_sw]) - rms_db(vb[m_sw]))
    print(f"  difference signal: {Cc['diff_rms_rel_sung_db']['sung_words']:.1f} dB rel sung (word intervals), correlation {Cc['corr_sung_words']:.4f}, level {a}-{b} {Cc['level_diff_sung_db']:+.2f} dB")
    rows = []
    for s in segs:
        i0, i1 = int(s['onset'] * SR), int(s['end'] * SR)
        ya, yb = va[i0:i1], vb[i0:i1]
        rows.append(dict(verse=s['verse'], name=s['name'], t0=s['onset'], t1=s['end'], level_diff_db=rms_db(ya) - rms_db(yb),
                         corr=float((ya * yb).sum() / np.sqrt((ya ** 2).sum() * (yb ** 2).sum())),
                         diff_rel_db=rms_db(ya - yb) - rms_db(ya)))
    Cc['per_segment'] = rows
    cr = np.array([r['corr'] for r in rows]); dr = np.array([r['diff_rel_db'] for r in rows])
    print(f"  per segment: corr median {np.median(cr):.4f} min {cr.min():.4f}; difference median {np.median(dr):.1f} dB, worst {dr.max():.1f} dB "
          f"(v{rows[int(np.argmax(dr))]['verse']} {rows[int(np.argmax(dr))]['name']})")
    # band-wise frame comparison: 46 ms frames, 11.6 ms hop, inside the sung bars
    Sa, Sb = SV3[a], SV3[b]
    fm_sb = np.array([m_sb[min(N - 1, int(tt * SR))] for tt in t3])
    CB = [(200, 1000), (1000, 3000), (3000, 6000), (6000, 10000), (10000, 16000)]
    refa = Sa[:, fm_sw].sum(0).mean()            # mean sung frame power
    ev = []
    for bnd in CB:
        bi = (f3 >= bnd[0]) & (f3 < bnd[1])
        ea = ndi.uniform_filter1d(Sa[bi].sum(0), 4); eb = ndi.uniform_filter1d(Sb[bi].sum(0), 4)
        sig = (np.maximum(ea, eb) > refa * 10 ** (-3.5)) & fm_sb              # at least one above -35 dB re mean sung frame power
        dd = db(ea + 1e-20) - db(eb + 1e-20)
        bad = sig & (np.abs(dd) > 6)
        lab, nlab = ndi.label(bad)
        for k in range(1, nlab + 1):
            ii = np.where(lab == k)[0]
            if len(ii) < 4: continue                                           # shorter than about 46 ms: ignore
            j = ii[np.argmax(np.abs(dd[ii]))]
            ev.append(dict(t0=round(float(t3[ii[0]]), 3), t1=round(float(t3[ii[-1]]), 3), band=bn(bnd), max_diff_db=round(float(dd[j]), 1),
                           higher=a if dd[j] > 0 else b,
                           level_of_higher_rel_mean_sung_frame_db=round(float(db(max(ea[j], eb[j])) - db(refa)), 1),
                           in_word=bool(m_sw[min(N - 1, int(t3[j] * SR))])))
        Cc.setdefault('band_stats', {})[bn(bnd)] = dict(frames_significant=int(sig.sum()), frames_gt6db=int(bad.sum()),
                                                        fraction_gt6db=float(bad.sum() / max(1, sig.sum())),
                                                        median_abs_diff_db=float(np.median(np.abs(dd[sig]))) if sig.sum() else None,
                                                        mean_diff_db_a_minus_b=float(dd[sig].mean()) if sig.sum() else None)
        print(f"  band {bn(bnd):11s}: significant frames {int(sig.sum()):5d}, |diff| > 6 dB in {100*bad.sum()/max(1,sig.sum()):5.1f} %, median |diff| {np.median(np.abs(dd[sig])):.2f} dB, mean {a}-{b} {dd[sig].mean():+.2f} dB")
    ev.sort(key=lambda e: -(abs(e['max_diff_db']) + e['level_of_higher_rel_mean_sung_frame_db'] / 2))
    Cc['disagreements'] = ev
    print(f"  {len(ev)} disagreement events (>6 dB for >=46 ms, level above -35 dB); strongest:")
    for e in ev[:25]:
        print(f"     {e['t0']:7.3f}-{e['t1']:7.3f} s  {e['band']:11s} {e['max_diff_db']:+6.1f} dB (higher: {e['higher']}, level {e['level_of_higher_rel_mean_sung_frame_db']:.1f} dB, in word: {e['in_word']})")
    # (c2) what is the difference made of?  Energy that one candidate has and the other lacks is split into the part
    # lying on the harmonics of the sung pitch (voice-like) and the rest (band-like).  Voiced word frames, 300-5000 Hz.
    import librosa
    y22 = librosa.resample(vref, orig_sr=SR, target_sr=SR // 2)
    f0, vfl, vpr = librosa.pyin(y22, fmin=180, fmax=720, sr=SR // 2, frame_length=1024, hop_length=256, center=True)
    f4, t4, _ = stft(x[:8192], 4096, 512)
    S4 = {k: np.abs(stft(v_, 4096, 512)[2]) ** 2 for k, v_ in (('mix', x), (a, va), (b, vb), ('inst_' + a, x - va), ('inst_' + b, x - vb))}
    nfr4 = min(S4['mix'].shape[1], len(f0)); t4 = np.arange(nfr4) * 512 / SR
    fm4 = np.array([m_sw[min(N - 1, int(tt * SR))] for tt in t4]) & np.nan_to_num(vfl[:nfr4]).astype(bool) & (np.nan_to_num(vpr[:nfr4]) > 0.5)
    fr4 = (f4 >= 300) & (f4 <= 5000); fsel = f4[fr4]
    comb = np.zeros((fr4.sum(), nfr4), bool)
    for i in np.where(fm4)[0]:
        k = np.arange(1, int(5000 / f0[i]) + 1)[:, None] * f0[i]
        hw = np.maximum(27.0, 0.01 * k)
        comb[:, i] = (np.abs(fsel[None, :] - k) <= hw).any(0)
    def onfrac(Pw):
        Pw = Pw[fr4][:, :nfr4][:, fm4]; cm = comb[:, fm4]
        return float(Pw[cm].sum() / Pw.sum()), float((Pw.sum(0) * cm.mean(0)).sum() / Pw.sum())
    D = dict(n_voiced_frames=int(fm4.sum()), seconds=float(fm4.sum() * 512 / SR), median_f0_hz=float(np.nanmedian(f0[:nfr4][fm4])))
    for k in S4:
        on, ch = onfrac(S4[k]); D[k] = dict(on_harmonics_fraction=on, chance_fraction=ch)
    PA, PB = S4[a], S4[b]
    for lab, ex, own in ((f'extra_in_{a}', np.maximum(PA - PB, 0), PA), (f'extra_in_{b}', np.maximum(PB - PA, 0), PB)):
        on, ch = onfrac(ex)
        tot = ex[fr4][:, :nfr4][:, fm4].sum(); ownt = own[fr4][:, :nfr4][:, fm4].sum()
        D[lab] = dict(on_harmonics_fraction=on, chance_fraction=ch, energy_rel_own_stem_db=float(db(tot) - db(ownt)),
                      on_harmonics_energy_rel_own_stem_db=float(db(tot * on) - db(ownt)), off_harmonics_energy_rel_own_stem_db=float(db(tot * (1 - on)) - db(ownt)))
    Cc['difference_composition'] = D
    print(f"  (c2) voiced word frames: {D['seconds']:.1f} s, median f0 {D['median_f0_hz']:.0f} Hz; fraction of the 300-5000 Hz energy on the sung harmonics (chance = share of bins in the comb):")
    for k in S4:
        print(f"       {k:10s}: {D[k]['on_harmonics_fraction']:.3f} (chance {D[k]['chance_fraction']:.3f})")
    for lab in (f'extra_in_{a}', f'extra_in_{b}'):
        e = D[lab]
        print(f"       {lab:13s}: {e['on_harmonics_fraction']:.3f} (chance {e['chance_fraction']:.3f}); energy {e['energy_rel_own_stem_db']:.1f} dB rel own stem "
              f"(on harmonics {e['on_harmonics_energy_rel_own_stem_db']:.1f}, off harmonics {e['off_harmonics_energy_rel_own_stem_db']:.1f})")
    out['c_agreement'] = Cc

json.dump(out, open(CACHE + '/karsilastir.json', 'w'), indent=1)
print('\nwritten', CACHE + '/karsilastir.json')
