# Car prices (Brazil) — project outline

This document describes the **logical structure** of the work: phases, high-level approaches, and how **testing** supports each step. It intentionally avoids naming specific programming languages, frameworks, or products so the plan can stay stable as implementation choices evolve.

---

## Goals

1. **Ingest** listing data from a **chosen, permitted** source (e.g. a public marketplace) in a controlled, respectful way and with a **strictly bounded** request volume to that source.
2. **Process** raw material into a **clean, consistent** representation suitable for analysis.
3. **Persist** that representation in a **relational** database with a clear model and traceability.
4. **Analyze** which factors are most associated with used-car prices in Brazil, with results that are **reproducible** and **auditable**.

---

## Guiding principles

- **Reproducibility:** The same inputs and configuration should yield the same stored dataset (within defined tolerances, e.g. time-dependent fields).
- **Separation of concerns:** Ingestion, cleaning, storage, and analysis are separate layers with explicit contracts between them.
- **Observability:** Each layer should report enough metadata (counts, errors, run identifiers) to debug failures without re-scraping blindly.
- **Ethics and compliance:** Respect the source’s terms of use, robots policy, and any published limits; design ingestion so it can be throttled, stopped, and audited. (Specific rules belong in a compliance note when implementation begins.)
- **Low request footprint:** Ingestion must not generate a **large or unbounded** number of HTTP calls. Prefer explicit **caps** (e.g. max requests per run, per day, or per time window), **delays** between calls, and **idempotent, cacheable** fetches so development, tests, and reprocessing do not multiply traffic.
- **Remote-safe repository:** Anything that **identifies a specific data source** (URLs, hostnames, source-specific field inventories, and similar discovery notes) lives in **local-only** files (see Phase 1). What is **committed** stays **generic**—schema shape, example placeholders, and tests on **synthetic** fixtures—so the remote copy of the project never needs to name a website.

---

## Phase 1 — Discovery and data contract

**Objective:** Understand what the source exposes (fields, units, categories, pagination) and freeze a **target schema** (logical model) for “what we want in the database,” independent of how HTML or APIs look today.

**Approach:**

- **Where the details live:** Record discovery and contract decisions in **machine-readable files** under a **gitignored** tree (e.g. `config/local/`) so application code and tooling can read them, while the **git remote** never receives source-specific names or URLs. Keep a **committed** example in `config/examples/` (shape only, no real endpoints or brands).
- **`.gitignore`:** Ignore the local directory (see repo root `.gitignore`). Treat anything there as **sensitive to attribution** of the data source, not as secrets in the cryptographic sense—same rule: it does not ship to the remote.
- Map **source fields** → **canonical names**, types, and allowed values (e.g. fuel type, body style, location).
- Define **primary entities** (e.g. listing, vehicle attributes, seller/location, snapshot time) and **relationships** (e.g. one listing over time = multiple observations if re-scraped).
- Decide **identity rules**: what uniquely identifies a listing, and how updates vs new listings are distinguished.
- Document **known gaps** (optional fields, inconsistent labels) and how they will be represented (null, “unknown,” or a separate code). Store gap notes in the same **local** files (or a dedicated local file) when they reference the live source.

**Testing:**

- **Contract tests:** Fix **small, versioned fixtures** (saved responses or **synthetic** records with **no** real domains or source-identifying strings) that represent “valid raw input” and assert they map to the canonical model without loss of required fields. Optional: a **local** copy of a sanitized real response for dev only, never committed.
- **Schema validation tests:** For any defined JSON/XML/intermediate format, assert invalid examples are **rejected** with clear errors.
- **Edge-case tables:** Examples of missing mileage, special editions, or duplicate titles—expected canonical output documented once and tested.

---

## Phase 2 — Ingestion (scraping / collection)

**Objective:** Reliably collect listing data at a defined **cadence** (e.g. daily, weekly) and hand off **raw or lightly normalized** payloads to the processing layer, while keeping **call volume small and predictable**.

**Approach:**

- **Request budget:** Define a **hard ceiling** on how many network requests a run may perform (and optionally per day/week). Treat the source gently: **sequential or low-concurrency** fetches, **fixed minimum interval** between requests, and no tight loops that retry without backoff. Scale scope by **widening the budget in config**, not by accident.
- **Entry points:** Use a **narrow, explicit** set of search or category entry points (e.g. location, make/model, year range) so collection is **bounded** rather than an open-ended crawl of the whole site.
- **Robustness:** Retries with backoff, handling of empty pages, and detection of **structural change** (layout or API change) vs transient errors—without multiplying retries into a **traffic storm** (cap total retries per URL and per run).
- **Raw layer:** Store or stream **minimal raw artifacts** (or checksums) so **reprocessing and parser work** use local data whenever possible, not repeat downloads of the same resource.
- **Deduplication at ingest:** Optional light deduplication by stable listing id if the source provides it; heavy merging stays in processing/DB. Avoid fetching the same listing page **more than once** within a run when its id is already known.
- **Configuration:** All limits (request budget, concurrency, inter-request delay, depth, scope) **externalized** so tests and production differ only by config; default test/local config should use **fixtures** or a **trivial** request budget, not the live source at scale.

**Testing:**

- **Recorded-response tests:** Run the fetch + parse pipeline against **fixtures** (not the live site) in CI to catch regressions when parsers change.
- **Integration smoke:** A **manual or scheduled** small live run in a non-CI environment validates that the real site is still compatible (separate from fast CI).
- **Property-style checks** where applicable: e.g. “every parsed listing has a non-empty id and a numeric price when the page is complete.”
- **Failure-injection tests:** Timeouts, empty HTML, or HTTP errors assert documented behavior (retry, skip, log, alert).

---

## Phase 3 — Processing and formatting

**Objective:** Transform ingested payloads into **clean rows** that match the relational model: normalized units, parsed numbers, consistent enums, and derived fields only when their definition is explicit.

**Approach:**

- **Parsing:** Extract numbers (price, mileage, engine displacement), dates, and text fields; handle Brazilian formats (e.g. thousands separators, `R$`, km).
- **Normalization:** Map strings to **controlled vocabularies** (make/model can stay text initially; fuel, transmission, and body type benefit from enums).
- **Geography:** Normalize city/state (or use stable codes) if the analysis requires regional controls.
- **Deduplication and history:** If the same listing is seen multiple times, define **surrogate keys**, **SCD-style** history, or “last seen” fields according to analytical needs.
- **Data quality flags:** Add boolean or enum columns for “suspicious” rows (e.g. price 0, mileage extreme) rather than silent drops, unless a strict filter is explicitly required.

**Testing:**

- **Unit tests** for every pure function: price parser, odometer parser, year validation, enum mapping.
- **Table-driven tests** for messy real-world strings (fixtures from Phase 1).
- **Regression tests** when business rules change (e.g. “drop vs flag” policy for invalid rows).
- **Cross-layer tests:** A full **golden file**: fixture in → expected normalized record out, compared field-by-field.

---

## Phase 4 — Relational storage

**Objective:** Load processed data into a **relational** database with **referential integrity**, **indexes** for common filters, and a path for **migrations** as the schema evolves.

**Approach:**

- **Core tables:** e.g. listings, vehicle attributes, optional seller/location dimensions, and **ingestion run** metadata (batch id, started_at, source, row counts).
- **Keys:** Surrogate primary keys; **natural keys** (platform listing id) with uniqueness constraints as appropriate.
- **Time:** Store **observed_at** / **collected_at** to support time-series and “price changed” analysis.
- **Idempotent loads:** For a given batch, re-running load should not duplicate rows (upsert or merge rules defined explicitly).
- **Performance:** Defer heavy indexing to requirements; start with query patterns the analysis will need (e.g. by state, year, make).

**Testing:**

- **Migration tests:** Apply migrations on an empty DB and on a **copy of production-like** schema; assert forward compatibility expectations.
- **Repository/integration tests:** Insert and read round-trips; foreign key and uniqueness constraints verified with negative cases.
- **Load tests (optional, later):** If volume is large, validate batch load duration and index usage on a subset.

---

## Phase 5 — Analysis (factors affecting prices)

**Objective:** Use the stored data to study **which factors are most associated with price** in Brazil, with transparent assumptions and limitations.

**Approach:**

- **Cohort definition:** e.g. used cars only, year or segment filters, exclude obvious data errors using quality flags.
- **Target variable:** list price (or a transformed scale); consider **regional** and **time** effects.
- **Feature set:** vehicle (year, mileage, fuel, power, optional equipment if available), brand/model effects, and geography.
- **Methods (conceptual):** start with **interpretable** models (e.g. hedonic regression, regularized linear models) before complex ML; add non-linear or ensemble methods if needed, with **cross-validation** and **leakage checks** (e.g. no future information in features).
- **Reporting:** Coefficients, partial dependence or SHAP (if using ML), and **sensitivity** to outlier handling.
- **Limitations section:** Omitted variable bias, selection bias in listings, endogenous trim levels, and platform-specific pricing behavior.

**Testing:**

- **Statistical sanity checks on fixtures:** Create a **toy dataset** with known relationships (e.g. “price increases with year when mileage fixed”) and assert the pipeline recovers the **sign** and approximate **order of magnitude** of effects.
- **Reproducibility tests:** Fixed random seeds; same input file → same outputs (or within floating-point tolerance for iterative solvers).
- **Data leakage tests:** Assertions that test splits do not include future time or duplicate listings across train/test.
- **Notebook or report checks:** If analysis is in notebooks, treat “export final figures from a run script with tests for figure inputs” or snapshot tests for critical summary tables.

---

## Cross-cutting — Testing and quality

| Layer        | What we prove                          | Typical test style                          |
|-------------|----------------------------------------|---------------------------------------------|
| Ingestion   | Parser + fetch error handling; respects request caps | Fixtures, recorded HTTP, no live in CI     |
| Processing| Correct parsing and business rules     | Unit + golden files                         |
| Database    | Schema, constraints, idempotent load   | Integration against real or container DB  |
| Analysis    | Reproducibility, no leakage, sanity     | Small synthetic + statistical checks        |

**Test data strategy:** Prefer **synthetic and anonymized** fixtures; never commit secrets. Live credentials only in environment-specific config, not in tests by default.

---

## Suggested order of work

1. Data contract and canonical model (Phase 1).  
2. End-to-end slice: one **small** category or region within the **request budget**, raw → processed → DB (Phases 2–4) with tests.  
3. Expand scope only by **raising caps deliberately**; harden ingestion (retries with limits, monitoring, alerts on unusual volume).  
4. Analysis and reporting (Phase 5) with strict reproducibility.

---

## Open decisions (to resolve when coding starts)

- Snapshot frequency and whether to keep **full history** or only **latest** per listing.
- Whether **make/model** normalization uses a **reference table** (curated) vs free text with post-hoc cleaning.
- Legal review of **automated data collection** vs any **authorized** or official channel the source may offer.

This outline should stay valid as a roadmap; add appendices for schema diagrams and runbooks once implementation details exist.
