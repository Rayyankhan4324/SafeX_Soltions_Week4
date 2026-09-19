# SafeX Week 4 — AI-Assisted Spa Website Quality Auditor

A low-volume, evidence-first audit tool for authorized spa-sector websites. It collects a small set of observable website signals, then optionally asks an LLM to turn those facts into a concise business-readiness assessment.

The central design rule is simple: **automatic observations and AI judgments never share a section or data field.** A reviewer can always see what the script detected, what the LLM inferred, and what still needs manual checking.

## What it checks

For up to eight sites, the auditor starts with the homepage and samples at most a configured number of same-domain HTML links. It records:

- Navigation labels and sampled-page count
- Contact forms, field count, contact-information hints, CTAs, booking-related CTAs, social links, and FAQ hints
- Homepage title and meta description, heading samples, local-business schema hint, and image alt-text coverage in the sampled pages
- Viewport-meta presence and one server-response timing measurement
- Robots.txt decisions, blocked pages, non-HTML pages, timeouts, and HTTP errors

It does **not** crawl a site, bypass controls, submit forms, log in, scan for vulnerabilities, test payments, or rate-test a server.

## Project structure

```text
audit.py                       Command-line entry point
spa_auditor/auditor.py         Polite fetcher, robots check, failures
spa_auditor/extractor.py       Rule-based HTML signals
spa_auditor/prompting.py       LLM prompt and strict output schema
spa_auditor/llm.py             Optional OpenAI structured-output review
spa_auditor/reporting.py       JSON, CSV, Markdown, and HTML reports
config/*.example.json          Safe site-list templates
tests/                         Offline unit tests
```

## Responsible-use boundary

Only include sites you own, have permission to review, or public sites where you are doing a small, read-only review. Record that status in the `authorization` field. The program accepts only `own_site`, `permission_granted`, and `public_read_only`; other values are skipped and documented in the report.

Keep the default small sample (four pages) and delay (1.5 seconds) unless you have written permission to do more. Review the relevant site terms and `robots.txt`; the program will stop when its user agent is disallowed by robots.txt.

## Setup

Python 3.10+ is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create your real configuration by copying one of the example files to `config/authorized_sites.json`. Do not commit private approval notes if the repository is public.

```json
{
  "sites": [
    {
      "name": "Harbour Calm Spa",
      "url": "https://example-spa.com/",
      "authorization": "permission_granted",
      "approval_note": "Email approval held by project owner, 2026-09-19."
    }
  ]
}
```

Use five to eight real, approved/public-read-only targets for the final course report. This repository intentionally ships with placeholders rather than claiming authorization for businesses that did not grant it.

## Run an extraction-only audit

```powershell
python audit.py --sites config/authorized_sites.json --output reports
```

Useful restraint controls:

```powershell
python audit.py --sites config/authorized_sites.json --output reports --max-pages 4 --delay 1.5 --timeout 12
```

The generated `reports/` folder contains:

- `audit_results.json` — machine-readable facts and LLM judgment in separate top-level fields
- `audit_summary.csv` — Website, Score, Problems, Missing Features, and Priority
- `audit_report.md` and `audit_report.html` — review-ready reports

Without an LLM request, the score is deliberately shown as **Awaiting LLM**. The tool does not invent a score or disguise a heuristic as an AI judgment.

## Add the optional LLM assessment

Set an API key in your local shell (never commit it), then run with `--llm`:

```powershell
$env:OPENAI_API_KEY = "your-key-here"
python audit.py --sites config/authorized_sites.json --output reports --llm
```

Optionally choose a permitted model:

```powershell
python audit.py --sites config/authorized_sites.json --output reports --llm --model gpt-4.1-mini
```

The LLM receives **only** the extracted facts and must return schema-constrained JSON: a 0–100 score, rationale, problems, likely missing features, prioritized recommendations, evidence, and human checks. If the key is missing, the API fails, or the JSON cannot be validated, the report remains usable and labels the judgment as pending. The integration uses the Responses API structured-output pattern described in the [official OpenAI documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

### LLM prompt design

The actual prompt lives in `spa_auditor/prompting.py`. Its important safeguards are:

1. Use only supplied facts; never invent a feature or absence.
2. Treat “not detected” as a weak signal, not proof of absence.
3. Give a specific evidence string for every recommendation.
4. Be more cautious when few pages loaded or a request failed.
5. Ask the human to verify visual/mobile behavior and real conversion flows.

## How to sanity-check five to eight results

Before sharing a score, manually review each website and record a short note next to it:

| Check | What to verify manually |
|---|---|
| Contact and booking | A visitor can find contact details and complete the intended flow. |
| Mobile behavior | The page works at a narrow viewport; viewport meta alone is not proof. |
| CTA quality | The prompt and destination make sense for a spa customer. |
| SEO basics | Page title and description are accurate, unique, and customer-facing. |
| Non-detections | Search relevant pages before reporting a missing form, FAQ, social account, or booking feature. |
| LLM judgment | Every problem and recommendation is supported by a recorded fact. |

If your judgment and the AI score diverge materially, keep the evidence, amend the prompt or facts if needed, and describe the discrepancy in your presentation. That is a stronger AI-product outcome than accepting an output blindly.

## Failure handling demonstrated

The program never crashes a whole batch because one target has an issue. It writes a failure entry for common cases:

- timeout or connection failure
- HTTP error
- non-HTML response
- robots.txt disallowance
- invalid URL or authorization field
- optional LLM/API or schema-validation failure

The offline tests include a timeout-style failure report and can be run with:

```powershell
python -B -m unittest discover -s tests -v
```

You can also exercise the complete command-line failure path without contacting a public website:

```powershell
python audit.py --sites config/failure_handling_demo.json --output reports/failure_demo
```

## Limitations and false-positive risks

- JavaScript-rendered pages, cookie banners, bot controls, and third-party widgets can hide content from a `requests`/BeautifulSoup extractor.
- A form might be a newsletter form rather than a booking/lead form. CTA keyword matching can also over-count irrelevant buttons.
- Image `alt` coverage is a sample ratio only. It does not establish accessible or meaningful alternative text.
- Response timing is one server request, not real-user page speed, Core Web Vitals, or a mobile performance test.
- A title, description, FAQ, social link, or schema “not detected” can be a false negative if it exists outside the small sample.
- The assessment is not a security audit, accessibility conformance review, legal review, or a substitute for business and design judgment.

## Submission checklist

- [ ] Replace placeholders with five to eight approved/public read-only spa sites.
- [ ] Keep authorization notes outside a public repository if sensitive.
- [ ] Run the tool with the default conservative sample and save `reports/`.
- [ ] Run `--llm` only after checking the factual extraction output.
- [ ] Manually sanity-check every final score and recommendation.
- [ ] Include the limitations above in your GitHub README or project presentation.
- [ ] Push this source code and your non-sensitive, final audit report to GitHub.
