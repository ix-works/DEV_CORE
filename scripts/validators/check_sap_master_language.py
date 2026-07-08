"""
check_sap_master_language.py — Z obje master language = TR doğrula (ADR 0005-D, T10).

Canlı SAP'de bir Z objenin adtcore:masterLanguage'ı TR mi kontrol eder. Post-create
çağrılır (obje aktif olmalı). EN/başka dil → BLOCKER.

Kök sebep (gap-analysis #20): SAPClient session'ında sap-language=TR default header'ı
eklenince create'ler TR master oluyor. Bu validator defense-in-depth: bir create yine
EN üretirse (örn. EN-sticky isim, ya da gelecekte regresyon) yakalar.

Kullanım:
    python scripts/validators/check_sap_master_language.py --name ZSD001_I_X --type ddls
    python scripts/validators/check_sap_master_language.py --name ZCL_X --type class

Exit: 0 = TR (veya obje yok/okunamadı → SKIP), 1 = TR DEĞİL (BLOCKER)
"""
# ENFORCES: C-RAP-LANG-01  (ADR 0019 coverage binding)
import argparse
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/


def main() -> int:
    ap = argparse.ArgumentParser(description="Z obje masterLanguage=TR kontrolü (ADR 0005-D)")
    ap.add_argument("path", nargs="?", help="run_review pozisyonel artifact (ad/tip path'ten türetilir)")
    ap.add_argument("--name", help="obje adı (verilmezse path stem'inden)")
    ap.add_argument("--type", help="ddls/class/... (verilmezse path uzantısından)")
    args, _ = ap.parse_known_args()  # run_review ek flag (--type table vb.) → yut

    # Ad/tip: --name öncelikli; yoksa pozisyonel path stem'inden türet (dosya-adı = obje-adı konvansiyonu).
    name, otype = args.name, args.type
    if not name and args.path:
        fn = Path(args.path).name
        name = fn.split(".")[0]
        if otype is None:
            low = fn.lower()
            otype = "ddls" if any(e in low for e in (".cds", ".ddls", ".asddls")) else (
                "class" if (".clas" in low or ".abap" in low) else None)
    if not name:
        print("SKIP — ne --name ne pozisyonel path verildi; master language kontrol edilemedi")
        return 0
    otype = otype or "class"

    try:
        from sap_client import SAPClient  # type: ignore
        import contextlib
        c = SAPClient()
        with contextlib.redirect_stdout(io.StringIO()):
            md = c.get_object_metadata(name, object_type=otype)
    except Exception as exc:
        print(f"SKIP — SAP okunamadı ({type(exc).__name__}: {exc}); master language kontrol edilemedi")
        return 0

    if not md:
        print(f"SKIP — {name} ({otype}) okunamadı/aktif değil")
        return 0

    m = re.search(r'masterLanguage="(\w+)"', md if isinstance(md, str) else str(md))
    lang = m.group(1) if m else None
    if lang == "TR":
        print(f"OK — {name} masterLanguage=TR (ADR 0005-D ✓)")
        return 0

    print(f"\n[BLOCKER] {name} masterLanguage={lang or '?'} — ADR 0005-D TR bekler.",
          file=sys.stderr)
    print("  Kök sebep: create session'ında sap-language=TR yoksa SAP EN logon'u kullanır. "
          "create_object artık TR header'lı (gap-analysis #20). EN-sticky isimse: TR ilk "
          "yaratımda yakala / TADIR-LANGU reset / yeni isim.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
