"""Live SAP integration test — yarat + sil bir test DTEL üzerinden.

⚠ Bu test GERÇEK SAP'a yazar. VPN açık, transport modifiable olmalı.

Akış:
  1. adt_transport_list → kullanıcı transport'unu listele
  2. adt_get(ZSD001_E_MCPTEST) → not_found bekle (önceki kalıntı varsa fail)
  3. adt_dtel_create → composite (reviewer SKIP, guardrails OK, create+activate+verify)
  4. adt_get → exists+active bekle
  5. adt_delete → ok bekle
  6. adt_get → not_found bekle (silindiğini doğrula)

Run:
    python -m mcp_servers.sap_adt.tests.integration_dtel

Args (env):
    MCP_TEST_TRANSPORT  — kullanılacak transport (default: <TRANSPORT>)
    MCP_TEST_PACKAGE    — paket (default: ZSD001_CLC)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TEST_NAME = "ZSD001_E_MCPTEST"
TEST_TYPE = "dtel"
DEFAULT_TRANSPORT = "<TRANSPORT>"
DEFAULT_PACKAGE = "ZSD001_CLC"
# Active Z domain from ZSD001_CLC package (created in Sprint 6, 2026-05-14).
DOMAIN = "ZSD001_D_DEMDT"


def _force_utf8():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _text(result) -> str:
    if not result.content:
        return ""
    return "\n".join(c.text for c in result.content if hasattr(c, "text"))


def _json(result) -> dict:
    txt = _text(result)
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw": txt}


def _hdr(title: str):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def main() -> int:
    _force_utf8()
    transport = os.getenv("MCP_TEST_TRANSPORT", DEFAULT_TRANSPORT)
    package = os.getenv("MCP_TEST_PACKAGE", DEFAULT_PACKAGE)

    repo_root = Path(__file__).resolve().parents[3]
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.sap_adt.server"],
        cwd=str(repo_root),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    failures: list[str] = []

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            _hdr(f"MCP server up — {len(tool_names)} tools")
            print(", ".join(sorted(tool_names)))

            if "adt_delete" not in tool_names:
                print("FAIL: adt_delete missing")
                return 1

            # 1. transport_list — sanity (gerçek transport olduğunu doğrula)
            _hdr("Step 1: adt_transport_list")
            r = await session.call_tool("adt_transport_list", {})
            d = _json(r)
            tlist = d.get("transports", [])
            print(f"Found {len(tlist)} transports")
            for t in tlist[:5]:
                print(f"  {t.get('number')}  [{t.get('status')}]  {t.get('description')}")
            found = any(t.get("number") == transport for t in tlist)
            if not found:
                print(f"WARN: target transport {transport} not in list — devam ediyorum, SAP üzerinden yine de denenecek")

            # 2. Pre-check: test DTEL var mı? (önceki test kalıntısı olabilir)
            _hdr(f"Step 2: adt_get({TEST_NAME}) — pre-check")
            r = await session.call_tool(
                "adt_get",
                {"name": TEST_NAME, "object_type": TEST_TYPE, "include_source": False},
            )
            d = _json(r)
            exists_before = d.get("exists", False)
            print(f"exists: {exists_before}")
            if exists_before:
                print(f"WARN: {TEST_NAME} mevcut — sil ve tekrar dene")
                # Try to clean up first
                r = await session.call_tool(
                    "adt_delete",
                    {"name": TEST_NAME, "object_type": TEST_TYPE, "transport": transport},
                )
                print(f"cleanup delete: {_json(r).get('ok')}")

            # 3. Create
            _hdr(f"Step 3: adt_dtel_create({TEST_NAME})")
            r = await session.call_tool(
                "adt_dtel_create",
                {
                    "name": TEST_NAME,
                    "domain_name": DOMAIN,
                    "description": "MCP Test DTEL (otomatik silinecek)",
                    "package": package,
                    "transport": transport,
                    "short_label": "MCP Tst",
                    "medium_label": "MCP Test DTEL",
                    "long_label": "MCP Server Test Data Element",
                    "heading_label": "MCP Test",
                },
            )
            d = _json(r)
            print(json.dumps({k: v for k, v in d.items() if k not in ("steps",)}, indent=2, ensure_ascii=False))
            print("steps:")
            for step, val in (d.get("steps") or {}).items():
                if isinstance(val, dict):
                    print(f"  {step}: ok={val.get('ok')}")
                    if val.get("log"):
                        for line in str(val["log"]).splitlines():
                            print(f"      | {line}")
                    if val.get("error"):
                        print(f"      ERROR: {val['error']}")
                else:
                    print(f"  {step}: {val}")
            if not d.get("ok"):
                failures.append("create_failed")
                print("FAIL: create not ok")

            # 4. Verify exists
            _hdr(f"Step 4: adt_get({TEST_NAME}) — post-create")
            r = await session.call_tool(
                "adt_get",
                {"name": TEST_NAME, "object_type": TEST_TYPE, "include_source": False},
            )
            d = _json(r)
            print(f"ok={d.get('ok')}  exists={d.get('exists')}")
            if not d.get("exists"):
                failures.append("post_create_missing")
                print("FAIL: created but not found")

            # 5. Delete
            _hdr(f"Step 5: adt_delete({TEST_NAME})")
            r = await session.call_tool(
                "adt_delete",
                {"name": TEST_NAME, "object_type": TEST_TYPE, "transport": transport},
            )
            d = _json(r)
            print(f"ok={d.get('ok')}  deleted={d.get('deleted')}")
            if d.get("client_log"):
                print(f"client_log:\n  {d['client_log']}")
            if not d.get("ok"):
                failures.append("delete_failed")
                print("FAIL: delete not ok")

            # 6. Verify gone
            _hdr(f"Step 6: adt_get({TEST_NAME}) — post-delete")
            r = await session.call_tool(
                "adt_get",
                {"name": TEST_NAME, "object_type": TEST_TYPE, "include_source": False},
            )
            d = _json(r)
            print(f"ok={d.get('ok')}  exists={d.get('exists')}")
            if d.get("exists"):
                failures.append("post_delete_still_present")
                print("FAIL: still present after delete")

    _hdr("Result")
    if failures:
        print(f"FAILED ({len(failures)}): {failures}")
        return 1
    print("ALL STEPS PASSED — MCP yarat + sil senaryosu OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
