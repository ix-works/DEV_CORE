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


_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")
_LISTE_SATIRI = re.compile(r"^\s*[-*·]\s")


def _fm_description(yol: Path) -> str:
    """Memory dosyasinin frontmatter `description:` alani.

    ⭐ NEDEN VAR (2026-08-21, olculdu): ureteç YALNIZ `- [Baslik](dosya) — ozet` seklindeki
    satirlari goruyordu. Canli MEMORY.md'de **146 liste satiri / 163 link** var, indekse giren **90**
    ⇒ **73 kayit JIT-RECALL'a HIC girmiyordu** ve bunu kimse gormuyordu (sessiz kayip;
    "0 kayit" ile "0 eslesme" ayni cikti). Ozet-cumlesi elle yazilan bir alandir ve
    unutulur; `description:` ise memory YAZIM SOZLESMESININ zorunlu alanidir (olculdu:
    214 dosyanin 213'unde var) ⇒ dogru geri-dusus kaynagi budur, 57 cumleyi elle yazmak
    degil.
    """
    try:
        t = yol.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if not t.startswith("---"):
        return ""
    son = t.find("\n---", 3)
    if son < 0:
        return ""
    m = re.search(r"^description:\s*(.+)$", t[:son], re.M)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def memory_kayitlari(memory_md: Path) -> list[dict]:
    out = []
    if not memory_md.is_file():
        return out
    metin = memory_md.read_text(encoding="utf-8", errors="replace")
    gorulen: set[str] = set()

    # (1) MEVCUT DAVRANIS — `anahtar` formulu (baslik x3 + oz) bilerek AYNEN korunur:
    #     bu tur skorlama davranisini DEGISTIRMEZ, KAPSAMI acar.
    #
    # ⚠ TEK DAVRANISSAL DUZELTME: `\s*` -> `[ \t]*`. `\s` SATIR SONUNU DA KAPSAR, bu yuzden
    # ozet-cumlesi OLMAYAN bir satir, `\s*`in `\n`i yutmasiyla BIR SONRAKI SATIRIN `-`
    # isaretini ayrac sanip o satirin METNINI kendi `oz`u yapiyordu (satir-atlamali
    # kirlenme). Bu, "47 kayit eksik" kusurunun IKINCI, daha sinsi yuzu: kayit VARDI ama
    # ozeti BASKA BIR DERSE aitti -> skorlama yanlis derse puan veriyordu.
    # Olculdu (canli MEMORY.md, 2026-08-21): eski desende 90 kaydin **42'si** komsu satirdan
    # kirlenmisti (lider bagimsiz olctu; kanonik sayi: infra-changelog). Bu kusuru KENDI fixture'i (P1/N1) yakaladi; korpus yazilmadan once
    # gorunmuyordu cunku eski korpusta ozetsiz satir HIC YOKTU.
    for m in re.finditer(r"^- \[([^\]]+)\]\(([^)]+)\)[ \t]*[—-][ \t]*(.+)$", metin, re.M):
        baslik, dosya, oz = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        gorulen.add(dosya)
        out.append({"id": f"mem:{dosya}", "kaynak": f"memory/{dosya}",
                    "baslik": baslik, "oz": oz[:160],
                    "anahtar": tokenle(baslik) * 3 + tokenle(oz)})

    # (2) GERI DUSUS — ozet-cumlesi OLMAYAN indeks satirlari.
    #     ⚠ Kapsam BILEREK `^- [` deseninden GENIS: canli indekste en degerli dersler
    #     `- ⭐ [Baslik](dosya)` / `- ⛔ [...]` seklinde yaziliyor ve dar desen onlari
    #     GORMUYORDU (olculdu: 9 satirin 4'u ⭐/⛔ isaretli). Ayrica bir satirda BIRDEN
    #     COK link olabilir (gruplu referans satirlari) -> her link ayri kayit.
    for satir in metin.splitlines():
        if not _LISTE_SATIRI.match(satir):
            continue
        for baslik, dosya in _MD_LINK.findall(satir):
            baslik, dosya = baslik.strip(), dosya.strip()
            if dosya in gorulen:
                continue
            gorulen.add(dosya)
            oz = _fm_description(memory_md.parent / dosya)
            if not oz:
                continue      # ne ozet ne description -> eskisi gibi kapsam disi (sessiz
                              # uydurma YOK; kaynak yoksa kayit da yok)
            baslik = re.sub(r"[*_`]", "", baslik)
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


def howto_kayitlari(playbook: Path) -> list[dict]:
    """howto-*.md dosyalarindan H1 baslik + ilk anlamli satir (radar-adopt 2026-08-01 eki)."""
    out = []
    for f in sorted(playbook.glob("howto-*.md")):
        t = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^#\s+(.+)$", t, re.M)
        if not m:
            continue
        baslik = m.group(1).strip()[:120]
        m2 = re.search(r"^>?\s*\*\*Tetik:\*\*\s*(.+)$", t, re.M) or              re.search(r"^>?\s*\*\*(?:Ne|Problem[^:]*):\*\*\s*(.+)$", t, re.M)
        oz = (m2.group(1) if m2 else "")[:200]
        out.append({"id": f"how:{f.name}", "kaynak": f"core/playbook/{f.name}",
                    "baslik": baslik, "oz": oz,
                    "anahtar": tokenle(baslik) * 3 + tokenle(oz) * 2})
    return out


def main() -> int:
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    # Memory dizini ÖNCE deterministik slug'dan çözülür (TEK KAYNAK, KAYIT S4); ancak
    # bulunamazsa eski "ada göre en taze eşleşme" sezgisi KORUNUR (recall fail-open'dır,
    # indeks üretememek sessiz bir kayıptır). ⚠ Sezginin son çaresi "en taze HERHANGİ
    # proje"dir → BAŞKA bir projenin hafızası bu projenin recall indeksine girebilir;
    # deterministik yol o riski normal durumda tümden kaldırır.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from utils.claude_paths import auto_memory_dizini, claude_projects_dir
    mem_dir = claude_projects_dir()
    memory_md = None
    kanonik = auto_memory_dizini(proj) / "MEMORY.md"
    if kanonik.is_file():
        memory_md = kanonik
    elif mem_dir.is_dir():
        aday = sorted(mem_dir.glob("*/memory/MEMORY.md"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        # proje adı geçen en taze eşleşme; yoksa en taze
        isim = katla(proj.name)
        memory_md = next((p for p in aday if isim in katla(str(p))), aday[0] if aday else None)
    kayitlar = []
    if memory_md:
        kayitlar += memory_kayitlari(memory_md)
    kayitlar += lessons_kayitlari(proj / "core" / "playbook" / "lessons-learned.md")
    kayitlar += howto_kayitlari(proj / "core" / "playbook")

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
