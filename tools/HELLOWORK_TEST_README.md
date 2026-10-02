# Hello Work small-scale acquisition test

This directory contains a **test-only** fetcher for E-FACE JOBS.

## Safety constraints

- It does not update `hellowork-demo.js`, `jobs.js`, or any public Pages data.
- It only reads explicit seed URLs in `hellowork_test_seeds.txt`.
- Each run is capped at 10 jobs.
- A minimum 3-second interval is enforced between requests.
- Employer-non-public markers cause automatic exclusion.
- Images and map data are never imported.
- The GitHub Actions workflow is `workflow_dispatch` only; no daily schedule is enabled.

## Purpose

Phase A verifies that a small number of generally public Hello Work job-detail pages can be normalized into an E-FACE-compatible JSON structure. Discovery/search automation is intentionally deferred until this parser test is reviewed.

## Output

`data/hellowork-test-output.json`

The Actions workflow uploads that JSON as an artifact. It does not commit the output back to the repository or publish it through GitHub Pages.


## Discovery test

`hellowork_discovery_test.py` connects the official search page to the detail parser.

Current safeguards:
- first search-result page only
- official area group `401 / 北九州市～福岡市`
- prefilter on the search page: work location must start with `福岡県福岡市`
- prefilter on the search page: public scope must be `1`
- at most 10 detail requests
- minimum 3 seconds between detail requests
- second location/public checks on the detail page
- output artifact only; no Pages publication


## Incremental update / diff test

`hellowork_diff_test.py` compares current and previous snapshots by Hello Work job number.

It classifies:
- `new`
- `active`
- `changed`
- `ended_candidate`

Important: `ended_candidate` is not deleted immediately. Because the current discovery scope is first-page-only, disappearance from the current snapshot is only a recheck signal.

`hellowork_discovery_test.py --previous <snapshot.json>` reuses detail data for job numbers already present in the previous snapshot. Existing jobs are not detail-fetched again. Only newly discovered job numbers are sent to the detail parser.

Verified with real public jobs:
- first run: 5 detail fetches
- second run with previous snapshot: 0 detail fetches, 5 reused existing records

Synthetic diff regression also verifies 1 new / 1 active / 1 changed / 1 ended_candidate.
