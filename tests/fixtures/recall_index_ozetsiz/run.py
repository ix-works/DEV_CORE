#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RECALL-INDEX: ozet-cumlesi OLMAYAN memory satirlari GORUNMEZ idi (2026-08-21).

NEDEN BU KORPUS VAR
-------------------
`build_recall_index.memory_kayitlari()` YALNIZ `- [Baslik](dosya) — ozet` seklindeki
satirlari goruyordu. Canli olcum (auto-memory, 2026-08-21):
    MEMORY.md indeks satiri 147 · indekse giren 90 · **GORUNMEYEN 57**
Bu SESSIZ bir kayipti: uretec "[OK] 90 kayit" diyordu, eksik 57'yi kimse bildirmiyordu
("0 kayit" ile "0 eslesme" ayni cikti). Ozet-cumlesi ELLE yazilan bir alandir ve
unutulur; `description:` memory yazim sozlesmesinin ZORUNLU alanidir (214 dosyanin
213'unde var) => dogru geri-dusus kaynagi odur.

⭐ SINIF, VAKA DEGIL: kuyruk kaydi dar deseni (`^- \\[`) isaret ediyordu; olcum kapsamin
DAHA GENIS oldugunu gosterdi — canli indekste en degerli dersler `- ⭐ [Baslik](dosya)`
ve `- ⛔ [...]` seklinde yaziliyor ve dar desen onlarin HICBIRINI gormuyordu (9 satirin
4'u yildizli). Fix sinifi kapatir: "liste satirindaki HER memory linki".

⛔ SKORLAMA DAVRANISI DEGISMEDI: `anahtar = tokenle(baslik)*3 + tokenle(oz)` formulu
AYNEN korunur (vektor C3 bunu her iki kayit turu icin civiller) ve mevcut 90 kaydin
ciktisi BAYT-ES kalir (vektor C1/C2).

KOSUM:  python tests/fixtures/recall_index_ozetsiz/run.py
        ... --mutasyon-geridusus-yok   (fix'in SOKUMU: description'a dusme kaldirilir)
        ... --mutasyon-dar-desen       (geri-dusus var ama YALNIZ `^- [` -> yildizli kacar)
        ... --mutasyon-uydur           (GEVSETME yonu: description YOKKEN de kayit uret)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi)

⚠ UC MUTASYON, HICBIRI DIGERINI KAPSAMAZ: biri geri-dusus VARLIGINI, biri KAPSAMINI,
  biri de "kaynak yoksa UYDURMA" degismezini sinar.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
URETEC = REPO / "scripts" / "build_recall_index.py"

MUTLAR = {
    # fix'in SOKUMU
    "--mutasyon-geridusus-yok": (
        '        if not _LISTE_SATIRI.match(satir):',
        '        if True:  # MUTASYON: geri-dusus tumden sokuldu\n            continue\n'
        '        if not _LISTE_SATIRI.match(satir):'),
    # KAPSAM daraltmasi: yildizli/isaretli satirlar yine kacar
    "--mutasyon-dar-desen": (
        '        if not _LISTE_SATIRI.match(satir):',
        '        if not re.match(r"^- \\[", satir):  # MUTASYON: dar desen geri geldi'),
    # GEVSETME yonu: kaynak yokken kayit UYDUR
    "--mutasyon-uydur": (
        '            if not oz:\n                continue',
        '            if not oz:\n                oz = baslik  # MUTASYON: kaynak yokken uydur'),
    # SATIR-ATLAMALI KIRLENME geri gelir (eski `\s*` davranisi).
    # ⚠ Yorum EKLEME: yer-tutucu bir CAGRI ARGUMANININ ortasindadir; `#` koyulursa satirin
    # kalani yorum olur ve `(` kapanmaz -> mutant SYNTAX ERROR verir. O zaman olculen sey
    # "mutasyon kacti" degil "mutasyon KURULAMADI"dir (ucuncu deger; ilk denemede yasandi).
    "--mutasyon-satirasan": (
        r'r"^- \[([^\]]+)\]\(([^)]+)\)[ \t]*[—-][ \t]*(.+)$"',
        r'r"^- \[([^\]]+)\]\(([^)]+)\)\s*[—-]\s*(.+)$"'),
}

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

DOSYALAR = {
    "feedback_ozetli.md": ("---\nname: ozetli\ndescription: BU DESCRIPTION KULLANILMAMALI"
                           " cunku satirda ozet var\nmetadata:\n  type: feedback\n---\n\ngovde\n"),
    "feedback_ozetsiz.md": ("---\nname: ozetsiz\ndescription: Ozetsiz dersin frontmatter"
                            " aciklamasi burada yasar\nmetadata:\n  type: feedback\n---\n\ngovde\n"),
    "feedback_yildizli.md": ("---\nname: yildizli\ndescription: Yildizli dersin aciklamasi"
                             " kritik oneme sahiptir\nmetadata:\n  type: feedback\n---\n\ngovde\n"),
    "feedback_isaretli.md": ("---\nname: isaretli\ndescription: Isaretli ve kalin yazilmis"
                             " dersin aciklamasi\nmetadata:\n  type: feedback\n---\n\ngovde\n"),
    "feedback_cifta.md": ("---\nname: cifta\ndescription: Ciftli satirin birinci linki"
                          "\nmetadata:\n  type: feedback\n---\n\ngovde\n"),
    "feedback_ciftb.md": ("---\nname: ciftb\ndescription: Ciftli satirin ikinci linki"
                          "\nmetadata:\n  type: feedback\n---\n\ngovde\n"),
    "feedback_fmsiz.md": "Bu dosyada frontmatter HIC YOK.\n\nGovde dogrudan basliyor.\n",
    "feedback_descsiz.md": ("---\nname: descsiz\nmetadata:\n  type: feedback\n---\n\n"
                            "description alani YOK.\n"),
    "project_gruplu.md": ("---\nname: gruplu\ndescription: Gruplu referans satirindaki"
                          " dersin aciklamasi\nmetadata:\n  type: project\n---\n\ngovde\n"),
    # feedback_yok.md BILEREK YAZILMAZ (diskte olmayan dosya vektoru)
}


def main() -> int:
    # BILINMEYEN KIP SESSIZCE YESIL GECMESIN (2026-08-22): `--mutasyon-ZIRVA` gibi bir
    # yazim hatasi `secili` bos biraktigi icin HIC mutasyon kurmadan TAM PUAN uretiyordu
    # (exit 0) -- yani "mutasyon yakalandi" sanilan sonuc aslinda mutasyonsuz kosumdu.
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in MUTLAR:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(MUTLAR)))

    secili = [a for a in sys.argv[1:] if a in MUTLAR]
    uretec = URETEC
    mutant = None
    if secili:
        kaynak = URETEC.read_text(encoding="utf-8")
        eski, yeni = MUTLAR[secili[0]]
        if eski not in kaynak:
            print(f"[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi ({secili[0]}) -> "
                  "mutasyon uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        mutant = URETEC.with_name("_mutant_build_recall_index.py")
        mutant.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8")
        # ⛔ KURULAMADI != KACTI (ucuncu deger): sozdizimi bozuk bir mutant kosMAZ; o zaman
        # "mutasyon yakalandi/kacti" hukmu ANLAMSIZDIR. Once mutantIN GECERLI oldugunu
        # kanitla. (Bu kontrol yokken --mutasyon-satirasan sessizce SyntaxError veriyordu.)
        try:
            compile(mutant.read_text(encoding="utf-8"), str(mutant), "exec")
        except SyntaxError as e:
            mutant.unlink(missing_ok=True)
            print(f"[DOGRULANAMADI] mutant SOZDIZIMI BOZUK ({secili[0]}): {e} -> "
                  "olculen sey mutasyon degil, kurulum hatasidir.")
            return 2
        uretec = mutant

    tmp = Path(tempfile.mkdtemp(prefix="recall_ozetsiz_"))
    sonuc: list[tuple[str, bool, str]] = []
    try:
        # --- hermetik sahte ortam: CLAUDE_CONFIG_DIR ile ~/.claude yonlendirilir ----
        proj = tmp / "proje"
        proj.mkdir(parents=True, exist_ok=True)
        cfg = tmp / "claudecfg"
        sys.path.insert(0, str(REPO / "scripts"))
        os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
        from utils.claude_paths import auto_memory_dizini  # noqa: E402
        mem = Path(auto_memory_dizini(proj))
        mem.mkdir(parents=True, exist_ok=True)
        (mem / "MEMORY.md").write_text(MEMORY_MD, encoding="utf-8")
        for ad, ic in DOSYALAR.items():
            (mem / ad).write_text(ic, encoding="utf-8")

        def ekle(ad, kosul, aciklama=""):
            sonuc.append((ad, bool(kosul), aciklama))

        # === UCTAN UCA: gercek CLI (kod != kablolama) ======================
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(proj)
        env["CLAUDE_CONFIG_DIR"] = str(cfg)
        env["PYTHONIOENCODING"] = "utf-8"
        p = subprocess.run([sys.executable, str(uretec)], env=env, cwd=str(proj),
                           capture_output=True, timeout=180)
        cikti = p.stdout.decode("utf-8", "replace")
        hedef = proj / ".tmp" / "recall-index.json"
        ekle("E1 CLI exit 0 + indeks dosyasi uretildi",
             p.returncode == 0 and hedef.is_file(),
             f"exit={p.returncode} stderr={p.stderr.decode('utf-8','replace')[:200]}")
        veri = json.loads(hedef.read_text(encoding="utf-8")) if hedef.is_file() else {"kayit": []}
        kayit = {k["id"]: k for k in veri["kayit"]}
        mem_kayit = {i: k for i, k in kayit.items() if i.startswith("mem:")}

        # === P: GERI DUSUS CALISIYOR ======================================
        ekle("P1 ozetsiz satir INDEKSE GIRER (description'dan)",
             "mem:feedback_ozetsiz.md" in mem_kayit
             and "frontmatter aciklamasi" in mem_kayit.get(
                 "mem:feedback_ozetsiz.md", {}).get("oz", ""),
             "eski kodda bu satir GORUNMEZDI")
        ekle("P2 ⭐ YILDIZLI satir da girer (dar desen bunu kaciriyordu)",
             "mem:feedback_yildizli.md" in mem_kayit
             and mem_kayit.get("mem:feedback_yildizli.md", {}).get("oz", "") != "",
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

        # === N: UYDURMA YASAGI (mutasyon-uydur bunlari KIRAR) =============
        ekle("N1 frontmatter'i OLMAYAN dosya -> kayit YOK",
             "mem:feedback_fmsiz.md" not in mem_kayit,
             "kaynak yoksa kayit da yok; baslik'i `oz` diye kopyalamak UYDURMADIR")
        ekle("N2 `description:` alani olmayan dosya -> kayit YOK",
             "mem:feedback_descsiz.md" not in mem_kayit)
        ekle("N3 diskte OLMAYAN dosya -> kayit YOK, COKME YOK",
             "mem:feedback_yok.md" not in mem_kayit and p.returncode == 0)

        # === C: KONTROL GRUBU — MEVCUT DAVRANIS DEGISMEDI =================
        ozetli = mem_kayit.get("mem:feedback_ozetli.md", {})
        ekle("C1 ozetli satirin `oz`u SATIRDAN gelir (description'dan DEGIL)",
             ozetli.get("oz", "").startswith("bu satirda ozet VAR")
             and "KULLANILMAMALI" not in ozetli.get("oz", ""),
             "geri-dusus mevcut kaynagi EZMEMELI")
        ekle("C2 ozetli kayit mevcut alan sozlesmesini korur",
             set(ozetli) == {"id", "kaynak", "baslik", "oz", "anahtar"}
             and ozetli.get("kaynak") == "memory/feedback_ozetli.md")

        # anahtar formulu HER IKI kayit turunde AYNI olmali (brif sarti)
        sys.path.insert(0, str(REPO / "scripts"))
        import importlib.util
        _s = importlib.util.spec_from_file_location("_bri_t", str(uretec))
        _m = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_m)
        def formul_ok(k):
            return k.get("anahtar") == _m.tokenle(k["baslik"]) * 3 + _m.tokenle(k["oz"])
        ekle("C3 `anahtar` formulu (baslik x3 + oz) IKI TURDE DE aynen korunur",
             formul_ok(ozetli) and formul_ok(mem_kayit["mem:feedback_ozetsiz.md"])
             if "mem:feedback_ozetsiz.md" in mem_kayit else False,
             "skorlama davranisi DEGISMEMELI (yalniz kapsam acildi)")

        ekle("C4 kayit sayisi TAM olarak kaynagi olan 7 ders",
             len(mem_kayit) == 7 and "mem:feedback_ozetli.md" in mem_kayit,
             f"mem kayit sayisi={len(mem_kayit)} (beklenen 7: ozetli+ozetsiz+yildizli+"
             f"isaretli+cifta+ciftb+gruplu; fmsiz/descsiz/yok KAYNAKSIZ = kayit YOK)")

        # ⭐ SATIR-ATLAMALI KIRLENME (2026-08-21'de bu korpus tarafindan bulundu) --------
        # Eski desen `...\)\s*[—-]\s*(.+)$` idi ve `\s` SATIR SONUNU kapsiyordu: ozetsiz bir
        # satir, bir SONRAKI satirin `- ` isaretini ayrac sanip O SATIRIN metnini kendi `oz`u
        # yapiyordu. Yani kayit VARDI ama ozeti BASKA BIR DERSE aitti -> skorlama yanlis
        # derse puan veriyordu. Canli MEMORY.md'de mevcut 90 kaydin **42'si** boyleydi.
        # ⛔ BU VEKTOR SILINEMEZ: kusur sessizdir, yalniz ozetsiz-satirI OLAN bir korpusta
        # gorunur ve eski korpusta oyle bir satir HIC YOKTU.
        kirli = [i for i, k in mem_kayit.items()
                 if "](" in k["oz"] or k["oz"].lstrip().startswith(("-", "⭐", "⛔"))]
        ekle("C6 SATIR-ATLAMALI KIRLENME yok: hicbir `oz` komsu satirin metni degil",
             not kirli, f"kirlenen kayitlar={kirli}")

        ekle("C5 CLI ozet satiri kayit sayisini BASAR (sessiz kayip gorunur olsun)",
             "recall-index:" in cikti and "memory=" in cikti, cikti.strip()[:160])

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
