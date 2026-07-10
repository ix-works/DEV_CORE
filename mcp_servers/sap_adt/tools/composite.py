"""Composite tools — multi-step flows with verification step.

- adt_domain_create  : create_domain + activate + verify
- adt_dtel_create    : create_dataelement + activate + verify (4 labels required)
- adt_struct_create  : create_structure + activate + verify

Pattern (atomic, fail-explicit):
  1. Guardrails (Z/Y prefix, transport, TR text, labels)
  2. Pre-check via adt_get → fail if already exists (caller must decide: keep/recreate)
  3. SAPClient.create_<x>() — shell + source set (no activation)
  4. SAPClient.activate_object()
  5. SAPClient.get_object_metadata() — verify
  6. Return step-by-step status

Rollback policy:
- Step 3 fail → nothing created, return error
- Step 4 fail → object exists inactive. Do NOT auto-delete; return inactive=true with errors.
  Caller decides: fix-and-retry, manual delete, or accept.
- Step 5 fail → object created+activated but verify mismatched. Return warning.

This conservative policy matches ADR 0007: composite is atomic-create, not atomic-rollback.
"""
from __future__ import annotations

import contextlib
import io
from typing import Any

from mcp_servers.sap_adt._app import mcp, log, profil_tool
from mcp_servers.sap_adt._reviewer import (
    reject_payload,
    run_reviewer,
    task_for_composite,
)
from mcp_servers.sap_adt.guardrails import (
    GuardrailViolation,
    require_all_labels,
    require_customer_namespace,
    require_tr_text,
    require_transport,
    require_writable_tier,
)
from mcp_servers.sap_adt._conn import get_active_tier


def _maybe_reviewer(tool_name: str, name: str, object_type: str,
                    artifact_path: str | None) -> tuple[dict | None, dict | None]:
    """Run reviewer pre-flight. Returns (reject_payload, warnings_dict).
    reject_payload is non-None when BLOCKER → tool must return it immediately.
    warnings_dict is non-None when WARNING → tool proceeds but includes it in response.
    Both None on PASS/SKIP.
    """
    task = task_for_composite(tool_name)
    result = run_reviewer(task, artifact_path)
    if result.is_blocker:
        return reject_payload(name, object_type, result), None
    if result.verdict == "WARNING":
        return None, {"reviewer": result.to_dict()}
    return None, ({"reviewer": result.to_dict()} if result.verdict != "SKIP" else None)


# Reuse atom helpers
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


def _exists(client, name: str, object_type: str) -> bool:
    """Return True if object already exists (even inactive)."""
    try:
        with _capture():
            md = client.get_object_metadata(name, object_type=object_type)
        return md is not None
    except Exception as e:
        from sap_adt_lib import SAPObjectNotFoundError  # type: ignore
        if isinstance(e, SAPObjectNotFoundError):
            return False
        # On other errors, assume not-known and let create handle.
        log.warning("exists-check failed for %s/%s: %s", object_type, name, e)
        return False


def _activate_and_verify(client, name: str, object_type: str) -> dict:
    """Step 4+5 — common tail. Returns dict with activated/verified flags.

    verified=True requires:
      - get_object_metadata returns non-None
      - SAP metadata XML contains adtcore:version="active"

    Sprint 6 T10 lesson: existence != active. Bağımlı objeler inconsistent ise
    activate çağrısı OK döner ama version "inactive" kalır.
    """
    import re
    out: dict[str, Any] = {}
    try:
        with _capture() as buf:
            activated = client.activate_object(name, object_type=object_type)
        out["activated"] = bool(activated)
        out["activate_log"] = buf.getvalue().strip()
    except Exception as exc:
        out["activated"] = False
        out["activate_error"] = _err_from_exc(exc)
        return out

    if not out["activated"]:
        return out

    # Verify metadata + version=active
    try:
        with _capture():
            md = client.get_object_metadata(name, object_type=object_type)
        if md is None:
            out["verified"] = False
            out["verify_reason"] = "metadata_not_found"
            return out
        md_text = md if isinstance(md, str) else str(md)
        m = re.search(r'adtcore:version="(\w+)"', md_text)
        version = m.group(1) if m else None
        # ADR 0005-D — masterLanguage=TR enforce (gap-analysis #20/B). Ekstra SAP çağrısı yok;
        # zaten çekilen metadata'dan oku. EN ise yüksek-sesli uyarı (session fix sonrası
        # yeni objeler TR; EN çıkarsa EN-sticky isim veya regresyon işareti).
        ml = re.search(r'masterLanguage="(\w+)"', md_text)
        out["master_language"] = ml.group(1) if ml else None
        if out["master_language"] and out["master_language"] != "TR":
            out["master_language_warning"] = (
                f"masterLanguage={out['master_language']} — ADR 0005-D TR bekler. "
                f"Yeni objeler TR olmalı (#20 session fix); EN ise isim EN-sticky olabilir "
                f"(TADIR-LANGU reset / yeni isim)."
            )
        if version == "active":
            out["verified"] = True
            out["sap_version"] = "active"
        else:
            out["verified"] = False
            out["verify_reason"] = f"sap_version={version or 'unknown'}_expected_active"
            out["sap_version"] = version
    except Exception as exc:
        out["verified"] = False
        out["verify_reason"] = f"verify_exception:{exc}"
    return out


# =============================================================================
# adt_domain_create
# =============================================================================

@profil_tool()
def adt_domain_create(
    name: str,
    datatype: str,
    length: int,
    description: str,
    package: str,
    transport: str,
    decimals: int = 0,
    lowercase: bool = False,
    fixed_values: list[dict] | None = None,
    artifact_path: str | None = None,
) -> dict:
    """Create + activate + verify a DDIC domain atomically.

    Guardrails: Z/Y prefix, transport non-empty, description non-empty.
    Reviewer (ADR 0006): if artifact_path given, run_review.py pre-flight; BLOCKER rejects.

    Args:
        name: Domain name (Z*/Y*).
        datatype: 'CHAR', 'NUMC', 'INT4', 'CURR', 'QUAN', 'DATS', 'TIMS', 'DEC', ...
        length: Field length.
        description: TR description (ADR 0005 §D — non-empty).
        package: Target package (must exist).
        transport: Modifiable transport.
        decimals: Decimal places (CURR/QUAN/DEC).
        lowercase: Allow lowercase letters.
        fixed_values: [{'value':'A','text':'...'}]
        artifact_path: Optional local file path for reviewer pre-flight (ADR 0006).
                       For domains, validators are not yet defined → reviewer SKIPs gracefully.

    Returns:
        {ok, name, type:'doma', steps: {reviewer, pre_check, create, activate, verify}, ...}
    """
    obj_type = "doma"
    try:
        require_writable_tier(get_active_tier(), what="domain create")
        require_customer_namespace(name, what=obj_type)
        require_transport(transport, what=f"{obj_type} create")
        require_tr_text(description, what="domain description")
    except GuardrailViolation as gv:
        return gv.as_dict()

    # Reviewer pre-flight (ADR 0006)
    blocker, warn = _maybe_reviewer("adt_domain_create", name, obj_type, artifact_path)
    if blocker:
        return blocker

    client = _get_client()
    steps: dict[str, Any] = {}

    # 1. Pre-check
    if _exists(client, name, obj_type):
        return {
            "ok": False,
            "error": "already_exists",
            "message": f"Domain {name} zaten mevcut. Önce adt_get ile incele, gerekirse manuel delete sonra tekrar dene.",
            "name": name,
            "type": obj_type,
        }
    steps["pre_check"] = "not_exists"

    # 2. Create (shell + source)
    try:
        with _capture() as buf:
            created = client.create_domain(
                name=name,
                datatype=datatype,
                length=length,
                description=description,
                package=package,
                transport=transport,
                decimals=decimals,
                lowercase=lowercase,
                fixed_values=fixed_values,
            )
        steps["create"] = {"ok": bool(created), "log": buf.getvalue().strip()}
    except Exception as exc:
        steps["create"] = _err_from_exc(exc)
        return {"ok": False, "name": name, "type": obj_type, "steps": steps}

    if not created:
        return {"ok": False, "name": name, "type": obj_type, "steps": steps,
                "message": "create_domain returned False — see steps.create.log"}

    # 3+4. Activate + verify
    tail = _activate_and_verify(client, name, obj_type)
    steps["activate"] = {"ok": tail.get("activated", False), "log": tail.get("activate_log", "")}
    if "activate_error" in tail:
        steps["activate"]["error"] = tail["activate_error"]
    steps["verify"] = {"ok": tail.get("verified", False)}
    if tail.get("master_language_warning"):
        steps["verify"]["master_language_warning"] = tail["master_language_warning"]

    ok_overall = steps["create"].get("ok") and tail.get("activated") and tail.get("verified")
    out = {
        "ok": bool(ok_overall),
        "name": name,
        "type": obj_type,
        "datatype": datatype,
        "length": length,
        "steps": steps,
    }
    if warn:
        out["reviewer"] = warn["reviewer"]
    return out


# =============================================================================
# adt_dtel_create
# =============================================================================

@profil_tool()
def adt_dtel_create(
    name: str,
    domain_name: str,
    description: str,
    package: str,
    transport: str,
    short_label: str,
    medium_label: str,
    long_label: str,
    heading_label: str,
    artifact_path: str | None = None,
) -> dict:
    """Create + activate + verify a DDIC data element atomically.

    ADR 0005 §D: All 4 labels (short/medium/long/heading) MUST be filled with TR text.
    Reviewer (ADR 0006): if artifact_path given, pre-flight runs; BLOCKER rejects.

    Args:
        name: Data element name (Z*/Y*).
        domain_name: Underlying domain (Z* preferred; standard ABAP types like CHAR1 also OK).
        description: TR description.
        package: Target package.
        transport: Modifiable transport.
        short_label, medium_label, long_label, heading_label: 4 TR labels (non-empty each).
        artifact_path: Optional local file path for reviewer pre-flight (ADR 0006).

    Returns:
        {ok, name, type:'dtel', steps, ...}
    """
    obj_type = "dtel"
    labels = {
        "short": short_label or "",
        "medium": medium_label or "",
        "long": long_label or "",
        "heading": heading_label or "",
    }
    try:
        require_writable_tier(get_active_tier(), what="dtel create")
        require_customer_namespace(name, what=obj_type)
        require_transport(transport, what=f"{obj_type} create")
        require_tr_text(description, what="dtel description")
        require_all_labels(labels, expected=["short", "medium", "long", "heading"])
    except GuardrailViolation as gv:
        return gv.as_dict()

    blocker, warn = _maybe_reviewer("adt_dtel_create", name, obj_type, artifact_path)
    if blocker:
        return blocker

    client = _get_client()
    steps: dict[str, Any] = {}

    if _exists(client, name, obj_type):
        return {
            "ok": False,
            "error": "already_exists",
            "message": f"Data element {name} zaten mevcut.",
            "name": name,
            "type": obj_type,
        }
    steps["pre_check"] = "not_exists"

    try:
        with _capture() as buf:
            created = client.create_dataelement(
                name=name,
                domain_name=domain_name,
                description=description,
                package=package,
                transport=transport,
                short_label=short_label,
                medium_label=medium_label,
                long_label=long_label,
                heading_label=heading_label,
            )
        steps["create"] = {"ok": bool(created), "log": buf.getvalue().strip()}
    except Exception as exc:
        steps["create"] = _err_from_exc(exc)
        return {"ok": False, "name": name, "type": obj_type, "steps": steps}

    if not created:
        return {"ok": False, "name": name, "type": obj_type, "steps": steps,
                "message": "create_dataelement returned False"}

    tail = _activate_and_verify(client, name, obj_type)
    steps["activate"] = {"ok": tail.get("activated", False), "log": tail.get("activate_log", "")}
    if "activate_error" in tail:
        steps["activate"]["error"] = tail["activate_error"]
    steps["verify"] = {"ok": tail.get("verified", False)}
    if tail.get("master_language_warning"):
        steps["verify"]["master_language_warning"] = tail["master_language_warning"]

    ok_overall = steps["create"].get("ok") and tail.get("activated") and tail.get("verified")
    out = {
        "ok": bool(ok_overall),
        "name": name,
        "type": obj_type,
        "domain": domain_name,
        "steps": steps,
    }
    if warn:
        out["reviewer"] = warn["reviewer"]
    return out


# =============================================================================
# adt_struct_create
# =============================================================================

@profil_tool()
def adt_struct_create(
    name: str,
    fields: list[dict],
    description: str,
    package: str,
    transport: str,
    artifact_path: str | None = None,
) -> dict:
    """Create + activate + verify a DDIC structure (INTTAB) atomically.

    Reviewer (ADR 0006): if artifact_path given, run_review.py struct_creation runs;
    BLOCKER rejects (must fix and retry). Strongly recommended for Sprint 6 flow:
    coordinator generates a local .asddls via sprint6_adapt_struct.py, then passes
    that path here so the reviewer can validate DTEL activity and annotations.

    Args:
        name: Structure name (Z*/Y*).
        fields: [{'name':'FIELD1','type':'char10'}, {'name':'CUST','type':'ZSD000_E_CUST'}, ...]
                'type' is either ABAP primitive (char10, numc8, ...) or a data element name.
        description: TR description.
        package: Target package.
        transport: Modifiable transport.
        artifact_path: Path to local .asddls / .ddls / struct source for reviewer.

    Returns:
        {ok, name, type:'tabl', steps, fields_count, reviewer?, ...}
    """
    obj_type = "tabl"  # structures live in tabl namespace (intttab category)
    try:
        require_writable_tier(get_active_tier(), what="structure create")
        require_customer_namespace(name, what="structure")
        require_transport(transport, what="structure create")
        require_tr_text(description, what="structure description")
    except GuardrailViolation as gv:
        return gv.as_dict()
    if not fields or not isinstance(fields, list):
        return {"ok": False, "error": "validation_error",
                "message": "fields boş olamaz — en az 1 field gerekli"}
    for i, f in enumerate(fields):
        if not isinstance(f, dict) or not f.get("name") or not f.get("type"):
            return {"ok": False, "error": "validation_error",
                    "message": f"fields[{i}] geçersiz — 'name' ve 'type' zorunlu"}

    blocker, warn = _maybe_reviewer("adt_struct_create", name, obj_type, artifact_path)
    if blocker:
        return blocker

    client = _get_client()
    steps: dict[str, Any] = {}

    if _exists(client, name, obj_type):
        return {
            "ok": False,
            "error": "already_exists",
            "message": f"Structure {name} zaten mevcut.",
            "name": name,
            "type": obj_type,
        }
    steps["pre_check"] = "not_exists"

    try:
        with _capture() as buf:
            created = client.create_structure(
                name=name,
                fields=fields,
                description=description,
                package=package,
                transport=transport,
            )
        steps["create"] = {"ok": bool(created), "log": buf.getvalue().strip()}
    except Exception as exc:
        steps["create"] = _err_from_exc(exc)
        return {"ok": False, "name": name, "type": obj_type, "steps": steps}

    if not created:
        return {"ok": False, "name": name, "type": obj_type, "steps": steps,
                "message": "create_structure returned False"}

    tail = _activate_and_verify(client, name, obj_type)
    steps["activate"] = {"ok": tail.get("activated", False), "log": tail.get("activate_log", "")}
    if "activate_error" in tail:
        steps["activate"]["error"] = tail["activate_error"]
    steps["verify"] = {"ok": tail.get("verified", False)}
    if tail.get("master_language_warning"):
        steps["verify"]["master_language_warning"] = tail["master_language_warning"]
    if "verify_reason" in tail:
        steps["verify"]["reason"] = tail["verify_reason"]
    if "sap_version" in tail:
        steps["verify"]["sap_version"] = tail["sap_version"]

    # Sprint 6 T10 — post-create consistency check (placeholder + field count diff).
    # adt_struct_create fields[] yöntemi bazen SAP'de sadece placeholder bırakır.
    # artifact_path verilmişse, lokal artifact ile SAP'deki source'u karşılaştır.
    consistency_ok = True
    if artifact_path:
        consistency = run_reviewer("struct_post_create", artifact_path)
        steps["post_check"] = {
            "ok": consistency.passed,
            "verdict": consistency.verdict,
            "blocker_count": consistency.blocker_count,
            "warning_count": consistency.warning_count,
        }
        if consistency.skip_reason:
            steps["post_check"]["skip_reason"] = consistency.skip_reason
        consistency_ok = consistency.passed

    ok_overall = (steps["create"].get("ok") and tail.get("activated")
                  and tail.get("verified") and consistency_ok)
    out = {
        "ok": bool(ok_overall),
        "name": name,
        "type": obj_type,
        "fields_count": len(fields),
        "steps": steps,
    }
    if warn:
        out["reviewer"] = warn["reviewer"]
    return out
