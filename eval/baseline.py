"""Baseline: a single prompt, as a salesperson would paste into a chat assistant.

    python -m eval.baseline            # needs ANTHROPIC_API_KEY; writes eval/baseline_outputs/<id>.md

The recorded baseline outputs in eval/baseline_outputs/ were produced with exactly this prompt
(see README for how they were generated).
"""
from __future__ import annotations

import json
import os
import pathlib

from brightroom.catalogue import catalogue_as_text

HERE = pathlib.Path(__file__).parent

BASELINE_PROMPT = """You are a sales assistant at BrightRoom, a studio that organises half-day workshops for \
small companies. Using only the catalogue below, write a proposal for this client enquiry, with itemised \
prices and a total.

{catalogue}

Client enquiry: {enquiry}"""


def build_prompt(enquiry: str) -> str:
    return BASELINE_PROMPT.format(catalogue=catalogue_as_text(), enquiry=enquiry)


def main() -> None:
    import anthropic
    client = anthropic.Anthropic()
    model = os.environ.get("BRIGHTROOM_MODEL", "claude-opus-5")
    out_dir = HERE / "baseline_outputs"
    out_dir.mkdir(exist_ok=True)
    for c in json.loads((HERE / "cases.json").read_text()):
        resp = client.messages.create(model=model, max_tokens=4000,
                                      messages=[{"role": "user", "content": build_prompt(c["enquiry"])}])
        text = "".join(b.text for b in resp.content if b.type == "text")
        (out_dir / f"{c['id']}.md").write_text(text)
        print(c["id"], "done")


if __name__ == "__main__":
    main()
