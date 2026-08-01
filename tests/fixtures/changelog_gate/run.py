#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAYIT-2 fixture — pre-commit 4. kontrol: INFRA-CHANGELOG gate.

Neden bu fixture kalici: bu kapi 2026-08-01'de "eklendi + canli test edildi" diye
changelog'a YAZILDI ama kod `reset --hard` ile KAYBOLDU; belge 1 gun boyunca
var-olmayan bir korumayi anlatti (sahte-koruma sinifi). Fixture artik kapinin
VARLIGINI degil DAVRANISINI olcer.

UCUNCU BAGLAM (F3-3): butun senaryolar DEV_CORE'un disinda, tempfile'da acilan
SENTETIK ve AYRI bir git reposunda kosar (farkli proje sekli: profiles/ yok,
blocklist yok, tek governance dosyasi). Ana repolarda `git add/commit` YAPILMAZ.

Kosum: python tests/fixtures/changelog_gate/run.py   (exit 0 = hepsi beklendigi gibi)
Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
GATE = REPO / "scripts" / "git-hooks" / "core_precommit.py"
HOOKS_DIR = REPO / "scripts" / "git-hooks"
CHANGELOG = "governance/infra-changelog.md"

SONUC: list[tuple[bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((kosul, f"{ad}{(' -> ' + detay) if detay else ''}"))


def git(kok: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    e = os.environ.copy()
    e.update(env or {})
    return subprocess.run(["git", *args], cwd=str(kok), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=e)


def yaz(kok: Path, rel: str, govde: str) -> None:
    p = kok / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(govde, encoding="utf-8")


def gate_kos(kok: Path, *args: str, env: dict | None = None) -> tuple[int, str]:
    e = os.environ.copy()
    e.pop("IX_NO_CHANGELOG", None)
    e.update(env or {})
    proc = subprocess.run([sys.executable, str(GATE), *args], cwd=str(kok),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=e, timeout=120)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def sandbox_kur() -> Path:
    kok = Path(tempfile.mkdtemp(prefix="chglog_gate_"))
    git(kok, "init", "-q")
    git(kok, "config", "user.email", "fixture@example.com")
    git(kok, "config", "user.name", "fixture")
    git(kok, "config", "commit.gpgsign", "false")
    # Sentetik proje sekli: DEV_CORE'a benzemeyen minimal agac.
    yaz(kok, "README.md", "# sentetik depo\n\nfixture icin.\n")
    yaz(kok, CHANGELOG, "# INFRA-CHANGELOG (sentetik)\n\n## scripts/hooks/ornek_hook.py\n")
    yaz(kok, "scripts/hooks/ornek_hook.py", "# v1\nprint('merhaba')\n")
    yaz(kok, "mcp_servers/ornek/arac.py", "# v1\n")
    yaz(kok, "tests/fixtures/ornek/veri.py", "# fixture VERISI (muaf)\n")
    yaz(kok, "docs/kilavuz.md", "# dokuman\n")
    git(kok, "add", "-A")
    git(kok, "commit", "-q", "-m", "ilk")
    return kok


def stage_temizle(kok: Path) -> None:
    git(kok, "reset", "-q", "HEAD")
    git(kok, "checkout", "-q", "--", ".")


def main() -> int:
    if not GATE.is_file():
        print(f"DOGRULANAMADI: gate bulunamadi {GATE}")
        return 1
    kok = sandbox_kur()

    # --- S1 BOZUK: infra kodu staged, changelog YOK -> BLOK
    yaz(kok, "scripts/hooks/ornek_hook.py", "# v2 davranis degisti\nprint('merhaba')\n")
    git(kok, "add", "scripts/hooks/ornek_hook.py")
    rc, out = gate_kos(kok)
    kontrol("S1 infra staged + changelog YOK -> BLOK (exit 1)", rc == 1, f"exit={rc}")
    kontrol("S1 mesaj sinifi ve cikis yolunu soyluyor",
            "INFRA-CHANGELOG-YOK" in out and "IX_NO_CHANGELOG=1" in out)

    # --- S2 TEMIZ: ayni degisiklik + changelog staged -> SERBEST
    yaz(kok, CHANGELOG, "# INFRA-CHANGELOG (sentetik)\n\n## scripts/hooks/ornek_hook.py\n"
                        "| 2026-08-01 | v2 | sentetik | fixture | - | - |\n")
    git(kok, "add", CHANGELOG)
    rc, out = gate_kos(kok)
    kontrol("S2 infra + changelog birlikte -> SERBEST (exit 0)", rc == 0, f"exit={rc}")
    stage_temizle(kok)

    # --- S3 TEMIZ: yalniz dokuman staged -> SERBEST (dokuman muaf)
    yaz(kok, "docs/kilavuz.md", "# dokuman v2\n")
    git(kok, "add", "docs/kilavuz.md")
    rc, out = gate_kos(kok)
    kontrol("S3 yalniz .md dokuman -> SERBEST (exit 0)", rc == 0, f"exit={rc}")
    stage_temizle(kok)

    # --- S4 KACIS: IX_NO_CHANGELOG=1 -> SERBEST + gorunur uyari
    yaz(kok, "scripts/hooks/ornek_hook.py", "# v3\nprint('merhaba')\n")
    git(kok, "add", "scripts/hooks/ornek_hook.py")
    rc, out = gate_kos(kok, env={"IX_NO_CHANGELOG": "1"})
    kontrol("S4 IX_NO_CHANGELOG=1 -> SERBEST (exit 0)", rc == 0, f"exit={rc}")
    kontrol("S4 kacis SESSIZ degil (uyari basiliyor)", "IX_NO_CHANGELOG" in out)
    stage_temizle(kok)

    # --- S5 MUAF: tests/fixtures/ altindaki .py test VERISIDIR -> SERBEST
    yaz(kok, "tests/fixtures/ornek/veri.py", "# veri v2\n")
    git(kok, "add", "tests/fixtures/ornek/veri.py")
    rc, out = gate_kos(kok)
    kontrol("S5 tests/fixtures/*.py (veri) -> SERBEST (exit 0)", rc == 0, f"exit={rc}")
    stage_temizle(kok)

    # --- S6 BOZUK: mcp_servers de infra sinifina dahil -> BLOK
    yaz(kok, "mcp_servers/ornek/arac.py", "# v2\n")
    git(kok, "add", "mcp_servers/ornek/arac.py")
    rc, out = gate_kos(kok)
    kontrol("S6 mcp_servers/*.py -> BLOK (exit 1)", rc == 1, f"exit={rc}")

    # --- S7 CI MODU: --all'da changelog gate TETIKLENMEZ (tum agac 'staged' gorunur)
    rc, out = gate_kos(kok, "--all", env={"IX_GENERICIZE_BLOCKLIST": "ZZZ_ESLESMEYEN_DESEN"})
    kontrol("S7 --all (CI) modunda changelog gate SUSAR (exit 0)",
            rc == 0 and "INFRA-CHANGELOG-YOK" not in out, f"exit={rc}")
    stage_temizle(kok)

    # --- S8 UCTAN UCA (GERCEK COMMIT): hooksPath kablolu -> commit BLOKLANIR
    yaz(kok, "scripts/hooks/ornek_hook.py", "# v4\nprint('merhaba')\n")
    git(kok, "add", "scripts/hooks/ornek_hook.py")
    ortak = {"IX_NO_CHANGELOG": ""}
    os.environ.pop("IX_NO_CHANGELOG", None)
    r = git(kok, "-c", f"core.hooksPath={HOOKS_DIR}", "commit", "-m", "infra v4 kayitsiz")
    ciktilar = (r.stdout or "") + (r.stderr or "")
    kontrol("S8 GERCEK commit BLOKLANDI (exit != 0)", r.returncode != 0, f"exit={r.returncode}")
    kontrol("S8 commit mesajinda gate gerekcesi var", "INFRA-CHANGELOG-YOK" in ciktilar)
    n_once = git(kok, "rev-list", "--count", "HEAD").stdout.strip()

    # --- S9 UCTAN UCA POZITIF: changelog eklenince ayni commit GECER
    yaz(kok, CHANGELOG, "# INFRA-CHANGELOG (sentetik)\n\n## scripts/hooks/ornek_hook.py\n"
                        "| 2026-08-01 | v4 | sentetik | fixture | - | - |\n")
    git(kok, "add", CHANGELOG)
    r2 = git(kok, "-c", f"core.hooksPath={HOOKS_DIR}", "commit", "-m", "infra v4 + kayit")
    n_sonra = git(kok, "rev-list", "--count", "HEAD").stdout.strip()
    kontrol("S9 changelog'lu GERCEK commit GECTI (exit 0)", r2.returncode == 0,
            f"exit={r2.returncode} {((r2.stdout or '') + (r2.stderr or ''))[:120]}")
    kontrol("S9 commit sayisi 1 artti (blok gercekti, sahte degil)",
            n_once.isdigit() and n_sonra.isdigit() and int(n_sonra) == int(n_once) + 1,
            f"{n_once} -> {n_sonra}")
    _ = ortak

    hata = [d for ok, d in SONUC if not ok]
    for ok, d in SONUC:
        print(f"  [{'OK' if ok else 'FAIL'}] {d}")
    print(f"\n{len(SONUC) - len(hata)}/{len(SONUC)} OK   (sandbox: {kok.name})")
    return 1 if hata else 0


if __name__ == "__main__":
    raise SystemExit(main())
