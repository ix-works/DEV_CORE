"""Query tools — read-only.

- adt_search_objects  : Search by name/wildcard, optional type filter
- adt_transport_list  : List modifiable transports for current user
- adt_lock_check      : Probe whether an object is currently locked

All return structured JSON; never write to SAP.
"""
from __future__ import annotations

import contextlib
import io
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
