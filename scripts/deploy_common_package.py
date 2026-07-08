# -*- coding: utf-8 -*-
"""deploy_common_package.py — Ortak paketi (varsayılan ZSD000_CLC) SAP'ye deploy eder.

README Adım 7'nin script'i. `sap_client.SAPClient` (sap_adt_lib wrapper) üzerinden, bağımlılık
sırasıyla deploy eder:
  1) ortak value-help CDS'leri (cds/*.cds)            → create_cds_view + activate
  2) ekran-üreteç FUGR + FM (functions/*.func.abap)   → create_function_group + create_function_module
                                                          + set_function_module_source(activate=True)
  3) ALV template programları (programs/*.prog.abap)  → create_object('program') + push_object (upload+activate)

⛔ PAKET YARATMAZ (ADR 0005-C: paket yaratmayı operatör yapar) — paket SAP'de yoksa önce operatöre yarattır.
⛔ Standart objeye dokunmaz; tüm objeler Z'li (ADR 0005). RFC-enable YAPMAZ
   (SE37 'Remote-Enabled Module' tek-tık manuel; bkz. adt-fugr-functions.md §3) — sonda hatırlatır.

Kullanım:
    python scripts/deploy_common_package.py --transport <TR>
    python scripts/deploy_common_package.py --transport <TR> --package ZSD000_CLC --erp-root ERP/SD --cwd <conn_dir>
    python scripts/deploy_common_package.py --dry-run        # sadece deploy planını göster (SAP'ye dokunmaz)
"""
import argparse
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from sap_adt_lib import set_explicit_working_dir
from sap_client import SAPClient

# TR açıklamalar (obje adına göre; yoksa generic fallback). ADR 0005-D: TR text zorunlu.
DESCRIPTIONS = {
    "ZSD000_I_BPNAME":      "Ortak VH - Is Ortagi Adi",
    "ZSD000_I_VKORGVH":     "Ortak VH - Satis Organizasyonu",
    "ZSD000_I_SHIPTYPEVH":  "Ortak VH - Sevkiyat Turu",
    "ZSD000_FG_SCREEN_GEN": "Ekran + GUI Status Ureteci (FUGR)",
    "ZSD000_FM_SCREEN_GEN": "Dynpro Ekrani + GUI Status Ureteci (RFC)",
    "ZSD000_P_ALV_TEMP1":   "ALV Template - Docking",
    "ZSD000_P_ALV_TEMP2":   "ALV Template - Custom Container",
    "ZSD000_P_ALV_TEMP3":   "ALV Template - Split (Master-Detail)",
}


def desc(name: str) -> str:
    return DESCRIPTIONS.get(name, f"{name} (ortak paket objesi)")


def _name_from(path: Path, suffix: str) -> str:
    """Dosya adından obje adını çıkar (çok-parçalı uzantıyı sıyır: .func.abap / .prog.abap / .cds)."""
    n = path.name
    return n[: -len(suffix)] if n.endswith(suffix) else path.stem


def main() -> int:
    ap = argparse.ArgumentParser(description="Ortak paketi SAP'ye deploy et")
    ap.add_argument("--transport", help="Transport request (ZORUNLU; --dry-run hariç)")
    ap.add_argument("--package", default="ZSD000_CLC", help="Ortak paket (varsayılan ZSD000_CLC)")
    ap.add_argument("--erp-root", default="ERP/SD", help="Paketin bulunduğu kök (varsayılan ERP/SD)")
    ap.add_argument("--cwd", help=".conn_adt içeren çalışma dizini")
    ap.add_argument("--dry-run", action="store_true", help="Sadece planı göster, SAP'ye dokunma")
    args = ap.parse_args()

    if args.cwd:
        set_explicit_working_dir(args.cwd)

    pkg_dir = Path(args.erp_root) / args.package
    if not pkg_dir.is_dir():
        print(f"[FAIL] Paket dizini yok: {pkg_dir}", file=sys.stderr)
        return 1

    cds_files = sorted((pkg_dir / "cds").glob("*.cds"))
    fm_files = sorted((pkg_dir / "functions").glob("*.func.abap"))
    prog_files = sorted((pkg_dir / "programs").glob("*.prog.abap"))

    # Deploy planı (bağımlılık sırası)
    plan = []
    for f in cds_files:
        plan.append(("cds", _name_from(f, ".cds"), f))
    for f in fm_files:
        plan.append(("fm", _name_from(f, ".func.abap"), f))
    for f in prog_files:
        plan.append(("program", _name_from(f, ".prog.abap"), f))

    print(f"=== Ortak paket deploy planı: {args.package} ({pkg_dir}) ===")
    for kind, name, _ in plan:
        print(f"  [{kind:>7}] {name}  — {desc(name)}")
    if not plan:
        print("[FAIL] Deploy edilecek obje bulunamadı.", file=sys.stderr)
        return 1

    if args.dry_run:
        print("\n(dry-run — SAP'ye dokunulmadı)")
        print("Sonra: --transport <TR> ile çalıştır; bitince SE37'de ZSD000_FM_SCREEN_GEN → Remote-Enabled Module.")
        return 0

    if not args.transport:
        print("[FAIL] --transport zorunlu. list_transports.py --modifiable-only ile öğren, "
              "KULLANICIYA SOR (asla uydurma).", file=sys.stderr)
        return 1

    client = SAPClient()
    tr = args.transport
    results = []  # (name, ok, note)

    for kind, name, f in plan:
        src = f.read_text(encoding="utf-8")
        try:
            if kind == "cds":
                client.create_cds_view(name, src, desc(name), args.package, transport=tr)
                ok = client.activate_object(name, "cds")
                results.append((name, bool(ok), "create+activate"))

            elif kind == "fm":
                fg = name.replace("_FM_", "_FG_")
                client.create_function_group(fg, desc(fg), args.package, transport=tr)       # idempotent
                client.create_function_module(name, fg, desc(name), transport=tr)            # idempotent (shell)
                res = client.adt_client.set_function_module_source(name, fg, src, transport=tr, activate=True)
                ok = bool(res.get("activation", {}).get("success", True)) if isinstance(res, dict) else True
                results.append((name, ok, f"FG={fg} + source+activate"))

            elif kind == "program":
                client.create_object("program", name, args.package, desc(name), transport=tr)  # shell (idempotent)
                res = client.push_object(name, "program", transport=tr, source_file=str(f))     # upload+activate
                ok = bool(res.get("success", False)) if isinstance(res, dict) else bool(res)
                results.append((name, ok, res.get("error", "") if isinstance(res, dict) else ""))

        except Exception as e:  # idempotent-tolerant: zaten-var vb. logla, devam et
            results.append((name, False, f"{type(e).__name__}: {e}"))

    print("\n=== Sonuç ===")
    fail = 0
    for name, ok, note in results:
        print(f"  {'[OK]  ' if ok else '[FAIL]'} {name}  {('— ' + note) if note else ''}")
        if not ok:
            fail += 1

    print("\n⚠️ SON ADIM (manuel): SE37 → ZSD000_FM_SCREEN_GEN → Attributes → "
          "Processing Type = Remote-Enabled Module (SOAP-RFC çağrısı için ŞART). "
          "Bkz. playbook/adt-fugr-functions.md §3.")
    if fail:
        print(f"\n[FAIL] {fail} obje deploy edilemedi — yukarıyı incele, kullanıcıya raporla "
              "(başarılı deme).", file=sys.stderr)
        return 1
    print("\n[OK] Ortak paket deploy edildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
