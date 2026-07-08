"""SAP ADT MCP Server — entry point.

Run as:
    python -m mcp_servers.sap_adt.server

Or registered in .claude/settings.json mcpServers section.

Tools register via decorators in mcp_servers/sap_adt/tools/*.py — importing those
modules triggers registration on the shared FastMCP instance (mcp_servers.sap_adt._app.mcp).

ADR: governance/decisions/0007-sap-adt-mcp-server.md
"""
from __future__ import annotations

from mcp_servers.sap_adt._app import mcp, log


@mcp.tool()
def ping() -> dict:
    """Sanity check — verifies MCP server is alive and reachable.

    Returns server name, version, and repo root.
    """
    from mcp_servers.sap_adt import __version__
    from mcp_servers.sap_adt._app import REPO_ROOT
    return {
        "ok": True,
        "service": "sap-adt-mcp",
        "version": __version__,
        "repo_root": str(REPO_ROOT),
    }


def _register_all() -> None:
    """Import tool modules so their @mcp.tool() decorators register."""
    from mcp_servers.sap_adt.tools import atom, composite, query  # noqa: F401
    log.info("Registered tool modules: atom, composite, query")


def main() -> None:
    _register_all()
    # Açılışta canlı bağlantı state'ini .conn_adt'den yaz → /mcp restart sonrası
    # statusline'daki "MCP farklı sisteme bakıyor" uyarısı ilk tool çağrısını
    # beklemeden (otomatik) güncellenir.
    from mcp_servers.sap_adt._conn import write_mcp_binding_state
    write_mcp_binding_state()
    log.info("SAP ADT MCP server starting (stdio transport)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
