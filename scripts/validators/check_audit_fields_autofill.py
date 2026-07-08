#!/usr/bin/env python3
"""check_audit_fields_autofill.py — Audit alanları olan ama setAdmin determination'ı
eksik RAP .bdef dosyalarını yakalar (memory: feedback_audit-alan-autofill-standardi, std 05 §9A).

NEDEN: Tabloda created_by/created_at/changed_by/changed_at gibi audit alanları varsa
RAP behavior'da setAdmin / admin-determination ile OTOMATİK doldurulmalı (idempotent,
instance-guard). Determination yoksa alanlar boş kalır → tutarsız audit izi.

KONSERVATİF tespit: SADECE .bdef dosyaları taranır. Dosya audit alan adı içeriyor AMA
admin/audit determination'ı VEYA set_admin/setadmin token'ı YOKSA WARNING. Audit alanı
net görünmeyen veya zaten determination'ı olan dosya işaretlenmez.

Kullanım:
    python check_audit_fields_autofill.py [--file <path>] [--strict]
    (--file verilmezse <source_root>/ altındaki *.bdef taranır)
Çıkış: 0 temiz/uyarı, 1 ihlal (--strict ile WARNING de fail).
"""
# ENFORCES: BE-11  (ADR 0019 coverage binding)
import argparse
import io
import re
import sys
from pathlib import Path
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[1]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Audit alan adları — created/changed/last-changed by/at çiftleri (case-insensitive).
_AUDIT_FIELDS = re.compile(
    r"\b("
    r"created_by|created_at|changed_by|changed_at|"
    r"createdby|createdat|lastchangedby|lastchangedat|"
    r"localcreatedby|localcreatedat|locallastchangedby|locallastchangedat|"
    r"local_created_by|local_created_at|local_last_changed_by|local_last_changed_at"
    r")\b",
    re.IGNORECASE,
)
# Admin determination zaten var mı? — determination + admin/audit, ya da set_admin/setadmin.
_DETERMINATION_ADMIN = re.compile(
    r"determination[^\n;]*\b(admin|audit)\b|\bset_admin\b|\bsetadmin\b",
    re.IGNORECASE,
)


# B7 fix (2026-07-09): yorum-strip — yorumdaki `// setAdmin` gerçek eksikliği MASKELEMESİN
_BDEF_LINE_C = re.compile(r"//[^\n]*")            # satır-sonu yorum (newline korunur → line_no sabit)
_BDEF_BLOCK_C = re.compile(r"/\*.*?\*/", re.DOTALL)  # blok yorum


def scan_bdef(text):
    """Audit alanı içeren ama admin determination'ı olmayan .bdef ise ilk audit alanını
    (line_no, field) olarak döner; aksi halde boş liste."""
    # determination-var kontrolü YORUM-SIZ metinde (yorumdaki setAdmin false-negative yaratmasın).
    clean = _BDEF_LINE_C.sub("", _BDEF_BLOCK_C.sub("", text))
    if _DETERMINATION_ADMIN.search(clean):
        return []
    for i, raw in enumerate(text.splitlines(), 1):
        line = _BDEF_LINE_C.sub("", raw)  # satırdaki yorumu at (line_no korunur)
        m = _AUDIT_FIELDS.search(line)
        if m:
            return [(i, m.group(1))]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="taranacak dosya (run_review pozisyonel artifact)")
    ap.add_argument("--file")
    ap.add_argument("--strict", action="store_true")
    args, _unknown = ap.parse_known_args()  # run_review ek flag geçebilir → yut

    root = Path(__file__).resolve().parents[2]
    target = args.file or args.path
    if target:
        files = [Path(target)]
    else:
        files = list((root / SOURCE_ROOT_NAME).rglob("*.bdef"))

    total = 0
    for f in files:
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for ln, field in scan_bdef(txt):
            total += 1
            rel = f.relative_to(root) if str(f).startswith(str(root)) else f
            print(f"[İHLAL] {rel}:{ln}  WARNING: audit alanı '{field}' var ama setAdmin/admin "
                  f"determination yok → otomatik doldurma için 'determination setAdmin on save' "
                  f"wire et (std 05 §9A).")

    if total:
        print(f"\n{total} uyarı — audit alanı olan .bdef'te setAdmin determination eksik. "
              f"Idempotent admin-determination ile created/changed alanlarını otomatik doldur.")
        return 1
    print("[OK] audit alanı / setAdmin determination ihlali yok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
