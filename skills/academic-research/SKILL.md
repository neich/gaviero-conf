---
name: academic-research
description: Academic literature research built on the `academic` MCP server (OpenAlex + Semantic Scholar + Europe PMC search, GROBID full text, citation graph, retraction checks, Consensus evidence). It measures search recall against a benchmark set, screens with two passes that lean towards inclusion, snowballs citations backward then forward, writes only from extracted quotes, and checks every claim against its cited passage. It writes to research/<slug>/ with sequential versions (<slug>-v1.md, <slug>-v2.md, …); each version has the scholarly review plus a full evidence table, a reproducible search log and a BibTeX file (a plain-language explanation is a separate step: /research-companion). Use it for questions about what the research literature says: literature reviews, state of the art, "what does the evidence say", systematic-style scoping, finding seminal and recent papers, checking whether a finding has held up. Use /deep-research instead for questions that are mainly about the web, products or news. Depth tiers are quick / standard (default) / deep, tunable with key=value overrides. Invoke reliably with /academic-research [tier:] [key=value ...] <question>.
argument-hint: "[quick:|deep:] [subq=N searches=N reads=N waves=N triangulate=N agents=N hops=N bench=N since=YYYY evidence=N review=0|1] <research question>"
allowed-tools: Task, Write, Read, WebFetch, WebSearch, mcp__academic__*
---

# Academic Research

Treat `$ARGUMENTS` as the research question. The method is a compact,
reproducible literature review:
scope → benchmark → search → screen → read & extract quotes → snowball →
appraise → outline → draft → verify claims → write a cited review to disk.

The **`academic` MCP server (`mcp__academic__*`) is the primary and normal
source** for every step. Use WebSearch/WebFetch only as a fallback (see
Fallbacks), and say in the report whenever you did.

## Depth parameters

Parse `$ARGUMENTS` like this:

```
[quick:|deep:] [key=value ...] <research question>
```

1. **Tier.** If the input starts with `quick:` or `deep:`, strip the prefix
   and use that tier. Otherwise use **standard**.
2. **Overrides.** Consume the leading `key=value` tokens whose key appears in
   the table below; each one overrides that knob. Everything after them is
   the question. Ignore a token with an unknown key or a bad value, and
   mention that in the plan.
3. **Clamp** every value to its hard cap.

| Knob          | Meaning                                                              | quick | standard | deep | Hard cap |
|---------------|----------------------------------------------------------------------|-------|----------|------|----------|
| `subq`        | Max sub-questions (0 = no subagents, investigate yourself)           | 0     | 4        | 6    | 8        |
| `searches`    | **Ceiling** on `search_works` queries per investigator               | 4     | 5        | 8    | 15       |
| `reads`       | Papers read in **full text** per investigator                        | 2     | 4        | 6    | 12       |
| `waves`       | Investigation waves (later waves target gaps/conflicts)              | 1     | 1        | 2    | 3        |
| `triangulate` | Min independent papers behind a load-bearing claim                   | 1     | 2        | 2    | 3        |
| `agents`      | Max investigator subagents across all waves                          | 0     | 4        | 8    | 12       |
| `hops`        | Max snowball rounds from seed papers (0 = off)                       | 0     | 1        | 2    | 3        |
| `bench`       | Benchmark papers used to measure search recall (0 = off)             | 0     | 5        | 10   | 15       |
| `evidence`    | `search_evidence` calls per run (Consensus allowance, 0 = off)       | 1     | 2        | 4    | 6        |
| `review`      | Run one Consensus `start_review` as a source of leads (0/1)          | 0     | 0        | 1    | 1        |
| `since`       | Earliest publication year for searches (`year_min`); default none    | —     | —        | —    | —        |

Examples: `/academic-research deep: reads=10 triangulate=3 <q>`,
`/academic-research since=2020 hops=2 bench=10 <q>`,
`/academic-research quick: evidence=0 <q>`.

Show the effective parameters in the plan (step 2) and in the report header.

## Evidence standard (applies `evidence-first` to literature — non-negotiable)

Every claim in the report and in the chat reply must come from evidence
gathered **in this run**.

- **No guessing, no memory.** Training knowledge may suggest queries and
  author names, but it is never a source. Never invent titles, authors, years,
  venues, DOIs, effect sizes, sample sizes, quotes or URLs. Copy bibliographic
  data from `resolve_work` / `search_works` output only.
- **Levels of access.** Record, for every paper, how much of it you actually
  saw:
  - **full text**: `get_fulltext` returned the relevant sections, or
    `search_corpus` returned passages from it.
  - **abstract only**: only metadata or abstract was seen (`search_works`,
    `resolve_work`, `search_evidence`).
  - **cited by others**: you know the paper only through other papers'
    citation contexts. Such a paper is never evidence for its own results.
- **Abstract ≠ paper.** Claims about methods, numbers, populations, effect
  sizes or limitations need full text. If only the abstract was available, add
  *(abstract only)*.
- **Syntheses are leads.** `start_review` answers, Consensus "takeaways",
  review articles' summaries of other papers, and subagent reports are not
  evidence for the claims they make about *other* papers. Open the underlying
  paper first, or label the claim *secondhand (via X)*.
- **Citation-context labels are leads too.** Any automatic "supporting /
  contrasting" label on a citation is unreliable. Read the citing sentence
  yourself. Finding no contrasting citations is not evidence that no contrary
  work exists.
- **Label every non-obvious claim**:
  - **established**: at least `triangulate` independent papers state it,
    at least one of them was read in full text, and the claim passed
    verification (step 5).
  - **supported**: fewer independent papers than `triangulate` require, only
    abstracts seen, or verification returned *partial*. Say which.
  - **contested**: papers disagree. Cite both sides.
  - **inferred**: your synthesis across papers. Give the reasoning.
  - **assumed**: flag it and say what would confirm it.
- **Independence.** A preprint and its published version, or two papers that
  report the same dataset or trial, count as **one** source. The same authors
  restating their own result also count as one, and you must say so.
- **Quotes before prose.** Every claim in the review is written from a
  verbatim quote extracted from the cited paper. Each quote carries an anchor
  (section name or `search_corpus` anchor) so it can be re-checked.
- **Calibrated, not hedged.** State established findings plainly. Report
  gaps, conflicts, null results and dead ends as such.

## The `academic` server — tools by role

| Role | Tools | Notes |
|---|---|---|
| **Preflight** | `server_status`, `list_collections` | GROBID alive? daily budgets (OpenAlex, Unpaywall) near ceiling? |
| **Discover** | `search_works` | Fuses the local corpus, OpenAlex, Semantic Scholar and Europe PMC. Filters: `year_min`, `year_max`, `open_access_only`, `limit`. With `collection`, it queues the top open-access results for ingestion. |
| **Discover (evidence)** | `search_evidence` | Consensus: study design, sample size, takeaway, journal quartile. Filters: `study_types`, `human`, `controlled`, `sample_size_min`, `sjr_max`, `exclude_preprints`, `year_min`. **Uses the monthly Consensus allowance**, so stay within `evidence`. |
| **Discover (local)** | `search_corpus` | Hybrid passage search over full text that is already stored. Use it first: earlier runs may already have ingested relevant papers. |
| **Resolve / dedupe** | `resolve_work` | Any ID (DOI, arXiv, PMID, PMCID, OpenAlex W-ID, S2 ID) or title + year + first author → one merged work, with the source of each field and any conflicts. |
| **Content** | `get_fulltext` (`section`, `offset`), `ingest_status`, `search_corpus` (`collection`) | `get_fulltext` with `collection` queues ingestion when the text is not stored yet. Read by section (`Methods`, `Results`, `Limitations`, `Discussion`) rather than whole papers. |
| **Relationships** | `get_references`, `get_citations` (`with_contexts`, `sort`), `expand_collection` (`dry_run=true`), `citation_graph` (`depth`, `direction`) | `pending=true` means edges are fetched in the background, so call again later. `with_contexts=true` returns the citing sentences. `citation_graph` can come back truncated or with placeholder nodes, so use it for an overview only and snowball with `get_references` / `get_citations`. |
| **Appraisal** | `check_retraction`, `get_journal`, `get_author` | Retraction status (Crossref, OpenAlex, PubMed); venue metrics; author profile. |
| **Synthesis (leads only)** | `start_review` → `get_review` | Consensus literature review. Slow and costly. Use only when `review=1`, at most once. Never cite it as evidence. |

### Run collection

Each run gets **one** collection named `ar-<kebab-slug>-<YYYY-MM-DD>` (check
`list_collections` first; add `-2`, `-3` if the name exists). All ingestion
in the run (`search_works`, `get_fulltext`, `search_evidence` with
`collection`) goes into it, so that `search_corpus(collection=…)` and
`expand_collection(collection, dry_run=true)` cover exactly this run's
corpus. Subagents use the same collection name. This is the only state the
skill writes on the server: never run `expand_collection` with
`dry_run=false` unless the user asks for it, and never touch other
collections.

### Pending and asynchronous calls

- `get_citations`, `get_references` and `citation_graph` may return
  `pending=true`, and ingestion runs in the background. Don't sit and wait.
  Continue with other work, then call again. After 3 attempts, go on without
  the result and record the gap in the report.
- After queuing ingestion, check `ingest_status(collection=…)`. If a job
  fails (paywalled, non-English, GROBID error), that paper stays
  *abstract only*. Try its open-access URL from `resolve_work` with WebFetch
  only if the claim is load-bearing.

## Procedure

1. **Scope.** If the question is genuinely ambiguous, ask up to 3 clarifying
   questions, once and all together, then proceed. Ambiguity here means
   population, intervention or exposure, outcome, timeframe, discipline, or
   whether the user wants a narrative review or a focused answer. Otherwise
   start immediately. Restate the question in research form: PICO/PECO for
   empirical questions, concept + context otherwise.

2. **Preflight, benchmark & plan.**
   - Run `server_status` and `list_collections`. If GROBID is down, full text
     won't ingest: say so and plan for abstract-level evidence. If a budget
     is near its ceiling, lower `searches` and say so.
   - Create the run collection name.
   - **Eligibility criteria.** Write numbered include and exclude criteria:
     topic, population or setting, study types, years, languages,
     peer-reviewed vs preprints. Add one short example of a clear include
     and one of a clear exclude. Screening uses exactly these criteria.
   - **Benchmark set (`bench` > 0).** Before running the planned searches,
     collect up to `bench` papers that are clearly relevant. Take them from
     sources independent of the planned `search_works` queries:
     - papers the user named;
     - the reference list (`get_references`) of one recent review or
       meta-analysis on the topic;
     - `search_evidence` hits (these count toward `evidence`).

     Resolve each one with `resolve_work`. Drop any the indexes don't
     contain, and record the set in the search log. Don't use their exact
     titles as queries; the set exists to measure the searches.
   - Split the question into at most `subq` sub-questions (none if `subq=0`).
     Assign the benchmark papers to the sub-questions they belong to.
   - **Search strings.** For each sub-question, write:
     - 2–3 **conceptual** strings: synonyms, key technical terms, and the
       field's own vocabulary;
     - 1 **objective** string built from terms that recur in the titles and
       abstracts of its benchmark papers (skip it when `bench=0`).

     LLM-written strings alone lose recall, so keep both kinds. Avoid year
     or language limits unless the question needs them, and justify any
     limit you use.
   - State the plan in a few lines before investigating: the effective
     parameters, the collection name, the criteria, and the benchmark set.

3. **Investigate.** Each investigator, whether that is you (`subq=0`) or a
   subagent, does the following:
   1. **Local first.** Run `search_corpus` on the sub-question. Reuse relevant
      stored passages; they count toward `reads`.
   2. **Search until recall is reached.**
      - Run the planned strings with `search_works`. Pass `collection` and,
        if set, `since` as `year_min`. Use `limit` 20–30.
      - Add angles as needed: the method name, the outcome name, and a
        "review OR meta-analysis" variant.
      - After each query, compute **relative recall**: benchmark papers
        retrieved so far ÷ benchmark papers assigned to this sub-question.
        If papers are missed, build the next query from the missed papers'
        title and abstract terms.
      - **Stop** when recall is ≥ 0.8 **and** the last query added no new
        papers that pass screening, or when `searches` is reached.
        `searches` is a ceiling, not a quota.
      - Log each query string exactly as run, with its hit count, the recall
        after it, and which stopping condition fired.
      - Never call the search complete just because the last query returned
        nothing new.
      - With `bench=0`, stop when a query adds nothing new or the ceiling is
        reached, and log "recall not measured".
   3. **Evidence search.** For empirical sub-questions, while the run's
      `evidence` budget remains, call `search_evidence` once with filters that
      match the question (e.g. `study_types: ["meta-analysis","systematic
      review","rct"]`, `human: true`).
   4. **Screen (two passes, leaning towards inclusion).**
      - Deduplicate by DOI / `resolve_work`, merging preprints with their
        published versions.
      - **Pass A.** Screen each title and abstract against the numbered
        criteria. Exclude only when a criterion **clearly** fails. Include
        when unsure or when the information is insufficient. A decision you
        can't make or parse counts as include.
      - **Pass B.** Re-screen every record that pass A excluded, without
        looking at pass A's reasoning. Go criterion by criterion, citing the
        sentence that fails each one. Final decision: include if **either**
        pass includes.
      - **No abstract.** Never exclude a record only because its abstract is
        missing. Check it with `resolve_work` / `get_fulltext`, or keep it,
        and count these records separately.
      - **Near misses.** Log excluded records that were close calls, with the
        criterion that failed.
      - Keep counts: identified → after dedupe → screened in → read in full.
   5. **Read & extract quotes.**
      - Choose the `reads` most load-bearing papers. Prefer, in order:
        systematic reviews and meta-analyses, large or controlled primary
        studies, seminal papers, then the most recent strong work.
      - Read them with `get_fulltext(id, collection=…, section=…)`, focusing
        on Methods, Results and Limitations. Use
        `search_corpus(query, collection=…)` to pull candidate passages.
      - For each paper, record **verbatim quotes** (each <60 words) with
        their anchors: design, N, population, main results with numbers, and
        limitations.
      - Score each quote 1–10 for relevance to the sub-question, and keep at
        most 3 per paper (the best ones). These quote notes are the only
        material the review may be written from.
   6. **Snowball (`hops` > 0).** Snowballing supplements the database search;
      it never replaces it.
      - **Seeds.** Choose up to 10 papers that have been screened in and
        read, deliberately varied in author group, venue and year. Never take
        all seeds from one research group. Benchmark papers that were
        confirmed relevant can be seeds.
      - **Backward first.** Run `get_references` on each seed.
        - **Coverage check.** OpenAlex misses roughly a third of reference
          lists. If a full research article returns implausibly few
          references (e.g. under 10), read its reference list from the full
          text (`get_fulltext(section="References")`) and resolve the
          relevant entries with `resolve_work`.
      - **Then forward.** Run `get_citations` (`sort="year_desc"`,
        `with_contexts=true`) on the seeds **and** on the papers that the
        backward step screened in.
      - **Rank before screening.** Score candidates by how many seeds or
        citation paths reach them. Use
        `expand_collection(collection, dry_run=true)` to find works co-cited
        by several of the papers you have read. Screen the top ~30 per round
        with the two-pass protocol above. Use the citing sentence (where and
        how a paper is cited) as an extra screening signal.
      - **Iterate.** Papers that were screened in and read become the next
        round's seeds. Stop when a round adds no screened-in papers, or when
        `hops` rounds are done. Log, for each round: the seeds, candidates,
        papers screened, and papers included.
      - **Look for:** the seminal origin of the idea; replications and failed
        replications; critiques and comments (comments can foreshadow a
        retraction); later meta-analyses that supersede a seed.
   7. **Appraise.** For every paper that will be cited, run `check_retraction`.
      For papers that carry load-bearing claims, also record the study design,
      sample size, population and the main limitation, taken from the quote
      notes (or `search_evidence` metadata, labelled as such). Use
      `get_journal` only as context. Venue metrics are not quality evidence,
      and they are never a reason to call a finding established.

   **Subagents (`subq > 0`).** Spawn one `general-purpose` subagent per
   sub-question, all in a single message (max 5 concurrent, queue the rest).
   Each prompt is its sub-question, its eligibility criteria, its search
   strings and its benchmark papers (with IDs), plus:

   > "Use the `academic` MCP server (`mcp__academic__*`) as your source. Use
   > collection `<collection>` for all ingestion, and don't touch any other
   > collection. Steps:
   > (1) `search_corpus` first.
   > (2) Run the given strings with `search_works` (year_min=<since> if set).
   > After each query, compute recall against the benchmark papers, and build
   > the next query from the terms of any you missed. Stop at recall ≥ 0.8
   > with no new includes, or after <searches> queries.
   > (3) <n> `search_evidence` call(s) if empirical (Consensus allowance,
   > don't exceed).
   > (4) Deduplicate with `resolve_work`. Screen in two passes: pass A
   > excludes only when a criterion clearly fails, and includes when unsure;
   > pass B re-screens every pass-A exclusion criterion by criterion; include
   > if either pass includes. Never exclude a record for lacking an abstract.
   > (5) Read the <reads> most load-bearing papers in full text via
   > `get_fulltext` (Methods, Results, Limitations). Extract verbatim quotes
   > (<60 words) with anchors, at most 3 per paper.
   > (6) Snowball up to <hops> round(s): up to 10 varied seeds; backward
   > (`get_references`) first, then forward (`get_citations`,
   > `with_contexts=true`) from the seeds plus the backward includes. Rank
   > candidates by how many seeds reach them, and screen the top ~30. Stop
   > when a round adds nothing. If a full article lists implausibly few
   > references, read them from its full text.
   > (7) Run `check_retraction` on every paper you report.
   > If a call returns pending=true, do other work and retry (max 3). Do not
   > write files, do not run `expand_collection` with dry_run=false, do not
   > call `start_review`.
   > Return ≤1000 words:
   > (a) bullet claims, each with the paper title, first author, year, DOI or
   > other ID, access level (`full-text` / `abstract-only` / `secondhand`),
   > and the supporting verbatim quote with its anchor;
   > (b) for each key study: design, N, population, main result, main
   > limitation;
   > (c) conflicts between papers, and critiques or failed replications
   > found;
   > (d) retractions found;
   > (e) every query string as run, with its hit count and the recall after
   > it; the stopping condition that fired; per-round snowball counts;
   > counts identified → deduped → screened in (pass A / pass B) → read;
   > near-miss exclusions;
   > (f) what you could not find or verify.
   > Report only what a paper you actually opened states, never what you
   > remember. Never invent titles, IDs, numbers or quotes. Say 'not found'
   > rather than filling a gap."

   **Waves (`waves > 1`).** After each wave, list:
   - gaps;
   - conflicts;
   - load-bearing claims that have fewer than `triangulate` independent
     papers;
   - load-bearing claims that rest only on abstracts;
   - benchmark papers that no search found.

   Launch targeted subagents on them in the next wave, within the `agents`
   total. Stop early if nothing material is left open.

   **Consensus review (`review=1`).** Start `start_review` early, in parallel
   with the investigation, so it isn't on the critical path. Collect it with
   `get_review` before synthesis. Mine it for papers you missed, then verify
   them through `resolve_work` / `get_fulltext` like any other lead.

4. **Outline & draft.**
   - **Outline first.** Build a thematic outline (themes, not subagents or
     papers). Assign quotes from the quote notes to each section. A section
     with no quotes is a gap: move it to Gaps & caveats instead of writing
     it.
   - **Weigh the evidence** for each theme: design strength, sample size,
     consistency across independent papers, recency, and whether later work
     replicated or contradicted it.
   - When papers conflict, say which evidence is stronger and why. Prefer a
     newer meta-analysis over older single studies, controlled over
     observational, and published over a preprint unless the preprint is
     newer and stronger. State the reason each time.
   - **Draft each section only from its assigned quotes.** Every sentence
     with a citation must trace to a specific quote. Keep the draft in
     memory; nothing is written to disk yet.

5. **Verify claims (grounded, independent).**
   - **Split** the draft into atomic (claim, cited paper ID, anchor) triples,
     one per cited claim.
   - **Verifier.** Hand the triples, without the rest of the draft, to a
     fresh `general-purpose` subagent. Verifier subagents don't count toward
     `agents`. Use at most 2, splitting the triples between them if there
     are many. When `agents=0` (quick tier), verify the triples yourself in
     a separate pass: re-fetch each passage and judge it **before**
     re-reading the claim's surrounding text. Log this as *self-verified*.

     The verifier prompt:

     > "For each (claim, paper, anchor) triple, re-fetch the passage yourself
     > with `mcp__academic__search_corpus` (collection `<collection>`) or
     > `mcp__academic__get_fulltext` (section from the anchor). Don't rely on
     > any quote you were given. Return one verdict per triple:
     > `supported` / `partial` (states only part, or a weaker version) /
     > `unsupported` / `contradicted` / `not-checkable` (text unavailable),
     > plus the passage (<60 words) you based it on. If you only saw the
     > abstract, add `abstract-level`. When unsure between two verdicts,
     > choose the weaker one. Do not write files or change any state."
   - **Act on the verdicts.** Don't rewrite freely: narrow the text to what
     the passage says, or remove it.

     | Verdict | Action |
     |---|---|
     | `supported` | Keep. |
     | `partial` | Narrow the claim to what the passage states. Its label is at most *supported*. |
     | `unsupported` | Drop it, or replace it with what the passage does say. |
     | `contradicted` | Correct it and flag it in Gaps & caveats. |
     | `not-checkable` | Keep only if it's labelled *(abstract only)* or *secondhand*. Never *established*. |
     | `abstract-level` | Never *established*. |
   - **Record in the search log:** triples checked, the count per verdict,
     the share that was supported, how many claims were dropped or narrowed,
     and the verifier (model and method). Verifiers are imperfect (roughly
     80–90% agreement with experts), and the rates depend on the verifier,
     so always name it.

6. **Self-check (before writing the files).** Go through the verified draft
   sentence by sentence:
   - Every cited paper was opened in this run, and its access level is shown.
   - Every cited claim passed step 5, and its label matches its verdict.
     Nothing marked *established* rests on abstracts alone, on fewer than
     `triangulate` independent papers, or on a *partial* verdict.
   - Preprint/published pairs and same-dataset papers are not counted twice.
   - Every cited paper has a retraction status. A retracted paper is either
     removed, or cited only as retracted.
   - Subagents' `abstract-only` and `secondhand` claims are labelled, not
     promoted.
   - Counts in the Method section match the search log and add up, including
     recall, the two screening passes, snowball rounds and verification.
   - Every reference in the review has an entry in the `.bib` file.
   - The version number is new, and all four files use it.
   - Move whatever falls out to Gaps & caveats.

7. **Write the files.** Each research topic has one folder,
   `research/<slug>/`, where `<slug>` is a short kebab-case slug of the
   question. Files inside it are versioned sequentially, starting at `v1`:
   - **Folder.** If `research/<slug>/` doesn't exist, create it (and
     `research/` if needed). If it does exist, this run is a new version of
     the same topic. Reuse the existing slug when the question clearly
     matches the topic, so versions don't scatter across near-identical
     folders.
   - **Version.** List the folder, find the highest existing
     `<slug>-v<N>.md`, and use `N+1`; use `v1` if there is none. Never
     overwrite or edit an earlier version.

   | File | Contents |
   |---|---|
   | `<slug>-v<N>.md` | The review, following the Report template below. |
   | `<slug>-v<N>-evidence-table.md` | The full evidence table: every screened-in study, not only the load-bearing ones in the review. |
   | `<slug>-v<N>-search-log.md` | Reproducibility log, described below. |
   | `<slug>-v<N>.bib` | BibTeX for every work in References. |

   The search log contains:
   - effective parameters and the collection name;
   - the eligibility criteria;
   - the benchmark set;
   - every search string exactly as run, with its tool, filters, hit count
     and the recall after it, plus which stopping condition fired;
   - screening counts per pass, records without an abstract, and near-miss
     exclusions with reasons;
   - snowball rounds: seeds, candidates, screened, included;
   - the flow (identified → deduped → screened in → read → cited);
   - verification statistics and the verifier used;
   - tool failures, pending calls and fallbacks.

   - **Links.** The review links to its sibling files of the same version
     (evidence table, search log, BibTeX), using relative links. Don't
     link a companion: it is written later by `/research-companion`, which
     links back to the review.
   - **Changes from the previous version.** If `N > 1`, read the previous
     review and add a short *Changes since v<N-1>* section at the end of the
     new one: papers added or dropped, labels that changed, and conclusions
     that moved.
   - **BibTeX.** Build entries only from `resolve_work` fields. Omit any field
     you didn't get, and never fill one from memory. Use keys of the form
     `firstauthorYEARfirstword`, and reuse the same keys in the evidence
     table.

8. **Reply** in chat with:
   - the folder path, the version number, and the files written;
   - the collection name;
   - search recall against the benchmark, and the verification result (share
     of claims supported, number dropped);
   - the command for a plain-language explanation, ready to copy:
     `/research-companion research/<slug>/<slug>-v<N>.md` (best run in a
     fresh session);
   - a summary of at most 10 lines, with evidence labels on the load-bearing
     claims;
   - any usage or allowance message a tool asked to have shown, copied
     word-for-word.

   Do not paste the full report.

## Report template

Keep prose tight. The review should be much shorter than the literature it
distils.

**Shared contract.** `/research-companion` parses this layout: the file
names, the `*Version v<N> · files:` header line, the section names, and
the evidence labels and access marks. If you change any of them, update
the contract section of `research-companion/SKILL.md` too.

```markdown
# <Headline answering the question>

*<YYYY-MM-DD> · depth: <tier> (subq=… searches=… reads=… waves=… triangulate=… agents=… hops=… bench=… evidence=… review=… since=…) · collection: <name> · <n> papers cited (<f> full text, <a> abstract only)*
*Version v<N> · files: [evidence table](<slug>-v<N>-evidence-table.md) · [search log](<slug>-v<N>-search-log.md) · [BibTeX](<slug>-v<N>.bib)*

## Abstract
150–250 words: question, approach, main findings with their strength, main
caveat, bottom line.

## Question & method
- **Question** (PICO/PECO or concept + context) and eligibility criteria.
- **Search:** strings used (conceptual + objective), the indexes behind them
  (OpenAlex, Semantic Scholar, Europe PMC via `search_works`; Consensus via
  `search_evidence`), date of search, any limits with the reason for them.
- **Recall:** benchmark size, relative recall reached, and the stopping
  condition that fired (or "recall not measured").
- **Screening:** a single LLM ran two passes leaning towards inclusion (pass
  B re-screened every exclusion). Give the counts per pass and the records
  without an abstract. Expected recall is about 0.8–0.95; this is not
  equivalent to dual human screening.
- **Flow:** identified → after dedupe → screened in → read in full → cited.
  Add snowballing: seeds, rounds, and works added per round.
- **Verification:** claims checked, share supported, number dropped or
  narrowed, and the verifier.
- **Limits of this method** (e.g. full text unavailable for N papers;
  citation data incomplete; not a formal systematic review).

## Findings
By theme. Each claim carries an inline citation and a label:
"X increases Y ([Author et al., 2024](https://doi.org/…)) — *established*
(3 independent studies, 2 full text)."
Labels: *established* · *supported* · *contested* · *inferred* · *assumed*.
Add *(abstract only)* or *secondhand (via X)* where it applies.

## Evidence table
| Study | Design | N / sample | Population / setting | Key result | Main limitation | Access |
|---|---|---|---|---|---|---|
Only studies that carry load-bearing claims; the complete table, with the
same columns plus a BibTeX key, goes in `<slug>-v<N>-evidence-table.md`. Leave a cell as
"not reported" or "not read" rather than guessing.

## Literature map
Based on the snowball rounds made in this run:
- **Seminal / foundational** work, and what it established.
- **Main lines of follow-up** (clusters of citing papers).
- **Replications, failed replications, critiques, retractions.**
- **Syntheses** (reviews and meta-analyses) and what they concluded.
- **Most recent relevant work.**

Each entry: [Title](url) (first author, year, ID), plus one line on how it
relates to the others ("cites X", "replicates Y", "contradicts Z").

## Quality & risk of bias
Design mix, sample sizes, preprint share, conflicts of interest or funding
when the paper states them, publication-bias signals, retractions found, and
heterogeneity across studies.

## Gaps & caveats
- What could not be verified or read, including claims that failed or
  couldn't be checked in verification.
- Where papers conflict, and what is likely to be stale.
- Benchmark papers no search found.
- Open research questions the literature itself names.
- Tool failures: pending calls that never resolved, ingestion failures,
  incomplete reference lists, budgets reached, fallbacks used.

Never omit this section.

## References
APA 7 style, alphabetical. Each entry ends with:
`DOI / arXiv / PMID · via <search_works | search_evidence | snowball | benchmark> · <full text | abstract only> · retraction: <none found | RETRACTED | expression of concern>`
```

Template rules:
- Nothing from memory. References list only works resolved in this run, and
  each one states what it is cited for.
- Quote sparingly in the review (<25 words per paper); paraphrase the quote
  notes by default.
- Dead ends count. Record an empty sub-question in Gaps & caveats rather than
  padding Findings.

## Fallbacks

- **The `academic` server is missing or down** (no `mcp__academic__*` tools,
  or `server_status` fails): say so. Then either stop and ask the user, or,
  if they agree, continue with `/deep-research`.
- **Full text not ingestible but load-bearing:** use WebFetch on the
  open-access URL or DOI landing page from `resolve_work`, and mark it
  *full text (web)*. The verifier may use the same URL.
- **Grey literature** (standards, reports, theses that the indexes don't
  cover): use WebSearch + WebFetch only when the question needs it, and list
  those sources separately in References as *non-indexed*.
- **Rate limits or budgets:** retry once after other work, then lower the
  remaining `searches` / `evidence` and note it in the report.

## Guardrails

- One investigator subagent per sub-question, never per search. Never exceed
  `agents` investigators (plus at most 2 verifiers), or any hard cap,
  whatever the overrides say.
- **Cost.** The run's cost comes mostly from `subq × (searches + reads) ×
  waves`, plus up to `10 seeds × hops` snowball rounds per investigator and
  one verification pass. `evidence` and `review` spend the monthly
  Consensus allowance, so keep them within their knobs. Don't call the
  separate `mcp__consensus__*` server from this skill; that would charge the
  same allowance twice.
- **Server state.** The only state written is ingestion into the run
  collection. Never delete, rename or expand other collections.
- If the question can be answered with one lookup (e.g. "what's the DOI of
  X", "is paper Y retracted"), answer it directly with the matching tool
  instead of running a review.
