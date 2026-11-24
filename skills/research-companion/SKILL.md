---
name: research-companion
description: Writes a plain-language companion to a technical research document, for a reader at the level of a first- or second-year PhD student who is new to the topic. It reads the target document and the references the document contains (linked files, cited papers and pages) where they are needed to explain it. It defines every term before use, keeps the document's numbers, hedges and certainty labels exactly, and adds checked links to background reading. The document is never edited; the companion is a new file beside it. Invoke with /research-companion <path to document>.
argument-hint: "<path to document>"
allowed-tools: Task, Read, Write, Edit, Glob, WebFetch, Bash
---

# Research Companion

Treat `$ARGUMENTS` as the path of the document to explain. If it is missing
or does not exist, ask for it and stop.

Write a companion that lets a first- or second-year PhD student understand
the document without making it less accurate. Readers like this know how
research works in general, but not this topic, its jargon or its methods.
When plain words are not enough, explain more: add a definition, an example,
or a link. Never drop the precise statement.

## Sources

- **The document** is the source of every claim the companion makes about
  its subject: findings, numbers, conclusions, recommendations and caveats.
- **The references it contains** are the local files it links to, and the
  papers, pages and DOIs it cites. Open one only when you need it to explain
  something the document leaves unexplained: a term, a method, a number, a
  step in an argument. Use relative links as local files, and fetch URLs
  and DOIs with WebFetch.
  - Anything you take from a reference is labelled as coming from it:
    "(from [the cited paper](url))". It is never presented as a finding of
    the document.
  - If a reference contradicts the document, do not fix the document. Add a
    visible *Note:* that points to both places.
- **Background knowledge** may be used only for textbook definitions (what a
  confidence interval is, what a DAG is), never for claims about the
  document's subject.
- Keep a list of every reference you opened, and what you used it for.

## Writing rules

**Accuracy**
- Keep every number, unit, hedge ("may", "in one study", "n=1") and
  certainty label the document uses. Show a label in italics, and explain
  it in plain words at its first use.
- Keep each result tied to the population, setting, system and period the
  document gives. Write "in 3 trials with adults, X reduced Y", not
  "X reduces Y".
- Keep the document's distinctions between findings and proposals, between
  checked and unchecked claims, and between what a source says and what the
  document infers.
- Add no judgement ("large", "clearly", "proves") and no cause or purpose
  that the document does not state. If an explanation of your own helps,
  mark it *(explanation, not from the document)*.
- If the document disagrees with itself, keep both versions and add a
  visible *Note:* pointing to both passages.
- Keep the document's citation links attached to the same claims.

**Plain language**
- Define every technical term, abbreviation, method name and statistic at or
  before its first use, using only everyday words or terms already defined.
- At its first use, say what each number measures: the metric, the unit, and
  what it is compared with. If the document does not say, write that it does
  not say.
- At the first mention of a named paper, system, dataset or organisation,
  say in one line what it is.
- Write short sentences, one idea per paragraph. Give an example or analogy
  for each hard concept, and say where the analogy breaks down.
- When a step of the document's reasoning is missing, say that it is
  missing. Do not fill it in.
- Tables and small diagrams are welcome when every cell comes from the
  document or its references.

## Background links

Link a concept at its first use when a good page exists, and again in the
Glossary. Prefer English Wikipedia, then official documentation, then a
stable reference work. Never link a URL you have not checked.

- **Wikipedia:** check titles in batches of up to 20:
  ```bash
  curl -s -A "research-companion/1.0" -G "https://en.wikipedia.org/w/api.php" \
    -d action=query -d format=json -d redirects=1 \
    -d "prop=extracts|pageprops" -d ppprop=disambiguation \
    -d exintro=1 -d explaintext=1 -d exsentences=1 -d exlimit=20 \
    --data-urlencode "titles=<T1>|<T2>|…"
  ```
  (Without Bash, use WebFetch on the same URL.)
  - Drop a title that is missing, is a disambiguation page, or whose first
    sentence describes a different concept.
  - Link the final title after redirects, as
    `https://en.wikipedia.org/wiki/<Title>`, with spaces written as `_` and
    `(` `)` as `%28` `%29`.
- **Other pages:** open each one once, and check that it loads and is about
  the term.

## Companion template

```markdown
# Understanding "<document title>"

*Companion to [<file name>](<relative path>) · <YYYY-MM-DD> · for readers new to this topic. It explains the document and adds no findings of its own; where the two differ, the document is right.*

## The short version
5–10 short sentences in everyday words: the question, the answer, how sure
the document is, and the main caveat.

## Key ideas you need first
The concepts the rest depends on, each defined (with a link), ordered so
each builds only on the ones before it.

## How the work was done
The method in plain steps, with the document's own numbers, and what each
step can and cannot catch.

## What the document found
Follow the document's own order. Each claim keeps its label, its numbers and
its citation, and ends with a pointer to the section it explains:
*(→ document: <section>)*.

## What is still open
The caveats, disputes and open questions the document gives.

## Glossary
Alphabetical: every term defined above, with a one-line definition and its
link.

## References used for this companion
The references you opened, and what each one was used for.
```

Leave out any section the document has nothing for.

## Procedure

1. **Read** the document completely.
2. **Gather.** List the references the document contains, and open the ones
   needed to explain it (see Sources).
3. **Write** the companion to `<document name without extension>-companion.md`
   beside the document. If that file exists, use `-companion-2.md`,
   `-companion-3.md`, and so on. Never overwrite a file, and never edit the
   document.
4. **Check (fresh subagent).** Spawn one `general-purpose` subagent that sees
   only the two files and the reference list. If no subagent is available,
   do this pass yourself and say so in the reply.

   > Read the companion `<companion>`, then the document `<document>`. You may
   > open the references listed in the companion's last section. Report, with
   > line numbers:
   > (1) claims about the subject that the document does not make, or that
   > drop a number, hedge, label or scope the document gives;
   > (2) content from a reference that is not marked as coming from it;
   > (3) terms, abbreviations or numbers used before they are explained;
   > (4) places where a newcomer would get lost, and what would help.
   > Write nothing.

5. **Fix** each reported problem with the smallest edit. Narrow or delete
   wrong claims; never fix one by adding a new claim. Check any new link.
6. **Reply** with the companion's path, the references opened, the problems
   the check found and how they were fixed, and anything left unresolved. Do
   not paste the companion.
