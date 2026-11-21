#!/usr/bin/env python3
"""Ortak yardimcilar: dosya yollari, soz yapisi (7 kita x 4 dize), Turkce heceleme, kelime eslestirme."""
import os, json, numpy as np

K = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # .../yeni3/analiz/kesim
A = os.path.dirname(os.path.dirname(os.path.dirname(K)))                 # .../ali-baba
VOKAL = os.path.join(A, "dinle_2_vokal.wav")
KELIME = os.path.join(A, "dinle_2_words.json")
OZELLIK = os.path.join(K, "ara", "ozellik.npz")

HAYVAN = ["inek", "koyun", "at", "horoz", "ördek", "köpek", "kedi"]
L1 = "Ali Baba'nın bir çiftliği var"
L4 = "Dinle bak dinle bak"
# L2: 6. kitada sarkici "köpekleri" yerine "ördekleri" demis -> SOYLENEN hali yazilir
L2 = ["Çiftliğinde inekleri var", "Çiftliğinde koyunları var", "Çiftliğinde bir de atı var",
      "Çiftliğinde horozları var", "Çiftliğinde ördekleri var", "Çiftliğinde ördekleri var",
      "Çiftliğinde bir kedisi var"]
L2_OLMASI_GEREKEN = list(L2); L2_OLMASI_GEREKEN[5] = "Çiftliğinde köpekleri var"
L3 = ["İnekler nasıl bağırır", "Koyunlar nasıl meler", "Atı nasıl kişner", "Horozlar nasıl öter",
      "Ördekler nasıl bağırır", "Köpekler nasıl havlar", "Kedisi nasıl miyavlar"]

UNLU = set("aeıioöuü")


def kucuk(s):
    """Turkce kucuk harf + noktalama temizligi."""
    s = s.replace("İ", "i").replace("I", "ı").lower()
    return "".join(ch for ch in s if ch.isalpha())


def hecele(kelime):
    """Turkce heceleme: her hecede tam bir unlu. Unluden onceki TEK unsuz sonraki heceye gider.
    Donus: yazildigi gibi (buyuk harf / kesme isareti korunur) hece listesi."""
    harf = [ch for ch in kelime if ch.isalpha()]
    kk = [kucuk(ch) for ch in harf]
    vi = [i for i, ch in enumerate(kk) if ch in UNLU]
    if not vi:
        return ["".join(harf)]
    sinir = [0]
    for a, b in zip(vi[:-1], vi[1:]):
        # a ve b unluleri arasindaki unsuzler: sonuncusu sonraki heceye; arada unsuz yoksa b'den bolunur
        sinir.append(b - 1 if b - a > 1 else b)
    sinir.append(len(harf))
    return ["".join(harf[s:e]) for s, e in zip(sinir[:-1], sinir[1:])]


BEKLENEN_HECE = {
    "L1": "A-li Ba-ba-nın bir çift-li-ği var",
    "L2": ["Çift-li-ğin-de i-nek-le-ri var", "Çift-li-ğin-de ko-yun-la-rı var", "Çift-li-ğin-de bir de a-tı var",
           "Çift-li-ğin-de ho-roz-la-rı var", "Çift-li-ğin-de ör-dek-le-ri var", "Çift-li-ğin-de ör-dek-le-ri var",
           "Çift-li-ğin-de bir ke-di-si var"],
    "L3": ["İ-nek-ler na-sıl ba-ğı-rır", "Ko-yun-lar na-sıl me-ler", "A-tı na-sıl kiş-ner", "Ho-roz-lar na-sıl ö-ter",
           "Ör-dek-ler na-sıl ba-ğı-rır", "Kö-pek-ler na-sıl hav-lar", "Ke-di-si na-sıl mi-yav-lar"],
    "L4": "Din-le bak din-le bak",
}


def dize_sozleri(v):
    return [L1, L2[v], L3[v], L4]


def beklenen_hece(v, d):
    b = BEKLENEN_HECE["L%d" % (d + 1)]
    return (b if isinstance(b, str) else b[v]).split()


def kelimeleri_oku():
    w = json.load(open(KELIME, encoding="utf8"))
    w = w["words"] if isinstance(w, dict) else w
    return [q for q in w if q.get("type", "word") == "word"]


def kitalari_esle(w):
    """Kelime listesini 7 kita x 4 dize yapisina oturtur; metin uyusmazsa hata verir.
    Donus: kita[v][d] = [kelime sozlukleri] (her birine 'hece' listesi eklenir)."""
    bas = [i for i in range(len(w) - 1) if kucuk(w[i]["text"]) == "ali" and kucuk(w[i + 1]["text"]).startswith("baba")]
    assert len(bas) == 7, bas
    kita = []
    for v, b in enumerate(bas):
        i = b; dizeler = []
        for d, soz in enumerate(dize_sozleri(v)):
            bh = beklenen_hece(v, d)
            kl = []
            for j, kel in enumerate(soz.split()):
                q = dict(w[i]); i += 1
                assert kucuk(q["text"]) == kucuk(kel), (v + 1, d + 1, q["text"], kel)
                h = hecele(kel)
                assert "-".join(kucuk(x) for x in h) == "-".join(kucuk(x) for x in bh[j].split("-")), (kel, h, bh[j])
                q["soz"] = kel; q["hece"] = h; q["json_bas"] = q["start"]; q["json_bit"] = q["end"]
                kl.append(q)
            dizeler.append(kl)
        kita.append(dizeler)
    return kita


def ozellik():
    return np.load(OZELLIK)


if __name__ == "__main__":
    for kel in "Ali Baba'nın bir çiftliği var Çiftliğinde inekleri koyunları atı horozları ördekleri kedisi İnekler nasıl bağırır meler kişner öter havlar miyavlar Köpekler Dinle bak de".split():
        print(kel, hecele(kel))
    k = kitalari_esle(kelimeleri_oku())
    print(sum(len(x["hece"]) for v in k for d in v for x in d), "hece;", sum(len(d) for v in k for d in v), "kelime")
