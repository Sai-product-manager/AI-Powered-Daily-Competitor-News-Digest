"""
mock_run.py

Purpose: This is NOT a mock of the workflow's *logic* - the flatten/dedupe,
relevance-filter, and digest-building functions below are direct Python ports
of the exact JavaScript used inside the n8n Code nodes in
`competitor-news-digest.json` (see: "Extract & Flatten Articles",
"Filter Low-Relevance News", "Build Daily Digest").

What IS mocked, per the submission guidelines' allowance for mock data:
  1. The NewsAPI.org response (mock_newsapi_responses.json) - stands in for
     a live API call, since this sandbox has no NewsAPI key.
  2. The AI summarize/categorize/score step (mock_ai_summarize) - stands in
     for the real OpenAI/Claude HTTP Request call, since this sandbox has no
     OpenAI/Anthropic key wired up. It's a simple deterministic heuristic,
     clearly separated from the real pipeline logic, so everything else in
     this trace is genuine, executed code - not a written description.

Run: python3 mock_run.py
Outputs: execution_log.txt, digest_slack_blocks.json, digest_email.html
"""

import json
import re
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Step 1: Load competitors (mirrors "Get Competitors (Google Sheets)" +
# "Filter Active + Build Query")
# ---------------------------------------------------------------------------

def load_competitors(csv_path):
    competitors = []
    with open(csv_path) as f:
        header = f.readline().strip().split(",")
        for line in f:
            row = dict(zip(header, line.strip().split(",")))
            if row.get("Active", "").upper() == "TRUE":
                competitors.append({
                    "competitor": row["Name"],
                    "query": row.get("SearchQuery") or row["Name"],
                })
    return competitors


# ---------------------------------------------------------------------------
# Step 2: Extract & Flatten Articles
# (direct port of the "Extract & Flatten Articles" Code node)
# ---------------------------------------------------------------------------

def extract_and_flatten(news_by_competitor, cap_per_competitor=5):
    seen = set()
    out = []
    for competitor, response in news_by_competitor.items():
        articles = response.get("articles", [])[:cap_per_competitor]
        for a in articles:
            url = a.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            out.append({
                "competitor": competitor,
                "title": a.get("title"),
                "description": a.get("description", ""),
                "url": url,
                "source": a.get("source", {}).get("name", "Unknown"),
                "publishedAt": a.get("publishedAt"),
            })
    return out


# ---------------------------------------------------------------------------
# Step 3: AI Summarize & Categorize -- MOCKED (see module docstring).
# In production this is an HTTP Request node to OpenAI/Claude using the
# exact prompt documented in the submission PDF / README.
# ---------------------------------------------------------------------------

CATEGORY_RULES = [
    (r"\b(raise[sd]?|funding|round|invest\w*)\b", "Funding"),
    (r"\b(partner\w*|integrat\w*)\b", "Partnership"),
    (r"\b(campaign\w*|brand\w*|\bads?\b)\b", "Marketing"),
    (r"\b(launch\w*|roll(s|ed)?\s?out|ship(s|ped)?|release[sd]?)\b", "Product Launch"),
    (r"\b(appoint\w*|\bvp\b|hir\w*|joins?\sas|names?)\b", "Hiring/Leadership"),
    (r"\b(lawsuit\w*|regulat\w*|antitrust|compliance)\b", "Legal/Regulatory"),
]

def mock_ai_summarize(article):
    text = f"{article['title']} {article['description']}".lower()

    category = "Other"
    for pattern, cat in CATEGORY_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            category = cat
            break

    # naive summary: trim description to ~2 sentences
    desc = article["description"].strip()
    sentences = re.split(r"(?<=[.!?])\s+", desc)
    summary = " ".join(sentences[:2]) if sentences else desc

    # relevance heuristic: generic listicle / roundup mentions score low,
    # named/strategic moves score high
    relevance = 8
    if re.search(r"\b(roundup|listicle|mentioned|briefly)\b", text, re.IGNORECASE):
        relevance = 3
    elif category in ("Funding", "Product Launch", "Partnership", "Hiring/Leadership"):
        relevance = 8
    elif category == "Marketing":
        relevance = 6
    else:
        relevance = 5

    return {**article, "summary": summary, "category": category, "relevance_score": relevance}


# ---------------------------------------------------------------------------
# Step 4: Filter Low-Relevance News
# (direct port of "Filter Low-Relevance News" Code node)
# ---------------------------------------------------------------------------

def filter_low_relevance(articles, min_relevance=6):
    return [a for a in articles if a.get("relevance_score", 0) >= min_relevance]


# ---------------------------------------------------------------------------
# Step 5: Build Daily Digest
# (direct port of "Build Daily Digest" Code node)
# ---------------------------------------------------------------------------

def build_daily_digest(articles):
    by_competitor = {}
    for a in articles:
        by_competitor.setdefault(a["competitor"], []).append(a)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slack_blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🗞️ Competitor Digest — {today}"}}
    ]
    html = f"<h2>Competitor News Digest — {today}</h2>"

    if not by_competitor:
        slack_blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "No relevant competitor news today."}})
        html += "<p>No relevant competitor news today.</p>"
    else:
        for competitor, items in by_competitor.items():
            slack_blocks.append({"type": "divider"})
            slack_blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*{competitor}*"}})
            html += f"<h3>{competitor}</h3><ul>"
            for a in items:
                slack_blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"• *[{a['category']}]* <{a['url']}|{a['title']}>\n{a['summary']}"}
                })
                html += f"<li><b>[{a['category']}]</b> <a href=\"{a['url']}\">{a['title']}</a><br>{a['summary']}</li>"
            html += "</ul>"

    return {"slackBlocks": slack_blocks, "htmlBody": html, "date": today, "articleCount": len(articles)}


# ---------------------------------------------------------------------------
# Run the full trace and log every stage
# ---------------------------------------------------------------------------

def main():
    log = []
    def out(msg):
        print(msg)
        log.append(msg)

    out("=" * 78)
    out("EXECUTION TRACE — Competitor News Digest workflow logic")
    out(f"Run timestamp (UTC): {datetime.now(timezone.utc).isoformat()}Z")
    out("=" * 78)

    competitors = load_competitors("../sample-data/Competitors_sheet.csv")
    out(f"\n[Step 1] Loaded {len(competitors)} active competitors from Competitors_sheet.csv:")
    for c in competitors:
        out(f"    - {c['competitor']}  (query: \"{c['query']}\")")

    with open("mock_newsapi_responses.json") as f:
        news_by_competitor = json.load(f)
    total_raw = sum(len(v["articles"]) for v in news_by_competitor.values())
    out(f"\n[Step 2] Fetched mock NewsAPI responses for {len(news_by_competitor)} competitors, {total_raw} raw articles total.")

    flattened = extract_and_flatten(news_by_competitor)
    out(f"\n[Step 3] Extract & Flatten Articles -> {len(flattened)} unique articles after dedupe/cap:")
    for a in flattened:
        out(f"    - [{a['competitor']}] {a['title']}")

    summarized = [mock_ai_summarize(a) for a in flattened]
    out(f"\n[Step 4] AI Summarize & Categorize (mocked model call) -> {len(summarized)} articles scored:")
    for a in summarized:
        title_short = (a['title'][:42] + "...") if len(a['title']) > 45 else a['title']
        out(f"    - [{a['competitor']:<8}] cat={a['category']:<16} rel={a['relevance_score']}  \"{title_short}\"")

    kept = filter_low_relevance(summarized, min_relevance=6)
    dropped = len(summarized) - len(kept)
    out(f"\n[Step 5] Filter Low-Relevance News (threshold >= 6) -> kept {len(kept)}, dropped {dropped}:")
    for a in summarized:
        status = "KEPT   " if a["relevance_score"] >= 6 else "DROPPED"
        title_short = (a['title'][:52] + "...") if len(a['title']) > 55 else a['title']
        out(f"    - [{status}] ({a['relevance_score']}/10) {title_short}")

    digest = build_daily_digest(kept)
    out(f"\n[Step 6] Build Daily Digest -> {digest['articleCount']} articles across {len(set(a['competitor'] for a in kept))} competitors.")

    with open("digest_slack_blocks.json", "w") as f:
        json.dump(digest["slackBlocks"], f, indent=2)
    with open("digest_email.html", "w") as f:
        f.write(digest["htmlBody"])

    out("\n[Step 7] Wrote outputs:")
    out("    - digest_slack_blocks.json  (payload for Slack chat.postMessage)")
    out("    - digest_email.html         (payload for Email Send node)")
    out("\n[Note] Delivery nodes (Slack API call, SMTP send) and the live")
    out("NewsAPI/OpenAI HTTP calls were not exercised in this sandbox (no")
    out("live credentials here) - only the transformation logic was run,")
    out("using the exact functions ported from the n8n Code nodes.")
    out("=" * 78)

    with open("execution_log.txt", "w") as f:
        f.write("\n".join(log))

if __name__ == "__main__":
    main()
