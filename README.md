# Procure — AI Procurement Request Copilot

An internal procurement workbench that gathers evidence, checks policy in code, and recommends the next human action. Built from the supplied FDE Assessment 3 starter pack, with a single-agent baseline and an analyst/reviewer variant.

**Live Gemini evaluation is complete:** on the same 32 cases, A matched the expected next action in **21/32** runs and B in **31/32**. Both preserved all tested policy controls, evidence provenance, and human handoffs. Choose **B for a supervised pilot**, with its remaining catalog-routing error documented below. This was one live repetition; the separate offline evaluation uses three repetitions and zero model calls. All records are synthetic. The app cannot purchase software, change budgets, or approve exceptions. The assessment does not require OpenAI; the [supplied starter README](docs/STARTER_README.md#3-add-your-llm-credentials) explicitly allows any provider/framework.

![Request workbench showing a budget shortfall and required reviews](docs/screenshots/desktop.png)

## Run locally

Requires **Python 3.12+**. Tested locally with Python 3.14.7; the CI workflow targets 3.12. Internet is needed for the first dependency installation; subsequent offline runs use only local services. No model key is needed for the demo.

```bash
git clone https://github.com/vedanshun05/fde-assessment3-procurement-copilot.git
cd fde-assessment3-procurement-copilot
./start.sh
```

Open **http://127.0.0.1:8501**. The same command installs pinned dependencies in `.venv` if needed, then starts the copilot and vendor-risk mock. Press Ctrl+C to stop both. The vendor API listens at `http://127.0.0.1:8001`.

If using the local workspace folder instead of GitHub, run `./start.sh` from this project's directory. Alternate ports:

```bash
./start.sh --port 8502 --vendor-port 8002
```

Windows PowerShell or manual setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock.txt
.\.venv\Scripts\python run_local.py
```

`python app.py` also invokes the same launcher. No frontend compilation or Node dependency is required to run the product.

## Product workflow

1. Pick one of ten sample requests or choose **New request**. Edit requester, product/vendor, annual cost, licenses, purpose, data access, and integrations.
2. Choose architecture A or B in **Analysis settings** and run analysis. B is the UI default following the live comparison; A remains available as the baseline.
3. Read the recommendation, source-linked evidence, required approvals, missing information, risk flags, and next step. Incomplete fields are clarified rather than invented.
4. **Download human review handoff** exports the analyzed request, decision, original evidence, and pending reviewer roles as JSON. It does not submit an approval. Every package has `purchase_authorized: false`.

The form remains editable and works on mobile. Editing the request invalidates the old result. Untrusted strings render as text. See [the demo script](docs/DEMO.md) and [mobile rendering](docs/screenshots/mobile.png).

## Agents, tools, and controls

**A:** one procurement agent gathers evidence through model function calls, interprets context, and returns a structured `AgentProposal`.

**B:** a procurement analyst gathers the same evidence and returns an `AnalystAssessment`; a policy/risk reviewer receives it with the original evidence in a fresh context and returns an `AgentProposal`.

Both use these five read-only tools:

| Tool | Evidence/check |
| --- | --- |
| `requester_budget` | Requester, manager, department, available software budget |
| `software_catalog` | Existing approved options, scope, licensed capacity |
| `vendor_registry` | Internal security/legal/onboarding status and prior purchases |
| `vendor_risk` | Actual HTTP retrieval from the mock vendor service, with bounded timeout |
| `policy_check` | Deterministic money/date checks, required roles, uncertainty, and risk flags |

Models use empty tool arguments; each tool is bound to the submitted request. They cannot redirect retrieval or modify business records. Retrieval is bounded to two model rounds. Code completes required evidence coverage, and per-run caching avoids duplicate physical tool calls. Both architectures preserve the same deterministic controls and canonical evidence ledger.

Annual-cost thresholds, budget comparisons, vendor validity, and sensitive-data rules run in code. Model proposals can add uncertainty/reviews, but cannot remove required controls. Unknown citations, missing/malformed evidence, model refusal/errors, and unverifiable material sources produce a human handoff. Approval claims in model rationale are flagged and held for manual review. The UI always shows approvals as pending.

Detailed workflow/architecture diagrams, trust boundaries, policy interpretations, and assumptions: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Optional live AI

**Gemini free tier:** create a key in [Google AI Studio](https://aistudio.google.com/api-keys), keep the project on its free tier, and configure it **locally** in `.env` (copy `.env.example` first if the file does not exist):

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_local_key
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_MIN_INTERVAL_SECONDS=6
COPILOT_MODE=offline
```

Restart the app; select **Live AI** under Analysis settings. Set `COPILOT_MODE=live` only if you want live mode as the default. Credentials stay server-side and `.env` is ignored by Git. The launcher sets the mock endpoint to its chosen `--vendor-port`; direct module/server use respects `VENDOR_RISK_BASE_URL`.

Gemini uses the official [generateContent REST API](https://ai.google.dev/api/generate-content), function declarations, and JSON-schema outputs, with a 30-second per-call timeout and no automatic retries. The default [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) supports function calling and structured outputs and has [free input/output pricing](https://ai.google.dev/gemini-api/docs/pricing). Account eligibility, model access, and actual [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) must be checked in AI Studio. Six-second spacing is configurable and does not guarantee sufficient daily/token quota. No Google provider SDK is needed; `httpx` is already pinned. See the [step-by-step Gemini setup](docs/GEMINI_SETUP.md).

OpenAI remains an optional alternative: set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL=gpt-4.1-mini-2025-04-14`. This path uses [Responses function calling](https://developers.openai.com/api/docs/guides/function-calling) and [structured output parsing](https://developers.openai.com/api/docs/guides/structured-outputs), with `store=False`, a 20-second timeout and SDK retries disabled. It uses the account's normal API pricing. If `LLM_PROVIDER` is omitted, a configured Gemini key selects Gemini; otherwise existing OpenAI setups retain their behavior.

## Reproduce verification and evaluation

After dependencies are installed, this command starts a temporary mock API on a free port, runs preflight, tests, the six public cases for A/B, and the complete comparison without replacing committed results:

```bash
.venv/bin/python scripts/check_project.py
```

With `./start.sh` running in another terminal, reproduce the committed three-repeat comparison:

```bash
.venv/bin/python evals/run_public_evals.py --architecture single
.venv/bin/python evals/run_public_evals.py --architecture staged
.venv/bin/python evals/compare.py --mode offline --repeat 3
```

Results include `summary.json`, `runs.csv`, and all per-case requests/decisions in `decisions.json`. A failed evaluation exits nonzero. The original `src.solution.handle_request(request_id, architecture)` adapter remains available to public/hidden harnesses; `analyze_request(...)` also accepts new/modified requests without ID-based answers.

The [32-case set](evals/cases.json) covers all ten supplied requests; exact financial, Legal, budget, and date boundaries; employee/customer PII; production integration; source conflicts; unknown requesters/vendors; missing integrations; injection inside requests/registry/API notes; the mock's real HTTP 503; and a controlled transport timeout. Both architectures use identical cases and alternating order across repetitions. Date/registry variations are documented controlled evidence overrides; the business dataset is unchanged.

Run the same comparison against live AI after configuring `.env`:

```bash
.venv/bin/python evals/compare.py --mode live --repeat 1
```

One repetition runs all 32 cases for each architecture (64 analyses, with multiple model calls per analysis). Use `--repeat 3` for a repeated comparison only when your active quota permits it. The script refuses to run without the selected provider's key, records the provider/model, and stops on HTTP 429 while saving explicitly incomplete results. A quota-interrupted run cannot establish the A/B comparison. It does not substitute offline scores for live results. Local live outputs are ignored until deliberately reviewed for inclusion.

## Results and ship decision

The [committed live Gemini results](evals/results/gemini/) contain 64 analyses and 160 real model calls using `gemini-3.5-flash-lite` on 8 October 2026. All requests completed without provider/quota failures. The comparison exits nonzero because recommendation errors were measured, not because it was interrupted; `comparison_complete` is true.

| Live metric, one repetition | A: Single | B: Staged |
| --- | ---: | ---: |
| Expected next action / all case checks | 21/32 (65.6%) | 31/32 (96.9%) |
| Ten original request cases: expected next action | 8/10 | 9/10 |
| Policy checks, ledger provenance, pending human handoff | 100% each | 100% each |
| Model completion | 32/32 | 32/32 |
| Mean latency including six-second call spacing | 12.507 s | 17.944 s |
| Model calls / executed tools per analysis | 2 / 5 | 3 / 5 |
| Total input / output tokens | 178,854 / 9,618 | 281,248 / 18,011 |

A incorrectly prioritized existing-tool checks for the add-on and training requests; nine additional failures repeat the training pattern in boundary/injection variants. B made one error: it routed TaskFlow for reviews instead of checking the existing catalog option first. B also has a rationale-quality limitation in I01 despite its correct next-action label. These scores are not an independent semantic-entailment measure. Nineteen of 32 cases reuse the training request, so the apparent gain is concentrated in that pattern; the ten-source-request scores give useful context. Full measurements, rationale inspection, and limitations are in [docs/EVALUATION.md](docs/EVALUATION.md).

**Choose B for the supervised assessment pilot.** Its extra structured review improved the measured next-action score by ten cases at the cost of one additional model call and about 5.4 seconds more mean latency with this pacing. Keep humans responsible for every decision, address the remaining catalog-routing error, and validate on fresh requests and repeated runs before broader deployment. The [decision memo](docs/ARCHITECTURE_DECISION.md) stays below 500 words.

The earlier offline simulation remains a separate regression baseline:

| Offline metric | A: Single | B: Staged |
| --- | ---: | ---: |
| Supplied public minimum checks | 6/6 | 6/6 |
| Expanded cases per repetition | 32 | 32 |
| Successful runs across three repetitions | 96/96 | 96/96 |
| Expected action, policy checks, ledger provenance, human handoff | 100% each | 100% each |
| Executed tools per run | 5 | 5 |
| LLM calls / model tokens | 0 / 0 | 0 / 0 |

The tiny offline timing differences do not establish a speed advantage. Recorded measurements and their conditions are in [the evaluation report](docs/EVALUATION.md) and [raw summary](evals/results/offline/summary.json). These results verify coded controls and structural evidence provenance; they do **not** establish live reasoning quality, semantic entailment, or universal prompt-injection robustness.

## Engineering checks

- Automated tests cover policy boundaries, reference-date behavior, malformed data, source identity, evidence tampering, policy drift, model refusals/invalid schemas/citations/approval claims, bounded tool orchestration, and secret-free API configuration.
- Simulated OpenAI client and Gemini HTTP tests exercise both live orchestration paths without spending tokens or implying a live LLM measurement. They also verify that quota exhaustion stops evaluation and saves incomplete results.
- Eight headless browser checks cover custom intake, both architectures, handoff downloads, injection/missing-information display, real HTTP outage display, inert HTML-looking input, responsive layouts, and uncaught JavaScript errors.
- GitHub Actions runs the offline verification and a tracked-file credential scan on Python 3.12.

Optional browser checks need Node 22+, Chromium, and the development dependency:

```bash
npm install
CHROMIUM_PATH=/usr/bin/chromium npm run test:ui
```

Point `CHROMIUM_PATH` to your installed Chrome/Chromium executable, and set `APP_URL` for alternate app ports. These checks use an isolated headless browser. Screenshots and the check record live in `docs/screenshots/`. Node is optional for development and is not used by the Python launcher.

## Known limitations

- Offline semantic matching/gap heuristics are limited. Live Gemini access and one paired pass are verified; OpenAI live access is unmeasured. The live sample is small, correlated, ordered A then B, and not a held-out production population.
- Catalog seat utilization, detailed feature fit, and complete data-processing contract terms are absent. Humans must verify them; vendor capabilities do not automatically establish the requested data use.
- The engine is tied to the supplied policy digest/reference date. Policy updates require a reviewed engine/test update rather than silently applying stale thresholds.
- Grounding evaluation compares evidence to the tool ledger; independent semantic entailment/rationale review is still needed for live results.
- This loopback prototype has no enterprise identity, persistent approval queue, durable audit log, verified signoff, or distributed rate-limit controls for production. Gemini pacing applies only within one process. It exports an evidence package for human review.
- A missing optional LLM key supports the offline product, but an AI-backed pilot requires configuring and evaluating the live path first.

## Submission files

| Deliverable | Location |
| --- | --- |
| Implementation plan and checklist | [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) |
| Starter inventory, provenance, defects/fixes | [docs/STARTER_INSPECTION.md](docs/STARTER_INSPECTION.md) |
| Workflow/architecture diagrams and assumptions | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Reproducible evaluation and raw results | [evals/compare.py](evals/compare.py), [live Gemini results](evals/results/gemini/), [offline results](evals/results/offline/) |
| Results interpretation | [docs/EVALUATION.md](docs/EVALUATION.md) |
| Architecture decision memo | [docs/ARCHITECTURE_DECISION.md](docs/ARCHITECTURE_DECISION.md) |
| Demo and submission checklist | [docs/DEMO.md](docs/DEMO.md), [STUDENT_CHECKLIST.md](STUDENT_CHECKLIST.md) |

Submit the public repository URL through the assessment [Google Form](https://forms.gle/ab9DrohuNQWukXCD9) by **8 October 2026**. The form has not been submitted automatically.

---

## Starter-pack provenance

The original starter README is retained at [docs/STARTER_README.md](docs/STARTER_README.md). Data and policies remain the supplied synthetic assessment records.
