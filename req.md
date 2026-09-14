# Project: FDE Skills Roadmap

Build a data pipeline that scrapes current Forward Deployed Engineer job postings,
extracts structured skill requirements, and renders a single-file HTML report.

## Hard constraints

- Do NOT scrape LinkedIn, Indeed, or any site that blocks automated access.
  Use only public APIs and job boards with permissive terms (listed below).
- Final output is ONE self-contained .html file — inline CSS/JS, no build step,
  no external assets except CDN script tags. It gets uploaded as a static page.
- Cache every raw fetch to disk. Never re-hit a source during development.

## Repo layout

fde-roadmap/
sources/ one module per source, each returning List[Posting]
extract/ LLM extraction against a fixed taxonomy
aggregate/ frequency, criticality, co-occurrence
render/ HTML generation
data/
raw/ cached API responses
processed/ normalized postings + extractions
taxonomy.yaml
main.py

## Step 1 — Collect (target: 300+ postings)

Sources:

- Greenhouse board API: boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true
- Lever: api.lever.co/v0/postings/{company}?mode=json
- Ashby: api.ashbyhq.com/posting-api/job-board/{company}
- HN Who Is Hiring via Algolia: hn.algolia.com/api/v1/search_by_date
- Remotive, Arbeitnow, Adzuna (free tiers)

Search titles for: "Forward Deployed Engineer", "Forward Deployed AI Engineer",
"Deployment Engineer", "Solutions Engineer (AI)", "Applied AI Engineer",
"Field Engineer", "Implementation Engineer AI".

Start by discovering board slugs for AI-native companies (Anthropic, OpenAI,
Scale, Sierra, Cohere, Databricks, Palantir, Glean, Harvey, Decagon, and peers) —
try each slug against all three ATS APIs and keep what resolves.

Posting schema: id, title, company, company_size_hint, location, remote_flag,
travel_mentioned, seniority_raw, url, posted_date, full_text, source.

Dedupe on (normalized_company, normalized_title).

## Step 2 — Extract

Define taxonomy.yaml FIRST as a closed vocabulary with canonical names and
aliases (so "AWS" / "Amazon Web Services" / "cloud" collapse to one node).
Six clusters: software_foundations, ai_application_engineering,
data_and_integrations, deployment_and_operations, customer_delivery,
product_thinking_and_communication.

For each posting, one LLM call returning strict JSON. Critically: extract skills
SEPARATELY per JD section, tagging each mention as one of
responsibility | requirement | nice_to_have
Segment the JD into these sections before extraction. This tagging is the
backbone of the whole analysis — do not skip it.

Also extract: seniority (normalized), years_required, travel_expectation,
customer_facing_intensity (1-5), top 5 responsibility verbs.

Validate every extracted skill against the taxonomy; log and review rejects.
Run 10 postings first, show me the output, wait for approval before the full run.

## Step 3 — Aggregate

- frequency: % of postings mentioning each skill
- criticality: share of that skill's mentions tagged `responsibility`
  (vs requirement/nice_to_have)
- co-occurrence: lift between skill pairs, keep only pairs above chance,
  cluster into 3-4 named "stacks that travel together"
- seniority distribution, travel/customer-facing distribution
- gap analysis: FDE skill frequencies vs a hardcoded list of what standard
  "AI engineer roadmaps" teach — surface what FDE demands that they omit

## Step 4 — Render HTML

Sections in order:

1. What an FDE does — horizontal flow diagram:
   Discover → Scope → Prototype → Integrate → Deploy → Evaluate → Improve → Feed back
2. Most requested technologies — horizontal bar chart, sorted, colored by cluster
3. **Frequency vs Criticality scatter** — X = frequency, Y = criticality.
   Four labeled quadrants. This is the centerpiece; give it the most space.
   Annotate the outliers (high-frequency/low-criticality like Python;
   low-frequency/high-criticality like stakeholder communication).
4. Capability clusters — the six, each with its member skills and coverage %
5. Learning roadmap — staged tracks, visual progression. For the Python track,
   lead with what to SKIP, not just what to learn.
6. Market insights — seniority, travel, customer-facing intensity, common
   responsibilities. Startup vs enterprise as directional prose only, not
   precise bars (sample sizes too thin to defend).
7. Proof projects — 4 build specs, each with scope, what it proves, and which
   clusters it exercises
8. Methodology — sources, n, date range, extraction approach, stated limitations

Use Chart.js or D3 via CDN. Responsive. Readable on mobile.
Leave a clearly marked placeholder div in Section 7 where I'll add one
sentence of my own — don't write any promotional copy yourself.

## Order of work

Ask me to approve taxonomy.yaml before extraction, and the 10-posting sample
before the full run. Build the HTML against fixture data first so rendering
work isn't blocked on collection.

==

the HTML style guide is under "/Users/pk/Documents/MyApps/owlhub/owl-hub"
