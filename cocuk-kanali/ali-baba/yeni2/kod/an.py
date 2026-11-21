import sys,subprocess,numpy as np,glob,os
def load(p,sr=44100):
    raw=subprocess.run(['ffmpeg','-v','error','-i',p,'-f','f32le','-ac','1','-ar',str(sr),'-'],capture_output=True).stdout
    return np.frombuffer(raw,dtype=np.float32)
def env(x,sr=44100,hop=441):
    n=len(x)//hop; return np.sqrt((x[:n*hop].reshape(n,hop)**2).mean(1)+1e-12)
def segs(e,thr,hop_s=0.01,mingap=0.08,minlen=0.05):
    on=e>thr; out=[];i=0
    while i<len(on):
        if on[i]:
            j=i
            while j<len(on) and on[j]: j+=1
            out.append([i*hop_s,j*hop_s]); i=j
        else: i+=1
    m=[]
    for s in out:
        if m and s[0]-m[-1][1]<mingap: m[-1][1]=s[1]
        else: m.append(s)
    return [s for s in m if s[1]-s[0]>=minlen]
if __name__=='__main__':
    for p in sorted(glob.glob(sys.argv[1]+'/*.mp3')):
        x=load(p); e=env(x); pk=e.max(); db=20*np.log10(e/pk)
        sg=segs(e,pk*10**(-20/20))
        # dominant freq of loudest segment
        print(f"{os.path.basename(p):14s} dur={len(x)/44100:.2f} peak={np.abs(x).max():.2f} floor={np.percentile(db,10):.0f}dB segs(-20dB)="+' '.join(f"{a:.2f}-{b:.2f}" for a,b in sg))
