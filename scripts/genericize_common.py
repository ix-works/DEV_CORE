#!/usr/bin/env python3
"""Genericize/sızıntı desenleri — `core_precommit` + `pre_tool_guard` TEK KAYNAK (D9).

Bu iki guard 2026-07-10'a kadar AYRI listelerden besleniyordu: `pre_tool_guard`
`<proje>/.claude/genericize-blocklist.txt`'ten, `core_precommit`
`<git-dir>/genericize-blocklist`'ten. Biri güncellenip diğeri unutulabiliyordu; üstelik
çözümleme cwd'ye bağlıydı. Artık ikisi de buradan okur ve HER İKİ konumu birleştirir.

⚠ İSİM LİSTESİ BU DOSYADA TUTULMAZ. DEV_CORE **public**tir; müşteri/sistem/kişi adını
buraya yazmak, engellemeye çalıştığımız sızıntının kendisidir.

Kaynak sırası (hepsi BİRLEŞİR, ilk-bulan-kazanır DEĞİL):
  1. env `IX_GENERICIZE_BLOCKLIST` (virgülle ayrılmış)   ← CI secret'i buraya
  2. `<git-dir>/genericize-blocklist`                     ← repo ağacı DIŞI, klonlanmaz
  3. `<proje-kökü>/.claude/genericize-blocklist.txt`      ← gitignore'lu
  4. yapısal (isimsiz) desenler — HER ZAMAN eklenir

Yapısal desenler isim içermediği için public'te güvenlidir ve taze klonda/CI'da da
çalışır. Ama isim-listesi YOKSA koruma yarımdır → `blocklist_var_mi()` ile fail-closed
davranmak arayanın sorumluluğudur (CI'da zorunlu).
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# ---------------------------------------------------------------- isim listesi

def _dosyadan(p: Path) -> list[str]:
    if not p.exists():
        return []
    try:
        satirlar = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [s.strip() for s in satirlar if s.strip() and not s.lstrip().startswith("#")]


def _git_dir(cwd: Path | None = None) -> Path | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True,
                             text=True, check=True, cwd=str(cwd) if cwd else None)
        return Path(out.stdout.strip())
    except Exception:
        return None


def proje_desenleri(proje_koku: Path | None = None, cwd: Path | None = None) -> list[str]:
    """Kimlik izi isim listesi (BİRLEŞİM, sırasız). Boşsa koruma yarımdır."""
    bulunan: list[str] = []

    env = os.environ.get("IX_GENERICIZE_BLOCKLIST", "").strip()
    if env:
        bulunan += [p.strip() for p in env.split(",") if p.strip()]

    gd = _git_dir(cwd)
    if gd is not None:
        bulunan += _dosyadan(gd / "genericize-blocklist")

    if proje_koku is not None:
        bulunan += _dosyadan(Path(proje_koku) / ".claude" / "genericize-blocklist.txt")

    # tekilleştir, sırayı koru
    return list(dict.fromkeys(bulunan))


def blocklist_var_mi(proje_koku: Path | None = None, cwd: Path | None = None) -> bool:
    return bool(proje_desenleri(proje_koku, cwd))


# ------------------------------------------------------------ yapısal desenler
# İsim içermez → public'te güvenli, taze klonda da çalışır.
YAPISAL = [
    r"C:[/\\]+Users[/\\]+(?!<)[^/\\ ]+",                       # makine-lokal kullanıcı yolu
    r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|net)\b)(?!test\b)(?!localhost\b)"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}",                           # e-posta (örnek domainler hariç)
]


def id_pattern(proje_koku: Path | None = None, cwd: Path | None = None) -> re.Pattern:
    """İsim listesi + yapısal desenler. IGNORECASE (D2: 'trakya' de yakalanmalı)."""
    desenler = proje_desenleri(proje_koku, cwd) + YAPISAL
    return re.compile("(" + "|".join(desenler) + ")", re.IGNORECASE)


# --------------------------------------------------------------- Z-obje adları
# Core dokümanlarında GEÇMESİNE İZİN VERİLEN kanonik örnek adları. Bunlar hiçbir
# gerçek projenin objesi değildir; naming standardı / playbook örnekleridir.
# Buraya yeni ad eklemek = "core'da bu ad görünebilir" demektir → GEREKÇELİ PR.
ORNEK_Z = frozenset({
    "ZSD000", "ZSD001",           # kanonik SD demo çifti (ADR 0005 istisnası)
    "ZMM001", "ZMM002", "ZMM004",  # standards/01-naming.md ağaç örnekleri
    "ZPP001", "ZFI001",            # standards/01-naming.md tablo örnekleri
    "ZBC001", "ZQM001",            # playbook API-proxy örnekleri
})

# D3: eski desen `\bzsd0(?!00|01)\d{2}` idi. `_` ve `z` ikisi de word-char olduğu için
# `\b` alt-çizgiden SONRA eşleşmiyordu → `project_zsd015`, `zcl_zsd009_mizan` KAÇIYORDU.
# D4: kapsam yalnız ZSD idi → ZBC/ZMM/ZQM/ZFI/ZPP hiç görülmüyordu.
Z_OBJ_PAT = re.compile(r"(?<![A-Za-z0-9])(Z[A-Z]{2}\d{3})(?!\d)", re.IGNORECASE)

# D4: SAP kullanıcı adı (gerçek kişi). Sadece BÜYÜK harf — `d_data` gibi değişken
# adlarını yanlış-yakalamamak için IGNORECASE YOK.
# ⚠ Yalnız 'X' ya da yalnız 'N' harflerinden oluşan diziler dokümantasyon PLACEHOLDER'ıdır
# (gerçek kullanıcı değil) → muaf. 2026-07-10: kendi README şablonumuz bu yanlış-pozitife
# takıldı. Guard doğru çalışıyordu; desen fazla genişti.
SAP_USER_PAT = re.compile(
    r"(?<![A-Za-z0-9_])D_"
    r"(?!X{2,}(?![A-Za-z0-9]))"   # placeholder: D_ + yalnız X'ler
    r"(?!N{2,}(?![A-Za-z0-9]))"   # placeholder: D_ + yalnız N'ler
    r"[A-Z]{4,}(?![A-Za-z0-9])")


def z_obje_sizintilari(metin: str) -> list[str]:
    """Örnek-allowlist'te olmayan Z-obje adları."""
    return [m.group(1) for m in Z_OBJ_PAT.finditer(metin)
            if m.group(1).upper() not in ORNEK_Z]


def sap_user_sizintilari(metin: str) -> list[str]:
    return [m.group(0) for m in SAP_USER_PAT.finditer(metin)]


def sizintilari_bul(metin: str, idp: re.Pattern) -> list[tuple[str, str]]:
    """(token, tür) listesi. Çağıran `idp`'yi `id_pattern()` ile üretir."""
    bulgular: list[tuple[str, str]] = []
    m = idp.search(metin)
    if m:
        bulgular.append((m.group(0), "kimlik izi"))
    for t in z_obje_sizintilari(metin):
        bulgular.append((t, "Z-obje adı"))
    for t in sap_user_sizintilari(metin):
        bulgular.append((t, "SAP kullanıcı adı"))
    return bulgular
