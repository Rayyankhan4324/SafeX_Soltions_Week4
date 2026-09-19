"""Run a low-volume SafeX spa website quality audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from spa_auditor.auditor import SpaAuditor
from spa_auditor.llm import pending_judgment, review_with_openai
from spa_auditor.reporting import write_reports


def load_sites(path: Path) -> list[dict[str, str]]:
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    sites = data.get("sites") if isinstance(data, dict) else data
    if not isinstance(sites, list) or not sites:
        raise ValueError("Site file must contain a non-empty 'sites' list.")
    if not 1 <= len(sites) <= 8:
        raise ValueError("Use between 1 and 8 sites to keep the review low volume.")
    for index, site in enumerate(sites, start=1):
        if not isinstance(site, dict) or not all(key in site for key in ("name", "url", "authorization")):
            raise ValueError(f"Site #{index} needs name, url, and authorization fields.")
    return sites


def main() -> int:
    parser = argparse.ArgumentParser(description="Low-volume quality audit for approved spa websites.")
    parser.add_argument("--sites", type=Path, required=True, help="JSON file containing 1-8 approved/public-read-only sites.")
    parser.add_argument("--output", type=Path, default=Path("reports"), help="Folder for JSON, CSV, Markdown, and HTML reports.")
    parser.add_argument("--max-pages", type=int, default=4, help="Maximum HTML pages per site (1-8; default 4).")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay in seconds between sampled pages (default 1.5).")
    parser.add_argument("--timeout", type=float, default=12.0, help="Request timeout in seconds (default 12).")
    parser.add_argument("--llm", action="store_true", help="Use the optional OpenAI structured-output review. Requires OPENAI_API_KEY.")
    parser.add_argument("--model", help="Optional OpenAI model override. Defaults to OPENAI_MODEL or gpt-4.1-mini.")
    args = parser.parse_args()
    try:
        sites = load_sites(args.sites)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    auditor = SpaAuditor(args.max_pages, args.delay, args.timeout)
    records: list[dict[str, Any]] = []
    for site in sites:
        print(f"Reviewing {site['name']} (small sample; max {args.max_pages} pages)...")
        result = auditor.audit_site(site)
        judgment = review_with_openai(result.facts, args.model) if args.llm else pending_judgment("LLM review was not requested. Run again with --llm after setting OPENAI_API_KEY.")
        records.append({
            "name": result.name,
            "url": result.url,
            "authorization": result.authorization,
            "automatically_detected_facts": result.facts,
            "ai_judgment": judgment,
        })
    try:
        paths = write_reports(records, args.output)
    except OSError as exc:
        print(f"Could not write reports to '{args.output}': {exc}", file=sys.stderr)
        return 2
    print("Finished. Reports written to:")
    for kind, path in paths.items():
        print(f"  {kind}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
