---
name: "light-plan"
description: "Plan and implement a medium-complexity task in one run, evidence-first: short written plan, per-step checks, one final verification, no per-milestone gates. Milestones only when one prompt asks for separate independent pieces of work. Use for work too involved for a plain prompt (several files or dependent steps) but not worth gated-plan plus execute-plan, or when the user asks for a light or quick plan or invokes /light-plan."
---

# Light plan

The user's prompt gives the goal. Write a short formal plan, then implement it in the same run. The plan keeps the work honest and resumable; it is not a deliverable to polish.

## Evidence rules

These apply in every section below.

- **No guessing.** If a plan entry or claim depends on a file, read it; on runtime behavior, run it; on a library's API, check the installed version or docs, using Context7 if available, never memory. Do not invent function names, flags, paths, or config keys. Do not plan a bug fix before reading the failing code path or reproducing the bug.
- **Cite and label.** Cite evidence inline (`src/auth.rs:142`, command output, test results). Label claims when it matters: **verified** (read or ran it in this session), **inferred** (state the reasoning), **assumed** (say what would confirm it).
- **"Works" means ran.** "This works" or "this is fixed" requires having run it. After a change, try to falsify it. Report incomplete evidence as incomplete, and a check you could not run as not run.
- **No blanket hedging.** State verified facts plainly. Confidence tracks the evidence.

## 1. Check the fit

Read the code involved first, then choose:

- **Too small** (one obvious change, no dependent steps): skip the plan and just do it. The evidence rules still apply.
- **Fits**: up to 8 steps, one coherent goal, every step verifiable from this working directory. Continue with a flat list of steps.
- **Independent goals**: the user's prompt asks for separate pieces of work, each its own dependency graph with no step needing another's result, for example two unrelated features in one prompt. Use one milestone per goal, up to 3 milestones with up to 8 steps each.
- **Too big** (a single goal needing more than 8 steps, more than 3 independent goals, or a migration or other change that is hard to undo): stop, say why, and recommend `gated-plan`. Do not start.

Milestones are the exception. Never use them to divide one goal into phases or to fit a large task under the step limit. If any step of one goal depends on another goal's result, it is one dependency graph: treat it as a single goal.

## 2. Settle doubts in one round

- Verify everything you can before writing the plan: paths, signatures, conventions, library APIs.
- Ask only what changes the outcome and that you cannot verify. Ask once, with all questions together, each carrying your recommended answer.
- Anything smaller becomes a labeled assumption in the plan, with what would confirm it. Do not ask about it.

## 3. Write the plan

Write to `plans/<plan-name>/<plan-name>-v<N>.md`, relative to the repo root. `<plan-name>` is short kebab-case; the folder and file share it. Start at `-v1`. Revising an existing plan means the next `N` beside it, never overwriting. Never write into another plan's folder.

```markdown
# <Goal>

Files to read first: <paths>
Evidence: <verified facts the plan relies on, each with path:line or command output>
Assumptions: <default chosen instead of asking; what would confirm it>
Non-goals: <what not to touch or refactor>

## Steps

### 1. <imperative title>
Files: <paths>
Change: <exactly what: identifiers, signatures, config keys>
Check: <command + expected result, test, or concrete observable>

### 2. ...

## Final check
- [ ] <mechanical criterion + how to check>
- [ ] Falsification: <the input, edge case, or negative test most likely to break the change>
- [ ] Full test/build command for the touched code: <command>
- [ ] Non-goals untouched: `git diff --stat` (if a git repo) lists only the planned files

## Progress log
<!-- Status: In progress / Complete / Blocked at <step>. One line per step with the check's evidence; deviations with why. -->
```

With independent goals, replace `## Steps` and `## Final check` with one `## Milestone <n>: <goal>` per goal. Each holds its own steps, numbered `<n>.1`, `<n>.2`, and its own `### Check M<n>` with the same items as the final check. Add a final `## Final check` only for what the goals share, such as the full build.

Leave out time estimates, motivation, and explanation. Every identifier in the plan was read in the repo, or is new and marked as new. If a step can't be written concretely, a decision is still open: settle it under section 2.

Tell the user the path, then start implementing without waiting for approval. If the user asked for a plan only, stop here.

## 4. Execute

Work through the steps in order, one at a time, in the current working directory.

1. Make the change.
2. Run the step's check. On failure, read the actual error before changing anything, then fix and re-run, up to 2 attempts. Still failing: treat it as a hard block.
3. Add one line to the progress log with the check's actual result, so a later session can resume from the last completed step.

If the plan's progress log already says `Blocked at <step>`, resume from that step, after confirming the logged state still matches the files.

Do not pause between steps or narrate progress.

**Deviations.** If a low-risk default is obvious (a renamed file, a stale assumption with a straightforward fix, an underspecified detail, harmless reordering), take it, log it with a one-line reason, and continue.

**Hard blocks.** Stop, set the status to `Blocked at <step>`, log what is needed, and report it when:

- Interpretations differ materially and a wrong pick is costly to undo.
- Credentials, access, or external resources are missing with no substitute.
- The plan contradicts itself or the codebase, or fixing the problem means redesigning it.
- The next step is destructive or irreversible and the plan doesn't authorize it.
- Continuing would change scope or touch a non-goal.

With milestones, a hard block stops only its own milestone. Log it, continue with the next milestone, and report the block at the end.

**Version control.** Leave all changes uncommitted; the user handles branches and commits. No worktrees, no parallel agents, no git write commands of any kind. Read-only git (`git status`, `git diff`, `git log`) is fine. Skip any git step and log it.

## 5. Final check

Re-run every item in the final check (with milestones, each `Check M<n>` when that milestone ends) yourself, against the actual files, and compare the diff with the plan. Do not reuse earlier output: run it again. Fix failures with the same 2-attempt limit.

Spawn one fresh agent for this check, instead of doing it yourself, only if the change touches authentication, permissions, secrets, persistence formats, or concurrency, if a deviation altered a step's design, or if the user asked for independent verification. With milestones, this is decided per milestone. Give it only the plan file and read access to the repo, and tell it: re-run each check itself, trust no claim in the progress log, do not modify files, and return PASS/FAIL per criterion with the command output or `path:line` behind it, marking anything it could not check as NOT RUN.

Before reporting, strike or flag any sentence you can't defend by pointing at something concrete from this session.

Then set the status and report to the user: what changed, the final check results with the evidence, anything not run or still only assumed, and any deviations they should review.
