#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fm_okuma_where_used fixture — FM (`func`) OKUMA KANALI + where-used'da "YOK" ↔ "0 ÇAĞIRAN" (Q261).

NEDEN VAR (Q261 = Q217/Q221 turunun artığı + Q106'nın where_used ayağı):
  ① Q221 generic URL tablosunu `func` için FAIL-CLOSED yaptı (grup adı FM adından
     türetilemez) ama ÇALIŞAN bir okuma kanalı açmadı: `adt_get(func)` ve
     `adt_where_used(func)` var olan FM için de, olmayan için de AYNI
     `error:"unexpected"` (ValueError) cevabını veriyordu.
  ② "Obje yok" ile "0 çağıran" ayrımı FM'de ölçülemiyordu.
  CANLI ÖLÇÜM (2026-09-13, DEV, salt-okur) — bu emülatörün kurallarının kaynağı:
     quickSearch objectType=FUGR/FF + tam ad          -> 1 isabet (uri FG'yi içerir)
     sap_client.search_objects(type=FUNC | FUNC/FF)    -> 0 (VAR OLAN FM için de)
       ⚠ 2026-09-13 (Q306①) düzeltme: bu 0 SUNUCUDAN DEĞİL, istemci tip süzgecinden gelir —
       ham quickSearch FUNC/FUNC/FF/func → 1 isabet `FUGR/FF` döner, süzgeç `FUNC≠FUGR` diye eler.
       MCP `adt_search_objects` artık FM takma adını FUGR/FF'ye çevirir (sorgu_araclari_durustlugu U1).
     GET <fm-uri>  Accept core.v1 / application/xml    -> 406 (gövde kabul tipini söyler)
     GET <fm-uri>  Accept fmodules.v3+xml              -> 200 (metadata)
     GET <fm-uri>/source/main text/plain               -> 200 (kaynak)
     var olmayan FM: GET <uri> 404 · /source/main 500 · usageReferences 500
     çağıransız FM: usageReferences 200 + boş liste
     KONTROL GRUBU sınıf: var olmayan sınıf usageReferences 200 + boş (PATTERN #11)

ÖLÇÜLEN DEĞİŞMEZLER:
  R1-R3  `adt_get(func)` grubu çözer, kaynağı `/source/main`den (text/plain), metadata'yı
         v3+xml ile okur; `include_source=False` metadata-only.            [KANAL]
  R4     Var olmayan FM → `ok:true exists:false` + `probe`; YANLIŞ "bu uçtan okunamaz"
         ipucu YOK (`warning` anahtarı yok).                               [AYRIM · ipucu]
  R5-R6  Arama / kaynak GET koşamazsa → `ok:false` ("bakamadım" ≠ "yok").
  R7-R8  Tam-ad eşleşmesi: yalnız ön-ek komşusu dönerse "yok"; komşu+tam ad → tam ad;
         aynı ad iki uç → `ok:false` (tahminle seçilmez).                  [FP]
  R9     `FUNC` filtresinin sahte sıfırı resolver'ı ETKİLEMEZ (resolver FUGR/FF sorar);
         R9a emülatörü kalibre eder (sap_client katmanında FUNC → 0, FUGR/FF → 1).
  R10    Generic kapı yerinde: `get_object_url(..,'func')` hâlâ ValueError.  [GEVŞETME YOK]
  W1-W5  `adt_where_used(func)`: çağıranlı → count · çağıransız → `count:0` +
         `existence_verified:true` · yok → OBJECT_NOT_FOUND + probe (count YOK) ·
         usageReferences 500 → ok:false (count YOK) · arama hatası → ok:false, NOT_FOUND DEĞİL.
  W6     KONTROL: sınıf var/yok davranışı değişmedi.
  I1-I2  `adt_impact_analysis(func)` aynı çözümlemeyi kullanır.
  C1-C3  CLI katmanı (`SAPClient.where_used`, `scripts/where_used.py`'nin çağırdığı yol).

SİLİNMEZ ÇAPALAR (her mutasyonda GEÇER): R9a · R10 · W6a. ⚠ W6b çapa DEĞİLDİR:
`--mutasyon-where-used-ayrim-sokuk` altında DÜŞER, çünkü sınıf ve FM "yok" dalını
PAYLAŞIR (tek dal söküldüğünde ikisi birden 0'a düşer — ölçüldü).

KAPSAM BEYANI — BAKMADIKLARI: gerçek SAP (canlı teyit ayrı kanıt satırıdır) ·
`scripts/where_used.py` alt-süreç çıktı metni · `adt_atc_check`/`adt_lock_check` func
(bu turda kanal AÇILMADI, generic kapıda ValueError verir) · usageReferences listesindeki
DEVC paket satırları (count'u şişirir — ayrı Q adayı, burada ölçülmez).

MUTASYON (bellekte; repoya dosya YAZILMAZ):
  --mutasyon-kanal-sokuk            MCP func dalları kapatılır (eski ValueError yolu)
  --mutasyon-where-used-ayrim-sokuk where_used 'yok' dalı sökülür (boş liste = 0)
  --mutasyon-okuma-ayrim-sokuk      adt_get 'yok' → exists:true
  --mutasyon-ipucu-geri             kanıtlı yokluğa "okunamaz" uyarısı geri eklenir
  --mutasyon-resolver-tahmin        tam-ad süzgeci sökülür (komşu FM kabul edilir)
  --mutasyon-bakamadim-yok          arama istisnası yutulup 'yok' sayılır
  --mutasyon-func-filtresi          resolver FUGR/FF yerine FUNC sorar
ESKİ KOD KARŞITLIĞI: `Q261_TABAN_ONEK=_` ortam değişkeni verilirse dört modül
(`object_types`, `sap_client`, `atom`, `query`) aynı dizindeki `_` önekli kardeşten
yüklenir (ör. `git show <taban>:scripts/sap_client.py > scripts/_sap_client.py`).
Kardeşler koşum sonrası SİLİNİR; korpus kalıcı bir SHA'ya bağlanmaz.

SAP GEREKTİRMEZ. Worktree/repo KÖKÜNDEN koş: `python tests/fixtures/fm_okuma_where_used/run.py`.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
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

# ── MCP SDK KOPRUSU (yalniz EKSIKSE; gercek SDK varsa dokunulmaz) ─────────────────
try:  # pragma: no cover - ortam kosullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    import types as _t
    _mcp = _t.ModuleType("mcp")
    _srv = _t.ModuleType("mcp.server")
    _fast = _t.ModuleType("mcp.server.fastmcp")

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

# ── MUTASYON BEYANI ──────────────────────────────────────────────────────────────
_ATOM = "mcp_servers/sap_adt/tools/atom.py"
_QUERY = "mcp_servers/sap_adt/tools/query.py"
_CLIENT = "scripts/sap_client.py"

MUTASYONLAR = {
    "--mutasyon-kanal-sokuk": [
        (_ATOM,
         "    if is_function_module_type(object_type):\n"
         "        return _read_function_module(name, object_type, include_source)\n",
         "    if False:\n"
         "        return _read_function_module(name, object_type, include_source)\n"),
        (_QUERY,
         "            if is_function_module_type(object_type):\n"
         "                fm = client.resolve_function_module(name)\n"
         "                varlik = fm.get(\"status\") == \"found\"\n",
         "            if False:\n"
         "                fm = client.resolve_function_module(name)\n"
         "                varlik = fm.get(\"status\") == \"found\"\n"),
    ],
    "--mutasyon-where-used-ayrim-sokuk": [
        (_QUERY,
         "            if not varlik:\n                yok = {\n",
         "            if False:\n                yok = {\n"),
    ],
    "--mutasyon-okuma-ayrim-sokuk": [
        (_ATOM,
         "        return {**ortak, \"exists\": False}\n",
         "        return {**ortak, \"exists\": True, \"resolved_uri\": None, \"source\": \"\"}\n"),
    ],
    "--mutasyon-ipucu-geri": [
        (_ATOM,
         "        return {**ortak, \"exists\": False}\n",
         "        return {**ortak, \"exists\": False, \"warning\": (\"'func' tipi bu uctan "
         "dogrudan okunamaz — exists:false 'obje yok' anlamina GELMEYEBILIR\")}\n"),
    ],
    "--mutasyon-resolver-tahmin": [
        (_CLIENT,
         "                       if (h.get('name') or '').strip().upper() == fm\n"
         "                       and '/fmodules/' in (h.get('uri') or '').lower()})\n",
         "                       if '/fmodules/' in (h.get('uri') or '').lower()})\n"),
    ],
    "--mutasyon-bakamadim-yok": [
        (_CLIENT,
         "        hits = self.search_objects(fm, max_results=50, obj_type=self.FM_SEARCH_TYPE)\n",
         "        try:\n"
         "            hits = self.search_objects(fm, max_results=50, obj_type=self.FM_SEARCH_TYPE)\n"
         "        except Exception:\n"
         "            hits = []\n"),
    ],
    "--mutasyon-func-filtresi": [
        (_CLIENT, "    FM_SEARCH_TYPE = 'FUGR/FF'\n", "    FM_SEARCH_TYPE = 'FUNC'\n"),
    ],
}
GECERLI_KIP = {"--mutasyon-kanal-sokuk", "--mutasyon-where-used-ayrim-sokuk",
               "--mutasyon-okuma-ayrim-sokuk", "--mutasyon-ipucu-geri",
               "--mutasyon-resolver-tahmin", "--mutasyon-bakamadim-yok",
               "--mutasyon-func-filtresi"}

_kipler = [a for a in sys.argv[1:] if a.startswith("--mutasyon")]
for _k in _kipler:
    if _k not in GECERLI_KIP:
        print(f"[KULLANIM] bilinmeyen kip: {_k} — gecerli: {sorted(GECERLI_KIP)}")
        sys.exit(2)
TABAN_ONEK = os.environ.get("Q261_TABAN_ONEK", "")
DEGISIM: dict[str, list[tuple[str, str]]] = {}
for _k in _kipler:
    for rel, eski, yeni in MUTASYONLAR[_k]:
        DEGISIM.setdefault(rel, []).append((eski, yeni))


def _yukle(ad: str, rel: str):
    """Modülü diskten (gerekirse `_` önekli kardeşten) oku, mutasyonu uygula, exec et."""
    asil = REPO / rel
    kaynak_yol = asil.with_name(TABAN_ONEK + asil.name) if TABAN_ONEK else asil
    if not kaynak_yol.is_file():
        print(f"[KURULAMADI] kaynak yok: {kaynak_yol}")
        sys.exit(2)
    metin = kaynak_yol.read_text(encoding="utf-8")
    for eski, yeni in DEGISIM.get(rel, []):
        n = metin.count(eski)
        if n != 1:
            print(f"[KURULAMADI] {rel}: mutasyon capasi {n} kez bulundu (1 bekleniyordu): "
                  f"{eski.strip()[:70]!r}")
            sys.exit(2)
        metin = metin.replace(eski, yeni)
    spec = importlib.util.spec_from_file_location(ad, str(asil))
    mod = importlib.util.module_from_spec(spec)              # type: ignore[arg-type]
    sys.modules[ad] = mod
    if "." in ad:
        ebeveyn, yaprak = ad.rsplit(".", 1)
        setattr(importlib.import_module(ebeveyn), yaprak, mod)
    exec(compile(metin, str(kaynak_yol), "exec"), mod.__dict__)
    return mod


try:
    object_types = _yukle("object_types", "scripts/object_types.py")
    sap_client = _yukle("sap_client", _CLIENT)
    importlib.import_module("mcp_servers.sap_adt.tools")
    atom = _yukle("mcp_servers.sap_adt.tools.atom", _ATOM)
    query = _yukle("mcp_servers.sap_adt.tools.query", _QUERY)
    from sap_adt_lib import SAPADTClient, SAPADTError, SAPObjectNotFoundError  # noqa: E402
except SystemExit:
    raise
except Exception as exc:                                     # pragma: no cover
    print(f"[KURULAMADI] modul yuklenemedi: {type(exc).__name__}: {exc}")
    sys.exit(2)

# ── SAHTE SAP (canlı ölçülen davranışın emülatörü) ─────────────────────────────────
# ⚠ core PUBLIC repo — yalnız jenerik örnek adlar.
FG = "ZSD001_FG_ORNEK"
FG2 = "ZSD001_FG_IKINCI"
FM_VAR = "ZSD001_FM_ORNEK"            # çağıranlı
FM_BOS = "ZSD001_FM_ORNEK_BOS"        # çağıransız
FM_YOK = "ZSD001_FM_YOK"
FM_KOMSU = "ZSD001_FM_ORNEK_EK"       # yalnız ön-ek komşusu
CLS_VAR = "ZCL_SD001_ORNEK"
CLS_YOK = "ZCL_SD001_YOK"
V3 = "application/vnd.sap.adt.functions.fmodules.v3+xml"


def fm_uri(fg: str, fm: str) -> str:
    return f"/sap/bc/adt/functions/groups/{fg.lower()}/fmodules/{fm.lower()}"


def cls_uri(c: str) -> str:
    return f"/sap/bc/adt/oo/classes/{c.lower()}"


class _Yanit:
    def __init__(self, kod: int, metin: str = ""):
        self.status_code, self.text = kod, metin
        self.content = metin.encode("utf-8")
        self.headers: dict = {}


class SahteSAP:
    def __init__(self, **ayar):
        self.fm = {FM_VAR: FG, FM_BOS: FG}              # ad -> FG
        self.siniflar = {CLS_VAR}
        self.refs = {fm_uri(FG, FM_VAR): [("ZCL_SD001_TUKETICI", "CLAS/OC"),
                                          ("ZSD001", "DEVC/K")],
                     fm_uri(FG, FM_BOS): [],
                     cls_uri(CLS_VAR): [("ZCL_SD001_BASKA", "CLAS/OC")]}
        self.arama_hata = False
        self.komsu_modu = False                         # aramada ön-ek komşularını da döndür
        self.cift_uc: set = set()
        self.kaynak_hata: set = set()
        self.wu_500: set = set()
        self.__dict__.update(ayar)
        self.istekler: list = []

    # -- GET ------------------------------------------------------------------
    def get(self, url, headers=None, params=None, timeout=None, **kw):
        acc = (headers or {}).get("Accept", "")
        yol = url.split("sap.example.test", 1)[-1]
        self.istekler.append(("GET", yol, acc, dict(params or {})))
        if yol.endswith("/repository/informationsystem/search"):
            return self._arama(params or {})
        if "/fmodules/" in yol:
            src = yol.endswith("/source/main")
            fm_ad = yol.split("/fmodules/", 1)[1].split("/", 1)[0].upper()
            fg_ad = yol.split("/functions/groups/", 1)[1].split("/", 1)[0].upper()
            var = self.fm.get(fm_ad) == fg_ad
            if src:
                if not var or fm_ad in self.kaynak_hata:
                    return _Yanit(500, "<exc:exception><message>An exception was raised"
                                       "</message></exc:exception>")
                if acc != "text/plain":
                    return _Yanit(406, "not acceptable")
                return _Yanit(200, f"FUNCTION {fm_ad.lower()}.\r\n  \" govde\r\nENDFUNCTION.\r\n")
            if not var:
                return _Yanit(404, f"<message>Function module {fm_ad} does not exist</message>")
            if acc not in (V3, "*/*"):
                return _Yanit(406, "<message>Accepted content types: %s</message>" % V3)
            return _Yanit(200, f'<fmodule:abapFunctionModule adtcore:name="{fm_ad}" '
                               f'adtcore:type="FUGR/FF"/>')
        if "/oo/classes/" in yol:
            ad = yol.rsplit("/", 1)[1].upper()
            return _Yanit(200, "<class/>") if ad in self.siniflar else _Yanit(404, "")
        return _Yanit(404, "")

    def _arama(self, params):
        if self.arama_hata:
            return _Yanit(500, "search down")
        q = str(params.get("query", "")).upper()
        t = str(params.get("objectType") or "").upper()
        satir = []
        if t in ("", "FUGR/FF"):                        # ölçüldü: FUNC / FUNC/FF → 0 isabet
            for ad, fg in self.fm.items():
                if ad == q or (self.komsu_modu and ad.startswith(q)):
                    satir.append((ad, "FUGR/FF", fm_uri(fg, ad)))
                    if ad in self.cift_uc:
                        satir.append((ad, "FUGR/FF", fm_uri(FG2, ad)))
        if t in ("", "CLAS", "CLAS/OC"):
            for ad in self.siniflar:
                if ad == q:
                    satir.append((ad, "CLAS/OC", cls_uri(ad)))
        govde = "".join(f'<adtcore:objectReference adtcore:uri="{u}" adtcore:type="{ty}" '
                        f'adtcore:name="{a}"/>' for a, ty, u in satir)
        return _Yanit(200, '<?xml version="1.0"?><adtcore:objectReferences '
                           'xmlns:adtcore="http://www.sap.com/adt/core">%s'
                           '</adtcore:objectReferences>' % govde)

    # -- usageReferences (POST) -----------------------------------------------
    def usage(self, uri):
        self.istekler.append(("POST", "usageReferences", "", {"uri": uri}))
        if uri in self.wu_500:
            return _Yanit(500, "")
        if uri and "/fmodules/" in uri and uri not in self.refs:
            return _Yanit(500, "")                      # ölçüldü: var olmayan FM ucu → 500
        liste = self.refs.get(uri, [])                  # sınıf yok / uri None → 200 + boş
        ns = ('xmlns:usagereferences="http://www.sap.com/adt/ris/usageReferences" '
              'xmlns:adtcore="http://www.sap.com/adt/core"')
        govde = "".join(
            f'<usagereferences:referencedObject usagereferences:uri="/sap/bc/adt/x/{a.lower()}">'
            f'<usagereferences:adtObject adtcore:name="{a}" adtcore:type="{ty}"/>'
            f'</usagereferences:referencedObject>' for a, ty in liste)
        return _Yanit(200, f'<?xml version="1.0"?><usagereferences:usageReferenceResult {ns}>'
                           f'{govde}</usagereferences:usageReferenceResult>')


class SahteAdt:
    search_objects = SAPADTClient.search_objects
    get_object_source = SAPADTClient.get_object_source
    get_object_structure = SAPADTClient.get_object_structure
    where_used = SAPADTClient.where_used
    MAX_SEARCH_RESULTS = 550

    def __init__(self, sap: SahteSAP):
        self.url = "https://sap.example.test"
        self.session = sap
        self.sap = sap
        self.timeout_short = 5
        self.debug_enabled = False
        self.debug_log_path = None
        self.csrf_token = None

    def _get_headers(self, accept_type="application/vnd.sap.adt.core.v1+xml", content_type=None):
        return {"Accept": accept_type}

    def _debug(self, *_a, **_k):
        return None

    def _request_with_csrf_retry(self, method, url, headers=None, params=None, data=None, **kw):
        return self.sap.usage((params or {}).get("uri"))


def kur(**ayar):
    sap = SahteSAP(**ayar)
    c = sap_client.SAPClient.__new__(sap_client.SAPClient)
    c.debug_enabled = False
    c.debug_log_path = None
    c.adt_client = SahteAdt(sap)
    c.local_base = REPO / ".tmp" / "fm_okuma_where_used_kum"
    atom._get_client = lambda _c=c: _c
    return c, sap


def cagir(fn, *a, **k):
    """Çökmeyi FAIL'e değil ÖLÇÜME çevir (mutasyon-dostu)."""
    try:
        return fn(*a, **k)
    except Exception as exc:                                  # noqa: BLE001
        return {"ok": None, "_exc": f"{type(exc).__name__}: {exc}"}


SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((ad, bool(kosul), detay))


def kisa(d) -> str:
    if not isinstance(d, dict):
        return repr(d)[:160]
    return repr({k: v for k, v in d.items() if k not in ("client_log", "metadata")})[:220]


# ── R: OKUMA (adt_get) ────────────────────────────────────────────────────────────
c, sap = kur()
r = cagir(atom.adt_get, FM_VAR, "func", include_source=True)
kontrol("R1 KANAL adt_get(func) var olan FM: exists:true + grup + kaynak + metadata",
        r.get("ok") is True and r.get("exists") is True
        and r.get("function_group") == FG and r.get("resolved_uri") == fm_uri(FG, FM_VAR)
        and "ENDFUNCTION" in str(r.get("source")) and "abapFunctionModule" in str(r.get("metadata")),
        kisa(r))
_get = [(y, a) for m, y, a, _p in sap.istekler if m == "GET" and "/fmodules/" in y]
kontrol("R2 kaynak `/source/main` text/plain · metadata çıplak uç v3+xml ile okundu",
        (fm_uri(FG, FM_VAR) + "/source/main", "text/plain") in _get
        and (fm_uri(FG, FM_VAR), V3) in _get, repr(_get))

c, sap = kur()
r = cagir(atom.adt_get, FM_VAR, "function", include_source=False)
kontrol("R3 include_source=False (+ `function` yazımı): metadata var, kaynak GET YOK",
        r.get("ok") is True and r.get("exists") is True and r.get("source") is None
        and r.get("metadata")
        and not any(y.endswith("/source/main") for _m, y, _a, _p in sap.istekler), kisa(r))

c, sap = kur()
r = cagir(atom.adt_get, FM_YOK, "func")
kontrol("R4 AYRIM var olmayan FM: ok:true exists:false + probe(FUGR/FF)",
        r.get("ok") is True and r.get("exists") is False and "FUGR/FF" in str(r.get("probe")),
        kisa(r))
kontrol("R4b kanıtlı yokluğa YANLIŞ 'bu uçtan okunamaz' uyarısı basılmaz",
        isinstance(r, dict) and "warning" not in r, kisa(r))

c, sap = kur(arama_hata=True)
r = cagir(atom.adt_get, FM_VAR, "func")
kontrol("R5 arama 500 → ok:false ('bakamadım' ≠ 'yok'; exists anahtarı YOK)",
        r.get("ok") is False and "exists" not in r, kisa(r))

c, sap = kur(kaynak_hata={FM_VAR})
r = cagir(atom.adt_get, FM_VAR, "func")
kontrol("R6 FM bulundu ama kaynak GET 500 → ok:false (sessiz boş kaynak YOK)",
        r.get("ok") is False and "exists" not in r, kisa(r))

c, sap = kur(komsu_modu=True, fm={FM_KOMSU: FG})
r = cagir(atom.adt_get, FM_VAR, "func")
kontrol("R7 FP: aramada yalnız ön-ek KOMŞUSU var → 'yok' (komşu okunmaz)",
        r.get("ok") is True and r.get("exists") is False, kisa(r))
c, sap = kur(komsu_modu=True, fm={FM_VAR: FG, FM_KOMSU: FG})
r = cagir(atom.adt_get, FM_VAR, "func")
kontrol("R7b FP: komşu + tam ad birlikte → TAM AD okunur",
        r.get("ok") is True and r.get("resolved_uri") == fm_uri(FG, FM_VAR), kisa(r))

c, sap = kur(cift_uc={FM_VAR})
r = cagir(atom.adt_get, FM_VAR, "func")
kontrol("R8 aynı tam ad iki uç → ok:false (tahminle seçilmez)",
        r.get("ok") is False and "exists" not in r, kisa(r))

c, sap = kur()
import contextlib as _cl  # noqa: E402
import io as _io  # noqa: E402
with _cl.redirect_stdout(_io.StringIO()):
    _func0 = cagir(c.search_objects, FM_VAR, 20, "FUNC")
    _fugr1 = cagir(c.search_objects, FM_VAR, 20, "FUGR/FF")
kontrol("R9a KALİBRASYON emülatör: FUNC filtresi var olan FM için 0, FUGR/FF 1 (canlı ölçüm)",
        _func0 == [] and isinstance(_fugr1, list) and len(_fugr1) == 1,
        f"FUNC={_func0!r} FUGR/FF={_fugr1!r}")
sap.istekler.clear()
r = cagir(atom.adt_get, FM_VAR, "func", include_source=False)
_tipler = [p.get("objectType") for m, y, _a, p in sap.istekler if y.endswith("/search")]
kontrol("R9 FUNC sahte-sıfırı resolver'ı etkilemez: arama objectType=FUGR/FF sordu ve buldu",
        _tipler == ["FUGR/FF"] and r.get("exists") is True, f"tipler={_tipler} {kisa(r)}")

try:
    object_types.get_object_url(FM_VAR, "func")
    _gen = "ACIK"
except ValueError:
    _gen = "ValueError"
except Exception as exc:                                      # noqa: BLE001
    _gen = type(exc).__name__
kontrol("R10 GEVŞETME YOK: generic get_object_url(func) hâlâ ValueError", _gen == "ValueError", _gen)

# ── W: WHERE-USED (adt_where_used) ────────────────────────────────────────────────
c, sap = kur()
r = cagir(query.adt_where_used, FM_VAR, "func")
# ⚠ 2026-09-13 Q306②: W1 eskiden `count:2` bekliyordu — emülatörün DEVC/K paket satırı
# DAHİL sayılıyordu (kusuru belgeleyen çapa). Paket düğümü çağıranın ATASIDIR (canlı 10/10):
# count = 1 obje, paket ayrı alanda. Davranış `sorgu_araclari_durustlugu` V1-V6'da ölçülür.
kontrol("W1 çağıranlı FM → ok:true count:1 (+1 paket düğümü ayrı) + resolved_uri",
        r.get("ok") is True and r.get("count") == 1 and r.get("package_count") == 1
        and r.get("resolved_uri") == fm_uri(FG, FM_VAR),
        kisa(r))
r = cagir(query.adt_where_used, FM_BOS, "func")
kontrol("W2 AYRIM çağıransız FM → ok:true count:0 + existence_verified:true",
        r.get("ok") is True and r.get("count") == 0 and r.get("existence_verified") is True, kisa(r))
r = cagir(query.adt_where_used, FM_YOK, "func")
kontrol("W3 AYRIM var olmayan FM → OBJECT_NOT_FOUND + probe, count anahtarı YOK",
        r.get("ok") is False and r.get("error_code") == "OBJECT_NOT_FOUND"
        and "count" not in r and "FUGR/FF" in str(r.get("probe")), kisa(r))

c, sap = kur(wu_500={fm_uri(FG, FM_VAR)})
r = cagir(query.adt_where_used, FM_VAR, "func")
kontrol("W4 usageReferences 500 → ok:false, count YOK (0'a çevrilmez)",
        r.get("ok") is False and "count" not in r and r.get("error_code") != "OBJECT_NOT_FOUND",
        kisa(r))

c, sap = kur(arama_hata=True)
r = cagir(query.adt_where_used, FM_VAR, "func")
kontrol("W5 arama hatası → ok:false, OBJECT_NOT_FOUND DEĞİL, count YOK",
        r.get("ok") is False and r.get("error_code") != "OBJECT_NOT_FOUND" and "count" not in r,
        kisa(r))

c, sap = kur()
r = cagir(query.adt_where_used, CLS_VAR, "class")
kontrol("W6a KONTROL sınıf var → ok:true count:1 (davranış korunur)",
        r.get("ok") is True and r.get("count") == 1, kisa(r))
r = cagir(query.adt_where_used, CLS_YOK, "class")
kontrol("W6b KONTROL sınıf yok → OBJECT_NOT_FOUND (usageReferences'ın 200+[]'si 0 sayılmaz)",
        r.get("ok") is False and r.get("error_code") == "OBJECT_NOT_FOUND" and "count" not in r,
        kisa(r))

# ── I: IMPACT ANALYSIS ────────────────────────────────────────────────────────────
c, sap = kur()
r = cagir(query.adt_impact_analysis, FM_VAR, "func", max_depth=1)
# ⚠ 2026-09-13 Q306②: I1 eskiden `impacted_count:2` bekliyordu (DEVC/K paket satırı etkilenen
# sayılıyordu — kusuru belgeleyen çapa). Paket düğümü atlanır ve ayrıca sayılır.
kontrol("I1 adt_impact_analysis(func) var → ok:true impacted_count:1 (+packages_skipped:1)",
        r.get("ok") is True and r.get("impacted_count") == 1 and r.get("packages_skipped") == 1,
        kisa(r))
r = cagir(query.adt_impact_analysis, FM_YOK, "func", max_depth=1)
kontrol("I2 adt_impact_analysis(func) yok → OBJECT_NOT_FOUND",
        r.get("ok") is False and r.get("error_code") == "OBJECT_NOT_FOUND", kisa(r))

# ── C: CLI KATMANI (SAPClient.where_used — scripts/where_used.py'nin yolu) ────────────
def _cli(ad, tip, **ayar):
    c2, _s = kur(**ayar)
    try:
        with _cl.redirect_stdout(_io.StringIO()):
            return ("DONDU", c2.where_used(ad, tip))
    except Exception as exc:                                  # noqa: BLE001
        return ("ISTISNA", type(exc).__name__)


_c1 = _cli(FM_BOS, "function")
kontrol("C1 CLI çağıransız FM → [] (obje VAR, doğrulandı)", _c1 == ("DONDU", []), repr(_c1))
_c2 = _cli(FM_YOK, "func")
kontrol("C2 CLI var olmayan FM → SAPObjectNotFoundError", _c2 == ("ISTISNA", "SAPObjectNotFoundError"),
        repr(_c2))
_c3 = _cli(FM_VAR, "func", arama_hata=True)
kontrol("C3 CLI arama hatası → NotFound DEĞİL, başka istisna",
        _c3[0] == "ISTISNA" and _c3[1] != "SAPObjectNotFoundError", repr(_c3))

# ── RAPOR ──────────────────────────────────────────────────────────────────────────
kip_etiketi = " ".join(_kipler) or ("TABAN(" + TABAN_ONEK + ")" if TABAN_ONEK else "yeni kod")
print(f"fm_okuma_where_used — kip: {kip_etiketi}")
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {detay}"))
gecen = sum(1 for _a, ok, _d in SONUC if ok)
print(f"SONUC: {gecen}/{len(SONUC)} PASS")
print("KAPSAM: bakilmayan = gercek SAP · where_used.py alt-surec metni · adt_atc_check/"
      "adt_lock_check func · usageReferences DEVC satirlari")
sys.exit(0 if gecen == len(SONUC) else 1)
