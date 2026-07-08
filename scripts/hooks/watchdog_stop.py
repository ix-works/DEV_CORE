#!/usr/bin/env python3
"""SessionEnd hook — bu session'in detached watchdog daemon'ini durdurur (stop-sentinel).

Daemon her <=10s stop-sentinel kontrol eder -> hizli ve temiz cikar (post-session
yanlis-alarm YOK). os.kill/pid yok (Windows TerminateProcess footgun'undan kacinir).
"""
import sys, json, os, glob


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    sid = str(data.get("session_id", "")).replace("/", "_").replace("\\", "_")[:64]
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    wd = os.path.join(proj, ".tmp", "claude_watchdog")

    def stop(s):
        try:
            open(os.path.join(wd, "stop_" + s), "w").close()
        except Exception:
            pass

    if sid:
        stop(sid)
    else:
        # sid yoksa tum canli daemon'lara stop yaz (heartbeat_* -> stop_*).
        for f in glob.glob(os.path.join(wd, "heartbeat_*")):
            stop(os.path.basename(f)[len("heartbeat_"):])

    sys.stdout.write(json.dumps({"suppressOutput": True}))


if __name__ == "__main__":
    main()
