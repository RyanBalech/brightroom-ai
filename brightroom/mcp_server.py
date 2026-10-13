"""BrightRoom MCP server: the proposal engine as tools for Claude Desktop / Claude Code / any MCP host.

The host LLM does the conversation and the writing; these tools do every number and every
feasibility decision. Run:  python -m brightroom.mcp_server   (stdio transport)
"""
from __future__ import annotations

import json
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from .brief import Brief
from .catalogue import catalogue_as_text
from .draft import audit_text, render_client_draft, render_review, template_cover_note
from .engine import evaluate
from .extract_rules import extract_rules
from .serialize import catalogue_dict, result_to_dict

ServiceId = Literal["S1", "S2", "S3", "S4"]
READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)

server = MCPServer(
    name="brightroom",
    title="BrightRoom proposal engine",
    version="1.0.0",
    instructions=(
        "Tools for BrightRoom's salesperson. Prices, venue choice and feasibility come ONLY from these tools — "
        "never compute or invent a price yourself. Typical flow: analyse_enquiry (or price_brief with fields you "
        "extracted) -> write the client message using only the returned figures -> check_draft on your text -> "
        "present it as a DRAFT for salesperson approval. Never confirm a booking or date, never offer a discount "
        "or an unlisted service."
    ),
)


@server.tool(title="Analyse a client enquiry", annotations=READ_ONLY)
def analyse_enquiry(enquiry: str) -> dict:
    """Turn a free-text client enquiry (English or French) into a structured brief, a feasibility status
    (READY_FOR_REVIEW / PROVISIONAL / INFEASIBLE / NEEDS_CLARIFICATION), an itemised package, alternatives with
    explicit trade-offs, and questions for the client. Uses the deterministic rule extractor; if you read the
    enquiry differently, call price_brief with your corrected fields."""
    r = evaluate(extract_rules(enquiry))
    out = result_to_dict(r)
    out["client_draft_markdown"] = render_client_draft(r, template_cover_note(r))
    out["salesperson_review_markdown"] = render_review(r)
    return out


@server.tool(title="Price a structured brief", annotations=READ_ONLY)
def price_brief(
    headcount: int | None = None,
    duration_hours: float | None = None,
    budget_eur: float | None = None,
    services_required: list[ServiceId] | None = None,
    services_optional: list[ServiceId] | None = None,
    wheelchair_access: bool | None = None,
    headcount_approx: bool = False,
    facilitator_hours: float | None = None,
    allergen_guarantee_requested: bool = False,
    dietary: list[str] | None = None,
    unlisted_required: list[str] | None = None,
    unlisted_optional: list[str] | None = None,
    keep_together: bool = False,
    date_text: str | None = None,
    asks_confirmation: bool = False,
    asks_discount: bool = False,
) -> dict:
    """Evaluate a brief you extracted yourself. Services: S1 coffee break, S2 lunch, S3 projector,
    S4 facilitator. Leave a field null when the client did not state it (the engine then asks or labels an
    assumption — do not guess). wheelchair_access: true = needed, false = client said not needed, null = not
    mentioned. Returns the same structure as analyse_enquiry."""
    b = Brief(
        headcount=headcount, headcount_approx=headcount_approx, duration_hours=duration_hours,
        budget_eur=budget_eur, services_required=list(services_required or []),
        services_optional=list(services_optional or []), facilitator_hours=facilitator_hours,
        wheelchair_access=wheelchair_access, dietary=list(dietary or []),
        allergen_guarantee_requested=allergen_guarantee_requested,
        unlisted_required=list(unlisted_required or []), unlisted_requests=list(unlisted_optional or []),
        keep_together=keep_together, date_text=date_text, asks_confirmation=asks_confirmation,
        asks_discount=asks_discount, extractor="mcp-host",
    )
    r = evaluate(b)
    out = result_to_dict(r)
    out["client_draft_markdown"] = render_client_draft(r, template_cover_note(r))
    return out


@server.tool(title="Audit a draft before sending", annotations=READ_ONLY)
def check_draft(text: str, enquiry: str) -> dict:
    """Audit client-facing text against the engine's result for this enquiry. Flags euro amounts the engine
    did not produce, booking/date/availability promises, discounts, guarantees and unlisted services presented
    as available. Call this on every message before showing it as ready to send."""
    r = evaluate(extract_rules(enquiry))
    problems = audit_text(text, r)
    return {"ok": not problems, "problems": problems, "status_of_enquiry": r.status,
            "allowed_euro_amounts": sorted(r.allowed_amounts)}


@server.tool(title="Get the approved catalogue", annotations=READ_ONLY)
def get_catalogue() -> dict:
    """The only venues, services, prices and rules BrightRoom may offer."""
    return catalogue_dict()


@server.resource("brightroom://catalogue", name="catalogue", title="Approved catalogue",
                 mime_type="application/json")
def catalogue_resource() -> str:
    return json.dumps(catalogue_dict(), indent=2, ensure_ascii=False)


@server.prompt(title="Draft a proposal from an enquiry")
def proposal_workflow(enquiry: str) -> str:
    """Step-by-step workflow for turning one client enquiry into a reviewed draft."""
    return f"""You are helping BrightRoom's salesperson answer this client enquiry:

<enquiry>
{enquiry}
</enquiry>

{catalogue_as_text()}

1. Call `analyse_enquiry`. Read the brief; if you understand the enquiry differently (e.g. a phrase the rules
   missed), call `price_brief` with the corrected fields and say what you changed.
2. Report the status first, in one line, with the blockers and the budget margin.
3. If the status is NEEDS_CLARIFICATION, write only the questions. Otherwise write a short, warm client message
   in the client's language, using ONLY figures returned by the tools. If INFEASIBLE, say plainly what cannot be
   met and present the alternatives with their trade-offs — never as if they met the request.
4. Call `check_draft` on your message and fix every problem it reports.
5. Present the result as a DRAFT for salesperson approval. Do not confirm, book, promise a date, offer a discount,
   or mention any service outside the catalogue as available."""


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
