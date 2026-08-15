# Competitor News Digest — n8n Workflow

Automatically fetches, summarizes, categorizes, and delivers competitor news every morning at 8:00 AM, with an optional Friday weekly rollup.

**File to import:** `competitor-news-digest.json` (n8n → Workflows → Import from File)

---

## 1. What it does

**Daily pipeline (8:00 AM):**
1. Reads your active competitor list from a **Google Sheet**.
2. For each competitor, calls **NewsAPI.org** (`/v2/everything`) for articles from the last 24 hours.
3. Flattens and dedupes articles (top 5 most recent per competitor, no duplicate URLs).
4. Sends each article to an **AI model** (OpenAI or Claude) with a prompt that returns strict JSON: a 2–3 line summary, a category (`Product Launch`, `Funding`, `Partnership`, `Hiring/Leadership`, `Legal/Regulatory`, `Marketing`, `Other`), and a 1–10 relevance score.
5. Filters out low-relevance noise (score < 6).
6. Logs every kept article to a **History** Google Sheet (for trend tracking).
7. Builds a grouped digest (by competitor → category) and sends it to **Slack** and **email**.

**Weekly pipeline (Friday 9:00 AM):**
1. Reads the last 7 days from the History sheet.
2. Asks the AI model for an executive rollup: top trends across competitors + one line per competitor.
3. Sends the rollup to Slack and email.

---

## 2. Architecture (node flow)

```
Daily Trigger (8AM)
  → Get Competitors (Google Sheets)
  → Filter Active + Build Query            [Code]
  → Fetch Competitor News (NewsAPI)        [HTTP Request]
  → Extract & Flatten Articles             [Code]
  → AI Summarize & Categorize              [HTTP Request → OpenAI/Claude]
  → Parse AI Output                        [Code]
  → Filter Low-Relevance News              [Code]  ── (score < 6 dropped)
      ├─→ Log to History Sheet             [Google Sheets: Append]
      └─→ Build Daily Digest               [Code]
              ├─→ Send Slack Digest        [Slack]
              └─→ Send Email Digest        [Email/SMTP]

Weekly Trigger (Fri 9AM)
  → Read History (Google Sheets)
  → Filter Last 7 Days                     [Code]
  → AI Weekly Rollup                       [HTTP Request → OpenAI/Claude]
  → Build Weekly Digest                    [Code]
      ├─→ Send Weekly Slack                [Slack]
      └─→ Send Weekly Email                [Email/SMTP]
```

---

## 3. APIs & tools used

| Purpose | Service | Node type | Free tier |
|---|---|---|---|
| Competitor news | [NewsAPI.org](https://newsapi.org) `/v2/everything` | HTTP Request | 100 req/day |
| Summarization + categorization + scoring | OpenAI `gpt-4o-mini` (chat completions) — or swap for Anthropic Claude, see §5 | HTTP Request | pay-as-you-go |
| Competitor list + history | Google Sheets | Google Sheets node | free |
| Delivery | Slack (`chat.postMessage`) | Slack node | free |
| Delivery | SMTP (Gmail, Outlook, etc.) | Email Send node | free |
| Scheduling | n8n Cron | Schedule Trigger | built-in |

---

## 4. Required credentials / configuration

**No API keys are included in this submission.** Configure the following in your n8n instance before running:

### Environment variables
| Variable | Used for | Where to get it |
|---|---|---|
| `NEWSAPI_KEY` | NewsAPI.org authentication | [newsapi.org/register](https://newsapi.org/register) |
| `OPENAI_API_KEY` | AI summarization | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `COMPETITORS_SHEET_ID` | Google Sheet ID holding the `Competitors` tab | From the sheet's URL |
| `HISTORY_SHEET_ID` | Google Sheet ID holding the `History` tab (can be the same sheet as above) | From the sheet's URL |
| `SLACK_CHANNEL_ID` | Slack channel to post digests to | Right-click channel → "Copy link" → ID is the last segment |
| `DIGEST_FROM_EMAIL` | Sender address for the email digest | Your verified SMTP sender |
| `DIGEST_TO_EMAIL` | Recipient (you, the PM) | Your inbox |

Set these under **n8n → Settings → Environment Variables** (self-hosted) or your n8n Cloud project's environment settings.

### n8n Credentials (configure under n8n → Credentials)
- **Google Sheets account** — OAuth2, used by "Get Competitors", "Log to History Sheet", "Read History"
- **Slack account** — OAuth token with `chat:write` scope, used by "Send Slack Digest" / "Send Weekly Slack"
- **SMTP account** — used by "Send Email Digest" / "Send Weekly Email"

### Google Sheet structure
**Tab `Competitors`**
| Name | SearchQuery | Active |
|---|---|---|
| Notion | Notion app | TRUE |
| Linear | Linear.app | TRUE |

**Tab `History`** (auto-populated by the workflow — create empty with just headers)
| Date | Competitor | Category | Headline | Summary | RelevanceScore | URL |
|---|---|---|---|---|---|---|

Sample CSVs for both are in `sample-data/` for quick import.

---

## 5. Using Claude instead of OpenAI

Both AI nodes (`AI Summarize & Categorize`, `AI Weekly Rollup`) are plain HTTP Request nodes so they're easy to swap. Replace the URL/headers/body with:

- URL: `https://api.anthropic.com/v1/messages`
- Headers: `x-api-key: {{$env.ANTHROPIC_API_KEY}}`, `anthropic-version: 2023-06-01`, `content-type: application/json`
- Body: `{ "model": "claude-sonnet-4-5", "max_tokens": 300, "messages": [{ "role": "user", "content": "<same prompt>" }] }`
- Parsing node: read `$json.content[0].text` instead of `$json.choices[0].message.content`

---

## 6. Optional extensions — status

| Extension | Included? | Notes |
|---|---|---|
| History in Google Sheets to track trends | ✅ Yes | "Log to History Sheet" node, append-only |
| Friday weekly rollup (Slack/email) | ✅ Yes | Separate trigger + branch in the same workflow file |
| Filter out low-relevance news (AI scoring) | ✅ Yes | AI returns `relevance_score` 1–10; threshold of 6 applied in "Filter Low-Relevance News" (adjust `MIN_RELEVANCE` in that Code node) |

---

## 7. How to demo it

1. Import `competitor-news-digest.json` into n8n.
2. Create the two credentials (Google Sheets, Slack) and the SMTP credential, plus the environment variables in §4.
3. Import `sample-data/Competitors_sheet.csv` into a Google Sheet tab named `Competitors`; create an empty `History` tab with just the header row.
4. Open the workflow and click **"Execute Workflow"** on the `Daily Trigger` node to run it manually (bypassing the 8 AM schedule) — this exercises the full pipeline end to end against live NewsAPI + AI calls.
5. Check the configured Slack channel and inbox for the digest; check the `History` tab for logged rows.
6. To demo the weekly rollup without waiting for Friday, manually execute the `Weekly Trigger (Friday 9AM)` node instead.
7. `sample-data/example_digest_output.md` shows expected output formatting if you want to preview it without running live API calls (mock data only, per submission guidelines — real runs use live NewsAPI/AI responses, not this file).

---

## 8. Known limitations / things to tune before production use

- NewsAPI's free tier only returns articles up to 24h old and caps at 100 requests/day — each competitor consumes 1 request per run, so keep the active competitor list ≤ ~15–20 to leave headroom for weekly runs and reruns.
- The relevance threshold (6/10) and "top 5 articles per competitor" cap are both adjustable constants in the Code nodes — tune based on how noisy your competitor set is.
- Google Sheets is used for both competitor config and history for simplicity; a database (Airtable, Postgres) would scale better past a few hundred rows.
