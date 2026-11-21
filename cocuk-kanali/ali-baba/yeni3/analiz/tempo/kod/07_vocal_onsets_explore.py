# Exploration: vocal-stem envelopes around each line-initial word, to choose a robust onset definition.
import numpy as np, json, scipy.signal as ss
from common import *
v=load_vocal(); words=load_words()
P=60/116.0; PHI=0.0015
def env(y,win_ms=10.0,hop_ms=1.0):
    n=int(SR*win_ms/1000); h=int(SR*hop_ms/1000)
    e=np.sqrt(np.convolve(y**2,np.ones(n)/n,mode='same'))
    return e[::h], h/SR
sosv=ss.butter(4,[90,1200],btype='band',fs=SR,output='sos'); vv=ss.sosfiltfilt(sosv,v)
sosh=ss.butter(4,3000,btype='high',fs=SR,output='sos'); vh=ss.sosfiltfilt(sosh,v)
eb,dt=env(v); ev,_=env(vv); eh,_=env(vh)
db=lambda e: 20*np.log10(e+1e-7)
print('vocal stem overall: peak %.1f dB, median %.1f dB, 5th pct %.1f dB'%(db(eb).max(),np.median(db(eb)),np.percentile(db(eb),5)))
VERSE_T=[6.20,18.62,33.12,46.56,59.48,73.96,86.40]
# group words into lines: a new line starts at each verse onset and at the known first words
lines=[]; cur=None
first_words={'Ali':1,'Çiftliğinde':2,'Dinle':4}
vi=0
ws=[w for w in words if w['start']<100.0]
i=0
while i<len(ws):
    w=ws[i]
    if w['text']=='Ali':
        vi+=1; l1=i
        l2=next(j for j in range(i,len(ws)) if ws[j]['text']=='Çiftliğinde')
        l3=next(j for j in range(l2,len(ws)) if ws[j]['text'].startswith('var'))+1
        l4=next(j for j in range(l3,len(ws)) if ws[j]['text']=='Dinle')
        end=l4+4
        for li,(a,b) in enumerate(((l1,l2),(l2,l3),(l3,l4),(l4,end))):
            lines.append(dict(verse=vi,line=li+1,words=ws[a:b]))
        i=end
    else: i+=1
print(len(lines),'lines')
for L in lines:
    w0=L['words'][0]; t0=w0['start']
    a=int((t0-0.30)/dt); b=int((t0+0.25)/dt)
    seg=db(eb[a:b]); segv=db(ev[a:b]); segh=db(eh[a:b]); tt=np.arange(a,b)*dt
    # first-syllable peak (within 250 ms after word start)
    pk=seg[int(0.30/dt):].max(); pkv=segv[int(0.30/dt):].max()
    # preceding minimum (within 300 ms before)
    kmin=int(np.argmin(seg[:int(0.33/dt)])); mn=seg[kmin]
    def cross(s,level,k0):
        idx=np.where(s[k0:]>=level)[0]
        return tt[k0+idx[0]] if len(idx) else np.nan
    c30=cross(seg,pk-30,kmin); c20=cross(seg,pk-20,kmin); c10=cross(seg,pk-10,kmin); c6=cross(seg,pk-6,kmin)
    kminv=int(np.argmin(segv[:int(0.33/dt)]))
    v20=cross(segv,pkv-20,kminv); v10=cross(segv,pkv-10,kminv); v6=cross(segv,pkv-6,kminv)
    # max slope of voiced envelope (dB per 10 ms) in the window
    sl=np.diff(segv[::5]); ks=int(np.argmax(sl)); tsl=tt[::5][ks]+2.5*dt
    nb=round((t0-PHI)/P); g=PHI+nb*P
    print(f"v{L['verse']} L{L['line']} '{w0['text']:11s}' word {t0:6.2f} grid {g:7.3f} | floor {mn:6.1f} dB @{tt[kmin]-g:+.3f} pk {pk:5.1f} | broadband -30:{c30-g:+.3f} -20:{c20-g:+.3f} -10:{c10-g:+.3f} -6:{c6-g:+.3f} | voiced -20:{v20-g:+.3f} -10:{v10-g:+.3f} -6:{v6-g:+.3f} maxslope:{tsl-g:+.3f} | hi-band pk {segh.max():.1f}")
json.dump([dict(verse=L['verse'],line=L['line'],words=L['words']) for L in lines],open(O+'/lines_words.json','w'),ensure_ascii=False,indent=1)
