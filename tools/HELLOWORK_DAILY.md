# Daily Hello Work publication

Production entry point: `python tools/hellowork_daily.py`.
The older discovery/diff/merge scripts remain available for offline regression and dry runs.

- Search reads one result page and schedules at most five candidates (two search requests).
- Verification makes at most 100 detail requests per execution, with four seconds between requests.
- No further detail request starts once 600 seconds have elapsed. A request already in progress can take up to its 30-second timeout, plus parsing time. The workflow has a separate 15-minute timeout.
- Previous public cards (at most three) and search candidates (at most five) have priority. Remaining slots advance oldest-attempt-first, including failed requests. Repeated search results cannot consume the entire verification budget.
- `data/hellowork-auto-state.json` stores every record, last attempt, last successful verification, lifecycle reason and published IDs. Unprocessed records become pending, never implicitly active or closed.
- Each execution constructs its public candidates exclusively from successful matching detail checks in that execution. Closed, ambiguous, mismatched, failed and deferred records are excluded. At most three freshly verified cards are selected; fewer are possible when fewer can be verified safely.
- A successful run commits both the queue and public JS, even when other records remain pending or require review. This prevents a permanent retry of the same initial batch.
- Confirmed closed records remain as history without recurring requests. Reappearance in search permits a fresh check.
- Search failure or an unexpected software failure still fails the workflow and preserves the previously committed files. Per-job request failures are recorded and do not prevent other checks.
- The audit artifact records limits, counts, published IDs and review reasons. No external failure is reported as a successful verification.

Regression tests include 1,000-record queue progress, request and time budgets, publication exclusion, closed-state handling, and a two-execution persistence test.

Limit sizing (2026-10-15): production run 38662648731 completed search and 20 checks in 96.1 seconds, including four-second request spacing. At this observed rate, 42 records take roughly 3.4 minutes and 100 records roughly eight minutes. The 600-second verification budget leaves room for ordinary variation; slow requests still defer the remainder safely. Each audit now includes actual verification elapsed seconds. These estimates are not a response-time guarantee.
