#!/usr/bin/env python3
"""PostToolUse hook — governance/standards/validator/spec/.rules.md/populate_*.py
duzenlemesinden SONRA run_all_validators.py --quick'i otomatik kosturur.

Amac: ADR 0006 kod gate'lerini "agent elle hatirlasin" yerine "harness otomatik
zorlasin" haline getirmek. Advisory degil-blokaj: yalnizca validator FAIL olursa
stderr'e ozet yazip exit 2 ile sonucu Claude'a geri besler (CLAUDE.md §6 STOP
kurali: validator fail -> once duzelt). Validator OK ise sessizce cikar (exit 0).

Tetiklemeyen dosyalar (kaynak kod, UI, vb.) icin hicbir sey yapmaz -> sifir gurultu.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[2]

# Yalnizca asagidaki yollar validator'lari tetikler (regex, / normalize edilmis path uzerinde)
TRIGGER = re.compile(
    r"(\.rules\.md$"
    r"|/governance/"
    r"|/standards/"
    r"|/validators/"
    r"|populate_[^/]*\.py$"
    r"|sprint[^/]*\.(md|json)$"
    r"|SPRINT_PLAN"
    r"|td_spec)",
    re.IGNORECASE,
)

# P1 SEÇİCİLİK (T1.8, denetim 2026-07-31): edit-anında 24 validator'lık tam quick-tur
# (~13 sn) yerine dosya-SINIFINA göre bilinen-güvenli ALT-KÜME koşulur. İLKE: tabloda
# eşleşmeyen her TRIGGER dosyası TAM tura düşer (varsayılan DAİMA tam — fail-open yolu
# yok; ADR 0023). Tam tur pre-commit + CI'da zaten koşuyor → edit-anı erken-uyarı işlevi
# sınıfla İLGİLİ validator'larla korunur. Sıra önemli: ilk eşleşen sınıf kazanır.
HIZLI_KUME = [
    # (sınıf-adı, yol-regex'i, koşulacak validator script'leri)
    ("rules-md", re.compile(r"\.rules\.md$", re.IGNORECASE),
     ["check_rule_gate_coverage.py", "check_package_rules_present.py"]),
    ("validator-py", re.compile(r"/validators/[^/]+\.py$", re.IGNORECASE),
     ["check_console_utf8.py", "check_project_root_resolution.py",
      "check_rule_gate_coverage.py"]),
    ("populate-py", re.compile(r"populate_[^/]*\.py$", re.IGNORECASE),
     ["check_console_utf8.py", "check_project_root_resolution.py"]),
    ("standards-decisions", re.compile(r"/(standards|governance/decisions)/.+\.md$", re.IGNORECASE),
     ["check_core_index_fresh.py", "check_rule_gate_coverage.py"]),
    ("governance-md", re.compile(r"/governance/.+\.md$", re.IGNORECASE),
     ["check_core_index_fresh.py", "check_core_not_committed.py"]),
    # sprint*/SPRINT_PLAN/td_spec: BİLİNÇLİ tabloda YOK → tam tur (sprint kontrolleri
    # canlı-SAP'li populate-içi gate'lerdir; edit-anında hangi alt-kümenin yeteceği
    # kanıtlanmadı — kanıtsız daraltma yapılmaz).
]


def _hizli_kume_kos(sinif: str, scriptler: list) -> "tuple[bool, str]":
    """Alt-kümeyi koşar. (ok, fail_ozeti) döner; koşulamayan script = FAIL sayılır
    (fail-closed: 'koşamadım' sessiz PASS'e dönüşmez)."""
    hatalar = []
    for s in scriptler:
        yol = REPO / "scripts" / "validators" / s
        try:
            r = subprocess.run([sys.executable, str(yol)], cwd=str(REPO),
                               capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                hatalar.append(f"[{s}]\n" + (r.stdout or r.stderr or "")[-400:])
        except Exception as e:
            hatalar.append(f"[{s}] KOŞULAMADI: {e}")
    return (not hatalar, "\n".join(hatalar))


# Seçenek 2 (2026-06-24): DURUM/İZLEME dökümanları kural TAŞIMAZ → governance/ altında
# olsalar da heavy validator run'ı (run_all --quick) tetiklemezler. RESUME çapaları,
# SESSION_NOTES, auto-generated registry. Daraltma yönü under-exclude (şüpheli dosya yine
# tam doğrulanır); yalnız net-durum dosyaları. (ADR0019 onboarding nudge'ı zaten yalnız
# standards/playbook/governance-decisions için → bu dosyalar onu da tetiklemez.)
STATUS_DOC = re.compile(
    r"(RESUME[^/]*\.md$"
    r"|/SESSION_NOTES\.md$"
    r"|/package-registry\.md$)",
    re.IGNORECASE,
)


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Gerekce + sinif kaydi: scripts/hooks/README.md S4. ASCII-only + yazma hatasi
    fail-safe'i BOZMAMALI (except: pass).
    """
    try:
        sys.stderr.write(
            "[post_validate] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> fail-safe "
            "SERBEST (exit 0); KARAR DEGILDIR (girdi hic okunamadi). "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        return 0

    tool_input = data.get("tool_input", {}) or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path:
        return 0

    norm = path.replace("\\", "/")

    # #11 (2026-06-11): UI manifest.json düzenlendi → OData ref cross-check HATIRLAT.
    # Araç (check_ui_odata_refs.py) hazırdı, tetik eksikti → "remember to run" disiplini
    # kod-nudge'a çevrildi (ui-freestyle §H ZORUNLU). Servise/dataSource'a dokunulduysa
    # browser'da tıklayarak değil statik cross-check ile doğrula.
    if re.search(r"/ui/[^/]+/.*manifest\.json$", norm, re.IGNORECASE):
        app = re.sub(r"/webapp/.*$", "", norm)
        sys.stderr.write(
            "[hook:post_validate] UI manifest.json düzenlendi. dataSource/servis "
            "değiştiysen UI↔OData ref tutarlılığını DOĞRULA (ui-freestyle §H):\n"
            f"  python scripts/check_ui_odata_refs.py --app {app} --service <SRVB_adi>\n"
            "(entity/property/function ref'leri canlı metadata ile statik kıyas — tıklama testi DEĞİL).\n"
        )
        return 2  # reminder (Claude'a geri beslenir)

    # #7 (2026-06-11): list/report view.xml → grid (sap.ui.table) standardı kontrol (ADR 0008).
    # check_list_view_grid conservative; flag ederse nudge (bloklamaz).
    if re.search(r"/ui/.+\.view\.xml$", norm, re.IGNORECASE):
        try:
            res = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "validators" / "check_list_view_grid.py"), path],
                cwd=str(REPO), capture_output=True, text=True, timeout=30)
            if res.returncode == 1 and (res.stdout or "").strip():
                sys.stderr.write(
                    "[hook:post_validate] Liste/rapor görünümü grid standardı (ADR 0008, feedback_grid-liste-standardi):\n"
                    + (res.stdout or "")[-500:] + "\n")
                return 2
        except Exception:
            pass

    # ADR 0019 §5 + §5A ONBOARDING (amendment 2026-06-18): kural-taşıyan dosyada YENİ/DEĞİŞEN
    # kural → 5-adım enforcement-onboarding + 8-ölçüt RUBRIC (metin-KALİTESİ) HATIRLAT.
    # KAPSAM genişletildi: checklists + standards + playbook + governance/decisions + AGENTS/CLAUDE
    # (eskiden YALNIZ checklists → ADR §5 "standards/playbook/checklists" sözünü eksik karşılıyordu).
    # Noise-azalt: edit güç-keyword içermeli (typo/format sessiz); checklist her zaman + coverage somut.
    nudged = False
    if re.search(r"/(standards|playbook|governance/decisions)/.+\.md$|/(AGENTS|CLAUDE)\.md$", norm, re.IGNORECASE):
        new_txt = tool_input.get("new_string") or tool_input.get("content") or ""
        for _e in (tool_input.get("edits") or []):
            new_txt += "\n" + (_e.get("new_string") or "")
        is_checklist = "/checklists/" in norm
        guc = re.search(r"\b(MUST|MUST-NOT|SHOULD|SHOULD-NOT|MAY|ZORUNLU|YASAK|YASAKTIR|ÖNERİLİR|OPSİYONEL|BLOCKER|WARNING)\b",
                        new_txt, re.IGNORECASE)
        if is_checklist or guc:
            lines = ["[hook:post_validate] Kural-taşıyan dosya düzenlendi — YENİ/DEĞİŞEN KURAL ise (değilse yoksay):"]
            if is_checklist:
                try:
                    res = subprocess.run(
                        [sys.executable, str(REPO / "scripts" / "validators" / "check_rule_gate_coverage.py"), "--strict"],
                        cwd=str(REPO), capture_output=True, text=True, timeout=60)
                    if res.returncode != 0:
                        lines.append("• COVERAGE AÇIĞI (kural↔gate, ADR 0019):\n" + (res.stdout or "")[-450:])
                except Exception:
                    pass
            lines.append("• ÖNCE-ARA (KB-01, CLAUDE.core §4): ① ARA (repo+core path=core/+memory+SESSION_NOTES+register: "
                         "zaten yazılı mı · regresyon mu ilk temas mı · komşu obje-tipinde var mı) → ② ÖLÇ (kontrol grubu; "
                         "ölçümü GERÇEK giriş noktasından ve SON hâl üzerinde yap — elle script çağrısı kablolamayı kanıtlamaz) "
                         "→ ③ DARALT (kanıtın kapsamını yaz) → ④ YAZ. Kayda `prior-art: bulundu <ref>` VEYA `yok` koy.")
            lines.append("• ONBOARDING (ADR 0019 §5): (1)güç-etiketle MUST/MUST-NOT/SHOULD/MAY (2)enforcement-seç "
                         "(3)gate+fixture(oto) VEYA reviewer+checklist-üyeliği(yargı) (4)stabil-ID (5)coverage-check.")
            lines.append("• RUBRIC metin-KALİTESİ (ADR 0019 §5A, 8 ölçüt): atomik · güç-açık · denetlenebilir(pass/fail) · "
                         "kapsam-belli · tek-ev(canonical,tekrar değil) · bağımsız-anlaşılır(+gerekçe) · stabil-ID · güncel-çelişkisiz.")
            sys.stderr.write("\n".join(lines) + "\n")
            nudged = True

    # Seçenek 2: durum/izleme dökümanı → kural taşımaz, heavy run ATLA (governance/ match'lese bile)
    if not TRIGGER.search(norm) or STATUS_DOC.search(norm):
        return 2 if nudged else 0

    # P1: dosya-sınıfı eşleşirse ALT-KÜME koş; eşleşmezse aşağıdaki TAM tur (varsayılan).
    for sinif, desen, scriptler in HIZLI_KUME:
        if desen.search(norm):
            ok, ozet = _hizli_kume_kos(sinif, scriptler)
            if ok:
                return 2 if nudged else 0
            sys.stderr.write(
                f"[hook:post_validate] hızlı-küme FAIL (sınıf: {sinif}; "
                f"{Path(path).name} düzenlendi).\n"
                "ADR 0006 gate: forward progress YOK -> önce ihlali düzelt.\n"
                "(Tam tur pre-commit/CI'da ayrıca koşar.)\n--- özet ---\n" + ozet + "\n")
            return 2

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(REPO / "scripts" / "validators" / "run_all_validators.py"),
                "--quick",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception:
        # Validator kosturulamazsa hook calismayi engellemesin
        return 0

    if result.returncode == 0:
        return 2 if nudged else 0  # run_all OK; nudge varsa yine de yüzeyle

    tail = (result.stdout or "")[-800:]
    sys.stderr.write(
        "[hook:post_validate] run_all_validators.py --quick FAIL "
        f"({Path(path).name} duzenlendi).\n"
        "ADR 0006 gate: forward progress YOK -> once ihlali duzelt.\n"
        "--- validator ozeti ---\n" + tail + "\n"
    )
    return 2  # PostToolUse: stderr Claude'a geri beslenir, blokaj degil


if __name__ == "__main__":
    sys.exit(main())
