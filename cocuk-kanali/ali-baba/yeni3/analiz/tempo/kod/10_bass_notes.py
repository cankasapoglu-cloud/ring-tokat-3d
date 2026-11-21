# High-resolution bass-note estimate per beat (sustain part of each beat, after the kick transient),
# to document the root/fifth alternation and the bar-end "turnaround" notes.
import numpy as np, json, scipy.signal as ss
from common import *
x=load_mix(); P=60/116.0; PHI=0.0015
names=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
dec=40; fs=SR/dec
y=ss.decimate(ss.decimate(x,8,ftype='fir',zero_phase=True),5,ftype='fir',zero_phase=True)
VB=[12,36,64,90,115,143,167]
NB=int((len(x)/SR-PHI)/P)-1
NF=1<<16
fr=np.fft.rfftfreq(NF,1/fs)
rows=[]
for b in range(NB):
    g=PHI+b*P
    a=int((g+0.10)*fs); e=int((g+P-0.02)*fs)
    seg=y[a:e]*np.hanning(e-a)
    S=np.abs(np.fft.rfft(seg,NF))
    # harmonic-sum salience over candidate f0 36..135 Hz (step 5 cents)
    cands=36*2**(np.arange(0,int(1200*np.log2(135/36)),5)/1200)
    sal=np.zeros(len(cands))
    for h,w in ((1,1.0),(2,0.9),(3,0.6),(4,0.4)):
        sal+=w*np.interp(cands*h,fr,S)
    k=int(np.argmax(sal)); f0=cands[k]
    midi=69+12*np.log2(f0/440)
    # strongest raw peak 36-135 Hz and 135-270
    m1=(fr>=36)&(fr<=135); fp=fr[m1][np.argmax(S[m1])]
    rows.append(dict(beat=b,t=g,f0=float(f0),midi=float(midi),pc=names[int(round(midi))%12],octave=int(round(midi))//12-1,cents=float(100*(midi-round(midi))),raw_peak_hz=float(fp),
                     level=float(20*np.log10(np.sqrt((seg**2).mean())+1e-9))))
def relpos(b):
    v=[vb for vb in VB if vb<=b]
    return (b-v[-1]) if v else None
line=''
print('beat: note(raw peak Hz)  — listed per verse, rel = beats from verse onset')
for i,vb in enumerate(VB):
    end=VB[i+1] if i+1<len(VB) else vb+28
    print(f'verse {i+1} (onset beat {vb}):')
    for r0 in range(vb,min(end,NB),4):
        print('   rel %2d: '%(r0-vb)+' | '.join(f"{rows[b]['pc']:2s}{rows[b]['octave']} {rows[b]['raw_peak_hz']:5.1f}Hz" for b in range(r0,min(r0+4,end,NB))))
print('intro:'); print('   '+' | '.join(f"{rows[b]['pc']:2s}{rows[b]['octave']} {rows[b]['raw_peak_hz']:5.1f}Hz" for b in range(0,12)))
# statistics: pitch class by position mod 4 relative to verse onset
from collections import Counter
st={}
for p in range(4):
    c=Counter()
    for i,vb in enumerate(VB):
        end=VB[i+1] if i+1<len(VB) else vb+28
        for b in range(vb,min(end,NB)):
            if (b-vb)%4==p: c[rows[b]['pc']]+=1
    st[p]=dict(c); print('position',p,dict(c.most_common()))
json.dump(dict(rows=rows,pc_by_position_mod4=st),open(O+'/bass_notes.json','w'),indent=0)
