#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_recall_index.py — U1 JIT-recall için hafif ders-indeksi üretici (radar 2026-08-01).

NE ÜRETİR: <proje>/.tmp/recall-index.json — her kayıt: {id, kaynak, baslik, oz, anahtar[]}.
KAYNAKLAR (pilot kapsamı, bilinçli dar):
  1. Auto-memory MEMORY.md indeks satırları (- [Başlık](dosya.md) — hook-cümlesi)
  2. core/playbook/lessons-learned.md PATTERN başlıkları (+ ilk açıklama cümlesi)

TASARIM İLKELERİ:
  · LLM YOK, embedding YOK — saf sözcük-eşleşme indeksi (Türkçe katlama: İ→i, ı→i,
    ş→s, ğ→g, ü→u, ö→o, ç→c; küçük harf). BM25 yerine ağırlıklı token-kesişimi
    (başlık-token'ı ×3, öz-token'ı ×1) — pilot için yeterli, bakımı sıfır.
  · İndeks İÇERİK taşımaz (tam metin değil) — yalnız başlık+tek-cümle öz+işaretçi.
    Recall-hook bunlardan top-K SATIR enjekte eder; ajan gerekirse kaynağı okur
    (progressive-disclosure; claude-mem "index, not full details" deseni).
  · Üretilmiş artefakt: .tmp/ altında, git'e girmez; bayatlarsa hook fail-open.
    Tazeleme: içerik-sağlık radar turu + istenirse session_start'a eklenebilir (ayrı karar).

Kullanım:  python core/scripts/build_recall_index.py   (proje kökünden)
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

_TR = str.maketrans("İIıŞşĞğÜüÖöÇç", "iiissgguuoocc")
_STOP = {"ve", "ile", "icin", "için", "bir", "bu", "da", "de", "the", "for", "and",
         "yok", "var", "olan", "her", "gate", "check"}


def katla(s: str) -> str:
    return s.translate(_TR).lower()


def tokenle(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_çğıöşü]{3,}", katla(s)) if t not in _STOP]


def memory_kayitlari(memory_md: Path) -> list[dict]:
    out = []
    if not memory_md.is_file():
        return out
    for m in re.finditer(r"^- \[([^\]]+)\]\(([^)]+)\)\s*[—-]\s*(.+)$",
                         memory_md.read_text(encoding="utf-8", errors="replace"), re.M):
        baslik, dosya, oz = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        out.append({"id": f"mem:{dosya}", "kaynak": f"memory/{dosya}",
                    "baslik": baslik, "oz": oz[:160],
                    "anahtar": tokenle(baslik) * 3 + tokenle(oz)})
    return out


def lessons_kayitlari(lessons: Path) -> list[dict]:
    out = []
    if not lessons.is_file():
        return out
    t = lessons.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"^#{2,3}\s*(PATTERN\s*#\d+[^\n]*)\n+([^\n]*)", t, re.M):
        baslik = m.group(1).strip()
        oz = re.sub(r"[*_`>]", "", m.group(2)).strip()[:160]
        out.append({"id": f"pat:{baslik.split(':')[0].strip()}",
                    "kaynak": "core/playbook/lessons-learned.md",
                    "baslik": baslik[:120], "oz": oz,
                    "anahtar": tokenle(baslik) * 3 + tokenle(oz)})
    return out


def main() -> int:
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    mem_dir = Path.home() / ".claude" / "projects"
    # Proje-kökünden memory dizinini çöz (harness şeması: C--<yol-kebap>)
    memory_md = None
    if mem_dir.is_dir():
        aday = sorted(mem_dir.glob("*/memory/MEMORY.md"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        # proje adı geçen en taze eşleşme; yoksa en taze
        isim = katla(proj.name)
        memory_md = next((p for p in aday if isim in katla(str(p))), aday[0] if aday else None)
    kayitlar = []
    if memory_md:
        kayitlar += memory_kayitlari(memory_md)
    kayitlar += lessons_kayitlari(proj / "core" / "playbook" / "lessons-learned.md")

    hedef = proj / ".tmp" / "recall-index.json"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps({"v": 1, "kayit": kayitlar}, ensure_ascii=False, indent=0),
                     encoding="utf-8")
    print(f"[OK] recall-index: {len(kayitlar)} kayıt "
          f"(memory={sum(1 for k in kayitlar if k['id'].startswith('mem:'))}, "
          f"pattern={sum(1 for k in kayitlar if k['id'].startswith('pat:'))}) → {hedef}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
