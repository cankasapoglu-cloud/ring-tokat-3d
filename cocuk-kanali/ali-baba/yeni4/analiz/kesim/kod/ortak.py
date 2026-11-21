#!/usr/bin/env python3
"""Ortak yardimcilar (v2_2 icin): dosya yollari, soz yapisi (7 kita x 5 bolum), Turkce heceleme, kelime eslestirme.
yeni3/analiz/kesim/kod/ortak.py'den uyarlandi.
Bolumler (kita basina):  L1 | L2 | ses (soylenen hayvan sesi: ATILACAK) | diye ("diye bağırır") | L4
Saklanacak parcalar:     parca 1 = L1, parca 2 = L2, parca 3 = diye + L4 (kesintisiz)."""
import os, json, numpy as np

K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # .../yeni4/analiz/kesim
A = os.path.dirname(os.path.dirname(os.path.dirname(K)))                 # .../ali-baba
VOKAL = os.path.join(A, "yeni4", "vokal", "kaynak", "v2_2_vokal.wav")
KELIME = os.path.join(A, "v2_2_words.json")
TEMPO = os.path.join(A, "yeni4", "analiz", "tempo", "tempo.json")
OZELLIK = os.path.join(K, "ara", "ozellik.npz")

HAYVAN = ["inek", "koyun", "at", "horoz", "ördek", "köpek", "kedi"]
HAYVAN_KELIME = ["inekleri", "koyunları", "atları", "horozları", "ördekleri", "köpekleri", "kedisi"]
BOLUM = ["L1", "L2", "ses", "diye", "L4"]
SAKLANAN = ["L1", "L2", "diye", "L4"]
L1 = "Ali Baba'nın bir çiftliği var"
L2 = ["çiftliğinde %s var" % h for h in HAYVAN_KELIME]
DIYE = "diye bağırır"
L4 = "çiftliğinde Ali Baba'nın"
SES_KELIME_SAYISI = 2                      # her kitada iki soylenen hayvan sesi kelimesi (Mö mö, Me me, ...)

# Hizalamada kullanilan, SOYLENDIGI gibi yazim (kita no 0..6 -> hayvan kelimesi). atlari.py'nin olcumune gore
# 3. kitada sarkici "atları" yerine dort heceli "a-tı-la-rı" soylemistir (bkz. kesim.json: atlari_check).
SOYLENEN = {2: "atıları"}

UNLU = set("aeıioöuü")
BEAT = 60.0 / 105.0
BAR = 4 * BEAT


def kucuk(s):
    """Turkce kucuk harf + noktalama temizligi."""
    s = s.replace("İ", "i").replace("I", "ı").lower()
    return "".join(ch for ch in s if ch.isalpha())


def hecele(kelime):
    """Turkce heceleme: her hecede tam bir unlu. Unluden onceki TEK unsuz sonraki heceye gider."""
    harf = [ch for ch in kelime if ch.isalpha()]
    kk = [kucuk(ch) for ch in harf]
    vi = [i for i, ch in enumerate(kk) if ch in UNLU]
    if not vi:
        return ["".join(harf)]
    sinir = [0]
    for a, b in zip(vi[:-1], vi[1:]):
        sinir.append(b - 1 if b - a > 1 else b)
    sinir.append(len(harf))
    return ["".join(harf[s:e]) for s, e in zip(sinir[:-1], sinir[1:])]


BEKLENEN_HECE = {
    "L1": "A-li Ba-ba-nın bir çift-li-ği var",
    "L2": ["çift-li-ğin-de i-nek-le-ri var", "çift-li-ğin-de ko-yun-la-rı var", "çift-li-ğin-de at-la-rı var",
           "çift-li-ğin-de ho-roz-la-rı var", "çift-li-ğin-de ör-dek-le-ri var", "çift-li-ğin-de kö-pek-le-ri var",
           "çift-li-ğin-de ke-di-si var"],
    "diye": "di-ye ba-ğı-rır",
    "L4": "çift-li-ğin-de A-li Ba-ba-nın",
}


def bolum_sozu(v, ad):
    return {"L1": L1, "L2": L2[v], "diye": DIYE, "L4": L4}[ad]


def beklenen_hece(v, ad):
    b = BEKLENEN_HECE[ad]
    return (b if isinstance(b, str) else b[v]).split()


def kelimeleri_oku():
    w = json.load(open(KELIME, encoding="utf8"))
    w = w["words"] if isinstance(w, dict) else w
    return [q for q in w if q.get("type", "word") == "word"]


def tempo_oku():
    return json.load(open(TEMPO, encoding="utf8"))


def kitalari_esle(w):
    """Kelime listesini 7 kita x 5 bolum yapisina oturtur; metin uyusmazsa hata verir.
    Donus: kita[v][ad] = [kelime sozlukleri] (saklanan bolumlerde 'hece' listesi eklenir; 'ses' icin metin yazildigi gibi)."""
    bas = [i for i in range(len(w) - 1) if kucuk(w[i]["text"]) == "ali" and kucuk(w[i + 1]["text"]).startswith("baba")
           and (i == 0 or kucuk(w[i - 1]["text"]) != "çiftliğinde")]
    assert len(bas) == 7, bas
    kita = []
    for v, b in enumerate(bas):
        i = b; bolumler = {}
        for ad in BOLUM:
            kl = []
            if ad == "ses":
                for _ in range(SES_KELIME_SAYISI):
                    q = dict(w[i]); i += 1
                    q["soz"] = q["text"]; q["json_bas"] = q["start"]; q["json_bit"] = q["end"]
                    kl.append(q)
            else:
                bh = beklenen_hece(v, ad)
                for j, kel in enumerate(bolum_sozu(v, ad).split()):
                    q = dict(w[i]); i += 1
                    assert kucuk(q["text"]) == kucuk(kel), (v + 1, ad, q["text"], kel)
                    h = hecele(kel)
                    assert "-".join(kucuk(x) for x in h) == "-".join(kucuk(x) for x in bh[j].split("-")), (kel, h, bh[j])
                    q["soz"] = kel; q["hece"] = h; q["json_bas"] = q["start"]; q["json_bit"] = q["end"]
                    kl.append(q)
            bolumler[ad] = kl
        if v < 6:
            assert i == bas[v + 1], (v + 1, i, bas[v + 1])
        else:
            assert i == len(w), (i, len(w))
        kita.append(bolumler)
    return kita


def kita_vuruslari():
    """7 kitanin ilk vurus (downbeat) zamani - tempo.json'dan (mp3 zaman ekseni = ayrilmis vokalin ekseni, gecikme 0)."""
    return list(tempo_oku()["summary"]["verse_downbeats"])


def ozellik():
    return np.load(OZELLIK)


if __name__ == "__main__":
    for kel in (L1 + " " + " ".join(HAYVAN_KELIME) + " " + DIYE + " " + L4 + " çiftliğinde").split():
        print(kel, hecele(kel))
    k = kitalari_esle(kelimeleri_oku())
    print(sum(len(x["hece"]) for v in k for ad in SAKLANAN for x in v[ad]), "hece;",
          sum(len(v[ad]) for v in k for ad in SAKLANAN), "saklanan kelime;", sum(len(v["ses"]) for v in k), "ses kelimesi")
    print(kita_vuruslari())
