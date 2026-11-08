#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""q405 fixture'ının SÜREÇ-İÇİ sondası — run.py her çağrıyı AYRI alt süreçte koşar.

Neden alt süreç: `sap_sync_pull` import anında `sys.stdout`'u değiştirir ve modül düzeyinde
`ROOT = project_root()` (env `CLAUDE_PROJECT_DIR`) okur ⇒ her vektör kendi kumunda, temiz bir
yorumlayıcıda koşar (`sys.modules` önbelleği vektörler arasında taşınmaz).

Çıktı sözleşmesi: son satır `@@<json>`. SAP'ye bağlanan hiçbir yol koşmaz — `sap_client` ve
`sap_adt_lib` gereken yerde `sys.modules` üzerinden SAHTE modülle değiştirilir (çağrı kaydedilir,
gerçek istemci hiç import edilmez).
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import types
from pathlib import Path

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]
sys.path.insert(0, str(REPO / "scripts" / "validators"))
sys.path.insert(0, str(REPO / "scripts"))


def cik(x) -> None:
    sys.stdout.write("@@" + json.dumps(x, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def _sahte_sap(kayit: list, metadata: str | None = None) -> None:
    """`sap_client` + `sap_adt_lib` yerine kayıt tutan sahte modüller (gerçek ağ YOK)."""
    class _Adt:
        def search_objects(self, ad, max_results=50):
            kayit.append(ad)
            raise RuntimeError("SAHTE-SAP: arama kaydedildi, ag yok")

    class SAPClient:
        def __init__(self, *a, **k):
            self.adt_client = _Adt()

        def get_object_metadata(self, ad, object_type=None):
            kayit.append(ad)
            return metadata

    m = types.ModuleType("sap_client")
    m.SAPClient = SAPClient
    sys.modules["sap_client"] = m
    sys.modules["sap_adt_lib"] = types.ModuleType("sap_adt_lib")


def main() -> None:
    komut, *a = sys.argv[1:]
    if komut == "tutarsizlik":                     # obj, tip, dosya
        import sap_sync_pull as s
        cik(s._dosya_tutarsizligi(a[0], a[1], Path(a[2])))
    elif komut == "pbe":                           # dosya
        from source_drift import pbe_siniflandir
        cik(pbe_siniflandir(Path(a[0])))
    elif komut == "drift_ad":                      # dosya
        import check_source_drift as c
        cik(c._object_name_from_file(Path(a[0])))
    elif komut == "bul":                           # ad, erp_root
        from source_drift import find_repo_source_file
        f = find_repo_source_file(a[0], erp_root=Path(a[1]))
        cik(f.name if f else None)
    elif komut == "adaylar":                       # ad, erp_root
        from source_drift import _pbe_adaylari
        cik([f.name for f, _s in _pbe_adaylari(a[0], Path(a[1]))])
    elif komut == "includes":                      # ad, erp_root
        from source_drift import find_repo_class_includes
        cik([[k, f.name] for k, f in find_repo_class_includes(a[0], Path(a[1]))])
    elif komut == "komut_adi":                     # kullanıcının ham argümanı, etiket
        import sap_sync_pull as s
        s._ARG_AD = a[0]
        cik(s._komut_adi(a[1]))
    elif komut == "sonuc":                         # kullanıcının ham argümanı, etiket
        import sap_sync_pull as s
        s._ARG_AD = a[0]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = s._sonuc(a[1], "auto", {"blocked_dirty": True, "reason": "r", "repo_path": "P"},
                          "SID", ' --file "P"', komut_tipi="auto")
        cik({"rc": rc, "out": buf.getvalue()})
    elif komut == "auto_stub":                     # ham ad argümanı, dosya
        kayit: list = []
        _sahte_sap(kayit)
        import sap_sync_pull as s
        sys.argv = ["sap_sync_pull.py", a[0], "--type", "auto", "--file", a[1], "--session", "SID"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = s.main()
        cik({"rc": rc, "aranan": kayit, "out": buf.getvalue()})
    elif komut == "ml":                            # pozisyonel artifact yolu
        kayit = []
        _sahte_sap(kayit, metadata='<x adtcore:masterLanguage="TR"/>')
        import runpy
        sys.argv = ["check_sap_master_language.py", a[0]]
        rc = None
        # redirect YOK: betik import anında `sys.stdout.buffer`'ı sarar (StringIO'da buffer yok)
        try:
            runpy.run_path(str(REPO / "scripts" / "validators" / "check_sap_master_language.py"),
                           run_name="__main__")
        except SystemExit as exc:
            rc = exc.code
        cik({"rc": rc, "aranan": kayit})
    else:
        raise SystemExit(f"bilinmeyen komut: {komut}")


if __name__ == "__main__":
    main()
