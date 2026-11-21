# Ali Baba'nin Ciftligi - backing track builder v3 (energetic, 134 BPM, 2-bar animal slot, G->A at verse 5)
import mido, json, subprocess, numpy as np, sys, os, wave, re
S=sys.argv[1]; O=sys.argv[2]
BPM=134; TPB=480; BEAT=60/BPM; BAR=4*BEAT; sr=44100
SF='/usr/share/sounds/sf2/FluidR3_GM.sf2'
MOD_VERSE=5; MOD=2      # verses >=5 and the ending are a whole step up (A major)
NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
nm=lambda m:f"{NAMES[m%12]}{m//12-1}"
BASE={'D':62,'E':64,'G':67}
VERSES=[('inek',['i','nek','le','ri','var'],['ba','ğı','rır'],'Çiftliğinde inekleri var','diye bağırır'),
 ('koyun',['ko','yun','la','rı','var'],['me','ler'],'Çiftliğinde koyunları var','diye meler'),
 ('at',['bir','de','a','tı','var'],['kiş','ner'],'Çiftliğinde bir de atı var','diye kişner'),
 ('horoz',['ho','roz','la','rı','var'],['ö','ter'],'Çiftliğinde horozları var','diye öter'),
 ('ördek',['ör','dek','le','ri','var'],['ba','ğı','rır'],'Çiftliğinde ördekleri var','diye bağırır'),
 ('köpek',['kö','pek','le','ri','var'],['hav','lar'],'Çiftliğinde köpekleri var','diye havlar'),
 ('kedi',['bir','ke','di','si','var'],['mi','yav','lar'],'Çiftliğinde bir kedisi var','diye miyavlar')]
L1=[(0,.5,'G'),(.5,.5,'G'),(1,.5,'G'),(1.5,.5,'G'),(2,1,'G'),(3,1,'D'),(4,1,'E'),(5,.5,'E'),(5.5,.5,'E'),(6,2,'D')]
L1S=['A','li','Ba','ba','nın','bir','çift','li','ği','var']
L2=[(0,1,'G'),(1,.5,'G'),(1.5,.5,'G'),(2,1,'G'),(3,1,'D'),(4,1,'E'),(5,.5,'E'),(5.5,.5,'E'),(6,2,'D')]
D5=[(0,.5,'G'),(.5,.5,'G'),(1,.5,'G'),(1.5,.5,'G'),(2,1.5,'G')]
D4=[(0,.5,'G'),(.5,.5,'G'),(1,1,'G'),(2,1.5,'G')]
def verse_notes(k):
    an,l2w,dw,_,_=VERSES[k]; out=[]
    for (b,d,n),s in zip(L1,L1S): out.append((1,s,n,b,d))
    for (b,d,n),s in zip(L2,['Çift','li','ğin','de']+l2w): out.append((2,s,n,12+b,d))
    dt=D5 if len(dw)==3 else D4
    for (b,d,n),s in zip(dt,['di','ye']+dw): out.append(('diye',s,n,32+b,d))
    for (b,d,n),s in zip(L2,['Çift','li','ğin','de','A','li','Ba','ba','nın']): out.append((3,s,n,36+b,d))
    return out
INTRO=4; VB=11; NV=7; END=4; TOTAL=INTRO+VB*NV+END
CH={'G':[55,59,62],'C':[55,60,64],'D7':[54,57,60,62],'E7':[56,59,62,64]}
ROOT={'G':43,'C':36,'D7':38,'E7':40}; FIFTH={'G':38,'C':43,'D7':45,'E7':47}
ROLL={'G':[62,67,59,67,62,67,59,67],'C':[64,67,60,67,64,67,60,67],'D7':[62,66,60,66,62,66,57,66],'E7':[64,68,62,68,64,68,59,68]}
# bars: (chords per beat, kind, stabs?, verse index or -1, transpose)
bars=[(['G']*4,'full',0,-1,0),(['C','C','G','G'],'full',0,-1,0),(['G','G','D7','D7'],'full',0,-1,0),(['G']*4,'fillB',0,-1,0)]
for k in range(NV):
    T=MOD if k+1>=MOD_VERSE else 0
    last=['C','C','E7','E7'] if k+1==MOD_VERSE-1 else ['C','C','G','D7']   # E7 pivots into A major
    bars+=[(['G']*4,'full',1,k,T),(['C','C','G','G'],'fillS',1,k,T),(['G','D7','G','G'],'ans',0,k,T),
           (['G']*4,'full',1,k,T),(['C','C','G','G'],'fillS',1,k,T),(['G','D7','G','G'],'ans',0,k,T),
           (['G']*4,'slot',0,k,T),(['G']*4,'slot2',0,k,T),(['G']*4,'full',1,k,T),(['G']*4,'full',1,k,T),(last,'fillB',1,k,T)]
bars+=[(['G','D7','G','G'],'ans',0,9,MOD),(['G','D7','G','G'],'ans2',0,9,MOD),(['C','C','D7','D7'],'roll',0,9,MOD),(['G']*4,'final',0,9,MOD)]
assert len(bars)==TOTAL
ev={}
def add(ch,b,d,n,v): ev.setdefault(ch,[]).append((b,d,n,int(min(127,v))))
BASS,BANJO,ACC,PNO,GLK,TPT,BRS,GUIDE,DR=0,1,2,3,4,5,6,7,9
PROG={BASS:33,BANJO:105,ACC:21,PNO:1,GLK:9,TPT:56,BRS:61,GUIDE:71}
VOL={BASS:113,BANJO:104,ACC:86,PNO:100,GLK:120,TPT:116,BRS:102,GUIDE:92,DR:124}
PAN={BASS:64,BANJO:36,ACC:94,PNO:54,GLK:78,TPT:60,BRS:70,GUIDE:64}
REV={DR:18,BASS:8}
ans_list=[]
def answer(b0,T,hi=False):
    for i,n in enumerate([71,71,69,69,67]):
        b=b0+(i*.5 if i<4 else 2); d=.42 if i<4 else 1.8; v=122 if i in(0,2,4) else 112
        add(TPT,b,d,n+T,v); add(BRS,b,d,n+T,v-10); add(BRS,b,d,n+T-12,v-14); add(GLK,b,d,n+T+12,118)
        if hi: add(BRS,b,d,n+T+4 if i<4 else n+T+4,v-16)   # third above on the repeat (ending)
def drums_full(b0,k,kind):
    for bt in range(4):
        fillS=(kind=='fillS' and bt==3); fillB=(kind=='fillB' and bt>=2)
        add(DR,b0+bt,.2,36,114)
        if bt in(1,3): add(DR,b0+bt,.2,38,114); add(DR,b0+bt,.2,39,104)
        if not(fillS or fillB):
            add(DR,b0+bt,.1,42,86); add(DR,b0+bt+.25,.1,42,46); add(DR,b0+bt+.5,.2,46,80); add(DR,b0+bt+.75,.1,42,52)
        for s,v in((0,44),(.25,36),(.5,74),(.75,40)): add(DR,b0+bt+s,.1,54,v)
        if k>=2:   # extra percussion from verse 3 on
            add(DR,b0+bt,.1,56,84); add(DR,b0+bt+.5,.1,76,72)
            if bt in(1,3): add(DR,b0+bt+.75,.1,77,66)
    add(DR,b0+2.5,.2,36,92)
    if kind=='fillS':
        add(DR,b0+3.25,.1,38,92); add(DR,b0+3.5,.1,48,104); add(DR,b0+3.75,.1,45,112)
    if kind=='fillB':
        for i,(n,v) in enumerate([(38,92),(38,98),(50,102),(50,106),(48,110),(47,114),(45,118),(43,124)]): add(DR,b0+2+i*.25,.1,n,v)
for bi,(ch,kind,stab,k,T) in enumerate(bars):
    b0=bi*4
    if kind in('full','ans','ans2','fillS','fillB'):
        for bt in range(4):
            c=ch[bt]
            low=FIFTH[c] if (bt==2 and c==ch[0]==ch[1]) else ROOT[c]
            add(BASS,b0+bt,.45,low+T,116); add(BASS,b0+bt+.5,.38,ROOT[c]+12+T,104)   # octave-jumping bass
            for e in range(2): add(BANJO,b0+bt+e*.5,.45,ROLL[c][bt*2+e]+T,100 if e==0 else 90)
            add(BANJO,b0+bt+.25,.2,CH[c][-1]+T,70); add(BANJO,b0+bt+.75,.2,CH[c][-1]+T,70)
            for n in CH[c]:
                add(PNO,b0+bt+.5,.28,n+12+T,100)            # off-beat ska/polka upstroke
                if bt in(1,3): add(ACC,b0+bt,.45,n+12+T,92); add(BANJO,b0+bt,.3,n+T,82)
                add(ACC,b0+bt+.5,.25,n+12+T,74)
            if bt in(0,2): add(PNO,b0+bt,.4,ROOT[c]+12+T,92); add(PNO,b0+bt,.4,ROOT[c]+24+T,84)   # "oom"
            if stab and bt in(1,3):
                for n in CH[c][-3:]: add(BRS,b0+bt+.5,.22,n+12+T,96)
        drums_full(b0,k,kind)
        if kind in('ans','ans2'):
            answer(b0,T,hi=(kind=='ans2')); ans_list.append((bi,T)); add(DR,b0,.2,55,104)
    elif kind in('slot','slot2'):
        add(BASS,b0,.9,43+T,84); add(BASS,b0+2,.9,38+T,78)
        for bt in range(4):
            add(DR,b0+bt,.2,36,92 if bt in(0,2) else 66)
            add(DR,b0+bt,.1,42,56); add(DR,b0+bt+.5,.1,42,38)
        if kind=='slot2':   # snare pickup back into the band
            add(DR,b0+3.5,.1,38,96); add(DR,b0+3.75,.1,38,118); add(DR,b0+3.75,.1,45,100)
    elif kind=='roll':
        for i in range(16):
            add(DR,b0+i*.25,.1,38,62+i*4)
            if i>=12: add(DR,b0+i*.25+.125,.1,38,58+i*4)
        for bt in range(4): add(DR,b0+bt,.2,36,112); add(DR,b0+bt,.1,56,84)
        add(DR,b0,.2,49,112)
        for bt,c in((0,'C'),(2,'D7')):
            add(BASS,b0+bt,1.9,ROOT[c]+T+12,118)
            for n in CH[c]:
                add(ACC,b0+bt,1.8,n+12+T,100); add(PNO,b0+bt,1.0,n+T,108); add(PNO,b0+bt,1.0,n+12+T,104); add(BANJO,b0+bt,.6,n+T,104)
                add(BRS,b0+bt,1.8,n+T,104)
        for i,n in enumerate([72,76,79,76,74,78,81,84]):   # rising fanfare
            add(TPT,b0+i*.5,.45,n+T,118); add(GLK,b0+i*.5,.45,n+12+T,112); add(BRS,b0+i*.5,.45,n-12+T,100)
    elif kind=='final':
        for i in range(10): add(DR,b0+i*.25,.1,38,70+i*4)
        add(DR,b0+2.5,.1,38,112); add(DR,b0+2.75,.1,38,120)
        for bt,d in((0,2.4),(3,2.2)):
            add(BASS,b0+bt,d,31+T+12,124); add(BASS,b0+bt,d,43+T+12,120)
            add(DR,b0+bt,.2,36,126); add(DR,b0+bt,.2,49,124); add(DR,b0+bt,.2,57,116); add(DR,b0+bt,.2,39,108)
            if bt==3: add(DR,b0+bt,.2,38,124)
            for n in CH['G']:
                add(ACC,b0+bt,d,n+12+T,106); add(PNO,b0+bt,d,n+T,114); add(PNO,b0+bt,d,n+12+T,108); add(BANJO,b0+bt,d,n+T,110)
                add(BRS,b0+bt,d,n+T,112); add(BRS,b0+bt,d,n+12+T,108)
            add(PNO,b0+bt,d,43+T,112)
            for n in (79,83,86): add(TPT,b0+bt,d,n+T,122); add(GLK,b0+bt,d,n+T,118)
# crashes at section starts
add(DR,0,.2,49,112)
for k in range(NV): add(DR,(INTRO+k*VB)*4,.2,49,116); add(DR,(INTRO+k*VB)*4,.2,57,96); add(DR,(INTRO+k*VB+8)*4,.2,49,100)
add(DR,(INTRO+NV*VB)*4,.2,49,118)
# intro tune: brass + glock
for (b,d,n) in [(0,1,67),(1,1,67),(2,1,67),(3,1,62),(4,1,64),(5,1,64),(6,2,62),(8,1,71),(9,1,71),(10,1,69),(11,1,69),(12,2,67)]:
    add(TPT,b,d*.9,n,118)
    add(BRS,b,d*.9,n,104); add(GLK,b,d*.9,n+12,116)
# guide melody (clarinet)
guide=[]
for k in range(NV):
    vb=(INTRO+k*VB)*4; T=MOD if k+1>=MOD_VERSE else 0
    for (ln,s,n,b,d) in verse_notes(k):
        m=BASE[n]+T; add(GUIDE,vb+b,d*0.9,m,98); guide.append((k+1,ln,s,nm(m),m,vb+b,d))
def write(path,chans):
    mid=mido.MidiFile(ticks_per_beat=TPB); tr=mido.MidiTrack(); mid.tracks.append(tr)
    msgs=[(0,0,mido.MetaMessage('set_tempo',tempo=mido.bpm2tempo(BPM)))]
    for c in chans:
        if c!=DR:
            msgs.append((0,1,mido.Message('program_change',channel=c,program=PROG[c])))
            msgs.append((0,1,mido.Message('control_change',channel=c,control=10,value=PAN[c])))
        msgs.append((0,1,mido.Message('control_change',channel=c,control=7,value=VOL[c])))
        msgs.append((0,1,mido.Message('control_change',channel=c,control=91,value=REV.get(c,40))))
        for (b,d,n,v) in ev.get(c,[]):
            msgs.append((round(b*TPB),3,mido.Message('note_on',channel=c,note=n,velocity=v)))
            msgs.append((round((b+d)*TPB),2,mido.Message('note_off',channel=c,note=n,velocity=0)))
    msgs.sort(key=lambda m:(m[0],m[1])); t=0
    for (tk,_,m) in msgs: tr.append(m.copy(time=tk-t)); t=tk
    mid.save(path)
def render(mid,wav):
    subprocess.run(['fluidsynth','-ni','-q','-g','0.22','-r','44100','-F',wav,SF,mid],check=True,capture_output=True)
def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).reshape(-1,2).astype(np.float64)/32768
def wr(p,x):
    w=wave.open(p,'w'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(x,-1,1)*32767).astype(np.int16).tobytes()); w.close()
def lufs(p):
    e=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',p,'-af','ebur128','-f','null','-'],capture_output=True,text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS',e)[-1])
ALL=[BASS,BANJO,ACC,PNO,GLK,TPT,BRS,DR]
for c in ALL+[GUIDE]: write(f'{S}/st{c}.mid',[c]); render(f'{S}/st{c}.mid',f'{S}/st{c}.wav')
write(S+'/altyapi.mid',ALL); write(S+'/rehber.mid',ALL+[GUIDE])
for n in('altyapi','rehber'): render(f'{S}/{n}.mid',f'{S}/{n}_raw.wav')
a=rd(S+'/altyapi_raw.wav'); r=rd(S+'/rehber_raw.wav')
N=int((TOTAL*BAR+2.5)*sr)
def fit(x):
    x=x[:N] if len(x)>=N else np.vstack([x,np.zeros((N-len(x),2))])
    f=int(0.4*sr); x=x.copy(); x[-f:]*=np.linspace(1,0,f)[:,None]; return x
a=fit(a); r=fit(r)
print('raw peaks',np.abs(a).max(),np.abs(r).max())
TGT=-13.0; CEIL=10**(-1.6/20); KNEE=0.62
def lim(x,g):
    y=x*g; m=np.abs(y); o=m>KNEE
    y[o]=np.sign(y[o])*(KNEE+(CEIL-KNEE)*np.tanh((m[o]-KNEE)/(CEIL-KNEE))); return y
g=10**(-6/20)/np.percentile(np.abs(r),99.9)
for it in range(6):
    wr(S+'/tmp_m.wav',lim(r,g)); L=lufs(S+'/tmp_m.wav')
    if abs(L-TGT)<0.1: break
    g*=10**((TGT-L)/20)
print(f'master gain {g:.3f} rehber LUFS {L} frac samples above knee {(np.abs(r*g)>KNEE).mean():.4f}')
a=lim(a,g); r=lim(r,g)
wr(O+'/altyapi.wav',a); wr(O+'/rehber.wav',r)
ci=np.zeros((int(round(BAR*sr)),2))
for i in range(4):
    t=np.arange(int(.06*sr))/sr; c=np.sin(2*np.pi*(1760 if i==0 else 1320)*t)*np.exp(-t*60)*0.7
    p=int(round(i*BEAT*sr)); ci[p:p+len(c)]+=c[:,None]
wr(S+'/rehber_sayimli.wav',np.vstack([ci,r]))
subprocess.run(['ffmpeg','-v','error','-y','-i',S+'/rehber_sayimli.wav','-c:a','libmp3lame','-b:a','192k',O+'/rehber_sayimli.mp3'],check=True)
R=lambda v:round(v,3)
tmod=(INTRO+(MOD_VERSE-1)*VB)*BAR
Z={'baslik':"Ali Baba'nın Çiftliği",'ezgi':'Old MacDonald Had a Farm (geleneksel, kamu malı)','ton':f'Sol majör (G); {MOD_VERSE}. kıtadan itibaren La majör (A)','olcu':'4/4','tempo_bpm':BPM,
 'vurus_sn':R(BEAT),'olcu_sn':round(BAR,5),'toplam_olcu':TOTAL,'muzik_bitis_sn':R(TOTAL*BAR),'dosya_suresi_sn':R(N/sr),
 'sayim_ofseti_sn':R(BAR),'not':'Tüm zamanlar altyapi.wav / rehber.wav / altyapi_sesli.wav / demo başlangıcına göredir. rehber_sayimli.mp3 için her zamana sayim_ofseti_sn ekleyin.',
 'ton_degisimi':{'kita':MOD_VERSE,'zaman_sn':R(tmod),'onceki':'G majör','sonraki':'A majör','yarim_ses':MOD,'gecis':f'{MOD_VERSE-1}. kıtanın son ölçüsünün 3-4. vuruşlarında E7','ezgi_araligi_once':'D4–G4','ezgi_araligi_sonra':'E4–A4'},
 'form':{'giris_olcu':INTRO,'kita_olcu':VB,'kita_sayisi':NV,'bitis_olcu':END,
   'kita_ici':['ö1-2: satır 1','ö3: enstrümantal cevap (brass+glockenspiel)','ö4-5: satır 2','ö6: enstrümantal cevap','ö7-8: HAYVAN SESİ boşluğu, 2 ölçü, her ölçüde bir ses (yalnız kick+hafif hi-hat+bas)','ö9: "diye ..."','ö10-11: satır 3']},
 'giris':{'baslangic':0,'bitis':R(INTRO*BAR)},'bitis':{'baslangic':R((INTRO+NV*VB)*BAR),'son_vurus':R((TOTAL-1)*BAR+3*BEAT)},'kitalar':[]}
lyr=[]
for k in range(NV):
    an,_,_,l2,dy=VERSES[k]; v0=(INTRO+k*VB)*BAR; ton='A majör' if k+1>=MOD_VERSE else 'G majör'
    notes=[{'satir':ln,'hece':s,'nota':n,'midi':m,'baslangic':R(b*BEAT),'sure':R(d*BEAT)} for (kk,ln,s,n,m,b,d) in guide if kk==k+1]
    Z['kitalar'].append({'kita':k+1,'hayvan':an,'ton':ton,'baslangic':R(v0),
      'satir1':{'soz':"Ali Baba'nın bir çiftliği var",'baslangic':R(v0),'bitis':R(v0+2*BAR)},
      'cevap1':{'baslangic':R(v0+2*BAR),'bitis':R(v0+3*BAR)},
      'satir2':{'soz':l2,'baslangic':R(v0+3*BAR),'bitis':R(v0+5*BAR)},
      'cevap2':{'baslangic':R(v0+5*BAR),'bitis':R(v0+6*BAR)},
      'hayvan_sesi':{'baslangic':R(v0+6*BAR),'bitis':R(v0+8*BAR),'ses1_baslangic':R(v0+6*BAR),'ses2_baslangic':R(v0+7*BAR)},
      'diye':{'soz':dy,'baslangic':R(v0+8*BAR),'bitis':R(v0+9*BAR)},
      'satir3':{'soz':"Çiftliğinde Ali Baba'nın",'baslangic':R(v0+9*BAR),'bitis':R(v0+11*BAR)},
      'bitis':R(v0+11*BAR),'notalar':notes})
    lyr.append(f"{k+1}. KITA — {an}  ({v0:.2f} sn, {ton})\nAli Baba'nın bir çiftliği var\n   (müzik cevabı)\n{l2}\n   (müzik cevabı)\n[{an} sesi] [{an} sesi]   (2 ölçü, iki kez)\n{dy}\nÇiftliğinde Ali Baba'nın\n")
json.dump(Z,open(O+'/zaman.json','w'),ensure_ascii=False,indent=1)
open(O+'/sozler.txt','w').write(f"ALİ BABA'NIN ÇİFTLİĞİ\n(Ezgi: Old MacDonald Had a Farm — geleneksel)\n4/4, {BPM} BPM. Sol majör; {MOD_VERSE}. kıtadan itibaren bir tam ses yukarı (La majör).\nGiriş 4 ölçü, her kıta 11 ölçü, bitiş 4 ölçü.\n\n[Giriş — 4 ölçü müzik]\n\n"+'\n'.join(lyr)+"\n[Bitiş — 4 ölçü müzik: cevap x2, trampet fanfarı + davul rulosu, final vuruşu]\n")
json.dump({'guide':guide,'ans':ans_list,'BEAT':BEAT,'BAR':BAR,'INTRO':INTRO,'VB':VB,'NV':NV},open(S+'/meta.json','w'),ensure_ascii=False)
print('VERSE 1 TABLE (verses 5-7: +2 semitones)'); print('line  syll   note midi  start_s  dur_s')
for (kk,ln,s,n,m,b,d) in guide:
    if kk==1: print(f"{str(ln):5s} {s:6s} {n:4s} {m:3d} {b*BEAT:8.3f} {d*BEAT:6.3f}")
print('total bars',TOTAL,'music end',TOTAL*BAR,'file',N/sr)
