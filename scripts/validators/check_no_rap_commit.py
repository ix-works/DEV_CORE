"""
check_no_rap_commit.py — RAP handler/helper class içinde DB-transaction kontrolü YASAK.

# ENFORCES: BE-26  (ADR 0019 coverage binding)

Neden (canlı post-mortem 2026-06-23): `ZSD001 create_transport_doc` (RAP action
handler'dan çağrılan helper class) içinde `BAPI_TRANSACTION_ROLLBACK/COMMIT` vardı.
RAP managed transaction içinde elle `COMMIT/ROLLBACK WORK` → runtime
`BEHAVIOR_ILLEGAL_STATEMENT` dump (SAPLBAPT) → bağlantı reset → "HTTP request failed".
**Bu hata static-check/syntax/ATC/bug-gate'i GEÇER, yalnız ilk gerçek RUNTIME testinde
çıkar** (bizde 3 bug-gate + syntax + ATC hepsi atladı). Kural prose olarak vardı
(adt-rap.md COMMIT ENTITIES; howto-document-lock COMMIT WORK) ama GATE'siz → atlandı
(ADR 0019: gate'siz kural ≈ kuralsız). Bu validator o boşluğu deterministik kapatır.

DOĞRU DESEN: commit gerektiren klasik BAPI'yi (BAPI_SHIPMENT_CREATE, SD_SCDS_CREATE/VI01...)
RAP'ten çağırırken AYRI LUW kullan → Z RFC-enabled FM + `CALL FUNCTION '...' DESTINATION 'NONE'`.
Commit yalnız o RFC-FM'de (ayrı roll-area) LEGAL. Reçete: playbook/adt-rap.md.

Kapsam: <source_root>/**/*.clas.abap, *.ccimp.abap, *.ccau.abap.
  Muaf: *.func.abap (RFC-FM wrapper = ayrı LUW → commit orada legal; bu validator taramaz).
  Kaçış: ilgili satıra `"#NO_RAP_COMMIT_CHECK <gerekçe>` (gerçek non-RAP class için; gerekçesiz değil).

Bulgular:
  ERROR (BLOCKER): COMMIT WORK · ROLLBACK WORK · BAPI_TRANSACTION_COMMIT ·
                   BAPI_TRANSACTION_ROLLBACK · COMMIT ENTITIES  — class'ta explicit DB-commit.
  WARN: FM-içi-commit sinyali (ör. `i_opt_commit = 'X'`) — çağrılan FM kendi içinde COMMIT WORK
        yapar; RAP'ten DİREKT çağrılırsa aynı dump. DESTINATION 'NONE' wrapper'a taşı. (Elle teyit:
        FM RAP-context'inde mi çağrılıyor.)

Kullanım:
    python scripts/validators/check_no_rap_commit.py
    python scripts/validators/check_no_rap_commit.py --strict   # WARN'ları da fail say

Exit: 0 — ERROR yok (WARN olabilir) · 1 — en az bir ERROR (veya --strict + WARN)
"""
import argparse
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent.parent
ERP = REPO / SOURCE_ROOT_NAME

_SKIP_SEGMENTS = {"node_modules", "dist", "tmp", ".tmp"}
_SCAN_SUFFIXES = (".clas.abap", ".ccimp.abap", ".ccau.abap")
_ESCAPE = "#NO_RAP_COMMIT_CHECK"

# ERROR — KLASİK DB-transaction kontrolü: RAP akışı içinde HER ZAMAN yasak (handler VEYA
#   RAP-LUW'a bağlı helper). Bunlar `COMMIT WORK` yapar → BEHAVIOR_ILLEGAL_STATEMENT.
_ERROR_PATTERNS = [
    (re.compile(r"\bCOMMIT\s+WORK\b", re.IGNORECASE), "COMMIT WORK"),
    (re.compile(r"\bROLLBACK\s+WORK\b", re.IGNORECASE), "ROLLBACK WORK"),
    (re.compile(r"\bBAPI_TRANSACTION_COMMIT\b", re.IGNORECASE), "BAPI_TRANSACTION_COMMIT"),
    (re.compile(r"\bBAPI_TRANSACTION_ROLLBACK\b", re.IGNORECASE), "BAPI_TRANSACTION_ROLLBACK"),
]
# WARN — bağlama-bağlı (deterministik karar veremez; bug-expert context teyit eder):
#   COMMIT ENTITIES = RAP EML commit; CONSUMER/controller'da MEŞRU, behavior HANDLER içinde YASAK.
#   i_opt_commit='X' = çağrılan FM kendi içinde COMMIT WORK yapar; RAP'ten DİREKT çağrı = aynı dump.
_WARN_PATTERNS = [
    (re.compile(r"\bCOMMIT\s+ENTITIES\b", re.IGNORECASE), "COMMIT ENTITIES (handler'da YASAK / consumer'da OK)"),
    (re.compile(r"\bi_opt_commit\s*=\s*'X'", re.IGNORECASE), "i_opt_commit='X' (FM-içi COMMIT)"),
]


def _strip_comment(line: str) -> str:
    """ABAP yorum at: tam-satır `*` → boş; inline `"` → öncesi. ('...' içi `"` nadir, kabul)."""
    if line.lstrip().startswith("*"):
        return ""
    q = line.find('"')
    return line if q < 0 else line[:q]


def _iter_files():
    if not ERP.exists():
        return
    import os
    # PERF: ERP.rglob node_modules'ı (1184 dizin) dolaşıyordu → os.walk ile yürüyüş anında buda.
    for dirpath, dirnames, filenames in os.walk(ERP):
        dirnames[:] = [d for d in dirnames if d.lower() not in _SKIP_SEGMENTS]
        for fn in filenames:
            if fn.lower().endswith(_SCAN_SUFFIXES):
                yield Path(dirpath) / fn


def _scan():
    findings = []  # (severity, label, file, lineno, text)
    for f in _iter_files():
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for i, raw in enumerate(lines, 1):
            if _ESCAPE in raw:
                continue
            code = _strip_comment(raw)
            if not code.strip():
                continue
            for rx, label in _ERROR_PATTERNS:
                if rx.search(code):
                    findings.append(("ERROR", label, f, i, raw.strip()[:120]))
            for rx, label in _WARN_PATTERNS:
                if rx.search(code):
                    findings.append(("WARN", label, f, i, raw.strip()[:120]))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="RAP handler/helper class'ta DB-commit yasağı (BE-26)")
    ap.add_argument("--strict", action="store_true", help="WARN'ları da fail say")
    ap.add_argument("--quick", action="store_true", help="(uyumluluk; bu kontrol zaten hızlı)")
    args = ap.parse_args()

    findings = _scan()
    errors = [x for x in findings if x[0] == "ERROR"]
    warns = [x for x in findings if x[0] == "WARN"]

    if not findings:
        print("RAP commit yasağı (BE-26): temiz (class'ta explicit DB-commit yok).")
        return 0

    for sev, label, f, ln, text in findings:
        rel = f.relative_to(REPO)
        tag = "[İHLAL]" if sev == "ERROR" else "[UYARI]"
        print(f"{tag} {rel}:{ln}  {label}  → {text}")

    print()
    print(f"Özet: {len(errors)} ERROR (explicit DB-commit), {len(warns)} WARN (FM-içi-commit sinyali).")
    if errors:
        print("ERROR = RAP handler/helper class'ta COMMIT/ROLLBACK yasak → runtime BEHAVIOR_ILLEGAL_STATEMENT "
              "dump (static görmez). Commit'i ayrı-LUW RFC-FM'e taşı (DESTINATION 'NONE'); reçete "
              "playbook/adt-rap.md. Gerçek non-RAP class ise satıra `\"#NO_RAP_COMMIT_CHECK <gerekçe>`. Build DURUR.")
    if warns:
        print("WARN = FM kendi içinde COMMIT yapıyor; RAP-context'ten DİREKT çağrılıyorsa aynı dump → "
              "DESTINATION 'NONE' wrapper'a taşı (elle teyit: çağrı RAP handler'dan mı).")

    if errors:
        return 1
    if warns and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
