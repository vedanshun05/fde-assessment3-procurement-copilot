# Procure — Assessment 3: AI Procurement Request Copilot

A local procurement product built from the supplied synthetic employees, budgets, catalog, vendors, purchase history, requests, policy, and mock vendor service. AI gathers evidence and recommends a next action; code enforces policy checks; humans retain sensitive approvals and exceptions.

## Setup and run

Requires **Python 3.12+**. From a fresh clone:

```bash
git clone https://github.com/vedanshun05/fde-assessment3-procurement-copilot.git
cd fde-assessment3-procurement-copilot
./start.sh
```

Open **http://127.0.0.1:8501**. The launcher installs pinned dependencies and starts the app and mock vendor API (`http://127.0.0.1:8001`). Ctrl+C stops both. Initial installation requires internet access.

The default offline simulation needs no key and makes zero LLM calls. For live AI, create `.env` from [.env.example](.env.example) if it does not already exist, configure these values locally, and restart:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_local_key
GEMINI_MODEL=gemini-3.5-flash-lite
COPILOT_MODE=live
```

Credentials stay server-side; `.env` is ignored by Git. The supplied assessment does not require an OpenAI key. Gemini was used for the recorded live comparison.

## Product workflow

1. Select a sample request or enter a new request, including cost, purpose, data access, and integrations.
2. Choose A or B and run analysis. The UI shows all six required outputs: **recommendation, evidence, approvals required, missing information, risk flags, and next step**.
3. Download the JSON human-review handoff containing the request, decision, evidence, and pending reviewer roles. Every handoff has `purchase_authorized: false`.

![Request details, evidence, and required reviews](docs/screenshots/desktop.png)

## Architecture and tools

| Architecture | Workflow |
| --- | --- |
| **A: single-agent baseline** | One procurement agent retrieves evidence and returns a structured proposal. |
| **B: staged two-agent variant** | An analyst retrieves the same evidence and returns a structured assessment. A policy/risk reviewer receives that assessment and the original evidence, then returns a structured proposal. |

Both architectures use the same five read-only tools:

| Tool | Purpose |
| --- | --- |
| `requester_budget` | Retrieve requester, manager, department, and available budget. |
| `software_catalog` | Retrieve existing approved options, scope, and licensed seats. |
| `vendor_registry` | Retrieve internal onboarding, security/legal status, and purchase history. |
| `vendor_risk` | Retrieve vendor/security status through the mock HTTP endpoint. |
| `policy_check` | Deterministically check spend thresholds, budget, review dates, sensitive data, and required approvals. |

Tools are bound to the submitted request. Shared code validates citations against retrieved evidence and preserves mandatory approvals, missing information, and risk flags. Tool or model failures produce a human-review handoff. The app does not execute purchases or approvals.

See the [workflow and architecture diagrams](docs/ARCHITECTURE.md).

## Assumptions

- Records are the supplied synthetic assessment data; costs are annualized USD amounts.
- Policy version 2026.09 uses the fixed reference date **2026-09-30**. A review aged 365 days is current; older, invalid, missing, or future dates require verification.
- Conflicting internal and service vendor information requires Security reconciliation. Sensitive data and integrations add the policy-required reviews.
- Licensed seats do not establish spare capacity. Humans verify feature fit, available seats, and contract terms where evidence is missing.

## Reproduce evaluation

The [32-case test set](evals/cases.json) is identical for A and B. It includes the ten supplied requests, financial/date boundaries, incomplete requests, existing tools, conflicting or expired vendor evidence, sensitive data, business-data prompt injection, HTTP failure, and timeout cases.

With the app and mock service running, reproduce the recorded comparisons:

```bash
.venv/bin/python evals/compare.py --mode live --repeat 1
.venv/bin/python evals/compare.py --mode offline --repeat 3
```

Live evaluation requires the configured Gemini key. Each comparison writes `summary.json`, `runs.csv`, and `decisions.json`; unmet expectations cause a nonzero exit. Committed artifacts are in [live results](evals/results/gemini/) and [offline results](evals/results/offline/).

For automated offline verification, including tests and the public evaluation cases:

```bash
.venv/bin/python scripts/check_project.py
```

## Results and architecture decision

The live comparison used **Gemini 3.5 Flash-Lite on 8 October 2026**, with one run of each case per architecture. All 64 analyses completed. Latency includes configured six-second spacing between model calls.

| Live metric | A: Single | B: Staged |
| --- | ---: | ---: |
| Correct next action | 21/32 (65.6%) | 31/32 (96.9%) |
| Correct next action on ten original requests | 8/10 | 9/10 |
| Deterministic policy checks | 100% | 100% |
| Evidence provenance against tool ledger | 100% | 100% |
| Correct pending human handoff | 100% | 100% |
| Mean latency | 12.507 s | 17.944 s |
| Mean LLM calls / executed tool calls | 2 / 5 | 3 / 5 |

A repeatedly chose an existing-tool check for training and add-on requests that required reviews. B's remaining error was routing TaskFlow for reviews before checking the existing catalog option. Offline simulation passed **96/96 runs per architecture** across three repetitions with zero LLM calls; those results check coded behavior rather than live AI reasoning.

**I would ship B for this assessment.** It matched ten more expected actions while preserving the same policy and human controls, at the cost of one additional model call and about 5.4 seconds more mean latency. B is the UI default. The [architecture decision memo](docs/ARCHITECTURE_DECISION.md) is under 500 words; the [evaluation report](docs/EVALUATION.md) contains detailed measurements.

## Known limitations

- The live comparison is one repetition of a small, correlated set: 19 of 32 cases reuse the training request. The result does not establish general performance on new requests.
- Evidence scoring checks provenance against the tool ledger; it does not independently verify every rationale. B also has a rationale-quality issue in case I01 despite its correct next-action label.
- Offline context heuristics do not measure live reasoning or universal prompt-injection resistance.
- Policy changes require a reviewed update to the deterministic engine and its checks. Human approvals remain outside this local assessment app.
