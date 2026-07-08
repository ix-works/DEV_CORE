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


@lru_cache(maxsize=4)
def _yaml_lite(yol: str) -> dict:
    """project.yaml lite-parser: `key: value` skalerleri + inline `[a, b]` +
    takip eden `- x` blok listeleri. Yorum (#) ve boş satır atlanır."""
    p = Path(yol)
    out: dict = {}
    if not p.exists():
        return out
    aktif_liste: str | None = None
    try:
        for ham in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = ham.split("#", 1)[0].rstrip()
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
