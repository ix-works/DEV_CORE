#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""behavior_manifest.py — Davranış-yüzeyi manifest üreteci/doğrulayıcısı (F2, §11.3).

Davranış yüzeyi = ajanın davranışını şekillendiren proje-lokal dosyalar. Manifest
(hash envanteri) LİDER-onaylı PR ile güncellenir; session_start her oturum başında
canlı ağacı manifest'le karşılaştırır → kayıtsız/değişmiş dosya = BÜYÜK uyarı.
(Tespit post-load'dur; ÖNLEME F1'dedir — çevre duvarı.)

Kullanım:
  python core/scripts/behavior_manifest.py generate   # .claude/behavior-manifest.json yaz
  python core/scripts/behavior_manifest.py verify     # 0=eş, 1=sapma(rapor stdout)
Kütüphane: verify_quiet(proj) -> list[str] sapma satırları (session_start kullanır).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Davranış-yüzeyi kalemleri (proje-köküne göre). Dizinler özyinelemeli taranır;
# junction'lar (core'dan gelen agents/skills/commands) manifest DIŞI — onların
# bütünlüğü core-git'in işidir; buradaki amaç PROJE-LOKAL sapmaları yakalamak.
YUZEY_DOSYALAR = ["CLAUDE.md", "CLAUDE.local.md", ".mcp.json", "project.yaml",
                  "scripts/hook_shim.py", ".claude/settings.json",
                  ".claude/settings.local.json"]
YUZEY_DIZINLER = [".claude/rules"]  # varsa; nested CLAUDE.md'ler ayrıca taranır
MANIFEST = ".claude/behavior-manifest.json"


def _hash(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _is_junction(p: Path) -> bool:
    try:
        os.readlink(p)
        return True
    except (OSError, ValueError):
        return False


def _topla(proj: Path) -> dict[str, str]:
    kayit: dict[str, str] = {}
    for rel in YUZEY_DOSYALAR:
        p = proj / rel
        if p.is_file():
            kayit[rel.replace("\\", "/")] = _hash(p)
    for rel in YUZEY_DIZINLER:
        d = proj / rel
        if d.is_dir() and not _is_junction(d):
            for f in sorted(d.rglob("*")):
                if f.is_file():
                    kayit[str(f.relative_to(proj)).replace("\\", "/")] = _hash(f)
    # nested CLAUDE.md'ler (kök hariç; core junction'ı atla)
    for f in sorted(proj.rglob("CLAUDE.md")):
        rel = str(f.relative_to(proj)).replace("\\", "/")
        if rel == "CLAUDE.md" or rel.startswith("core/") or "/core/" in rel:
            continue
        if any(seg in rel for seg in ("node_modules/", ".git/", ".tmp/")):
            continue
        kayit[rel] = _hash(f)
    return kayit


def generate(proj: Path) -> Path:
    m = proj / MANIFEST
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text(json.dumps(_topla(proj), indent=1, sort_keys=True), encoding="utf-8")
    return m


def verify_quiet(proj: Path) -> list[str]:
    """Sapma listesi döndürür (boş=temiz). Manifest yoksa tek uyarı satırı."""
    m = proj / MANIFEST
    if not m.exists():
        return ["manifest YOK (.claude/behavior-manifest.json) — üret: "
                "python core/scripts/behavior_manifest.py generate"]
    try:
        beklenen = json.loads(m.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"manifest OKUNAMADI: {e}"]
    canli = _topla(proj)
    sapma: list[str] = []
    for rel, h in canli.items():
        if rel not in beklenen:
            sapma.append(f"KAYITSIZ yeni davranış dosyası: {rel}")
        elif beklenen[rel] != h:
            sapma.append(f"DEĞİŞMİŞ (manifest-onaysız): {rel}")
    for rel in beklenen:
        if rel not in canli:
            sapma.append(f"manifest'te var, diskte YOK: {rel}")
    return sapma


def main() -> int:
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "generate":
        print(f"[ OK ] manifest yazıldı: {generate(proj)} ({len(_topla(proj))} kalem)")
        return 0
    sapmalar = verify_quiet(proj)
    if not sapmalar:
        print("[ OK ] behavior-manifest: canlı ağaç manifest'le EŞ")
        return 0
    print("[FAIL] behavior-manifest SAPMALARI:")
    for s in sapmalar:
        print("   ⛔ " + s)
    print("Onaylıysa: generate ile güncelle (lider-PR disiplini); değilse --safe-mode + lider'e bildir.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
