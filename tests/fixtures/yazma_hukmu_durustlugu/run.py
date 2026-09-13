#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yazma_hukmu_durustlugu fixture — MCP yazma araclarinin OZ-RAPORU ile SAP'nin gercek hukmu.

Iki kayit, AYNI sinif ("aracin basari/basarisizlik hukmu SAP'nin hukmunden ayrisiyor"),
TERS yonlerde:

  Q278 (sahte-OK)  `adt_publish_service` basariyi HTTP kodundan kuruyordu:
                   HTTP 200 + govdede `<SEVERITY>ERROR</SEVERITY>` "Service Binding ... does
                   not exist." -> `ok:true, published:true`. FIX: hukum GOVDEDEN kurulur;
                   ERROR -> ok:false · OK -> ok:true · hukumsuz/taninmayan -> ok:false +
                   published:None (OLCULEMEDI).
  Q273 (sahte-FAIL) basarili push'ta post_check'teki bir WARNING kapisi olcum uretemeyince
                   (`measured=false`) `resp.ok = False` oluyordu. FIX: `ok` yalniz BLOCKER
                   (ya da taninmayan verdict / blocker_count>0) ile duser; WARNING
                   `post_check.unmeasured|warnings` + `post_check_notice` ile GORUNUR kalir.

  Q292 (sahte-OK, KARDES) `scripts/create_rap_service.py::step_publish` ayni kusur:
                   `return r.status_code in (200, 201, 202)`. FIX: hukum TEK KAYNAGA tasindi
                   (`create_rap_service.publish_hukmu`; atom ince sarmalayici) ·
                   step_publish UC DEGERLI doner (True/False/None) · `main` None'da exit 1.
  Q293 (iki yon, KARDES) `composite.adt_struct_create` post-check'i `consistency.passed`
                   kullaniyordu: WARNING (timeout/measured=false) -> ok:false (sahte-FAIL) ·
                   SKIP (post-check HIC kosmadi) -> ok:true + post_check.ok:true (olculemedi =
                   temiz). FIX: Q273 sozlesmesi tek kaynakta (`_reviewer.post_check_ozeti`):
                   ok yalniz BLOCKER ile duser; olculemeyen kapi `unmeasured` + `hukum` +
                   `post_check_notice` ile GORUNUR.

⛔ KONTROL GRUBU (silinmez): P2 taninan basari govdesi HALA ok:true (fail-closed asiri
genellenmedi) · R3 BLOCKER HALA ok:false (⚠GEVSETME siniri) · R4 taninmayan verdict HALA
ok:false · R4b WARNING+blocker_count>0 HALA ok:false · R6 push'un kendisi basarisizsa ok:false ·
K2 step_publish SEVERITY=OK HALA True · K4 HTTP 500 HALA basarisiz · K6b main OK govdesi exit 0 ·
C4/C6 composite BLOCKER / taninmayan verdict HALA ok:false · C5 PASS notice YOK · C7 artifact yok ·
C8 aktivasyon basarisizsa post-check PASS olsa da ok:false.

⚠ GOVDE ZARFI: repoda HAM publish yaniti kayitli degil; yalniz parcalar var
(`<SEVERITY>ERROR</SEVERITY> <LONG_TEXT>Service Binding X does not exist.</LONG_TEXT>` —
tuketici projenin test-bulgulari plani, kalem A27; `<SEVERITY>OK</SEVERITY> … activated
locally` — playbook/adt-rap.md §32.6l). Bu yuzden her hukum HEM zarfli (asXML benzeri) HEM
ciplak/kirpilmis govdeyle olculur: ayristirici zarftan bagimsiz olmali. Gercek zarf sekli
DOGRULANAMADI.

KOSUM:
    python tests/fixtures/yazma_hukmu_durustlugu/run.py                         (exit 0)
MUTASYON (reddedilen tasarim enjekte edilir; `git show` YOK -> sig klonda da kosar):
    --mutasyon                  iki eski hukum birlikte             -> dusmeli
    --mutasyon-publish          YALNIZ Q278 eski hukmu (HTTP kodu)  -> P1/P1b/P3/P4/P6/P7a duser
    --mutasyon-postcheck        YALNIZ Q273 eski hukmu (passed)     -> R1/R1b/R2/R7a/R7b duser
    --mutasyon-crs              Q292: paylasilan publish hukmu HTTP koduna doner (TEK KAYNAK:
                                atom P* vektorleri de duser — iki tuketici tek sozlesme)
    --mutasyon-composite        Q293: composite eski `passed` hukmu      -> C1/C2/C3/C9/C10 duser
    --mutasyon-gorunurluk       olculemeyen kapi SESSIZ (unmeasured sokulur, hukum 'gecti')
                                atom + composite birlikte -> R1b/R5c/R7b/C1b/C2/C3 duser
ESKI KOD (fix oncesi atom.py; tek seferlik kanit, CI'da kosmaz):
    git show 6047fa2:mcp_servers/sap_adt/tools/atom.py > .tmp/atom_taban.py
    python tests/fixtures/yazma_hukmu_durustlugu/run.py --taban-dosya .tmp/atom_taban.py
ESKI KOD — KARDESLER (Q292/Q293; ayni dizinde `_` onekli kardes kopya, kosum sonrasi SIL):
    git show 4b05609:scripts/create_rap_service.py > scripts/_create_rap_service.py
    git show 4b05609:mcp_servers/sap_adt/tools/composite.py > mcp_servers/sap_adt/tools/_composite.py
    python tests/fixtures/yazma_hukmu_durustlugu/run.py --taban-kardes
    (K*/C* vektorleri kardes kopyalara karsi kosar; atom/_reviewer GUNCEL kalir)
Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "mcp_servers").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
for p in (REPO, REPO / "scripts", REPO / "scripts" / "utils"):
    sys.path.insert(0, str(p))
os.environ.setdefault("CLAUDE_PROJECT_DIR", str(REPO))

GECERLI_KIP = {"--mutasyon", "--mutasyon-publish", "--mutasyon-postcheck",
               "--mutasyon-crs", "--mutasyon-composite", "--mutasyon-gorunurluk"}
KIP = None
TABAN_DOSYA = None
TABAN_KARDES = False
_argv = sys.argv[1:]
_i = 0
while _i < len(_argv):
    _a = _argv[_i]
    if _a in GECERLI_KIP:
        KIP = _a
    elif _a == "--taban-dosya" and _i + 1 < len(_argv):
        TABAN_DOSYA = Path(_argv[_i + 1]).resolve()
        _i += 1
    elif _a == "--taban-kardes":
        TABAN_KARDES = True
    elif _a.startswith("--"):
        print(f"[KULLANIM] bilinmeyen kip: {_a} (gecerli: {sorted(GECERLI_KIP)} | "
              f"--taban-dosya <yol> | --taban-kardes)")
        raise SystemExit(2)
    _i += 1
if KIP and (TABAN_DOSYA or TABAN_KARDES):
    print("[KULLANIM] taban kipi ile mutasyon kipi birlikte verilmez")
    raise SystemExit(2)

# ── MCP SDK KOPRUSU (test-harness'i; desen: aktivasyon_baseline_tazeligi) ───────────────
try:  # pragma: no cover - ortam kosullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    _mcp, _srv, _fast = (types.ModuleType("mcp"), types.ModuleType("mcp.server"),
                         types.ModuleType("mcp.server.fastmcp"))

    class _FastMCP:
        def __init__(self, *a, **k):
            pass

        def tool(self, *a, **k):
            def _dek(fn):
                return fn
            return _dek

    _fast.FastMCP = _FastMCP                                 # type: ignore[attr-defined]
    _srv.fastmcp = _fast                                     # type: ignore[attr-defined]
    _mcp.server = _srv                                       # type: ignore[attr-defined]
    sys.modules.setdefault("mcp", _mcp)
    sys.modules.setdefault("mcp.server", _srv)
    sys.modules.setdefault("mcp.server.fastmcp", _fast)

import logging                                                # noqa: E402
logging.disable(logging.CRITICAL)

try:
    if TABAN_DOSYA:
        # ESKI KOD: tek surec, TEK agac (sys.modules cakismasi yok) — atom'un yerine
        # fix-oncesi kaynak ayni modul adiyla yuklenir; bagimliliklari gercek repodandir.
        if not TABAN_DOSYA.is_file():
            raise SystemExit(f"[fixture-hatasi] taban dosyasi yok: {TABAN_DOSYA}")
        import mcp_servers.sap_adt.tools as _tools_pkg  # noqa: F401
        _spec = importlib.util.spec_from_file_location("mcp_servers.sap_adt.tools.atom", TABAN_DOSYA)
        atom = importlib.util.module_from_spec(_spec)          # type: ignore[arg-type]
        sys.modules["mcp_servers.sap_adt.tools.atom"] = atom
        _spec.loader.exec_module(atom)                          # type: ignore[union-attr]
    else:
        from mcp_servers.sap_adt.tools import atom
    from mcp_servers.sap_adt._reviewer import ReviewerResult
    from mcp_servers.sap_adt import _reviewer as REV
    import create_rap_service as CRS
    if TABAN_KARDES:
        # ESKI KOD — KARDESLER: `_` onekli kopya AYRI modul adiyla yuklenir; gercek
        # `create_rap_service` / `composite` sys.modules'ta DEGISMEZ (atom onlara bagli).
        import mcp_servers.sap_adt.tools as _tools_pkg2  # noqa: F401

        def _kardes_yukle(modul_adi: str, yol: Path):
            if not yol.is_file():
                raise SystemExit(f"[fixture-hatasi] taban kardes kopyasi yok: {yol}")
            sp = importlib.util.spec_from_file_location(modul_adi, yol)
            m = importlib.util.module_from_spec(sp)             # type: ignore[arg-type]
            sys.modules[modul_adi] = m
            sp.loader.exec_module(m)                            # type: ignore[union-attr]
            return m

        CRS_MOD = _kardes_yukle("_create_rap_service", REPO / "scripts" / "_create_rap_service.py")
        COMP = _kardes_yukle("mcp_servers.sap_adt.tools._composite",
                             REPO / "mcp_servers" / "sap_adt" / "tools" / "_composite.py")
    else:
        CRS_MOD = CRS
        from mcp_servers.sap_adt.tools import composite as COMP
except SystemExit:
    raise
except Exception as exc:                                    # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] modul yuklenemedi (sessiz gecme YOK): {exc}")

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


# =============================================================================
# Q278 — SAHTE PUBLISH UCU
# =============================================================================
def _zarf(ic: str) -> str:
    """asXML benzeri zarf (sekli DOGRULANAMADI — ayristirici zarftan bagimsiz olmali)."""
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<asx:abap xmlns:asx="http://www.sap.com/abapxml" version="1.0"><asx:values>'
            f'<DATA>{ic}</DATA></asx:values></asx:abap>')


GOVDE_ERROR_IC = ("<SEVERITY>ERROR</SEVERITY><SHORT_TEXT/>"
                  "<LONG_TEXT>Service Binding ZSD001_UI_ORDER does not exist.</LONG_TEXT>")
GOVDE_OK_IC = ("<SEVERITY>OK</SEVERITY><SHORT_TEXT>Service ZSD001_UI_ORDER_O2 activated locally"
               "</SHORT_TEXT><LONG_TEXT/>")


class _Yanit:
    def __init__(self, status_code: int, text: str):
        self.status_code, self.text = status_code, text


class _SahteOturum:
    def __init__(self):
        self.yanit = _Yanit(200, "")
        self.post_sayisi = 0

    def post(self, url, params=None, headers=None, data=None, verify=False, timeout=None):
        self.post_sayisi += 1
        return self.yanit


class _SahtePublishAdt:
    def __init__(self):
        self.url = "https://sap-a.test"
        self.session = _SahteOturum()


ARAC = {"client": None}      # atom._get_client bunu dondurur


def _publish(status: int, govde: str, ad: str = "ZSD001_UI_ORDER_O2") -> dict:
    adt = _SahtePublishAdt()
    adt.session.yanit = _Yanit(status, govde)
    ARAC["client"] = adt
    return atom.adt_publish_service(name=ad)


def _ozet(r: dict) -> str:
    return (f"ok={r.get('ok')!r} published={r.get('published')!r} probe={r.get('publish_probe')!r} "
            f"sev={r.get('severity')!r} notice={str(r.get('publish_notice', '-'))[:70]!r} "
            f"err={r.get('error', '-')}")


def p1_error_govdesi():
    """KUSURUN KENDISI: HTTP 200 + SEVERITY=ERROR -> basarisiz (zarfli + ciplak)."""
    for etiket, govde in (("zarfli", _zarf(GOVDE_ERROR_IC)), ("ciplak", GOVDE_ERROR_IC)):
        r = _publish(200, govde)
        kontrol(f"P1 ⭐ HTTP 200 + SEVERITY=ERROR ({etiket}) -> ok:false + published:false",
                r.get("ok") is False and r.get("published") is False, _ozet(r))
    r = _publish(200, _zarf(GOVDE_ERROR_IC))
    kontrol("P1b hata mesaji yanitta gorunur (sap_message 'does not exist' + notice)",
            "does not exist" in str(r.get("sap_message")) and bool(r.get("publish_notice")),
            _ozet(r))


def p2_ok_govdesi_kontrol():
    """⛔ KONTROL: taninan basari govdesi HALA basari (fail-closed asiri genellenmedi)."""
    for etiket, govde in (("zarfli", _zarf(GOVDE_OK_IC)), ("ciplak", GOVDE_OK_IC)):
        r = _publish(200, govde)
        kontrol(f"P2 ⛔ KONTROL HTTP 200 + SEVERITY=OK ({etiket}) -> ok:true + published:true",
                r.get("ok") is True and r.get("published") is True
                and "publish_notice" not in r, _ozet(r))


def p3_hukumsuz_govde():
    """Belirsiz govde BASARI SAYILMAZ: SEVERITY yok -> ok:false + published:None + notice."""
    for etiket, govde in (("bos", ""), ("html", "<html><body>ok</body></html>"),
                          ("duz-metin", "Service published")):
        r = _publish(200, govde)
        kontrol(f"P3 ⭐ HTTP 200 + SEVERITY YOK ({etiket}) -> ok:false + published:None + OLCULEMEDI",
                r.get("ok") is False and r.get("published") is None
                and "ÖLÇÜLEMEDİ" in str(r.get("publish_notice", "")), _ozet(r))


def p4_taninmayan_severity():
    """Olculmemis deger (ornek WARNING) tahminle basari/hata sayilmaz -> None."""
    r = _publish(200, _zarf("<SEVERITY>WARNING</SEVERITY><LONG_TEXT>x</LONG_TEXT>"))
    kontrol("P4 taninmayan SEVERITY -> ok:false + published:None + probe severity_taninmadi",
            r.get("ok") is False and r.get("published") is None
            and r.get("publish_probe") == "severity_taninmadi", _ozet(r))


def p5_http_hata_kontrol():
    """⛔ KONTROL (eski davranis korunur): HTTP 500 -> basarisiz."""
    r = _publish(500, _zarf(GOVDE_OK_IC))
    kontrol("P5 ⛔ KONTROL HTTP 500 (govde OK dese bile) -> ok:false + published:false",
            r.get("ok") is False and r.get("published") is False, _ozet(r))


def p6_karisik_severity():
    """Coklu mesaj: biri ERROR ise basari DEGIL."""
    r = _publish(200, _zarf("<SEVERITY>OK</SEVERITY><SEVERITY>ERROR</SEVERITY>"
                            "<LONG_TEXT>kismi</LONG_TEXT>"))
    kontrol("P6 SEVERITY OK+ERROR karisik -> ok:false + published:false",
            r.get("ok") is False and r.get("published") is False, _ozet(r))


def p7_ucuncu_baglam_kirpilmis_ve_onekli():
    """UCUNCU BAGLAM (farkli okuma yolu): XML AYRISTIRILAMAZ (kirpilmis govde) + ad alani onekli
    etiket + kucuk harf deger. Regex yolu da ayni hukmu vermeli."""
    kirpik = _zarf(GOVDE_ERROR_IC)[:-30]                     # kapanis etiketleri kesildi
    r = _publish(200, kirpik)
    kontrol("P7a kirpilmis (ayristirilamaz) govde + ERROR -> ok:false (regex yolu)",
            r.get("ok") is False and r.get("published") is False, _ozet(r))
    r2 = _publish(200, '<x:D xmlns:x="urn:t"><x:SEVERITY> ok </x:SEVERITY></x:D>')
    kontrol("P7b ad-alani onekli etiket + kucuk harf/bosluklu 'ok' -> ok:true",
            r2.get("ok") is True and r2.get("published") is True, _ozet(r2))


def p8_guardrail_capa():
    """⛔ FP CAPASI: guardrail'ler POST'tan ONCE durur (fix bu sirayi degistirmedi)."""
    adt = _SahtePublishAdt()
    ARAC["client"] = adt
    r = atom.adt_publish_service(name="API_SALES_ORDER_SRV")
    kontrol("P8 ⛔ CAPA standart ad -> guardrail reddi + POST sayisi 0",
            r.get("ok") is False and adt.session.post_sayisi == 0,
            f"ok={r.get('ok')} post={adt.session.post_sayisi} err={r.get('error')}")


# =============================================================================
# Q273 — POST_CHECK
# =============================================================================
class _SahtePushClient:
    """push_object sonucu dogrudan verilir: olculen sey atom'un post_check HUKMUDUR."""

    def __init__(self, sonuc: dict):
        self.sonuc = sonuc

    def push_object(self, object_name, object_type="class", transport=None, source_file=None):
        return dict(self.sonuc)


BASARILI_PUSH = {"success": True, "source_uploaded": True, "activated": True, "readback_ok": True}
POST = {"sonuc": None, "cagri": []}


def _sahte_reviewer(task, artifact_path, ack_drop=""):
    POST["cagri"].append(task)
    if task in ("struct_post_create", "sap_active_check"):
        return POST["sonuc"]
    return ReviewerResult(verdict="PASS")                   # pre-flight temiz


def _olcemeyen_warning() -> ReviewerResult:
    """Q273'un canli vakasinin ikizi: BLOCKER kapi PASS, WARNING kapi measured=false (SKIP)."""
    return ReviewerResult(
        verdict="WARNING", blocker_count=0, warning_count=1,
        results=[
            {"validator": "check_sap_active_version.py", "severity": "BLOCKER", "status": "PASS",
             "message": ""},
            {"validator": "check_sap_master_language.py", "severity": "WARNING", "status": "SKIP",
             "message": "PRE-FLIGHT ÖLÇMEDİ: ... measured=false reason=metadata-okunamadi"},
        ])


def _push(tip: str, post: ReviewerResult, push_sonuc: dict | None = None) -> dict:
    POST["sonuc"], POST["cagri"] = post, []
    ARAC["client"] = _SahtePushClient(push_sonuc or BASARILI_PUSH)
    return atom.adt_push_source(name="ZSD001_I_DEMO", object_type=tip,
                                source="define view entity ZSD001_I_DEMO as select from t { key a }",
                                transport="TRK900001")


def _pozet(r: dict) -> str:
    return (f"ok={r.get('ok')!r} post_check={r.get('post_check')!r} "
            f"notice={str(r.get('post_check_notice', '-'))[:60]!r} err={r.get('error', '-')}")


def r1_olcemeyen_warning_ddls():
    """KUSURUN KENDISI (ddls -> sap_active_check dali)."""
    r = _push("ddls", _olcemeyen_warning())
    pc = r.get("post_check") or {}
    kontrol("R1 ⭐ basarili push + post_check WARNING(measured=false) -> ok:TRUE",
            r.get("ok") is True and "sap_active_check" in POST["cagri"], _pozet(r))
    kontrol("R1b WARNING SESSIZ DEGIL: verdict + unmeasured(gate adi) + ust-duzey notice",
            pc.get("verdict") == "WARNING"
            and any("master_language" in str(k.get("gate")) for k in pc.get("unmeasured") or [])
            and "ÖLÇÜLEMEDİ" in str(r.get("post_check_notice", "")), _pozet(r))


def r2_struct_dali():
    """IKINCI KOD DALI (structure -> struct_post_create; eski kodda ayri blok)."""
    r = _push("structure", _olcemeyen_warning())
    kontrol("R2 ⭐ struct dali: basarili push + WARNING -> ok:TRUE + notice",
            r.get("ok") is True and "struct_post_create" in POST["cagri"]
            and bool(r.get("post_check_notice")), _pozet(r))


def r3_blocker_kontrol():
    """⛔ KONTROL / ⚠GEVSETME SINIRI: BLOCKER HALA ok:false."""
    for tip, task in (("ddls", "sap_active_check"), ("structure", "struct_post_create")):
        post = ReviewerResult(verdict="BLOCKER", blocker_count=1, results=[
            {"validator": "check_sap_active_version.py", "severity": "BLOCKER", "status": "FAIL",
             "message": ""}])
        r = _push(tip, post)
        kontrol(f"R3 ⛔ KONTROL post_check BLOCKER ({tip}) -> ok:FALSE",
                r.get("ok") is False and task in POST["cagri"], _pozet(r))


def r4_taninmayan_verdict_kontrol():
    """⛔ KONTROL: gevsetme WARNING ile SINIRLI — taninmayan verdict ve blocker_count>0 dusurur."""
    r = _push("ddls", ReviewerResult(verdict="ERROR"))
    kontrol("R4 ⛔ KONTROL taninmayan verdict -> ok:FALSE (fail-closed)",
            r.get("ok") is False, _pozet(r))
    r2 = _push("ddls", ReviewerResult(verdict="WARNING", blocker_count=1, warning_count=1))
    kontrol("R4b ⛔ KONTROL verdict WARNING ama blocker_count>0 -> ok:FALSE",
            r2.get("ok") is False, _pozet(r2))


def r5_pass_skip_kontrol():
    """⛔ KONTROL: PASS/SKIP -> ok:true, notice YOK (alarm yorgunlugu capasi)."""
    r = _push("ddls", ReviewerResult(verdict="PASS"))
    kontrol("R5 ⛔ KONTROL PASS -> ok:true + notice YOK + post_check.ok true",
            r.get("ok") is True and "post_check_notice" not in r
            and (r.get("post_check") or {}).get("ok") is True, _pozet(r))
    r2 = _push("tabl", ReviewerResult(verdict="SKIP", skipped=True, skip_reason="artifact_not_found:x"))
    kontrol("R5b ⛔ KONTROL SKIP -> ok:true + skip_reason gorunur",
            r2.get("ok") is True
            and (r2.get("post_check") or {}).get("skip_reason") == "artifact_not_found:x", _pozet(r2))


def r6_push_basarisiz_kontrol():
    """⛔ KONTROL: push'un KENDISI basarisizsa post_check kosmaz, ok:false (degismedi)."""
    r = _push("ddls", ReviewerResult(verdict="PASS"),
              {"success": False, "source_uploaded": True, "activated": False})
    kontrol("R6 ⛔ KONTROL push basarisiz -> ok:false + post_check KOSMADI",
            r.get("ok") is False and "sap_active_check" not in POST["cagri"]
            and "post_check" not in r, _pozet(r))


def r7_olculmus_uyari_ve_timeout():
    """UCUNCU BAGLAM: WARNING'in IKI farkli kaynagi — olculmus bulgu (FAIL/WARNING, dtel dali)
    ve reviewer timeout'u (sonuc YOK, skip_reason var; doma dali). Ok dusmez, iz kaybolmaz."""
    post = ReviewerResult(verdict="WARNING", warning_count=1, results=[
        {"validator": "check_x_uyari.py", "severity": "WARNING", "status": "FAIL", "message": ""}])
    r = _push("dtel", post)
    pc = r.get("post_check") or {}
    kontrol("R7a olculmus WARNING bulgusu -> ok:true + post_check.warnings gate adi",
            r.get("ok") is True
            and any(k.get("gate") == "check_x_uyari.py" for k in pc.get("warnings") or []), _pozet(r))
    zaman = ReviewerResult(verdict="WARNING", warning_count=1,
                           skip_reason="reviewer_timeout — MCP içi reviewer 30s aştı")
    r2 = _push("doma", zaman)
    pc2 = r2.get("post_check") or {}
    kontrol("R7b reviewer timeout (sonucsuz WARNING) -> ok:true + unmeasured 'reviewer'",
            r2.get("ok") is True
            and any(k.get("gate") == "reviewer" for k in pc2.get("unmeasured") or []), _pozet(r2))


def r5c_atom_skip_gorunurluk():
    """Q293 ortak yardimcinin atom'a yansimasi: SKIP (post-check KOSMADI) ok'u DUSURMEZ ama
    'temiz' de GORUNMEZ -> unmeasured + hukum olculemedi + notice."""
    r = _push("tabl", ReviewerResult(verdict="SKIP", skipped=True,
                                     skip_reason="reviewer_exception:boom"))
    pc = r.get("post_check") or {}
    kontrol("R5c atom SKIP(skip_reason) -> ok:true + hukum olculemedi + unmeasured + notice",
            r.get("ok") is True and pc.get("hukum") == "olculemedi"
            and any("reviewer_exception" in str(k.get("reason")) for k in pc.get("unmeasured") or [])
            and "ÖLÇÜLEMEDİ" in str(r.get("post_check_notice", "")), _pozet(r))


def r8_tek_kaynak_capasi():
    """KOPYA SOZLESME CAPASI: atom post-check hukmunu `_reviewer`'dan ALIR, kendi kopyasini tutmaz."""
    kontrol("R8 atom._post_check_ozeti IS _reviewer.post_check_ozeti + atom'da yerel sabit YOK",
            getattr(atom, "_post_check_ozeti", None) is REV.post_check_ozeti
            and not hasattr(atom, "_POST_CHECK_OK_DUSURMEYEN"),
            f"atom={getattr(atom, '_post_check_ozeti', None)!r}")


# =============================================================================
# Q292 — create_rap_service.step_publish + main (CLI giris noktasi)
# =============================================================================
class _SahteAdtIstemci:
    def __init__(self, yanit: _Yanit):
        self.url = "https://sap-a.test"
        self.session = _SahteOturum()
        self.session.yanit = yanit


def _step_publish(status: int, govde: str):
    ist = _SahteAdtIstemci(_Yanit(status, govde))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        donus = CRS_MOD.step_publish(ist, "TOK")
    return donus, buf.getvalue(), ist


def _kozet(donus, cikti: str, ist) -> str:
    return f"donus={donus!r} post={ist.session.post_sayisi} cikti={cikti[-160:]!r}"


def k1_error_govdesi():
    """KUSURUN KENDISI: HTTP 200 + SEVERITY=ERROR -> False (eski kod True)."""
    for etiket, govde in (("zarfli", _zarf(GOVDE_ERROR_IC)), ("ciplak", GOVDE_ERROR_IC)):
        d, c, ist = _step_publish(200, govde)
        kontrol(f"K1 ⭐ step_publish HTTP 200 + SEVERITY=ERROR ({etiket}) -> False + mesaj",
                d is False and "does not exist" in c, _kozet(d, c, ist))


def k2_ok_govdesi_kontrol():
    """⛔ KONTROL: SEVERITY=OK hala basari."""
    for etiket, govde in (("zarfli", _zarf(GOVDE_OK_IC)), ("ciplak", GOVDE_OK_IC)):
        d, c, ist = _step_publish(200, govde)
        kontrol(f"K2 ⛔ KONTROL step_publish HTTP 200 + SEVERITY=OK ({etiket}) -> True",
                d is True and ist.session.post_sayisi == 1, _kozet(d, c, ist))


def k3_hukumsuz_govde():
    """Belirsiz govde basari SAYILMAZ: None (OLCULEMEDI) — False'tan AYRI (eski kod True)."""
    for etiket, govde in (("bos", ""), ("html", "<html><body>ok</body></html>")):
        d, c, ist = _step_publish(200, govde)
        kontrol(f"K3 ⭐ step_publish SEVERITY YOK ({etiket}) -> None + 'ÖLÇÜLEMEDİ' ciktida",
                d is None and "ÖLÇÜLEMEDİ" in c, _kozet(d, c, ist))


def k4_http_hata_kontrol():
    """⛔ KONTROL (eski davranis korunur): HTTP 500 -> basarisiz."""
    d, c, ist = _step_publish(500, _zarf(GOVDE_OK_IC))
    kontrol("K4 ⛔ KONTROL step_publish HTTP 500 -> basarisiz (falsy)", not d, _kozet(d, c, ist))


def k5_tek_kaynak_capasi():
    """KOPYA SOZLESME CAPASI: MCP tool'u hukmu create_rap_service'ten ALIR (tek kaynak)."""
    asil = CRS.publish_hukmu if hasattr(CRS, "publish_hukmu") else None
    isaret = {"isaret": "tek-kaynak"}
    try:
        CRS.publish_hukmu = lambda s, b: isaret                # type: ignore[attr-defined]
        d = atom._publish_hukmu(200, "")
    finally:
        if asil is not None:
            CRS.publish_hukmu = asil                            # type: ignore[attr-defined]
    kontrol("K5 atom._publish_hukmu -> create_rap_service.publish_hukmu + atom'da yerel kopya YOK",
            d is isaret and not any(hasattr(atom, a) for a in
                                    ("_PUBLISH_SEVERITY_BASARI", "_SEVERITY_RE", "_publish_govdesi_oku")),
            f"donus={d!r}")


def _crs_main(status: int, govde: str):
    """UCUNCU BAGLAM: gercek CLI giris noktasi `main()` — argparse + adim zinciri + exit kodu."""
    ist = _SahteAdtIstemci(_Yanit(status, govde))
    eski = (sys.argv, CRS_MOD.SAPADTClient, CRS_MOD.csrf)
    sys.argv = ["create_rap_service.py", "--step", "publish", "--srvb-name", "ZSD001_UI_ORDER_O2"]
    CRS_MOD.SAPADTClient = lambda: ist                          # type: ignore[assignment]
    CRS_MOD.csrf = lambda c: "TOK"                              # type: ignore[assignment]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = CRS_MOD.main()
    finally:
        sys.argv, CRS_MOD.SAPADTClient, CRS_MOD.csrf = eski
    return rc, buf.getvalue(), ist


def k6_cli_main_ucuncu_baglam():
    rc, c, ist = _crs_main(200, _zarf(GOVDE_ERROR_IC))
    kontrol("K6a ⭐ main --step publish + SEVERITY=ERROR -> exit 1 (eski 0)",
            rc == 1 and ist.session.post_sayisi == 1, f"rc={rc} {_kozet(None, c, ist)}")
    rc, c, ist = _crs_main(200, _zarf(GOVDE_OK_IC))
    kontrol("K6b ⛔ KONTROL main --step publish + SEVERITY=OK -> exit 0",
            rc == 0, f"rc={rc} {_kozet(None, c, ist)}")
    rc, c, ist = _crs_main(200, "")
    kontrol("K6c ⭐ main --step publish + govde hukumsuz -> exit 1 (belirsiz basari sayilmaz)",
            rc == 1, f"rc={rc} {_kozet(None, c, ist)}")


# =============================================================================
# Q293 — composite.adt_struct_create (MCP tool fonksiyonunun kendisi, SAP'siz oturum)
# =============================================================================
STRUCT_KAYNAK = ("define structure zsd001_s_demo {\n"
                 "  field1 : abap.char(10);\n  field2 : abap.numc(8);\n}\n")


class _SahteStructIstemci:
    """create_structure + activate_object + get_object_metadata + /source/main GET.
    Composite'in GERCEK govdesi kosar (_exists / _activate_and_verify / _verify_ddic_content)."""

    def __init__(self, aktive: bool = True):
        self.url = "https://sap-a.test"
        self.olusturuldu = False
        self.aktive = aktive
        self.session = self

    def get_object_metadata(self, name, object_type=None):
        if not self.olusturuldu:
            return None
        return '<adtcore:x adtcore:version="active" masterLanguage="TR"/>'

    def create_structure(self, **kw):
        self.olusturuldu = True
        return True

    def activate_object(self, name, object_type=None):
        return self.aktive

    def _get_headers(self, accept=None):
        return {}

    def get(self, url, headers=None, params=None, timeout=None, **kw):
        return _Yanit(200, STRUCT_KAYNAK)


def _struct(post: ReviewerResult | None, artifact: str | None = "x/ZSD001_S_DEMO.asddls",
            aktive: bool = True) -> dict:
    POST["sonuc"], POST["cagri"] = post, []
    ARAC["client"] = _SahteStructIstemci(aktive=aktive)
    return COMP.adt_struct_create(
        name="ZSD001_S_DEMO", fields=[{"name": "FIELD1", "type": "char10"}],
        description="Demo yapı", package="ZSD001_CLC", transport="TRK900001",
        artifact_path=artifact)


def _sozet(r: dict) -> str:
    st = r.get("steps") or {}
    return (f"ok={r.get('ok')!r} post_check={st.get('post_check')!r} "
            f"notice={str(r.get('post_check_notice', '-'))[:60]!r} err={r.get('error', '-')} "
            f"cagri={POST['cagri']}")


def _pc(r: dict) -> dict:
    return (r.get("steps") or {}).get("post_check") or {}


def c1_olcemeyen_warning():
    """KUSURUN KENDISI (sahte-FAIL yonu): basarili yaratma + WARNING(measured=false)."""
    r = _struct(_olcemeyen_warning())
    kontrol("C1 ⭐ struct_create basarili + post_check WARNING(measured=false) -> ok:TRUE",
            r.get("ok") is True and "struct_post_create" in POST["cagri"], _sozet(r))
    pc = _pc(r)
    kontrol("C1b WARNING SESSIZ DEGIL: hukum olculemedi + unmeasured(gate) + ust-duzey notice",
            pc.get("hukum") == "olculemedi"
            and any("master_language" in str(k.get("gate")) for k in pc.get("unmeasured") or [])
            and "ÖLÇÜLEMEDİ" in str(r.get("post_check_notice", "")), _sozet(r))


def c2_reviewer_timeout():
    """reviewer_timeout: sonucsuz WARNING (skip_reason var, results bos)."""
    zaman = ReviewerResult(verdict="WARNING", warning_count=1,
                           skip_reason="reviewer_timeout — MCP içi reviewer 30s aştı")
    r = _struct(zaman)
    kontrol("C2 ⭐ reviewer timeout -> ok:true + unmeasured 'reviewer' + notice",
            r.get("ok") is True
            and any(k.get("gate") == "reviewer" for k in _pc(r).get("unmeasured") or [])
            and bool(r.get("post_check_notice")), _sozet(r))


def c3_skip_olculemedi_gecti_degil():
    """⭐ OLCULEMEDI != GECTI (gorunurluk yonu): SKIP bugun sessizce ok:true + post_check.ok:true.
    ok DEGISMEZ (Q273 sozlesmesi) — degisen, olculemedigin GORUNUR olmasi."""
    r = _struct(ReviewerResult(verdict="SKIP", skipped=True,
                               skip_reason="artifact_not_found:x/ZSD001_S_DEMO.asddls"))
    pc = _pc(r)
    kontrol("C3 ⭐ SKIP(artifact_not_found) -> ok:true + hukum olculemedi + unmeasured sebep + notice",
            r.get("ok") is True and pc.get("hukum") == "olculemedi"
            and any("artifact_not_found" in str(k.get("reason")) for k in pc.get("unmeasured") or [])
            and "ÖLÇÜLEMEDİ" in str(r.get("post_check_notice", "")), _sozet(r))
    r2 = _struct(ReviewerResult(verdict="SKIP"))              # JSON ayristirilamadi yolu: sebepsiz SKIP
    kontrol("C3b sebepsiz SKIP -> hukum olculemedi + unmeasured 'reviewer sonuç üretmedi'",
            r2.get("ok") is True and _pc(r2).get("hukum") == "olculemedi"
            and any("üretmedi" in str(k.get("reason")) for k in _pc(r2).get("unmeasured") or []),
            _sozet(r2))


def c4_blocker_kontrol():
    """⛔ KONTROL / ⚠GEVSETME SINIRI: BLOCKER HALA ok:false."""
    post = ReviewerResult(verdict="BLOCKER", blocker_count=1, results=[
        {"validator": "check_sap_struct_consistency.py", "severity": "BLOCKER", "status": "FAIL",
         "message": "placeholder"}])
    r = _struct(post)
    kontrol("C4 ⛔ KONTROL post_check BLOCKER -> ok:FALSE",
            r.get("ok") is False and "struct_post_create" in POST["cagri"], _sozet(r))


def c5_pass_kontrol():
    """⛔ KONTROL: PASS -> ok:true, notice YOK (alarm yorgunlugu capasi)."""
    r = _struct(ReviewerResult(verdict="PASS"))
    kontrol("C5 ⛔ KONTROL PASS -> ok:true + notice YOK + post_check.ok true",
            r.get("ok") is True and "post_check_notice" not in r and _pc(r).get("ok") is True,
            _sozet(r))


def c6_taninmayan_verdict_kontrol():
    """⛔ KONTROL: gevsetme WARNING ile SINIRLI."""
    r = _struct(ReviewerResult(verdict="ERROR"))
    kontrol("C6 ⛔ KONTROL taninmayan verdict -> ok:FALSE", r.get("ok") is False, _sozet(r))
    r2 = _struct(ReviewerResult(verdict="WARNING", blocker_count=1, warning_count=1))
    kontrol("C6b ⛔ KONTROL WARNING ama blocker_count>0 -> ok:FALSE", r2.get("ok") is False, _sozet(r2))


def c7_artifact_yok_kontrol():
    """⛔ KONTROL: artifact_path verilmediyse post-check KOSMAZ (davranis degismedi)."""
    r = _struct(ReviewerResult(verdict="BLOCKER", blocker_count=1), artifact=None)
    kontrol("C7 ⛔ KONTROL artifact_path yok -> post_check YOK + ok:true",
            r.get("ok") is True and "post_check" not in (r.get("steps") or {})
            and "struct_post_create" not in POST["cagri"], _sozet(r))


def c8_aktivasyon_basarisiz():
    """⛔ KONTROL: VE-zinciri korunur. + notice basarisiz yanitta 'BASARILI' demez."""
    r = _struct(ReviewerResult(verdict="PASS"), aktive=False)
    kontrol("C8 ⛔ KONTROL aktivasyon basarisiz + post PASS -> ok:FALSE", r.get("ok") is False, _sozet(r))
    r2 = _struct(ReviewerResult(verdict="SKIP", skipped=True, skip_reason="reviewer_exception:x"),
                 aktive=False)
    kontrol("C8b aktivasyon basarisiz + SKIP -> ok:false + ust notice YOK + unmeasured steps'te",
            r2.get("ok") is False and "post_check_notice" not in r2
            and bool(_pc(r2).get("unmeasured")), _sozet(r2))


def c9_olculmus_uyari():
    """Olculmus WARNING bulgusu (FAIL/WARNING) -> ok:true + warnings + hukum uyari (eski ok:false)."""
    post = ReviewerResult(verdict="WARNING", warning_count=1, results=[
        {"validator": "check_x_uyari.py", "severity": "WARNING", "status": "FAIL", "message": ""}])
    r = _struct(post)
    kontrol("C9 olculmus WARNING -> ok:true + warnings gate + hukum uyari",
            r.get("ok") is True and _pc(r).get("hukum") == "uyari"
            and any(k.get("gate") == "check_x_uyari.py" for k in _pc(r).get("warnings") or []),
            _sozet(r))


def c10_tek_kaynak_capasi():
    kontrol("C10 composite._post_check_ozeti IS _reviewer.post_check_ozeti (atom ile tek sozlesme)",
            getattr(COMP, "_post_check_ozeti", None) is REV.post_check_ozeti,
            f"composite={getattr(COMP, '_post_check_ozeti', None)!r}")


# =============================================================================
# MUTASYON — REDDEDILEN TASARIM
# =============================================================================
def _eski_publish_hukmu(status_code, body):
    """REDDEDILEN (Q278 oncesi): hukum yalniz HTTP kodundan."""
    p = status_code in (200, 201, 202)
    return {"ok": p, "published": p, "severity": [], "sap_message": None,
            "publish_probe": "http"}


def _eski_post_check_ozeti(post):
    """REDDEDILEN (Q273 oncesi): `passed` degilse ok duser (WARNING dahil).

    ⚠ Eski kodun alanlarini BIREBIR tasir (skip_reason dahil): eksik alanli bir mutant
    KONTROL satirini (R5b) da dusurur ve mutasyon skorunu harness artefaktiyla sisirir
    (olculdu 2026-09-13: ilk mutant skip_reason'i atliyordu, R5b yalniz mutasyonda dustu;
    fix-oncesi gercek kodla (`--taban-dosya`) R5b GECIYORDU)."""
    ozet = {"ok": post.passed, "verdict": post.verdict,
            "blocker_count": post.blocker_count, "warning_count": post.warning_count}
    if post.skip_reason:
        ozet["skip_reason"] = post.skip_reason
    return (ozet, not post.passed)


def _eski_composite_ozeti(post):
    """REDDEDILEN (Q293 oncesi composite): `consistency.passed` — alanlar BIREBIR eski kod
    (`composite.py@4b05609:546-554`: ok/verdict/blocker_count/warning_count[/skip_reason])."""
    ozet = {"ok": post.passed, "verdict": post.verdict,
            "blocker_count": post.blocker_count, "warning_count": post.warning_count}
    if post.skip_reason:
        ozet["skip_reason"] = post.skip_reason
    return (ozet, not post.passed)


def _sessiz_ozet(post):
    """REDDEDILEN: dogru `ok` hukmu AMA olculemeyen kapi SESSIZ (unmeasured sokulur, 'gecti')."""
    ozet, dusur = REV.post_check_ozeti(post)
    ozet.pop("unmeasured", None)
    if ozet.get("hukum") == "olculemedi":
        ozet["hukum"] = "gecti"
    return ozet, dusur


def _mutasyonu_uygula(kip: str) -> bool:
    kuruldu = True
    if kip in ("--mutasyon", "--mutasyon-publish"):
        kuruldu = kuruldu and hasattr(atom, "_publish_hukmu")
        atom._publish_hukmu = _eski_publish_hukmu            # type: ignore[attr-defined]
    if kip in ("--mutasyon", "--mutasyon-postcheck"):
        kuruldu = kuruldu and hasattr(atom, "_post_check_ozeti")
        atom._post_check_ozeti = _eski_post_check_ozeti      # type: ignore[attr-defined]
    if kip == "--mutasyon-crs":
        kuruldu = kuruldu and hasattr(CRS_MOD, "publish_hukmu")
        CRS_MOD.publish_hukmu = _eski_publish_hukmu          # type: ignore[attr-defined]
    if kip == "--mutasyon-composite":
        kuruldu = kuruldu and hasattr(COMP, "_post_check_ozeti")
        COMP._post_check_ozeti = _eski_composite_ozeti       # type: ignore[attr-defined]
    if kip == "--mutasyon-gorunurluk":
        kuruldu = kuruldu and hasattr(COMP, "_post_check_ozeti") and hasattr(atom, "_post_check_ozeti")
        COMP._post_check_ozeti = _sessiz_ozet                # type: ignore[attr-defined]
        atom._post_check_ozeti = _sessiz_ozet                # type: ignore[attr-defined]
    return kuruldu


def main() -> int:
    if KIP:
        if not _mutasyonu_uygula(KIP):
            print(f"[KURULAMADI] {KIP}: mutasyon noktasi hedef modulde yok")
            return 3
        print(f"[MUTASYON] {KIP} — reddedilen tasarim enjekte edildi (gercek kaynak DEGISMEDI)")
    if TABAN_DOSYA:
        print(f"[TABAN] fix-oncesi atom yuklendi: {TABAN_DOSYA.name}")
    if TABAN_KARDES:
        print("[TABAN] fix-oncesi kardesler yuklendi: _create_rap_service.py + _composite.py")

    atom.get_active_tier = lambda: "DEV"                     # type: ignore[assignment]
    atom._get_client = lambda: ARAC["client"]                # type: ignore[assignment]
    atom.run_reviewer = _sahte_reviewer                      # type: ignore[assignment]
    CRS.csrf = lambda a: "TOK"                               # type: ignore[assignment]
    COMP.get_active_tier = lambda: "DEV"                     # type: ignore[assignment]
    COMP._get_client = lambda: ARAC["client"]                # type: ignore[assignment]
    COMP.run_reviewer = _sahte_reviewer                      # type: ignore[assignment]

    # ⚠ COKME != FAIL: patlayan bolum ADIYLA FAIL yazilir.
    for bolum in (p1_error_govdesi, p2_ok_govdesi_kontrol, p3_hukumsuz_govde,
                  p4_taninmayan_severity, p5_http_hata_kontrol, p6_karisik_severity,
                  p7_ucuncu_baglam_kirpilmis_ve_onekli, p8_guardrail_capa,
                  r1_olcemeyen_warning_ddls, r2_struct_dali, r3_blocker_kontrol,
                  r4_taninmayan_verdict_kontrol, r5_pass_skip_kontrol,
                  r6_push_basarisiz_kontrol, r7_olculmus_uyari_ve_timeout,
                  r5c_atom_skip_gorunurluk, r8_tek_kaynak_capasi,
                  k1_error_govdesi, k2_ok_govdesi_kontrol, k3_hukumsuz_govde,
                  k4_http_hata_kontrol, k5_tek_kaynak_capasi, k6_cli_main_ucuncu_baglam,
                  c1_olcemeyen_warning, c2_reviewer_timeout, c3_skip_olculemedi_gecti_degil,
                  c4_blocker_kontrol, c5_pass_kontrol, c6_taninmayan_verdict_kontrol,
                  c7_artifact_yok_kontrol, c8_aktivasyon_basarisiz, c9_olculmus_uyari,
                  c10_tek_kaynak_capasi):
        try:
            bolum()
        except BaseException as exc:                         # noqa: BLE001
            kontrol(f"[BOLUM COKTU] {bolum.__name__}", False,
                    f"{type(exc).__name__}: {str(exc)[:160]}")

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    for ad, ok, detay in SONUC:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad}")
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print(f"         -> {detay}")
    print(f"\n{gecen}/{len(SONUC)} OK")
    if KIP:
        # ⛔ BU SATIRA sayi/sayi YAZMA: run_battery skoru SON eslesmeden okur.
        print("[MUTASYON] beklenti: skor taban kosumundan DUSUK olmali")
        return 0 if gecen < len(SONUC) else 1
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
