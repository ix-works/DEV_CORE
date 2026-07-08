#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yabancı-proje güvenlik ön-taraması (F1/F3 firewall — D30, iki modlu).

NEDEN: Claude Code bir klasörde açıldığında oradaki hook'lar/MCP server'lar/CLAUDE.md
ONAYSIZ etki eder (hook = keyfi komut çalıştırma). Tanımadığın bir projeyi Claude ile
açmadan ÖNCE davranış-yüzeyini görmek zorundasın.

MOD 0 (varsayılan — Claude'suz, düz python; ÖNCE BU):
    python foreign_project_audit.py C:\\yol\\yabanci-proje
  Dosya-VARLIK envanteri + risk sınıflaması. İçerik çalıştırmaz, import etmez.

MOD 1 (--deep — yine Claude'suz; komut/içerik özeti):
    python foreign_project_audit.py C:\\yol\\yabanci-proje --deep
  Hook komutlarını, MCP server komutlarını, CLAUDE.md import satırlarını LİSTELER
  (yalnız okur). Derin insan-incelemesi için ham madde. Temiz çıkarsa proje
  guest_mode.py ile misafir-modda açılabilir (bkz. scripts/guest_mode.py).

Çıkış kodu: 0 = yüzey boş/temiz · 1 = YÜKSEK-risk yüzey var (incele!) · 2 = kullanım hatası.
"""
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (göreli-yol, risk, neden) — VARLIĞI bile rapor edilir
YUZEY = [
    (".claude/settings.json",       "YÜKSEK", "hook'lar ONAYSIZ çalışır (keyfi komut)"),
    (".claude/settings.local.json", "YÜKSEK", "lokal hook/permission override"),
    (".mcp.json",                   "YÜKSEK", "MCP server = oturumda çalışan süreç"),
    (".claude/hooks",               "YÜKSEK", "hook script klasörü"),
    ("CLAUDE.md",                   "ORTA",   "talimat enjeksiyonu (import zinciri dahil)"),
    ("CLAUDE.local.md",             "ORTA",   "lokal talimat dosyası"),
    (".claude/agents",              "ORTA",   "alt-ajan tanımları (araç yetkileri)"),
    (".claude/commands",            "ORTA",   "slash-komut tanımları"),
    (".claude/skills",              "ORTA",   "skill talimatları"),
    (".claude/plugins",             "ORTA",   "plugin konfigürasyonu"),
    (".claude/memory-seed",         "DÜŞÜK",  "memory tohumları (talimat etkisi dolaylı)"),
]

_HOOK_CMD = re.compile(r'"command"\s*:\s*"([^"]+)"')
_MCP_CMD = re.compile(r'"(command|args|url)"\s*:\s*(\[[^\]]*\]|"[^"]*")')
_IMPORT = re.compile(r"^\s*@\S+", re.M)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    deep = "--deep" in sys.argv
    if len(args) != 1:
        print(__doc__)
        return 2
    kok = Path(args[0])
    if not kok.is_dir():
        print(f"HATA: klasör yok: {kok}")
        return 2

    print(f"═══ YABANCI-PROJE ÖN-TARAMA (mod {'1/deep' if deep else '0'}): {kok} ═══")
    yuksek = 0
    bulgu = 0
    for rel, risk, neden in YUZEY:
        p = kok / rel
        if not p.exists():
            continue
        bulgu += 1
        if risk == "YÜKSEK":
            yuksek += 1
        n = sum(1 for _ in p.rglob("*") if _.is_file()) if p.is_dir() else 1
        print(f"  [{risk:6}] {rel}  ({n} dosya) — {neden}")
        if not deep:
            continue
        try:
            if p.is_file() and p.suffix == ".json" or p.name.endswith(".json"):
                icerik = p.read_text(encoding="utf-8", errors="replace")
                for m in _HOOK_CMD.finditer(icerik):
                    print(f"           komut: {m.group(1)}")
                if p.name == ".mcp.json":
                    for m in _MCP_CMD.finditer(icerik):
                        print(f"           mcp {m.group(1)}: {m.group(2)[:100]}")
            elif p.is_file() and p.suffix == ".md":
                for m in _IMPORT.finditer(p.read_text(encoding="utf-8", errors="replace")):
                    print(f"           import: {m.group(0).strip()}")
            elif p.is_dir():
                for f in sorted(p.rglob("*")):
                    if f.is_file():
                        print(f"           - {f.relative_to(kok)}")
        except Exception as e:
            print(f"           (okunamadı: {e})")

    if bulgu == 0:
        print("  Davranış-yüzeyi dosyası YOK — Claude etkileyecek bir şey bulunamadı.")
    print("═══ SONUÇ:", "⛔ YÜKSEK-risk yüzey VAR — içerikleri incele; onaylamadan bu "
          "klasörde Claude AÇMA (veya guest_mode + hooks'suz aç)" if yuksek
          else "✓ yüksek-risk yüzey yok (ORTA/DÜŞÜK varsa yine göz at)", "═══")
    return 1 if yuksek else 0


if __name__ == "__main__":
    raise SystemExit(main())
