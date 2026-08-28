#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HOOK KATMANI COVERAGE + `# ENFORCES:` SATIR-BASI CAPASI (2026-08-22).

NEDEN BU KORPUS VAR
-------------------
ADR 0019 uc-kademesi ("dosya var · WIRED · beyanli") bugune kadar YALNIZ
`scripts/validators/check_*.py` icin hesaplaniyordu. Hook'lar da gate'tir ve ayni
curumeye aciktir -- dahasi hook'ta "WIRED" DAHA sert bir kavramdir:

  Olculmus vaka (lessons-learned): `pre_tool_guard`a PowerShell destegi eklendi,
  29 senaryoluk test YESIL verdi, PR merge edildi -- ama `settings` matcher'i
  `Bash|mcp__sap-adt__.*` oldugu icin hook PowerShell'de HIC tetiklenmedi.
  Ders: guard'i DOGRUDAN cagiran her test sahte guvence uretir
  ("kod-seviyesi koruma" != "korunuyor"). ORPHAN sinifi tam bu dersin gate'idir.

IKINCI KUSUR (C2'nin ON KOSULU): `ENFORCES_RE` satir-basi CAPASIZ idi
(`r"#\\s*ENFORCES:"`). Kardesi `SEVERITY_RE` 2026-08-20'de tam bu yuzden
`^[ \\t]*#` ile capalanmisti; gerekce kayitli: **bir markoru TARIF eden metin, o
markoru BEYAN etmis sayilamaz**. Capasiz regex ile bir docstring icindeki
"`# ENFORCES:` satiri ekle" ANLATIMI gercek beyan yerine gecerdi ⇒ 17 hook'a beyan
eklenirken kabul olcutu ("17/17 beyan gorulur") ANLAMSIZ olurdu (sahte-yesil).

⛔ IZOLASYON: mutasyonlar GERCEK kaynaga YAZILMAZ. Her senaryo kendi gecici
agacinda kurulur (kopya validator + stub hook'lar + kendi settings.template.json).
Gercek kaynaga yazan mutasyon komsu testleri kirletir (olculmus sinif).

KOSUM:  python tests/fixtures/hook_gate_coverage/run.py
        ... --mutasyon-capa-yok        (ENFORCES_RE capasi sokulur -> duzyazi beyan sayilir)
        ... --mutasyon-hook-katmani-yok(hook bulgulari exit koduna KATILMAZ)
        ... --mutasyon-olcum-sessiz    ("OLCULEMEDI" hali sessizce temiz sayilir)
        ... --mutasyon-optout-yok      (N2: hook-ORPHAN dali OPT_OUT'u OKUMAZ)
        ... --mutasyon-id-sinirsiz     (N4: ENFORCES id ayristirmasi SINIRSIZ -- fix sokumu)
        ... --mutasyon-id-asiri-dar    (N4: ayristirma ASIRI daralir -- yalniz ILK token)
        ... --mutasyon-matcher-katmani-yok (N3: MATCHER DELIK bulgusu exit koduna KATILMAZ)
        ... --mutasyon-matcher-adi-uydur  (N3: beklenen kume KODDAN degil ELLE gelir)
        ... --mutasyon-optout-genis    (N5: muafiyet ENFORCES testini DE yutar)
        ... --mutasyon-kor-sessiz      (N5: kor yazim sessizce "tool ayrimi yok" sayilir)
        ... --mutasyon-kor-kovada      (N5: kor hook yanlis kovada da sayilir)
        ... --mutasyon-mesaj-tek-secenek (N5: MATCHER DELIK mesaji TEK secenek verir)
        ... --mutasyon-kor-bloklar     (N5: kor-yazim BLOKLAYICIYA terfi eder)
        ... --mutasyon-kova-cikarma    (Q1: kova KUME FARKI degil SAYI CIKARMASI)
        ... --mutasyon-kismi-korluk-yok(Q2: KISMI korluk 'tam denetlendi' sayilir)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi)

⭐ Q1/Q2 (2026-08-29) — UYUYAN IKI SAHTE-YESIL (S19/S20/S21):
  · Q1 kova aritmetigi SAYI CIKARMASIYLA yapiliyordu; kumeler cakisinca yalan soyluyordu
    (`OPT_OUT` ∩ kor-yazim -> ozet **-1 hook** basardi). Kume farki yapisal cozum.
    ⚠ BUGUNKU VERIDE CAKISMA YOK (olculdu: 17 hook · 7 tool-ayrimi · OPT_OUT=0 ·
    olculemeyen=0) => basilan sayi DEGISMEDI (10). Duzeltme bugunu degil cakisma GUNUNU
    hedefler; S19 o gunu sentetik olarak KURAR.
  · Q2 KISMI korluk: cozulen bir dalin YANINDA cozulemeyen ikinci dal varsa hook hicbir
    kovaya dusmuyor, gate "[OK] ... her tool matcher'la yonleniyor" diyordu.
  ⛔ IKI DAL YAPISAL OLARAK AYRIK YAZILDI (`elif` DEGIL): ilk yazimda `elif bos_kiyas:`
  idi ve TAM korlugu de yakaliyordu -> kardes mutasyon `--mutasyon-kor-sessiz` KACTI
  (21/21). Savunma-derinligi ust dalin OLCULEBILIRLIGINI yok ediyordu.

⭐ N3 (2026-08-22) — MATCHER-KAPSAMI (S13/S14): hook katmaninin ORPHAN dali "sablona
kablolu mu?" (var/yok) sorusunu yanitlar. S13/S14 bir ADIM ILERI gider: KABLOLU ama
YANLIS ADRESE mi? Olculmus vaka: `pre_tool_guard`a PowerShell destegi eklendi, 29
senaryo YESIL verdi, PR merge edildi -- matcher `Bash|mcp__sap-adt__.*` oldugu icin
hook PowerShell'de HIC tetiklenmedi. S14 tam bu sekli kurar (kod Bash+PowerShell
bekler, matcher yalniz Bash yonlendirir); S13 ayni agacin TEMIZ halidir (CORE-05:
ihlal FAIL **ve** temiz PASS -- tek yonlu test hipotezi dogrulamaz).

⚠ ON DORT MUTASYON, HICBIRI DIGERINI KAPSAMAZ: capa · bulgu->exit kablolamasi ·
  "olculemedi != temiz" · OPT_OUT muafiyeti (VARLIGI ve KAPSAMI ayri ayri) ·
  id-daraltmasi · daraltmanin POZITIF KONTROLU · kor-yazim tespiti ve KOVA aritmetigi ·
  bulgu MESAJININ iki onarim secenegi (metin de bir davranistir) · kor-yazimin SIDDETI.

⭐ N5 (2026-08-22) — DURUSTLUK TURU (S16/S17/S18), YENI YETENEK YOK:
  · S16: OPT_OUT muafiyeti `continue` ile ENFORCES testini DE yutuyordu -> basilan
    cumle ("kablolama ARANMAZ") muafiyetin GERCEK kapsamindan DARdi.
  · S17: `tool_name`e bakan ama yazimi (frozenset/ters-kiyas/fonksiyon-ici sabit/
    birlestirme) cozulemeyen hook, "tool ayrimi YAPMIYOR (kapsam disi)" kovasina
    dusuyordu = OLUMLU bicimde YANLIS. ⛔ Korluk KALDI, sadece GORUNUR oldu.
    ⚠ SIDDET: kor-yazim BLOKLAMAZ (uyarir) -- kusur hook'ta degil GATE'te; bloklamak
    gecerli Python'u araca uydurmaya zorlardi (`frozenset` bu evde yerlesik deyim).
  · S18: MATCHER DELIK mesaji TEK onarim veriyordu; olu dislama dali vakasinda o
    onarim YANLIS (matcher'i genisletmek tetiklenme yuzeyini buyutur).

⭐ N2 (2026-08-22) — MUAF-GIRIS PASS VEKTORU (S10): ADR 0019 devreye-alma merdiveninin
ADIM-6'si "IKI fixture: muaf-olmayan ihlal FAIL **ve** muaf giris PASS" der. Hook-ORPHAN
dali ilk yazimda (ayni gun) muafiyeti hic okumadigi icin bu adim ATLANMISTI: C-TPL-01
"OPT_OUT'a gerekceli ekle" derken bu gate ayni hook'u ORPHAN basip commit'i durduruyordu
(HARD) ⇒ belgelenmis kacis yolu fiilen KULLANILAMAZ. S10 iki gate'in AYNI cevabi
verdigini olcer; S4 onun kontrol grubudur (muafiyet YOKken ayni agac exit 1).

⭐ N4 (2026-08-22) — ID AYRISTIRMA SINIRI (S11/S12): kanonik beyan
`# ENFORCES: CORE-04  (ADR 0019 coverage binding)` idi ve sinirsiz split ACIKLAMAYI da
id sayiyordu (`0019`, `coverage` ...). S12 daraltmayi, S11 daraltmanin POZITIF KONTROLUNU
(cok-id'li mesru beyan HALA ikisini de verir) civiller -- biri digerini KAPSAMAZ.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
VDIR = REPO / "scripts" / "validators"
GATE = VDIR / "check_rule_gate_coverage.py"
TPL_SYNC = VDIR / "check_settings_template_sync.py"
HOOKS_GERCEK = REPO / "scripts" / "hooks"

OLCULEMEDI = "[ÖLÇÜLEMEDİ]"              # BLOKLAYAN olcum hatasi (sablon/hook bozuk)
OLCULEMEDI_UYARI = "[ÖLÇÜLEMEDİ · UYARI"  # kor-yazim: GORUNUR ama rc'yi ETKILEMEZ

# --- mutasyon capalari (ICERIK capasi; taban SHA DEGIL) ----------------------
CAPA_RE = ('ENFORCES_RE = re.compile(r"^[ \\t]*#\\s*ENFORCES:\\s*(.+)", '
           're.IGNORECASE | re.MULTILINE)')
# ⚠ CAPALAR N3'te (2026-08-22) TAZELENDI: matcher katmani `total`e uc terim daha
# ekleyince eski capalar TUTMADI ve iki mutasyon `[DOGRULANAMADI]` (exit 2) dondu.
# ⛔ BU BIR BASARIDIR, ariza degil: ucuncu deger olmasaydi bayat capa "mutasyon
# uygulanmadi" halini "mutasyon YAKALANDI" diye raporlardi (KURULAMADI != KACTI).
# Capalar artik SADECE kendi katmanlarini soker -> mutasyonlar birbirini KAPSAMAZ.
CAPA_TOTAL = ("             + len(h_missing) + len(h_orphan) + len(h_undeclared)\n"
              "             + (1 if h_olcum_hatasi else 0)\n")
# ⛔ CAPA_OLCUM IKI TERIMI BIRDEN SOKER -- ve bu bir GEVSETME DEGIL, MASKELEME
# ONARIMIDIR (olculdu 2026-08-22): N3 matcher katmani AYNI bozuk sablonu okudugu icin
# kendi `m_sablon_hatasi` terimini uretti; yalniz hook terimini soken mutasyon exit 1'i
# HALA goruyordu ve S7 SAHTE-YESIL kaldi (mutasyon KACTI, 14/14). Iki bagimsiz bulgu
# ayni exit koduna cikiyorsa biri otekini MASKELER -- bu evde olculmus sinif.
# ⚠ `len(m_delik)` ve `len(m_parse_hatalari)` BILEREK KORUNUR: S14/S15 bu mutasyondan
# ETKILENMEMELI, aksi halde mutasyonlar birbirini kapsardi.
CAPA_OLCUM = ("             + (1 if h_olcum_hatasi else 0)\n"
              "             + len(m_delik) + len(m_parse_hatalari) + "
              "(1 if m_sablon_hatasi else 0))")
# N2/N5: hook dalindaki OPT_OUT muafiyeti (N5'te `continue` -> `muaf` bayragina dondu:
# muafiyet YALNIZ ORPHAN testini atlar, ENFORCES testi HERKESE kosar).
CAPA_OPTOUT = ("        muaf = ad in h_optout  # C-TPL-01 muafiyeti — "
               "YALNIZ kablolama aranmaz\n")
# N5: kor-yazim (tool_name gecer ama ad kumesi BOS) -> OLCULEMEDI kaydi
CAPA_KOR = "        if kaynakta_tool and not bulunan and not onek:\n"
# N5: "kor hook 'tool ayrimi yapmiyor' kovasindan DUSULUR" aritmetigi
# ⚠ CAPA TAZELENDI (2026-08-29, Q1): kova artik SAYI CIKARMASI degil KUME FARKI.
# Eski capa (`len(h_mevcut) - m_denetlenen - len(h_optout) - m_olculemeyen_hook`)
# tabanda ARTIK YOK; guncellenmeseydi bu mutasyon [DOGRULANAMADI] (exit 2) donerdi --
# ki tam da oyle oldu ve UCUNCU DEGER sayesinde "gecti" diye okunmadi.
CAPA_KOR_KOVA = "    h_ayrim_yapmayan = h_mevcut - h_tool_ayrimi_yapan - h_optout - m_olculemeyen_adlar\n"
# N5: MATCHER DELIK bulgusunun IKI SECENEKLI onarim metni
CAPA_MESAJ = ("              f\"MATCHER DELİK=İKİ onarım var, vakaya göre seç: "
              "(a) koruma ÖLÜ ise \"\n"
              "              f\"şablondaki matcher'a o tool'u ekle "
              "(kablolu ama YANLIŞ ADRESTE) \"\n"
              "              f\"(b) kodda o tool'u işleyen dal ÖLÜ ise DALI KALDIR — "
              "dışlama dalı + \"\n"
              "              f\"bilinçli dar matcher bu sınıftadır; orada matcher'ı "
              "genişletmek \"\n"
              "              f\"hook'un tetiklenme yüzeyini gereksiz büyütür.\",\n")
# N4: id ayristirma yardimcisinin GOVDESI
CAPA_ID = ('    govde = ham.split("(", 1)[0]  # `(` görülünce dur — sonrası insan açıklamasıdır\n'
           '    return {t for t in re.split(r"[,\\s]+", govde.strip()) if _ID_RE.fullmatch(t)}')

# N3: MATCHER DELIK bulgusunun exit koduna KABLOLANMASI
CAPA_MATCHER_TOTAL = "             + len(m_delik) + len(m_parse_hatalari) + (1 if m_sablon_hatasi else 0))"
# N3: beklenen kumenin KODDAN turetilmesi (AST karsilastirma taramasi)
CAPA_MATCHER_AST = "                    if isinstance(op, (ast.In, ast.Eq, ast.NotIn, ast.NotEq)):"

MUTLAR = {
    # fix'in SOKUMU: capa kaldirilir -> duzyazidaki anis BEYAN sayilir (S6 duser)
    "--mutasyon-capa-yok": (
        CAPA_RE,
        'ENFORCES_RE = re.compile(r"#\\s*ENFORCES:\\s*(.+)", re.IGNORECASE)'),
    # KABLOLAMA sokumu: hook bulgulari hesaplanir ama exit koduna KATILMAZ.
    # ⚠ Bu, "gate kodu var ama bagli degil" sinifidir -- tam da ORPHAN'in olctugu sey.
    "--mutasyon-hook-katmani-yok": (CAPA_TOTAL, ""),
    # "OLCULEMEDI != TEMIZ" sozlesmesinin sokumu (S7 duser).
    "--mutasyon-olcum-sessiz": (
        CAPA_OLCUM,
        "             + 0\n"
        "             + len(m_delik) + len(m_parse_hatalari) + 0)"),
    # N3: AYRISTIRILAMAYAN HOOK bulgusunun exit'e kablolanmasi (S15 duser).
    # ⛔ AYRI MUTASYON SART: bu hata kaynagi sablondan BAGIMSIZDIR (bozuk .py dosyasi),
    # bu yuzden `--mutasyon-olcum-sessiz` onu HIC sinamaz.
    "--mutasyon-hook-parse-sessiz": (
        "+ len(m_delik) + len(m_parse_hatalari) +",
        "+ len(m_delik) + 0 +"),
    # N2 fix'in SOKUMU: muafiyet okunmaz -> muaf hook yine ORPHAN olur (S10 duser).
    "--mutasyon-optout-yok": (
        CAPA_OPTOUT, "        muaf = False  # MUTASYON: muafiyet OKUNMAZ\n"),
    # ⭐ N5 fix'in SOKUMU (AYRI DEGISMEZ): muafiyet ESKI haline (`continue`) doner ->
    # ORPHAN testiyle BIRLIKTE ENFORCES testini de yutar (S16 duser, S10 PASS kalir).
    # ⛔ Ustteki mutasyon bunu KAPSAMAZ: biri "muafiyet OKUNUYOR mu", oteki
    # "muafiyetin KAPSAMI ilan edildigi kadar mi" sorusunu olcer.
    "--mutasyon-optout-genis": (
        CAPA_OPTOUT,
        "        if ad in h_optout:\n"
        "            continue  # MUTASYON: eski davranis (ENFORCES testini DE yutar)\n"
        "        muaf = ad in h_optout\n"),
    # ⭐ N5: KOR-YAZIM tespitinin SOKUMU -> `tool_name`e bakan ama cozulemeyen hook
    # sessizce "tool ayrimi YAPMIYOR" kovasina duser (S17 duser: ne OLCULEMEDI notu
    # ne de dogru kova sayisi kalir).
    "--mutasyon-kor-sessiz": (
        CAPA_KOR, '        if False:  # MUTASYON: korluk sessizce "temiz" sayilir\n'),
    # ⭐ N5 IKINCI DEGISMEZ: kayit BASILIR ama kova aritmetigi ESKI kalir -> kor hook
    # HEM OLCULEMEDI listesinde HEM "tool ayrimi yapmiyor" sayisinda gorunur (cifte
    # sayim + olumlu-yanlis cumle). S17 YALNIZ kova cengelinden duser => o cengelin
    # tasiyici oldugunu kanitlar (ustteki mutasyon bunu ayirt EDEMEZ).
    "--mutasyon-kor-kovada": (
        CAPA_KOR_KOVA,
        "    h_ayrim_yapmayan = h_mevcut - h_tool_ayrimi_yapan - h_optout\n"),
    # ⭐ Q1 (2026-08-29) — KOVA ARITMETIGININ BICIMI (AYRI DEGISMEZ):
    # ustteki mutasyon "olculemeyen hook kovadan DUSULUYOR mu" sorusunu olcer;
    # bu ise "dusulme KUME FARKIYLA mi yoksa SAYI CIKARMASIYLA mi yapiliyor"
    # sorusunu. Ikisi ayni sey DEGIL: cikarma dogru sayiyi da uretebilir (bugun
    # uretiyor) ama kumeler CAKISINCA yalan soyler. S19 tam o cakismayi kurar.
    "--mutasyon-kova-cikarma": (
        '          f"{len(h_ayrim_yapmayan)} "\n',
        '          f"{len(h_mevcut) - m_denetlenen - len(h_optout) '
        '- len(m_olculemeyen_adlar)} "\n'),
    # ⭐ Q2 (2026-08-29) — KISMI KORLUK dalinin SOKUMU: cozulen bir dalin YANINDA
    # cozulemeyen ikinci dal tasiyan hook sessizce "tam denetlendi" sayilir (S20 duser).
    # ⛔ `--mutasyon-kor-sessiz`ten AYRI: o TAM korlugu, bu KISMI korlugu olcer.
    "--mutasyon-kismi-korluk-yok": (
        "        if bos_kiyas and (bulunan or onek):\n",
        "        if False:  # MUTASYON: kismi korluk sessizce 'tam denetlendi' sayilir\n"),
    # ⭐ N5 SIDDET CENGELI: kor-yazim `total`e KATILIRSA (yani BLOKLAYICI olursa)
    # S17 duser. ⛔ AYRI DEGISMEZ: ustteki iki mutasyon "kayit basiliyor mu / dogru
    # kovada mi" sorusunu olcer, bu "SIDDETI dogru mu" sorusunu. Warn-first bir dal
    # kazara bloklayiciya terfi ederse yalnizca BURASI kirmizi olur.
    "--mutasyon-kor-bloklar": (
        CAPA_MATCHER_TOTAL,
        "             + len(m_delik) + len(m_parse_hatalari) + len(m_korler) + "
        "(1 if m_sablon_hatasi else 0))"),
    # ⭐ N5: MESAJ fix'inin SOKUMU -> TEK onarim secenegi (fix oncesi hali). S18 duser.
    # ⚠ Mesaj METNI de bir davranistir: yanlis onarim oneren bulgu, bulunmayan
    # bulgudan pahaliya mal olabilir (matcher'i gereksiz genisletir).
    "--mutasyon-mesaj-tek-secenek": (
        CAPA_MESAJ,
        "              f\"MATCHER DELİK=şablondaki matcher'a o tool'u ekle "
        "(kablolu ama YANLIŞ ADRESTE).\",\n"),
    # N4 fix'in SOKUMU: sinirsiz split -> parantezli aciklama id uretir (S12 duser).
    "--mutasyon-id-sinirsiz": (
        CAPA_ID,
        '    return {t.strip() for t in re.split(r"[,\\s]+", ham) if t.strip()}'),
    # N4 POZITIF KONTROLU: daraltma ASIRIYA kacarsa (yalniz ilk token) cok-id'li
    # mesru beyan KIRILIR (S11 duser). ⛔ Ustteki mutasyon bunu KAPSAMAZ: biri
    # "yeterince daralttik mi", digeri "fazla daralttik mi" sorusunu olcer.
    "--mutasyon-id-asiri-dar": (
        CAPA_ID,
        '    govde = ham.split("(", 1)[0].split()\n'
        '    return {govde[0]} if govde and _ID_RE.fullmatch(govde[0]) else set()'),
    # N3 KABLOLAMA sokumu: delik HESAPLANIR ama exit koduna KATILMAZ -> S14 duser.
    # ⚠ Bu, gate'in KENDI uzerinde "kod != kablolama" sinifidir: bulgu basilir,
    # commit gecer. Cikti okunup exit kodu okunmazsa fark edilmez.
    "--mutasyon-matcher-katmani-yok": (
        CAPA_MATCHER_TOTAL, "             + 0)"),
    # N3 TURETME sokumu: AST karsilastirma taramasi olur -> hicbir hook'ta tool adi
    # BULUNMAZ -> denetlenen 0 olur (OLU GATE). ⛔ S13 bunu yakalar: "denetlenen>0"
    # bir ERISILEBILIRLIK cengelidir -- kusursuz agacta bile SIFIR denetleyen bir
    # gate, gecilemez degil GORUNMEZ bir gate'tir.
    "--mutasyon-matcher-adi-uydur": (
        CAPA_MATCHER_AST, "                    if False:"),
}

SABLON_BOZUK = "{ bu gecerli JSON DEGIL "


def _hook_govdesi(beyan: str) -> str:
    """Stub hook. `beyan` ham satir olarak gomulur (girinti/duzyazi varyantlari icin)."""
    return ("#!/usr/bin/env python3\n"
            f"{beyan}\n"
            '"""stub hook (fixture)."""\n'
            "raise SystemExit(0)\n")


HOOK_GOVDELERI = {
    # kanonik beyan (satir basi)
    "alfa": _hook_govdesi("# ENFORCES: X-01  (ADR 0019 coverage binding)"),
    # ⭐ GIRINTILI beyan MESRUDUR -- kardes SEVERITY_RE de `[ \t]*` toleransi tasir.
    # Capa eklenirken bu tolerans KAYBOLSAYDI gercek beyanlar dusherdi (pozitif kontrol).
    "beta": _hook_govdesi("    # ENFORCES: X-02  (girintili ama GERCEK beyan)"),
    # ⛔ DUZYAZI: markoru TARIF eder, BEYAN ETMEZ -> UNDECLARED sayilmali.
    "gama": ('#!/usr/bin/env python3\n'
             '"""Bu hook `# ENFORCES: X-03` markorunu TARIF eder; beyan DEGILDIR."""\n'
             "raise SystemExit(0)\n"),
    # beyani hic olmayan hook
    "delta": _hook_govdesi("# (beyan yok)"),
    # ⭐ N3: AYRISTIRILAMAYAN hook (SyntaxError). `# ENFORCES:` beyani GECERLI ve
    # kablolu -> hook katmani TEMIZ der; YALNIZ matcher katmani (AST) sikayet eder.
    # Boylece S15, S7'den BAGIMSIZ bir olcum-hatasi kaynagi kullanir.
    "zeta": ('#!/usr/bin/env python3\n'
             '# ENFORCES: X-07  (ADR 0019 coverage binding)\n'
             '"""stub hook: AYRISTIRILAMAZ (fixture)."""\n'
             'def bozuk(  :\n'),
    # ⭐ N3: kodunda TOOL ADI gecen hook. `pre_tool_guard`in gercek sekli budur:
    # kabuk tool'lari bir modul sabitinde durur, `tool_name in <sabit>` ile bakilir.
    # Beklenen kume ELLE VERILMEZ -- gate bunu AST ile KODDAN okur.
    "epsilon": ('#!/usr/bin/env python3\n'
                '# ENFORCES: X-06  (ADR 0019 coverage binding)\n'
                '"""stub hook: tool ayrimi YAPAR (fixture)."""\n'
                'import json, sys\n'
                '_KABUK_TOOLLARI = ("Bash", "PowerShell")\n'
                'data = {}\n'
                'tool_name = data.get("tool_name", "")\n'
                'if tool_name in _KABUK_TOOLLARI:\n'
                '    pass\n'
                'raise SystemExit(0)\n'),
    # ⭐ N5: KOR YAZIM. `tool_name`e BAKAR ama yazimi ayristiricinin tanidiklarindan
    # DEGIL (`frozenset(...)` cozulmez) -> ad kumesi BOS kalir. ⛔ Vektor kusurun
    # GERCEK yazim biciminde yazilir (olculen dort kor yazimdan biri). Bu hook
    # "tool ayrimi YAPMIYOR" DEGILDIR; gate onu OLCEMEZ -> [ÖLÇÜLEMEDİ].
    "teta": ('#!/usr/bin/env python3\n'
             '# ENFORCES: X-08  (ADR 0019 coverage binding)\n'
             '"""stub hook: tool ayrimi yapar, YAZIMI taninmiyor (fixture)."""\n'
             'data = {}\n'
             'if data.get("tool_name") in frozenset({"Bash", "PowerShell"}):\n'
             '    pass\n'
             'raise SystemExit(0)\n'),
    # ⭐ N5: DISLAMA dali (negatif kutupluluk — `itg_backstop`un gercek sekli).
    # Gate "kodda ADI GECEN tool" sorar, kutupluluk TAHMIN ETMEZ; matcher onu
    # yonlendirmiyorsa bulgu DOGRUDUR ama dogru onarim matcher'i genisletmek
    # DEGIL olu dali kaldirmaktir -> mesaj IKI secenek vermek ZORUNDA.
    "eta": ('#!/usr/bin/env python3\n'
            '# ENFORCES: X-09  (ADR 0019 coverage binding)\n'
            '"""stub hook: DISLAMA dali (fixture)."""\n'
            'data = {}\n'
            'tool_name = data.get("tool_name", "")\n'
            'if tool_name == "NotebookEdit":\n'
            '    raise SystemExit(0)\n'
            'raise SystemExit(0)\n'),
    # ⭐ Q2 (2026-08-29): KISMI KORLUK. `teta`nin (TAM korluk) kardesi ama AYNI SEY DEGIL:
    # burada BIR dal cozuluyor (`tool_name in _KABUK` -> {"Bash"}) ve IKINCI dal
    # cozulemiyor (`frozenset(...)`). Fix'ten once bu hook HICBIR kovaya dusmuyordu:
    # `bulunan` dolu oldugu icin KOR-YAZIM degil, matcher'i oldugu icin DELIK degil
    # => gate "[OK] ... her tool matcher'la yonleniyor" diyordu. Yani cozulemeyen dalin
    # tool'lari HIC denetlenmemis olmasina ragmen "tam kapsam" ilan ediliyordu.
    # ⛔ Vektor kusurun GERCEK yazim biciminde: `frozenset` bu evde yerlesik deyimdir ve
    # (b) TETIK aynen soyle tarif edilmisti: "mevcut cozulebilir dalin YANINA ikinci bir
    # tool dali eklendigi gun".
    "iota": ('#!/usr/bin/env python3\n'
             '# ENFORCES: X-10  (ADR 0019 coverage binding)\n'
             '"""stub hook: BIR dal cozulur, IKINCI dal cozulmez (fixture)."""\n'
             'data = {}\n'
             '_KABUK = ("Bash",)\n'
             'tool_name = data.get("tool_name", "")\n'
             'if tool_name in _KABUK:\n'
             '    pass\n'
             'if tool_name in frozenset({"PowerShell", "NotebookEdit"}):\n'
             '    pass\n'
             'raise SystemExit(0)\n'),
}


def _validator_govdesi(beyan: str) -> str:
    """Stub `check_*.py`. `beyan` ham `# ENFORCES:` satiri olarak gomulur."""
    return ("#!/usr/bin/env python3\n"
            f"{beyan}\n"
            '"""stub validator (fixture)."""\n'
            "raise SystemExit(0)\n")


def kur(kok: Path, hooklar: list[str], *, kablosuz: tuple[str, ...] = (),
        checklist_satiri: str = "", sablon_bozuk: bool = False,
        gate_kaynak: str | None = None, optout: tuple[str, ...] = (),
        validatorler: dict[str, str] | None = None,
        matcherler: dict[str, str] | None = None) -> Path:
    """Izole agac kurar: kopya validator + stub hook'lar + kendi settings.template.json.

    `REPO = Path(__file__).resolve().parents[2]` oldugu icin validator'i
    <kok>/scripts/validators/ altina koymak REPO'yu <kok> yapar (CORE-03: core
    varliklari icin `__file__` MESRUDUR, proje-kokune cevrilmez).
    """
    (kok / "scripts" / "validators").mkdir(parents=True, exist_ok=True)
    (kok / "scripts" / "hooks").mkdir(parents=True, exist_ok=True)
    (kok / "claude").mkdir(parents=True, exist_ok=True)
    (kok / "playbook" / "checklists").mkdir(parents=True, exist_ok=True)

    hedef = kok / "scripts" / "validators" / GATE.name
    hedef.write_text(gate_kaynak if gate_kaynak is not None
                     else GATE.read_text(encoding="utf-8"), encoding="utf-8")
    # ⛔ Tuketicinin IMPORT KOKU tasinmali: gate, kablolama okuyucusunu C-TPL-01'den
    # import eder (kopya DEGIL). Kardes dosya agacta yoksa olculen sey "fix" degil
    # "kurulum hatasi" olur (KURULAMADI != KACTI).
    tpl_kaynak = TPL_SYNC.read_text(encoding="utf-8")
    if optout:
        # ⛔ OPT_OUT TEK KAYNAKTIR: gate onu C-TPL-01 modulunden IMPORT eder. Fixture
        # bu yuzden muafiyeti KOPYA bir listeye degil, kardes modulun KENDISINE yazar --
        # aksi hâlde olculen sey "ortak kaynak" degil fixture'in kendi kurgusu olurdu.
        eski_optout = "OPT_OUT: set[str] = set()"
        assert eski_optout in tpl_kaynak, "OPT_OUT capasi C-TPL-01'de bulunamadi"
        tpl_kaynak = tpl_kaynak.replace(
            eski_optout, "OPT_OUT: set[str] = {%s}" % ", ".join(repr(a) for a in optout), 1)
    (kok / "scripts" / "validators" / TPL_SYNC.name).write_text(tpl_kaynak, encoding="utf-8")

    # Stub validator'lar + onlari WIRED gosteren stub runner (yoksa hepsi ORPHAN olurdu).
    for ad, beyan in (validatorler or {}).items():
        (kok / "scripts" / "validators" / f"{ad}.py").write_text(
            _validator_govdesi(beyan), encoding="utf-8")
    if validatorler:
        (kok / "scripts" / "validators" / "run_all_validators.py").write_text(
            "VALIDATORS = [\n"
            + "".join(f'    "{ad}.py",\n' for ad in validatorler)
            + "]\n", encoding="utf-8")

    for ad in hooklar:
        (kok / "scripts" / "hooks" / f"{ad}.py").write_text(
            HOOK_GOVDELERI[ad], encoding="utf-8")

    kablolu = [a for a in hooklar if a not in kablosuz]
    matcherler = matcherler or {}

    def _kanca(ad):
        return {"type": "command", "command": "python",
                "args": ["scripts/hook_shim.py", ad]}

    # matcher'i BELIRTILEN hook'lar kendi bloklarinda; otekiler matcher'siz blokta
    # (matcher yoksa Claude Code semantigi ".*" = her tool -> kapsam TAM).
    bloklar = [{"matcher": m, "hooks": [_kanca(ad)]}
               for ad, m in matcherler.items() if ad in kablolu]
    kalan = [ad for ad in kablolu if ad not in matcherler]
    if kalan:
        bloklar.append({"hooks": [_kanca(ad) for ad in kalan]})
    sablon = {"hooks": {"PreToolUse": bloklar}}
    yol = kok / "claude" / "settings.template.json"
    if sablon_bozuk:
        yol.write_text(SABLON_BOZUK, encoding="utf-8")
    else:
        yol.write_text(json.dumps(sablon, indent=2), encoding="utf-8")

    if checklist_satiri:
        (kok / "playbook" / "checklists" / "x.md").write_text(
            "| ID | Kontrol | Gate | Severity |\n|---|---|---|---|\n"
            + checklist_satiri + "\n", encoding="utf-8")
    return hedef


def kos_tpl(kok: Path) -> tuple[int, str]:
    """KARDES GATE (C-TPL-01) ayni agacta ne diyor? -- "iki gate zit cevap vermesin"."""
    yol = kok / "scripts" / "validators" / TPL_SYNC.name
    p = subprocess.run([sys.executable, str(yol)], capture_output=True, timeout=180)
    return p.returncode, (p.stdout.decode("utf-8", "replace")
                          + p.stderr.decode("utf-8", "replace"))


def kos(gate_yolu: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(gate_yolu)], capture_output=True, timeout=180)
    return p.returncode, (p.stdout.decode("utf-8", "replace")
                          + p.stderr.decode("utf-8", "replace"))


def main() -> int:
    # BILINMEYEN KIP SESSIZCE YESIL GECMESIN: `--mutasyon-ZIRVA` gibi bir yazim hatasi
    # HIC mutasyon kurmadan TAM PUAN uretirdi (exit 0) -- "mutasyon yakalandi" sanilan
    # sonuc aslinda mutasyonsuz kosum olurdu.
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(MUTLAR)))

    secili = [a for a in sys.argv[1:] if a in MUTLAR]
    gate_kaynak = None
    if secili:
        ham = GATE.read_text(encoding="utf-8")
        eski, yeni = MUTLAR[secili[0]]
        if eski not in ham:
            print(f"[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi ({secili[0]}) -> "
                  "mutasyon uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        gate_kaynak = ham.replace(eski, yeni, 1)

    tmp = Path(tempfile.mkdtemp(prefix="hook_gate_cov_"))
    sonuc: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, aciklama=""):
        sonuc.append((ad, bool(kosul), aciklama))

    def senaryo(ad: str, **kw) -> tuple[int, str]:
        kok = tmp / ad
        kok.mkdir(parents=True, exist_ok=True)
        return kos(kur(kok, gate_kaynak=gate_kaynak, **kw))

    def senaryo2(ad: str, **kw) -> tuple[int, str, int, str]:
        """Ayni agacta HER IKI gate -> (cov_rc, cov_out, tpl_rc, tpl_out)."""
        kok = tmp / ad
        kok.mkdir(parents=True, exist_ok=True)
        gate = kur(kok, gate_kaynak=gate_kaynak, **kw)
        rc, out = kos(gate)
        trc, tout = kos_tpl(kok)
        return rc, out, trc, tout

    try:
        # === S1 TEMIZ TABAN — kusursuz agac SIFIR bulgu vermeli ===============
        # ⚠ Bu vektor "erisilebilir yesil" kanitidir: gate'in TEMIZLENEBILIR oldugunu
        # gostermeyen bir gate, gecilemez bir gate'tir.
        rc, out = senaryo("s1", hooklar=["alfa", "beta"])
        ekle("S1 temiz agac -> exit 0 + hook ozeti SIFIR bulgu",
             rc == 0 and "Özet (hook): OK=2 · MISSING=0 · ORPHAN=0 · UNDECLARED=0" in out,
             f"exit={rc}")

        # === S2 GIRINTI TOLERANSI (pozitif kontrol) ==========================
        # ⛔ SILINEMEZ: capa eklenirken girinti toleransi de kaybolsaydi gercek
        # beyanlar dusherdi. "Sikilastirma kapiyi korletmedi" kaniti YALNIZ burasi.
        rc, out = senaryo("s2", hooklar=["beta"])
        ekle("S2 GIRINTILI `    # ENFORCES:` GERCEK beyandir (kapsam kaybi yok)",
             rc == 0 and "UNDECLARED=0" in out, f"exit={rc}")

        # === S3 UNDECLARED — beyansiz hook ===================================
        rc, out = senaryo("s3", hooklar=["alfa", "delta"])
        ekle("S3 beyansiz hook -> exit 1 + HOOK UNDECLARED + adi listelenir",
             rc == 1 and "HOOK UNDECLARED" in out and "delta" in out, f"exit={rc}")

        # === S4 ORPHAN — kablolanmamis hook (ASIL DERS) ======================
        # ⭐ S10'un KONTROL GRUBU: muafiyet YOKken ayni agac -> IKI gate de exit 1.
        rc, out, trc, tout = senaryo2("s4", hooklar=["alfa", "beta"], kablosuz=("beta",))
        ekle("S4 KABLOSUZ hook + OPT_OUT=() -> IKI gate de exit 1 (ORPHAN)",
             rc == 1 and "HOOK ORPHAN" in out and "beta" in out
             and trc == 1 and "KABLOLU DEĞİL" in tout,
             f"cov_exit={rc} tpl_exit={trc}")

        # === S5 MISSING — checklist yol-iddiasi, dosya YOK ===================
        rc, out = senaryo("s5", hooklar=["alfa"],
                          checklist_satiri="| K-01 | ornek | `scripts/hooks/hayalet.py` | BLOCKER |")
        ekle("S5 checklist `hooks/<ad>.py` verir ama dosya YOK -> exit 1 + HOOK MISSING",
             rc == 1 and "HOOK MISSING" in out and "hayalet" in out, f"exit={rc}")

        # === S6 DUZYAZI BEYAN SAYILMAZ (capanin KENDISI) =====================
        rc, out = senaryo("s6", hooklar=["alfa", "gama"])
        ekle("S6 docstring'de ANILAN `# ENFORCES:` BEYAN DEGILDIR -> gama UNDECLARED",
             rc == 1 and "HOOK UNDECLARED" in out and "gama" in out, f"exit={rc}")

        # === S7 OLCULEMEDI != TEMIZ =========================================
        # ⚠ HOOK LISTESI BILEREK BOS: ilk yazimda `hooklar=["alfa"]` idi ve vektor
        # SAHTE-YESIL veriyordu -- bozuk sablon kablolu-kumeyi de bosaltinca alfa
        # ORPHAN olup exit 1'i ZATEN uretiyordu. Yani "olculemedi exit'e katiliyor"
        # iddiasi olculmemis, KABA filtre ince filtreyi MASKELEMISTI
        # (`--mutasyon-olcum-sessiz` bu yuzden KACIYORdu; olculdu 2026-08-22).
        # Hook yokken tek olasi bulgu kaynagi OLCUM HATASIDIR -> izolasyon tam.
        rc, out = senaryo("s7", hooklar=[], sablon_bozuk=True)
        ekle("S7 sablon okunamazsa SESSIZ GECMEZ -> exit 1 + [ÖLÇÜLEMEDİ] notu",
             rc == 1 and OLCULEMEDI in out, f"exit={rc}")

        # === S10 ⭐ MUAF-GIRIS PASS (N2 — ADR 0019 merdiveni ADIM-6) ==========
        # S4 ile AYNI agac, TEK fark OPT_OUT. Muafiyet kullanildiginda IKI gate de
        # SUSMALI. Bu vektor olmadan "muafiyet var" iddiasi olculmemis kalirdi --
        # ve gate muafiyeti sessizce iptal ederken kimse fark etmezdi (olculdu:
        # ilk yazimda tam bu oluyordu, C-TPL-01 exit 0 / coverage exit 1).
        rc, out, trc, tout = senaryo2("s10", hooklar=["alfa", "beta"],
                                      kablosuz=("beta",), optout=("beta",))
        ekle("S10 MUAF-GIRIS: OPT_OUT=('beta',) -> IKI gate de exit 0 (zit cevap YOK)",
             rc == 0 and "ORPHAN=0" in out and "OPT_OUT" in out and "beta" in out
             and trc == 0,
             f"cov_exit={rc} tpl_exit={trc}")

        # === S11 ⭐ N4 POZITIF KONTROL — cok-id'li MESRU beyan korunur =========
        # ⛔ SILINEMEZ: N4 bir DARALTMADIR; "yeterince daralttik mi" (S12) ile
        # "fazla daralttik mi" (S11) AYRI sorulardir ve ayri mutasyonlarla civilidir.
        cok_id = "# ENFORCES: X-04, X-05  (ADR 0019 coverage binding)"
        rc, out = senaryo("s11", hooklar=["alfa"],
                          validatorler={"check_ornek": cok_id},
                          checklist_satiri=(
                              "| X-04 | ornek | `check_ornek.py` | BLOCKER |\n"
                              "| X-05 | ornek | `check_ornek.py` | BLOCKER |"))
        ekle("S11 `# ENFORCES: X-04, X-05` -> IKI id de beyan sayilir (OK=2, UNDECLARED=0)",
             rc == 0 and "Özet: OK=2 · MISSING=0 · ORPHAN=0 · UNDECLARED=0" in out,
             f"exit={rc}")

        # === S12 ⭐ N4 DARALTMA — parantezli ACIKLAMA id URETMEZ ===============
        # Kanonik beyanin aciklamasindaki `0019` token'i, id biciminE UYAR (rakam) --
        # yani onu eleyen sey `_ID_RE` DEGIL, `(` durdurucusudur. Vektor bilerek bu
        # token'i secer: "kaba filtre ince filtreyi maskelemesin".
        rc, out = senaryo("s12", hooklar=["alfa"],
                          validatorler={"check_ornek": cok_id},
                          checklist_satiri="| 0019 | ornek | `check_ornek.py` | BLOCKER |")
        ekle("S12 aciklamadaki `0019` BEYAN DEGILDIR -> exit 1 + UNDECLARED",
             rc == 1 and "UNDECLARED=1" in out and "0019" in out, f"exit={rc}")

        # === S13 ⭐ MATCHER TAM KAPSAM (CORE-05'in "temiz PASS" yarisi) =======
        # ⛔ SILINEMEZ: S14 tek basina "gate bir sey yakaliyor" der; kusursuz agacin
        # TEMIZLENEBILIR oldugunu YALNIZ S13 kanitlar. Ayrica `denetlenen=1` cengeli
        # ERISILEBILIRLIK olcusudur: turetme bozulursa (mutasyon) burasi SIFIR gosterir.
        rc, out = senaryo("s13", hooklar=["alfa", "epsilon"],
                          matcherler={"epsilon": "Bash|PowerShell"})
        ekle("S13 kodun andigi TUM tool matcher'da -> exit 0 + DENETLENEN=1 · DELIK=0",
             rc == 0 and "Özet (matcher): DENETLENEN=1 · DELİK=0" in out, f"exit={rc}")

        # === S14 ⭐ MATCHER DELIK — olculmus PowerShell vakasinin BIREBIR sekli ====
        # kod: ("Bash","PowerShell") · matcher: yalniz "Bash" ⇒ hook PowerShell'de HIC
        # tetiklenmez ama envanterde "kablolu" gorunur (ORPHAN DEGIL!). Iste bu yuzden
        # ORPHAN dali bu sinifi yakalayamaz ve ayri bir dal gerekir.
        rc, out = senaryo("s14", hooklar=["alfa", "epsilon"],
                          matcherler={"epsilon": "Bash"})
        ekle("S14 kod PowerShell bekler, matcher yalniz Bash -> exit 1 + MATCHER DELIK",
             rc == 1 and "MATCHER DELİK" in out and "PowerShell" in out
             and "ORPHAN=0" in out,  # kablolu -> ORPHAN DEGIL; sinif AYRI
             f"exit={rc}")

        # === S15 ⭐ AYRISTIRILAMAYAN HOOK -> OLCULEMEDI (SESSIZ GECMEZ) =======
        # ⚠ Hook katmani bu agaci TEMIZ gorur (dosya var · kablolu · beyanli) -- yani
        # bulgu YALNIZ matcher katmanindan gelir. Bozuk bir hook'un "tool ayrimi
        # yapmiyor" sayilmasi, gate'i bozuk kodla YESILE cevirirdi.
        rc, out = senaryo("s15", hooklar=["alfa", "zeta"])
        ekle("S15 ayristirilamayan hook -> exit 1 + [ÖLÇÜLEMEDİ] (sessiz 'tool ayrimi yok' DEGIL)",
             rc == 1 and OLCULEMEDI in out and "zeta" in out
             and "Özet (hook): OK=2" in out,  # hook katmani TEMIZ -> izolasyon kaniti
             f"exit={rc}")

        # === S16 ⭐ MUAF + BEYANSIZ -> HALA exit 1 (N5'in DISI) ==============
        # S10 ile AYNI kurgu, TEK fark: muaf hook'un `# ENFORCES:` beyani YOK.
        # Muafiyet KABLOLAMA muafiyetidir; beyan muafiyeti DEGIL. Fix'ten once
        # `continue` ENFORCES testini de yutuyordu ve bu agac exit 0 veriyordu ⇒
        # basilan cumle ("kablolama ARANMAZ") muafiyetin GERCEK kapsamindan DARdi.
        # ⚠ Kardes gate (C-TPL-01) burada exit 0 der ve bu ZIT CEVAP DEGILDIR:
        # o gate beyani hic okumaz, iki gate FARKLI soru sorar.
        rc, out, trc, tout = senaryo2("s16", hooklar=["alfa", "delta"],
                                      kablosuz=("delta",), optout=("delta",))
        ekle("S16 MUAF+BEYANSIZ hook -> exit 1 + HOOK UNDECLARED (muafiyet beyani YUTMAZ)",
             rc == 1 and "HOOK UNDECLARED" in out and "delta" in out
             and "ORPHAN=0" in out and "OPT_OUT" in out and trc == 0,
             f"cov_exit={rc} tpl_exit={trc}")

        # === S17 ⭐ KOR YAZIM -> OLCULEMEDI ama UYARI (rc=0) ==================
        # ⛔ Bu vektor TANIMA YETENEGI olcmez -- korluk BILEREK duruyor. Olctugu sey
        # DURUSTLUK + SIDDET: kor hook (a) [ÖLÇÜLEMEDİ] satirinda ADIYLA gorunur
        # (b) "tool ayrimi YAPMIYOR" kovasindan DUSULUR (c) ama commit'i DURDURMAZ.
        # Agacta 2 hook var; alfa gercekten tool ayrimi yapmiyor, teta OLCULEMEDI =>
        # kova 1 olmali (fix'ten once 2 idi ve teta'yi "kapsam disi" diye
        # OLUMLU-YANLIS tanimliyordu).
        # ⭐ `rc == 0` BILINCLI (kullanici karari 2026-08-22): kusur hook'ta DEGIL
        # gate'te. Bloklamak "gecerli Python'unu araca uydur" derdi; `frozenset` bu
        # evde yerlesik deyimdir. ⛔ SIDDET CENGELI SILINEMEZ -- `--mutasyon-kor-bloklar`
        # tam bu satiri sinar (warn-first bir dal kazara BLOKLAYICIYA terfi etmesin).
        rc, out = senaryo("s17", hooklar=["alfa", "teta"])
        ekle("S17 kor yazim -> rc=0 (UYARI) + [ÖLÇÜLEMEDİ] teta ADIYLA + kova=1",
             rc == 0 and OLCULEMEDI_UYARI in out and "teta" in out
             and "KÖR-YAZIM=1" in out
             and OLCULEMEDI not in out
             and "1 hook tool ayrımı YAPMIYOR" in out, f"exit={rc}")

        # === S18 ⭐ OLU DISLAMA DALI -> bulgu DOGRU, onarim IKI SECENEKLI ======
        # Kod `NotebookEdit`i ADIYLA isler (dislama), matcher yalniz `Bash` yonlendirir.
        # Bulgu dogrudur; ama burada matcher'a `NotebookEdit` eklemek hook'un
        # tetiklenme yuzeyini GEREKSIZ buyutur -- dogru onarim OLU DALI kaldirmaktir.
        rc, out = senaryo("s18", hooklar=["alfa", "eta"], matcherler={"eta": "Bash"})
        ekle("S18 olu dislama dali -> MATCHER DELIK + mesaj IKI onarim secenegi verir",
             rc == 1 and "MATCHER DELİK" in out and "NotebookEdit" in out
             and "DALI KALDIR" in out, f"exit={rc}")

        # === S19 ⭐ Q1: KOVA ARITMETIGI KUME FARKI OLMALI ====================
        # ⛔ CAKISAN KUME VEKTORU: tek hook (`teta`) HEM `OPT_OUT`ta HEM kor-yazimli.
        # ESKI aritmetik (sayi cikarmasi) onu IKI KEZ dusuyordu:
        #     len(h_mevcut)=1 - m_denetlenen=0 - len(h_optout)=1 - olculemeyen=1 = -1
        # ve ozet "**-1 hook** tool ayrimi YAPMIYOR" basiyordu. Kume farki NEGATIFE
        # DUSEMEZ: {teta} - {} - {teta} - {teta} = {} => 0.
        # ⚠ Bu vektor kaydin (2026-08-22 "Q1") (b) TETIGININ birebir sekli: "OPT_OUT'a
        # bir hook girdigi gun -- C-TPL-01'in hata mesaji bu kacis yolunu ACIKCA
        # oneriyor -- ve o hook kor-yazimliysa".
        # ⛔ NEGATIF SAYI CAPASI SILINEMEZ: yalniz "0" aramak yetmez, eski kod bir gun
        # baska bir sekilde 0 uretebilir; asil yasak olan NEGATIF sayinin basilmasidir.
        rc, out = senaryo("s19", hooklar=["teta"], optout=("teta",))
        ekle("S19 Q1: OPT_OUT ∩ kor-yazim -> kova 0 (NEGATIF sayi YOK)",
             rc == 0 and "0 hook tool ayrımı YAPMIYOR" in out
             and "-1 hook" not in out, f"exit={rc}")

        # === S20 ⭐ Q2: KISMI KORLUK 'tam denetlendi' SAYILMAZ ================
        # `iota` iki tool dali tasir: biri cozulur (Bash), oteki cozulmez (frozenset).
        # Fix'ten once bu hook hicbir kovaya dusmez ve gate "[OK] ... her tool matcher'la
        # yonleniyor" derdi -- yani OLCULMEMIS bir dal "denetlendi" sayilirdi.
        # ⛔ SIDDET S17 ile AYNI (rc=0, UYARI): kusur hook'ta degil GATE'in okuyamamasinda.
        # ⛔ KOVA CENGELI: `alfa` gercekten tool ayrimi yapmiyor => kova 1 olmali; `iota`
        # oraya DUSMEMELI (olumlu-yanlis tanim).
        rc, out = senaryo("s20", hooklar=["alfa", "iota"])
        ekle("S20 Q2: kismi korluk -> rc=0 (UYARI) + [ÖLÇÜLEMEDİ] iota ADIYLA + kova=1",
             rc == 0 and OLCULEMEDI_UYARI in out and "iota" in out
             and "KÖR-YAZIM=1" in out and OLCULEMEDI not in out
             and "1 hook tool ayrımı YAPMIYOR" in out, f"exit={rc}")

        # === S21 ⭐ Q2 POZITIF KONTROL — TAM cozulen hook UYARI ALMAZ =========
        # ⛔ SILINEMEZ: S20 tek basina "her hooka kor-yazim de" mutasyonuyla da gecerdi.
        # `epsilon` tek ve TAMAMEN cozulebilir bir dal tasir => KOR-YAZIM=0 olmali.
        # (Q2 fix'i asiri-siki olsaydi burasi kirmizi yanardi -- daraltmanin siniri.)
        rc, out = senaryo("s21", hooklar=["alfa", "epsilon"])
        ekle("S21 Q2 POZITIF KONTROL: tam cozulen hook UYARI ALMAZ (KÖR-YAZIM=0)",
             rc == 0 and "KÖR-YAZIM=0" in out and OLCULEMEDI_UYARI not in out
             and "DENETLENEN=1" in out, f"exit={rc}")

        # === S8 KABLOLAMA MANTIGI KOPYALANMADI ==============================
        # C-TPL-01 ile ORTAK okuyucu: ayni olgu iki yerde yasarsa biri bayatlar.
        kaynak = GATE.read_text(encoding="utf-8")
        # ⚠ Capa N2'de genisletildi: OPT_OUT da AYNI moduldan gelir. Iki adin da
        # ayni import satirinda olmasi "tek kaynak" sozlesmesinin ta kendisidir.
        ekle("S8 kablolama okuyucusu + OPT_OUT C-TPL-01'den IMPORT edilir (kopya DEGIL)",
             "from check_settings_template_sync import OPT_OUT, _kablolu_hooklar" in kaynak
             and "OPT_OUT: set[str]" not in kaynak,
             "kopya mantik = ikinci gercek (olculmus curume sinifi)")

        # === S9 GERCEK REPO — mevcut davranis BOZULMADI (pozitif kontrol) ====
        # ⚠ Sandbox yesili CANLI yesil demek degildir: gercek korpusta da olc.
        rc, out = kos(GATE)
        gercek_hook = len([p for p in HOOKS_GERCEK.glob("*.py")
                           if not p.name.startswith("_")])
        ekle("S9 CANLI repo: validator katmani + hook katmani birlikte TEMIZ",
             rc == 0 and "Özet: OK=" in out
             and f"Özet (hook): OK={gercek_hook} ·" in out
             and "MISSING=0 · ORPHAN=0 · UNDECLARED=0" in out,
             f"exit={rc}; canli hook sayisi={gercek_hook}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"[kalinti-kontrolu] gecici agac duruyor mu: "
              f"{'EVET -- TEMIZLIK BASARISIZ' if tmp.exists() else 'hayir'}")

    gecen = sum(1 for _a, k, _c in sonuc if k)
    for ad, k, ac in sonuc:
        print(f"  [{'PASS' if k else 'FAIL'}] {ad}" + (f"  ({ac})" if not k else ""))
    print(f"\nhook_gate_coverage: {gecen}/{len(sonuc)}")
    if secili:
        print(f"  (MUTASYON {secili[0]} — dusmesi BEKLENEN vektorler var; "
              f"tam skor 'mutasyon KACTI' demektir)")
        return 0 if gecen < len(sonuc) else 1
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
