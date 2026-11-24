"""Findings sidecar of deep-explore.gaviero: `findings_sidecar.py OUT_DIR`.

Runs in the `deep-explore-report` loop as the second `until command`, so
only after `report_gate.py` has passed. Builds OUT_DIR/report.findings.json,
the academic-mcp findings sidecar (schemas/findings-v1.md and
findings-v1.schema.json in the academic-mcp repository), from the claim
ledger, the findings, the audits, the latest frontier and landscape.json.
Then it writes OUT_DIR/findings-build.json for the `recorder` agent, which
stores the sidecar with the academic server's record_research tool.

Mapping: one claim per ledger claim, id `stmt:<claim key>`, kind finding.

  citable supported   label verified; one evidence line `supports` on the
                      resolved work, quoting the verifier's passage (else
                      the investigator's quote)
  citable partial     label unverified; evidence `inconclusive`: the
                      source states a weaker or narrower version
  citable unverified  label unverified; evidence `supports` as the
                      investigator asserted it, on the work it named
  citable forbidden   left out (not_supported, retracted, unresolvable)
  counter_evidence    kind limitation, label unverified (never audited)
  contradictions      relations `contradicts` between the two claims
  open / parked questions of the latest frontier -> open_questions

The run key is `deep-explore-<collection>`: the collection is unique per
run, so re-running deep-explore-report on the same OUT_DIR records a new
revision of the same run. run.question is landscape.json's `brief`; when
it is missing the recorder replaces the placeholder with the brief.

It never fails the report loop: the exit code is 0 whenever the arguments
parse. Problems go to findings-build.json (`status` other than "ok") and
to stdout. Standard library only; Python 3.10 or newer.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_common  # noqa: E402
from gate_common import GateInputError, as_dict, as_int, as_list, as_str  # noqa: E402

SKILL = "deep-explore"
SKILL_VERSION = "2026-11-24"
SIDECAR = "report.findings.json"
BUILD_LOG = "findings-build.json"
MAX_BYTES = 5 * 1024 * 1024
QUOTE_CHARS = 400
TEXT_CHARS = 2000
TITLE_CHARS = 500
NOTE_CHARS = 500
LOCATOR_CHARS = 200
SECTION_CHARS = 300

LABELS = ("verified_multi", "verified", "single_source", "inferred", "assumed", "unverified")
SUPPORT_LABELS = ("verified_multi", "verified", "single_source")
ACCESS_RANK = {"snippet": 0, "abstract": 1, "fetched": 2, "full_text": 3}
CERTAINTY = {"high": "high", "medium": "moderate", "moderate": "moderate", "low": "low"}
CHECKED_VIA = {"corpus": "full_text", "fulltext": "full_text", "abstract": "abstract", "citations": "snippet", "web": "fetched"}
RUN_KEY_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
DOUBLE_QUOTES = "\"“”«»"
ELLIPSIS_RE = re.compile(r"\s*(?:\[\s*(?:\.\s*){3}\]|\(\s*(?:\.\s*){3}\)|\[…\]|\(…\)|\.{3,}|…)\s*")


# ── text ─────────────────────────────────────────────────────────────────────


def clean_text(value: Any, limit: int) -> str:
    """Whitespace collapsed; past `limit` characters cut at a word and ended with "…"."""
    text = " ".join(as_str(value).split())
    if len(text) > limit:
        cut = text.rfind(" ", 0, limit)
        text = (text[:cut] if cut > 0 else text[: limit - 1]).rstrip() + "…"
    return text


def clean_quote(value: Any) -> Optional[str]:
    """A quote fit for findings-v1, or None.

    Whitespace collapsed, one pair of surrounding double quotation marks
    removed, every ellipsis written as " … " (the server matches each part
    on its own), leading and trailing ellipses dropped, and at most 400
    characters kept, cut at a word: a prefix of a verbatim quote is still
    verbatim. The words themselves are never changed.
    """
    q = " ".join(as_str(value).split())
    if len(q) >= 2 and q[0] in DOUBLE_QUOTES and q[-1] in DOUBLE_QUOTES and not any(c in DOUBLE_QUOTES for c in q[1:-1]):
        q = q[1:-1].strip()
    q = ELLIPSIS_RE.sub(" … ", q).strip()
    q = re.sub(r"^(?:…\s*)+|(?:\s*…)+$", "", q).strip()
    if len(q) > QUOTE_CHARS:
        cut = q.rfind(" ", 0, QUOTE_CHARS + 1)
        q = q[: cut if cut > 0 else QUOTE_CHARS].rstrip(" …")
    return q or None


def run_key(text: str) -> str:
    """`text` as a findings run key: a-z, 0-9, '.', '_' or '-', starting with a letter or digit."""
    key = re.sub(r"[^a-z0-9._-]+", "-", as_str(text).lower())
    key = re.sub(r"-{2,}", "-", key).lstrip("._-")
    return key[:128].rstrip("._-") or "deep-explore-run"


def _rfc3339(path: Path) -> Optional[str]:
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return None
    moment = datetime.datetime.fromtimestamp(stamp, tz=datetime.timezone.utc).replace(microsecond=0)
    return moment.isoformat().replace("+00:00", "Z")


# ── identifiers and sources ──────────────────────────────────────────────────


def ids_of_work(work: dict) -> dict:
    """findings-v1 `ids` of a work the verifier resolved."""
    ids: dict[str, str] = {}
    openalex = gate_common.clean_openalex(work.get("openalex"))
    if re.fullmatch(r"W\d+", openalex):
        ids["openalex"] = openalex
    doi = gate_common.clean_doi(work.get("doi"))
    if doi:
        ids["doi"] = doi
    arxiv = as_str(work.get("arxiv")).strip()
    if arxiv:
        ids["arxiv"] = arxiv
    return ids


def ids_of_claimed(work_id: Any) -> dict:
    """findings-v1 `ids` of the identifier an investigator wrote (W-id, DOI, arXiv, PMID, PMCID, URL)."""
    raw = as_str(work_id).strip()
    low = raw.lower()
    if not raw:
        return {}
    match = re.fullmatch(r"(?:https?://openalex\.org/)?w(\d+)", low)
    if match:
        return {"openalex": "W" + match.group(1)}
    if low.startswith("doi:"):
        return {"doi": raw[4:].strip()} if raw[4:].strip() else {}
    match = re.match(r"https?://(?:dx\.)?doi\.org/(10\..+)", raw, re.I)
    if match:
        return {"doi": match.group(1)}
    if low.startswith("10."):
        return {"doi": raw}
    if low.startswith("arxiv:"):
        return {"arxiv": raw[6:].strip()} if raw[6:].strip() else {}
    match = re.fullmatch(r"(?:https?://arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?", low)
    if match:
        return {"arxiv": match.group(1)}
    match = re.fullmatch(r"pmid:\s*(\d+)", low)
    if match:
        return {"pmid": match.group(1)}
    if re.fullmatch(r"pmc\d+", low):
        return {"pmcid": raw.upper()}
    if low.startswith(("http://", "https://")):
        return {"url": raw}
    return {}


def source_key(ids: dict, title: str) -> Optional[str]:
    """The ledger's work key for these identifiers (OpenAlex, DOI, arXiv, title), else PMID / PMCID / URL."""
    key = gate_common.work_key({**ids, "title": title})
    if key:
        return key
    for name in ("pmid", "pmcid", "url"):
        if ids.get(name):
            return f"{name}:{ids[name]}"
    return None


class Sources:
    """The sidecar's `sources`, one per work key; access is the most of the work any line read."""

    def __init__(self) -> None:
        self.entries: dict[str, dict] = {}

    def add(self, key: Optional[str], ids: dict, title: str, year: int, via: str, access: str) -> Optional[str]:
        if not key:
            return None
        sid = "src:" + re.sub(r"\s+", "-", key)
        entry = self.entries.get(sid)
        if entry is None:
            entry = {"id": sid}
            if ids:
                entry["ids"] = dict(ids)
            if title:
                entry["title"] = title
            if year:
                entry["year"] = year
            entry["via"] = via
            entry["access"] = access
            self.entries[sid] = entry
            return sid
        if ids:
            merged = entry.setdefault("ids", {})
            for name, value in ids.items():
                merged.setdefault(name, value)
        if title and "title" not in entry:
            entry["title"] = title
        if year and "year" not in entry:
            entry["year"] = year
        if ACCESS_RANK[access] > ACCESS_RANK[entry["access"]]:
            entry["access"] = access
        if via == "academic-mcp":
            entry["via"] = via
        return sid

    def values(self) -> list[dict]:
        return list(self.entries.values())


# ── access, labels, reasons ──────────────────────────────────────────────────


def access_of_finding(evidence: Any, channel: str) -> str:
    """How much of the work the investigator read: fulltext / abstract_only / anything else."""
    evidence = as_str(evidence).strip().lower()
    if evidence == "fulltext":
        return "fetched" if channel == "web" else "full_text"
    if evidence == "abstract_only":
        return "abstract"
    return "snippet"


def unverified_reason(entry: dict, audited: dict) -> str:
    flags = as_list(entry.get("flags"))
    if "title_mismatch" in flags:
        return "the claimed title does not match the work the verifier resolved"
    if "no_work" in flags:
        return "the verifier recorded no resolved work"
    if "no_audit" in flags:
        return "no audit verdict"
    verdict = as_str(entry.get("verdict")) or "none"
    reason = clean_text(audited.get("reason"), NOTE_CHARS)
    return f"audit verdict {verdict}" + (f" ({reason})" if reason else "")


def _optional_json(path: Path) -> Any:
    try:
        return gate_common.load_json(path)
    except GateInputError:
        return None


def _claim_index(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


# ── build ────────────────────────────────────────────────────────────────────


def build(out: Path) -> tuple[dict, dict]:
    """(the sidecar, counts) for OUT_DIR `out`."""
    ledger = gate_common.build_ledger(out)
    ledger_claims = as_dict(ledger.get("claims"))
    works = as_dict(ledger.get("works"))
    landscape = as_dict(_optional_json(out / "landscape.json"))
    frontiers = gate_common.versioned_files(out, "frontier")
    frontier = as_dict(_optional_json(frontiers[max(frontiers)])) if frontiers else {}
    audits = gate_common.versioned_files(out, "audit")

    findings: dict[str, dict] = {}
    finding_claims: dict[str, dict] = {}
    for aid, _n, path in gate_common.finding_files(out):
        data = as_dict(_optional_json(path))
        findings[aid] = data
        for index, claim in enumerate(as_list(data.get("claims"))):
            finding_claims[gate_common.claim_key(aid, index)] = as_dict(claim)

    audited: dict[str, dict] = {}
    fidelity: dict[str, dict] = {}
    contradictions: list[dict] = []
    for _n, path in audits.items():
        data = as_dict(_optional_json(path))
        for claim in as_list(data.get("claims")):
            claim = as_dict(claim)
            aid = as_str(claim.get("finding")).strip()
            index = _claim_index(claim.get("index"))
            if aid and index is not None:
                audited[gate_common.claim_key(aid, index)] = claim
        for entry in as_list(data.get("fidelity")):
            entry = as_dict(entry)
            fidelity[as_str(entry.get("finding")).strip()] = entry
        contradictions.extend(as_dict(c) for c in as_list(data.get("contradictions")))

    question_text: dict[str, str] = {}
    for q in as_list(frontier.get("questions")):
        q = as_dict(q)
        question_text[as_str(q.get("id"))] = as_str(q.get("question"))

    def section_of(aid: str) -> str:
        qid = gate_common.question_id_of(aid)
        text = question_text.get(qid) or as_str(findings.get(aid, {}).get("question"))
        return clean_text(f"{qid}: {text}" if text else qid, SECTION_CHARS)

    def fidelity_qualifier(aid: str) -> Optional[str]:
        entry = as_dict(fidelity.get(aid))
        verdict = as_str(entry.get("verdict")).strip().lower()
        if verdict not in ("narrowed", "substituted"):
            return None
        note = clean_text(entry.get("note"), NOTE_CHARS)
        return f"lane fidelity: {verdict}" + (f" — {note}" if note else "")

    sources = Sources()
    claims: list[dict] = []
    counts = {
        "ledger_claims": len(ledger_claims),
        "excluded_forbidden": 0,
        "skipped_empty": 0,
        "counter_evidence": 0,
    }

    for key, entry in ledger_claims.items():
        citable = as_str(entry.get("citable"))
        if citable == "forbidden":
            counts["excluded_forbidden"] += 1
            continue
        text = clean_text(entry.get("text"), TEXT_CHARS)
        if not text:
            counts["skipped_empty"] += 1
            continue
        aid = as_str(entry.get("finding"))
        fc = finding_claims.get(key, {})
        au = audited.get(key, {})
        channel = as_str(fc.get("channel")).strip().lower()
        via = "web" if channel == "web" else "academic-mcp"
        strength = as_str(fc.get("strength")).strip()
        locator = clean_text(fc.get("locator"), LOCATOR_CHARS)
        qualifiers: list[str] = []
        extra = fidelity_qualifier(aid)
        if extra:
            qualifiers.append(extra)

        evidence: Optional[dict] = None
        wk = entry.get("work_key")
        if citable in ("supported", "partial"):
            work = as_dict(works.get(wk))
            access = CHECKED_VIA.get(as_str(au.get("checked_via")).strip().lower()) or access_of_finding(
                fc.get("evidence"), channel
            )
            sid = sources.add(
                wk, ids_of_work(work), clean_text(work.get("title"), TITLE_CHARS), as_int(work.get("year")), via, access
            )
            quote = clean_quote(entry.get("passage")) or clean_quote(fc.get("quote"))
            if sid:
                evidence = {"source": sid, "direction": "supports" if citable == "supported" else "inconclusive"}
            if citable == "supported":
                label = "verified"
                certainty = CERTAINTY.get(as_str(fc.get("confidence")).strip().lower())
            else:
                label = "unverified"
                certainty = "low"
                qualifiers.append("audit: partial — the source states a weaker or narrower version")
        else:
            label = "unverified"
            certainty = "low"
            qualifiers.append("audit: " + unverified_reason(entry, au))
            access = access_of_finding(fc.get("evidence"), channel)
            ids = ids_of_claimed(entry.get("claimed_work_id"))
            title = clean_text(entry.get("claimed_title"), TITLE_CHARS)
            year = as_int(entry.get("claimed_year"))
            skey = source_key(ids, title)
            # The work the verifier resolved describes these identifiers better
            # than the investigator's title (which may be the mismatch itself).
            if wk in works and skey in (None, wk):
                work = as_dict(works.get(wk))
                skey, ids = wk, ids_of_work(work)
                title, year = clean_text(work.get("title"), TITLE_CHARS), as_int(work.get("year"))
            sid = sources.add(skey, ids, title, year, via, access)
            quote = clean_quote(fc.get("quote")) or clean_quote(entry.get("passage"))
            if sid:
                evidence = {"source": sid, "direction": "supports"}

        claim: dict[str, Any] = {"id": "stmt:" + key, "text": text, "kind": "finding", "section": section_of(aid), "label": label}
        if qualifiers:
            claim["qualifiers"] = qualifiers
        if certainty:
            claim["certainty"] = certainty
        if evidence is not None:
            evidence["access"] = access
            if strength:
                evidence["evidence_type"] = strength.replace("_", " ")
            if quote:
                evidence["quote"] = quote
            if locator:
                evidence["locator"] = locator
            reason = clean_text(au.get("reason"), NOTE_CHARS)
            if citable == "partial" and reason:
                evidence["scope_note"] = reason
            claim["evidence"] = [evidence]
        claims.append(claim)

    for aid, data in findings.items():
        for index, counter in enumerate(as_list(data.get("counter_evidence"))):
            counter = as_dict(counter)
            text = clean_text(counter.get("text"), TEXT_CHARS)
            if not text:
                continue
            counts["counter_evidence"] += 1
            claim = {
                "id": f"stmt:{aid}#counter-{index}",
                "text": text,
                "kind": "limitation",
                "section": section_of(aid),
                "label": "unverified",
                "qualifiers": ["counter-evidence from the lane's falsification search; not audited"],
                "certainty": "low",
            }
            ids = ids_of_claimed(counter.get("work_id"))
            sid = sources.add(source_key(ids, ""), ids, "", 0, "academic-mcp", "snippet")
            if sid:
                claim["evidence"] = [{"source": sid, "direction": "supports"}]
            claims.append(claim)

    claim_ids = {c["id"] for c in claims}
    relations: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()
    for c in contradictions:
        a, b = "stmt:" + as_str(c.get("a")).strip(), "stmt:" + as_str(c.get("b")).strip()
        if a == b or a not in claim_ids or b not in claim_ids or (a, b) in seen_pairs or (b, a) in seen_pairs:
            continue
        seen_pairs.add((a, b))
        relation = {"from": a, "to": b, "kind": "contradicts"}
        note = clean_text(c.get("note"), NOTE_CHARS)
        if note:
            relation["note"] = note
        relations.append(relation)

    open_questions: list[str] = []
    for q in as_list(frontier.get("questions")):
        q = as_dict(q)
        status = as_str(q.get("status")).strip().lower()
        text = clean_text(q.get("question"), TEXT_CHARS)
        qid = as_str(q.get("id"))
        if not text:
            continue
        if status in ("open", "active"):
            open_questions.append(f"{qid}: {text}")
        elif status == "parked":
            why = clean_text(q.get("why"), NOTE_CHARS)
            open_questions.append(f"{qid} (parked): {text}" + (f" — would need: {why}" if why else ""))

    resolved = out.resolve()
    collection = as_str(landscape.get("collection")).strip() or as_str(frontier.get("collection")).strip()
    if collection:
        rid = run_key(f"{SKILL}-{collection}")
    else:
        started = (_rfc3339(out / "landscape.json") or "")[:10]
        rid = run_key(f"{SKILL}-{resolved.name}-{started}")
    brief = as_str(landscape.get("brief")).strip()
    counts["question_source"] = "landscape.json" if brief else "placeholder"
    question = brief or f"deep-explore run {resolved.name}: the brief is not recorded in landscape.json"

    run: dict[str, Any] = {
        "id": rid,
        "skill": SKILL,
        "skill_version": SKILL_VERSION,
        "question": question,
        "params": {
            "out_dir": out.as_posix(),
            "collection": collection,
            "passes": max(audits) if audits else 0,
            "lanes": len(findings),
            "ledger_claims": len(ledger_claims),
            "excluded_forbidden": counts["excluded_forbidden"],
            "channels": as_dict(landscape.get("channels")),
        },
    }
    started_at = _rfc3339(out / "landscape.json")
    ended_at = _rfc3339(out / "report.md")
    if started_at:
        run["started_at"] = started_at
    if ended_at:
        run["ended_at"] = ended_at
    run["report"] = "report.md"
    run["evidence"] = "ledger.json"

    sidecar: dict[str, Any] = {"schema_version": 1, "run": run, "sources": sources.values(), "claims": claims}
    if relations:
        sidecar["relations"] = relations
    if open_questions:
        sidecar["open_questions"] = open_questions

    by_label = {name: 0 for name in LABELS}
    for c in claims:
        by_label[c["label"]] += 1
    counts.update(
        {
            "claims": len(claims),
            "by_label": {name: n for name, n in by_label.items() if n},
            "sources": len(sidecar["sources"]),
            "relations": len(relations),
            "open_questions": len(open_questions),
        }
    )
    return sidecar, counts


# ── lint (findings-v1 rules L1-L10) ──────────────────────────────────────────


def lint(sidecar: dict) -> list[str]:
    """Every findings-v1 lint problem of `sidecar`; the server rejects a file with any."""
    problems: list[str] = []
    if sidecar.get("schema_version") != 1:
        problems.append("schema_version: must be 1")
    run = as_dict(sidecar.get("run"))
    if not RUN_KEY_RE.fullmatch(as_str(run.get("id"))):
        problems.append("run.id: must be 1-128 characters of a-z, 0-9, '.', '_' or '-', starting with a letter or digit")
    for field in ("skill", "question"):
        if not as_str(run.get(field)).strip():
            problems.append(f"run.{field}: must not be empty")
    if "params" in run and not isinstance(run["params"], dict):
        problems.append("run.params: must be an object")

    source_ids: set[str] = set()
    for i, s in enumerate(as_list(sidecar.get("sources"))):
        sid = as_str(as_dict(s).get("id"))
        if not sid.startswith("src:"):
            problems.append(f'sources[{i}].id: must start with "src:"')
        if sid in source_ids:
            problems.append(f'sources[{i}].id: duplicate "{sid}"')
        source_ids.add(sid)
        if as_dict(s).get("access") not in ACCESS_RANK:
            problems.append(f"sources[{i}].access: must be one of {', '.join(ACCESS_RANK)}")

    claims = as_list(sidecar.get("claims"))
    claim_ids: set[str] = set()
    for i, c in enumerate(claims):
        cid = as_str(as_dict(c).get("id"))
        if not cid.startswith("stmt:"):
            problems.append(f'claims[{i}].id: must start with "stmt:"')
        if cid in claim_ids:
            problems.append(f'claims[{i}].id: duplicate "{cid}"')
        claim_ids.add(cid)

    lines = 0
    for i, c in enumerate(claims):
        c = as_dict(c)
        if not 1 <= len(as_str(c.get("text"))) <= TEXT_CHARS:
            problems.append(f"claims[{i}].text: must be 1-2000 characters")
        evidence = [as_dict(e) for e in as_list(c.get("evidence"))]
        lines += len(evidence)
        for j, e in enumerate(evidence):
            if as_str(e.get("source")) not in source_ids:
                problems.append(f'claims[{i}].evidence[{j}].source: unknown source "{as_str(e.get("source"))}"')
            if "quote" in e and not 1 <= len(as_str(e.get("quote"))) <= QUOTE_CHARS:
                problems.append(f"claims[{i}].evidence[{j}].quote: must be 1-400 characters")
        for j, inf in enumerate(as_list(c.get("inferred_from"))):
            if as_str(as_dict(inf).get("claim")) not in claim_ids:
                problems.append(f'claims[{i}].inferred_from[{j}].claim: unknown claim "{as_str(as_dict(inf).get("claim"))}"')
        label = c.get("label")
        supporting = any(e.get("direction") == "supports" for e in evidence)
        if label not in LABELS:
            problems.append(f"claims[{i}].label: unknown label {label!r}")
        elif label == "assumed" and supporting:
            problems.append(f"claims[{i}].label: assumed claim has supporting evidence")
        elif label == "inferred" and not evidence and not as_list(c.get("inferred_from")):
            problems.append(f"claims[{i}].label: inferred claim needs evidence or inferred_from")
        elif label in SUPPORT_LABELS and not supporting:
            problems.append(f"claims[{i}].label: {label} claim needs supporting evidence")

    known = source_ids | claim_ids
    for i, r in enumerate(as_list(sidecar.get("relations"))):
        r = as_dict(r)
        for end in ("from", "to"):
            if as_str(r.get(end)) not in known:
                problems.append(f'relations[{i}].{end}: unknown id "{as_str(r.get(end))}"')
        if r.get("from") == r.get("to"):
            problems.append(f"relations[{i}]: from and to are the same")

    if len(source_ids) > 2000:
        problems.append("sources: more than 2000 entries")
    if len(claims) > 2000:
        problems.append("claims: more than 2000 entries")
    if lines > 10000:
        problems.append("claims: more than 10000 evidence lines in total")
    return problems


# ── main ─────────────────────────────────────────────────────────────────────


def _utf8_stdout() -> None:
    # gaviero reads the probe's output as UTF-8; a Windows pipe defaults to
    # the ANSI code page, which mangles "—" and cannot encode most scripts.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="findings_sidecar.py",
        description="Findings sidecar of deep-explore.gaviero: writes report.findings.json (academic-mcp "
        "findings-v1) and findings-build.json. Always exits 0; read findings-build.json for the status.",
    )
    parser.add_argument("out_dir", help="the run's OUT_DIR")
    return parser


def _run(out: Path) -> dict:
    if not out.is_dir():
        return {"status": "skipped", "problems": [f"{out}: not a directory"]}
    if not gate_common.versioned_files(out, "audit"):
        return {"status": "skipped", "problems": ["no audit-v*.json in OUT_DIR"]}
    sidecar, counts = build(out)
    path = out.resolve() / SIDECAR
    text = json.dumps(sidecar, indent=1, ensure_ascii=False) + "\n"
    problems = lint(sidecar)
    size = len(text.encode("utf-8"))
    if size > MAX_BYTES:
        problems.append(f"{SIDECAR}: {size} bytes, over the 5 MB limit")
    gate_common.write_text(path, text)
    return {
        "status": "ok" if not problems else "lint_failed",
        "path": str(path),
        "run_id": sidecar["run"]["id"],
        "counts": counts,
        "problems": problems,
    }


def main(argv: Optional[list] = None) -> int:
    _utf8_stdout()
    args = _parser().parse_args(argv)
    out = Path(args.out_dir)
    try:
        report = _run(out)
    except Exception as exc:  # noqa: BLE001 — a sidecar problem must never fail the report loop
        report = {
            "status": "error",
            "problems": [f"{type(exc).__name__}: {exc}"],
            "traceback": traceback.format_exc(limit=6),
        }
    if out.is_dir():
        try:
            gate_common.write_json(out / BUILD_LOG, report)
        except OSError as exc:
            report.setdefault("problems", []).append(f"{BUILD_LOG}: cannot write ({exc})")
    if report["status"] == "ok":
        counts = report["counts"]
        print(
            f"FINDINGS: wrote {SIDECAR} ({counts['claims']} claims, {counts['sources']} sources, "
            f"{counts['excluded_forbidden']} forbidden left out) and {BUILD_LOG}"
        )
    else:
        print(f"FINDINGS: {report['status'].upper()}: " + "; ".join(report.get("problems", []))[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
