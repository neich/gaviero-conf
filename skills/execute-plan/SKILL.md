---
name: execute-plan
description: Execute a plan autonomously, start to finish, without pausing to ask permission. Built for plans written by gated-plan (plans/<name>/<name>-v<N>.md, with steps, self-checks, independent gates and a Progress log); also runs other structured plans such as PLAN.md, a roadmap doc or a pasted plan. Resolves small deviations with the strongest default and logs them; stops only at hard stops, failed gates or genuine blocks; resumes from the last passed checkpoint. Use when the user asks to execute, run or implement a plan end-to-end, or invokes /execute-plan.
argument-hint: "[plan path | plan name]"
---

# Execute Plan

Run the whole plan in one continuous run and hand back a clean record. Asking before each step is a failure mode, not caution. Don't narrate progress in chat: the log holds it.

## 1. Find the plan

Plans written by `gated-plan` live at `plans/<plan-name>/<plan-name>-v<N>.md`. The latest version has the highest `N`, compared as a number (`-v10` beats `-v9`).

- **A file path:** run exactly that file. If a newer version exists, still run the named one and note it in the log.
- **A plan name or its folder:** run the latest version in `plans/<plan-name>/`.
- **A plan pasted or attached in chat:** use it directly.
- **Nothing named:** look in `plans/*/`. One plan folder: run its latest version. Several: ask which. No `plans/` folder: look for `PLAN.md`, `plan.md`, `IMPLEMENTATION_PLAN.md`, `ROADMAP.md` or similar; if there are several candidates or none, ask which.

When you have to ask, ask before doing anything else: starting on the wrong plan wastes the run.

Then read the whole plan before acting, and classify it:
- **Gated plan:** it has a `## Progress log` and gate sections (`### Gate M<n>`, `## Final gate`). Follow section 3.
- **Other plan:** anything else. Follow section 4.

## 2. Precedence

The plan file wins over this skill. Its executor instructions, execution model, `## Hard stops`, gates, retry limits and failure handling apply as written; this skill fills only what the plan leaves out. Where the plan is silent, the defaults below apply.

## 3. Gated plans

**Log.** Log only in the plan's own `## Progress log`. Never create a separate log file: a strict plan's hard stops may forbid it. Keep a `Status:` line at the top of the log (add it if missing) with one of `Not started`, `In progress`, `Blocked at <step>`, `Failed at <gate>`, `Complete`. Each version of a plan is its own file with its own log; a new version starts fresh.

**Start or resume.** Read the log first.
- No entries: set `Status: In progress`, log the start date and the file run, and begin at the first step.
- Checkpoints, or `Blocked at <step>`: confirm the files still match the last checkpoint (`git status`, `git diff --stat`, and the files that checkpoint lists). Then continue from the step after the last passed checkpoint, or from the blocked step. If the files don't match, that is a hard block.
- `Failed at <gate>`: resume only if the user asks. Then re-run that gate with a fresh retry budget.
- `Complete`: report that and do nothing.
- A failed plan review recorded by `gated-plan-strict`: hard block. Don't execute an unreviewed plan.

**Steps.** For each step, in order:
1. If the plan has `## Hard stops`, check the step against them. On a match, don't act: write a stop report (step, condition hit, what is needed to continue), set `Status: Blocked at <step>`, and end the run.
2. Make the change.
3. Run the step's self-check. On failure, read the actual error before changing anything, then fix and re-run, up to 2 attempts. Still failing: hard block.
4. Log one line with the self-check's actual result.

**Gates.** At each gate, spawn a fresh agent. Never evaluate a gate yourself, and never skip one. Give the agent only the plan file path, the gate's name and read access to the working directory. Never give it your transcript or reasoning. Tell it:

> Evaluate `<gate>` in `<plan path>`. Re-run every check yourself and trust no claim in the progress log. Do not modify files or run git write commands. Return PASS or FAIL per criterion with the command output or `path:line` behind it, mark anything you could not check as NOT RUN, and end with an overall PASS or FAIL.

Wait for the result.
- **PASS:** log a checkpoint: the gate, its evidence, and the files changed since the last checkpoint.
- **FAIL:** fix what failed and re-submit to a new fresh agent, up to the gate's `Max retries` (default 2). Still failing: write a failure report (criterion, evidence, attempts), set `Status: Failed at <gate>`, and stop. A crossed hard stop fails with no retry.

After the final gate passes, set `Status: Complete`.

## 4. Other plans

**Log.** Append a `## Progress log` section with a `Status:` line to the plan file. If the plan was pasted, write `plan_log.md` in the working directory instead.

**Steps.** Treat each phase, stage or numbered item as a step, in order. Run any check the plan gives. Where it gives none, choose a concrete check (a command and its expected result, a test, an observable), run it, and log it as your own choice. Same 2-attempt limit as section 3. There are no gates unless the plan defines them; if it does, run them as in section 3.

At the end, re-run every check against the final state before setting `Status: Complete`.

## 5. Deviations and hard blocks

The test: is there a low-risk default a competent engineer would confidently pick, or is this a call that belongs to the user? Anything the plan's hard stops cover is never a simple deviation.

**Simple deviation:** take the strongest default, log it, and continue.
- A file, function, API or dependency has a different name than the plan says, and the equivalent is obvious.
- A detail is underspecified and any reasonable choice meets the step's goal.
- A step fails because the plan's assumption is stale, and the fix is a straightforward adaptation, not a redesign.
- Two sub-steps can be reordered or merged without changing the outcome.
- Typos, missing boilerplate, or naming mismatches the plan clearly implies.

**Hard block:** stop, set `Status: Blocked at <step>`, log the blocker and what is needed, and report it.
- Interpretations differ materially and a wrong pick is costly to undo.
- Credentials, access or external resources are missing with no substitute.
- The plan contradicts itself or the codebase in a way that isn't a typo.
- The next step is destructive or irreversible and the plan doesn't authorize it.
- Continuing would mean a scope, budget or priority call that is the user's to make.

If independent steps remain after a block, say they could proceed, but don't reorder the plan without the user's confirmation.

Log a deviation as:

```
- Deviation: <what didn't match the plan>
  Resolution: <what you did instead>
  Why: <one line>
```

## 6. Versions

Use the versions the plan pins. Use context7 (if available) or the installed source only to read the API at that version. Never upgrade or swap a pinned dependency on your own; if a pinned version can't be used, that is a hard block unless the plan allows a change.

## 7. Git

The user handles branches and commits. Work in the current working tree and leave every change uncommitted. Never create or enter a worktree: no `git worktree`, no `EnterWorktree`, no `isolation: "worktree"` on subagents. Never run git commands that change state: `branch`, `checkout`, `switch`, `add`, `commit`, `stash`, `reset`, `restore`, `merge`, `rebase`, `cherry-pick`, `tag`, `pull`, `push`, or PRs. Read-only git (`git status`, `git diff`, `git log`) is fine. If the plan has a git step, skip it and log `Skipped — git left to user`, saying where a commit would naturally go.

## 8. Report

Report in chat only when the run ends: finished, blocked, or failed at a gate. Give the plan path and the final status; each gate's result with its key evidence; the deviations the user should review; and, if stopped, exactly what is needed to continue.
