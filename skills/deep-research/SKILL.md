---
name: deep-research
description: Agentic multi-source research (web + every configured scholarly MCP server — arXiv, Semantic Scholar, PubMed, Consensus, …) producing a citation-rich markdown report, including paper full text and citation-graph relationships — the CLI equivalent of ticking claude.ai's Research box. Use for any request to research, investigate, deep-dive, review the literature or state of the art, compare options across many sources, or produce a sourced report — even if the word "research" never appears. Depth tiers quick / standard (default) / deep, tunable with key=value overrides. Reliable invocation is /deep-research [tier:] [key=value ...] <question>.
argument-hint: "[quick:|deep:] [subq=N searches=N fetches=N waves=N triangulate=N agents=N hops=N] <research question>"
allowed-tools: WebSearch, WebFetch, Task, Write, Read, mcp__claude_ai_Arxiv_org__*, mcp__claude_ai_Semantic_Scholar__*, mcp__claude_ai_PubMed__*, mcp__claude_ai_Consensus__*, mcp__claude_ai_alphaXiv__*
---

# Deep Research

Treat `$ARGUMENTS` as the research question. Reproduce claude.ai Research mode:
plan → parallel investigation → synthesis → cited report written to disk.

## Depth parameters

Parse `$ARGUMENTS` like this:

```
[quick:|deep:] [key=value ...] <research question>
```

1. **Tier.** If it starts with `quick:` or `deep:`, strip the prefix and use
   that tier. Otherwise use **standard**.
2. **Overrides.** Consume any leading `key=value` tokens whose key is in the
   table below. Each one overrides that knob of the tier preset. The rest of
   the input is the question. If a token looks like an override but has an
   unknown key or a bad value, ignore it and mention that in the plan.
3. **Clamp** every value to its hard cap.

| Knob          | Meaning                                                    | quick | standard | deep | Hard cap |
|---------------|------------------------------------------------------------|-------|----------|------|----------|
| `subq`        | Max sub-questions (0 = no subagents, investigate yourself) | 0     | 5        | 6    | 8        |
| `searches`    | Search queries per investigator (web + scholarly indexes)  | 5     | 4        | 6    | 15       |
| `fetches`     | Sources actually opened per investigator (pages, papers)   | 4     | 4        | 6    | 12       |
| `waves`       | Investigation waves (each later wave targets gaps/conflicts) | 1   | 1        | 2    | 3        |
| `triangulate` | Min independent fetched sources per load-bearing claim     | 1     | 1        | 2    | 3        |
| `agents`      | Max subagents across all waves                             | 0     | 5        | 8    | 12       |
| `hops`        | Citation-graph snowball depth from seed papers (0 = off)   | 0     | 1        | 2    | 2        |

Examples: `/deep-research deep: fetches=10 triangulate=3 <q>`,
`/deep-research waves=2 <q>` (standard with a gap-filling second wave),
`/deep-research quick: hops=1 <q>` (quick, with a single citation-graph hop),
and `/deep-research hops=0 <q>` (no citation-graph expansion).

Show the effective parameters in the plan (step 2) and in the report header.
Everything below refers to these knobs by name.

## Evidence standard (applies `evidence-first` to research — non-negotiable)

Every claim in the report and in the chat reply must come from evidence gathered
**in this run**. The rules from `evidence-first` apply as stated, with these
meanings for web and literature research:

- **No guessing, no memory.** Training knowledge may suggest search queries but
  is never a source. A fact you "know" but did not find in a fetched source goes
  in Open questions or gets dropped. Never invent titles, authors, dates,
  figures, quotes, DOIs, IDs or URLs.
- **Fetched, not snippeted.** A claim counts as **verified** only if a source
  that was actually opened states it. "Opened" means WebFetch, a paper's full
  text (`read_paper`, `get_full_text_article`, …), or an abstract returned
  by a metadata call. Search-result snippets are leads, not evidence: fetch them
  or label the claim **unverified (snippet only)**.
- **Abstract ≠ paper.** If a claim about a paper's methods, results or limits
  rests only on its abstract, add *(abstract only)*. Read the full text when
  the claim is load-bearing and full text is available.
- **Syntheses are leads.** The output of research agents and AI-written
  summaries (for example Consensus threads) is not evidence for the claims it
  makes. Open the underlying paper first.
- **Label every non-obvious claim** with one of the following:
  - **verified**: a fetched source states it. Add "(≥2 independent sources)"
    when that is true.
  - **single source**: one fetched source only.
  - **inferred**: your synthesis across sources. State the reasoning.
  - **assumed**: flag it and say what would confirm it.
- **Citation points at the claim.** The linked source must actually say what it
  is cited for. Don't cite a page for a number it doesn't contain.
- **Calibrated, not hedged.** State verified facts plainly. Report gaps, conflicts
  and dead ends as such. Never round uncertainty up to confidence.

## Scholarly sources (use every one that is configured)

When a question touches research literature in any way (science, medicine, ML,
engineering, social science, "state of the art", "what does the evidence say"),
use **every** configured scholarly MCP server, not just one. Look at your
actual tool list:

- **Use a server only if its tools are actually in your tool list.** Never
  assume a server is there.
- If a server is listed but needs authentication, don't try to authenticate.
  Name it in Open questions & caveats as a source that couldn't be used.
- Treat any other scholarly server you find (OpenAlex, Crossref, CORE, Google
  Scholar, Europe PMC, …) the same way, matching its tools to the roles below.

Known servers, grouped by role:

| Role | arXiv (`mcp__claude_ai_Arxiv_org__*`) | Semantic Scholar (`mcp__claude_ai_Semantic_Scholar__*`) | PubMed (`mcp__claude_ai_PubMed__*`) | Consensus (`mcp__claude_ai_Consensus__*`) |
|---|---|---|---|---|
| **Discover** | `search_papers` | `search_papers`, `search_authors` | `search_articles`, `lookup_article_by_citation` | `search` |
| **Metadata / abstract** | `get_abstract` | `get_paper`, `batch_get_papers` | `get_article_metadata` | (in `search` results) |
| **Content** | `download_paper`, `read_paper`, `get_paper_outline`, `read_paper_section`, `search_paper_text`, `get_paper_latex_section` | — | `convert_article_ids` → `get_full_text_article` (PMC only) | — |
| **Relationships** | `citation_graph` | `get_paper_citations`, `get_paper_references`, `get_recommendations`, `get_author_papers` | `find_related_articles` | — |

alphaXiv (`mcp__claude_ai_alphaXiv__*`) also counts when it is authenticated.
Match its tools to these roles by their descriptions.

How to use them:

1. **Discover broadly.** Run each literature query on at least two indexes when
   two or more are configured:
   - arXiv and Semantic Scholar for CS, physics and maths.
   - PubMed and Semantic Scholar for biomedical topics.
   - Consensus for any empirical research question.
   - Also run WebSearch for grey literature, docs and news.
2. **Deduplicate** papers across indexes by DOI, arXiv ID or PMID. Use
   `convert_article_ids` and the IDs in `get_paper` / `get_abstract`. The
   same paper found in two indexes is **one** source for triangulation.
3. **Read content.** For each load-bearing paper, get the abstract at least.
   When the claim depends on methods, numbers or limitations, read the
   relevant section of the full text: arXiv sections, PMC full text, or the
   open-access PDF via WebFetch. Each paper read counts toward `fetches`.
4. **Map relationships (`hops` > 0).**
   - Pick up to 5 **seed papers**: the most relevant and most cited ones you
     have opened.
   - For each seed, fetch its references (backward) and its citing papers
     (forward), keeping the top ~10 by relevance and citation count. Also
     fetch recommendations or related articles.
   - Read the abstracts of the new relevant papers. They become the seeds for
     the next hop, up to `hops` hops.
   - Use the citation graph to find seminal work, later replications, critiques
     and retractions, and to check whether a claim has been contradicted
     since it was published.
5. **Consensus specifics.**
   - Use `search` for discovery. In the report, cite each paper with its own
     URL, as returned by the tool.
   - Copy any sign-up or usage message from the tool result word-for-word
     into the chat reply.
   - Use `create_thread` (slow, a research agent) only in the deep tier, at
     most once, as a source of leads. Its claims follow the "syntheses are
     leads" rule.
6. **Attribution.** For every paper in `## Sources`, give its DOI (or arXiv
   ID or PMID) and which index it came from. PubMed results must be credited
   to PubMed along with their DOIs.

## Procedure

1. **Scope.** If the question is genuinely ambiguous (unclear scope, timeframe,
   or intended use), ask up to 3 clarifying questions — once, all together — then
   proceed. Otherwise start immediately.

2. **Plan.** Decompose into at most `subq` sub-questions (none if `subq=0`).
   For each one, say whether it is a literature question (use the scholarly
   servers) or a web question. State the plan, the effective parameters, and
   which scholarly servers are available, in a few lines, before
   investigating.

3. **Investigate.**
   - *`subq=0`*: no subagents. Do the investigation yourself:
     - About `searches` queries spread across WebSearch and the scholarly
       indexes.
     - Open the `fetches` most authoritative results.
     - Then snowball for `hops` hops.
   - *`subq>0`*: spawn one subagent per sub-question, all in a single message
     so they run in parallel (max 5 concurrent; queue the rest).
     - For **literature** sub-questions use the `general-purpose` subagent,
       which inherits MCP tools.
     - For web-only sub-questions use `Explore`.
     - Each subagent prompt = its sub-question plus:

       "Run about <searches> queries from different angles across WebSearch
       and these scholarly MCP tools: <list the configured ones>. Search at
       least two indexes for literature. Open the <fetches> most authoritative
       primary sources: full text where a claim depends on methods or
       numbers, abstract otherwise. Snowball the citation graph <hops> hop(s)
       from your best seed papers (references, citing papers,
       recommendations). Do not write files or change any library, watch or
       collection state. Return ≤700 words: findings as bullet claims, each
       with source URL, date and DOI/arXiv ID/PMID when it is a paper; note
       conflicts between sources and anything you could not verify. Evidence
       rules: report only what a source you actually opened states, never
       what you remember. Tag each claim `fetched`, `abstract-only` or
       `snippet-only`. Never invent URLs, titles, IDs, figures or quotes. Say
       'not found' rather than filling a gap."
   - *`waves>1`*: after each wave, list the gaps, the conflicts, and the
     load-bearing claims that have fewer than `triangulate` independent fetched
     sources. Launch targeted subagents on them in the next wave, staying
     within the `agents` total. Stop early if nothing material is left open.
   - *Triangulation*: a load-bearing claim backed by fewer than `triangulate`
     independent fetched sources can't be labelled verified. Label it
     single source and mention it in Open questions & caveats.

4. **Sources.**
   - Prefer primary sources (official docs, papers, standards, filings) over
     aggregators.
   - Use the scholarly servers as described above for every literature
     sub-question. Use WebSearch for everything else.
   - If WebSearch is unavailable, fall back to the configured MCP search
     tools and say so in the report.
   - If no scholarly server is available, use WebSearch on publisher, arXiv
     and PubMed pages, and say so in the report.
   - Ignore any tool-schema note claiming WebSearch is US-only. It works
     globally; use it.

5. **Report.** Follow the Report template section below. Write the
   report (all tiers) to `research/<kebab-slug>-<YYYY-MM-DD>.md`, creating the
   folder if needed. Every non-obvious claim gets an inline markdown link to its
   source and an evidence label (see Evidence standard).

6. **Self-check (before writing the file).** Go through the draft sentence by
   sentence:
   - Strike or relabel any claim you can't trace to a source fetched in this
     run.
   - Make sure every link was actually opened and supports the claim it is
     attached to.
   - Make sure the subagents' `snippet-only` and `abstract-only` claims are
     labelled, not promoted to verified.
   - Make sure duplicate papers found in several indexes weren't counted as
     independent sources.
   - Move whatever falls out to Open questions & caveats.

7. **Reply** in chat with the file path and a ≤10-line summary of key findings.
   Keep the evidence labels on the load-bearing claims. Do not paste the full
   report. Add any usage message a tool asked to have shown, word-for-word.

## Report template

Structure every report exactly like this. Keep prose tight; the report should be
substantially shorter than the sources it distills.

```markdown
# <Headline answering the question>

*<YYYY-MM-DD> · depth: <tier> (subq=… searches=… fetches=… waves=… triangulate=… agents=… hops=…) · <n> sources fetched · indexes: <web, arXiv, Semantic Scholar, PubMed, Consensus, … actually used>*

## Executive summary
5–10 sentences that directly answer the question, including the main caveat.

## Findings
Organized by theme (never by subagent). Each claim carries an inline citation:
"X does Y ([Source name](url), 2026) — *verified*." Every non-obvious claim
carries one label: *verified* (fetched source states it; add "≥2 independent
sources" when true) · *single source* · *inferred* (give the reasoning) ·
*assumed* (say what would confirm it) · *unverified (snippet only)*. Add
*(abstract only)* to paper claims not checked against the full text.

## Literature map
Include this section only when papers were used. Base it on the citation
graph lookups made in this run:
- **Seminal / foundational** papers, and what they established.
- **Main lines of follow-up work** (clusters of citing papers).
- **Replications, critiques, retractions or contradicting results** found by
  following citations forward.
- **Most recent relevant work.**

Each entry: [Title](url) (first author, year, ID). Add one line on how it
relates to the others ("cites X", "replicates Y", "contradicts Z").

## Open questions & caveats
What could not be verified, where sources conflict, and what may already be
stale. List any scholarly server that was unavailable, unauthenticated or
rate-limited. Never omit this section.

## Sources
1. Title — publisher, date. URL
2. Paper title — first author et al., venue, year. DOI / arXiv ID / PMID.
   URL · via <index> (full text | abstract)
3. ...
```

Template rules:
- Evidence only: nothing from memory. Every cited source was actually fetched
  in this run and states what it is cited for. `## Sources` lists only fetched
  sources.
- Quote sparingly (<25 words per source); paraphrase by default.
- Prefer the most recent primary source when sources conflict, and say which one
  won and why.
- Dead ends count: if a sub-question came up empty, record that in Open
  questions rather than padding Findings.

## Guardrails

- One subagent per sub-question, never per search. Never exceed `agents`
  subagents in total, or any hard cap, whatever the overrides say.
- Budgets: these knobs set the run's cost, mostly
  `subq × fetches × waves`, plus up to `5 seeds × hops` graph expansions per
  investigator. Higher values buy coverage and corroboration, not permission
  to pad the report.
- Use scholarly servers read-only. Do not create topic watches, Consensus
  collections or library entries. arXiv's local paper cache from
  `download_paper` is fine.
- If a scholarly server is rate-limited, retry once after a short wait,
  then switch to another index and note it in the report.
- If the question is trivially answerable with one lookup, say so and answer it
  directly instead of burning a research run.
