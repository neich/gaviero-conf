---
name: finish-stage
description: Close out a research, implementation, simulation or test stage by writing its results in the shape the explain-stage skill consumes — a five-section report.md and a validated manifest.json (metrics with units and sources, artifacts with roles and column meanings, decisions, and the highlights worth explaining). Use whenever a stage, step, run, sweep or experiment is finished and the user asks to write up, close, finish, summarise, or record its results — even if they do not mention a manifest, a report, or the explainer.
---

# Finish a stage

You are ending a stage whose results will later be turned into an explainer by someone who was not there. Write the results in a shape a script can read, and do not declare the stage finished until the validator passes.

## The validator script

This skill's files live in the global skills folder, not in the current project, so relative paths like `scripts/…` do not resolve. Always run the script by its absolute path:

```
python "$GAVIERO_ROOT/.gaviero/skills/finish-stage/scripts/finish_stage.py" <args>
```

Below, `finish_stage.py` means that full command. If `$GAVIERO_ROOT` is unset, tell the user and stop; do not search the disk for the script.

## Input: the brief

The user gives a sentence or short paragraph with: the stage id and what it set out to do; the stage directory where `report.md` and `manifest.json` go; and the files to read — plans, logs, notebooks, result tables, database, anything the results should be drawn from. Example:

> Finish F1 step 3, the throughput sweep over five scenarios; goal was to find which fit the 60 min wall-clock budget. Stage dir `runs/f1/step3`. Read `runs/f1/step3/plan.md`, `runs/f1/step3/theta.csv` and the `scenarios` table in `runs/f1/step3/run.db`.

Only the named files are inputs; if you ran the stage yourself in this session, your own context counts too, but every number you write still has to exist in a file, because the validator checks it. If the brief names no stage dir or no files, ask; do not guess. Record the brief verbatim in the manifest's `brief` field.

## What to write, in the stage directory

**`report.md`** — exactly these H2 sections (say "none" rather than omit one):

```markdown
# <stage id> — <title>
## Goal
## What was done
## Results
## Decision
## Open issues
```

Every number that matters goes in *Results* with its unit and the file it comes from. Tables are welcome. Prose that repeats the manifest is fine; prose that contradicts it is a bug.

**`manifest.json`** — same content, machine-readable. Print the exact JSON schema with `finish_stage.py --schema` before writing it:

- `metrics`: one entry per number a reader should know. `value` + `unit` + `source` file, `meaning` in one sentence, and `budget` whenever the number is judged against a threshold. The explainer draws that threshold; without it the reader sees a number and not a verdict.
- `artifacts`: every data file, with `role` and, for tables, `columns` (name → meaning and unit). An unexplained column will be misread later.
- `decisions`: what was decided and `because` of which metric ids.
- `highlights`: 3–6 points, in the order you would explain them to a colleague. **Each becomes one explainer step**, so make each a single claim and attach the metric and artifact ids it rests on. This is the one field only you can fill well: the explainer will not re-derive what mattered.

Keep the manifest small; it is a table of contents for the data, not a copy of it.

## Validate, then finish

```
python "$GAVIERO_ROOT/.gaviero/skills/finish-stage/scripts/finish_stage.py" <stage-dir>
```

It checks the report headings, the manifest against the schema, that every metric source exists and contains the stated value, that every referenced file and id resolves, and that every artifact file exists. Fix every `FAIL`; the stage is not finished until it prints `PASS`. Report the stage dir and the highlights list back to the user.
