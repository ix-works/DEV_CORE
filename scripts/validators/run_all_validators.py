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
    # ADVISORY (bilinçli): desen meşru existence-read ile hatalı non-key-read'i AYIRT EDEMEZ
    # (standards/05 §5.1). Bloklamaz, listeler; bulguda exit 1 isteyen opt-in `--bulguda-exit1`.
    ("RAP BY-assoc keys-only read (advisory, BE-20)", "check_rap_byassoc_keys_only.py", [], "project",
     ["s4_private", "s4_public", "btp_abap"]),
    ("RAP commit yasağı (HARD, BE-26)", "check_no_rap_commit.py", [], "project",
     ["s4_private", "s4_public", "btp_abap"]),
    ("AMDP yorum-apostrof (HARD, BE-28c)", "check_amdp_comment_apostrophe.py", [], "project",
     ["s4_private", "s4_public", "btp_abap", "ecc"]),  # ecc: yalnız db=hana'da anlamlı (validator no-op'a düşer)
    # CDS'te `"` / SRVD'de herhangi bir yorum: SAP ikisini de SESSİZCE yutar
    # (CDS: kaynağı hiç almaz, push yine "[OK] activated" der · SRVD: yorumu siler,
    # obje aktive olur, repo canlıdan sapar). BEŞ kontrol de yeşil verirken kaçtı.
    ("CDS/SRVD yorum sözdizimi (HARD, BE-61)", "check_cds_srvd_comment_syntax.py", [], "project",
     ["s4_private", "s4_public", "btp_abap"]),
    # Miktar/tutar alanı `coalesce()`a HAM girerse SAP aktivasyonu REDDEDER
    # ("Amounts and quantities are not allowed in expression"). ADR 0006 reviewer o objeye
    # PASS vermişti (13/13 rc=0) ⇒ hiçbir yerel kapı bu DERLEYİCİ kuralını görmüyordu.
    # ⛔ warn-first (bulguda exit 0) — BİLİNÇLİ: kural alanın TİPİNİ bilmeyi gerektirir,
    # yol ifadelerinde (`_Assoc.Alan`) tarama SEZGİSELDİR. Korpusta ölçüldü (2026-08-29):
    # 263 .cds / 307 kapsanan eleman → 11 bulgu, "doğru emsal" görünümlerde SIFIR FP.
    # Terfi (BLOCKER) TARİHLİ ayrı karardır; bulguda exit 1 isteyen: --bulguda-exit1.
    ("CDS miktar/tutar ifade (warn-first, C-CDS-QTYEXPR-01)", "check_cds_qty_in_expression.py",
     [], "project", ["s4_private", "s4_public", "btp_abap"]),
    # .bdef yorumundaki ters-tırnak SAP'de ÇOĞALIYOR (repo 2 → canlı 8). Sessiz VE büyüyen:
    # push/aktivasyon/syntax_check üçü de yeşil; fark yalnız readback bayt kıyasında. 2 kez yaşandı.
    ("bdef ters-tırnak (HARD, BE-62)", "check_bdef_backtick.py", [], "project",
     ["s4_private", "s4_public", "btp_abap"]),
    ("KD ham-mermaid yok (DOC-KD-15)", "check_kd_no_raw_mermaid.py", [], "project", None),
    # FS gövdesi analiz-günlüğüne dönüşmesin (İLKE-2b, 3 katman) — 2026-08-17: 9 sürümlük FS gövdesinde
    # satırların ~%25'i sürüm etiketi/gate-ID/"canlı ölçüldü" notu taşıyordu, onaya sunulamadı. Warn-first.
    ("FS gövdesi analiz-günlüğü sızıntısı (advisory/warn-first, DOC-FS-05/06a)", "check_fs_no_analysis_log.py", [], "project", None),
    ("Proje-kökü çözümlemesi (HARD, CORE-01/ADR 0020)", "check_project_root_resolution.py", [], "both", None),
    ("Kural↔gate coverage (HARD, ADR 0019)", "check_rule_gate_coverage.py", [], "both", None),
    # Hook'lar ajana "OKU: <yol>" der; yol çözülmezse ZORUNLU protokol sessizce atlanır
    # (2026-07-09 denetimi: 32 talimat, 0 okuma). C-HOOK-01.
    ("Hook enjekte-yol çözümlemesi (HARD, C-HOOK-01)", "check_hook_injected_paths.py", [], "project", None),
    # core/ junction'dır → Grep/Glob görmez. CORE-INDEX gerçek dosyadır ve o körlüğü
    # kapatır; bayat indeks ajana YANLIŞ yol verir (sessiz hata). C-IDX-01.
    ("CORE-INDEX tazeliği (HARD, C-IDX-01)", "check_core_index_fresh.py", [], "project", None),
    # Windows cp1252: non-ASCII basan script çöker → exit 1, gerçek FAIL'den ayırt edilemez.
    # 2026-07-09'da üç script arka arkaya bu yüzden çöktü. C-ENC-01.
    ("Konsol UTF-8 koruması (HARD, C-ENC-01)", "check_console_utf8.py", [], "both", None),
    # MEMORY.md'nin yalnız ilk 200 satırı VEYA ilk 25KB'ı yüklenir; gerisi SESSİZCE düşer.
    # Ölü indeks linki / erişilemez hatıra = model için o bilgi YOK. C-MEM-01.
    ("Auto-memory bütçe + indeks bütünlüğü (HARD, C-MEM-01)", "check_memory_index.py", [], "both", None),
    # Her oturum yüklenen talimat dosyaları sessizce şişer (ölçüldü: %55 blok-tekrar).
    # warn-first — bloklamaz; HARD terfisi tarihli karar (deferred-triggers). C-BUD-01.
    ("Talimat-dosyası bütçesi (soft, C-BUD-01)", "check_instruction_budget.py", [], "both", None),
    # "manual-edit: PROHIBITED" diyen ama tazeliği ölçülmeyen artefakt sessizce bayatlar. C-REG-01.
    ("package-registry tazeliği (HARD, C-REG-01)", "check_package_registry_fresh.py", [], "project", None),
    # Hook yazmak ≠ şablona kablolamak. sap_worktype_hint + itg_backstop şablona hiç
    # eklenmemişti → init_project geride bir proje üretiyordu (2026-07-10 provası). C-TPL-01.
    ("settings.template ↔ hook envanteri (HARD, C-TPL-01)", "check_settings_template_sync.py", [], "both", None),
    # Paylaşılan ABAP üretecinin İMZASI değişip KILAVUZU değişmeyince sapma SESSİZ kalıyordu
    # (ZSD000_FM_SCREEN_GEN: 2026-07-31 IT_BUTTONS · 2026-08-14 donör+anahtarlar — 4 gün).
    # warn-first (bulguda exit 0); ADR 0019 §54 shakeout sonrası terfi kararı ayrı. CLC-SCR7.
    # ⚠ Ad "freshness" İÇERMEZ: --quick o deseni atlar, bu gate pre-commit'te KOŞMALI.
    ("FM imzası ↔ kılavuz senkron (warn-first, CLC-SCR7)", "check_fm_signature_doc_sync.py",
     [], "project", None),
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

    # T1.10 (2026-07-31): sıralı subprocess → ThreadPool paralel koşum; ÇIKTI kanonik
    # sırada basılır (submit-hepsi → sırayla bekle+bas → format/CI-parse birebir korunur).
    # Validator'lar salt-okur tarayıcılardır; eşzamanlılık güvenliği seri-vs-paralel
    # bayt-eşitlik testiyle kanıtlanır. İnce ayar/kıyas: IX_VALIDATOR_WORKERS (varsayılan 8).
    from concurrent.futures import ThreadPoolExecutor

    is_listesi = []  # (label, gorunen_ad, cmd|None)  — cmd=None → dosya YOK (FAIL)
    for label, script_name, extra_args, scope, profiller in VALIDATORS:
        if args.quick and "freshness" in script_name:
            skipped.append((label, "quick")); continue
        if not proje_modu and scope == "project":
            skipped.append((label, "core-modu")); continue
        if profil and profiller and profil not in profiller:
            skipped.append((label, f"profil={profil}")); continue
        script_path = validators_dir / script_name
        if not script_path.exists():
            is_listesi.append((label, script_name, None)); continue
        cmd = [sys.executable, str(script_path), *extra_args]
        if args.strict:
            cmd.append("--strict")
        is_listesi.append((label, script_name, cmd))
    if proje_modu:
        for label, path in _local_validators(proj):
            is_listesi.append((label, path.name, [sys.executable, str(path)]))

    def _kos(cmd):
        return subprocess.run(cmd, check=False, env=env, cwd=proj,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace")

    try:
        iscik = max(1, int(os.environ.get("IX_VALIDATOR_WORKERS", "8")))
    except ValueError:
        iscik = 8
    with ThreadPoolExecutor(max_workers=iscik) as havuz:
        gelecekler = [(label, ad, havuz.submit(_kos, cmd) if cmd else None)
                      for label, ad, cmd in is_listesi]
        for label, ad, fut in gelecekler:  # kanonik sırada bekle+bas
            print(f"\n--- {label} --- ({ad})")
            if fut is None:
                print("[FAIL] validator dosyası YOK")
                failed.append(label); continue
            r = fut.result()
            if r.stdout:
                sys.stdout.write(r.stdout)
            if r.stderr:
                sys.stderr.write(r.stderr)
            ran.append(label)
            if r.returncode != 0:
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
