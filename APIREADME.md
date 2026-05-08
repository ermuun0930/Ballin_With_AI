# LegisRisk API

Serverless HTTP API that scores publicly-traded companies for legislative risk
from the 119th Congress bill pipeline. Scoring is similarity-driven: each
ticker's SEC business description is embedded with Amazon Titan v2 and matched
against bill exposure embeddings; the per-bill effective probability of harm
combines passage probability, bill materiality, and ticker–bill cosine
similarity, then aggregates via Noisy-OR. Optional per-bill impact
classification (positive / negative / neutral) is delegated to Claude Sonnet
4.5 on Bedrock.

- **Runtime**: AWS Lambda (Python 3.13, arm64), 512 MB, 60 s timeout, behind API Gateway. Packaged with AWS SAM.
- **Source**: [`lambda_function.py`](lambda_function.py) · **Infra**: [`template.yaml`](template.yaml) · **Deploy config**: [`samconfig.toml`](samconfig.toml)
- **Live endpoint**: `POST https://o13e3w95bk.execute-api.us-east-1.amazonaws.com/Prod/risk`

---

## Endpoint

```
POST /risk
Content-Type: application/json
```

### Request body

```json
{
  "tickers": ["AAPL", "XOM", "PFE"],
  "analyze_impact": false
}
```

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `tickers` | `string[]` | yes | — | 1–200 ticker symbols, case-insensitive. `.` is normalized to `-` (e.g. `BRK.B` → `BRK-B`). Excess entries past 200 are silently dropped. |
| `analyze_impact` | `boolean` | no | `false` | When `true`, calls Claude Sonnet on Bedrock once per ticker (batched over its top bills) to label each top bill `positive` / `negative` / `neutral`. Adds ~0.5–1.5 s/ticker and Bedrock cost. |

Tickers may be in the precomputed universe (~1,287 entries — S&P 500 plus
everything Nova flagged as exposed during pipeline build) or arbitrary. Unknown
tickers fall back to a live SEC EDGAR fetch + live Titan embed (see
[Live ticker fallback](#live-ticker-fallback) below).

### Response — 200

```json
{
  "results": [
    {
      "ticker": "AAPL",
      "company": "APPLE INC.",
      "industry": "Electronic Computers",
      "risk_score": 0.7339,
      "n_bills_scored": 15505,
      "n_bills_above_threshold": 54,
      "top_bills": [
        {
          "bill_type": "hr",
          "bill_number": "7749",
          "title": "To amend the National Quantum Initiative Act ...",
          "industry": "Technology",
          "p_passage": 0.0961,
          "materiality": 0.700,
          "similarity": 0.412,
          "effective_p": 0.0277,
          "impact": "positive",
          "impact_rationale": "Quantum R&D funding extends Apple's optionality in computing roadmap."
        }
      ]
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `ticker` | string | Uppercased, `.`→`-` normalized. |
| `company` | string \| null | Issuer name from `ticker_index.csv` or live SEC `submissions` JSON. |
| `industry` | string \| null | SIC description from SEC EDGAR. Not GICS. |
| `risk_score` | number 0..1 \| null | Materiality- and similarity-weighted Noisy-OR (see [Scoring](#scoring)). `null` only when no SEC business description is resolvable for the ticker — `note` is set in that case. |
| `n_bills_scored` | int | Pipeline size considered (typically 15,505 active 119th-Congress bills). |
| `n_bills_above_threshold` | int | Bills clearing `SIM_THRESHOLD` (default 0.20) cosine similarity to this ticker. |
| `top_bills` | array | Up to 5 bills with the highest `effective_p`, descending. Empty when no bill clears the threshold. |
| `top_bills[].bill_type` | string | Lowercased: `hr`, `s`, `hjres`, `sjres`, `hconres`, `sconres`, `hres`, `sres`. |
| `top_bills[].bill_number` | string | Bill number as a string. |
| `top_bills[].title` | string | Official bill title. |
| `top_bills[].industry` | string | Bill's exposure industry (Nova Pro classification during pipeline build). |
| `top_bills[].p_passage` | number 0..1 | Probability the bill becomes law this Congress (gradient-boosting model trained on Congresses 108–117, validated on 118). |
| `top_bills[].materiality` | number 0..1 | Bill economic materiality (Nova Pro). `0.0` for ceremonial bills (post-office namings, sense-of-Congress, commemoratives) and they're effectively excluded from `risk_score`. |
| `top_bills[].similarity` | number 0..1 | Cosine similarity between bill exposure embedding and ticker business-description embedding. Both are L2-normalized Titan v2 1024-d vectors. |
| `top_bills[].effective_p` | number 0..1 | `p_passage × materiality × similarity`. The per-bill contribution into Noisy-OR. |
| `top_bills[].impact` | `"positive"` \| `"negative"` \| `"neutral"` \| null | Present only when `analyze_impact=true`. `null` if Bedrock classification failed for that ticker. |
| `top_bills[].impact_rationale` | string | Up to 200 chars. Sonnet's justification, or a short error string if classification failed. |
| `note` | string | Present only when `risk_score` is null (no SEC business description). |

### Response — 400

```json
{ "error": "body must be valid JSON" }
```
or
```json
{ "error": "POST body must be {\"tickers\": [\"AAPL\", ...]}" }
```

Triggered by unparseable JSON or a missing/empty/non-array `tickers` field
respectively. There are no other server-defined error responses; per-ticker
problems (unknown tickers, Bedrock failures) degrade gracefully inside the
`results` array.

---

## Examples

```bash
# Baseline scoring (no LLM)
curl -sS -X POST "$API_URL" \
  -H 'Content-Type: application/json' \
  -d '{"tickers":["AAPL","XOM","PFE"]}'

# With per-bill impact analysis
curl -sS -X POST "$API_URL" \
  -H 'Content-Type: application/json' \
  -d '{"tickers":["AAPL","XOM"],"analyze_impact":true}'

# Unknown ticker (live SEC fallback)
curl -sS -X POST "$API_URL" \
  -H 'Content-Type: application/json' \
  -d '{"tickers":["RBLX"]}'
```

---

## Scoring

Per [`score_ticker`](lambda_function.py):

1. **Resolve ticker → vector**. Look up in the precomputed `ticker_index.csv`. On miss, fetch SEC EDGAR submissions, extract Item 1 from the latest 10-K, and call Titan v2 to embed it (cached per warm container).
2. **Compute cosine similarity** between the ticker vector and every bill embedding. Both are L2-normalized at build time, so cosine reduces to a single dot product `BILL_EMB @ vec`.
3. **Threshold** at `SIM_THRESHOLD` (default 0.20). Bills below are discarded — they aren't materially related to the ticker's business.
4. **Per-bill effective probability**: `eff_i = clip(p_passage_i × materiality_i × similarity_i, 0, 1)`.
5. **Noisy-OR aggregate** across the survivors:

   ```
   risk_score = 1 − Π (1 − eff_i)
   ```

   Interpretation: probability that **at least one** materially-relevant
   bill passes and meaningfully affects this ticker, treating bills as
   conditionally independent.

6. **Top bills**: select the 5 highest `effective_p` survivors (not the 5 most similar — the ones with the largest expected impact).

**Why three factors and not just `p_passage`?**
- `p_passage` alone is industry-blind: a high-probability post-office naming
  bill should not raise a chemical company's risk.
- `materiality` collapses ceremonial bills to zero contribution.
- `similarity` weights each bill by how directly it maps to *this* ticker's
  business, not just its broad industry — so an oil refiner and a wind-energy
  utility get different scores from the same energy bills.

---

## Optional impact annotation

Triggered by `analyze_impact: true`. Per [`annotate_impact`](lambda_function.py):

- One Bedrock call per ticker, batching all of that ticker's top bills into a single Sonnet prompt.
- Tickers fan out via `ThreadPoolExecutor` (max `IMPACT_MAX_WORKERS`, default 8).
- Strict JSON output requested; markdown code fences are tolerated and stripped.
- Per-process cache keyed on `(ticker, bill_type, bill_number)` — repeated requests against a warm container skip Bedrock entirely.
- Failure mode: Bedrock errors are caught at the per-ticker level. All bills for that ticker get `impact: null` and `impact_rationale: <error string truncated to 200 chars>`. The rest of the response is unaffected.

---

## Live ticker fallback

For tickers absent from `ticker_index.csv`, the function performs a live
resolution per [`_live_business_summary`](lambda_function.py) /
[`_resolve_ticker`](lambda_function.py):

1. Lazily fetch and cache `https://www.sec.gov/files/company_tickers.json` (ticker → CIK).
2. Fetch `https://data.sec.gov/submissions/CIK<10-digit>.json` for issuer name + SIC + filings index.
3. Find the latest `10-K` filing, fetch the primary document, strip HTML, extract Item 1 (Business) up to 6,000 chars.
4. If Item 1 was found, embed `"<name>. Industry: <sic>. <item1>"` (truncated to 4,000 chars) via Titan v2.
5. Cache the resulting `(vector, info)` in process memory.

If any step fails (no CIK match, network error, missing 10-K, embedding error)
the ticker gets `risk_score: null` with a `note` and an empty `top_bills`.

SEC requests use the `SEC_UA` header (default
`LegisRisk research kevinddrummer@gmail.com`) per SEC fair-access policy. urllib
does not auto-decompress, so requests don't ask for gzip; gzipped responses are
decompressed manually.

---

## Cold-start data artifacts

On import, Lambda loads four files from [`api/data/`](data/) (bundled in the
deployment zip; ~70 MB total):

| File | Shape / size | Built by | Purpose |
|---|---|---|---|
| `pipeline_bills.csv` | 15,505 rows | `API.ipynb` (Component A + Nova Pro classification) | One row per active 119th-Congress bill: `bill_type, bill_number, title, industry, p_passage, materiality, emb_row`. Drives the `PIPELINE` list and the per-bill `_P_VEC`, `_M_VEC`, `_ROW_IDX` arrays. |
| `bill_embeddings.npy` | (15505, 1024) float32 | Titan v2 over Nova-Pro exposure summaries | L2-normalized bill vectors. `emb_row` in the CSV is the row index here. |
| `ticker_index.csv` | 1,287 rows | S&P 500 + Nova-flagged tickers from EDGAR | `ticker, name, sic_description`. Row index aligns with `ticker_embeddings.npy`. |
| `ticker_embeddings.npy` | (1287, 1024) float32 | Titan v2 over SEC 10-K Item 1 | L2-normalized ticker vectors. |

Per-bill arrays are materialized once at import for fast scoring:

```python
_ROW_IDX = np.array([b["emb_row"]    for b in PIPELINE], dtype=np.int64)
_P_VEC   = np.array([b["p_passage"]  for b in PIPELINE], dtype="float32")
_M_VEC   = np.array([b["materiality"] for b in PIPELINE], dtype="float32")
```

To regenerate the artifacts, re-run [`API.ipynb`](../API.ipynb) end-to-end —
this rebuilds Component A (passage probability), regenerates Nova Pro
classifications, and re-embeds bills/tickers via Titan v2.

There are also three Parquet-format artifacts (`bill_exposures.parquet`,
`bill_index.parquet`, `bills_classified_with_risk.parquet`,
`ticker_index.parquet`, `sp500_sectors.csv`) in the data folder. These are
**not** read by the Lambda runtime — they're upstream / debugging artifacts
from the notebook. Removing them shrinks the deployment zip.

---

## Configuration

Environment variables read by [`lambda_function.py`](lambda_function.py):

| Env var | Default | Purpose |
|---|---|---|
| `PIPELINE_PATH` | `data/pipeline_bills.csv` | Override bundled bills CSV. |
| `BILL_EMB_PATH` | `data/bill_embeddings.npy` | Override bundled bill embeddings. |
| `TICKER_IDX_PATH` | `data/ticker_index.csv` | Override bundled ticker index. |
| `TICKER_EMB_PATH` | `data/ticker_embeddings.npy` | Override bundled ticker embeddings. |
| `BEDROCK_REGION` | `us-east-1` | Region for the `bedrock-runtime` client. |
| `IMPACT_MODEL_ID` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Bedrock model id (or cross-region inference profile) for impact classification. |
| `EMBED_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Bedrock model id for live ticker embedding. |
| `IMPACT_MAX_WORKERS` | `8` | Max parallel Bedrock calls per request when `analyze_impact=true`. |
| `SIM_THRESHOLD` | `0.20` | Cosine-similarity floor for a bill to count toward `risk_score`. |
| `SEC_UA` | `LegisRisk research kevinddrummer@gmail.com` | `User-Agent` header for SEC EDGAR fetches. SEC requires a contact in the UA. |

[`template.yaml`](template.yaml) currently exposes only `BedrockModelId` and
`BedrockRegion` as CloudFormation parameters. See
[Known issues](#known-issues) before relying on parameter overrides.

---

## Deployment

**Prereqs**:
- AWS CLI configured with credentials for the target account.
- AWS SAM CLI installed.
- Bedrock model access enabled in `BEDROCK_REGION` for both:
  - `anthropic.claude-sonnet-4-5-*` (or whichever `IMPACT_MODEL_ID` is set)
  - `amazon.titan-embed-text-v2`

  Bedrock console → *Model access* → request access (instant for Anthropic and Amazon models on most accounts).

**Build + deploy**:

```bash
cd api/
sam build
sam deploy            # uses samconfig.toml; first time: sam deploy --guided
```

Deploy output includes `ApiUrl`. Use it as `$API_URL` in the curl examples.

**Parameter overrides** (e.g. pinning a specific Sonnet version):

```bash
sam deploy --parameter-overrides BedrockModelId=us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

> ⚠️ See [Known issues](#known-issues) — the `BedrockModelId` parameter
> currently sets the wrong env var, so this override may not take effect.
> Set `IMPACT_MODEL_ID` directly in the SAM template until that's resolved.

### IAM

The function role is granted `bedrock:InvokeModel` on:

- `arn:aws:bedrock:<region>::foundation-model/anthropic.claude-sonnet-*`
- `arn:aws:bedrock:*:<account>:inference-profile/<BedrockModelId>`
- `arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-*` (covers cross-region inference profile fan-out)

No outbound network restrictions — the function makes plain HTTPS to
`sec.gov` and `data.sec.gov` for the live fallback path.

---

## Operational notes

- **Latency**:
  - Cold start: ~2–4 s (loads ~70 MB of artifacts into memory; numpy is the only non-stdlib dep).
  - Warm baseline (no LLM): ~50–150 ms per request regardless of ticker count, because scoring is a single matmul against `BILL_EMB`.
  - Warm with `analyze_impact=true`: ~0.5–1.5 s per ticker, parallelized up to `IMPACT_MAX_WORKERS`.
  - Live SEC fallback adds ~1–3 s per unknown ticker (multiple SEC HTTP calls + Titan embed). Cached after the first miss.
- **Cost**:
  - Baseline: essentially free (Lambda + API Gateway only).
  - Impact analysis: per ticker ≈ 5 bills × (title-only prompt) ≈ 300 input + 300 output tokens of Sonnet. At Sonnet 4.5 pricing (~$3/MTok in, $15/MTok out) that's ≈ $0.005 per ticker.
  - Live fallback embedding: one Titan v2 call per unknown ticker (~$0.00002 per call at 8k chars).
- **Caching** (per warm container only — no DynamoDB):
  - `_TICKER_TO_CIK_CACHE` — single SEC ticker→CIK map, ~14k entries.
  - `_LIVE_TICKER_CACHE` — `{ticker → {vec, info}}` for live-resolved tickers, including negative entries.
  - `_IMPACT_CACHE` — `{(ticker, bill_type, bill_number) → impact dict}`.
  - All caches die when the container is recycled. If sustained traffic warrants persistence, DynamoDB-back the impact cache first (highest hit rate, most expensive miss).
- **Limits**:
  - Max 200 tickers per request (silently truncated past that).
  - Lambda timeout 60 s — with `IMPACT_MAX_WORKERS=8` and 200 tickers asking for impact, you'd queue ~25 batches of ~1 s each. Fine for typical portfolio sizes, tight at the limit.
- **Determinism**: scoring is fully deterministic given the bundled artifacts. Impact classification uses Sonnet at `temperature=0.0`, so it's near-deterministic but not bitwise-stable.
- **No persistent state**: function is a pure read against bundled artifacts plus optional SEC + Bedrock calls.

---

## Known issues

These are real gaps between [`template.yaml`](template.yaml) and
[`lambda_function.py`](lambda_function.py) — flagged for awareness, not fixed
as part of this doc rewrite:

1. **Env-var name mismatch.** The SAM template sets `BEDROCK_MODEL_ID`, but the
   code reads `IMPACT_MODEL_ID` (and also `EMBED_MODEL_ID`). The defaults
   happen to match, so things work — but `sam deploy --parameter-overrides
   BedrockModelId=...` has no runtime effect. Fix: rename the template's
   `Environment.Variables.BEDROCK_MODEL_ID` to `IMPACT_MODEL_ID`, and add an
   `EMBED_MODEL_ID` variable + parameter if you want to make the embedding
   model overridable.

2. **IAM doesn't cover Titan embeddings.** The function policy in
   [`template.yaml`](template.yaml) only allows `bedrock:InvokeModel` on
   `anthropic.claude-sonnet-*`. The live ticker fallback calls
   `amazon.titan-embed-text-v2`, which will return `AccessDeniedException`.
   The error is swallowed in `_embed_text` so the request still returns 200,
   but unknown tickers will silently end up with `risk_score: null`. Fix: add
   `arn:aws:bedrock:<region>::foundation-model/amazon.titan-embed-text-v2*`
   to the policy `Resource` list.

3. **No CORS / auth.** The endpoint is open and unauthenticated. Fine for a
   project demo, not for production. Add an API Gateway usage plan + API key,
   or a Lambda authorizer, before exposing widely.
