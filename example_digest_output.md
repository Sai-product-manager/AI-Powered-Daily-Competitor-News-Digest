# Example Output — Daily Digest (mock run, 2026-08-13, 8:00 AM)

This is what lands in Slack / email after one full run of the workflow, using the mock competitor list and NewsAPI-style responses.

---

## 🗞️ Competitor Digest — 2026-08-13

---
**Notion**
• *[Marketing]* [Notion launches new brand campaign](https://example.com/notion-campaign)
Notion kicked off a global ad campaign positioning itself as the "connected workspace" for modern teams.

---
**Linear**
• *[Product Launch]* [Linear ships customer requests triage view](https://example.com/linear-triage)
Linear released a new triage view to help teams turn customer feedback into prioritized product work faster.

---
**ClickUp**
• *[Partnership]* [ClickUp partners with Zoom](https://example.com/clickup-zoom)
ClickUp announced a native Zoom integration letting users start and log meetings directly from tasks.

---

*(Notion's AI-notes story and Linear's funding story from the day before scored below the relevance threshold on day 2 and were logged to History but not re-sent — this is the low-relevance filter at work.)*

---

## Example Weekly Rollup — sent Friday 9:00 AM

> **📊 Weekly Competitor Rollup — week of 2026-08-15**
>
> Top trends this week:
> 1. **AI features are the battleground** — Notion (AI meeting notes) and Asana (new VP of Product for AI) both made explicit AI plays.
> 2. **Integrations as a wedge** — ClickUp's Zoom partnership suggests competitors are competing on "where work already happens" rather than building everything natively.
> 3. **Linear continues to out-ship on workflow tooling** — two product-facing updates (triage view, funding to expand roadmap) in one week.
>
> Per competitor:
> - **Notion:** Leaning into AI + a new brand campaign — doubling down on both product and positioning.
> - **Linear:** Well-funded and shipping fast; keep an eye on enterprise features.
> - **Asana:** Investing in AI leadership — expect AI-related launches in the next 1–2 quarters.
> - **ClickUp:** Expanding via partnerships rather than net-new features this week.

---

*Note: article content above is mock data (see `sample-data/History_sheet.csv`) standing in for real NewsAPI.org responses, used only to demonstrate formatting and grouping logic end-to-end without consuming API quota.*
