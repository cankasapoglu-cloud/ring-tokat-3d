import mido, json, subprocess, numpy as np, sys, os, wave
S=sys.argv[1]; O=sys.argv[2]
BPM=126; TPB=480; BEAT=60/BPM; BAR=4*BEAT
SF='/usr/share/sounds/sf2/FluidR3_GM.sf2'
NN={'D4':62,'E4':64,'G4':67}
names={62:'D4',64:'E4',67:'G4'}
VERSES=[('inek',['i','nek','le','ri','var'],['ba','ğı','rır'],'Çiftliğinde inekleri var','diye bağırır'),
 ('koyun',['ko','yun','la','rı','var'],['me','ler'],'Çiftliğinde koyunları var','diye meler'),
 ('at',['bir','de','a','tı','var'],['kiş','ner'],'Çiftliğinde bir de atı var','diye kişner'),
 ('horoz',['ho','roz','la','rı','var'],['ö','ter'],'Çiftliğinde horozları var','diye öter'),
 ('ördek',['ör','dek','le','ri','var'],['ba','ğı','rır'],'Çiftliğinde ördekleri var','diye bağırır'),
 ('köpek',['kö','pek','le','ri','var'],['hav','lar'],'Çiftliğinde köpekleri var','diye havlar'),
 ('kedi',['bir','ke','di','si','var'],['mi','yav','lar'],'Çiftliğinde bir kedisi var','diye miyavlar')]
# rhythm templates: (beat offset from line start, dur beats, note)
L1=[(0,.5,'G4'),(.5,.5,'G4'),(1,.5,'G4'),(1.5,.5,'G4'),(2,1,'G4'),(3,1,'D4'),(4,1,'E4'),(5,.5,'E4'),(5.5,.5,'E4'),(6,2,'D4')]
L1S=['A','li','Ba','ba','nın','bir','çift','li','ği','var']
L2=[(0,1,'G4'),(1,.5,'G4'),(1.5,.5,'G4'),(2,1,'G4'),(3,1,'D4'),(4,1,'E4'),(5,.5,'E4'),(5.5,.5,'E4'),(6,2,'D4')]
D5=[(0,.5,'G4'),(.5,.5,'G4'),(1,.5,'G4'),(1.5,.5,'G4'),(2,1.5,'G4')]
D4=[(0,.5,'G4'),(.5,.5,'G4'),(1,1,'G4'),(2,1.5,'G4')]
def verse_notes(k):
    an,l2w,dw,_,_=VERSES[k]; out=[]
    for (b,d,n),s in zip(L1,L1S): out.append((1,s,n,b,d))
    for (b,d,n),s in zip(L2,['Çift','li','ğin','de']+l2w): out.append((2,s,n,12+b,d))
    dt=D5 if len(dw)==3 else D4
    for (b,d,n),s in zip(dt,['di','ye']+dw): out.append(('diye',s,n,28+b,d))
    for (b,d,n),s in zip(L2,['Çift','li','ğin','de','A','li','Ba','ba','nın']): out.append((3,s,n,32+b,d))
    return out
INTRO=4; VB=10; NV=7; END=4; TOTAL=INTRO+VB*NV+END
CH={'G':[55,59,62],'C':[55,60,64],'D7':[54,57,60,62]}
ROOT={'G':43,'C':36,'D7':38}; FIFTH={'G':38,'C':43,'D7':45}
ROLL={'G':[62,67,59,67,62,67,59,67],'C':[64,67,60,67,64,67,60,67],'D7':[62,66,60,66,62,66,57,66]}
# per-bar: (chords per beat, kind)
bars=[]
bars+= [(['G']*4,'full'),(['C','C','G','G'],'full'),(['G','G','D7','D7'],'full'),(['G']*4,'fill')]
VPAT=[(['G']*4,'full'),(['C','C','G','G'],'full'),(['G','D7','G','G'],'ans'),
      (['G']*4,'full'),(['C','C','G','G'],'full'),(['G','D7','G','G'],'ans'),
      (['G']*4,'slot'),(['G']*4,'full'),(['G']*4,'full'),(['C','C','G','D7'],'full')]
for k in range(NV): bars+=VPAT
bars+=[(['G','D7','G','G'],'ans'),(['G','D7','G','G'],'ans'),(['C','C','D7','D7'],'stop'),(['G']*4,'final')]
assert len(bars)==TOTAL
ev={}  # channel -> list of (start_beat, dur_beats, note, vel)
def add(ch,b,d,n,v): ev.setdefault(ch,[]).append((b,d,n,v))
BASS,BANJO,ACC,PNO,GLK,FLT,GUIDE,DR=0,1,2,3,4,5,6,9
PROG={BASS:32,BANJO:105,ACC:21,PNO:0,GLK:9,FLT:73,GUIDE:71}
VOL={BASS:94,BANJO:88,ACC:92,PNO:94,GLK:108,FLT:96,GUIDE:74,DR:108}
PAN={BASS:64,BANJO:38,ACC:92,PNO:56,GLK:74,FLT:58,GUIDE:64}
def lead(b,d,n,v=108):
    add(GLK,b,d,n,v); add(FLT,b,d*0.92,n,v-14)
def answer(b0,pno=False):
    for i,n in enumerate([83,83,81,81]): lead(b0+i*.5,.5,n)
    lead(b0+2,1.75,79,112)
    if pno:
        for i,n in enumerate([71,71,69,69]): add(PNO,b0+i*.5,.45,n,96)
        add(PNO,b0+2,1.5,67,100)
for bi,(ch,kind) in enumerate(bars):
    b0=bi*4
    if kind in('full','ans','fill'):
        for bt in range(4):
            c=ch[bt]
            if bt==0 or c!=ch[bt-1] or bt==2:
                n=ROOT[c] if (bt==0 or c!=ch[bt-1] or c!=ch[0]) else FIFTH[c]
                add(BASS,b0+bt,.9,n,104 if bt==0 else 96)
            for e in range(2):
                add(BANJO,b0+bt+e*.5,.45,ROLL[c][bt*2+e]+0,88 if e==0 else 76)
            if bt in(1,3):
                for n in CH[c]: add(ACC,b0+bt,.4,n+12,84)
                for n in CH[c]: add(BANJO,b0+bt,.3,n,70)
            if bt in(0,2):
                for n in CH[c]: add(PNO,b0+bt,.8,n,80 if bt==0 else 70)
                add(PNO,b0+bt,.8,ROOT[c]+12,74)
        add(BASS,b0+3.5,.4,FIFTH[ch[3]] if kind!='ans' else 38,84)
        for bt in range(4):
            add(DR,b0+bt,.2,36 if bt in(0,2) else 38,108 if bt in(0,2) else 98)
            if bt in(1,3): add(DR,b0+bt,.2,39,96)
            add(DR,b0+bt,.2,42,82); add(DR,b0+bt+.5,.2,42,60); add(DR,b0+bt+.5,.2,54,52)
        add(DR,b0+2.5,.2,36,84)
        if kind=='fill':
            for e in range(4): add(DR,b0+2+e*.5,.2,38,78+e*10)
            add(DR,b0+3.75,.2,38,110)
    elif kind=='slot':   # light beat + bass only
        add(BASS,b0,.9,43,74); add(BASS,b0+2,.9,38,68)
        for bt in range(4):
            if bt in(0,2): add(DR,b0+bt,.2,36,84)
            add(DR,b0+bt,.2,42,58); add(DR,b0+bt+.5,.2,42,40)
        add(DR,b0+3.5,.2,38,70); add(DR,b0+3.75,.2,38,86)  # tiny pickup back into the band
    elif kind=='stop':
        for bt,c in((0,'C'),(2,'D7')):
            add(BASS,b0+bt,.6,ROOT[c],112); add(DR,b0+bt,.2,36,115); add(DR,b0+bt,.2,38,110); add(DR,b0+bt,.2,39,100)
            for n in CH[c]:
                add(ACC,b0+bt,.5,n+12,100); add(PNO,b0+bt,.5,n,104); add(BANJO,b0+bt,.5,n,100)
            lead(b0+bt,.5,84 if c=='C' else 81,112)
        add(DR,b0+3.5,.2,38,90); add(DR,b0+3.75,.2,38,104)
    elif kind=='final':
        add(BASS,b0,3,31,118); add(BASS,b0,3,43,112)
        add(DR,b0,.2,36,122); add(DR,b0,.2,38,112); add(DR,b0,.2,49,118); add(DR,b0,.2,39,100)
        for n in CH['G']:
            add(ACC,b0,3,n+12,100); add(PNO,b0,3,n,108); add(PNO,b0,3,n+12,100); add(BANJO,b0,3,n,104)
        add(BANJO,b0,3,67,104)
        for n in (79,83,86): lead(b0,3,n,116)
# crashes at section starts
add(DR,0,.2,49,104)
for k in range(NV): add(DR,(INTRO+k*VB)*4,.2,49,96)
add(DR,(INTRO+NV*VB)*4,.2,49,100)
# intro lead: G G G D | E E D - | B B A A | G -
for i,(b,d,n) in enumerate([(0,1,79),(1,1,79),(2,1,79),(3,1,74),(4,1,76),(5,1,76),(6,2,74),(8,1,83),(9,1,83),(10,1,81),(11,1,81),(12,2.5,79)]): lead(b,d*.95,n)
# verse answers
ans_bars=[]
for k in range(NV):
    vb=INTRO+k*VB
    for a in (2,5): answer((vb+a)*4); ans_bars.append(vb+a)
eb=INTRO+NV*VB
answer(eb*4); answer((eb+1)*4,pno=True)
# guide melody
guide=[]
for k in range(NV):
    vb=(INTRO+k*VB)*4
    for (ln,s,n,b,d) in verse_notes(k):
        add(GUIDE,vb+b,d*0.9,NN[n],96); guide.append((k+1,ln,s,n,vb+b,d))
def write(path,chans):
    mid=mido.MidiFile(ticks_per_beat=TPB); tr=mido.MidiTrack(); mid.tracks.append(tr)
    msgs=[(0,0,mido.MetaMessage('set_tempo',tempo=mido.bpm2tempo(BPM)))]
    for c in chans:
        if c!=DR:
            msgs.append((0,1,mido.Message('program_change',channel=c,program=PROG[c])))
            msgs.append((0,1,mido.Message('control_change',channel=c,control=10,value=PAN[c])))
        msgs.append((0,1,mido.Message('control_change',channel=c,control=7,value=VOL[c])))
        msgs.append((0,1,mido.Message('control_change',channel=c,control=91,value=40)))
        for (b,d,n,v) in ev.get(c,[]):
            msgs.append((round(b*TPB),3,mido.Message('note_on',channel=c,note=n,velocity=v)))
            msgs.append((round((b+d)*TPB),2,mido.Message('note_off',channel=c,note=n,velocity=0)))
    msgs.sort(key=lambda m:(m[0],m[1])); t=0
    for (tk,_,m) in msgs: tr.append(m.copy(time=tk-t)); t=tk
    mid.save(path)
def render(mid,wav):
    subprocess.run(['fluidsynth','-ni','-q','-g','0.3','-r','44100','-F',wav,SF,mid],check=True,capture_output=True)
def rd(p):
    w=wave.open(p); x=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).reshape(-1,2).astype(np.float64)/32768; return x
def wr(p,x):
    w=wave.open(p,'w'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
    w.writeframes((np.clip(x,-1,1)*32767).astype(np.int16).tobytes()); w.close()
ALL=[BASS,BANJO,ACC,PNO,GLK,FLT,DR]
[write(f'{S}/st{c}.mid',[c]) or render(f'{S}/st{c}.mid',f'{S}/st{c}.wav') for c in ALL+[GUIDE]]; write(S+'/altyapi.mid',ALL); write(S+'/rehber.mid',ALL+[GUIDE]); write(S+'/guide.mid',[GUIDE]); write(S+'/lead.mid',[GLK,FLT])
for n in('altyapi','rehber','guide','lead'): render(f'{S}/{n}.mid',f'{S}/{n}_raw.wav')
a=rd(S+'/altyapi_raw.wav'); r=rd(S+'/rehber_raw.wav')
N=int((TOTAL*BAR+2.5)*44100)
def fit(x):
    x=x[:N] if len(x)>=N else np.vstack([x,np.zeros((N-len(x),2))])
    f=int(0.4*44100); x=x.copy(); x[-f:]*=np.linspace(1,0,f)[:,None]; return x
a=fit(a); r=fit(r)
print('raw peaks',np.abs(a).max(),np.abs(r).max())
g=10**(-7/20)/np.percentile(np.abs(r),99.9)
def lim(x,T=0.6,C=0.84):
    y=x*g; m=np.abs(y); o=m>T
    y[o]=np.sign(y[o])*(T+(C-T)*np.tanh((m[o]-T)/(C-T))); return y
print('gain',g,'frac samples above knee',(np.abs(r*g)>0.6).mean())
a=lim(a); r=lim(r)
wr(O+'/altyapi.wav',a); wr(O+'/rehber.wav',r)
# count-in: 4 clicks, one bar
sr=44100; ci=np.zeros((int(round(BAR*sr)),2))
for i in range(4):
    t=np.arange(int(.06*sr))/sr; c=np.sin(2*np.pi*(1760 if i==0 else 1320)*t)*np.exp(-t*60)*0.6
    p=int(round(i*BEAT*sr)); ci[p:p+len(c)]+=c[:,None]
wr(S+'/rehber_sayimli.wav',np.vstack([ci,r]))
subprocess.run(['ffmpeg','-v','error','-y','-i',S+'/rehber_sayimli.wav','-c:a','libmp3lame','-b:a','192k',O+'/rehber_sayimli.mp3'],check=True)
# timing json
R=lambda v:round(v,3)
Z={'baslik':"Ali Baba'nın Çiftliği",'ezgi':'Old MacDonald Had a Farm (geleneksel, kamu malı)','ton':'Sol majör (G)','olcu':'4/4','tempo_bpm':BPM,
 'vurus_sn':R(BEAT),'olcu_sn':R(BAR),'toplam_olcu':TOTAL,'muzik_bitis_sn':R(TOTAL*BAR),'dosya_suresi_sn':R(N/44100),
 'sayim_ofseti_sn':R(BAR),'not':'Tüm zamanlar altyapi.wav / rehber.wav / demo başlangıcına göredir. rehber_sayimli.mp3 için her zamana sayim_ofseti_sn ekleyin.',
 'form':{'giris_olcu':INTRO,'kita_olcu':VB,'kita_sayisi':NV,'bitis_olcu':END,
   'kita_ici':['ö1-2: satır 1','ö3: enstrümantal cevap (Si Si La La Sol)','ö4-5: satır 2','ö6: enstrümantal cevap','ö7: HAYVAN SESİ boşluğu (yalnız hafif davul+bas)','ö8: "diye ..."','ö9-10: satır 3']},
 'giris':{'baslangic':0,'bitis':R(INTRO*BAR)},'bitis':{'baslangic':R((INTRO+NV*VB)*BAR),'son_akor':R((TOTAL-1)*BAR)},'kitalar':[]}
lyr=[]
for k in range(NV):
    an,_,_,l2,dy=VERSES[k]; v0=(INTRO+k*VB)*BAR
    notes=[{'satir':ln,'hece':s,'nota':n,'midi':NN[n],'baslangic':R(b*BEAT),'sure':R(d*BEAT)} for (kk,ln,s,n,b,d) in guide if kk==k+1]
    Z['kitalar'].append({'kita':k+1,'hayvan':an,'baslangic':R(v0),
      'satir1':{'soz':"Ali Baba'nın bir çiftliği var",'baslangic':R(v0),'bitis':R(v0+2*BAR)},
      'cevap1':{'baslangic':R(v0+2*BAR),'bitis':R(v0+3*BAR)},
      'satir2':{'soz':l2,'baslangic':R(v0+3*BAR),'bitis':R(v0+5*BAR)},
      'cevap2':{'baslangic':R(v0+5*BAR),'bitis':R(v0+6*BAR)},
      'hayvan_sesi':{'baslangic':R(v0+6*BAR),'bitis':R(v0+7*BAR)},
      'diye':{'soz':dy,'baslangic':R(v0+7*BAR),'bitis':R(v0+8*BAR)},
      'satir3':{'soz':"Çiftliğinde Ali Baba'nın",'baslangic':R(v0+8*BAR),'bitis':R(v0+10*BAR)},
      'bitis':R(v0+10*BAR),'notalar':notes})
    lyr.append(f"{k+1}. KITA — {an}  ({v0:.2f} sn)\nAli Baba'nın bir çiftliği var\n   (müzik cevabı)\n{l2}\n   (müzik cevabı)\n[{an} sesi]\n{dy}\nÇiftliğinde Ali Baba'nın\n")
json.dump(Z,open(O+'/zaman.json','w'),ensure_ascii=False,indent=1)
open(O+'/sozler.txt','w').write("ALİ BABA'NIN ÇİFTLİĞİ\n(Ezgi: Old MacDonald Had a Farm — geleneksel)\nSol majör, 4/4, 126 BPM. Giriş 4 ölçü, her kıta 10 ölçü, bitiş 4 ölçü.\n\n[Giriş — 4 ölçü müzik]\n\n"+'\n'.join(lyr)+"\n[Bitiş — 4 ölçü müzik, \"ta-da\"]\n")
json.dump({'guide':guide,'ans_bars':ans_bars,'BEAT':BEAT,'BAR':BAR,'g':g},open(S+'/meta.json','w'),ensure_ascii=False)
print('VERSE 1 TABLE'); print('line  syll   note midi  beat   start_s  dur_s')
for (kk,ln,s,n,b,d) in guide:
    if kk==1: print(f"{str(ln):5s} {s:6s} {n:4s} {NN[n]:3d} {b-INTRO*4:5.1f} {b*BEAT:8.3f} {d*BEAT:6.3f}")
print('total bars',TOTAL,'music end',TOTAL*BAR,'file',N/44100)
