#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worktree_blocklist fixture — kimlik blocklist'i WORKTREE'de de bulunmali.

NEDEN VAR (2026-08-01, bug-avi kuyrugu; infra-expert saha-bulgusu, lider dogruladi):
`genericize_common._git_dir()` `git rev-parse --git-dir` kullaniyordu. Bir git
WORKTREE'sinde bu `.git/worktrees/<ad>` doner; blocklist ise ANA deponun
`.git/genericize-blocklist` dosyasidir -> dosya BULUNAMAZ -> `core_precommit`
fail-closed'a duser -> **worktree'den hicbir commit atilamaz**.
Worktree, infra-fix prosedurunun ZORUNLU calisma alani oldugu icin bu, akisin
tamamini kilitliyordu. (Yazma-ani kardesi AV-21'di: pre_tool_guard core'u
yol-dizgesinden tanidigi icin worktree'de sizinti guard'i kapaliydi.)

Ayrica ana repoda donen deger GORELI olabilir (`.git`) ve surec cwd'sine gore
cozulur -> mutlaklastirilmazsa baska cwd'den cagrildiginda sessizce yanlis yere bakilir.

SENARYOLAR (hepsi sentetik git deposunda; ana repolara DOKUNULMAZ):
  S1 KONTROL: ana repoda blocklist BULUNUR          (eskiden de bulunuyordu — capasi)
  S2 WORKTREE'de blocklist BULUNUR                  (asil kayit)
  S3 _git_dir worktree'de ORTAK dizini doner        (mekanizma capasi)
  S4 blocklist YOKSA bulunmaz                       (FP capasi: her zaman True demiyor)
  S5 baska cwd'den cagrildiginda da dogru cozer     (goreli-yol capasi)
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "scripts").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")

spec = importlib.util.spec_from_file_location("gc_fx", REPO / "scripts" / "genericize_common.py")
g = importlib.util.module_from_spec(spec)                   # type: ignore[arg-type]
sys.modules["gc_fx"] = g
spec.loader.exec_module(g)                                  # type: ignore[union-attr]


def _kos(*a, cwd=None):
    return subprocess.run(list(a), cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="wt_bl_"))
    ana = tmp / "ana"
    ana.mkdir()
    _kos("git", "init", "-q", ".", cwd=ana)
    _kos("git", "config", "user.email", "t@example.com", cwd=ana)
    _kos("git", "config", "user.name", "t", cwd=ana)
    (ana / "x.md").write_text("# x\n", encoding="utf-8")
    _kos("git", "add", "-A", cwd=ana)
    _kos("git", "commit", "-qm", "ilk", cwd=ana)

    # blocklist ANA deponun git dizinine konur (gercek yerlesim)
    gd = Path(_kos("git", "rev-parse", "--git-dir", cwd=ana).stdout.strip())
    if not gd.is_absolute():
        gd = (ana / gd).resolve()
    (gd / "genericize-blocklist").write_text("SENTETIK_AD\n", encoding="utf-8")

    wt = tmp / "wt"
    r = _kos("git", "worktree", "add", "-q", str(wt), "HEAD", cwd=ana)
    if r.returncode != 0:
        print(f"  [FAIL] worktree kurulamadi (sessiz gecme YOK): {r.stderr[:120]}")
        return 1

    sonuc = []
    sonuc.append(("S1 KONTROL: ana repoda blocklist BULUNUR",
                  g.blocklist_var_mi(cwd=ana) is True, f"cwd={ana.name}"))
    sonuc.append(("S2 WORKTREE'de blocklist BULUNUR",
                  g.blocklist_var_mi(cwd=wt) is True, f"cwd={wt.name}"))
    wt_gd = g._git_dir(cwd=wt)
    sonuc.append(("S3 _git_dir worktree'de ORTAK dizini doner",
                  wt_gd is not None and "worktrees" not in str(wt_gd), f"_git_dir={wt_gd}"))
    # S4 — FP capasi: blocklist silinince bulunmamali (fonksiyon her zaman True DEMEZ)
    (gd / "genericize-blocklist").unlink()
    sonuc.append(("S4 FP-CAPA: blocklist YOKSA bulunmaz",
                  g.blocklist_var_mi(cwd=wt) is False, "blocklist silindi"))
    (gd / "genericize-blocklist").write_text("SENTETIK_AD\n", encoding="utf-8")
    # S5 — goreli-yol capasi: surecin cwd'si BASKA yerdeyken de dogru cozmeli
    eski = os.getcwd()
    try:
        os.chdir(tmp)
        sonuc.append(("S5 baska cwd'den de dogru cozer",
                      g.blocklist_var_mi(cwd=wt) is True, f"process cwd={tmp.name}"))
    finally:
        os.chdir(eski)

    # S6 — PLATFORM ÇAPASI: `git rev-parse` GÖRELİ dönerse (Linux'ta olan budur; Windows'ta
    # mutlak gelir) sonuç, sorgunun cwd'sine göre çözülmeli — sürecin kendi cwd'sine göre
    # DEĞİL. Bu vaka olmadan hata yerelde (Windows) GÖRÜNMEZ ve yalnız CI'da patlar;
    # 2026-08-01'de tam olarak öyle oldu. `subprocess.run` geçici olarak sahteleştirilir.
    gercek_run = subprocess.run

    def _sahte(cmd, *a, **k):
        if isinstance(cmd, list) and cmd[:2] == ["git", "rev-parse"]:
            class _R:
                returncode = 0
                stdout = ".git\n"
                stderr = ""
            return _R()
        return gercek_run(cmd, *a, **k)

    eski2 = os.getcwd()
    try:
        g.subprocess.run = _sahte          # type: ignore[attr-defined]
        os.chdir(tmp)                      # süreç cwd'si BAŞKA yerde — asıl tuzak
        sonuc.append(("S6 PLATFORM: git GÖRELİ dönerse sorgunun cwd'sine göre çözülür",
                      g.blocklist_var_mi(cwd=ana) is True, "git -> '.git' (Linux şekli)"))
    finally:
        g.subprocess.run = gercek_run      # type: ignore[attr-defined]
        os.chdir(eski2)

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
