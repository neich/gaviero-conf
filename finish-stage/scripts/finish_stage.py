#!/usr/bin/env python3
"""Validate a finished stage's report.md + manifest.json (see ../references/manifest.schema.json).
Usage: python finish_stage.py <stage-dir>      exit 0 on PASS, 1 on any FAIL.
       python finish_stage.py --schema        print the manifest JSON schema."""
import csv, json, math, re, sqlite3, sys
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "references" / "manifest.schema.json"
HEADINGS = ["Goal", "What was done", "Results", "Decision", "Open issues"]
NUM_RE = re.compile(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?(?![\w.])")
fails = []
def fail(m): fails.append(m); print("FAIL", m)
def ok(m): print("ok  ", m)

def validate(inst, schema, path="manifest"):
    t = schema.get("type"); types = t if isinstance(t, list) else [t] if t else []
    py = {"object": dict, "array": list, "string": str, "number": (int, float), "boolean": bool}
    if types and not any(isinstance(inst, py[x]) and not (x == "number" and isinstance(inst, bool)) for x in types):
        fail(f"{path}: expected {types}, got {type(inst).__name__}"); return
    if isinstance(inst, dict):
        for r in schema.get("required", []):
            if r not in inst: fail(f"{path}: missing required '{r}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in inst:
                if k not in props: fail(f"{path}: unexpected key '{k}'")
        if "additionalProperties" in schema and isinstance(schema["additionalProperties"], dict):
            for k, v in inst.items(): validate(v, schema["additionalProperties"], f"{path}.{k}")
        for k, v in inst.items():
            if k in props: validate(v, props[k], f"{path}.{k}")
    if isinstance(inst, list):
        if len(inst) < schema.get("minItems", 0): fail(f"{path}: needs at least {schema['minItems']} items")
        for i, v in enumerate(inst): validate(v, schema.get("items", {}), f"{path}[{i}]")

def nums(text): 
    out = set()
    for m in NUM_RE.findall(text):
        try: out.add(float(m.replace(",", ".")))
        except ValueError: pass
    return out

def file_values(p: Path):
    ext = p.suffix.lower()
    if ext == ".json":
        n, s = set(), []
        def walk(x):
            if isinstance(x, bool): return
            if isinstance(x, (int, float)): n.add(float(x))
            elif isinstance(x, str): s.append(x); n.update(nums(x))
            elif isinstance(x, dict): [walk(v) for v in x.values()]; s.extend(x.keys())
            elif isinstance(x, list): [walk(v) for v in x]
        walk(json.loads(p.read_text())); return n, "\n".join(s)
    if ext in (".db", ".sqlite", ".sqlite3"):
        n, s = set(), []
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        for (t,) in con.execute("select name from sqlite_master where type='table'"):
            for row in con.execute(f'select * from "{t}"'):
                for v in row:
                    if isinstance(v, (int, float)) and not isinstance(v, bool): n.add(float(v))
                    elif isinstance(v, str): s.append(v); n.update(nums(v))
        con.close(); return n, "\n".join(s)
    txt = p.read_text(errors="replace"); return nums(txt), txt

def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    if sys.argv[1] == "--schema": print(SCHEMA.read_text()); return
    sd = Path(sys.argv[1]).resolve()
    rep, man = sd / "report.md", sd / "manifest.json"
    if not rep.exists(): fail("report.md missing")
    else:
        heads = re.findall(r"^## (.+?)\s*$", rep.read_text(), re.M)
        missing = [h for h in HEADINGS if h not in heads]
        (fail if missing else ok)(f"report.md headings" + (f": missing {missing}" if missing else ""))
    if not man.exists(): fail("manifest.json missing"); return done()
    try: m = json.loads(man.read_text())
    except json.JSONDecodeError as e: fail(f"manifest.json is not valid JSON: {e}"); return done()
    before = len(fails); validate(m, json.loads(SCHEMA.read_text()))
    if len(fails) > before: return done()
    ok("manifest schema")

    mids = {x["id"] for x in m["metrics"]}; afiles = {x["file"] for x in m["artifacts"]}
    for a in m["artifacts"]:
        (ok if (sd / a["file"]).exists() else fail)(f"artifact {a['file']}")
    cache = {}
    for x in m["metrics"]:
        p = sd / x["source"]
        if not p.exists(): fail(f"metric {x['id']}: source {x['source']} not found"); continue
        if x["source"] not in cache: cache[x["source"]] = file_values(p)
        n, s = cache[x["source"]]; v = x["value"]
        found = any(math.isclose(float(v), y, rel_tol=1e-9, abs_tol=1e-12) for y in n) if isinstance(v, (int, float)) else v in s
        (ok if found else fail)(f"metric {x['id']} = {v!r} in {x['source']}")
    for h in m["highlights"]:
        for mid in h.get("metrics", []):
            if mid not in mids: fail(f"highlight {h['id']}: unknown metric id {mid}")
        for f in h.get("artifacts", []):
            if f not in afiles: fail(f"highlight {h['id']}: {f} is not a declared artifact")
    for d in m.get("decisions", []):
        for mid in d.get("metrics", []):
            if mid not in mids: fail(f"decision {d['id']}: unknown metric id {mid}")
    ok(f"{len(m['highlights'])} highlights: " + " | ".join(h['text'] for h in m['highlights']))
    done()

def done():
    print(f"\n{'FAIL' if fails else 'PASS'} — {len(fails)} fail"); sys.exit(1 if fails else 0)

if __name__ == "__main__": main()
