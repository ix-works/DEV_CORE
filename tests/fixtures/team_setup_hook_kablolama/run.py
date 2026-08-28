#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E-05 — overlay ONAY KAPISI git-hook kablolamasini DURDURMAMALI.

KUSUR (2026-08-01 bug-avi, `E-05`; 2026-08-28'de duzeltildi):
`team_setup.main()` icinde `if not junctions(...): return 1` vardi. `junctions()`
overlay farki ONAY BEKLIYORSA da False doner (`claude_overlay.materyalize`:
*"FARK VAR - onaysiz ezme YOK (T2.5)"*) - yani TAMAMEN NORMAL bir onay kapisi.
Sonuc: kendisiyle ilgisi olmayan dort adim SESSIZCE dusuyordu:

    dosya_tamamla · hookspath_core · hookspath_proje · _core_index_yenile

`hookspath_proje` PROJE reposunun `core.hooksPath`ini set eder; set edilmezse git
`scripts/git-hooks/pre-commit`i **ASLA calistirmaz** => yeni klonda pre-commit
gate'leri KURULMAMIS olur ve bunu hicbir sey soylemez ("kod != kablolama"; ayni sinif
`hookspath_proje` docstring'inde zaten belgeli).

UC AYAK:
  KIRMIZI - taban surum (`git show HEAD:`) + onay bekleyen overlay -> hooksPath SET DEGIL
  YESIL   - duzeltilmis surum + AYNI kosul            -> hooksPath SET (rc HALA 1)
  POZITIF - overlay YOKken normal kurulum akisi BOZULMADI (her iki surumde de rc=0
  KONTROL   ve hooksPath set) => fix "hatayi yutarak" calismiyor.

⛔ Bu korpus SAP'ye baglanmaz, ag kullanmaz. Sandbox proje temp dizindedir.

Kosum:
    python tests/fixtures/team_setup_hook_kablolama/run.py
    python tests/fixtures/team_setup_hook_kablolama/run.py --mutasyon-erken-donus
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

CORE = Path(__file__).resolve().parents[3]
TS = CORE / "scripts" / "team_setup.py"
TABAN_AD = "_zz_taban_team_setup.py"   # gecici; finally'de SILINIR

SONUC: list[tuple[bool, str]] = []

# E-05 fix'inin CAPASI: `junctions()` FALSE dondugunde erken `return 1` YOKTUR
# (kablolama adimlari yine kosar). Taban/mutasyon bu capayi SOKER.
_E05_CAPA = ("    kurulum_ok = junctions(proje, overlay_onayli=a.overlay_onayli)\n"
             "    if not kurulum_ok:\n")


def _fix_sok(kaynak: str, nicin: str) -> str:
    """Guncel team_setup.py'den E-05 fix'ini SOK (erken `return 1` geri gelir).

    ⛔ Zamandan bagimsiz: girdi calisma agacindaki GUNCEL dosyadir, git gecmisi DEGIL.
    Capa bulunamazsa GURULTULU dur — sessizce 'taban == fix' durumuna dusmek, kirmizi
    ayagi olu birakir (tam olarak 2026-08-28 regresyonu).
    """
    if _E05_CAPA not in kaynak:
        raise SystemExit(
            f"TABAN URETILEMEDI ({nicin}): E-05 capasi (`kurulum_ok` kontrolu) "
            f"team_setup.py icinde bulunamadi. Fix'in yazimi degismis => uretilen "
            f"'taban' ARTIK kusuru uretmiyor olabilir. _E05_CAPA'yi GUNCELLE.")
    return kaynak.replace(
        _E05_CAPA,
        "    kurulum_ok = junctions(proje, overlay_onayli=a.overlay_onayli)\n"
        "    if not kurulum_ok:\n"
        "        return 1  # TABAN/MUTASYON: E-05 oncesi erken donus geri kondu\n"
        "    if not kurulum_ok:\n", 1)


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((kosul, ad))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if detay else ""))


def sandbox_proje(kok: Path, overlay: bool, etiket: str) -> Path:
    """Sahte proje: git reposu + pre-commit dosyasi (+ istege bagli ONAY BEKLEYEN overlay)."""
    p = kok / f"proje_{etiket}"
    (p / "scripts" / "git-hooks").mkdir(parents=True)
    (p / "scripts" / "git-hooks" / "pre-commit").write_text(
        "#!/bin/sh\nexit 0\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "init", "-q", str(p)], check=True, capture_output=True)
    # commit sart degil; hookspath_proje yalniz `.git` varligina ve dosyaya bakar.

    if overlay:
        # `claude-local/agents/*.md` => overlay VAR. Ayrica `.claude/agents` GERCEK dizin
        # ve icerigi uretilecekten FARKLI => `fark_raporu` dolu => materyalize onaysiz
        # URETMEZ => junctions() False. Bu bir HATA DEGIL, ONAY KAPISIDIR.
        (p / "claude-local" / "agents").mkdir(parents=True)
        (p / "claude-local" / "agents" / "zz-deney.md").write_text(
            "---\nname: zz-deney\ndescription: fixture overlay\n---\n\ngovde\n",
            encoding="utf-8", newline="\n")
        (p / ".claude" / "agents").mkdir(parents=True)
        (p / ".claude" / "agents" / "zz-deney.md").write_text(
            "ESKI VE FARKLI ICERIK — fark_raporu bunu yakalar\n",
            encoding="utf-8", newline="\n")
    return p


def kos(script: Path, proje: Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, str(script), "--project", str(proje),
         "--no-install", "--no-plugins", "--no-seed", "--no-smoke"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=300, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def hookspath(proje: Path) -> str:
    r = subprocess.run(["git", "-C", str(proje), "config", "--local", "core.hooksPath"],
                       capture_output=True, text=True)
    return (r.stdout or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon-erken-donus", action="store_true",
                    help="fix'i SOK: erken `return 1`u geri getir (taban davranis)")
    a = ap.parse_args()

    print(__doc__.strip().splitlines()[0])
    print(f"MOD: {'MUTASYON --erken-donus' if a.mutasyon_erken_donus else 'NORMAL'}\n")

    taban_yol = CORE / "scripts" / TABAN_AD
    tmpdir = tempfile.mkdtemp(prefix="ix_e05_")
    try:
        tmp = Path(tmpdir)

        # ── TABAN (KIRMIZI ayak) — KAYNAKTAN TURETILIR, REPO DURUMUNDAN DEGIL ──
        # ⛔ `git show HEAD:` KULLANILMAZ (2026-08-28'de main'i kirdi): fix merge
        #    edilince HEAD *fix*'i icerir => taban = fix => kirmizi ayak yesile doner.
        # ✅ Guncel `team_setup.py` kopyalanir ve E-05 fix'i SOKULUR: `kurulum_ok`
        #    kontrolune erken `return 1` geri konur = duzeltme oncesi davranis.
        #    (Dosya CORE/scripts/ icine yazilir cunku `CORE_ROOT = __file__/../..`;
        #     temp dizinde CORE_ROOT yanlis cozulurdu. `finally` blogu SILER.)
        taban_yol.write_text(_fix_sok(TS.read_text(encoding="utf-8"), "taban"),
                             encoding="utf-8", newline="")

        # ── kosulacak "fix" surumu (mutasyonluysa erken donus geri gelir) ───────
        fix_yol = TS
        mut_yol = CORE / "scripts" / "_zz_mut_team_setup.py"
        if a.mutasyon_erken_donus:
            mut_yol.write_text(_fix_sok(TS.read_text(encoding="utf-8"), "mutasyon"),
                               encoding="utf-8", newline="")
            fix_yol = mut_yol

        # ══ KIRMIZI ════════════════════════════════════════════════════════════
        print("-- KIRMIZI: taban surum + ONAY BEKLEYEN overlay --")
        p1 = sandbox_proje(tmp, overlay=True, etiket="r1_taban")
        rc, cikti = kos(taban_yol, p1)
        hp = hookspath(p1)
        kontrol("R1 taban: overlay onay bekliyor -> rc=1", rc == 1, f"rc={rc}")
        kontrol("R1b taban: git-hook kablolamasi HIC YAPILMADI (hooksPath BOS)",
                hp == "", f"hooksPath={hp!r}")

        # ══ YESIL ══════════════════════════════════════════════════════════════
        print("\n-- YESIL: duzeltilmis surum + AYNI kosul --")
        p2 = sandbox_proje(tmp, overlay=True, etiket="v1_fix")
        rc2, cikti2 = kos(fix_yol, p2)
        hp2 = hookspath(p2)
        kontrol("V1 fix: git-hook kablolamasi YAPILDI (pre-commit artik canli)",
                hp2 == "scripts/git-hooks", f"hooksPath={hp2!r}")
        kontrol("V1b fix: HATA YUTULMADI — kurulum yine BASARISIZ (rc=1)",
                rc2 == 1, f"rc={rc2}")
        kontrol("V1c fix: onay kapisi hala ISLIYOR (overlay onaysiz EZILMEDI)",
                (p2 / ".claude" / "agents" / "zz-deney.md").read_text(
                    encoding="utf-8").startswith("ESKI VE FARKLI"),
                "overlay dosyasi degismemis olmali")

        # ══ POZITIF KONTROL — normal akis bozulmadi mi? ════════════════════════
        print("\n-- POZITIF KONTROL: overlay YOK, normal kurulum akisi --")
        p3 = sandbox_proje(tmp, overlay=False, etiket="p1_taban")
        rc3, cikti3 = kos(taban_yol, p3)
        hp3 = hookspath(p3)
        p4 = sandbox_proje(tmp, overlay=False, etiket="p2_fix")
        rc4, cikti4 = kos(fix_yol, p4)
        hp4 = hookspath(p4)
        kontrol("P1 taban: overlaysiz kurulum rc=0 + hooksPath set",
                rc3 == 0 and hp3 == "scripts/git-hooks", f"rc={rc3} hooksPath={hp3!r}")
        kontrol("P2 fix: overlaysiz kurulum AYNI sonuc (rc + hooksPath BIREBIR)",
                rc4 == rc3 and hp4 == hp3, f"rc={rc4} hooksPath={hp4!r}")
        kontrol("P3 fix normal akista CORE-INDEX adimina da ULASIYOR",
                "CORE-INDEX" in cikti4, "cikti CORE-INDEX satiri icermeli")

        # ══ 3. BAGLAM — git reposu OLMAYAN proje (repo_mode=none) ══════════════
        print("\n-- 3. BAGLAM: git reposu olmayan proje --")
        p5 = tmp / "proje_gitsiz"
        (p5 / "scripts" / "git-hooks").mkdir(parents=True)
        (p5 / "scripts" / "git-hooks" / "pre-commit").write_text(
            "#!/bin/sh\nexit 0\n", encoding="utf-8", newline="\n")
        rc5, cikti5 = kos(fix_yol, p5)
        kontrol("V2 gitsiz proje: cokmez, uyari verir (repo_mode=none dali)",
                rc5 in (0, 1) and "pre-commit kablolamas" in cikti5,
                f"rc={rc5}")
    finally:
        for y in (taban_yol, CORE / "scripts" / "_zz_mut_team_setup.py"):
            try:
                y.unlink()
            except FileNotFoundError:
                pass
        shutil.rmtree(tmpdir, ignore_errors=True)

    gecen = sum(1 for ok, _ in SONUC if ok)
    print(f"\n{'=' * 62}\nSONUC: {gecen}/{len(SONUC)}")
    if gecen != len(SONUC):
        print("Dusen: " + ", ".join(ad for ok, ad in SONUC if not ok))
    if a.mutasyon_erken_donus:
        print("(MUTASYON: dusus BEKLENIR)")
        return 0
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    raise SystemExit(main())
