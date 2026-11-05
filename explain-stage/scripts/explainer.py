#!/usr/bin/env python3
"""explainer.py — deterministic scaffolding around per-step LLM slide writing.

  init   OUT --stage-dir DIR --brief TEXT [--extra PATH[:ROLE]]...   build the step plan from DIR/manifest.json
  status OUT                                                          show steps and their state
  next   OUT                                                          print the brief for the next step to draft
  render OUT [--no-browser]                                           assemble explainer.qmd + explainer.json, render, gate
  accept OUT ID [ID...]                                               freeze steps (hash recorded; render refuses silent edits)
  redo   OUT ID --why TEXT                                            reopen a step with a critique
  lesson TEXT                                                         append a standing rule to references/lessons.md

The agent writes, per step: steps/<id>.json (caption, why, claims) and steps/<id>.qmd (the visual).
Everything else is produced here, the same way every time.
"""
import argparse, hashlib, json, shutil, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFS = HERE.parent / "references"
sys.path.insert(0, str(HERE))
import gate  # noqa: E402

def load(out): return json.loads((out / "state.json").read_text())
def save(out, st): (out / "state.json").write_text(json.dumps(st, indent=2, ensure_ascii=False))
def sha(p: Path): return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
def step_files(out, sid): return out / "steps" / f"{sid}.json", out / "steps" / f"{sid}.qmd"

# ------------------------------------------------------------------ init
def cmd_init(a):
    out, sd = Path(a.out).resolve(), Path(a.stage_dir).resolve()
    if (out / "state.json").exists(): sys.exit(f"{out} already initialised; use status/next/redo")
    mpath = sd / "manifest.json"
    if not mpath.exists(): sys.exit(f"no manifest.json in {sd} (produce it with the finish-stage skill)")
    man = json.loads(mpath.read_text())
    gate.fails.clear(); gate.validate(man, json.loads((REFS / "manifest.schema.json").read_text()), "manifest")
    if gate.fails: sys.exit("manifest does not follow manifest.schema.json:\n  " + "\n  ".join(gate.fails))

    (out / "data").mkdir(parents=True, exist_ok=True); (out / "steps").mkdir(exist_ok=True)
    sources = []
    def add(src: Path, role):
        if not src.exists(): sys.exit(f"named file not found: {src}")
        dst = out / "data" / src.name
        if dst.exists() and sha(dst) != sha(src): sys.exit(f"name clash in data/: {src.name}")
        shutil.copy2(src, dst); sources.append({"file": f"data/{src.name}", "from": str(src), "role": role})
    add(mpath, "manifest")
    if (sd / "report.md").exists(): add(sd / "report.md", "report")
    for art in man["artifacts"]: add(sd / art["file"], art["role"])
    for ex in a.extra or []:
        path, _, role = ex.partition(":"); add(Path(path).resolve(), role or "extra data named in the brief")

    by_id = {m["id"]: m for m in man["metrics"]}
    by_file = {Path(x["file"]).name: x for x in man["artifacts"]}
    def enrich(mids, files):
        return ([by_id[m] for m in mids if m in by_id],
                [{"file": f"data/{Path(f).name}", **{k: v for k, v in by_file.get(Path(f).name, {}).items() if k != 'file'}} for f in files])
    steps = [{"id": "goal", "title": "Goal", "text": man["goal"], "why": man.get("summary", ""),
              "metrics": [], "files": [], "status": "pending", "critiques": []}]
    for h in man["highlights"]:
        ms, fs = enrich(h.get("metrics", []), h.get("artifacts", []))
        steps.append({"id": h["id"], "title": h["text"][:60], "text": h["text"], "why": h.get("why", ""),
                      "metrics": ms, "files": fs, "status": "pending", "critiques": []})
    if man.get("decisions"):
        ms, _ = enrich([m for d in man["decisions"] for m in d.get("metrics", [])], [])
        steps.append({"id": "decision", "title": "Decision", "text": " ".join(d["text"] for d in man["decisions"]),
                      "why": " ".join(d.get("because", "") for d in man["decisions"]), "metrics": ms, "files": [],
                      "status": "pending", "critiques": []})
    st = {"stage": man["stage"], "title": man["title"], "brief": a.brief, "producer_brief": man.get("brief", ""), "created": str(date.today()),
          "stage_dir": str(sd), "sources": sources, "steps": steps}
    save(out, st); print(f"initialised {out}\n"); cmd_status(a)

# ------------------------------------------------------------------ status / next
def cmd_status(a):
    out = Path(a.out).resolve(); st = load(out)
    print(f"{st['stage']} — {st['title']}   ({len(st['sources'])} sources)")
    for s in st["steps"]:
        j, q = step_files(out, s["id"]); drafted = j.exists() and q.exists()
        flag = {"accepted": "✔", "pending": "·"}[s["status"]] if not (s["status"] == "pending" and drafted) else "○"
        crit = f"  ⟵ redo: {s['critiques'][-1]}" if s["status"] == "pending" and s["critiques"] else ""
        print(f"  {flag} {s['id']:<12} {s['title']}{crit}")
    print("  ✔ accepted   ○ drafted, not yet accepted   · not drafted")

def cmd_next(a):
    out = Path(a.out).resolve(); st = load(out)
    for s in st["steps"]:
        j, q = step_files(out, s["id"])
        if s["status"] == "pending" and not (j.exists() and q.exists() and not s["critiques"]):
            break
    else:
        print("all steps drafted; run render, then accept or redo"); return
    lessons = (REFS / "lessons.md").read_text().strip() if (REFS / "lessons.md").exists() else ""
    print(f"# Slide brief — step `{s['id']}` of {st['stage']}\n")
    print(f"Overall brief from the user:\n> {st['brief']}\n")
    if st.get("producer_brief"): print(f"How the stage was described when its results were written:\n> {st['producer_brief']}\n")
    print(f"## This step\n{s['text']}\n" + (f"Why it matters: {s['why']}\n" if s["why"] else ""))
    if s["metrics"]:
        print("## Metrics to show (values live in the source file; read them from there, do not retype)")
        for m in s["metrics"]:
            b = f", budget {m['budget']}" if "budget" in m else ""
            print(f"- {m['id']}: {m.get('name', '')} = {m['value']} {m.get('unit', '')}{b} — {m.get('meaning', '')}  [{m['source']}]")
    if s["files"]:
        print("\n## Files to draw from")
        for f in s["files"]:
            cols = "; ".join(f"{k}: {v}" for k, v in f.get("columns", {}).items())
            print(f"- {f['file']} — {f.get('role', '')}" + (f" ({cols})" if cols else ""))
    others = [x for x in st["sources"] if x["file"] not in {f["file"] for f in s["files"]}]
    if others: print("\nOther sources available: " + ", ".join(f"{x['file']} ({x['role']})" for x in others))
    if s["critiques"]:
        print("\n## Critique to address (this step was sent back)")
        for c in s["critiques"]: print(f"- {c}")
    if lessons: print(f"\n## Standing lessons\n{lessons}")
    print(f"""
## Write these two files
1. `steps/{s['id']}.json` — {{"caption": ..., "why": ..., "claims": [{{"text", "value", "source", "derived"?}}]}}
   caption = the point in plain language; claims = every number/label the visual shows, with its source file.
2. `steps/{s['id']}.qmd` — markdown + {{ojs}} cells for the visual. Globals available: `spec`, `step`, `current`, `d3`, `Plot`, `html`.
   Read data with FileAttachment("data/<file>"). No numeric literal that is a claim. The step is shown only when selected; no autoplay needed.
Then: `python {HERE / 'explainer.py'} render {out}`""")

# ------------------------------------------------------------------ render
HEADER = """---
title: "{title}"
format:
  html:
    embed-resources: true
    toc: false
    page-layout: full
---

```{{ojs}}
//| echo: false
spec = FileAttachment("explainer.json").json()
```

```{{ojs}}
//| echo: false
viewof step = {{
  const n = spec.steps.length;
  const el = html`<div class="explainer-nav" style="display:flex;gap:.6em;align-items:center;margin:.5em 0">
    <button>◀</button><span style="min-width:6em"></span><button>▶</button></div>`;
  const [prev, next] = el.querySelectorAll("button"), label = el.querySelector("span");
  const set = i => {{ el.value = Math.max(0, Math.min(n - 1, i)); label.textContent = `${{el.value + 1}} / ${{n}}`;
                    el.dispatchEvent(new Event("input", {{bubbles: true}})); }};
  prev.onclick = () => set(el.value - 1); next.onclick = () => set(el.value + 1);
  document.addEventListener("keydown", e => {{ if (e.key === "ArrowRight") set(el.value + 1); if (e.key === "ArrowLeft") set(el.value - 1); }});
  window.__explainerSteps = n; window.__explainerSet = set;
  el.value = 0; label.textContent = `1 / ${{n}}`;
  return el;
}}
```

```{{ojs}}
//| echo: false
current = spec.steps[step]
```

```{{ojs}}
//| echo: false
{{
  document.querySelectorAll(".explainer-step").forEach(el => el.style.display = el.dataset.step === current.id ? "" : "none");
  return html`<div class="explainer-caption"><h2>${{step + 1}}. ${{current.caption}}</h2>
    ${{current.why ? html`<p><em>${{current.why}}</em></p>` : ""}}
    <ul>${{(current.claims ?? []).map(c => html`<li>${{c.text}} <b>${{c.value}}</b> <small>(${{c.derived ? "derived from " : ""}}${{c.source}})</small></li>`)}}</ul></div>`;
}}
```
"""

def cmd_render(a):
    out = Path(a.out).resolve(); st = load(out)
    steps_json, body, skipped = [], [], []
    for s in st["steps"]:
        j, q = step_files(out, s["id"])
        if not (j.exists() and q.exists()): skipped.append(s["id"]); continue
        if s["status"] == "accepted" and (sha(j), sha(q)) != tuple(s["sha"]):
            sys.exit(f"step {s['id']} is accepted but its files changed; run `redo {s['id']} --why ...` first")
        sj = json.loads(j.read_text()); sj["id"] = s["id"]
        sj.setdefault("data", [f["file"] for f in s["files"]]); steps_json.append(sj)
        body.append(f'\n::: {{.explainer-step data-step="{s["id"]}"}}\n\n{q.read_text().strip()}\n\n:::\n')
    if not steps_json: sys.exit("no drafted steps to render")
    spec = {"stage": st["stage"], "title": st["title"], "brief": st["brief"],
            "sources": [{"file": x["file"], "from": x["from"], "note": x["role"]} for x in st["sources"]], "steps": steps_json}
    (out / "explainer.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False))
    (out / "explainer.qmd").write_text(HEADER.format(title=f"{st['stage']} — {st['title']}") + "".join(body))
    if skipped: print("not yet drafted, left out:", ", ".join(skipped))
    fails, warns = gate.run(out, browser=not a.no_browser)
    print(f"\n{'FAIL' if fails else 'PASS'} — {len(fails)} fail, {len(warns)} warn")
    if not fails: print(f"open with: cd {out} && quarto preview explainer.qmd   (OJS needs http, not file://)")
    sys.exit(1 if fails else 0)

# ------------------------------------------------------------------ accept / redo / lesson
def cmd_accept(a):
    out = Path(a.out).resolve(); st = load(out)
    for sid in a.ids:
        s = next((x for x in st["steps"] if x["id"] == sid), None) or sys.exit(f"unknown step {sid}")
        j, q = step_files(out, sid)
        if not (j.exists() and q.exists()): sys.exit(f"step {sid} has no files to accept")
        s["status"], s["sha"], s["critiques"] = "accepted", [sha(j), sha(q)], []
        print(f"accepted {sid}")
    save(out, st)

def cmd_redo(a):
    out = Path(a.out).resolve(); st = load(out)
    s = next((x for x in st["steps"] if x["id"] == a.id), None) or sys.exit(f"unknown step {a.id}")
    s["status"] = "pending"; s.pop("sha", None); s["critiques"].append(a.why); save(out, st)
    print(f"reopened {a.id}; run `next` to get the brief with the critique")

def cmd_lesson(a):
    p = REFS / "lessons.md"
    if not p.exists(): p.write_text("# Lessons\n\nStanding rules for every explainer, added only on explicit request.\n\n")
    p.write_text(p.read_text().rstrip("\n") + f"\n- {a.text}\n"); print(f"added to {p}")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("init"); p.add_argument("out"); p.add_argument("--stage-dir", required=True); p.add_argument("--brief", required=True); p.add_argument("--extra", action="append")
    for c in ("status", "next"): sp.add_parser(c).add_argument("out")
    p = sp.add_parser("render"); p.add_argument("out"); p.add_argument("--no-browser", action="store_true")
    p = sp.add_parser("accept"); p.add_argument("out"); p.add_argument("ids", nargs="+")
    p = sp.add_parser("redo"); p.add_argument("out"); p.add_argument("id"); p.add_argument("--why", required=True)
    sp.add_parser("lesson").add_argument("text")
    a = ap.parse_args(); globals()[f"cmd_{a.cmd}"](a)

if __name__ == "__main__":
    main()
