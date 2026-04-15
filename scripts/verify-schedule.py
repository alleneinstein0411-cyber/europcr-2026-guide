#!/usr/bin/env python3
"""
verify-schedule.py — Sanity-check that all sessionIds referenced in
schedule_final.json still exist in sessions_all_v2.json.

Useful after a data refresh to ensure no schedule blocks point to
non-existent sessions.

Outputs: JSON to stdout.
Exit codes:
    0 — all sessions valid
    1 — some sessionIds missing
    2 — error
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
SRC = ROOT / "app-data"


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    try:
        sessions = load_json(SRC / "sessions_all_v2.json")
        schedule = load_json(SRC / "schedule_final.json")
    except Exception as err:
        print(json.dumps({"error": str(err)}, indent=2))
        return 2

    session_ids = {s["id"] for s in sessions}

    missing_picks = []
    missing_backups = []
    total_picks = 0
    total_backups = 0

    for day in schedule.get("days", []):
        for block in day.get("blocks", []):
            pick = block.get("pick", {})
            sid = pick.get("sessionId")
            if sid:
                total_picks += 1
                if sid not in session_ids:
                    missing_picks.append({
                        "day": day["day"],
                        "time": block.get("time"),
                        "sessionId": sid,
                        "title": pick.get("title"),
                    })
            for i, backup in enumerate(block.get("backups", []) or []):
                bsid = backup.get("sessionId")
                if bsid:
                    total_backups += 1
                    if bsid not in session_ids:
                        missing_backups.append({
                            "day": day["day"],
                            "time": block.get("time"),
                            "backupIdx": i,
                            "sessionId": bsid,
                            "title": backup.get("title"),
                        })

    result = {
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "totalPicks": total_picks,
        "totalBackups": total_backups,
        "totalSessions": len(session_ids),
        "missingPicks": missing_picks,
        "missingBackups": missing_backups,
        "healthy": len(missing_picks) == 0 and len(missing_backups) == 0,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["healthy"] else 1


if __name__ == "__main__":
    sys.exit(main())
