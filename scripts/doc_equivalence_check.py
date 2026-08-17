#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""doc_equivalence_check.py — doküman yeniden-yazımında VERİ KAYBI ölçer (DOC-FS-07, İLKE-2b).

Kullanım:
  python scripts/doc_equivalence_check.py --old ESKI.md --new YENI.md [--new EK-B.md ...] [--report RAPOR.md]

"Yeni" = birden çok dosya olabilir (yeni FS gövdesi + EK "Karar ve Kanıt Günlüğü" + RESEARCH…):
eski dokümandan çıkan her bilgi bu KÜMENİN içinde bulunmalıdır. Dört ölçüm:
  1. KİMLİK kümeleri  : FR-/BR-/AC-/T-/TC-/ÖK-/G/KI-/BG-/SF-/DÖ-/R-/S-/N-/SCR-/hata kodu (P-/C-/O-/L-/M-/F-/B-)
                        eski \\ yeni = boş olmalı (yeni'de fazlası serbest).
  2. MOCKUP blokları  : ``` kod blokları (kutulu ekran taslağı) — eski bloğun içerik satırlarının ≥%90'ı yeni'de.
  3. DEĞERLER         : tablo/alan/tcode/obje adları (BÜYÜK_HARF_ALT_ÇİZGİ ≥4), 4+ haneli sayılar, tarih (GG.AA.YYYY),
                        `kod` işaretli tokenlar — eski \\ yeni = boş.
  4. CÜMLELER (bulanık): eski gövdenin her cümlesi (≥40 karakter, tablo satırları hücrelere bölünür) yeni kümede
                        difflib oranı ≥0.72 ile bulunmalı; bulunmayanlar listelenir (insan gözden geçirir:
                        "gerçekten silindi mi, yoksa yeniden ifade mi edildi").
Çıktı: özet + eksik listeleri; exit 0 = 1-2-3'te sıfır kayıp VE 4'te kayıp oranı ≤ eşik (--sentence-loss-max, vars. %3);
aksi 1. Rapor dosyası (--report) doc-gate reviewer'a kanıt olarak verilir.
"""
from __future__ import annotations
import argparse
import difflib
import re
import sys
from pathlib import Path

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

ID_RES = [
    r"\bFR-\d{3}\b", r"\bBR-\d{3}\b", r"\bAC-\d{2,3}[a-z]?\b", r"\bTC?-\d{2,3}\b", r"\bÖK-\d{2}\b",
    r"\bG\d{1,2}(?:-P)?\b", r"\bKI-\d{2}\b", r"\bBG-\d{2}\b", r"\bSF-\d{2}\b", r"\bDÖ-\d{2}\b",
    r"\bR-\d{1,2}\b", r"\bS-\d{1,2}[a-d]?\b", r"\bN-\d\b", r"\bSCR-\d{3}\b", r"\bU-\d{2}\b",
    r"\b[PCOLMFB]-\d{2}\b",  # hata kodları
    r"\bK\d{1,2}\b",          # kullanıcı isteği/karar (K1..K11)
]
VALUE_RES = [
    r"\b[A-ZÇĞİÖŞÜ][A-Z0-9ÇĞİÖŞÜ_/]{3,}\b",   # ZSD001_T_HEAD, TVAK, VBRK-FKDAT, /NS/… gibi obje/alan adları
    r"\b\d{4,}\b",                             # 4+ haneli sayı (belge no, adet, cari no)
    r"\b\d{2}\.\d{2}\.\d{4}\b",                # tarih
    r"`[^`\n]{2,60}`",                         # kod tokenı
]
STOP_VALUES = {"YENİ", "HAZIR", "TAMAMLANDI", "İPTAL", "ONAY", "EVET", "HAYIR", "TÜMÜ", "GATE", "HIGH", "MEDIUM", "LOW"}


def read(p: str) -> str:
    return Path(p).read_text(encoding="utf-8", errors="replace")


def ids(text: str) -> set[str]:
    out = set()
    for r in ID_RES:
        out.update(re.findall(r, text))
    return out


def values(text: str) -> set[str]:
    out = set()
    for r in VALUE_RES:
        for m in re.findall(r, text):
            m = m.strip("`")
            if m in STOP_VALUES or len(m) < 4:
                continue
            out.add(m)
    return out


def code_blocks(text: str) -> list[list[str]]:
    blocks, cur, inb = [], [], False
    for ln in text.splitlines():
        if ln.strip().startswith("```"):
            if inb and cur:
                blocks.append(cur)
            cur, inb = [], not inb
            continue
        if inb:
            cur.append(ln.rstrip())
    return blocks


def sentences(text: str) -> list[str]:
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("```") or s.startswith("|---") or s.startswith("#"):
            continue
        parts = [c.strip() for c in s.split("|")] if s.startswith("|") else re.split(r"(?<=[.!?;])\s+", s)
        for p in parts:
            p = re.sub(r"[*_`>]+", "", p).strip()
            if len(p) >= 40:
                out.append(p)
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*_`>|]+", "", s)).strip().lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", action="append", required=True, help="tekrarlanabilir: yeni FS + EK + …")
    ap.add_argument("--report", default=None)
    ap.add_argument("--sentence-loss-max", type=float, default=3.0, help="yüzde; varsayılan 3")
    ap.add_argument("--fuzzy", type=float, default=0.72)
    a = ap.parse_args()

    old = read(a.old)
    new = "\n".join(read(p) for p in a.new)
    lines = []
    P = lines.append

    # 1 kimlikler
    mi = sorted(ids(old) - ids(new))
    P(f"## 1. Kimlik kümeleri — eski {len(ids(old))} · yeni {len(ids(new))} · EKSİK {len(mi)}")
    if mi:
        P("  " + ", ".join(mi))

    # 2 mockup
    nb_lines = {norm(l) for b in code_blocks(new) for l in b if l.strip()}
    lost_blocks = []
    ob = code_blocks(old)
    for k, b in enumerate(ob, 1):
        content = [norm(l) for l in b if l.strip()]
        if not content:
            continue
        hit = sum(1 for l in content if l in nb_lines)
        ratio = hit / len(content)
        if ratio < 0.9:
            lost_blocks.append((k, ratio, b[0][:80]))
    P(f"## 2. Mockup/kod blokları — eski {len(ob)} · ≥%90 korunmayan {len(lost_blocks)}")
    for k, r, head in lost_blocks:
        P(f"  blok #{k} korunma %{r*100:.0f} — {head}")

    # 3 değerler
    mv = sorted(values(old) - values(new))
    P(f"## 3. Değerler (tablo/alan/tcode/sayı/tarih/kod) — eski {len(values(old))} · EKSİK {len(mv)}")
    if mv:
        P("  " + ", ".join(mv[:200]) + (" …" if len(mv) > 200 else ""))

    # 4 cümleler
    ns = [norm(s) for s in sentences(new)]
    ns_set = set(ns)
    lost = []
    osents = sentences(old)
    for s in osents:
        n = norm(s)
        if n in ns_set:
            continue
        best = difflib.get_close_matches(n, ns, n=1, cutoff=a.fuzzy)
        if not best:
            lost.append(s)
    pct = 100.0 * len(lost) / max(1, len(osents))
    P(f"## 4. Cümleler (bulanık ≥{a.fuzzy}) — eski {len(osents)} · bulunmayan {len(lost)} (%{pct:.1f}; eşik %{a.sentence_loss_max})")
    for s in lost[:400]:
        P(f"  - {s[:200]}")

    ok = not mi and not lost_blocks and not mv and pct <= a.sentence_loss_max
    P("")
    P("SONUÇ: " + ("DENK — veri kaybı yok (1-3 sıfır, 4 eşik altı)" if ok else "KAYIP VAR — yukarıdaki listeler kapatılmadan onaya çıkmaz"))
    text = "\n".join(lines)
    print(text)
    if a.report:
        Path(a.report).write_text("# Doküman denklik raporu\n\n- eski: `%s`\n- yeni: %s\n\n%s\n" % (
            a.old, ", ".join("`%s`" % p for p in a.new), text), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
