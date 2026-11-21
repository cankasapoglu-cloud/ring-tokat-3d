# Bleed of the band INSIDE the sung frames (where the instrumental-stretch numbers say nothing).
#   usage: python3 05_sarki_ici_sizinti.py      -> gecici/sarki_ici_sizinti.json
# Idea: in a voiced frame the voice only has energy on the harmonics k*f0 of the sung pitch (plus noise).  Tonal
# partials of the mix that lie clearly OFF that comb belong to the band (bass, chords).  How much of each such band
# partial is still present in the vocal stem?
#  (i)   per band partial: level in the stem relative to the same partial in the mix (dB), 150-4000 Hz
#  (ii)  energy below the sung fundamental (120 Hz .. 0.80*f0): no voice partial can be there
#  (iii) energy between the harmonics (off the comb) of the stem relative to its own harmonic energy
# f0: librosa.pyin on the stem itself (22.05 kHz, 46 ms frames, 11.6 ms hop).
# A peak of the mix that lies off the comb is not automatically a band partial: the ringing tail of the previous sung
# note, a second voice or a pitch glide also produce such peaks, and those are voice.  Therefore every off-comb peak is
# checked against the LOOP TEMPLATE of the band: the mix at the same position of the 2-bar chord loop in the
# instrumental bars (bars 4/5 of verses 1-6, median of the six).  "band partial" = the template holds a partial of at
# least -6 dB of the peak's power at that bin (+-1); "voice-caused" = the template is more than 12 dB lower.
import sys, json, numpy as np, scipy.ndimage as ndi, librosa
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *

P = stem_paths(); names = list(P.keys())
x = load_mix(); N = len(x); R = regions()
m_sw = mask_from(R['sung_words'], N)
NF, HP = 4096, 512
f, t, Sx = stft(x, NF, HP); PX = np.abs(Sx) ** 2
out = dict(method='see the header of kod/05_sarki_ici_sizinti.py', stft='4096 / 512, Hann')
# loop template on the global frame grid: for a frame at time tt inside sung bar j of any verse, the median over verses
# 1-6 of the mix power at the same phase of instrumental bar 4 + (j mod 2)
nfr_all = PX.shape[1]; t_all = np.arange(nfr_all) * HP / SR
TPL = np.zeros_like(PX, dtype=np.float32); in_sung_bar = np.zeros(nfr_all, bool)
PXm = np.maximum(np.maximum(PX, np.roll(PX, 1, 0)), np.roll(PX, -1, 0))        # +-1 bin
for vi, d0 in enumerate(VERSE_DB):
    for j in range(4):
        a0 = d0 + j * BAR
        fr = np.where((t_all >= a0) & (t_all < a0 + BAR))[0]
        src = []
        for v2 in range(6):
            ts = VERSE_DB[v2] + (4 + j % 2) * BAR + (t_all[fr] - a0)
            src.append(PXm[:, np.clip(np.round(ts * SR / HP).astype(int), 0, nfr_all - 1)])
        TPL[:, fr] = np.median(np.array(src), 0); in_sung_bar[fr] = True
for nm in names:
    hz = json.load(open(f'{CACHE}/hizala_{nm}.json'))
    g = hz['sum_check']['gain_stems_over_mix'] if 'sum_check' in hz else 1.0
    v = load_stem(P[nm]['vocals'])[:N] / g
    PV = np.abs(stft(v, NF, HP)[2]) ** 2
    y22 = librosa.resample(v, orig_sr=SR, target_sr=SR // 2)
    f0, vfl, vpr = librosa.pyin(y22, fmin=180, fmax=720, sr=SR // 2, frame_length=1024, hop_length=256, center=True)
    nfr = min(PV.shape[1], len(f0)); tt = np.arange(nfr) * HP / SR
    voiced = np.array([m_sw[min(N - 1, int(q * SR))] for q in tt]) & np.nan_to_num(vfl[:nfr]).astype(bool) & (np.nan_to_num(vpr[:nfr]) > 0.5)
    # keep frames whose pitch is locally steady (within 3 % of both neighbours two frames away): the comb is then reliable
    f0s = f0[:nfr].copy(); ok = voiced.copy()
    for i in np.where(voiced)[0]:
        nb = [j for j in (i - 2, i + 2) if 0 <= j < nfr]
        if any((not voiced[j]) or abs(f0s[j] / f0s[i] - 1) > 0.03 for j in nb): ok[i] = False
    idx = np.where(ok)[0]
    Lm = db(PX + 1e-20)
    medm = ndi.median_filter(Lm, size=(25, 1))
    band = (f >= 150) & (f <= 4000)
    peak = (Lm > np.roll(Lm, 1, 0)) & (Lm >= np.roll(Lm, -1, 0)) & (Lm - medm >= 10) & band[:, None]
    ref = db(PX[:, :nfr][:, ok].max())
    peak &= (Lm > ref - 50)
    off_ratio, on_ratio, off_f, off_t, off_lvl, off_tpl = [], [], [], [], [], []
    sub_v = 0.0; sub_m = 0.0; tot_v = 0.0; on_e = 0.0; off_e = 0.0; on_bins = 0; off_bins = 0
    for i in idx:
        k = np.arange(1, int(4200 / f0s[i]) + 1) * f0s[i]
        dist = np.abs(f[:, None] - k[None, :]).min(1)                    # distance to the nearest sung harmonic (Hz)
        hwn = np.maximum(27.0, 0.012 * f)                                # on-comb half width
        hwf = np.maximum(55.0, 0.035 * f)                                # clearly off the comb beyond this
        pk = np.where(peak[:, i])[0]
        for b in pk:
            r = float(db(PV[b - 1:b + 2, i].max() + 1e-20) - db(PX[b, i]))
            if dist[b] >= hwf[b] and f[b] > 150:
                off_ratio.append(r); off_f.append(float(f[b])); off_t.append(float(tt[i])); off_lvl.append(float(Lm[b, i] - ref))
                off_tpl.append(float(db(TPL[b, i] + 1e-20) - db(PX[b, i])) if in_sung_bar[i] else np.nan)
            elif dist[b] <= hwn[b] and f[b] >= 0.9 * f0s[i]:
                on_ratio.append(r)
        sb = (f >= 120) & (f <= 0.80 * f0s[i])
        sub_v += PV[sb, i].sum(); sub_m += PX[sb, i].sum(); tot_v += PV[(f >= 100) & (f <= 16000), i].sum()
        rng = (f >= 0.9 * f0s[i]) & (f <= 4000)
        on = rng & (dist <= hwn); off = rng & (dist >= hwf)
        on_e += PV[on, i].sum(); off_e += PV[off, i].sum(); on_bins += on.sum(); off_bins += off.sum()
    off_ratio = np.array(off_ratio); on_ratio = np.array(on_ratio); off_f = np.array(off_f); off_t = np.array(off_t)
    off_tpl = np.array(off_tpl); off_lvl = np.array(off_lvl)
    isband = off_tpl >= -6; isvoice = off_tpl < -12
    def summ(sel):
        q = off_ratio[sel]
        if len(q) == 0: return dict(n=0)
        e_m = (10 ** (off_lvl[sel] / 10)).sum(); e_v = (10 ** ((off_lvl[sel] + q) / 10)).sum()
        dd = dict(n=int(len(q)), stem_vs_mix_db_median=float(np.median(q)), p75=float(np.percentile(q, 75)), p90=float(np.percentile(q, 90)),
                  p99=float(np.percentile(q, 99)), energy_weighted_stem_vs_mix_db=float(db(e_v) - db(e_m)),
                  fraction_above_minus20db=float((q > -20).mean()), fraction_above_minus12db=float((q > -12).mean()), fraction_above_minus6db=float((q > -6).mean()), by_range={})
        for lo, hi in ((150, 280), (280, 600), (600, 1200), (1200, 2400), (2400, 4000)):
            r_ = (off_f[sel] >= lo) & (off_f[sel] < hi)
            dd['by_range'][f'{lo}-{hi}'] = dict(n=int(r_.sum()), median_db=float(np.median(q[r_])) if r_.sum() else None,
                                                p90_db=float(np.percentile(q[r_], 90)) if r_.sum() else None,
                                                fraction_above_minus12db=float((q[r_] > -12).mean()) if r_.sum() else None)
        return dd
    cls = dict(band_partials_confirmed_by_loop_template=summ(isband), off_comb_peaks_caused_by_the_voice=summ(isvoice),
               undecided=summ(~isband & ~isvoice & ~np.isnan(off_tpl)))
    d = dict(separator_scale=g, n_voiced_steady_frames=int(len(idx)), seconds=float(len(idx) * HP / SR),
             f0_hz=dict(min=float(np.nanmin(f0s[ok])), median=float(np.nanmedian(f0s[ok])), max=float(np.nanmax(f0s[ok])),
                        p05=float(np.nanpercentile(f0s[ok], 5)), p95=float(np.nanpercentile(f0s[ok], 95))),
             band_partials_off_the_sung_harmonics=dict(
                 n=int(len(off_ratio)), stem_vs_mix_db_median=float(np.median(off_ratio)), p75=float(np.percentile(off_ratio, 75)),
                 p90=float(np.percentile(off_ratio, 90)), p99=float(np.percentile(off_ratio, 99)),
                 fraction_above_minus20db=float((off_ratio > -20).mean()), fraction_above_minus12db=float((off_ratio > -12).mean()),
                 fraction_above_minus6db=float((off_ratio > -6).mean()),
                 by_range={f'{lo}-{hi}': dict(n=int(((off_f >= lo) & (off_f < hi)).sum()),
                                              median_db=float(np.median(off_ratio[(off_f >= lo) & (off_f < hi)])) if ((off_f >= lo) & (off_f < hi)).sum() else None,
                                              p90_db=float(np.percentile(off_ratio[(off_f >= lo) & (off_f < hi)], 90)) if ((off_f >= lo) & (off_f < hi)).sum() else None,
                                              fraction_above_minus12db=float((off_ratio[(off_f >= lo) & (off_f < hi)] > -12).mean()) if ((off_f >= lo) & (off_f < hi)).sum() else None)
                           for lo, hi in ((150, 280), (280, 600), (600, 1200), (1200, 2400), (2400, 4000))}),
             **cls,
             voice_partials_on_the_sung_harmonics=dict(n=int(len(on_ratio)), stem_vs_mix_db_median=float(np.median(on_ratio)),
                                                       p10=float(np.percentile(on_ratio, 10)), p01=float(np.percentile(on_ratio, 1)),
                                                       fraction_below_minus6db=float((on_ratio < -6).mean()), fraction_below_minus12db=float((on_ratio < -12).mean())),
             below_fundamental_120Hz_to_0p8f0=dict(stem_rel_stem_total_db=float(db(sub_v) - db(tot_v)), stem_vs_mix_db=float(db(sub_v) - db(sub_m))),
             between_harmonics=dict(off_comb_energy_rel_on_comb_db=float(db(off_e) - db(on_e)),
                                    off_comb_density_rel_on_comb_db=float(db(off_e / off_bins) - db(on_e / on_bins))))
    # worst leaked band partials: time, frequency
    order = [j for j in np.argsort(-off_ratio) if isband[j]][:600]
    worst = sorted([dict(t=round(float(off_t[j]), 3), f_hz=round(float(off_f[j]), 1), stem_vs_mix_db=round(float(off_ratio[j]), 1), mix_level_db_re_max=round(float(off_lvl[j]), 1))
                    for j in order if off_ratio[j] > -6], key=lambda e: e['t'])
    # merge into events (same partial within 60 ms / 30 Hz)
    ev = []
    for w in worst:
        if ev and w['t'] - ev[-1]['t1'] <= 0.06 and abs(w['f_hz'] - ev[-1]['f_hz']) <= 30:
            ev[-1]['t1'] = w['t']; ev[-1]['n'] += 1; ev[-1]['max_db'] = max(ev[-1]['max_db'], w['stem_vs_mix_db'])
        else:
            ev.append(dict(t0=w['t'], t1=w['t'], f_hz=w['f_hz'], n=1, max_db=w['stem_vs_mix_db']))
    d['leaked_partials_above_minus6db_events'] = [e for e in ev if e['n'] >= 3][:60]
    d['leaked_partials_note'] = 'template-confirmed band partials that are less than 6 dB down in the stem for at least 3 frames (35 ms)'
    out[nm] = d
    bp = d['band_partials_off_the_sung_harmonics']; vp = d['voice_partials_on_the_sung_harmonics']
    print(f"[{nm}] voiced steady frames {d['seconds']:.1f} s, f0 {d['f0_hz']['p05']:.0f}..{d['f0_hz']['p95']:.0f} Hz (median {d['f0_hz']['median']:.0f})")
    print(f"   band partials off the sung harmonics (n={bp['n']}): stem vs mix median {bp['stem_vs_mix_db_median']:.1f} dB, p75 {bp['p75']:.1f}, p90 {bp['p90']:.1f}, p99 {bp['p99']:.1f}; "
          f"> -20 dB: {100*bp['fraction_above_minus20db']:.1f} %, > -12 dB: {100*bp['fraction_above_minus12db']:.1f} %, > -6 dB: {100*bp['fraction_above_minus6db']:.1f} %")
    for k_, e in bp['by_range'].items():
        if e['n']: print(f"        {k_:10s} Hz: n={e['n']:5d} median {e['median_db']:6.1f} dB, p90 {e['p90_db']:6.1f} dB, > -12 dB: {100*e['fraction_above_minus12db']:.1f} %")
    for lab in ('band_partials_confirmed_by_loop_template', 'off_comb_peaks_caused_by_the_voice', 'undecided'):
        e = d[lab]
        if not e['n']: print(f"   {lab}: none"); continue
        print(f"   {lab} (n={e['n']}): stem vs mix median {e['stem_vs_mix_db_median']:.1f} dB, p75 {e['p75']:.1f}, p90 {e['p90']:.1f}, p99 {e['p99']:.1f}, energy-weighted {e['energy_weighted_stem_vs_mix_db']:.1f} dB; "
              f"> -20 dB: {100*e['fraction_above_minus20db']:.1f} %, > -12 dB: {100*e['fraction_above_minus12db']:.1f} %, > -6 dB: {100*e['fraction_above_minus6db']:.1f} %")
        for k_, q in e['by_range'].items():
            if q['n']: print(f"        {k_:10s} Hz: n={q['n']:5d} median {q['median_db']:6.1f} dB, p90 {q['p90_db']:6.1f} dB, > -12 dB: {100*q['fraction_above_minus12db']:.1f} %")
    print(f"   voice partials on the sung harmonics (n={vp['n']}): stem vs mix median {vp['stem_vs_mix_db_median']:.2f} dB, p10 {vp['p10']:.1f}, p01 {vp['p01']:.1f}; "
          f"< -6 dB: {100*vp['fraction_below_minus6db']:.2f} %, < -12 dB: {100*vp['fraction_below_minus12db']:.2f} %")
    print(f"   below the fundamental (120 Hz .. 0.8 f0): stem {d['below_fundamental_120Hz_to_0p8f0']['stem_rel_stem_total_db']:.1f} dB re stem total, {d['below_fundamental_120Hz_to_0p8f0']['stem_vs_mix_db']:.1f} dB vs mix")
    print(f"   between the harmonics: energy {d['between_harmonics']['off_comb_energy_rel_on_comb_db']:.1f} dB re harmonic energy (density {d['between_harmonics']['off_comb_density_rel_on_comb_db']:.1f} dB)")
    print(f"   leaked partial events (> -6 dB vs mix for >= 3 frames): {len(d['leaked_partials_above_minus6db_events'])}")
    for e in d['leaked_partials_above_minus6db_events'][:25]:
        print(f"        {e['t0']:7.3f}-{e['t1']:7.3f} s  {e['f_hz']:7.1f} Hz  max {e['max_db']:+.1f} dB  ({e['n']} frames)")
json.dump(out, open(CACHE + '/sarki_ici_sizinti.json', 'w'), indent=1)
