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


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
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
            lines.append("• ONBOARDING (ADR 0019 §5): (1)güç-etiketle MUST/MUST-NOT/SHOULD/MAY (2)enforcement-seç "
                         "(3)gate+fixture(oto) VEYA reviewer+checklist-üyeliği(yargı) (4)stabil-ID (5)coverage-check.")
            lines.append("• RUBRIC metin-KALİTESİ (ADR 0019 §5A, 8 ölçüt): atomik · güç-açık · denetlenebilir(pass/fail) · "
                         "kapsam-belli · tek-ev(canonical,tekrar değil) · bağımsız-anlaşılır(+gerekçe) · stabil-ID · güncel-çelişkisiz.")
            sys.stderr.write("\n".join(lines) + "\n")
            nudged = True

    # Seçenek 2: durum/izleme dökümanı → kural taşımaz, heavy run ATLA (governance/ match'lese bile)
    if not TRIGGER.search(norm) or STATUS_DOC.search(norm):
        return 2 if nudged else 0

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
