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
# Bölüm SIRASI açık ve sabit: eskiden `set(TYPE_SECTION.values())` geziliyordu — dize hash'i
# süreç başına rastgele olduğundan bölüm sırası her koşumda değişiyor, içerik AYNIYKEN dosyada
# yüzlerce satırlık sahte diff üretiyordu (ölçüldü 2026-10-03: 3 koşu → 2 farklı sıra; içerik
# farkı 0 iken diff 720 satır). Sıra, o tarihte repodaki dosyanınkiyle aynı tutuldu.
SECTIONS = ("classes", "functions", "tables", "interfaces")
assert set(SECTIONS) == set(TYPE_SECTION.values())
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
    for sec in SECTIONS:
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

    # Klasör YOKSA yarat: taze klon/yeni core kökünde `governance/reference/` bulunmaz →
    # eskiden burada FileNotFoundError ile ölüyordu, harita hiç üretilmiyordu ve
    # check_released_objects.py boş harita ile SESSİZCE PASS veriyordu (fail-open).
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Bölüm İÇİ anahtarlar SIRALI: kaynak JSON'un kayıt sırası upstream sürümler arasında
    # değişiyor (FPS02, 2026-09-28) ⇒ içerik aynıyken yine sahte diff (ölçüldü: 0 içerik
    # farkı, 458 satır diff). Successor LİSTELERİNİN sırasına dokunulmaz (kaynak sırası korunur).
    for sec in SECTIONS:
        out[sec] = dict(sorted(out[sec].items()))
    # newline="\n" ŞART: metin kipi Windows'ta her `\n`'i `\r\n` yapar; dosya
    # `.gitattributes` `*.json text eol=lf` altında ⇒ her yenilemede tüm çalışma kopyası
    # CRLF'e dönüyordu (ölçüldü 2026-10-03: 4702/4702 satır CRLF, harita içeriği aynıyken).
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    counts = {s: len(out.get(s, {})) for s in SECTIONS}
    print(f"yazildi: {OUT}  | {n} obje | {counts}")

if __name__ == "__main__":
    main()
