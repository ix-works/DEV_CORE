#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fugr_include_yazim fixture — Q383: fonksiyon grubu include'u (FUGR/I) yazma + aktivasyon.

NEDEN VAR (2026-11-07)
  SE54 TMG olay include'u (`L<FG>F01`) çekirdek araçlarıyla YAZILAMIYORDU: `include` tipi daima
  `programs/includes` (PROG/I) yoluna gidiyor, kilit R3TR PROG istiyor ve SAP `403 TK/103 "Nesne
  adı için sözdizim olanaksız"` dönüyordu. Kilit hatasının özeti T100'ü ATIYOR, çare olarak
  koşulsuz "yetki (S_DEVELOP)" öneriyordu. MCP `adt_activate` FUGR/I tipini tanımıyordu.
  Çalışan elle reçete (2026-10-30, canlı): kilit(FUGR/I URL) → PUT → unlock →
  activate_object(include URL) → aktif readback rstrip-eşit.

EKSENLER / VEKTÖRLER
  A  object_types: FUGR/I URL'i, grup ZORUNLU, generic URL fail-closed, contextRef ayrıştırma +
     grup kanıtı (A8 · tekil bağlam A10); containerRef YALNIZ teşhis (A6/A9 — kanıt değil)
     (canlı biçim `canli/` — 2026-11-07 salt-GET, genericize).
  B  lock_object ②: CSRF yenileme GERÇEKTEN koşar → ikinci 403 TK/103 özete girer; yetki önerisi
     yalnız yetki mesajında; okunamayan gövde ÖLÇÜLEMEDİ der; 404×3 KONTROL (NO_LOCK_SUPPORT).
  C  SAPClient ①: push_fugr_include kilit/PUT/aktivasyon/readback HEP FUGR/I ucundan; grup
     uyuşmazlığı / metadata 404 → YAZMADAN dur; `include` + FUGR contextRef → kilitten önce red;
     KONTROL: düz include + L-öneksiz (CMOD tipi) include eski yol. Bug-gate (6a8e0c6): grup
     normalize (C9) · CLI ad alanı ADR 0005-A (C10/C11) · SAPClient.activate_object grup kanıtı (C12).
  D  CLI push_object.py: --group/--source-file zorunluluğu (exit 2) + dağıtım.
  E  MCP atom ③: adt_push_source/adt_activate `group`; group_required; guardrail (grup Z/Y +
     `L<GRUP>` öneki); aktivasyon worklist sondası FUGR/I hedefiyle; içerik readback'i bu tipte koşar.
     Bug-gate F1: öneki geçen YANLIŞ grup contextRef kanıtıyla reddedilir (E9; önceki metin
     containerRef diyordu, YANLIŞTI: SAP URL grubunu yansıtır, ölçüm 2026-11-08), push kaydı grubu (E8),
     `also` + FUGR/I fail-closed (E10).
  ⛔ 2026-11-08 CANLI: SAP FUGR/I ucunda URL grubunu `containerRef`e YANSITIR (200, var olmayan
     grupta da) ⇒ grup kaniti `programs/includes` contextRef FUGR/I SAPL<GRUP> (A8). Sahte oturum
     yansitmayi modeller (A9); onek kuralini gecen var olmayan grup C13/E11/L3. L = adt_lock_check.

SAP: HİÇBİR istek gerçek sisteme gitmez — sahte oturumlar; CLAUDE_PROJECT_DIR + cwd geçici kum.

KULLANIM
  python tests/fixtures/fugr_include_yazim/run.py                     # taban (exit 0)
  python tests/fixtures/fugr_include_yazim/run.py --mutasyon-<ad>     # tek mutasyon (KIPLER)
  Mutasyon çıkışı (run_battery karar tablosu): ilan edilen küme TAM düştü → 1 · sapma → 2 ·
  çapa ≠ 1 kez / mutant derlenmedi → 3.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]
if not (REPO / "scripts").is_dir() or not (REPO / "mcp_servers").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
CANLI = BURASI / "canli"
_KUM = tempfile.mkdtemp(prefix="fugr_inc_")
os.environ["CLAUDE_PROJECT_DIR"] = _KUM
for _v in ("CLAUDE_CWD", "INIT_CWD", "COPILOT_CWD"):
    os.environ.pop(_v, None)
for _p in (REPO / "scripts" / "utils", REPO / "scripts", REPO):
    sys.path.insert(0, str(_p))

GRUP = "ZSD001_FG"
INCL = "LZSD001_FGF01"
FUGR_URL = "/sap/bc/adt/functions/groups/zsd001_fg/includes/lzsd001_fgf01"
PROG_URL = "/sap/bc/adt/programs/includes/lzsd001_fgf01"
# `L<GRUP>` onek kuralini group='ZSD001' ile de gecen YANLIS grup ucu (bug-gate F1)
YANLIS_URL = "/sap/bc/adt/functions/groups/zsd001/includes/lzsd001_fgf01"
# CANLI MODEL (2026-11-08, adt-gateway salt-GET negatif kontrol): SAP FUGR/I ucunda URL'deki
# grubu `containerRef`e GERI YANSITIR ve 200 doner — var olan baska grupta da, var olmayan
# grupta da. Tek fark `packageName` (var olmayan grupta yok). Sahte oturum bunu modeller.
VAR_GRUPLAR = {"ZSD001_FG", "ZSD001"}          # ZSD001 = "baska var olan Z grup" yer tutucusu
KISA_GRUP = "ZSD001_F"                          # onek kuralini gecer, grup YOK (`<GRUP>_T` tipi)
TR = "<TR_ISTEK>"
KAYNAK = "*----- olay include'u\nFORM f_ornek.\n  CLEAR sy-subrc.\nENDFORM.\n"

S: list = []
_TUT: list = []


def ekle(ad, kosul, detay=""):
    S.append((ad, bool(kosul), str(detay)[:300]))


def _sessiz(fn, *a, **k):
    eski = (sys.stdout, sys.stderr)
    atik = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
    sys.stdout = sys.stderr = atik
    try:
        try:
            return fn(*a, **k), None
        except Exception as exc:                      # noqa: BLE001 — istisna ÖLÇÜLÜR
            return None, exc
    finally:
        _TUT.append(atik)
        sys.stdout, sys.stderr = eski


def _oku(ad):
    return (CANLI / ad).read_text(encoding="utf-8")


def _exc_govde(msgid, msgno, metin, v1=""):
    return ('<?xml version="1.0" encoding="utf-8"?><exc:exception xmlns:exc="http://www.sap.com/'
            'abapxml/types/communicationframework"><namespace id="com.sap.adt"/>'
            '<type id="ExceptionResourceNoAccess"/><message lang="TR">%s</message>'
            '<localizedMessage lang="TR">%s</localizedMessage><properties>'
            '<entry key="T100KEY-ID">%s</entry><entry key="T100KEY-NO">%s</entry>'
            '<entry key="T100KEY-V1">%s</entry></properties></exc:exception>'
            % (metin, metin, msgid, msgno, v1))


TK103 = _exc_govde("TK", "103", "Nesne adı için sözdizim olanaksız", INCL)
YETKI = _exc_govde("S#", "021", "You are not authorized to edit objects of this type")
WL_BOS = ('<?xml version="1.0" encoding="utf-8"?><ioc:inactiveObjects '
          'xmlns:ioc="http://www.sap.com/abapxml/inactiveCtsObjects"/>')


class _Y:
    def __init__(self, kod, text=""):
        self.status_code, self.text, self.headers, self.cookies = kod, text, {}, {}


# ─────────────────────────────────────────────────────────────────────────────
# A — object_types
# ─────────────────────────────────────────────────────────────────────────────
def bolum_a(OT):
    ekle("A1 ⭐ get_fugr_include_url -> functions/groups/<fg>/includes/<incl>",
         OT.get_fugr_include_url(GRUP, INCL) == FUGR_URL, OT.get_fugr_include_url(GRUP, INCL))
    r, exc = _sessiz(OT.get_fugr_include_url, "", INCL)
    ekle("A2 grup bos -> ValueError (tahmin yok)", isinstance(exc, ValueError), repr(exc))
    r, exc = _sessiz(OT.get_object_url, INCL, "fugr-include")
    ekle("A3 get_object_url(fugr-include) FAIL-CLOSED + kanonik yolu soyler",
         isinstance(exc, ValueError) and "get_fugr_include_url" in str(exc), repr(exc)[:200])
    ekle("A4 ⭐ include_fugr_baglami(canli programs/includes meta) -> grup",
         OT.include_fugr_baglami(_oku("progs_include_meta.xml")) == GRUP,
         OT.include_fugr_baglami(_oku("progs_include_meta.xml")))
    duz = _oku("progs_include_meta.xml").replace(
        'adtcore:uri="/sap/bc/adt/functions/groups/zsd001_fg/source/main" adtcore:type="FUGR/I" '
        'adtcore:name="SAPLZSD001_FG"',
        'adtcore:uri="/sap/bc/adt/programs/programs/zsd001_prog" adtcore:type="PROG/P" '
        'adtcore:name="ZSD001_PROG"')
    ekle("A5 KONTROL duz program include'u (contextRef PROG/P) -> None",
         duz != _oku("progs_include_meta.xml") and OT.include_fugr_baglami(duz) is None,
         OT.include_fugr_baglami(duz))
    ekle("A6 fugr_include_konteyneri(canli FUGR/I meta) -> grup; bozuk govde -> None",
         OT.fugr_include_konteyneri(_oku("fugr_include_meta.xml")) == GRUP
         and OT.fugr_include_konteyneri("<html>") is None,
         OT.fugr_include_konteyneri(_oku("fugr_include_meta.xml")))
    ekle("A7 KONTROL include tipi URL'i DEGISMEDI (programs/includes)",
         OT.get_object_url("ZSD001_INCL", "include") == "/sap/bc/adt/programs/includes/zsd001_incl")
    k = OT.fugr_include_grup_kaniti
    pm = _oku("progs_include_meta.xml")
    sonuc = {"dogru": k(pm, GRUP)[0], "normalize": k(pm, "  zsd001_fg ")[0],
             "baska-grup": k(pm, "ZSD001")[0], "kisa": k(pm, KISA_GRUP)[0],
             "fugr-f": k(_progs_meta(tip="FUGR/F"), GRUP)[0],
             "prog-p": k(_progs_meta("ZSD001_PROG", "PROG/P"), GRUP)[0],
             "bozuk": k("<html>", GRUP)[0], "bos-grup": k(pm, "")[0]}
    ekle("A8 ⭐ fugr_include_grup_kaniti: YALNIZ contextRef FUGR/I SAPL<GRUP> kanittir",
         sonuc == {"dogru": True, "normalize": True, "baska-grup": False, "kisa": False,
                   "fugr-f": False, "prog-p": False, "bozuk": False, "bos-grup": False}, sonuc)
    yans = _yansiyan_meta(KISA_GRUP, var=False)
    ekle("A9 MODEL (canli 2026-11-08): FUGR/I containerRef URL grubunu yansitir -> eski kanit "
         "var olmayan grubu da 'dogrular'",
         OT.fugr_include_konteyneri(yans) == KISA_GRUP and "packageName" not in yans
         and "packageName" in _yansiyan_meta("ZSD001"), yans[:120])
    sayac2 = pm.replace('include:contextRefCount="1"', 'include:contextRefCount="2"')
    ikinci = ('<include:contextRef adtcore:uri="/sap/bc/adt/functions/groups/zsd001_diger/source/main" '
              'adtcore:type="FUGR/I" adtcore:name="SAPLZSD001_DIGER"/></include:abapInclude>')
    coklu = pm.replace('</include:abapInclude>', ikinci)
    tekil = {"canli-sayac-1": k(pm, GRUP)[0], "sayac-2": k(sayac2, GRUP)[0],
             "coklu-fugr": k(coklu, GRUP)[0]}
    ekle("A10 ⭐ tekil baglam: contextRefCount>1 ya da birden cok FARKLI FUGR/I contextRef -> "
         "fail-closed; KONTROL canli contextRefCount=1 -> True",
         'contextRefCount="1"' in pm and sayac2 != pm and coklu != pm
         and tekil == {"canli-sayac-1": True, "sayac-2": False, "coklu-fugr": False}, tekil)


# ─────────────────────────────────────────────────────────────────────────────
# B — lock_object hata ozeti (②)
# ─────────────────────────────────────────────────────────────────────────────
class _KilitOturum:
    def __init__(self, yanitlar):
        self.yanitlar = list(yanitlar)
        self.postlar: list = []

    def post(self, url, headers=None, data=None, params=None, timeout=None, **kw):
        self.postlar.append(url)
        kod, govde = self.yanitlar.pop(0) if self.yanitlar else (599, "")
        return _Y(kod, govde)


def _kilit_istemci(L, yanitlar):
    c = L.SAPADTClient.__new__(L.SAPADTClient)
    c.debug_enabled = False
    c.url = "http://sahte.invalid"
    c.user = "SAP_USER_A"
    c.csrf_token = "T0"
    c.timeout_short = 5
    c.session = _KilitOturum(yanitlar)
    c._update_cookies = lambda *a, **k: None
    c._get_headers = lambda *a, **k: {"X-CSRF-Token": c.csrf_token}
    c.yenileme = []

    def _fetch(force_refresh=False):
        c.yenileme.append(force_refresh)
        c.csrf_token = "T%d" % len(c.yenileme)
        return c.csrf_token
    c.fetch_csrf_token = _fetch
    return c


def _kilitle(L, yanitlar):
    c = _kilit_istemci(L, yanitlar)
    r, exc = _sessiz(c.lock_object, PROG_URL, transport=TR)
    return c, r, exc


def bolum_b(L):
    c, r, exc = _kilitle(L, [(403, "CSRF token validation failed"), (403, TK103),
                             (403, TK103), (403, TK103)])
    m = str(exc or "")
    # Ozet satiri AYRICA olculur: oneri satiri da T100'u anar; yalniz tum metne bakmak
    # ozetin sebebi dusurmesini GORMEZ (mutasyon --mutasyon-t100 bunu olcer).
    ozet = next((x for x in m.splitlines() if x.startswith("Deneme sonuçları:")), "")
    ekle("B1 ⭐ 403 TK/103 -> ozet SATIRI T100+metni tasir, yetki (S_DEVELOP) ONERILMEZ, "
         "fugr-include ipucu",
         isinstance(exc, L.SAPLockError) and "TK/103: Nesne adı için sözdizim olanaksız" in ozet
         and "S_DEVELOP" not in m and "fugr-include" in m
         and "yetkiden söz etmiyor (yetki deseni eşleşmedi" in m, m[:300])
    ekle("B1c ⭐ CSRF yenilemesi GERCEKTEN kostu (force_refresh) ve yenileme SONRASI 403 TK/103 ozette",
         c.yenileme == [True] and "(CSRF yenileme sonrası) -> 403 [TK/103" in m,
         f"yenileme={c.yenileme} postlar={len(c.session.postlar)} m={m[:200]}")
    c, r, exc = _kilitle(L, [(403, YETKI)] * 3)
    m = str(exc or "")
    ekle("B2 KONTROL gercek yetki mesaji -> S_DEVELOP onerisi KALIR",
         isinstance(exc, L.SAPLockError) and "S_DEVELOP" in m and "S#/021" in m, m[:240])
    c, r, exc = _kilitle(L, [(403, "<html><title>Forbidden</title></html>")] * 3)
    m = str(exc or "")
    ekle("B3 okunamayan 403 govdesi -> sebep ÖLÇÜLEMEDİ, yetki VARSAYILMAZ",
         isinstance(exc, L.SAPLockError) and "ÖLÇÜLEMEDİ" in m and "S_DEVELOP" not in m
         and "-> 403" in m, m[:240])
    c, r, exc = _kilitle(L, [(404, "")] * 3)
    ekle("B4 KONTROL 404x3 -> NO_LOCK_SUPPORT (davranis AYNEN)",
         r == "NO_LOCK_SUPPORT" and exc is None, f"r={r} exc={exc!r}")


# ─────────────────────────────────────────────────────────────────────────────
# C — SAPClient push zinciri (①)
# ─────────────────────────────────────────────────────────────────────────────
class _MetaOturum:
    def __init__(self, meta):
        self.meta = meta          # {url-sonu: (kod, govde) | istisna}
        self.getler: list = []

    def get(self, url, headers=None, params=None, verify=None, timeout=None, **kw):
        self.getler.append(url)
        for uc, yan in self.meta.items():
            if url.endswith(uc):
                if isinstance(yan, Exception):
                    raise yan
                return _Y(*yan)
        m = re.search(r"/functions/groups/([^/]+)/includes/[^/?]+$", url)
        if m:   # SAP davranisi (2026-11-08 olculdu): URL grubunu yansit, 200
            return _Y(200, _yansiyan_meta(m.group(1), m.group(1).upper() in VAR_GRUPLAR))
        return _Y(404, "")


def _yansiyan_meta(grup, var=True):
    """FUGR/I metadata'si — containerRef URL'deki gruptan doldurulur (SAP yansitmasi)."""
    t = _oku("fugr_include_meta.xml").replace("functions/groups/zsd001_fg",
                                               "functions/groups/" + grup.lower())
    t = t.replace('adtcore:name="ZSD001_FG"', f'adtcore:name="{grup.upper()}"')
    if not var:
        t = t.replace(' adtcore:packageName="ZSD001_PKG"', "")
    return t


def _progs_meta(ana_program="SAPLZSD001_FG", tip="FUGR/I"):
    return _oku("progs_include_meta.xml").replace(
        'adtcore:type="FUGR/I" adtcore:name="SAPLZSD001_FG"',
        f'adtcore:type="{tip}" adtcore:name="{ana_program}"')


class _SahteAdt:
    def __init__(self, meta, aktif=None, akt_basari=True, kilit_hata=None):
        self.url = "http://sahte.invalid"
        self.user = "SAP_USER_A"
        self.timeout_short = 5
        self.session = _MetaOturum(meta)
        self.olaylar: list = []
        self.aktif = aktif
        self.akt_basari = akt_basari
        self.kilit_hata = kilit_hata
        self._last_lock_effective_transport = None
        self._last_lock_is_link_up = ''
        self.kilit_sondalari: list = []
        self.kilit_bilgi = None

    def fetch_source_etag(self, url):
        self.olaylar.append(("etag", url))
        return "E1"

    def is_object_locked(self, url):
        self.kilit_sondalari.append(url)
        if self.kilit_bilgi is None:
            self._last_lock_check_reason = "http_404"   # canli olcum 2026-11-08: /adt/locks 404
        return self.kilit_bilgi

    def get_transport_info(self, url):
        return "No transport info available"

    def lock_object(self, url, transport=None, **kw):
        self.olaylar.append(("lock", url, transport))
        if self.kilit_hata:
            raise self.kilit_hata
        self._last_lock_effective_transport = transport
        return "LH1"

    def set_object_source(self, url, src, lock_handle, transport=None, etag=None, **kw):
        self.olaylar.append(("put", url, lock_handle, transport))
        self.yuklenen = src

    def unlock_object(self, url, lock_handle):
        self.olaylar.append(("unlock", url))
        return True

    def activate_object(self, name, url):
        self.olaylar.append(("activate", name, url))
        return {"success": self.akt_basari, "errors": [], "warnings": []}

    def get_object_source(self, url, return_etag=False, version=None):
        self.olaylar.append(("readback", url, version))
        return (self.aktif if self.aktif is not None else getattr(self, "yuklenen", "")) + "\n"

    def _object_name_from_url(self, url):
        return url.rsplit("/", 1)[-1]


def _sapclient(SC, adt):
    c = SC.SAPClient.__new__(SC.SAPClient)
    c.adt_client = adt
    c.debug_enabled = False
    c.debug_log_path = None
    c.local_base = Path(_KUM) / "src"
    return c


def _kaynak_dosyasi(icerik=KAYNAK, ad="incl.abap"):
    p = Path(_KUM) / ad
    p.write_text(icerik, encoding="utf-8", newline="")
    return str(p)


def _tipler(adt, tip):
    return [o for o in adt.olaylar if o[0] == tip]


def bolum_c(SC):
    meta_ok = {FUGR_URL: (200, _oku("fugr_include_meta.xml")),
               PROG_URL: (200, _oku("progs_include_meta.xml"))}
    adt = _SahteAdt(meta_ok)
    r, exc = _sessiz(_sapclient(SC, adt).push_fugr_include, INCL, GRUP, TR, _kaynak_dosyasi())
    r = r or {}
    sira = [o[0] for o in adt.olaylar]
    ekle("C1 ⭐ push_fugr_include: kilit/PUT/unlock/aktivasyon/readback HEP FUGR/I ucundan",
         r.get("success") is True and r.get("readback_ok") is True
         and _tipler(adt, "lock") == [("lock", FUGR_URL, TR)]
         and bool(_tipler(adt, "put")) and _tipler(adt, "put")[0][1] == FUGR_URL + "/source/main"
         and _tipler(adt, "activate") == [("activate", INCL, FUGR_URL)]
         and "unlock" in sira and "activate" in sira and sira.index("unlock") < sira.index("activate")
         and bool(_tipler(adt, "readback")) and _tipler(adt, "readback")[0][2] == "active"
         and not any(PROG_URL in str(o) for o in adt.olaylar),
         f"r={ {k: r.get(k) for k in ('success', 'readback_ok', 'error')} } olaylar={adt.olaylar} exc={exc!r}")
    ekle("C1b readback rstrip: SAP kapanis satir sonu fark sayilmaz + readback_md5 dolu",
         r.get("readback_ok") is True and len(r.get("readback_md5") or "") == 32, r.get("readback_md5"))

    # Gercekci model: FUGR/I ucu grubu YANSITIR (200); kanit programs/includes contextRef'i
    adt = _SahteAdt({PROG_URL: (200, _progs_meta("SAPLZSD001_DIGER"))})
    r, _ = _sessiz(_sapclient(SC, adt).push_fugr_include, INCL, GRUP, TR, _kaynak_dosyasi())
    r = r or {}
    ekle("C2 ⭐ contextRef SAPL<baska grup> (FUGR/I ucu --group'u yansitsa da) -> YAZILMADI "
         "(kilit/PUT YOK), SAPValidationError",
         r.get("success") is False and r.get("error_type") == "SAPValidationError"
         and not _tipler(adt, "lock") and not _tipler(adt, "put"),
         f"r={r.get('error_type')} olaylar={adt.olaylar}")
    adt = _SahteAdt({PROG_URL: (404, "")})
    r, _ = _sessiz(_sapclient(SC, adt).push_fugr_include, INCL, GRUP, TR, _kaynak_dosyasi())
    r = r or {}
    ekle("C3 programs/includes metadata 404 (FUGR/I ucu 200 yansitsa da) -> fail-closed, kilit YOK",
         r.get("success") is False and r.get("error_type") == "SAPValidationError"
         and not _tipler(adt, "lock"), f"r={r.get('error')} olaylar={adt.olaylar}")
    adt = _SahteAdt(meta_ok, aktif="baska kaynak")
    r, _ = _sessiz(_sapclient(SC, adt).push_fugr_include, INCL, GRUP, TR, _kaynak_dosyasi())
    r = r or {}
    ekle("C4 aktif readback FARKLI -> success False + readback_ok False",
         r.get("success") is False and r.get("readback_ok") is False, f"r={r}")

    # C5..C8 — `include` tipiyle gelen FUGR include'u
    meta_prog = {PROG_URL: (200, _oku("progs_include_meta.xml"))}
    adt = _SahteAdt(meta_prog)
    r, _ = _sessiz(_sapclient(SC, adt).push_object, INCL, "include", None, _kaynak_dosyasi())
    r = r or {}
    ekle("C5 ⭐ --type include + SAP contextRef FUGR/I -> kilitten ONCE red + dogru komut onerisi",
         r.get("error_type") == "FugrIncludeTypeError" and not _tipler(adt, "lock")
         and f"--type fugr-include --group {GRUP}" in (r.get("error") or ""),
         f"r={r.get('error_type')} olaylar={adt.olaylar}")
    duz = _oku("progs_include_meta.xml").replace("functions/groups/zsd001_fg/source/main",
                                                 "programs/programs/zsd001_prog").replace(
        'adtcore:type="FUGR/I"', 'adtcore:type="PROG/P"')
    adt = _SahteAdt({PROG_URL: (200, duz)}, kilit_hata=RuntimeError("SAHTE_DUR"))
    r, _ = _sessiz(_sapclient(SC, adt).push_object, INCL, "include", None, _kaynak_dosyasi())
    r = r or {}
    ekle("C6 KONTROL duz program include'u -> ESKI yol (programs/includes kilidi denenir)",
         bool(_tipler(adt, "lock")) and _tipler(adt, "lock")[0][1] == PROG_URL
         and r.get("error_type") != "FugrIncludeTypeError", f"olaylar={adt.olaylar}")
    ex_ad = "ZSD001_EXITU01"
    ex_url = "/sap/bc/adt/programs/includes/zsd001_exitu01"
    ex_meta = _oku("progs_include_meta.xml").replace(INCL, ex_ad)
    adt = _SahteAdt({ex_url: (200, ex_meta)}, kilit_hata=RuntimeError("SAHTE_DUR"))
    r, _ = _sessiz(_sapclient(SC, adt).push_object, ex_ad, "include", None, _kaynak_dosyasi())
    r = r or {}
    ekle("C7 KONTROL L-oneksiz include (CMOD tipi, contextRef FUGR) -> ESKI yol korunur",
         bool(_tipler(adt, "lock")) and _tipler(adt, "lock")[0][1] == ex_url
         and r.get("error_type") != "FugrIncludeTypeError", f"olaylar={adt.olaylar}")
    # C14/C15 — Q393 P2a: namespace'li grubun include'u `/NS/L<GRUP>…` ('L' namespace'ten SONRA);
    # canli bicim (2026-11-08 DEV salt-GET): contextRef FUGR/F name=grup, uri grubu %2f KODLU tasir.
    ns_ad, ns_url = "/NSPC/LFG1TOP", "/sap/bc/adt/programs/includes/%2Fnspc%2Flfg1top"
    ns_meta = _oku("progs_include_meta.xml").replace(INCL, ns_ad).replace(
        'adtcore:type="FUGR/I" adtcore:name="SAPLZSD001_FG"', 'adtcore:type="FUGR/F" adtcore:name="/NSPC/FG1"'
    ).replace("functions/groups/zsd001_fg/source/main", "functions/groups/%2fnspc%2ffg1/source/main")
    adt = _SahteAdt({ns_url: (200, ns_meta)}, kilit_hata=RuntimeError("SAHTE_DUR"))
    r, _ = _sessiz(_sapclient(SC, adt).push_object, ns_ad, "include", None, _kaynak_dosyasi())
    r = r or {}
    ekle("C14 ⭐ NS grup include'u (/NSPC/L…) --type include -> kilitten ONCE red; grup COZULMUS "
         "(/NSPC/FG1, %2F degil) komut onerisinde",
         r.get("error_type") == "FugrIncludeTypeError" and not _tipler(adt, "lock")
         and "--group /NSPC/FG1 " in (r.get("error") or ""), f"r={r.get('error_type')} {r.get('error')!r:.160} olaylar={adt.olaylar}")
    ns_ex, ns_ex_url = "/NSPC/ZXINC", "/sap/bc/adt/programs/includes/%2Fnspc%2Fzxinc"
    adt = _SahteAdt({ns_ex_url: (200, ns_meta.replace(ns_ad, ns_ex))}, kilit_hata=RuntimeError("SAHTE_DUR"))
    r, _ = _sessiz(_sapclient(SC, adt).push_object, ns_ex, "include", None, _kaynak_dosyasi())
    r = r or {}
    ekle("C15 KONTROL NS L-oneksiz include (/NSPC/ZX…, contextRef FUGR) -> ESKI yol korunur",
         bool(_tipler(adt, "lock")) and _tipler(adt, "lock")[0][1] == ns_ex_url
         and r.get("error_type") != "FugrIncludeTypeError", f"olaylar={adt.olaylar}")
    adt = _SahteAdt({PROG_URL: ConnectionError("ag yok")}, kilit_hata=RuntimeError("SAHTE_DUR"))
    r, _ = _sessiz(_sapclient(SC, adt).push_object, INCL, "include", None, _kaynak_dosyasi())
    ekle("C8 metadata GET istisnasi -> on-kontrol OLCULEMEDI, eski akis (kilit denenir)",
         bool(_tipler(adt, "lock")), f"olaylar={adt.olaylar}")

    # C9..C12 — bug-gate (6a8e0c6) bulgulari
    adt = _SahteAdt(meta_ok)
    r, exc = _sessiz(_sapclient(SC, adt).push_fugr_include, INCL, "  " + GRUP.lower() + " ", TR,
                     _kaynak_dosyasi())
    r = r or {}
    ekle("C9 Ö3 bosluklu/kucuk harfli grup normalize edilir -> yaniltici ValidationError YOK",
         r.get("success") is True and r.get("group") == GRUP,
         f"r={ {k: r.get(k) for k in ('success', 'group', 'error')} } exc={exc!r}")
    adt = _SahteAdt(meta_ok)
    r1, _ = _sessiz(_sapclient(SC, adt).push_fugr_include, "LSD001F01", "SD001", TR, _kaynak_dosyasi())
    r1 = r1 or {}
    ekle("C10 ⭐ CLI yolu ADR 0005-A: grup Z/Y degil -> GuardrailViolation, GET/kilit/PUT YOK",
         r1.get("success") is False and r1.get("error_type") == "GuardrailViolation"
         and not adt.session.getler and not adt.olaylar,
         f"r={r1.get('error_type')} get={adt.session.getler}")
    adt = _SahteAdt(meta_ok)
    r2, _ = _sessiz(_sapclient(SC, adt).push_fugr_include, "LZSD001_BASKAF01", GRUP, TR,
                    _kaynak_dosyasi())
    r2 = r2 or {}
    ekle("C11 CLI yolu: include 'L<GRUP>' onekli degil -> GuardrailViolation, GET/kilit YOK",
         r2.get("success") is False and r2.get("error_type") == "GuardrailViolation"
         and not adt.session.getler and not adt.olaylar,
         f"r={r2.get('error_type')} get={adt.session.getler}")
    # ⛔ Eski kurulum "yanlis grup ucu 200 + GERCEK grup containerRef" varsayiyordu — YANLISTI
    # (2026-11-08 canli: SAP URL grubunu yansitir). Artik model yansitir; kanit contextRef'tir.
    adt = _SahteAdt(meta_ok)       # YANLIS_URL: SAP yansitmasi (200 + containerRef ZSD001)
    c = _sapclient(SC, adt)
    yanlis, _ = _sessiz(c.activate_object, INCL, "fugr_include", "ZSD001")
    yanlis_akt = _tipler(adt, "activate")
    dogru, _ = _sessiz(c.activate_object, INCL, "fugr_include", GRUP)
    ekle("C12 ⭐ SAPClient.activate_object: contextRef SAPL<grup> tutmuyor -> False + aktivasyon POST YOK; "
         "KONTROL dogru grup aktive",
         yanlis is False and yanlis_akt == [] and dogru is True
         and _tipler(adt, "activate") == [("activate", INCL, FUGR_URL)],
         f"yanlis={yanlis} dogru={dogru} olaylar={adt.olaylar}")
    adt = _SahteAdt(meta_ok)
    r, _ = _sessiz(_sapclient(SC, adt).push_fugr_include, INCL, KISA_GRUP, TR, _kaynak_dosyasi())
    r = r or {}
    ekle("C13 ⭐ onek kuralini gecen VAR OLMAYAN grup (SAP 200 + yansitma) -> YAZILMADI: "
         "ETag/kilit/PUT YOK",
         r.get("success") is False and r.get("error_type") == "SAPValidationError"
         and not adt.olaylar and any(u.endswith(PROG_URL) for u in adt.session.getler),
         f"r={r.get('error_type')}:{(r.get('error') or '')[:90]} olaylar={adt.olaylar}")


# ─────────────────────────────────────────────────────────────────────────────
# D — CLI push_object.py
# ─────────────────────────────────────────────────────────────────────────────
_DAGITIM = r'''
import sys, types, runpy
m = types.ModuleType("sap_client")
class SAPClient:
    def push_fugr_include(self, **k):
        print("CAGRI:push_fugr_include:%s:%s" % (k.get("group"), k.get("include_name")))
        return {"success": True}
    def push_object(self, **k):
        print("CAGRI:push_object:%s" % k.get("object_type"))
        return {"success": True}
    def push_class_include(self, **k):
        print("CAGRI:push_class_include")
        return {"success": True}
m.SAPClient = SAPClient
sys.modules["sap_client"] = m
sys.argv = [r"@PO@"] + @ARGV@
runpy.run_path(r"@PO@", run_name="__main__")
'''


def _cli(argv, dagitim=False):
    po = str(REPO / "scripts" / "push_object.py")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", CLAUDE_PROJECT_DIR=_KUM)
    if dagitim:
        kod = _DAGITIM.replace("@PO@", po).replace("@ARGV@", repr(argv))
        komut = [sys.executable, "-c", kod]
    else:
        komut = [sys.executable, po] + argv
    p = subprocess.run(komut, cwd=_KUM, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def bolum_d():
    src = _kaynak_dosyasi()
    rc, o = _cli(["--name", INCL, "--type", "fugr-include", "--transport", TR, "--source-file", src])
    ekle("D1 ⭐ fugr-include + --group YOK -> exit 2 (sessiz programs/includes DUSUSU YOK)",
         rc == 2 and "--group <FG> ZORUNLU" in o, f"rc={rc} {o[-200:]}")
    rc, o = _cli(["--name", "ZSD001_INCL", "--type", "include", "--group", GRUP, "--transport", TR])
    ekle("D2 --group + --type include -> exit 2 (yersiz grup)",
         rc == 2 and "yalniz --type fugr-include" in o, f"rc={rc} {o[-200:]}")
    rc, o = _cli(["--name", INCL, "--type", "fugr-include", "--group", GRUP, "--transport", TR])
    ekle("D3 fugr-include + --source-file YOK -> exit 2", rc == 2 and "--source-file ZORUNLU" in o,
         f"rc={rc} {o[-200:]}")
    rc, o = _cli(["--name", INCL, "--type", "fugr-include", "--group", GRUP, "--transport", TR,
                  "--source-file", src], dagitim=True)
    ekle("D4 ⭐ dagitim: --type fugr-include -> SAPClient.push_fugr_include(group=...)",
         rc == 0 and f"CAGRI:push_fugr_include:{GRUP}:{INCL}" in o, f"rc={rc} {o[-300:]}")


# ─────────────────────────────────────────────────────────────────────────────
# E — MCP atom (③)
# ─────────────────────────────────────────────────────────────────────────────
def _mcp_kopru():
    try:  # pragma: no cover - ortam kosullu
        import mcp.server.fastmcp  # type: ignore  # noqa: F401
    except Exception:
        _mcp, _srv, _fast = (types.ModuleType("mcp"), types.ModuleType("mcp.server"),
                             types.ModuleType("mcp.server.fastmcp"))

        class _FastMCP:
            def __init__(self, *a, **k):
                pass

            def tool(self, *a, **k):
                return lambda fn: fn
        _fast.FastMCP = _FastMCP                                 # type: ignore[attr-defined]
        _srv.fastmcp = _fast                                     # type: ignore[attr-defined]
        _mcp.server = _srv                                       # type: ignore[attr-defined]
        sys.modules.setdefault("mcp", _mcp)
        sys.modules.setdefault("mcp.server", _srv)
        sys.modules.setdefault("mcp.server.fastmcp", _fast)
    import logging
    logging.disable(logging.CRITICAL)


def bolum_e(SC):
    _mcp_kopru()
    from mcp_servers.sap_adt.tools import atom
    atom.get_active_tier = lambda: "DEV"                   # type: ignore[assignment]
    meta = {FUGR_URL: (200, _oku("fugr_include_meta.xml")),
            PROG_URL: (200, _oku("progs_include_meta.xml")),
            "/sap/bc/adt/activation/inactiveobjects": (200, WL_BOS)}
    adt = _SahteAdt(meta)
    istemci = _sapclient(SC, adt)
    atom._get_client = lambda: istemci                     # type: ignore[assignment]

    r, exc = _sessiz(atom.adt_push_source, INCL, "fugr_include", KAYNAK, transport=TR,
                     skip_reviewer=True, group=GRUP)
    r = r or {}
    ekle("E1 ⭐ adt_push_source(fugr_include, group) -> push_fugr_include yolu, ok True",
         r.get("ok") is True and (r.get("result") or {}).get("object_url") == FUGR_URL
         and _tipler(adt, "lock") == [("lock", FUGR_URL, TR)],
         f"ok={r.get('ok')} err={r.get('error') or (r.get('result') or {}).get('error')} exc={exc!r}")
    n_once = len(adt.olaylar)
    r, _ = _sessiz(atom.adt_activate, INCL, "fugr_include")
    r = r or {}
    ekle("E2 ⭐ adt_activate(fugr_include) grupsuz -> group_required, SAP cagrisi YOK",
         r.get("ok") is False and r.get("error") == "group_required" and len(adt.olaylar) == n_once,
         f"r={r}")
    r, exc = _sessiz(atom.adt_activate, INCL, "fugr_include", group=GRUP)
    r = r or {}
    akt = [o for o in adt.olaylar[n_once:] if o[0] == "activate"]
    ekle("E3 ⭐ adt_activate(fugr_include, group) -> FUGR/I ucu aktive + worklist sondasi dogruladi",
         r.get("ok") is True and akt == [("activate", INCL, FUGR_URL)]
         and r.get("activation_verified") is True,
         f"ok={r.get('ok')} akt={akt} verified={r.get('activation_verified')} "
         f"err={r.get('error')} exc={exc!r}")
    ekle("E4 ⭐ icerik readback FUGR/I'da da KOSTU (adt_push_source kaydi + grup) -> esitlik",
         r.get("content_verified") is True and r.get("content_probe") == "esitlik",
         f"content_verified={r.get('content_verified')} probe={r.get('content_probe')} "
         f"reason={r.get('content_reason')}")
    r, _ = _sessiz(atom.adt_activate, "ZCL_SD001_ORNEK", "class", group=GRUP)
    r = r or {}
    ekle("E5 KONTROL group + class -> group_not_applicable", r.get("error") == "group_not_applicable", r)
    r, _ = _sessiz(atom.adt_push_source, "LZSD001_BASKAF01", "fugr_include", KAYNAK,
                   transport=TR, skip_reviewer=True, group=GRUP)
    r = r or {}
    r2, _ = _sessiz(atom.adt_activate, "LSD001F01", "fugr_include", group="SD001")
    r2 = r2 or {}
    ekle("E6 guardrail: include 'L<GRUP>' onekli degil / grup Z-Y degil -> ADR_0005_A, yazma YOK",
         r.get("ok") is False and "ADR_0005_A" in str(r) and r2.get("ok") is False
         and "ADR_0005_A" in str(r2), f"r={str(r)[:160]} r2={str(r2)[:160]}")
    ekle("E7 _activation_uri: grupsuz None, gruplu FUGR/I URL'i; KONTROL class AYNEN",
         atom._activation_uri(INCL, "fugr/i") is None
         and atom._activation_uri(INCL, "fugr-include", GRUP) == FUGR_URL
         and atom._activation_uri("ZCL_X", "class") == "/sap/bc/adt/oo/classes/zcl_x",
         f"{atom._activation_uri(INCL, 'fugr/i')} {atom._activation_uri(INCL, 'fugr-include', GRUP)}")

    # E8..E10 — bug-gate (6a8e0c6) F1: grup KANITI aktivasyondan once; also + FUGR/I red
    # YANLIS_URL icin acik kayit YOK: sahte oturum SAP gibi grubu YANSITIR (2026-11-08 olculdu)
    anahtar = (INCL, atom._type_key("fugr_include"))
    eski_kayit = atom._LAST_PUSHED.get(anahtar)
    atom._LAST_PUSHED[anahtar] = {"grup": "ZSD001_DIGER"}
    n0 = len(adt.olaylar)
    r, exc = _sessiz(atom.adt_activate, INCL, "fugr_include", group=GRUP)
    r = r or {}
    ekle("E8 push kaydinin grubu farkli -> fugr_group_mismatch, aktivasyon YOK",
         r.get("ok") is False and r.get("error") == "fugr_group_mismatch"
         and not [o for o in adt.olaylar[n0:] if o[0] == "activate"], f"r={r} exc={exc!r}")
    atom._LAST_PUSHED.pop(anahtar, None)
    n0, g0 = len(adt.olaylar), len(adt.session.getler)
    r, exc = _sessiz(atom.adt_activate, INCL, "fugr_include", group="ZSD001")
    r = r or {}
    ekle("E9 ⭐ adt_activate: onek kuralini gecen YANLIS grup (contextRef SAPL<grup> tutmuyor) -> "
         "fugr_group_unverified, aktivasyon POST YOK",
         r.get("ok") is False and r.get("error") == "fugr_group_unverified"
         and not [o for o in adt.olaylar[n0:] if o[0] == "activate"]
         and any(u.endswith(PROG_URL) for u in adt.session.getler[g0:]),
         f"r={str(r)[:200]} exc={exc!r} olaylar={adt.olaylar[n0:]}")
    if eski_kayit is not None:
        atom._LAST_PUSHED[anahtar] = eski_kayit
    n0, g0 = len(adt.olaylar), len(adt.session.getler)
    ra, _ = _sessiz(atom.adt_activate, "ZCL_SD001_ORNEK", "class",
                    also=[{"name": INCL, "object_type": "fugr_include", "group": GRUP}])
    rb, _ = _sessiz(atom.adt_activate, INCL, "fugr_include",
                    also=[{"name": "ZCL_SD001_ORNEK", "object_type": "class"}], group=GRUP)
    ra, rb = ra or {}, rb or {}
    ekle("E10 also + fugr_include (oge ya da birincil) -> fugr_include_also_unsupported, SAP istegi YOK",
         ra.get("error") == "fugr_include_also_unsupported"
         and rb.get("error") == "fugr_include_also_unsupported"
         and len(adt.olaylar) == n0 and len(adt.session.getler) == g0,
         f"ra={str(ra)[:120]} rb={str(rb)[:120]}")
    n0 = len(adt.olaylar)
    kayit = atom._LAST_PUSHED.pop(anahtar, None)     # push kaydi farki (E8) ayri olculur
    r, exc = _sessiz(atom.adt_activate, INCL, "fugr_include", group=KISA_GRUP)
    r = r or {}
    if kayit is not None:
        atom._LAST_PUSHED[anahtar] = kayit
    ekle("E11 ⭐ adt_activate: onek kuralini gecen VAR OLMAYAN grup (SAP 200 + yansitma) -> "
         "fugr_group_unverified, aktivasyon POST YOK",
         r.get("ok") is False and r.get("error") == "fugr_group_unverified"
         and not [o for o in adt.olaylar[n0:] if o[0] == "activate"], f"r={str(r)[:200]} exc={exc!r}")

    # L — adt_lock_check (salt-okur): FUGR/I + group
    from mcp_servers.sap_adt.tools import query
    adt.kilit_bilgi = {"locked": False, "lock_owner": None}
    k0, g0 = len(adt.kilit_sondalari), len(adt.session.getler)
    r, exc = _sessiz(query.adt_lock_check, INCL, "fugr_include", group=GRUP)
    r = r or {}
    ekle("L1 ⭐ adt_lock_check(fugr_include, group) -> grup kaniti + sonda FUGR/I URL'iyle",
         r.get("ok") is True and r.get("locked") is False
         and adt.kilit_sondalari[k0:] == [FUGR_URL]
         and any(u.endswith(PROG_URL) for u in adt.session.getler[g0:]),
         f"r={str(r)[:160]} sonda={adt.kilit_sondalari[k0:]} exc={exc!r}")
    k0, g0 = len(adt.kilit_sondalari), len(adt.session.getler)
    r, _ = _sessiz(query.adt_lock_check, INCL, "fugr_include")
    r = r or {}
    ekle("L2 adt_lock_check(fugr_include) grupsuz -> group_required, SAP istegi YOK",
         r.get("error") == "group_required" and r.get("locked") is None
         and len(adt.kilit_sondalari) == k0 and len(adt.session.getler) == g0, f"r={r}")
    k0 = len(adt.kilit_sondalari)
    r, _ = _sessiz(query.adt_lock_check, INCL, "fugr_include", group=KISA_GRUP)
    r = r or {}
    ekle("L3 ⭐ adt_lock_check: var olmayan onekli grup -> fugr_group_unverified, kilit ucu SORULMAZ",
         r.get("error") == "fugr_group_unverified" and r.get("locked") is None
         and len(adt.kilit_sondalari) == k0, f"r={str(r)[:200]}")
    adt.kilit_bilgi = None
    r, _ = _sessiz(query.adt_lock_check, INCL, "fugr_include", group=GRUP)
    r = r or {}
    r2, _ = _sessiz(query.adt_lock_check, "ZCL_SD001_ORNEK", "class", group=GRUP)
    r2 = r2 or {}
    ekle("L4 KONTROL /adt/locks 404 (canli olcum) -> kilit_belirsiz locked None (hayir DEGIL); "
         "group + class -> group_not_applicable",
         r.get("error") == "kilit_belirsiz" and r.get("locked") is None and r.get("reason") == "http_404"
         and r2.get("error") == "group_not_applicable", f"r={str(r)[:160]} r2={str(r2)[:120]}")


def main() -> int:
    import importlib
    mods = {}
    for ad in ("object_types", "sap_adt_lib", "sap_client"):
        m, exc = _sessiz(importlib.import_module, ad)
        if m is None:
            print(f"[fixture-hatasi] {ad} import edilemedi: {exc!r}")
            return 3
        mods[ad] = m
    for fn, arg in ((bolum_a, mods["object_types"]), (bolum_b, mods["sap_adt_lib"]),
                    (bolum_c, mods["sap_client"]), (bolum_d, None), (bolum_e, mods["sap_client"])):
        try:
            fn(arg) if arg is not None else fn()
        except Exception as exc:                       # noqa: BLE001 — bolum cokmesi FAIL'dir
            ekle(f"{fn.__name__} COKTU", False, f"{type(exc).__name__}: {exc}")
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    shutil.rmtree(_KUM, ignore_errors=True)
    return 0 if n == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYON — her kip TEK bir degismezi geri alir; dusmesi ILAN EDILEN kume TAM olmalidir.
# ─────────────────────────────────────────────────────────────────────────────
MUTASYONLAR = {
    "--mutasyon-yol": ("scripts/object_types.py",
                       '    return (f"/sap/bc/adt/functions/groups/{quote(g.lower(), safe=\'\')}"\n'
                       '            f"/includes/{quote(i.lower(), safe=\'\')}")\n',
                       '    return f"/sap/bc/adt/programs/includes/{quote(i.lower(), safe=\'\')}"\n',
                       # 2026-11-08: kanit programs/includes'tan alindigi icin yanlis FUGR/I URL'i
                       # sahte oturumda yazimi DURDURMAZ (C1b/C4/C9/E4/E9 gecer, olculdu);
                       # yakalayan URL'i olcen vektorlerdir (A1 C1 C12 E1 E3 E7 L1).
                       {"A1", "C1", "C12", "E1", "E3", "E7", "L1"}),
    # Paylasilan grup kaniti (push + SAPClient.activate_object + MCP): varsayilan fail-closed
    "--mutasyon-grup-dogrulama": ("scripts/sap_client.py",
                                  "            sonuc['ok'], sonuc['sebep'] = bool(ok), sebep\n",
                                  "            sonuc['ok'], sonuc['sebep'] = True, sebep\n",
                                  {"C2", "C12", "C13", "E9", "E11", "L3"}),
    "--mutasyon-varsayilan-kapali": ("scripts/sap_client.py",
                                     "        sonuc: Dict[str, Any] = {'ok': False, 'group': g,",
                                     "        sonuc: Dict[str, Any] = {'ok': True, 'group': g,",
                                     {"C3"}),
    # 2026-11-08 canli: eski kanit (FUGR/I containerRef) URL grubunu yansitir -> KENDINI DOGRULAR
    "--mutasyon-kanit-kaynagi": ("scripts/sap_client.py",
                                 "        kod, govde, hata = self._metadata_getir(sonuc['kanit_url'])\n"
                                 "        ok, sebep = fugr_include_grup_kaniti(govde, g, root=get_explicit_working_dir()) if kod == 200 else (False, '')\n",
                                 "        kod, govde, hata = self._metadata_getir(sonuc['object_url'])\n"
                                 "        ok, sebep = ((__import__('object_types').fugr_include_konteyneri(govde) == g), 'containerRef') if kod == 200 else (False, '')\n",
                                 {"C2", "C3", "C12", "C13", "E9", "E11", "L1", "L3"}),
    "--mutasyon-kanit-ad": ("scripts/object_types.py",
                            "        if ref['type'] == 'FUGR/I' and ref['name'] == beklenen:\n",
                            "        if ref['type'] == 'FUGR/I' and ref['name'].startswith('SAPL'):\n",
                            {"A8", "C2", "C12", "C13", "E9", "E11", "L3"}),
    "--mutasyon-kanit-sayac": ("scripts/object_types.py",
                               "    if sayac is not None and sayac.strip() != '1':\n",
                               "    if False:\n",
                               {"A10"}),
    "--mutasyon-kanit-coklu": ("scripts/object_types.py",
                               "    if len(fugr_baglamlari) > 1:\n",
                               "    if False:\n",
                               {"A10"}),
    "--mutasyon-kanit-tip": ("scripts/object_types.py",
                             "        if ref['type'] == 'FUGR/I' and ref['name'] == beklenen:\n",
                             "        if ref['type'].startswith('FUGR') and ref['name'] == beklenen:\n",
                             {"A8"}),
    "--mutasyon-kilit-grup-kaniti": ("mcp_servers/sap_adt/tools/query.py",
                                     "        if not dogrulama.get(\"ok\"):\n",
                                     "        if False:\n",
                                     {"L3"}),
    "--mutasyon-kilit-url": ("mcp_servers/sap_adt/tools/query.py",
                             "bilgi = adt.is_object_locked(dogrulama[\"object_url\"])",
                             "bilgi = adt.is_object_locked(dogrulama[\"kanit_url\"])",
                             {"L1"}),
    "--mutasyon-kilit-grup-zorunlu": ("mcp_servers/sap_adt/tools/query.py",
                                      "    if fugr_inc and not (group or \"\").strip():\n",
                                      "    if False:\n",
                                      {"L2"}),
    # Ö3: push sonucundaki grup normalize (kanit tarafi kendi icinde strip eder — A8)
    "--mutasyon-grup-strip": ("scripts/sap_client.py",
                              "            'group': (group or '').strip().upper(), 'include'",
                              "            'group': (group or '').upper(), 'include'",
                              {"C9"}),
    "--mutasyon-cli-ad-alani": ("scripts/sap_client.py",
                                "        if ad_hatasi:\n",
                                "        if False:\n",
                                {"C10", "C11"}),
    "--mutasyon-istemci-akt-kaniti": ("scripts/sap_client.py",
                                      "            if not dogrulama['ok']:\n",
                                      "            if False:\n",
                                      {"C12"}),
    "--mutasyon-mcp-grup-kaniti": ("mcp_servers/sap_adt/tools/atom.py",
                                   "        if not dogrulama.get(\"ok\"):\n",
                                   "        if False:\n",
                                   {"E9", "E11"}),
    "--mutasyon-mcp-push-kaydi": ("mcp_servers/sap_adt/tools/atom.py",
                                  "        if rec.get(\"grup\") and str(rec[\"grup\"]).strip().upper() != g_norm:\n",
                                  "        if False:\n",
                                  {"E8"}),
    "--mutasyon-mcp-also-red": ("mcp_servers/sap_adt/tools/atom.py",
                                "    if also and any(_fugr_include_mi(t) for t in\n",
                                "    if False and any(_fugr_include_mi(t) for t in\n",
                                {"E10"}),
    "--mutasyon-include-red": ("scripts/sap_client.py",
                               "            _grup = include_fugr_baglami(_govde) if _kod == 200 else None\n",
                               "            _grup = None\n",
                               {"C5", "C14"}),
    "--mutasyon-l-onek": ("scripts/sap_client.py",
                          "            if _grup and not _govde_ad.startswith('L'):\n",
                          "            if False:\n",
                          {"C7", "C15"}),
    # Q393 P2a: 'L' kontrolu namespace SIYRILMADAN yapilirsa /NSPC/L… CMOD sanilir (eski yol)
    "--mutasyon-l-onek-ns": ("scripts/sap_client.py",
                             "            _govde_ad = object_name.upper()[len(_ns):] if _ns else object_name.upper()\n",
                             "            _govde_ad = object_name.upper()\n",
                             {"C14"}),
    # Q393 P2a: contextRef uri'sindeki grup KODLU kalirsa komut onerisi %2FNSPC%2FFG1 olur
    "--mutasyon-baglam-kodlu": ("scripts/object_types.py",
                                "            return url_parcasindan_ad(parcalar[i + 1])",
                                "            return parcalar[i + 1].upper()",
                                {"C14"}),
    "--mutasyon-t100": ("scripts/sap_adt_lib.py",
                        "        if sebep:\n            etiket = ",
                        "        if False:\n            etiket = ",
                        {"B1", "B1c", "B2"}),
    "--mutasyon-yetki-kosulsuz": ("scripts/sap_adt_lib.py",
                                  "    if any(_KILIT_YETKI_RE.search(sb.get('metin') or '') for sb in metinler):\n",
                                  "    if True:\n",
                                  {"B1", "B3"}),
    "--mutasyon-csrf": ("scripts/sap_adt_lib.py",
                        "                elif response.status_code == 403 and 'CSRF' in response.text:\n"
                        "                    if self.debug_enabled:\n"
                        "                        self._debug(f\"[DEBUG] lock_object attempt {attempt_num} - CSRF error",
                        "                elif False:\n"
                        "                    if self.debug_enabled:\n"
                        "                        self._debug(f\"[DEBUG] lock_object attempt {attempt_num} - CSRF error",
                        {"B1c"}),
    "--mutasyon-cli-grup": ("scripts/push_object.py",
                            "        if not args.group:\n",
                            "        if False:\n",
                            {"D1"}),
    "--mutasyon-mcp-push-yolu": ("mcp_servers/sap_adt/tools/atom.py",
                                 "            if fugr_inc:\n                # Q383: FUGR/I yolu",
                                 "            if False:\n                # Q383: FUGR/I yolu",
                                 {"E1", "E4"}),
    "--mutasyon-mcp-grup-zorunlu": ("mcp_servers/sap_adt/tools/atom.py",
                                    "    if not g:\n        raise ValueError(\"object_type='fugr_include' için group",
                                    "    if False:\n        raise ValueError(\"object_type='fugr_include' için group",
                                    {"E2"}),
    "--mutasyon-mcp-aktivasyon-yolu": ("mcp_servers/sap_adt/tools/atom.py",
                                       "                activated = client.activate_object(name, object_type=object_type, group=group)\n",
                                       "                activated = client.activate_object(name, object_type=object_type)\n",
                                       {"E3", "E4"}),
    "--mutasyon-mcp-readback": ("mcp_servers/sap_adt/tools/atom.py",
                                "    fugr_inc = _fugr_include_mi(t)   # Q383",
                                "    fugr_inc = False   # Q383",
                                {"E4"}),
}
KIPLER = ["--mutasyon-yol", "--mutasyon-grup-dogrulama", "--mutasyon-include-red",
          "--mutasyon-l-onek", "--mutasyon-t100", "--mutasyon-yetki-kosulsuz", "--mutasyon-csrf",
          "--mutasyon-cli-grup", "--mutasyon-mcp-push-yolu", "--mutasyon-mcp-grup-zorunlu",
          "--mutasyon-mcp-aktivasyon-yolu", "--mutasyon-mcp-readback",
          "--mutasyon-grup-strip", "--mutasyon-cli-ad-alani", "--mutasyon-istemci-akt-kaniti",
          "--mutasyon-mcp-grup-kaniti", "--mutasyon-mcp-push-kaydi", "--mutasyon-mcp-also-red",
          "--mutasyon-varsayilan-kapali", "--mutasyon-kanit-kaynagi", "--mutasyon-kanit-ad",
          "--mutasyon-kanit-tip", "--mutasyon-kilit-grup-kaniti", "--mutasyon-kilit-url",
          "--mutasyon-kilit-grup-zorunlu", "--mutasyon-kanit-sayac", "--mutasyon-kanit-coklu",
          "--mutasyon-l-onek-ns", "--mutasyon-baglam-kodlu"]


def _mutasyon(kip) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kok = Path(tempfile.mkdtemp(prefix="fugr_inc_kum_"))
    try:
        for alt in ("scripts", "mcp_servers"):
            shutil.copytree(REPO / alt, kok / alt,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
        hedef = kok / "tests" / "fixtures" / BURASI.name
        shutil.copytree(BURASI, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        dosya = kok / yol
        asil = dosya.read_bytes().decode("utf-8")
        if asil.count(eski) != 1:
            print(f"[KURULAMADI] {kip} -> capa {asil.count(eski)} kez ({yol})")
            return 3
        mutant = asil.replace(eski, yeni, 1)
        try:
            compile(mutant, str(dosya), "exec")
        except SyntaxError as exc:
            print(f"[KURULAMADI] {kip} -> mutant derlenmedi: {exc}")
            return 3
        dosya.write_bytes(mutant.encode("utf-8"))
        r = subprocess.run([sys.executable, str(hedef / "run.py")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600, cwd=str(kok))
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        if not m:
            son = [x for x in (r.stdout + r.stderr).splitlines() if x.strip()][-1:] or ["-"]
            print(f"[ALT-SUREC SAYI VERMEDI] {kip} rc={r.returncode} son={son[0][:160]}")
            return 3
        dusen = {x.split()[1] for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")}
        print(f"{kip}: {m.group(0)} · dusen={sorted(dusen)} · ilan={sorted(beklenen)}")
        if dusen == beklenen:
            print("MUTASYON DUSTU (ilan edilen kume TAM)")
            return 1
        print(f"[SAPMA] fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)}")
        return 2
    finally:
        shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    _kipler = [a for a in sys.argv[1:] if a.startswith("--")]
    if _kipler:
        if len(_kipler) != 1 or _kipler[0] not in MUTASYONLAR:
            print(f"[KULLANIM] gecerli kipler: {KIPLER}")
            sys.exit(2)
        sys.exit(_mutasyon(_kipler[0]))
    sys.exit(main())
