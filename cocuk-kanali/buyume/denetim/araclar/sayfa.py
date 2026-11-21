# Denetim icin bakis sayfalari uretir (yalniz buyume/denetim icine yazar).
import os, glob
from PIL import Image, ImageDraw, ImageFont
K='/home/user/ring-tokat-3d/cocuk-kanali'; O=K+'/buyume/denetim'
os.makedirs(O+'/sayfalar',exist_ok=True)
def font(s):
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']:
        if os.path.exists(p): return ImageFont.truetype(p,s)
    return ImageFont.load_default()
F=font(22)
kapak={
 '1-alibaba':[K+'/ali-baba/kapak.jpg',K+'/ali-baba/kapak-7.jpg'],
 '2-aile':[K+'/pitirin-ailesi/kare/13_kucak.png'],
 '3-parmak':[K+'/parmak-ailesi/kapak.jpg'],
 '4-maymun':[K+'/bes-kucuk-maymun/kapak.jpg'],
 '5-balon':[K+'/balon-sarkisi/kapak.jpg'],
 '6-elyikama':[K+'/el-yikama/kare/09_temiz.png'],
 '7-otobus':[K+'/otobus-sarkisi/kare/02_kanca_b.png'],
}
def fit(im,w,h):
    im=im.convert('RGB'); r=min(w/im.width,h/im.height)
    im2=im.resize((max(1,int(im.width*r)),max(1,int(im.height*r))),Image.LANCZOS)
    bg=Image.new('RGB',(w,h),(40,40,40)); bg.paste(im2,((w-im2.width)//2,(h-im2.height)//2)); return bg
allk=[]
for ad,ks in kapak.items():
    fr=sorted(glob.glob(f'{O}/kareler/{ad}_k*.jpg'))
    cells=[(os.path.basename(p).split('_')[-1][:-4]+' sn',Image.open(p)) for p in fr]
    for k in ks:
        im=Image.open(k); print(ad,os.path.relpath(k,K),im.size,round(os.path.getsize(k)/1e6,2),'MB', 'oran=%.3f'%(im.width/im.height))
        cells.append(('KAPAK ADAYI '+os.path.basename(k),im)); allk.append((ad,os.path.basename(k),im))
    cols=3; rows=(len(cells)+cols-1)//cols
    W,H=640,360; sheet=Image.new('RGB',(cols*W,rows*(H+30)),(20,20,20)); d=ImageDraw.Draw(sheet)
    for i,(lab,im) in enumerate(cells):
        x=(i%cols)*W; y=(i//cols)*(H+30)
        sheet.paste(fit(im,W,H),(x,y+30)); d.text((x+8,y+3),f'{ad}  {lab}',fill=(255,255,0),font=F)
    sheet.save(f'{O}/sayfalar/{ad}.jpg',quality=88)
# tum kapak adaylari: telefon liste boyu (320x180) ve onerilen-video boyu (168x94)
W,H=320,180; n=len(allk); sheet=Image.new('RGB',(4*W+50,2*(H+30)+ (94+40)),(245,245,245)); d=ImageDraw.Draw(sheet); f2=font(15)
for i,(ad,nm,im) in enumerate(allk):
    x=10+(i%4)*(W+10); y=(i//4)*(H+30)
    sheet.paste(fit(im,W,H),(x,y+24)); d.text((x,y+3),f'{ad} {nm}',fill=(0,0,0),font=f2)
y=2*(H+30)+10
for i,(ad,nm,im) in enumerate(allk):
    sheet.paste(fit(im,168,94),(10+i*(168+4),y+20))
d.text((10,y),'168x94 (onerilenler sutunu boyu)',fill=(0,0,0),font=f2)
sheet.save(f'{O}/sayfalar/kapak-adaylari.jpg',quality=90)
