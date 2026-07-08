#!/usr/bin/env python3
"""PreToolUse (matcher: Edit|Write) — PULL-BEFORE-EDIT gate (ADR 0016 revize).

Yönetilen bir SAP source dosyasını (<source_root>/ altı, source uzantısı) düzenlemeden ÖNCE,
o objenin canlı GÜNCEL hali bu SEANSTA çekilmiş/yazılmış olmalı. Değilse edit
BLOKLANIR (exit 2) ve agent önce `scripts/sap_sync_pull.py` ile çeker. Böylece
working-copy daima TAZE canlıdan türer → push, canlıdaki belgelenmemiş bir değişikliği
sessizce ezmez. (Eski M1 pre-push drift-block kaldırıldı; koruma artık edit-öncesine taşındı.)

MUAFİYET (sessiz GEÇ, exit 0):
  - SAP source DEĞİL (doküman/script/governance/ADR vb.) — gate yok.
  - ref_docs/ docs/ .tmp/ ... (deploy edilebilir kaynak değil) · class alt-include'ları.
  - Dosya YOK (yeni obje/yaratım — çekecek bir şey yok).
  - git-DIRTY (commit'siz yerel değişiklik = zaten üstünde çalışıyorsun; pull onu EZER → DOKUNMA).
  - session_id yoksa / store okunamıyorsa → fail-safe (editlemeyi brick'leme).

Bayatsa exit 2 (stderr → agent'a geri besler, ne yapacağını söyler).
"""
import io
import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
FRESH_STORE = ROOT / ".claude" / ".session_fresh.json"

_SOURCE_EXTS = (
    ".cds", ".ddls", ".asddls", ".bdef", ".srvd", ".srvb",
    ".abap", ".dcl", ".asdcls", ".ddlx", ".asddlxs",
)
_EXCLUDED_DIRS = {"ref_docs", "docs", ".tmp", "legacy", "_archive", "archive", "drafts"}
_CLASS_SUBSOURCE = (
    ".ccimp.abap", ".ccdef.abap", ".ccau.abap", ".ccmac.abap",
    ".clas.locals_def.abap", ".clas.locals_imp.abap",
    ".clas.testclasses.abap", ".clas.macros.abap",
)


def _is_managed_sap_source(p: Path) -> bool:
    n = p.name.lower()
    if not n.endswith(_SOURCE_EXTS):
        return False
    if n.endswith(_CLASS_SUBSOURCE):   # alt-include ana objeyle gelir, ayrı pull edilmez
        return False
    parts = {s.lower() for s in p.parts}
    if "erp" not in parts:
        return False
    if _EXCLUDED_DIRS & parts:
        return False
    return True


def _infer_type(p: Path) -> str:
    n = p.name.lower()
    if n.endswith(".bdef"):
        return "bdef"
    if n.endswith(".srvd"):
        return "srvd"
    if n.endswith(".srvb"):
        return "srvb"
    if n.endswith(".clas.abap"):
        return "class"
    if n.endswith(".prog.abap"):
        return "program"
    if n.endswith(".intf.abap"):
        return "interface"
    if n.endswith(".abap"):
        return "class"
    if n.endswith((".dcl", ".asdcls")):
        return "accesscontrol"
    if n.endswith((".ddlx", ".asddlxs")):
        return "metadataextension"
    return "ddls"   # .cds / .ddls / .asddls — DDLS endpoint (interface/consumption/DB-view)


def _object_name(p: Path) -> str:
    return p.name.split(".", 1)[0].upper()


def _git_dirty(p: Path) -> bool:
    """Working-tree'de commit'siz değişiklik var mı? (WIP → pull EZMESİN)."""
    try:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--", str(p)],
            capture_output=True, text=True, timeout=8,
        )
        return bool(r.stdout.strip())
    except Exception:
        return False   # git yoksa/çalışmazsa dirty sayma (fail-safe: gate'i koru)


def _is_fresh(session_id: str, obj: str) -> bool:
    try:
        store = json.loads(FRESH_STORE.read_text(encoding="utf-8"))
    except Exception:
        return False
    if store.get("session_id") != session_id:   # store başka seanstan → bayat
        return False
    return obj in (store.get("objects") or {})


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0   # input parse edilemedi → fail-safe geç

    tool = data.get("tool_name", "") or ""
    if tool not in ("Edit", "Write", "MultiEdit"):
        return 0

    ti = data.get("tool_input", {}) or {}
    fp = ti.get("file_path") or ti.get("path") or ""
    if not fp:
        return 0
    p = Path(fp)

    if not _is_managed_sap_source(p):
        return 0                       # SAP source değil → gate yok
    if not p.exists():
        return 0                       # yeni dosya/obje → çekecek bir şey yok
    if _git_dirty(p):
        return 0                       # WIP (commit'siz) → zaten üstünde çalışıyorsun

    session_id = str(data.get("session_id") or "")
    if not session_id:
        return 0                       # seans kimliği yok → fail-safe geç

    obj = _object_name(p)
    if _is_fresh(session_id, obj):
        return 0                       # bu seansta çekildi/push edildi → TAZE, geç

    obj_type = _infer_type(p)
    sys.stderr.write(
        f"⛔ PULL-BEFORE-EDIT (PreToolUse guard, ADR 0016 revize): '{obj}' bu seansta "
        f"SAP'den çekilMEDİ. Düzenlemeden ÖNCE güncel halini al:\n"
        f"   python scripts/sap_sync_pull.py {obj} --type {obj_type} --session {session_id}\n"
        f"(canlıyı çeker → {p.name} dosyasına yazar → seans-taze damgalar; sonra edit'i TEKRAR dene.)\n"
        f"AMAÇ: working-copy daima TAZE canlıdan türesin → push, canlıdaki belgelenmemiş "
        f"değişikliği ezmesin. Obje başına seansta yalnız 1 kez.\n"
        f"SAP erişilemiyorsa: `... --session {session_id} --offline` (fetch'siz taze damgalar; "
        f"canlıdan ezme riskini bilerek kabul edersin).\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
