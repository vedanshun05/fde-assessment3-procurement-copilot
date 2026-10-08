# Five-minute demonstration

1. Run `./start.sh` and open `http://127.0.0.1:8501` (or the configured alternate port). Without credentials, point out the offline-mode label; with a local Gemini key and `COPILOT_MODE=live`, show Live AI. B is the UI default. Human authority remains pending in both modes.
2. Analyze **SignFlow Add-on (REQ-1001)**. Show the requester budget, vendor/service evidence, Manager approval, and expansion reason. No purchase is authorized.
3. Analyze **TaskFlow Pro (REQ-1008)**. Show the existing company-wide option and the instruction to verify unused capacity rather than assume spare licenses.
4. Analyze **ProspectPilot (REQ-1005)**. Show the Sales budget shortfall, Security/Privacy/Legal reviews, and the evidence references. Download the review handoff and show that every role is pending and `purchase_authorized` is false.
5. Analyze **NeuralDesk Team Workspace (REQ-1006)**. Show cost/users/data clarification and the prompt-injection flag. The request's claim of CFO approval has no authority.
6. Analyze **NimbusAI Contract Reviewer (REQ-1009)**. Show the real mock HTTP 503, retained budget/registry evidence, and manual-review next step.
7. Under Analysis settings, compare A and B. Show analyst/reviewer stages for B and the mode-specific call counts: zero in offline mode; two calls for A and three for B in the recorded live experiment.
8. Show `evals/results/gemini/summary.json`, the 32-case set, and the decision memo. Explain the live scores (21/32 A, 31/32 B), remaining routing errors, correlated training variants, and the one-repetition limitation. Show the separate offline regression results without presenting them as live quality.

To reproduce live AI, follow [Gemini free-tier setup](GEMINI_SETUP.md), configure `.env` locally, restart the services, select Live AI, and repeat the paired evaluation within the active quota. OpenAI is optional. Do not present offline timing as live model latency, or quota-interrupted results as a completed comparison.
