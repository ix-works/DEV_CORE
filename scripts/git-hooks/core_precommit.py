#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEV_CORE pre-commit gate (B11 — D19/D21). STAGED dosyalar üzerinde 3 kontrol:

1) GENERICIZE-LEAK: proje/müşteri kimliği core'a COMMIT'LENEMEZ (sistem adı,
   kullanıcı, eski-kök yolu, ZSD-numaralı paket adları; ZSD000/ZSD001 demo istisnası).
   pre_tool_guard Ö5 yazım-anı erken-uyarıdır; KESİN gate budur (+ CI'da aynısı).
2) LINK-AUDIT: staged .md'lerdeki göreli linkler çözülmeli (dosya-dizininden VEYA
   repo-kökünden). Kopuk link = FAIL.
3) APPLIES_TO ŞEMASI (D21): standards/ + playbook/ altındaki her .md frontmatter'ında
   `applies_to:` olmalı ve değerler enum'da olmalı (profiles/*.yaml adları + 'all').
   Typo = sessiz profil-kaybı — şema doğrulaması bunu yakalar.

Yalnız staged içerik taranır (git show :path) — working-tree kirliliği gate'i etkilemez.
Çıkış: ihlal varsa 1 (commit bloklanır), yoksa 0.
"""
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Kimlik desenleri (pre_tool_guard._CORE_LEAK ile hizalı + commit-gate ekleri) ──
ID_PAT = re.compile(
    r"(<PROJECT_NAME>|<PROJECT_NAME>|<LEGACY_SOURCE>|<LEGACY_SOURCE>|<SAP_HOST>|<SAP_USER>|<USER>|<USER>"
    r"|C:[/\\]+<LEGACY_ROOT>|C:[/\\]+Users[/\\]+DELL)")
ZSD_PAT = re.compile(r"\bzsd0(?!00|01)\d{2}", re.IGNORECASE)  # ZSD000/001 demo serbest

# Dosya-bazlı izinli token'lar (taramadan ÖNCE içerikten çıkarılır; kalan yine taranır)
ALLOWED_TOKENS = {
    "README.md": ["<PROJECT_NAME>_DOKUM", "<USER>"],  # ilk-proje + tarihsel-yedek referansı
}
# Desen-sözlüğü taşıyan dosyalar (tarama anlamsız — kendileri desen tanımlar)
SCAN_EXEMPT = {
    "scripts/hooks/pre_tool_guard.py",
    "scripts/git-hooks/core_precommit.py",
}

BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".ico", ".woff",
              ".woff2", ".ttf", ".xlsx", ".docx", ".pptx", ".exe", ".dll"}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True)
    return r.stdout.decode("utf-8", errors="replace")


def staged_files() -> list[str]:
    out = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    return [p for p in out.split("\0") if p]


def staged_content(path: str) -> str | None:
    """Staged (index) içerik; binary ise None."""
    if Path(path).suffix.lower() in BINARY_EXT:
        return None
    r = subprocess.run(["git", "show", ":" + path], capture_output=True)
    if r.returncode != 0:
        return None
    raw = r.stdout
    if b"\0" in raw[:8000]:
        return None
    return raw.decode("utf-8", errors="replace")


def profile_enum(repo: Path) -> set[str]:
    enum = {"all"}
    prof = repo / "profiles"
    if prof.is_dir():
        enum |= {p.stem for p in prof.glob("*.yaml")}
    return enum


def check_generic(path: str, text: str, hatalar: list[str]) -> None:
    if path in SCAN_EXEMPT:
        return
    for tok in ALLOWED_TOKENS.get(path, []):
        text = text.replace(tok, "")
    for pat, ad in ((ID_PAT, "kimlik"), (ZSD_PAT, "ZSD-numarali paket")):
        m = pat.search(text)
        if m:
            satir = text[: m.start()].count("\n") + 1
            hatalar.append(
                f"GENERICIZE-LEAK  {path}:{satir}  '{m.group(0)}' ({ad}) — core'a "
                f"proje/müşteri izi giremez; placeholder'la (<SYSTEM_ID>, ZSD<NNN> ...)")


def check_links(path: str, text: str, repo: Path, hatalar: list[str]) -> None:
    base = (repo / path).parent
    for m in LINK_RE.finditer(text):
        hedef = m.group(1).split("#", 1)[0]
        if (not hedef or hedef.startswith(("http://", "https://", "mailto:"))
                or "<" in hedef or hedef.startswith("/") or re.match(r"^[A-Za-z]:", hedef)):
            continue
        if not ((base / hedef).exists() or (repo / hedef).exists()):
            satir = text[: m.start()].count("\n") + 1
            hatalar.append(f"KOPUK-LINK  {path}:{satir}  '{m.group(1)}' — ne dosya-dizininden "
                           f"ne repo-kökünden çözülüyor")


def check_applies_to(path: str, text: str, enum: set[str], hatalar: list[str]) -> None:
    bas = text[:500]
    m = re.search(r"applies_to:\s*\[([^\]]*)\]", bas)
    if not m:
        hatalar.append(
            f"APPLIES_TO-YOK  {path}  — standards/playbook .md'leri frontmatter'da "
            f"`applies_to: [...]` beyan etmek zorunda (D21; enum: {sorted(enum)})")
        return
    for tok in (t.strip().strip("'\"") for t in m.group(1).split(",")):
        if tok and tok not in enum:
            hatalar.append(
                f"APPLIES_TO-GECERSIZ  {path}  — '{tok}' enum'da yok {sorted(enum)}; "
                f"typo = sessiz profil-kaybı (D21)")


def main() -> int:
    repo = Path(_git("rev-parse", "--show-toplevel").strip() or ".")
    enum = profile_enum(repo)
    hatalar: list[str] = []
    for path in staged_files():
        text = staged_content(path)
        if text is None:
            continue
        check_generic(path, text, hatalar)
        if path.endswith(".md"):
            check_links(path, text, repo, hatalar)
            if path.startswith(("standards/", "playbook/")):
                check_applies_to(path, text, enum, hatalar)
    if hatalar:
        print("⛔ pre-commit GATE (B11) — commit BLOKLANDI:\n")
        for h in hatalar:
            print("  " + h)
        print(f"\n  Toplam {len(hatalar)} ihlal. Düzelt → tekrar commit. "
              f"(Bypass YASAK — ADR 0005 kültürü; gerçekten istisna ise ALLOWED_TOKENS/"
              f"SCAN_EXEMPT'e GEREKÇELİ PR ile ekle.)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
