"""Smoke test — spawn the MCP server, list tools, call ping + guardrail check.

Run:
    python -m mcp_servers.sap_adt.tests.smoke
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _force_utf8():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _content_text(result) -> str:
    if not result.content:
        return ""
    parts = []
    for c in result.content:
        if hasattr(c, "text"):
            parts.append(c.text)
    return "\n".join(parts)


async def main() -> int:
    _force_utf8()
    repo_root = Path(__file__).resolve().parents[3]
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.sap_adt.server"],
        cwd=str(repo_root),
    )

    failures = 0

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"Registered tools ({len(tool_names)}): {tool_names}")

            expected = {
                "ping",
                # atom
                "adt_get", "adt_post_shell", "adt_push_source", "adt_activate",
                # composite
                "adt_domain_create", "adt_dtel_create", "adt_struct_create",
                # query
                "adt_search_objects", "adt_transport_list", "adt_lock_check",
            }
            missing = expected - set(tool_names)
            if missing:
                print(f"FAIL: missing tools: {missing}")
                failures += 1
            else:
                print("OK: all expected tools registered")

            # 1. ping
            res = await session.call_tool("ping", {})
            text = _content_text(res)
            print(f"\n[ping] {text[:200]}")
            if res.isError or '"ok": true' not in text:
                print("FAIL: ping did not return ok")
                failures += 1
            else:
                print("OK: ping")

            # 2. Guardrail block — adt_post_shell with non-Z name
            res = await session.call_tool(
                "adt_post_shell",
                {
                    "object_type": "doma",
                    "name": "VBAK",  # standart SAP table-like
                    "package": "ZSD000",
                    "transport": "<TRANSPORT>",
                    "description": "test",
                },
            )
            text = _content_text(res)
            print(f"\n[guardrail post_shell VBAK] {text[:300]}")
            if "ADR_0005_A" not in text or '"ok": false' not in text:
                print("FAIL: guardrail should have blocked standard-namespace name")
                failures += 1
            else:
                print("OK: guardrail blocked standard namespace")

            # 3. Guardrail block — empty transport
            res = await session.call_tool(
                "adt_post_shell",
                {
                    "object_type": "doma",
                    "name": "ZTEST_X",
                    "package": "ZSD000",
                    "transport": "",
                    "description": "test",
                },
            )
            text = _content_text(res)
            print(f"\n[guardrail empty transport] {text[:300]}")
            if "ADR_0005_C" not in text:
                print("FAIL: guardrail should have blocked empty transport")
                failures += 1
            else:
                print("OK: guardrail blocked empty transport")

    print()
    if failures == 0:
        print(f"ALL SMOKE CHECKS PASSED ({len(tool_names)} tools)")
        return 0
    print(f"FAILURES: {failures}")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
