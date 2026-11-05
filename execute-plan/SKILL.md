---
name: execute-plan
description: Execute a long, multi-phase or multi-stage implementation plan autonomously, start to finish, without pausing between steps to ask permission. Use whenever the user hands over a structured plan (phases, stages, milestones, a roadmap doc) and asks Claude to build it, implement it, "just run it," or execute it end-to-end. Small deviations from the plan (missing details, outdated references, minor conflicts) get resolved with the strongest reasonable default and logged, not escalated. Execution only stops for genuine hard blocks — missing access, irreversible actions, or choices only the user can make. Produces a plan_log.md recording every deviation and how it was resolved.
---

# Execute Plan

The user wants autonomous execution of a plan. Treat "check in before each phase" as a failure mode, not caution. The value of this skill is finishing the whole plan in one continuous run and handing back a clean record of what happened, not a string of "should I proceed?" messages.

## Inputs

- **Plan file:** the user should point you at the file containing the plan (e.g. "execute the plan at docs/rollout-plan.md"). If they pasted the plan inline or attached it instead of naming a path, use that directly.
- **Versioned plans.** Plans are normally stored as `plans/<plan-name>/<plan-name>-v<N>.md`, which is what `gated-plan` writes. The latest version of a plan is the file with the highest `N`, compared as a number (so `-v10` beats `-v9`). Resolve what the user refers to like this:
  - A specific file (e.g. `plans/auth-token-refresh/auth-token-refresh-v2.md`): use exactly that file. If a newer version exists, still run the named one, and note in the log that a newer version exists.
  - A plan name (e.g. "execute auth-token-refresh") or its folder: use the latest version in `plans/<plan-name>/`.
- If no plan is referenced at all, look in `plans/*/` first:
  - Exactly one plan folder: use its latest version.
  - Several plan folders: ask which plan.
  - No `plans/` folder: look for an older-style candidate in the working directory (`PLAN.md`, `plan.md`, `IMPLEMENTATION_PLAN.md`, `ROADMAP.md`, or similar). If several candidates exist, or none do, ask which file.

  In all these cases, ask before doing anything else. This is the one point where confirming first is worth it, since starting on the wrong plan wastes the entire run.
- **Log file.** For a versioned plan, the log is `plan_log-v<N>.md` in the plan's folder, matching the version being run. Logs from earlier versions are left alone. For any other plan, the log is `plan_log.md` next to the plan file. Wherever this skill says `plan_log.md`, it means this file.
- If that log already exists and its `Status` says `Blocked at Phase X`, treat this as a resume: pick up from that phase instead of starting over. A log from a different version is never a resume point. A new version starts fresh.

## Before starting

Read the entire plan first, not just the current phase — later phases often depend on choices made early on, and you want to know that before phase 1. Then create the log file (see Inputs; at the project root if the location isn't obvious) with the plan's path, including its version, and a phase list, and update it as you go — not just at the end. If the session is interrupted, the log should still reflect real progress.

## Version control: hands off

The user handles all branching and commits manually. Work directly in the current working tree and leave every change uncommitted.

- Never create or switch into a git worktree: no `git worktree`, no `EnterWorktree`, no `isolation: "worktree"` on subagents.
- Never run git commands that change repository state: no `branch`, `checkout`, `switch`, `add`, `commit`, `stash`, `reset`, `restore`, `merge`, `rebase`, `cherry-pick`, `tag`, `pull`, `push`, and no PRs (`gh pr ...`). Read-only inspection (`git status`, `git diff`, `git log`) is fine.
- If the plan includes a git step (e.g. "create a branch", "commit after phase 2", "open a PR"), skip it, don't treat it as a hard block, and log it in `plan_log.md` as `Skipped — git left to user`, saying where a commit or branch boundary would naturally go.

## The execution loop

For each phase/stage, in order:

1. Execute it fully.
2. If something doesn't match the plan exactly, classify it (below), resolve it, log it if it was a real deviation, and continue immediately — no need to narrate the decision to the user mid-flight, it's in the log.
3. If it's a hard block, stop there (see below).

## Simple deviation vs. hard block

The dividing line is: **is there a low-risk default a competent engineer would confidently pick, or does this require a judgment call that belongs to the user?**

**Simple deviation — resolve with the strongest recommendation and keep going:**
- The plan references a file, function, API, or dependency that doesn't exist under that exact name, but an obvious equivalent does
- A parameter, config value, or detail is underspecified, and any reasonable choice satisfies what the phase is actually trying to accomplish
- A step fails because an assumption in the plan is stale (e.g., a library version, a schema shape), and the fix is a straightforward adaptation, not a redesign
- Two sub-steps could be reordered or merged without changing the outcome
- Typos, missing boilerplate, or naming mismatches the plan clearly implies

**Hard block — stop and ask:**
- Multiple reasonable interpretations would lead to materially different outcomes, and picking wrong is costly or awkward to undo
- Required credentials, access, or external resources are missing with no substitute
- The plan contradicts itself, or contradicts the existing codebase/environment, in a way that isn't a simple typo
- The next step is destructive or irreversible (deleting data, dropping a table, spending real money) and the plan doesn't clearly authorize it
- Continuing would mean making a scope, budget, or priority call that's the user's to make, not the agent's

When a hard block hits: stop, record it in `plan_log.md` as unresolved, and report the blocker plus exactly what's needed to clear it. If other, genuinely independent phases remain, note that they could proceed in parallel, but don't restructure the plan's order on your own judgment — confirm first.

## plan_log.md format

Keep entries short and skip phases with nothing to report:

```markdown
# Plan Execution Log

**Plan:** <path, e.g. plans/auth-token-refresh/auth-token-refresh-v2.md>
**Started:** <date>
**Status:** In progress / Complete / Blocked at Phase X

## Phase 1: <name>
- Deviation: <what didn't match the plan>
- Resolution: <what you did instead>
- Why: <one line>

## Phase 2: <name>
No deviations.

## Phase 3: <name> — BLOCKED
- Blocker: <what stopped execution>
- Needed: <what input or decision would unblock it>
```

## Tone

Don't ask for confirmation before each phase, file, or command. Don't stop to summarize progress unless you've hit a hard block or finished the whole plan. Brief status is fine in `plan_log.md`; it doesn't need to be repeated to the user in chat until there's something they actually need to act on.

Use MCP server contetx7 (if available) to get the most current version of libraries and artifacts used in the plan.