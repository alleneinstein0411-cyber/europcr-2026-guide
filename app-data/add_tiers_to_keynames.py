#!/usr/bin/env python3
"""
Append (S)/(A)/(B) tier suffix to schedule.json keyNames where the
speaker is researched but the suffix was missing. This makes the
chip badge colour show on every option in the schedule + edit view.
"""

import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SCHED = ROOT.parent / 'app' / 'data' / 'schedule.json'
SPEAKERS = ROOT.parent / 'app' / 'data' / 'speakers.json'

speakers = json.loads(SPEAKERS.read_text())
tiers = {n: v.get('tier') for n, v in speakers.items() if v.get('tier')}

sch = json.loads(SCHED.read_text())

added = 0
def patch(name_list):
    global added
    if not isinstance(name_list, list): return name_list
    out = []
    for n in name_list:
        m = re.match(r'^(.+?)\((S|A|B)\)$', n)
        if m:
            out.append(n)  # already tagged
            continue
        clean = n.strip()
        t = tiers.get(clean)
        if t:
            out.append(f'{clean}({t})')
            added += 1
        else:
            out.append(clean)
    return out

for day in sch.get('days', []):
    for blk in day.get('blocks', []):
        pick = blk.get('pick', {})
        if 'keyNames' in pick:
            pick['keyNames'] = patch(pick['keyNames'])
        for b in blk.get('backups', []) or []:
            if 'keyNames' in b:
                b['keyNames'] = patch(b['keyNames'])

SCHED.write_text(json.dumps(sch, ensure_ascii=False, indent=2))
print(f'Tagged {added} speaker names with tier suffix')
