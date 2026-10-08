# Architecture decision memo

**Decision: ship B, the procurement analyst plus policy/risk reviewer, for the supervised assessment pilot.** Keep A available as the simpler baseline. Humans retain every approval and exception decision.

The live experiment used Gemini 3.5 Flash-Lite, the same 32 versioned cases and shared deterministic controls, with one repetition per architecture. All 64 analyses completed, making 160 real model calls. B matched the expected next action and passed all case checks in 31/32 cases (96.9%); A passed 21/32 (65.6%). Both achieved 100% on tested policy expectations, canonical evidence provenance, and pending human handoffs. The separate three-repetition offline simulation passed 96/96 runs per architecture but did not measure AI reasoning.

A repeatedly treated the SignFlow training package as a duplicate software purchase instead of routing its distinct service need to the required reviewer. It also mishandled the signing add-on. B's staged assessment improved those next actions, but incorrectly routed TaskFlow for reviews rather than checking the existing company-wide catalog option first. Correct action labels also do not guarantee sound rationales: B's I01 rationale questioned the training gap despite choosing the expected action.

B costs one additional model call per analysis: three versus two. Mean observed latency was 17.944 seconds versus 12.507 seconds, including six-second provider-call spacing. B consumed 281,248 input and 18,011 output tokens, versus A's 178,854 and 9,618. For this human-reviewed prototype, the observed improvement justifies the extra call and roughly 5.4 seconds of mean latency. These are free-tier-paced prototype measurements, not production latency or billed-cost estimates.

The evidence is limited: nineteen cases reuse the training request with changed boundaries or evidence, only one live repetition was run, and A preceded B in every pair. On the ten original request cases, A scored 8/10 and B 9/10. Grounding checks establish ledger provenance rather than independent semantic entailment; successful injection examples do not prove universal resistance.

Before broader deployment, validate both architectures on fresh requests and repeated runs, address B's catalog-routing error, and have reviewers assess rationales against original evidence. Reconsider A if better need interpretation achieves similar quality with fewer calls. Neither architecture may authorize purchases; the shared policy engine and human handoff remain mandatory.
