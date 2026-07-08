#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""program_to_spec.py — ABAP/CDS source → taslak FS/TS iskeleti (gap-analysis #4).

Tersine mühendislik: <LEGACY_SOURCE> (SEVKEMRI) veya Z source'tan GERÇEK teknik fact'leri
(tablolar, ekranlar, FM'ler, selection params, FORM/METHOD'lar, CDS entity) çıkarır;
standards/04 hizalı bir FS/TS TASLAĞI üretir.

⚠️ KURAL (ADR / feedback_zli-obje-text-tahmin-yasak):
  - Bu script SADECE source'ta GERÇEKTEN olan'ı çıkarır (uydurmaz).
  - Narrative bölümleri (Amaç/İş Kuralları/TO-BE) <TODO: ...> olarak bırakılır —
    coordinator gerçek source + <LEGACY_SOURCE> app davranışından doldurur.
  - Çıktı TASLAKtır → spec-mutabakat gate ZORUNLU (kullanıcı onayı olmadan build yok).

Kullanım:
    python scripts/program_to_spec.py <source.abap> [<source2.abap> ...] [--out TD/DRAFT_X.md]
    python scripts/program_to_spec.py <source_root>/SD/SEVKEMRI/sources/ZSD_007_*.abap
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_PATTERNS = {
    "tables": re.compile(r'\bTABLES?\s*:?\s+(\w+)', re.IGNORECASE),
    "select_from": re.compile(r'\b(?:FROM|JOIN)\s+(\w+)', re.IGNORECASE),
    "params": re.compile(r'\bPARAMETERS?\s*:?\s+(\w+)', re.IGNORECASE),
    "selopts": re.compile(r'\bSELECT-OPTIONS\s*:?\s+(\w+)', re.IGNORECASE),
    "call_func": re.compile(r"\bCALL\s+FUNCTION\s+'([^']+)'", re.IGNORECASE),
    "bapi": re.compile(r"\bCALL\s+FUNCTION\s+'(BAPI_\w+)'", re.IGNORECASE),
    "forms": re.compile(r'\bFORM\s+(\w+)', re.IGNORECASE),
    "methods": re.compile(r'\bMETHODS?\s*:?\s+(\w+)', re.IGNORECASE),
    "screens": re.compile(r'\b(?:CALL|SET)\s+SCREEN\s+(\d+)', re.IGNORECASE),
    "classes": re.compile(r'\bCLASS\s+(\w+)\s+DEFINITION', re.IGNORECASE),
    "cds_entity": re.compile(r'\bdefine\s+(?:root\s+)?view\s+entity\s+(\w+)', re.IGNORECASE),
    "report": re.compile(r'\bREPORT\s+(\w+)', re.IGNORECASE),
    "func_pool": re.compile(r'\bFUNCTION-POOL\s+(\w+)', re.IGNORECASE),
}
# Standart SAP tabloları (ihtimal) — büyük harf, 3+ ve Z ile başlamayan
_STD_TABLE_HINT = re.compile(r'^[A-Y]\w{2,}$')


def _uniq(seq):
    seen, out = set(), []
    for x in seq:
        u = x.upper()
        if u not in seen:
            seen.add(u); out.append(x)
    return out


def extract(text: str) -> dict:
    text = "\n".join(l for l in text.splitlines() if not l.strip().startswith("*"))
    facts = {}
    for key, rx in _PATTERNS.items():
        facts[key] = _uniq(rx.findall(text))
    return facts


def render(facts: dict, sources: list[str]) -> str:
    prog = (facts["report"] or facts["func_pool"] or facts["classes"]
            or facts["cds_entity"] or ["<obje>"])[0]
    tables = _uniq(facts["tables"] + facts["select_from"])
    std_tables = [t for t in tables if _STD_TABLE_HINT.match(t.upper()) and not t.upper().startswith("Z")]
    z_tables = [t for t in tables if t.upper().startswith("Z")]
    L = []
    w = L.append
    w(f"# TASLAK FS/TS — {prog}")
    w("")
    w("> ⚠️ **OTOMATİK TASLAK** (`program_to_spec.py`). Teknik fact'ler source'tan çıkarıldı; ")
    w("> narrative `<TODO>`'lar coordinator tarafından **gerçek source + <LEGACY_SOURCE> davranışından** ")
    w("> doldurulur (tahmin yok). **Spec-mutabakat gate zorunlu** — onaysız build yok.")
    w("")
    w(f"**Kaynak dosya(lar):** {', '.join(sources)}")
    w(f"**Şablon:** `standards/04-documentation-fs-ts.md`")
    w("")
    w("---")
    w("## FS — Fonksiyonel (taslak)")
    w("")
    w("### 2.1 Amaç")
    w("<TODO: <LEGACY_SOURCE> app'inin bu programı ne için kullandığını gerçek davranıştan yaz>")
    w("### 2.2 Kapsam")
    w("<TODO: kapsam>")
    w("### 3. İş Süreci (AS-IS → TO-BE)")
    w("<TODO: AS-IS <LEGACY_SOURCE> akışı; TO-BE yeni sistem akışı>")
    w("### 4.2 İş Kuralları")
    w("<TODO: validation/determination kuralları — source'taki FORM/METHOD mantığından>")
    w("### 5.1 Ekran Listesi")
    if facts["screens"]:
        for s in facts["screens"]:
            w(f"- Dynpro {s}  <TODO: amaç>")
    else:
        w("- <ekran yok / liste-rapor> ")
    w("")
    w("---")
    w("## TS — Teknik (taslak, source'tan çıkarıldı)")
    w("")
    w(f"**Ana obje:** {prog}")
    w("")
    w("### Kullanılan tablolar")
    if std_tables:
        w(f"- **Standart (teyit et — sistemde var mı, ADR 0005-A okuma):** {', '.join(std_tables)}")
    if z_tables:
        w(f"- **Z tablolar:** {', '.join(z_tables)}")
    if not tables:
        w("- <tespit edilemedi>")
    w("")
    w("### Selection ekranı")
    sel = facts["params"] + facts["selopts"]
    w(f"- Parametre/SELECT-OPTIONS: {', '.join(sel) if sel else '<yok>'}")
    w("")
    w("### Çağrılan Function Module / BAPI")
    if facts["call_func"]:
        for fn in facts["call_func"]:
            tag = " (BAPI — released mı? ADR 0005-B)" if fn.upper().startswith("BAPI_") else ""
            w(f"- `{fn}`{tag}")
    else:
        w("- <yok>")
    w("")
    w("### Modülerleştirme")
    if facts["forms"]:
        w(f"- FORM rutinleri (klasik): {', '.join(facts['forms'][:30])}")
    if facts["methods"]:
        w(f"- METHOD'lar (OO): {', '.join(facts['methods'][:30])}")
    if facts["classes"]:
        w(f"- CLASS'lar: {', '.join(facts['classes'])}")
    if facts["cds_entity"]:
        w(f"- CDS entity: {', '.join(facts['cds_entity'])}")
    w("")
    w("### RAP/klasik kararı (coordinator)")
    w("<TODO: Z transactional doküman → RAP managed | std doküman sarıyor → unmanaged/klasik "
      "(standards/05 §2). Liste-rapor → klasik ALV (standards/06) veya read-only RAP.>")
    w("")
    w("> Sonraki adım: bu taslağı düzelt → **spec-mutabakat** → build.")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="ABAP/CDS source → taslak FS/TS")
    ap.add_argument("sources", nargs="+", help="Source dosya(lar)ı")
    ap.add_argument("--out", help="Çıktı .md yolu (yoksa stdout)")
    args = ap.parse_args()

    merged = {k: [] for k in _PATTERNS}
    used = []
    for s in args.sources:
        p = Path(s)
        if not p.exists():
            print(f"[uyarı] {p} yok, atlandı", file=sys.stderr); continue
        used.append(s)
        f = extract(p.read_text(encoding="utf-8", errors="replace"))
        for k in merged:
            merged[k].extend(f[k])
    for k in merged:
        merged[k] = _uniq(merged[k])
    if not used:
        print("HATA: geçerli source yok", file=sys.stderr); return 1

    doc = render(merged, used)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(doc + "\n", encoding="utf-8")
        print(f"[OK] Taslak yazıldı: {args.out}  (düzelt → spec-mutabakat → build)")
    else:
        print(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
