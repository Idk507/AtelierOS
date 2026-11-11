"""Validate proposed P00 schemas and synthetic oracles; never call providers."""
from __future__ import annotations

import copy
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "packages/evaluation/p00"
JOURNEYS = ("research-to-design", "material-substitution", "sample-feedback")


def load(path: Path) -> dict:
    """Read a local JSON document; parse and I/O failures fail validation."""
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    """Raise a stable validation failure, including under optimized Python."""
    if not condition:
        raise ValueError(message)


def validator(path: Path) -> Draft202012Validator:
    """Check the schema itself before validating instances and formats."""
    schema = load(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_scenario(data: dict) -> None:
    """Check structure, lineage, locked geometry, evidence links and cost oracle."""
    validator(FIXTURES / "scenario.schema.json").validate(data)
    sources = {s["source_id"] for s in data["sources"]}
    require(len(sources) == len(data["sources"]), "duplicate source id")
    revisions = data["revisions"]
    ids = {r["id"] for r in revisions}
    require(len(ids) == len(revisions), "duplicate revision id")
    previous = None
    locked: dict = {}
    for revision in revisions:
        payload = {k: v for k, v in revision.items() if k != "hash"}
        digest = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")).hexdigest()
        require(digest == revision["hash"], "revision hash mismatch")
        require(revision["parent_revision_id"] == previous, "broken revision lineage")
        components = {c["id"]: c for c in revision["components"]}
        require(len(components) == len(revision["components"]), "duplicate component id")
        for component_id, baseline in locked.items():
            require(components.get(component_id) == baseline, "locked component changed")
        locked.update({k: v for k, v in components.items() if v["locked"]})
        previous = revision["id"]
    require(data["expected_approved_revision_id"] == revisions[0]["id"],
            "draft fixture silently advances approval")
    case_ids = [c["id"] for c in data["cases"]]
    require(len(set(case_ids)) == len(case_ids), "duplicate case id")
    require(all(c["base_revision"] in ids for c in data["cases"]), "unknown case revision")
    details = data["details"]
    if data["journey"] == "material-substitution":
        candidates = details["candidates"]
        require(len({c["id"] for c in candidates}) == 3, "duplicate material candidate")
        for candidate in candidates:
            require(candidate["source_id"] in sources, "unknown catalog source")
            stretch = candidate["stretch_percent"]
            expected = ("unknown" if stretch is None else "compatible"
                        if stretch >= details["hard_requirement_min_stretch_percent"]
                        else "incompatible")
            require(candidate["eligibility"] == expected, "false candidate eligibility")
        require({c["eligibility"] for c in candidates} ==
                {"compatible", "incompatible", "unknown"}, "missing alternative class")
        cost = details["cost"]
        selected = next(c for c in candidates if c["id"] == cost["candidate_id"])
        require(selected["eligibility"] == "compatible", "selected unqualified material")
        require(revisions[-1]["material_id"] == selected["id"], "wrong selected material")
        total = (Decimal(cost["length_m"]) * (1 + Decimal(cost["wastage_fraction"]))
                 * Decimal(selected["price_per_m"]) + Decimal(cost["trim"])
                 + Decimal(cost["other"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        require(total == Decimal(cost["expected_total"]), "cost oracle mismatch")
        require(set(data["invalidated_artifacts"]) == {"render", "bom", "spec"},
                "missing material dependency invalidation")
    elif data["journey"] == "research-to-design":
        require(details["claim"]["source_id"] in sources, "unresolved citation")
        require(details["claim"]["text"] in details["claim"]["source_span"],
                "claim not supported by synthetic snippet")
    else:
        require(details["sample_revision_id"] in ids, "unknown sample revision")
        require(details["feedback"]["component_id"] in
                {c["id"] for c in revisions[0]["components"]}, "unknown feedback component")


def main() -> None:
    """Validate the complete P00 package and reject deliberate corruptions."""
    for directory in (ROOT / ".claude", ROOT / "docs", FIXTURES):
        for path in directory.rglob("*.json"):
            load(path)
    for path in (ROOT / "docs/contracts").glob("*.schema.json"):
        validator(path)
    examples = ROOT / "docs/contracts/examples"
    validator(ROOT / "docs/contracts/patch.schema.json").validate(load(examples / "sleeve-patch.json"))
    for name in ("proposal-event", "commit-event"):
        validator(ROOT / "docs/contracts/event.schema.json").validate(load(examples / f"{name}.json"))
    approval = load(examples / "aesthetic-approval.json")
    validator(ROOT / "docs/contracts/approval.schema.json").validate(approval)
    fixtures = {name: load(FIXTURES / f"{name}.json") for name in JOURNEYS}
    for name, data in fixtures.items():
        require(data["journey"] == name, "fixture filename mismatch")
        validate_scenario(data)
    require(approval["content_hash"] ==
            fixtures["material-substitution"]["revisions"][-1]["hash"],
            "approval example must bind exact fixture revision")
    negative_count = 0
    mutations = [
        ("synthetic", lambda d: d.update(synthetic=False)),
        ("cost", lambda d: d["details"]["cost"].update(expected_total="1.00")),
        ("unknown evidence", lambda d: d["details"]["candidates"][2].update(eligibility="compatible")),
        ("locked geometry", lambda d: d["revisions"][1]["components"][0].update(geometry=[999])),
        ("lineage", lambda d: d["revisions"][1].update(parent_revision_id="missing")),
        ("commercial evidence", lambda d: d["sources"][0].update(verified_commercial_evidence=True)),
        ("invalidation", lambda d: d.update(invalidated_artifacts=[])),
        ("approval", lambda d: d.update(expected_approved_revision_id="r2")),
    ]
    for label, mutate in mutations:
        bad = copy.deepcopy(fixtures["material-substitution"])
        mutate(bad)
        # Rehash corrupt revisions so semantic checks, not just hash checks,
        # must catch broken locks and lineage.
        for revision in bad["revisions"]:
            payload = {k: v for k, v in revision.items() if k != "hash"}
            revision["hash"] = hashlib.sha256(json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")).hexdigest()
        try:
            validate_scenario(bad)
        except (ValueError, ValidationError, StopIteration):
            negative_count += 1
        else:
            raise ValueError(f"negative control accepted: {label}")
    adr_paths = sorted((ROOT / "docs/adr").glob("ADR-00[1-6]-*.md"))
    require(len(adr_paths) == 6, "expected six ADRs")
    for path in adr_paths:
        require("Status: PROPOSED" in path.read_text(encoding="utf-8"), "ADR auto-approved")
    print(f"PASS: 3 scenarios, 4 API/event examples, 6 proposed ADRs, {negative_count} rejected corruptions")
    print("STATIC ONLY: no PostgreSQL, browser, live provider or professional review evidence")


if __name__ == "__main__":
    main()
