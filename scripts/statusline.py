#!/usr/bin/env python3
"""Claude Code statusline — <PROJECT_NAME>.

Format: <SISTEM>/<TIER>[ RO] | ctx <N>% | Sprint <N> (<done>/<total>) | <TRANSPORT> | VPN <icon> | <branch> [| agents:<N>]
  ctx <N>% = context penceresi kullanim yuzdesi (yesil<50 · sari 50-74 · kirmizi>=75); %50'de proaktif compact/clear hatirlatici
  agents:<N> = o an aktif calisan ajan/task (ADR 0018 lazy: standing roster YOK; eski 'team:N' fallback kaldirildi — kapanmis ajanlari sayiyordu)

Input: JSON on stdin (model, workspace, cwd, etc.)
Output: single line to stdout.
Failures are silent — emit a minimal fallback so the bar never breaks Claude Code.
"""
import json
import os
import re
import socket
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
import sys as _pc_sys
from pathlib import Path as _pc_Path
_pc_sys.path.insert(0, str(_pc_Path(__file__).resolve().parents[0]))
from utils.project_config import SOURCE_ROOT_NAME  # K12: kaynak-klasor adi config'ten

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

SESSION_NOTE_NAME = "SESSION_NOTES.md"
ACTIVE_PKG_FILE = ".claude/active_package"
VPN_CACHE_FILE = ".claude/.statusline_vpn_cache"
VPN_CACHE_TTL_S = 60
VPN_TIMEOUT_S = 0.5
SAP_HOST_FALLBACK = "<SYSTEM_ID>"
SAP_PORT_FALLBACK = 8000

SPRINT_RX = re.compile(r"Sprint\s+(\d+\w?)(?:\s+ilerleme)?\s+(\d+)\s*/\s*(\d+)", re.IGNORECASE)
TRANSPORT_RX = re.compile(r"\b(DS4K\d{6})\b")


def read_stdin_json():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def workspace_root(payload):
    # CLAUDE_PROJECT_DIR önce: state dosyaları (.claude/*) HER ZAMAN proje kökünde
    # olmalı. cwd npm/ui5 build sırasında alt-klasöre kayarsa cache yanlış yere yazılır
    # → UI dist'e sızar → BSP deploy 400 (feedback_hook-komut-project-dir-execform).
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root and Path(env_root).exists():
        return Path(env_root)
    ws = payload.get("workspace") or {}
    if isinstance(ws, dict):
        for key in ("current_dir", "cwd", "root"):
            v = ws.get(key)
            if v and Path(v).exists():
                return Path(v)
    cwd = payload.get("cwd")
    if cwd and Path(cwd).exists():
        return Path(cwd)
    return Path.cwd()


def active_package(root: Path):
    state = root / ACTIVE_PKG_FILE
    if state.exists():
        name = state.read_text(encoding="utf-8", errors="ignore").strip()
        if name:
            return name, _find_session_notes_by_name(root, name)
    note = _latest_session_notes(root)
    if note:
        pkg = note.parent.name
        return pkg, note
    return None, None


def _find_session_notes_by_name(root: Path, pkg: str):
    for p in root.rglob(SESSION_NOTE_NAME):
        if p.parent.name.upper() == pkg.upper():
            return p
    return None


def _latest_session_notes(root: Path):
    candidates = []
    erp = root / SOURCE_ROOT_NAME
    if not erp.exists():
        return None
    for p in erp.rglob(SESSION_NOTE_NAME):
        try:
            candidates.append((p.stat().st_mtime, p))
        except OSError:
            continue
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def parse_session_notes(path: Path):
    sprint, done, total, transport = None, None, None, None
    if not path or not path.exists():
        return sprint, done, total, transport
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return sprint, done, total, transport
    head = "\n".join(text.splitlines()[:80])
    m = SPRINT_RX.search(head)
    if m:
        sprint = m.group(1)
        done = m.group(2)
        total = m.group(3)
    m2 = TRANSPORT_RX.search(head)
    if m2:
        transport = m2.group(1)
    return sprint, done, total, transport


def git_branch(root: Path):
    head = root / ".git" / "HEAD"
    if not head.exists():
        return None
    try:
        line = head.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return None
    if line.startswith("ref:"):
        return line.split("/", 2)[-1]
    return line[:7] if line else None


def sap_host_port(root: Path):
    url = os.getenv("ADT_SAP_URL")
    if not url:
        conn = root / ".conn_adt"
        if conn.exists():
            try:
                for line in conn.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.startswith("ADT_SAP_URL"):
                        _, _, val = line.partition("=")
                        url = val.strip().strip('"').strip("'")
                        break
            except OSError:
                pass
    if not url:
        return SAP_HOST_FALLBACK, SAP_PORT_FALLBACK
    parsed = urlparse(url if "://" in url else "https://" + url)
    host = parsed.hostname or SAP_HOST_FALLBACK
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, port


def sap_system(root: Path):
    """Aktif sistem adı + tier (.conn_adt → env fallback). Bağlandığımız sistemi gösterir."""
    name, tier = None, None
    conn = root / ".conn_adt"
    if conn.exists():
        try:
            for line in conn.read_text(encoding="utf-8", errors="ignore").splitlines():
                s = line.strip()
                if s.startswith("ADT_SAP_SYSTEM_NAME") and "=" in s:
                    name = s.split("=", 1)[1].strip() or name
                elif s.startswith("ADT_SAP_TIER") and "=" in s:
                    tier = (s.split("=", 1)[1].strip() or "").upper() or tier
        except OSError:
            pass
    name = name or os.getenv("ADT_SAP_SYSTEM_NAME")
    tier = tier or (os.getenv("ADT_SAP_TIER") or "").upper() or None
    return name, tier


def mcp_binding(root: Path):
    """MCP surecinin CANLI bagli oldugu sistem (.claude/.mcp_active_system). Yoksa None.

    MCP, client'i ilk cagrida .conn_adt'den baglar ve surec boyunca cache'ler; bu dosya
    o anlik baglanmayi yansitir. .conn_adt ile ayrisirsa /mcp restart gerekiyor demektir."""
    f = root / ".claude" / ".mcp_active_system"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def _host_of(url: str):
    if not url:
        return None
    return (urlparse(url if "://" in url else "https://" + url).hostname or "").lower() or None


def mcp_mismatch_label(root: Path):
    """MCP, .conn_adt'den FARKLI sisteme bagliysa (restart gerek) bir etiket dondur, yoksa None."""
    mcp = mcp_binding(root)
    if not mcp:
        return None  # MCP henuz bu surecte baglanmadi → bilgi yok, uyari verme
    conn_host, _ = sap_host_port(root)
    mcp_host = _host_of(mcp.get("url") or "")
    if not mcp_host or not conn_host or mcp_host == conn_host.lower():
        return None  # ayni sistem → uyari yok
    label = mcp.get("system") or mcp_host.split(".")[0].upper()
    if (mcp.get("tier") or "").upper() in ("QA", "PRD"):
        label += " RO"
    return label


def vpn_ok(root: Path):
    cache = root / VPN_CACHE_FILE
    now = time.time()
    if cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if now - data.get("ts", 0) < VPN_CACHE_TTL_S:
                return bool(data.get("ok"))
        except Exception:
            pass
    host, port = sap_host_port(root)
    ok = False
    try:
        with socket.create_connection((host, port), timeout=VPN_TIMEOUT_S):
            ok = True
    except Exception:
        ok = False
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"ok": ok, "ts": now}), encoding="utf-8")
    except OSError:
        pass
    return ok


def active_agents(payload):
    for key in ("agents", "active_agents", "background_tasks", "tasks"):
        v = payload.get(key)
        if isinstance(v, list):
            return len(v)
        if isinstance(v, int):
            return v
    return None


# ANSI renkler — context esigi GORUNUR olsun (%60 proaktif-compact hedefi)
_C_GREEN, _C_YELLOW, _C_RED, _C_RESET = "\033[32m", "\033[33m", "\033[31m", "\033[0m"


def context_pct(payload):
    """Context penceresi kullanim yuzdesi (statusline JSON: context_window.used_percentage,
    resmi pre-calculated alan). Erken oturum / compact sonrasi null olabilir -> None."""
    cw = payload.get("context_window")
    if not isinstance(cw, dict):
        return None
    val = cw.get("used_percentage")
    if val is None:
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _ctx_segment(pct):
    # Eylem penceresi %50-60 (kullanici tercihi). Gorunur esik asil kaldirac
    # (CLAUDE_AUTOCOMPACT_PCT_OVERRIDE garantisiz).
    # >=75 kirmizi (acil) · 50-74 sari (devam->compact / kesim->checkpoint+clear) · <50 yesil.
    color = _C_RED if pct >= 75 else _C_YELLOW if pct >= 50 else _C_GREEN
    return f"{color}ctx {pct}%{_C_RESET}"


def short_pkg(name):
    if not name:
        return None
    m = re.match(r"(Z[A-Z]+\d+)", name)
    return m.group(1) if m else name


def build_line(root: Path, payload):
    note = active_package(root)[1]  # PKG segmenti kaldırıldı; note yalnız Sprint/Transport için
    sprint, done, total, transport = parse_session_notes(note) if note else (None, None, None, None)
    branch = git_branch(root)
    vpn = vpn_ok(root)
    agents = active_agents(payload)
    pct = context_pct(payload)

    sys_name, tier = sap_system(root)
    if not sys_name:
        # ADT_SAP_SYSTEM_NAME yoksa (eski .conn_adt) host adindan turet — '?' gosterme.
        host, _ = sap_host_port(root)
        if host:
            sys_name = host.split(".")[0].upper()

    parts = []
    if sys_name:
        label = sys_name
        if tier:
            label += f"/{tier}"
        if tier in ("QA", "PRD"):
            label += " RO"  # salt-okunur: yanlislikla mutasyon denenmesin (ADR 0010)
        parts.append(label)

    # Context kullanim % — sol tarafta (dar terminalde sagdan kirpilmasin). %60'ta sariya doner.
    if pct is not None:
        parts.append(_ctx_segment(pct))

    # MCP .conn_adt'den farkli sisteme mi bagli? (switch_tier yapilmis ama /mcp edilmemis)
    mcp_warn = mcp_mismatch_label(root)
    if mcp_warn:
        parts.append(f"!MCP={mcp_warn} (/mcp)")
    # PKG segmenti KALDIRILDI (kullanıcı 2026-07-01): active_package/en-son-SESSION_NOTES
    #   chain'i çalışılan paketi otomatik yansıtmıyordu (yeni pakette SESSION_NOTES yoksa
    #   bayat kalıyordu, ör. ZSD001'de çalışırken 'ZSD001' gösteriyordu) → yanıltıcı, kaldırıldı.
    #   (note hâlâ Sprint/Transport için kullanılıyor.)
    if sprint:
        if done and total:
            parts.append(f"Sprint {sprint} ({done}/{total})")
        else:
            parts.append(f"Sprint {sprint}")
    if transport:
        parts.append(transport)
    parts.append(f"VPN {'OK' if vpn else 'X'}")
    if branch:
        parts.append(branch)
    # ADR 0018: standing roster YOK (lazy lifecycle). Yalnız CANLI aktif ajan sayisini goster.
    # Eski 'team:N' fallback'i kaldirildi: ~/.claude/teams/*/config.json members[] shutdown'da
    # budanmadigindan kapanmis efemeral ajanlari "duran takim" gibi sayiyordu (yaniltici birikme).
    if agents:
        parts.append(f"agents:{agents}")
    return " | ".join(parts)


def main():
    try:
        payload = read_stdin_json()
        root = workspace_root(payload)
        line = build_line(root, payload)
    except Exception:
        line = "<PROJECT_NAME>"
    sys.stdout.write(line)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
