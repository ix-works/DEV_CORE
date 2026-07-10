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
CI modu: `--all` ile TÜM tracked dosyalar taranır (core-ci.yml full-tree gate'i).
Çıkış: ihlal varsa 1 (commit/CI bloklanır), yoksa 0.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def _id_desenleri() -> list[str]:
    """Core'a girmesi yasak kimlik izleri (pre_tool_guard._leak_desenleri ile hizalı).

    ⚠ LİSTE BU DOSYADA TUTULMAZ. DEV_CORE **public**tir; müşteri/sistem/kişi adını
    buraya yazmak, engellemeye çalıştığımız sızıntının kendisidir (2026-07-09 dersi:
    guard'ın kendi filtresi public repoda bu adları ilan ediyordu).

    Kaynak sırası (ilk bulunan kazanır):
      1. env `IX_GENERICIZE_BLOCKLIST` (virgülle ayrılmış)
      2. `<repo>/.git/genericize-blocklist`  ← repo AĞACININ DIŞI: commit'lenmez,
         klonlanmaz, push edilmez. Her makine kendi listesini tutar.
      3. jenerik varsayılan — isim içermez, yalnız yapısal desenler
    """
    env = os.environ.get("IX_GENERICIZE_BLOCKLIST", "").strip()
    # ⚠ BİRLEŞİM, EZME DEĞİL (2026-07-10 düzeltmesi). Eskiden proje-listesi VARSA erken
    # return ediyordu → jenerik yapısal desenler (makine-yolu, e-posta) DÜŞÜYORDU. Sonuç
    # tersineydi: blocklist'li makinede pre-commit makine-yolunu/e-postayı KAÇIRIYOR,
    # blocklist'siz CI runner'ında müşteri adını KAÇIRIYORdu — public repoya giden son
    # kapı her iki senaryoda yarım koruyordu (2026-07-10 denetimi, canlı ölçüldü).
    # `pre_tool_guard._leak_desenleri()` ile AYNI semantik: proje + jenerik BİRLEŞİR.
    proje = []
    if env:
        proje = [p.strip() for p in env.split(",") if p.strip()]
    else:
        try:
            git_dir = Path(subprocess.run(["git", "rev-parse", "--git-dir"],
                                          capture_output=True, text=True, check=True
                                          ).stdout.strip())
            dosya = git_dir / "genericize-blocklist"
            if dosya.exists():
                satirlar = dosya.read_text(encoding="utf-8", errors="replace").splitlines()
                proje = [s.strip() for s in satirlar
                         if s.strip() and not s.lstrip().startswith("#")]
        except Exception:
            proje = []

    # Jenerik yapısal desenler HER ZAMAN eklenir (isim içermez). PLACEHOLDER muaftır.
    jenerik = [
        r"C:[/\\]+Users[/\\]+(?!<)[^/\\ ]+",                 # makine-lokal kullanıcı yolu
        # e-posta: RFC 2606 rezerve/örnek domainleri HARİÇ
        r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|net)\b)(?!test\b)(?!localhost\b)"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    ]
    return proje + jenerik


ID_PAT = re.compile("(" + "|".join(_id_desenleri()) + ")")
ZSD_PAT = re.compile(r"\bzsd0(?!00|01)\d{2}", re.IGNORECASE)  # ZSD000/001 demo serbest

# Dosya-bazlı izinli token'lar (taramadan ÖNCE içerikten çıkarılır; kalan yine taranır)
ALLOWED_TOKENS = {
    # mimari şemadaki placeholder (gerçek proje/müşteri adı YASAK)
    "README.md": ["<PROJECT_NAME>"],
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
