#!/usr/bin/env python3
"""sinama.py - dinleme araclarinin birim sinamalari (ag gerektirmez, kredi harcamaz).

    python3 sinama.py            # hepsi
    python3 sinama.py -k gemini  # yalnizca Gemini istek/cevap sinamalari

Kapsam: Gemini istek govdesi kurma ve cevap cozme (canli anahtar olmadan), soz hizalama ve sozcuk hata orani,
nota bolme / ton / ritim / kirpilma olcumlerinin cevabi bilinen yapay isaretlerdeki sonucu.
"""
import os, sys, json, glob, math, tempfile, unittest, warnings

warnings.filterwarnings("ignore")
BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
import numpy as np


class GeminiSinama(unittest.TestCase):
    def setUp(self):
        import gemini_dinle as g
        self.g = g

    def test_openai_istek_govdesi(self):
        b = self.g.istek_govdesi(["QUJD", "REVG"], "soru?", "gemini-x")
        self.assertEqual(b["model"], "gemini-x")
        ic = b["messages"][0]["content"]
        self.assertEqual(ic[0], {"type": "text", "text": "soru?"})
        self.assertEqual([p["type"] for p in ic[1:]], ["input_audio", "input_audio"])
        self.assertEqual(ic[2]["input_audio"], {"data": "REVG", "format": "mp3"})
        json.dumps(b)                                               # JSON'a cevrilebilir olmali

    def test_yerel_istek_govdesi_soru_sonda(self):
        b = self.g.yerel_istek_govdesi(["QQ==", "Qg=="], "hangisi?", ["Kayıt A:", "Kayıt B:"])
        p = b["contents"][0]["parts"]
        self.assertEqual([list(x)[0] for x in p], ["text", "inline_data", "text", "inline_data", "text"])
        self.assertEqual(p[1]["inline_data"], {"mime_type": "audio/mpeg", "data": "QQ=="})
        self.assertEqual(p[-1]["text"], "hangisi?")                 # soru sesten SONRA

    def test_openai_yanit_basarili(self):
        t = json.dumps({"choices": [{"message": {"role": "assistant", "content": "SES: doğal"}}]})
        self.assertEqual(self.g.yaniti_coz(t), (True, "SES: doğal", 200))

    def test_openai_yanit_hatalar(self):
        ok, msg, kod = self.g.yaniti_coz(json.dumps([{"error": {"code": 429, "message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}}]))
        self.assertFalse(ok)
        self.assertEqual(kod, 429)
        self.assertIn("Kota", self.g.hata_aciklamasi(kod, msg))
        ok, msg, kod = self.g.yaniti_coz('{"error": {"code": 400, "message": "Invalid Auth key.", "status": "INVALID_ARGUMENT"}}')
        self.assertFalse(ok)
        self.assertIn("anahtar", self.g.hata_aciklamasi(kod, msg).lower())
        ok, msg, kod = self.g.yaniti_coz("<html>502</html>")
        self.assertFalse(ok)
        self.assertEqual(kod, 0)
        ok, msg, kod = self.g.yaniti_coz('{"choices": []}')
        self.assertFalse(ok)

    def test_yerel_yanit(self):
        t = json.dumps({"candidates": [{"content": {"parts": [{"text": "dusunce", "thought": True}, {"text": "SES: biraz yapay | 0:12"}]}, "finishReason": "STOP"}]})
        self.assertEqual(self.g.yerel_yaniti_coz(t), (True, "SES: biraz yapay | 0:12", 200))
        ok, msg, kod = self.g.yerel_yaniti_coz(json.dumps({"error": {"code": 401, "message": "API key not valid", "status": "UNAUTHENTICATED"}}))
        self.assertEqual((ok, kod), (False, 401))
        self.assertIn("x-goog-api-key", self.g.hata_aciklamasi(kod, msg))
        ok, msg, kod = self.g.yerel_yaniti_coz(json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}))
        self.assertFalse(ok)
        self.assertIn("SAFETY", msg)

    def test_rubrik_coz(self):
        y = ("DUYDUGUM: Türkçe, kadın sesi, davul ve bas.\nSOZLER: Ali Baba'nın bir çiftliği var\n**SES**: Biraz yapay | sesli harfler düz, 00:12\n"
             "AKORT: müzikle uyumlu | sorun duymadım\nRITIM: ara sıra kaçıyor | 00:20\nENERJI: canlı\nTELAFFUZ: hafif yabancı aksan | 'çiftliği' 00:07\n"
             "SARKI_MI: ezgiyle söylüyor\nDENGE: dengeli\nTUHAF: 00:18 - inek sesi bozuk; 00:40 - söz kesiliyor\nOZET: Ses yapay.")
        r = self.g.rubrik_coz(y)
        self.assertEqual(r["_eksik"], [])
        self.assertEqual(r["SES"], {"secim": "biraz yapay", "gerekce": "sesli harfler düz, 00:12"})
        self.assertEqual(r["ENERJI"]["secim"], "canlı")
        self.assertEqual(r["TELAFFUZ"]["secim"], "hafif yabancı aksan")
        self.assertIn("inek sesi", r["TUHAF"]["metin"])
        self.assertEqual(self.g.rubrik_coz("alakasiz metin")["_eksik"], self.g.RUBRIK_ANAHTARLARI)

    def test_ab_coz_gercek_onbellek_cevabi(self):
        y = ("1. **B** – B'deki vokal doğal.\n2. **A**: A'da vokal akortlu.\n3. A - ritim\n4. **Fark yok** – ikisi de\n5. B\n6. **A**: daha iyi; kusur 0:37")
        self.assertEqual(self.g.ab_coz(y), {1: "B", 2: "A", 3: "A", 4: "fark yok", 5: "B", 6: "A"})
        self.assertEqual(self.g.ab_coz("bos")[1], None)

    def test_iki_yon_birlestir(self):
        ilk = {1: "A", 2: "A", 3: "B", 4: "fark yok", 5: None, 6: "A"}           # (X, Y) sirasi
        ters = {1: "B", 2: "A", 3: "A", 4: "fark yok", 5: "A", 6: "B"}          # (Y, X) sirasi
        b = self.g.iki_yon_birlestir(ilk, ters)
        self.assertEqual(b[1], "X")                    # iki sorguda da X kazandi
        self.assertEqual(b[2], "TUTARSIZ")             # hep "A" dedi: konum yanliligi
        self.assertEqual(b[3], "Y")
        self.assertEqual(b[4], "fark yok")
        self.assertEqual(b[5], None)
        self.assertEqual(b[6], "X")

    def test_rubrik_metni_sabit_sorulari_icerir(self):
        for k in self.g.RUBRIK_ANAHTARLARI:
            self.assertIn(k + ":", self.g.RUBRIK)
        for s in ("emin değilim", "yabancı aksan", "ninni gibi", "MM:SS"):
            self.assertIn(s, self.g.RUBRIK)

    def test_onbellek_anahtari_eski_cevaplarla_uyumlu(self):
        """Ana oturumun 14:49'da aldigi A/B cevabi ayni anahtarla bulunmali (ag istegi YAPMAZ)."""
        kok = os.path.dirname(os.path.dirname(BURASI))
        a, b = os.path.join(kok, "ali-baba", "yeni", "vokal", "ornek_kita1.mp3"), os.path.join(kok, "ali-baba", "dinle_2.mp3")
        if not (os.path.exists(a) and os.path.exists(b) and glob.glob(os.path.join(self.g.ONBELLEK, "*.json"))):
            self.skipTest("ornek dosyalar ya da onbellek yok")
        import hashlib
        sesler = [self.g._kucult(a, None, 27.0), self.g._kucult(b, None, 27.0)]
        anahtar = hashlib.sha1(("|".join(hashlib.sha1(s.encode()).hexdigest() for s in sesler) + self.g.KARSILASTIRMA).encode()).hexdigest()
        self.assertTrue(os.path.exists(os.path.join(self.g.ONBELLEK, anahtar + ".json")), "onbellek anahtari degismis: " + anahtar)


class SozlerSinama(unittest.TestCase):
    def setUp(self):
        import dinle_sozler as z
        self.z = z

    def test_normalle_ve_hece(self):
        self.assertEqual(self.z.normalle("Baba'nın,"), "babanın")
        self.assertEqual(self.z.normalle("IŞIK İÇİN"), "ışıkiçin")
        self.assertEqual(self.z.normalle("kâğıt"), "kağıt")
        self.assertEqual(self.z.hece_say("Çiftliğinde"), 4)
        self.assertEqual(self.z.hece_say("Ali Baba'nın"), 5)

    def test_beklenen_sozcukler_yok_sayilanlar(self):
        m = "# baslik\n1. KITA — inek (7 sn)\nAli Baba'nın çiftliği\n   (müzik cevabı)\n[inek sesi] var\nNAKARAT\n"
        self.assertEqual([b[1] for b in self.z.beklenen_sozcukler(m)], ["ali", "babanın", "çiftliği", "var"])

    def test_hizalama(self):
        h = self.z.hizala("a b c d".split(), "a x c".split())
        self.assertEqual([t for t, _, _ in h], ["ayni", "degisik", "ayni", "eksik"])
        h = self.z.hizala("a b".split(), "a b a b".split())            # tekrar: ILK soylenis eslesir, sonraki fazla
        self.assertEqual(h, [("ayni", 0, 0), ("ayni", 1, 1), ("fazla", None, 2), ("fazla", None, 3)])

    def test_sozcuk_hata_orani(self):
        bek = self.z.beklenen_sozcukler("Çiftliğinde köpekleri var\nKöpekler nasıl havlar")
        soz = [{"metin": w, "normal": self.z.normalle(w), "bas": i * 0.5, "son": i * 0.5 + 0.4, "logprob": -0.1}
               for i, w in enumerate("Çiftliğinde ördekleri var. Köpekler nasıl havlar? hey".split())]
        k = self.z.karsilastir(bek, soz)
        self.assertEqual((k["degisik"], k["eksik"], k["fazla"]), (1, 0, 1))
        self.assertAlmostEqual(k["sozcuk_hata_orani"], 2 / 6, places=3)
        self.assertEqual(k["yanlis_sozcukler"][0]["beklenen"], "köpekleri")
        self.assertEqual(k["yanlis_sozcukler"][0]["duyulan"], "ördekleri")
        self.assertEqual(k["yanlis_sozcukler"][0]["zaman"], 0.5)
        self.assertEqual(k["fazla_sozcukler"][0]["duyulan"], "hey")

    def test_hece_hizi(self):
        soz = [{"metin": "Ali", "bas": 0.0, "son": 0.5}, {"metin": "Baba", "bas": 0.5, "son": 1.0}, {"metin": "var", "bas": 3.0, "son": 3.5},
               {"metin": "çiftliği", "bas": 3.5, "son": 4.0}]
        h = self.z.hece_hizi(soz)
        self.assertEqual(h["toplam_hece"], 8)
        self.assertEqual(h["obek_sayisi"], 2)
        self.assertAlmostEqual(h["obekler"][0]["hece_sn"], 4.0)

    def test_scribe_cevabi_ayristirma(self):
        s = {"words": [{"text": "[koyun sesi]", "start": 1, "end": 2, "type": "audio_event"}, {"text": " ", "start": 2, "end": 2.1, "type": "spacing"},
                       {"text": "Ali", "start": 2.1, "end": 2.4, "type": "word", "logprob": -0.9}]}
        soz, olay = self.z.duyulanlar(s)
        self.assertEqual([w["metin"] for w in soz], ["Ali"])
        self.assertEqual([w["metin"] for w in olay], ["[koyun sesi]"])
        self.assertEqual(self.z.dusuk_guvenli(soz)[0]["sozcuk"], "Ali")

    def test_kredi_siniri_cagriyi_engeller(self):
        z = self.z
        with tempfile.TemporaryDirectory() as d:
            eski = (z.ONBELLEK, z.DEFTER, z.KREDI_SINIRI)
            try:
                z.ONBELLEK, z.DEFTER, z.KREDI_SINIRI = d, os.path.join(d, "defter.json"), 100
                json.dump({"kayitlar": [{"tahmini_kredi": 90}]}, open(z.DEFTER, "w"))
                f = os.path.join(d, "x.mp3")
                open(f, "wb").write(b"0123")
                sonuc, durum = z.scribe(f, 60.0, gunluk=lambda *a: None)          # 60 sn = 330 kredi > kalan 10 -> cagri YAPILMAZ
                self.assertIsNone(sonuc)
                self.assertEqual(durum["kaynak"], "reddedildi")
            finally:
                z.ONBELLEK, z.DEFTER, z.KREDI_SINIRI = eski


class OlcumSinama(unittest.TestCase):
    def setUp(self):
        import dinle_olcum as o
        self.o = o

    def test_nota_bolme_ve_cent(self):
        dt = 0.016
        t = np.arange(0, 3.0, dt)
        midi = np.where(t < 1.0, 60.0, np.where(t < 2.0, 62.3, 64.0)) + 0.02 * np.sin(2 * np.pi * 5.5 * t) * (t >= 2.0)
        sesli = np.ones(len(t), bool)
        sesli[(t > 0.95) & (t < 1.0)] = False
        nt = self.o.notalara_bol(t, midi, sesli)
        self.assertEqual([n["ad"] for n in nt], ["C4", "D4", "E4"])
        self.assertAlmostEqual(nt[1]["cent"], 30.0, delta=1.0)
        self.assertLess(nt[0]["ic_std_cent"], 1.0)
        self.assertTrue(nt[2]["vibrato"] is not None)

    def test_ton_bulma(self):
        pch = np.zeros(12)
        pch[[7, 9, 11, 0, 2, 4, 6]] = [5, 2, 3, 2.5, 4, 2, 1]            # Sol major agirlikli
        k = self.o.ks_ton(pch)
        self.assertEqual((k[0], k[1]), (7, "major"))
        self.assertEqual(self.o.gam(9, "minor"), {9, 11, 0, 2, 4, 5, 7})

    def test_ritim_sikilik(self):
        vurus = np.arange(0, 40, 0.5)
        rng = np.random.default_rng(3)
        tam = vurus[4:60] + 0.25 * rng.integers(0, 2, 56) + rng.normal(0, 0.008, 56)
        c, _ = self.o.ritim(tam, vurus, 120)
        self.assertGreater(c["sekizlik"]["sikilik_R"], 0.9)
        self.assertLess(abs(c["sekizlik"]["ortalama_kayma_ms"]), 10)
        c, _ = self.o.ritim(tam + 0.06, vurus, 120)                       # 60 ms gec
        self.assertAlmostEqual(c["sekizlik"]["ortalama_kayma_ms"], 60, delta=8)
        c, _ = self.o.ritim(rng.uniform(2, 30, 60), vurus, 120)            # rastgele
        self.assertLess(c["sekizlik"]["sikilik_R"], 0.3)

    def test_temel_kirpilma_ve_sessizlik(self):
        import soundfile as sf
        sr = 44100
        t = np.arange(int(sr * 4)) / sr
        x = 1.6 * np.sin(2 * np.pi * 220 * t)
        x[:sr] = 0.0                                                      # 1 sn bas sessizligi
        x = np.clip(x, -1, 1).astype(np.float32)
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "kirpik.wav")
            sf.write(f, np.stack([x, x], axis=1), sr, subtype="PCM_16")
            xx, s2 = self.o.ses_coz(f)
            c = self.o.temel(f, xx, s2)
        self.assertTrue(c["kirpilma"]["var_mi"])
        self.assertAlmostEqual(c["sessizlik"]["bastaki_sn"], 1.0, delta=0.08)
        self.assertGreater(c["stereo"]["sol_sag_korelasyon"], 0.999)
        self.assertAlmostEqual(c["sure_sn"], 4.0, delta=0.01)

    def test_yerel_ton_degisimi(self):
        o = self.o
        n = int(120 * o.SR / o.HOP)
        t = np.arange(n) * o.HOP / o.SR
        C = np.full((12, n), 0.05)
        for k, w in zip([7, 9, 11, 0, 2, 4, 6], [5, 2, 3, 2.5, 4, 2, 1]):   # Sol major, 60. saniyede bir tam ses yukari (La major)
            C[k, t < 60] += w
            C[(k + 2) % 12, t >= 60] += w
        tonlar = o.yerel_tonlar(C, t, np.ones(n))
        self.assertEqual([(x["tonik"], x["mod"]) for x in tonlar], [(7, "major"), (9, "major")])
        self.assertAlmostEqual(tonlar[0]["son"], 60.0, delta=3.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
