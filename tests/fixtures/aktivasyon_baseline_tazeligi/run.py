#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""aktivasyon_baseline_tazeligi fixture — Q271: BAYAT BASELINE -> SAHTE `content_mismatch`.

NEDEN VAR (olculmus kok, 2026-09-09):
`mcp_servers/sap_adt/tools/atom.py` readback-gate'i, `adt_activate` sonrasi AKTIF kaynagi
"bu surecte push edilen kaynak" ile kiyaslar. Baseline (`_LAST_PUSHED`) eskiden YALNIZ push
TAM basariliysa yaziliyordu (`if ok:`), oysa `push_object` basarisi
`source_uploaded AND activated AND readback is not False`tir (scripts/sap_client.py:1030).

  ⇒ AKTIF kaynagi belirleyen sey UPLOAD'dir, aktivasyon DEGIL. Upload'i gecip aktivasyonu
    patlayan bir push (T11 base<->consumption rename kilidi) SAP'deki inaktif surumu
    DEGISTIRIR ama baseline'i ESKI kaynakta birakir. Bagimlilik duzeltilip obje
    `adt_activate` ile (cogu kez `also=` atomik co-activation) aktive edilince arac canli
    YENI kaynagi ESKI baseline ile kiyaslar -> "yazim oturmadi, re-push gerekli" = SAHTE
    BLOCKER. Canli vaka playbook/adt-cds.md:622'de zaten yaziliydi ("T11-a false-alarm").

SAHTE-NEGATIF GERCEK KUSURDAN PAHALIDIR: dogru isi yanlis sanip geri aldirir.

POLITIKA (fix): baseline UPLOAD aninda yazilir ve KAYNAK/ZAMAN/KAPSAM tasir.
  D1 YAZIM   — `source_uploaded` -> kayit (aktivasyon patlasa da, `aktive=False` damgasiyla)
  D2 KIYAS   — KIRMIZI iddia (content_mismatch) yalniz baseline kiyasa UYGUNSA kurulur:
               belirsiz kaynak (push istisna ile bitti) veya baska binding -> UCUNCU DEGER
               (`content_verified: None`), "dogrulandi" DA demez.
  D3 KUNYE   — her content_* yanitinda push sirasi/zamani/yasi/binding + diff YONU.

⛔ KONTROL GRUBU BU TESTIN OMURGASI: V4/V4b "gercek uyusmazlik HALA yakalanir" ve V5b
"belirsiz kayitta ESITLIK hala YESIL kanittir" satirlari. Onlar silinirse fix bir
"kapiyi susturma"ya doner ve gate KORLESIR (yesil suit duzeltmenin kaniti degildir).

KOSUM:
    python tests/fixtures/aktivasyon_baseline_tazeligi/run.py                   (exit 0)
MUTASYON (yeni kod -> `git show <sha>` yok; REDDEDILEN TASARIM enjekte edilir):
    python tests/fixtures/aktivasyon_baseline_tazeligi/run.py --mutasyon
        her iki degismez geri alinir (eski yazim kurali + eski kiyas)   -> dusmeli
    python tests/fixtures/aktivasyon_baseline_tazeligi/run.py --mutasyon-yalniz-yazim
        YALNIZ D1 geri alinir (aktivasyon patlarsa baseline yazilmaz)   -> V2/V4b duser
    python tests/fixtures/aktivasyon_baseline_tazeligi/run.py --mutasyon-yalniz-kiyas
        YALNIZ D2+D3 geri alinir (belirsiz/binding/kunye yok)           -> V5/V6/V7 duser
Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import os
import sys
import time as _time
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

GECERLI_KIP = {"--mutasyon", "--mutasyon-yalniz-yazim", "--mutasyon-yalniz-kiyas"}
KIP = None
for _a in sys.argv[1:]:
    if _a in GECERLI_KIP:
        KIP = _a
    elif _a.startswith("--"):
        print(f"[KULLANIM] bilinmeyen kip: {_a} (gecerli: {sorted(GECERLI_KIP)})")
        raise SystemExit(2)

# ── MCP SDK KOPRUSU (test-harness'i, uretim kodu DEGIL) ──────────────────────────
# Olculen sey MCP tool KATMANININ DAVRANISI (calisma-zamani) -> AST ile okunamaz, import
# sart. CI'da `mcp` paketi YOK; yalniz EKSIKSE asgari sahte modul kurulur (gercek SDK
# varsa DOKUNULMAZ). Desen: tests/fixtures/dogrulama_kosamadi/run.py.
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
logging.disable(logging.CRITICAL)      # MCP profil uyarilari ciktiyi bogmasin

try:
    from mcp_servers.sap_adt.tools import atom
    from sap_client import SAPClient
    from sap_adt_lib import SAPADTError
except Exception as exc:                                    # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] modul yuklenemedi (sessiz gecme YOK): {exc}")

# ⚠ HARNESS: `SAPClient.push_object` aktivasyon-sonrasi yayilim icin `time.sleep(1)`
# (uyusmazlikta 2 sn) bekler. Sahte SAP'de yayilim gecikmesi YOKTUR; beklemek olculen
# davranisi degistirmez, yalnizca korpusu ~20 sn yavaslatir -> uyku susturulur.
# ⛔ `time.time` DOKUNULMAZ (fix'in kendisi ona dayanir).
_time.sleep = lambda *_a, **_k: None                          # type: ignore[assignment]

SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


# =============================================================================
# SAHTE SAP — "aktif surum" ile "inaktif surum" AYRI tutulur (kusurun yasadigi yer)
# =============================================================================
class _SahteAdt:
    """Gercek `SAPClient.push_object` govdesinin ihtiyac duydugu asgari ADT yuzeyi.

    Degismez: `set_object_source` INAKTIF surumu yazar; AKTIF surum ancak aktivasyon
    BASARILI olursa guncellenir. Gercek SAP'de de boyledir ve Q271'in kusuru tam olarak
    bu iki surumun ayrismasindan dogar."""

    def __init__(self, aktif: str = "", url: str = "https://sap-a.test", client: str = "100"):
        self.url, self.client, self.user = url, client, "TESTUSER"
        self.aktif = aktif          # AKTIF surum
        self.inaktif = aktif        # yuklenen (henuz aktive edilmemis) surum
        self.aktivasyon_ok = True   # aktivasyon basarili mi (T11 kilidi -> False)
        self.aktivasyon_sahte_ok = False   # "success:true" der ama AKTIF surumu guncellemez
        self.upload_hatasi = None   # set_object_source'un atacagi istisna
        self._last_lock_effective_transport = "TRK900001"
        self._last_lock_is_link_up = ""

    # --- push_object'in cagirdiklari ---
    def get_transport_info(self, url):
        return "TRK900001"

    def is_object_locked(self, url):
        return {"locked": False}

    def fetch_source_etag(self, url):
        return "etag123"

    def lock_object(self, url, transport=None):
        return "LOCK1"

    def unlock_object(self, url, lock):
        return True

    def set_object_source(self, url, src, lock, transport, etag=None):
        if self.upload_hatasi is not None:
            raise self.upload_hatasi
        self.inaktif = src
        return True

    def activate_object(self, name, url):
        if self.aktivasyon_sahte_ok:
            return {"success": True}          # SAHTE-OK: aktif surum GUNCELLENMEZ
        if not self.aktivasyon_ok:
            return {"success": False,
                    "errors": [{"message": "Field ... is still being used in view ..."}]}
        self.aktif = self.inaktif
        return {"success": True}

    def get_object_source(self, url, return_etag=False, version=None):
        return self.aktif

    # --- _aktivasyon_readback'in cagirdigi (aktive-bekleyen worklist'i) ---
    @property
    def session(self):
        class _Oturum:
            @staticmethod
            def get(url, headers=None, verify=False, timeout=None):
                class _Y:
                    status_code = 200
                    text = "<root/>"            # bos worklist -> "aktive bekleyen yok"
                return _Y()
        return _Oturum()


class _SahteClient:
    """`adt_push_source` + `adt_activate`in gordugu SAPClient yuzeyi.

    `push_object` GERCEK govdedir (test mantigi yeniden uygulanmaz): basari kurali
    (`uploaded AND activated AND readback is not False`) korpusun DISINDA yasar."""

    def __init__(self, adt: _SahteAdt):
        self.adt_client, self.debug_enabled = adt, False
        self.local_base = Path(".")

    def _find_existing_transport(self, name, otype, transport):
        return transport

    def push_object(self, object_name, object_type="class", transport=None, source_file=None):
        return SAPClient.push_object(self, object_name=object_name, object_type=object_type,
                                     transport=transport, source_file=source_file)

    def activate_object(self, name, object_type="class"):
        adt = self.adt_client
        if adt.aktivasyon_sahte_ok:
            return True                        # "aktive ettim" der, aktif surum eski kalir
        if not adt.aktivasyon_ok:
            return False
        adt.aktif = adt.inaktif
        return True


V1_KAYNAK = "define view entity ZQ271_V as select from tab { key alan_a }"
V2_KAYNAK = "define view entity ZQ271_V as select from tab { key alan_a, alan_yeni }"

ARAC = {"client": None}     # aktif sahte client (atom._get_client bunu dondurur)


def _kur(aktif: str = "", **kw) -> _SahteAdt:
    """Temiz baslangic: modul-duzeyi baseline sozlugu SIFIRLANIR (vektor izolasyonu)."""
    atom._LAST_PUSHED.clear()
    adt = _SahteAdt(aktif, **kw)
    ARAC["client"] = _SahteClient(adt)
    return adt


def _push(ad="ZQ271_V", tip="ddls", kaynak=V1_KAYNAK):
    return atom.adt_push_source(name=ad, object_type=tip, source=kaynak,
                                transport="TRK900001", skip_reviewer=True)


def _aktive(ad="ZQ271_V", tip="ddls", also=None):
    return atom.adt_activate(name=ad, object_type=tip, also=also)


# =============================================================================
# VEKTORLER
# =============================================================================
def v1_temiz_tur():
    """BAGLAM-1 (regresyon): push + aktive AYNI oturumda, her sey temiz."""
    _kur(aktif="")
    p = _push()
    a = _aktive()
    kontrol("V1 BAGLAM-1 temiz push -> ok:true",
            p.get("ok") is True, f"ok={p.get('ok')} err={p.get('error', '-')}")
    kontrol("V1 BAGLAM-1 temiz aktivasyon -> content_verified TRUE, mismatch YOK, ok TRUE",
            a.get("content_verified") is True and not a.get("content_mismatch")
            and a.get("ok") is True,
            f"ok={a.get('ok')} verified={a.get('content_verified')!r} "
            f"mismatch={a.get('content_mismatch')!r}")


def v2_upload_oldu_aktivasyon_patladi():
    """Q271 KOKU (T11-a ikizi): upload gecti, aktivasyon patladi -> baseline YENI kaynak."""
    adt = _kur(aktif="")
    _push(kaynak=V1_KAYNAK)                    # v1 tam basarili -> aktif=v1
    adt.aktivasyon_ok = False                  # T11 kilidi: base<->consumption
    p2 = _push(kaynak=V2_KAYNAK)               # upload OLDU, aktivasyon PATLADI
    kontrol("V2a push ok:false DONER (aktivasyon patladi) — bu dogru davranis",
            p2.get("ok") is False, f"ok={p2.get('ok')}")
    kontrol("V2b UPLOAD baseline'i GUNCELLEDI (kok fix: olcut upload, `ok` degil)",
            (atom._LAST_PUSHED.get(("ZQ271_V", "ddls")) or {}).get("source") == V2_KAYNAK,
            f"baseline={str((atom._LAST_PUSHED.get(('ZQ271_V', 'ddls')) or {}).get('source'))[:60]!r}")
    adt.aktivasyon_ok = True                   # bagimlilik duzeltildi
    a = _aktive()                              # T11 cozumu: co-activate/aktive
    kontrol("V2c ⭐ SAHTE MISMATCH DOGMAZ (aktif=yuklenen) -> verified TRUE, ok TRUE",
            a.get("content_verified") is True and not a.get("content_mismatch")
            and a.get("ok") is True,
            f"ok={a.get('ok')} verified={a.get('content_verified')!r} "
            f"mismatch={a.get('content_mismatch')!r} sebep={str(a.get('content_reason', '-'))[:90]}")


def v3_push_yok_dogrudan_aktive():
    """BAGLAM-2: bu surecte hic push yok -> kayit YOK -> iddia da YOK (uydurma yasak)."""
    _kur(aktif=V1_KAYNAK)
    a = _aktive()
    kontrol("V3 BAGLAM-2 push YOK -> content_* alani HIC uretilmez + ok TRUE",
            a.get("ok") is True and "content_verified" not in a and "content_mismatch" not in a,
            f"ok={a.get('ok')} anahtarlar={[k for k in a if k.startswith('content')]}")


def v4_gercek_uyusmazlik_hala_yakalanir():
    """BAGLAM-3 / KONTROL GRUBU: gate SUSTURULMADI — gercek uyusmazlik HALA BLOCKER."""
    # V4a: tam basarili push, sonra aktif surum DISARIDAN geri alindi (transport import /
    #      baska kullanici) + aktivasyon sahte-OK -> aktif != yuklenen.
    adt = _kur(aktif="")
    _push(kaynak=V2_KAYNAK)                    # baseline=v2, aktif=v2
    adt.aktif = V1_KAYNAK                      # aktif surum disaridan ESKIYE dondu
    adt.aktivasyon_sahte_ok = True             # "aktive ettim" der, aktif surum degismez
    a = _aktive()
    kontrol("V4a ⛔ KONTROL gercek uyusmazlik -> content_mismatch TRUE + ok FALSE (korunmali)",
            a.get("content_mismatch") is True and a.get("content_verified") is False
            and a.get("ok") is False,
            f"ok={a.get('ok')} verified={a.get('content_verified')!r} "
            f"mismatch={a.get('content_mismatch')!r}")
    # V4b: upload-only baseline (aktivasyon patlamis push) + aktivasyon GERCEKTEN oturmadi.
    #      Eski kodda baseline hic yazilmadigi icin bu vaka SESSIZCE atlaniyordu.
    adt2 = _kur(aktif=V1_KAYNAK)
    adt2.aktivasyon_ok = False
    _push(kaynak=V2_KAYNAK)                    # upload oldu (baseline=v2), aktif=v1
    adt2.aktivasyon_ok, adt2.aktivasyon_sahte_ok = True, True   # sahte-OK: aktif v1 kalir
    a2 = _aktive()
    kontrol("V4b ⭐ upload-only baseline ile GERCEK uyusmazlik da yakalanir (eskiden sessiz atlama)",
            a2.get("content_mismatch") is True and a2.get("ok") is False,
            f"ok={a2.get('ok')} verified={a2.get('content_verified')!r} "
            f"mismatch={a2.get('content_mismatch')!r}")


def v5_belirsiz_baseline():
    """Istisna `client.push_object`ten KACTI -> yuklenen kaynak BILINMIYOR: KIRMIZI dusurulur.

    ⭐ SINIR OLCULDU (2026-09-09): `SAPClient.push_object` HER `Exception`i yutar ve
    `result` doner (`sap_client.py` dis `except ...: return result`); `source_uploaded`
    upload'in hemen ardindan set edilir ⇒ o yolda BELIRSIZLIK YOKTUR. Belirsizlik yalnizca
    istisna CAGRIDAN KACARSA gercektir. Bu ayrimi V5f (kontrol grubu) civiler."""
    adt = _kur(aktif="")
    _push(kaynak=V1_KAYNAK)                                   # baseline=v1
    cl = ARAC["client"]
    _gercek_push = cl.push_object

    def _kacan_push(**kw):
        raise SAPADTError("Connection reset by peer")          # cagriDAN kacan istisna
    cl.push_object = _kacan_push                               # type: ignore[assignment]
    p = _push(kaynak=V2_KAYNAK)
    cl.push_object = _gercek_push                              # type: ignore[assignment]
    kontrol("V5a push istisnasi tool'a yansir -> ok:false (aynen)", p.get("ok") is False,
            f"ok={p.get('ok')} error={p.get('error')}")
    kontrol("V5b baseline BELIRSIZ damgalandi (silinmedi)",
            bool((atom._LAST_PUSHED.get(("ZQ271_V", "ddls")) or {}).get("belirsiz")),
            f"belirsiz={(atom._LAST_PUSHED.get(('ZQ271_V', 'ddls')) or {}).get('belirsiz')!r}")
    # aktif surum baseline'dan FARKLI (ne yuklendigi bilinmiyor) -> UCUNCU DEGER
    adt.aktif = V2_KAYNAK
    adt.aktivasyon_sahte_ok = True
    a = _aktive()
    kontrol("V5c ⚠GEVSETME belirsiz baseline + fark -> None + stale_baseline TRUE, ok DUSMEZ",
            a.get("content_verified") is None and a.get("content_stale_baseline") is True
            and not a.get("content_mismatch") and a.get("ok") is True,
            f"ok={a.get('ok')} verified={a.get('content_verified')!r} "
            f"stale={a.get('content_stale_baseline')!r}")
    kontrol("V5d ⛔ KONTROL bilgi KAYBOLMAZ: diff + sebep yanitta durur",
            bool(a.get("content_diff")) and "BASELINE" in str(a.get("content_reason", "")),
            f"diff={'VAR' if a.get('content_diff') else 'YOK'} "
            f"sebep={str(a.get('content_reason'))[:80]}")
    # POZITIF KONTROL: gevsetme YALNIZ kirmizi yonde — esitlik hala YESIL kanit.
    adt.aktif = V1_KAYNAK
    a2 = _aktive()
    kontrol("V5e ⛔ KONTROL belirsiz kayitta ESITLIK hala content_verified TRUE (yesil kaybolmadi)",
            a2.get("content_verified") is True,
            f"verified={a2.get('content_verified')!r}")
    # ⛔ KONTROL GRUBU — GEVSETMENIN SINIRI: upload'in OLMADIGI bilinen yolda (push_object
    # dict donuyor, source_uploaded=False) baseline BELIRSIZ SAYILMAZ; eski baseline hala
    # en son yuklenen kaynaktir ve gercek uyusmazlik BLOCKER olmaya devam eder. Bu satir
    # silinirse gevsetme sinifin TAMAMINA yayilir ve gate korlesir.
    adt3 = _kur(aktif="")
    _push(kaynak=V2_KAYNAK)                                    # baseline=v2, aktif=v2
    adt3.upload_hatasi = SAPADTError("Internal Server Error")   # upload PATLADI (dict doner)
    p3 = _push(kaynak=V1_KAYNAK)
    rec3 = atom._LAST_PUSHED.get(("ZQ271_V", "ddls")) or {}
    adt3.upload_hatasi = None
    adt3.aktif, adt3.aktivasyon_sahte_ok = V1_KAYNAK, True      # aktif surum baseline'dan farkli
    a3 = _aktive()
    kontrol("V5f ⛔ KONTROL upload OLMADIGI BILINEN yolda baseline belirsiz SAYILMAZ -> "
            "gercek uyusmazlik HALA blocker",
            p3.get("ok") is False and not rec3.get("belirsiz")
            and rec3.get("source") == V2_KAYNAK
            and a3.get("content_mismatch") is True and a3.get("ok") is False,
            f"push_ok={p3.get('ok')} belirsiz={rec3.get('belirsiz')!r} "
            f"mismatch={a3.get('content_mismatch')!r} ok={a3.get('ok')}")


def v6_baska_sisteme_ait_baseline():
    """KAPSAM: kayit baska binding'e (host|client) aitse kiyas ANLAMSIZ -> None."""
    _kur(aktif="")
    _push(kaynak=V1_KAYNAK)                    # sistem A'ya yazildi
    eski = ARAC["client"]
    yeni_adt = _SahteAdt(aktif=V2_KAYNAK, url="https://sap-b.test", client="200")
    yeni_adt.aktivasyon_sahte_ok = True
    ARAC["client"] = _SahteClient(yeni_adt)    # switch_tier ikizi: baska sistem
    a = _aktive()
    ARAC["client"] = eski
    kontrol("V6 baseline BASKA sisteme ait -> None + mismatch YOK + ok TRUE",
            a.get("content_verified") is None and not a.get("content_mismatch")
            and a.get("ok") is True and "BASELINE" in str(a.get("content_reason", "")),
            f"ok={a.get('ok')} verified={a.get('content_verified')!r} "
            f"sebep={str(a.get('content_reason'))[:80]}")


def v7_kunye_ve_yon():
    """GORUNURLUK (triage :122-125): sebep KAYNAK/ZAMAN/KAPSAM + diff YONU tasimali."""
    adt = _kur(aktif="")
    _push(kaynak=V2_KAYNAK)
    adt.aktif = V1_KAYNAK
    adt.aktivasyon_sahte_ok = True
    a = _aktive()
    sebep = str(a.get("content_reason", ""))
    kunye = a.get("content_baseline") or {}
    kontrol("V7a mismatch sebebi KUNYE tasir (push sirasi + zaman damgasi + yas)",
            "push#" in sebep and "sn " in sebep and "BASELINE" in sebep, sebep[:120])
    kontrol("V7b mismatch sebebi diff YONUNU tasir (yalniz-push / yalniz-aktif satir sayisi)",
            "-push'ta" in sebep and "-aktifte" in sebep, sebep[-140:])
    kontrol("V7c content_baseline yapisal kunye dondurur (sira/yas/binding/aktive)",
            isinstance(kunye, dict) and kunye.get("push_sira") is not None
            and kunye.get("yas_sn") is not None and bool(kunye.get("binding"))
            and "push_aktive_etti" in kunye, f"kunye={kunye}")


def v7b_uc_degerin_ayirt_edilebilirligi():
    """⭐ UCUNCU DEGER TEK `None`'A COKMEMELI (lider notu 2026-09-09).

    `content_verified: None` iki AYRI sebeple doner (bayat/belirsiz baseline · baska
    binding). Ikisi tek None'a cokerse "olcemedim"in NEDENI kaybolur ve tuketici
    ayrimi yeniden kuramaz. `content_probe` bu ayrimin MAKINE-OKUNUR tasiyicisidir."""
    sondalar = {}

    # (a) None #1 — baseline BELIRSIZ (istisna push cagrisindan KACTI)
    adt = _kur(aktif="")
    _push(kaynak=V1_KAYNAK)
    cl = ARAC["client"]
    _gercek = cl.push_object

    def _kacan(**kw):
        raise SAPADTError("Connection reset by peer")
    cl.push_object = _kacan                                   # type: ignore[assignment]
    _push(kaynak=V2_KAYNAK)
    cl.push_object = _gercek                                  # type: ignore[assignment]
    adt.aktif, adt.aktivasyon_sahte_ok = V2_KAYNAK, True
    sondalar["belirsiz"] = _aktive().get("content_probe")

    # (b) None #2 — baseline BASKA BINDING'e ait
    _kur(aktif="")
    _push(kaynak=V1_KAYNAK)
    yeni = _SahteAdt(aktif=V2_KAYNAK, url="https://sap-b.test", client="200")
    yeni.aktivasyon_sahte_ok = True
    ARAC["client"] = _SahteClient(yeni)
    sondalar["binding"] = _aktive().get("content_probe")

    # (c) True  — esitlik   (d) False — gercek fark
    _kur(aktif="")
    _push(kaynak=V1_KAYNAK)
    sondalar["esitlik"] = _aktive().get("content_probe")
    adt2 = _kur(aktif="")
    _push(kaynak=V2_KAYNAK)
    adt2.aktif, adt2.aktivasyon_sahte_ok = V1_KAYNAK, True
    sondalar["fark"] = _aktive().get("content_probe")

    kontrol("V7d ⭐ IKI `None` yolu AYIRT EDILEBILIR (content_probe farkli + ikisi de dolu)",
            bool(sondalar["belirsiz"]) and bool(sondalar["binding"])
            and sondalar["belirsiz"] != sondalar["binding"], f"sondalar={sondalar}")
    kontrol("V7e DORT sonucun DORDU de ayri sonda kodu tasir (sozlesme tam)",
            len(set(sondalar.values())) == 4 and None not in set(sondalar.values()),
            f"sondalar={sondalar}")


def v8_ucuncu_baglam_co_activation():
    """UCUNCU BAGLAM = AYRI KOD YOLU: `also=` atomik co-activation (T11-a'nin oz yolu).

    Ayrica 2026-06-21 AD-CARPISMASI fix'inin regresyon capasi: ayni ad hem ddls hem bdef."""
    adt = _kur(aktif="")
    import create_rap_service as CRS
    eski_csrf, eski_av = CRS.csrf, CRS.activate_and_verify

    def _sahte_av(a, tok, refs):
        adt.aktif = adt.inaktif                # atomik co-activation basarili
        return True

    CRS.csrf, CRS.activate_and_verify = (lambda a: "TOK"), _sahte_av
    try:
        adt.aktivasyon_ok = False              # T11 kilidi: tek-obje aktivasyon patlar
        _push(ad="ZQ271_V", tip="ddls", kaynak=V2_KAYNAK)      # upload oldu, aktive olmadi
        a = _aktive(ad="ZQ271_V", tip="ddls",
                    also=[{"name": "ZQ271_V", "object_type": "bdef"}])
        rb = a.get("content_readback") or {}
        kontrol("V8a ⭐ co-activation (`also=`) yolunda SAHTE mismatch DOGMAZ",
                a.get("ok") is True
                and (rb.get("ZQ271_V") or {}).get("content_verified") is True,
                f"ok={a.get('ok')} rb={ {k: v.get('content_verified') for k, v in rb.items()} }")
        kontrol("V8b ⛔ KONTROL ad-carpismasi: BDEF kaydi YOK -> BDEF icin iddia URETILMEZ "
                "(ddls kaynagiyla kiyaslanmaz)",
                len(rb) == 1 and "ZQ271_V" in rb,
                f"rb_anahtar={list(rb)} (ddls+bdef ayni ad; yalniz ddls'in kaydi var)")
    finally:
        CRS.csrf, CRS.activate_and_verify = eski_csrf, eski_av


def v9_delete_temizligi():
    """REGRESYON: kayit sozlugu tuple->dict oldu; `adt_delete`in bayat-kayit temizligi
    (atom.py, `_LAST_PUSHED` pop dongusu) HALA calisiyor mu?"""
    _kur(aktif="")
    _push(kaynak=V1_KAYNAK)
    var_once = ("ZQ271_V", "ddls") in atom._LAST_PUSHED
    cl = ARAC["client"]

    def _sil(object_name, object_type, transport=None, confirm=False):
        return True

    def _md(name, object_type="class"):
        return None                            # silindi (404 ikizi)
    cl.delete_object, cl.get_object_metadata = _sil, _md     # type: ignore[attr-defined]
    atom.adt_delete(name="ZQ271_V", object_type="ddls", transport="TRK900001")
    kontrol("V9 delete bayat kaydi TEMIZLER (dict semasi eski temizligi bozmadi)",
            var_once and ("ZQ271_V", "ddls") not in atom._LAST_PUSHED,
            f"once={var_once} sonra={('ZQ271_V', 'ddls') in atom._LAST_PUSHED}")


# =============================================================================
# MUTASYON — REDDEDILEN TASARIM (fix oncesi davranis) enjekte edilir
# =============================================================================
def _eski_baseline_yaz(client, name, object_type, source, *, aktive):
    """REDDEDILEN D1: baseline yalniz push TAM basariliysa (aktivasyon dahil) yazilir."""
    if not aktive:
        return
    atom._LAST_PUSHED[(name.upper(), atom._type_key(object_type))] = {
        "object_type": object_type, "source": source, "ts": _time.time(),
        "sira": 0, "binding": "", "aktive": True, "belirsiz": None, "dogrulandi_ts": None,
    }


def _eski_baseline_belirsiz(name, object_type, sebep):
    """REDDEDILEN D1: istisnada kayit DOKUNULMADAN birakilirdi."""
    return None


def _eski_content_readback(client, name, object_type):
    """REDDEDILEN D2+D3: kaynak/zaman/kapsam degerlendirilmez; fark = daima BLOCKER."""
    t = (object_type or "").lower().strip()
    if t not in atom._SOURCE_BASED_TYPES:
        return {}
    rec = atom._LAST_PUSHED.get((name.upper(), atom._type_key(object_type)))
    if not rec:
        return {}
    pushed = rec.get("source") or ""
    try:
        import sap_adt_lib as L                                  # type: ignore
        from source_drift import normalize_source                # type: ignore
        adt = getattr(client, "adt_client", None) or client
        url = L._resolve_source_url(name, t)
        if not url:
            return {"content_verified": None, "content_reason": "source URL cozulemedi"}
        with atom._capture_stdout():
            live = adt.get_object_source(url, version="active")
    except Exception as exc:                                     # noqa: BLE001
        return {"content_verified": None, "content_reason": f"content readback exception: {exc}"}
    if normalize_source(live) == normalize_source(pushed):
        return {"content_verified": True}
    import difflib
    diff = "\n".join(difflib.unified_diff(
        normalize_source(pushed).splitlines(), normalize_source(live).splitlines(),
        fromfile="pushed", tofile="active", lineterm="", n=1))[:1500]
    return {"content_verified": False, "content_mismatch": True,
            "content_reason": "AKTIF source push edilenle ESLESMIYOR — Re-push + re-activate gerekli.",
            "content_diff": diff}


def _mutasyonu_uygula(kip: str) -> None:
    if kip in ("--mutasyon", "--mutasyon-yalniz-yazim"):
        atom._baseline_yaz = _eski_baseline_yaz            # type: ignore[assignment]
        atom._baseline_belirsiz = _eski_baseline_belirsiz  # type: ignore[assignment]
    if kip in ("--mutasyon", "--mutasyon-yalniz-kiyas"):
        atom._content_readback = _eski_content_readback    # type: ignore[assignment]


def main() -> int:
    if KIP:
        _mutasyonu_uygula(KIP)
        print(f"[MUTASYON] {KIP} — reddedilen tasarim enjekte edildi (gercek kaynak DEGISMEDI)")

    atom.get_active_tier = lambda: "DEV"                   # type: ignore[assignment]
    atom._get_client = lambda: ARAC["client"]              # type: ignore[assignment]

    # ⚠ COKME != FAIL: mutasyonda bir bolum patlarsa fixture SESSIZCE olur ve "olcum
    # yapildi" sanilir. Her bolum izole; patlayan bolum ADIYLA FAIL yazilir.
    for bolum in (v1_temiz_tur, v2_upload_oldu_aktivasyon_patladi, v3_push_yok_dogrudan_aktive,
                  v4_gercek_uyusmazlik_hala_yakalanir, v5_belirsiz_baseline,
                  v6_baska_sisteme_ait_baseline, v7_kunye_ve_yon,
                  v7b_uc_degerin_ayirt_edilebilirligi,
                  v8_ucuncu_baglam_co_activation, v9_delete_temizligi):
        try:
            bolum()
        except BaseException as exc:                       # noqa: BLE001
            kontrol(f"[BOLUM COKTU] {bolum.__name__}", False,
                    f"{type(exc).__name__}: {str(exc)[:160]}")

    gecen = sum(1 for _, ok, _ in SONUC if ok)
    for ad, ok, detay in SONUC:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad}")
        if not ok or os.environ.get("IX_FIXTURE_VERBOSE"):
            print(f"         -> {detay}")
    print(f"\n{gecen}/{len(SONUC)} OK")
    if KIP:
        # Mutasyon kipinde DUSMEK beklenir; tam puan = korpus o degismezi OLCMUYOR (KACTI).
        # ⛔ BU SATIRA `N/M` YAZMA: run_battery skoru ciktinin SON `N/M` eslesmesinden okur
        # (tests/run_battery.py:218 `SKOR_RE.findall(...)[-1]`). Buraya "taban 23/23" gibi bir
        # ifade konursa batarya mutasyonu TAM PUAN sanip `KACTI` der — korpus dusmus olsa BILE.
        # (Olculdu 2026-09-09: uc kip de sahte `KACTI(rc=0) 23/23` raporlandi.)
        print("[MUTASYON] beklenti: skor taban kosumundan DUSUK olmali")
        return 0 if gecen < len(SONUC) else 1
    return 0 if gecen == len(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
