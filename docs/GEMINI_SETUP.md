# Free live AI with Gemini

The assessment does not require an OpenAI account or paid API. The [starter README](STARTER_README.md#3-add-your-llm-credentials) allows the provider and framework of your choice. A real model is still needed to evaluate AI reasoning; the offline simulation makes zero model calls.

## Configure the free tier

1. Open [Google AI Studio's API keys page](https://aistudio.google.com/api-keys) and sign in with your Google account.
2. Create a key in a project on the **free tier**. New AI Studio users may receive a default project/key after accepting the terms. You do not need to enable paid billing for this setup. If your account/project has no usable free quota, the application will report a model failure rather than claim a successful AI assessment.
3. Open the project's `.env` locally. Copy `.env.example` only if `.env` does not already exist. Save these values:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_local_key
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_MIN_INTERVAL_SECONDS=6
COPILOT_MODE=live
```

4. Restart `./start.sh` and open `http://127.0.0.1:8501`. **Live AI** is enabled when the selected provider's key is configured. Select A or B and analyze a request. Check that Run details show model calls and the raw result records `telemetry.provider: gemini`. A configured key does not prove model access: `model_unavailable` means the actual call failed.

The key stays server-side and `.env` is ignored by Git. Do not paste the key into chat, commit it, or place it in browser JavaScript. No OpenAI key is needed for Gemini. If both keys exist, `LLM_PROVIDER` determines which is used.

## Evaluate within your quota

Check [your active rate limits in AI Studio](https://aistudio.google.com/rate-limit?timeRange=last-28-days). Limits depend on the model/account and apply per project, including requests per minute, input tokens per minute, and requests per day. Adjust the minimum call interval to fit your quota; spacing alone cannot solve an exhausted daily/token allowance.

Keep the app running so the vendor mock is available, then run in another terminal from the project directory:

```bash
.venv/bin/python evals/compare.py --mode live --repeat 1
```

This evaluates the same 32 cases for both architectures: 64 analyses, each requiring multiple model calls. A normally completed A uses two to three calls; B uses one additional structured call. Use `--repeat 3` for the full repeated experiment when your quota allows it. Results are written to `evals/results/live/` and remain ignored by Git until reviewed.

An HTTP 429 stops further evaluation calls, saves partial results, and exits unsuccessfully. `summary.json` records `comparison_complete: false` and `halt_reason: provider_rate_limit`; do not report this as a complete A/B result. Wait for quota to reset, adjust pacing if needed, and rerun when a full comparison is possible. Inspect rationales and source entailment before updating the evaluation report and decision memo.

## Failure handling

- Missing key: Live AI stays disabled and the evaluation refuses to run.
- Invalid/restricted key, unavailable model, timeout, refusal, or malformed output: the app retains deterministic evidence/approvals and holds for human review with `model_unavailable`.
- Quota failure: the app also marks `model_rate_limited`; the evaluation saves incomplete results and stops. There are no automatic provider retries or automatic upgrades to a paid tier.

Google's free tier can use submitted content to improve its products; the assessment data is synthetic. See [Google's current pricing](https://ai.google.dev/gemini-api/docs/pricing), [key setup](https://ai.google.dev/gemini-api/docs/api-key), and [quota documentation](https://ai.google.dev/gemini-api/docs/rate-limits). The default [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) supports both function calling and structured outputs. Changing the model requires rerunning both architectures with the same model and conditions.
