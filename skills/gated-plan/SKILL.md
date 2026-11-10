---
name: "gated-plan"
description: "Use instead of implementation-plan for any plan an AI agent will execute unattended: questions the user first, then writes a plan with independent-agent gates."
---

# Gated plans for unattended AI execution

The user's prompt gives the goal. Produce a plan a frontier AI model can execute start to finish without a human, verified by independent agents. Code is the main case; the same rules apply to research, docs, or data work.

## 1. Resolve every doubt before writing

- Interview the user about anything you cannot verify yourself, relentlessly, until you share an understanding of every decision the plan needs. Ask as many questions as needed.
- Walk the design tree: settle the root decisions first, then the decisions that depend on them, one branch at a time. Batch questions only when their answers are independent of each other; later questions build on earlier answers.
- Each question carries your recommended answer.
- If the codebase or the tools under "Verification resources" can answer a question, explore instead of asking.
- Do not draft the plan until every branch is resolved. Then summarise the decisions in a few lines and have the user confirm the summary. An unresolved doubt in the plan becomes a guess during execution.
- Verify facts before they enter the plan: read the repo for paths, signatures, conventions; check installed versions/docs for APIs. Anything you can't verify becomes a question, not an assumption.

### Verification resources

Verify with tools before asking the user: every fact checked is one question fewer. Use only tools that are actually in your tool list, and never assume one exists.

- **Repo:** gaviero `repo_outline` and `node_doc` for structure and signatures; `symbol_refs` for callers and callees; `blast_radius` for what a change affects and which tests cover it. Use them to write non-goals and to pick the commands for self-checks. Use `memory_search` for earlier decisions and gotchas, and treat its results as leads to confirm in the code.
- **Libraries:** find the installed version in the lockfile or manifest. Then read the API at that version: context7 (`resolve-library-id`, then `query-docs`), or the installed source (`node_modules`, site-packages, `~/.cargo/registry`, vendored code). Never pin a version or an API from memory.
- **Known issues:** WebSearch and WebFetch for deprecations, breaking changes and open bugs in the pinned versions (changelogs, release notes, issue trackers). A claim counts only if you opened the page; a search snippet is a lead. Never put secrets or private code in a search query.
- **Large repos:** before drafting, you may launch read-only explorer subagents in parallel, one per area, to gather facts. This is plan authoring; the no-parallel-agents rule in the execution model applies to execution only. Open each fact an explorer reports yourself before it enters the plan.
- **Literature:** if a milestone depends on what published research says, run `/deep-research` first and have the plan cite its report. Don't research the literature inside this skill.

The verification is done when every path, identifier, version and API in the plan was read in this session; everything else is a question for the user.

## 2. Write for the AI executor

It runs in a fresh session with no memory of this conversation.

Cut: time estimates, effort sizing, motivation, tutorials, "familiarize yourself" steps.

State exactly:
- File paths, identifiers, signatures, types, config keys.
- Existing files to use as style reference and what to copy from them.
- Library names with pinned versions and the real API to use.
- Step order by dependency.
- Non-goals: what not to touch or refactor.

Each step is self-contained: repeat identifiers rather than "the function from earlier". If a step can't be written concretely, a decision is still open: go back to section 1.

Execution model (state it in every plan):
- All milestones, steps and gates run sequentially, one at a time, in the current working directory. No parallel agents, no git worktrees, no isolated copies of the repo.
- No git write actions: no branch, checkout, commit, tag, stash, reset, merge, rebase or push. The user handles branching, commits and pushes manually. Read-only git (`git status`, `git diff`, `git log`) is allowed for self-checks and gates.

## 3. Verification and gates

- **Every step** has a self-check the executor runs: command + expected result, test that must pass, or concrete observable.
- **Each milestone and the end** have an independent gate:
  - Run by a fresh agent given only the gate spec and the artifacts (files, repo state). Never the executor's transcript or reasoning.
  - The evaluator works on the same working directory (no worktree), runs while the executor waits, and does not modify files.
  - The spec lists mechanical pass criteria; the evaluator re-runs checks itself and returns PASS/FAIL with evidence per criterion.
  - Write criteria the evaluator can decide without judgment calls or asking anyone.
- **On FAIL**: executor fixes and re-submits, up to the retry limit set per gate (default 2). Still failing: stop, write a failure report in the progress log (criterion, evidence, attempts), no further milestones.
- **On PASS**: record a checkpoint in the progress log (milestone, gate evidence, files changed) so a fresh session can resume from it. No git commit, tag or snapshot.

## 4. Output

### Where the plan goes

Always write the plan to this path, relative to the repo root:

```
plans/<plan-name>/<plan-name>-v<N>.md
```

- **`<plan-name>`**: choose a short kebab-case name for the goal (lowercase
  letters, digits and hyphens, e.g. `auth-token-refresh`). Use the user's
  name for the plan if they give one. The folder and the file share this name.
- **New plan**: write version `-v1`, e.g.
  `plans/auth-token-refresh/auth-token-refresh-v1.md`. Create
  `plans/<plan-name>/` if it doesn't exist. If the folder already exists for a
  different goal, pick another name. Never write into another plan's folder.
- **Evolving a plan**: when an existing plan is revised, write the next version
  next to it (`-v2`, `-v3`, …). Find the highest existing `N` in the folder
  and add 1. Never overwrite or delete earlier versions. Start the new version
  with a `Supersedes: <plan-name>-v<N-1>.md` line and a short summary of what
  changed.
- Tell the user the exact path you wrote, and that `/execute-plan <path>` runs it.

The plan uses this shape:

```markdown
# <Goal>

## Context
Paths involved, files to read first, current state.

## Constraints and non-goals
Sequential execution in the current working directory; no worktrees, no parallel agents, no git write actions (branching, commits and pushes are done manually by the user).

## Milestone 1: <name>
### Step 1.1: <imperative title>
Files: <paths>
Change: <exactly what>
Self-check: <command / test / observable>

### Gate M1
Evaluator receives: <artifacts>
Pass criteria:
- [ ] <mechanical criterion + how to check>
Max retries: <n>
On pass: log checkpoint `M1` in the progress log

## Milestone 2: ...

## Final gate

## Progress log

Status: Not started

<!-- Executor appends: step done, gate results with evidence, checkpoints, failure report. A fresh session resumes from the last passed gate. -->
```

Executor instructions at the top of the file: run with `/execute-plan <this file's path>`; run steps in order, one at a time, in the current working directory; run each self-check; spawn the gate evaluator at each gate and wait for its result; log everything; never skip a gate; never create worktrees or run git write commands.