# -*- coding: utf-8 -*-
"""
run_all_validators.py — Tüm validator'ları tek noktadan çalıştırır (ADR 0020, B10).

Kullanım (PROJE kökünden):
    python core/scripts/validators/run_all_validators.py [--strict] [--quick]

Modlar (D20a):
  PROJE modu : <proje>/project.yaml VAR → scope=project+both validator'lar + profil
               filtreleri + <proje>/scripts/validators-local/* keşfi.
  CORE modu  : project.yaml YOK (örn. DEV_CORE reposunda CI) → yalnız scope=both
               (statik/çekirdek) validator'lar; proje-bağlamı isteyenler SKIP —
               required-check kırmızıya boğulmaz.

Env sözleşmesi: alt-süreçlere IX_SOURCE_ROOT / IX_SAP_PROFILE / CLAUDE_PROJECT_DIR
basılır; validator'lar utils.project_config üzerinden okur (K12 — hard-code yok).

Exit: 0=hepsi geçti · 1=en az biri FAIL.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_CORE_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORE_SCRIPTS))
from utils.project_config import project_root, has_project_yaml, sap_profile, source_root_name  # noqa: E402

# (etiket, script, ekstra-arg, scope, profiller)
#   scope: "project" = proje-bağlamı ister (CORE modunda SKIP) · "both" = her modda
#   profiller: None = tüm profiller; liste = yalnız o profillerde (§9.4b)
VALIDATORS = [
    ("KESİN YASAKLAR fiziksel damga (HARD, ADR 0005)", "check_kesin_yasaklar.py", [], "project", None),
    ("Core-sızıntı kilidi (R1/2.7)", "check_core_not_committed.py", [], "project", None),
    ("Paket .rules.md varlık", "check_package_rules_present.py", [], "project", None),
    ("Paket naming regex", "check_package_naming.py", [], "project", None),
    ("Obje paket sınırı", "check_object_in_correct_pkg.py", [], "project", None),
    ("Script playbook referansı", "check_scripts_documented.py", [], "both", None),
    ("Freestyle UI5 tuzaklar (T1 V2-nav hard)", "check_ui5_freestyle_traps.py", [], "project", None),
    ("Liste=grid (sap.ui.table) (HARD, ADR 0008)", "check_list_view_grid.py", [], "project", None),
    ("Filtre/VH/grid arama deseni (HARD, FE-32)", "check_filter_search_pattern.py", [], "project", None),
    ("RAP BY-assoc keys-only read (soft, BE-20)", "check_rap_byassoc_keys_only.py", [], "project",
     ["s4_private", "s4_public", "btp_abap"]),
    ("RAP commit yasağı (HARD, BE-26)", "check_no_rap_commit.py", [], "project",
     ["s4_private", "s4_public", "btp_abap"]),
    ("AMDP yorum-apostrof (HARD, BE-28c)", "check_amdp_comment_apostrophe.py", [], "project",
     ["s4_private", "s4_public", "btp_abap", "ecc"]),  # ecc: yalnız db=hana'da anlamlı (validator no-op'a düşer)
    ("KD ham-mermaid yok (DOC-KD-15)", "check_kd_no_raw_mermaid.py", [], "project", None),
    ("Proje-kökü çözümlemesi (HARD, CORE-01/ADR 0020)", "check_project_root_resolution.py", [], "both", None),
    ("Kural↔gate coverage (HARD, ADR 0019)", "check_rule_gate_coverage.py", [], "both", None),
    ("Playbook freshness (uyarı)", "check_playbook_freshness.py", [], "both", None),
]


def _local_validators(proj: Path) -> list[tuple[str, Path]]:
    """<proje>/scripts/validators-local/*.py keşfi (alfabetik; _ ile başlayanlar hariç)."""
    d = proj / "scripts" / "validators-local"
    if not d.is_dir():
        return []
    return [(f"LOCAL: {p.stem}", p) for p in sorted(d.glob("*.py")) if not p.name.startswith("_")]


def main() -> int:
    parser = argparse.ArgumentParser(description="Tüm validator'ları çalıştır")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--quick", action="store_true", help="freshness check atla")
    args = parser.parse_args()

    proj = project_root()
    proje_modu = has_project_yaml()
    profil = sap_profile() if proje_modu else None

    env = dict(os.environ,
               CLAUDE_PROJECT_DIR=str(proj),
               IX_SOURCE_ROOT=source_root_name(),
               PYTHONPATH=str(_CORE_SCRIPTS) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    if profil:
        env["IX_SAP_PROFILE"] = profil

    mod_adi = "PROJE" if proje_modu else "CORE (D20a: proje-bağlamı isteyenler SKIP)"
    print(f"run_all_validators — mod: {mod_adi}"
          + (f" · profil: {profil}" if profil else "")
          + (f" · source_root: {source_root_name()}" if proje_modu else ""))
    if proje_modu and not profil:
        print("⚠ project.yaml var ama sap_profile DOLDURULMAMIŞ — profil-filtreleri "
              "uygulanamıyor (fail-safe: profil-bağımlı validator'lar yine koşar; "
              "kurulum: project.yaml sap_profile alanını doldur).")

    validators_dir = Path(__file__).parent
    failed, skipped, ran = [], [], []

    for label, script_name, extra_args, scope, profiller in VALIDATORS:
        if args.quick and "freshness" in script_name:
            skipped.append((label, "quick")); continue
        if not proje_modu and scope == "project":
            skipped.append((label, "core-modu")); continue
        if profil and profiller and profil not in profiller:
            skipped.append((label, f"profil={profil}")); continue

        script_path = validators_dir / script_name
        if not script_path.exists():
            failed.append(label)
            print(f"\n--- {label} --- ({script_name})\n[FAIL] validator dosyası YOK")
            continue
        cmd = [sys.executable, str(script_path), *extra_args]
        if args.strict:
            cmd.append("--strict")
        print(f"\n--- {label} --- ({script_name})")
        result = subprocess.run(cmd, check=False, env=env, cwd=proj)
        ran.append(label)
        if result.returncode != 0:
            failed.append(label)

    # validators-local keşfi (yalnız proje modunda)
    if proje_modu:
        for label, path in _local_validators(proj):
            print(f"\n--- {label} --- ({path.name})")
            result = subprocess.run([sys.executable, str(path)], check=False, env=env, cwd=proj)
            ran.append(label)
            if result.returncode != 0:
                failed.append(label)

    print("\n" + "=" * 60 + "\nÖzet:")
    for label in ran:
        print(f"  [{'FAIL' if label in failed else 'OK'}]   {label}".replace("[OK]  ", "[OK]"))
    for label, neden in skipped:
        print(f"  [SKIP] {label} ({neden})")

    if failed:
        print(f"\n{len(failed)} validator FAIL — yukarıdaki çıktıları incele.", file=sys.stderr)
        return 1
    print("\nTüm validator'lar OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
