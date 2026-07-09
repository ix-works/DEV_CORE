"""
agent_log.py — Alt-ajan audit helper (ADR 0018). SABİT ADRES = bu komut; arama YOK.

Alt-ajan transcript'leri: ~/.claude/projects/<proje>/<session-uuid>/subagents/agent-<id>.jsonl
(her ajanın TAM iç-işlemi: tool_use/result + SendMessage). meta: agent-<id>.meta.json = {"agentType": "<isim>"}.
Aktif session = o projedeki en-son-değişen top-level *.jsonl (otomatik çözülür).

Kullanım:
    python scripts/agent_log.py --list                  # bu session'daki ajanlar
    python scripts/agent_log.py --agent ajan3-booking   # o ajanın okunabilir timeline'ı
    python scripts/agent_log.py --agent bug-expert --tail 30
    python scripts/agent_log.py --list --all-sessions   # tüm session'lar
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/ importları
from utils.project_config import project_root

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ADR 0020: junction'da __file__ DEV_CORE'a çözülür → transcript klasör adı PROJE kökünden
# encode edilmeli (aksi halde alt-ajan logları DEV_CORE klasörüne bakar)
REPO = project_root()


def project_dir() -> Path:
    base = Path.home() / ".claude" / "projects"
    enc = re.sub(r"[^A-Za-z0-9]", "-", str(REPO))     # <PROJECT_ROOT> -> C--AI-PROJE-<PROJECT_NAME>
    cand = base / enc
    if cand.exists():
        return cand
    # fallback: en-son aktif *.jsonl barındıran alt-dizin
    subs = [d for d in base.glob("*") if d.is_dir() and list(d.glob("*.jsonl"))]
    if not subs:
        sys.exit(f"proje dizini bulunamadı: {base}")
    return max(subs, key=lambda d: max(os.path.getmtime(f) for f in d.glob("*.jsonl")))


def current_session_uuid(pdir: Path) -> str:
    js = list(pdir.glob("*.jsonl"))
    if not js:
        sys.exit("aktif session jsonl yok")
    return max(js, key=os.path.getmtime).stem


def subagents_dir(pdir: Path, uuid: str) -> Path:
    return pdir / uuid / "subagents"


def list_agents(sdir: Path):
    if not sdir.exists():
        print(f"(bu session'da alt-ajan yok: {sdir})")
        return
    rows = []
    for meta in sdir.glob("agent-*.meta.json"):
        jf = meta.with_suffix("").with_suffix(".jsonl")
        try:
            name = json.loads(meta.read_text(encoding="utf-8")).get("agentType", "?")
        except Exception:
            name = "?"
        n = sum(1 for _ in jf.open(encoding="utf-8", errors="replace")) if jf.exists() else 0
        mt = os.path.getmtime(jf) if jf.exists() else 0
        rows.append((mt, name, jf.stem.replace("agent-", "")[:12], n))
    for mt, name, aid, n in sorted(rows, reverse=True):
        import datetime
        ts = datetime.datetime.fromtimestamp(mt).strftime("%m-%d %H:%M") if mt else "-"
        print(f"  {ts}  {name:<22} id={aid:<14} olay={n}")


def find_agent_files(sdir: Path, name: str):
    out = []
    for meta in sdir.glob("agent-*.meta.json"):
        try:
            if json.loads(meta.read_text(encoding="utf-8")).get("agentType") == name:
                jf = meta.with_suffix("").with_suffix(".jsonl")
                if jf.exists():
                    out.append(jf)
        except Exception:
            pass
    return sorted(out, key=os.path.getmtime)


def brief(v, n=140):
    s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
    s = " ".join(s.split())
    return s[:n] + ("…" if len(s) > n else "")


def render(jf: Path, tail=None):
    events = []
    with jf.open(encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            try:
                events.append(json.loads(ln))
            except Exception:
                pass
    lines = []
    for e in events:
        ts = (e.get("timestamp") or "")[11:19]
        msg = e.get("message", {})
        if not isinstance(msg, dict):
            continue
        c = msg.get("content")
        if isinstance(c, str):
            if c.strip():
                lines.append(f"{ts}  TEXT: {brief(c)}")
        elif isinstance(c, list):
            for it in c:
                if not isinstance(it, dict):
                    continue
                t = it.get("type")
                if t == "text" and it.get("text", "").strip():
                    lines.append(f"{ts}  TEXT: {brief(it['text'])}")
                elif t == "tool_use":
                    nm = it.get("name")
                    inp = it.get("input", {}) or {}
                    if nm == "SendMessage":
                        lines.append(f"{ts}  →MSG to={inp.get('to')}: {brief(inp.get('summary') or inp.get('message'), 100)}")
                    elif nm == "Bash":
                        lines.append(f"{ts}  TOOL Bash: {brief(inp.get('command'), 100)}")
                    elif nm in ("Write", "Edit", "Read"):
                        lines.append(f"{ts}  TOOL {nm}: {inp.get('file_path', '')}")
                    else:
                        lines.append(f"{ts}  TOOL {nm}: {brief(inp, 90)}")
                elif t == "tool_result":
                    rc = it.get("content")
                    txt = rc if isinstance(rc, str) else json.dumps(rc, ensure_ascii=False)
                    lines.append(f"{ts}    ← {brief(txt, 120)}")
    if tail:
        lines = lines[-tail:]
    print("\n".join(lines) if lines else "(boş transcript)")


def main():
    ap = argparse.ArgumentParser(description="Alt-ajan audit log (ADR 0018)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--agent")
    ap.add_argument("--tail", type=int)
    ap.add_argument("--all-sessions", action="store_true")
    args = ap.parse_args()

    pdir = project_dir()
    uuid = current_session_uuid(pdir)
    sdir = subagents_dir(pdir, uuid)
    print(f"[session {uuid[:8]}]  {sdir}")

    if args.agent:
        files = find_agent_files(sdir, args.agent)
        if not files:
            sys.exit(f"'{args.agent}' bu session'da bulunamadı (--list ile gör)")
        jf = files[-1]  # en yeni (re-spawn varsa)
        print(f"--- {args.agent}  ({jf.name}, {len(files)} spawn'dan en yenisi) ---")
        render(jf, tail=args.tail)
    else:
        list_agents(sdir)


if __name__ == "__main__":
    main()
