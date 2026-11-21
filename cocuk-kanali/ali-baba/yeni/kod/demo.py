import sys,json,os,shutil,subprocess,numpy as np,wave
S,O=sys.argv[1:3]; sys.path.insert(0,S+'/code'); import an
sr=44100
PICK={'inek':('inek_2',[[0.90,2.06]],"A real cow mooing twice, clear and close, farm recording"),
'koyun':('koyun_1',[[1.07,2.36]],"A real sheep bleating twice (baa, baa), clear and close"),
'at':('at_4',[[0.02,1.90]],"A real horse neighing (whinny) once, clear and close"),
'horoz':('horoz_4',[[0.07,2.10]],"A real rooster crowing once (cock-a-doodle-doo), clear and close"),
'ordek':('ordek_2',[[0.35,2.38]],"A real duck quacking three times, clear and close"),
'kopek':('kopek_2',[[1.46,2.39]],"A friendly dog barking twice, clear and close"),
'kedi':('kedi_1',[[0.00,0.72],[1.80,2.46]],"A real cat meowing twice, cute, clear and close")}
Z=json.load(open(O+'/zaman.json'))
def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).reshape(-1,2).astype(np.float64)/32768
def wr(p,x):
    w=wave.open(p,'w'); w.setnchannels(x.shape[1] if x.ndim>1 else 1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(x,-1,1)*32767).astype(np.int16).tobytes()); w.close()
mix=rd(O+'/rehber.wav'); base=mix.copy()
os.makedirs(O+'/ses/alternatif',exist_ok=True); os.makedirs(O+'/ses/kirpilmis',exist_ok=True)
for f in os.listdir(S+'/dl'): shutil.copy(S+'/dl/'+f,O+'/ses/alternatif/'+f)
db=lambda v:20*np.log10(v+1e-12); out={'model':'eleven_text_to_sound_v3','flow_id':'qdvipqwtDeWv5QJDVnRV','kredi_toplam':476,'kredi_not':'7 çağrı x 4 varyasyon x ~16,67 kredi (çağrı başına 68). Seçilmeyen varyasyonlar ses/alternatif/ içinde.','sesler':{}}
for k,(key,(src,trims,prompt)) in enumerate(PICK.items()):
    shutil.copy(f'{S}/dl/{src}.mp3',f'{O}/ses/{key}.mp3')
    x=an.load(f'{O}/ses/{key}.mp3'); e=an.env(x); sg=an.segs(e,e.max()*0.1)
    parts=[]
    for i,(a,b) in enumerate(trims):
        c=x[int(a*sr):int(b*sr)].astype(np.float64).copy(); fi=int(.015*sr); fo=int(.09*sr)
        c[:fi]*=np.linspace(0,1,fi); c[-fo:]*=np.linspace(1,0,fo); parts.append(c)
        if i<len(trims)-1: parts.append(np.zeros(int(.12*sr)))
    c=np.concatenate(parts)
    ce=an.env(c.astype(np.float32)); loud=ce[ce>ce.max()*0.1]; r=np.sqrt((loud**2).mean())
    g=min(10**(-15/20)/r, 10**(-1.5/20)/np.abs(c).max()); c*=g
    wr(f'{O}/ses/kirpilmis/{key}.wav',c)
    v=Z['kitalar'][k]; s0,s1=v['hayvan_sesi']['baslangic'],v['hayvan_sesi']['bitis']; L=len(c)/sr
    t=s0+(s1-s0-L)/2 if L<=s1-s0 else s1+0.03-L
    p=int(round(t*sr)); mix[p:p+len(c)]+=c[:,None]
    bs=base[int(s0*sr):int(s1*sr)].mean(1); slot_b=db(np.sqrt((bs**2).mean()))
    clip_r=db(np.sqrt((c**2).mean()))
    out['sesler'][key]={'dosya':f'ses/{key}.mp3','kaynak_varyasyon':src,'prompt':prompt,'sure_sn':round(len(x)/sr,2),
      'yuksek_bolumler_sn(-20dB)':[[round(a,2),round(b,2)] for a,b in sg],'yuksek_aralik_sn':[round(sg[0][0],2),round(sg[-1][1],2)],
      'kirpma_sn':trims,'kirpilmis_dosya':f'ses/kirpilmis/{key}.wav','kirpilmis_sure_sn':round(L,2),
      'demo_yerlesim_sn':[round(t,3),round(t+L,3)],'bosluk_sn':[s0,s1],'kita':k+1,
      'demo_seviye':{'ses_rms_dBFS':round(clip_r,1),'altyapi_bosluk_rms_dBFS':round(slot_b,1),'fark_dB':round(clip_r-slot_b,1)}}
    print(f"{key:6s} src={src} dur={len(x)/sr:.2f} loud={sg[0][0]:.2f}-{sg[-1][1]:.2f} trim={trims} len={L:.2f} place={t:.2f}-{t+L:.2f} slot={s0}-{s1} clip_rms={clip_r:.1f} backing_slot={slot_b:.1f} peak={db(np.abs(c).max()):.1f}")
json.dump(out,open(O+'/ses/sesler.json','w'),ensure_ascii=False,indent=1)
print('mix peak',np.abs(mix).max()); wr(S+'/demo.wav',mix)
subprocess.run(['ffmpeg','-v','error','-y','-i',S+'/demo.wav','-af','loudnorm=I=-15:TP=-1.5:LRA=11','-ar','44100','-c:a','libmp3lame','-b:a','192k',O+'/demo_altyapi_sesli.mp3'],check=True)
