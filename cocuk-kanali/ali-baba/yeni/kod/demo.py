import sys,json,os,shutil,subprocess,numpy as np,wave
S,O=sys.argv[1:3]; sys.path.insert(0,S+'/code'); import an
sr=44100
PICK={'inek':('inek_2',[[0.90,2.06],[3.92,5.10]],.09,"iki farklı möö (aynı kayıt)"),
'koyun':('koyun_1',[[1.07,2.36],[1.07,2.36]],.09,"aynı meleme iki kez"),
'at':('at_4',[[0.02,1.72],[0.02,1.72]],.22,"aynı kişneme iki kez, sonu 1,7 sn'de fade ile kısaltıldı"),
'horoz':('horoz_4',[[0.07,1.77],[0.07,1.77]],.30,"aynı ötüş iki kez, sonu 1,7 sn'de fade ile kısaltıldı"),
'ordek':('ordek_2',[[0.35,1.60],[1.94,3.18]],.07,"vak vak + vak vak: 1-2. ve 3-4. vaklamalar"),
'kopek':('kopek_1',[[0.05,0.77],[1.85,2.60]],.07,"hav hav + hav hav: 1-2. ve 3-4. havlamalar"),
'kedi':('kedi_1',[[0.00,0.72],[1.80,2.46]],.09,"iki farklı miyav (aynı kayıt)")}
Z=json.load(open(O+'/zaman.json'))
def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).reshape(-1,2).astype(np.float64)/32768
def wr(p,x):
    w=wave.open(p,'w'); w.setnchannels(x.shape[1] if x.ndim>1 else 1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(x,-1,1)*32767).astype(np.int16).tobytes()); w.close()
mix=rd(O+'/rehber.wav'); base=rd(O+'/altyapi.wav'); mix2=base.copy()
os.makedirs(O+'/ses/kirpilmis',exist_ok=True)
for f in os.listdir(O+'/ses/kirpilmis'): os.remove(O+'/ses/kirpilmis/'+f)
db=lambda v:20*np.log10(v+1e-12); out={'model':'eleven_text_to_sound_v3','flow_id':'qdvipqwtDeWv5QJDVnRV','kredi_toplam':476,'kredi_not':'7 çağrı x 4 varyasyon x ~16,67 kredi (çağrı başına 68). Tüm varyasyonlar ses/alternatif/ içinde. 2. sürümde yeni üretim yapılmadı.','sesler':{}}
for k,(key,(src,trims,fo_s,note)) in enumerate(PICK.items()):
    shutil.copy(f'{O}/ses/alternatif/{src}.mp3',f'{O}/ses/{key}.mp3')
    x=an.load(f'{O}/ses/{key}.mp3'); e=an.env(x); sg=an.segs(e,e.max()*0.1)
    v=Z['kitalar'][k]; s0,s1=v['hayvan_sesi']['baslangic'],v['hayvan_sesi']['bitis']
    bs=base[int(s0*sr):int(s1*sr)].mean(1); slot_b=db(np.sqrt((bs**2).mean())); calls=[]
    for i,(a,b) in enumerate(trims):
        c=x[int(a*sr):int(b*sr)].astype(np.float64).copy(); fi=int(.015*sr); fo=int(fo_s*sr)
        c[:fi]*=np.linspace(0,1,fi); c[-fo:]*=np.linspace(1,0,fo)
        ce=an.env(c.astype(np.float32)); loud=ce[ce>ce.max()*0.1]; r=np.sqrt((loud**2).mean())
        g=min(10**(-13/20)/r, 10**(-1.5/20)/np.abs(c).max()); c*=g
        wr(f'{O}/ses/kirpilmis/{key}_{i+1}.wav',c); L=len(c)/sr
        t=v['hayvan_sesi'][f'ses{i+1}_baslangic']-0.04; p=int(round(t*sr)); mix[p:p+len(c)]+=c[:,None]; mix2[p:p+len(c)]+=c[:,None]
        cr=db(np.sqrt((c**2).mean()))
        calls.append({'kirpma_sn':[a,b],'dosya':f'ses/kirpilmis/{key}_{i+1}.wav','sure_sn':round(L,2),'yerlesim_sn':[round(t,3),round(t+L,3)],'rms_dBFS':round(cr,1),'altyapidan_fark_dB':round(cr-slot_b,1)})
        print(f"{key:6s} {src} call{i+1} trim={a}-{b} len={L:.2f} place={t:.2f}-{t+L:.2f} rms={cr:.1f} (+{cr-slot_b:.1f} dB over backing {slot_b:.1f}) peak={db(np.abs(c).max()):.1f}")
    out['sesler'][key]={'dosya':f'ses/{key}.mp3','kaynak_varyasyon':src,'sure_sn':round(len(x)/sr,2),
      'yuksek_bolumler_sn(-20dB)':[[round(a,2),round(b,2)] for a,b in sg],'yuksek_aralik_sn':[round(sg[0][0],2),round(sg[-1][1],2)],
      'aciklama':note,'kita':k+1,'bosluk_sn':[s0,s1],'cagrilar':calls}
json.dump(out,open(O+'/ses/sesler.json','w'),ensure_ascii=False,indent=1)
def guard(y,T=0.80,C=10**(-1.6/20)):
    y=y.copy(); m=np.abs(y); o=m>T; y[o]=np.sign(y[o])*(T+(C-T)*np.tanh((m[o]-T)/(C-T))); return y
print('pre-guard peaks demo/altyapi_sesli',np.abs(mix).max(),np.abs(mix2).max()); mix=guard(mix); mix2=guard(mix2)
print('final peaks dBFS',db(np.abs(mix).max()),db(np.abs(mix2).max())); wr(S+'/demo.wav',mix); wr(O+'/altyapi_sesli.wav',mix2)
subprocess.run(['ffmpeg','-v','error','-y','-i',S+'/demo.wav','-af','loudnorm=I=-13:TP=-1:LRA=11','-ar','44100','-c:a','libmp3lame','-b:a','192k',O+'/demo_altyapi_sesli.mp3'],check=True)
