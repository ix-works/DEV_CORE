#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEV_CORE pre-commit gate (B11 — D19/D21). STAGED dosyalar üzerinde 3 kontrol:

1) GENERICIZE-LEAK: proje/müşteri kimliği core'a COMMIT'LENEMEZ. İçerik VE dosya adı
   taranır (D5). Kapsam: isim listesi (env/<git-dir>/<proje>.claude, IGNORECASE) +
   yapısal desenler — makine-yolu, e-posta, Z-obje adı (`genericize_common.ORNEK_Z`
   allowlist'i dışındakiler), SAP kullanıcı adı (`D_XXXX`).
   Desenler `scripts/genericize_common.py`'de; `pre_tool_guard` AYNI kaynağı kullanır (D9).
   İsim listesi yoksa `--all` (CI) modunda FAIL-CLOSED (D1).
   pre_tool_guard yazım-anı erken-uyarıdır; KESİN gate budur (+ CI'da aynısı).
2) LINK-AUDIT: staged .md'lerdeki göreli linkler çözülmeli (dosya-dizininden VEYA
   repo-kökünden). Kopuk link = FAIL.
3) APPLIES_TO ŞEMASI (D21): standards/ + playbook/ altındaki her .md frontmatter'ında
   `applies_to:` olmalı ve değerler enum'da olmalı (profiles/*.yaml adları + 'all').
   Typo = sessiz profil-kaybı — şema doğrulaması bunu yakalar.

Yalnız staged içerik taranır (git show :path) — working-tree kirliliği gate'i etkilemez.
CI modu: `--all` ile TÜM tracked dosyalar taranır (core-ci.yml full-tree gate'i).
Çıkış: ihlal varsa 1 (commit/CI bloklanır), yoksa 0.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genericize_common import (  # noqa: E402  (sys.path bootstrap'tan SONRA)
    blocklist_var_mi, id_pattern, sizintilari_bul,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Tek kaynak: scripts/genericize_common.py (D9). İsim listesi env + <git-dir> +
# <proje>/.claude birleşimi; yapısal desenler (makine-yolu, e-posta, Z-obje, SAP
# kullanıcı adı) her zaman devrede. IGNORECASE → 'trakya' de yakalanır (D2).
ID_PAT = id_pattern()

# Dosya-bazlı izinli token'lar (taramadan ÖNCE içerikten çıkarılır; kalan yine taranır)
ALLOWED_TOKENS = {
    # mimari şemadaki placeholder (gerçek proje/müşteri adı YASAK)
    "README.md": ["<PROJECT_NAME>"],
}
# Desen-sözlüğü taşıyan dosyalar (tarama anlamsız — kendileri desen tanımlar)
SCAN_EXEMPT = {
    "scripts/hooks/pre_tool_guard.py",
    "scripts/git-hooks/core_precommit.py",
    "scripts/genericize_common.py",
}

# Link-check muafiyeti: build_core_index.py'nin ÜRETTİĞİ CORE-INDEX kasıtlı olarak PROJE-göreli
# `../core/...` link'leri taşır (proje-kökünden junction ile çözülür; core-repo-kökünden çözülmez).
# build_core_index gerçek dosyaları listeler → link hedefleri garanti var. Bu index'i link-check'ten
# muaf tut (aksi halde her regen 70+ false-positive KOPUK-LINK verir). Genericize-scan'e TABİ kalır.
LINK_EXEMPT = {
    "governance/CORE-INDEX.md",
}

BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".ico", ".woff",
              ".woff2", ".ttf", ".xlsx", ".docx", ".pptx", ".exe", ".dll"}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], capture_output=True)
    return r.stdout.decode("utf-8", errors="replace")


def staged_files(all_tracked: bool = False) -> list[str]:
    if all_tracked:
        out = _git("ls-files", "-z")
    else:
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
    # D5: dosya ADI da taranır. İçeriği genericize edilmiş ama adı unutulmuş dosyalar
    # (ör. `feedback_<müşteri>-full-dump.md`) eskiden gate'ten geçiyordu — canlı oldu.
    for tok, ad in sizintilari_bul(path, ID_PAT):
        hatalar.append(
            f"GENERICIZE-LEAK  {path}  (DOSYA ADI) '{tok}' ({ad}) — core'a proje/müşteri "
            f"izi giremez; dosyayı yeniden adlandır.")

    for tok in ALLOWED_TOKENS.get(path, []):
        text = text.replace(tok, "")
    for tok, ad in sizintilari_bul(text, ID_PAT):
        m = re.search(re.escape(tok), text)
        satir = text[: m.start()].count("\n") + 1 if m else 0
        hatalar.append(
            f"GENERICIZE-LEAK  {path}:{satir}  '{tok}' ({ad}) — core'a proje/müşteri izi "
            f"giremez; placeholder'la (<SYSTEM_ID>, <SAP_USER>, ZSD001 ...)")


def check_links(path: str, text: str, repo: Path, hatalar: list[str]) -> None:
    if path in LINK_EXEMPT:
        return
    # Kod-bloğu (```...```) ve inline-kod (`...`) içindeki linkler ÖRNEKTİR — tarama dışı
    # (satır numarası korunsun diye newline'lar bırakılarak boşaltılır).
    text = re.sub(r"```.*?```", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), text)
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
    all_tracked = "--all" in sys.argv
    repo = Path(_git("rev-parse", "--show-toplevel").strip() or ".")
    enum = profile_enum(repo)

    # D1 (2026-07-10 denetimi) — FAIL-CLOSED. İsim listesi `.git/genericize-blocklist`'te
    # yaşar; `.git/` ASLA klonlanmaz. CI runner taze klon yaptığı için liste hiç
    # yüklenmiyordu → public repoya giden SON KAPI müşteri/sistem/kişi adına KÖRDÜ
    # (canlı ölçüldü: müşteri adı, sistem kimliği ve kullanıcı adı exit 0 ile geçti).
    # Artık: CI/full-tree modunda liste yoksa DUR. Lokal pre-commit'te yalnız uyar
    # (geliştiriciyi bloklamak yerine kurulum eksiğini bildir).
    if not blocklist_var_mi(proje_koku=repo):
        if all_tracked:
            print("⛔ GENERICIZE GATE — kimlik blocklist'i YÜKLENEMEDİ (fail-closed).\n")
            print("  Yapısal desenler (makine-yolu, e-posta, Z-obje, SAP kullanıcı adı)")
            print("  devrede; ama müşteri/sistem/kişi ADLARI için isim listesi ŞART.\n")
            print("  CI için: repository secret `IX_GENERICIZE_BLOCKLIST` tanımla")
            print("  (virgülle ayrılmış regex listesi) ve workflow adımına env olarak geçir.")
            print("  Lokal için: `<git-dir>/genericize-blocklist` ya da")
            print("  `<proje>/.claude/genericize-blocklist.txt` oluştur.")
            return 1
        sys.stderr.write(
            "⚠ genericize blocklist bulunamadı — yalnız yapısal desenler devrede. "
            "Müşteri/sistem/kişi adı YAKALANMAZ. `<git-dir>/genericize-blocklist` kur.\n")

    hatalar: list[str] = []
    for path in staged_files(all_tracked):
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
