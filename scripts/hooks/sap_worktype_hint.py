#!/usr/bin/env python3
"""PreToolUse (SAP-yazma MCP tool'ları) — DETERMİNİSTİK worktype-checklist hatırlatması.

NEDEN (2026-07-10 skill-injection redizaynı): eski `skill_injector` "bu SAP işi mi + hangi
checklist" tespitini prompt-KEYWORD regex'iyle yapıyordu → kırılgan ("CDS view yarat"
kaçtı, İngilizce "public transport" yanlış-tetikledi). Referans ekosistemin tamamı keşfi
`description`-semantik native mekanizmayla yapıyor; keyword-hook azınlık ve en kırılgan.

REDİZAYN:
  (A) KEŞİF ("bu SAP işi mi + hangi skill") → native `sap-abap-dev` skill `description`'ı
      (943 char, zaten devrede). skill_injector'dan SAP-tespiti KALDIRILDI.
  (B) ENFORCEMENT ("worktype checklist yazımdan önce oku") → BU HOOK. Prompt'tan niyet
      tahmin ETMEZ; GERÇEK SAP-yazma anında, GERÇEK obje-tipinden (tool argümanı) checklist'i
      adıyla söyler. "CDS view yarat"ın nasıl yazıldığı önemsizleşir — deterministik.

Non-blocking (exit 0 + additionalContext). Gerçek gate ADR 0006 run_review'dur; bu, doğru
checklist'i doğru anda hatırlatan fail-closed sigortadır. Session+worktype başına BİR kez
(gürültü olmasın) — pre-flight semantiği.
"""
import json
import os
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


# Tool → (worktype-grup, obje-tipi belirsizse). Dedicated create tool'ları tipi ima eder.
_TOOL_TIPI = {
    "mcp__sap-adt__adt_dtel_create": "dtel",
    "mcp__sap-adt__adt_domain_create": "doma",
    "mcp__sap-adt__adt_struct_create": "struct",
    "mcp__sap-adt__adt_publish_service": "srvb",
}
# push_source / activate: obje-tipi tool_input.object_type'tan gelir.
_TIP_TOOLLARI = {"mcp__sap-adt__adt_push_source", "mcp__sap-adt__adt_activate"}

# obje-tipi (küçük harf, ilk 4+) → (worktype-grup, checklist satırı). Grup = dedup anahtarı.
def _checklist(otype: str):
    t = (otype or "").lower().strip()
    if t.startswith("ddls") or "cds" in t or t.startswith("view"):
        return ("cds", "CDS view → OKU: playbook/checklists/cds-creation.md "
                       "(+ playbook/adt-cds.md 'TEK CDS YARATMA') · standards/05")
    if t.startswith(("bdef", "srvd", "srvb", "beh")) or "behavior" in t or "service" in t:
        return ("rap", "RAP (BDEF/behavior/SRVD/SRVB) → OKU: "
                       "playbook/checklists/rap-creation.md · standards/05 · adt-rap §32/§35")
    if t.startswith(("doma", "dtel")):
        return ("ddic-dd", "DDIC domain/DTEL → OKU: playbook/checklists/domain-dtel-creation.md "
                           "· standards/01 §5B (reuse-gate, TR-4-label)")
    if t.startswith("struct") or t.startswith("tabl") or t == "stru":
        return ("ddic-st", "DDIC struct/tablo → OKU: playbook/checklists/struct-creation.md "
                           "/ table-update.md · standards/01 §5B (+ check_td_cancelled_fields)")
    if t.startswith("prog") or "report" in t or "dynpro" in t:
        return ("classic", "Klasik dialog/report → OKU: playbook/checklists/classic-dialog-creation.md "
                           "· standards/06 (§1 include-böl ZORUNLU)")
    return (None, "")


def _session_id(proj: Path) -> str:
    try:
        d = json.loads((proj / ".claude" / ".current_session").read_text(encoding="utf-8"))
        return str(d.get("session_id") or "")
    except Exception:
        return ""


def _already_hinted(proj: Path, sid: str, grup: str) -> bool:
    """Session+worktype başına BİR kez. Marker .claude/.worktype_hinted.json (git-dışı)."""
    f = proj / ".claude" / ".worktype_hinted.json"
    try:
        st = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        st = {}
    if st.get("session") != sid:                      # yeni session → sıfırla
        st = {"session": sid, "hinted": []}
    if grup in st.get("hinted", []):
        return True
    st.setdefault("hinted", []).append(grup)
    try:
        f.write_text(json.dumps(st), encoding="utf-8", newline="\n")
    except Exception:
        pass
    return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    tool = data.get("tool_name", "") or ""
    ti = data.get("tool_input", {}) or {}

    if tool in _TOOL_TIPI:
        otype = _TOOL_TIPI[tool]
    elif tool in _TIP_TOOLLARI and isinstance(ti, dict):
        otype = ti.get("object_type", "") or ""
    else:
        return 0                                       # SAP-yazma tool'u değil → sessiz

    grup, satir = _checklist(otype)
    if not grup:
        return 0                                       # checklist'i olan bir worktype değil

    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    sid = _session_id(proj)
    if _already_hinted(proj, sid, grup):
        return 0                                       # bu worktype bu session'da hatırlatıldı

    # Yol öneki: core/ junction (öneksiz Read çözülmez — D29).
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # core/scripts
        from utils.inject_paths import core_onekle  # type: ignore
        satir = core_onekle(satir)
    except Exception:
        pass

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": (
                f"[SAP-yazma worktype hatırlatması — DETERMİNİSTİK, obje-tipi='{otype}'] "
                f"{satir}. SAP-yazma öncesi ADR 0006 run_review pre-flight'ı KOŞ (PASS→yaz). "
                "Bu, checklist'i doğru anda hatırlatan fail-closed sigortadır (session'da 1 kez)."
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
