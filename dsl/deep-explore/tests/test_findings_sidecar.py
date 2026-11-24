"""Tests for findings_sidecar.py (ledger -> academic-mcp findings-v1 sidecar)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import helpers  # noqa: E402  (puts the tools folder on sys.path)
import findings_sidecar  # noqa: E402

# findings-v1.schema.json from the academic-mcp repository; the schema test
# is skipped when it is not there.
SCHEMA = Path(
    os.environ.get(
        "FINDINGS_V1_SCHEMA",
        "C:/Users/natxm/Dropbox/work/git/research/academic-mcp/schemas/findings-v1.schema.json",
    )
)


def validate(instance: Any, schema: dict, root: dict, path: str = "$") -> list[str]:
    """The subset of JSON Schema 2020-12 that findings-v1.schema.json uses."""
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        return validate(instance, root["$defs"][name], root, path)
    if "anyOf" in schema:
        options = [validate(instance, option, root, path) for option in schema["anyOf"]]
        return [] if any(not o for o in options) else [f"{path}: matches no anyOf option ({options[0][0]})"]
    errors: list[str] = []
    types = schema.get("type")
    if types is not None:
        types = types if isinstance(types, list) else [types]
        checks = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "null": lambda v: v is None,
            "boolean": lambda v: isinstance(v, bool),
        }
        if not any(checks[t](instance) for t in types):
            return [f"{path}: expected {types}, got {type(instance).__name__}"]
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required {key!r}")
        for key, value in instance.items():
            if key in props:
                errors.extend(validate(value, props[key], root, f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unknown field {key!r}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], root, f"{path}[{i}]"))
    return errors


def make_run(out: Path, brief: bool = True) -> None:
    """Two passes: q1 supported (W1) + partial (W2), q2 cannot_verify, q3 forbidden, q4 title mismatch."""
    helpers.write_json(
        out,
        "landscape.json",
        {
            **({"brief": "Map the failure modes of X."} if brief else {}),
            "collection": "explore-failure-modes-x",
            "channels": {"academic": "ok", "web": "unused"},
        },
    )
    c_supported = helpers.claim("Claim A holds in adults.")
    c_supported["quote"] = "\u201cClaim A holds ... in adults\u201d"
    c_partial = helpers.claim("Claim B doubles the rate.", work_id="https://doi.org/10.1/b", title="B paper")
    c_partial["confidence"] = "medium"
    c_unverified = helpers.claim("Claim C is common.", work_id="arXiv:2401.01234", title="C preprint", year=2024)
    c_unverified["evidence"] = "abstract_only"
    c_unverified["quote"] = "C is common"
    finding1 = helpers.finding("q1-p1", [c_supported, c_partial])
    finding1["counter_evidence"] = [{"text": "One cohort found no effect of A.", "work_id": "W9"}]
    finding2 = helpers.finding("q2-p1", [c_unverified])
    audit1 = helpers.audit(
        1,
        [
            {**helpers.audit_claim("q1-p1", 0, "supported"), "passage": "Claim A holds in adults (n = 40)."},
            {
                **helpers.audit_claim(
                    "q1-p1", 1, "partial", work=helpers.work(openalex="W2", doi="10.1/b", title="B paper")
                ),
                "reason": "only in mice",
                "checked_via": "abstract",
            },
            {**helpers.audit_claim("q2-p1", 0, "cannot_verify", work={}), "passage": "", "reason": "no full text yet"},
        ],
        fidelity=[("q2-p1", "narrowed")],
    )
    audit1["contradictions"] = [{"a": "q1-p1#0", "b": "q2-p1#0", "note": "opposite populations"}]
    helpers.write_pass(
        out,
        1,
        frontier=helpers.frontier(1, [helpers.question("q1"), helpers.question("q2"), helpers.question("q3")]),
        assignments=["q1-p1", "q2-p1"],
        findings=[finding1, finding2],
        audit=audit1,
    )
    finding3 = helpers.finding("q3-p2", [helpers.claim("Claim D.", work_id="W3")])
    finding4 = helpers.finding("q4-p2", [helpers.claim("Claim E.", work_id="W4", title="Something else entirely")])
    audit2 = helpers.audit(
        2,
        [
            helpers.audit_claim("q3-p2", 0, "not_supported", work=helpers.work(openalex="W3")),
            helpers.audit_claim("q4-p2", 0, "supported", work=helpers.work(openalex="W4", title="Unrelated title")),
        ],
    )
    helpers.write_pass(
        out,
        2,
        frontier=helpers.frontier(
            2,
            [
                helpers.question("q1", status="closed"),
                helpers.question("q2"),
                helpers.question("q3", status="parked", why="a trial nobody ran"),
                helpers.question("q4"),
            ],
        ),
        assignments=["q3-p2", "q4-p2"],
        findings=[finding3, finding4],
        audit=audit2,
    )
    helpers.write_json(out, "frontier-v3.json", helpers.frontier(3, [helpers.question("q1", status="closed")]))
    (out / "report.md").write_text("# Report\n", encoding="utf-8")


class SidecarTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_gate(self) -> tuple[dict, dict, str]:
        code, stdout = helpers.run_main(findings_sidecar, [self.out])
        self.assertEqual(code, 0, stdout)
        build = helpers.read_json(self.out, "findings-build.json")
        sidecar = helpers.read_json(self.out, "report.findings.json") if (self.out / "report.findings.json").exists() else {}
        return build, sidecar, stdout

    def test_maps_the_ledger_to_findings_v1(self) -> None:
        make_run(self.out)
        build, sidecar, stdout = self.run_gate()
        self.assertEqual(build["status"], "ok", build)
        self.assertEqual(build["path"], str((self.out / "report.findings.json").resolve()))
        self.assertIn("FINDINGS: wrote report.findings.json", stdout)

        run = sidecar["run"]
        self.assertEqual(run["id"], "deep-explore-explore-failure-modes-x")
        self.assertEqual(run["skill"], "deep-explore")
        self.assertEqual(run["question"], "Map the failure modes of X.")
        self.assertEqual((run["report"], run["evidence"]), ("report.md", "ledger.json"))
        self.assertEqual(run["params"]["passes"], 2)

        claims = {c["id"]: c for c in sidecar["claims"]}
        self.assertNotIn("stmt:q3-p2#0", claims)  # forbidden: not_supported
        self.assertEqual(build["counts"]["excluded_forbidden"], 1)

        a = claims["stmt:q1-p1#0"]
        self.assertEqual((a["label"], a["kind"], a["certainty"]), ("verified", "finding", "high"))
        self.assertEqual(a["section"], "q1: What explains q1?")
        self.assertEqual(
            a["evidence"],
            [
                {
                    "source": "src:W1",
                    "direction": "supports",
                    "access": "full_text",
                    "evidence_type": "single study",
                    "quote": "Claim A holds in adults (n = 40).",
                    "locator": "results",
                }
            ],
        )

        b = claims["stmt:q1-p1#1"]
        self.assertEqual((b["label"], b["certainty"]), ("unverified", "low"))
        self.assertEqual(b["evidence"][0]["direction"], "inconclusive")
        self.assertEqual(b["evidence"][0]["access"], "abstract")
        self.assertEqual(b["evidence"][0]["scope_note"], "only in mice")
        self.assertIn("audit: partial", b["qualifiers"][0])

        c = claims["stmt:q2-p1#0"]
        self.assertEqual(c["label"], "unverified")
        self.assertEqual(c["evidence"][0]["source"], "src:arxiv:2401.01234")
        self.assertEqual(c["evidence"][0]["access"], "abstract")
        self.assertEqual(c["evidence"][0]["quote"], "C is common")
        self.assertTrue(any(q.startswith("lane fidelity: narrowed") for q in c["qualifiers"]))
        self.assertTrue(any("cannot_verify" in q and "no full text yet" in q for q in c["qualifiers"]))

        e = claims["stmt:q4-p2#0"]  # supported, but the claimed title does not match the resolved work
        self.assertEqual(e["label"], "unverified")
        self.assertIn("title does not match", e["qualifiers"][0])

        counter = claims["stmt:q1-p1#counter-0"]
        self.assertEqual((counter["kind"], counter["label"]), ("limitation", "unverified"))
        self.assertEqual(counter["evidence"][0]["source"], "src:W9")

        sources = {s["id"]: s for s in sidecar["sources"]}
        self.assertEqual(sources["src:W1"]["ids"], {"openalex": "W1"})
        self.assertEqual(sources["src:W1"]["access"], "full_text")
        self.assertEqual(sources["src:W2"]["ids"], {"openalex": "W2", "doi": "10.1/b"})
        self.assertEqual(sources["src:arxiv:2401.01234"]["ids"], {"arxiv": "2401.01234"})
        self.assertEqual(sources["src:arxiv:2401.01234"]["year"], 2024)
        self.assertEqual(sources["src:W4"]["title"], "Unrelated title")  # the resolved record, not the claimed title

        self.assertEqual(
            sidecar["relations"],
            [{"from": "stmt:q1-p1#0", "to": "stmt:q2-p1#0", "kind": "contradicts", "note": "opposite populations"}],
        )
        self.assertNotIn("open_questions", sidecar)  # frontier-v3 has only the closed q1

    def test_open_and_parked_questions_come_from_the_latest_frontier(self) -> None:
        make_run(self.out)
        (self.out / "frontier-v3.json").unlink()
        _build, sidecar, _ = self.run_gate()
        self.assertEqual(
            sidecar["open_questions"],
            ["q2: What explains q2?", "q3 (parked): What explains q3? — would need: a trial nobody ran", "q4: What explains q4?"],
        )

    def test_missing_brief_uses_a_placeholder_the_recorder_replaces(self) -> None:
        make_run(self.out, brief=False)
        build, sidecar, _ = self.run_gate()
        self.assertEqual(build["status"], "ok")
        self.assertEqual(build["counts"]["question_source"], "placeholder")
        self.assertIn("brief is not recorded", sidecar["run"]["question"])

    def test_output_passes_its_own_lint_and_the_schema(self) -> None:
        make_run(self.out)
        _build, sidecar, _ = self.run_gate()
        self.assertEqual(findings_sidecar.lint(sidecar), [])
        if not SCHEMA.is_file():
            self.skipTest(f"schema not found: {SCHEMA}")
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(validate(sidecar, schema, schema), [])

    def test_rebuilding_an_unchanged_run_writes_the_same_bytes(self) -> None:
        make_run(self.out)
        self.run_gate()
        first = (self.out / "report.findings.json").read_bytes()
        self.run_gate()
        self.assertEqual((self.out / "report.findings.json").read_bytes(), first)

    def test_never_fails_the_loop(self) -> None:
        code, stdout = helpers.run_main(findings_sidecar, [self.out / "missing"])
        self.assertEqual(code, 0)
        self.assertIn("FINDINGS: SKIPPED", stdout)
        helpers.write_json(self.out, "audit-v1.json", {"pass": 1, "claims": []})
        helpers.write_json(self.out, "x-finding-v1.json", ["not an object"])
        (self.out / "frontier-v1.json").write_text("{broken", encoding="utf-8")
        build, _sidecar, _ = self.run_gate()
        self.assertEqual(build["status"], "ok")


class QuoteTest(unittest.TestCase):
    def test_clean_quote(self) -> None:
        q = findings_sidecar.clean_quote
        self.assertIsNone(q("   "))
        self.assertEqual(q('"whole quote"'), "whole quote")
        self.assertEqual(q('"a" and "b"'), '"a" and "b"')
        self.assertEqual(q("first part ... second part"), "first part … second part")
        self.assertEqual(q("first [...] second (…) third"), "first … second … third")
        self.assertEqual(q("... trailing and leading ..."), "trailing and leading")
        long = " ".join(["word"] * 200)
        self.assertLessEqual(len(q(long)), 400)
        self.assertTrue(long.startswith(q(long)))

    def test_ids_of_claimed(self) -> None:
        ids = findings_sidecar.ids_of_claimed
        self.assertEqual(ids("https://openalex.org/W123"), {"openalex": "W123"})
        self.assertEqual(ids("doi:10.1/x"), {"doi": "10.1/x"})
        self.assertEqual(ids("https://doi.org/10.1/X"), {"doi": "10.1/X"})
        self.assertEqual(ids("2401.01234v2"), {"arxiv": "2401.01234v2"})
        self.assertEqual(ids("arxiv:hep-th/9901001"), {"arxiv": "hep-th/9901001"})
        self.assertEqual(ids("PMID: 123"), {"pmid": "123"})
        self.assertEqual(ids("pmc999"), {"pmcid": "PMC999"})
        self.assertEqual(ids("https://example.org/p"), {"url": "https://example.org/p"})
        self.assertEqual(ids("a title"), {})

    def test_run_key(self) -> None:
        self.assertEqual(findings_sidecar.run_key("deep-explore-Explore_X Y!"), "deep-explore-explore_x-y")
        self.assertTrue(findings_sidecar.RUN_KEY_RE.fullmatch(findings_sidecar.run_key("--__" + "a" * 300)))


if __name__ == "__main__":
    unittest.main()
