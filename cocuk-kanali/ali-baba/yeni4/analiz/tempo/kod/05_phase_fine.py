# Fine beat-phase study (about 1 ms resolution): beat-synchronous average of band envelopes on an exact 105.000 BPM fold.
# Shows where inside the beat period the kick attack and the other hits sit; librosa.beat.beat_track as a third opinion.
import numpy as np, json, scipy.signal as ss
from common import *
x=load_mix()
P=60/105.0
def env_band(lo,hi,sm_ms=3.0):
    sos=ss.butter(4,[lo,hi],btype='band',fs=SR,output='sos'); y=ss.sosfiltfilt(sos,x)
    e=y**2
    n=int(SR*sm_ms/1000); k=np.ones(n)/n
    return np.sqrt(np.convolve(e,k,mode='same'))
bands={'kick_40_120':(40,120),'low_120_300':(120,300),'mid_300_2000':(300,2000),'high_2k_8k':(2000,8000),'air_8k_16k':(8000,16000)}
res={}
T0,T1=8.0,100.0          # body of the song
tt=np.arange(int(T0*SR),int(T1*SR))/SR
nbin=571                 # ~1 ms bins over one beat
for name,(lo,hi) in bands.items():
    e=env_band(lo,hi)[int(T0*SR):int(T1*SR)]
    ph=(tt%P)/P
    idx=np.minimum((ph*nbin).astype(int),nbin-1)
    prof=np.bincount(idx,weights=e,minlength=nbin)/np.bincount(idx,minlength=nbin)
    d=np.diff(np.concatenate([prof[-1:],prof]))
    tb=(np.arange(nbin)+0.5)/nbin*P
    k_rise=int(np.argmax(d)); k_peak=int(np.argmax(prof))
    seg=np.roll(prof,-(k_peak-int(0.12/P*nbin)))[:int(0.12/P*nbin)+1]
    mn=seg.min(); half=mn+0.5*(prof[k_peak]-mn)
    j=np.where(seg>=half)[0][0]
    t_half=(tb[k_peak]-0.12+j*P/nbin)%P
    res[name]=dict(peak_phase_s=float(tb[k_peak]),max_rise_phase_s=float(tb[k_rise]),half_rise_phase_s=float(t_half),
                   peak_over_mean=float(prof.max()/prof.mean()),profile=prof.tolist())
    d2=d.copy()
    for q in range(nbin):
        dist=min(abs(q-k_rise),nbin-abs(q-k_rise))*P/nbin
        if dist<0.10: d2[q]=-1
    k2=int(np.argmax(d2))
    res[name]['second_rise_phase_s']=float(tb[k2]); res[name]['second_rise_rel']=float(d[k2]/d[k_rise])
    # rise strength at the four sixteenth positions (max of d within +-25 ms), relative to the max rise
    six=[]
    for q in range(4):
        c=q*P/4; dist=np.minimum(np.abs(tb-c),P-np.abs(tb-c)); six.append(float(d[dist<=0.025].max()/d[k_rise]))
    res[name]['rise_at_sixteenths_rel']=six
    print(f"{name:14s} peak@{tb[k_peak]*1000:6.1f} ms  max-rise@{tb[k_rise]*1000:6.1f} ms  half-rise@{t_half*1000:6.1f} ms  peak/mean {prof.max()/prof.mean():.2f} | 2nd rise@{tb[k2]*1000:6.1f} ms rel {d[k2]/d[k_rise]:.2f} | rise at 16ths {[round(s,2) for s in six]}")
import librosa
y=x.astype(np.float32)
tempo,beats=librosa.beat.beat_track(y=y,sr=SR,hop_length=256,start_bpm=105,units='time',tightness=100)
tempo=float(np.atleast_1d(tempo)[0])
ph=np.array(beats)%P
ang=np.angle(np.exp(2j*np.pi*ph/P).mean()); cm=(ang/(2*np.pi)*P)%P
R=abs(np.exp(2j*np.pi*ph/P).mean())
ibi=np.diff(beats)
print('librosa tempo',tempo,'n beats',len(beats),'median IBI',np.median(ibi),'-> bpm',60/np.median(ibi),'circ-mean phase %.4f s, concentration R=%.3f'%(cm,R))
body=[b for b in beats if 8<b<100]
phb=np.array(body)%P; angb=np.angle(np.exp(2j*np.pi*phb/P).mean()); cmb=(angb/(2*np.pi)*P)%P
fitbpm=60/np.polyfit(np.arange(len(body)),body,1)[0]
print('librosa body beats: circ-mean phase %.4f, R=%.3f, linear-fit bpm %.3f'%(cmb,abs(np.exp(2j*np.pi*phb/P).mean()),fitbpm))
res['librosa_beat_track']=dict(tempo_bpm=tempo,n_beats=len(beats),median_ibi_s=float(np.median(ibi)),circ_mean_phase_s=float(cm),phase_concentration_R=float(R),
     body_circ_mean_phase_s=float(cmb),body_linear_fit_bpm=float(fitbpm),beats=[float(b) for b in beats])
json.dump(res,open(O+'/phase_fine.json','w'))
