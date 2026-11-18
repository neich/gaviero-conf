---
name: research-companion
description: Writes a plain-language companion to a complex research report, for a reader at the level of a first- or second-year PhD student who is new to the topic and to how the report was made. Run it only when the user explicitly asks for a companion. It works on the reports of the deep-explore DSL script, /deep-research and /academic-research, and (in generic mode) on any other report. Every term, abbreviation, number type and pipeline word is defined before use. Background concepts get checked links (Wikipedia first, then official docs or reference works). The report's evidence labels, numbers, hedges and scope are kept exactly; it explains the report and never extends it. Drafting, a naive-reader test, a faithfulness check and revisions each run in a fresh agent that sees only the files, never the research session. The report is never edited; the companion is a new file beside it. Invoke with /research-companion [rounds=N] <report .md | deep-explore OUT_DIR | research/<slug>/>.
argument-hint: "[rounds=1-3] <path to report .md | deep-explore output folder | research/<slug>/>"
allowed-tools: Task, Read, Write, Edit, Glob, Grep, WebFetch, Bash
---

# Research Companion

Treat `$ARGUMENTS` as the report to explain. The output is a separate file
that makes the report understandable to a first- or second-year PhD student
who does not know this topic or how the report was produced, without making
it any less accurate. The report stays as it is: it is the reference, and the
companion is the guide to reading it.

**Why the rules are strict.** Plain-language rewrites of science written by
language models often state results more broadly than the source did. Readers
also rate them as clear even when they understood them less well. So accuracy
comes first, and readability comes from explaining more, not from saying
less. When simple wording is not enough, add an explanation, an example or a
link. Do not drop the precise statement.

**Why separate agents.** The skill may run right after a research session,
when the investigation is still in context: unaudited findings, dropped
papers, leads. That invites the companion to add things the report never
said. So drafting, reading, checking and revising are each done by a fresh
agent that is given only file paths. You (the main agent) resolve the input,
dispatch, check links, and write the log. Do not add content about the topic
yourself.

## When to use it

Only when the user asks for a companion, explicitly (`/research-companion
[rounds=N] <path>`). No research skill or DSL script runs it on its own:
`/academic-research`, `/deep-research` and the deep-explore script only
write their reports. Do not start this skill unprompted after a research
run. At most, mention that it exists.

**If you were given one role** (a subagent whose prompt names a role), do
only that role, as written under **Roles**. The Procedure is for the agent
that dispatches the roles. Do not run the other roles yourself.

## Parameters

`rounds=N` (default 2, clamp to 1–3): how many review-and-revise rounds the
companion goes through. Strip it from `$ARGUMENTS`. The rest is the path.

## Source profiles

Each producer writes a different layout and uses different certainty words.
Detect the profile in step 1 and give the subagents the matching block from
this section. If a producer changes its layout, update its profile here too.

### deep-explore (DSL script `.gaviero/dsl/deep-explore/deep-explore.gaviero`)

- **Detect:** a folder (the run's `OUT_DIR`) with `report.md` and
  `report-audit.md`, usually with `landscape.md`, `journal.md`,
  `archive.md`, `frontier-v*.json`, `audit-v*.json`. A `report.md` whose
  sections include `## Answer`, `## New avenues`, `## Contested and open`,
  `## How the field was explored` and `## Audit`.
- **Input:** always `report.md` (the citation-checked version), never
  `report-draft.md`. If only `report-draft.md` exists, the run did not
  finish. Say so and stop.
- **Siblings:**
  - `report-audit.md` is part of the report: what the final citation check
    changed and why.
  - `landscape.md`, `journal.md` and `archive.md` may be read **only to
    explain how the exploration ran**. They contain claims that no audit
    checked, so no claim about the topic may come from them.
  - Never read `*-finding-v*.json`, `frontier-v*.json`, `assignments-v*.json`
    or `audit-v*.json`. They hold unaudited claims, and the report already
    summarises the audit.
- **Output:** `<OUT_DIR>/report-companion.md`.
- **Sections to explain (in order):** Answer, Findings, New avenues,
  Contested and open (including "Unverified leads"), How the field was
  explored, Audit, References.
- **Certainty words and fixed phrases** (use the same phrase every time):
  - Claim strength:
    - *replicated*: "found again by more than one independent study";
    - *single study*: "rests on one study";
    - *review*: "comes from a review article that summarises other studies,
      not from a new experiment";
    - *preprint*: "comes from a paper not yet peer reviewed";
    - *contested*: "studies disagree".
  - Source access, if the report shows it:
    - *fulltext*: "checked against the paper's full text";
    - *abstract only*: "checked against the paper's summary (its abstract),
      not its full text";
    - *citation context*: "taken from how a citing paper describes the work,
      not from the work itself";
    - *consensus*: "taken from the Consensus search service's summary of the
      paper".
  - Audit verdicts:
    - *supported*: "an independent checker found a passage in the source
      that says this";
    - *partial*: "the source says only a weaker or narrower version, and
      the report states that narrower version";
    - *not supported*: "the checker could not find this in the source";
    - *cannot verify* / *unverifiable*: "the full text was not available to
      check it";
    - *unresolvable*: "the cited work could not be found in the scholarly
      databases";
    - *retracted*: "the paper was withdrawn by its journal or authors".
  - **Unverified leads:** "a hint the run found but did not check against a
    source; not a finding". Never present one as a result.
  - **New avenues** are proposals for future research made by the run. They
    are not findings. Say so every time you discuss one.
  - **Task substitution:** a lane answered an easier, nearby question instead
    of the one it was given. The audit catches this and the question is
    reopened.
- **Pipeline vocabulary** (define each term that the report uses, with this
  meaning):
  - *brief*: the research question the run was given.
  - *scout*: the first agent. It maps the field before any question is asked.
  - *landscape*: the scout's map. It records what is settled, the *research
    front* (what groups are actively working on in the last ~2 years),
    *clusters* (groups of papers that cite each other), *controversies*,
    *open problems*, *bridges* (works cited from two clusters that rarely
    cite each other) and *blind spots* (assumptions, methods or neighbouring
    fields that nobody in the field looks at).
  - *anchor works*: the 3–6 central papers that the scout's citation search
    starts from.
  - *frontier*: the run's list of questions. Each one is *open*, *active*,
    *closed* (answered by supported claims), *dead* (two lanes found nothing,
    or the literature cannot answer it) or *parked* (only a new experiment or
    new data could answer it).
  - *pass*: one round of the loop: curate, then investigate, then verify,
    then decide whether to stop.
  - *curator*: the agent that updates the frontier each pass and chooses that
    pass's questions.
  - *lane*: one investigator working on one question in one pass. Its *lens*
    is *exploit* (answer a high-priority question well), *explore* (map an
    unfamiliar direction) or *falsify* (try hard to disprove the run's
    strongest claim).
  - *operators*: the curator's ways of generating new questions:
    - decompose: split a broad question into testable parts;
    - falsify: ask what result would refute the leading claim;
    - bridge: connect clusters that do not cite each other;
    - analogy: find another field that studies the same mechanism under a
      different name;
    - recency: look at the newest work citing the anchors;
    - gap: follow stated open problems;
    - method transfer: use one cluster's method to test another cluster's
      claim.
  - *priority*: relevance + expected information gain + novelty +
    tractability − depth. Each score runs from 0 to 3. Depth is how many
    steps the question is from a seed question.
  - *verifier*: the auditor. It checks each claim against the source's own
    text. The script is designed to run it on a different model family
    from the investigators, but that depends on how the run was set up, so
    say so only if the report does.
  - *stop judge*: the agent that ends the loop when the frontier is exhausted
    or no longer adding verified knowledge. Agreement between agents is not a
    reason to stop.
  - *citation check*: the final step. It looks up every reference again and
    checks it for retraction.
  - *snowballing*: following a paper's references (*backward*) or the papers
    that cite it (*forward*).
  - *citation context*: the sentence around a citation in a citing paper.
  - *full text* vs *abstract only*: whether a claim was checked against the
    paper's body or only against its summary.
  - *collection* / *corpus*: the run's store of full texts on the academic
    server. The server itself searches OpenAlex, Semantic Scholar and Europe
    PMC, and uses Consensus for evidence summaries.

### deep-research (skill `/deep-research`)

- **Detect:** a file `research/<slug>-<YYYY-MM-DD>[-vN].md` whose italic
  header line contains `depth:` and `evidence: [`, with the sections
  `## Executive summary`, `## Findings`, `## Implementation notes` and
  `## Open questions & caveats`. Its evidence file is
  `<same name>.evidence.md`. A later version links the evidence files of the
  earlier versions too.
- **Siblings:** the evidence file(s) may be read **only to explain how the
  research ran** (sub-questions, sources opened, indexes used, waves). They
  are the raw research record and contain unchecked material, so no claim
  about the topic may come from them.
- **Output:** `<report basename>-companion.md` beside the report.
- **Sections to explain (in order):** the "What changed" box and `[vN]`
  marks if present, Executive summary, Findings, Implementation notes,
  Literature map, Open questions & caveats, Sources.
- **Certainty words and fixed phrases:**
  - *verified*: "a source the research actually opened states this". Add
    "and at least N independent sources agree" when the label says "≥N
    independent sources".
  - *single source*: "only one opened source states this".
  - Explain the difference once, in *How to read "how sure are we"*, using
    the report's own `triangulate` value(s) from its header. A load-bearing
    claim (one the answer depends on) may be called *verified* only when
    at least `triangulate` independent opened sources state it. Otherwise
    it is labelled *single source*. With `triangulate=1`, a claim resting
    on one source can therefore carry either label. A versioned report can
    use different values per version, so say which applies.
  - *inferred*: "the report's own reasoning across sources, not something a
    source states". Keep the reasoning the report gives.
  - *assumed*: "an assumption the report did not check".
  - *unverified (snippet only)*: "seen only in a search-result preview; the
    page itself was not opened".
  - *(abstract only)*: "checked against the paper's summary (its abstract),
    not its full text".
- **Pipeline vocabulary:**
  - *depth tier*: quick, standard or deep. It sets the knobs below.
  - *knobs*:
    - `subq`: the number of sub-questions;
    - `searches`: queries per investigator;
    - `fetches`: sources actually opened per investigator;
    - `waves`: rounds of investigation, where each later wave targets the
      gaps and conflicts left by the one before;
    - `triangulate`: the minimum number of independent opened sources needed
      for a load-bearing claim to count as verified;
    - `agents`: the total number of subagents;
    - `hops`: how many steps of citation snowballing.
  - *sub-question*: a part of the main question, investigated by its own
    subagent.
  - *triangulation*: confirming a claim with independent sources. The same
    paper found in two databases counts once.
  - *index*: a search database (web search, arXiv, Semantic Scholar, PubMed,
    OpenAlex, Europe PMC, Consensus).
  - *seed paper*: a paper that citation snowballing starts from.
  - *load-bearing claim*: a claim the answer depends on.

### academic-research (skill `/academic-research`)

- **Detect:** `research/<slug>/<slug>-v<N>.md` whose header line starts
  `*Version v<N> · files:`, with the sections Findings, Evidence table,
  Literature map, Quality & risk of bias, and Gaps & caveats. A folder
  `research/<slug>/` resolves to the highest `<slug>-v<N>.md`.
- **Siblings:** `<slug>-v<N>-evidence-table.md` and
  `<slug>-v<N>-search-log.md` are part of the review and may support
  claims. `<slug>-v<N>.bib` only gives reference metadata.
- **Output:** `<slug>-v<N>-companion.md` beside the review.
- **Sections to explain (in order):** Abstract, Question & method,
  Findings, Evidence table, Literature map, Quality & risk of bias, Gaps &
  caveats, *Changes since v<N-1>*, References.
- **Fixed phrases:**
  - *established*: "the evidence is solid".
  - *supported*: "some evidence points this way, but [the review's reason
    why it falls short]".
  - *contested*: "studies disagree".
  - *inferred*: "the review's own interpretation, not a direct finding".
  - *assumed*: "an assumption the review did not check".
  - Explain the access marks *(abstract only)*, *secondhand (via X)* and
    *full text (web)*.
- **Pipeline vocabulary:** benchmark set, relative recall, screening,
  snowballing, risk of bias. Define them from the review's own method
  section and search log.

### generic (anything else)

- **Output:** `<basename>-companion.md` beside the report.
- Explain the report's own structure in its own order. Keep its own
  certainty words, and explain each one the same way every time it appears.
- If the report grades no evidence, say so in the opening line. Do not
  invent grades.
- Sibling files are used only if the report links them, and only to explain
  method.

## Procedure

1. **Resolve the input.**
   - Parse `rounds=`. Resolve the path:
     - a `.md` file is used as is;
     - a folder resolves by profile: deep-explore → `report.md`;
       academic-research → the highest `<slug>-v<N>.md`; otherwise the single
       non-companion, non-evidence `.md` in the folder;
     - a bare slug: try `research/<slug>/`, then `research/<slug>*.md`.
   - If nothing matches, or more than one report matches, ask the user for
     the path and stop.
   - **Refuse** to explain a file that is itself a companion
     (`*-companion.md`, `*-companion-<n>.md`, `report-companion*.md`,
     `companion-*.md`), an evidence or audit file (`*.evidence.md`,
     `*-evidence-table.md`, `*-search-log.md`, `report-audit.md`), a working
     file (`report-draft.md`, `journal.md`, `archive.md`, `landscape.md`)
     or a JSON artefact. Name
     the report the user probably meant.
   - Read the report and detect the profile (see Source profiles). Collect
     the sibling files that exist and are allowed for that profile.
   - **Output path:** use the profile's name. If that file already exists,
     use `-companion-2.md`, `-companion-3.md` and so on (for deep-explore:
     `report-companion-2.md`, …). Never overwrite or edit an earlier
     companion, and never edit the report or its siblings.
   - **Skill file path.** Agents you dispatch read their role from this
     file. Give them its absolute path: `$GAVIERO_ROOT` expanded, plus
     `/.gaviero/skills/research-companion/SKILL.md`. If `GAVIERO_ROOT` is
     unset, paste the needed sections into the prompts instead (you already
     have this file loaded).
   - Note the report's length. The companion is often longer than the
     report. That is expected.

2. **Draft.** Spawn one fresh `general-purpose` subagent with the
   **Drafter** role (see Roles), filling in `<report>`, `<output>`,
   `<siblings>` (each with its allowed use), `<profile>` and the skill file
   path.

3. **Review rounds.** Repeat up to `rounds` times:
   a. Spawn a fresh subagent with the **Naive reader** role. It gets only
      `<output>`.
   b. Spawn a fresh subagent with the **Faithfulness checker** role. Pass it
      the reader's takeaways.
   c. **Links (you, mechanically).** Collect every URL in the companion that
      is not a citation copied from the report. Check each one as described
      in **Background links**. Record which links are broken, point to a
      disambiguation page, or do not match the term they are attached to.
   d. If (a), (b) or (c) found anything, spawn a fresh subagent with the
      **Reviser** role, passing all findings from (a), (b) and (c). Then:
      - re-check (c) yourself for any new link;
      - read each judgement call the reviser listed. If the report does not
        state the connection, mark it *the companion's own reading* or
        remove it.
   e. **Stop early** when a round finds no faithfulness or takeaway problem,
      no define-before-use problem, and at most 3 minor reader items. Pass
      those items to one final Reviser without another review. Do not exceed
      `rounds`. List whatever is left in the log.

4. **Log.** Append the *About this companion* section (the template's last
   section) with Edit. Include:
   - the date, the source files read and how each was used, and the
     profile;
   - the rounds run, the terms defined, and the links kept and dropped;
   - for each round, the problems found in each category and how each was
     fixed;
   - anything left unresolved;
   - the sentence: "drafted, read, checked and revised by separate agents
     that saw only the files listed; the naive reader saw only the
     companion".

5. **Reply.** When run by hand, reply in chat with:
   - the companion's path and the profile;
   - the rounds run and the problems fixed per round;
   - the terms defined and the links kept and dropped;
   - anything left unresolved, and anything the drafter or checker flagged
     as inconsistent in the report itself.

   Do not paste the companion.

**If subagents are unavailable** (no Task or Agent tool): do the draft,
reader, check and revise as separate passes yourself. For the reader pass,
read only the companion. Say so in the log and the reply, and recommend
re-running `/research-companion` in a fresh session for proper isolation.

## Roles

Each role is done by a fresh agent. The agent reads this file, follows its
own role section, and follows the sections that role names. The angle-bracket
fields are filled in by the dispatching agent. `<siblings>` lists each
sibling file together with its allowed use from the profile.

### Drafter

> Write a plain-language companion to the report at `<report>`. Write it to
> `<output>`. You may also read `<siblings>`, under the limits given for
> each. Use only those files, plus the background allowance in Writing
> rules. Do not search the literature, open the cited papers, or use any
> tool other than Read, Write, WebFetch and (if you have it) Bash for curl.
> Use WebFetch and curl only to look up background pages to link and to
> check them. Profile: `<profile>`.
>
> Follow exactly: the `<profile>` block under **Source profiles**, and the
> sections **Reader**, **Writing rules**, **Background links** and
> **Companion template**. Leave *About this companion* as an empty heading.
>
> Return at most 300 words:
> - the terms you defined (the count and the list);
> - the links you used, and the candidates you dropped with the reason;
> - each report passage you could not explain without adding content (left
>   out on purpose);
> - anything in the report that looked inconsistent. Report it; do not fix
>   it.

### Naive reader

> You are a second-year PhD student in a neighbouring field. You are reading
> `<output>` for the first time, and you have nothing else. Read only that
> file, completely. Do not open the report or any other file, and do not
> look anything up. Return:
> 1. **Lost points.** Each sentence or paragraph where you got lost, where a
>    term was used before it was explained, where an explanation relied on
>    something not yet explained, or where a step in the reasoning was
>    skipped. Quote it and say what was missing.
> 2. **Too thin.** Places where a simpler explanation, an example or a link
>    would have helped.
> 3. **Takeaways.** Your 6–12 main takeaways, in your own words, as you
>    would tell a colleague. For each one, say how sure the companion says
>    the evidence is.
> 4. **Confusing links.** Any linked page whose title did not seem to match
>    the term it was attached to.
> 5. **Overall.** One line: is this readable for someone at your level, and
>    what is the single biggest remaining obstacle?
>
> Give line numbers with every quote. Be honest. Saying "everything was
> clear" when it was not makes this test useless.

(This role needs no section of this file. Give the reader only this text.)

### Faithfulness checker

> Compare the companion `<output>` with the report `<report>` and
> `<siblings>`. You wrote neither file. Do not edit either. Read both files
> completely. The labelling rules are the `<profile>` block under **Source
> profiles** (its fixed phrases) and the section **Writing rules**.
>
> A visible *Note on the report:* that points out a real inconsistency
> inside the report is allowed: check that both passages exist and are
> described correctly. Text marked *the companion's own reading* or *the
> companion's explanation* is allowed only if it is textbook-level or
> plainly derived.
>
> Report every problem as a triple: (companion sentence, problem, report
> passage or reason).
> 1. **Faithfulness.**
>    - A claim about the topic that has no matching sentence in the report.
>    - A claim taken from a sibling file that may only be used to explain
>      method.
>    - A certainty label that is stronger than the report's, or missing. A
>      label worded differently from its fixed phrase. A label whose fixed
>      phrase is absent at its first use in a top-level section. (The italic
>      label alone is fine after that.)
>    - A background definition or "why this matters" line that makes a
>      claim about the system or field the report studies, or adds a cause
>      or purpose the report does not give.
>    - A number that differs from the report.
>    - A result stated for a broader population, setting, period or system
>      than the report gives.
>    - A judgement ("large", "clearly", "proves", "successful") that the
>      report does not make.
>    - A hedge that was removed.
>    - A proposal or unverified lead presented as a finding.
>    - A citation link changed or attached to a different claim.
> 2. **Takeaways.** For each reader takeaway in `<takeaways>`, say whether
>    the report supports it at that strength. A wrong takeaway means the
>    companion invites a misreading: point to the companion passage that
>    causes it.
> 3. **Define-before-use.** A technical term, abbreviation, statistic,
>    method name or pipeline word that is used before it is defined. A
>    definition that relies on an undefined term. A term missing from the
>    Glossary.
> 4. **Definitions.** A background definition that is wrong, or one that
>    makes a claim about this topic's findings.
> 5. **Coverage.** A report section, finding, caveat or open question that
>    the companion skips without saying so.
> 6. **Same word, two senses** without saying so.
>
> When unsure whether something is a problem, report it. One line per
> problem, with companion line numbers, grouped by category, most serious
> first.

### Reviser

> Revise the companion `<output>` in place with Edit. Use the report
> `<report>` (and `<siblings>`, under their limits) as the only source for
> claims about the topic. Follow the `<profile>` block under **Source
> profiles** and the sections **Reader**, **Writing rules** and **Background
> links**. Fix every item in `<findings>` with the smallest change that
> resolves it:
> - **Faithfulness and takeaway problems:** narrow the sentence to what the
>   report says, or restore the label, number, hedge or scope, or delete the
>   sentence. Never fix a problem by adding a new claim.
> - **Reader's lost points and thin spots:** add a definition, a step, an
>   example or a checked link before the point of use. If the report does not
>   define something, say so. If a point cannot be made simpler without
>   becoming wrong, keep it precise and add an unpacking sentence.
> - **Define-before-use:** add or move the definition, and add the Glossary
>   entry.
> - **Coverage:** explain the skipped part, or state that it was left out
>   and why.
> - **Broken or mismatched links:** remove them, or replace them with a page
>   you check first.
>
> Return a list: for each item, the fix you made, or why you made no change.
> List separately every judgement call where you connected two things the
> report does not explicitly connect.

## Reader

Write for a first- or second-year PhD student:
- They know how research works in general: papers, peer review, citations,
  what an experiment is.
- They do not know this topic, its jargon, or any of the producer's pipeline
  words.
- Their statistics are uneven. Explain what each kind of number means (an
  effect size, a confidence interval, a sample size *N*, a recall
  percentage) the first time one appears.
- They are reading to understand the report well enough to use it, check
  it, and explain it to someone else.

## Writing rules

**Source.**
- Write only from the given files. Every claim about the topic (findings,
  numbers, papers, conflicts, gaps, proposals) must map to a sentence in the
  report or in a sibling file that is allowed to support claims. Add no new
  papers, numbers or conclusions.
- **Background explanations** are the one place where general knowledge is
  allowed: what a meta-analysis is, what a confidence interval means, what
  a DAG is, what OpenAlex is. Keep them at textbook level. Never make them
  about this topic's findings. When there is a linked page, keep them
  consistent with it.
- A background definition must not say anything about the system, field or
  question the report studies: no "this is why X is hard", and no "X slows
  down when…". Such statements are findings. Put them in the findings
  sections with the report's label, scope and section pointer, or leave them
  out.
- Do not add purposes, causes or consequences ("so agents cannot tamper",
  "this is why…") that the report does not state. If one helps the reader,
  mark it as *the companion's explanation, not the report's* and keep it
  textbook-level.
- If a passage cannot be explained without adding content, leave it out and
  report it.

**Accuracy.**
- **Keep every label and hedge.** Every claim keeps the report's label in
  italics. Give the label's fixed phrase from the profile at its first use
  in each top-level section, and wherever the label is the point of the
  sentence. After that, the italic label alone is enough. Never use a
  different wording for the same label. Keep the report's own hedges
  ("may", "in one study", "n=1"), and keep them at first mention, including
  in *The short version*.
- **Do not rank or interpret labels beyond the report.** Do not say one
  label is stronger than another, or what a label implies about who checked
  what, unless the report or the producer's definition (the profile) says
  so.
- **Never broaden the scope.** Keep each result tied to its population,
  setting, system, design and period. Report study results as what the
  studies found ("in 3 trials with adults, X reduced Y"), not as general
  truths ("X reduces Y"), unless the report states the general claim at its
  strongest label.
- **Keep the numbers**: effect sizes, intervals, N, counts, percentages,
  versions, dates. Explain what each kind of number means. Do not replace a
  number with a vaguer word. Do not turn a number into a judgement ("a big
  effect") unless the report does.
- **Keep the distinctions:**
  - findings vs proposals (new avenues, recommendations);
  - verified vs unverified;
  - what a source says vs what the report infers.
  The companion's job is to make these lines easier to see, not to blur
  them.
- **Every number gets its yardstick.** At its first use, say what a number
  measures: the metric, benchmark or task, the unit, and what it is compared
  with. Take this from the report. If the report does not say, write "the
  report does not say what this measures" rather than guess.
- **Every named thing gets a "what it is".** At the first mention of a
  paper, system, tool, benchmark, dataset, company or organisation, give
  one line saying what it is: "AI-Researcher, an automated research-agent
  system the report reviews". Take the line from the report. Use general
  knowledge only for something widely known, and keep it consistent with a
  checked link. Otherwise write "the report does not describe it further".
  Do not explain a name by using another name that has not been
  introduced.
- **The report's own system vocabulary counts as jargon.** Keywords,
  settings, flags, file names and component names of the tool or system the
  report is about each get a definition at first use, taken from the
  report. If the report uses one without defining it, say so. A short code
  or config snippet may illustrate a concept only if it is copied from the
  report.
- **Do not hide the report's own inconsistencies.** If two passages of the
  report disagree, for example a summary figure that differs from the
  figure in Findings, keep both as written. Add a visible *Note on the
  report:* line that points to both passages, and do not resolve the
  disagreement.
- **Put undefined terms where they are used.** When the report uses a term
  without defining it, say so once, where the term matters. Do not fill
  *Key ideas you need first* with "the report does not define X" entries.
  That section is for concepts the reader needs and can be given. List the
  report's undefined terms once, in the Glossary, marked "(not defined in
  the report)".
- **Flag words used in two senses.** When the same word means different
  things (for example *wave* in the research method and *wave* in the
  system studied), say so at the second sense.
- **Tables and diagrams are allowed** when every cell comes from the report:
  a timeline, a mapping from problems to proposals, a small ASCII diagram.
  They often explain structure better than prose.
- **Explain why, not only what.** When the report gives a design or a
  conclusion that rests on a chain of reasons, lay out the chain before the
  conclusion, in the report's order. When a step of the chain is missing
  from the report, say that it is missing.
- **Complexity is allowed.** When a point cannot be simplified without
  becoming wrong, keep the precise version and add a sentence or an example
  that unpacks it. Length is not a constraint; correctness is.
- Keep citation links exactly as the report gives them, attached to the same
  claims. Numbered references `[n]` stay as `[n]` and point to the report's
  References list.
- End each explained claim or paragraph with a pointer to the report section
  it explains, for example *(→ report: Findings › Budgets)*, so the reader
  can check it.

**Plain language.**
- **Define before use.** Introduce every technical term, abbreviation,
  statistic, method name and pipeline word at or before its first use.
  Expand the abbreviation, then say in one or two sentences what it is and
  why it matters here. The producer's own method vocabulary (see the
  profile) is usually the densest jargon, so it gets the same treatment. A
  definition may use only everyday words or words already defined.
- Order **Key ideas you need first** so that each concept relies only on
  the ones before it.
- Write short sentences in the active voice, with one idea per paragraph.
- Give one concrete example or analogy per hard concept where it helps, and
  say where the analogy breaks down.
- When the report's own sentence is dense, quote it (under 40 words), then
  unpack it piece by piece.
- Do not aim for a readability score. Automatic readability metrics track
  comprehension poorly; define-before-use and the naive-reader test are the
  checks.

## Background links

Link a concept at its first use, and again in the Glossary, when a good
reference page exists. Links are background only, never evidence for a
claim about the topic.

- **Prefer, in this order:**
  1. English Wikipedia.
  2. For a software tool, library, protocol or database: its official
     documentation or home page.
  3. A stable reference work for the field, such as the Stanford
     Encyclopedia of Philosophy, the NCBI Bookshelf, the Cochrane Handbook
     or Glossary, or a standard textbook chapter that is free online.
  4. A paper already cited in the report.

  Aim for about 50 distinct pages, at most 70. Repeating a link in the
  Glossary does not count again. Go over 50 only for terms that the
  naive reader flagged or that the findings depend on.
- **Never guess a URL.** Check Wikipedia titles in batches of up to 20, one
  request per batch.
  - With Bash, use curl, which encodes the titles for you:

    ```bash
    curl -s -A "research-companion-skill/1.0" -G "https://en.wikipedia.org/w/api.php" \
      -d action=query -d format=json -d redirects=1 \
      -d "prop=extracts|pageprops" -d ppprop=disambiguation \
      -d exintro=1 -d explaintext=1 -d exsentences=1 -d exlimit=20 \
      --data-urlencode "titles=<T1>|<T2>|…"
    ```

  - Without Bash, use WebFetch on
    `https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=extracts|pageprops&ppprop=disambiguation&exintro=1&explaintext=1&exsentences=1&exlimit=20&titles=<T1>|<T2>|…`.
    URL-encode the titles: spaces as `_`, and `&` as `%26`.
- Drop or replace a title that:
  - is missing (it has a `"missing"` key);
  - is a disambiguation page (it has `pageprops.disambiguation`);
  - has a first sentence that describes a different concept. For example,
    *Snowball sampling* is survey recruitment, not citation snowballing.
- Link to the final title after redirects. Read the `redirects` and
  `normalized` arrays, and write the link as
  `https://en.wikipedia.org/wiki/<Title>` with spaces as `_`, and `(` `)`
  as `%28` `%29`. Some markdown renderers cut a link at the first `)`.
- Check every non-Wikipedia link with its own request: it must load, and the
  page must be about the term. Never link an unchecked URL.
- If no good page exists, give no link. The definition is enough.

## Companion template

```markdown
# Understanding "<report headline, shortened if very long>"

*Companion to [<report file name>](<relative path to report>) · <YYYY-MM-DD> · for readers new to this topic and to how the report was made. It explains the report and adds no findings of its own; where the two differ, the report is right.*

## How to read this companion
3–6 sentences: what the report is (which tool or pipeline produced it), what
this companion covers, how labels are shown (italic label + plain phrase),
and how the *(→ report: …)* pointers work.

## The short version
5–10 short sentences: the question, the answer, how sure the report is
(labels explained), and the main caveat. It is read before anything is
defined, so use everyday words, or define a term inline in a few words. Do
not name papers or systems here unless they are explained in the same
sentence. Keep long notes about the report's inconsistencies out of this
section: a one-line pointer to the later *Note on the report* is enough.

## Key ideas you need first
The concepts the findings depend on, both topic concepts and pipeline
concepts. Define each one (with a link where possible), and order them so
that each builds only on the ones before it.

## How the report was produced
The method in plain steps, with the report's real numbers (passes, lanes,
sources opened, claims audited, parameters). Say what each step protects
against and what it can still miss.

## How to read "how sure are we"
The profile's certainty words with their fixed phrases, and which kinds of
evidence count as stronger or weaker here.

## What the report found
The same themes, in the same order, as the report's main findings section
(Answer + Findings / Executive summary + Findings / Findings). Each claim
keeps its label, numbers and citation link, and ends with a section pointer.

## <Profile-specific sections, in the report's order>
- deep-explore: "New directions the run proposes" (New avenues: proposals,
  not findings) · "Disputed, open and unchecked" (Contested and open) ·
  "How much of the evidence held up" (Audit + report-audit.md).
- deep-research: "What it means in practice" (Implementation notes: the
  recommendation, specifics, constraints, alternatives, decisions left open)
  · "How the sources relate" (Literature map) · "What is still open"
  (Open questions & caveats).
- academic-research: "Reading the evidence table and literature map" (using
  one row as a worked example) · "Quality and risk of bias" · "What we still
  don't know" (Gaps & caveats).
- generic: one section per remaining section of the report.

## Changes since the previous version
Only if the report has such a section, box or version marks: explain them.

## Finding and reading the sources
How to read a reference entry in this report (DOI, arXiv ID, PMID, OpenAlex
ID, what each is and how to open it), using one entry as a worked example.

## Glossary
Alphabetical. Every term defined above, with a one-line definition and the
link.

## About this companion
The log from step 4.
```

Leave out a section the report has nothing for. Never invent content to fill
one.

## Guardrails

- Never edit the report, its sibling files, or an earlier companion.
- Never read deep-explore's JSON artefacts. Never take a claim about the
  topic from a file that is allowed only for method.
- At most `1 + 3 × rounds` subagents per run (drafter, then reader, checker
  and reviser per round). That is at most 10.
- **Cost.** In the dry run on a 491-line `/deep-research` report, two rounds
  used about 1M subagent tokens. One round costs roughly half that.
- Do not search the literature or open the cited papers. If the report is
  wrong or thin, say so in the reply. Fixing the report is a job for the
  tool that produced it.
