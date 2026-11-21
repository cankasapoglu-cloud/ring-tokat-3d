# Fine beat-phase study (1 ms resolution): beat-synchronous average of band envelopes.
# Shows where inside the 116 BPM beat period the kick attack and the off-beat "chick" sit,
# and gives a third opinion from librosa.beat.beat_track.
import numpy as np, json, scipy.signal as ss
from common import *
x=load_mix()
P=60/116.0
def env_band(lo,hi,sm_ms=3.0):
    if lo is None: y=x
    else:
        sos=ss.butter(4,[lo,hi],btype='band',fs=SR,output='sos'); y=ss.sosfiltfilt(sos,x)
    e=y**2
    n=int(SR*sm_ms/1000); k=np.ones(n)/n
    return np.sqrt(np.convolve(e,k,mode='same'))
bands={'kick_40_120':(40,120),'low_120_300':(120,300),'mid_300_2000':(300,2000),'high_2k_8k':(2000,8000),'air_8k_16k':(8000,16000)}
res={}
T0,T1=6.0,100.0          # body of the song (drums present)
tt=np.arange(int(T0*SR),int(T1*SR))/SR
nbin=517                 # ~1 ms bins over one beat
for name,(lo,hi) in bands.items():
    e=env_band(lo,hi)[int(T0*SR):int(T1*SR)]
    ph=(tt%P)/P
    idx=np.minimum((ph*nbin).astype(int),nbin-1)
    prof=np.bincount(idx,weights=e,minlength=nbin)/np.bincount(idx,minlength=nbin)
    # rise = positive derivative of the folded envelope (circular)
    d=np.diff(np.concatenate([prof[-1:],prof]))
    tb=(np.arange(nbin)+0.5)/nbin*P
    k_rise=int(np.argmax(d)); k_peak=int(np.argmax(prof))
    # 50%-rise point before the peak: walk back from the peak to the preceding minimum
    seg=np.roll(prof,-(k_peak-int(0.12/P*nbin)))[:int(0.12/P*nbin)+1]   # last 120 ms before peak
    mn=seg.min(); half=mn+0.5*(prof[k_peak]-mn)
    j=np.where(seg>=half)[0][0]
    t_half=(tb[k_peak]-0.12+j*P/nbin)%P
    res[name]=dict(peak_phase_s=float(tb[k_peak]),max_rise_phase_s=float(tb[k_rise]),half_rise_phase_s=float(t_half),
                   peak_over_mean=float(prof.max()/prof.mean()),profile=prof.tolist())
    # second strongest rise at least 150 ms away (the other eighth)
    d2=d.copy(); 
    for q in range(nbin):
        dist=min(abs(q-k_rise),nbin-abs(q-k_rise))*P/nbin
        if dist<0.15: d2[q]=-1
    k2=int(np.argmax(d2))
    res[name]['second_rise_phase_s']=float(tb[k2]); res[name]['second_rise_rel']=float(d[k2]/d[k_rise])
    print(f"{name:14s} peak@{tb[k_peak]*1000:6.1f} ms  max-rise@{tb[k_rise]*1000:6.1f} ms  half-rise@{t_half*1000:6.1f} ms  peak/mean {prof.max()/prof.mean():.2f} | 2nd rise@{tb[k2]*1000:6.1f} ms rel {d[k2]/d[k_rise]:.2f}")
# librosa third opinion
import librosa
y=x.astype(np.float32)
tempo,beats=librosa.beat.beat_track(y=y,sr=SR,hop_length=256,start_bpm=116,units='time',tightness=100)
tempo=float(np.atleast_1d(tempo)[0])
ph=np.array(beats)%P
# circular mean of beat phases relative to the 116.00 grid
ang=np.angle(np.exp(2j*np.pi*ph/P).mean()); cm=(ang/(2*np.pi)*P)%P
R=abs(np.exp(2j*np.pi*ph/P).mean())
ibi=np.diff(beats)
print('librosa tempo',tempo,'n beats',len(beats),'median IBI',np.median(ibi),'-> bpm',60/np.median(ibi),'circ-mean phase %.4f s, concentration R=%.3f'%(cm,R))
body=[b for b in beats if 6<b<100]
phb=np.array(body)%P; angb=np.angle(np.exp(2j*np.pi*phb/P).mean()); cmb=(angb/(2*np.pi)*P)%P
print('librosa body beats: circ-mean phase %.4f, R=%.3f, linear-fit bpm %.3f'%(cmb,abs(np.exp(2j*np.pi*phb/P).mean()),60/np.polyfit(np.arange(len(body)),body,1)[0]))
res['librosa_beat_track']=dict(tempo_bpm=tempo,n_beats=len(beats),median_ibi_s=float(np.median(ibi)),circ_mean_phase_s=float(cm),phase_concentration_R=float(R),
     body_circ_mean_phase_s=float(cmb),body_linear_fit_bpm=float(60/np.polyfit(np.arange(len(body)),body,1)[0]),beats=[float(b) for b in beats])
json.dump(res,open(O+'/phase_fine.json','w'))
