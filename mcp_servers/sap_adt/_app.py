"""Shared FastMCP instance and infrastructure.

Imported by server.py (entry point) and tools/*.py (tool registration).
Lives separately to avoid circular imports.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

logging.basicConfig(
    level=os.getenv("SAP_ADT_MCP_LOG", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("sap-adt-mcp")

mcp = FastMCP(
    name="sap-adt",
    instructions=(
        "SAP ABAP Development Tools (ADT) — typed tool layer. "
        "Hardcoded ADR 0005 guardrails: Z/Y prefix mandatory, TR text required, "
        "no standard object modification, no transport release."
    ),
)


def profil_tool(available_on: tuple = ("all",)):
    """`@mcp.tool()` yerine kullanılır — profil uymuyorsa tool HİÇ register edilmez (D34d).

    Prompt'a "bu tool'u kullanma" demek ricadır; `tools/list`'ten gizlemek sınırdır.
    Profil çözülemiyorsa (project.yaml eksik/bozuk) fail-closed: hiçbir tool açılmaz.
    Gerekçe + kanıt disiplini: `mcp_servers/sap_adt/_profile.py`.
    """
    from mcp_servers.sap_adt._profile import aktif_profil, uygun_mu

    def sarmalayici(fn):
        profil = aktif_profil()
        if not uygun_mu(available_on, profil):
            log.warning(
                "tool GİZLENDİ: %s (profil=%s, available_on=%s)",
                getattr(fn, "__name__", "?"), profil, available_on,
            )
            return fn  # register EDİLMEZ; import hatası olmasın diye fonksiyon döner
        return mcp.tool()(fn)

    return sarmalayici
