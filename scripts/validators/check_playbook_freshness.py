"""
check_playbook_freshness.py — Playbook'un güncel kalması için uyarı verir.

Mantık (LESSONS_LEARNED #6 — TempScripts → Playbook yansıtmama'nın çözümü):
- Son N gün içinde playbook/ altında commit var mı?
- scripts/ altında create_*/populate_*/run_* script'i değişti veya eklendi mi?
- Script değişikliği var ama playbook değişikliği yok → UYARI (T1/T2/T9 trigger'lı pattern unutulmuş olabilir)

Kullanım:
    python scripts/validators/check_playbook_freshness.py
    python scripts/validators/check_playbook_freshness.py --days 30

Exit kodu:
    0 — OK (playbook güncel veya script değişikliği yok)
    1 — Sadece UYARI (warning), kritik değil — CI'da fail etmemeli (--strict ile fail)

Not: Bu kod gate'i şu an "soft" — sadece uyarır. Çok agresif olunca dev workflow'u sıkıştırır.
"""
import argparse
import subprocess
import sys
from datetime import datetime, timedelta

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def git_log_since(days: int, path: str) -> list[str]:
    """Son N gün içinde path altında değişen dosya listesi."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    result = subprocess.run(
        ["git", "log", f"--since={since}", "--name-only", "--pretty=format:", "--", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Playbook freshness kontrolü")
    parser.add_argument("--days", type=int, default=30, help="Bakılacak gün sayısı")
    parser.add_argument("--strict", action="store_true", help="Uyarı yerine fail et")
    args = parser.parse_args()

    scripts_changed = git_log_since(args.days, "scripts/")
    playbook_changed = git_log_since(args.days, "playbook/")

    # Sadece create_/populate_/run_ değişikliklerine bak
    relevant_scripts = [
        s for s in scripts_changed
        if any(token in s for token in ("create_", "populate_", "run_"))
        and s.endswith(".py")
    ]

    if not relevant_scripts:
        print(f"OK — Son {args.days} günde create_/populate_/run_ script değişikliği yok.")
        return 0

    if not playbook_changed:
        msg = (
            f"UYARI: Son {args.days} günde {len(set(relevant_scripts))} script değişti "
            f"ama playbook/ güncellenmedi.\n"
            f"  Değişen script'ler: {sorted(set(relevant_scripts))[:5]}{'...' if len(set(relevant_scripts)) > 5 else ''}\n"
            f"  T1/T2/T9 trigger'larını kontrol et: yeni pattern playbook'a yazıldı mı?"
        )
        if args.strict:
            print(f"HATA — {msg}", file=sys.stderr)
            return 1
        print(msg, file=sys.stderr)
        return 0

    print(
        f"OK — Son {args.days} günde {len(set(relevant_scripts))} script değişti, "
        f"playbook/'ta {len(set(playbook_changed))} güncelleme var."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
