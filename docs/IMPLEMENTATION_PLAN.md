# Assessment 3 implementation plan

## Target

Build a local AI Procurement Request Copilot using the supplied starter pack. Demonstrate the same employee-request workflow with a single procurement agent (A) and an analyst plus policy/risk reviewer (B). Choose an architecture using measured results rather than agent count. Submission closes 8 October 2026.

## Work sequence

1. **Plan and checklist:** record requirements, acceptance criteria, evaluation scenarios, and deliverables in this file.
2. **Inspect the starter pack:** download the original archive, inventory code/data/policies, run the scaffold where practical, and document defects and fixes. Keep its business data and policies as the source of truth.
3. **Build the working product:** implement validated request intake, grounded evidence retrieval, deterministic budget/approval rules, structured recommendations, explicit human review, and both architectures. Provide a single command to start the UI and mock service.
4. **Evaluate:** run both architectures against exactly the same versioned cases, including injected text and service failures. Report recommendation accuracy, evidence grounding, policy compliance, human escalation, latency, model calls, and tool calls. Separate offline fixtures from real model measurements.
5. **Prepare submission:** document setup, assumptions, tools, workflow/architecture diagrams, evaluation commands/results, limitations, and a decision memo of at most 500 words. Check the repository for secrets and confirm a clean-clone start path.

Framework choices will follow the starter-pack inspection. A local application is sufficient; no deployment is required by the brief.

## Product acceptance criteria

- An employee can enter or select a request and see a completed analysis in the UI.
- Results contain recommendation, evidence, approvals required, missing information, risk flags, and next step.
- At least three tools are callable and traced. Budget/approval thresholds are checked by deterministic code.
- Evidence identifies its source and relevant records; unsupported statements cannot silently become approvals.
- A working single-agent baseline is built before the staged/two-agent variant.
- Sensitive decisions and policy exceptions go to a named human role. The UI cannot treat an AI recommendation as a completed purchase approval.
- Missing data, stale/conflicting vendor status, unavailable APIs, and untrusted business text lead to explicit uncertainty or review.
- Both architectures use the same input cases, tools, policies, and deterministic guardrails.
- Model credentials remain server-side and outside Git; a documented offline mode supports local inspection without a key.

## Evaluation design

Create expected outcomes from the supplied policies and records before measuring the architectures. Include:

| Case family | What it verifies |
| --- | --- |
| Standard eligible request | Appropriate next action and correct required approvals |
| Existing software fits the need | Avoid unnecessary purchase; cite catalog evidence |
| Missing or ambiguous request fields | Ask for specific information and avoid invented facts |
| Budget overrun or exact threshold | Deterministic comparisons and required escalation |
| Restricted/sensitive data | Security/privacy review cannot be bypassed |
| Unknown, expired, or conflicting vendor | Preserve conflicting evidence and require review |
| Malicious instructions inside records | Treat retrieved business data as data |
| Vendor endpoint unavailable | Visible degraded evidence and safe human handoff |
| Invalid model output/model unavailable | Validated failure result; no fabricated completion |

Record the provider, model, mode, case count, attempts, and measurement conditions with every results file. Offline simulation checks application behavior but does not establish live LLM quality. Live evaluation remains separately reproducible when credentials are supplied.

## Submission checklist

- [x] Requirements and implementation plan
- [x] Starter pack inspected and scaffold defects documented
- [x] Working product with all six required output fields
- [x] At least three tools, including deterministic rules
- [x] Single-agent architecture A
- [x] Staged/two-agent architecture B
- [x] Human-review workflow
- [x] One-command local startup
- [x] Versioned evaluation cases and reproducible runner
- [x] Results and fair architecture comparison (offline, clearly labelled)
- [x] Architecture/workflow diagrams and assumptions
- [x] Decision memo, at most 500 words
- [x] README with setup, workflow, agents/tools, results, decision, and limitations
- [x] `.env.example` and no committed secrets
- [x] Tests of policy boundaries, grounding, and failure behavior
- [x] Clean-clone verification
- [ ] Public GitHub repository URL
- [ ] Submit repository URL through the assessment Google Form

## Scope and decisions

The copilot recommends and prepares a human handoff; it does not pay vendors, procure licenses, or approve sensitive exceptions. Use the starter policy's actual fields and thresholds. Document any missing-policy interpretation rather than presenting it as supplied policy. Publishing the repository and submitting the Google Form are tracked separately from completing the local software.
