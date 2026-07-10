#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PR merge yardımcısı — merge'den ÖNCE CI yeşilliğini doğrular. (Opsiyonel araç, gate DEĞİL.)

NEDEN: 2026-07-10'da bir PR `validators` job'u KIRMIZIYKEN `--admin` ile merge edildi.
`gh pr merge --admin` kırmızı CI'yi sessizce merge eder ve merge GERİ ALINAMAZ.

⚠ Bu bir **gate değildir.** Guard'a bir kural olarak eklenmedi; önce dokümanla hatırlatma
denenir (gate-moratoryumu 4. şart, ADR 0019). Kural `CLAUDE.core.md §1.1`'de (L1a) yazılıdır:
*merge'den önce CI kontrol edilir; `--admin` kırmızıyı atlatmaz.* Bu araç o kontrolü
kolaylaştırır — kullanmak zorunlu değil, ama kullanmamak için sebep de yok.

Kullanım:
    python core/scripts/merge_pr.py --repo <ORG>/<REPO> --pr <N> --squash --admin --delete-branch
    ... --dry-run

Not: `--repo` ZORUNLUDUR (guard kural 9 — `gh` hedefi cwd'den çıkarır, `core/` junction'dır).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

IYI = {"SUCCESS", "NEUTRAL", "SKIPPED"}


def _gh(*args: str) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} → {r.stderr.strip()[:200]}")
    return r.stdout


def _ci_yesil_mi(repo: str, pr: int) -> tuple[bool, list[str]]:
    ham = _gh("pr", "view", str(pr), "--repo", repo, "--json", "statusCheckRollup")
    kontroller = json.loads(ham).get("statusCheckRollup") or []
    if not kontroller:
        return False, ["hiç status check yok (CI koştu mu?)"]
    kotu = []
    for k in kontroller:
        ad = k.get("name") or k.get("context") or "?"
        son = (k.get("conclusion") or k.get("state") or "PENDING").upper()
        if son not in IYI:
            kotu.append(f"{ad}={son}")
    return (not kotu), sorted(set(kotu))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, help="<ORG>/<REPO> — AÇIKÇA verilir (guard kural 9)")
    ap.add_argument("--pr", required=True, type=int)
    ap.add_argument("--squash", action="store_true")
    ap.add_argument("--delete-branch", action="store_true")
    ap.add_argument("--admin", action="store_true", help="ruleset onay şartı (tek code-owner)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    print(f"[merge_pr] {a.repo}#{a.pr}\n")

    durum = json.loads(_gh("pr", "view", str(a.pr), "--repo", a.repo, "--json", "state"))["state"]
    if durum != "OPEN":
        print(f"[SKIP] PR durumu {durum} — merge edilecek bir şey yok.")
        return 0

    yesil, kotu = _ci_yesil_mi(a.repo, a.pr)
    if not yesil:
        print("⛔ CI YEŞİL DEĞİL — merge YOK:")
        for k in kotu:
            print(f"     · {k}")
        print("\n   `--admin` CI'yi atlatmaz. Önce düzelt ya da koşumun bitmesini bekle.")
        return 1
    print("[ OK ] tüm status check'ler yeşil")

    argv = ["pr", "merge", str(a.pr), "--repo", a.repo]
    if a.squash:
        argv.append("--squash")
    if a.admin:
        argv.append("--admin")
    if a.delete_branch:
        argv.append("--delete-branch")

    if a.dry_run:
        print(f"\n[DRY-RUN] gh {' '.join(argv)}")
        return 0
    print(f"\n→ gh {' '.join(argv)}")
    _gh(*argv)
    print("[ OK ] merged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(f"⛔ {e}", file=sys.stderr)
        raise SystemExit(1)
