#!/usr/bin/env python3
"""check_cds_srvd_comment_syntax.py — CDS/SRVD kaynaklarinda YANLIS KATMAN yorumu yakalar.

NEDEN (2026-07-28, ayni gun IKI kez yasandi — ikisi de SESSIZ):

  1. `.cds` icinde ABAP tarzi `"` yorumu. CDS DDL'de yorum `//` ve `/* */`'dir; `"` yorum
     DEGILDIR. SAP kaynagi **sessizce reddeder**: push `[OK] Source uploaded` +
     `[OK] Object activated` der, canli kaynak DEGISMEZ. Yakalayan tek sey readback
     esitligiydi (canli 4163 ch vs yerel 5321 ch).

  2. `.srvd` icinde herhangi bir yorum. SAP: `Comments are not supported and will be
     deleted on save`. Bazen aktivasyon iptal olur (gurultulu, fark edilir), ama NORMAL
     davranis **sessizce silip aktive etmek**tir -> repo canliya gore SAPAR ve kimse
     fark etmez. Kanit: bu kural yokken 3 SRVD aylarca sapik kaldi (repo'da yorum vardi,
     canlida 0 yorum, objeler aktif ve calisiyordu).

NEDEN VALIDATOR (ADR 0019 5 sart):
  1. Hata gercekten yasandi — ayni gun IKI kez.
  2. Sonuc SESSIZ (ikisi de; SRVD'de aylarca birikmis sapma).
  3. Baska katman yakalamiyor — OLCULDU: run_review PASS · abaplint temiz ·
     run_all_validators OK · adt_syntax_check valid:true · push [OK]. BESI DE yesil.
     (adt_syntax_check bu vakada INACTIVE=eski surumu okur -> yeni kaynak hakkinda
     hicbir sey soylemez.)
  4. Dokuman katmani yetersiz kaldi: kural yokken sapma sessizce birikti.
  5. Kullanici acik onayi alindi (2026-07-28).

KAPSAM (dar tutuldu, gurultu yok):
  - `.cds`: yalniz KOD satirinda `"`. Tek-tirnakli literaller ve `//` yorum govdeleri
    ONCE cikarilir; `/* */` blok yorumlari da cikarilir.
  - `.srvd`: `//` veya `/*` (literal disinda).

Kullanim:
    python check_cds_srvd_comment_syntax.py [--file <path>] [--strict]
Cikis: 0 temiz, 1 ihlal.
"""
# ENFORCES: BE-61  (ADR 0019 coverage binding)
import argparse
import io
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import SOURCE_ROOT_NAME, project_root  # K12

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_BLOK_YORUM = re.compile(r"/\*.*?\*/", re.S)
_TEK_TIRNAK = re.compile(r"'[^']*'")


def _kod_kismi(satir: str) -> str:
    """Satirdan literalleri ve `//` yorum govdesini cikarip KOD kismini dondurur."""
    s = _TEK_TIRNAK.sub("''", satir)      # literal icerigi notrle ('a"b' yanlis-pozitif olmasin)
    kesme = s.find("//")
    if kesme >= 0:
        s = s[:kesme]
    return s


def tara_cds(text: str):
    """.cds: KOD satirinda `"` -> ihlal. (yorum/literal disinda)"""
    govde = _BLOK_YORUM.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    hits = []
    for i, raw in enumerate(govde.splitlines(), 1):
        if '"' in _kod_kismi(raw):
            hits.append((i, raw.strip(), 'CDS DDL\'de `"` YORUM DEGILDIR (yorum: // ve /* */). '
                                         'SAP kaynagi SESSIZCE reddeder: push [OK] der, canli kaynak DEGISMEZ.'))
    return hits


def tara_srvd(text: str):
    """.srvd: herhangi bir yorum -> ihlal."""
    hits = []
    blok_icinde = False
    for i, raw in enumerate(text.splitlines(), 1):
        s = _TEK_TIRNAK.sub("''", raw)
        if blok_icinde:
            hits.append((i, raw.strip(), "SRVD yorum DESTEKLEMEZ."))
            if "*/" in s:
                blok_icinde = False
            continue
        if "//" in s or "/*" in s:
            hits.append((i, raw.strip(),
                         "SRVD yorum DESTEKLEMEZ — SAP 'will be deleted on save' der ve "
                         "yorumu SESSIZCE SILER; obje aktive olur ama repo canliya gore SAPAR."))
            if "/*" in s and "*/" not in s:
                blok_icinde = True
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="taranacak dosya (run_review pozisyonel artifact)")
    ap.add_argument("--file")
    ap.add_argument("--strict", action="store_true")
    args, _unknown = ap.parse_known_args()

    root = project_root()
    target = args.file or args.path
    if target:
        files = [Path(target)]
    else:
        kok = root / SOURCE_ROOT_NAME
        files = list(kok.rglob("*.cds")) + list(kok.rglob("*.srvd"))

    toplam = 0
    for f in files:
        sfx = f.suffix.lower()
        if sfx not in (".cds", ".srvd"):
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        hits = tara_cds(txt) if sfx == ".cds" else tara_srvd(txt)
        for ln, icerik, sebep in hits:
            toplam += 1
            rel = f.relative_to(root) if str(f).startswith(str(root)) else f
            print(f"[İHLAL] {rel}:{ln}  {sebep}\n         → {icerik}")

    if toplam:
        print(f"\n{toplam} ihlal — YANLIS KATMAN yorumu. Bu hata sinifi SESSIZDIR: "
              f"run_review/abaplint/run_all_validators/adt_syntax_check ve push'un "
              f"'[OK] activated' mesaji BUNU GORMEZ. Kanit = readback esitligi.")
        return 1

    print("CDS/SRVD yorum sozdizimi: temiz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
