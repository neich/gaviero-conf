#!/usr/bin/env python3
"""Deterministic checker for the paper-review DSL workflow.

Runs as the loop's `until command`:

    python -I check_review.py <OUT_DIR> <ITER> <MAX_CLAIMS>

It validates the JSON artefacts of review pass ITER against the contracts
C2-C8 and rules R01-R27 of plans/paper-review-dsl/paper-review-dsl-v1.md.
It only reads files. Every problem is printed as one line
`ERROR <file>: <rule> <message>`; the exit code is 0 when the pass is
consistent, 1 when it is not and 2 on a usage error. The output is what the
next pass's agents see when the check fails.
"""

import glob
import json
import math
import os
import re
import sys

LABELS = ["supported", "partially_supported", "unsupported", "contradicted", "cannot_assess"]
INTERNAL = ["substantiated", "overstated", "unsubstantiated", "cannot_assess"]
CLAIM_TYPES = ["result", "comparative", "method", "theory", "causal", "generalisation", "null_result"]
QUALIFIER_KEYS = ["scope", "conditions", "comparator", "quantifier", "threshold", "hedge"]
PROVENANCE = ["stated", "inferred", "default"]
EDGE_TYPES = ["supports", "depends_on", "contradicts", "elaborates", "same_as"]
LENSES = ["primary", "cross", "omissions", "novelty", "reconcile"]
EVIDENCE_LABELS = ["supports", "refutes", "not_enough_info"]
EVIDENCE_KINDS = ["fulltext", "abstract_only", "citation_context", "web"]
AUDIT_VERDICTS = ["verified", "partial", "not_supported", "cannot_verify"]
AUDIT_VIA = ["corpus", "fulltext", "abstract", "web"]
STATUSES = ["agreed", "resolved", "contested", "pending"]

ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
CLAIM_ID_RE = re.compile(r"^c\d{2}$")
BIB_ID_RE = re.compile(r"^b\d{2,3}$")
TOLERANCE = 1e-6

USAGE = "usage: python -I check_review.py <OUT_DIR> <ITER> <MAX_CLAIMS>"


def is_str(value, non_empty=False):
    return isinstance(value, str) and (not non_empty or value.strip() != "")


def is_num(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def is_str_list(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


class Checker:
    def __init__(self, out_dir, n, max_claims):
        self.out = out_dir
        self.n = n
        self.max_claims = max_claims
        self.errors = []
        self.bib_ids = None
        self.claim_ids = []
        self.deps = {}
        self.has_cycle = False
        self.queue = []
        self.reviews = {}
        self.prev_status = None

    # ── helpers ──────────────────────────────────────────────────────────
    def err(self, rel, rule, message):
        self.errors.append(f"ERROR {rel}: {rule} {message}")

    def load(self, rel, rule):
        path = os.path.join(self.out, rel)
        if not os.path.isfile(path):
            self.err(rel, rule, "missing file")
            return None
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError) as exc:
            self.err(rel, rule, f"invalid JSON: {exc}")
            return None

    def review_files(self, item_id):
        """Every reviews/<item_id>-v<k>.json file, any pass."""
        folder = os.path.join(self.out, "reviews")
        if not os.path.isdir(folder):
            return []
        pattern = re.compile(r"^" + re.escape(item_id) + r"-v\d+\.json$")
        return sorted(name for name in os.listdir(folder) if pattern.match(name))

    def read_review_file(self, name):
        path = os.path.join(self.out, "reviews", name)
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    # ── C2: bibliography.json (R05) ──────────────────────────────────────
    def check_bibliography(self):
        rel = "bibliography.json"
        data = self.load(rel, "R05")
        if data is None:
            return
        entries = data.get("entries") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            self.err(rel, "R05", "`entries` must be an array")
            return
        ids = set()
        for i, entry in enumerate(entries):
            where = f"entries[{i}]"
            if not isinstance(entry, dict):
                self.err(rel, "R05", f"{where} must be an object")
                continue
            bid = entry.get("id")
            if not is_str(bid) or not BIB_ID_RE.match(bid):
                self.err(rel, "R05", f"{where}.id {bid!r} must match ^b\\d{{2,3}}$")
            elif bid in ids:
                self.err(rel, "R05", f"duplicate id {bid}")
            else:
                ids.add(bid)
            if not is_str(entry.get("raw")):
                self.err(rel, "R05", f"{where}.raw must be a string")
            if not is_str(entry.get("title")):
                self.err(rel, "R05", f"{where}.title must be a string")
            if "year" not in entry or not (entry["year"] is None or is_int(entry["year"])):
                self.err(rel, "R05", f"{where}.year must be an int or null")
            if "work_id" not in entry or not (entry["work_id"] is None or is_str(entry["work_id"])):
                self.err(rel, "R05", f"{where}.work_id must be a string or null")
            if not isinstance(entry.get("resolved"), bool):
                self.err(rel, "R05", f"{where}.resolved must be a bool")
            if "retracted" not in entry or not (
                entry["retracted"] is None or isinstance(entry["retracted"], bool)
            ):
                self.err(rel, "R05", f"{where}.retracted must be a bool or null")
        self.bib_ids = ids

    # ── C3: claims.json (R01-R04) ────────────────────────────────────────
    def check_claims(self):
        rel = "claims.json"
        data = self.load(rel, "R03")
        if data is None:
            return
        if not isinstance(data, dict):
            self.err(rel, "R03", "top level must be an object")
            return
        paper = data.get("paper")
        if not isinstance(paper, dict) or not is_str(paper.get("title")):
            self.err(rel, "R03", "`paper` must be an object with a string `title`")
        claims = data.get("claims")
        if not isinstance(claims, list):
            self.err(rel, "R03", "`claims` must be an array")
            return
        if not 1 <= len(claims) <= self.max_claims:
            self.err(
                rel,
                "R01",
                f"{len(claims)} claims; allowed 1..MAX_CLAIMS (MAX_CLAIMS={self.max_claims})",
            )
        seen = set()
        for i, claim in enumerate(claims):
            where = f"claims[{i}]"
            if not isinstance(claim, dict):
                self.err(rel, "R03", f"{where} must be an object")
                continue
            cid = claim.get("id")
            if not is_str(cid) or not CLAIM_ID_RE.match(cid):
                self.err(rel, "R02", f"{where}.id {cid!r} must match ^c\\d{{2}}$")
            elif cid in seen:
                self.err(rel, "R02", f"duplicate claim id {cid}")
            else:
                seen.add(cid)
                self.claim_ids.append(cid)
                where = cid
            for key in ("text", "quote", "locator"):
                if not is_str(claim.get(key), non_empty=True):
                    self.err(rel, "R03", f"{where}.{key} must be a non-empty string")
            if claim.get("type") not in CLAIM_TYPES:
                self.err(rel, "R03", f"{where}.type {claim.get('type')!r} not in {CLAIM_TYPES}")
            if claim.get("attribution") not in ("own", "reported"):
                self.err(rel, "R03", f"{where}.attribution must be own|reported")
            qualifiers = claim.get("qualifiers")
            if not isinstance(qualifiers, dict) or any(
                not is_str(qualifiers.get(k)) for k in QUALIFIER_KEYS
            ):
                self.err(rel, "R03", f"{where}.qualifiers needs string keys {QUALIFIER_KEYS}")
            provenance = claim.get("qualifier_provenance")
            if not isinstance(provenance, dict) or any(
                provenance.get(k) not in PROVENANCE for k in QUALIFIER_KEYS
            ):
                self.err(
                    rel,
                    "R03",
                    f"{where}.qualifier_provenance needs keys {QUALIFIER_KEYS} with values {PROVENANCE}",
                )
            for key in ("paper_evidence", "cited_refs", "sub_claims"):
                if not is_str_list(claim.get(key)):
                    self.err(rel, "R03", f"{where}.{key} must be an array of strings")
            refs = claim.get("cited_refs")
            if self.bib_ids is not None and is_str_list(refs):
                for ref in refs:
                    if ref not in self.bib_ids:
                        self.err(rel, "R04", f"{where}.cited_refs names {ref!r}, not in bibliography.json")

    # ── C4: graph.json (R06-R07) ─────────────────────────────────────────
    def check_graph(self):
        rel = "graph.json"
        self.deps = {cid: [] for cid in self.claim_ids}
        data = self.load(rel, "R06")
        if data is None:
            return
        edges = data.get("edges") if isinstance(data, dict) else None
        if not isinstance(edges, list):
            self.err(rel, "R06", "`edges` must be an array")
            return
        known = set(self.claim_ids)
        for i, edge in enumerate(edges):
            where = f"edges[{i}]"
            if not isinstance(edge, dict):
                self.err(rel, "R06", f"{where} must be an object")
                continue
            src, dst, kind = edge.get("from"), edge.get("to"), edge.get("type")
            ok = True
            if src not in known or dst not in known:
                self.err(rel, "R06", f"{where} endpoints {src!r} -> {dst!r} must be known claim ids")
                ok = False
            elif src == dst:
                self.err(rel, "R06", f"{where} is a self-loop on {src}")
                ok = False
            if kind not in EDGE_TYPES:
                self.err(rel, "R06", f"{where}.type {kind!r} not in {EDGE_TYPES}")
                ok = False
            if not is_str(edge.get("anchor"), non_empty=True):
                self.err(rel, "R06", f"{where}.anchor must be a non-empty string")
            confidence = edge.get("confidence")
            if not is_num(confidence) or not 0 <= confidence <= 1:
                self.err(rel, "R06", f"{where}.confidence must be a number in [0,1]")
            if ok and kind == "depends_on":
                self.deps[src].append(dst)
        cycle = self.find_cycle()
        if cycle:
            self.has_cycle = True
            self.err(rel, "R07", "depends_on edges form a cycle: " + " -> ".join(cycle))

    def find_cycle(self):
        state = {cid: 0 for cid in self.deps}  # 0 new, 1 on stack, 2 done
        stack = []

        def visit(node):
            state[node] = 1
            stack.append(node)
            for nxt in self.deps.get(node, []):
                if state.get(nxt, 0) == 1:
                    return stack[stack.index(nxt):] + [nxt]
                if state.get(nxt, 0) == 0:
                    found = visit(nxt)
                    if found:
                        return found
            stack.pop()
            state[node] = 2
            return None

        for cid in list(self.deps):
            if state[cid] == 0:
                found = visit(cid)
                if found:
                    return found
        return None

    # ── C5: queue-v<N>.json (R08-R11) ────────────────────────────────────
    def check_queue(self):
        rel = f"queue-v{self.n}.json"
        data = self.load(rel, "R08")
        if data is None:
            return
        if not isinstance(data, list):
            self.err(rel, "R08", "the queue must be a JSON array")
            return
        known = set(self.claim_ids)
        ids = set()
        for i, item in enumerate(data):
            where = f"[{i}]"
            if not isinstance(item, dict):
                self.err(rel, "R08", f"{where} must be an object")
                continue
            extra = set(item) - {"id", "claim", "lens", "note", "tier"}
            missing = {"id", "claim", "lens", "note"} - set(item)
            if extra or missing:
                self.err(
                    rel,
                    "R08",
                    f"{where} keys must be id/claim/lens/note (+ optional tier); "
                    f"extra {sorted(extra)}, missing {sorted(missing)}",
                )
            iid = item.get("id")
            if not is_str(iid) or not ITEM_ID_RE.match(iid):
                self.err(rel, "R08", f"{where}.id {iid!r} is not a valid item id")
                continue
            if iid in ids:
                self.err(rel, "R08", f"duplicate item id {iid}")
                continue
            ids.add(iid)
            where = iid
            if not is_str(item.get("note"), non_empty=True):
                self.err(rel, "R08", f"{where}.note must be a non-empty string")
            if "tier" in item and not is_str(item.get("tier"), non_empty=True):
                self.err(rel, "R08", f"{where}.tier must be a non-empty string")
            lens, claim = item.get("lens"), item.get("claim")
            if lens not in LENSES:
                self.err(rel, "R08", f"{where}.lens {lens!r} not in {LENSES}")
                continue
            paper_lens = lens in ("omissions", "novelty")
            if paper_lens != (claim == "paper"):
                self.err(rel, "R09", f"{where}: claim must be \"paper\" iff lens is omissions or novelty")
            if not paper_lens and claim not in known:
                self.err(rel, "R09", f"{where}.claim {claim!r} is not a claim id")
            expected = {
                "primary": f"{claim}-a",
                "cross": f"{claim}-b",
                "omissions": "paper-omissions",
                "novelty": "paper-novelty",
                "reconcile": f"{claim}-r{self.n}",
            }[lens]
            if iid != expected:
                self.err(rel, "R09", f"id {iid!r} should be {expected!r} for lens {lens}")
            self.queue.append(item)

        if self.n == 1:
            for cid in self.claim_ids:
                for lens in ("primary", "cross"):
                    count = sum(1 for q in self.queue if q.get("claim") == cid and q.get("lens") == lens)
                    if count != 1:
                        self.err(rel, "R10", f"pass 1 needs exactly one {lens} item for {cid} (found {count})")
            for lens in ("omissions", "novelty"):
                count = sum(1 for q in self.queue if q.get("lens") == lens)
                if count != 1:
                    self.err(rel, "R10", f"pass 1 needs exactly one {lens} item (found {count})")
            if any(q.get("lens") == "reconcile" for q in self.queue):
                self.err(rel, "R10", "pass 1 must not contain reconcile items")
        else:
            seen_claims = set()
            for q in self.queue:
                if q.get("lens") != "reconcile":
                    self.err(rel, "R11", f"pass {self.n} may contain only reconcile items, found {q.get('id')!r}")
                    continue
                cid = q.get("claim")
                if cid in seen_claims:
                    self.err(rel, "R11", f"more than one reconcile item for {cid}")
                seen_claims.add(cid)
                if self.prev_status is not None:
                    status = self.prev_status.get(cid)
                    if status != "pending":
                        self.err(
                            rel,
                            "R11",
                            f"{q.get('id')}: status of {cid} in ledger-v{self.n - 1}.json is "
                            f"{status!r}, not pending",
                        )

    def load_previous_ledger(self):
        if self.n < 2:
            return
        rel = f"ledger-v{self.n - 1}.json"
        data = self.load(rel, "R11")
        if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
            if data is not None:
                self.err(rel, "R11", "previous ledger has no `claims` array")
            return
        self.prev_status = {
            c.get("id"): c.get("status") for c in data["claims"] if isinstance(c, dict)
        }

    # ── C6: reviews (R12-R15) ────────────────────────────────────────────
    def check_reviews(self):
        for item in self.queue:
            iid = item["id"]
            rel = f"reviews/{iid}-v{self.n}.json"
            path = os.path.join(self.out, rel)
            if not os.path.isfile(path):
                self.err(rel, "R12", "missing review file for queue item")
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    review = json.load(fh)
            except (OSError, ValueError) as exc:
                self.err(rel, "R12", f"invalid JSON in review file: {exc}")
                continue
            if not isinstance(review, dict):
                self.err(rel, "R13", "review must be an object")
                continue
            self.reviews[iid] = review
            self.check_review(rel, item, review)

    def check_review(self, rel, item, review):
        paper = item.get("claim") == "paper"
        for key in ("item", "claim", "lens"):
            want = item.get("id") if key == "item" else item.get(key)
            if review.get(key) != want:
                self.err(rel, "R13", f"`{key}` is {review.get(key)!r}, expected {want!r}")
        if review.get("pass") != self.n or not is_int(review.get("pass")):
            self.err(rel, "R13", f"`pass` is {review.get('pass')!r}, expected {self.n}")
        outcome = review.get("outcome")
        if outcome not in ("done", "blocked"):
            self.err(rel, "R13", f"`outcome` {outcome!r} must be done|blocked")
        if not is_str(review.get("blocked_reason")):
            self.err(rel, "R13", "`blocked_reason` must be a string")
        elif outcome == "blocked" and not review["blocked_reason"].strip():
            self.err(rel, "R13", "`blocked_reason` must be non-empty when outcome is blocked")
        label, internal = review.get("label"), review.get("internal")
        if label not in LABELS + ["n/a"]:
            self.err(rel, "R13", f"`label` {label!r} not in {LABELS + ['n/a']}")
        if internal not in INTERNAL + ["n/a"]:
            self.err(rel, "R13", f"`internal` {internal!r} not in {INTERNAL + ['n/a']}")
        if (label == "n/a") != paper or (internal == "n/a") != paper:
            self.err(rel, "R13", "`label` and `internal` must be n/a iff the claim is \"paper\"")
        if review.get("confidence") not in ("high", "medium", "low"):
            self.err(rel, "R13", "`confidence` must be high|medium|low")
        score = review.get("base_score")
        if paper or outcome == "blocked":
            if score is not None:
                self.err(rel, "R13", "`base_score` must be null for paper-level or blocked reviews")
        elif not is_num(score) or not 0 <= score <= 1:
            self.err(rel, "R13", "`base_score` must be a number in [0,1]")
        for key in ("evidence", "findings", "new_evidence", "search_log"):
            if not isinstance(review.get(key), list):
                self.err(rel, "R13", f"`{key}` must be an array")
        if not isinstance(review.get("changed_from_previous"), bool):
            self.err(rel, "R13", "`changed_from_previous` must be a bool")
        if not is_str(review.get("change_reason")):
            self.err(rel, "R13", "`change_reason` must be a string")
        for i, ev in enumerate(review.get("evidence") or []):
            self.check_evidence(rel, i, ev)
        if review.get("changed_from_previous") is True and not review.get("new_evidence"):
            self.err(rel, "R15", "`changed_from_previous` is true but `new_evidence` is empty")

    def check_evidence(self, rel, i, ev):
        where = f"evidence[{i}]"
        if not isinstance(ev, dict):
            self.err(rel, "R14", f"{where} must be an object")
            return
        for key in ("work_id", "title", "passage", "locator"):
            if not is_str(ev.get(key)):
                self.err(rel, "R14", f"{where}.{key} must be a string")
        if "year" not in ev or not (ev["year"] is None or is_int(ev["year"])):
            self.err(rel, "R14", f"{where}.year must be an int or null")
        if ev.get("label") not in EVIDENCE_LABELS:
            self.err(rel, "R14", f"{where}.label {ev.get('label')!r} not in {EVIDENCE_LABELS}")
        if ev.get("evidence") not in EVIDENCE_KINDS:
            self.err(rel, "R14", f"{where}.evidence {ev.get('evidence')!r} not in {EVIDENCE_KINDS}")
        if not isinstance(ev.get("retracted"), bool):
            self.err(rel, "R14", f"{where}.retracted must be a bool")
        passage = ev.get("passage")
        if is_str(passage):
            words = len(passage.split())
            if words > 40:
                self.err(rel, "R14", f"{where}.passage has {words} words (max 40 words)")

    # ── C7: audit-v<N>.json (R16) ────────────────────────────────────────
    def check_audit(self):
        rel = f"audit-v{self.n}.json"
        data = self.load(rel, "R16")
        if data is None:
            return
        if not isinstance(data, dict):
            self.err(rel, "R16", "audit must be an object")
            return
        if data.get("pass") != self.n:
            self.err(rel, "R16", f"audit `pass` is {data.get('pass')!r}, expected {self.n}")
        queue_ids = [q["id"] for q in self.queue]
        reviews = data.get("reviews")
        if not isinstance(reviews, list):
            self.err(rel, "R16", "audit `reviews` must be an array")
        else:
            counts = {}
            for i, entry in enumerate(reviews):
                if not isinstance(entry, dict):
                    self.err(rel, "R16", f"audit reviews[{i}] must be an object")
                    continue
                iid = entry.get("item")
                counts[iid] = counts.get(iid, 0) + 1
                if not isinstance(entry.get("usable"), bool) or not is_str(entry.get("note")):
                    self.err(rel, "R16", f"audit reviews[{i}] needs bool `usable` and string `note`")
                if iid not in queue_ids:
                    self.err(rel, "R16", f"audit reviews entry for unknown item {iid!r}")
            for iid in queue_ids:
                if counts.get(iid, 0) != 1:
                    self.err(rel, "R16", f"audit needs exactly one reviews entry for {iid} (found {counts.get(iid, 0)})")
        expected = set()
        for iid, review in self.reviews.items():
            evidence = review.get("evidence")
            if isinstance(evidence, list):
                expected.update((iid, k) for k in range(len(evidence)))
        loaded = set(self.reviews)
        evidence = data.get("evidence")
        if not isinstance(evidence, list):
            self.err(rel, "R16", "audit `evidence` must be an array")
            return
        seen = {}
        for i, entry in enumerate(evidence):
            if not isinstance(entry, dict):
                self.err(rel, "R16", f"audit evidence[{i}] must be an object")
                continue
            key = (entry.get("item"), entry.get("index"))
            seen[key] = seen.get(key, 0) + 1
            if entry.get("verdict") not in AUDIT_VERDICTS:
                self.err(rel, "R16", f"audit evidence[{i}].verdict {entry.get('verdict')!r} not in {AUDIT_VERDICTS}")
            if entry.get("checked_via") not in AUDIT_VIA:
                self.err(rel, "R16", f"audit evidence[{i}].checked_via {entry.get('checked_via')!r} not in {AUDIT_VIA}")
            if not is_str(entry.get("reason")):
                self.err(rel, "R16", f"audit evidence[{i}].reason must be a string")
            if not isinstance(entry.get("resolved"), bool) or not isinstance(entry.get("retracted"), bool):
                self.err(rel, "R16", f"audit evidence[{i}] needs bool `resolved` and `retracted`")
            if key not in expected and key[0] in loaded:
                self.err(rel, "R16", f"audit evidence entry for unknown evidence {key[0]}#{key[1]}")
        for key in sorted(expected, key=lambda k: (str(k[0]), k[1])):
            if seen.get(key, 0) != 1:
                self.err(
                    rel,
                    "R16",
                    f"audit needs exactly one evidence entry for {key[0]}#{key[1]} (found {seen.get(key, 0)})",
                )

    # ── C8: ledger-v<N>.json (R17-R27) ───────────────────────────────────
    def check_ledger(self):
        rel = f"ledger-v{self.n}.json"
        data = self.load(rel, "R17")
        if data is None:
            return 0
        if not isinstance(data, dict):
            self.err(rel, "R17", "ledger must be an object")
            return 0
        if data.get("pass") != self.n:
            self.err(rel, "R17", f"ledger `pass` is {data.get('pass')!r}, expected {self.n}")
        claims = data.get("claims")
        if not isinstance(claims, list):
            self.err(rel, "R17", "ledger `claims` must be an array")
            return 0
        entries = {}
        for i, entry in enumerate(claims):
            if not isinstance(entry, dict):
                self.err(rel, "R17", f"claims[{i}] must be an object")
                continue
            cid = entry.get("id")
            if cid in entries:
                self.err(rel, "R17", f"claim {cid!r} appears more than once")
                continue
            if cid not in self.claim_ids:
                self.err(rel, "R17", f"claim {cid!r} is not in claims.json")
                continue
            entries[cid] = entry
        for cid in self.claim_ids:
            if cid not in entries:
                self.err(rel, "R17", f"claim {cid} has no ledger entry")

        required = (
            "status", "label", "round0", "counted_reviews", "reconcile_reviews", "flips",
            "base_strength", "propagated_strength", "positions", "settling_evidence",
        )
        for cid, entry in entries.items():
            missing = [k for k in required if k not in entry]
            if missing:
                self.err(rel, "R17", f"{cid} is missing keys {missing}")
            self.check_ledger_entry(rel, cid, entry)

        if not self.has_cycle:
            self.check_propagation(rel, entries)

        pending = sorted(cid for cid, e in entries.items() if e.get("status") == "pending")
        open_claims = data.get("open_claims")
        if not is_str_list(open_claims) or sorted(open_claims) != pending:
            self.err(rel, "R26", f"open_claims is {open_claims!r}, expected {pending!r}")

        paper = data.get("paper")
        if not isinstance(paper, dict):
            self.err(rel, "R27", "`paper` must be an object")
        else:
            if paper.get("claims_total") != len(self.claim_ids):
                self.err(rel, "R27", f"paper.claims_total is {paper.get('claims_total')!r}, expected {len(self.claim_ids)}")
            for status in STATUSES:
                count = sum(1 for e in entries.values() if e.get("status") == status)
                if paper.get(status) != count:
                    self.err(rel, "R27", f"paper.{status} is {paper.get(status)!r}, expected {count}")
            for key in ("omissions_review", "novelty_review"):
                value = paper.get(key, "<missing>")
                if value is None:
                    continue
                if not is_str(value) or not self.review_files(value):
                    self.err(rel, "R27", f"paper.{key} {value!r} must be null or an existing review id")
        return len(pending)

    def check_ledger_entry(self, rel, cid, entry):
        status, label = entry.get("status"), entry.get("label")
        if status not in STATUSES:
            self.err(rel, "R18", f"{cid}.status {status!r} not in {STATUSES}")
        if label is not None and label not in LABELS:
            self.err(rel, "R18", f"{cid}.label {label!r} not in {LABELS} or null")
        if (label is not None) != (status in ("agreed", "resolved")):
            self.err(rel, "R18", f"{cid}.label must be non-null iff status is agreed or resolved")

        round0 = entry.get("round0")
        reconcile = entry.get("reconcile_reviews")
        flips = entry.get("flips")
        positions = entry.get("positions")
        if status == "agreed":
            ok = (
                isinstance(round0, dict)
                and round0.get("primary") is not None
                and round0.get("primary") == round0.get("cross") == label
            )
            if not ok:
                self.err(rel, "R19", f"{cid} is agreed but round0 {round0!r} does not equal label {label!r}")
        if status == "resolved":
            ok = (
                isinstance(reconcile, list) and reconcile
                and isinstance(flips, list) and flips
                and all(isinstance(f, dict) and f.get("new_evidence") for f in flips)
                and isinstance(flips[-1], dict) and flips[-1].get("to") == label
            )
            if not ok:
                self.err(
                    rel,
                    "R20",
                    f"{cid} is resolved but needs reconcile_reviews, flips with non-empty "
                    f"new_evidence, and label equal to the last flip's `to`",
                )
        if status == "contested":
            labels = [p.get("label") for p in positions if isinstance(p, dict)] if isinstance(positions, list) else []
            ok = (
                len(labels) >= 2
                and all(lab in LABELS for lab in labels)
                and len(set(labels)) == len(labels)
                and is_str(entry.get("settling_evidence"), non_empty=True)
            )
            if not ok:
                self.err(rel, "R21", f"{cid} is contested but needs >= 2 positions with distinct labels and settling_evidence")
        if status == "pending" and isinstance(reconcile, list) and len(reconcile) >= 2:
            self.err(rel, "R22", f"{cid} is pending with {len(reconcile)} reconcile reviews (max 1)")

        counted = entry.get("counted_reviews")
        for key, ids in (("counted_reviews", counted), ("reconcile_reviews", reconcile)):
            if not is_str_list(ids):
                self.err(rel, "R23", f"{cid}.{key} must be an array of review ids")
                continue
            for rid in ids:
                files = self.review_files(rid)
                if len(files) != 1:
                    self.err(rel, "R23", f"{cid}.{key} names {rid!r}: expected one reviews/{rid}-v*.json, found {len(files)}")
                elif key == "counted_reviews":
                    review = self.read_review_file(files[0])
                    if not isinstance(review, dict) or review.get("outcome") != "done":
                        self.err(rel, "R23", f"{cid}.counted_reviews names {rid!r}, whose outcome is not done")

        scores = []
        if is_str_list(counted):
            for rid in counted:
                files = self.review_files(rid)
                if len(files) == 1:
                    review = self.read_review_file(files[0])
                    if isinstance(review, dict) and is_num(review.get("base_score")):
                        scores.append(review["base_score"])
        expected = sum(scores) / len(scores) if scores else None
        base = entry.get("base_strength")
        if expected is None:
            if base is not None:
                self.err(rel, "R24", f"{cid}.base_strength must be null (no counted base_score)")
        elif not is_num(base) or abs(base - expected) > TOLERANCE:
            self.err(rel, "R24", f"{cid}.base_strength is {base!r}, expected {expected:.6f}")

    def check_propagation(self, rel, entries):
        computed = {}

        def value(cid):
            if cid in computed:
                return computed[cid]
            entry = entries.get(cid, {})
            base = entry.get("base_strength")
            if not is_num(base):
                computed[cid] = None
                return None
            result = base
            for target in self.deps.get(cid, []):
                target_value = value(target)
                if target_value is not None:
                    result = min(result, target_value)
            computed[cid] = result
            return result

        for cid, entry in entries.items():
            expected = value(cid)
            given = entry.get("propagated_strength")
            if expected is None:
                if given is not None:
                    self.err(rel, "R25", f"{cid}.propagated_strength must be null when base_strength is null")
            elif not is_num(given) or abs(given - expected) > TOLERANCE:
                self.err(rel, "R25", f"{cid}.propagated_strength is {given!r}, expected {expected:.6f}")

    # ── driver ───────────────────────────────────────────────────────────
    def run(self):
        self.check_bibliography()
        self.check_claims()
        self.check_graph()
        self.load_previous_ledger()
        self.check_queue()
        self.check_reviews()
        self.check_audit()
        pending = self.check_ledger()
        return pending


def parse_positive_int(text):
    try:
        value = int(text)
    except ValueError:
        return None
    return value if value > 0 else None


def main(argv):
    if len(argv) != 4:
        print(USAGE, file=sys.stderr)
        return 2
    out_dir = argv[1]
    n = parse_positive_int(argv[2])
    max_claims = parse_positive_int(argv[3])
    if n is None or max_claims is None:
        print(USAGE, file=sys.stderr)
        return 2
    checker = Checker(out_dir, n, max_claims)
    pending = checker.run()
    if checker.errors:
        for line in checker.errors:
            print(line)
        print(f"FAIL {len(checker.errors)} problem(s) in pass {n}")
        return 1
    print(
        f"OK pass {n}: {len(checker.claim_ids)} claims, "
        f"{len(checker.queue)} queue items, {pending} pending"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
