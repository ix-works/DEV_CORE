"""Atom tools — single ADT REST operation each.

- adt_get          : Read object source/metadata
- adt_post_shell   : Create empty Z shell (no source)
- adt_push_source  : Push source body to existing object
- adt_activate     : Activate object

All tools:
- Return structured JSON: {ok: bool, ...}
- Capture SAPClient stdout chatter into 'client_log' field (does not pollute MCP stdio)
- Apply ADR 0005 guardrails before any SAP HTTP call
- Map SAPADTError subclasses to error codes (auth/not_found/locked/exists/...)
"""
from __future__ import annotations

import contextlib
import io
import tempfile
from pathlib import Path
from typing import Any

from mcp_servers.sap_adt._app import mcp, log, profil_tool
from mcp_servers.sap_adt._reviewer import (
    reject_payload,
    run_reviewer,
    task_for_push,
)
from mcp_servers.sap_adt.guardrails import (
    GuardrailViolation,
    reject_standard_delete,
    require_customer_namespace,
    require_transport,
    require_writable_tier,
)
from mcp_servers.sap_adt._conn import get_active_tier

# Lazy import — SAPClient pulls auth + .conn_adt; defer until first call.
_client = None
_sap_client_sig0 = None        # yüklü sap_client modülünün (size, sha1) imzası — bayat-süreç backstop'u
_sap_client_mtime_seen = None  # son stat'lanan mtime; fast-path (mtime değişmedikçe hash atlanır)


# ADR 0016 REVİZE (2026-06-16): pre-push DRIFT GUARD (M1) + post-write REPO SYNC (M2)
# KALDIRILDI. Sebep: repo≠canlı symmetric kıyası KASITLI edit'leri de blokluyordu
# (working-tree ≠ live her edit'te doğal). Yeni model = PULL-BEFORE-EDIT: edit'ten ÖNCE
# güncel çekilir (PreToolUse Edit|Write hook, scripts/hooks/pull_before_edit.py + seans
# tazelik), böylece push'ta ayrıca kontrol gerekmez. Bkz. ADR 0016 + scripts/sap_sync_pull.py.

# ── READBACK-GATE (2026-06-21, onaylı) ──────────────────────────────────────
# Sorun (kanıt: ZSD001_I_SHIP_POOL `where` kaybı): yazım SAP'de TAM oturmayabilir
# (activate eksik/kısmi, ya da aktif sürüm push edilenden geride kalır) ama tool "ok"
# döner → sessizce drift. Çözüm: activate SONRASI aktif source'u çek + push edilenle
# normalize-compare; fark varsa BLOCKER (ok=False). Delete sonrası: obje hâlâ varsa BLOCKER.
# Maliyet ölçüldü ~50ms/obje (sıcak session). XML-DDIC source taşımaz → content-compare ATLA
# (composite create + _activate_and_verify alan-verify'i kapsar).
# NAME-COLLISION FIX (2026-06-21, gw-deliv kanıtı): ZSD001_I_SHIP_POOL hem DDLS (CDS) hem
# BDEF olabilir. Yalnız İSİMLE key'lersek BDEF push'u CDS kaydını EZER → BDEF aktive edilince
# readback CDS-source ile kıyaslayıp SAHTE-mismatch verir. Çözüm: (name.upper(), type_key) ile key.
_LAST_PUSHED: dict[tuple[str, str], tuple[str, str]] = {}   # (name.upper(), type_key) -> (object_type, source)
_TYPE_KEY_CANON = {
    "cds": "ddls", "cdsview": "ddls", "ddl": "ddls", "ddls": "ddls",
    "behaviordefinition": "bdef", "bdef": "bdef",
    "servicedefinition": "srvd", "srvd": "srvd",
    "clas": "class", "class": "class", "intf": "interface", "interface": "interface",
    "prog": "program", "program": "program",
}


def _type_key(t: str) -> str:
    """Tip eşanlamlılarını kanonikleştir (cds/ddl→ddls, behaviordefinition→bdef, ...)."""
    t = (t or "").lower().strip()
    return _TYPE_KEY_CANON.get(t, t)


_SOURCE_BASED_TYPES = {
    "ddls", "cds", "cdsview", "ddl", "bdef", "behaviordefinition",
    "srvd", "servicedefinition", "class", "clas", "program", "prog",
    "interface", "intf", "dcl", "accesscontrol", "ddlx", "metadataextension",
}


def _content_readback(client, name: str, object_type: str) -> dict:
    """Activate sonrası: AKTİF source'u çek + bu seansta push edilenle normalize-compare.

    Yalnız source-based tip + bu seansta push kaydı varsa çalışır (salt re-activate'te
    push kaydı yok → atla). Fark = yazım tam oturmadı → blocker sinyali.

    Returns: {} (uygulanmaz) | {content_verified: True}
           | {content_verified: False, content_mismatch: True, content_reason, content_diff}
           | {content_verified: None, content_reason} (readback yapılamadı — soft)
    """
    t = (object_type or "").lower().strip()
    if t not in _SOURCE_BASED_TYPES:
        return {}
    rec = _LAST_PUSHED.get((name.upper(), _type_key(object_type)))
    if not rec:
        return {}
    _, pushed = rec
    try:
        import sap_adt_lib as L  # type: ignore
        from source_drift import normalize_source  # type: ignore
        adt = getattr(client, "adt_client", None) or client
        url = L._resolve_source_url(name, t)
        if not url:
            return {"content_verified": None,
                    "content_reason": f"source URL çözülemedi (type={t}) — content readback atlandı"}
        with _capture_stdout():   # SAPClient stdout chatter MCP stdio'yu kirletmesin
            live = adt.get_object_source(url, version="active")
    except Exception as exc:  # noqa: BLE001
        return {"content_verified": None, "content_reason": f"content readback exception: {exc}"}

    if normalize_source(live) == normalize_source(pushed):
        return {"content_verified": True}
    import difflib
    diff = "\n".join(difflib.unified_diff(
        normalize_source(pushed).splitlines(), normalize_source(live).splitlines(),
        fromfile="pushed", tofile="active", lineterm="", n=1))[:1500]
    return {
        "content_verified": False,
        "content_mismatch": True,
        "content_reason": ("AKTİF source push edilenle EŞLEŞMİYOR — yazım SAP'de tam oturmadı "
                           "(activate eksik/kısmi ya da aktif sürüm geride; 'where'-kaybı sınıfı). "
                           "Re-push + re-activate gerekli; pull etmeden ÖNCE düzelt."),
        "content_diff": diff,
    }


def _exists_after_delete(client, name: str, object_type: str):
    """Delete sonrası varlık readback. True=hâlâ var (silme oturmadı) | False=yok | None=bilinemedi."""
    try:
        with _capture_stdout():   # SAPClient stdout chatter MCP stdio'yu kirletmesin
            md = client.get_object_metadata(name, object_type=object_type)
        return md is not None
    except Exception:  # noqa: BLE001
        return None  # NotFound/erişilemez → 'yok' iddiası etme; soft


def _get_client():
    global _client, _sap_client_sig0, _sap_client_mtime_seen
    if _client is None:
        from sap_client import SAPClient  # type: ignore
        _client = SAPClient()
        _sap_client_sig0 = _module_file_sig("sap_client")     # yüklü sürümün imzası (bayat-süreç baz)
        _sap_client_mtime_seen = _module_file_mtime("sap_client")  # fast-path başlangıç mtime'ı
        _record_active_binding(_client)
        log.info("SAPClient initialised")
    else:
        _guard_binding_current(_client)  # cache'li client bağlantı-stale ise REDDET (backstop)
        _guard_module_current()          # sap_client.py disk'te değişti ise (bayat-süreç) REDDET
    return _client


def _module_file_mtime(modname: str):
    """Yüklü modülün disk dosyasının mtime'ı; bilinemezse None. (fast-path stat'ı.)"""
    try:
        import sys, os
        f = getattr(sys.modules.get(modname), "__file__", None)
        return os.path.getmtime(f) if f and os.path.isfile(f) else None
    except Exception:  # noqa: BLE001
        return None


def _module_file_sig(modname: str):
    """Yüklü modülün disk dosyasının (size, sha1) imzası; bilinemezse None.

    Yükleme anında çağrılır → o anki disk içeriği = belleğe yüklenen kod. Sonradan
    dosya değişirse imza ayrışır. (mtime DEĞİL hash: git checkout/CRLF mtime'ı değiştirip
    yanlış-pozitif yapabilir; içerik-hash yalnız gerçek kod değişiminde tetikler.)"""
    try:
        import sys, os, hashlib
        m = sys.modules.get(modname)
        f = getattr(m, "__file__", None)
        if not f or not os.path.isfile(f):
            return None
        data = open(f, "rb").read()
        return (len(data), hashlib.sha1(data).hexdigest())
    except Exception:  # noqa: BLE001
        return None


def _guard_module_current() -> None:
    """Backstop: MCP server uzun-ömürlü süreç → `sap_client.py` fix'ten ÖNCE yüklendiyse
    bellekte BAYAT kod çalıştırır (örn. classrun sahte 'does not implement if_oo_adt_classrun~main').

    On-disk `sap_client.py` yüklü sürümden FARKLI ise süreç bayat → ADT işlemini RED + actionable
    mesaj. `_guard_binding_current` (bağlantı-bayatlığı) ile paralel ikinci katman.

    PERF: normalde yalnız bir `stat()` (mtime). mtime değişmedikçe içerik HASH'lenmez (fast-path)
    → ADT çağrısı başına ek maliyet ≈ birkaç µs. Hash yalnız dosya gerçekten değişince (nadir) koşar.
    Check kendisi kırılırsa fail-open (yanlış-pozitif ADT'yi brick etmesin)."""
    global _sap_client_mtime_seen
    try:
        if _sap_client_sig0 is None:
            return
        mt = _module_file_mtime("sap_client")
        if mt is not None and mt == _sap_client_mtime_seen:
            return  # fast-path: dosya mtime'ı değişmemiş → hash gereksiz
        cur = _module_file_sig("sap_client")  # mtime değişti → içeriği hash'le (git-checkout no-op olabilir)
        _sap_client_mtime_seen = mt
        if cur is None:
            return
        stale = cur != _sap_client_sig0
    except Exception:  # noqa: BLE001
        return
    if stale:
        raise RuntimeError(
            "MCP SERVER BAYAT KOD: 'sap_client.py' disk'te güncellendi ama bu süreç eski sürümü "
            "bellekte çalıştırıyor (örn. adt_classrun sahte 'does not implement' hatası verebilir). "
            "ADT işlemi REDDEDİLDİ — '/mcp' ile yeniden bağlan ya da MCP server'ı restart et."
        )


def _guard_binding_current(client) -> None:
    """Backstop (ADR 0010): cache'li client'in BAGLI oldugu sistem .conn_adt ile ayni mi?

    switch_tier .conn_adt'yi degistirir ama bu surecin client'i eski sisteme bagli kalir
    (/mcp restart edilene dek). Ayrisirsa ADT islemini RED — yoksa istek eski sisteme
    gider ama tier guard yeni sistemi okur (write DEV der, ECC QA'ya gider → felaket).
    Hook (pre_tool_guard) asil katman; bu ikinci katman (bypass yok). Check kendisi
    kirilirsa fail-open (hook yakalar)."""
    try:
        from urllib.parse import urlparse
        from mcp_servers.sap_adt._conn import _conn_value
        adt = getattr(client, "adt_client", None)
        bound_url = getattr(adt, "url", "") or ""
        bound_cl = str(getattr(adt, "client", "") or "")
        cur_url = _conn_value("ADT_SAP_URL", "") or ""
        cur_cl = str(_conn_value("ADT_SAP_CLIENT", "") or "")
        bh = (urlparse(bound_url if "://" in bound_url else "https://" + bound_url).hostname or "").lower()
        ch = (urlparse(cur_url if "://" in cur_url else "https://" + cur_url).hostname or "").lower()
        differ = (bh and ch and bh != ch) or (bound_cl and cur_cl and bound_cl != cur_cl)
    except Exception:
        return  # guard'in kendi hatasi ADT'yi tamamen bricklemesin (hook authoritative)
    if differ:
        raise RuntimeError(
            f"BAĞLANTI TUTARSIZLIĞI (ADR 0010): MCP '{bh}' (client {bound_cl}) sistemine bağlı "
            f"ama .conn_adt artık '{ch}' (client {cur_cl}). switch_tier yapıldı, /mcp restart "
            f"EDİLMEDİ. ADT işlemi REDDEDİLDİ — önce '/mcp' ile yeniden bağlan."
        )


def _record_active_binding(client) -> None:
    """MCP'nin CANLI bagli oldugu sistemi .claude/.mcp_active_system'e yaz (fiili url/client ile).

    Asil yazici _conn.write_mcp_binding_state (acilista da kullanilir). Burada gercek
    bagli host/client gecilir → fiili hedef dogrulanir. Asla client yaratimini kirmaz."""
    try:
        from mcp_servers.sap_adt._conn import write_mcp_binding_state
        adt = getattr(client, "adt_client", None)
        write_mcp_binding_state(
            url=getattr(adt, "url", None),
            client=getattr(adt, "client", None),
        )
    except Exception:  # pragma: no cover - state yazimi asla baglanmayi kirmaz
        pass


def _err_from_exc(exc: Exception) -> dict:
    """Map SAPADTError subclasses (and generic Exception) to structured response."""
    from sap_adt_lib import (  # type: ignore
        SAPAuthenticationError,
        SAPConnectionError,
        SAPObjectNotFoundError,
        SAPObjectExistsError,
        SAPLockError,
        SAPActivationError,
        SAPValidationError,
        SAPADTError,
    )
    if isinstance(exc, SAPAuthenticationError):
        code = "auth_failed"
    elif isinstance(exc, SAPConnectionError):
        code = "connection_failed"
    elif isinstance(exc, SAPObjectNotFoundError):
        code = "not_found"
    elif isinstance(exc, SAPObjectExistsError):
        code = "already_exists"
    elif isinstance(exc, SAPLockError):
        code = "locked"
    elif isinstance(exc, SAPActivationError):
        code = "activation_failed"
    elif isinstance(exc, SAPValidationError):
        code = "validation_error"
    elif isinstance(exc, SAPADTError):
        code = "sap_error"
    else:
        code = "unexpected"
    out = {
        "ok": False,
        "error": code,
        "message": str(exc),
    }
    if isinstance(exc, SAPLockError) and getattr(exc, "lock_owner", None):
        out["lock_owner"] = exc.lock_owner
    if isinstance(exc, SAPActivationError) and getattr(exc, "errors", None):
        out["errors"] = exc.errors
    return out


@contextlib.contextmanager
def _capture_stdout():
    """SAPClient methods print to stdout. In MCP stdio mode stdout is the protocol channel.
    Capture it so client chatter does not break JSON-RPC framing."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


# XML-based DDIC objects have NO /source/main endpoint — they are read as a single
# object XML (via get_ddic_object), not as source text. Routing them through
# download_object (which appends /source/main) 404s and the object falsely reports
# exists:false even when live (recon 2026-06-16, ZSD001_E_RAILN).
_DDIC_XML_TYPES = {"dataelement", "domain", "table", "structure", "tabletype"}


def _ddic_xml_type(object_type: str):
    """Canonical DDIC XML type name if object_type is an XML-based DDIC object
    (data element/domain/table/structure/table type), else None."""
    try:
        from object_types import normalize_object_type  # type: ignore
        canonical = normalize_object_type(object_type)
    except Exception:
        return None
    return canonical if canonical in _DDIC_XML_TYPES else None


# =============================================================================
# adt_get
# =============================================================================

@profil_tool()
def adt_get(name: str, object_type: str = "class", include_source: bool = True) -> dict:
    """Get an SAP ADT object: existence, metadata, and (optionally) source.

    Args:
        name: Object name (case-insensitive, normalised to upper on SAP side).
        object_type: ADT object type. Common: 'class', 'doma', 'dtel', 'tabl', 'view',
                     'ddls' (CDS), 'fugr', 'func', 'enqu', 'msag', 'prog'.
        include_source: If True, also fetches source text. Set False for fast metadata-only.

    Returns:
        {ok, name, type, exists, source?, metadata?, client_log}
        On miss:  {ok: true, exists: false, name, type}
        On error: {ok: false, error, message}
    """
    # MSAG (mesaj sınıfı): adt_get msag tipini DESTEKLEMEZ → özel messageclass endpoint'i.
    if (object_type or "").lower().strip() in ("msag", "messageclass"):
        return adt_msgclass_read(name)

    client = _get_client()
    log_buf = io.StringIO()

    # XML-based DDIC objects (DTEL/DOMA/TABL/structure/tabletype): read object XML
    # directly; they have no /source/main source endpoint (see _DDIC_XML_TYPES note).
    ddic_xml_type = _ddic_xml_type(object_type)
    if ddic_xml_type is not None:
        try:
            with _capture_stdout() as out:
                xml = client.get_ddic_object(ddic_xml_type, name)
            log_buf.write(out.getvalue())
            return {
                "ok": True,
                "name": name,
                "type": object_type,
                "exists": xml is not None,
                "source": xml,
                "metadata": xml,
                "client_log": log_buf.getvalue().strip(),
            }
        except Exception as exc:
            from sap_adt_lib import SAPObjectNotFoundError, SAPADTError  # type: ignore
            if isinstance(exc, SAPObjectNotFoundError) or (
                isinstance(exc, SAPADTError) and getattr(exc, "status_code", None) == 404
            ):
                return {
                    "ok": True,
                    "name": name,
                    "type": object_type,
                    "exists": False,
                    "client_log": log_buf.getvalue().strip(),
                }
            return _err_from_exc(exc)

    try:
        with _capture_stdout() as out:
            source = None
            metadata = None
            if include_source:
                source = client.download_object(name, object_type=object_type, save_local=False)
            metadata = client.get_object_metadata(name, object_type=object_type)
        log_buf.write(out.getvalue())
        return {
            "ok": True,
            "name": name,
            "type": object_type,
            "exists": source is not None or metadata is not None,
            "source": source,
            "metadata": metadata,
            "client_log": log_buf.getvalue().strip(),
        }
    except Exception as exc:
        from sap_adt_lib import SAPObjectNotFoundError  # type: ignore
        if isinstance(exc, SAPObjectNotFoundError):
            return {
                "ok": True,
                "name": name,
                "type": object_type,
                "exists": False,
                "client_log": log_buf.getvalue().strip(),
            }
        return _err_from_exc(exc)


# =============================================================================
# adt_msgclass_read  (mesaj sınıfı / MSAG okuma — adt_get msag DESTEKLEMEZ)
# =============================================================================
_MC_NS_MC = "http://www.sap.com/adt/MessageClass"
_MC_NS_AC = "http://www.sap.com/adt/core"


def _parse_msgclass_xml(xml_text: str) -> dict:
    """ADT `mc:messageClass` XML → {name, master_language, description, messages:[...]}.

    Kanıt (canlı MSAG doğrulaması, 2026-07-12): her mesaj `<mc:messages mc:msgno mc:msgtext
    mc:selfexplainatory mc:documented>` attribute'ları taşır; metin HTML-escape'li (ET çözer).
    """
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_text)

    def _ac(a: str):
        return root.get("{%s}%s" % (_MC_NS_AC, a))

    messages = []
    for el in root.findall("{%s}messages" % _MC_NS_MC):
        def _g(a: str, _el=el):
            return _el.get("{%s}%s" % (_MC_NS_MC, a))
        messages.append({
            "no": _g("msgno"),
            "text": _g("msgtext"),
            "selfexplanatory": (_g("selfexplainatory") == "true"),
            "documented": (_g("documented") == "true"),
        })
    return {
        "name": _ac("name"),
        "master_language": _ac("masterLanguage"),
        "description": _ac("description"),
        "messages": messages,
    }


@profil_tool()
def adt_msgclass_read(name: str) -> dict:
    """Read a message class (MSAG) and ALL its messages via ADT. READ-ONLY.

    Neden ayrı tool: `adt_get` msag tipini DESTEKLEMEZ ve `adt_table_read` T100'ü
    filtreleyemez (WHERE param yok; T100 preview 400 verir). Bu tool resmî ADT kaynağını
    kullanır: ham GET `/sap/bc/adt/messageclass/{name}`
    (Accept `application/vnd.sap.adt.mc.messageclass+xml`) → XML parse.

    Referans: marcellourbani/vscode_abap_remote_fs (Message Class Editor). CANLI-DOĞRULANDI
    (2026-07-12): `/messages` alt-path'i 404; kök `/messageclass/{name}` +
    `.mc.messageclass+xml` Accept çalışır (reference'ın `.v2+xml` header'ı 406 verir —
    sunucu kabul-tipini kendi bildirir).

    Args:
        name: Mesaj sınıfı adı (ör. 'ZSD001').

    Returns:
        {ok, name, exists, master_language?, description?, count?, messages?, client_log}
        messages: [{no, text, selfexplanatory, documented}, ...] (text: '&' çözülmüş, master dil).
        On miss: {ok: true, exists: false, name}
    """
    client = _get_client()
    log_buf = io.StringIO()
    try:
        adt = getattr(client, "adt_client", None) or client
        from urllib.parse import quote
        url = adt.url + "/sap/bc/adt/messageclass/" + quote(name.lower(), safe="")
        with _capture_stdout() as out:
            r = adt.session.get(
                url,
                headers={"Accept": "application/vnd.sap.adt.mc.messageclass+xml"},
                verify=False, timeout=60,
            )
        log_buf.write(out.getvalue())
        if r.status_code == 404:
            return {"ok": True, "name": name.upper(), "exists": False,
                    "client_log": log_buf.getvalue().strip()}
        if r.status_code != 200:
            return {"ok": False, "name": name.upper(), "error": "http_%d" % r.status_code,
                    "message": (r.text or "")[:500], "client_log": log_buf.getvalue().strip()}
        parsed = _parse_msgclass_xml(r.text)
        return {
            "ok": True,
            "name": parsed["name"] or name.upper(),
            "exists": True,
            "master_language": parsed["master_language"],
            "description": parsed["description"],
            "count": len(parsed["messages"]),
            "messages": parsed["messages"],
            "client_log": log_buf.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_post_shell
# =============================================================================

@profil_tool()
def adt_post_shell(
    object_type: str,
    name: str,
    package: str,
    transport: str,
    description: str,
    extra: dict | None = None,
) -> dict:
    """Create an empty SAP object shell (inactive, no source yet).

    Use adt_push_source + adt_activate after this for atom flow.
    Composite tools (adt_*_create) chain these three atomically.

    Args:
        object_type: 'class', 'doma', 'dtel', 'tabl', 'ddls', 'msag', ...
        name: Customer-namespace name (Z* or Y*).
        package: Target SAP package.
        transport: Modifiable transport request number.
        description: Short description (TR for Z* objects per ADR 0005 §D).
        extra: Object-specific parameters (e.g., {'datatype':'CHAR','length':10} for domain).

    Returns:
        {ok, name, type, object_url?, client_log}
        On guardrail block: {ok: false, error: 'guardrail_violation', code, message}
    """
    try:
        require_writable_tier(get_active_tier(), what=f"{object_type} create")
        require_customer_namespace(name, what=object_type)
        require_transport(transport, what=f"{object_type} create")
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    try:
        with _capture_stdout() as out:
            result = client.create_object(
                object_type=object_type,
                name=name,
                package=package,
                description=description,
                transport=transport,
                **(extra or {}),
            )
        return {
            "ok": bool(result),
            "name": name,
            "type": object_type,
            "result": result if isinstance(result, dict) else None,
            "client_log": out.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_push_source
# =============================================================================

@profil_tool()
def adt_push_source(
    name: str,
    object_type: str,
    source: str,
    transport: str | None = None,
    skip_reviewer: bool = False,
    ack_drop: str = "",
) -> dict:
    """Push source text to an existing SAP object.

    The shell must exist (use adt_post_shell first, or composite tools).
    Activation is a separate step — call adt_activate after.

    Reviewer pre-flight (ADR 0006) runs automatically on the source text
    (written to a temp file, passed to scripts/validators/run_review.py).
    BLOCKER verdict rejects the push. Use skip_reviewer=True only for emergencies
    (and document why in the commit message).

    Args:
        name: Object name (Z*/Y*).
        object_type: 'class', 'ddls', 'prog', 'tabl', ...
        source: Source body text (full content; partial diffs not supported).
        transport: Modifiable transport (optional if object already has assignment).
        skip_reviewer: Bypass reviewer pre-flight (NOT recommended).
        ack_drop: Comma-separated table field names whose DROP is explicitly
            approved (user+lead, ADR 0005-B). Forwarded to the embedded reviewer's
            --ack-drop → ONLY these named drops become ACK-WARNING; any un-named
            drop or any TYPE/RENAME change still BLOCKER. This is the targeted,
            auditable alternative to skip_reviewer for intentional table DROPs —
            the rest of the drop-guard (and all other checks) stay active.

    Returns:
        {ok, name, type, result, client_log, reviewer?}
    """
    try:
        require_writable_tier(get_active_tier(), what=f"{object_type} push")
        require_customer_namespace(name, what=object_type)
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    tmp_file = None
    reviewer_warn = None
    try:
        # Write source to temp file first — needed by both reviewer and SAPClient.push_object.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=f".{object_type}.txt",
            delete=False,
        ) as f:
            f.write(source)
            tmp_file = Path(f.name)

        # Reviewer pre-flight (ADR 0006) — automatic, single point of enforcement.
        if not skip_reviewer:
            task = task_for_push(object_type)
            review = run_reviewer(task, str(tmp_file), ack_drop=ack_drop)
            if review.is_blocker:
                return reject_payload(name, object_type, review)
            if review.verdict != "SKIP":
                reviewer_warn = review.to_dict()

        # ADR 0016 REVİZE: pre-push DRIFT GUARD (M1) KALDIRILDI — kasıtlı edit'leri de
        # blokluyordu (repo≠canlı her meşru edit'te doğal). Tazelik artık edit-ÖNCESİ
        # pull-before-edit hook ile sağlanır → push'ta ayrı drift-kontrolü gerekmez.
        with _capture_stdout() as out:
            result = client.push_object(
                object_name=name,
                object_type=object_type,
                transport=transport,
                source_file=str(tmp_file),
            )
        ok = bool(result and (result.get("success") if isinstance(result, dict) else True))
        resp = {
            "ok": ok,
            "name": name,
            "type": object_type,
            "result": result if isinstance(result, dict) else None,
            "client_log": out.getvalue().strip(),
        }
        if reviewer_warn:
            resp["reviewer"] = reviewer_warn

        # Readback-gate: push edilen source'u kaydet → adt_activate sonrası AKTİF source ile
        # normalize-compare için (yazımın tam oturduğunu doğrula). Upload başarılıysa.
        if ok:
            _LAST_PUSHED[(name.upper(), _type_key(object_type))] = (object_type, source)

        # Sprint 6 T10 — post-push consistency check.
        # Struct/table push'larda placeholder kalma veya version=inactive durumlarını
        # yakalamak için reviewer'ı tekrar (post-mode) çağır.
        if ok and not skip_reviewer:
            obj_lower = (object_type or "").lower()
            if obj_lower in ("structure", "struct"):
                post = run_reviewer("struct_post_create", str(tmp_file))
                resp["post_check"] = {
                    "ok": post.passed,
                    "verdict": post.verdict,
                    "blocker_count": post.blocker_count,
                    "warning_count": post.warning_count,
                }
                if post.skip_reason:
                    resp["post_check"]["skip_reason"] = post.skip_reason
                if not post.passed:
                    resp["ok"] = False
            elif obj_lower in ("tabl", "ddls", "dtel", "doma"):
                # Generic active-version check via the same orchestrator.
                post = run_reviewer("sap_active_check", str(tmp_file))
                resp["post_check"] = {
                    "ok": post.passed,
                    "verdict": post.verdict,
                }
                if post.skip_reason:
                    resp["post_check"]["skip_reason"] = post.skip_reason
                if not post.passed:
                    resp["ok"] = False
        return resp
    except Exception as exc:
        return _err_from_exc(exc)
    finally:
        if tmp_file and tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass


# =============================================================================
# adt_activate
# =============================================================================

@profil_tool()
def adt_delete(
    name: str,
    object_type: str,
    transport: str | None = None,
) -> dict:
    """Delete a Z/Y namespace SAP object.

    Hard guardrail (ADR 0005 §A): only Z*/Y* objects deletable. Standard SAP
    objects → reject. Caller bears responsibility for downstream impact;
    where-used analysis is the caller's job (not done here).

    Args:
        name: Object name (must be Z*/Y*).
        object_type: 'class', 'doma', 'dtel', 'tabl', 'ddls', 'msag', 'prog', ...
        transport: Modifiable transport for the delete entry.

    Returns:
        {ok, name, type, deleted, client_log}
    """
    try:
        require_writable_tier(get_active_tier(), what=f"{object_type} delete")
        reject_standard_delete(name, object_type)
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    try:
        with _capture_stdout() as out:
            deleted = client.delete_object(
                object_name=name,
                object_type=object_type,
                transport=transport,
                confirm=False,  # MCP context: no interactive prompt possible
            )
        resp = {
            "ok": bool(deleted),
            "name": name,
            "type": object_type,
            "deleted": bool(deleted),
            "client_log": out.getvalue().strip(),
        }
        # Readback-gate: silme GERÇEKTEN oturdu mu — obje hâlâ varsa BLOCKER.
        if resp["ok"]:
            still = _exists_after_delete(client, name, object_type)
            if still is True:
                resp["ok"] = False
                resp["deleted"] = False
                resp["delete_verified"] = False
                resp["delete_reason"] = ("Silme sonrası obje HÂLÂ mevcut (readback) — silme "
                                         "oturmadı. Lock/transport/bağımlılık kontrol et, tekrar dene.")
            elif still is False:
                resp["delete_verified"] = True
            else:
                resp["delete_verified"] = None
                resp["delete_reason"] = "Silme sonrası varlık readback yapılamadı (soft; manuel teyit)."
        # _LAST_PUSHED temizliği — silinen objenin bayat push kaydı kalmasın (tüm tip-varyantları).
        for _k in [k for k in _LAST_PUSHED if k[0] == name.upper()]:
            _LAST_PUSHED.pop(_k, None)
        return resp
    except Exception as exc:
        return _err_from_exc(exc)


# Aktivasyon obje URI segmentleri (tip → ADT path; /source/main YOK). Çoklu-obje atomik
# aktivasyon (interface DDLS + BDEF + class aynı /activation POST'ta — ADIM-1 tipi RAP
# zincirleri) + activate_object'in bilmediği tipler (bdef/srvd) için.
_ACTIVATION_URI_SEG = {
    "ddls": "ddic/ddl/sources", "cds": "ddic/ddl/sources", "cdsview": "ddic/ddl/sources",
    "bdef": "bo/behaviordefinitions", "behaviordefinition": "bo/behaviordefinitions",
    "class": "oo/classes", "clas": "oo/classes",
    "srvd": "ddic/srvd/sources", "servicedefinition": "ddic/srvd/sources",
    "dcl": "acm/dcl/sources", "accesscontrol": "acm/dcl/sources",
    "ddlx": "ddic/ddlx/sources", "metadataextension": "ddic/ddlx/sources",
    "domain": "ddic/domains", "doma": "ddic/domains",
    "dataelement": "ddic/dataelements", "dtel": "ddic/dataelements",
    "table": "ddic/tables", "tabl": "ddic/tables", "structure": "ddic/structures",
    "program": "programs/programs", "prog": "programs/programs",
    "srvb": "businessservices/bindings", "servicebinding": "businessservices/bindings",
}


def _activation_uri(name: str, object_type: str):
    from urllib.parse import quote
    seg = _ACTIVATION_URI_SEG.get((object_type or "").lower().strip())
    if not seg:
        return None
    return f"/sap/bc/adt/{seg}/{quote(name.lower(), safe='')}"


@profil_tool()
def adt_activate(name: str, object_type: str = "class", also: list | None = None) -> dict:
    """Activate an SAP object — single, OR multiple objects ATOMICALLY (one /activation POST).

    Atomik çoklu-obje aktivasyon (RAP zincirleri): birbirine bağımlı objeler (ör. interface
    DDLS + onun BDEF'i + behavior class) AYNI istekte aktive edilmeli → `also` ile ek objeleri
    ver, hepsi tek POST'ta aktive + doğrulanır (activationExecuted + type=E parse; sahte-OK
    imkansız). bdef/srvd gibi activate_object'in desteklemediği tipler de bu yolda çalışır.

    Args:
        name: Birincil obje adı (Z*/Y*).
        object_type: 'class', 'ddls', 'bdef', 'srvd', 'tabl', ...
        also: Atomik co-activate ek objeler: [{"name": "...", "object_type": "..."}, ...].
              None/boş → tek-obje aktivasyon (klasik yol).

    Returns:
        {ok, name, type, activated, errors?, warnings?, refs?, client_log}
    """
    try:
        require_writable_tier(get_active_tier(), what=f"{object_type} activate")
        require_customer_namespace(name, what=object_type)
        for o in (also or []):
            require_customer_namespace(o.get("name", ""), what=o.get("object_type", "object"))
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()

    # --- ATOMİK ÇOKLU-OBJE AKTİVASYON (also verildiyse) ---
    if also:
        refs = []
        pairs = [(name, object_type)] + [(o.get("name"), o.get("object_type")) for o in also]
        for n, t in pairs:
            uri = _activation_uri(n, t)
            if not uri:
                return {"ok": False, "error": "unsupported_type",
                        "message": f"Aktivasyon URI çözülemedi: {n} (type={t}). "
                                   f"Desteklenen tipler: {sorted(set(_ACTIVATION_URI_SEG))}"}
            refs.append((uri, n))
        try:
            from create_rap_service import csrf, activate_and_verify  # type: ignore
            adt = getattr(client, "adt_client", None) or client
            with _capture_stdout() as out:
                tok = csrf(adt)
                activate_and_verify(adt, tok, refs)   # activationExecuted!=true / type=E → raises
            resp = {
                "ok": True,
                "name": name,
                "type": object_type,
                "activated": True,
                "refs": [n for _, n in refs],
                "client_log": out.getvalue().strip(),
            }
            # Readback-gate: her aktive edilen source-based obje için içerik doğrula.
            rb_all = {}
            for n, t in pairs:
                rb = _content_readback(client, n, t)
                if rb:
                    rb_all[n.upper()] = rb
                    if rb.get("content_verified") is False:
                        resp["ok"] = False
            if rb_all:
                resp["content_readback"] = rb_all
            return resp
        except Exception as exc:
            return _err_from_exc(exc)

    # --- TEK-OBJE AKTİVASYON ---
    # srvb gibi activate_object'in DESTEKLEMEDİĞİ tipler: kanonik /activation POST
    # (activation-ref, segment _ACTIVATION_URI_SEG'den) yoluyla aktive et — activationExecuted
    # + type=E parse → sahte-OK imkansız (gateway'in elle REST workaround'unu typed yapar,
    # ders 2026-06-22 SRVB). Çalışan/source-tabanlı tipler (class/tabl/...) klasik
    # activate_object yolunda kalır (içerik readback-gate'i korunur, regresyon yok).
    _ref_only = {"srvb", "servicebinding"}
    if (object_type or "").lower().strip() in _ref_only:
        uri = _activation_uri(name, object_type)
        try:
            from create_rap_service import csrf, activate_and_verify  # type: ignore
            adt = getattr(client, "adt_client", None) or client
            with _capture_stdout() as out:
                tok = csrf(adt)
                activate_and_verify(adt, tok, [(uri, name)])   # !=true / type=E → raises
            return {
                "ok": True, "name": name, "type": object_type, "activated": True,
                "refs": [name], "client_log": out.getvalue().strip(),
                "note": "activation-ref yolu (activate_object bu tipi desteklemiyor). "
                        "OData $metadata tazelemek gerekiyorsa ayrıca adt_publish_service çağır.",
            }
        except Exception as exc:
            return _err_from_exc(exc)

    try:
        with _capture_stdout() as out:
            activated = client.activate_object(name, object_type=object_type)
        log_text = out.getvalue()

        # Parse a few signals from client log (best-effort; structured result is already in 'activated')
        errors: list[str] = []
        warnings: list[str] = []
        for line in log_text.splitlines():
            if line.startswith("  - ") and "warning" in log_text.lower():
                warnings.append(line[4:].strip())

        resp = {
            "ok": True,
            "name": name,
            "type": object_type,
            "activated": bool(activated),
            "client_log": log_text.strip(),
        }

        # Readback-gate: aktive edilen source-based obje için AKTİF source'u push edilenle
        # karşılaştır. Fark → yazım tam oturmadı → BLOCKER (ok=False). XML-DDIC/kayıtsız → no-op.
        rb = _content_readback(client, name, object_type)
        if rb:
            resp.update(rb)
            if rb.get("content_verified") is False:
                resp["ok"] = False

        # ADR 0016 REVİZE: post-write REPO SYNC (M2) KALDIRILDI — gereksiz (push edince repo
        # zaten ≈ canlı; tazelik bir sonraki edit'te pull-before-edit hook ile sağlanır).
        return resp
    except Exception as exc:
        return _err_from_exc(exc)


@profil_tool()
def adt_publish_service(name: str, version: str = "0001") -> dict:
    """(Re)publish an OData V2 service binding (SRVB) — refreshes the OData $metadata.

    SRVD expose / underlying CDS değişince, yayınlanmış OData metadata'sının (entity set +
    property) yeni hâli yansıtması için SRVB republish gerekir. Bu, raw `/businessservices/
    odatav2/publishjobs` POST'unun TYPED, guardrailed muadili (raw-Bash classifier bloğunu
    önler). Sonuç doğrulaması = `GET /sap/opu/odata/sap/<NAME>/$metadata` (çağıran yapar).

    Args:
        name: Service binding (SRVB) adı, ör. ZSD001_UI_BOOKING_O2.
        version: Servis sürümü (default '0001').

    Returns:
        {ok, name, status_code, published, body, client_log}
    """
    try:
        require_writable_tier(get_active_tier(), what="service publish")
        require_customer_namespace(name, what="service binding")
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    try:
        from create_rap_service import csrf, publish_xml, PUBLISH_V2  # type: ignore
        adt = getattr(client, "adt_client", None) or client
        with _capture_stdout() as out:
            tok = csrf(adt)
            r = adt.session.post(
                adt.url + PUBLISH_V2,
                params={"servicename": name, "serviceversion": version},
                headers={"X-CSRF-Token": tok, "Content-Type": "application/xml",
                         "Accept": "application/xml, application/vnd.sap.as+xml;charset=UTF-8;"
                                   "dataname=com.sap.adt.StatusMessage",
                         "sap-client": "100", "sap-language": "TR"},
                data=publish_xml(name).encode("utf-8"), verify=False, timeout=120,
            )
        published = r.status_code in (200, 201, 202)
        return {
            "ok": published,
            "name": name,
            "status_code": r.status_code,
            "published": published,
            "body": (r.text or "")[:900],
            "client_log": out.getvalue().strip(),
        }
    except Exception as exc:
        return _err_from_exc(exc)


# =============================================================================
# adt_classrun  (gap-analysis C1 — ABAP çalıştırma kanalı)
# =============================================================================

@profil_tool()
def adt_classrun(name: str) -> dict:
    """Bir IF_OO_ADT_CLASSRUN sınıfını çalıştır (ADT classrun, F9-run muadili).

    ADT-only ABAP execute kanalı. RFC FM (RPY_DYNPRO_INSERT/RS_CUA_*) çağıran generator
    sınıflarını çalıştırmak için (ekran/GUI status üretimi — C1). Kod ÇALIŞTIRIR (yazma
    yapabilir) → ADR 0010 tier guard: yalnızca DEV.

    Args:
        name: Sınıf (Z*/Y*, if_oo_adt_classrun~main implement etmeli).

    Returns:
        {ok, class, status, output} — output = out->write konsol çıktısı.
    """
    try:
        require_writable_tier(get_active_tier(), what="classrun execute")
        require_customer_namespace(name, what="class")
    except GuardrailViolation as gv:
        return gv.as_dict()

    client = _get_client()
    try:
        with _capture_stdout() as out:
            res = client.run_classrun(name)
        if isinstance(res, dict):
            res.setdefault("client_log", out.getvalue().strip())
        return res
    except Exception as exc:
        return _err_from_exc(exc)
