---
name: "gated-plan-strict"
description: "Add-on to gated-plan: hard stop conditions plus an independent review of the plan before execution. Use only when the user asks for it or invokes /gated-plan-strict."
---

# Strict add-on for gated plans

Apply `gated-plan` in full, then add the two sections below.

## 1. Hard stop conditions

During the questioning rounds, ask the user for project-specific hard stops, proposing the defaults below as the recommended answer.

Defaults: the executor must stop, not attempt, when an action would:
- Delete or overwrite data outside the plan's listed files, or rewrite git history (force push, reset of pushed commits).
- Be irreversible outside the repo: deploys, migrations on shared databases, sending emails/messages, payments, publishing.
- Need credentials, secrets, or permissions not already provided.
- Touch anything listed in the plan's non-goals.
- Require a decision the plan does not specify.

In the plan file, add a `## Hard stops` section right after `## Constraints and non-goals`, listing every condition concretely (named paths, commands, services). Add to the executor instructions: before each step, check it against the hard stops; on a match, do not act, write a stop report in the progress log (step, condition hit, what would be needed to continue), and end the run.

Gate evaluators also check: no hard-stop condition was crossed. A crossing is FAIL with no retry.

## 2. Plan review gate

After writing the plan and before handing it over:

- Spawn a fresh agent given only the plan file and read access to the repo (not this conversation).
- It checks, returning PASS/FAIL with evidence per item:
  - Every path, identifier, API, and version in the plan exists or is explicitly marked as to-be-created.
  - Every step has a runnable self-check; every gate has mechanical criteria and a retry limit.
  - No step requires a judgment call or information missing from the plan.
  - Steps are in valid dependency order and self-contained.
  - Hard stops are concrete, not vague.
- On FAIL: fix the plan. If a fix needs information only the user has, ask the user. Re-run the review with a new fresh agent until PASS.
- Record the final review result at the top of the progress log.