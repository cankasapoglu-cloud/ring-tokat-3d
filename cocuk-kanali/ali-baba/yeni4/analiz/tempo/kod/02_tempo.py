# Step 1: global tempo + beat phase with two independent methods, and per-window drift check.
#  method A: full-band spectral-flux onset envelope (full mix)
#  method B: low-frequency (40-120 Hz, kick/bass) energy-rise envelope (full mix)
# For each envelope: (1) comb/grid search = mean envelope on a beat grid, maximised over
# (BPM, phase); (2) autocorrelation peak near the expected beat lag.  Search range 99..111 BPM.
import numpy as np, json, scipy.signal as ss
from common import *
x=load_mix()
print('duration %.3f s'%(len(x)/SR))
f,t,S=stft_mag(x)
envA=flux(S,f,30,16000)
ker=np.hanning(5); ker/=ker.sum()
envA=np.convolve(envA,ker,mode='same')
eLF=band_energy_env(x,40,120,smooth_ms=8.0)
tLF=np.arange(len(eLF))*HOP/SR
l=np.log(eLF+1e-4*eLF.max())
envB=np.maximum(np.diff(l,prepend=l[0]),0)
envB=np.convolve(envB,ker,mode='same')
envB=np.interp(t,tLF,envB)
envC=np.convolve(flux(S,f,8000,16000),ker,mode='same')
np.savez(CACHE+'/env.npz',t=t,envA=envA,envB=envB,envC=envC,eLF=np.interp(t,tLF,eLF))

def search(env,t,t0,t1,bpms,nphase=200):
    best=(-1,None,None); table=[]
    e=env/ (env[(t>=t0)&(t<=t1)].mean()+1e-12)
    for bpm in bpms:
        P=60.0/bpm
        ph=t0+np.arange(nphase)/nphase*P
        sc=np.array([grid_score(e,t,P,p,t0,t1) for p in ph])
        k=sc.argmax(); table.append((bpm,sc[k],ph[k]))
        if sc[k]>best[0]: best=(sc[k],bpm,ph[k])
    return best,np.array(table)
def refine(env,t,t0,t1,bpm0,span=0.4,step=0.005,nphase=400):
    return search(env,t,t0,t1,np.arange(bpm0-span,bpm0+span+1e-9,step),nphase)
def acf_tempo(env,t0,t1,lo=BPM_LO,hi=BPM_HI):
    e=env[(t>=t0)&(t<=t1)]; e=e-e.mean()
    ac=ss.correlate(e,e,mode='full',method='fft')[len(e)-1:]; ac/=ac[0]
    res={}
    for mult in (1,4,8,24):
        lag_lo=int(np.floor(mult*60/hi*FPS)); lag_hi=int(np.ceil(mult*60/lo*FPS))
        if lag_hi+1>=len(ac): continue
        k=lag_lo+np.argmax(ac[lag_lo:lag_hi+1])
        y0,y1,y2=ac[k-1],ac[k],ac[k+1]; d=0.5*(y0-y2)/(y0-2*y1+y2)
        res[mult]=dict(bpm=float(mult*60/((k+d)/FPS)),acf=float(y1))
    return res

T0,T1=0.5,float(t[-1])-0.5
out={'envelope_hop_s':HOP/SR,'search_range_bpm':[BPM_LO,BPM_HI],'duration_s':len(x)/SR}
coarse=np.arange(BPM_LO,BPM_HI+1e-4,0.05)
for name,env in (('A_spectral_flux_fullband',envA),('B_lowfreq_40_120Hz',envB),('C_hats_8_16k_flux',envC)):
    best,tab=search(env,t,T0,T1,coarse)
    (sc,bpm,ph),tab2=refine(env,t,T0,T1,best[1])
    P=60/bpm; ph0=ph-np.floor(ph/P)*P
    idx=np.argsort(tab[:,1])[::-1][:5]
    out[name]={'global':dict(bpm=float(bpm),beat_period_s=float(P),phase_first_beat_s=float(ph0),score=float(sc),
                             coarse_top5=[dict(bpm=float(tab[i,0]),score=float(tab[i,1])) for i in idx]),
               'acf_global':acf_tempo(env,T0,T1)}
    print(name,'global bpm %.3f period %.5f phase %.4f score %.3f'%(bpm,P,ph0,sc))
    print('   coarse top5',[(round(tab[i,0],2),round(tab[i,1],3)) for i in idx])
    print('   acf',out[name]['acf_global'])
    wins=[]
    for a in np.arange(0,T1-20+0.01,10.0):
        b=a+20
        bw,tabw=search(env,t,a,b,np.arange(BPM_LO,BPM_HI+1e-4,0.1))
        (scw,bpmw,phw),_=refine(env,t,a,b,bw[1],span=1.0,step=0.02)
        Pw=60/bpmw; c=(a+b)/2
        kb=np.round((c-phw)/Pw); tb=phw+kb*Pw
        dev=((tb-ph0+P/2)%P)-P/2
        ac=acf_tempo(env,a,b)
        wins.append(dict(t0=float(a),t1=float(b),bpm=float(bpmw),score=float(scw),beat_near_centre_s=float(tb),
                         dev_from_global_grid_ms=float(dev*1000),acf_bpm_1beat=ac[1]['bpm'],acf_bpm_4beat=ac[4]['bpm'],acf_bpm_8beat=ac[8]['bpm']))
        print('   win %5.1f-%5.1f bpm %.2f score %.2f dev-from-global %.1f ms | acf1 %.2f acf4 %.2f acf8 %.2f'%(a,b,bpmw,scw,dev*1000,ac[1]['bpm'],ac[4]['bpm'],ac[8]['bpm']))
    out[name]['windows_20s']=wins
json.dump(out,open(O+'/tempo_step1.json','w'),indent=1)
