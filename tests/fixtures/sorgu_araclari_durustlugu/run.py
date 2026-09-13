#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sorgu_araclari_durustlugu fixture — Q304 · Q305 · Q306①② · Q310 (MCP okuma/sorgu araçları).

NEDEN VAR (2026-09-13; dört kayıt tek tur; CANLI ölçüm DEV, salt-okur — emülatörün kaynağı):
  Q304  `adt_sql_query` 400'de SAP gövdesini TAŞIMIYORDU (yalnız `[ERROR] … [400] Failed to run
        query`); kırpılan sonuçta `truncated`/`total_rows` yoktu.
        CANLI: 400 gövdesi XML `exc:exception/message` · aralıklı 500 gövdesi HTML `<title>
        Application Server Error` · `totalRows` limitten BAĞIMSIZ toplamdır (T005 limit 10 →
        10 satır, totalRows 249) AMA aggregate'de alttaki satır sayısıdır (COUNT(*) → 1 satır,
        totalRows 249) ⇒ `truncated` totalRows'tan TÜRETİLMEZ (S6 FP çapası).
  Q305  `adt_inactive_objects` TADIR sorgusu. CANLI: kayıttaki "2 adla 400" TEKRARLANMADI
        (birebir sorgu 2/2 200, araç uçtan uca 2/2 ok:true); ölçülen tek 400 sınırı LİSTE
        UZUNLUĞU (15 ad 200 · 25 ad 400; 2026-08-19 kaydı 15 ad 400) ⇒ 5'erli parçalar.
  Q306① quickSearch SUNUCUSU `FUNC`/`FUNC/FF`/`func` filtresine UYAR ve FM'i `FUGR/FF` tipiyle
        döndürür (5/5 FM); `FUGR` → 0. Sahte 0 `sap_client.search_objects` İSTEMCİ süzgecinde
        doğuyordu (canlı: sap_client FUNC/FUNC/FF/func → 0, FUGR/FF → 1).
  Q306② usageReferences bir AĞAÇTIR: `DEVC/K` düğümleri çağıranların PAKET ATALARIDIR (4 sınıf,
        10/10 paket düğümü bir obje düğümünün parentUri zincirinde); alt satırlar (tipsiz
        adtObject + objectIdentifier) kullanım yerleridir. Eski sayım paketleri de sayıyordu.
  Q310  worklist ayrıştırması iki kopyada (MCP `adt_inactive_objects`, `worklist_audit.py`)
        yaşıyordu → kanonik `sap_adt_lib.aktivasyon_worklist_ayristir` (+ user/deleted/transport).

DEĞİŞMEZLER → VEKTÖRLER
  S1-S9  Q304 gövde görünür · None sözleşmesi + eski [ERROR] satırı aynen · truncated KESİN
         (row_limit+1 sonda satırı; tam row_limit kadar satır = kırpık DEĞİL: S4b/S8b)
  T1-T6  Q305 parçalama · başarısız/kırpık parça yalnız KENDİ adlarını null yapar · silinmiş hâlâ
         elenir · TADIR'da satırı OLMAYAN ad kırpık SAYILMAZ (T5, Q adayı davranışı aynen) ·
         kırpık kararı gerçek adt_sql_query yolunda sondadan çıkar (T6)
  U1-U6  Q306① FM takma adları bulur · başka takma adda süzgeç elemesi GÖRÜNÜR · gerçek sıfır sessiz
  V1-V6  Q306② count=obje · yalnız paket → ok:false · impact paketi saymaz/izlemez · CLI aynı ayrım
  X1-X6  Q310 kanonik alanlar · iki yol AYNI liste (canlı aynı-ad F/FF) · kablolama (nöbetçi) ·
         ioc olmayan gövde artık "temiz" değil (SIKILAŞTIRMA) · HTML davranışı aynen

⛔ SİLİNMEZ FP ÇAPALARI: S1b S5 S6 S9 T4 U3 U4 U5 U6 V3 X2 X3 X6 — bunlar olmadan "her şeye
   ok:false / truncated:true / uyarı bas" diyen bir fix de geçerdi.

KİPLER (bellekte metin yaması; repoya/diske YAZILMAZ):
  --mutasyon-q304-govde            last_sql_error üretilmez
  --mutasyon-q304-kirpma           truncated sabit False
  --mutasyon-q304-kirpma-tahmin    truncated totalRows'tan türetilir (reddedilen tasarım)
  --mutasyon-q304-kirpma-esik      eski tahmin `row_count >= row_limit` (tam-limit sonucu sahte kırpık)
  --mutasyon-q304-sonda-yok        row_limit+1 sonda satırı istenmez
  --mutasyon-q305-parca            parça boyutu sınırsız (tek sorgu)
  --mutasyon-q305-sessiz-parca     başarısız parça "ölçüldü" sayılır
  --mutasyon-q305-kirpik-olculdu   kırpık TADIR yanıtı ölçülmüş sayılır
  --mutasyon-q306-esleme           FM takma adı eşlemesi sökülür
  --mutasyon-q306-uyari            süzgeç elemesi uyarısı sökülür
  --mutasyon-q306-paket            paket ayrımı sökülür (her şey obje)
  --mutasyon-q306-yalniz-paket     yalnız-paket fail-closed dalı sökülür
  --mutasyon-q306-impact           impact analizinde paket atlama sökülür
  --mutasyon-q306-cli              CLI yalnız-paket dalı sökülür
  --mutasyon-q310-alan             kanonik `user` alanı boşaltılır
  --mutasyon-q310-bos-liste        worklist_audit ioc olmayan gövdeyi [] sayar
  --mutasyon-q310-mcp-temiz        MCP ioc olmayan gövdeyi ok:true count:0 sayar
ESKİ KOD KARŞITLIĞI: `--taban <sha>` → beş üretim modülü `git show <sha>:<yol>`dan yüklenir
  (taban fix'i zaten taşıyorsa exit 2 + [DOGRULANAMADI]).

KAPSAM BEYANI — BAKMADIKLARI: gerçek SAP (canlı teyit ayrı kanıt) · MCP SDK açıklama üretimi ·
  TADIR'da SATIRI OLMAYAN ad (bugün `tadir_deleted:false`; Q adayı, bilerek ölçülmez) ·
  where_used.py alt-süreç (main() süreç içinde ölçülür) · 500 ardından "Session Timed Out" 400.

SAP GEREKTİRMEZ. Repo/worktree KÖKÜNDEN koş: `python tests/fixtures/sorgu_araclari_durustlugu/run.py`.
"""
from __future__ import annotations

import contextlib
import importlib
import importlib.util
import io
import os
import re
import subprocess
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

# ── MCP SDK KOPRUSU (yalniz EKSIKSE) ──────────────────────────────────────────────
try:  # pragma: no cover - ortam kosullu
    import mcp.server.fastmcp  # type: ignore  # noqa: F401
except Exception:
    import types as _t
    _mcp, _srv, _fast = (_t.ModuleType("mcp"), _t.ModuleType("mcp.server"),
                         _t.ModuleType("mcp.server.fastmcp"))

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

# ── MUTASYON BEYANI ──────────────────────────────────────────────────────────────
_LIB = "scripts/sap_adt_lib.py"
_CL = "scripts/sap_client.py"
_QY = "mcp_servers/sap_adt/tools/query.py"
_WA = "scripts/worklist_audit.py"
_WU = "scripts/where_used.py"

MUTASYONLAR = {
    "--mutasyon-q304-govde": [
        (_CL, "            self.last_sql_error = sap_hata_govdesi(e)\n",
         "            self.last_sql_error = None\n")],
    "--mutasyon-q304-kirpma": [
        (_QY, '    return rows[:row_limit], len(rows) > row_limit\n',
         '    return rows[:row_limit], False\n')],
    "--mutasyon-q304-kirpma-tahmin": [
        (_QY, '            # KESİN (sonda satırı): row_limit+1 istendi, row_limit\'ten FAZLA satır '
              'geldi ⇒ kırpıldı.\n            "truncated": _kirpik,\n',
         '            "truncated": (data.get("total_rows") or 0) > n,\n')],
    "--mutasyon-q304-kirpma-esik": [
        (_QY, '    return rows[:row_limit], len(rows) > row_limit\n',
         '    return rows[:row_limit], len(rows) >= row_limit\n')],
    "--mutasyon-q304-sonda-yok": [
        (_QY, '    return row_limit + 1 if isinstance(row_limit, int) and row_limit > 0 else row_limit\n',
         '    return row_limit\n')],
    "--mutasyon-q305-parca": [
        (_QY, "_TADIR_PARCA = 5\n", "_TADIR_PARCA = 10 ** 6\n")],
    "--mutasyon-q305-sessiz-parca": [
        (_QY, '                        hatalar.append(res.get("message") or res.get("error") '
              'or "bilinmeyen")\n                        continue\n',
         "                        sorulan.update(parca)\n                        continue\n")],
    "--mutasyon-q305-kirpik-olculdu": [
        (_QY, '                    if res.get("truncated"):\n', "                    if False:\n")],
    "--mutasyon-q306-esleme": [
        (_QY, '            gonderilen = getattr(client, "FM_SEARCH_TYPE", None) or "FUGR/FF"\n',
         "            pass\n")],
    "--mutasyon-q306-uyari": [
        (_QY, '        if meta.get("type_filter_dropped") and not results:\n',
         "        if False:\n")],
    "--mutasyon-q306-paket": [
        (_CL, "        (paketler if tip.startswith('DEVC') else objeler).append(r)\n",
         "        objeler.append(r)\n")],
    "--mutasyon-q306-yalniz-paket": [
        (_QY, "        if paketler and not objeler:\n", "        if False:\n")],
    "--mutasyon-q306-impact": [
        (_QY, "                    refs, _paketler = where_used_paket_ayir(refs)\n",
         "                    _paketler = []\n")],
    "--mutasyon-q306-cli": [
        (_WU, "    if not objeler:\n", "    if False:\n")],
    "--mutasyon-q310-alan": [
        (_LIB, "            'user': obj.get('{%s}user' % _AKT_IOC_NS) or '',\n",
         "            'user': '',\n")],
    "--mutasyon-q310-bos-liste": [
        (_WA, "        return None\n    return [{k: g[k] for k in _GIRDI_ALANLARI} for g in girdiler]\n",
         "        return []\n    return [{k: g[k] for k in _GIRDI_ALANLARI} for g in girdiler]\n")],
    "--mutasyon-q310-mcp-temiz": [
        (_QY, '            return {"ok": False, "error": "worklist_govdesi_degil",\n',
         '            return {"ok": True, "count": 0, "error": "worklist_govdesi_degil",\n')],
}
GECERLI_KIP = {"--mutasyon-q304-govde", "--mutasyon-q304-kirpma", "--mutasyon-q304-kirpma-tahmin",
               "--mutasyon-q304-kirpma-esik", "--mutasyon-q304-sonda-yok",
               "--mutasyon-q305-parca", "--mutasyon-q305-sessiz-parca",
               "--mutasyon-q305-kirpik-olculdu", "--mutasyon-q306-esleme",
               "--mutasyon-q306-uyari", "--mutasyon-q306-paket", "--mutasyon-q306-yalniz-paket",
               "--mutasyon-q306-impact", "--mutasyon-q306-cli", "--mutasyon-q310-alan",
               "--mutasyon-q310-bos-liste", "--mutasyon-q310-mcp-temiz"}

_kipler = [a for a in sys.argv[1:] if a.startswith("--mutasyon")]
for _k in _kipler:
    if _k not in GECERLI_KIP:
        print(f"[KULLANIM] bilinmeyen kip: {_k} — gecerli: {sorted(GECERLI_KIP)}")
        sys.exit(2)
TABAN = sys.argv[sys.argv.index("--taban") + 1] if "--taban" in sys.argv else ""
DEGISIM: dict[str, list[tuple[str, str]]] = {}
for _k in _kipler:
    for rel, eski, yeni in MUTASYONLAR[_k]:
        DEGISIM.setdefault(rel, []).append((eski, yeni))


def _kaynak(rel: str) -> str:
    if not TABAN:
        return (REPO / rel).read_text(encoding="utf-8")
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{TABAN}:{rel}"], capture_output=True)
    if r.returncode != 0:
        print(f"[KURULAMADI] git show {TABAN}:{rel} basarisiz: {r.stderr[:160]!r}")
        sys.exit(2)
    return r.stdout.decode("utf-8")


def _yukle(ad: str, rel: str):
    """Modülü (gerekirse tabandan) oku, kipin yamasını uygula, exec et (diske yazmaz)."""
    metin = _kaynak(rel)
    for eski, yeni in DEGISIM.get(rel, []):
        n = metin.count(eski)
        if n != 1:
            print(f"[KURULAMADI] {rel}: mutasyon capasi {n} kez bulundu (1 bekleniyordu): "
                  f"{eski.strip()[:70]!r}")
            sys.exit(2)
        metin = metin.replace(eski, yeni)
    asil = REPO / rel
    spec = importlib.util.spec_from_file_location(ad, str(asil))
    mod = importlib.util.module_from_spec(spec)              # type: ignore[arg-type]
    sys.modules[ad] = mod
    if "." in ad:
        ebeveyn, yaprak = ad.rsplit(".", 1)
        setattr(importlib.import_module(ebeveyn), yaprak, mod)
    exec(compile(metin, str(asil), "exec"), mod.__dict__)
    return mod


try:
    L = _yukle("sap_adt_lib", _LIB)
    SC = _yukle("sap_client", _CL)
    importlib.import_module("mcp_servers.sap_adt.tools")
    Q = _yukle("mcp_servers.sap_adt.tools.query", _QY)
    from mcp_servers.sap_adt import _conn as CONN  # noqa: E402
    # ⚠ worklist_audit / where_used import aninda (win32) sys.stdout/stderr'i AYNI buffer uzerine
    # yeni TextIOWrapper ile sarar. Ikinci sarma birincisini sahipsiz birakir -> GC buffer'i
    # KAPATIR ("I/O operation on closed file", rc=1, cikti yok). Asil akislari geri koy ve
    # modul sarmalayicilarini buffer'i kapatmadan AYIR (detach).
    for _ad, _rel, _hedef in (("worklist_audit", _WA, "WA"), ("where_used", _WU, "WU")):
        _o, _e = sys.stdout, sys.stderr
        _o.flush()
        _e.flush()
        globals()[_hedef] = _yukle(_ad, _rel)
        for _yeni, _asil in ((sys.stdout, _o), (sys.stderr, _e)):
            if _yeni is not _asil:
                _yeni.flush()
                _yeni.detach()
        sys.stdout, sys.stderr = _o, _e
except SystemExit:
    raise
except Exception as exc:                                     # pragma: no cover
    print(f"[KURULAMADI] modul yuklenemedi: {type(exc).__name__}: {exc}")
    sys.exit(2)
if TABAN and "_TADIR_PARCA" in _kaynak(_QY):
    print(f"[DOGRULANAMADI] taban {TABAN} fix'i ZATEN tasiyor (_TADIR_PARCA var) -> sayi yok")
    sys.exit(2)
CONN.get_active_tier = lambda: "DEV"                         # type: ignore[assignment]
SAPADTError = L.SAPADTError

# ── SAHTE SAP (canlı ölçülen biçimlerin emülatörü; ⚠ core PUBLIC — jenerik adlar) ──
FG = "ZSD001_FG_ORNEK"
FM = "ZSD001_FM_ORNEK"
CLS = "ZCL_SD001_ORNEK"                # agacli where-used
CLS_PAKET = "ZCL_SD001_YALNIZ_PAKET"   # yalniz paket dugumu donen (tanimsiz sekil)
CLS_BOS = "ZCL_SD001_TUKETICISIZ"
DDLS = "ZSD001_I_ORNEK"
TUK = "ZCL_SD001_TUKETICI"
ENH = "ZENH_SD001_ORNEK"
AYNI_AD = (REPO / "tests" / "fixtures" / "aktivasyon_govde_hukmu" / "canli" /
           "worklist_ayni_ad.xml").read_text(encoding="utf-8")
HATA400 = ('<?xml version="1.0" encoding="utf-8"?><exc:exception '
           'xmlns:exc="http://www.sap.com/abapxml/types/communicationframework">'
           '<namespace id="http://www.sap.com/adt/wda/dataPreview"/>'
           '<type id="ExceptionDataPreviewGeneral"/>'
           '<message lang="EN">all expressions in the projection list must have an alias name'
           '</message></exc:exception>')
HTML500 = ('<!DOCTYPE html> <html><head> <title>Application Server Error</title> </head>'
           '<body>x</body></html>')


def fm_uri(fg, fm):
    return f"/sap/bc/adt/functions/groups/{fg.lower()}/fmodules/{fm.lower()}"


def cls_uri(c):
    return f"/sap/bc/adt/oo/classes/{c.lower()}"


def pkg_uri(p):
    return f"/sap/bc/adt/packages/{p.lower()}"


def dp_xml(kolon, degerler, toplam):
    veri = "".join(f"<dataPreview:data>{v}</dataPreview:data>" for v in degerler)
    return ('<?xml version="1.0" encoding="utf-8"?><dataPreview:tableData '
            'xmlns:dataPreview="http://www.sap.com/adt/dataPreview">'
            f'<dataPreview:totalRows>{toplam}</dataPreview:totalRows>'
            '<dataPreview:queryExecutionTime>1</dataPreview:queryExecutionTime>'
            f'<dataPreview:columns><dataPreview:metadata dataPreview:name="{kolon}"/>'
            f'<dataPreview:dataSet>{veri}</dataPreview:dataSet></dataPreview:columns>'
            '</dataPreview:tableData>')


class _Yanit:
    def __init__(self, kod, metin=""):
        self.status_code, self.text = kod, metin
        self.headers: dict = {}


def _canli_agac():
    """CANLI where-used ağacının biçimi (2026-09-13): ENHO + sınıf (+kullanım satırı) + 3 paket ata."""
    alt, orta, ust = pkg_uri("ZSD001_ALT"), pkg_uri("ZSD001"), pkg_uri("ZSD000")
    return [
        (f"/sap/bc/adt/enhancements/{ENH.lower()}", alt, ENH, "ENHO/XHB"),
        (cls_uri(TUK), alt, TUK, "CLAS/OC"),
        (cls_uri(TUK) + "/source/main#start=10,5", cls_uri(TUK), TUK, None),
        (alt, orta, "ZSD001_ALT", "DEVC/K"),
        (orta, ust, "ZSD001", "DEVC/K"),
        (ust, None, "ZSD000", "DEVC/K"),
    ]


class SahteSAP:
    def __init__(self):
        self.fm = {FM: FG}
        self.siniflar = {CLS, CLS_PAKET, CLS_BOS}
        self.ddls = {DDLS}
        self.refs = {cls_uri(CLS): _canli_agac(),
                     cls_uri(CLS_PAKET): [(pkg_uri("ZSD001"), None, "ZSD001", "DEVC/K")]}
        self.sql = None
        self.worklist, self.worklist_kodu = AYNI_AD, 200
        self.istekler: list = []

    def get(self, url, headers=None, params=None, timeout=None, **kw):
        yol = url.split("sap.example.test", 1)[-1]
        self.istekler.append(("GET", yol, dict(params or {})))
        if yol.endswith("/informationsystem/search"):
            return self._arama(params or {})
        if yol.endswith("/activation/inactiveobjects"):
            return _Yanit(self.worklist_kodu, self.worklist)
        return _Yanit(404, "")

    def _arama(self, params):
        q = str(params.get("query", "")).upper()
        t = str(params.get("objectType") or "").upper()
        satir = []
        # CANLI: FUNC · FUNC/FF · func · FUGR/FF · filtresiz -> FUGR/FF isabet; FUGR -> 0
        if t in ("", "FUNC", "FUNC/FF", "FUGR/FF"):
            satir += [(a, "FUGR/FF", fm_uri(g, a)) for a, g in self.fm.items() if a == q]
        if t in ("", "CLAS", "CLAS/OC"):
            satir += [(a, "CLAS/OC", cls_uri(a)) for a in self.siniflar if a == q]
        # SENTETIK (olculmemis) takma ad: sunucu 'CDS' filtresini DDLS/DF'ye cevirir — sinif
        # duzeyi GORUNURLUK vektoru icin (U2); gercek bir SAP iddiasi DEGILDIR.
        if t in ("", "CDS"):
            satir += [(a, "DDLS/DF", f"/sap/bc/adt/ddic/ddl/sources/{a.lower()}")
                      for a in self.ddls if a == q]
        govde = "".join(f'<adtcore:objectReference adtcore:uri="{u}" adtcore:type="{ty}" '
                        f'adtcore:name="{a}"/>' for a, ty, u in satir)
        return _Yanit(200, '<?xml version="1.0"?><adtcore:objectReferences '
                           'xmlns:adtcore="http://www.sap.com/adt/core">%s'
                           '</adtcore:objectReferences>' % govde)

    def usage(self, uri):
        self.istekler.append(("POST", "usageReferences", {"uri": uri}))
        ns = ('xmlns:usageReferences="http://www.sap.com/adt/ris/usageReferences" '
              'xmlns:adtcore="http://www.sap.com/adt/core"')
        parca = []
        for u, ebeveyn, ad, tip in self.refs.get(uri, []):
            ea = f' usageReferences:parentUri="{ebeveyn}"' if ebeveyn else ""
            if tip:
                ic = f'<usageReferences:adtObject adtcore:name="{ad}" adtcore:type="{tip}"/>'
            else:
                ic = (f'<usageReferences:adtObject adtcore:name="{ad}"/>'
                      '<usageReferences:objectIdentifier/>')
            parca.append(f'<usageReferences:referencedObject usageReferences:uri="{u}"{ea}>'
                         f'{ic}</usageReferences:referencedObject>')
        return _Yanit(200, f'<?xml version="1.0"?><usageReferences:usageReferenceResult {ns}>'
                           f'{"".join(parca)}</usageReferences:usageReferenceResult>')


class SahteAdt:
    search_objects = L.SAPADTClient.search_objects
    where_used = L.SAPADTClient.where_used
    MAX_SEARCH_RESULTS = 550

    def __init__(self, sap):
        self.url = "https://sap.example.test"
        self.session = sap
        self.sap = sap
        self.timeout_short = 5
        self.debug_enabled = False

    def _get_headers(self, accept_type="application/vnd.sap.adt.core.v1+xml", content_type=None):
        return {"Accept": accept_type}

    def _debug(self, *_a, **_k):
        return None

    def _request_with_csrf_retry(self, method, url, headers=None, params=None, data=None, **kw):
        return self.sap.usage((params or {}).get("uri"))

    def get_object_structure(self, url):
        if url.rstrip("/").rsplit("/", 1)[-1].upper() in self.sap.siniflar:
            return "<class/>"
        raise SAPADTError("yok", status_code=404)

    def run_query(self, query, row_number=100):
        return self.sap.sql(query, row_number)


def kur():
    sap = SahteSAP()
    c = SC.SAPClient.__new__(SC.SAPClient)
    c.debug_enabled = False
    c.debug_log_path = None
    c.adt_client = SahteAdt(sap)
    Q._get_client = lambda _c=c: _c                           # type: ignore[assignment]
    return c, sap


def firlat(kod, govde):
    def _f(query, row_number=100):
        raise SAPADTError("Failed to run query", status_code=kod, response_text=govde)
    return _f


def cagir(fn, *a, **k):
    """Çökmeyi FAIL'e değil ÖLÇÜME çevir (mutasyon/taban dostu)."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*a, **k)
    except SystemExit as exc:
        return {"_exit": exc.code}
    except Exception as exc:                                  # noqa: BLE001
        return {"ok": None, "_exc": f"{type(exc).__name__}: {exc}"}


SONUC: list[tuple[str, bool, str]] = []


def kontrol(ad, kosul, detay=""):
    SONUC.append((ad, bool(kosul), str(detay)[:230]))


def kisa(d):
    if not isinstance(d, dict):
        return repr(d)[:200]
    return repr({k: v for k, v in d.items() if k not in ("client_log", "results", "rows")})[:230]


def g(d, k, v=None):
    return d.get(k, v) if isinstance(d, dict) else v


# ═══ S) Q304 — SAP gövdesi + kırpma ════════════════════════════════════════════
c, sap = kur()
sap.sql = firlat(400, HATA400)
_b = io.StringIO()
try:
    with contextlib.redirect_stdout(_b):
        _d = c.run_sql_query("SELECT land1, COUNT(*) FROM t005 GROUP BY land1", 10)
except Exception as exc:                                      # noqa: BLE001
    _d = {"_exc": repr(exc)}
_h = getattr(c, "last_sql_error", None)
kontrol("S1 ⭐400: SAP sebep metni alt katmanda (last_sql_error.message + status_code)",
        _d is None and isinstance(_h, dict) and _h.get("status_code") == 400
        and _h.get("message") == "all expressions in the projection list must have an alias name",
        f"d={_d!r} h={_h!r}")
kontrol("S1b ⛔CAPA None sözleşmesi + eski [ERROR] satırı AYNEN (20+ çağıran)",
        _d is None and "[ERROR] SQL query error: [400] Failed to run query" in _b.getvalue(),
        _b.getvalue()[:120])

c, sap = kur()
sap.sql = firlat(500, HTML500)
cagir(c.run_sql_query, "SELECT land1 FROM t005", 10)
_h = getattr(c, "last_sql_error", None)
kontrol("S2 ⭐aralıklı 500 HTML gövdesi → message = <title> (Application Server Error)",
        isinstance(_h, dict) and _h.get("message") == "Application Server Error"
        and str(_h.get("body_excerpt", "")).startswith("<!DOCTYPE html>"), repr(_h)[:160])

c, sap = kur()
sap.sql = firlat(400, HATA400)
r = cagir(Q.adt_sql_query, query="SELECT land1, COUNT(*) FROM t005 GROUP BY land1", row_limit=10)
# message'ta sebep İKİ yoldan birinden gelir: alt katmanın `[ERROR] SAP yaniti:` log satırı ya da
# (log sebebi taşımıyorsa) `SAP: <sebep>` eki — tekrar basılmaz. Değişmez: SEBEP METNİ message'ta.
kontrol("S3 ⭐MCP 400 → ok:false + sap_error.message + SAP sebep metni message'ta",
        g(r, "ok") is False and g(g(r, "sap_error", {}), "message", "").startswith("all expressions")
        and "all expressions in the projection list" in str(g(r, "message")), kisa(r))

c, sap = kur()
_istenen: list = []


def _tablo(kolon, toplam):
    """SAP emülatörü: `rowNumber`'a UYAR (canlı: limit 10 → 10 satır), en fazla `toplam` satır."""
    def _f(q, n):
        _istenen.append(n)
        return dp_xml(kolon, [f"A{i}" for i in range(min(int(n), toplam))], toplam)
    return _f


sap.sql = _tablo("LAND1", 249)
r = cagir(Q.adt_sql_query, query="SELECT land1 FROM t005", row_limit=10)
kontrol("S4 ⭐kırpma GÖRÜNÜR ve KESİN: 249 satırlık tabloda row_limit=10 → 10 satır + truncated:true",
        g(r, "ok") is True and g(r, "row_count") == 10 and len(g(r, "rows", []) or []) == 10
        and g(r, "truncated") is True and g(r, "total_rows") == 249
        and bool(g(r, "truncated_notice")) and _istenen[-1:] == [11],
        f"{kisa(r)} istenen={_istenen}")

sap.sql = _tablo("LAND1", 10)
r = cagir(Q.adt_sql_query, query="SELECT land1 FROM t005 WHERE land1 LIKE 'A%'", row_limit=10)
kontrol("S4b ⛔CAPA tam row_limit kadar satır (10/10) → truncated:FALSE (eski >= tahmini sahte kırpık derdi)",
        g(r, "ok") is True and g(r, "row_count") == 10 and g(r, "truncated") is False
        and "truncated_notice" not in (r or {}), kisa(r))

sap.sql = lambda q, n: dp_xml("LAND1", ["A1", "A2", "A3"], 3)
r = cagir(Q.adt_sql_query, query="SELECT land1 FROM t005 WHERE land1 LIKE 'A%'", row_limit=100)
kontrol("S5 ⛔CAPA tam sonuç → truncated:false, notice YOK, error YOK",
        g(r, "ok") is True and g(r, "truncated") is False and "truncated_notice" not in (r or {})
        and "error" not in (r or {}) and g(r, "row_count") == 3, kisa(r))

sap.sql = lambda q, n: dp_xml("CNT", ["249"], 249)
r = cagir(Q.adt_sql_query, query="SELECT COUNT(*) AS cnt FROM t005", row_limit=100)
kontrol("S6 ⛔CAPA aggregate: 1 satır + totalRows 249 → truncated:FALSE (totalRows'tan türetilmez)",
        g(r, "ok") is True and g(r, "truncated") is False and g(r, "row_count") == 1, kisa(r))

c, sap = kur()


def _kopuk(q, n):
    raise RuntimeError("baglanti koptu")


sap.sql = _kopuk
r = cagir(Q.adt_sql_query, query="SELECT land1 FROM t005", row_limit=10)
kontrol("S7 ⭐gövdesiz istisna → ok:false, sap_error UYDURULMAZ",
        g(r, "ok") is False and "sap_error" not in (r or {}) and bool(g(r, "message")), kisa(r))

c, sap = kur()
sap.sql = _tablo("MANDT", 9)
r = cagir(Q.adt_table_read, table="T000", row_limit=5)
_r2 = r
sap.sql = firlat(400, HATA400)
r = cagir(Q.adt_table_read, table="T000", row_limit=5)
_etiket = g(g(_r2, "data", {}), "rows_labeled", []) or []
kontrol("S8 ⭐kardeş adt_table_read: 9 satırlık tabloda row_limit=5 → 5 satır + truncated:true · 400 → sap_error",
        g(_r2, "ok") is True and g(_r2, "truncated") is True and len(_etiket) == 5
        and g(r, "ok") is False and bool(g(g(r, "sap_error", {}), "message")),
        f"{kisa(_r2)} | {kisa(r)}")
sap.sql = _tablo("MANDT", 5)
r = cagir(Q.adt_table_read, table="T000", row_limit=5)
kontrol("S8b ⛔CAPA adt_table_read tam 5/5 satır → truncated:FALSE",
        g(r, "ok") is True and g(r, "truncated") is False
        and len(g(g(r, "data", {}), "rows_labeled", []) or []) == 5, kisa(r))

c, sap = kur()
sap.sql = firlat(400, HATA400)
cagir(c.run_sql_query, "SELECT x FROM t000", 5)
sap.sql = lambda q, n: dp_xml("MANDT", ["100"], 1)
cagir(c.run_sql_query, "SELECT mandt FROM t000", 5)
kontrol("S9 ⛔CAPA başarılı çağrı önceki hatayı TAŞIMAZ (last_sql_error bayatlamaz)",
        getattr(c, "last_sql_error", None) is None, repr(getattr(c, "last_sql_error", "yok")))

# ═══ T) Q305 — TADIR parçalama ═════════════════════════════════════════════════
ADLAR25 = ["ZCL_SD001_PARCA_%02d" % i for i in range(1, 26)]


def wl_xml(adlar):
    ns = ('xmlns:ioc="http://www.sap.com/abapxml/inactiveCtsObjects" '
          'xmlns:adtcore="http://www.sap.com/adt/core"')
    govde = "".join(
        '<ioc:entry><ioc:object ioc:deleted="false" ioc:user="SAP_USER_A">'
        f'<ioc:ref adtcore:uri="{cls_uri(a)}" adtcore:type="CLAS/OC" adtcore:name="{a}"/>'
        '</ioc:object></ioc:entry>' for a in adlar)
    return f'<?xml version="1.0"?><ioc:inactiveObjects {ns}>{govde}</ioc:inactiveObjects>'


def tadir_emul(sinir=15, dusen=None, kirpik=None, silinmis=()):
    """`adt_sql_query` yerine: CANLI sınır modeli (>sinir ad → 400) + seçilebilir parça hatası."""
    cagrilar: list = []

    def _f(query, row_limit=100, **kw):
        adlar = re.findall(r"'([^']+)'", query)
        cagrilar.append(adlar)
        if len(adlar) > sinir:
            return {"ok": False, "error": "sorgu_kosmadi",
                    "message": "ADT data preview sorgusu KOŞMADI — [400] · SAP: uzun liste",
                    "sap_error": {"status_code": 400, "message": "uzun liste"}}
        if dusen and dusen in adlar:
            return {"ok": False, "error": "sorgu_kosmadi",
                    "message": "ADT data preview sorgusu KOŞMADI — SAP: parca reddedildi"}
        rows = [{"OBJ_NAME": a, "OBJECT": "CLAS", "DELFLAG": "X" if a in silinmis else ""}
                for a in adlar]
        return {"ok": True, "row_count": len(rows), "rows": rows,
                "truncated": bool(kirpik and kirpik in adlar)}
    return _f, cagrilar


_sql_asil = Q.adt_sql_query


def inaktif(adlar_ya_da_govde, sql):
    c2, sap2 = kur()
    sap2.worklist = (adlar_ya_da_govde if isinstance(adlar_ya_da_govde, str)
                     else wl_xml(adlar_ya_da_govde))
    Q.adt_sql_query = sql                                     # type: ignore[assignment]
    try:
        return cagir(Q.adt_inactive_objects)
    finally:
        Q.adt_sql_query = _sql_asil                           # type: ignore[assignment]


_f, _cg = tadir_emul(sinir=15)
r = inaktif(ADLAR25, _f)
kontrol("T1 ⭐⚠GEVSETME-HUCRESI 25 ad (tek sorguda 400 modeli) → parçalı ölçüm ok:true count:25",
        g(r, "ok") is True and g(r, "count") == 25 and g(r, "count_verified") is True, kisa(r))
_sorulan = sorted(a for p in _cg for a in p)
kontrol("T1b her TADIR sorgusu ≤5 ad ve 25 adın HEPSİ tam bir kez soruldu",
        bool(_cg) and max(len(p) for p in _cg) <= 5 and _sorulan == sorted(ADLAR25),
        f"parca_boylari={[len(p) for p in _cg]}")

_f, _cg = tadir_emul(sinir=15, dusen=ADLAR25[12])
r = inaktif(ADLAR25, _f)
_bekl = ADLAR25[10:15]
kontrol("T2 ⭐1 parça 400 → ok:false · o parçanın 5 adı null · 20 ad ölçülü · sebep tadir_check'te",
        g(r, "ok") is False and g(r, "unverified_count") == 5 and g(r, "confirmed_live_count") == 20
        and sorted(o["name"] for o in g(r, "unverified", []) or []) == _bekl
        and "parca reddedildi" in str(g(r, "tadir_check")) and "count" not in (r or {}), kisa(r))

_f, _cg = tadir_emul(sinir=100, kirpik=ADLAR25[0])
r = inaktif(ADLAR25, _f)
kontrol("T3 ⭐kırpık TADIR yanıtı ölçülmüş SAYILMAZ → o parçanın 5 adı null, ok:false",
        g(r, "ok") is False and g(r, "unverified_count") == 5
        and "KIRPILDI" in str(g(r, "tadir_check")), kisa(r))

_f, _cg = tadir_emul(sinir=100, silinmis={"ZCL_SD001_PARCA_01"})
r = inaktif(ADLAR25[:2], _f)
kontrol("T4 ⛔CAPA silinmiş obje HÂLÂ elenir (count:1, stale:1, ok:true)",
        g(r, "ok") is True and g(r, "count") == 1 and g(r, "stale_deleted_count") == 1, kisa(r))


def tadir_xml(satirlar):
    """Çok kolonlu dataPreview gövdesi (OBJ_NAME · OBJECT · DELFLAG) — sütun bazlı, canlı biçim."""
    kol = []
    for i, ad in enumerate(("OBJ_NAME", "OBJECT", "DELFLAG")):
        veri = "".join(f"<dataPreview:data>{s[i]}</dataPreview:data>" for s in satirlar)
        kol.append(f'<dataPreview:columns><dataPreview:metadata dataPreview:name="{ad}"/>'
                   f'<dataPreview:dataSet>{veri}</dataPreview:dataSet></dataPreview:columns>')
    return ('<?xml version="1.0" encoding="utf-8"?><dataPreview:tableData '
            'xmlns:dataPreview="http://www.sap.com/adt/dataPreview">'
            f'<dataPreview:totalRows>{len(satirlar)}</dataPreview:totalRows>'
            '<dataPreview:queryExecutionTime>1</dataPreview:queryExecutionTime>'
            f'{"".join(kol)}</dataPreview:tableData>')


def uctan_uca(adlar, sql):
    """GERÇEK `adt_sql_query` yolu (stub yok): kırpık kararı sonda satırından çıkar."""
    c4, sap4 = kur()
    sap4.worklist = wl_xml(adlar)
    sap4.sql = sql
    return cagir(Q.adt_inactive_objects)


# Q adayı sınırı (lider şartı 3): TADIR'da SATIRI OLMAYAN ad bugün `tadir_deleted:false` alır.
# Bu PR bunu DEĞİŞTİRMEZ; eksik satır "kırpık" SAYILMAZ (kırpık = row_limit'ten FAZLA satır).
_T5_YOK = {ADLAR25[1], ADLAR25[3]}
r = uctan_uca(ADLAR25[:5], lambda q, n: tadir_xml(
    [(a, "CLAS", "") for a in re.findall(r"'([^']+)'", q) if a not in _T5_YOK]))
_t5 = {o.get("name"): o.get("tadir_deleted") for o in g(r, "inactive_objects", []) or []}
kontrol("T5 ⛔CAPA uçtan uca: 5 ad sorulur, TADIR 3 satır döner → kırpık DEĞİL, eksik 2 ad false "
        "(Q adayı davranışı AYNEN)",
        g(r, "ok") is True and g(r, "count") == 5 and len(_t5) == 5
        and all(v is False for v in _t5.values()), f"{kisa(r)} {_t5}")

r = uctan_uca(ADLAR25[:5], lambda q, n: tadir_xml(
    [(ADLAR25[0], "CLAS", "")] * min(int(n), 500)))
kontrol("T6 ⭐uçtan uca: parça yanıtı row_limit'i AŞAR (sonda satırı geldi) → 5 ad null, ok:false, KIRPILDI",
        g(r, "ok") is False and g(r, "unverified_count") == 5
        and "KIRPILDI" in str(g(r, "tadir_check")), kisa(r))

# ═══ U) Q306① — arama tip filtresi ═════════════════════════════════════════════
_u1 = {}
for _tip in ("FUNC", "FUNC/FF", "func", "function"):
    c, sap = kur()
    r = cagir(Q.adt_search_objects, FM, object_type=_tip)
    _u1[_tip] = (g(r, "count"), g(r, "object_type_sent"))
kontrol("U1 ⭐FM takma adları (FUNC · FUNC/FF · func · function) → var olan FM BULUNUR (FUGR/FF)",
        all(v == (1, "FUGR/FF") for v in _u1.values()), repr(_u1))

c, sap = kur()
r = cagir(Q.adt_search_objects, DDLS, object_type="CDS")
kontrol("U2 ⭐SENTETIK takma ad: sunucu isabeti istemci süzgecinde elenirse GÖRÜNÜR (dropped+warning)",
        g(r, "ok") is True and g(r, "count") == 0 and g(r, "type_filter_dropped") == 1
        and g(r, "server_hit_count") == 1 and "ANLAMINA GELMEZ" in str(g(r, "warning")), kisa(r))
_b = io.StringIO()
with contextlib.redirect_stdout(_b):
    try:
        _cl = c.search_objects(DDLS, 20, "CDS")
    except Exception as exc:                                  # noqa: BLE001
        _cl = repr(exc)
kontrol("U2b CLI katmanı (sap_client.search_objects) aynı elemeyi [UYARI] satırıyla basar",
        _cl == [] and "[UYARI] Sunucu 1 isabet" in _b.getvalue(), _b.getvalue()[-160:])

c, sap = kur()
r = cagir(Q.adt_search_objects, CLS, object_type="CLAS/OC")
kontrol("U3 ⛔CAPA tam ADT tipi: count:1, eleme 0, uyarı YOK",
        g(r, "count") == 1 and g(r, "type_filter_dropped") == 0 and "warning" not in (r or {}),
        kisa(r))
r = cagir(Q.adt_search_objects, FM)
kontrol("U4 ⛔CAPA tip filtresiz: count:1, object_type_sent None",
        g(r, "count") == 1 and g(r, "object_type_sent") is None and "warning" not in (r or {}),
        kisa(r))
c, sap = kur()
_fm = cagir(c.resolve_function_module, FM)
_tipler = [p.get("objectType") for m, y, p in sap.istekler if y.endswith("/search")]
kontrol("U5 ⛔CAPA resolver (Q261) DEĞİŞMEDİ: FUGR/FF sorar ve bulur",
        g(_fm, "status") == "found" and _tipler == ["FUGR/FF"], f"{_fm!r} {_tipler}")
c, sap = kur()
r = cagir(Q.adt_search_objects, FM, object_type="FUGR")
kontrol("U6 ⛔CAPA 3.BAGLAM sunucunun GERÇEK sıfırı (FUGR → 0, canlı) sessiz: eleme 0, uyarı YOK",
        g(r, "count") == 0 and g(r, "type_filter_dropped") == 0 and "warning" not in (r or {}),
        kisa(r))

# ═══ V) Q306② — where-used paket düğümleri ═════════════════════════════════════
c, sap = kur()
r = cagir(Q.adt_where_used, CLS, "class")
kontrol("V1 ⭐canlı ağaç biçimi → count:2 (ENHO + sınıf), 3 paket ayrı alanda",
        g(r, "ok") is True and g(r, "count") == 2 and g(r, "package_count") == 3
        and sorted(x["type"] for x in g(r, "references", []) or []) == ["CLAS/OC", "ENHO/XHB"],
        kisa(r))
r = cagir(Q.adt_where_used, CLS_PAKET, "class")
kontrol("V2 ⭐yalnız paket düğümü → ok:false where_used_belirsiz, count BASILMAZ",
        g(r, "ok") is False and g(r, "error") == "where_used_belirsiz" and "count" not in (r or {}),
        kisa(r))
r = cagir(Q.adt_where_used, CLS_BOS, "class")
kontrol("V3 ⛔CAPA boş ağaç → ok:true count:0 existence_verified (0 çağıran hâlâ kanıtlı)",
        g(r, "ok") is True and g(r, "count") == 0 and g(r, "existence_verified") is True, kisa(r))
c, sap = kur()
r = cagir(Q.adt_impact_analysis, CLS, "class", max_depth=2)
_post = [p.get("uri") for m, y, p in sap.istekler if m == "POST"]
kontrol("V4 ⭐impact: paketler etkilenen SAYILMAZ ve özyinelemeye GİRMEZ",
        g(r, "ok") is True and g(r, "impacted_count") == 2 and g(r, "packages_skipped") == 3
        and not any("/packages/" in str(u) for u in _post), f"{kisa(r)} post={_post}")


def cli(ad):
    c3, _s3 = kur()
    WU.SAPClient = lambda _c=c3: _c                           # type: ignore[attr-defined]
    eski_argv = sys.argv
    sys.argv = ["where_used.py", "--object-name", ad, "--object-type", "class"]
    b = io.StringIO()
    try:
        with contextlib.redirect_stdout(b):
            rc = WU.main()
    except Exception as exc:                                  # noqa: BLE001
        rc = f"ISTISNA {type(exc).__name__}"
    finally:
        sys.argv = eski_argv
    return rc, b.getvalue()


_rc, _out = cli(CLS)
kontrol("V5 ⭐CLI where_used.py: 2 kullanım sayılır, paketler sayılmaz (exit 0)",
        _rc == 0 and "Found 2 usage(s)" in _out, f"rc={_rc} {_out[-160:]!r}")
_rc, _out = cli(CLS_PAKET)
kontrol("V6 ⭐CLI yalnız paket → exit 1 + 'UNREADABLE' (0/N kullanım iddia edilmez)",
        _rc == 1 and "UNREADABLE" in _out, f"rc={_rc} {_out[-160:]!r}")

# ═══ X) Q310 — kanonik worklist ayrıştırması ════════════════════════════════════
BEKLENEN = [
    {"name": "ZCL_SD001_ORNEK_A", "type": "CLAS/OC", "uri": cls_uri("ZCL_SD001_ORNEK_A"),
     "user": "SAP_USER_A", "deleted": False, "transport": ""},
    {"name": "ZCL_SD001_ORNEK_B", "type": "CLAS/OC", "uri": cls_uri("ZCL_SD001_ORNEK_B"),
     "user": "SAP_USER_A", "deleted": False, "transport": ""},
    {"name": "ZSD001_FM_ORNEK", "type": "FUGR/F", "uri": "/sap/bc/adt/functions/groups/zsd001_fm_ornek",
     "user": "SAP_USER_A", "deleted": False, "transport": ""},
    {"name": "ZSD001_FM_ORNEK", "type": "FUGR/FF", "uri": fm_uri("ZSD001_FM_ORNEK", "ZSD001_FM_ORNEK"),
     "user": "SAP_USER_A", "deleted": False, "transport": "SAHK900002"},
]
_ALAN = ("name", "type", "uri", "user", "deleted", "transport")

_k = cagir(L.aktivasyon_worklist_ayristir, AYNI_AD)
_ff = [x for x in _k if isinstance(x, dict) and x.get("type") == "FUGR/FF"] if isinstance(_k, list) else []
_om = [x for x in _k if isinstance(x, dict) and x.get("type") == "CLAS/OM"] if isinstance(_k, list) else []
kontrol("X1 ⭐kanonik ayrıştırıcı user/deleted/transport üretir (canlı aynı-ad gövde; eski 4 alan aynen)",
        isinstance(_k, list) and len(_k) == 6 and len(_ff) == 1
        and (_ff[0].get("user"), _ff[0].get("deleted"), _ff[0].get("transport"))
        == ("SAP_USER_A", False, "SAHK900002")
        and _ff[0].get("parent_uri") == "/sap/bc/adt/functions/groups/zsd001_fm_ornek"
        and all(o.get("transport") == "SAHK900001" for o in _om), repr(_ff)[:200])

_wa = cagir(WA._parse_entries, AYNI_AD)
kontrol("X2 ⛔CAPA worklist_audit listesi DEĞİŞMEDİ (aynı-ad F ve FF AYRI, OM/transport girdisi yok)",
        _wa == BEKLENEN, repr(_wa)[:230])
r = inaktif(AYNI_AD, tadir_emul(sinir=100)[0])
_mcp = [{k: o.get(k) for k in _ALAN} for o in g(r, "inactive_objects", []) or []]
kontrol("X3 ⛔CAPA MCP adt_inactive_objects AYNI listeyi verir (iki yol = kanonik)",
        g(r, "ok") is True and _mcp == BEKLENEN, f"{kisa(r)} {_mcp!r}"[:230])

_asil_ayr = L.aktivasyon_worklist_ayristir
_nobet = [{"name": "ZCL_SD001_NOBETCI", "type": "CLAS/OC", "uri": cls_uri("ZCL_SD001_NOBETCI"),
           "parent_uri": "", "user": "SAP_USER_N", "deleted": False, "transport": ""}]
L.aktivasyon_worklist_ayristir = lambda govde: [dict(x) for x in _nobet]  # type: ignore[assignment]
try:
    _wa_n = cagir(WA._parse_entries, AYNI_AD)
    r = inaktif(AYNI_AD, tadir_emul(sinir=100)[0])
finally:
    L.aktivasyon_worklist_ayristir = _asil_ayr                # type: ignore[assignment]
kontrol("X4 ⭐KABLOLAMA: kanonik fonksiyon değişince İKİ yol da onu izler (kopya ayrıştırıcı YOK)",
        [x.get("name") for x in (_wa_n or [])] == ["ZCL_SD001_NOBETCI"]
        and [o.get("name") for o in g(r, "inactive_objects", []) or []] == ["ZCL_SD001_NOBETCI"],
        f"wa={_wa_n!r} mcp={kisa(r)}"[:230])

r = inaktif("<root/>", tadir_emul(sinir=100)[0])
_wa = cagir(WA._parse_entries, "<root/>")
kontrol("X5 ⭐SIKILASTIRMA ioc olmayan 200 gövde: MCP ok:false (count YOK) · worklist_audit None",
        g(r, "ok") is False and g(r, "error") == "worklist_govdesi_degil" and "count" not in (r or {})
        and _wa is None, f"{kisa(r)} wa={_wa!r}")
_html = "<html><body>Logon</body></html"
r = inaktif(_html, tadir_emul(sinir=100)[0])
_wa = cagir(WA._parse_entries, _html)
kontrol("X6 ⛔CAPA bozuk/HTML gövde: MCP ok:false · worklist_audit None (davranış AYNEN)",
        g(r, "ok") is False and _wa is None, f"{kisa(r)} wa={_wa!r}")

# ── RAPOR ──────────────────────────────────────────────────────────────────────────
kip_etiketi = " ".join(_kipler) or (f"TABAN({TABAN})" if TABAN else "yeni kod")
print(f"sorgu_araclari_durustlugu — kip: {kip_etiketi}")
for ad, ok, detay in SONUC:
    print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {detay}"))
gecen = sum(1 for _a, ok, _d in SONUC if ok)
print(f"{gecen}/{len(SONUC)} OK")
print(f"SONUC: {gecen}/{len(SONUC)} PASS")
print("KAPSAM: bakilmayan = gercek SAP · MCP SDK aciklama uretimi · TADIR'da satiri olmayan ad "
      "(Q adayi) · where_used.py alt-surec · 500 ardindan Session Timed Out 400")
sys.exit(0 if gecen == len(SONUC) else 1)
