# Exploration: per-eighth-note band onset strengths on the 116 BPM grid, to see which eighths
# carry kick / snare / hats, and how the pattern relates to the sung lines.
import numpy as np, json
from common import *
x=load_mix()
f,t,S=stft_mag(x)
bands={'kick40_120':(40,120),'low120_300':(120,300),'mid300_2k':(300,2000),'hi2k_8k':(2000,8000),'air8k_16k':(8000,16000)}
F={k:flux(S,f,lo,hi) for k,(lo,hi) in bands.items()}
E={k:np.sqrt((S[(f>=lo)&(f<=hi)]**2).sum(0)) for k,(lo,hi) in bands.items()}
P=60/116.0; PH=0.0047
words=load_words()
starts=[6.20,18.62,33.12,46.56,59.48,73.96,86.40]
n8=int((t[-1]-PH)/(P/2))
rows=[]
for k in range(n8):
    g=PH+k*P/2
    r={'k':k,'t':g}
    for b in bands:
        m=(t>=g-0.045)&(t<=g+0.045)
        r[b]=F[b][m].max()
        m2=(t>=g)&(t<=g+0.12)
        r['E_'+b]=E[b][m2].mean()
    rows.append(r)
# normalise each band by its median over the song body
for b in bands:
    med=np.median([r[b] for r in rows if 5<r['t']<100])+1e-9
    for r in rows: r[b]/=med
def wordat(g):
    s=''
    for w in words:
        if g-P/4<=w['start']<g+P/4: s+=w['text']+' '
    return s
print(' k   beat  time    kick  low   mid   hi    air   words')
for r in rows:
    k=r['k']
    print(f"{k:4d} {k/2:5.1f} {r['t']:7.3f} "+' '.join(f"{r[b]:5.2f}" for b in bands)+'  '+wordat(r['t']))
np.save(O+'/eighth_rows.npy',np.array([[r['k'],r['t']]+[r[b] for b in bands]+[r['E_'+b] for b in bands] for r in rows]))
