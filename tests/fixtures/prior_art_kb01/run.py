#!/usr/bin/env python3
"""KB-01 ONCE-ARA tur-ici hatirlaticisi (watchdog_launch._prior_art_nudge).

NEDEN BU KORPUS VAR
-------------------
KB-01 ("once ARA, sonra yaz/karar ver") MUST'tir ama zorlamasi `post_validate` nudge'i +
reviewer'di: ikisi de YAZIM SONRASI / KURAL-DOSYASI yolunda. Karar TUR ORTASINDA, alt-ajan
brifingi yazilirken veriliyor ve o yolda hicbir sey ates etmiyordu (lessons PATTERN #30).

⛔ NEDEN "ATIF VAR MI" DIYE SORMUYOR: 570 gercek brifing olculdu -> **%98,6'si zaten bir
yol/dosya atfi tasiyor**. Metin-izi arayan bir kontrol herkesi gecirirdi (trivial yesil).
Kontrol bu yuzden brifingin metnini YARGILAMAZ: aramayi kendi yapar, brifingin atif
vermedigi recete dosyasini geri bildirir. Gecmek icin yazilacak sihirli cumle YOKTUR.

AYRICA — AGENT-TYPE TUZAGI dali (2026-08-22, N1). Ayni hook'un UCUNCU nudge dali:
alt-ajan `subagent_type="infra-expert"` + `name="<baska ad>"` ile spawn edilince harness
`agent_type`'i VERILEN ADA esitler; `infra_write_guard` muafiyeti `agent_type`'a baktigi
icin DUSER ve ajan hicbir infra dosyasina yazamaz. 3 kez tekrarladi, her seferinde bir
ajan turu yandi. Kusuru gorebilen TEK yer spawn anidir (`subagent_type` ile `name` YALNIZ
burada yan yana durur) -- yazma-tarafi payload'inda ajan TANIMI yoktur, bu yuzden guard'a
dokunulmadi.

⛔ NEDEN RUNPY VEKTORU (A5) SILINEMEZ: dal, muaf kumeyi `infra_write_guard`tan IMPORT
eder (kopya liste tutulmaz). Canlida bu hook `hook_shim` uzerinden `runpy.run_path` ile
kosar ve o yolda `sys.path[0]` BOS olabilir => kardes-import DOGRUDAN cagride YESIL,
CANLIDA OLU olurdu. A5 tam o cagri seklini kurar (bu evde olculmus kablolama sinifi).

⛔ DAEMON KALDIRILDI (2026-08-29, kullanici karari): bu hook artik SAP watchdog daemon'i
BASLATMAZ. `watchdog_stop.py` + `watchdog_daemon.sh` silindi, `C-WATCH-01` kaldirildi
(`governance/removed-controls.md`). ESKI P4 vektoru ("dort emit yolunun hepsinde not
cikar") KENDINI EMEKLIYE AYIRDI ve kaldirmanin KENDI degismezine tasindi: heartbeat
dizini YARATILMAZ + `[WATCHDOG]` izi YOK. Mutasyonu `--mutasyon-daemon-geri`.

KOSUM:  python tests/fixtures/prior_art_kb01/run.py
        python tests/fixtures/prior_art_kb01/run.py --mutasyon            (kontrolu SOK)
        python tests/fixtures/prior_art_kb01/run.py --mutasyon-failopen   (KOSMADI'yi sustur)
        python tests/fixtures/prior_art_kb01/run.py --mutasyon-agent-type (N1 dalini SOK)
        python tests/fixtures/prior_art_kb01/run.py --mutasyon-agent-syspath
                                                    (N1: runpy sys.path capasini SOK)
        python tests/fixtures/prior_art_kb01/run.py --mutasyon-daemon-geri
                                                    (reddedilen daemon tasarimini ENJEKTE et)
Cikis:  0 hepsi beklendigi gibi · 1 sapma · 2 DOGRULANAMADI (mutasyon capasi tutmadi)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent          # <repo>/tests/fixtures/<ad>/run.py
HOOK = REPO / "scripts" / "hooks" / "watchdog_launch.py"

# --- mutasyon capalari (taban SHA degil, ICERIK capasi) ----------------------
MUT_SOK = (
    '        adaylar = {m.lower() for m in _PA_RX_PY.findall(prompt)}',
    '        adaylar = set()  # MUTASYON: kontrol sokuldu',
)
MUT_FAILOPEN = (
    '            return ("[PRIOR-ART] KOSMADI -- playbook/ ya da scripts/ bulunamadi (%s). "\n'
    '                    "Bu SESSIZ GECIS DEGILDIR: KB-01 aramasini ELLE yap." % kok)',
    '            return None  # MUTASYON: fail-open (sessiz gecis)',
)

VAKA3 = (
    "9 tablo nasil yazilsin? (`ack_drop` guard-asimi onayi gerekiyor) "
    "A - ack_drop=\"client\" ile MCP yolu (Onerilen): adt_push_source ile 9 tablo yazilir. "
    "Reviewer'in 4 kontrolunden 3'u PASS; dusen kontrol 'client alani kayboluyor' diyor - ama "
    "o alan SAP'nin KENDI shell varsayilani ve bizim DDL'imiz onun yerine 'key mandt' koyuyor "
    "(playbook 28.3-3'un zorunlu kildigi donusum; 0c kapisi zaten dogruladi). Tablolar aktive "
    "edilmedigi icin DB'de nesne yok, veri kaybi fiziksel olarak imkansiz. "
    "B - once populate_tables.py'yi duzelt: CORRNR okuma duzeltmesi (infra-fix akisi). Iki "
    "sakincasi var: yeni kod kesintisiz kosunun kritik yoluna girer ve o yol raw-REST oldugu "
    "icin reviewer'i HIC calistirmaz, yani drop-guard'i da atlar. "
    "C - 9 shell'i bana devret (SE11): tablolari sen SE11'den yaratirsin; 175 alani elle "
    "girmek demek, CSV'ler hazir oldugu icin bu secenegin maliyeti yuksek. GOREV ve KANIT KURAL."
)


# --- N1 mutasyon capalari (2026-08-22) --------------------------------------
# ⛔ IKI DEGISMEZ -> IKI MUTASYON, hicbiri otekini KAPSAMAZ:
#   (a) dalin `_ek_notlar` uretim hattina KABLOLU olmasi (kod yazilmis olmasi yetmez)
#   (b) kardes-import'un RUNPY yolunda ayakta kalmasi (sys.path capasi)
# (b) olmadan (a) "dogrudan cagride calisiyor" der ve CANLIDA sessizce olurdu.
MUT_AGENT_TYPE = (
    "    for _f in (_brifing_lint, _prior_art_nudge, _agent_type_tuzagi):",
    "    for _f in (_brifing_lint, _prior_art_nudge):")
MUT_AGENT_SYSPATH = (
    "    d = os.path.dirname(os.path.abspath(__file__))\n"
    "    if d not in sys.path:\n"
    "        sys.path.insert(0, d)\n",
    "")

# ⛔ KALDIRMANIN MUTASYONU (2026-08-29) — "yeni kodda mutasyon tabani = REDDEDILEN
# TASARIM". SAP watchdog daemon mekanizmasi komple kaldirildi; taban artik daemon'suz
# oldugu icin `git show <sha>` ile geri alinacak bir taban YOK => reddedilen tasarim
# ENJEKTE edilir (heartbeat dizini + `[WATCHDOG]` satiri) ve P4 DUSMELIDIR. Bu capa
# olmadan P4 "bugun daemon yok" diye trivial-yesil olurdu ve daemon sessizce geri
# eklenebilirdi. Gerekce: governance/removed-controls.md (2026-08-29 satiri).
MUT_DAEMON_GERI = (
    '    notlar = _ek_notlar(data).strip("\\n")\n',
    '    notlar = _ek_notlar(data).strip("\\n")\n'
    "    # MUTASYON: reddedilen daemon tasarimi geri getirildi\n"
    "    try:\n"
    "        os.makedirs(os.path.join(os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd(),\n"
    "                                 '.tmp', 'claude_watchdog'), exist_ok=True)\n"
    "    except Exception:\n"
    "        pass\n"
    "    notlar = '[WATCHDOG] Detached daemon baslatildi.\\n' + notlar\n")


def _uzun(govde: str) -> str:
    """Brifing-lint muafiyet esigi 400 karakter; vektorler onun USTUNDE olmali."""
    dolgu = (" Bagimsiz okuma cagrilarini tek turda paralel gonder; ara urunleri diske yaz; "
             "kanitsiz iddia rapora yazilmaz; bulunamadi degildir yok. ")
    while len(govde) < 520:
        govde += dolgu
    return govde


def sandbox_kur(kok: Path, junction_sekli: bool = True) -> None:
    """Hermetik sahte proje: <kok>[/core]/playbook + /scripts."""
    taban = kok / "core" if junction_sekli else kok
    pb, sc = taban / "playbook", taban / "scripts"
    pb.mkdir(parents=True, exist_ok=True)
    sc.mkdir(parents=True, exist_ok=True)
    # recete evi: populate_tables.py TAM 2 dosyada gecer (esik = 2 -> isabet sayilir)
    (pb / "adt-tables-structures.md").write_text(
        "# Z Tablo Yaratma\n## 15. Z Tablo (TABL/DT) Yaratma\n"
        "### 28.0 Hazir Production Script\n"
        "python scripts/populate_tables.py --csv x.csv --force-recreate\n",
        encoding="utf-8")
    (pb / "00-discipline-and-principles.md").write_text(
        "# Disiplin\nUretim script'leri: populate_tables.py, populate_domains.py\n",
        encoding="utf-8")
    # esik USTU kontrol: her_yerde.py UC recetede gecer -> karar tasimaz, sessiz kalmali
    for ad in ("a.md", "b.md", "c.md"):
        (pb / ad).write_text("genel arac her_yerde.py her yerde gecer\n", encoding="utf-8")
    for ad in ("populate_tables.py", "populate_domains.py", "her_yerde.py"):
        (sc / ad).write_text("# sahte script\n", encoding="utf-8")


def kos(hook: Path, proje: Path, payload: dict, ham: bytes | None = None):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    env["PYTHONIOENCODING"] = "utf-8"
    girdi = ham if ham is not None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    p = subprocess.run([sys.executable, str(hook)], input=girdi, env=env,
                       capture_output=True, cwd=str(proje), timeout=120)
    out = p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace")
    try:
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        gecerli_json = True
    except Exception:
        ctx, gecerli_json = "", (out.strip() == "")
    return p.returncode, ctx, err, gecerli_json


def payload(prompt: str, sid: str = "pa-test") -> dict:
    return {"session_id": sid, "tool_name": "Agent", "tool_input": {"prompt": prompt}}


def main() -> int:
    # BILINMEYEN KIP SESSIZCE YESIL GECMESIN (2026-08-22): `--mutasyon-ZIRVA` gibi bir
    # yazim hatasi eskiden HIC mutasyon kurmadan TAM PUAN uretiyordu (exit 0).
    gecerli = {"--mutasyon", "--mutasyon-failopen", "--mutasyon-agent-type",
               "--mutasyon-agent-syspath", "--mutasyon-daemon-geri"}
    for a in sys.argv[1:]:
        if a.startswith("--mutasyon") and a not in gecerli:
            raise SystemExit(f"[KULLANIM] bilinmeyen mutasyon kipi: {a} -> gecerli: "
                             + ", ".join(sorted(gecerli)))

    mutasyon = "--mutasyon" in sys.argv
    mut_failopen = "--mutasyon-failopen" in sys.argv
    mut_at = "--mutasyon-agent-type" in sys.argv
    mut_syspath = "--mutasyon-agent-syspath" in sys.argv
    mut_daemon = "--mutasyon-daemon-geri" in sys.argv
    hook = HOOK
    yedek = None

    if mutasyon or mut_failopen or mut_at or mut_syspath or mut_daemon:
        kaynak = HOOK.read_text(encoding="utf-8")
        if mut_at:
            eski, yeni = MUT_AGENT_TYPE
        elif mut_syspath:
            eski, yeni = MUT_AGENT_SYSPATH
        elif mut_daemon:
            eski, yeni = MUT_DAEMON_GERI
        else:
            eski, yeni = MUT_SOK if mutasyon else MUT_FAILOPEN
        if eski not in kaynak:
            print("[DOGRULANAMADI] mutasyon capasi tabanda bulunamadi -> mutasyon "
                  "gercekten uygulanmadi; 'gecti' sonucu ANLAMSIZ olurdu.")
            return 2
        # Mutant KOMSULARINI bulabilsin diye scripts/hooks ICINE yazilir (runpy/import sinifi)
        hook = HOOK.with_name("_mutant_watchdog_launch.py")
        hook.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8")
        yedek = hook

    tmp = Path(tempfile.mkdtemp(prefix="pa_kb01_"))
    sonuc = []
    try:
        sb = tmp / "proje"
        sandbox_kur(sb)
        sb_duz = tmp / "corerepo"          # junction'siz core-repo sekli (3. baglam)
        sandbox_kur(sb_duz, junction_sekli=False)
        bos = tmp / "playbooksuz"          # playbook/ YOK -> KOSMADI beklenir
        bos.mkdir(parents=True, exist_ok=True)

        PA = "[PRIOR-ART / KB-01]"
        KOSMADI = "[PRIOR-ART] KOSMADI"
        LINT = "[BRIFING-LINT]"

        atifsiz = _uzun(
            "GOREV: populate_tables.py ile 9 tabloyu yaz. KANIT KURALLARI gecerlidir. "
            "Kapsam: yalniz bu 9 tablo; CSV'ler hazir. Cikti: SendMessage(to:main). ")
        atifli = atifsiz + " OKU: playbook/adt-tables-structures.md (recete burada)."

        def ekle(ad, kosul, aciklama):
            sonuc.append((ad, bool(kosul), aciklama))

        # --- P: AYIRT EDICILER ------------------------------------------------
        rc, ctx, _e, ok = kos(hook, sb, payload(atifsiz))
        ekle("P1 atifsiz-brifing YAKALANIR",
             PA in ctx and "adt-tables-structures.md" in ctx,
             "script adi gecti, recete var, atif YOK -> recete yolu verilmeli")
        ekle("P1b stdout sozlesmesi", rc == 0 and ok, f"exit={rc} gecerli-json={ok}")

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(VAKA3)))
        ekle("P2 GERCEK VAKA (2026-08-19 16:53 payload'i)",
             PA in ctx and "adt-tables-structures.md" in ctx,
             "o gun ~40 dk kaybettiren recete spawn aninda yuzeye cikmali")

        rc, ctx, _e, _ok = kos(hook, sb_duz, payload(atifsiz))
        ekle("P3 3.BAGLAM junction'siz core-repo sekli",
             PA in ctx and "adt-tables-structures.md" in ctx,
             "core/ alt dizini YOKken proje kokunun kendisi taranmali")

        # ⭐ P4 (2026-08-29 REPOINT) — DAEMON KALDIRILDI, GERI GELMESIN.
        # ESKI P4: "dort emit yolunun (idempotent/daemon-yok/bash-yok/basari) hepsinde
        # not cikar" -- heartbeat dosyasi kurup idempotent dali zorluyordu. SAP watchdog
        # daemon mekanizmasi komple kaldirilinca (kullanici karari) o senaryo KENDINI
        # EMEKLIYE AYIRDI: dal YOK, tek emit yolu var. Vektor SILINMEDI, kaldirmanin
        # KENDI degismezine tasindi -- yoksa mutasyonlar (M) emekli olamaz ve suit
        # [YAMA TUTMADI]/[KACTI] ile kirmizi kalirdi.
        # ⛔ DEGISMEZ: hook heartbeat dizinini YARATMAZ, `[WATCHDOG]` BASMAZ; nudge cikar.
        temiz = tmp / "daemonsuz"
        sandbox_kur(temiz)
        wd_yol = temiz / ".tmp" / "claude_watchdog"
        rc, ctx, _e, ok = kos(hook, temiz, payload(atifsiz))
        ekle("P4 DAEMON KALDIRILDI: .tmp/claude_watchdog YARATILMAZ + [WATCHDOG] izi YOK "
             "(nudge yine cikar)",
             (not wd_yol.exists()) and "[WATCHDOG]" not in ctx and PA in ctx
             and rc == 0 and ok,
             f"heartbeat_dizini={wd_yol.exists()} watchdog_izi={'[WATCHDOG]' in ctx} "
             f"nudge={PA in ctx} exit={rc}")

        # --- N: YANLIS-POZITIF CAPALARI (mutasyonda AYAKTA KALMALI) -----------
        rc, ctx, _e, _ok = kos(hook, sb, payload(atifli))
        ekle("N1 FP: recete ZATEN anilmis -> sessiz",
             PA not in ctx and KOSMADI not in ctx,
             "'baktim' kaniti varsa tekrar durtme")

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: FS dokumanini oku ve ozetle. KANIT KURALLARI gecerlidir. ")))
        ekle("N2 FP: hicbir script adi yok -> sessiz", PA not in ctx and KOSMADI not in ctx, "")

        rc, ctx, _e, _ok = kos(hook, sb, payload("populate_tables.py kos."))
        ekle("N3 FP: <400 karakter mekanik spawn -> sessiz",
             PA not in ctx and KOSMADI not in ctx, "brifing-lint ile AYNI muafiyet")

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: hicbir_yerde_olmayan_script.py ile calis. KANIT KURALLARI gecerli. ")))
        ekle("N4 FP: var OLMAYAN script adi -> sessiz",
             PA not in ctx and KOSMADI not in ctx, "envanter filtresi (uydurma ad gurultu yapmaz)")

        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "GOREV: her_yerde.py kullan. KANIT KURALLARI gecerlidir. ")))
        ekle("N5 FP: 3 recetede gecen GENEL arac -> sessiz",
             PA not in ctx and KOSMADI not in ctx, "esik=2; her yerde gecen arac karar tasimaz")

        # --- K: KONTROL GRUBU / KABLOLAMA (mevcut davranis bozulmadi mi) ------
        rc, ctx, _e, _ok = kos(hook, sb, payload(_uzun(
            "Su dosyayi duzenle ve populate_tables.py'yi kos. Sablon izleri kasten yok. ")))
        ekle("K1 BRIFING-LINT REGRESYONU: sablonsuz brifing hala uyarilir",
             LINT in ctx, "prior-art ekseni eski nudge'i yutmamali")
        ekle("K1b iki eksen AYNI anda cikabilir", LINT in ctx and PA in ctx, "")

        rc, ctx, _e, _ok = kos(hook, sb, payload(atifli))
        ekle("K2 BRIFING-LINT kontrol grubu: sablonlu brifing uyarilmaz",
             LINT not in ctx, "GOREV + KANIT KURAL var -> lint sessiz")

        # --- F: FAIL-OPEN YASAGI ----------------------------------------------
        rc, ctx, _e, ok = kos(hook, bos, payload(atifsiz))
        ekle("F1 OLCEMEDIM != TEMIZ: playbook/ yokken KOSMADI der",
             KOSMADI in ctx, "sessiz exit 0 = 'sorun yok' diye okunur; yasak")
        ekle("F1b KOSMADI'da da stdout sozlesmesi korunur", rc == 0 and ok, f"exit={rc}")

        # === A) AGENT-TYPE TUZAGI (N1, 2026-08-22) =========================
        AT = "[AGENT-TYPE TUZAGI]"
        AT_KOSMADI = "[AGENT-TYPE] KOSMADI"

        def at_payload(ti):
            d = payload("x")
            d["tool_input"] = dict(ti, prompt="kisa spawn")
            return d

        # ⚠ VEKTORLER GERCEK TRANSCRIPT'TEN (2026-08-22, uc canli spawn):
        #   {'subagent_type':'infra-expert','name':'infra-kuyruk-2208'}  <- KUSUR
        #   {'subagent_type':'infra-expert'}                              <- dogru
        #   {'subagent_type':'bug-expert'}                                <- dogru
        rc, ctx, _e, ok = kos(hook, sb, at_payload(
            {"subagent_type": "infra-expert", "name": "infra-kuyruk-2208"}))
        ekle("A1 KUSURLU spawn (muaf rol + FARKLI ad) -> NOT VAR + exit 0",
             AT in ctx and "infra-kuyruk-2208" in ctx and rc == 0 and ok,
             f"exit={rc} json={ok}; nudge basilmali (BLOKLAMAZ)")

        rc, ctx, _e, _ok = kos(hook, sb, at_payload({"subagent_type": "infra-expert"}))
        ekle("A2 ADSIZ spawn (dogru kullanim) -> SESSIZ",
             AT not in ctx and AT_KOSMADI not in ctx,
             "ad verilmediyse agent_type degismez -> uyari GURULTUDUR")

        rc, ctx, _e, _ok = kos(hook, sb, at_payload(
            {"subagent_type": "bug-expert", "name": "bug-turu-1"}))
        ekle("A3 MUAF OLMAYAN rol + ad -> SESSIZ",
             AT not in ctx and AT_KOSMADI not in ctx,
             "muafiyeti olmayan rolde kaybedilecek muafiyet de yok")

        # ⭐ A4 SINIR: ad == subagent_type ise `agent_type` DEGISMEZ -> uyari gurultudur.
        rc, ctx, _e, _ok = kos(hook, sb, at_payload(
            {"subagent_type": "infra-expert", "name": "infra-expert"}))
        ekle("A4 SINIR: ad == subagent_type -> SESSIZ",
             AT not in ctx and AT_KOSMADI not in ctx,
             "esit adda muafiyet DUSMEZ; uyarmak yanlis-pozitif olurdu")

        # ⭐ A5 RUNPY: canli cagri sekli (hook_shim.template.py:79) -- kardes-import
        # `sys.path[0]=''` altinda da cozulmeli. SILINEMEZ: bu capa olmadan dal
        # dogrudan cagride YESIL, canlida OLU olur.
        sim = tmp / "sim_runpy.py"
        sim.write_text("import runpy, sys\n"
                       "sys.path[0] = ''\n"
                       "runpy.run_path(sys.argv[1], run_name='__main__')\n",
                       encoding="utf-8")
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(sb)
        env["PYTHONIOENCODING"] = "utf-8"
        pr = subprocess.run(
            [sys.executable, str(sim), str(hook)],
            input=json.dumps(at_payload(
                {"subagent_type": "infra-expert", "name": "infra-kuyruk-2208"})).encode("utf-8"),
            env=env, capture_output=True, cwd=str(sb), timeout=120)
        r_out = pr.stdout.decode("utf-8", "replace")
        try:
            r_ctx = json.loads(r_out)["hookSpecificOutput"]["additionalContext"]
        except Exception:
            r_ctx = ""
        ekle("A5 RUNPY (canli hook_shim sekli): kardes-import COZULUR, not VAR",
             AT in r_ctx and AT_KOSMADI not in r_ctx and pr.returncode == 0,
             f"exit={pr.returncode}; sys.path[0]='' altinda import olmemeli")

        rc, ctx, _e, ok = kos(hook, sb, {"session_id": "pa", "tool_input": "bozuk-tip"})
        ekle("F3 payload SEKLI bozuksa da KOSMADI der (except dali)",
             KOSMADI in ctx and rc == 0 and ok,
             "sessiz None = 'prior-art yok' diye okunurdu; ayri capa")

        rc, ctx, err, ok = kos(hook, sb, {}, ham=b"{bozuk json")
        ekle("F2 parse-fail REGRESYONU: exit 0 + gorunur not",
             rc == 0 and "GIRDI-PARSE-EDILEMEDI" in err,
             "mevcut B0b sozlesmesi bozulmadi")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if yedek is not None:
            try:
                yedek.unlink()
            except Exception:
                pass

    gecen = sum(1 for _a, o, _d in sonuc if o)
    for ad, o, aciklama in sonuc:
        print(("  PASS  " if o else "  FAIL  ") + ad + (f"   ({aciklama})" if aciklama else ""))
    print(f"\nprior_art_kb01: {gecen}/{len(sonuc)}")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
