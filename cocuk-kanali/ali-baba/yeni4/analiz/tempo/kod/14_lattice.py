# Refined beat lattice of the full mix from the precise transient positions (13_drift_fine.py).
# beat n (mix timeline) = phase + n * period.  Pooled linear fit of the sharp-transient series.
import numpy as np, json
from common import *
d=json.load(open(O+'/drift_fine.json')); BN=105.0; P0=60/BN; PHI0=0.0
tc=np.array(d['window_centres_s'])
keys=['low_120_300_on','mid_300_2000_on','high_2k_8k_on','air_8k_16k_on','air_8k_16k_off']
# keep only series whose window values are consistent (resid sd < 3 ms)
keys=[k for k in keys if d[k]['resid_sd_ms']<3.0]
ON=[k for k in keys if k.endswith('_on')]
T=np.concatenate([tc for k in ON]); D=np.concatenate([np.array(d[k]['dev_ms']) for k in ON])
sl,ic=np.polyfit(T,D,1); r=D-(ic+sl*T)
rng=np.random.default_rng(0); bs=[]
M=np.array([d[k]['dev_ms'] for k in ON]).mean(0)
for _ in range(2000):
    i=rng.integers(0,len(tc),len(tc))
    if len(set(i))<3: continue
    bs.append(np.polyfit(tc[i],M[i],1)[0])
period=P0*(1+sl/1000); phase=PHI0+ic/1000
out=dict(bpm=60/period,beat_period_s=period,bar_period_s=4*period,phase_first_beat_s=phase,series_used=ON,
         slope_ms_per_s_vs_105_000=float(sl),slope_bootstrap_sd=float(np.std(bs)),intercept_ms_vs_phase_0=float(ic),residual_sd_ms=float(r.std()),
         bpm_uncertainty=float(BN*np.std(bs)/1000),
         per_series_mean_dev_ms={k:d[k]['mean_dev_ms'] for k in d if isinstance(d[k],dict) and 'mean_dev_ms' in d[k]},
         definition='beat time = steepest rise of the on-beat transient (kick click / attack in the bands 120 Hz-16 kHz); the kick low-frequency body (40-120 Hz) rises about 25 ms later',
         drift_of_exact_105_bpm_grid_over_100s_ms=float(sl*100))
print(json.dumps(out,indent=1))
json.dump(out,open(O+'/lattice.json','w'),indent=1)
