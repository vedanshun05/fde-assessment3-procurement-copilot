# Starter-pack inspection

## Provenance

Downloaded on 4 October 2026 from the Google Drive link in `FDE_Assessment_3.pdf`.

- Archive: `FDE_Assessment_3_Starter_Pack`
- SHA-256: `6bcd67e43978d823d6401f384ba157abe803cdb4d9e669d9b879740015b66fcd`
- Original README: `docs/STARTER_README.md`
- Supplied business data and policy are preserved in `data/`.

## Inventory and contract

- 10 employees, 6 department budgets, 10 catalog products, 13 vendors, 8 purchases, and 10 requests.
- FastAPI vendor-risk mock with a deliberate HTTP 503 for NimbusAI.
- Policy version 2026.09; reference date **2026-09-30**, with 365-day vendor-review validity.
- `src.solution.handle_request(request_id, architecture)` must return `ProcurementDecision`.
- Six public cases check minimum behavior; the other four sample requests cover additional scenarios.
- The policy engine, agent workflow, and actual solution are intentionally absent.

## Findings and actions

| Finding | Evidence | Action |
| --- | --- | --- |
| Environment lacks starter dependencies | Original `python3 verify_setup.py` reports FastAPI, Uvicorn, pandas, and Streamlit missing | Install project dependencies in a local virtual environment |
| Public evaluation can exit successfully without a solution | `NotImplementedError` branch prints STOP and returns from `main()` | Make failed/incomplete evaluation exit nonzero |
| No agent implementation | `src/solution.py` raises `NotImplementedError` | Implement A first, then B through the supplied adapter |
| UI is only a request picker and raw JSON panel | `app.py` | Replace with request intake, evidence, required reviews, and a handoff export |
| Mock route decodes an already decoded path value | `unquote(vendor_name)` in FastAPI route | Remove second decode so literal percent sequences retain identity |
| Results are ignored by Git | `evals/results_*.csv` in `.gitignore` | Track curated, labelled results under `evals/results/` |
| SignalWatch registry/service disagree; NimbusAI fails; REQ-1006 contains injection | Supplied vendor/request records | Preserve these intentional test conditions; do not repair business evidence to make tests pass |
| Seat utilization is absent | Catalog includes licensed seats, not unused seats | Cite licensed capacity and ask humans to verify availability; never invent spare seats |

CSV files use normal CRLF line endings, parse successfully, and are not corrupt. Initial missing dependencies are an environment issue, not a starter-code defect.

## Implementation choices

Keep Python and the FastAPI mock. Replace the optional Streamlit UI with a small FastAPI-served HTML/CSS/JavaScript app so both services share one Python environment without a frontend build step. Keep all original data, original public cases, and the evaluation adapter. Add a bounded OpenAI Responses tool loop with structured model outputs and an explicit deterministic offline simulation. Apply the same policy engine and evidence checks to A and B. Human review is an exportable handoff, never an autonomous purchase.

Live model quality cannot be measured without a locally configured API key. Offline results will state zero LLM calls and will not be presented as live AI performance.
