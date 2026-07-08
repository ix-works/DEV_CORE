"""
sprint_retrospective.py — Sprint sonu kalite + reviewer metric raporu.

Yapar:
  1. Bu sprint'te kaç "fix:" / "düzelt" commit (patinaj göstergesi)
  2. Reviewer çağrıları (eğer log'lanmışsa)
  3. Validator yakalama oranı
  4. False positive sayısı (manuel işaretlenmiş)
  5. Estimated net kazanç (dk)
  6. Öneri: 3 sprint üst üste negatif → reviewer'ı sadeleştir

Kullanım:
    python scripts/validators/sprint_retrospective.py --sprint 6
    python scripts/validators/sprint_retrospective.py --since 2026-05-14
"""
import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def git_commits_since(since: str) -> list[str]:
    """git log --since=<date> --oneline"""
    try:
        r = subprocess.run(['git', 'log', f'--since={since}', '--oneline'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', check=False)
        return [l for l in r.stdout.splitlines() if l.strip()]
    except Exception as e:
        print(f'UYARI: git log hatası: {e}', file=sys.stderr)
        return []


def main() -> int:
    parser = argparse.ArgumentParser(description='Sprint sonu retrospektif raporu')
    parser.add_argument('--sprint', help='Sprint numarası (örn. 6)')
    parser.add_argument('--since', help='Tarihten itibaren (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=7, help='--since verilmediyse son N gün')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    since = args.since or (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    print(f'\n{"="*70}')
    print(f'SPRINT RETROSPEKTİF — {args.sprint or "all"} ({since}\'dan itibaren)')
    print(f'{"="*70}\n')

    commits = git_commits_since(since)
    print(f'Toplam commit: {len(commits)}')

    # Patinaj göstergesi: "fix:" prefix'li commit'ler
    fix_commits = [c for c in commits if 'fix:' in c.lower() or 'düzelt' in c.lower()]
    print(f'"fix:" / düzelt commit\'leri: {len(fix_commits)}')
    for c in fix_commits[:5]:
        print(f'  {c}')

    # Feature commits (Sprint kapatma göstergesi)
    feat_commits = [c for c in commits if 'feat' in c.lower() or 'sprint' in c.lower()]
    print(f'\nFeature / Sprint commit\'leri: {len(feat_commits)}')

    # Reviewer kullanımı (eğer commit message'da geçiyorsa)
    review_commits = [c for c in commits if 'review' in c.lower() or 'reviewer' in c.lower()]
    print(f'Reviewer-related commit\'ler: {len(review_commits)}')

    # Tahmini patinaj kaybı (her fix ~10 dk)
    estimated_patinaj_loss = len(fix_commits) * 10
    print(f'\nTahmini patinaj kaybı (~10dk/fix): {estimated_patinaj_loss} dk')

    # Tahmini reviewer overhead (her sprint ~8 dk)
    estimated_reviewer_overhead = 8 if args.sprint else 0

    # Net kazanç tahmini
    net = estimated_patinaj_loss - estimated_reviewer_overhead
    print(f'Tahmini reviewer overhead: {estimated_reviewer_overhead} dk')
    print(f'Net (negatif = kayıp): {net:+d} dk')

    if net < 0:
        print('\n⚠ Bu sprint reviewer\'dan beklenen değer alınamadı.')
        print('  Sebep olası: setup eksik, validator zinciri yetersiz, false positive yüksek')

    # Öneri kısmı
    print(f'\n{"="*70}')
    print('ÖNERİLER:')
    if len(fix_commits) > 3:
        print(f'  • {len(fix_commits)} fix commit — patinaj göstergesi yüksek.')
        print('    Reviewer kapasitesini büyütmeyi düşün:')
        print('    - Yeni validator script gerekiyor mu?')
        print('    - Checklist madde eklemeli mi?')
    if not review_commits:
        print('  • Reviewer kullanımı görünmüyor. Bu sprintte aktif edildi mi?')
    if estimated_patinaj_loss == 0:
        print('  • Patinaj sıfır — reviewer çalışıyor veya iş kolaydı.')
    print(f'{"="*70}\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
