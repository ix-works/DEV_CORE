#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reviewer_tip_kapsam fixture — push'un kabul ettigi HER tip reviewer haritasinda BEYANLI mi?

NEDEN VAR (2026-08-01 adversarial bug-avi, W2-MCPT-03 / MG-02):
Push katmani tip ESANLAMLILARINI kabul ediyor (`_TYPE_KEY_CANON`, `_ACTIVATION_URI_SEG`,
`_SOURCE_BASED_TYPES`), reviewer haritasi ise yalniz kanonik adlari taniyordu. Eksik anahtar
-> `.get()` None -> ADR 0006 pre-flight SESSIZCE atlanir. Olculdu:
    object_type="ddls"  -> BLOCKER + push RED
    object_type="cds"   -> SKIP     + push GECTI      (ayni obje, ayni ADT URL'i)
Ayni asimetri `tabl` <-> `table`/`structure`'da vardi ve orada sonucu daha agir:
`table_update` zinciri `check_table_field_drop` (VERI-KAYBI BLOCKER'i) tasir.

ASIL KUSUR TEK BIR EKSIK ANAHTAR DEGIL, IKI TABLONUN SESSIZCE AYRISABILMESIYDI.
Bu test o ayrismayi kalici olarak gorunur kilar: yeni bir tip push'a eklenip reviewer
haritasi unutulursa BURASI KIRILIR.

AYRIM (onemli): "eksik anahtar" ile "bilincli None" ayni sey DEGILDIR.
  - eksik  -> sessiz atlama = BUG
  - None   -> kayda gecmis karar ("zincir henuz yok") = kabul
Bu yuzden test ANAHTAR VARLIGI arar, deger DOLULUGU degil.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "mcp_servers").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))


def _yukle(rel: str, ad: str):
    spec = importlib.util.spec_from_file_location(ad, REPO / rel)
    m = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    sys.modules[ad] = m
    spec.loader.exec_module(m)                          # type: ignore[union-attr]
    return m


def main() -> int:
    rv = _yukle("mcp_servers/sap_adt/_reviewer.py", "rv_fx")
    # atom `_app`/`_reviewer` import eder; tablolari METIN olarak degil MODUL olarak almak
    # icin paket yolu gerekir. Import zinciri kurulamazsa SESSIZ GECME yerine FAIL.
    try:
        atom = _yukle("mcp_servers/sap_adt/tools/atom.py", "atom_fx")
    except Exception as exc:                            # pragma: no cover
        print(f"  [FAIL] atom yuklenemedi (sessiz gecme YOK): {exc}")
        return 1

    harita = rv.OBJECT_TYPE_TO_TASK
    kabul: set[str] = set()
    kabul |= set(getattr(atom, "_TYPE_KEY_CANON", {}).keys())
    kabul |= set(getattr(atom, "_ACTIVATION_URI_SEG", {}).keys())
    kabul |= set(getattr(atom, "_SOURCE_BASED_TYPES", set()))
    kabul |= set(getattr(atom, "_DDIC_XML_TYPES", set()))

    if not kabul:
        print("  [FAIL] push tip tablolari BOS okundu — test hicbir sey olcmuyor")
        return 1

    eksik = sorted(t for t in kabul if t not in harita)
    sonuc = []
    sonuc.append(("push'un kabul ettigi tipler reviewer haritasinda BEYANLI",
                  not eksik, f"kabul={len(kabul)} eksik={eksik or 'yok'}"))

    # KONTROL GRUBU: bilinen dogru esleme hala duruyor mu (test kendi kendini kandirmasin)
    sonuc.append(("kontrol: ddls -> cds_update", harita.get("ddls") == "cds_update",
                  str(harita.get("ddls"))))
    sonuc.append(("kontrol: tabl -> table_update", harita.get("tabl") == "table_update",
                  str(harita.get("tabl"))))
    # ESANLAMLI ESITLIGI: ayni ADT hedefine yazan tipler AYNI task'i vermeli
    sonuc.append(("esanlamli esitligi: cds/cdsview/ddl == ddls",
                  {harita.get(k) for k in ("cds", "cdsview", "ddl")} == {harita.get("ddls")},
                  str({k: harita.get(k) for k in ("cds", "cdsview", "ddl", "ddls")})))
    sonuc.append(("esanlamli esitligi: table/structure == tabl (VERI-KAYBI guard'i)",
                  {harita.get(k) for k in ("table", "structure")} == {harita.get("tabl")},
                  str({k: harita.get(k) for k in ("table", "structure", "tabl")})))
    # task_for_push gercekten cozuyor mu (harita dogru ama fonksiyon yanlissa yakala)
    sonuc.append(("task_for_push('table') veri-kaybi zincirini veriyor",
                  rv.task_for_push("table") == "table_update", str(rv.task_for_push("table"))))
    sonuc.append(("task_for_push('CDS') buyuk-harfte de cozuluyor",
                  rv.task_for_push("CDS") == "cds_update", str(rv.task_for_push("CDS"))))

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
