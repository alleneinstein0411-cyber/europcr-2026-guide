#!/usr/bin/env python3
"""
fix-speaker-names.py — Repair speaker name fragments created by PDF extraction.

Common issues:
    "H. C" + "Tan"  →  "H. C. Tan"   (period dropped after middle initial)
    "A. P. P" + "Venkatachalam"  →  similar
    "J. M" + "De La Torre Hernandez"  →  similar

This post-processes app-data/sessions_all_v2.json in-place. Idempotent:
re-running on already-fixed data is a no-op.

After running, re-run `python3 scripts/build-data.py` to regenerate app/data/.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "app-data" / "sessions_all_v2.json"

# Regex: a short initials-only name like "H. C" or "A. P. P" (ending without period)
INITIALS_FRAGMENT = re.compile(r"^[A-Z]\.(?:\s*[A-Z]\.?)*\s*[A-Z]$")

# Whitelist: never touch these names (they're legitimate short names)
KEEP_AS_IS = {"A.", "B.", "H.", "R.", "J."}  # not actually valid speakers anyway


def is_initials_fragment(s: str) -> bool:
    """E.g. 'H. C' (without trailing period) — likely truncated."""
    if not s or s in KEEP_AS_IS:
        return False
    return bool(INITIALS_FRAGMENT.match(s.strip()))


def is_surname_continuation(s: str) -> bool:
    """A plain surname-looking word that could complete a split name."""
    if not s:
        return False
    s = s.strip()
    # No initials, no period, capitalized, at least 2 chars
    return (
        len(s) >= 2
        and s[0].isupper()
        and "." not in s
        and not s.isupper()  # not an acronym
    )


def merge_fragments(names):
    """Scan through a list of names and merge initials fragments with next surname."""
    out = []
    i = 0
    while i < len(names):
        cur = names[i]
        if (
            i + 1 < len(names)
            and is_initials_fragment(cur)
            and is_surname_continuation(names[i + 1])
        ):
            merged = cur.rstrip(". ") + ". " + names[i + 1].strip()
            out.append(merged)
            i += 2
        else:
            out.append(cur)
            i += 1
    return out


def fix_sessions(data):
    """Walk all sessions and fix speakers + agenda speaker fields."""
    fixed_count = 0
    for session in data:
        speakers = session.get("speakers") or {}
        if isinstance(speakers, dict):
            for role, names in speakers.items():
                if isinstance(names, list):
                    new_names = merge_fragments(names)
                    if new_names != names:
                        fixed_count += len(names) - len(new_names)
                        speakers[role] = new_names

        # Agenda items' speaker field (comma-separated names)
        for item in session.get("agenda", []) or []:
            sp = item.get("speaker", "")
            if not sp:
                continue
            # Only apply if there's a comma-separated list
            if "," in sp:
                parts = [p.strip() for p in sp.split(",")]
                merged = merge_fragments(parts)
                if merged != parts:
                    item["speaker"] = ", ".join(merged)
                    fixed_count += len(parts) - len(merged)

    return fixed_count


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    count = fix_sessions(data)

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Fixed {count} split name fragments in {len(data)} sessions.")


if __name__ == "__main__":
    main()
