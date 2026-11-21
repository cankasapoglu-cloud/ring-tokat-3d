#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanal görsellerini projedeki HAZIR Pıtır resimlerinden üretir.
Resim üreten hiçbir servis kullanılmaz, internet gerekmez.

Kullanım:
    python3 uret.py                                    -> "Dudek Stüdyo" / "Pıtır ile Öğren"
    python3 uret.py "Düdük Stüdyo"                     -> yalnızca kanal adı değişir
    python3 uret.py "Düdük Stüdyo" "Pıtır ile Öğren"   -> iki ad da verilir

Çıktılar (bu dosyanın durduğu klasöre yazılır):
    banner_2560x1440.png   kapak görseli; adlar ve Pıtır ortadaki 1546x423 güvenli alanda
    profil_800x800.png     profil resmi; daire kırpılınca yüz tam görünür
    filigran_150x150.png   videoların köşesine konan şeffaf küçük Pıtır
    kontrol_*.png          yalnızca gözle kontrol içindir, YouTube'a yüklenmez
"""
import argparse
import math
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]  # cocuk-kanali klasörü
LANCZOS = Image.Resampling.LANCZOS
BICUBIC = Image.Resampling.BICUBIC

# ---- Kaynak resimler (hepsi projede zaten var) ----
K = {
    "arka": KOK / "3d/hazir/bg_cayir.jpg",                # çayır ve gökyüzü
    "pitir_banner": KOK / "3d/varlik/pitir_salla_agiz.png",  # el sallayan, gülen Pıtır
    "pitir_yuz": KOK / "3d/varlik/pitir_durus_agiz.png",     # önden, gülen Pıtır
    "gunes": KOK / "3d/hazir/gunes.png",
    "balon": KOK / "3d/hazir",                            # balon_<renk>.png
    "ornek_kare": KOK / "ali-baba/kare/10.png",           # yalnızca filigran kontrolü için
}

# ---- Yazı tipi: projedeki başlıklarla aynı (Fredoka kalın). Yoksa DejaVu Sans Bold. ----
FONTLAR = [
    KOK / "uzun-01/fonts/fredoka-latin-700-normal.woff2",      # a-z, ü ö ç, ı
    KOK / "uzun-01/fonts/fredoka-latin-ext-700-normal.woff2",  # İ ş Ş ğ Ğ
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]

# (ana renk, açık ton, koyu ton) — videolardaki başlıklarla aynı palet
PALET = [
    ((229, 57, 53), (255, 138, 128), (154, 18, 18)),    # kırmızı
    ((30, 136, 229), (144, 202, 249), (11, 60, 138)),   # mavi
    ((251, 140, 0), (255, 204, 128), (168, 78, 0)),     # turuncu
    ((67, 160, 71), (165, 214, 167), (20, 82, 26)),     # yeşil
    ((142, 36, 170), (206, 147, 216), (67, 17, 122)),   # mor
]

GUVENLI = (1546, 423)  # YouTube'un her cihazda gösterdiği orta alan


# ------------------------------------------------------------------ yazı tipi
@lru_cache(None)
def _font(yol, boy):
    try:
        return ImageFont.truetype(str(yol), boy, layout_engine=ImageFont.Layout.BASIC)
    except Exception:
        return None


YOLLAR = [y for y in FONTLAR if _font(y, 48) is not None]
if not YOLLAR:
    sys.exit("HATA: hiçbir yazı tipi açılamadı.")


@lru_cache(None)
def _iz(yol, h):
    im = Image.new("L", (140, 140), 0)
    ImageDraw.Draw(im).text((40, 95), h, font=_font(yol, 48), fill=255, anchor="ls")
    return im.tobytes()


def harf_var(yol, h):
    """Bu yazı tipinde bu harf gerçekten var mı? (Yoksa 'boş kutu' çizilir; onu yakalar.)"""
    return h.isspace() or _iz(yol, h) != _iz(yol, "￿")


def font_sec(h, boy):
    for y in YOLLAR:
        if harf_var(y, h):
            return _font(y, boy)
    return _font(YOLLAR[-1], boy)


def eksik_harfler(metin):
    return [h for h in metin if not any(harf_var(y, h) for y in YOLLAR)]


def olc(metin, boy, ara):
    fl = [font_sec(h, boy) for h in metin]
    xs, x = [], 0.0
    for f, h in zip(fl, metin):
        xs.append(x)
        x += f.getlength(h) + ara
    return fl, xs, x - ara


# ------------------------------------------------------------------ yardımcılar
def kat(renk, maske):
    """Tek renkli (ya da resimli) katman; saydamlığı maskeden alır. Kenarlar kararmaz."""
    k = renk.convert("RGBA") if isinstance(renk, Image.Image) else Image.new("RGBA", maske.size, tuple(renk) + (255,))
    k.putalpha(maske)
    return k


def ustune(tuval, im, x, y):
    """im'i tuvalin (x, y) noktasına saydamlığıyla koyar; taşan kısmı kırpar."""
    x, y = round(x), round(y)
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(im.width, tuval.width - x), min(im.height, tuval.height - y)
    if ex > sx and ey > sy:
        tuval.alpha_composite(im.crop((sx, sy, ex, ey)), (x + sx, y + sy))


def boyut(im, yukseklik=None, olcek=None):
    if olcek is None:
        olcek = yukseklik / im.height
    return im.resize((max(1, round(im.width * olcek)), max(1, round(im.height * olcek))), LANCZOS)


def kesim_ac(yol):
    """Şeffaf zeminli resmi açar, kenardaki 1 piksellik gri saçağı tıraşlar."""
    im = Image.open(yol).convert("RGBA")
    im.putalpha(im.getchannel("A").filter(ImageFilter.MinFilter(3)))
    return im


def golgeli(im, dx=0, dy=6, bulanik=8, alfa=90, renk=(0, 0, 0)):
    """Resmin altına yumuşak gölge ekler. (resim, pay) döndürür; pay kadar sola-yukarı koy."""
    pay = int(bulanik * 3 + max(abs(dx), abs(dy)) + 2)
    a = Image.new("L", (im.width + 2 * pay, im.height + 2 * pay), 0)
    a.paste(im.getchannel("A"), (pay + dx, pay + dy))
    a = a.filter(ImageFilter.GaussianBlur(bulanik)).point(lambda v: v * alfa // 255)
    out = kat(renk, a)
    out.alpha_composite(im, (pay, pay))
    return out, pay


def cikartma(im, kalinlik, renk=(255, 255, 255)):
    """Resmin çevresine çıkartma gibi düz renkli kenar ekler. (resim, pay) döndürür."""
    pay = int(kalinlik * 2.5 + 6)
    a = Image.new("L", (im.width + 2 * pay, im.height + 2 * pay), 0)
    a.paste(im.getchannel("A"), (pay, pay))
    # önce ince bıyık ve tüy uçlarını yok say ki kenar çizgisi pürüzsüz olsun
    g = a.filter(ImageFilter.GaussianBlur(kalinlik * 0.35)).point(lambda v: 255 if v >= 128 else 0)
    g = g.filter(ImageFilter.GaussianBlur(kalinlik / 1.6))
    g = g.point(lambda v: 255 if v >= 14 else 0).filter(ImageFilter.GaussianBlur(1.3))
    out = kat(renk, g)
    out.alpha_composite(im, (pay, pay))
    return out, pay


def satirlar(a):
    """Her satır için (sol, sağ, dolu piksel sayısı) ya da None."""
    m = a.point(lambda v: 255 if v > 128 else 0)
    out = []
    for y in range(m.height):
        s = m.crop((0, y, m.width, y + 1))
        k = s.getbbox()
        out.append((k[0], k[2], s.histogram()[255]) if k else None)
    return out


def bas_olcusu(im):
    """Pıtır'ın başını bulur: (merkez x, merkez y, merkezden en uzak nokta) — kaynak pikseliyle."""
    s = satirlar(im.getchannel("A"))
    H = im.height
    ust = next(y for y, k in enumerate(s) if k)
    boyun = min((k[2], y) for y, k in enumerate(s) if k and 0.42 * H <= y <= 0.60 * H)[1]
    bas = [(y, k) for y, k in enumerate(s[:boyun]) if k]
    cx = (min(k[0] for _, k in bas) + max(k[1] for _, k in bas)) / 2
    cy = (ust + boyun) / 2
    r = max(max(math.hypot(k[0] - cx, y - cy), math.hypot(k[1] - cx, y - cy)) for y, k in bas)
    return cx, cy, r, boyun


def kuyruksuz(im):
    """Boynun altında, gövdenin solunda kalan kuyruğu siler.
    (Yakın çekimde kuyruk ucu kenarda anlamsız bir leke gibi duruyordu.)"""
    im = im.copy()
    cx, _, _, boyun = bas_olcusu(im)
    a = im.getchannel("A")
    px = a.load()
    cxi, onceki, egim, gecmis = round(cx), None, 0.0, []
    for y in range(boyun, im.height):
        if px[cxi, y] <= 40:
            break
        gercek = cxi
        while gercek > 0 and px[gercek - 1, y] > 40:
            gercek -= 1
        if onceki is not None and gercek < onceki - 10:   # kuyruk kola yapışmış: kol kenarını tahmin et
            onceki = max(float(gercek), onceki + egim)
        else:
            onceki = float(gercek)
            gecmis.append(gercek)
            if len(gecmis) >= 12:
                egim = (gecmis[-1] - gecmis[-12]) / 11
        for x in range(round(onceki)):
            px[x, y] = 0
    im.putalpha(a)
    return im


# ------------------------------------------------------------------ yazılar
def renkli_yazi(metin, boy):
    """Videolardaki başlık stili: her harf ayrı renk, beyaz kenar, koyu kabartma."""
    ara = boy * 0.07
    fl, xs, toplam = olc(metin, boy, ara)
    kal = max(2, round(boy * 0.10))      # koyu kenar
    byz = max(1, round(boy * 0.055))     # beyaz kenar
    kay = boy * 0.085                    # kabartma derinliği
    pay = kal + math.ceil(kay) + 8
    W = math.ceil(toplam) + 2 * pay
    H = math.ceil(boy * 1.7) + 2 * pay
    taban = pay + round(boy * 1.15)
    koyular, beyazlar, dolgular = [], [], []
    n = 0
    for h, f, x in zip(metin, fl, xs):
        if h.isspace():
            continue
        ana, acik, koyu = PALET[n % len(PALET)]
        n += 1
        px = pay + x
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        for q in range(6):
            d.text((px, taban + kay * q / 5 + boy * 0.01), h, font=f, fill=255, anchor="ls",
                   stroke_width=kal, stroke_fill=255)
        koyular.append(kat(koyu, m))
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).text((px, taban), h, font=f, fill=255, anchor="ls", stroke_width=byz, stroke_fill=255)
        beyazlar.append(kat((255, 255, 255), m))
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).text((px, taban), h, font=f, fill=255, anchor="ls")
        sutun = Image.new("RGB", (1, H))
        y0, y1 = taban - boy * 0.80, taban + boy * 0.10
        for y in range(H):
            # en üstte bile rengin yarısı kalsın: Ö, ü, ğ, İ noktaları soluk çıkmasın
            u = 0.5 + 0.5 * min(1.0, max(0.0, (y - y0) / (y1 - y0)) / 0.45)
            sutun.putpixel((0, y), tuple(round(a + (b - a) * u) for a, b in zip(acik, ana)))
        dolgular.append(kat(sutun.resize((W, H)), m))
    tuval = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for k in koyular + beyazlar + dolgular:
        tuval.alpha_composite(k)
    return tuval.crop(tuval.getbbox())


def etiket(metin, boy, yazi=(11, 60, 138), zemin=(255, 255, 255), kenar=(255, 179, 0)):
    """Yuvarlak köşeli beyaz etiket içinde tek renkli yazı (stüdyo adı için)."""
    ara = boy * 0.03
    fl, xs, toplam = olc(metin, boy, ara)
    xp, yp = round(boy * 0.62), round(boy * 0.40)
    kb = max(3, round(boy * 0.08))
    buyuk = round(boy * 0.70)  # büyük harf yüksekliği (yaklaşık)
    W, H = math.ceil(toplam) + 2 * xp, buyuk + 2 * yp
    S = 4

    def hap(ic):
        m = Image.new("L", (W * S, H * S), 0)
        ImageDraw.Draw(m).rounded_rectangle((ic * S, ic * S, (W - ic) * S - 1, (H - ic) * S - 1),
                                            radius=(H / 2 - ic) * S, fill=255)
        return m.resize((W, H), LANCZOS)

    t = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    t.alpha_composite(kat(kenar, hap(0)))
    t.alpha_composite(kat(zemin, hap(kb)))
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for h, f, x in zip(metin, fl, xs):
        d.text((xp + x, yp + buyuk), h, font=f, fill=255, anchor="ls")
    t.alpha_composite(kat(yazi, m))
    return t


def sigdir(ciz, metin, max_gen, max_yuk, boy):
    """Yazıyı verilen genişliğe ve yüksekliğe sığana kadar küçültür."""
    while True:
        im = ciz(metin, boy)
        if (im.width <= max_gen and im.height <= max_yuk) or boy <= 24:
            return im, boy
        boy = min(boy - 2, int(boy * min(max_gen / im.width, max_yuk / im.height)))


# ------------------------------------------------------------------ banner
def banner_ciz(kanal, program, bulanik=2.2):
    W, H = 2560, 1440
    gx0, gy0 = (W - GUVENLI[0]) // 2, (H - GUVENLI[1]) // 2
    gx1, gy1 = gx0 + GUVENLI[0], gy0 + GUVENLI[1]

    # Zemin: projedeki çayır resmi. Hafif bulanık; Pıtır ve yazı öne çıksın.
    arka = Image.open(K["arka"]).convert("RGB")
    ol = max(W * 1.05 / arka.width, H * 1.05 / arka.height)
    arka = arka.resize((round(arka.width * ol), round(arka.height * ol)), LANCZOS)
    x0, y0 = (arka.width - W) // 2, round((arka.height - H) * 0.42)
    t = arka.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(bulanik)).convert("RGBA")

    # Süsler: yalnızca güvenli alanın DIŞINDA (televizyonda ve bilgisayarda görünür).
    ustune(t, boyut(Image.open(K["gunes"]).convert("RGBA"), yukseklik=270), 1490, 70)

    def balon(ad, mx, ust, yuk, aci):
        b = boyut(Image.open(K["balon"] / f"balon_{ad}.png").convert("RGBA"), yukseklik=yuk)
        if aci:
            b = b.rotate(aci, resample=BICUBIC, expand=True)
        ustune(t, b, mx - b.width / 2, ust)

    for b in [("turuncu", 840, 150, 150, 5), ("yesil", 1160, 80, 115, -4),
              ("kirmizi", 150, 470, 470, -9), ("sari", 318, 395, 500, 7), ("mavi", 240, 640, 430, -2),
              ("yesil", 2410, 470, 470, 9), ("mor", 2242, 395, 500, -7), ("turuncu", 2320, 640, 430, 2)]:
        balon(*b)

    # Pıtır: güvenli alanın solunda, ayakları çimende.
    p = boyut(kesim_ac(K["pitir_banner"]), yukseklik=396)
    px, py = gx0 + 36, gy1 - 10 - p.height
    ayak = [k for k in satirlar(p.getchannel("A"))[-30:-6] if k]
    ax0, ax1 = min(k[0] for k in ayak), max(k[1] for k in ayak)
    g = Image.new("L", (p.width + 120, 120), 0)
    ImageDraw.Draw(g).ellipse((60 + ax0 - 18, 38, 60 + ax1 + 18, 88), fill=120)
    ustune(t, kat((15, 60, 10), g.filter(ImageFilter.GaussianBlur(9))), px - 60, py + p.height - 72)
    ustune(t, p, px, py)
    kutular = {"Pıtır": (px, py, px + p.width, py + p.height)}

    # Yazılar: Pıtır'ın sağında; büyük program adı, altında etiket içinde kanal adı.
    ax, bx = px + p.width + 26, gx1 - 40
    baslik, boy = sigdir(renkli_yazi, program, bx - ax, 250, 150)
    hap, _ = sigdir(etiket, kanal, (bx - ax) * 0.85, 120, max(40, round(boy * 0.52)))
    bosluk = 18
    blok = baslik.height + bosluk + hap.height
    cx = (ax + bx) // 2
    by = gy0 + (GUVENLI[1] - blok) // 2
    # yazının arkasına bulut gibi yumuşak beyaz ışık
    isik = Image.new("L", (W, H), 0)
    ImageDraw.Draw(isik).ellipse((cx - baslik.width // 2 - 40, by - 10, cx + baslik.width // 2 + 40, by + blok + 10), fill=150)
    t.alpha_composite(kat((255, 255, 255), isik.filter(ImageFilter.GaussianBlur(60))))
    bxy = (cx - baslik.width // 2, by)
    hxy = (cx - hap.width // 2, by + baslik.height + bosluk)
    for im, (x, y), ayar in [(baslik, bxy, dict(dy=8, bulanik=10, alfa=85, renk=(10, 40, 90))),
                             (hap, hxy, dict(dy=6, bulanik=8, alfa=90, renk=(10, 40, 90)))]:
        gl, pay = golgeli(im, **ayar)
        ustune(t, gl, x - pay, y - pay)
    kutular["Program adı"] = bxy + (bxy[0] + baslik.width, bxy[1] + baslik.height)
    kutular["Kanal adı"] = hxy + (hxy[0] + hap.width, hxy[1] + hap.height)

    tasan = [ad for ad, k in kutular.items() if k[0] < gx0 or k[1] < gy0 or k[2] > gx1 or k[3] > gy1]
    return t.convert("RGB"), (gx0, gy0, gx1, gy1), kutular, tasan, boy


# ------------------------------------------------------------------ profil
def profil_ciz():
    N, S = 800, 2
    T = N * S
    # Zemin: ortası açık, kenarı koyu gök mavisi + hafif güneş ışınları
    gecis = Image.radial_gradient("L").resize((T, T), BICUBIC)
    t = Image.composite(Image.new("RGB", (T, T), (46, 150, 236)), Image.new("RGB", (T, T), (196, 236, 255)), gecis).convert("RGBA")
    isin = Image.new("L", (T, T), 0)
    d = ImageDraw.Draw(isin)
    for i in range(12):
        d.pieslice((-T, -T, 2 * T, 2 * T), i * 30 - 97, i * 30 - 83, fill=46)
    t.alpha_composite(kat((255, 255, 255), isin.filter(ImageFilter.GaussianBlur(3))))

    im = kuyruksuz(kesim_ac(K["pitir_yuz"]))
    cx, cy, r, _ = bas_olcusu(im)
    s = 0.90 * (T / 2) / r                      # kulak uçları dairenin içinde kalsın
    b = boyut(im, olcek=s)
    rgb = Image.merge("RGB", b.split()[:3]).filter(ImageFilter.UnsharpMask(radius=3, percent=70, threshold=2))
    b = Image.merge("RGBA", rgb.split() + (b.getchannel("A"),))
    st, pay = cikartma(b, 10 * S)
    gl, pay2 = golgeli(st, dy=7 * S, bulanik=9 * S, alfa=75, renk=(8, 50, 110))
    ustune(t, gl, T / 2 - cx * s - pay - pay2, T * 0.485 - cy * s - pay - pay2)
    return t.resize((N, N), LANCZOS).convert("RGB")


# ------------------------------------------------------------------ filigran
def filigran_ciz():
    N, S = 150, 4
    T = N * S
    im = kuyruksuz(kesim_ac(K["pitir_yuz"]))
    cx, cy, r, _ = bas_olcusu(im)
    s = 0.76 * (T / 2) / r
    k = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    ustune(k, boyut(im, olcek=s), T / 2 - cx * s, T * 0.455 - cy * s)
    R = 0.845 * T / 2                           # gövdeyi yuvarlak bir çizgiyle bitir
    disk = Image.new("L", (T, T), 0)
    ImageDraw.Draw(disk).ellipse((T / 2 - R, T / 2 - R, T / 2 + R, T / 2 + R), fill=255)
    k.putalpha(ImageChops.multiply(k.getchannel("A"), disk))
    st, pay = cikartma(k, 3.6 * S)
    gl, pay2 = golgeli(st, dy=3, bulanik=5, alfa=90)
    t = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    ustune(t, gl, -pay - pay2, -pay - pay2)
    return t.resize((N, N), LANCZOS)


# ------------------------------------------------------------------ kontrol resimleri
def daire(im, cap):
    k = im.convert("RGBA").resize((cap, cap), LANCZOS)
    m = Image.new("L", (cap * 4, cap * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, cap * 4 - 1, cap * 4 - 1), fill=255)
    k.putalpha(m.resize((cap, cap), LANCZOS))
    return k


def kontroller(cikti, ban, alan, prof, fil):
    gx0, gy0, gx1, gy1 = alan
    ban.crop(alan).save(cikti / "kontrol_banner_orta_1546x423.png")
    ban.crop((0, gy0, ban.width, gy1)).save(cikti / "kontrol_banner_masaustu_2560x423.png")
    # Hangi cihaz neresini görüyor?
    k = ban.resize((1280, 720), LANCZOS)
    d = ImageDraw.Draw(k)
    f = _font(FONTLAR[-1], 18) or _font(YOLLAR[0], 18)
    for i, (ad, gen, renk) in enumerate([("Sarı çerçeve: bilgisayar 2560x423", 2560, (255, 235, 59)),
                                         ("Turuncu çerçeve: tablet 1855x423", 1855, (255, 152, 0)),
                                         ("Kırmızı çerçeve: telefon = güvenli alan 1546x423", 1546, (255, 82, 82))]):
        x = (2560 - gen) / 4
        d.rectangle((x, gy0 / 2, 1280 - x - 1, gy1 / 2), outline=renk, width=3)
        d.text((12, 36 + i * 26), ad, font=f, fill=renk, stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((12, 10), "Televizyon: resmin tamamı", font=f, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    k.save(cikti / "kontrol_banner_alanlar.png")
    # Profil: daire kırpması, büyük ve küçük boylar
    k = Image.new("RGBA", (1060, 820), (240, 240, 240, 255))
    ImageDraw.Draw(k).rectangle((830, 0, 1060, 410), fill=(24, 24, 24))
    ustune(k, daire(prof, 800), 10, 10)
    for cap, x, y in [(176, 857, 30), (98, 896, 236), (48, 921, 348), (176, 857, 440), (98, 896, 646), (48, 921, 758)]:
        ustune(k, daire(prof, cap), x, y)
    k.convert("RGB").save(cikti / "kontrol_profil_daire.png")
    # Filigran: koyu, açık ve renkli zeminde + gerçek bir video karesinin köşesinde
    kare = Image.open(K["ornek_kare"]).convert("RGBA").resize((1280, 720), LANCZOS)
    k = Image.new("RGBA", (1280, 220 + 720), (255, 255, 255, 255))
    for i, renk in enumerate([(20, 20, 20), (255, 255, 255), (60, 150, 60), (90, 170, 240), (250, 150, 30), (128, 128, 128)]):
        ImageDraw.Draw(k).rectangle((i * 213, 0, i * 213 + 213, 220), fill=renk)
        ustune(k, fil, i * 213 + 31, 35)
    ustune(kare, fil.resize((100, 100), LANCZOS), 1280 - 100 - 24, 720 - 100 - 24)
    ustune(k, kare, 0, 220)
    k.convert("RGB").save(cikti / "kontrol_filigran.png")
    # Türkçe harf denemesi
    a = renkli_yazi("ıİ şŞ ğĞ üÜ öÖ çÇ", 110)
    b = etiket("ıİ şŞ ğĞ üÜ öÖ çÇ", 60)
    k = Image.new("RGBA", (max(a.width, b.width) + 60, a.height + b.height + 80), (120, 190, 240, 255))
    ustune(k, a, 30, 20)
    ustune(k, b, 30, a.height + 50)
    k.convert("RGB").save(cikti / "kontrol_harfler.png")


# ------------------------------------------------------------------ ana akış
def main():
    ap = argparse.ArgumentParser(description="Kanal görsellerini (kapak, profil, filigran) üretir.")
    ap.add_argument("kanal", nargs="?", default="Dudek Stüdyo", help="Kanal / stüdyo adı")
    ap.add_argument("program", nargs="?", default="Pıtır ile Öğren", help="Program adı")
    ap.add_argument("--cikti", default=str(BURASI), help="Çıktı klasörü (varsayılan: bu klasör)")
    a = ap.parse_args()
    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)

    for ad in ("arka", "pitir_banner", "pitir_yuz", "gunes", "ornek_kare"):
        if not K[ad].exists():
            sys.exit(f"HATA: kaynak resim yok: {K[ad]}")
    eksik = eksik_harfler(a.kanal + a.program)
    if eksik:
        print("UYARI: şu harfler yazı tipinde yok, bozuk çıkabilir:", " ".join(eksik))
    print("Yazı tipi:", ", ".join(Path(y).name for y in YOLLAR))

    # Kapak: 6 MB sınırını aşarsa zemini biraz daha yumuşatıp yeniden dener.
    for bulanik in (2.2, 3.5, 5.0, 7.0):
        ban, alan, kutular, tasan, boy = banner_ciz(a.kanal, a.program, bulanik)
        yol = cikti / "banner_2560x1440.png"
        ban.save(yol, optimize=True)
        mb = yol.stat().st_size / 1e6
        if mb < 5.8:
            break
    print(f"banner_2560x1440.png  {ban.size[0]}x{ban.size[1]}  {mb:.2f} MB  (zemin yumuşatma {bulanik}, başlık harf boyu {boy})")
    print(f"  güvenli alan: x {alan[0]}-{alan[2]}, y {alan[1]}-{alan[3]}")
    for ad, k in kutular.items():
        print(f"  {ad:12s}: x {k[0]}-{k[2]}, y {k[1]}-{k[3]}")
    print("  GÜVENLİ ALAN:", "TAMAM, hepsi içinde" if not tasan else "DİKKAT, dışarı taşan var: " + ", ".join(tasan))
    if mb >= 6:
        print("  DİKKAT: dosya 6 MB'tan büyük!")

    prof = profil_ciz()
    prof.save(cikti / "profil_800x800.png", optimize=True)
    print(f"profil_800x800.png    {prof.size[0]}x{prof.size[1]}  {(cikti / 'profil_800x800.png').stat().st_size / 1e6:.2f} MB")
    fil = filigran_ciz()
    fil.save(cikti / "filigran_150x150.png", optimize=True)
    print(f"filigran_150x150.png  {fil.size[0]}x{fil.size[1]}  {(cikti / 'filigran_150x150.png').stat().st_size / 1e3:.0f} KB  (şeffaf zemin)")

    kontroller(cikti, ban, alan, prof, fil)
    print("Kontrol resimleri: kontrol_*.png")


if __name__ == "__main__":
    main()
