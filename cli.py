"""Command-line entry point.

    python cli.py "20 people, 4 hours, coffee and lunch are required. Total budget €850."
    python cli.py --offline --file enquiry.txt
"""
import argparse
import sys

from brightroom.draft import brief_table
from brightroom.pipeline import run


def main() -> None:
    ap = argparse.ArgumentParser(description="BrightRoom enquiry -> draft proposal")
    ap.add_argument("enquiry", nargs="?", help="enquiry text (or use --file / stdin)")
    ap.add_argument("--file")
    ap.add_argument("--offline", action="store_true", help="rules only, no LLM calls")
    a = ap.parse_args()
    text = open(a.file).read() if a.file else (a.enquiry or sys.stdin.read())
    out = run(text, use_llm=False if a.offline else None)
    confirmed, optional, missing = brief_table(out.result.brief)
    print("=" * 72, "\nSTRUCTURED BRIEF  (extractor:", out.result.brief.extractor + ")")
    print("  Confirmed:", *confirmed, sep="\n    - ")
    print("  Optional / other:", *(optional or ["—"]), sep="\n    - ")
    print("  Missing:", *(missing or ["—"]), sep="\n    - ")
    print("=" * 72, "\nSALESPERSON REVIEW\n")
    print(out.review_md)
    print("=" * 72, f"\nCLIENT DRAFT  (cover note: {out.cover_source})\n")
    print(out.client_md)
    for e in out.llm_errors + [f"guardrail: {v}" for v in out.audit_violations]:
        print("!", e)
    print(f"\n[{out.seconds:.2f}s]")


if __name__ == "__main__":
    main()
