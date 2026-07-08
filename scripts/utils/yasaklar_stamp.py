# -*- coding: utf-8 -*-
"""KESİN YASAKLAR fiziksel-damga ortak modülü (init_project / sync_yasaklar / guard).

Tasarım (kullanıcı direktifi 2026-07-08): yasaklar HER projenin kök CLAUDE.md'sine
FİZİKSEL yazılır — @import'a (junction'a) bağlı DEĞİL. Kök CLAUDE.md Claude Code
tarafından junction'sız DOĞRUDAN yüklenir → junction kırılsa bile anayasa context'te.
Tek kaynak: core/claude/kesin-yasaklar.canonical.md. Drift-guard damganın kanonikle
birebir eşliğini zorlar (bayat kopya = BLOCKER).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

BEGIN = "<!-- KESIN-YASAKLAR:BEGIN — kanonik: core/claude/kesin-yasaklar.canonical.md · ELLE DÜZENLEME (sync_yasaklar.py yeniden-damgalar) -->"
END = "<!-- KESIN-YASAKLAR:END -->"
_BLOCK_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)


def canonical_path(core_root: Path) -> Path:
    return core_root / "claude" / "kesin-yasaklar.canonical.md"


def canonical_text(core_root: Path) -> str:
    """Kanonik blok içeriği (normalize: satır-sonu LF, sağ-trim, tek son-newline)."""
    raw = canonical_path(core_root).read_text(encoding="utf-8")
    return _normalize(raw)


def _normalize(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in s.split("\n")).strip() + "\n"


def stamped_block(core_root: Path) -> str:
    """Projeye yazılacak tam damga (marker'lar + kanonik içerik)."""
    return f"{BEGIN}\n{canonical_text(core_root)}{END}"


def extract_block(claude_md_text: str) -> str | None:
    """CLAUDE.md içinden marker'lar arası kanonik-içeriği çıkar (marker'sız, normalize)."""
    m = _BLOCK_RE.search(claude_md_text)
    if not m:
        return None
    inner = m.group(0)[len(BEGIN):-len(END)]
    return _normalize(inner)


def digest(s: str) -> str:
    return hashlib.sha256(_normalize(s).encode("utf-8")).hexdigest()[:16]


def upsert(claude_md_text: str, core_root: Path) -> str:
    """CLAUDE.md metnine damgayı ekle/güncelle. Varsa değiştirir, yoksa EN BAŞA koyar
    (kök CLAUDE.md'nin ilk satırları = daima-yüklü anayasa)."""
    blok = stamped_block(core_root)
    if _BLOCK_RE.search(claude_md_text):
        return _BLOCK_RE.sub(lambda _: blok, claude_md_text)
    # Başlık (# ...) varsa onun ALTINA, yoksa en başa
    lines = claude_md_text.split("\n")
    if lines and lines[0].startswith("# "):
        return lines[0] + "\n\n" + blok + "\n\n" + "\n".join(lines[1:]).lstrip("\n")
    return blok + "\n\n" + claude_md_text


def check(claude_md_text: str, core_root: Path) -> tuple[bool, str]:
    """(ok, mesaj). Damga var + kanonikle birebir eş mi?"""
    proje = extract_block(claude_md_text)
    if proje is None:
        return False, ("KESİN YASAKLAR damgası YOK (kök CLAUDE.md'de "
                       f"{BEGIN[:40]}... bloğu bulunamadı) — yasaklar junction'a bağımlı "
                       "kalmış. Çözüm: python core/scripts/sync_yasaklar.py")
    kanon = canonical_text(core_root)
    if digest(proje) != digest(kanon):
        return False, ("KESİN YASAKLAR damgası kanonikten SAPMIŞ (bayat/değiştirilmiş) — "
                       f"proje={digest(proje)} kanonik={digest(kanon)}. "
                       "Çözüm: python core/scripts/sync_yasaklar.py")
    return True, "KESİN YASAKLAR damgası kanonikle eş"
