"""Query tools — read-only.

- adt_search_objects  : Search by name/wildcard, optional type filter
- adt_transport_list  : List modifiable transports for current user
- adt_lock_check      : Probe whether an object is currently locked

All return structured JSON; never write to SAP.
"""
from __future__ import annotations

import contextlib
import io
import re
from typing import Any

from mcp_servers.sap_adt._app import mcp, log, profil_tool


def _get_client():
    from mcp_servers.sap_adt.tools.atom import _get_client as _g
    return _g()


def _err_from_exc(exc: Exception) -> dict:
    from mcp_servers.sap_adt.tools.atom import _err_from_exc as _e
    return _e(exc)


@contextlib.contextmanager
def _capture():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


# =============================================================================
# adt_search_objects
# =============================================================================

@profil_tool()
def adt_search_objects(
    query: str,
    max_results: int = 50,
    object_type: str | None = None,
) -> dict:
    """Search SAP objects by name/wildcard.

    Args:
        query: Search query — wildcards allowed (e.g., 'ZSD001*', 'ZSD000_E_*').
        max_results: Cap on results (default 50, max recommended 500).
        object_type: Optional ADT type filter ('CLAS', 'INTF', 'DOMA', 'DTEL', 'TABL', 'DDLS', 'PROG').

    Returns:
        {ok, count, results: [{name, type, uri, description}, ...], query, client_log}
    """
    client = _get_client()
    try:
        with _capture() as buf:
            results = client.search_objects(
                query=query,
                max_results=max_results,
                obj_type=object_type,
            )
        return {
            "ok": True,
            "query": query,
            "object_type": object_type,
            "count": len(results),
            "results": results,
            "client_log": buf.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_transport_list
# =============================================================================

@profil_tool(("ecc", "s4_private", "s4_public"))  # btp_abap: transport=gcts -> CTS ucu yok
def adt_transport_list(user: str | None = None) -> dict:
    """List a user's transport requests (modifiable + released).

    Use this BEFORE create/modify operations to confirm the correct transport ID.
    Never invent a transport — always pick one from this list and verify with the user.

    Args:
        user: SAP user name. Defaults to the .conn_adt user.

    Returns:
        {ok, count, transports: [{number, description, status}, ...], client_log}
    """
    client = _get_client()
    try:
        with _capture() as buf:
            transports = client.list_user_transports(user=user)
        return {
            "ok": True,
            "user": user,
            "count": len(transports),
            "transports": transports,
            "client_log": buf.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_where_used  (gap-analysis #10)
# =============================================================================

@profil_tool()
def adt_where_used(name: str, object_type: str = "class") -> dict:
    """Where-used: bir Z objeyi referanslayan objeleri listele (read-only).

    Etki analizi + SİLMEDEN ÖNCE kullanım kontrolü (ADR 0005 / #3 reuse-gate eş).
    Standart ADT usageReferences endpoint'i kullanır; SAP'ye YAZMAZ.

    Args:
        name: Obje adı (Z*/Y* veya standart — okuma serbest).
        object_type: ADT tipi ('class', 'ddls', 'dtel', 'doma', 'tabl', 'intf', 'prog', ...).

    Returns:
        {ok, name, type, count, references: [{name, type, uri, description}], client_log}
        Obje YOKSA: {ok: false, error_code: "OBJECT_NOT_FOUND", ...} — count DÖNMEZ.

    Gate (T11): SAP, silinmiş obje için de usageReferences'ta 200 + boş liste döner.
    "count=0" sorusu "tüketicisi yok mu?" ile "obje yok mu?" ayrımını YAPAMAZ — bu
    ayrım orphan-sweep'te yanlış silmeye yol açar. Varlık önce doğrulanır; obje yoksa
    count HİÇ dönmez ki çağıran onu 0 sanmasın.
    """
    client = _get_client()
    try:
        from object_types import get_object_url  # type: ignore

        with _capture() as buf:
            if not client.object_exists(name.upper(), object_type):
                return {
                    "ok": False,
                    "error_code": "OBJECT_NOT_FOUND",
                    "name": name,
                    "type": object_type,
                    "hint": (
                        f"{name} ({object_type}) SAP'de yok. where_used bos liste "
                        f"donerdi; bunu 'tuketicisi yok' diye okuma."
                    ),
                    "client_log": buf.getvalue().strip(),
                }
            url = get_object_url(name.upper(), object_type)
            refs = client.adt_client.where_used(url)
        return {
            "ok": True,
            "name": name,
            "type": object_type,
            "count": len(refs) if hasattr(refs, "__len__") else 0,
            "references": refs,
            "client_log": buf.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_atc_check  (gap-analysis #10)
# =============================================================================

@profil_tool()
def adt_atc_check(name: str, object_type: str = "class",
                  variant: str | None = None, max_verdicts: int = 100) -> dict:
    """ATC statik kod kontrolü (Clean ABAP / performans / güvenlik) — read-only.

    Reviewer'ı (ADR 0006) tamamlar; SAP'ye YAZMAZ. Bulgular severity'li döner.

    Args:
        name: Obje adı (Z*/Y*).
        object_type: ADT tipi ('class', 'ddls', 'prog', ...).
        variant: ATC check variant. None ise .conn_adt ADT_ATC_VARIANT'tan okunur
                 (sisteme özgü, ör. ZZNDBS_ATC); o da yoksa 'DEFAULT'.
        max_verdicts: Maks bulgu sayısı.

    Returns:
        {ok, name, type, variant, finding_count, findings: [...], client_log}
    """
    client = _get_client()
    try:
        if variant is None:
            from mcp_servers.sap_adt._conn import get_atc_variant
            variant = get_atc_variant()
        from object_types import get_object_url  # type: ignore
        url = get_object_url(name.upper(), object_type)
        with _capture() as buf:
            res = client.adt_client.run_atc_check(url, variant=variant, max_verdicts=max_verdicts)
        findings = res.get("findings", []) if isinstance(res, dict) else (res or [])

        # Proje kuralı (kullanıcı, T3): YALNIZCA Priority 1 ZORUNLU düzeltilir;
        # Priority 2/3 kullanıcının açık onayıyla pass geçilebilir.
        def _prio(f):
            return str((f or {}).get("priority", "")).strip()
        prio1 = [f for f in findings if _prio(f) == "1"]
        prio_other = [f for f in findings if _prio(f) not in ("1", "")]
        return {
            "ok": True,
            "name": name,
            "type": object_type,
            "variant": variant,
            "finding_count": len(findings),
            "priority_1_count": len(prio1),          # ZORUNLU düzelt
            "other_priority_count": len(prio_other),  # kullanıcı onayıyla pass
            "must_fix": len(prio1) > 0,
            "policy": ("Priority 1 ZORUNLU düzeltilir; Priority 2/3 yalnızca kullanıcının "
                       "açık onayıyla pass geçilebilir (proje kuralı)."),
            "findings": findings,
            "client_log": buf.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_syntax_check  (gap-analysis #10)
# =============================================================================

@profil_tool()
def adt_syntax_check(name: str, object_type: str = "class") -> dict:
    """Sözdizimi kontrolü (aktivasyon pre-audit) — aktive ETMEDEN. read-only.

    SAP'deki inactive sürümü kontrol eder; push-before-activate akışında aktivasyon
    hatası/patinajını (ADR 0006/T10) önceden yakalar.

    Args:
        name: Obje adı (Z*/Y*).
        object_type: ADT tipi ('class', 'ddls', 'prog', ...).

    Returns:
        {ok, name, type, valid, errors: [...], warnings: [...], client_log}
    """
    client = _get_client()
    try:
        with _capture() as buf:
            res = client.syntax_check(name, object_type=object_type)
        return {
            "ok": True,
            "name": name,
            "type": object_type,
            "valid": bool(res.get("valid")) if isinstance(res, dict) else None,
            "errors": res.get("errors", []) if isinstance(res, dict) else [],
            "warnings": res.get("warnings", []) if isinstance(res, dict) else [],
            "client_log": buf.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_package_contents  (gap-analysis #10)
# =============================================================================

@profil_tool()
def adt_package_contents(package: str) -> dict:
    """Bir paketin içeriğini (objeleri) listele — read-only.

    Args:
        package: Paket adı (ör. 'ZSD001_CLC').

    Returns:
        {ok, package, count, objects: [{name, type, uri, ...}], client_log}
    """
    client = _get_client()
    try:
        with _capture() as buf:
            objs = client.list_package_contents(package)
        return {
            "ok": True,
            "package": package,
            "count": len(objs) if hasattr(objs, "__len__") else 0,
            "objects": objs,
            "client_log": buf.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_table_read  (gap-analysis #10 + #2 PII guard, ADR 0011)
# =============================================================================

@profil_tool()
def adt_table_read(
    table: str,
    row_limit: int = 100,
    columns: str | list | None = None,
    acknowledge_risk: bool = False,
    approval_text: str | None = None,
) -> dict:
    """Tablo verisi oku (ADT data preview). ⚠️ ADR 0011 PII guard'a tabi.

    DEV tier: serbest. QA/PRD tier: hassas tablo/alan (KNA1/PA*/banka/TCKN...) için
    acknowledge_risk=True + açık onay kelimesi ('onay'/'approve'/'proceed') ZORUNLU;
    muğlak ifade yetmez (KVKK — ADR 0011).

    ⚠️ HİZALAMA: Satırlar `data.rows_labeled` ([{KOLON: değer}, ...]) olarak döner —
    kolon-adı→değer eşlemeli (hizalama-güvenli). Ham POZİSYONEL `data.data` dizisi (kolon-adı
    içermez, gözle-hizalamada off-by-one'a açıktı — ders 2026-06-22 DORIT.BATCH, üst üste 3 kez
    ısırdı) etiketleme BAŞARILI olduğunda çıktıdan KALDIRILIR; alan değerini DAİMA
    `rows_labeled`'dan oku. (Kolon listesi alınamayan nadir durumda pozisyonel `data.data`
    korunur — veri kaybı olmasın.) Tek/birkaç kolon yeterliyse `columns` ver → SELECT daralır.

    Args:
        table: Tablo adı (ör. 'ZSD001_T_BOOKHD', 'T000').
        row_limit: Maks satır (default 100).
        columns: İstenen kolon(lar) — "BATCH,HU_IDENT" (virgüllü str) veya liste. None → SELECT *.
        acknowledge_risk: QA/PRD'de hassas veri için açık risk-kabulü.
        approval_text: Onay metni (affirmative kelime içermeli).

    Returns:
        {ok, table, data, client_log} veya guardrail_violation (QA/PRD hassas, onaysız).
        data.rows_labeled: [{KOLON: değer}, ...] (hizalama-güvenli; satırları BURADAN oku).
        data.columns: kolon adları (referans). data.data (pozisyonel) etiketleme başarılıysa kaldırılır.
    """
    from mcp_servers.sap_adt._conn import get_active_tier
    from mcp_servers.sap_adt.data_guard import require_data_access
    from mcp_servers.sap_adt.guardrails import GuardrailViolation
    try:
        require_data_access(
            get_active_tier(), table,
            acknowledge_risk=acknowledge_risk, approval_text=approval_text,
        )
    except GuardrailViolation as gv:
        return gv.as_dict()

    # İstenen kolonları normalize et (str "A,B" veya liste) → daraltılmış SELECT (off-by-one'sız).
    col_list = None
    if columns:
        raw = columns.split(",") if isinstance(columns, str) else list(columns)
        col_list = [str(c).strip().upper() for c in raw if str(c).strip()]
    select_cols = ", ".join(col_list) if col_list else "*"

    client = _get_client()
    try:
        # run_sql_query (table_contents deprecated). OSQL — sadece OKUMA (SELECT).
        with _capture() as buf:
            data = client.run_sql_query(
                f"SELECT {select_cols} FROM {table.upper()}", max_rows=row_limit)
        # Kolon-adı→değer eşlemeli görünüm — pozisyonel diziyi gözle hizalama off-by-one'ını
        # yapısal olarak önler (ders 2026-06-22 DORIT.BATCH/HU_IDENT karıştırma).
        try:
            if isinstance(data, dict):
                cols = data.get("columns")
                rows = data.get("data")
                if cols and isinstance(rows, list):
                    data["rows_labeled"] = [dict(zip(cols, r)) for r in rows]
                    # Footgun kaldır: etiketleme başarılıysa ham POZİSYONEL diziyi çıktıdan SÖK
                    # → gözle-hizalama off-by-one imkânsızlaşır (ders 2026-06-22 DORIT.BATCH).
                    # `columns` referans için kalır. Kolon alınamazsa (nadir) bu blok atlanır →
                    # pozisyonel `data` KORUNUR (veri kaybı olmasın).
                    data.pop("data", None)
                    data["_note"] = ("Satırları 'rows_labeled' ([{KOLON: değer}]) listesinden okuyun; "
                                     "ham pozisyonel 'data' dizisi footgun olduğu için kaldırıldı.")
        except Exception:
            pass  # etiketleme best-effort; ham veri her hâlükârda döner
        return {
            "ok": True,
            "table": table,
            "row_limit": row_limit,
            "data": data,
            "client_log": buf.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_sql_query  (WHERE-filtreli serbest SELECT — ADT Data Preview freestyle)
# =============================================================================
_SQL_WRITE_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MODIFY|DROP|CREATE|ALTER|TRUNCATE|MERGE|UPSERT|"
    r"COMMIT|ROLLBACK|CALL|EXEC|GRANT|REVOKE|LOCK)\b", re.IGNORECASE)


@profil_tool()
def adt_sql_query(
    query: str,
    row_limit: int = 100,
    acknowledge_risk: bool = False,
    approval_text: str | None = None,
) -> dict:
    """WHERE/JOIN/aggregate destekli serbest OpenSQL **SELECT** çalıştır — READ-ONLY.

    `adt_table_read` yalnız `SELECT * FROM tablo` yapar (WHERE yok); bu tool ADT Data
    Preview freestyle (`/datapreview/freestyle`) ile tam OpenSQL SELECT'i koşar:
    WHERE, JOIN, GROUP BY, COUNT/SUM. INTO/UP TO **YAZMA** — SAP kendi ekler.

    Guard'lar:
      • **SELECT-only (ADR 0005-B):** SELECT/WITH ile başlamalı; yazma/DDL keyword'ü
        (INSERT/UPDATE/DELETE/MODIFY/DROP/...) tespit edilirse REDDEDİLİR. (Data Preview
        zaten server-side salt-okuma; bu tool-seviyesi ikinci katman.)
      • **PII (ADR 0011):** FROM/JOIN tabloları çıkarılır; DEV serbest, QA/PRD'de hassas
        tablo (KNA1/PA*/banka/TCKN...) için `acknowledge_risk=True` + onay kelimesi ZORUNLU.

    Args:
        query: OpenSQL SELECT. Ör: "SELECT msgnr, text FROM t100 WHERE arbgb = 'ZSD001' AND sprsl = 'T'".
        row_limit: Maks satır (default 100).
        acknowledge_risk / approval_text: QA/PRD hassas-tablo için (ADR 0011).

    Returns:
        {ok, query, row_count, columns, rows: [{KOLON: değer}, ...], executed?, client_log}
        veya {ok: false, error, message} (SELECT-değil / yazma-keyword) veya guardrail_violation.
        Satırları DAİMA `rows`'tan oku (kolon-adı→değer eşlemeli; hizalama-güvenli).
    """
    q = (query or "").strip().rstrip(";").strip()
    low = q.lstrip("( \t\n").lower()
    if not (low.startswith("select") or low.startswith("with")):
        return {"ok": False, "error": "not_select",
                "message": "Yalnız SELECT/WITH sorgusu kabul edilir (WHERE/JOIN/aggregate). "
                           "Yazma/DDL reddedilir (ADR 0005-B)."}
    # String-literalleri sök → literal içindeki keyword yanlış-pozitif reddetmesin.
    q_nolit = re.sub(r"'[^']*'", "''", q)
    if _SQL_WRITE_RE.search(q_nolit):
        return {"ok": False, "error": "write_keyword",
                "message": "Yazma/DDL/işlem keyword'ü tespit edildi — REDDEDİLDİ (ADR 0005-B). "
                           "Bu tool yalnız salt-okuma SELECT içindir."}

    from mcp_servers.sap_adt._conn import get_active_tier
    from mcp_servers.sap_adt.data_guard import require_data_access
    from mcp_servers.sap_adt.guardrails import GuardrailViolation
    tables = {t.upper() for t in re.findall(
        r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_/]*)", q_nolit, re.IGNORECASE)}
    try:
        for t in sorted(tables):
            require_data_access(get_active_tier(), t,
                                acknowledge_risk=acknowledge_risk, approval_text=approval_text)
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    try:
        with _capture() as buf:
            data = client.run_sql_query(q, max_rows=row_limit)
        cols = data.get("columns") if isinstance(data, dict) else None
        rows = data.get("data") if isinstance(data, dict) else None
        rows_labeled = ([dict(zip(cols, r)) for r in rows]
                        if (cols and isinstance(rows, list)) else rows)
        return {
            "ok": True,
            "query": q,
            "tables": sorted(tables),
            "executed": data.get("executedQueryString") if isinstance(data, dict) else None,
            "columns": cols,
            "row_count": len(rows) if isinstance(rows, list) else 0,
            "rows": rows_labeled,
            "client_log": buf.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_dump_list  (ST22 ABAP short-dump feed — runtime hata teşhisi)
# =============================================================================
_ATOM_NS = "http://www.w3.org/2005/Atom"


@profil_tool()
def adt_dump_list(limit: int = 20, from_ts: str | None = None, to_ts: str | None = None) -> dict:
    """ST22 ABAP kısa-dump (short dump) feed'ini oku — READ-ONLY.

    RAP/UI/classrun çalıştırmalarında runtime 500/kısa-dump kök-neden teşhisi (SAP GUI'siz).
    `GET /sap/bc/adt/runtime/dumps` (Accept `application/atom+xml;type=feed`) → Atom feed parse.

    Args:
        limit: Döndürülecek maks dump (default 20; feed en yeni→eski).
        from_ts / to_ts: Opsiyonel zaman penceresi (feed'in `from`/`to` param'ı; ör. '20260710154122').

    Returns:
        {ok, count, dumps: [{error_type, program, user, timestamp, title, id, dump_uri}], client_log}
        `dump_uri` = tek dumpın ADT detay URI'si (sonra detay çekmek için).
    """
    import xml.etree.ElementTree as ET
    client = _get_client()
    try:
        adt = getattr(client, "adt_client", None) or client
        params: dict = {}
        if from_ts:
            params["from"] = from_ts
        if to_ts:
            params["to"] = to_ts
        with _capture() as buf:
            r = adt.session.get(
                adt.url + "/sap/bc/adt/runtime/dumps", params=params,
                headers={"Accept": "application/atom+xml;type=feed"}, verify=False, timeout=60)
        if r.status_code != 200:
            return {"ok": False, "error": "http_%d" % r.status_code,
                    "message": (r.text or "")[:400], "client_log": buf.getvalue().strip()}
        root = ET.fromstring(r.text)
        dumps = []
        for e in root.findall("{%s}entry" % _ATOM_NS):
            if len(dumps) >= limit:
                break
            cats = e.findall("{%s}category" % _ATOM_NS)

            def _cat(lbl, _cats=cats):
                for c in _cats:
                    if c.get("label") == lbl:
                        return c.get("term")
                return None

            author = e.find("{%s}author/{%s}name" % (_ATOM_NS, _ATOM_NS))
            updated = e.find("{%s}updated" % _ATOM_NS)
            idel = e.find("{%s}id" % _ATOM_NS)
            title = e.find("{%s}title" % _ATOM_NS)
            dump_uri = None
            for lnk in e.findall("{%s}link" % _ATOM_NS):
                if "/runtime/dump/" in (lnk.get("href") or ""):
                    dump_uri = lnk.get("href")
                    break
            dumps.append({
                "error_type": _cat("ABAP runtime error"),
                "program": _cat("Terminated ABAP program"),
                "user": author.text if author is not None else None,
                "timestamp": updated.text if updated is not None else None,
                "title": title.text if title is not None else None,
                "id": idel.text if idel is not None else None,
                "dump_uri": dump_uri,
            })
        return {"ok": True, "count": len(dumps), "dumps": dumps, "client_log": buf.getvalue().strip()}
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_inactive_objects  (aktive-bekleyen worklist — worklist_audit MCP-native)
# =============================================================================
_IOC_NS = {"ioc": "http://www.sap.com/abapxml/inactiveCtsObjects",
           "adtcore": "http://www.sap.com/adt/core"}


@profil_tool()
def adt_inactive_objects() -> dict:
    """Aktive-bekleyen (inactive) obje worklist'ini oku — READ-ONLY.

    `scripts/worklist_audit.py`'nin MCP-native karşılığı. Gün-sonu/commit-öncesi "aktive
    edilmemiş obje var mı" kontrolü tek çağrıya iner. `GET /sap/bc/adt/activation/inactiveobjects`.

    Returns:
        {ok, count, inactive_objects: [{name, type, uri, user}], client_log}
        count=0 → aktive-bekleyen ana obje yok (transport/method-seviyesi girdiler elenir).
    """
    import xml.etree.ElementTree as ET
    client = _get_client()
    try:
        adt = getattr(client, "adt_client", None) or client
        with _capture() as buf:
            r = adt.session.get(adt.url + "/sap/bc/adt/activation/inactiveobjects",
                                headers={"Accept": "application/*"}, verify=False, timeout=45)
        if r.status_code != 200:
            return {"ok": False, "error": "http_%d" % r.status_code,
                    "message": (r.text or "")[:300], "client_log": buf.getvalue().strip()}
        root = ET.fromstring(r.text)
        out, seen = [], set()
        for entry in root.findall("ioc:entry", _IOC_NS):
            obj = entry.find("ioc:object", _IOC_NS)
            if obj is None:
                continue
            ref = obj.find("ioc:ref", _IOC_NS)
            if ref is None:
                continue  # transport-seviyesi (boş object)
            a_type = ref.get("{%s}type" % _IOC_NS["adtcore"], "") or ""
            a_name = ref.get("{%s}name" % _IOC_NS["adtcore"], "") or ""
            a_uri = ref.get("{%s}uri" % _IOC_NS["adtcore"], "") or ""
            if a_type.endswith("/OM") or "#type=" in a_uri:
                continue  # method/sub-obje → ana obje girdisi var
            key = a_uri.split("#")[0].rstrip("/")
            if not a_name or key in seen:
                continue
            seen.add(key)
            out.append({"name": a_name.strip(), "type": a_type, "uri": key,
                        "user": obj.get("{%s}user" % _IOC_NS["ioc"], "") or ""})
        return {"ok": True, "count": len(out), "inactive_objects": out,
                "client_log": buf.getvalue().strip()}
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_enhancements  (bir objedeki enhancement/BAdI implementasyonları — legacy analiz)
# =============================================================================
_ENH_NS = {"enh": "http://www.sap.com/adt/abapsource/enhancements",
           "adtcore": "http://www.sap.com/adt/core"}
_ENH_SEG = {"program": "programs/programs", "prog": "programs/programs",
            "class": "oo/classes", "clas": "oo/classes",
            "include": "programs/includes", "incl": "programs/includes",
            "functiongroup": "functions/groups", "fugr": "functions/groups"}


@profil_tool()
def adt_enhancements(name: str, object_type: str = "program", include_source: bool = False) -> dict:
    """Bir objeye BAĞLI enhancement implementasyonlarını (implicit/explicit source enh.) oku — READ-ONLY.

    ECC/legacy davranış analizinde std koda NE enjekte edilmiş + NEREYE görmek. Her impl'in
    enjeksiyon SİTE'lerini (full_name = enhancement-point yolu, position, mode/replacing) ve
    `include_source=True` ise base64-çözülmüş enjekte kaynağı verir. `.../source/main/enhancements/elements`.
    Std obje OKUR, DEĞİŞTİRMEZ (ADR 0005 temiz).

    Args:
        name: Obje adı. object_type: 'program'|'class'|'include'|'functiongroup'.
        include_source: True → her site'ın enjekte-kaynağını (base64→utf8) dahil et (büyük olabilir).

    Returns:
        {ok, name, exists, count, enhancements: [{name, type, version, enhanced_object,
         sites: [{full_name, mode, replacing, impl_uri, position_uri, source?}]}], client_log}
        (ENHO tipleri objeye-bağlı; `adt_enhancement_read` ile impl kaynağını isimle de çekebilirsiniz.)
    """
    import xml.etree.ElementTree as ET
    import base64
    seg = _ENH_SEG.get((object_type or "").lower().strip())
    if not seg:
        return {"ok": False, "error": "unsupported_type",
                "message": "object_type: program|class|include|functiongroup"}
    _E = "{%s}" % _ENH_NS["enh"]
    _A = "{%s}" % _ENH_NS["adtcore"]
    client = _get_client()
    try:
        adt = getattr(client, "adt_client", None) or client
        from urllib.parse import quote
        url = (adt.url + "/sap/bc/adt/" + seg + "/" + quote(name.lower(), safe="")
               + "/source/main/enhancements/elements")
        with _capture() as buf:
            r = adt.session.get(url, headers={"Accept": "application/vnd.sap.adt.enhancements.v3+xml"},
                                verify=False, timeout=45)
        if r.status_code == 404:
            return {"ok": True, "name": name.upper(), "exists": False, "count": 0,
                    "enhancements": [], "client_log": buf.getvalue().strip()}
        if r.status_code != 200:
            return {"ok": False, "error": "http_%d" % r.status_code,
                    "message": (r.text or "")[:300], "client_log": buf.getvalue().strip()}
        root = ET.fromstring(r.text)
        out = []
        for impl in root.iter(_E + "enhancementImplementations"):
            eobj = impl.find(".//" + _E + "enhancedObject")
            sites = []
            for scp in impl.iter(_E + "sourceCodePlugin"):
                pos = scp.find(".//" + _E + "position")
                site = {
                    "full_name": scp.get(_E + "full_name", ""),
                    "mode": scp.get(_E + "mode", ""),
                    "replacing": scp.get(_E + "replacing", ""),
                    "impl_uri": scp.get(_E + "uri", ""),
                    "position_uri": pos.get(_A + "uri", "") if pos is not None else "",
                }
                if include_source:
                    src_el = scp.find(_E + "source")
                    if src_el is not None and src_el.text:
                        try:
                            site["source"] = base64.b64decode(src_el.text).decode("utf-8", "replace")
                        except Exception:  # noqa: BLE001
                            site["source"] = None
                sites.append(site)
            out.append({
                "name": impl.get(_A + "name", ""),
                "type": impl.get(_A + "type", ""),
                "version": impl.get(_A + "version", ""),
                "enhanced_object": eobj.get(_A + "name", "") if eobj is not None else "",
                "sites": sites,
            })
        return {"ok": True, "name": name.upper(), "exists": True, "count": len(out),
                "enhancements": out, "client_log": buf.getvalue().strip()}
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_enhancement_read  (ENHO/BAdI-impl kaynağını İSİMLE oku)
# =============================================================================
_ENHO_TYPE_SEG = {"enhoxhh": "enhancements/enhoxhh", "enhoxh": "enhancements/enhoxh",
                  "enhoxhb": "enhancements/enhoxhb"}


@profil_tool()
def adt_enhancement_read(name: str, enh_type: str = "enhoxhh") -> dict:
    """Bir ENHO/BAdI-impl objesinin ham ABAP kaynağını İSİMLE oku — READ-ONLY.

    `adt_enhancements`'in verdiği impl adını tam kaynağa çevirir (legacy davranış analizinin
    ikinci yarısı). `.../enhancements/{enh_type}/{name}/source/main`.

    Args:
        name: ENHO obje adı (namespaced ise '/NS/...' URL-encode edilir). enh_type:
              'enhoxhh' (source-plugin) | 'enhoxh' (impl) | 'enhoxhb' (BAdI impl).

    Returns:
        {ok, name, type, exists, source, client_log}
    """
    from mcp_servers.sap_adt.tools.atom import _read_source_object
    seg = _ENHO_TYPE_SEG.get((enh_type or "").lower().strip())
    if not seg:
        return {"ok": False, "error": "unsupported_type", "message": "enh_type: enhoxhh|enhoxh|enhoxhb"}
    return _read_source_object(name, seg, enh_type.lower())


# =============================================================================
# adt_enhancement_options  (obje HANGİ exit/point/spot'u SUNUYOR — ⚠ devasa yanıt)
# =============================================================================
_ENHO_OPT_NS = {"enho": "http://www.sap.com/adt/enhancementOptions/enho",
                "enhocore": "http://www.sap.com/abapsource/enhancementscore",
                "atom": "http://www.w3.org/2005/Atom"}


@profil_tool()
def adt_enhancement_options(name: str, object_type: str = "program",
                            name_filter: str | None = None, max_results: int = 100) -> dict:
    """Bir objenin SUNDUĞU enhancement option'ları (exit/point/BAdI) listele — READ-ONLY.

    "Bu program/FG nereden genişletilebilir / nereye enjekte edilebilir" haritası.
    `.../enhancements/options`. ⚠ Yanıt DEVASA olabilir (MB'larca) → `name_filter` + `max_results`
    ile daralt. Std obje OKUR, DEĞİŞTİRMEZ (ADR 0005 temiz).

    Args:
        name: Obje adı. object_type: 'program'|'class'|'include'|'functiongroup'.
        name_filter: Yalnız full_name'inde bu metin geçen option'lar (ör. 'EX:' exit'ler).
        max_results: Döndürülecek maks option (default 100).

    Returns:
        {ok, name, matched, returned, truncated, options: [{full_name, description, mode,
         source_link}], client_log}
    """
    import xml.etree.ElementTree as ET
    seg = _ENH_SEG.get((object_type or "").lower().strip())
    if not seg:
        return {"ok": False, "error": "unsupported_type",
                "message": "object_type: program|class|include|functiongroup"}
    _O = "{%s}" % _ENHO_OPT_NS["enho"]
    _OC = "{%s}" % _ENHO_OPT_NS["enhocore"]
    _AT = "{%s}" % _ENHO_OPT_NS["atom"]
    client = _get_client()
    try:
        adt = getattr(client, "adt_client", None) or client
        from urllib.parse import quote
        url = (adt.url + "/sap/bc/adt/" + seg + "/" + quote(name.lower(), safe="")
               + "/enhancements/options")
        with _capture() as buf:
            r = adt.session.get(
                url, headers={"Accept": "application/vnd.sap.adt.enhancementoptions.v2+xml"},
                verify=False, timeout=90)
        if r.status_code == 404:
            return {"ok": True, "name": name.upper(), "matched": 0, "returned": 0,
                    "options": [], "client_log": buf.getvalue().strip()}
        if r.status_code != 200:
            return {"ok": False, "error": "http_%d" % r.status_code,
                    "message": (r.text or "")[:300], "client_log": buf.getvalue().strip()}
        root = ET.fromstring(r.text)
        matched, opts = 0, []
        flt = name_filter.lower() if name_filter else None
        for opt in root.iter(_O + "option"):
            fn = opt.get(_OC + "full_name", "")
            if flt and flt not in fn.lower():
                continue
            matched += 1
            if len(opts) < max_results:
                link = opt.find(_AT + "link")
                opts.append({
                    "full_name": fn,
                    "description": opt.get(_O + "fullDescription", ""),
                    "mode": opt.get(_O + "mode", ""),
                    "source_link": link.get("href") if link is not None else None,
                })
        return {"ok": True, "name": name.upper(), "matched": matched, "returned": len(opts),
                "truncated": matched > len(opts), "options": opts,
                "client_log": buf.getvalue().strip()}
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_feature_probe  (ADT sunucu yetenek keşfi — statik profil matrisini canlı-kanıta çevirir)
# =============================================================================
_APP_NS = "http://www.w3.org/2007/app"


@profil_tool()
def adt_feature_probe(filter: str | None = None) -> dict:
    """ADT sunucu yetenek keşfi (discovery) — hangi ADT collection'ları/yetenekleri MEVCUT. READ-ONLY.

    `profiles/` matrisimiz "rehberdir, kanıt değildir" (D34d) — bu tool onu CANLI-kanıta çevirir:
    sistemde hangi ADT yetenek uçları (RAP generator, BOPF, abapGit, datapreview, atc...) açık.
    `GET /sap/bc/adt/discovery` (Atom service doc) parse.

    Args:
        filter: Opsiyonel — yalnız title/href/workspace'inde bu metin geçen collection'lar.

    Returns:
        {ok, collection_count, collections: [{workspace, title, href}], client_log}
    """
    import xml.etree.ElementTree as ET
    client = _get_client()
    try:
        adt = getattr(client, "adt_client", None) or client
        with _capture() as buf:
            r = adt.session.get(adt.url + "/sap/bc/adt/discovery",
                                headers={"Accept": "application/atomsvc+xml"}, verify=False, timeout=60)
        if r.status_code != 200:
            return {"ok": False, "error": "http_%d" % r.status_code,
                    "message": (r.text or "")[:300], "client_log": buf.getvalue().strip()}
        root = ET.fromstring(r.text)
        flat = []
        for ws in root.findall("{%s}workspace" % _APP_NS):
            wt = ws.find("{%s}title" % _ATOM_NS)
            ws_title = wt.text if wt is not None else None
            for col in ws.findall("{%s}collection" % _APP_NS):
                ct = col.find("{%s}title" % _ATOM_NS)
                flat.append({"workspace": ws_title,
                             "title": ct.text if ct is not None else None,
                             "href": col.get("href")})
        if filter:
            fl = filter.lower()
            flat = [x for x in flat if any(fl in (x.get(k) or "").lower()
                                           for k in ("title", "href", "workspace"))]
        return {"ok": True, "collection_count": len(flat), "collections": flat,
                "client_log": buf.getvalue().strip()}
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_grep_source  (paket/obje kapsamında ABAP kaynak-metin regex arama)
# =============================================================================
_GREP_TYPE_MAP = {"CLAS": "class", "PROG": "program", "INTF": "interface",
                  "FUGR": "functiongroup", "DDLS": "ddls", "BDEF": "bdef"}


@profil_tool()
def adt_grep_source(
    pattern: str,
    package: str | None = None,
    objects: str | list | None = None,
    object_types: str = "CLAS,PROG,INTF,DDLS",
    max_objects: int = 80,
    ignore_case: bool = True,
) -> dict:
    """Paket/obje kapsamında ABAP **KAYNAK-METİN** regex arama — READ-ONLY.

    `adt_where_used` "beni kim referanslıyor" der; bu tool "bu metin/pattern nerede geçiyor"
    der (tamamlayıcı). Kaynağı indirip satır-satır regex. Token-ekonomisi için `max_objects`
    ve toplam 500 eşleşme sınırlı — sınıra ulaşılırsa `truncated_*` işaretlenir (sessiz-kesme yok).

    Args:
        pattern: Python regex. package: paket adı (kapsam). objects: "NAME" veya "NAME:type"
                 virgüllü liste (package'a alternatif). object_types: paket-taramada tip filtresi
                 (CLAS/PROG/INTF/DDLS/FUGR/BDEF). max_objects: taranacak maks obje. ignore_case.

    Returns:
        {ok, pattern, scanned_objects, match_count, truncated_object_scope, truncated_matches,
         matches: [{object, type, line, text}], client_log}
    """
    import re as _re
    from mcp_servers.sap_adt.tools.atom import adt_get
    try:
        rx = _re.compile(pattern, _re.IGNORECASE if ignore_case else 0)
    except _re.error as e:
        return {"ok": False, "error": "bad_regex", "message": str(e)}

    wanted = {t.strip().upper() for t in (object_types.split(",") if object_types else []) if t.strip()}
    client = _get_client()
    targets: list = []
    try:
        if objects:
            raw = objects.split(",") if isinstance(objects, str) else list(objects)
            for item in [str(x).strip() for x in raw if str(x).strip()]:
                if ":" in item:
                    n, t = item.split(":", 1)
                    targets.append((n.strip(), t.strip().lower()))
                else:
                    targets.append((item, "class"))
        elif package:
            with _capture():
                objs = client.list_package_contents(package)
            for o in (objs or []):
                pref = (o.get("type") or "").split("/")[0].upper()
                if wanted and pref not in wanted:
                    continue
                at = _GREP_TYPE_MAP.get(pref)
                if not at:
                    continue
                targets.append((o.get("name"), at))
        else:
            return {"ok": False, "error": "no_scope", "message": "package veya objects gerekli"}
    except Exception as exc:
        return _err_from_exc(exc)

    truncated_scope = len(targets) > max_objects
    targets = targets[:max_objects]
    matches, scanned, hit_cap = [], 0, False
    for n, at in targets:
        r = adt_get(n, object_type=at, include_source=True)
        src = r.get("source")
        if not isinstance(src, str) or not src:
            continue
        scanned += 1
        for i, line in enumerate(src.splitlines(), 1):
            if rx.search(line):
                matches.append({"object": n, "type": at, "line": i, "text": line.strip()[:200]})
                if len(matches) >= 500:
                    hit_cap = True
                    break
        if hit_cap:
            break
    return {"ok": True, "pattern": pattern, "scanned_objects": scanned,
            "match_count": len(matches), "truncated_object_scope": truncated_scope,
            "truncated_matches": hit_cap, "matches": matches}


# =============================================================================
# adt_impact_analysis  (blast-radius — özyinelemeli where-used)
# =============================================================================
@profil_tool()
def adt_impact_analysis(name: str, object_type: str = "ddls",
                        max_depth: int = 2, max_nodes: int = 150) -> dict:
    """Değişiklik etki-alanı (blast-radius) — bir objeyi DOLAYLI referanslayanları
    özyinelemeli where-used ile çıkarır. READ-ONLY.

    "Fix öncesi where-used + blast-radius" feedback'inin otomasyonu: direkt referanslardan
    başlayıp `max_depth` seviyeye kadar yukarı çıkar ("kim etkilenir"). Çok-katmanlı CDS
    stack'inde değişiklik-riskini ölçer. `max_nodes` ile sınırlı — aşılırsa `truncated=True`
    (sessiz-kesme yok).

    Args:
        name: Kök obje. object_type: 'ddls'|'class'|'dtel'|'tabl'|'intf'... max_depth: özyineleme
              derinliği (default 2). max_nodes: toplam maks düğüm (default 150).

    Returns:
        {ok, name, type, max_depth, impacted_count, truncated,
         by_depth: [{depth, count, objects:[{name,type,uri,depth}]}], client_log}
    """
    client = _get_client()
    try:
        from object_types import get_object_url  # type: ignore
        adt = getattr(client, "adt_client", None) or client
        with _capture() as buf:
            if not client.object_exists(name.upper(), object_type):
                return {"ok": False, "error_code": "OBJECT_NOT_FOUND", "name": name,
                        "type": object_type, "client_log": buf.getvalue().strip()}
            root_url = get_object_url(name.upper(), object_type)
            seen = {name.upper() + "|" + object_type.lower()}
            frontier = [root_url]
            levels = []
            truncated = False
            for depth in range(max_depth):
                level_nodes, next_frontier = [], []
                for url in frontier:
                    refs = adt.where_used(url) or []
                    for r in refs:
                        rn = (r.get("name") or "").upper()
                        rt = (r.get("type") or "")
                        ru = (r.get("uri") or "").split("#")[0]
                        key = rn + "|" + rt.lower()
                        if not rn or key in seen:
                            continue
                        seen.add(key)
                        level_nodes.append({"name": rn, "type": rt, "uri": ru, "depth": depth + 1})
                        if ru:
                            next_frontier.append(ru)
                        if len(seen) >= max_nodes:
                            truncated = True
                            break
                    if truncated:
                        break
                levels.append(level_nodes)
                frontier = next_frontier
                if truncated or not frontier:
                    break
        all_nodes = [n for lvl in levels for n in lvl]
        return {"ok": True, "name": name.upper(), "type": object_type, "max_depth": max_depth,
                "impacted_count": len(all_nodes), "truncated": truncated,
                "by_depth": [{"depth": i + 1, "count": len(lvl), "objects": lvl}
                             for i, lvl in enumerate(levels)],
                "client_log": buf.getvalue().strip()}
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_unit_run  (ABAP Unit test koşucu — bug-gate'i canlı-test seviyesine çıkarır)
# =============================================================================
_AUNIT_SEG = {"class": "oo/classes", "clas": "oo/classes",
              "program": "programs/programs", "prog": "programs/programs",
              "functiongroup": "functions/groups", "fugr": "functions/groups"}
_AUNIT_NS = "http://www.sap.com/adt/aunit"
_ADTCORE_NS = "http://www.sap.com/adt/core"


@profil_tool()
def adt_unit_run(name: str, object_type: str = "class") -> dict:
    """Bir Z objenin ABAP Unit testlerini çalıştır → sonuç/assertion döner. READ-ONLY.

    `POST /sap/bc/adt/abapunit/testruns` (run config). Test KOŞAR ama kalıcı obje değişimi
    YOK → ADR 0005 temiz (Z-scope). BUG GATE'i "checklist" seviyesinden "canlı test sonucu"na
    çıkarır. Test yoksa boş sonuç (passed=true, method 0).

    Args:
        name: Obje (Z*/Y*). object_type: 'class'|'program'|'functiongroup'.

    Returns:
        {ok, name, method_count, failed_count, passed, classes: [{class, methods:[{method,
         status, alerts:[{severity, kind, title}]}]}], client_log}
    """
    import xml.etree.ElementTree as ET
    seg = _AUNIT_SEG.get((object_type or "").lower().strip())
    if not seg:
        return {"ok": False, "error": "unsupported_type",
                "message": "object_type: class|program|functiongroup"}
    client = _get_client()
    try:
        from create_rap_service import csrf  # type: ignore
        from urllib.parse import quote
        adt = getattr(client, "adt_client", None) or client
        objuri = "/sap/bc/adt/" + seg + "/" + quote(name.lower(), safe="")
        body = ('<?xml version="1.0" encoding="UTF-8"?>'
                '<aunit:runConfiguration xmlns:aunit="http://www.sap.com/adt/aunit"'
                ' xmlns:adtcore="http://www.sap.com/adt/core">'
                '<external><coverage active="false"/></external>'
                '<adtcore:objectSets><objectSet kind="inclusive"><adtcore:objectReferences>'
                '<adtcore:objectReference adtcore:uri="' + objuri + '"/>'
                '</adtcore:objectReferences></objectSet></adtcore:objectSets>'
                '</aunit:runConfiguration>')
        with _capture() as buf:
            tok = csrf(adt)
            r = adt.session.post(
                adt.url + "/sap/bc/adt/abapunit/testruns",
                headers={"X-CSRF-Token": tok,
                         "Content-Type": "application/vnd.sap.adt.abapunit.testruns.config.v4+xml",
                         "Accept": "application/vnd.sap.adt.abapunit.testruns.result.v2+xml",
                         "sap-client": "100"},
                data=body.encode("utf-8"), verify=False, timeout=180)
        if r.status_code != 200:
            return {"ok": False, "error": "http_%d" % r.status_code,
                    "message": (r.text or "")[:400], "client_log": buf.getvalue().strip()}
        root = ET.fromstring(r.text)

        def _an(el, a):
            return el.get("{%s}%s" % (_ADTCORE_NS, a), "")

        classes, mcount, fcount = [], 0, 0
        for prog in root.iter("{%s}program" % _AUNIT_NS):
            for tclass in prog.iter("{%s}testClass" % _AUNIT_NS):
                methods = []
                for tm in tclass.iter("{%s}testMethod" % _AUNIT_NS):
                    alerts = []
                    for al in tm.iter("{%s}alert" % _AUNIT_NS):
                        title_el = al.find("{%s}title" % _AUNIT_NS)
                        alerts.append({
                            "severity": al.get("severity", ""),
                            "kind": al.get("kind", ""),
                            "title": title_el.text if title_el is not None else None,
                        })
                    mcount += 1
                    if alerts:
                        fcount += 1
                    methods.append({"method": _an(tm, "name"),
                                    "status": "failed" if alerts else "passed",
                                    "alerts": alerts})
                classes.append({"class": _an(tclass, "name"), "methods": methods})
        return {"ok": True, "name": name.upper(), "method_count": mcount,
                "failed_count": fcount, "passed": fcount == 0,
                "classes": classes, "client_log": buf.getvalue().strip()}
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_lock_check
# =============================================================================

@profil_tool()
def adt_lock_check(name: str, object_type: str = "class") -> dict:
    """Probe whether an SAP object is currently locked.

    Strategy: issue a metadata read; if SAPLockError fires, object is locked.
    This is a best-effort probe — some lock types only surface during write.

    Args:
        name: Object name.
        object_type: ADT type ('class', 'doma', 'dtel', 'tabl', 'ddls', ...).

    Returns:
        {ok, name, type, locked: bool, lock_owner?: str, exists: bool, client_log}
    """
    client = _get_client()
    try:
        from sap_adt_lib import SAPLockError, SAPObjectNotFoundError  # type: ignore
    except ImportError:
        SAPLockError = Exception  # type: ignore
        SAPObjectNotFoundError = Exception  # type: ignore

    try:
        with _capture() as buf:
            md = client.get_object_metadata(name, object_type=object_type)
        return {
            "ok": True,
            "name": name,
            "type": object_type,
            "exists": md is not None,
            "locked": False,
            "client_log": buf.getvalue().strip(),
        }
    except Exception as exc:
        if isinstance(exc, SAPLockError):
            return {
                "ok": True,
                "name": name,
                "type": object_type,
                "exists": True,
                "locked": True,
                "lock_owner": getattr(exc, "lock_owner", None),
                "message": str(exc),
            }
        if isinstance(exc, SAPObjectNotFoundError):
            return {
                "ok": True,
                "name": name,
                "type": object_type,
                "exists": False,
                "locked": False,
            }
        return _err_from_exc(exc)
