"""Reviewer (ADR 0006) integration for MCP tools.

Wraps scripts/validators/run_review.py — calls it as a subprocess with --json,
parses the verdict, and returns a structured result MCP tools can act on.

Used by composite tools and adt_push_source as a mandatory pre-flight (BLOCKER
rejects the tool call). Manual CLI usage (`python scripts/validators/run_review.py
...`) remains a parallel option for local-only drafts.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from mcp_servers.sap_adt._app import REPO_ROOT, log

_REVIEW_SCRIPT = REPO_ROOT / "scripts" / "validators" / "run_review.py"

# Object type → reviewer task name. Tools pass object_type; we map to a known task.
# Tasks must exist in run_review.py TASK_VALIDATORS dict.
OBJECT_TYPE_TO_TASK = {
    "ddls": "cds_update",     # CDS view source push
    "tabl": "table_update",   # table or structure
    "doma": None,             # no validator chain defined yet (domain_creation_csv is CSV-batch)
    "dtel": None,             # dtel_update validators not defined yet
    "msag": None,
    "prog": None,
    "class": None,
}

# Composite tool name → task for its created object.
COMPOSITE_TOOL_TO_TASK = {
    "adt_struct_create": "struct_creation",
    "adt_domain_create": None,   # no validators yet — gracefully PASS
    "adt_dtel_create": None,     # no validators yet
}


class ReviewerResult:
    """Structured result from run_review.py invocation."""

    __slots__ = ("verdict", "blocker_count", "warning_count", "results",
                 "skipped", "skip_reason", "raw")

    def __init__(
        self,
        verdict: str,
        blocker_count: int = 0,
        warning_count: int = 0,
        results: Optional[list] = None,
        skipped: bool = False,
        skip_reason: str = "",
        raw: Optional[dict] = None,
    ):
        self.verdict = verdict  # PASS | WARNING | BLOCKER | SKIP
        self.blocker_count = blocker_count
        self.warning_count = warning_count
        self.results = results or []
        self.skipped = skipped
        self.skip_reason = skip_reason
        self.raw = raw or {}

    @property
    def passed(self) -> bool:
        return self.verdict in ("PASS", "SKIP")

    @property
    def is_blocker(self) -> bool:
        return self.verdict == "BLOCKER"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "blocker_count": self.blocker_count,
            "warning_count": self.warning_count,
            "results": self.results,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


def run_reviewer(task: Optional[str], artifact_path: Optional[str],
                 ack_drop: str = "") -> ReviewerResult:
    """Invoke scripts/validators/run_review.py and parse its JSON output.

    Args:
        task: reviewer task type (e.g., 'struct_creation', 'cds_update').
              None → skip (no task mapped yet for this tool/type).
        artifact_path: path to the local file to review. Must exist on disk.
                       None → skip (coordinator did not provide an artifact).
        ack_drop: comma-separated field names whose table DROP is explicitly
                  approved (user+lead, ADR 0005-B). Forwarded to run_review's
                  --ack-drop → ONLY these named drops become ACK-WARNING; any
                  un-named drop or any TYPE/RENAME change still BLOCKER. Empty
                  → no acknowledgement (default; full drop-guard).

    Returns:
        ReviewerResult — coordinator-friendly verdict + details.
        verdict='SKIP' when task or artifact missing (gracefully proceed).
    """
    if not task:
        return ReviewerResult(verdict="SKIP", skipped=True,
                              skip_reason="no_reviewer_task_for_this_operation")
    if not artifact_path:
        return ReviewerResult(verdict="SKIP", skipped=True,
                              skip_reason="no_artifact_path_provided")

    artifact = Path(artifact_path)
    if not artifact.is_absolute():
        artifact = REPO_ROOT / artifact_path
    if not artifact.exists():
        return ReviewerResult(verdict="SKIP", skipped=True,
                              skip_reason=f"artifact_not_found:{artifact}")

    if not _REVIEW_SCRIPT.exists():
        log.error("run_review.py not found at %s", _REVIEW_SCRIPT)
        return ReviewerResult(verdict="SKIP", skipped=True,
                              skip_reason="run_review_script_missing")

    cmd = [
        sys.executable,
        str(_REVIEW_SCRIPT),
        "--task", task,
        "--artifact", str(artifact),
        "--json",
    ]
    if ack_drop:
        # Hedefli onaylı-DROP ack — yalnız drop-guard'a iletilir (run_review içinde
        # check_table_field_drop'a geçer). Blanket bypass DEĞİL: isimsiz drop/tip
        # değişikliği yine BLOCKER. ADR 0005-B kullanıcı+lider bilinçli onayı.
        cmd += ["--ack-drop", ack_drop]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            # stdin=DEVNULL ZORUNLU: MCP server type=stdio → JSON-RPC'yi stdin/stdout
            # pipe'tan konuşur. Bunu vermezsek çocuk subprocess parent'ın stdin pipe
            # handle'ını miras alır ve Windows'ta bloke olur → her çağrı 120s donardı
            # (standalone 0.6s; bug spawn'da, script'te değil). Bkz. _reviewer-stdio-deadlock.
            stdin=subprocess.DEVNULL,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        # Timeout ≠ ihlal. Eskiden BLOCKER (0/0) döndürüp meşru push'u bloklıyordu
        # (2026-06-10 reviewer-kör vakası). Artık non-blocking WARNING: push geçer
        # ama coordinator manuel run_review.py çalıştırmalı (asıl gate zaten manuel).
        log.warning("Reviewer timeout for task=%s artifact=%s — WARNING (manuel review öner)",
                    task, artifact)
        return ReviewerResult(
            verdict="WARNING", skipped=False, warning_count=1,
            skip_reason=("reviewer_timeout — MCP içi reviewer 30s aştı; push bloke "
                         "EDİLMEDİ. Manuel doğrula: python scripts/validators/run_review.py "
                         f"--task {task} --artifact <path>"))
    except Exception as exc:
        log.warning("Reviewer subprocess error: %s", exc)
        return ReviewerResult(verdict="SKIP", skipped=True,
                              skip_reason=f"reviewer_exception:{exc}")

    # Parse JSON from stdout. run_review.py with --json emits structured payload.
    raw: dict = {}
    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError:
        # Best-effort: pick last JSON object in output
        try:
            tail = proc.stdout.rfind("{")
            if tail >= 0:
                raw = json.loads(proc.stdout[tail:])
        except Exception:
            raw = {}

    verdict = raw.get("verdict", "BLOCKER" if proc.returncode == 1 else "SKIP")
    return ReviewerResult(
        verdict=verdict,
        blocker_count=int(raw.get("blocker_count", 0)),
        warning_count=int(raw.get("warning_count", 0)),
        results=raw.get("results", []),
        raw=raw,
    )


def task_for_push(object_type: str) -> Optional[str]:
    """Resolve reviewer task for adt_push_source by object type."""
    return OBJECT_TYPE_TO_TASK.get((object_type or "").lower())


def task_for_composite(tool_name: str) -> Optional[str]:
    """Resolve reviewer task for a composite tool by its name."""
    return COMPOSITE_TOOL_TO_TASK.get(tool_name)


def reject_payload(name: str, object_type: str, result: ReviewerResult) -> dict:
    """Build the MCP error payload when reviewer returns BLOCKER."""
    return {
        "ok": False,
        "error": "reviewer_blocker",
        "message": (
            f"Reviewer pre-flight (ADR 0006) BLOCKER verdict: "
            f"{result.blocker_count} blocker, {result.warning_count} warning. "
            f"Düzelt ve tekrar dene. Manuel: "
            f"python scripts/validators/run_review.py --task <X> --artifact <path>"
        ),
        "name": name,
        "type": object_type,
        "reviewer": result.to_dict(),
    }
