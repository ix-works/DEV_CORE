#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ix_doctor_memory_git — K7a memory dizini git + remote GÖZLEMİ (yeni-proje akışı F4).

KUSUR (yeni-proje akışı denetimi 2026-10-03, F4): `seed_memory` yeni projenin auto-memory
dizinini git'siz doğurur; CLAUDE.core §1.1 gün-sonu adımı ise memory'nin "kendi PRIVATE
remote'lu git'inde" olduğunu varsayar ⇒ yedeksiz tek kopya, hiçbir yüzey söylemiyordu
(K7a yalnız MEMORY.md doluluğuna bakıyordu).

DÜZELTME: K7a2 satırı — `.git` yok ⇒ WARN · `.git` var remote yok ⇒ WARN · ikisi de var ⇒ PASS.
⛔ FAIL YOK (yalnız gözlem; yeni gate ADR 0019 moratoryumuna tabidir).

YALITIM: memory dizini `CLAUDE_CONFIG_DIR` ile KUMA yönlenir (`utils.claude_paths`
onurlar) ⇒ gerçek `~/.claude` OKUNMAZ/YAZILMAZ. `deploy_ui --help` (7b) sahte rc 0;
proje `project.yaml`'ı `active_package`sız (7c WARN — bu korpus 7c'ye bakmaz).
Tüketilen satırlar: yalnız "memory" geçen satırlar.

VEKTÖRLER (her biri ayrı kum config dizini, `katman7()` GERÇEK):
  N1  memory dizini YOK          → 7a FAIL (bugünkü) + 7a2 SKIP (iki kez söylenmez)
  N2  MEMORY.md dolu, .git YOK   → 7a PASS + 7a2 WARN "git'siz"; FAIL yok
  N3  .git var, remote YOK       → 7a2 WARN "remote YOK"; FAIL yok
  N4  .git + remote              → 7a2 PASS (kapsam notu: push ölçülmedi)
  N5  KONTROL: N2–N4'te 7a satırı bugünküyle AYNI ("memory dolu")

MUTASYON (bellekte; çapa tam 1 kez bulunmazsa exit 2):
  --mutasyon-git-fail      git'siz satırı FAIL olur          → N2 düşer (gözlem → gate kayması)
  --mutasyon-remote-bakma  `.git` varsa remote'a bakmadan PASS → N3 düşer
TABAN (eski kod): --kaynak <ix_doctor.py>  → N1–N4 düşer (7a2 satırı yok); N5 geçer

Çıkış: 0 beklendiği gibi · 1 sapma · 2 KURULAMADI
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DOCTOR = REPO / "scripts" / "ix_doctor.py"

GECERLI_KIP = ("--mutasyon-git-fail", "--mutasyon-remote-bakma")
KIP: set[str] = set()
TABAN: Path | None = None
_a = sys.argv[1:]
while _a:
    x = _a.pop(0)
    if x == "--kaynak" and _a:
        TABAN = Path(_a.pop(0)).resolve()
    elif x in GECERLI_KIP:
        KIP.add(x)
    else:
        print(f"[DURDU] bilinmeyen arguman: {x!r} — gecerli: {list(GECERLI_KIP)} + --kaynak")
        sys.exit(2)

SONUC: list[tuple[str, bool]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul)))
    print(f"  [{'OK' if kosul else 'FAIL'}] {ad}" + (f"  -- {detay}" if not kosul and detay else ""))


def _degistir(metin: str, eski: str, yeni: str, ad: str) -> str:
    n = metin.count(eski)
    if n != 1:
        print(f"[DURDU] KURULAMADI: {ad} capasi {n} kez bulundu (1 bekleniyordu): {eski[:70]!r}")
        sys.exit(2)
    return metin.replace(eski, yeni)


def kaynak_metni() -> str:
    if TABAN is not None:
        return TABAN.read_text(encoding="utf-8")
    m = DOCTOR.read_text(encoding="utf-8")
    if "--mutasyon-git-fail" in KIP:
        m = _degistir(m, "        r.append((WARN, f\"memory dizini git'siz:",
                      "        r.append((FAIL, f\"memory dizini git'siz:", "git-fail")
    if "--mutasyon-remote-bakma" in KIP:
        m = _degistir(m, "        rc, out = _git(mem_dir, \"remote\")\n",
                      "        rc, out = 0, \"origin\"\n", "remote-bakma")
    return m


def _git(p: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(p), *args], check=True, capture_output=True)


def _sil(d: Path) -> None:
    def _ac(func, path, _exc):  # noqa: ANN001
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    kw = {"onexc": _ac} if sys.version_info >= (3, 12) else {"onerror": _ac}
    try:
        shutil.rmtree(d, **kw)  # type: ignore[arg-type]
    except Exception:
        shutil.rmtree(d, ignore_errors=True)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ix_memgit_"))
    eski_env = {k: os.environ.get(k) for k in ("CLAUDE_PROJECT_DIR", "CLAUDE_CONFIG_DIR",
                                               "GIT_CEILING_DIRECTORIES")}
    try:
        proje = tmp / "proje"
        proje.mkdir()
        (proje / "project.yaml").write_text("sap_profile: s4_private\n", encoding="utf-8")
        os.environ["CLAUDE_PROJECT_DIR"] = str(proje)
        os.environ["GIT_CEILING_DIRECTORIES"] = str(tmp)

        g = {"__name__": "ix_doctor_memgit", "__file__": str(DOCTOR), "__builtins__": __builtins__}
        exec(compile(kaynak_metni(), str(DOCTOR), "exec"), g)
        _gercek_run = g["_run"]

        def _sahte_run(args, *a, **k):  # noqa: ANN001
            if any(str(x).endswith("deploy_ui.py") for x in args):
                return 0, "sahte"
            return _gercek_run(args, *a, **k)

        g["_run"] = _sahte_run
        sys.path.insert(0, str(REPO / "scripts"))
        from utils.claude_paths import auto_memory_dizini  # noqa: E402

        def senaryo(ad: str, kur) -> list:  # noqa: ANN001
            os.environ["CLAUDE_CONFIG_DIR"] = str(tmp / f"cfg_{ad}")
            mem = auto_memory_dizini(proje)
            if mem.parent.parent.parent != tmp / f"cfg_{ad}":
                print(f"[DURDU] KURULAMADI: memory yolu kuma yönlenmedi: {mem}")
                sys.exit(2)
            kur(mem)
            return [[t, m] for t, m in g["katman7"]() if "memory" in m]

        def dolu(mem: Path) -> None:
            mem.mkdir(parents=True)
            (mem / "MEMORY.md").write_text("# hafiza\n- satir\n", encoding="utf-8")

        def gitli(mem: Path, remote: bool) -> None:
            dolu(mem)
            _git(mem, "init", "-q")
            if remote:
                _git(mem, "remote", "add", "origin", "https://github.com/ornek-org/ornek-repo-memory.git")

        s1 = senaryo("n1", lambda mem: None)
        kontrol("N1 memory dizini YOK → 7a FAIL + 7a2 SKIP",
                [t for t, _ in s1] == ["FAIL", "SKIP"] and s1[1][1].startswith("memory git denetimi atlandı"),
                f"sonuc={s1}")

        s2 = senaryo("n2", dolu)
        kontrol("N2 MEMORY.md dolu + .git YOK → 7a2 WARN git'siz, FAIL yok",
                [t for t, _ in s2] == ["PASS", "WARN"] and s2[1][1].startswith("memory dizini git'siz")
                and "PROJECT_BOOTSTRAP" in s2[1][1], f"sonuc={s2}")

        s3 = senaryo("n3", lambda mem: gitli(mem, False))
        kontrol("N3 .git var + remote YOK → 7a2 WARN remote YOK, FAIL yok",
                [t for t, _ in s3] == ["PASS", "WARN"] and "remote YOK" in s3[1][1], f"sonuc={s3}")

        s4 = senaryo("n4", lambda mem: gitli(mem, True))
        kontrol("N4 .git + remote → 7a2 PASS (origin) + kapsam notu",
                [t for t, _ in s4] == ["PASS", "PASS"] and "(origin)" in s4[1][1]
                and "ölçülmedi" in s4[1][1], f"sonuc={s4}")

        kontrol("N5 KONTROL: N2–N4'te 7a satırı bugünkü 'memory dolu' PASS'ı",
                all(s and s[0][0] == "PASS" and s[0][1].startswith("memory dolu:") for s in (s2, s3, s4)))
    finally:
        for k, v in eski_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        _sil(tmp)

    ok = sum(1 for _, k in SONUC if k)
    etiket = f" [TABAN {TABAN}]" if TABAN else (f" [{' '.join(sorted(KIP))}]" if KIP else "")
    print(f"\nix_doctor_memory_git{etiket}: {ok}/{len(SONUC)} PASS")
    return 0 if ok == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
