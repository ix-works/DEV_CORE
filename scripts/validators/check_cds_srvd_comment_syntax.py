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

KAPSAM (desen dar, UZANTI ailesi tam):
  - CDS DDL kaynagi (`.cds`, `.ddls`, `.asddls`, `.ddl`): yalniz KOD satirinda `"`.
    Tek-tirnakli literaller ve `//` yorum govdeleri ONCE cikarilir; `/* */` blok
    yorumlari da cikarilir. (Uzanti ailesi 2026-08-28'de tamamlandi — bkz.
    `_CDS_UZANTILARI` yanindaki B2-10 notu; onceden yalniz `.cds` taraniyordu ve
    tuketici projede 41 DDL kaynagi HIC gorulmuyordu.)
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
# K1 (2026-08-20): ORTAK kapsam sozlesmesi — 'ihlal yok' ile 'bakacak dosya yok'
# ayrilir. 0 dosya FAIL URETMEZ (mesru olabilir), ama SESSIZ de gecmez.
from utils.kapsam import Kapsam  # noqa: E402

KAPSAM = Kapsam('CDS-DDL/.srvd')   # K1: taranan dosya sayaci

# ── UZANTI KAPSAMI (B2-10, 2026-08-28) ──────────────────────────────────────────
# `.cds` TEK BASINA yazilmisti; oysa ayni DDL kaynagi repoda UC uzantiyla yasiyor
# (`source_drift._TYPE_TO_EXTENSIONS`: table/structure -> `.asddls/.ddls/.cds`).
# CANLI OLCUM 2026-08-28 (tuketici proje): ayni icerik `.cds`'te `1 ihlal`,
# `.ddls.asddls`'te "temiz" -> **28 .asddls + 1 .ddls + 12 .ddl dosya HIC
# TARANMIYORDU**. Bu LATENT degil CANLI bir kapsam bosluguydu.
# BE-61 kurali dile baglidir ("CDS DDL'de `\"` yorum DEGILDIR"), DOSYA ADINA degil.
# ⚠ KAPSAMA ALINMAYANLAR (olculdu, bilincli): `.dcl` (3 dosya) ve `.bdef` (32 dosya)
#    -> ikisi de tara_cds ile 0 bulgu verdi (FP yok) ama AYRI artefakt siniflaridir
#    (DCL access-control, BDEF davranis tanimi; BDEF'in kendi kapisi var:
#    check_bdef_backtick). Kapsam genisletmesi KARARDIR; kanit raporda, karar liderde.
_CDS_UZANTILARI = (".cds", ".ddls", ".asddls", ".ddl")
_TARANAN_UZANTILAR = _CDS_UZANTILARI + (".srvd",)

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
        # T1.9 (2026-07-31): rglob node_modules/dist ağaçlarını da yürüyordu (UI app'leri)
        # → prune'lu walk. Ölçüm: aynı dosya kümesi, 1,38s → 0,06s.
        files = []
        import os as _os
        for _r, _ds, _fs in _os.walk(kok):
            _ds[:] = [d for d in _ds if d not in ("node_modules", ".git", "dist", "coverage")]
            files += [Path(_r) / f for f in _fs if f.lower().endswith(_TARANAN_UZANTILAR)]

    toplam = 0
    for f in KAPSAM.say(files):
        sfx = f.suffix.lower()
        if sfx not in _TARANAN_UZANTILAR:
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        hits = tara_cds(txt) if sfx in _CDS_UZANTILARI else tara_srvd(txt)
        for ln, icerik, sebep in hits:
            toplam += 1
            rel = f.relative_to(root) if str(f).startswith(str(root)) else f
            print(f"[İHLAL] {rel}:{ln}  {sebep}\n         → {icerik}")

    if toplam:
        print(f"\n{toplam} ihlal — YANLIS KATMAN yorumu. Bu hata sinifi SESSIZDIR: "
              f"run_review/abaplint/run_all_validators/adt_syntax_check ve push'un "
              f"'[OK] activated' mesaji BUNU GORMEZ. Kanit = readback esitligi.")
        return 1

    print("CDS/SRVD yorum sozdizimi: temiz." + KAPSAM.ek())
    return 0


if __name__ == "__main__":
    sys.exit(main())
