#!/usr/bin/env python3
# ENFORCES: C-SPAWN-01  (ADR 0019 coverage binding)
"""PreToolUse(Agent) hook — alt-ajan spawn ANINDA brifing nudge'lari basar (blok YOK).

UC nudge dali, hepsi exit 0 / additionalContext:
- BRIFING-LINT      : R2 sablon izleri (GOREV/KANIT KURAL) + ENGELLENIRSEN ekseni
- PRIOR-ART / KB-01 : brifingde adi gecen core script'inin recetesi playbook'ta var mi
- AGENT-TYPE TUZAGI : `name` verilince infra_write_guard muafiyetinin dusmesi

Soylenecek bir sey yoksa STDOUT BOS kalir (sessiz).

⛔ SAP WATCHDOG DAEMON MEKANIZMASI KALDIRILDI (2026-08-29, kullanici karari) — geri
   EKLENMEZ. Bu hook detached daemon BASLATMAZ, `.tmp/claude_watchdog` heartbeat'i
   YAZMAZ, `[WATCHDOG]` satiri BASMAZ; `watchdog_stop.py` + `watchdog_daemon.sh`
   silindi ve `C-WATCH-01` kurali kaldirildi. Gerekce (olculdu): "oturum basina TEK
   daemon" iddiasina ragmen ayni anda 4 daemon canliydi (idempotentlik kirik), 2 bayat
   "SAP WATCHDOG ALERT" MessageBox acik kaldi ve `.tmp/watchdog-alerts.log`
   `reach=000 fails=26` yazarken kimse aksiyon almadi (uyari korlugu).
   Kanonik kayit: `governance/removed-controls.md` + `governance/infra-changelog.md`.
   Kapsam disi (AYRI arac, daemon degil): `scripts/agent_watchdog.sh` — Monitor ile
   ELLE kosulan stall izleyici.
"""
import sys, json, os, re

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
                # `.tmp` EXIST_OK ile burada acilir: daemon dali kaldirilana kadar (2026-08-29)
                # dizini main()'in `makedirs(.tmp/claude_watchdog)` cagrisi yan-etkiyle
                # yaratiyordu. O cagri gidince bu log SESSIZCE olurdu (except: pass).
                os.makedirs(os.path.join(_proj, ".tmp"), exist_ok=True)
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
        # "heartbeat taze" diyordu: canlilik olcer, ILERLEME olcmez -- ve tam da bu yuzden
        # o daemon 2026-08-29'da kaldirildi; DERS duruyor, MEKANIZMA yok). Kusur ajanda degil
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
                "bekledi; o gun kosan daemon 'heartbeat taze' diyordu -- CANLILIK, "
                "ILERLEME DEGILDIR (daemon 2026-08-29'da kaldirildi; ders duruyor). "
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


# --- AGENT-TYPE TUZAGI ekseni (2026-08-22, N1) -------------------------------
# ⛔ OLCULMUS VAKA (3 kez tekrarladi, her seferinde bir ajan turu YANDI): bir alt-ajan
# `subagent_type="infra-expert"` AMA `name="infra-kuyruk-2208"` ile spawn edilince
# harness'in yazma tarafina giden payload'da `agent_type` VERILEN ADA esitlenir.
# `infra_write_guard` muafiyeti (`MUAF_AJANLAR`) `agent_type`'a bakar => muafiyet DUSER
# ve ajan HICBIR infra dosyasina yazamaz; kusur ajanda degil SPAWN CAGRISINDADIR.
#
# ⛔ NEDEN GUARD'A DOKUNULMADI (M1 ELENDI, olcumle): yazma-tarafi payload'inda yalniz
# `agent_type` + `agent_id` var; ajan TANIMI (subagent_type) oraya HIC ulasmiyor =>
# guard kimligi "tipten" cozemez. Kusuru gorebilen TEK yer spawn anidir, cunku
# `subagent_type` ve `name` YALNIZ BURADA yan yana durur.
#
# ⛔ SIDDET = NUDGE (bloklamaz), ADR 0019 merdiveni: eylem GERI ALINABILIR (ajan yeniden
# spawn edilir) => runtime blok mesru degil. Kardes iki dal gibi not basar, exit 0.
#
# ⛔ MUAF KUME TEK KAYNAKTAN: `infra_write_guard.MUAF_AJANLAR` IMPORT edilir. Kopya liste
# tutmak bu evde olculmus curume sinifidir (ayni olgu iki yerde yasarsa biri bayatlar) --
# ustelik burada bayat kopya, muafiyeti OLMAYAN bir role uyari basmak demektir.
def _muaf_ajanlar():
    """infra_write_guard.MUAF_AJANLAR -- TEK KAYNAK.

    ⛔ sys.path ELLE kurulur: bu hook canlida `hook_shim.py` uzerinden `runpy` ile
    kosar ve o yolda `sys.path[0]` BOS olabilir => kardes-import dogrudan cagride
    YESIL, canlida OLU olurdu (bu evde olculmus kablolama sinifi). Dizin core'un
    KENDI varligidir => `__file__` turevi CORE-03 geregi MESRUDUR.
    """
    d = os.path.dirname(os.path.abspath(__file__))
    if d not in sys.path:
        sys.path.insert(0, d)
    from infra_write_guard import MUAF_AJANLAR  # type: ignore
    return set(MUAF_AJANLAR)


def _agent_type_tuzagi(data):
    """spawn'da `name` verilmis + rol MUAF ise: muafiyetin dusecegini SPAWN ANINDA soyle."""
    ti = data.get("tool_input")
    if not isinstance(ti, dict):
        return None
    st, ad = ti.get("subagent_type"), ti.get("name")
    if not isinstance(st, str) or not isinstance(ad, str):
        return None
    st, ad = st.strip(), ad.strip()
    # Ad YOKSA tuzak da YOK (dogru kullanim) · ad == tip ise `agent_type` DEGISMEZ.
    if not st or not ad or ad == st:
        return None
    try:
        muaf = _muaf_ajanlar()
    except Exception as e:
        # ⛔ FAIL-OPEN YOK: kume okunamadiysa "muaf degil" VARSAYILMAZ (o varsayim tam da
        # kacirdigimiz vakayi sessizce gecirirdi). KOSMADI denir, exit 0 korunur.
        return ("[AGENT-TYPE] KOSMADI -- muaf ajan kumesi okunamadi (%s: %s). Bu SESSIZ "
                "GECIS DEGILDIR: `name` verdiysen infra_write_guard muafiyetinin dustugunu "
                "ELLE dogrula." % (type(e).__name__, e))
    if st not in muaf:
        return None  # muafiyeti olmayan rolde kaybedilecek muafiyet de yok
    return ("[AGENT-TYPE TUZAGI] Spawn'da `name` VERILDI (%r) ve `subagent_type` (%r) ile "
            "AYNI DEGIL => harness `agent_type`'i VERDIGIN ADA esitler. "
            "`infra_write_guard` muafiyeti `subagent_type`'a DEGIL `agent_type`'a bakar "
            "(MUAF_AJANLAR) => MUAFIYET DUSER ve ajan hicbir infra dosyasina YAZAMAZ "
            "(tests/** + governance/** acik kalir). Olculdu: bu 3 kez tekrarladi, her "
            "seferinde bir ajan turu yandi. ONARIM: `name` alanini KALDIR -- "
            "`subagent_type` zaten yeterli. (Nudge; bloklamaz.)" % (ad, st))


def _ek_notlar(data):
    """UC nudge dalinin notlarini birlestirir; kontrolun kendisi hook'u dusuremez.

    ⛔ TEK EMIT YOLU (2026-08-29): daemon dali kaldirilmadan once bu fonksiyon DORT ayri
    dala (idempotent / daemon-yok / bash-yok / basari) elle eklenmisti ve eskiden bazi
    dallar lint'e ULASMADAN return ediyordu = sessiz atlama. Artik dal YOK; not uretimi
    main()'in tek cikisindan gecer."""
    parcalar = []
    for _f in (_brifing_lint, _prior_art_nudge, _agent_type_tuzagi):
        try:
            _n = _f(data)
        except Exception as e:  # kontrolun kendisi hook'u dusuremez
            _n = "[%s] KOSMADI -- %s: %s" % (_f.__name__, type(e).__name__, e)
        if _n:
            parcalar.append(_n)
    return ("\n" + "\n".join(parcalar)) if parcalar else ""


def _parse_fail_notu() -> None:
    """Parse-fail dalinin SESSIZLIGINI kaldirir; exit 0 fail-safe'i AYNEN korunur.

    Bos sozlukle devam edilir -> `tool_input` okunamaz, UC nudge dali da SESSIZ kalir
    (kayip: o spawn icin brifing kontrolu HIC kosmaz). Gerekce + sinif kaydi:
    scripts/hooks/README.md S4. Not STDERR'e gider: bu hook'un STDOUT'u JSON
    sozlesmesidir.
    """
    try:
        sys.stderr.write(
            "[watchdog_launch] GIRDI-PARSE-EDILEMEDI: stdin JSON okunamadi -> BOS girdiyle "
            "devam (degrade, exit 0); bu spawn icin brifing nudge'lari kosmaz. "
            "Negatif-test: governance/infra-test-recipes.md B0b\n")
    except Exception:
        pass


def main():
    """Nudge-only: not varsa additionalContext, yoksa STDOUT BOS.

    ⛔ Daemon dali 2026-08-29'da KALDIRILDI (dosya basligindaki gerekce). Buraya
    heartbeat / DETACHED Popen / `[WATCHDOG]` satiri GERI EKLENMEZ; capa
    `tests/fixtures/prior_art_kb01` P4 + `--mutasyon-daemon-geri`.
    """
    try:
        data = json.load(sys.stdin)
    except Exception:
        _parse_fail_notu()
        data = {}
    notlar = _ek_notlar(data).strip("\n")
    if notlar:
        emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
              "additionalContext": notlar}})


if __name__ == "__main__":
    main()
