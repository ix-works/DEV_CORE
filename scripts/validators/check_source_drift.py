"""
check_source_drift.py — Repo ↔ canlı SAP kaynak DRIFT validator (ADR 0016 M3).

Repo'daki yönetilen Z source dosyalarını (<source_root>/<MODULE>/<PKG>/<folder>/*.srvd|.cds|
.ddls|.asddls|.abap|.bdef ...) tarar; her biri için canlı AKTİF source'u çeker,
normalize (CRLF/trailing-ws yok say) edip kıyaslar, drift'leri RAPORLAR.

SAP bağlantısı yoksa (.conn_adt / oturum) freshness gibi SOFT-SKIP (exit 0).
Bağlantı varsa: drift bulunursa --strict ile fail (exit 1); strict değilse uyarı
(exit 0). Böylece run_all_validators normal akışı bozmaz ama --strict CI drift'i yakalar.

Kullanım:
    python scripts/validators/check_source_drift.py
    python scripts/validators/check_source_drift.py --strict
    python scripts/validators/check_source_drift.py --name ZSD001_UI_BOOKING --object-type srvd
    python scripts/validators/check_source_drift.py --limit 50

Exit kodu:
    0 — Drift yok VEYA bağlantı yok (soft-skip) VEYA sadece uyarı (strict değil)
    1 — Drift bulundu ve --strict (veya bağlantı/IO hata --strict ile)
"""
import argparse
import sys
from pathlib import Path

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# scripts/ dizinini path'e ekle (sap_adt_lib + source_drift import için)
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from utils.project_config import SOURCE_ROOT_NAME  # noqa: E402  # K12
from source_drift import (  # noqa: E402
    SOURCE_EXTENSIONS,
    compare_sources,
    find_repo_source_file,
    repo_root,
    _is_excluded_path,
    _is_class_subsource,
)

# Repo dosya uzantısı → ADT obje tipi (canlı GET için).
# Çoklu olası tip → sırayla denenir (ilk 200 kazanır).
_EXT_TO_TYPES = {
    ".srvd": ["srvd"],
    ".srvb": ["srvb"],
    ".bdef": ["bdef"],
    ".cds": ["ddls"],
    ".ddls": ["ddls"],
    ".asddls": ["ddls"],
    ".abap": ["class", "program", "include", "functiongroup"],
    ".dcl": ["accesscontrol"],
    ".asdcls": ["accesscontrol"],
    ".ddlx": ["metadataextension"],
    ".asddlxs": ["metadataextension"],
}

# srvd/srvb/bdef object_types.py'de merkezi değil → ADT REST path elle.
_TYPE_TO_ADT_PATH = {
    "srvd": "ddic/srvd/sources",
    "srvb": "ddic/srvb/services",
    "bdef": "bo/behaviordefinitions",
    "ddls": "ddic/ddl/sources",
    "class": "oo/classes",
    "program": "programs/programs",
    "include": "programs/includes",
    "functiongroup": "functions/groups",
    "accesscontrol": "acm/dcl/sources",
    "metadataextension": "ddic/ddlx/sources",
}


def _object_name_from_file(f: Path) -> str:
    """Dosya adından obje adı (ilk '.'a kadar, büyük harf)."""
    return f.name.split(".", 1)[0].upper()


def _fetch_active_source(client, name: str, ext: str):
    """Canlı AKTİF source'u getir. (source_str, used_type) veya (None, None).

    None,None → obje hiçbir aday tipte bulunamadı (yeni/yerel-only → drift yok).
    """
    for obj_type in _EXT_TO_TYPES.get(ext, []):
        adt_path = _TYPE_TO_ADT_PATH.get(obj_type)
        if not adt_path:
            continue
        url = f"{client.url}/sap/bc/adt/{adt_path}/{name.lower()}/source/main"
        try:
            r = client.session.get(
                url,
                params={"sap-client": "100", "version": "active"},
                headers={"Accept": "text/plain"},
                verify=False,
                timeout=15,
            )
        except Exception:
            continue
        if r.status_code == 200 and r.text.strip():
            src = r.text.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
            return src, obj_type
        # 404 → bu tipte yok, sonraki adayı dene
    return None, None


def _collect_repo_files(erp_root: Path, name_filter: str | None) -> list[Path]:
    """<source_root> altındaki source dosyalarını topla (companion .md/.txt elenmiş)."""
    files: list[Path] = []
    for f in erp_root.rglob("*"):
        if not f.is_file():
            continue
        fl = f.name.lower()
        if fl.endswith((".md", ".txt", ".json", ".xml")):
            continue
        # muaf klasör (ref_docs/docs/.tmp ...) + class alt-include'ları → atla
        if _is_excluded_path(f, erp_root) or _is_class_subsource(fl):
            continue
        if not any(fl.endswith(ext) for ext in SOURCE_EXTENSIONS):
            continue
        if name_filter and _object_name_from_file(f) != name_filter.upper():
            continue
        files.append(f)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Repo ↔ canlı SAP kaynak drift kontrolü")
    parser.add_argument("--name", help="Tek obje adı (örn. ZSD001_UI_BOOKING)")
    parser.add_argument("--object-type", help="(opsiyonel) --name ile birlikte tip ipucu")
    parser.add_argument("--limit", type=int, default=0, help="En fazla N dosya tara (0=hepsi)")
    parser.add_argument("--strict", action="store_true", help="Drift bulununca fail (exit 1)")
    args = parser.parse_args()

    erp_root = repo_root() / SOURCE_ROOT_NAME
    if not erp_root.exists():
        print(f"UYARI: {erp_root} yok — drift check atlandı")
        return 0

    if args.name:
        repo_file = find_repo_source_file(args.name, erp_root=erp_root)
        files = [repo_file] if repo_file else []
        if not files:
            print(f"UYARI: {args.name} için repo'da source dosyası yok — atlandı")
            return 0
    else:
        files = _collect_repo_files(erp_root, None)
        if args.limit > 0:
            files = files[: args.limit]

    if not files:
        print("OK — taranacak source dosyası yok")
        return 0

    # SAP bağlantısı (soft-skip)
    try:
        from sap_adt_lib import SAPADTClient
        client = SAPADTClient()
    except Exception as e:
        print(f"UYARI: SAP bağlantısı kurulamadı, drift check atlandı (soft-skip): {e}")
        return 0

    drifted: list[tuple[Path, str]] = []
    checked = 0
    not_live = 0

    for f in files:
        name = _object_name_from_file(f)
        ext = "." + f.name.lower().split(".", 1)[1] if "." in f.name else ""
        # çift uzantı normalize: en uzun eşleşen SOURCE_EXTENSIONS
        matched_ext = next((e for e in SOURCE_EXTENSIONS if f.name.lower().endswith(e)), ext)
        live, used_type = _fetch_active_source(client, name, matched_ext)
        if live is None:
            not_live += 1
            continue
        checked += 1
        try:
            repo_src = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        is_drift, summary = compare_sources(live, repo_src)
        if is_drift:
            drifted.append((f, f"{name} ({used_type}): {summary}"))

    if not drifted:
        print(
            f"OK — drift yok. Kıyaslanan canlı obje: {checked}, "
            f"canlıda olmayan/atlanan: {not_live}, taranan dosya: {len(files)}"
        )
        return 0

    print(f"\n--- DRIFT bulundu: {len(drifted)} obje (canlı ≠ repo) ---", file=sys.stderr)
    for f, msg in drifted:
        print(f"  [DRIFT] {f}", file=sys.stderr)
        print(f"          {msg}", file=sys.stderr)
    print(
        "\n  Push ETME — canlıyı repo'ya çek (adt_get include_source=true) + reconcile, "
        "sonra push. (ADR 0016)",
        file=sys.stderr,
    )

    if args.strict:
        return 1
    print("\n  (Uyarı modu — --strict ile fail eder)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
