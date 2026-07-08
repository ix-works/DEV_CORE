"""
run_all_validators.py — Tüm validator'ları tek noktadan çalıştırır.

Kullanım:
    python scripts/validators/run_all_validators.py
    python scripts/validators/run_all_validators.py --strict   # warning'leri de fail
    python scripts/validators/run_all_validators.py --quick    # freshness check atla

Exit kodu:
    0 — Tüm validator'lar geçti
    1 — Bir veya daha fazlası fail oldu

Tipik kullanım: pre-commit hook ve oturum başında sprint_gate_check'ten sonra.
"""
import argparse
import subprocess
import sys
from pathlib import Path

# Windows konsol UTF-8 fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# (name, args) — sırayla çalıştırılır, exit code toplanır
VALIDATORS = [
    ("Paket .rules.md varlık", "check_package_rules_present.py", []),
    ("Paket naming regex", "check_package_naming.py", []),
    ("Obje paket sınırı", "check_object_in_correct_pkg.py", []),
    ("Script playbook referansı", "check_scripts_documented.py", []),
    # ADR 0016 REVİZE (2026-06-16): "Source drift (repo↔canlı)" validatorü (M3) KALDIRILDI —
    # yeni modelde repo≠canlı düzenleme sırasında DOĞAL (working-tree edit), drift-raporu noise
    # olurdu. Koruma edit-öncesine taşındı (pull-before-edit hook + sap_sync_pull). check_source_drift.py
    # dosyası repoda durur (deprecated) ama run_all'da KOŞMAZ.
    ("Freestyle UI5 tuzaklar (T1 V2-nav hard)", "check_ui5_freestyle_traps.py", []),
    # ADR 0019 orphan-wire + A-2 triage (2026-06-18): check_list_view_grid WIRED.
    # Detektör daraltıldı (gerçek m.Table şartı → detay-form + akordion FP'leri elendi, 10→0) → HARD.
    ("Liste=grid (sap.ui.table) (HARD, ADR 0008)", "check_list_view_grid.py", []),
    # FE-32 (2026-06-24): rapor/liste filtre+VH+grid arama deseni — caseSensitive:false YASAK
    # (V2+/IWBEP toupper/tolower üretir → HTTP 400, SAP Note 1797736). HARD=caseSensitive:false;
    # WARN=rapor Filter.view tek-değer Input (MultiInput/select-options olmalı). Kanonik: ZSD001.
    ("Filtre/VH/grid arama deseni (HARD caseSensitive:false, FE-32)", "check_filter_search_pattern.py", []),
    ("RAP BY-assoc keys-only read (soft, BE-20)", "check_rap_byassoc_keys_only.py", []),
    # ADR 0019 + canlı post-mortem (2026-06-23): RAP handler/helper class'ta DB-commit yasağı.
    # ERROR (BLOCKER)=explicit COMMIT/ROLLBACK/BAPI_TRANSACTION/COMMIT ENTITIES; WARN=FM-içi-commit (i_opt_commit).
    ("RAP commit yasağı (HARD, BE-26)", "check_no_rap_commit.py", []),
    # ADR 0019 + canlı post-mortem (2026-06-29): AMDP SQLScript `--` yorumunda apostrof = aktivasyon
    # "multi-line literal" FAIL (adt_syntax_check/abaplint/bug-gate GÖRMEZ — activation-only). BE-28c terfi: checklist→wired.
    ("AMDP yorum-apostrof (HARD, BE-28c)", "check_amdp_comment_apostrophe.py", []),
    # DOC-KD-15 (2026-07-02): KD çıktısına ham ```mermaid sızması (render EDİLMEMİŞ → html/app-help'te
    # kod bloğu). fit_se→booking+5 KD tekrarı; DOC-KD-11 broken-image bunu görmez (kod render olur).
    ("KD ham-mermaid yok (DOC-KD-15)", "check_kd_no_raw_mermaid.py", []),
    # NOT: check_docu_itf_line_width.py (DOC-F1-01) yalnız run_review class_push'a WIRED
    # (write-time, per-artifact HARD). run_all repo-geneli'ne EKLENMEDİ çünkü pre-existing
    # CANLI ZSD001/013/014 runner'larında gizli ihlal var (ayrı remediation) → repo-geneli
    # HARD-block yanlış olurdu. Yeni/değişen DOCU runner push'u run_review'da gate'lenir.
    # ADR 0019 KEYSTONE (2026-06-18): kural↔gate coverage (sahte-WIRED/orphan/binding).
    # HARD (terfi 2026-06-18, shakeout temiz): bulgu = BLOCKER (kural↔gate kopuk).
    ("Kural↔gate coverage (HARD, ADR 0019)", "check_rule_gate_coverage.py", []),
    ("Playbook freshness (uyarı)", "check_playbook_freshness.py", []),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Tüm validator'ları çalıştır")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--quick", action="store_true", help="freshness check atla")
    args = parser.parse_args()

    validators_dir = Path(__file__).parent
    failed = []
    skipped = []

    for label, script_name, extra_args in VALIDATORS:
        if args.quick and "freshness" in script_name:
            skipped.append(label)
            continue

        script_path = validators_dir / script_name
        cmd = [sys.executable, str(script_path), *extra_args]
        if args.strict:
            cmd.append("--strict")

        print(f"\n--- {label} --- ({script_name})")
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            failed.append(label)

    print("\n" + "=" * 60)
    print("Özet:")
    for label, script_name, _ in VALIDATORS:
        if label in skipped:
            print(f"  [SKIP] {label}")
        elif label in failed:
            print(f"  [FAIL] {label}")
        else:
            print(f"  [OK]   {label}")

    if failed:
        print(f"\n{len(failed)} validator FAIL — yukarıdaki çıktıları incele.", file=sys.stderr)
        return 1

    print("\nTüm validator'lar OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
