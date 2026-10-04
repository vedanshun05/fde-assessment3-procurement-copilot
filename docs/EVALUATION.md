# Evaluation results and interpretation

## Measurement conditions

- Mode: **offline deterministic simulation**; no provider, no model, zero LLM calls and tokens.
- Python: 3.14.7, local Linux environment.
- Final expanded comparison: 32 versioned cases, three repetitions, 96 runs per architecture / 192 total.
- Architecture order alternates between repetitions. Both use identical source data, inputs, HTTP mock, deterministic engine, and final validation.
- Vendor facts are retrieved over HTTP. Date/conflict cases apply controlled overrides to fetched responses and copied registry files. The timeout is injected; NimbusAI's HTTP 503 is provided by the actual mock endpoint.
- Policy reference date: 2026-09-30. The system clock is used only for run timestamps/latency.
- Case-set SHA-256: `a193a46760f205fbcdc385cd7dbae01940c2c2c46c3db322e6716a3fb114e00d`.
- Measurement timestamp and all raw checks are recorded in `evals/results/offline/summary.json` and `runs.csv`.

## Final results

| Metric | A: Single | B: Staged |
| --- | ---: | ---: |
| Public minimum checks | 6/6 | 6/6 |
| Expanded runs passed | 96/96 | 96/96 |
| Expected next-action accuracy | 100% | 100% |
| Versioned policy expectations | 100% | 100% |
| Exact evidence-ledger provenance | 100% | 100% |
| Pending human-review handoff | 100% | 100% |
| Mean latency (ms) | 1.894 | 1.849 |
| Median latency (ms) | 1.743 | 1.695 |
| Executed tools per run | 5 | 5 |
| LLM calls / input tokens / output tokens | 0 / 0 / 0 | 0 / 0 / 0 |
| Live-model completion rate | Not measured | Not measured |

The 0.045 ms difference in mean timing is too small and specific to this simulation to establish an architecture advantage. No model latency or production-load measurement is included.

## What the checks establish

The expected actions, roles, flags, forbidden roles/flags, and missing-information expectations are versioned in `evals/cases.json`. Evaluation does not ask the solution to generate its own expected answers. Request IDs are replaced with evaluation IDs to catch public-ID lookup implementations.

Financial tests include $1,000/$1,000.01, $10,000/$10,000.01, $25,000/$25,000.01, available budget/one cent above, and new-vendor Legal review at $9,999.99/$10,000 with otherwise approved terms. Date tests include 365/366-day validity, future dates and conflicting dates. Other scenarios cover current vendors with employee/customer PII, production integration independent of a data label, source code, existing tools, unknown vendors/requesters, missing integrations, untrusted requester/registry/API notes, HTTP 503 and timeout.

Grounding checks require every final evidence item to appear unchanged in the tool trace's canonical ledger, with a valid ID. Unsupported model citations are failures. This verifies provenance, not an independent semantic judgment that every rationale is entailed by its sources.

Human-handoff checks require `human_review_required`, pending review status, reviewer roles, and a nonempty next step. Browser checks verify the exported package marks all reviewers pending and explicitly denies purchase authorization.

## Additional engineering validation

- **57 automated tests passed.** These include the ten starter integrity/API tests, exact boundaries, typed inputs, stale/invalid dates, timeouts, vendor identity validation, model refusals/invalid output/unsupported tools/citations/approval claims, independent staged reviewer context, policy drift, and secret-free API configuration.
- Fake model-client tests exercise real orchestration code while reporting no actual model-quality result.
- **Eight isolated headless browser checks passed** across intake, A/B, handoff export, missing-information/injection display, outage display, HTML-looking input, responsive layouts, and JavaScript errors. See `docs/screenshots/ui-verification.json`.
- The dependency stack emits one Starlette warning recommending `httpx2` for its future test-client path. Current tests pass; this warning is not an application error.
- Final visual review corrected the distinction between an empty registry date and a null API date: both mean missing, so they should require Security without a false source-conflict flag. A regression test and forbidden flags in new-vendor cases verify this behavior.

## Limits and next live experiment

Offline success does not establish LLM reasoning quality, live prompt-injection robustness, semantic evidence entailment, false-escalation rates, model cost, or production latency. The user chose to continue offline, so no live score is fabricated and `model_completed_rate` is null.

After configuring a local key, run `evals/compare.py --mode live --repeat 3` with the same fixed model and case set for both architectures. Record model/provider, attempted calls, failed calls, token counts, latency, and corrected/unsupported citations. Review rationales and source entailment manually, including whether B catches interpretation errors or adds unnecessary review burden. Live refusal/errors count as incomplete model runs even when deterministic controls preserve a safe handoff.

Decision: prefer A for a controlled pilot after that live validation; B currently has no observed offline quality benefit. See the architecture decision memo for the shipping rationale.
