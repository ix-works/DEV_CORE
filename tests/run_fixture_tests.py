#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_fixture_tests.py — 10 validator icin bad/good fixture ciftlerini kosar (G1/T3.6).

Her validator icin tests/fixtures/<validator>/{bad,good}/ altinda gercekci bir mini
"proje koku" bulunur (SOURCE_CODES/... veya docs/...). Bu dizin CLAUDE_PROJECT_DIR
olarak validator subprocess'ine verilir; validator boylece kendi normal (argumansiz,
repo-geneli tarama) modunda calisir:

  - bad/  -> validator FAIL vermeli (exit != 0)
  - good/ -> validator PASS vermeli (exit == 0)

Herhangi bir cift beklenenin tersini verirse (ya da fixture eksikse) NIHAI exit 1.

Kullanim:
    python tests/run_fixture_tests.py
Cikis: 0 -- 10/10 beklendigi gibi, 1 -- en az bir sapma.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
VALIDATORS_DIR = HERE.parent / "scripts" / "validators"

# G1/T3.6 ilk-10: hepsi CLAUDE_PROJECT_DIR + argumansiz repo-geneli tarama modunu
# destekler (proje_root()/source_dir() -> env). ATLANDI: check_rap_byassoc_keys_only
# (kod her zaman `return 0` -- SOFT, fixture'la FAIL uretilemez) ve check_console_utf8
# (CORE = Path(__file__).resolve().parents[2] hard-code -- kendi scripts/ agacini tarar,
# CLAUDE_PROJECT_DIR/cwd'den BAGIMSIZ -- fixture ile izole edilemez).
VALIDATORS = [
    "check_bdef_backtick",
    "check_cds_srvd_comment_syntax",
    "check_list_view_grid",
    "check_ui5_freestyle_traps",
    "check_filter_search_pattern",
    "check_decimal_write_to",
    "check_method_param_type_c",
    "check_no_rap_commit",
    "check_amdp_comment_apostrophe",
    "check_kd_no_raw_mermaid",
]


def run_validator(name: str, fixture_dir: Path) -> tuple[int, str]:
    script = VALIDATORS_DIR / f"{name}.py"
    env = os.environ.copy()
    # Sizinti onleme: parent surecten IX_*/CLAUDE_PROJECT_DIR miras alinmaz.
    for k in list(env):
        if k == "CLAUDE_PROJECT_DIR" or k.startswith("IX_"):
            env.pop(k, None)
    env["CLAUDE_PROJECT_DIR"] = str(fixture_dir)
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(fixture_dir),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    rows = []  # (name, bad_desc, good_desc, verdict, detail)
    all_ok = True

    for name in VALIDATORS:
        script = VALIDATORS_DIR / f"{name}.py"
        bad_dir = FIXTURES / name / "bad"
        good_dir = FIXTURES / name / "good"

        if not script.is_file():
            rows.append((name, "n/a", "n/a", "DOĞRULANAMADI", f"validator bulunamadı: {script}"))
            all_ok = False
            continue
        if not bad_dir.is_dir() or not good_dir.is_dir():
            rows.append((name, "n/a", "n/a", "DOĞRULANAMADI", "fixture bad/good dizini eksik"))
            all_ok = False
            continue

        try:
            bad_rc, bad_out = run_validator(name, bad_dir)
            good_rc, good_out = run_validator(name, good_dir)
        except Exception as exc:  # pragma: no cover -- gercek calisma-zamani hatasi
            rows.append((name, "n/a", "n/a", "DOĞRULANAMADI", f"çalıştırma hatası: {exc}"))
            all_ok = False
            continue

        bad_ok = bad_rc != 0
        good_ok = good_rc == 0
        ok = bad_ok and good_ok
        all_ok = all_ok and ok

        detail = ""
        if not bad_ok:
            detail += f" | bad BEKLENMEDİK exit={bad_rc} çıktı: {bad_out.strip()[:200]}"
        if not good_ok:
            detail += f" | good BEKLENMEDİK exit={good_rc} çıktı: {good_out.strip()[:200]}"

        rows.append((
            name,
            f"exit={bad_rc} ({'OK' if bad_ok else 'TERS'})",
            f"exit={good_rc} ({'OK' if good_ok else 'TERS'})",
            "PASS" if ok else "FAIL",
            detail,
        ))

    name_w = max(len(r[0]) for r in rows) + 2
    print(f"{'validator':<{name_w}} {'bad (fail beklenir)':<26} {'good (pass beklenir)':<26} sonuç")
    print("-" * (name_w + 26 + 26 + 8))
    for name, bad_s, good_s, verdict, detail in rows:
        print(f"{name:<{name_w}} {bad_s:<26} {good_s:<26} {verdict}")
        if detail:
            print(f"    -> {detail.strip(' |')}")

    n_pass = sum(1 for r in rows if r[3] == "PASS")
    print(f"\n{n_pass}/{len(rows)} PASS")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
