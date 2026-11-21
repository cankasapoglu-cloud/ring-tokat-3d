# Refined beat lattice of the full mix from the precise high-frequency transient positions (13_drift_fine.py).
# beat n (mix timeline) = phase + n * period.   Pooled linear fit of the four HF series.
import numpy as np, json
from common import *
d=json.load(open(O+'/drift_fine.json')); P0=60/116.0; PHI0=0.0015
tc=np.array(d['window_centres_s'])
keys=['air_8k_16k_on','mid_300_2000_off','high_2k_8k_off','air_8k_16k_off']
T=np.concatenate([tc for k in keys]); D=np.concatenate([np.array(d[k]['dev_ms']) for k in keys])
sl,ic=np.polyfit(T,D,1); r=D-(ic+sl*T)
# bootstrap over windows for the slope uncertainty
rng=np.random.default_rng(0); bs=[]
M=np.array([d[k]['dev_ms'] for k in keys]).mean(0)
for _ in range(2000):
    i=rng.integers(0,len(tc),len(tc)); 
    if len(set(i))<3: continue
    bs.append(np.polyfit(tc[i],M[i],1)[0])
period=P0*(1+sl/1000); phase=PHI0+ic/1000
out=dict(bpm=60/period,beat_period_s=period,bar_period_s=4*period,phase_first_beat_s=phase,
         slope_ms_per_s_vs_116_000=float(sl),slope_bootstrap_sd=float(np.std(bs)),intercept_ms_vs_phase_0_0015=float(ic),residual_sd_ms=float(r.std()),
         bpm_uncertainty=float(116.0*np.std(bs)/1000),
         definition='beat time = steepest rise of the high-frequency transient of the on-beat hit (hats 8-16 kHz) / of the off-beat "chick" minus half a beat; the kick low-frequency body (120-300 Hz) rises about 6 ms later',
         drift_of_exact_116_bpm_grid_over_100s_ms=float(sl*100))
print(json.dumps(out,indent=1))
json.dump(out,open(O+'/lattice.json','w'),indent=1)
