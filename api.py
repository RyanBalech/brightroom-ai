"""HTTP API over the engine, and the server for the React front end (web/).

    python api.py                       # http://localhost:8611  (serves web/dist if built)
    uvicorn api:app --reload --port 8000  # API only, for `npm run dev` in web/
"""
from __future__ import annotations

import json
import pathlib
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from brightroom import llm
from brightroom.catalogue import VENUES
from brightroom.pipeline import run
from brightroom.serialize import catalogue_dict, result_to_dict

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "web" / "dist"
CASE_FILES = {"Designed": "cases.json", "Blind 1": "heldout_cases.json", "Blind 2": "blind2_cases.json"}

app = FastAPI(title="BrightRoom proposal API", version="1.0.0")


class AnalyseIn(BaseModel):
    enquiry: str = Field(min_length=1, max_length=5000)
    use_llm: bool | None = None


def _cases(fname: str) -> list[dict]:
    return json.loads((ROOT / "eval" / fname).read_text())


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "llm_available": llm.llm_available(), "model": llm.MODEL}


@app.get("/api/catalogue")
def catalogue() -> dict:
    return catalogue_dict()


@app.get("/api/cases")
def cases() -> list[dict]:
    return [{"id": c["id"], "type": c["type"], "source": c["source"], "enquiry": c["enquiry"],
             "expected": c["expected"]["behaviour"]} for c in _cases("cases.json")]


@app.post("/api/analyse")
def analyse(body: AnalyseIn) -> dict:
    use_llm = body.use_llm if body.use_llm is not None else llm.llm_available()
    if use_llm and not llm.llm_available():
        raise HTTPException(400, "Claude mode requested but ANTHROPIC_API_KEY is not set.")
    out = run(body.enquiry, use_llm=use_llm)
    r = out.result
    d = result_to_dict(r)
    d.update({
        "venue_name": VENUES[r.package.venue_id].name if r.package else None,
        "headcount": r.brief.headcount,
        "client_draft_markdown": out.client_md,
        "cover_source": out.cover_source,
        "audit_violations": out.audit_violations,
        "llm_errors": out.llm_errors,
        "seconds": round(out.seconds, 3),
        "issues": [{"code": i.code, "severity": i.severity, "message": i.message} for i in r.issues],
    })
    return d


@app.post("/api/eval")
def run_eval() -> dict:
    """Re-run every test set deterministically (rules mode)."""
    from eval.run_eval import check
    sets, rows = {}, []
    for label, fname in CASE_FILES.items():
        n_ok = 0
        cs = _cases(fname)
        for c in cs:
            o = run(c["enquiry"], use_llm=False)
            ok, fails = check(c, o)
            n_ok += ok
            rows.append({"set": label, "id": c["id"], "type": c["type"], "status": o.result.status,
                         "total": o.result.package.total if o.result.package else None, "pass": ok, "fails": fails})
        sets[label] = {"passed": n_ok, "total": len(cs)}
    return {"sets": sets, "rows": rows}


@app.get("/api/baseline")
def baseline() -> list[dict]:
    """Rubric judgements of the single-prompt baseline (eval/results_baseline.md)."""
    out = []
    for line in (ROOT / "eval" / "results_baseline.md").read_text().splitlines():
        m = re.match(r"\| (T\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$", line)
        if m:
            out.append({"id": m.group(1), "expected": m.group(2).strip(), "baseline": m.group(3).strip(),
                        "judgement": m.group(4).strip()})
    return out


# ---- front end (built React app) -------------------------------------------------------------
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8611)
