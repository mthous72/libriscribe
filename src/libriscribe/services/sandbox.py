"""Sandbox staging (B27 Slice A) — per-run candidate staging with human cherry-pick.

Candidates NEVER touch the live KB until the author explicitly accepts them and applies the
run ("never auto-accept", locked decision). One JSON file per run under
``projects/<p>/sandbox/<run_id>.json`` (per-run granularity, locked). Candidate ``fields``
reuse the exact shape ``lore_intake.merge_apply`` consumes (incl. ``voice_*``), so applying
is just merge_apply over the accepted candidates — no new merge logic.

Run:       {id, created_at, seed: {kind, ...}, status: staged|applied|abandoned,
            applied_at, candidates: [Candidate]}
Candidate: {id, category: characters|locations|lore|arcs, name, op: new|update,
            fields: {...}, status: pending|accepted|rejected, source, rationale,
            confidence, evidence}
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from libriscribe.services.project_service import get_projects_dir

CATEGORIES = ("characters", "locations", "lore", "arcs", "worldbuilding")

# gap-finder entity_type -> sandbox category
_GAP_TYPE_TO_CATEGORY = {"character": "characters", "location": "locations",
                         "lore": "lore", "arc": "arcs", "thread": "arcs"}


def _dir(project_name: str) -> Path:
    return get_projects_dir() / project_name / "sandbox"


def _path(project_name: str, run_id: str) -> Path:
    return _dir(project_name) / f"{run_id}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save(project_name: str, run: dict) -> None:
    d = _dir(project_name)
    d.mkdir(parents=True, exist_ok=True)
    _path(project_name, run["id"]).write_text(json.dumps(run, indent=2), encoding="utf-8")


def new_candidate(category: str, name: str, fields: dict | None = None, *, op: str = "new",
                  source: str = "", rationale: str = "", evidence: str = "",
                  confidence: float | None = None) -> dict:
    return {
        "id": uuid.uuid4().hex[:8],
        "category": category if category in CATEGORIES else "lore",
        "name": str(name).strip(),
        "op": op if op in ("new", "update") else "new",
        "fields": dict(fields or {}),
        "status": "pending",     # never auto-accepted
        "source": source,
        "rationale": rationale,
        "confidence": confidence,
        "evidence": evidence,
    }


def create_run(project_name: str, seed: dict, candidates: list[dict]) -> dict:
    run = {
        "id": uuid.uuid4().hex[:8],
        "created_at": _now(),
        "seed": seed or {"kind": "manual"},
        "status": "staged",
        "applied_at": None,
        "candidates": [c for c in candidates if c.get("name")],
    }
    _save(project_name, run)
    return run


def list_runs(project_name: str) -> list[dict]:
    """Run metadata (no candidate bodies), newest first."""
    d = _dir(project_name)
    runs: list[dict] = []
    if d.exists():
        for f in d.glob("*.json"):
            try:
                r = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            counts: dict[str, int] = {"pending": 0, "accepted": 0, "rejected": 0}
            for c in r.get("candidates", []):
                counts[c.get("status", "pending")] = counts.get(c.get("status", "pending"), 0) + 1
            runs.append({
                "id": r["id"], "created_at": r.get("created_at", ""), "seed": r.get("seed", {}),
                "status": r.get("status", "staged"), "applied_at": r.get("applied_at"),
                "candidate_count": len(r.get("candidates", [])), "counts": counts,
            })
    runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return runs


def get_run(project_name: str, run_id: str) -> dict | None:
    p = _path(project_name, run_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def delete_run(project_name: str, run_id: str) -> bool:
    p = _path(project_name, run_id)
    if p.exists():
        p.unlink()
        return True
    return False


def update_candidate(project_name: str, run_id: str, candidate_id: str,
                     *, status: str | None = None, name: str | None = None,
                     fields: dict | None = None) -> dict | None:
    """Set a candidate's status (pending/accepted/rejected) and/or edit its name/fields."""
    run = get_run(project_name, run_id)
    if not run:
        return None
    for c in run.get("candidates", []):
        if c.get("id") == candidate_id:
            if status in ("pending", "accepted", "rejected"):
                c["status"] = status
            if name is not None and str(name).strip():
                c["name"] = str(name).strip()
            if fields is not None:
                c["fields"] = dict(fields)
            _save(project_name, run)
            return c
    return None


def apply_accepted(project_name: str, kb, run_id: str) -> dict[str, Any] | None:
    """Merge ONLY the accepted candidates into the KB (via lore_intake.merge_apply) and mark
    the run applied. Pending/rejected candidates are untouched. Returns the merge summary."""
    from libriscribe.services import lore_intake

    run = get_run(project_name, run_id)
    if not run:
        return None
    records: dict[str, Any] = {cat: [] for cat in CATEGORIES if cat != "worldbuilding"}
    wb_fields: dict[str, Any] = {}
    accepted = 0
    for c in run.get("candidates", []):
        if c.get("status") != "accepted":
            continue
        if c.get("category") == "worldbuilding":
            # merge_apply consumes worldbuilding as ONE {"fields": ...} dict, not a list
            wb_fields.update(c.get("fields", {}) or {})
            accepted += 1
        elif c.get("category") in records:
            records[c["category"]].append({"name": c["name"], "fields": c.get("fields", {})})
            accepted += 1
    if wb_fields:
        records["worldbuilding"] = {"fields": wb_fields}
    summary = lore_intake.merge_apply(kb, records) if accepted else {c: 0 for c in CATEGORIES}
    run["status"] = "applied"
    run["applied_at"] = _now()
    _save(project_name, run)
    return {"applied": accepted, "summary": summary}


def stage_gaps(project_name: str, gaps: list[dict], seed_kind: str = "gap_scan") -> dict:
    """Stage gap-finder findings (e.g. deep-scan undefined entities) as create-candidates —
    the gap→sandbox seed that makes B28's output actionable."""
    candidates = []
    for g in gaps or []:
        name = str(g.get("entity_name", "")).strip()
        if not name:
            continue
        category = _GAP_TYPE_TO_CATEGORY.get(str(g.get("entity_type", "")).lower(), "lore")
        candidates.append(new_candidate(
            category, name,
            op="update" if g.get("target") else "new",
            source=str(g.get("type", "gap")),
            rationale=str(g.get("message", "")),
            evidence=str(g.get("evidence", "")),
        ))
    return create_run(project_name, {"kind": seed_kind}, candidates)
