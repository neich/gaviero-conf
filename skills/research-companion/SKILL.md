---
name: research-companion
description: Writes a plain-language companion that explains an existing research review to a bright reader who is new to the field and to evidence synthesis (a first-year PhD student). Every term and abbreviation is defined before use, background concepts get checked links (Wikipedia first), and the review's evidence labels, numbers and scope are kept exactly — it explains the review, it never extends it. Drafting and checking run in fresh subagents that see only the files, never the research session. Built for /academic-research output (research/<slug>/<slug>-v<N>.md, writes <slug>-v<N>-companion.md beside it); other reports work in a generic mode. Invoke with /research-companion <path to review .md | research/<slug>/>.
argument-hint: "<path to review .md | research/<slug>/ folder>"
allowed-tools: Task, Read, Write, Edit, Glob, WebFetch
---

# Research Companion

Treat `$ARGUMENTS` as the review to explain. The output is a separate file
that makes the review understandable to a first-year PhD student without
making it less accurate.

**Why the rules are strict.** LLM-written plain-language versions of
science tend to state results more broadly than the source did, and readers
rate them as clear even when they understand them less well than
human-written ones. So accuracy comes first, and readability is reached by
explaining more, not by saying less.

**Why subagents.** Loading this skill does not clear the conversation. If it
runs right after a research session, the investigation (full texts, leads,
dropped papers) is still in context and invites additions the review never
made. The draft and the check are therefore done by fresh subagents that are
given only file paths. You (the main agent) only resolve inputs, dispatch,
apply the checker's fixes and write the log. Don't add content of your own.

## Shared contract with `academic-research`

This skill reads the layout that `/academic-research` writes. If that skill
changes any of the following, update this file too:
- File names: `<slug>-v<N>.md`, `<slug>-v<N>-evidence-table.md`,
  `<slug>-v<N>-search-log.md`, `<slug>-v<N>.bib`.
- Header line starting `*Version v<N> · files:`.
- Sections: Abstract, Question & method, Findings, Evidence table,
  Literature map, Quality & risk of bias, Gaps & caveats, References,
  and *Changes since v<N-1>* when N > 1.
- Evidence labels: *established*, *supported*, *contested*, *inferred*,
  *assumed*; access marks *(abstract only)*, *secondhand (via X)*,
  *full text (web)*.

## Procedure

1. **Resolve the input.**
   - A `.md` file: use it. A folder `research/<slug>/`: use the highest
     `<slug>-v<N>.md` in it (Glob). A bare slug: try `research/<slug>/`.
     Anything else, or nothing found: ask the user for the path and stop.
   - Never explain a file that is itself a companion, evidence table or
     search log.
   - **Mode.** Read the review. If it matches the shared contract (header
     line, Findings + Gaps & caveats sections, the labels), use
     **academic mode** and collect the sibling files that exist. Otherwise
     use **generic mode**: explain whatever structure and labels the
     document has, skip template sections it has nothing for, and say in the
     companion's opening line that the source does not use the
     academic-research layout (and, if true, that it does not grade its
     evidence).
   - **Output name.** Academic mode: `<slug>-v<N>-companion.md` beside the
     review. Generic mode: `<basename>-companion.md` beside it. If that file
     exists, use `-companion-2.md`, `-companion-3.md`, … Never overwrite or
     edit an earlier companion, and never edit the review or its siblings.

2. **Draft (fresh subagent).** Spawn one `general-purpose` subagent with the
   prompt below, filling in the paths and the output path. It writes the
   companion file itself and returns a short report.

   > "Write a plain-language companion to the research review at `<review>`.
   > Also read, if listed: `<evidence table>`, `<search log>`. Write it to
   > `<output>`. Use only those files plus the background-definition
   > allowance below. Do not search the literature, open the cited papers,
   > or use any other tool than Read, Write and WebFetch (WebFetch only for
   > link checks). Mode: `<academic | generic>`.
   >
   > <paste the sections **Writing rules**, **Background links** and
   > **Companion template** of this skill verbatim>
   >
   > Return ≤300 words: terms defined (count and list), links kept and
   > links dropped with the reason, any review passage you could not
   > explain without adding content (left out on purpose), and anything in
   > the review that looked inconsistent (report it, don't fix it)."

3. **Check (second fresh subagent).** Spawn one `general-purpose` subagent,
   which writes nothing:

   > "Compare the companion `<output>` with the review `<review>` (and
   > `<evidence table>`, `<search log>` if listed). You did not write either.
   > Report every problem as (companion sentence, problem, review passage or
   > reason):
   > (1) **Faithfulness.** A claim about the topic that has no matching
   > review sentence; a label that is stronger than the review's, or
   > missing; a number that differs; a result stated for a broader
   > population, setting or period than the review gives; a judgement
   > ('large', 'clearly') the review does not make; a hedge removed.
   > (2) **Define-before-use.** A technical term, abbreviation, statistic or
   > method name used before it is defined, a definition that relies on an
   > undefined term, a term missing from the Glossary.
   > (3) **Definitions.** A background definition that is wrong or that
   > makes a claim about this topic's findings.
   > (4) **Links.** Re-check every Wikipedia link with the MediaWiki API
   > batch call: `<paste the URL pattern from Background links>`. Report
   > missing pages, disambiguation pages, and pages whose first sentence is
   > about a different concept. Check other links with one WebFetch each.
   > When unsure whether something is a problem, report it."

4. **Fix.** Apply each reported problem with Edit, by the smallest change
   that resolves it:
   - Faithfulness: narrow the sentence to what the review says, restore the
     label, number or scope, or delete the sentence. Never resolve it by
     adding new claims.
   - Define-before-use: add or move the definition; add the Glossary entry.
   - Wrong definition: correct it to the textbook meaning, or remove it.
   - Broken or mismatched link: remove it, or replace it with a title that
     passes the batch check (run the check yourself).

   If more than 5 faithfulness problems were found, run step 3 once more on
   the fixed file. Don't loop further; list what remains in the log.

5. **Log.** Append an *About this companion* section to the companion
   (the template's last section): date, source files read, mode, terms
   defined, links kept / dropped, checker findings per category and how
   each was fixed, anything left unresolved, and "drafted and checked by
   separate subagents that saw only the files listed".

6. **Reply** in chat with: the companion path, the mode, terms defined,
   links kept / dropped, checker findings fixed and any left, and anything
   the drafter flagged as inconsistent in the review. Do not paste the
   companion.

**If subagents are unavailable** (no Task tool): do steps 2 and 3 yourself
in two separate passes, say so in the log and the reply, and recommend
re-running in a fresh session for proper isolation.

## Writing rules

**Source.**
- Write only from the given files. Every claim about the topic (findings,
  numbers, papers, conflicts, gaps) must map to a sentence in the review or
  its sibling files. No new papers, numbers or conclusions.
- **Background definitions** (what a meta-analysis is, what a confidence
  interval means) are the one place general knowledge is allowed. Keep them
  textbook-level, never about this topic's findings, and consistent with
  the linked page when there is one.
- If a passage can't be explained without adding content, leave it out and
  report it.

**Accuracy.**
- **Keep every label and hedge.** Show the review's label in italics, then
  say what it means, with one fixed phrase per label everywhere:
  *established* → "the evidence is solid"; *supported* → "some evidence
  points this way, but [the reason the review gives for why it falls
  short]"; *contested* → "studies disagree"; *inferred* → "the review's own
  interpretation, not a direct finding"; *assumed* → "an assumption the
  review did not check". Carry over *(abstract only)*, *secondhand* and
  *full text (web)* and explain them. In generic mode, keep the document's
  own certainty words and explain them the same way.
- **Never broaden scope.** Keep each result tied to its population,
  setting, design and period. Report study results as what studies found
  ("in 3 trials with adults, X reduced Y"), not as general truths ("X
  reduces Y"), unless the review states the general claim as *established*.
- **Keep the numbers** (effect sizes, intervals, N, counts, recall) and
  explain what each kind of number means. Don't replace numbers with vaguer
  words, and don't turn a number into a judgement ("a big effect") unless
  the review does.
- **Complexity is allowed.** When a point can't be simplified without
  becoming wrong, keep the precise version and add a sentence or an example
  that unpacks it. Length is not a constraint; correctness is.
- Keep citation links exactly as the review gives them.

**Plain language.**
- **Define before use.** Every technical term, abbreviation, statistic and
  method name is introduced at or before its first use: expand the
  abbreviation, then say in one or two sentences what it is and why it
  matters here. This includes the review method's own vocabulary
  (benchmark set, relative recall, screening, snowballing, abstract only,
  the evidence labels), which is usually the densest jargon. A definition
  may only use everyday words or words already defined.
- Order **Key ideas you need first** so that each concept relies only on
  the ones before it.
- Short sentences, active voice, one idea per paragraph. One concrete
  example or analogy per hard concept where it helps, and say where the
  analogy breaks down.
- Don't aim for a readability score. Automatic readability metrics track
  comprehension poorly; define-before-use is the check.

## Background links

Link a concept at its first use (and again in the Glossary) when a good
reference page exists. Links are background only, never evidence for a
claim.
- **Prefer** English Wikipedia; then a stable reference work for the field
  (e.g. Stanford Encyclopedia of Philosophy, Cochrane or NCBI Bookshelf
  glossaries); then a paper already cited in the review. At most 40 links.
- **Never guess a URL.** Check Wikipedia titles in batches of up to 20, one
  WebFetch per batch:
  `https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=extracts|pageprops&ppprop=disambiguation&exintro=1&explaintext=1&exsentences=1&exlimit=20&titles=<T1>|<T2>|…`
  Drop or replace a title that is missing, is a disambiguation page, or
  whose first sentence describes a different concept (e.g. *Snowball
  sampling* is survey recruitment, not citation snowballing). Link to the
  final title after redirects (`https://en.wikipedia.org/wiki/<Title>`,
  spaces as `_`). Check every non-Wikipedia link with its own WebFetch.
  Never link an unchecked URL.
- If no good page exists, give no link; the definition is enough.

## Companion template

```markdown
# Understanding "<review headline>"

*Companion to [<review file name>](<review file name>) · <YYYY-MM-DD> · written for readers new to this field and to literature reviews. It explains the review and adds no findings of its own; where the two differ, the review is right.*

## The short version
5–10 sentences: the question, the answer, how sure the review is (labels
explained), and the main caveat.

## Key ideas you need first
The concepts the findings depend on, each defined (with link), ordered so
each builds only on the ones before it.

## How the review was done
The method in plain steps, with the real numbers from the search log: how
papers were found, how recall was measured against the benchmark set, how
papers were screened, read and snowballed, and how claims were verified.
Say what each step protects against and what it can still miss.

## How to read "how sure are we"
The evidence labels and access levels, with the fixed phrases, and which
kinds of studies count as stronger or weaker evidence here.

## What the evidence says
Same themes and order as the review's Findings. Each claim keeps its label,
numbers and citation link, and ends with a pointer to the review section it
explains.

## What we still don't know
The review's Gaps & caveats, explained: why each gap matters and, if the
review says so, what evidence would close it.

## Reading the evidence table and literature map
How to read the columns and the map, using one row or entry from this
review as a worked example.

## Changes since v<N-1>
Only if the review has this section: it, explained.

## Glossary
Alphabetical: every term defined above, a one-line definition, the link.

## About this companion
The log from step 5.
```

In generic mode, drop or rename sections the source has nothing for, and
never invent content to fill one.

## Guardrails

- Never edit the review, its sibling files, or an earlier companion.
- At most 3 subagents per run (drafter, checker, one re-check).
- No literature search and no opening of cited papers: if the review is
  wrong or thin, say so in the reply; fixing it is a job for
  `/academic-research`.
