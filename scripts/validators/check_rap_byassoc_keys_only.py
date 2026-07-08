"""
check_rap_byassoc_keys_only.py — RAP ccimp/class'larda keys-only BY-assoc read tuzağı (SOFT/WARNING).

Tuzak (standards/05 §5 · bug-checklist BE-20 · feedback_rap-by-assoc-read-all-fields):
  READ ENTITIES ... ENTITY parent BY \\_child FROM <key> RESULT lt
  -> child'ın YALNIZ KEY alanlarını döner; non-key (tarih/durum/tip/tutar) INITIAL kalır
  -> validation/determination SESSİZCE yanlış çalışır (syntax 0-error, RUNTIME'da çıkar).
  Non-key okuyacaksan ALL FIELDS WITH / FIELDS (...) WITH (FROM değil) ŞART.

Bu validator HARD blok DEĞİL (her FROM read bug değil — yalnız existence/line_exists için meşru).
`READ ENTITIES ... BY \\_assoc ... FROM ...` read'lerini (ALL FIELDS / FIELDS ( olmayan) WARNING
olarak listeler → reviewer/bug-expert BE-20 ile "non-key alan okunuyor mu" doğrular.

Kullanım: python scripts/validators/check_rap_byassoc_keys_only.py
Exit: her zaman 0 (soft). Bulgu varsa stdout'a uyarı yazar.
"""
# ENFORCES: BE-20  (ADR 0019 coverage binding)
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[2]
ERP = REPO / "ERP"

# READ ENTITIES ... BY \_assoc ... (FROM | ALL FIELDS WITH | FIELDS ( ) ... RESULT
# Statement = "READ ENTITIES" ... "RESULT" arası (çok satır).
READ_STMT = re.compile(
    r"READ\s+ENTITIES\b.*?\bRESULT\b", re.IGNORECASE | re.DOTALL)
BY_ASSOC = re.compile(r"BY\s+\\_\w+", re.IGNORECASE)
SAFE = re.compile(r"\bALL\s+FIELDS\s+WITH\b|\bFIELDS\s*\(", re.IGNORECASE)
USES_FROM = re.compile(r"\bFROM\b", re.IGNORECASE)


def main() -> int:
    findings = []
    import os
    _prune = {"node_modules", "dist", ".tmp", "tmp", ".git"}
    abap_files = []
    for dirpath, dirnames, filenames in os.walk(ERP):  # PERF: node_modules budama
        dirnames[:] = [d for d in dirnames if d.lower() not in _prune]
        abap_files += [Path(dirpath) / fn for fn in filenames if fn.endswith(".abap")]
    for f in abap_files:
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in READ_STMT.finditer(txt):
            stmt = m.group(0)
            m_assoc = BY_ASSOC.search(stmt)
            if not m_assoc:
                continue          # BY-assoc read değil
            if SAFE.search(stmt):
                continue          # ALL FIELDS WITH / FIELDS ( -> güvenli
            if not USES_FROM.search(stmt):
                continue
            line_no = txt[: m.start()].count("\n") + 1
            rel = f.relative_to(REPO).as_posix()
            findings.append((rel, line_no, m_assoc.group(0)))

    if findings:
        print("[WARN] keys-only BY-assoc read aday(lar)ı (BE-20 ile doğrula — non-key alan okunuyorsa ALL FIELDS WITH):")
        for rel, ln, assoc in findings:
            print(f"   {rel}:{ln}  READ ENTITIES ... {assoc} ... FROM (ALL FIELDS/FIELDS WITH yok)")
        print("   → Yalnız existence/line_exists ise OK; non-key alan (ls-Field) okunuyorsa ALL FIELDS WITH kullan.")
    else:
        print("[OK] keys-only BY-assoc read aday'ı yok (tüm BY-assoc read'ler ALL FIELDS/FIELDS WITH veya existence-only).")
    return 0   # SOFT


if __name__ == "__main__":
    sys.exit(main())
