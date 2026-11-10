---
name: deep-solve
description: All-resources problem solving for hard codebase tasks — bugs that resist a first look, cross-cutting changes, unfamiliar subsystems, "why does X happen" questions that need wide exploration. Spends freely on parallel subagents, code-graph and memory MCP tools, docs lookups (context7), web search/fetch and any other configured MCP server, then converges on a verified fix or answer. Use when the user asks to go all out, dig deep, use everything, or when a problem clearly needs broad exploration before it can be solved. Invoke as /deep-solve [quick:|deep:] [key=value ...] <problem>.
argument-hint: "[quick:|deep:] [agents=N waves=N web=on|off mode=fix|diagnose] <problem>"
---

# Deep Solve

Treat `$ARGUMENTS` as the problem. Use as many resources as the problem
needs: parallel explorers, every useful tool, external docs and issue
trackers. Then converge on **one** solution and verify it.

The loop: frame → orient → explore in parallel → converge → solve → verify → report.

## Parameters

Parse `$ARGUMENTS` as `[quick:|deep:] [key=value ...] <problem>`.

1. **Tier.** A leading `quick:` or `deep:` selects that tier. Otherwise use
   **standard**.
2. **Overrides.** Leading `key=value` tokens with a known key override the
   tier preset. Ignore unknown keys or bad values, and say so in the plan.
3. **Clamp** every value to its hard cap.

| Knob     | Meaning                                                   | quick | standard | deep  | Hard cap |
|----------|-----------------------------------------------------------|-------|----------|-------|----------|
| `agents` | Max explorer subagents across all waves                   | 2     | 5        | 10    | 14       |
| `waves`  | Exploration waves (later waves target open hypotheses)    | 1     | 2        | 3     | 4        |
| `web`    | Allow WebSearch/WebFetch and remote MCP servers           | on    | on       | on    | —        |
| `mode`   | `fix` = change code and verify; `diagnose` = answer only  | fix   | fix      | fix   | —        |

If the problem is a question ("why…", "how does…", "where…"), the default
`mode` is `diagnose`. An explicit `mode=` always wins.

Show the effective parameters in the plan.

## Evidence standard (applies `evidence-first`)

- **Read it or run it.** A claim about code needs a file:line. A claim about
  behaviour needs output you produced in this run. A claim about a library
  needs its docs or source *at the installed version*.
- **Explorer reports are leads.** Before building on a subagent's claim,
  open the cited file:line yourself. Pay particular attention to the claims
  the fix depends on.
- **Label claims** that aren't obvious: **verified**, **inferred** (say why),
  **assumed** (say what would confirm it).
- **"Fixed" means it was run.** You can say "fixed" only after reproducing
  the failure, applying the change, and seeing the same check pass.

## Resources (use what is actually in your tool list)

Check your real tool list before planning. Never assume a tool exists. Map
what you have to these roles:

| Role | Tools (examples) |
|---|---|
| **Orient** | gaviero `repo_outline`, `memory_search`, `node_doc`; `git log`/`git blame` via Bash |
| **Navigate code** | Grep, Glob, Read; gaviero `symbol_refs` (callers/callees), `blast_radius` (dependents, missing tests) |
| **Run** | Bash: build, tests, repro scripts, `--help` of installed CLIs |
| **Library docs** | context7 `resolve-library-id` → `query-docs`; installed source (vendored deps, `~/.cargo/registry`, `node_modules`, site-packages) |
| **Outside world** | WebSearch, WebFetch (issue trackers, changelogs, RFCs, forum threads); any other configured MCP server whose tools fit |
| **Parallelism** | `Agent`/`Task` subagents; otherwise many independent tool calls in one message |

- **No subagent tool?** Do the lanes yourself. Batch independent
  Grep/Read/MCP calls into the same message so they run in parallel. Say in
  the plan that subagents are unavailable.
- **`web=off`:** use only local tools and context7.

## Procedure

1. **Frame.** Restate the problem in one or two lines. Then state:
   - what "solved" means: the observable success check;
   - the constraints.

   Ask up to 3 clarifying questions, once and all together, **only** if a
   wrong guess would waste the run. Otherwise go.

2. **Orient (cheap, before spending).** Spend a few calls getting the lay of
   the land:
   - `repo_outline` and `memory_search` on the problem's keywords (earlier
     decisions and gotchas);
   - recent `git log` on the suspect area;
   - locate the entry points;
   - if `mode=fix` and the bug is reproducible, **reproduce it now** and
     keep the exact command.

   If this is already enough to solve it confidently, skip to step 5 and
   say so. Don't burn a parallel run on an easy problem.

3. **Plan.** Write the plan in a few lines:
   - 2–4 candidate **hypotheses** or solution approaches;
   - the exploration **lanes**;
   - the effective parameters and the resources available.

   Lanes should be disjoint, each with a concrete question. Pick from:
   - *Code path*: trace the flow from entry point to symptom. Callers and
     callees, data shape at each hop.
   - *Blast radius*: what else depends on the code you'd change? What tests
     cover it? What would break?
   - *History*: `git log -S`/`-L`, `git blame`. When did the behaviour
     change, and why (commit messages, linked issues)?
   - *Library/runtime*: the dependency's real behaviour at the installed
     version (context7, its source, its changelog).
   - *Outside world*: upstream issues, known bugs, errata, prior fixes for
     the same error message (WebSearch → WebFetch the primary page).
   - *Alternatives*: how the codebase already solves a similar problem
     elsewhere, so the fix follows local convention.

4. **Explore (parallel).** Launch one subagent per lane in a **single
   message**, so they run concurrently, up to `agents` in total. Use
   `Explore` for read-only code lanes. Use `general-purpose` for lanes that
   need web or MCP tools (it inherits them).

   Each subagent prompt is its lane question plus this block:

   > Context: <problem statement + key file paths found in orient>.
   > Investigate only this lane. Read-only: do not edit, write, or create
   > files; do not run commands that modify state (no installs, no git
   > writes, no deletes). Use any read tool, MCP server, docs lookup or web
   > source that helps. Return ≤600 words:
   > (1) direct answer to the lane question;
   > (2) evidence as bullets, each with `path:line`, command + output
   > excerpt, or URL;
   > (3) what this implies for these hypotheses: <list>;
   > (4) what you could not verify.
   > Report only what you actually read or ran — never memory. Say "not
   > found" rather than filling a gap.

   **Between waves** (`waves` > 1):
   - Update the hypothesis table: hypothesis → supporting and contradicting
     evidence → status.
   - Launch the next wave only at what is still open, contradictory or
     load-bearing-but-unverified, within the remaining `agents` budget.
   - Stop early once one hypothesis is confirmed and the rest are ruled out.

5. **Converge.** Pick the solution and say why. Cite the evidence that
   confirms it and what rules out the alternatives. Before going further,
   personally re-open the file:line evidence the fix depends on.

   If no hypothesis survives, go back to step 4, as long as budget remains.
   If none remains, report honestly (see step 7).

6. **Solve and verify** (`mode=fix`).
   - **Single writer.** Only you edit files, never a subagent.
   - Make the smallest change that solves the problem, following local
     conventions found in the *Alternatives* lane.
   - Re-run the reproduction from step 2: it must now pass.
   - Run the tests around the blast radius, plus build/lint for the touched
     crate or package.
   - Add a regression test when the codebase has tests for that area.
   - Try to falsify the fix: edge cases, the other callers found by
     `symbol_refs`/`blast_radius`.
   - If verification fails, return to step 5 with the new evidence. Never
     report a fix whose check didn't pass.

7. **Report** in chat. Keep it short and evidence-labelled:
   - **Answer / fix:** what was wrong, or what the answer is (file:line).
   - **Change:** files touched and why (`mode=fix`).
   - **Verification:** the commands you ran and their results, failing →
     passing.
   - **Ruled out:** the alternatives and the evidence against each, one line
     apiece.
   - **Open:** what remains unverified or risky, and what would settle it.
   - **Spend:** lanes, agents and waves used.

## Guardrails

- **Budget.** Never exceed `agents` or any hard cap. One subagent per lane,
  never one per search. More budget buys coverage of distinct questions,
  not duplicate digging.
- **Subagents are read-only.** All edits happen in step 6, by you, after
  converging.
- **Respect the permission policy.** Don't try to get around denied commands
  or blocked paths. If a lane needs something blocked, report it under
  **Open**.
- **Never send secrets, credentials, or private code** to web search or
  external MCP servers. Search with error messages and public identifiers
  only.
- **Cite external evidence by URL.** A web source supports a claim only if
  it was fetched. A search snippet is a lead, not evidence.
- **Don't widen the problem.** Note unrelated bugs or smells under **Open**;
  don't fix them.
