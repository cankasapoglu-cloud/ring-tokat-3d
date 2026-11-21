# High-resolution bass-note estimate per beat (sustain part of each beat, after the kick transient),
# listed per verse relative to the verse onset beat (24 beats = 6 bars per verse).
import numpy as np, json, scipy.signal as ss
from common import *
from collections import Counter
x=load_mix(); P,PHI=lattice()
names=NAMES
fs=SR/40
y=ss.decimate(ss.decimate(x,8,ftype='fir',zero_phase=True),5,ftype='fir',zero_phase=True)
VB=[int(round((tv-PHI)/P)) for tv in VERSE_T]
print('verse onset beats',VB,'diffs',np.diff(VB).tolist(),'mod4',[b%4 for b in VB])
NB=int((len(x)/SR-PHI)/P)-1
NF=1<<16
fr=np.fft.rfftfreq(NF,1/fs)
def note_of(seg):
    S=np.abs(np.fft.rfft(seg*np.hanning(len(seg)),NF))
    cands=36*2**(np.arange(0,int(1200*np.log2(135/36)),5)/1200)
    sal=np.zeros(len(cands))
    for h,w in ((1,1.0),(2,0.9),(3,0.6),(4,0.4)):
        sal+=w*np.interp(cands*h,fr,S)
    k=int(np.argmax(sal)); f0=cands[k]
    m1=(fr>=36)&(fr<=135); fp=fr[m1][np.argmax(S[m1])]
    return f0,fp,float(sal[k])
rows=[]
for b in range(NB):
    g=PHI+b*P
    r=dict(beat=b,t=g)
    for lab,(o0,o1) in (('',(0.10,P-0.02)),('_h1',(0.08,P/2)),('_h2',(P/2+0.02,P-0.01))):
        a=int((g+o0)*fs); e=int((g+o1)*fs); seg=y[a:e]
        f0,fp,sal=note_of(seg); midi=69+12*np.log2(f0/440)
        r.update({'f0'+lab:float(f0),'midi'+lab:float(midi),'pc'+lab:names[int(round(midi))%12],'octave'+lab:int(round(midi))//12-1,
                  'cents'+lab:float(100*(midi-round(midi))),'raw_peak_hz'+lab:float(fp),'level'+lab:float(20*np.log10(np.sqrt((seg**2).mean())+1e-9))})
    rows.append(r)
print('beat: note (cents) level dB | [first-half note / second-half note]  — per verse, rel = beats from verse onset')
def cell(b):
    r=rows[b]; return f"{r['pc']:2s}{r['octave']}{r['cents']:+4.0f}c {r['level']:5.1f}dB [{r['pc_h1']:2s}/{r['pc_h2']:2s}]"
print('intro (beats 0..%d):'%(VB[0]-1))
for r0 in range(VB[0]%4-4 if VB[0]%4 else 0,VB[0],4):
    print('   beat %3d: '%r0+' | '.join(cell(b) if b>=0 else ' '*27 for b in range(r0,min(r0+4,VB[0]))))
for i,vb in enumerate(VB):
    end=VB[i+1] if i+1<len(VB) else min(vb+28,NB)
    print(f'verse {i+1} (onset beat {vb}, t={PHI+vb*P:.3f}):')
    for r0 in range(vb,min(end,NB),4):
        print('   rel %2d: '%(r0-vb)+' | '.join(cell(b) for b in range(r0,min(r0+4,end,NB))))
st={}
for p in range(24):
    c=Counter()
    for i,vb in enumerate(VB):
        if vb+p<NB: c[rows[vb+p]['pc']]+=1
    st[p]=dict(c)
print('pitch class of the bass by position (0..23) inside the 24-beat verse, 7 verses:')
for bar in range(6):
    print('  bar %d: '%bar+' | '.join(f"b{q}: "+','.join(f'{k}{v}' for k,v in Counter(st[bar*4+q]).most_common(3)) for q in range(4)))
cents=[r['cents'] for r in rows if r['level']>np.median([q['level'] for q in rows])-6]
print('bass cents deviation from equal temperament A440: median %+.1f, IQR %+.1f..%+.1f'%(np.median(cents),np.percentile(cents,25),np.percentile(cents,75)))
json.dump(dict(verse_onset_beats=VB,rows=rows,pc_by_position_in_verse=st,bass_cents_median=float(np.median(cents))),open(O+'/bass_notes.json','w'),indent=0)
