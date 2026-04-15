#!/usr/bin/env python3
"""
Session A2: Extract speaker list from sessions_all_v2.json
- Build unique speaker profiles with session mappings
- Classify priority for Session B research
- Output speaker-list.json
"""
import json
import re
from collections import defaultdict

DATA_DIR = "/Users/YUANCHIEHCHANG/Desktop/五月EuroPCR/app-data"

with open(f"{DATA_DIR}/sessions_all_v2.json") as f:
    sessions = json.load(f)

# ── 1. Collect all speakers ──────────────────────────────────────
speaker_map = defaultdict(lambda: {
    "name": "",
    "sessions": [],           # [{id, title, day, role, track, type}]
    "roles": set(),
    "tracks": set(),
    "types": set(),
    "days": set(),
    "sessionCount": 0,
    "priority": "normal",     # will be set later
    "priorityReasons": [],
    "lbtPresenter": False,
    "liveOperator": False,
    "agendaSpeaker": False,
})

# Also collect agenda-level speakers (those giving specific talks)
agenda_speakers = defaultdict(list)  # name -> [{session_id, item}]

for s in sessions:
    day = s["day"]
    sid = s["id"]
    title = s.get("title", "")
    track = s.get("track", "")
    stype = s.get("type", "")
    
    # Session-level speakers
    if s.get("speakers") and isinstance(s["speakers"], dict):
        for role, names in s["speakers"].items():
            if not isinstance(names, list):
                continue
            for name in names:
                # Skip single-letter artifacts
                if len(name.strip()) <= 2:
                    continue
                # Skip obvious fragments
                if not re.search(r'[a-zA-Z]{2,}', name):
                    continue
                    
                sp = speaker_map[name]
                sp["name"] = name
                sp["sessions"].append({
                    "id": sid,
                    "title": title[:100],
                    "day": day,
                    "role": role,
                    "track": track,
                    "type": stype,
                })
                sp["roles"].add(role)
                sp["tracks"].add(track)
                sp["types"].add(stype)
                sp["days"].add(day)
    
    # Agenda-level speakers (people giving specific talks within a session)
    if s.get("agenda") and isinstance(s["agenda"], list):
        for item in s["agenda"]:
            sp_name = item.get("speaker")
            if sp_name and isinstance(sp_name, str) and len(sp_name.strip()) > 2:
                agenda_speakers[sp_name].append({
                    "sessionId": sid,
                    "item": item.get("item", "")[:120],
                    "day": day,
                })
                if sp_name in speaker_map:
                    speaker_map[sp_name]["agendaSpeaker"] = True

# ── 2. Finalize counts ──────────────────────────────────────────
for name, sp in speaker_map.items():
    # Only count Tue-Thu sessions
    tue_thu = [s for s in sp["sessions"] if s["day"] in ("Tuesday", "Wednesday", "Thursday")]
    sp["sessionCount"] = len(tue_thu)
    sp["sessionCountTotal"] = len(sp["sessions"])

# ── 3. Classify priority ────────────────────────────────────────

# Priority keywords for session titles (case-insensitive)
HIGH_RELEVANCE_KEYWORDS = [
    "left main", "complex pci", "tavi", "tavr", "transcatheter aortic",
    "structural heart", "aortic stenosis", "mitral", "tricuspid",
    "late-breaking", "hotline", "cto", "bifurcation",
    "live educational", "intravascular imaging", "ivus", "oct",
]

LBT_SESSION_ID = "WED-0945-BLEU-001"

# Known LBT presenters from manifest
LBT_PRESENTERS = {"R. Scarsini", "B. Bergmark", "J. E. Nielsen-Kudsk"}

for name, sp in speaker_map.items():
    reasons = []
    
    # ── LBT presenter ──
    if name in LBT_PRESENTERS:
        sp["lbtPresenter"] = True
        reasons.append("LBT presenter")
    
    # Check if they're in the LBT session at all
    for sess in sp["sessions"]:
        if sess["id"] == LBT_SESSION_ID:
            reasons.append("LBT session participant")
            break
    
    # ── LIVE case operator ──
    live_ops = [s for s in sp["sessions"] 
                if s["role"] == "operators" and s["type"] == "LIVE"]
    if live_ops:
        sp["liveOperator"] = True
        reasons.append(f"LIVE operator ({len(live_ops)} cases)")
    
    # ── High-frequency speaker (appears in many Tue-Thu sessions) ──
    if sp["sessionCount"] >= 5:
        reasons.append(f"High-frequency ({sp['sessionCount']} Tue-Thu sessions)")
    
    # ── Anchorperson/Spokesperson in high-relevance sessions ──
    key_roles = {"anchorpersons", "spokespersons", "operators"}
    for sess in sp["sessions"]:
        if sess["day"] not in ("Tuesday", "Wednesday", "Thursday"):
            continue
        if sess["role"] in key_roles:
            title_lower = sess["title"].lower()
            for kw in HIGH_RELEVANCE_KEYWORDS:
                if kw in title_lower:
                    reasons.append(f"Key role in '{kw}' session")
                    break
    
    # ── Hotline anchorperson/spokesperson ──
    hotline_key = [s for s in sp["sessions"] 
                   if s["type"] == "Hotline" and s["role"] in key_roles]
    if hotline_key:
        reasons.append(f"Hotline key role ({len(hotline_key)})")
    
    # ── Agenda speaker (gives named talks, not just chairs) ──
    if name in agenda_speakers:
        agenda_items = agenda_speakers[name]
        tue_thu_items = [a for a in agenda_items if a["day"] in ("Tuesday", "Wednesday", "Thursday")]
        if len(tue_thu_items) >= 3:
            reasons.append(f"Active agenda speaker ({len(tue_thu_items)} talks)")
    
    # Deduplicate reasons
    sp["priorityReasons"] = list(dict.fromkeys(reasons))
    
    # Set priority level
    if sp["lbtPresenter"]:
        sp["priority"] = "critical"  # Must research
    elif sp["liveOperator"] and sp["sessionCount"] >= 3:
        sp["priority"] = "high"
    elif len(reasons) >= 3:
        sp["priority"] = "high"
    elif len(reasons) >= 1:
        sp["priority"] = "medium"
    else:
        sp["priority"] = "normal"

# ── 4. Convert to list and sort ─────────────────────────────────
priority_order = {"critical": 0, "high": 1, "medium": 2, "normal": 3}

speaker_list = []
for name, sp in speaker_map.items():
    # Only include Tue-Thu speakers
    if sp["sessionCount"] == 0:
        continue
    speaker_list.append({
        "name": sp["name"],
        "priority": sp["priority"],
        "priorityReasons": sp["priorityReasons"],
        "sessionCount": sp["sessionCount"],
        "lbtPresenter": sp["lbtPresenter"],
        "liveOperator": sp["liveOperator"],
        "roles": sorted(sp["roles"]),
        "tracks": sorted(sp["tracks"]),
        "types": sorted(sp["types"]),
        "days": sorted(sp["days"]),
        "sessions": [s for s in sp["sessions"] if s["day"] in ("Tuesday", "Wednesday", "Thursday")],
    })

speaker_list.sort(key=lambda x: (priority_order.get(x["priority"], 9), -x["sessionCount"], x["name"]))

# ── 5. Summary stats ────────────────────────────────────────────
total = len(speaker_list)
by_priority = defaultdict(int)
for sp in speaker_list:
    by_priority[sp["priority"]] += 1

print(f"Total unique speakers (Tue-Thu): {total}")
print(f"  Critical (LBT presenters): {by_priority['critical']}")
print(f"  High (LIVE operators + multi-reason): {by_priority['high']}")
print(f"  Medium (some priority signals): {by_priority['medium']}")
print(f"  Normal (no special flags): {by_priority['normal']}")
print(f"\nResearch candidates (critical+high+medium): {by_priority['critical']+by_priority['high']+by_priority['medium']}")
print()

# Show critical + high speakers
print("=== CRITICAL speakers ===")
for sp in speaker_list:
    if sp["priority"] == "critical":
        print(f"  {sp['name']} ({sp['sessionCount']} sessions): {', '.join(sp['priorityReasons'])}")

print("\n=== HIGH priority speakers ===")
for sp in speaker_list:
    if sp["priority"] == "high":
        print(f"  {sp['name']} ({sp['sessionCount']} sessions): {', '.join(sp['priorityReasons'])}")

# ── 6. Write output ─────────────────────────────────────────────
output = {
    "generatedAt": "2026-04-14",
    "source": "sessions_all_v2.json",
    "totalSpeakers": total,
    "byPriority": dict(by_priority),
    "researchCandidates": by_priority["critical"] + by_priority["high"] + by_priority["medium"],
    "speakers": speaker_list,
}

with open(f"{DATA_DIR}/speaker-list.json", "w") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nWritten to {DATA_DIR}/speaker-list.json")

# Also write a compact research queue (just priority speakers)
research_queue = [sp for sp in speaker_list if sp["priority"] in ("critical", "high", "medium")]
with open(f"{DATA_DIR}/speaker-research-queue.json", "w") as f:
    json.dump({
        "total": len(research_queue),
        "byPriority": {
            "critical": by_priority["critical"],
            "high": by_priority["high"],
            "medium": by_priority["medium"],
        },
        "speakers": research_queue,
    }, f, ensure_ascii=False, indent=2)

print(f"Written research queue ({len(research_queue)} speakers) to {DATA_DIR}/speaker-research-queue.json")
