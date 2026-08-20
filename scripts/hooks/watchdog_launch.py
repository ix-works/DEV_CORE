#!/usr/bin/env python3
"""PreToolUse(Agent) hook — arka-plan agent spawn edilince detached watchdog daemon'i baslatir.

Amac: SAP/VPN/MCP kopmasindan dogan sessiz stall'i, Claude/lider'e BAGIMLI OLMADAN,
kullaniciya dogrudan (Windows MessageBox + log) haber veren bir daemon'i garantiye almak.
- Session basina TEK daemon (heartbeat dosyasi ile idempotent — os.kill footgun'u YOK).
- Windows'ta DETACHED_PROCESS ile konsola bagimsiz baslatilir.
- additionalContext ile lidere de tek-satir bilgi enjekte eder (ilk spawn).
"""
import sys, json, os, time, subprocess, re

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
        notlar = []
        if eksik:
            notlar.append("[BRIFING-LINT] Spawn prompt'unda R2 sablon izleri eksik: "
                          + ", ".join(eksik)
                          + " — sablon: core/claude/templates/spawn-brief.md (kanit-kurallari + "
                            "gorev sinirlari + goreve-iliskin dersler alanlari zorunlu; "
                            "nudge, blok degil).")

        # --- ENGELLENIRSEN ekseni (sablon §9; 2026-08-20) --------------------
        # ⛔ VAKA: `isolation:"worktree"` ile acilan bir infra ajaninin worktree'si YANLIS
        # repoda olustu; charter'i canli agaca yazmayi yasakladigi icin YAZACAK YERI YOKTU.
        # Yasaga uydu, bekledi, HABER VERMEDI -> 26 dk olculebilir cikti SIFIR (watchdog
        # "heartbeat taze" diyordu: canlilik olcer, ILERLEME olcmez). Kusur ajanda degil
        # BRIFTEYDI.
        #
        # ⭐ EKSEN DAR TUTULDU, OLCULEREK (587 gercek brif, transcript korpusu):
        #   · ham "madde var mi?"                 -> %86,7 atesler  ⇒ KULLANILAMAZ
        #     (ilk gunde uyari korlugu; mevcut GOREV ekseninin tabani %25,0)
        #   · DAR eksen (baska-agac + yazma isi)  -> %18,4 kapsam, %16,0 atesleme
        #     ⇒ KB-01'in olculmus gurultu tabaniyla (%13,9) ayni bant.
        # Yani kontrol "herkese sablon ezberlet" demiyor; yalniz BASKA BIR AGACA YAZMA isi
        # verilen brifte kacis-yolunun yazili olmasini istiyor -- vakanin tam sekli.
        yer = _re.search(r"WORKTREE|ISOLATION|DEV_CORE|_WT[\\/ ]|AYRI DEPO|BASKA REPO", duz)
        yazma = _re.search(r"\bFIX\b|DUZELT|YAZ|OLUSTUR|URET|COMMIT|UYGULA|EKLE", duz)
        engel = _re.search(r"ENGELLEN|YAZACAK YER|DERHAL BILDIR|DERHAL .{0,20}SENDMESSAGE", duz)
        if yer and yazma and not engel:
            notlar.append(
                "[BRIFING-LINT] Bu brif BASKA BIR AGACA yazma isi veriyor ama "
                "'ENGELLENIRSEN DERHAL BILDIR' maddesi YOK (sablon §9). "
                "Olculmus vaka: yazacak yeri olmayan bir ajan yasaga uyup 26 dk SESSIZ "
                "bekledi; watchdog 'heartbeat taze' diyordu (canlilik != ilerleme). "
                "Ekle: 'Yazacak yerin yoksa/yasakla cakisiyorsan TAHMIN ETME, BEKLEME -> "
                "DERHAL SendMessage(to:\"main\")'. Ayrica worktree adresini brife YAZ.")
        if notlar:
            return "\n".join(notlar)
    except Exception:
        pass
    return None

# --- KB-01 ONCE-ARA ekseni (2026-08-19) -------------------------------------
# Neden METIN-IZI DEGIL ARAMA: 570 gercek brifing olculdu -> %98,6'si zaten bir
# yol/dosya atfi tasiyor. "Atif var mi" diye soran bir kontrol pratikte HERKESI
# gecirir (trivial yesil) ve bugunku uc isirigin UCUNU DE kacirirdi. Bu yuzden
# kontrol brifingin METNINI yargilamaz: aramayi KENDI yapar ve brifingin atif
# VERMEDIGI recete dosyasini geri bildirir. Gecmek icin yazilacak sihirli bir
# cumle YOKTUR (oyunlanamaz) -- cikti bir KARAR degil, bir ARAMA SONUCUDUR.
_PA_RX_PY = re.compile(r"\b([A-Za-z_][A-Za-z0-9_-]{2,})\.py\b")
_PA_RX_DOSYA = re.compile(r"\b[\w.-]+\.(?:py|md|abap|json|ya?ml)\b", re.IGNORECASE)
# Isabet esigi: token EN FAZLA bu kadar recetede geciyorsa "ozel recete" sayilir.
# 2 secildi (olcum: 1 -> vaka3 KACIYOR; 3 -> gurultu %17,0'dan %17,5'e cikar, kazanc yok).
_PA_ESIK = 2
_PA_UST_N = 3


def _prior_art_nudge(data):
    """Brifingde ADI GECEN core script'inin recetesi playbook'ta var mi, brifing ona
    atif veriyor mu? Vermiyorsa recete yolunu SPAWN ANINDA (tur ortasinda) verir.

    Sozlesme: None = soylenecek bir sey yok. Metin = ya bulgu ya da "KOSMADI" notu.
    ⛔ FAIL-OPEN YOK: kontrol kosamazsa SESSIZ kalmaz, KOSMADI der (exit 0 korunur --
    bu hook'un stdout'u JSON sozlesmesidir; gorunurluk additionalContext'ten gider).
    """
    try:
        ti = data.get("tool_input") or {}
        prompt = ti.get("prompt") or ""
        if len(prompt) < 400:
            return None  # kisa/mekanik spawn -- brifing-lint ile ayni muafiyet
        adaylar = {m.lower() for m in _PA_RX_PY.findall(prompt)}
        if not adaylar:
            return None  # hicbir script adi gecmiyor -> soracak sey yok
        proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        kok = os.path.join(proj, "core")
        if not os.path.isdir(os.path.join(kok, "playbook")):
            kok = proj  # core-repo'nun kendisinde junction yok
        pb_dir = os.path.join(kok, "playbook")
        sc_dir = os.path.join(kok, "scripts")
        if not os.path.isdir(pb_dir) or not os.path.isdir(sc_dir):
            return ("[PRIOR-ART] KOSMADI -- playbook/ ya da scripts/ bulunamadi (%s). "
                    "Bu SESSIZ GECIS DEGILDIR: KB-01 aramasini ELLE yap." % kok)
        # (a) adaylardan GERCEKTEN var olanlar (uydurma script adi gurultu yapmasin)
        gercek = set()
        for r, dirs, fs in os.walk(sc_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "attic", ".git")]
            for f in fs:
                if f.endswith(".py") and f[:-3].lower() in adaylar:
                    gercek.add(f[:-3].lower())
        if not gercek:
            return None
        # (b) recete taramasi
        isabet = {}
        for r, dirs, fs in os.walk(pb_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "attic", ".git")]
            for f in fs:
                if not f.endswith(".md"):
                    continue
                yol = os.path.join(r, f)
                try:
                    ic = open(yol, encoding="utf-8", errors="replace").read().lower()
                except Exception:
                    continue
                for t in gercek:
                    if (t + ".py") in ic:
                        isabet.setdefault(t, []).append(yol)
        # (c) brifingin ZATEN andigi dosya adlari isabet sayilmaz ("baktim" kaniti)
        anilan = {x.lower() for x in _PA_RX_DOSYA.findall(prompt)}
        bulgu = []
        for t, yollar in isabet.items():
            if len(yollar) > _PA_ESIK:
                continue  # her yerde gecen genel arac -> karar tasimaz
            if any(os.path.basename(y).lower() in anilan for y in yollar):
                continue  # brifing bu token icin ZATEN bir recete anmis = "baktim" kaniti
            bulgu.append((len(yollar), t, yollar))
        if not bulgu:
            return None
        bulgu.sort()
        satir = []
        for _n, t, yollar in bulgu[:_PA_UST_N]:
            kisa = [os.path.relpath(y, kok).replace("\\", "/") for y in yollar[:2]]
            satir.append("  - %s.py -> %s" % (t, ", ".join(kisa)))
        return ("[PRIOR-ART / KB-01] Brifingde adi gecen script'in RECETESI playbook'ta VAR; "
                "brifing o dosyaya atif VERMIYOR:\n" + "\n".join(satir) +
                "\n  Spawn'dan ONCE o bolumu OKU ya da yolunu ajana ver. Arama SENIN yerine "
                "yapildi -- 'baktim, ilgisiz' demek serbest; ATLAMAK serbest degil "
                "(CLAUDE.core.md KB-01).")
    except Exception as e:
        return ("[PRIOR-ART] KOSMADI -- kontrol hata verdi (%s: %s). Bu SESSIZ GECIS "
                "DEGILDIR: KB-01 aramasini ELLE yap." % (type(e).__name__, e))


def _ek_notlar(data):
    """brifing-lint + prior-art notlarini birlestirir. DAEMON'DAN BAGIMSIZ calisir:
    daemon/bash bulunamasa bile brifing kontrolleri kosar (eski davraniste bu yollar
    lint'e ulasmadan return ediyordu = sessiz atlama)."""
    parcalar = []
    for _f in (_brifing_lint, _prior_art_nudge):
        try:
            _n = _f(data)
        except Exception as e:  # kontrolun kendisi hook'u dusuremez
            _n = "[%s] KOSMADI -- %s: %s" % (_f.__name__, type(e).__name__, e)
        if _n:
            parcalar.append(_n)
    return ("\n" + "\n".join(parcalar)) if parcalar else ""


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Bos sozlukle devam edilir ve seans kimligi 'nosid'e duser -> watchdog YANLIS
    anahtarla acilir. Gerekce + sinif kaydi: scripts/hooks/README.md S4.
    Not STDERR'e gider: bu hook'un STDOUT'u JSON sozlesmesidir.
    """
    try:
        sys.stderr.write(
            "[watchdog_launch] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> BOS girdiyle "
            "devam (degrade, exit 0); seans kimligi 'nosid'e duser. "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
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
            emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ek + _ek_notlar(data)}})
            return
    except Exception:
        pass

    # Junction'lı projede core script'leri proj/core/ altındadır; core-repo'nun kendisinde proj/scripts/.
    daemon = os.path.join(proj, "core", "scripts", "hooks", "watchdog_daemon.sh")
    if not os.path.exists(daemon):
        daemon = os.path.join(proj, "scripts", "hooks", "watchdog_daemon.sh")
    if not os.path.exists(daemon):
        emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
              "additionalContext": "[WATCHDOG] daemon script yok (%s) — Monitor/cron'a dus." % daemon
              + _ek_notlar(data)}})
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
              "additionalContext": "[WATCHDOG] bash bulunamadi — detached daemon yok; 5dk cron watchdog aktif kalsin."
              + _ek_notlar(data)}})
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

    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
          "additionalContext": msg + _ek_notlar(data)}})


if __name__ == "__main__":
    main()
