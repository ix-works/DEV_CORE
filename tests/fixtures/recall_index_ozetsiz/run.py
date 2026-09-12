#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RECALL-INDEX: uretec + hook tazeleme korpusu (2026-08-21 dogdu · Q287 2026-09-12 genisledi).

NEDEN BU KORPUS VAR
-------------------
SAHNE 1 (2026-08-21) — `build_recall_index.memory_kayitlari()` YALNIZ `- [Baslik](dosya) — ozet`
seklindeki satirlari goruyordu. Canli olcum (auto-memory, 2026-08-21):
    MEMORY.md indeks satiri 147 · indekse giren 90 · **GORUNMEYEN 57**
Bu SESSIZ bir kayipti: uretec "[OK] 90 kayit" diyordu, eksik 57'yi kimse bildirmiyordu
("0 kayit" ile "0 eslesme" ayni cikti). Ozet-cumlesi ELLE yazilan bir alandir ve
unutulur; `description:` memory yazim sozlesmesinin ZORUNLU alanidir (214 dosyanin
213'unde var) => dogru geri-dusus kaynagi odur.

SAHNE 2 (Q287) — memory butce diyetiyle kayitlar `_indeks-*.md` HUB'larina tasindi, uretec
yalniz MEMORY.md'yi okuyordu: canli 294 ders dosyasinin 107'si indekslenebiliyordu ve 5 hub
dosyasinin KENDISI ders sayiliyordu. Hub satirlari `- [[slug]] — oz` bicimindedir.

SAHNE 3 (Q287) — indeksi TAZELEYEN hicbir mekanizma yoktu (bir proje 3 hafta bayat, uc proje
HIC indekssiz). `recall_inject` artik bayat/yok indeksi AYNI SUREC'te uretir; kilit + atomik
yazim + status dosyasi. Vektorler GERCEK hook CLI'si ve hook_shim'in runpy ortami ile kosar.

⭐ SINIF, VAKA DEGIL: kuyruk kaydi dar deseni (`^- \\[`) isaret ediyordu; olcum kapsamin
DAHA GENIS oldugunu gosterdi — canli indekste en degerli dersler `- ⭐ [Baslik](dosya)`
ve `- ⛔ [...]` seklinde yaziliyor ve dar desen onlarin HICBIRINI gormuyordu (9 satirin
4'u yildizli). Fix sinifi kapatir: "indeks kaynagindaki HER memory linki".

⛔ SKORLAMA DAVRANISI DEGISMEDI: `anahtar = tokenle(baslik)*3 + tokenle(oz)` formulu
AYNEN korunur (vektor C3/H11 bunu her kayit turu icin civiller).

⚠ Q287 DERSI — YETIM GERI-DUSUSU MUTASYONLARI MASKELER: hicbir indekste gecmeyen dosya da
description'dan kayit olur. Bu yuzden "geri-dusus sokuldu" / "dar desen" mutasyonlarinda
kayitlar YINE var (yetim olarak) ve eski P1..P6 vektorleri YESIL kaldi (olculdu: 16/16 KACTI).
Ayirt edici olan: BASLIGIN linkten gelmesi (P7) ve `yetim=0` sayaci (C7).

KOSUM:  python tests/fixtures/recall_index_ozetsiz/run.py [--mutasyon-<kip>]
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi/derlenmedi)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
URETEC = REPO / "scripts" / "build_recall_index.py"
HOOK = REPO / "scripts" / "hooks" / "recall_inject.py"

# kip -> (hedef dosya, eski, yeni). Hedef "U" = uretec, "H" = hook.
MUTLAR = {
    # --- SAHNE 1: fix'in SOKUMU (Q287: capa liste-satiri sarti kalktigi icin yeni satira tasindi)
    "--mutasyon-geridusus-yok": ("U",
        '        for baslik, dosya in _satir_linkleri(satir):',
        '        if True:  # MUTASYON: geri-dusus tumden sokuldu\n            continue\n'
        '        for baslik, dosya in _satir_linkleri(satir):'),
    # KAPSAM daraltmasi: yildizli/isaretli/duzyazi satirlari yine kacar
    "--mutasyon-dar-desen": ("U",
        '        for baslik, dosya in _satir_linkleri(satir):',
        '        if not re.match(r"^- \\[", satir):  # MUTASYON: dar desen geri geldi\n'
        '            continue\n'
        '        for baslik, dosya in _satir_linkleri(satir):'),
    # GEVSETME yonu: kaynak yokken kayit UYDUR
    "--mutasyon-uydur": ("U",
        '            if not oz:\n                continue',
        '            if not oz:\n                oz = baslik  # MUTASYON: kaynak yokken uydur'),
    # SATIR-ATLAMALI KIRLENME geri gelir (eski `\s*` davranisi).
    # ⚠ Yorum EKLEME: yer-tutucu bir CAGRI ARGUMANININ ortasindadir; `#` koyulursa satirin
    # kalani yorum olur ve `(` kapanmaz -> mutant SYNTAX ERROR verir.
    "--mutasyon-satirasan": ("U",
        r'r"^- \[([^\]]+)\]\(([^)]+)\)[ \t]*[—-][ \t]*(.+)$"',
        r'r"^- \[([^\]]+)\]\(([^)]+)\)\s*[—-]\s*(.+)$"'),
    # --- SAHNE 2 (Q287) ---------------------------------------------------------------
    "--mutasyon-hub-yok": ("U",
        '    hub_lar = sorted(p for p in memory_md.parent.glob(_HUB_DESENI) if p.is_file())',
        '    hub_lar = []  # MUTASYON: hub okunmaz'),
    "--mutasyon-wiki-ozlu-yok": ("U",
        '    for m in _WIKI_OZLU.finditer(metin):',
        '    for m in []:  # MUTASYON: wiki satir ozu okunmaz'),
    "--mutasyon-wiki-link-yok": ("U",
        '        if m.group(1) is not None:\n'
        '            out.append((_slug_basligi(m.group(1)), _wiki_dosya(m.group(1))))',
        '        if m.group(1) is not None:\n'
        '            continue  # MUTASYON: [[slug]] linki taninmaz'),
    "--mutasyon-hub-kayit": ("U",
        '    return ad == "MEMORY.md" or fnmatch.fnmatch(ad, _HUB_DESENI)',
        '    return False  # MUTASYON: hub/MEMORY.md ders kaydi sayilir'),
    "--mutasyon-oz-kesme-yok": ("U",
        '    m = _HER_LINK.search(oz)',
        '    m = None  # MUTASYON: oz sonraki linkte kesilmez'),
    "--mutasyon-ic-koseli": ("U",
        r'_HER_LINK = re.compile(r"\[\[([^\]|#]+)\]\]|\[((?:[^\[\]]|\[[^\]]*\])+)\]\(([^)]+\.md)\)")',
        r'_HER_LINK = re.compile(r"\[\[([^\]|#]+)\]\]|\[([^\]]+)\]\(([^)]+\.md)\)")'),
    "--mutasyon-yetim-uydur": ("U",
        '        if not oz:\n            continue\n        yetim += 1',
        '        if not oz:\n            oz = p.stem  # MUTASYON: yetimde kaynak yokken uydur\n'
        '        yetim += 1'),
    "--mutasyon-damga-yok": ("U",
        '        os.utime(hedef, (damga, damga))',
        '        pass  # MUTASYON: indeks mtime kaynak damgasina cekilmez'),
    # --- SAHNE 3 (Q287): hook tazeleme ----------------------------------------------
    "--mutasyon-tazeleme-yok": ("H",
        '    _tazele(proj, idx_p)\n',
        '    pass  # MUTASYON: tazeleme sokuldu\n'),
    "--mutasyon-bayat-olcut-yok": ("H",
        '            if idx_p.stat().st_mtime >= B.kaynak_mtime(proj):\n'
        '                return              # taze',
        '            if True:  # MUTASYON: yalniz YOK tetikler, BAYAT gorulmez\n'
        '                return              # taze'),
    "--mutasyon-kilit-yok": ("H",
        '        fd = _kilit_al(tmp / "recall-index.lock")',
        '        fd = os.open(os.devnull, os.O_RDONLY)  # MUTASYON: kilit yok sayilir'),
    "--mutasyon-olu-kilit-kalir": ("H",
        '            if yas < _KILIT_BAYAT_SN:',
        '            if True:  # MUTASYON: olu kilit hic temizlenmez'),
    "--mutasyon-hata-sessiz": ("H",
        '        _durum_yaz(tmp, {"tetik": tetik, "sonuc": "HATA", "hata": hata})',
        '        return  # MUTASYON: tazeleme hatasi SESSIZ'),
    "--mutasyon-stdout-kirli": ("H",
        '            bilgi = B.uret(proj)',
        '            bilgi = B.uret(proj); print("[OK] recall-index tazelendi")  # MUTASYON'),
}

# ============================== SAHNE 1 ==============================================
MEMORY_MD = """# Proje hafizasi

## Feedback

- [Ozetli ders](feedback_ozetli.md) — bu satirda ozet VAR, davranis degismemeli
- [Ozetsiz ders](feedback_ozetsiz.md)
- ⭐ [Yildizli ders](feedback_yildizli.md)
- ⛔ [**Kalin ve isaretli ders**](feedback_isaretli.md)
- [Cift link A](feedback_cifta.md) · [Cift link B](feedback_ciftb.md)
- [Frontmattersiz ders](feedback_fmsiz.md)
- [Description alani olmayan](feedback_descsiz.md)
- [Diskte olmayan dosya](feedback_yok.md)

## Project

- **Gruplu referans:** [Gruplu ders](project_gruplu.md) (parantez icinde aciklama)
"""


def _fm(ad, desc, tip="feedback"):
    return f"---\nname: {ad}\ndescription: {desc}\nmetadata:\n  type: {tip}\n---\n\ngovde\n"


DOSYALAR = {
    "feedback_ozetli.md": _fm("ozetli", "BU DESCRIPTION KULLANILMAMALI cunku satirda ozet var"),
    "feedback_ozetsiz.md": _fm("ozetsiz", "Ozetsiz dersin frontmatter aciklamasi burada yasar"),
    "feedback_yildizli.md": _fm("yildizli", "Yildizli dersin aciklamasi kritik oneme sahiptir"),
    "feedback_isaretli.md": _fm("isaretli", "Isaretli ve kalin yazilmis dersin aciklamasi"),
    "feedback_cifta.md": _fm("cifta", "Ciftli satirin birinci linki"),
    "feedback_ciftb.md": _fm("ciftb", "Ciftli satirin ikinci linki"),
    "feedback_fmsiz.md": "Bu dosyada frontmatter HIC YOK.\n\nGovde dogrudan basliyor.\n",
    "feedback_descsiz.md": ("---\nname: descsiz\nmetadata:\n  type: feedback\n---\n\n"
                            "description alani YOK.\n"),
    "project_gruplu.md": _fm("gruplu", "Gruplu referans satirindaki dersin aciklamasi", "project"),
    # feedback_yok.md BILEREK YAZILMAZ (diskte olmayan dosya vektoru)
}

# ============================== SAHNE 2 (hub) ========================================
S2_MEMORY_MD = """# Hafiza

- [Kok ders](feedback_kok.md) — kok indeksteki ozet kazanir
- [Hub A](_indeks-a.md) — alt indeks A
- **Alt indeks B:** [tam indeks](_indeks-b.md)
"""
S2_HUB_A = """---
name: _indeks-a
description: A hub dosyasinin kendi aciklamasi KAYIT OLMAMALI
metadata:
  type: reference
---

# A indeksi

- [[feedback_wiki-ozlu-ders]] — wiki satirindaki ozet metni burada
- [[feedback_wiki-ozsuz-ders]]
- [[feedback_kok]] — hubdaki ozet KULLANILMAMALI
"""
S2_HUB_B = """---
name: _indeks-b
description: B hub dosyasinin kendi aciklamasi KAYIT OLMAMALI
metadata:
  type: reference
---

- ⭐ [Md linkli hub dersi](feedback_md-hub.md)
- [Coklu A](feedback_coklu-a.md) — coklu satirin ilk ozeti · [Coklu B](feedback_coklu-b.md) — ikinci ozet
- [Push "[OK]" ic koseli baslik](feedback_ic-koseli.md)

Duzyazi satirinda linkli alt kayitlar: [[feedback_duzyazi-a]] · [[feedback_duzyazi-b]]
"""
S2_DOSYALAR = {
    "MEMORY.md": S2_MEMORY_MD,
    "_indeks-a.md": S2_HUB_A,
    "_indeks-b.md": S2_HUB_B,
    "feedback_kok.md": _fm("kok", "Kok dersin description metni KULLANILMAMALI"),
    "feedback_wiki-ozlu-ders.md": _fm("wiki-ozlu", "Wiki ozlu description KULLANILMAMALI"),
    "feedback_wiki-ozsuz-ders.md": _fm("wiki-ozsuz", "Wiki ozsuz dersin aciklamasi frontmatterda"),
    "feedback_md-hub.md": _fm("md-hub", "Md linkli hub dersinin aciklamasi"),
    "feedback_coklu-a.md": _fm("coklu-a", "Coklu A description"),
    "feedback_coklu-b.md": _fm("coklu-b", "Coklu B dersinin aciklamasi"),
    "feedback_ic-koseli.md": _fm("ic-koseli", "Ic koseli baslikli dersin aciklamasi"),
    "feedback_duzyazi-a.md": _fm("duzyazi-a", "Duzyazi A dersinin aciklamasi"),
    "feedback_duzyazi-b.md": _fm("duzyazi-b", "Duzyazi B dersinin aciklamasi"),
    "feedback_yetim.md": _fm("yetim", "Hicbir indekste gecmeyen yetim dersin aciklamasi"),
    "feedback_yetim-descsiz.md": "---\nname: yetim-descsiz\n---\n\ndescription yok\n",
}
S2_BEKLENEN = {"feedback_kok.md", "feedback_wiki-ozlu-ders.md", "feedback_wiki-ozsuz-ders.md",
               "feedback_md-hub.md", "feedback_coklu-a.md", "feedback_coklu-b.md",
               "feedback_ic-koseli.md", "feedback_duzyazi-a.md", "feedback_duzyazi-b.md",
               "feedback_yetim.md"}

# ============================== SAHNE 3 (hook) =======================================
S3_MEMORY_MD = "# Hafiza\n\n- [Hub](_indeks-h.md) — alt indeks\n"
S3_HUB = ("---\nname: _indeks-h\ndescription: hub\nmetadata:\n  type: reference\n---\n\n"
          "- [[feedback_zeplin-kargo-rotasi]] — zeplin kargo rotasi planlama ornegi\n")
S3_DOSYALAR = {
    "MEMORY.md": S3_MEMORY_MD,
    "_indeks-h.md": S3_HUB,
    "feedback_zeplin-kargo-rotasi.md": _fm("zeplin", "Zeplin kargo rotasi dersi"),
}
S3_LESSONS = "# Lessons\n\n## PATTERN #1: Denizalti periskop kalibrasyonu\n\nperiskop ayari once\n"
S3_HOWTO = "# Howto ornek konu\n\n> **Tetik:** ornek tetik cumlesi burada\n"
PROMPT_ZEPLIN = "zeplin kargo rotasi planlama konusunda daha once ne ogrendik acaba"
PROMPT_BALON = "balon yuk dengesi hesaplama notu hakkinda daha once bir sey yazmis miydik"
PROMPT_KISA = "devam"


def _yaz(dizin: Path, dosyalar: dict) -> None:
    dizin.mkdir(parents=True, exist_ok=True)
    for ad, ic in dosyalar.items():
        (dizin / ad).write_text(ic, encoding="utf-8")


def _mutant_kur(kip: str):
    hedef_tur, eski, yeni = MUTLAR[kip]
    asil = URETEC if hedef_tur == "U" else HOOK
    kaynak = asil.read_text(encoding="utf-8")
    if eski not in kaynak:
        print(f"[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi ({kip}) -> "
              "mutasyon uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
        return None, None
    mutant = asil.with_name(f"_mutant_{asil.name}")
    mutant.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8")
    # ⛔ KURULAMADI != KACTI (ucuncu deger): sozdizimi bozuk bir mutant kosMAZ.
    try:
        compile(mutant.read_text(encoding="utf-8"), str(mutant), "exec")
    except SyntaxError as e:
        mutant.unlink(missing_ok=True)
        print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({kip}): {e} -> "
              "olculen sey mutasyon degil, kurulum hatasidir.")
        return None, None
    return hedef_tur, mutant


def main() -> int:
    # BILINMEYEN KIP SESSIZCE YESIL GECMESIN (2026-08-22)
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(MUTLAR)))

    secili = [a for a in sys.argv[1:] if a in MUTLAR]
    uretec, hook, mutant = URETEC, HOOK, None
    if secili:
        tur, mutant = _mutant_kur(secili[0])
        if mutant is None:
            return 2
        if tur == "U":
            uretec = mutant
        else:
            hook = mutant

    tmp = Path(tempfile.mkdtemp(prefix="recall_ozetsiz_"))
    sonuc: list[tuple[str, bool, str]] = []

    def ekle(ad, kosul, aciklama=""):
        sonuc.append((ad, bool(kosul), aciklama))

    try:
        cfg = tmp / "claudecfg"
        sys.path.insert(0, str(REPO / "scripts"))
        os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
        from utils.claude_paths import auto_memory_dizini  # noqa: E402

        def ortam(proj):
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = str(proj)
            env["CLAUDE_CONFIG_DIR"] = str(cfg)
            env["PYTHONIOENCODING"] = "utf-8"
            return env

        def cli(proj, *arg):
            p = subprocess.run([sys.executable, str(uretec), *arg], env=ortam(proj),
                               cwd=str(proj), capture_output=True, timeout=180)
            return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")

        def mem_oku(proj):
            h = proj / ".tmp" / "recall-index.json"
            veri = json.loads(h.read_text(encoding="utf-8")) if h.is_file() else {"kayit": []}
            return {k["id"]: k for k in veri["kayit"] if k["id"].startswith("mem:")}

        # ======================= SAHNE 1 =================================================
        proj = tmp / "proje"
        proj.mkdir(parents=True, exist_ok=True)
        mem = Path(auto_memory_dizini(proj))
        _yaz(mem, {"MEMORY.md": MEMORY_MD, **DOSYALAR})

        rc, cikti, err = cli(proj)
        hedef = proj / ".tmp" / "recall-index.json"
        ekle("E1 CLI exit 0 + indeks dosyasi uretildi",
             rc == 0 and hedef.is_file(), f"exit={rc} stderr={err[:200]}")
        mem_kayit = mem_oku(proj)

        ekle("P1 ozetsiz satir INDEKSE GIRER (description'dan)",
             "frontmatter aciklamasi" in mem_kayit.get("mem:feedback_ozetsiz.md", {}).get("oz", ""),
             "eski kodda bu satir GORUNMEZDI")
        ekle("P2 ⭐ YILDIZLI satir da girer (dar desen bunu kaciriyordu)",
             mem_kayit.get("mem:feedback_yildizli.md", {}).get("oz", "") != "",
             "canli indekste en degerli dersler bu bicimde yaziliyor")
        ekle("P3 ⛔ isaretli + **kalin** baslik girer, baslik temizlenir",
             "mem:feedback_isaretli.md" in mem_kayit
             and "*" not in mem_kayit.get("mem:feedback_isaretli.md", {}).get("baslik", "*"),
             "markdown vurgu isaretleri baslikta kalmamali")
        ekle("P4 TEK satirdaki IKI link -> IKI ayri kayit",
             "mem:feedback_cifta.md" in mem_kayit and "mem:feedback_ciftb.md" in mem_kayit)
        ekle("P5 gruplu referans satiri (`- **X:** [link]`) da girer",
             "mem:project_gruplu.md" in mem_kayit)
        ekle("P6 yeni kayitlarin `oz` alani GERCEKTEN DOLU",
             all(mem_kayit.get(i, {}).get("oz", "").strip()
                 for i in ("mem:feedback_ozetsiz.md", "mem:feedback_yildizli.md",
                           "mem:feedback_isaretli.md", "mem:feedback_cifta.md",
                           "mem:project_gruplu.md")),
             "bos `oz` = kayit var ama skorlamaya HICBIR SEY katmiyor (sahte kazanim)")
        # Q287: yetim geri-dususu kaydi YINE uretir; ayirt edici olan BASLIGIN kaynagidir.
        basliklar = {i: mem_kayit.get(i, {}).get("baslik") for i in
                     ("mem:feedback_ozetsiz.md", "mem:feedback_yildizli.md",
                      "mem:feedback_isaretli.md", "mem:project_gruplu.md")}
        ekle("P7 geri-dusus kayitlarinin BASLIGI linkten gelir (slug'dan degil)",
             basliklar == {"mem:feedback_ozetsiz.md": "Ozetsiz ders",
                           "mem:feedback_yildizli.md": "Yildizli ders",
                           "mem:feedback_isaretli.md": "Kalin ve isaretli ders",
                           "mem:project_gruplu.md": "Gruplu ders"},
             f"basliklar={basliklar} (slug basligi = yetim yolundan girmis demektir)")

        ekle("N1 frontmatter'i OLMAYAN dosya -> kayit YOK",
             "mem:feedback_fmsiz.md" not in mem_kayit,
             "kaynak yoksa kayit da yok; baslik'i `oz` diye kopyalamak UYDURMADIR")
        ekle("N2 `description:` alani olmayan dosya -> kayit YOK",
             "mem:feedback_descsiz.md" not in mem_kayit)
        ekle("N3 diskte OLMAYAN dosya -> kayit YOK, COKME YOK",
             "mem:feedback_yok.md" not in mem_kayit and rc == 0)

        ozetli = mem_kayit.get("mem:feedback_ozetli.md", {})
        ekle("C1 ozetli satirin `oz`u SATIRDAN gelir (description'dan DEGIL)",
             ozetli.get("oz", "").startswith("bu satirda ozet VAR")
             and "KULLANILMAMALI" not in ozetli.get("oz", ""),
             "geri-dusus mevcut kaynagi EZMEMELI")
        ekle("C2 ozetli kayit mevcut alan sozlesmesini korur",
             set(ozetli) == {"id", "kaynak", "baslik", "oz", "anahtar"}
             and ozetli.get("kaynak") == "memory/feedback_ozetli.md")

        import importlib.util
        _s = importlib.util.spec_from_file_location("_bri_t", str(uretec))
        _m = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_m)

        def formul_ok(k):
            return bool(k) and k.get("anahtar") == _m.tokenle(k["baslik"]) * 3 + _m.tokenle(k["oz"])
        ekle("C3 `anahtar` formulu (baslik x3 + oz) IKI TURDE DE aynen korunur",
             formul_ok(ozetli) and formul_ok(mem_kayit.get("mem:feedback_ozetsiz.md")),
             "skorlama davranisi DEGISMEMELI (yalniz kapsam acildi)")
        ekle("C4 kayit sayisi TAM olarak kaynagi olan 7 ders",
             len(mem_kayit) == 7 and "mem:feedback_ozetli.md" in mem_kayit,
             f"mem kayit sayisi={len(mem_kayit)}")
        kirli = [i for i, k in mem_kayit.items()
                 if "](" in k["oz"] or k["oz"].lstrip().startswith(("-", "⭐", "⛔"))]
        ekle("C6 SATIR-ATLAMALI KIRLENME yok: hicbir `oz` komsu satirin metni degil",
             not kirli, f"kirlenen kayitlar={kirli}")
        ekle("C5 CLI ozet satiri kayit sayisini BASAR (sessiz kayip gorunur olsun)",
             "recall-index:" in cikti and "memory=" in cikti, cikti.strip()[:160])
        ekle("C7 butun dosyalar indeksli -> CLI `yetim=0`",
             "yetim=0" in cikti, cikti.strip()[:200])

        # ======================= SAHNE 2 (hub) ===========================================
        proj2 = tmp / "proje2"
        proj2.mkdir(parents=True, exist_ok=True)
        mem2 = Path(auto_memory_dizini(proj2))
        _yaz(mem2, S2_DOSYALAR)
        gelecek = time.time() + 7200
        os.utime(mem2 / "feedback_duzyazi-b.md", (gelecek, gelecek))
        rc2, cikti2, err2 = cli(proj2)
        k2 = mem_oku(proj2)
        ids2 = {i[4:] for i in k2}
        ekle("H0 CLI exit 0 (hub sahnesi)", rc2 == 0, f"exit={rc2} stderr={err2[:200]}")
        w = k2.get("mem:feedback_wiki-ozlu-ders.md", {})
        ekle("H1 hub `[[slug]] — oz` satiri girer: oz SATIRDAN, baslik SLUG'dan",
             w.get("oz") == "wiki satirindaki ozet metni burada" and w.get("baslik") == "wiki ozlu ders",
             f"kayit={ {k: w.get(k) for k in ('baslik', 'oz')} }")
        ekle("H2 ozsuz `[[slug]]` -> description",
             k2.get("mem:feedback_wiki-ozsuz-ders.md", {}).get("oz", "").startswith("Wiki ozsuz dersin"))
        ekle("H3 hub dosyalari ve MEMORY.md ders KAYDI DEGIL",
             not any(i.startswith("_indeks-") or i == "MEMORY.md" for i in ids2), f"ids={sorted(ids2)}")
        ekle("H4 iki kaynakta gecen ders TEK kayit, MEMORY.md satir ozu kazanir",
             k2.get("mem:feedback_kok.md", {}).get("oz") == "kok indeksteki ozet kazanir",
             f"oz={k2.get('mem:feedback_kok.md', {}).get('oz')}")
        md = k2.get("mem:feedback_md-hub.md", {})
        ekle("H5 hub'daki ozsuz ⭐ `[Baslik](dosya)` -> baslik linkten, oz description'dan",
             md.get("baslik") == "Md linkli hub dersi" and md.get("oz", "").startswith("Md linkli hub"),
             f"kayit={ {k: md.get(k) for k in ('baslik', 'oz')} }")
        ca = k2.get("mem:feedback_coklu-a.md", {})
        ekle("H6 coklu linkli satirda oz SONRAKI LINKTE kesilir (satir-ici kirlenme yok)",
             ca.get("oz") == "coklu satirin ilk ozeti" and "mem:feedback_coklu-b.md" in k2,
             f"coklu-a oz={ca.get('oz')!r}")
        ekle("H7 baslikta ic koseli parantez (`[OK]`) linki bozmaz",
             k2.get("mem:feedback_ic-koseli.md", {}).get("baslik", "").startswith('Push "[OK]"'),
             f"baslik={k2.get('mem:feedback_ic-koseli.md', {}).get('baslik')!r}")
        ekle("H8 DUZYAZI satirindaki `[[a]] · [[b]]` linkleri indeksli sayilir",
             {"feedback_duzyazi-a.md", "feedback_duzyazi-b.md"} <= ids2)
        ekle("H9 yetim: description VARSA kayit, YOKSA kayit yok; CLI `hub=2, yetim=1`",
             "feedback_yetim.md" in ids2 and "feedback_yetim-descsiz.md" not in ids2
             and "hub=2" in cikti2 and "yetim=1" in cikti2, cikti2.strip()[:200])
        ekle("H10 kayit kumesi TAM beklenen 10 ders",
             ids2 == S2_BEKLENEN, f"fazla={sorted(ids2 - S2_BEKLENEN)} eksik={sorted(S2_BEKLENEN - ids2)}")
        ekle("H11 `anahtar` formulu wiki kaydinda da aynen", formul_ok(w))
        idx2 = proj2 / ".tmp" / "recall-index.json"
        ekle("D1 indeks mtime'i kaynak damgasina cekilir (gelecege damgali kaynak -> sonsuz bayatlik YOK)",
             idx2.is_file() and idx2.stat().st_mtime >= gelecek - 1,
             f"idx={idx2.stat().st_mtime if idx2.is_file() else None} kaynak={gelecek}")
        yardim = tmp / "proje_yardim"
        yardim.mkdir()
        rc_h, out_h, _ = cli(yardim, "--help")
        ekle("A1 `--help` -> exit 0, indeks URETILMEZ",
             rc_h == 0 and not (yardim / ".tmp" / "recall-index.json").exists(), f"exit={rc_h}")
        rc_z, _, _ = cli(yardim, "--zirva-bayrak")
        ekle("A2 bilinmeyen bayrak -> exit != 0, indeks URETILMEZ",
             rc_z != 0 and not (yardim / ".tmp" / "recall-index.json").exists(), f"exit={rc_z}")

        # ======================= SAHNE 3 (hook tazeleme) =================================
        proj3 = tmp / "proje3"
        pb = proj3 / "core" / "playbook"
        pb.mkdir(parents=True)
        (pb / "lessons-learned.md").write_text(S3_LESSONS, encoding="utf-8")
        (pb / "howto-ornek.md").write_text(S3_HOWTO, encoding="utf-8")
        mem3 = Path(auto_memory_dizini(proj3))
        _yaz(mem3, S3_DOSYALAR)
        t3 = proj3 / ".tmp"
        idx3, st3, kilit3 = t3 / "recall-index.json", t3 / "recall-index.status", t3 / "recall-index.lock"

        def hook_kos(prompt, via=None):
            cmd = [sys.executable, str(hook)] if via is None else [sys.executable, str(via), str(hook)]
            p = subprocess.run(cmd, input=json.dumps({"prompt": prompt}).encode("utf-8"),
                               env=ortam(proj3), cwd=str(proj3), capture_output=True, timeout=120)
            return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")

        def ctx(out):
            try:
                return json.loads(out)["hookSpecificOutput"]["additionalContext"]
            except Exception:
                return None

        def status():
            try:
                return json.loads(st3.read_text(encoding="utf-8"))
            except Exception:
                return {}

        def kalinti():
            return sorted(p.name for p in t3.glob("*.tmp")) if t3.is_dir() else []

        # T7 kisa prompt: maliyet sifir, indeks uretilmez
        rc, out, _ = hook_kos(PROMPT_KISA)
        ekle("T7 kisa prompt -> indeks URETILMEZ, cikti yok",
             rc == 0 and out.strip() == "" and not idx3.exists())

        # T1 indeks YOK -> ayni prompt'ta uretilir ve enjekte edilir
        rc, out, err = hook_kos(PROMPT_ZEPLIN)
        c = ctx(out)
        ekle("T1 indeks YOK -> AYNI prompt'ta uretilir + enjeksiyon",
             rc == 0 and idx3.is_file() and c is not None and "zeplin" in c,
             f"rc={rc} out={out[:160]!r} err={err[:160]!r}")
        s = status()
        ekle("T1b status: tetik=YOK sonuc=OK + kayit sayisi + zaman",
             s.get("tetik") == "YOK" and s.get("sonuc") == "OK" and s.get("kayit", 0) >= 3
             and s.get("pattern") == 1 and s.get("howto") == 1 and "zaman" in s, f"status={s}")
        ekle("T10 stdout YALNIZ hook JSON'u (uretec ciktisi sizmaz)",
             c is not None and out.strip().count("\n") == 0, f"out={out[:200]!r}")
        ekle("T1c kilit ve gecici dosya kalintisi YOK",
             not kilit3.exists() and not kalinti(), f"kalinti={kalinti()}")

        # ⛔ Buradan sonra dosya erisimleri _ns/_oku/_sil ile: mutasyon (ya da eski kod) bir
        # dosyayi HIC uretmezse korpus COKMEMELI, vektoru FAIL olarak OLCMELI (ilk kurulumda
        # `--mutasyon-tazeleme-yok` ve 8e8feef kosumu FileNotFoundError ile oluyordu).
        def _ns(p):
            try:
                return p.stat().st_mtime_ns
            except OSError:
                return None

        def _oku(p):
            try:
                return p.read_text(encoding="utf-8")
            except OSError:
                return None

        def _sil(p):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)

        # T3 taze -> yeniden uretim yok (indeks mtime + status degismez)
        idx_m, st_ic = _ns(idx3), _oku(st3)
        time.sleep(0.05)
        rc, out, _ = hook_kos(PROMPT_ZEPLIN)
        ekle("T3 taze indeks -> YENIDEN URETILMEZ (mtime + status ayni)",
             rc == 0 and idx_m is not None and _ns(idx3) == idx_m and st_ic is not None
             and _oku(st3) == st_ic and ctx(out) is not None)

        # T2 BAYAT (memory) -> yeni ders ayni prompt'ta gorunur
        yeni = time.time() + 30
        (mem3 / "feedback_balon-yuk-dengesi.md").write_text(_fm("balon", "Balon yuk dengesi dersi"),
                                                            encoding="utf-8")
        with open(mem3 / "_indeks-h.md", "a", encoding="utf-8") as f:
            f.write("- [[feedback_balon-yuk-dengesi]] — balon yuk dengesi hesaplama notu\n")
        for pth in (mem3 / "feedback_balon-yuk-dengesi.md", mem3 / "_indeks-h.md"):
            os.utime(pth, (yeni, yeni))
        rc, out, _ = hook_kos(PROMPT_BALON)
        c = ctx(out)
        ekle("T2 BAYAT (memory degisti) -> tazelenir, yeni ders AYNI prompt'ta enjekte",
             rc == 0 and c is not None and "balon" in c and status().get("tetik") == "BAYAT",
             f"out={out[:160]!r} status={status()}")

        # T2b BAYAT (lessons-learned) -> yeni PATTERN indekse girer
        yeni2 = time.time() + 60
        with open(pb / "lessons-learned.md", "a", encoding="utf-8") as f:
            f.write("\n## PATTERN #2: Ikinci desen basligi\n\nikinci desenin ozeti\n")
        os.utime(pb / "lessons-learned.md", (yeni2, yeni2))
        hook_kos(PROMPT_ZEPLIN)
        ids3 = {k["id"] for k in json.loads(idx3.read_text(encoding="utf-8"))["kayit"]} if idx3.is_file() else set()
        ekle("T2b lessons-learned degisti -> PATTERN #2 indekste (PATTERN/howto korunur)",
             {"pat:PATTERN #1", "pat:PATTERN #2", "how:howto-ornek.md"} <= ids3, f"ids={sorted(ids3)}")

        # T4 CANLI kilit + BAYAT indeks -> tazeleme ATLANIR, eski indeks hizmet eder, kilit dokunulmaz
        idx_m = _ns(idx3)
        yeni3 = time.time() + 90
        os.utime(mem3 / "feedback_zeplin-kargo-rotasi.md", (yeni3, yeni3))
        t3.mkdir(parents=True, exist_ok=True)
        kilit3.write_text("baska-oturum", encoding="utf-8")
        rc, out, _ = hook_kos(PROMPT_ZEPLIN)
        ekle("T4 canli kilit + bayat indeks -> URETIM YOK, eski indeksle enjeksiyon, kilit yerinde",
             rc == 0 and idx_m is not None and _ns(idx3) == idx_m and ctx(out) is not None
             and kilit3.exists(),
             f"rc={rc} idx_once={idx_m} idx_sonra={_ns(idx3)} kilit={kilit3.exists()}")

        # T4b CANLI kilit + indeks YOK -> eski davranis: sessiz exit 0
        _sil(idx3)
        if not kilit3.exists():
            kilit3.write_text("baska-oturum", encoding="utf-8")   # T4 bir mutasyonda kilidi sildiyse
        rc, out, err = hook_kos(PROMPT_ZEPLIN)
        ekle("T4b canli kilit + indeks YOK -> sessiz exit 0, cikti yok, indeks uretilmez",
             rc == 0 and out.strip() == "" and not idx3.exists(), f"out={out[:120]!r} err={err[:120]!r}")

        # T5 OLU kilit (eski mtime) -> temizlenir, uretim yapilir
        _sil(idx3)
        if not kilit3.exists():
            kilit3.write_text("olu-oturum", encoding="utf-8")
        eski = time.time() - 120
        os.utime(kilit3, (eski, eski))
        rc, out, _ = hook_kos(PROMPT_ZEPLIN)
        ekle("T5 olu kilit -> kaldirilir + indeks uretilir",
             rc == 0 and idx3.is_file() and not kilit3.exists() and ctx(out) is not None,
             f"idx={idx3.is_file()} kilit={kilit3.exists()}")

        # T6 uretim HATASI -> fail-open + status HATA + stderr; additionalContext'e gurultu yok
        _sil(idx3)
        _sil(kilit3)
        idx3.mkdir()
        rc, out, err = hook_kos(PROMPT_ZEPLIN)
        s = status()
        ekle("T6 tazeleme hatasi -> exit 0, stdout bos, status HATA+hata metni, stderr notu",
             rc == 0 and out.strip() == "" and s.get("sonuc") == "HATA" and s.get("hata")
             and "RECALL-INDEX-TAZELENEMEDI" in err and not kilit3.exists() and not kalinti(),
             f"rc={rc} out={out[:80]!r} status={s} err={err[:160]!r} kalinti={kalinti()}")
        idx3.rmdir()

        # T9 hook_shim esligi: runpy.run_path + sys.path[0] proje koku DEGIL
        shim = tmp / "shim" / "hook_shim_es.py"
        shim.parent.mkdir()
        shim.write_text("import runpy, sys\nh = sys.argv[1]\nsys.argv = [h]\n"
                        "runpy.run_path(h, run_name='__main__')\n", encoding="utf-8")
        rc, out, err = hook_kos(PROMPT_ZEPLIN, via=shim)
        ekle("T9 runpy (hook_shim) ortaminda da uretim + enjeksiyon",
             rc == 0 and idx3.is_file() and ctx(out) is not None, f"rc={rc} err={err[:200]!r}")

        # T8 ESZAMANLI 6 surec, indeks YOK -> hepsi exit 0, gecerli JSON, kalinti yok
        _sil(idx3)
        _sil(kilit3)
        ps = [subprocess.Popen([sys.executable, str(hook)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=ortam(proj3), cwd=str(proj3)) for _ in range(6)]
        for p in ps:
            p.stdin.write(json.dumps({"prompt": PROMPT_ZEPLIN}).encode("utf-8"))
            p.stdin.close()
        cikis = []
        for p in ps:
            o = p.stdout.read().decode("utf-8", "replace")
            p.wait(timeout=120)
            cikis.append((p.returncode, o))
        gecerli_json = True
        try:
            json.loads(idx3.read_text(encoding="utf-8"))
        except Exception:
            gecerli_json = False
        ekle("T8 6 eszamanli surec -> hepsi exit 0, stdout bos|gecerli JSON, indeks gecerli, kalinti yok",
             all(r == 0 and (o.strip() == "" or ctx(o) is not None) for r, o in cikis)
             and gecerli_json and not kilit3.exists() and not kalinti(),
             f"rc={[r for r, _ in cikis]} json={gecerli_json} kilit={kilit3.exists()} kalinti={kalinti()}")

    finally:
        if mutant is not None:
            try:
                mutant.unlink()
            except Exception:
                pass
            print(f"[kalinti-kontrolu] mutant dosya duruyor mu: "
                  f"{'EVET -- TEMIZLIK BASARISIZ' if mutant.exists() else 'hayir'}")
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for _a, k, _c in sonuc if k)
    for ad, k, ac in sonuc:
        print(f"  [{'PASS' if k else 'FAIL'}] {ad}" + (f"  ({ac})" if ac and not k else ""))
    print(f"\nrecall_index_ozetsiz: {gecen}/{len(sonuc)}")
    if secili:
        print(f"  (MUTASYON {secili[0]} — dusmesi BEKLENEN vektorler var; "
              f"tam skor 'mutasyon KACTI' demektir)")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
