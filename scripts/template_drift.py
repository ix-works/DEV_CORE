# -*- coding: utf-8 -*-
"""template_drift.py — Kaynak proje ile bu template arasında METODOLOJİ farkını raporlar.

Amaç: kaynak projede (upstream) kural/hook/validator/pattern geliştikçe, template'e
portlanmamış değişiklikleri tespit etmek. Projeye-özel token'ları (proje adı, sistem,
ZSD<NNN> dev paketleri, ORDER/ORDER gibi) normalize ederek SADECE gerçek metodoloji
farkını gösterir. Bkz. MAINTENANCE.md.

Kullanım:
    python scripts/template_drift.py --source C:\\<LEGACY_ROOT>\\KaynakProje --template .

Çıktı: her metodoloji dosyası için durum — SAME / DRIFT (kaynak değişmiş) / ONLY_SOURCE /
ONLY_TEMPLATE. DRIFT olanlar port adayıdır.
"""
import argparse
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Sync kapsamindaki metodoloji yollari (MAINTENANCE.md ile uyumlu).
METHODOLOGY = [
    "CLAUDE.md", "AGENTS.md", "MAINTENANCE.md",
    "standards/", "playbook/", "governance/decisions/",
    "governance/tooling-plugins.md", "governance/vscode-setup.md",
    "governance/agent-teams-operating-model.md",
    "scripts/", "mcp_servers/", ".claude/skills/", ".claude/settings.json",
    ".claude/agents/", ".claude/commands/", ".claude/memory-seed/",
    "templates/",
]
# Kapsam DISI (projeye ozel — karsilastirma).
EXCLUDE = ["ERP/", "governance/package-registry.md", "governance/cbo-inventory.json",
           "governance/research/", "governance/api-docs/", "SESSION_NOTES", "SPEC",
           "__pycache__", ".git", "scripts/init_project.py", "scripts/template_drift.py",
           "scripts/genericize_for_template.py",  # kaynak-spesifik port araci (RULES projeye bagli)
           "scripts/TempScripts/", "scripts/ui-smoke/node_modules/", "scripts/ui-smoke/test-results/",
           "node_modules/", ".last-run.json", "test-results/"]
TEXT_EXT = {".md", ".py", ".abap", ".asddls", ".cds", ".json", ".txt", ".tmpl",
            ".yaml", ".yml", ".env", ".template", ".func"}

# Projeye-ozel token'lari normalize et (fark gurultusunu sustur).
NORMALIZERS = [
    (re.compile(r"ZSD0(0[1-9]|1[0-9])"), "ZSD0NN"),   # dev paket numaralari -> tek form
    (re.compile(r"\bVOYAGE\b|\bFITTINGS\b|\bDISPATCH\b", re.I), "DOMAIN"),
    (re.compile(r"<PROJECT_NAME>|<PROJECT_NAME>|<PROJECT_NAME>\s*Döküm"), "PROJ"),
    (re.compile(r"<SYSTEM_ID>|<SAP_HOST>"), "SYS"),
    (re.compile(r"<TRANSPORT>|[A-Z]{4}K9\d{5}"), "TR"),
    (re.compile(r"<SAP_USER>|<SAP_USER>", re.I), "USER"),
]


try:
    # Kaynak tarafini da TEMPLATE ile ayni generic forma indir (proje adi/yol/repo-URL/
    # ZSD<NNN>/ORDER/sistem/kullanici...). Template zaten generic -> genericize idempotent.
    # Boylece SADECE GERCEK metodoloji farki kalir (sahte genericize-token drift'i elenir).
    from genericize_for_template import genericize as _genericize  # type: ignore
except Exception:
    _genericize = None


def normalize(text):
    # Satır-sonu normalize (CRLF/CR -> LF) — aksi halde CRLF<->LF farki sahte DRIFT sisirir.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if _genericize is not None:
        text = _genericize(text)
    for rx, sub in NORMALIZERS:
        text = rx.sub(sub, text)
    return text


def in_scope(rel):
    s = rel.replace("\\", "/")
    if any(x in s for x in EXCLUDE):
        return False
    return any(s == m or s.startswith(m) for m in METHODOLOGY)


def collect(root):
    out = {}
    for p in Path(root).rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT:
            continue
        rel = str(p.relative_to(root))
        if not in_scope(rel):
            continue
        try:
            out[rel.replace("\\", "/")] = normalize(p.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, PermissionError):
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="Kaynak proje kök yolu")
    ap.add_argument("--template", default=".", help="Template kök yolu (varsayılan: .)")
    args = ap.parse_args()

    src = collect(args.source)
    tpl = collect(args.template)
    if not src:
        print(f"HATA: kaynakta metodoloji dosyası bulunamadı: {args.source}", file=sys.stderr)
        return 1

    drift, only_src, only_tpl, same = [], [], [], 0
    for rel, stext in sorted(src.items()):
        if rel not in tpl:
            only_src.append(rel)
        elif tpl[rel] != stext:
            drift.append(rel)
        else:
            same += 1
    only_tpl = sorted(set(tpl) - set(src))

    print(f"=== TEMPLATE DRIFT ===\nKaynak: {args.source}\nTemplate: {args.template}\n")
    print(f"DRIFT (kaynak değişmiş — port adayı): {len(drift)}")
    for r in drift:
        print(f"   ~ {r}")
    print(f"\nONLY_SOURCE (kaynakta var, template'te yok): {len(only_src)}")
    for r in only_src:
        print(f"   + {r}")
    print(f"\nONLY_TEMPLATE (template'e özel): {len(only_tpl)}")
    for r in only_tpl:
        print(f"   - {r}")
    print(f"\nSAME (senkron): {same}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
