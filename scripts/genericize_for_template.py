# -*- coding: utf-8 -*-
"""genericize_for_template.py — Metodoloji dosyalarını template'e taşırken projeye-özel
kimliği generic placeholder'lara çevirir VE artık (residual) sızıntı adaylarını FLAG'ler.

MAINTENANCE.md "Otomatik portlama YASAK (TD sızar)" kuralının ruhuna uyar: kör kopya
DEĞİL — token haritasını uygular + map'in YAKALAMADIĞI olası kimlik sızıntılarını
(e-posta, kişisel yol, müşteri adı vb.) listeler ki insan gözden geçirsin.

Token haritası kaynağı: MAINTENANCE.md §Port + init_project.py PLACEHOLDER_KEYS +
template_drift.py NORMALIZERS (araştırma raporu 2026-06-28).

Kullanım:
    # Tek dosya STDOUT'a (önizleme):
    python scripts/genericize_for_template.py --file <yol> --stdout
    # Bir dizini template'e genericize ederek yansıt (mirror):
    python scripts/genericize_for_template.py --src-dir .claude/memory-seed \\
        --dst-dir C:/<LEGACY_ROOT>/DEVELOPMENT_TEMPLATE_FILES/.claude/memory-seed
    # Yalnız leak taraması (yazma yok):
    python scripts/genericize_for_template.py --src-dir playbook --scan-only
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# --- Sıralı genericize kuralları (uzun/çok-kelimeli önce) ---
# (pattern, replacement, is_regex)
RULES: list[tuple[str, str, bool]] = [
    # Kişisel kimlik (map'te yok ama mutlaka temizle)
    (r"<USER>34@gmail\.com", "<USER_EMAIL>", True),
    (r"C:\\Users\\DELL", r"C:\\Users\\<USER>", True),
    (r"C:/Users/DELL", "C:/Users/<USER>", True),
    # Repo URL (yoldan/isimden ÖNCE — tam URL'i yakala)
    (r"https?://github\.com/<USER>/<PROJECT_NAME>_DOKUM", "<PROJECT_REPO_URL>", True),
    (r"<USER>/<PROJECT_NAME>_DOKUM", "<PROJECT_REPO_URL>", True),
    # Proje kök yolu (kişisel-yoldan önce proje-özel kökü yakala)
    (r"C:\\<LEGACY_ROOT>\\<PROJECT_NAME>", "<PROJECT_ROOT>", True),
    (r"C:/<LEGACY_ROOT>/<PROJECT_NAME>", "<PROJECT_ROOT>", True),
    # Legacy kaynak
    (r"C:\\<LEGACY_ROOT>\\<LEGACY_SOURCE>[^\s'\")]*", "<LEGACY_SOURCE>", True),
    (r"C:/<LEGACY_ROOT>/<LEGACY_SOURCE>[^\s'\")]*", "<LEGACY_SOURCE>", True),
    # Proje adı — tüm yazım varyantları (boşluklu/boşluksuz, ö/o, ü/u, ASCII)
    (r"<PROJECT_NAME>\s*D[öo]k[üu]m", "<PROJECT_NAME>", True),
    (r"<PROJECT_NAME>", "<PROJECT_NAME>", True),
    (r"<PROJECT_NAME>_DOKUM", "<PROJECT_NAME>", True),
    (r"\b<LEGACY_SOURCE>\b", "<LEGACY_SOURCE>", True),
    # Sistem / kullanıcı / transport
    (r"<SAP_HOST>", "<SYSTEM_ID>", True),
    (r"\b<SAP_USER>\b", "<SAP_USER>", True),
    (r"\b<SAP_USER>\b", "<SAP_USER>", True),
    (r"\b[A-Z]{4}K9\d{5}\b", "<TRANSPORT>", True),  # <TRANSPORT> vb.
    # İş-domain adları → nötr ORDER (identifier içinde de: ZCL_SD015_VOYAGE → ..._ORDER;
    # \b YOK çünkü '_VOYAGE' word-boundary'siz)
    (r"VOYAGE", "ORDER", True),
    (r"FITTINGS", "ORDER", True),
    (r"DISPATCH", "ORDER", True),
    # ZSD dev paket no'ları → ZSD001 (ZSD000 KORU, ZSD020+ KORU)
    (r"ZSD0(0[1-9]|1[0-9])", "ZSD001", True),
    # Z'siz modül-paket/class formu (ZCL_SD015, SD015_...) → SD001 (ZSD0NN üstte hallolur)
    (r"SD0(0[1-9]|1[0-9])", "SD001", True),
]

# Genericize SONRASI hâlâ kalan olası sızıntılar (insan gözden geçirsin)
LEAK_PATTERNS: list[tuple[str, str]] = [
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "e-posta"),
    (r"\bDELL\b", "DELL (kişisel kullanıcı)"),
    (r"\b<SAP_USER>\b", "SAP kullanıcı kalıntısı"),
    (r"<SAP_HOST>\w*", "sistem ID kalıntısı"),
    (r"<PROJECT_NAME>", "proje adı kalıntısı"),
    # ZSD001 = genericize HEDEF değeri (kalıntı değil) → 002-019 kalırsa flag
    (r"ZSD0(0[2-9]|1[0-9])\b", "ZSD dev-paket kalıntısı"),
    (r"\bVOYAGE\b|\bFITTINGS\b", "iş-domain kalıntısı"),
]


def genericize(text: str) -> str:
    for pat, repl, is_regex in RULES:
        if is_regex:
            text = re.sub(pat, repl, text)
        else:
            text = text.replace(pat, repl)
    return text


def scan_leaks(text: str) -> list[str]:
    hits = []
    for pat, label in LEAK_PATTERNS:
        for m in set(re.findall(pat, text)):
            hits.append(f"{label}: {m}")
    return hits


def process_file(src: Path, dst: Path | None, scan_only: bool, to_stdout: bool) -> dict:
    raw = src.read_text(encoding="utf-8", errors="replace")
    out = genericize(raw)
    leaks = scan_leaks(out)
    changed = out != raw
    if to_stdout:
        sys.stdout.write(out)
    elif not scan_only and dst is not None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(out, encoding="utf-8", newline="\n")
    return {"src": src, "changed": changed, "leaks": leaks}


def main() -> int:
    ap = argparse.ArgumentParser(description="Metodoloji dosyalarını template için genericize et + leak tara")
    ap.add_argument("--file", help="Tek dosya")
    ap.add_argument("--src-dir", help="Kaynak dizin (rekürsif .md/.py/.json...)")
    ap.add_argument("--dst-dir", help="Hedef dizin (mirror); yoksa scan-only gibi davranır")
    ap.add_argument("--stdout", action="store_true", help="Tek dosyayı STDOUT'a yaz (önizleme)")
    ap.add_argument("--scan-only", action="store_true", help="Yazma; yalnız leak raporu")
    ap.add_argument("--ext", default=".md,.py,.json,.txt,.template,.tmpl,.yaml,.yml",
                    help="İşlenecek uzantılar (virgülle)")
    args = ap.parse_args()

    exts = {e if e.startswith(".") else "." + e for e in args.ext.split(",")}
    results = []

    if args.file:
        src = Path(args.file)
        dst = Path(args.dst_dir) / src.name if args.dst_dir else None
        results.append(process_file(src, dst, args.scan_only, args.stdout))
    elif args.src_dir:
        src_root = Path(args.src_dir)
        dst_root = Path(args.dst_dir) if args.dst_dir else None
        scan_only = args.scan_only or dst_root is None
        for f in sorted(src_root.rglob("*")):
            if f.is_file() and f.suffix in exts:
                rel = f.relative_to(src_root)
                dst = (dst_root / rel) if dst_root else None
                results.append(process_file(f, dst, scan_only, False))
    else:
        ap.error("--file veya --src-dir gerekli")

    # Rapor
    changed = [r for r in results if r["changed"]]
    leaky = [r for r in results if r["leaks"]]
    if not args.stdout:
        print(f"\n--- GENERICIZE RAPORU ---")
        print(f"  İşlenen dosya : {len(results)}")
        print(f"  Değişen       : {len(changed)}")
        print(f"  Yazım         : {'HAYIR (scan/stdout)' if (args.scan_only or args.stdout or not args.dst_dir) else args.dst_dir}")
        if leaky:
            print(f"\n  ⚠ OLASI SIZINTI ({len(leaky)} dosya) — İNSAN GÖZDEN GEÇİRMELİ:")
            for r in leaky:
                print(f"    {r['src']}:")
                for lk in sorted(set(r["leaks"])):
                    print(f"        - {lk}")
        else:
            print("\n  ✓ Genericize sonrası sızıntı adayı YOK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
