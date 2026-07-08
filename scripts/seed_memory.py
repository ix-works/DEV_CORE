# -*- coding: utf-8 -*-
"""seed_memory.py — Repo'daki committed memory tohumunu, bu makinedeki Claude Code
proje-hafıza klasörüne kopyalar (merge-safe).

NEDEN: Claude Code'un "auto-memory" dosyaları repo DIŞINDA, kullanıcı profilinde tutulur:
    ~/.claude/projects/<proje-slug>/memory/*.md  +  MEMORY.md (index)
Bunlar version-control'de OLMADIĞI için clone'da gelmez. Bu script, repoya committed
`.claude/memory-seed/` içeriğini (davranış/feedback kuralları) o klasöre tohumlar →
yeni geliştirici, proje sahibinin çalışma disiplinini (feedback memory) devralır.

KAPSAM: SADECE feedback (nasıl-çalışırsın) memory'leri tohumlanır. Projeye-özel work-state
(project-type memory) tohuma DAHİL DEĞİLDİR (başka projeye yanıltıcı).

MERGE-SAFE: Hedefte zaten var olan dosyayı EZMEZ (yerel daha taze olabilir). Yalnız eksik
dosyaları ekler. MEMORY.md index'i yalnız hedefte yoksa kopyalanır; varsa dokunulmaz
(kullanıcının kendi index'i korunur). --force ile üzerine yazılabilir.

Proje-slug: repo kök yolundaki alfanümerik-olmayan her karakter '-' ile değiştirilir
(Claude Code konvansiyonu). Ör: C:\\<LEGACY_ROOT>\\<PROJECT_NAME> -> C--AI-PROJE-<PROJECT_NAME>

Kullanım (repo kökünde):
    python scripts/seed_memory.py            # eksikleri ekle, raporla
    python scripts/seed_memory.py --dry-run  # ne yapacağını göster, yazma
    python scripts/seed_memory.py --force     # var olanları da seed'le ez (DİKKAT)
    python scripts/seed_memory.py --target <yol>  # hedef memory klasörünü elle ver
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = REPO_ROOT / ".claude" / "memory-seed"


def project_slug(path: Path) -> str:
    """Claude Code proje-hafıza klasör adı: yoldaki alfanümerik-olmayan -> '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def default_target() -> Path:
    slug = project_slug(REPO_ROOT)
    return Path.home() / ".claude" / "projects" / slug / "memory"


def main() -> int:
    ap = argparse.ArgumentParser(description="Repo memory tohumunu makineye seed et")
    ap.add_argument("--target", default=None, help="Hedef memory klasörü (vermezsen otomatik hesaplanır)")
    ap.add_argument("--dry-run", action="store_true", help="Yalnız raporla, yazma")
    ap.add_argument("--force", action="store_true", help="Var olan dosyaları da seed ile ez")
    args = ap.parse_args()

    if not SEED_DIR.exists():
        print(f"[FAIL] Seed klasörü yok: {SEED_DIR}", file=sys.stderr)
        return 1

    seed_files = sorted(SEED_DIR.glob("feedback_*.md"))
    seed_index = SEED_DIR / "MEMORY.md"
    if not seed_files:
        print(f"[WARN] {SEED_DIR} içinde feedback_*.md yok — tohumlanacak bir şey yok.")
        return 0

    target = Path(args.target) if args.target else default_target()
    print(f"[INFO] Repo kök : {REPO_ROOT}")
    print(f"[INFO] Seed     : {SEED_DIR} ({len(seed_files)} feedback dosyası)")
    print(f"[INFO] Hedef    : {target}")
    print(f"[INFO] Mod      : {'DRY-RUN' if args.dry_run else ('FORCE' if args.force else 'merge (eksikleri ekle)')}")

    added, skipped, forced = [], [], []

    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    for f in seed_files:
        dst = target / f.name
        if dst.exists() and not args.force:
            skipped.append(f.name)
            continue
        if dst.exists() and args.force:
            forced.append(f.name)
        else:
            added.append(f.name)
        if not args.dry_run:
            shutil.copy2(f, dst)

    # MEMORY.md index — yalnız hedefte yoksa kopyala (kullanıcı index'ini koru)
    index_action = "atlandı (zaten var)"
    if seed_index.exists():
        dst_index = target / "MEMORY.md"
        if not dst_index.exists() or args.force:
            index_action = "kopyalandı" if not dst_index.exists() else "EZİLDİ (--force)"
            if not args.dry_run:
                shutil.copy2(seed_index, dst_index)

    print("\n--- ÖZET ---")
    print(f"  Eklendi : {len(added)}")
    if forced:
        print(f"  Ezildi  : {len(forced)} (--force)")
    print(f"  Atlandı : {len(skipped)} (zaten mevcut, korundu)")
    print(f"  MEMORY.md index: {index_action}")
    if args.dry_run:
        print("\n  (DRY-RUN — hiçbir dosya yazılmadı)")
    elif added or forced:
        print("\n[OK] Feedback memory tohumlandı. Yeni Claude oturumunda kurallar yüklenir.")
    else:
        print("\n[OK] Her şey güncel — eklenecek yeni feedback memory yok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
