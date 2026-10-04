# Five-minute demonstration

1. Run `./start.sh` and open `http://127.0.0.1:8501`. Point out the offline-mode label and pending human authority.
2. Analyze **SignFlow Add-on (REQ-1001)**. Show the requester budget, vendor/service evidence, Manager approval, and expansion reason. No purchase is authorized.
3. Analyze **TaskFlow Pro (REQ-1008)**. Show the existing company-wide option and the instruction to verify unused capacity rather than assume spare licenses.
4. Analyze **ProspectPilot (REQ-1005)**. Show the Sales budget shortfall, Security/Privacy/Legal reviews, and the evidence references. Download the review handoff and show that every role is pending and `purchase_authorized` is false.
5. Analyze **NeuralDesk Team Workspace (REQ-1006)**. Show cost/users/data clarification and the prompt-injection flag. The request's claim of CFO approval has no authority.
6. Analyze **NimbusAI Contract Reviewer (REQ-1009)**. Show the real mock HTTP 503, retained budget/registry evidence, and manual-review next step.
7. Under Analysis settings, switch to B and analyze another request. Show analyst/reviewer stages in Run details and zero LLM calls in offline mode.
8. Show `evals/results/offline/summary.json`, the 32-case set, and the decision memo. State clearly that live model quality remains unmeasured.

For live AI later, configure `.env` locally, restart the services, select Live AI, and repeat the paired evaluation. Do not present offline timing as live model latency.
