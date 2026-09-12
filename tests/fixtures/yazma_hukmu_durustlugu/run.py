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

⛔ KONTROL GRUBU (silinmez): P2 taninan basari govdesi HALA ok:true (fail-closed asiri
genellenmedi) · R3 BLOCKER HALA ok:false (⚠GEVSETME siniri) · R4 taninmayan verdict HALA
ok:false · R4b WARNING+blocker_count>0 HALA ok:false · R6 push'un kendisi basarisizsa ok:false.

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
ESKI KOD (fix oncesi atom.py; tek seferlik kanit, CI'da kosmaz):
    git show 6047fa2:mcp_servers/sap_adt/tools/atom.py > .tmp/atom_taban.py
    python tests/fixtures/yazma_hukmu_durustlugu/run.py --taban-dosya .tmp/atom_taban.py
Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import importlib.util
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

GECERLI_KIP = {"--mutasyon", "--mutasyon-publish", "--mutasyon-postcheck"}
KIP = None
TABAN_DOSYA = None
_argv = sys.argv[1:]
_i = 0
while _i < len(_argv):
    _a = _argv[_i]
    if _a in GECERLI_KIP:
        KIP = _a
    elif _a == "--taban-dosya" and _i + 1 < len(_argv):
        TABAN_DOSYA = Path(_argv[_i + 1]).resolve()
        _i += 1
    elif _a.startswith("--"):
        print(f"[KULLANIM] bilinmeyen kip: {_a} (gecerli: {sorted(GECERLI_KIP)} | --taban-dosya <yol>)")
        raise SystemExit(2)
    _i += 1
if KIP and TABAN_DOSYA:
    print("[KULLANIM] --taban-dosya ile mutasyon kipi birlikte verilmez")
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
    import create_rap_service as CRS
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


def _mutasyonu_uygula(kip: str) -> bool:
    kuruldu = True
    if kip in ("--mutasyon", "--mutasyon-publish"):
        kuruldu = kuruldu and hasattr(atom, "_publish_hukmu")
        atom._publish_hukmu = _eski_publish_hukmu            # type: ignore[attr-defined]
    if kip in ("--mutasyon", "--mutasyon-postcheck"):
        kuruldu = kuruldu and hasattr(atom, "_post_check_ozeti")
        atom._post_check_ozeti = _eski_post_check_ozeti      # type: ignore[attr-defined]
    return kuruldu


def main() -> int:
    if KIP:
        if not _mutasyonu_uygula(KIP):
            print(f"[KURULAMADI] {KIP}: mutasyon noktasi atom'da yok")
            return 3
        print(f"[MUTASYON] {KIP} — reddedilen tasarim enjekte edildi (gercek kaynak DEGISMEDI)")
    if TABAN_DOSYA:
        print(f"[TABAN] fix-oncesi atom yuklendi: {TABAN_DOSYA.name}")

    atom.get_active_tier = lambda: "DEV"                     # type: ignore[assignment]
    atom._get_client = lambda: ARAC["client"]                # type: ignore[assignment]
    atom.run_reviewer = _sahte_reviewer                      # type: ignore[assignment]
    CRS.csrf = lambda a: "TOK"                               # type: ignore[assignment]

    # ⚠ COKME != FAIL: patlayan bolum ADIYLA FAIL yazilir.
    for bolum in (p1_error_govdesi, p2_ok_govdesi_kontrol, p3_hukumsuz_govde,
                  p4_taninmayan_severity, p5_http_hata_kontrol, p6_karisik_severity,
                  p7_ucuncu_baglam_kirpilmis_ve_onekli, p8_guardrail_capa,
                  r1_olcemeyen_warning_ddls, r2_struct_dali, r3_blocker_kontrol,
                  r4_taninmayan_verdict_kontrol, r5_pass_skip_kontrol,
                  r6_push_basarisiz_kontrol, r7_olculmus_uyari_ve_timeout):
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
