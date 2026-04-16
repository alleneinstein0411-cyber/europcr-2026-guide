#!/usr/bin/env python3
"""
Remove single-character/bogus speaker-name fragments left over from PDF parsing.
Passes: sessions.json (speakers dict + agenda[].speaker) and
schedule.json (pick.keyNames + backups[].keyNames).
"""

import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SESSIONS = ROOT.parent / 'app' / 'data' / 'sessions.json'
SCHED    = ROOT.parent / 'app' / 'data' / 'schedule.json'

# A name looks fragmentary if it's only 1-2 chars or a single uppercase letter
# Also filter "A.", "B.", "F. J", "B. G. Libungan" (the last is OK since it has surname)
NAME_OK = re.compile(r'^[A-Z]\.?(\s+[A-Z]\.?)*\s+[A-Z][a-zA-ZüöäéèàÖçš\-\'’]{1,}')
# Alternative: reject if string after stripping doesn't contain any letter group of >=3 chars
def is_fragment(n):
    if not n: return True
    n = n.strip().rstrip('.,;:')
    if len(n) <= 2: return True
    # Reject pure initials like "F. J" (no multi-char token)
    # Look for any token of length >= 3 that is mixed case (likely surname)
    tokens = [t.strip('.,') for t in n.split()]
    has_surname = any(len(t) >= 3 and not t.isupper() and t[0].isupper() for t in tokens)
    return not has_surname


def clean_list(lst):
    if not isinstance(lst, list): return lst
    return [n for n in lst if not is_fragment(n)]


def main():
    s = json.loads(SESSIONS.read_text())
    total_cleaned = 0
    for sid, sess in s.items():
        sp = sess.get('speakers')
        if isinstance(sp, dict):
            for role, names in list(sp.items()):
                if isinstance(names, list):
                    new = clean_list(names)
                    removed = len(names) - len(new)
                    if removed:
                        total_cleaned += removed
                    sp[role] = new
        elif isinstance(sp, list):
            new = []
            for item in sp:
                n = item.get('name') if isinstance(item, dict) else item
                if not is_fragment(n):
                    new.append(item)
                else:
                    total_cleaned += 1
            sess['speakers'] = new
        # Agenda speakers
        for a in (sess.get('agenda') or []):
            spk = a.get('speaker')
            if spk and is_fragment(spk):
                a['speaker'] = None
                total_cleaned += 1

    SESSIONS.write_text(json.dumps(s, ensure_ascii=False, indent=2))
    print(f'sessions.json: removed {total_cleaned} fragment names')

    # Schedule
    sch = json.loads(SCHED.read_text())
    sch_cleaned = 0
    for day in sch.get('days', []):
        for blk in day.get('blocks', []):
            pick = blk.get('pick', {})
            if isinstance(pick.get('keyNames'), list):
                new = clean_list(pick['keyNames'])
                sch_cleaned += len(pick['keyNames']) - len(new)
                pick['keyNames'] = new
            for b in blk.get('backups', []) or []:
                if isinstance(b.get('keyNames'), list):
                    new = clean_list(b['keyNames'])
                    sch_cleaned += len(b['keyNames']) - len(new)
                    b['keyNames'] = new
    SCHED.write_text(json.dumps(sch, ensure_ascii=False, indent=2))
    print(f'schedule.json: removed {sch_cleaned} fragment keyNames')


if __name__ == '__main__':
    main()
