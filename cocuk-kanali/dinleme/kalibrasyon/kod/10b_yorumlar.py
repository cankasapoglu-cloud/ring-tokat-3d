#!/usr/bin/env python3
"""Raporun yorum paragraflarini yazar (kod/yorumlar.json). Paragraflardaki sayilar ara/*.json'dan cekilir; yargilar elle yazilmistir."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from set import SET, KAL, KOK


def oku(ad, vars=None):
    y = os.path.join(KAL, "ara", ad)
    return json.load(open(y, encoding="utf8")) if os.path.exists(y) else (vars if vars is not None else {})


M = {m["ad"]: m for m in oku("olcumler.json", [])}
SD, AY, AK, UT, GK = oku("soz_denetimi.json"), oku("ayrisma.json"), oku("aksan_deneyi.json"), oku("unlu_tinisi.json"), oku("gercek_kanallar.json")
P, A, E, PI = "parmak-ailesi__", "ali-baba__", "el-yikama__", "pitirin-ailesi__yavas_2"


def s(v, n=1, isaret=False, yuzde=False):
    if v is None:
        return "–"
    if yuzde:
        return ("%%%.*f" % (n, 100 * v)).replace(".", ",")
    if isinstance(v, int) and not isaret:
        return str(v)
    return (("%+.*f" if isaret else "%.*f") % (n, v)).replace(".", ",")


def m(ad, k):
    return (M.get(ad) or {}).get(k)


def deg(adlar, k):
    return [m(a, k) for a in adlar if m(a, k) is not None]


def ar(adlar, k, n=2, isaret=False, yuzde=False):
    v = deg(adlar, k)
    if not v:
        return "–"
    return s(min(v), n, isaret, yuzde) if min(v) == max(v) else "%s … %s" % (s(min(v), n, isaret, yuzde), s(max(v), n, isaret, yuzde))


def gk(ad, e, k):
    g = GK.get(ad) or {}
    for ee, mm in g.items():
        if ee.startswith(e):
            return mm.get(k)
    return None


def lp(ad, k="ortalama_logprob"):
    return ((SD.get(ad) or {}).get("guven") or {}).get(k)


DOGAL = [A + "v2_2", A + "dinle_2", E + "coskulu_2", P + "coskulu_1", A + "coskulu_1", A + "coskulu_2", P + "duzgun_1", P + "duzgun_2", P + "turkce_2", P + "yavas_2", PI, E + "sarki_1", P + "sarki_2"]
DOGAL = [a for a in DOGAL if a in M]
ISL = [A + "ornek_kita1", A + "sarki_birlesik"]
COS, NIN = [a for a in (E + "coskulu_2", P + "coskulu_1", A + "demo_altyapi_sesli") if a in M], [a for a in (P + "yavas_2", PI, E + "sarki_1") if a in M]
VOKALLI = [a for a in M if a != A + "demo_altyapi_sesli"]
OTEKI16 = [a for a in VOKALLI if a != A + "dogal_onizleme"]
Y = {}
kisa = lambda a: a.split("__")[1]
KISA = lambda a: a.replace("__", "/")
N_OTEKI = len(OTEKI16)

# ------------------------------------------------------------------------------------------------ ENERJI
etiketsiz_eksi = [a for a in M if a not in COS + NIN and (m(a, "coca_cosku") or 0) < 0]
yanlis_uyari = [a for a in M if (m(a, "ozet") or {}).get("Enerji / coşku") == "dikkat" and (m(a, "coca_cosku") or 0) > 0.05 and (m(a, "ced_ninni") or 0) < 0.01]
Y["ENERJI_YORUM"] = "\n".join([
    "**MusicCoCa coşku farkı ve CED \"ninni\" olasılığı kullanıcının yargısını temiz ayırıyor;** iki şarkıda da aynı şarkının coşkulu ve ninni gibi kaydı doğru yana düşüyor "
    "(El Yıkama: %s karşısında %s; Parmak Ailesi: %s karşısında %s)." % (s(m(E + "coskulu_2", "coca_cosku"), 2, True), s(m(E + "sarki_1", "coca_cosku"), 2, True), s(m(P + "coskulu_1", "coca_cosku"), 2, True), s(m(P + "yavas_2", "coca_cosku"), 2, True)),
    "",
    "- Etiketsiz kayıtlar da tutarlı: yavaş dönemin öteki kayıtları (%s) eksi yanda." % ", ".join("`%s` %s" % (kisa(a), s(m(a, "coca_cosku"), 2, True)) for a in etiketsiz_eksi),
    "- `v2_2` (beğenildi, coşkusu hiç konuşulmadı) %s ile boşluğun içinde. Eşik bıçak sırtı değil; arada kalan kayıt \"kararsız\" sayılmalı." % s(m(A + "v2_2", "coca_cosku"), 2, True),
    "- **Hareketlilik puanı tek başına güvenilmez.** \"Ninni gibi\" denen `el-yikama/sarki_1` %s puan alıyor; seçilen coşkulu kayıtlar %s. Aradaki %s puanlık boşluğun içine etiketsiz %d kayıt giriyor. "
    "Puan vuruş ve olay sayıyor; `sarki_1` yavaş söylenmiş ama altyapısı kıpırtılı." % (s(m(E + "sarki_1", "enerji_puani"), 0), ar([E + "coskulu_2", P + "coskulu_1"], "enerji_puani", 0),
                                                                                    s((min(deg([E + "coskulu_2", P + "coskulu_1"], "enerji_puani")) - m(E + "sarki_1", "enerji_puani")), 0),
                                                                                    len([a for a in M if a not in COS + NIN and m(E + "sarki_1", "enerji_puani") < (m(a, "enerji_puani") or 0) < min(deg([E + "coskulu_2", P + "coskulu_1"], "enerji_puani"))])),
    "- **Aracın özet satırı yanlış uyarı veriyor.** Kural \"MusicCoCa eksi YA DA ninni ≥ 0,02 YA DA puan < 62\". Üçüncü koşul yüzünden MusicCoCa'sı açıkça artı olan %d kayıt \"ninni/sakin\" uyarısı alıyor: %s."
    % (len(yanlis_uyari), ", ".join("`%s` (puan %s, MusicCoCa %s)" % (kisa(a), s(m(a, "enerji_puani"), 0), s(m(a, "coca_cosku"), 2, True)) for a in yanlis_uyari))
    + (" Bunların arasında kullanıcının \"olmuş\" dediği altyapı da var." if A + "demo_altyapi_sesli" in yanlis_uyari else ""),
    "- Hece hızı ve otomatik tempo coşkuyu göstermiyor: seçilen `el-yikama/coskulu_2` %s hece/sn ile \"ninni gibi\" `parmak/yavas_2`'den (%s) yavaş; otomatik tempo \"ninni gibi\" kayıtlarda daha yüksek çıkıyor (%s BPM; büyük olasılıkla çift sayım)."
    % (s(m(E + "coskulu_2", "hece_sn_obek_medyan"), 1), s(m(P + "yavas_2", "hece_sn_obek_medyan"), 1), ar(NIN, "tempo_bpm", 0)),
    "",
    "Neyi söylemez: bu göstergeler müziğin türünü ve hareketini tanıyor; şarkıcının sesindeki neşeyi değil. Coşkulu bir altyapının üstünde isteksiz söyleyen bir ses bu sayılarla yakalanmaz.",
])

# ------------------------------------------------------------------------------------------------ DOGALLIK
dogal_wer = deg(DOGAL, "wer")
dogal_donmus = sorted([(m(a, "y_donmus_sure_orani") or 0, a) for a in DOGAL], reverse=True)
yuksek_donmus = [(v, a) for v, a in dogal_donmus if v >= 0.10]
mos_ninni = [P + "yavas_2", PI, E + "sarki_1"]
Y["DOGALLIK_YORUM"] = "\n".join([
    "Burada üç kayıt **aynı vokalden** geliyor, bu yüzden karşılaştırma temiz: `dinle_2` (özgün, beğenildi), `dogal-onizleme` (aynı vokal hiç işlenmeden başka orkestraya kondu), "
    "`sarki_birlesik` (aynı vokal iki katına esnetildi ve perdesi ezgiye çekildi). `ornek_kita1` ise konuşma sentezinin vokoderle ezgiye oturtulmuş hâli.",
    "",
    "**Temiz ayıran tek sayı: makine sözleri anlıyor mu.**",
    "",
    "- İşlenmemiş %d yapay şarkıcı kaydında sözcük hata oranı %s. Aynı vokal başka orkestrada %s. İşlenmiş iki vokalde %s ve %s."
    % (len(DOGAL), ar(DOGAL, "wer", 1, yuzde=True), s(m(A + "dogal_onizleme", "wer"), 1, yuzde=True), s(m(A + "sarki_birlesik", "wer"), 1, yuzde=True), s(m(A + "ornek_kita1", "wer"), 1, yuzde=True)),
    "- `dinle_2` → `sarki_birlesik`: aynı ses, aynı sözler; esnetme ve perde düzleme hata oranını %s'ten %s'e çıkarıyor. Scribe \"Ali Baba'nın\" yerine \"Ülke'nin\", \"dinle bak\" yerine \"iner ya\" duyuyor."
    % (s(m(A + "dinle_2", "wer"), 1, yuzde=True), s(m(A + "sarki_birlesik", "wer"), 1, yuzde=True)),
    "- Scribe'ın emin olmadığı sözcüklerin oranı da aynı yönde (%s ve %s; doğal kayıtlarda en çok %s), ama boşluk dar; eşik önermiyorum."
    % (s(lp(A + "sarki_birlesik", "oran_-0.3_alti"), 0, yuzde=True), s(lp(A + "ornek_kita1", "oran_-0.3_alti"), 0, yuzde=True),
       s(max([lp(a, "oran_-0.3_alti") for a in DOGAL + [A + "dogal_onizleme"] if lp(a, "oran_-0.3_alti") is not None] or [0]), 1, yuzde=True)),
    "",
    "**Aracın \"yapaylık\" vekilleri ayırmıyor.**",
    "",
    "- **Donmuş ünlü:** işlenmiş iki vokali yakalıyor (%s ve %s), ama doğal kayıtlardan %s de aynı uyarıyı alıyor. Bunlar yavaş, uzun tutulan notalarla söylenen kayıtlar; "
    "uyarı \"zaman esnetme / vokoder izlenimi\" diyor, oysa ölçtüğü şey uzun tutulan ünlü. Aynı vokalin iki hâli arasında işe yarıyor (`dinle_2` %s → `sarki_birlesik` %s), tek kayda hüküm olarak yaramıyor."
    % (s(m(A + "sarki_birlesik", "y_donmus_sure_orani"), 0, yuzde=True), s(m(A + "ornek_kita1", "y_donmus_sure_orani"), 0, yuzde=True),
       ", ".join("`%s` (%s)" % (KISA(a), s(v, 0, yuzde=True)) for v, a in yuksek_donmus) if yuksek_donmus else "hiçbiri",
       s(m(A + "dinle_2", "y_donmus_sure_orani"), 0, yuzde=True), s(m(A + "sarki_birlesik", "y_donmus_sure_orani"), 0, yuzde=True)),
    "- **Nota içi oynaklık, ızgaraya yapışma, vibrato:** örtüşüyor. `sarki_birlesik`'in perdesi panoda cetvelle çizilmiş gibi, ama oynaklığı %s cent (doğal kayıtlar %s). "
    "Ayrılmış kanaldaki artıklar düz perdeye sahte bir titreme ekliyor." % (s(m(A + "sarki_birlesik", "y_nota_ici_oynaklik_cent_medyan"), 1), ar(DOGAL, "y_nota_ici_oynaklik_cent_medyan", 1)),
    "- **\"Ünsüzlerde tiz zayıf\" uyarısı:** beğenilen `parmak/coskulu_1` de alıyor (%s dB; eşik −14). Yanlış alarm." % s(m(P + "coskulu_1", "y_unsuzlerde_tiz_payi_db"), 1, True),
    "- **Tiz doku:** işlenmiş vokallerde yüksek (%s, %s), ama hiç işlenmemiş vokalin başka orkestradaki hâlinde de %s. Sesi değil, ayırma artığını ölçüyor."
    % (s(m(A + "ornek_kita1", "y_tiz_doku_degisim_katsayisi"), 2), s(m(A + "sarki_birlesik", "y_tiz_doku_degisim_katsayisi"), 2), s(m(A + "dogal_onizleme", "y_tiz_doku_degisim_katsayisi"), 2)),
    "- **Konuşma-kalitesi tahminleri (DNSMOS, NISQA, Distill-MOS, UTMOS22):** hiç ayırmıyor. İşlenmiş vokaller UTMOS %s ve %s; beğenilen dört kayıt %s. Üstelik en yüksek UTMOS'u alan dört kayıt (%s) "
    "hepsi reddedilmiş, yavaş dönemin kayıtları: sakin, seyrek altyapılı kayıtta ses \"temiz konuşma\"ya daha çok benziyor. **Bu puanlar kullanıcının zevkiyle ters düşüyor; iyi/kötü notu olarak kullanılmamalı.**"
    % (s(m(A + "ornek_kita1", "utmos22"), 2), s(m(A + "sarki_birlesik", "utmos22"), 2), ar([A + "v2_2", A + "dinle_2", E + "coskulu_2", P + "coskulu_1"], "utmos22", 2),
       ", ".join("`%s` %s%s" % (KISA(a), s(v, 2), "" if [x for x in SET if x["ad"] == a][0]["karar"] == "reddetti" else " (BEĞENİLDİ)") for v, a in sorted([(m(a, "utmos22"), a) for a in VOKALLI if m(a, "utmos22") is not None], reverse=True)[:4])),
    "- CED'in \"sentetik şarkı\" ve \"konuşma sentezleyici\" etiketleri: ayırmıyor (sentetik şarkı: işlenmiş vokallerde %s ve %s, doğal kayıtlarda %s)."
    % (s(m(A + "ornek_kita1", "v_sentetik_sarki"), 3), s(m(A + "sarki_birlesik", "v_sentetik_sarki"), 3), ar(DOGAL, "v_sentetik_sarki", 3)),
    "",
    "Sonuç: araç \"bu vokal bozulmuş\" yargısını **sözlerin anlaşılmazlığı üzerinden** veriyor, sesin tınısı üzerinden değil. Sözleri anlaşılır kalan ama yapay tınlayan bir vokal bu sayılardan temiz çıkar.",
])

# ------------------------------------------------------------------------------------------------ GERCEK KANAL
BIRLESIK_EK = ""
if GK:
    o, g = "otomatik", "gerçek"
    Y["GERCEK_KANAL_YORUM"] = "\n".join([
        "- **Ön dinleme (işlenmemiş vokal, başka orkestra):** otomatik ayırmada ±25 cent içinde %%%s, ızgaraya yapışma %s, vokal − altyapı %s dB çıkmıştı. Gerçek kanallarla %%%s, %s ve %s dB. "
        "Yani \"detone\" ve \"gömük\" görünen vokal aslında öyle değil; ayırıcı bu karışımda vokali temiz çıkaramamış (klarnet ezgisi ve hayvan sesleri vokal kanalına sızmış)."
        % (s(gk(A + "dogal_onizleme", o, "yuzde_25cent"), 0), s(gk(A + "dogal_onizleme", o, "y_perde_izgaraya_yapisma_R"), 2), s(gk(A + "dogal_onizleme", o, "vokal_eksi_altyapi_db"), 1, True),
           s(gk(A + "dogal_onizleme", g, "yuzde_25cent"), 0), s(gk(A + "dogal_onizleme", g, "y_perde_izgaraya_yapisma_R"), 2), s(gk(A + "dogal_onizleme", g, "vokal_eksi_altyapi_db"), 1, True)),
        "- **Aynı kayıtta armoni:** gerçek kanallarla en iyi kaydırma %s, armonik destek %s, akor sesi %s, gam içi %s."
        % (s(gk(A + "dogal_onizleme", g, "en_iyi_kaydirma"), 0, True), s(gk(A + "dogal_onizleme", g, "destek_gercek"), 2), s(gk(A + "dogal_onizleme", g, "akor_sesi"), 0, yuzde=True), s(gk(A + "dogal_onizleme", g, "gam_ici"), 0, yuzde=True)),
        "- **Esnetilmiş vokal (`sarki_birlesik`):** gerçek kanalla donmuş ünlü %s (ayırmayla %s), nota içi oynaklık %s cent (ayırmayla %s), ızgaraya yapışma %s (ayırmayla %s). "
        % (s(gk(A + "sarki_birlesik", g, "y_donmus_sure_orani"), 0, yuzde=True), s(gk(A + "sarki_birlesik", o, "y_donmus_sure_orani"), 0, yuzde=True), s(gk(A + "sarki_birlesik", g, "y_nota_ici_oynaklik_cent_medyan"), 1),
           s(gk(A + "sarki_birlesik", o, "y_nota_ici_oynaklik_cent_medyan"), 1), s(gk(A + "sarki_birlesik", g, "y_perde_izgaraya_yapisma_R"), 2), s(gk(A + "sarki_birlesik", o, "y_perde_izgaraya_yapisma_R"), 2))
        + BIRLESIK_EK,
        "- **Vokoder vokali (`ornek_kita1`, kurucunun eski ölçümü):** gerçek kanalla ızgaraya yapışma %s (ayırmayla %s), ±25 cent içinde %%%s (ayırmayla %%%s), ritim R %s (ayırmayla %s). "
        "Ayırma, yapaylığın en belirgin izini (perdenin ızgaraya aşırı yapışması) siliyor ve ritmi bozuk gösteriyor."
        % (s(gk(A + "ornek_kita1", g, "y_perde_izgaraya_yapisma_R"), 2), s(gk(A + "ornek_kita1", o, "y_perde_izgaraya_yapisma_R"), 2), s(gk(A + "ornek_kita1", g, "yuzde_25cent"), 0), s(gk(A + "ornek_kita1", o, "yuzde_25cent"), 0),
           s(gk(A + "ornek_kita1", g, "ritim_R"), 2), s(gk(A + "ornek_kita1", o, "ritim_R"), 2)),
        "",
        "Çıkarım: **kendi ürettiğimiz kayıtlarda kanallar zaten elimizde; `--ayir` yerine `--vokal/--altyapi` kullanılmalı.** Otomatik ayırma hem yapaylık izlerini bulandırıyor hem de sahte \"detone / gömük\" uyarıları üretiyor.",
    ])

# ------------------------------------------------------------------------------------------------ UYUM
kaydirma_sifir_degil = [a for a in OTEKI16 if m(a, "en_iyi_kaydirma") not in (0, None)]
ayiranlar = []
for k, ad_, n_, isr, kucuk_kotu in (("yuzde_25cent", "±25 cent içinde", 0, False, True), ("y_perde_izgaraya_yapisma_R", "ızgaraya yapışma R", 2, False, True), ("vokal_eksi_altyapi_db", "vokal − altyapı dB", 1, True, True),
                                    ("v_konusma", "CED'in vokal kanalına \"konuşma\" demesi", 2, False, False)):
    v0 = m(A + "dogal_onizleme", k)
    vs = deg(OTEKI16, k)
    if v0 is None or not vs:
        continue
    temiz = (v0 < min(vs)) if kucuk_kotu else (v0 > max(vs))
    yz = "%" if k == "yuzde_25cent" else ""
    ayiranlar.append("%s: ön dinleme %s%s, öteki %d kayıt %s%s … %s%s%s" % (ad_, yz, s(v0, n_, isr), N_OTEKI, yz, s(min(vs), n_, isr), yz, s(max(vs), n_, isr), "" if temiz else " (örtüşüyor)"))
Y["UYUM_YORUM"] = "\n".join([
    "Reddedilen ön dinlemede vokal, beğenilen `dinle_2`'nin vokalinin **hiç işlenmemiş** hâli; değişen yalnızca orkestra. Yani bu çift, \"vokal iyi ama orkestrayla olmamış\" yargısı için neredeyse deney gibi.",
    "",
    "**Yan yana (aynı vokal, iki orkestra) fark çok açık:**",
    "",
    "| | `dinle_2` (beğenildi) | ön dinleme (\"olmamış\") |",
    "|---|---|---|",
    "| Vokalin söylediği seste orkestranın enerjisi (armonik destek) | %s | %s |" % (s(m(A + "dinle_2", "destek_gercek"), 2), s(m(A + "dogal_onizleme", "destek_gercek"), 2)),
    "| En iyi kaydırma (0 olmalı) | %s | %s |" % (s(m(A + "dinle_2", "en_iyi_kaydirma"), 0, True), s(m(A + "dogal_onizleme", "en_iyi_kaydirma"), 0, True)),
    "| Vokal − altyapı | %s dB | %s dB |" % (s(m(A + "dinle_2", "vokal_eksi_altyapi_db"), 1, True), s(m(A + "dogal_onizleme", "vokal_eksi_altyapi_db"), 1, True)),
    "| ±25 cent içinde | %%%s | %%%s |" % (s(m(A + "dinle_2", "yuzde_25cent"), 0), s(m(A + "dogal_onizleme", "yuzde_25cent"), 0)),
    "| Sözcük hata oranı | %s | %s (\"Ali Baba'nın\" → \"Anne babamın\") |" % (s(m(A + "dinle_2", "wer"), 1, yuzde=True), s(m(A + "dogal_onizleme", "wer"), 1, yuzde=True)),
    "",
    "**Tek kayda bakınca aracın armoni hükmü tutmuyor:**",
    "",
    "- \"En iyi kaydırma 0 olmalı\" denetimi ön dinlemeye **sorun** diyor (%s). Ama beğenilen `el-yikama/coskulu_2` de aynı sonucu alıyor (%s; destek %s). En iyi kaydırması 0 olmayan başka kayıtlar da var: %s."
    % (s(m(A + "dogal_onizleme", "en_iyi_kaydirma"), 0, True), s(m(E + "coskulu_2", "en_iyi_kaydirma"), 0, True), s(m(E + "coskulu_2", "destek_gercek"), 2),
       ", ".join("`%s` (%s)" % (KISA(a), s(m(a, "en_iyi_kaydirma"), 0, True)) for a in kaydirma_sifir_degil if a != E + "coskulu_2")),
    "- Nedeni: ölçü, vokalin söylediği seste orkestranın ne kadar enerjisi olduğuna bakıyor. Vokal akorun üçlüsünde ya da beşlisinde duruyorsa (kök ses yerine), tamamen uyumlu olsa bile \"kaydırsak daha iyi\" çıkıyor.",
    "- \"Gam içi söyleme\" ön dinlemede %s ile **iyi** diyor; armoni kuramı açısından vokal gerçekten gamın içinde. Kullanıcının \"olmamış\" dediği şey kuramsal uyumsuzluk değil."
    % s(m(A + "dogal_onizleme", "gam_ici"), 0, yuzde=True),
    "",
    "**Ön dinlemeyi öteki %d vokalli kayıttan ayıran sayılar var, ama armoni sayıları değil:**" % N_OTEKI,
    "",
] + ["- " + x + "." for x in ayiranlar] + [
    "",
    "Bunların hepsi aynı şeyi söylüyor: **ayırıcı bu karışımdan temiz bir vokal çıkaramıyor.** Gerçek kanallarla ölçünce (yukarıdaki tablo) vokalin kendisi sağlam. Demek ki aracın yakaladığı şey dolaylı bir belirti: "
    "vokalin yerinde, onunla yarışan başka bir ezgi sesi var (vokalin altına konan klarnet) ve makine ikisini ayıramıyor. Bu, kullanıcının \"altta başka ezgi çalıyor, olmamış\" demesiyle uyumlu; ama tek örnek.",
    "",
    "Ritim ölçüsü bu boyutta işe yaramadı: ön dinleme R %s, beğenilen `dinle_2` %s. Ritmi için hiçbir şikâyet olmayan `el-yikama/sarki_1` %s, `pitirin-ailesi/yavas_2` %s çıktı (vuruş ızgarası yanlış bulunmuş olmalı)."
    % (s(m(A + "dogal_onizleme", "ritim_R"), 2), s(m(A + "dinle_2", "ritim_R"), 2), s(m(E + "sarki_1", "ritim_R"), 2), s(m(PI, "ritim_R"), 2)),
])

# ------------------------------------------------------------------------------------------------ AKSAN
PAR = [P + "coskulu_1", P + "duzgun_1", P + "duzgun_2", P + "turkce_2", P + "yavas_2", P + "sarki_2"]
AKS, DIG = [P + "duzgun_1", P + "duzgun_2"], [P + "coskulu_1", P + "turkce_2", P + "yavas_2", P + "sarki_2"]
akv = lambda a, k: ((AK.get(a) or {}).get(k) or {}).get("medyan")
bur = lambda a: ((AK.get(a) or {}).get("sozcuk_suresi_sn") or {}).get("buradayım", [None])[0]
def ar2(adlar, f, n=1, isaret=True):
    v = [f(a) for a in adlar if f(a) is not None]
    return "%s … %s" % (s(min(v), n, isaret), s(max(v), n, isaret)) if v else "–"
Y["AKSAN_YORUM"] = "\n".join([
    "Altı Parmak Ailesi kaydı aynı sözleri söylüyor; ikisi (`duzgun_1`, `duzgun_2`) \"Türkçe konuşan bir İngiliz gibi\" diye reddedildi. **Hiçbir sayı bu ikisini ötekilerden ayırmıyor:**",
    "",
    "- **Sözcük hata oranı:** aksanlı iki kayıt %s; öteki dördü %s. Scribe aksanlı söyleneni de doğru yazıyor." % (ar(AKS, "wer", 0, yuzde=True), ar(DIG, "wer", 0, yuzde=True)),
    "- **Scribe'ın güveni:** `duzgun_2` ortalama logprob %s; seçilen kayıt %s. Fark yok. Dil olasılığı, bu çalışmada dökümü alınan kayıtların hepsinde 1,00 (Türkçe)." % (s(lp(P + "duzgun_2"), 3, True), s(lp(P + "coskulu_1"), 3, True)),
    "- **Kalite tahminleri:** aksanlı iki kayıt birbirine bile benzemiyor (NISQA %s ve %s)." % (s(m(P + "duzgun_1", "nisqa"), 2), s(m(P + "duzgun_2", "nisqa"), 2)),
    "- **İki fonetik deney** (araç dışı; aynı sözcükler kayıtlar arasında karşılaştırıldı): \"parmak\"taki r'nin İngiliz r'sine benzeyip benzemediği (aksanlılar %s dB, ötekiler %s dB) ve "
    "\"buradayım\"ın son ünlüsünün \"ı\" mı \"i\" mi olduğu (aksanlılar %s dB, ötekiler %s dB). İkisinde de aksanlı kayıtlar ötekilerin aralığının içinde. Ayrıca ikinci ölçü sözcüğün süresinden etkileniyor; güvenilmez."
    % (ar2(AKS, lambda a: akv(a, "parmak_r_vekili_db")), ar2(DIG, lambda a: akv(a, "parmak_r_vekili_db")), ar2(AKS, lambda a: akv(a, "buradayim_son_unlu_on_art_db")), ar2(DIG, lambda a: akv(a, "buradayim_son_unlu_on_art_db"))),
    "- **Ortak ölçülebilir tek özellik yavaşlık:** \"buradayım\" sözcüğü aksanlı iki kayıtta %s sn sürüyor, öteki dördünde %s sn; hece hızı da en düşük ikisi (%s/sn). "
    "Bu bir tempo ölçüsü; yavaş ama düzgün Türkçeyle söylenen bir kayıt da aynı sayıyı verir. **Aksan dedektörü olarak önermiyorum.**"
    % (ar2(AKS, bur, 2, False), ar2(DIG, bur, 2, False), ar(AKS, "hece_sn_obek_medyan", 1)),
    "- `duzgun_1`'de bir \"Merhaba\" dökümde \"Merengim\" çıktı. Bozuk telaffuzun izi olabilir; ama tek sözcük ve `duzgun_2`'de böyle bir şey yok.",
    "",
    "**Gemini'nin \"TELAFFUZ\" satırı denenmedi.** Araçta hazır (`gemini_dinle.py dinle <dosya>`), ama bu çalışmada canlı istek göndermedim. Sınamak için üç istek yeter: `duzgun_1`, `duzgun_2` ve `coskulu_1`. "
    "Önbellekteki eski cevaplar temkinli olmayı gerektiriyor: aynı iki kayıt sırası değiştirilip iki kez sorulduğunda (yeni45 / eski41) altı maddenin altısında da iki seferde **\"B\"**, yani sonra çalınan kazanmış. "
    "Tek yönlü A/B cevabı kanıt sayılmamalı.",
    "",
    "Sonuç: **aksan için tek hakem hâlâ kullanıcının kulağı.** Araç bu konuda \"sorun yok\" derse bu hiçbir şey ifade etmez.",
])

# ------------------------------------------------------------------------------------------------ HIZ
def kar(a):
    k = (SD.get(a) or {}).get("kitalar") or []
    b = [x["bas_sn"] for x in k]
    d = [b[i + 1] - b[i] for i in range(len(b) - 1)]
    return (sum(d) / len(d)) if d else None
Y["HIZ_YORUM"] = "\n".join([
    "- `sarki_2` (\"sözler çok hızlı geçiyor\") altı kaydın en hızlısı: öbek medyanı %s hece/sn, kıtadan kıtaya %s sn, toplam %s sn." % (s(m(P + "sarki_2", "hece_sn_obek_medyan"), 1), s(kar(P + "sarki_2"), 1), s(m(P + "sarki_2", "sure_sn"), 0)),
    "- Ama **seçilen** `coskulu_1` hemen yanında: %s hece/sn, %s sn. Aradaki %s hece/sn'lik fark, sözcük zamanlarının ±50 ms belirsizliği kadar. Söz içi hızda seçilen kayıt daha bile hızlı (%s karşısında %s)."
    % (s(m(P + "coskulu_1", "hece_sn_obek_medyan"), 1), s(kar(P + "coskulu_1"), 1), s(abs((m(P + "sarki_2", "hece_sn_obek_medyan") or 0) - (m(P + "coskulu_1", "hece_sn_obek_medyan") or 0)), 1),
       s(m(P + "coskulu_1", "hece_sn_soz_ici"), 1), s(m(P + "sarki_2", "hece_sn_soz_ici"), 1)),
    "- Aracın \"söyleyiş hızı\" uyarısı ters çalışıyor: uyarıyı beğenilen `coskulu_1` alıyor (bir saniyelik \"Buradayım, merhaba\" parçası 6,6 hece/sn çıktığı için), reddedilen `sarki_2` almıyor.",
    "- Görünen tek fark nefes payı: `sarki_2`'de soru ve cevap tek solukta söyleniyor ve kıtalar %s saniyede bir geliyor; `coskulu_1`'de son iki kıtada soruyla cevap arasında bir saniyelik ara var ve kıtalar %s saniyede bir geliyor."
    % (s(kar(P + "sarki_2"), 0), s(kar(P + "coskulu_1"), 0)),
    "",
    "**Eşik önermiyorum.** Kullanıcının kabul ettiği en hızlı kayıt ile reddettiği kayıt arasında ölçülebilir boşluk yok. Hece hızı iki sürümü sıralamaya yarar, \"çok hızlı\" hükmü vermeye yaramaz.",
])

# ------------------------------------------------------------------------------------------------ SURE / EZGI
uzun, kabul = [A + "coskulu_1", A + "coskulu_2"], [A + "v2_2", A + "dinle_2", E + "coskulu_2", P + "coskulu_1"]
Y["SURE_YORUM"] = ("\"Çok uzun\" denen iki kayıt %s sn; kabul edilen dört şarkı %s sn; \"olmuş\" denen yedi kıtalık altyapı %s sn. Arada temiz boşluk var (%s ile %s sn arası). "
                   "Doğrudan ölçüm; araç süreyi yazıyor ama uyarı vermiyor."
                   % (ar([a for a in uzun if a in M], "sure_sn", 0), ar(kabul, "sure_sn", 0), s(m(A + "demo_altyapi_sesli", "sure_sn"), 0), s(m(A + "demo_altyapi_sesli", "sure_sn"), 0),
                      s(min(deg([a for a in uzun if a in M], "sure_sn") or [0]), 0)))
Y["EZGI_YORUM"] = "\n".join([
    "Kullanıcı `v2_2` ve `dinle_2` için \"ezgi bilinen Ali Baba ezgisi değil\" dedi. **Araç bunu ölçmüyor;** yalnızca vokalin kendi orkestrasıyla uyumuna bakıyor, ve ikisi de kendi orkestrasıyla uyumlu çıkıyor.",
    "",
    "Tek dolaylı ipucu: `v2_2`'nin altyapı tonu **%s** bulundu. Bilinen ezgi majör; ton doğru bulunduysa bu kayıt o ezgi olamaz (ama ton bulma majör / minör ayrımında yanılabiliyor). `dinle_2`'de ton belirsiz çıktığı için aynı ipucu yok. "
    "Gerçek denetim için vokalin nota dizisini bilinen ezginin notalarıyla karşılaştırmak gerekir; notalar depoda hazır (`ali-baba/yeni3/altyapi/zaman_dogal.json` içinde `ezgi_notalari`), araçta böyle bir adım yok." % (m(A + "v2_2", "ton") or "?"),
])

# ------------------------------------------------------------------------------------------------ ESIKLER
ec, en_ = None, None
for r in (AY.get("enerji") or {}).get("olculer", []):
    if r["olcu"] == "coca_cosku":
        ec = r
    if r["olcu"] == "ced_ninni":
        en_ = r
wer_dogal_max = max(deg(DOGAL, "wer") or [0])
ESIK = []
if ec and ec.get("temiz_bosluk"):
    ESIK.append(dict(boyut="Enerji", kural="MusicCoCa coşku farkı **≥ %s → coşkulu yanda**; **≤ %s → ninni yanında**; arası kararsız" % (s(ec["bosluk"][1], 2, True), s(ec["bosluk"][0], 2, True)),
                     dayanak="coşkulu denen %d kayıt %s; ninni denen %d kayıt %s" % (len(COS), ar(COS, "coca_cosku", 2, True), len(NIN), ar(NIN, "coca_cosku", 2, True)), n="%d + %d" % (len(COS), len(NIN)),
                     nott="`v2_2` (%s) arada kalıyor" % s(m(A + "v2_2", "coca_cosku"), 2, True)))
if en_ and en_.get("temiz_bosluk"):
    ESIK.append(dict(boyut="Enerji", kural="CED \"ninni\" olasılığı **≥ 0,01 → ninni yanına kayıyor** (boşluğun ortası; ninni denenlerin hepsi ≥ %s, coşkulu denenlerin hepsi %s)" % (s(en_["bosluk"][1], 3), s(en_["bosluk"][0], 3)),
                     dayanak="coşkulu %s; ninni %s" % (ar(COS, "ced_ninni", 3), ar(NIN, "ced_ninni", 3)), n="%d + %d" % (len(COS), len(NIN)), nott="iki gösterge birlikte aynı yanı gösteriyorsa güvenilir; biri yetmez"))
ESIK.append(dict(boyut="Sözler", kural="Her kıtanın anahtar sözcüğü (aile adı, hayvan adı, söylenen hayvan sesi) beklenenle aynı değilse **ele**",
                 dayanak="kullanıcının söylediği yanlış ad hatalarının ikisi de bu yolla bulundu; sözcük hata oranı ayırmıyor", n="2 + 3", nott="eşik değil, kural; tek hecelik seslerde döküm yanılabiliyor"))
ESIK.append(dict(boyut="Anlaşılırlık (işlenmiş vokal)", kural="Sözcük hata oranı **≥ %30 → makine sözleri anlamıyor**, vokal bozulmuş olabilir",
                 dayanak="işlenmemiş kayıtlar en çok %s; aynı vokal başka orkestrada %s; işlenmiş iki vokal %s ve %s"
                 % (s(wer_dogal_max, 1, yuzde=True), s(m(A + "dogal_onizleme", "wer"), 1, yuzde=True), s(m(A + "sarki_birlesik", "wer"), 1, yuzde=True), s(m(A + "ornek_kita1", "wer"), 1, yuzde=True)),
                 n="%d + 2" % len(DOGAL), nott="%%30, %s ile %s arasındaki boşluğun içinde bir değer; altında kalmak \"doğal\" demek değil" % (s(m(A + "dogal_onizleme", "wer"), 0, yuzde=True), s(m(A + "sarki_birlesik", "wer"), 0, yuzde=True))))
ESIK.append(dict(boyut="Süre", kural="**180 sn'den uzun → \"çok uzun\" uyarısı**", dayanak="reddedilen %s sn; kabul edilen en uzun %s sn" % (ar([a for a in uzun if a in M], "sure_sn", 0), s(m(A + "demo_altyapi_sesli", "sure_sn"), 0)), n="5 + 2",
                 nott="kullanıcının sözü: \"3-3,5 dakika çok uzun\""))
ESIK.append(dict(boyut="Uyum (geçici, tek örnek)", kural="`--ayir` sonrası **vokal − altyapı < −8 dB** ve **±25 cent içinde < %75** birlikteyse: vokal karışımda kayboluyor, kullanıcıya göndermeden önce bak",
                 dayanak="ön dinleme %s dB ve %%%s; öteki vokalli kayıtlar en kötü %s dB ve %%%s"
                 % (s(m(A + "dogal_onizleme", "vokal_eksi_altyapi_db"), 1, True), s(m(A + "dogal_onizleme", "yuzde_25cent"), 0), s(min(deg(OTEKI16, "vokal_eksi_altyapi_db")), 1, True), s(min(deg(OTEKI16, "yuzde_25cent")), 0)),
                 n="%d + 1" % N_OTEKI, nott="**tek olumsuz örnek**; armoniyi değil ayırıcının zorlanmasını ölçüyor"))
Y["ESIKLER"] = "\n".join(["| Boyut | Kural | Dayanak | Örnek sayısı (olumlu + olumsuz) | Not |", "|---|---|---|---|---|"] + ["| %s | %s | %s | %s | %s |" % (e["boyut"], e["kural"], e["dayanak"], e["n"], e["nott"]) for e in ESIK] + [
    "",
    "**Eşik önermediğim yerler** (boşluk temiz değil): hareketlilik puanı; küçük sözcük hata oranları (%30'un altı); donmuş ünlü oranı ve öteki yapaylık vekilleri; konuşma-kalitesi tahminleri; "
    "armonik destek ve \"en iyi kaydırma\"; ritim sıkılığı; hece hızı; aksanla ilgili her şey.",
])
Y["_esikler_json"] = [{"boyut": e["boyut"], "kural": e["kural"].replace("**", ""), "dayanak": e["dayanak"], "ornek_sayisi": e["n"], "not": e["nott"].replace("**", "")} for e in ESIK]

# ------------------------------------------------------------------------------------------------ OZET SATIRLARI
KONU = ["Enerji / coşku", "Vokal / altyapı dengesi", "Vokal altyapıyla aynı armonide mi", "Gam içi söyleme", "Akort (detone mi)", "Çakışan uzun notalar", "Ritme oturma", "Yapaylık işaretleri (vekil)", "Sözler", "Söyleyiş hızı"]
say = lambda a: sum(1 for k in KONU if (m(a, "ozet") or {}).get(k) in ("dikkat", "sorun"))
BEG = [x["ad"] for x in SET if x["karar"] == "begendi" and x["ad"] in M and x["ad"] != A + "demo_altyapi_sesli"]
RED = [x["ad"] for x in SET if x["karar"] == "reddetti" and x["ad"] in M]
Y["OZET_SATIRI_YORUM"] = "\n".join([
    "- **Uyarı sayısı bir kalite notu değil.** Beğenilen dört şarkıda %s uyarı var; reddedilen on iki kayıtta %s. Örtüşüyor: aksan yüzünden reddedilen `duzgun_2` %d uyarıyla, seçilen `parmak/coskulu_1` %d uyarıyla çıkıyor."
    % ("%d ile %d arası" % (min(say(a) for a in BEG), max(say(a) for a in BEG)), "%d ile %d arası" % (min(say(a) for a in RED), max(say(a) for a in RED)), say(P + "duzgun_2"), say(P + "coskulu_1")),
    "- **Beğenilen kayıtlarda yanlış alarmlar:** `el-yikama/coskulu_2`'de \"aynı armonide mi: sorun\"; `parmak/coskulu_1`'de \"ünsüzlerde tiz zayıf\" ve \"söyleyiş hızı\"; üç beğenilen kayıtta \"ritme oturma: dikkat\" (R %s)."
    % ar([A + "dinle_2", E + "coskulu_2", P + "coskulu_1"], "ritim_R", 2),
    "- **Doğru yerde öten satırlar:** \"Sözler\" (işlenmiş iki vokalde ve ön dinlemede ✗), \"Enerji\" (ninni denen üç kayıtta !), \"Vokal / altyapı dengesi\" ve \"Akort\" (vokalli kayıtlar içinde yalnızca ön dinlemede).",
    "- Beğenilen çalgısal altyapı (`demo_altyapi_sesli`) %d uyarı alıyor; hepsi hayvan seslerinin vokal sanılmasından." % say(A + "demo_altyapi_sesli"),
    "- **Hiç işe yaramayan satır:** \"Ritme oturma\". Beğenilen ve reddedilen kayıtlar arasında R değerleri tamamen karışık; ritmi için şikâyet olmayan iki kayıtta R %s ve %s çıktı." % (s(m(E + "sarki_1", "ritim_R"), 2), s(m(PI, "ritim_R"), 2)),
])

# ------------------------------------------------------------------------------------------------ PANOLAR
Y["PANO_YORUM"] = "\n".join([
    "Dokuz kaydın panolarına Read aracıyla baktım (dört beğenilen: `v2_2`, `dinle_2`, `parmak/coskulu_1`, `demo_altyapi_sesli`; beş reddedilen: `ornek_kita1`, `sarki_birlesik`, `dogal-onizleme`, `duzgun_1`, `parmak/yavas_2`). "
    "Resim, özet sayıların söylemediği dört şeyi gösterdi:",
    "",
    "1. **Merdiven gibi perde (`sarki_birlesik`, perde panosu).** Vokal çizgisi cetvelle çizilmiş yatay çubuklar; notadan notaya dik basamakla iniyor; birkaç hece tek düz çizginin üstünde. "
    "Aynı vokalin özgün hâlinde (`dinle_2`) çizgi kıvrımlı, notalar kısa, geçişler eğik. Sayılar bunu kaçırdı (nota içi oynaklık %s cent, \"çok düz\" uyarısı yok); göz hemen görüyor. "
    "`ornek_kita1`'de aynı görüntü var: düz çubuklar, aralarında geçiş yok." % s(m(A + "sarki_birlesik", "y_nota_ici_oynaklik_cent_medyan"), 1),
    "2. **Vokal orkestranın boş bıraktığı seste (`dogal-onizleme`, perde panosunun en alt şeridi).** Mavi noktalar (vokalin söylediği ses: Mi) beyaz, boş bir satırda duruyor; orkestranın koyu şeritleri Do, Sol ve Fa'da. "
    "`dinle_2`'de aynı mavi noktalar koyu bir şeridin tam üstünde. Özet satırı \"gam içi %s, iyi\" diyordu; resim \"şarkıcı orkestranın çalmadığı yerde söylüyor\" diyor. "
    "Üst şeritte bir şey daha görünüyor: `dinle_2`'de orkestra tek akorda duruyor, ön dinlemede her ölçüde akor değişiyor ama vokal hep aynı seste kalıyor." % s(m(A + "dogal_onizleme", "gam_ici"), 0, yuzde=True),
    "3. **\"Çakışan nota\" dediği şey hayvan sesi (`ornek_kita1`, `dogal-onizleme`, `sarki_birlesik`).** Genel panoda turuncu \"[inek sesi]\" şeridinin altında, aşağı doğru kayan geniş bir harmonik yığını var; "
    "perde panosunda tam orada pes, −40 centlik kırmızı X'li iki \"nota\". Araç ineği detone şarkıcı sanıyor. Sayıya bakınca \"2 çakışan nota\" bir vokal kusuru gibi; resme bakınca değil. "
    "Çalgısal `demo_altyapi_sesli`'nin genel bakışında \"vokal var\" şeridi yalnızca yedi hayvan sesinin olduğu yerde dolu: dosyada şarkıcı olmadığı bir bakışta anlaşılıyor, oysa özet tablosu bu dosyaya da akort ve yapaylık uyarıları yazıyor.",
    "4. **Ninni ile coşkulu arasındaki fark tek bakışta (`parmak/yavas_2` karşısında `parmak/coskulu_1`, genel bakış).** MusicCoCa çubukları birinde baştan sona kırmızı (eksi), ötekinde baştan sona mavi. "
    "Spektrogramda coşkulu kayıt baştan aşağı sık dikey çizgilerle dolu (vurmalılar); ninni gibi olanda yatay bantlar ve altta toplanmış enerji var. Düzey şeridinde ninni kaydında altyapı vokal girince geri çekiliyor. "
    "`yavas_2`'nin \"donmuş ünlü\" satırındaki 11 kırmızı işaret her dizenin sonuna düzenli diziliyor: bunlar işlem artığı değil, uzatılan dize sonları.",
    "",
    "Resmin **göstermediği**: aksan. `duzgun_1` ile `coskulu_1`'in panoları yan yana konunca görülen tek fark, `duzgun_1`'de sözcüklerin iki üç kat uzun, kaygan ve ünsüzlerin silik olması; bu yavaş söyleyişin resmi, aksanın değil. "
    "\"atıları\" gibi tek hecelik bir bozukluk da panoda seçilmiyor.",
    "",
    "Sonuç: **görsel kanal gerçek bilgi ekliyor**, özellikle doğallık ve uyum boyutlarında, yani sayıların en zayıf olduğu yerde. Her yeni kayıtta en az bir perde panosuna bakmak, \"yapaylık işareti yok\" satırına güvenmekten iyidir.",
])
Y["_gorsel_json"] = [
    {"kayitlar": ["ali-baba__sarki_birlesik", "ali-baba__ornek_kita1", "ali-baba__dinle_2"], "gorulen": "islenmis vokalde perde cizgisi merdiven basamagi gibi duz ve dik gecisli; ozgun vokalde kivrimli", "sayida_var_mi": False},
    {"kayitlar": ["ali-baba__dogal_onizleme", "ali-baba__dinle_2"], "gorulen": "kroma seridinde vokalin ses sinifi orkestranin bos satirinda; ozgun kayitta koyu seridin ustunde", "sayida_var_mi": "kismen (armonik destek 0,28'e karsi 0,65; ozet satirinda gorunmuyor)"},
    {"kayitlar": ["ali-baba__ornek_kita1", "ali-baba__dogal_onizleme", "ali-baba__sarki_birlesik"], "gorulen": "'cakisan / detone nota' isaretleri hayvan sesinin ustunde", "sayida_var_mi": False},
    {"kayitlar": ["parmak-ailesi__yavas_2", "parmak-ailesi__coskulu_1"], "gorulen": "MusicCoCa cubuklari bastan sona eksi / arti; spektrogramda vurmali cizgileri; donmus unlu isaretleri dize sonlarinda", "sayida_var_mi": True},
    {"kayitlar": ["parmak-ailesi__duzgun_1", "parmak-ailesi__coskulu_1"], "gorulen": "aksan gorunmuyor; yalnizca sozcuklerin uzunlugu ve kayganligi", "sayida_var_mi": "aksan icin hicbir iz yok"},
]

# ------------------------------------------------------------------------------------------------ KUSURLAR
KUS = [
    ("Enerji özet satırı", "\"ninni/sakin\" uyarısı hareketlilik puanı < 62 olunca tek başına ötüyor; MusicCoCa'sı açıkça artı olan kayıtlarda yanlış uyarı (%s)." % ", ".join("`%s`" % kisa(a) for a in yanlis_uyari),
     "Uyarıyı MusicCoCa < 0 ya da CED ninni ≥ 0,02 koşuluna bağlamak; puanı yalnızca bilgi olarak yazmak."),
    ("Hayvan sesleri vokal sanılıyor", "Ayırıcı gerçek hayvan seslerini vokal kanalına koyuyor; araç bunları nota sayıp \"çakışan / detone nota\" ve geniş ses aralığı raporluyor. "
     "`ornek_kita1`'de işaretlenen 2 notanın 2'si, `sarki_birlesik`'te 3'ün 3'ü Scribe'ın hayvan sesi aralığının içinde; `dogal-onizleme`'de 4'ün en az 2'si (öteki ikisi horoz sesinin yerinde). "
     "Çalgısal `demo_altyapi_sesli`'de bütün \"vokal\" ölçümleri (donmuş ünlü %26, 3 çakışan nota) hayvan sesi.",
     "Scribe'ın ses olayı aralıklarını ([inek sesi] …) ya da CED'in hayvan pencerelerini nota analizinden çıkarmak; vokalsiz dosyada vokal bölümlerini hiç yazmamak."),
    ("\"Aynı armonide mi\" denetimi", "Beğenilen `el-yikama/coskulu_2`'ye \"sorun\" diyor (en iyi kaydırma %s). Vokal akorun kökünde değil üçlüsünde / beşlisinde durunca yanlış alarm." % s(m(E + "coskulu_2", "en_iyi_kaydirma"), 0, True),
     "Hükmü kaydırma sırasına değil, akor sesi oranına ve gam dışı orana bağlamak; ya da yalnızca ±1, ±2, ±6 kaydırmayı sorun saymak (şimdi −4 de sorun sayılıyor)."),
    ("Ton belirsizken de çakışan nota hükmü", "`duzgun_1`'de 8 uzun nota işaretlendi (6'sı \"gam dışı\" Fa); araç aynı raporda tonun belirsiz olduğunu (Sol majör?) söylüyor, vokalin kendi dağılımı Do majör gösteriyor. Hüküm \"sorun\" çıkıyor.",
     "Ton belirsizse \"gam dışı\" notaları hükme katmamak (gam içi oranında olduğu gibi)."),
    ("Donmuş ünlü uyarısı", "Doğal ama yavaş söylenen kayıtlarda ötüyor (%s). Metni \"zaman esnetme / vokoder izlenimi\" diyor." % (", ".join("`%s` %s" % (KISA(a), s(v, 0, yuzde=True)) for v, a in yuksek_donmus) or "–"),
     "Eşiği hece hızına göre ayarlamak ya da metni \"uzun tutulan ünlüler\" diye yumuşatmak."),
    ("\"Ünsüzlerde tiz zayıf\" uyarısı", "−14 dB eşiği doğal kayıtların ortasında: beğenilen `parmak/coskulu_1` %s dB." % s(m(P + "coskulu_1", "y_unsuzlerde_tiz_payi_db"), 1, True), "Eşiği düşürmek ya da uyarıyı kaldırmak."),
    ("Söyleyiş hızı uyarısı", "Tek bir bir saniyelik öbek 6,5 hece/sn'yi geçince bütün kayda \"dikkat\" diyor; beğenilen kayıt uyarı alıyor, \"çok hızlı\" denen almıyor.", "En hızlı tek öbek yerine medyanı ve kıta aralığını kullanmak."),
    ("Ritim satırındaki \"tavan ≈ 0,65\"", "Gerçek kayıtlarda R %s ölçüldü; 0,65 tavan değil. Ayrıca doğal bir kayıtta R %s (ızgara yanlış bulunmuş)." % (s(max(deg(VOKALLI, "ritim_R")), 2), s(m(E + "sarki_1", "ritim_R"), 2)),
     "Metni düzeltmek; otomatik ızgarada R'yi hüküm olarak değil bilgi olarak vermek."),
    ("Eski döküm verilemiyor", "Elde `*_words.json` varken aracı yeniden kredi harcamadan çalıştırmanın yolu yok; sarıcı yazmak gerekti.", "`--dokum-dosyasi` seçeneği."),
    ("Varsayılan çıktı klasörü çakışıyor", "Klasör adı yalnızca dosya adından geliyor: `ali-baba/coskulu_1.mp3` ile `parmak-ailesi/coskulu_1.mp3` aynı `raporlar/coskulu_1/` klasörüne yazar.", "Klasör adına üst klasörü ya da dosya özetini eklemek."),
    ("Kanal ayırma hep 0. ve 1. çekirdekte", "Aynı anda çalışan bütün dinle.py kopyaları aynı iki çekirdeğe sabitleniyor; bu çalışmada ayırma, öteki ekiplerle çakıştığı için beklenenin 2-3 katı sürdü (155 sn'lik şarkı 397 sn).", "Çekirdek seçimini ortam değişkenine bağlamak."),
    ("Beklenen sözlerdeki [hayvan sesi] etiketleri kullanılmıyor", "Scribe gerçek hayvan seslerini adıyla etiketliyor ([inek sesi], [koyun sesi] …; ön dinlemede yedisi de doğru sırada), ama araç bunları beklenenle karşılaştırmıyor.",
     "Söz dosyasındaki köşeli etiketleri Scribe'ın ses olaylarıyla sırayla eşleştirmek. Dikkat: `sarki_birlesik`'te Scribe sözleri yanlış duyunca kediyi \"[tilki sesi]\" diye etiketledi; etiket sözlerden bağımsız değil."),
]
Y["KUSURLAR"] = "\n".join(["| Konu | Görülen | Öneri |", "|---|---|---|"] + ["| %s | %s | %s |" % k for k in KUS])
Y["_kusurlar_json"] = [{"konu": a, "gorulen": b.replace("`", ""), "oneri": c.replace("`", "")} for a, b, c in KUS]

# ------------------------------------------------------------------------------------------------ SINIRLAR / SONRA
SIN = [
    "**Örnek çok küçük.** 17 kayıt; boyut başına 1 ile 6 arası etiket. \"Temiz boşluk\" iki üç noktanın arasındaki boşluktur; bir sonraki kayıt onu kapatabilir.",
    "**Etiketler özet.** Kullanıcının sözleri bana tek cümlelik özetler olarak geldi. Bir kayıt birden çok nedenle reddedilmiş olabilir (`duzgun_1` hem aksanlı hem yavaş hem söz hatalı); hangisinin belirleyici olduğunu bilmiyorum.",
    "**Beğenilen kayıt kusursuz kayıt değil.** `v2_2` beğenildi ama söz hatalı; `dinle_2` beğenildi ama bir kıtada yanlış hayvan var. \"Olumlu\" grup, o boyutta şikâyet edilmeyen kayıtlar demek.",
    "**Beklenen sözler yeniden kuruldu** (üretim istemleri depoda yok); sözcük hata oranları birkaç puan oynayabilir.",
    "**Yedi kayıtta eski döküm kullanıldı**; bunlarda Scribe'ın sözcük güveni yok. Aksanla reddedilen `duzgun_1` bunlardan biri.",
    "**Bütün vokaller otomatik ayırmayla elde edildi.** Ayırma kendi artıklarını ekliyor; gerçek kanallarla ölçüm iki kayıtta bunu gösterdi. Perde, akort ve yapaylık sayıları \"ayrılmış vokal\" için geçerlidir.",
    "**Bütün doğal vokaller aynı tür yapay şarkıcıdan.** Gerçek bir insan şarkıcının ya da başka bir üreticinin kaydında sayılar başka yerde durabilir.",
    "**Ben hiçbir kaydı duymadım.** Bu rapor, makinelerin ürettiği sayıların ve resimlerin kullanıcının sözleriyle karşılaştırmasıdır.",
]
Y["SINIRLAR"] = "\n".join("- " + x for x in SIN)
Y["_sinirlar_json"] = [x.replace("**", "").replace("`", "") for x in SIN]
SON = [
    "**Her yeni kullanıcı kararını bu kümeye ekle.** `kod/set.py`'ye bir satır, sonra `02` ve `05`…`11` betikleri: tablolar ve eşikler kendiliğinden güncellenir. Kalibrasyonu güçlendirecek tek şey daha çok etiket.",
    "**Kullanıcıya göndermeden önce sıra:** (1) kıta kıta anahtar sözcük denetimi, (2) MusicCoCa + CED ninni, (3) süre, (4) bir perde panosuna göz at, (5) önceki beğenilen kayıtla yan yana ölç. Aksan ve \"hoş mu\" için kullanıcının kulağı.",
    "**Kendi ürettiğimiz karışımlarda `--vokal/--altyapi` kullan**, `--ayir` değil.",
    "**Gemini'nin telaffuz satırını sına** (izin verilirse üç istek: `duzgun_1`, `duzgun_2`, `coskulu_1`). Aksanı yakalıyorsa araçtaki tek aksan göstergesi olur; yakalamıyorsa o satır rapordan çıkarılmalı.",
    "**Ezgi karşılaştırması ekle:** vokalin nota dizisini bilinen ezginin notalarıyla hizalayan bir adım. Kullanıcının iki kayıtta söylediği şikâyeti şu an hiçbir şey ölçmüyor.",
    "**Kullanıcının beğendiği gerçek Türkçe çocuk şarkıları** (3-5 tane) referans olarak eklenirse, \"doğal ses\" ve \"doğru aksan\" için ilk kez olumlu bir ölçüt olur.",
]
Y["SONRA"] = "\n".join("%d. %s" % (i + 1, x) for i, x in enumerate(SON))
Y["_gereksinim_json"] = [x.replace("**", "").replace("`", "") for x in SON]
json.dump(Y, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "yorumlar.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
print("yorumlar yazildi:", sorted(k for k in Y if not k.startswith("_")))
