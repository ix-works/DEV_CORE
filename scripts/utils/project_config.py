# -*- coding: utf-8 -*-
"""project_config — proje kimliğinin TEK okuma noktası (K12/§9.3; ADR 0020).

Core script/validator'ları klasör adı, profil, prefix gibi PROJE-değerlerini
HARD-CODE ETMEZ — buradan okur. Kaynak sırası:
  1. env (IX_SOURCE_ROOT / IX_SAP_PROFILE ... — run_all_validators subprocess'lere basar)
  2. <proje>/project.yaml (lite-parser; pyyaml bağımlılığı YOK)
  3. güvenli fallback

Proje kökü: env CLAUDE_PROJECT_DIR → cwd. (DİKKAT: core script'leri junction üzerinden
koşar; __file__.resolve() DEV_CORE'a çözülür — proje kökü için ASLA __file__ kullanma.)
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env else Path.cwd()


_TIRNAK_ACAN_ONCUL = {":", "-", "[", ","}


def _yorumu_ayikla(satir: str) -> str:
    """Satırdan `#` yorumunu ayıklar — `#` YALNIZ TIRNAK DIŞINDA yorum başlatır.

    Neden (DEV_CORE Issue #391, 2026-11-07): eski `satir.split("#", 1)[0]` tırnağa
    bakmıyordu ⇒ namespace'li paket istisnası `["#NSPC#SD001:^#NSPC#CL_SD001_"]`
    `'['`'e, blok öğesi `- '#NSPC#SD001:…'` boş dizgiye iniyordu (sessiz veri kaybı).
    Kurallar (ölçülen tüketici biçimleri korunur):
      · Tırnak yalnız bir DEĞER/ÖĞE başında açılır: satır başı ya da önceki boşluk-dışı
        karakter `:` `-` `[` `,` ise. Kelime içindeki kesme işareti (`Paket'in`) tırnak
        DEĞİLDİR ⇒ tırnaksız değerde bugünkü kesim aynen kalır (`a#b` → `a`).
      · Tek tırnakta `''`, çift tırnakta `\\x` kaçışı atlanır.
      · Tırnak kapandıktan sonraki `   # açıklama` yine yorumdur.
      · Kapanmamış tırnak ⇒ ESKİ kesime düşülür (belirsiz girdi; bugünkü davranış).
    """
    tirnak: str | None = None
    onceki = ""            # son boşluk-dışı karakter (tırnak dışında)
    i, n = 0, len(satir)
    while i < n:
        c = satir[i]
        if tirnak is None:
            if c == "#":
                return satir[:i]
            if c in ("'", '"') and (onceki == "" or onceki in _TIRNAK_ACAN_ONCUL):
                tirnak = c
            elif not c.isspace():
                onceki = c
        elif tirnak == "'":
            if c == "'":
                if i + 1 < n and satir[i + 1] == "'":
                    i += 1          # '' kaçışı
                else:
                    tirnak, onceki = None, "'"
        else:  # çift tırnak
            if c == "\\":
                i += 1              # kaçışlı karakteri atla
            elif c == '"':
                tirnak, onceki = None, '"'
        i += 1
    if tirnak is not None:
        return satir.split("#", 1)[0]
    return satir


@lru_cache(maxsize=4)
def _yaml_lite(yol: str) -> dict:
    """project.yaml lite-parser: `key: value` skalerleri + inline `[a, b]` +
    takip eden `- x` blok listeleri. Yorum (#, yalnız tırnak DIŞINDA —
    `_yorumu_ayikla`) ve boş satır atlanır."""
    p = Path(yol)
    out: dict = {}
    if not p.exists():
        return out
    aktif_liste: str | None = None
    try:
        # ⚠ `utf-8-sig` ZORUNLU, `utf-8` DEĞİL (2026-08-01 bug-avı AV-02).
        # BOM'lu bir project.yaml'da anahtar SİLİNMEZ — ADI BOZULUR: ilk satır
        # '﻿sap_profile' olur → `cfg("sap_profile")` None döner → MCP profil
        # katmanı fail-closed'a düşer ve TÜM SAP tool yüzeyi sessizce `ping`e iner
        # (mcp_servers/sap_adt/_profile.py). Tetikleyici bizim bilinen tuzağımız:
        # PowerShell ile yazılan dosyaya BOM eklenir (memory: powershell-utf8-bom-trap).
        # `utf-8-sig` BOM'suz dosyada `utf-8` ile BAYT-EŞ davranır (regresyon riski yok).
        for ham in p.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
            s = _yorumu_ayikla(ham).rstrip()
            if not s.strip():
                continue
            if aktif_liste and s.strip().startswith("- "):
                out[aktif_liste].append(s.strip()[2:].strip().strip("'\""))
                continue
            aktif_liste = None
            if ":" not in s or s.startswith(" "):
                continue
            k, v = s.split(":", 1)
            k, v = k.strip(), v.strip()
            if v.startswith("[") and v.endswith("]"):
                out[k] = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
            elif v == "":
                out[k] = []
                aktif_liste = k
            else:
                out[k] = v.strip("'\"")
    except Exception:
        return out
    return out


def cfg(key: str, default=None):
    """Öncelik: env IX_<KEY_UPPER> → project.yaml → default."""
    env = os.environ.get("IX_" + key.upper())
    if env is not None:
        return env
    return _yaml_lite(str(project_root() / "project.yaml")).get(key, default)


def has_project_yaml() -> bool:
    return (project_root() / "project.yaml").exists()


def source_root_name() -> str:
    """Kaynak-kod klasörü adı (K12). Fallback: mevcut dizine bak (göç-dönemi toleransı)."""
    v = cfg("source_root")
    if v:
        return str(v)
    root = project_root()
    if (root / "SOURCE_CODES").is_dir():
        return "SOURCE_CODES"
    if (root / "ERP").is_dir():
        return "ERP"  # göç-öncesi eski düzen toleransı
    return "SOURCE_CODES"


def source_dir() -> Path:
    return project_root() / source_root_name()


def sap_profile() -> str | None:
    v = cfg("sap_profile")
    return None if (v in (None, "", "__DOLDUR__")) else str(v)


# Sık kullanılan sabit-benzeri erişim (import-anında çözülür; script ömrü kısa → güvenli)
SOURCE_ROOT_NAME = source_root_name()
