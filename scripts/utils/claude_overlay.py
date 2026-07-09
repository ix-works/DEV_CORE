#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`.claude/{agents,skills,commands}` için PROJE-LOKAL overlay kanalı.

SORUN (2026-07-09 denetimi): bu üç dizin core'a junction'dır. Claude Code proje-seviyesi
agent/skill/command'ı YALNIZ bu dizinlerden okur → **proje-özel agent tanımlanamıyordu.**
Sonuç: core'daki jenerik tanımlar projeye dayatılıyor ve genericize sırasında proje
gerçekleri placeholder'a dönüyor (ör. `backend-expert.md`: gerçek bir örnek obje yerine
var olmayan bir ad). "Tahmin yasak" diyen sistem, ajanı tahmine itiyordu.

ÇÖZÜM — OPT-IN overlay:
    <proje>/claude-local/agents/*.md   (COMMIT'Lİ, proje reposunda)
Bu dizin varsa `team_setup` `.claude/agents`'ı **junction yerine gerçek dizin** olarak
üretir: core dosyaları + üzerine proje dosyaları (aynı ad = override).
Yoksa hiçbir şey değişmez — junction kalır (sıfır blast radius).

GÜVENLİK: `.claude/{agents,skills,commands}/` zaten `.gitignore`'da (R1 sızıntı kilidi,
`check_core_not_committed` zorlar) → üretilen core kopyası proje reposuna GİRMEZ.

DRIFT: overlay manifest'i, override edilen her dosyanın **core'daki hash'ini** saklar.
Core güncellenince `check_claude_overlay` uyarır: "core değişti, overlay'i gözden geçir".
Böylece overlay sessizce bayatlamaz.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

TIPLER = ("agents", "skills", "commands")
MANIFEST_ADI = ".overlay-manifest.json"
DAMGA = "<!-- CORE-URETILDI: elle duzenleme; kaynak core/claude/{tip}/{ad} -->\n"


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _junction_mu(p: Path) -> bool:
    try:
        return p.is_dir() and os.path.realpath(p) != os.path.abspath(p)
    except OSError:
        return False


def overlay_kaynagi(proje: Path, tip: str) -> Path:
    return proje / "claude-local" / tip


def overlay_var_mi(proje: Path, tip: str) -> bool:
    k = overlay_kaynagi(proje, tip)
    return k.is_dir() and any(k.glob("*.md"))


def hedef(proje: Path, tip: str) -> Path:
    return proje / ".claude" / tip


def _beklenen(proje: Path, core_root: Path, tip: str) -> dict:
    """Üretilecek dosya kümesi: {ad: (kaynak_yolu, core_hash|None)}"""
    out: dict = {}
    core_dizin = core_root / "claude" / tip
    if core_dizin.is_dir():
        for f in sorted(core_dizin.glob("*.md")):
            out[f.name] = (f, _hash(f))
    for f in sorted(overlay_kaynagi(proje, tip).glob("*.md")):
        core_esi = core_dizin / f.name
        out[f.name] = (f, _hash(core_esi) if core_esi.is_file() else None)
    return out


def materyalize(proje: Path, core_root: Path, tip: str) -> tuple:
    """`.claude/<tip>`'i gerçek dizin olarak üret (core + overlay). -> (ok, mesaj)"""
    if not overlay_var_mi(proje, tip):
        return False, f"overlay yok: {overlay_kaynagi(proje, tip)}"

    h = hedef(proje, tip)
    if _junction_mu(h):
        os.rmdir(h)                     # junction'ı kaldır (hedefe DOKUNMAZ)
    elif h.is_dir():
        shutil.rmtree(h)                # eski üretim
    h.mkdir(parents=True, exist_ok=True)

    beklenen = _beklenen(proje, core_root, tip)
    manifest = {"tip": tip, "dosyalar": {}}
    for ad, (kaynak, core_hash) in beklenen.items():
        icerik = kaynak.read_text(encoding="utf-8", errors="replace")
        proje_ustu = kaynak.parent == overlay_kaynagi(proje, tip)
        if not proje_ustu:
            icerik = DAMGA.format(tip=tip, ad=ad) + icerik
        (h / ad).write_text(icerik, encoding="utf-8")
        manifest["dosyalar"][ad] = {
            "kaynak": "proje" if proje_ustu else "core",
            "core_hash": core_hash,       # override edilen core dosyasının hash'i (drift için)
        }
    (h / MANIFEST_ADI).write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                                  encoding="utf-8")
    n_proje = sum(1 for v in manifest["dosyalar"].values() if v["kaynak"] == "proje")
    return True, f"{tip}: {len(beklenen)} dosya ({n_proje} proje-lokal override)"


def durum(proje: Path, core_root: Path, tip: str) -> tuple:
    """-> (mod, sorunlar)  mod ∈ {'junction','overlay','yok'}"""
    h = hedef(proje, tip)
    if not h.exists():
        return "yok", [f"{tip}: dizin yok"]
    if _junction_mu(h):
        if overlay_var_mi(proje, tip):
            return "junction", [f"{tip}: claude-local/{tip} VAR ama .claude/{tip} hâlâ junction "
                                f"→ proje agent'ları YÜKLENMİYOR. Onarım: team_setup.py --repair-junctions"]
        return "junction", []

    # gerçek dizin → overlay olmalı ve güncel olmalı
    if not overlay_var_mi(proje, tip):
        return "overlay", [f"{tip}: gerçek dizin ama claude-local/{tip} yok → sızıntı riski, elle incele"]

    mf = h / MANIFEST_ADI
    if not mf.is_file():
        return "overlay", [f"{tip}: overlay manifest yok → team_setup.py --repair-junctions"]
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
    except Exception:
        return "overlay", [f"{tip}: overlay manifest okunamadı"]

    sorunlar = []
    beklenen = _beklenen(proje, core_root, tip)
    eksik = set(beklenen) - set(m["dosyalar"])
    fazla = set(m["dosyalar"]) - set(beklenen)
    if eksik:
        sorunlar.append(f"{tip}: overlay'de EKSİK {sorted(eksik)} (core yeni dosya ekledi?)")
    if fazla:
        sorunlar.append(f"{tip}: overlay'de FAZLA {sorted(fazla)} (core sildi?)")

    for ad, kayit in m["dosyalar"].items():
        if kayit["kaynak"] != "proje" or ad not in beklenen:
            continue
        _, guncel_core_hash = beklenen[ad]
        if guncel_core_hash and kayit.get("core_hash") and guncel_core_hash != kayit["core_hash"]:
            sorunlar.append(f"{tip}/{ad}: CORE GÜNCELLENDİ ({kayit['core_hash']} → {guncel_core_hash}) "
                            f"— proje override'ı bayatlamış olabilir, gözden geçir")
    return "overlay", sorunlar
