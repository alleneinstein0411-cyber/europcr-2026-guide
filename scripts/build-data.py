#!/usr/bin/env python3
"""
build-data.py — Merges source data from app-data/ into app/data/ for the web app.

Source files (read-only):
    app-data/sessions_all_v2.json           (588 sessions, raw extraction)
    app-data/speakers/batch-*.json          (60 researched speakers)
    app-data/trials/trials_intelligence_v1.json  (8 trials)
    app-data/schedule_final.json            (user's curated 20-block schedule)
    app-data/manifest.json                  (project metadata)

Output files (overwritten):
    app/data/sessions.json    (all 588, id-indexed)
    app/data/speakers.json    (researched speakers, name-indexed)
    app/data/trials.json      (trials, id-indexed)
    app/data/schedule.json    (curated schedule, day-grouped)
    app/data/meta.json        (build timestamp, counts, source file hashes)

Run from project root:
    python3 scripts/build-data.py
"""

import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
SRC = ROOT / "app-data"
DST = ROOT / "app" / "data"


def file_hash(path: Path) -> str:
    """Return SHA-256 hash of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def load_json(path: Path):
    """Load JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data, indent=None):
    """Write JSON with stable, compact output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent, separators=(",", ":") if not indent else None)


def build_sessions():
    """Index sessions by id, keep only attending days (Tue/Wed/Thu)."""
    raw = load_json(SRC / "sessions_all_v2.json")
    attending_days = {"Tuesday", "Wednesday", "Thursday"}
    by_id = {}
    skipped_friday = 0
    for s in raw:
        if s.get("day") not in attending_days:
            skipped_friday += 1
            continue
        by_id[s["id"]] = s
    print(f"  sessions: {len(by_id)} kept (+ {skipped_friday} Friday sessions excluded)")
    return by_id


def build_speakers():
    """Merge all speaker batches, index by name."""
    batch_dir = SRC / "speakers"
    by_name = {}
    batches_loaded = 0
    for batch_file in sorted(batch_dir.glob("batch-*.json")):
        batch = load_json(batch_file)
        batches_loaded += 1
        for sp in batch.get("speakers", []):
            name = sp.get("name")
            if not name:
                continue
            # Add batch provenance
            sp["_batch"] = batch_file.stem
            by_name[name] = sp
    print(f"  speakers: {len(by_name)} from {batches_loaded} batches")
    return by_name


def build_trials():
    """Load trial intelligence, index by trialId."""
    raw = load_json(SRC / "trials" / "trials_intelligence_v1.json")
    trials_list = raw.get("trials", [])
    by_id = {t["trialId"]: t for t in trials_list}
    print(f"  trials: {len(by_id)}")
    return by_id


def build_schedule():
    """Load curated schedule as-is (already well-structured)."""
    schedule = load_json(SRC / "schedule_final.json")
    total_blocks = sum(len(d.get("blocks", [])) for d in schedule.get("days", []))
    print(f"  schedule: {len(schedule['days'])} days, {total_blocks} blocks")
    return schedule


def build_meta():
    """Build metadata with source hashes and timestamp."""
    sources = {
        "sessions": SRC / "sessions_all_v2.json",
        "schedule": SRC / "schedule_final.json",
        "trials": SRC / "trials" / "trials_intelligence_v1.json",
        "manifest": SRC / "manifest.json",
    }
    source_hashes = {k: file_hash(v) for k, v in sources.items()}

    manifest = load_json(SRC / "manifest.json")

    return {
        "buildTime": datetime.now(timezone.utc).isoformat(),
        "dataVersion": "1.0",
        "projectStatus": manifest.get("status", "unknown"),
        "pdfVersion": manifest.get("pdfSource", {}).get("version", "unknown"),
        "conferenceDays": manifest.get("conferenceDays", []),
        "sourceHashes": source_hashes,
        "counts": {
            "sessions": 0,  # filled below
            "speakers": 0,
            "trials": 0,
            "scheduledBlocks": 0,
        },
    }


def main():
    print("Building app/data/ from app-data/...")
    print()

    print("Processing:")
    sessions = build_sessions()
    speakers = build_speakers()
    trials = build_trials()
    schedule = build_schedule()
    meta = build_meta()

    # Fill counts
    meta["counts"]["sessions"] = len(sessions)
    meta["counts"]["speakers"] = len(speakers)
    meta["counts"]["trials"] = len(trials)
    meta["counts"]["scheduledBlocks"] = sum(
        len(d.get("blocks", [])) for d in schedule.get("days", [])
    )

    print()
    print("Writing output to app/data/...")

    # Write compact (no indent) for production size
    write_json(DST / "sessions.json", sessions)
    write_json(DST / "speakers.json", speakers)
    write_json(DST / "trials.json", trials)
    write_json(DST / "schedule.json", schedule, indent=2)  # keep schedule human-readable
    write_json(DST / "meta.json", meta, indent=2)

    # Size report
    total_bytes = sum((DST / f).stat().st_size for f in
                      ["sessions.json", "speakers.json", "trials.json", "schedule.json", "meta.json"])
    print()
    print(f"Build complete. Total output: {total_bytes / 1024:.1f} KB")
    print()
    for f in sorted(DST.glob("*.json")):
        print(f"  {f.name:20s}  {f.stat().st_size / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
