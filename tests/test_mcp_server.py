"""MCP server tested in-memory through the official client."""
import json

import anyio

from brightroom.mcp_server import server
from mcp.client import Client


def _call(tool, args):
    async def go():
        async with Client(server) as c:
            r = await c.call_tool(tool, args)
            return r, (r.structured_content or (json.loads(r.content[0].text) if not r.is_error else None))
    return anyio.run(go)


def test_lists_tools_prompt_resource():
    async def go():
        async with Client(server) as c:
            return ({t.name for t in (await c.list_tools()).tools},
                    {p.name for p in (await c.list_prompts()).prompts},
                    {str(r.uri) for r in (await c.list_resources()).resources})
    tools, prompts, resources = anyio.run(go)
    assert tools == {"analyse_enquiry", "price_brief", "check_draft", "get_catalogue"}
    assert prompts == {"proposal_workflow"} and resources == {"brightroom://catalogue"}


def test_analyse_enquiry_q2():
    _, d = _call("analyse_enquiry", {"enquiry": "20 people, 4 hours, coffee and lunch are required. Total budget €850."})
    assert d["status"] == "INFEASIBLE" and d["package"]["total_eur"] == 940 and d["budget_margin_eur"] == -90


def test_price_brief_wheelchair_never_studio():
    _, d = _call("price_brief", {"headcount": 6, "duration_hours": 4, "budget_eur": 300,
                                 "services_required": ["S1"], "wheelchair_access": True})
    assert d["package"]["venue"].startswith("V2") and d["package"]["total_eur"] == 468
    assert d["status"] == "INFEASIBLE"


def test_check_draft_flags_invented_price_and_promise():
    _, d = _call("check_draft", {"text": "Your Loft is booked for €799 with a 10% discount!",
                                 "enquiry": "20 people, 4 hours, coffee and lunch. Budget €850."})
    assert not d["ok"] and len(d["problems"]) >= 3


def test_invalid_service_rejected():
    r, _ = _call("price_brief", {"headcount": 5, "services_required": ["S9"]})
    assert r.is_error
