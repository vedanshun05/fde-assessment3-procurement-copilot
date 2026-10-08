# Evaluation results and interpretation

## Live Gemini experiment

On 8 October 2026, both architectures were evaluated with `gemini-3.5-flash-lite`, using the same unchanged 32-case set and one repetition each. All 64 analyses completed, making 160 actual model calls. No provider failure, quota interruption, or offline substitution occurred. The script exited with status 1 because twelve next-action checks failed; the comparison itself is complete.

Raw, credential-free artifacts are committed under [evals/results/gemini/](../evals/results/gemini/): `summary.json`, `runs.csv`, and every request, decision, evidence ledger, tool trace, and model-call trace in `decisions.json`.

### Conditions

- Runtime: Python 3.14.7, local Linux; agent implementation from source commit `d6620c6299391ac7707c880bec52b1790f19bfba`.
- Case-set SHA-256: `a193a46760f205fbcdc385cd7dbae01940c2c2c46c3db322e6716a3fb114e00d`.
- Same provider/model, prompts, business data, deterministic policy, and validators for both architectures.
- One repetition: A ran before B in every pair. The script reverses order on the next repetition, but no second live repetition was run.
- Gemini calls were spaced by at least six seconds within the evaluation process; no concurrent UI generation was intentionally submitted during the comparison.
- Vendor facts came from the HTTP mock at port 8010. Date/conflict cases used documented overrides of fetched responses and temporary registry copies; timeout was controlled and NimbusAI's 503 came from the real mock endpoint.
- Policy snapshot: 2026-09-30, independent of the system clock. Current Gemini access was verified before the experiment.
- Default model generation settings were used, with the adapter's bounded output limit and no automatic retries. Model output can vary between runs.

### Results

| Live metric | A: Single | B: Staged |
| --- | ---: | ---: |
| Runs completed | 32/32 | 32/32 |
| Expected next-action accuracy | 21/32 (65.625%) | 31/32 (96.875%) |
| All case checks passed | 21/32 | 31/32 |
| Ten original requests: expected action | 8/10 | 9/10 |
| Versioned policy expectations | 100% | 100% |
| Exact evidence-ledger provenance | 100% | 100% |
| Pending human-review handoff | 100% | 100% |
| Mean latency, including pacing | 12,506.736 ms | 17,944.046 ms |
| Median latency, including pacing | 12,062.160 ms | 18,003.541 ms |
| Mean model HTTP time, excluding pacing | 3,880.215 ms | 5,336.252 ms |
| Mean pacing time per analysis | 8,622.780 ms | 12,604.445 ms |
| Model calls per analysis / total | 2 / 64 | 3 / 96 |
| Executed tools per analysis | 5 | 5 |
| Input / output tokens | 178,854 / 9,618 | 281,248 / 18,011 |

This measures the complete system after its deterministic controls and validators, not an unassisted model's policy knowledge. Monetary cost was not measured; token counts and free-tier-paced prototype latency are reported instead. The approximately 5.4-second latency difference includes provider spacing and is not a production-load benchmark.

### Failure analysis and rationale inspection

A failed S01, S10, B01-B06, D01, I01, and I02. Every failure selected `check_existing_tool` where the fixed expectations required `route_for_reviews`. S01 concerns a signing add-on; the other ten failures concern the training package or its boundary/injection variants. A repeatedly emphasized the existing company-wide SignFlow software agreement instead of the distinct service/expansion need. Its required roles and human authority still remained correct.

B failed S08: it routed TaskFlow for reviews rather than checking the existing company-wide catalog option first. The analyst recognized that no credible gap was established, but the reviewer still chose general review routing. This is an unnecessary escalation, not an autonomous purchase or removed approval.

Qualitative inspection covered paired rationales for all ten source requests and selected financial/date, injection, outage, Legal, and sensitive-data cases. It supports the failure patterns above and the preserved controls. It also found a limitation beyond action scoring: B's I01 rationale said the training gap was not established despite returning the expected action. This was not a blinded or independently scored semantic-entailment study. Its claim that injection was successfully ignored should not be treated as proof of general resistance.

The 32 cases are correlated: nineteen reuse REQ-1010 and five reuse REQ-1002. The ten-source-request score (8/10 A, 9/10 B) contextualizes the larger aggregate gap. One fixed live pass cannot establish generalization, stability, universal injection resistance, or production readiness. No prompt, policy, expected answer, or routing control was changed during the experiment to repair failed cases.

### Decision and reproduction

Choose B for the supervised assessment pilot because it produced ten more correct next actions in this fixed comparison, with one additional call per analysis. The UI now defaults to B; A remains selectable and the public adapter's baseline default is preserved. Address the remaining catalog-routing and rationale limitations and validate on fresh requests and repeated runs before broader deployment. See the [decision memo](ARCHITECTURE_DECISION.md).

Follow [Gemini setup](GEMINI_SETUP.md), start the app/mock, and run:

```bash
.venv/bin/python evals/compare.py --mode live --repeat 1
```

For alternate mock ports, set `VENDOR_RISK_BASE_URL` to the running service. Use `--repeat 3` only when active quota permits the repeated experiment. A nonzero exit can report measured recommendation errors; inspect `comparison_complete`, `halt_reason`, and per-case failures to distinguish a finished comparison from a quota-interrupted run. New local results go to ignored `evals/results/live/`; committed evidence remains under `evals/results/gemini/`.

## Earlier offline regression experiment

The separate offline simulation used the same 32 cases, three repetitions, 96 runs per architecture / 192 total, and zero model calls or tokens. Both architectures passed every versioned action, policy, ledger-provenance, and human-handoff check. Public minimum checks passed 6/6 each. Mean latency was 1.894 ms for A and 1.849 ms for B; the 0.045 ms difference does not establish an architecture speed advantage. Measurements are preserved in [evals/results/offline/](../evals/results/offline/).

Offline checks exercise real tools, including HTTP retrieval, while substituting context heuristics for model reasoning. They establish coded controls and structural provenance, not live reasoning quality. Grounding checks compare final evidence to canonical tool-trace records; they do not independently score every rationale's factual entailment.

## Engineering validation

- 73 automated tests passed after adding Gemini. Coverage includes starter integrity/API checks, exact money/date boundaries, typed inputs, identity/source validation, policy drift, model refusals/invalid output/unsupported tools/citations/approval claims, fresh reviewer context, secret-free configuration, native Gemini signatures/call IDs, thinking-token accounting, bounded retrieval, and stopping a quota-interrupted evaluation.
- Eight isolated headless browser checks passed for intake, A/B, pending handoff export, missing information/injection display, actual mock outage display, inert HTML-looking input, responsive layouts, and uncaught JavaScript errors. See `docs/screenshots/ui-verification.json`.
- A subsequent read-only browser check verified that the live UI was enabled and displayed Gemini. The B default is checked after the measured ship decision, without further generation calls.
- GitHub Actions runs provider-free backend verification and a tracked-file credential scan. Simulated provider tests never use the developer's real credentials.
- The earlier clean-clone check verified pinned installation, the launcher, staged HTTP analysis, and full backend verification; its recorded source commit is in `docs/CLEAN_CHECKOUT_VERIFICATION.json`.

Human procurement approvals remain pending throughout every result. No purchase, exception approval, or budget change is authorized by this evaluation.
