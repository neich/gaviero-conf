---
name: explain-stage
description: Build a plain-language, interactive, step-by-step HTML explainer (Quarto + Observable JS) for the results of one finished research / implementation / test stage, from its report.md + manifest.json plus any extra data files the user names, with a deterministic script driving the steps and a gate that verifies nothing shown was invented. Use whenever the user asks to explain, visualise, walk through, or make a companion / explainer / infographic / animation for a stage, step, run, sweep, experiment or set of results — even without the words "Quarto" or "explainer" — and when they ask to redo, fix or improve one step of an existing explainer.
---

# Explain a stage

Deterministic parts (step plan, file snapshot, page assembly, navigation, caption panel, verification) are done by the `explainer.py` script. You do the creative part: one slide at a time, with full freedom over the visual.

## The script

This skill's files live in the global skills folder, not in the current project, so relative paths like `scripts/…` do not resolve. Always run the script by its absolute path:

```
python "$GAVIERO_ROOT/.gaviero/skills/explain-stage/scripts/explainer.py" <command> …
```

Below, `explainer.py` means that full command. If `$GAVIERO_ROOT` is unset, tell the user and stop; do not search the disk for the script.

## Input: the brief

The user gives a sentence or short paragraph saying what the stage did and where the results are: the stage directory (which holds `report.md` + `manifest.json`, produced by the `finish-stage` skill; see "Results contract" below) and, optionally, extra files with a role ("`sim/run7/spikes.csv` for raw spike times"). Only those files are sources. If the stage dir has no `manifest.json`, or a named file is missing, say so and stop; do not substitute files you found yourself.

## Loop

```
explainer.py init  <out> --stage-dir <dir> --brief "<brief>" [--extra <path>:<role>]...
explainer.py next  <out>        # brief for the next step → you write steps/<id>.json and steps/<id>.qmd
explainer.py render <out>       # assemble, render, gate; repeat next/render until all steps drafted
explainer.py accept <out> <id>… # user is happy with a step → freeze it
explainer.py redo   <out> <id> --why "<critique>"   # user finds a step unclear → reopen with the critique
explainer.py status <out>
```

`init` copies the sources into `<out>/data/` (a snapshot) and makes one step per manifest highlight, plus Goal and Decision steps. `next` prints exactly what that step must show, which metrics and files it rests on, and any critique. `render` writes `explainer.qmd` / `explainer.json` from the step files the same way every time; accepted steps are hash-locked and never regenerated.

Default `<out>`: `<stage-dir>/explainer/`.

## Writing a step

Read "Writing explainer.qmd" below first (runtime constraints and data/plot patterns). Then:

- `steps/<id>.json`: `caption` (the point, in simple language), `why`, and `claims` — every number or label the visual shows, each with its `value` and `source` file (`"brief"` is a valid source for values the user stated). Mark computed values `"derived": true`.
- `steps/<id>.qmd`: markdown and `{ojs}` cells. Show, don't list: one clear diagram per idea, animated where motion carries meaning, interactive where the reader would want to poke (hover values, toggle scenarios, scrub a threshold). Every displayed value is read from `data/…` or from `spec`; never typed in. Layout constants are fine.

The page header already provides step navigation (buttons + arrow keys, no autoplay), the caption panel, and the globals `spec`, `step`, `current`. Your step is only shown when selected, so write it as if it were the whole page.

## Gate results

`FAIL` blocks: schema, a claim not found in its source, render error, OJS runtime error. `WARN` lists on-screen numbers found in no source: fix them, or confirm they are derived and the caption says so. Bare integers under 1000 are ignored as counters.

## After a critique

`redo` reopens the step with the user's words attached; `next` shows them. Rewrite only that step. Do not touch accepted steps. Nothing is learned automatically: only when the user explicitly asks for a rule to be kept, run `explainer.py lesson "<rule>"`; `next` shows the lessons file on every step.

## Report back

Give the `<out>` path, how to open it (`quarto preview explainer.qmd` — OJS does not run from `file://` and needs network access to jsdelivr for Plot/Inputs), the step list with its status, and one line per remaining WARN.

## Requirements

Quarto ≥ 1.4 on PATH; Python 3; `playwright` + Chromium for the on-screen check (`pip install playwright && playwright install chromium`). Without it the gate validates and renders and skips the on-screen check with a warning.

## Results contract (what the stage directory must contain)

Every stage that will be explained ends by writing two files in its stage directory (the `finish-stage` skill produces them):

1. `report.md` — the narrative, with exactly these H2 sections (empty ones say "none"): `## Goal`, `## What was done`, `## Results`, `## Decision`, `## Open issues`. Every number that matters is in *Results* with its unit and the file it comes from.
2. `manifest.json` — the same content, machine-readable:
   - `metrics`: each number a reader should know, with `unit`, `source` file, `meaning`, and `budget` when it is judged against a threshold.
   - `artifacts`: every data file, with a `role` and, for tables, a `columns` map. Without this the explainer cannot know what a column means.
   - `decisions`: what was decided and `because` of which metrics.
   - `highlights`: 3–6 points in narrative order. **Each highlight becomes one explainer step.** Each references the metrics and artifacts it rests on.

Extra data that was not part of the planned outputs (raw simulator dumps, ad-hoc CSVs) needs no manifest entry; it is named in the brief with a role and treated like an artifact.

## Writing explainer.qmd

### Runtime constraints (verified with Quarto 1.10.18)

- `embed-resources: true` inlines `FileAttachment` data into the HTML (the page still works after the CSV is deleted). Verified.
- OJS **does not run from `file://`**. Open the page through a server: `quarto preview explainer.qmd`, or `python -m http.server` in the stage dir. Verified.
- `Inputs`, `Plot` and `d3` are fetched at runtime from `cdn.jsdelivr.net` / `cdn.observableusercontent.com`; the page needs network access to those hosts. Verified.
- `ojs_define()` (passing data from a Python/R cell) only works during a full `quarto render`, not when running cells interactively. Prefer `FileAttachment` on the stage's files; it is simpler and keeps the data path explicit.

### Front matter

Generated by `explainer.py render` (title, `embed-resources: true`, full page layout). Do not write it in step files.

### Loading stage files

```{ojs}
rates   = FileAttachment("data/rates.csv").csv({typed: true})
summary = FileAttachment("data/summary.json").json()
```

For SQLite: `db = FileAttachment("data/run.db").sqlite()` then `db.query("select layer, rate_hz from rates")`.
For a markdown report, do not parse it in OJS; put the values into `explainer.json` claims (with `source`) and quote them from there:

```{ojs}
spec = FileAttachment("explainer.json").json()
```

### Globals the header provides

`spec` (explainer.json), `step` (0-based index, user-driven), `current` (this step's json entry). Your step's cells run always but are displayed only when selected; keep them cheap (filter data, don't reload it).

A claim value from your own step, without retyping it:

```{ojs}
budget = current.claims.find(c => c.text.startsWith("budget")).value
```

### Animated transitions

Observable Plot re-renders on each step; for motion between steps use D3 on an SVG you own:

```{ojs}
{
  const svg = d3.create("svg").attr("viewBox", [0, 0, 640, 320]);
  const sel = svg.selectAll("circle").data(rates.slice(0, step + 1), d => d.layer);
  sel.join(
    enter => enter.append("circle").attr("cx", (d, i) => 80 + i * 120).attr("cy", 160).attr("r", 0)
                  .call(e => e.transition().duration(600).attr("r", d => d.rate_hz * 4)),
    update => update,
    exit => exit.transition().duration(300).attr("r", 0).remove()
  );
  return svg.node();
}
```

Every radius, position and label above must derive from loaded data (`d.rate_hz`), not literals. Layout constants (640, 320, 80) are fine; they are not claims.

### Data-plot patterns

Spike raster (columns `t_ms`, `neuron_id`, `cell_type`):

```{ojs}
Plot.plot({
  height: 400, x: {label: "t (ms)"}, y: {label: "neuron"},
  marks: [Plot.dot(spikes, {x: "t_ms", y: "neuron_id", fill: "cell_type", r: 1})]
})
```

Spectrum (columns `f_hz`, `power`):

```{ojs}
Plot.plot({
  x: {type: "log", label: "f (Hz)"}, y: {type: "log", label: "power"},
  marks: [Plot.line(psd, {x: "f_hz", y: "power"})]
})
```

Layered schematic (cortical layers as bands, values from data):

```{ojs}
Plot.plot({
  y: {domain: layers.map(d => d.layer), label: null},
  marks: [Plot.barX(layers, {y: "layer", x: "rate_hz", fill: "layer"}), Plot.text(layers, {y: "layer", x: "rate_hz", text: d => `${d.rate_hz} Hz`, dx: 18})]
})
```

Filter any plot by `step` (e.g. `spikes.filter(d => d.t_ms <= current.t_max)`) so the diagram reveals with the narrative.

Note: the `Plot`/`Inputs` snippets follow the documented API but could not be executed in the authoring sandbox (no CDN access). The gate will tell you if a cell throws.

### Before running render

- No numeric literal in the `.qmd` is a claim about the data.
- Every step in `explainer.json` is visible somewhere in the page.
