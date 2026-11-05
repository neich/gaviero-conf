#!/usr/bin/env python3
"""Gate for a stage explainer.

Usage: python gate.py <out-dir> [--json explainer.json] [--qmd explainer.qmd]
                      [--settle-ms 4000] [--no-browser]

Checks, in order:
  1. explainer.json matches references/explainer.schema.json (structural check, no external deps)
  2. every non-derived claim value occurs in its declared source file (or in the brief)
  3. `quarto render` succeeds and front matter has embed-resources: true
  4. the rendered page, served over HTTP and loaded in headless Chromium, shows no OJS
     runtime error and no number absent from the union of source files (WARN per number)

Exit 0 on pass (warnings allowed), 1 on any FAIL.
"""
import argparse, csv, http.server, json, math, os, re, socketserver, sqlite3, subprocess, sys, threading
from pathlib import Path

NUM_RE = re.compile(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?(?![\w.])")
SCHEMA = Path(__file__).resolve().parent.parent / "references" / "explainer.schema.json"

fails, warns = [], []
def fail(msg): fails.append(msg); print("FAIL", msg)
def warn(msg): warns.append(msg); print("WARN", msg)
def ok(msg): print("ok  ", msg)

# ---------- 1. schema (minimal validator for the subset used by explainer.schema.json) ----------
def validate(inst, schema, path="$"):
    t = schema.get("type")
    types = t if isinstance(t, list) else [t] if t else []
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
        for k, v in inst.items():
            if k in props: validate(v, props[k], f"{path}.{k}")
    if isinstance(inst, list):
        if "minItems" in schema and len(inst) < schema["minItems"]: fail(f"{path}: needs at least {schema['minItems']} items")
        for i, v in enumerate(inst): validate(v, schema.get("items", {}), f"{path}[{i}]")

# ---------- 2. value sets from source files ----------
def parse_num(s):
    try: return float(s.replace(",", "."))
    except ValueError: return None

def nums_in_text(text):
    return {n for m in NUM_RE.findall(text) if (n := parse_num(m)) is not None}

def source_values(path: Path):
    """Return (numbers:set[float], text:str) found in a source file."""
    ext = path.suffix.lower()
    if ext in (".md", ".txt", ".csv", ".tsv"):
        txt = path.read_text(errors="replace"); return nums_in_text(txt), txt
    if ext == ".json":
        nums, strs = set(), []
        def walk(x):
            if isinstance(x, bool): return
            if isinstance(x, (int, float)): nums.add(float(x))
            elif isinstance(x, str): strs.append(x); nums.update(nums_in_text(x))
            elif isinstance(x, dict): [walk(v) for v in x.values()]; strs.extend(x.keys())
            elif isinstance(x, list): [walk(v) for v in x]
        walk(json.loads(path.read_text())); return nums, "\n".join(strs)
    if ext in (".db", ".sqlite", ".sqlite3"):
        nums, strs = set(), []
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        for (tbl,) in con.execute("select name from sqlite_master where type='table'"):
            for row in con.execute(f'select * from "{tbl}"'):
                for v in row:
                    if isinstance(v, (int, float)) and not isinstance(v, bool): nums.add(float(v))
                    elif isinstance(v, str): strs.append(v); nums.update(nums_in_text(v))
        con.close(); return nums, "\n".join(strs)
    warn(f"unsupported source type {path.name}; only its text is scanned")
    txt = path.read_text(errors="replace"); return nums_in_text(txt), txt

def has_num(nset, v, rel=1e-9):
    return any(math.isclose(v, n, rel_tol=rel, abs_tol=1e-12) for n in nset)

# ---------- 3. render ----------
def render(stage: Path, qmd: str):
    fm = (stage / qmd).read_text().split("---")
    if len(fm) < 3 or not re.search(r"embed-resources:\s*true", fm[1]): fail("front matter lacks 'embed-resources: true'")
    r = subprocess.run(["quarto", "render", qmd, "--to", "html"], cwd=stage, capture_output=True, text=True)
    if r.returncode != 0: fail("quarto render failed:\n" + r.stderr[-2000:]); return None
    html = stage / (Path(qmd).stem + ".html")
    ok(f"rendered {html.name} ({html.stat().st_size // 1024} KB)"); return html

# ---------- 4. browser ----------
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def on_screen_text(stage: Path, html: Path, settle_ms: int):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        warn("playwright not installed; on-screen check skipped"); return None
    handler = lambda *a, **k: Quiet(*a, directory=str(stage), **k)
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        grab = """() => { const c = document.body.cloneNode(true);
                c.querySelectorAll('.tick text, script, style, .cell-code, pre, details').forEach(e => e.remove());
                return c.innerText; }"""
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{port}/{html.name}"); pg.wait_for_timeout(settle_ms)
            n = pg.evaluate("() => window.__explainerSteps || 0")
            if n:  # step-driven page: visit every step so hidden ones are checked too
                parts = []
                for i in range(n):
                    pg.evaluate(f"() => window.__explainerSet({i})"); pg.wait_for_timeout(800)
                    parts.append(pg.evaluate(grab))
                txt = "\n".join(parts)
            else:
                txt = pg.evaluate(grab)
            b.close()
        srv.shutdown()
    return txt

def run(stage: Path, json_name="explainer.json", qmd_name="explainer.qmd", settle_ms=4000, browser=True):
    """Programmatic entry: returns (fails, warns)."""
    fails.clear(); warns.clear()
    _run(stage, json_name, qmd_name, settle_ms, browser)
    return list(fails), list(warns)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage"); ap.add_argument("--json", default="explainer.json"); ap.add_argument("--qmd", default="explainer.qmd")
    ap.add_argument("--settle-ms", type=int, default=4000); ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    _run(Path(a.stage).resolve(), a.json, a.qmd, a.settle_ms, not a.no_browser)
    finish()

def _run(stage, json_name, qmd_name, settle_ms, browser):
    spec = json.loads((stage / json_name).read_text())
    validate(spec, json.loads(SCHEMA.read_text()))
    if fails: return
    ok("schema")

    values = {"brief": (nums_in_text(spec["brief"]), spec["brief"])}
    for src in spec["sources"]:
        s = src["file"]; p = stage / s
        if not p.exists(): fail(f"source not found: {s}"); continue
        values[s] = source_values(p)
    all_nums = set().union(*(n for n, _ in values.values())) if values else set()

    for st in spec["steps"]:
        for c in st.get("claims", []):
            if c.get("derived"): continue
            if c["source"] not in values: fail(f"step {st['id']}: claim source '{c['source']}' is not in sources"); continue
            nums, txt = values[c["source"]]
            v = c["value"]
            found = has_num(nums, float(v)) if isinstance(v, (int, float)) else (v in txt)
            (ok if found else fail)(f"step {st['id']}: {v!r} in {c['source']}")
    if fails: return

    html = render(stage, qmd_name)
    if html is None or not browser: return

    txt = on_screen_text(stage, html, settle_ms)
    if txt is None: return
    if "OJS Runtime Error" in txt or "unable to load module" in txt: fail("page shows an OJS runtime error (open it to see which cell)")
    seen = set()
    for m in NUM_RE.findall(txt):
        v = parse_num(m)
        if v is None or m in seen: continue
        seen.add(m)
        # small bare integers (step counters, list numbers) are not claims; everything else must exist in a source
        if "." not in m and "," not in m and "e" not in m.lower() and abs(v) < 1000: continue
        if not has_num(all_nums, v): warn(f"on-screen number {m} not found in any source (derived? then the caption must say so)")
    ok(f"on-screen check: {len(seen)} numeric tokens inspected")

def finish():
    print(f"\n{'FAIL' if fails else 'PASS'} — {len(fails)} fail, {len(warns)} warn")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
