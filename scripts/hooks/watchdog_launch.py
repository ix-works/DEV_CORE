#!/usr/bin/env python3
"""PreToolUse(Agent) hook — arka-plan agent spawn edilince detached watchdog daemon'i baslatir.

Amac: SAP/VPN/MCP kopmasindan dogan sessiz stall'i, Claude/lider'e BAGIMLI OLMADAN,
kullaniciya dogrudan (Windows MessageBox + log) haber veren bir daemon'i garantiye almak.
- Session basina TEK daemon (heartbeat dosyasi ile idempotent — os.kill footgun'u YOK).
- Windows'ta DETACHED_PROCESS ile konsola bagimsiz baslatilir.
- additionalContext ile lidere de tek-satir bilgi enjekte eder (ilk spawn).
"""
import sys, json, os, time, subprocess

# Windows konsolu/pipe'i cp1252'dir: non-ASCII basmak UnicodeEncodeError ile COKER
# (exit 1 -> gercek FAIL'den ayirt edilemez). C-ENC-01 / check_console_utf8.py
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


def emit(obj):
    sys.stdout.write(json.dumps(obj))



def _brifing_lint(data):
    """T2.8 (2026-07-31): spawn prompt'unda R2 sablon izleri var mi? BLOKLAMAZ — nudge.
    Sablon: core/claude/templates/spawn-brief.md. Kisa/mekanik spawn'lar (<400 karakter,
    ör. test-echo) muaf — sablon zorunlulugu substantive isler icindir."""
    try:
        ti = data.get("tool_input") or {}
        prompt = ti.get("prompt") or ""
        if len(prompt) < 400:
            return None
        # NFKD-katla + regex-toleransli eslesme. Canli FP 2026-08-01: izole testte ayni
        # metin TEMIZ ama harness-payload'inda 'GÖREV' bulunamadi ('KANIT KURAL' bulundu)
        # -> temsil farki. Teshis icin bulunamayan anahtarin cevresi .tmp'ye loglanir;
        # kok-analiz radar madde-7'de.
        import re as _re
        import unicodedata
        duz = "".join(c for c in unicodedata.normalize("NFKD", prompt.upper())
                      if not unicodedata.combining(c)).replace("İ", "I")
        desenler = {"GOREV": _re.compile(r"G[OÖ0]?.?REV"), "KANIT KURAL": _re.compile(r"KANIT[ -]KURAL")}
        eksik = [a for a, rx in desenler.items() if not rx.search(duz)]
        if eksik:
            try:
                import datetime as _dt
                _proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
                with open(os.path.join(_proj, ".tmp", "brifing-lint-debug.log"), "a",
                          encoding="utf-8") as _f:
                    _f.write(f"{_dt.datetime.now().isoformat()} eksik={eksik} "
                             f"ilk300={duz[:300]!r}\n")
            except Exception:
                pass
        if eksik:
            return ("[BRIFING-LINT] Spawn prompt'unda R2 sablon izleri eksik: "
                    + ", ".join(eksik)
                    + " — sablon: core/claude/templates/spawn-brief.md (kanit-kurallari + "
                      "gorev sinirlari + goreve-iliskin dersler alanlari zorunlu; nudge, blok degil).")
    except Exception:
        pass
    return None

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    sid = str(data.get("session_id", "nosid")).replace("/", "_").replace("\\", "_")[:64] or "nosid"
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    wd = os.path.join(proj, ".tmp", "claude_watchdog")
    try:
        os.makedirs(wd, exist_ok=True)
    except Exception:
        pass

    hb = os.path.join(wd, "heartbeat_" + sid)
    # Zaten canli daemon var mi? (heartbeat < 200s taze) -> tekrar baslatma AMA tek-satir teyit ver
    # (#1: sessiz suppressOutput yerine "zaten canli, hb=Ns" -> "yine baslamadi mi" suphesi kalksin).
    try:
        if os.path.exists(hb) and (time.time() - os.path.getmtime(hb)) < 200:
            age = int(time.time() - os.path.getmtime(hb))
            ek = "[WATCHDOG] Zaten canli (seans basina 1 daemon) — heartbeat %ss taze; yeniden baslatilmadi (idempotent, hata degil)." % age
            lint = _brifing_lint(data)
            if lint:
                ek += "\n" + lint
            emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ek}})
            return
    except Exception:
        pass

    # Junction'lı projede core script'leri proj/core/ altındadır; core-repo'nun kendisinde proj/scripts/.
    daemon = os.path.join(proj, "core", "scripts", "hooks", "watchdog_daemon.sh")
    if not os.path.exists(daemon):
        daemon = os.path.join(proj, "scripts", "hooks", "watchdog_daemon.sh")
    if not os.path.exists(daemon):
        emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
              "additionalContext": "[WATCHDOG] daemon script yok (%s) — Monitor/cron'a dus." % daemon}})
        return

    # KRITIK: hook ortaminda 'bash' PATH'te olmayabilir (gercek sebep buydu) -> MUTLAK yol coz.
    bash_exe = None
    try:
        import shutil
        bash_exe = shutil.which("bash")
    except Exception:
        pass
    if not bash_exe:
        for c in (r"C:\Program Files\Git\bin\bash.exe",
                  r"C:\Program Files\Git\usr\bin\bash.exe",
                  r"C:\Program Files (x86)\Git\bin\bash.exe",
                  "/usr/bin/bash", "/bin/bash"):
            if os.path.exists(c):
                bash_exe = c
                break
    if not bash_exe:
        emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
              "additionalContext": "[WATCHDOG] bash bulunamadi — detached daemon yok; 5dk cron watchdog aktif kalsin."}})
        return

    # OUTER Popen = bash_exe MUTLAK (hook PATH'inde bash yok). INNER = bare `bash`
    # (outer git-bash icinde calisir, orada 'bash' PATH'te var; mutlak-Windows-path'i MSYS exec edemez).
    # PROJ arg2 olarak açıkça geçilir: daemon core'da yaşadığından BASH_SOURCE-türetimi
    # junction'da DEV_CORE'a çözülür — proje kökünü launcher bilir (env-first).
    daemon_posix = daemon.replace("\\", "/")
    proj_posix = proj.replace("\\", "/")
    launch_cmd = "nohup bash '%s' '%s' '%s' >/dev/null 2>&1 &" % (daemon_posix, sid, proj_posix)
    try:
        subprocess.Popen(
            [bash_exe, "-c", launch_cmd],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=proj, close_fds=True,
        )
        msg = ("[WATCHDOG] Detached daemon baslatildi (session basina 1). SAP reach ~100s izler; "
               "2 tur erisimsizde Windows MessageBox + .tmp/watchdog-alerts.log ALERT — SENDEN BAGIMSIZ. "
               "~2s icinde expire; SessionEnd'de kapanir.")
    except Exception as e:
        msg = "[WATCHDOG] daemon baslatilamadi (%s) — 5dk cron watchdog aktif." % e

    lint = _brifing_lint(data)
    if lint:
        msg += "\n" + lint
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}})


if __name__ == "__main__":
    main()
