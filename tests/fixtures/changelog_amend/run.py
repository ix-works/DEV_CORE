#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""changelog_amend fixture — İNFRA-CHANGELOG gate'inin kıyas birimi COMMIT değil DAL.

NEDEN VAR (2026-08-01 bug-avı kuyruğu, 'amend FP' kaydı; kullanıcı onayıyla GEVŞETME):
`check_changelog` yalnız staged kümeye bakıyordu. `git commit --amend`'de staged-diff
HEAD'e göre hesaplanır; changelog satırı amend edilen commit'in İÇİNDE olsa bile gate
"changelog bu commit'te değişmiyor" deyip blokluyordu. Bug avında 3 kez yaşandı; her
seferinde IX_NO_CHANGELOG=1 kaçışı kullanıldı — FP'nin normalleştirdiği kaçış, gate'in
korumasından tehlikeli. Fix: staged kümede yoksa DAL genelinde
(merge-base(origin/main)..staged-tree) changelog değişti mi diye ikinci kontrol.

GEVŞEME SINIRI (çapalar S1/S2): taze dalda (merge-base == HEAD) davranış ESKİSİYLE
BİREBİR; origin/main çözülemezse fail-closed (eski katı yol).

SENARYOLAR (sentetik git deposu; gerçek repolara DOKUNULMAZ):
  K1 KONTROL: infra .py staged, changelog hiçbir yerde yok      → BLOK (gate hâlâ çalışıyor)
  K2 KONTROL: infra .py + changelog birlikte staged             → GEÇER (klasik yol)
  P1 FP-VAKASI: changelog+kod commit'lendi, amend'de ek kod     → GEÇER (eski sürümde BLOK)
  P2 ÇOK-COMMIT: c1 changelog, c2'de yeni kod staged            → GEÇER (eski sürümde BLOK)
  S1 GEVŞEME-SINIRI: taze dal (HEAD==origin/main), kod, chlog yok → BLOK (gevşeme dal-içi)
  S2 FAIL-CLOSED: origin/main ref'i YOK, amend senaryosu        → BLOK (çözülemedi = katı yol)
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

spec = importlib.util.spec_from_file_location(
    "cpc_fx", REPO / "scripts" / "git-hooks" / "core_precommit.py")
cpc = importlib.util.module_from_spec(spec)                 # type: ignore[arg-type]
sys.modules["cpc_fx"] = cpc
spec.loader.exec_module(cpc)                                # type: ignore[union-attr]

INFRA = "scripts/validators/check_sentetik.py"
CHLOG = cpc.CHANGELOG_PATH


def _kos(*a, cwd):
    return subprocess.run(list(a), cwd=str(cwd), capture_output=True, text=True)


def _depo_kur(tmp: Path, origin_ref: bool = True) -> Path:
    d = tmp / ("r_o" if origin_ref else "r_x")
    (d / "scripts/validators").mkdir(parents=True)
    (d / Path(CHLOG).parent).mkdir(parents=True, exist_ok=True)
    _kos("git", "init", "-q", "-b", "main", ".", cwd=d)
    _kos("git", "config", "user.email", "t@example.com", cwd=d)
    _kos("git", "config", "user.name", "t", cwd=d)
    (d / "README.md").write_text("# sentetik\n", encoding="utf-8")
    (d / CHLOG).write_text("# changelog\n", encoding="utf-8")
    _kos("git", "add", "-A", cwd=d)
    _kos("git", "commit", "-qm", "ilk", cwd=d)
    if origin_ref:
        sha = _kos("git", "rev-parse", "HEAD", cwd=d).stdout.strip()
        _kos("git", "update-ref", "refs/remotes/origin/main", sha, cwd=d)
    return d


def _gate_bloklar_mi(depo: Path) -> bool:
    """check_changelog'u deponun staged kümesiyle koştur → hata üretti mi?"""
    eski = os.getcwd()
    try:
        os.chdir(depo)
        dosyalar = cpc.staged_files()
        hatalar: list[str] = []
        cpc.check_changelog(dosyalar, hatalar)
        return bool(hatalar)
    finally:
        os.chdir(eski)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="chlog_amend_"))
    sonuc: list[tuple[str, bool, str]] = []

    # ── K1 + K2 + S1: taze dal (HEAD == origin/main) ────────────────────────────
    d = _depo_kur(tmp)
    (d / INFRA).write_text("print('v1')\n", encoding="utf-8")
    _kos("git", "add", INFRA, cwd=d)
    b = _gate_bloklar_mi(d)
    sonuc.append(("K1 KONTROL: kod var, changelog yok -> BLOK", b is True, f"blok={b}"))
    sonuc.append(("S1 GEVSEME-SINIRI: taze dalda davranis eskisiyle birebir (BLOK)",
                  b is True, "merge-base==HEAD"))
    (d / CHLOG).write_text("# changelog\n| yeni satir |\n", encoding="utf-8")
    _kos("git", "add", CHLOG, cwd=d)
    b = _gate_bloklar_mi(d)
    sonuc.append(("K2 KONTROL: kod + changelog birlikte -> GECER", b is False, f"blok={b}"))

    # ── P1: amend FP vakası ─────────────────────────────────────────────────────
    _kos("git", "commit", "-qm", "kod + changelog", cwd=d)          # dal-commit'i
    (d / INFRA).write_text("print('v2 amend eki')\n", encoding="utf-8")
    _kos("git", "add", INFRA, cwd=d)                                # amend'e girecek ek
    b = _gate_bloklar_mi(d)
    sonuc.append(("P1 FP-VAKASI: changelog HEAD'de, amend'de ek kod -> GECER",
                  b is False, f"blok={b}"))

    # ── P2: çok-commit'li dal ───────────────────────────────────────────────────
    _kos("git", "commit", "-qm", "amend yerine ikinci commit", cwd=d)
    (d / "scripts/validators/check_sentetik2.py").write_text("print('c2')\n", encoding="utf-8")
    _kos("git", "add", "scripts/validators/check_sentetik2.py", cwd=d)
    b = _gate_bloklar_mi(d)
    sonuc.append(("P2 COK-COMMIT: c1'de changelog, c2'de yeni kod -> GECER",
                  b is False, f"blok={b}"))

    # ── S2: origin/main YOK → fail-closed ───────────────────────────────────────
    d2 = _depo_kur(tmp, origin_ref=False)
    (d2 / INFRA).write_text("print('v1')\n", encoding="utf-8")
    (d2 / CHLOG).write_text("# changelog\n| satir |\n", encoding="utf-8")
    _kos("git", "add", "-A", cwd=d2)
    _kos("git", "commit", "-qm", "kod + changelog", cwd=d2)
    (d2 / INFRA).write_text("print('v2')\n", encoding="utf-8")
    _kos("git", "add", INFRA, cwd=d2)
    b = _gate_bloklar_mi(d2)
    sonuc.append(("S2 FAIL-CLOSED: origin/main yok, amend senaryosu -> BLOK",
                  b is True, f"blok={b}"))

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
