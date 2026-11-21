# Shared helpers for the tempo-grid analysis of dinle_2.
import json, numpy as np, soundfile as sf, scipy.signal as ss
A='/home/user/ring-tokat-3d/cocuk-kanali/ali-baba'
O=A+'/yeni3/analiz/tempo'
SR=44100
HOP=256            # 5.805 ms envelope hop
NFFT=2048
FPS=SR/HOP

CACHE=O+'/gecici'          # deletable cache (decoded mix, envelopes); re-created on demand
def load_mix():
    import os, subprocess
    p=CACHE+'/mix_44k_mono.wav'
    if not os.path.exists(p):
        os.makedirs(CACHE,exist_ok=True)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',A+'/dinle_2.mp3','-ar',str(SR),'-ac','1',p],check=True)
    x,sr=sf.read(p); assert sr==SR; return x
def lattice():
    """refined beat lattice of the mix (14_lattice.py): returns (beat period s, time of beat 0 s)"""
    L=json.load(open(O+'/lattice.json')); return L['beat_period_s'],L['phase_first_beat_s']
def load_vocal():
    x,sr=sf.read(A+'/dinle_2_vokal.wav'); assert sr==SR
    if x.ndim>1: x=x.mean(1)
    return x
def load_words():
    d=json.load(open(A+'/dinle_2_words.json'))
    w=d['words'] if isinstance(d,dict) else d
    return [x for x in w if x.get('type')=='word']

def stft_mag(x,nfft=NFFT,hop=HOP):
    f,t,S=ss.stft(x,SR,window='hann',nperseg=nfft,noverlap=nfft-hop,boundary='zeros',padded=True)
    return f,t,np.abs(S)       # t = frame centre times (s)

def flux(S,f,lo=None,hi=None,log_c=100.0):
    """Half-wave rectified log-magnitude spectral flux in a band. Frame i = change from i-1 to i,
    i.e. it is time-stamped at frame centre i."""
    band=np.ones(len(f),bool)
    if lo is not None: band&=f>=lo
    if hi is not None: band&=f<=hi
    L=np.log1p(log_c*S[band])
    d=np.diff(L,axis=1,prepend=L[:,:1])
    return np.maximum(d,0).sum(0)

def band_energy_env(x,lo,hi,smooth_ms=10.0,order=4):
    """Band-pass, rectify, low-pass -> amplitude envelope sampled at HOP."""
    sos=ss.butter(order,[lo,hi],btype='band',fs=SR,output='sos')
    y=ss.sosfiltfilt(sos,x)
    sos2=ss.butter(2,1000.0/smooth_ms/2/np.pi*2,btype='low',fs=SR,output='sos')
    e=ss.sosfiltfilt(sos2,np.abs(y))
    return np.maximum(e[::HOP],0)

def interp_env(env,t,times):
    """Linear interpolation of an envelope (sampled at frame times `t`) at arbitrary times."""
    return np.interp(times,t,env,left=0,right=0)

def grid_score(env,t,period,phase,t0,t1,width=0.0):
    """Mean envelope value on the beat grid phase + k*period inside [t0,t1]."""
    k0=np.ceil((t0-phase)/period); k1=np.floor((t1-phase)/period)
    g=phase+np.arange(k0,k1+1)*period
    return interp_env(env,t,g).mean()
