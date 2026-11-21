#!/usr/bin/env python3
"""YouTube arama sonucu sayfalarindan (ham-html/*.html) ilk sayfa videolarini ayiklar.
Kullanim: python3 -I ayikla.py <ham-html klasoru> <cikti.csv>
Yalnizca standart kutuphane kullanir; ag istegi yapmaz.
"""
import csv
import glob
import json
import os
import re
import sys

SORGULAR = {
    "q1_cocuk_sarkilari": "çocuk şarkıları",
    "q2_bebek_sarkilari": "bebek şarkıları",
    "q3_ali_babanin_ciftligi": "ali babanın çiftliği",
    "q4_parmak_ailesi_sarkisi": "parmak ailesi şarkısı",
    "q5_otobus_sarkisi": "otobüs şarkısı",
    "q6_el_yikama_sarkisi": "el yıkama şarkısı",
    "q7_bes_kucuk_maymun": "beş küçük maymun",
    "q8_renkler_sarkisi": "renkler şarkısı",
    "q9_aile_sarkisi_cocuk": "aile şarkısı çocuk",
}


def metin(d):
    if not d:
        return ""
    if isinstance(d, str):
        return d
    if "simpleText" in d:
        return d["simpleText"]
    if "runs" in d:
        return "".join(r.get("text", "") for r in d["runs"])
    if "content" in d and isinstance(d["content"], str):
        return d["content"]
    return ""


def goruntuleme_sayi(t):
    """'1.234.567 görüntüleme' / '1,2 Mn görüntüleme' / '345 B' / '2,1 Mr' -> int"""
    if not t:
        return ""
    s = t.lower().replace("\xa0", " ")
    if "görüntüleme yok" in s:
        return 0
    m = re.search(r"([\d.,]+)\s*(mr|mn|b)?\b", s)
    if not m:
        return ""
    sayi, ek = m.group(1), m.group(2)
    if ek:
        v = float(sayi.replace(".", "").replace(",", "."))
        v *= {"b": 1e3, "mn": 1e6, "mr": 1e9}[ek]
        return int(v)
    return int(sayi.replace(".", "").replace(",", "") or 0)


def sure_saniye(t):
    if not t or not re.match(r"^\d+(:\d+)+$", t.strip()):
        return ""
    p = [int(x) for x in t.strip().split(":")]
    s = 0
    for x in p:
        s = s * 60 + x
    return s


BIRIM_AY = {"yıl": 12.0, "ay": 1.0, "hafta": 0.23, "gün": 1 / 30.4, "saat": 1 / 730.0, "dakika": 0.0}


def yas_ay(t):
    if not t:
        return ""
    m = re.search(r"(\d+)\s*(yıl|ay|hafta|gün|saat|dakika)", t.lower())
    if not m:
        return ""
    return round(int(m.group(1)) * BIRIM_AY[m.group(2)], 2)


def video_satiri(v, raf):
    owner = v.get("ownerText") or v.get("longBylineText") or v.get("shortBylineText") or {}
    kanal = metin(owner)
    kanal_id, kanal_url = "", ""
    try:
        be = owner["runs"][0]["navigationEndpoint"]["browseEndpoint"]
        kanal_id = be.get("browseId", "")
        kanal_url = be.get("canonicalBaseUrl", "")
    except Exception:
        pass
    gm = metin(v.get("viewCountText"))
    sm = metin(v.get("lengthText"))
    ym = metin(v.get("publishedTimeText"))
    rozet = ",".join(
        b.get("metadataBadgeRenderer", {}).get("label", "") or b.get("metadataBadgeRenderer", {}).get("tooltip", "")
        for b in (v.get("badges") or [])
    )
    dogr = ",".join(
        b.get("metadataBadgeRenderer", {}).get("tooltip", "") for b in (v.get("ownerBadges") or [])
    )
    return {
        "tur": "video",
        "baslik": metin(v.get("title")),
        "kanal": kanal,
        "kanal_id": kanal_id,
        "kanal_url": kanal_url,
        "goruntuleme_metni": gm,
        "goruntuleme_sayi": goruntuleme_sayi(gm),
        "sure_metni": sm,
        "sure_saniye": sure_saniye(sm),
        "yas_metni": ym,
        "yas_ay": yas_ay(ym),
        "video_id": v.get("videoId", ""),
        "raf": raf,
        "rozet": rozet,
        "kanal_rozeti": dogr,
    }


def bos(tur, baslik, raf, **kw):
    r = {k: "" for k in ALANLAR}
    r.update({"tur": tur, "baslik": baslik, "raf": raf})
    r.update(kw)
    return r


ALANLAR = [
    "sorgu", "sira", "tur", "baslik", "kanal", "kanal_id", "kanal_url", "goruntuleme_metni",
    "goruntuleme_sayi", "sure_metni", "sure_saniye", "yas_metni", "yas_ay", "video_id", "raf",
    "rozet", "kanal_rozeti",
]


def yuru(n, raf, out, sayac):
    """Belge sirasini koruyarak dolasir."""
    if isinstance(n, list):
        for x in n:
            yuru(x, raf, out, sayac)
        return
    if not isinstance(n, dict):
        return
    for k, v in n.items():
        if k == "videoRenderer":
            out.append(video_satiri(v, raf))
        elif k == "channelRenderer":
            out.append(bos("kanal", metin(v.get("title")), raf, kanal=metin(v.get("title")),
                           kanal_id=v.get("channelId", ""),
                           goruntuleme_metni=metin(v.get("videoCountText")) + " | " + metin(v.get("subscriberCountText"))))
        elif k in ("reelItemRenderer",):
            out.append(bos("short", metin(v.get("headline")), raf, video_id=v.get("videoId", ""),
                           goruntuleme_metni=metin(v.get("viewCountText")),
                           goruntuleme_sayi=goruntuleme_sayi(metin(v.get("viewCountText")))))
        elif k == "shortsLockupViewModel":
            t = (v.get("overlayMetadata") or {}).get("primaryText", {}).get("content", "")
            g = (v.get("overlayMetadata") or {}).get("secondaryText", {}).get("content", "")
            vid = ""
            try:
                vid = v["onTap"]["innertubeCommand"]["reelWatchEndpoint"]["videoId"]
            except Exception:
                pass
            out.append(bos("short", t, raf, video_id=vid, goruntuleme_metni=g, goruntuleme_sayi=goruntuleme_sayi(g)))
        elif k in ("playlistRenderer", "radioRenderer"):
            out.append(bos("oynatma_listesi", metin(v.get("title")), raf, kanal=metin(v.get("longBylineText") or v.get("shortBylineText")),
                           sure_metni=metin(v.get("videoCountText") or v.get("videoCountShortText"))))
        elif k == "lockupViewModel":
            t = ""
            try:
                t = v["metadata"]["lockupMetadataViewModel"]["title"]["content"]
            except Exception:
                pass
            out.append(bos("oynatma_listesi", t, raf, video_id=v.get("contentId", ""),
                           rozet=v.get("contentType", "")))
        elif k in ("shelfRenderer", "reelShelfRenderer", "richShelfRenderer", "horizontalCardListRenderer"):
            alt = metin(v.get("title")) or (metin((v.get("header") or {}).get("richListHeaderRenderer", {}).get("title")))
            yuru(v, alt or k, out, sayac)
        elif k == "gridShelfViewModel":
            alt = ""
            try:
                alt = v["header"]["sectionHeaderViewModel"]["headline"]["content"]
            except Exception:
                pass
            yuru(v, alt or "Shorts", out, sayac)
        elif k in ("adSlotRenderer", "searchPyvRenderer", "promotedSparklesWebRenderer", "promotedVideoRenderer"):
            sayac["reklam"] = sayac.get("reklam", 0) + 1
        elif k in ("secondaryContents", "header", "topbar", "frameworkUpdates", "responseContext"):
            continue
        else:
            yuru(v, raf, out, sayac)


def main():
    kaynak, cikti = sys.argv[1], sys.argv[2]
    tum = []
    for yol in sorted(glob.glob(os.path.join(kaynak, "*.html"))):
        ad = os.path.splitext(os.path.basename(yol))[0]
        sorgu = SORGULAR.get(ad, ad)
        html = open(yol, encoding="utf-8", errors="replace").read()
        m = re.search(r"var ytInitialData\s*=\s*(\{.*?\});\s*</script>", html, re.S)
        if not m:
            print("ytInitialData yok:", ad, file=sys.stderr)
            continue
        veri = json.loads(m.group(1))
        try:
            kok = veri["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]
        except KeyError:
            kok = veri.get("contents", veri)
        out, sayac = [], {}
        yuru(kok, "", out, sayac)
        tahmini = veri.get("estimatedResults", "")
        for i, r in enumerate(out, 1):
            r["sorgu"] = sorgu
            r["sira"] = i
            tum.append(r)
        nv = sum(1 for r in out if r["tur"] == "video")
        print(f"{sorgu}: {len(out)} oge ({nv} video), reklam={sayac.get('reklam', 0)}, tahmini_sonuc={tahmini}")
    with open(cikti, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR)
        w.writeheader()
        for r in tum:
            w.writerow({k: r.get(k, "") for k in ALANLAR})
    print("yazildi:", cikti, len(tum), "satir")


if __name__ == "__main__":
    main()
