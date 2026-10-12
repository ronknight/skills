---
name: email-campaign-attribution
description: Attribute orders to email campaigns honestly - join email-platform engagement (clicks, opens) to CRM or shop orders by normalized email address, credit the last click within a window (opens as a separate, clearly labelled tier), rank campaigns by revenue per recipient, and report coverage, match rate and a no-causation disclaimer with every number. Use when asked which campaigns drive revenue, when building a campaign leaderboard or closed-loop report from Mailchimp, Klaviyo or a similar platform plus a CRM, or when adding an email open pixel that reports to GA4.
license: MIT
---

# Email campaign attribution

The question is "which campaigns made money?". Without a holdout group you
can't answer it causally. You can answer "which campaigns were the last thing a
buyer engaged with before ordering", and say so on every output. Done carefully,
that is still the most useful ranking marketing has.

## Pipeline

```
extract engagement -> extract orders -> resolve identity -> attribute in a window -> rank -> report with context
```

Read-only against every source system. Land raw extracts first (files or a
local database such as DuckDB or SQLite), then build the model from them, so a
rerun doesn't call the APIs again.

## Extract

- **Campaign worklist from the API** (`status = sent`), not from a CSV export.
  Exports miss campaigns, and the gap is usually drafts, not data loss. Diff the
  two both ways and report the difference.
- **Per-person clicks** are the valuable data, and often the expensive one:
  some platforms only return click members per link, so the call count is
  campaigns × clicked links. Measure that before promising a runtime.
- **Make extraction resumable**: a checkpoint table keyed by campaign (and link)
  so a killed run continues instead of starting over. Build it first, before the
  first long backfill.
- Bound long backfills with flags (months of history, links per campaign) that
  **report what they skipped**, so missing coverage stays visible.
- Check report data retention: per-member data for old campaigns may be gone.
- **Roster: all statuses.** Don't filter to subscribed members. Someone who
  ordered and then unsubscribed is still attributable.

## Identity

Email is the join key. Normalize:

- trim, lowercase, Unicode NFKC;
- strip `+tag` suffixes **only** for providers known to ignore them (Gmail and
  Google Workspace consumer addresses);
- **don't strip dots**: that's a Gmail-only rule and wrong for business domains.

Resolve in ordered rules (for example order email, then account email fields,
then a customer-number merge field on the email platform) and record which rule
matched. Unmatched people are counted, never attributed.

- **Suppress role and internal addresses** (`sales@`, `info@`, `orders@`,
  `noreply@`, your own domain) from person-level attribution. One shared inbox
  can dominate the engagement data.
- **Fan-out**: one email can map to several customer accounts. Split the credit
  evenly and record the split factor, rather than picking one silently.
- **CRM duplicates**: if the matched account is in a known duplicate group, mark
  the match as degraded. Duplicates split revenue across records.
- Report the match rate **per list**. A low rate on a leads list is a fact about
  that list, not a pipeline bug.

## Orders

- Use **billed** order states only (for example invoiced). Exclude quotes,
  baskets and cancellations by name, and raise a data-quality metric for any
  state you don't recognise instead of silently including or dropping it.
- Watch for one order appearing in several states over time (pending, then
  invoiced) under the same ID; count it once.
- Cross-check total order revenue per period against the accounting ledger, and
  show the difference.

## Attribution

For each order by person *p* on date *d*:

1. Take *p*'s engagement events with `event_time <= d`.
2. **Click within N days** (for example 30): tier A, credited to the most
   recent click.
3. Otherwise **open within M days** (for example 14): tier B, most recent open.
4. Otherwise unattributed.

- **Windows are configuration.** Platform defaults (often 5 days or 24 hours)
  suit consumer retail. B2B reorder cycles are longer. Measure the
  days-to-order distribution and set the windows from it.
- **Run a window-sensitivity test** (7, 14, 30, 60 days). If the results barely
  change, engagement isn't discriminating, and the report must say the model is
  weak.
- **Never add tier A and tier B together.** Opens are inflated by privacy
  proxies (Apple Mail Privacy Protection pre-loads images) and most platforms
  expose no flag to filter them. Report click-attributed and open-associated
  revenue side by side, never as one "email revenue" total.

See [references/attribution.sql](references/attribution.sql) for the window
join.

## Metrics

| Metric | Why |
|---|---|
| **Revenue per recipient** (tier A revenue / delivered) | the ranking metric; campaign sizes vary by orders of magnitude, so totals mislead |
| Tier A revenue, tier B revenue | adjacent, never summed |
| Unique clicks, **CTOR** (unique clicks / unique opens) | the honest engagement metric after privacy-proxy opens |
| Median days-to-order | the empirical check on the windows |
| Unattributed share | how much revenue email can't claim |

## Every output carries context

- Coverage: share of orders with a resolvable email, identity match rate.
- Tier mix: A, B, unattributed.
- The window used.
- The disclaimer: "Last-touch association within a window. Not incremental
  revenue."

Real incrementality needs holdout groups at send time. That's a separate
project; recommend it rather than implying the attribution measures it.

## Useful by-products

- **Engaged, not converted**: recent clickers with no order, grouped by owning
  sales rep. Often the most actionable list in the project.
- **Identity audit sample**: 100 random resolved matches with a blank verdict
  column for a person to check by hand.

## Open pixel to GA4 (optional)

A 1x1 GIF endpoint can forward an `email_open` event to GA4 through the
Measurement Protocol:

- Read `measurement_id` and `api_secret` from environment variables on the
  server; never put them in the email.
- Always return the GIF, even if the GA4 call fails, with `Cache-Control:
  no-store`.
- **Don't send personal data to GA4**: no email addresses or names in
  parameters (Google's terms forbid it). Use an opaque client ID or a hashed
  account reference.
- Pixel opens carry the same privacy-proxy inflation. Treat them like tier B.

## Handling the data

Engagement and order data is personal and commercial. Keep extracts and the
local database out of git and out of public places, read credentials from
environment variables, and share only aggregated outputs.
