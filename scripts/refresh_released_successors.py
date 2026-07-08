#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""refresh_released_successors.py — SAP resmi cloudification repo'sundan
(governance/reference/released_successors.json) OTORİTE successor haritasını yeniler.

Kaynak: SAP/abap-atc-cr-cv-s4hc — biz on-prem/PCE → objectReleaseInfo_PCELatest.json.
Çıkardığı: state=notToBeReleased/deprecated + successors dolu objeler, tipe göre
(tables/classes/functions/interfaces). check_released_objects.py 'tables'i kullanır.

Kullanım: python scripts/refresh_released_successors.py
Tetik: deferred-triggers — 3+ ay eski veya S/4 sürüm yükseltme.
"""
import urllib.request, json, sys, io
from datetime import date
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SRC = "https://raw.githubusercontent.com/SAP/abap-atc-cr-cv-s4hc/main/src/objectReleaseInfo_PCELatest.json"
OUT = Path(__file__).resolve().parents[1] / "governance" / "reference" / "released_successors.json"

# TADIR tipi -> JSON bölümü (validator 'tables'i tarar; gerisi referans/ileride)
TYPE_SECTION = {"TABL": "tables", "CLAS": "classes", "FUGR": "functions",
                "FUNC": "functions", "INTF": "interfaces"}
RELEVANT_STATES = {"notToBeReleased", "deprecated", "released_with_restrictions"}

def main():
    print("indiriliyor:", SRC)
    raw = urllib.request.urlopen(urllib.request.Request(SRC, headers={"User-Agent": "curl/8"}), timeout=60).read()
    ori = json.loads(raw).get("objectReleaseInfo", [])
    print("kayit:", len(ori))

    out = {"_meta": {
        "purpose": "Clean Core: non-released obje -> released successor (OTORİTE, SAP resmi JSON'dan üretildi).",
        "source": SRC, "generated": date.today().isoformat(),
        "note": "check_released_objects.py 'tables' kullanır. Çok-successor olabilir (MARA->I_Product+4). "
                "Severity WARNING (ADR 0005-B READ yasak değil; Clean Core Level A tercihi).",
        "refresh": "python scripts/refresh_released_successors.py"}}
    for sec in set(TYPE_SECTION.values()):
        out[sec] = {}

    n = 0
    for o in ori:
        succ = o.get("successors") or []
        if not succ:
            continue
        sec = TYPE_SECTION.get(o.get("objectType", ""))
        if not sec:
            continue
        if o.get("state") not in RELEVANT_STATES:
            continue
        name = (o.get("objectKey") or o.get("tadirObjName") or "").upper()
        if not name:
            continue
        out[sec][name] = {
            "successors": [s.get("tadirObjName") or s.get("objectKey") for s in succ],
            "state": o.get("state"),
            "classification": o.get("successorClassification"),
            "app": o.get("applicationComponent"),
        }
        n += 1

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {s: len(out.get(s, {})) for s in set(TYPE_SECTION.values())}
    print(f"yazildi: {OUT}  | {n} obje | {counts}")

if __name__ == "__main__":
    main()
