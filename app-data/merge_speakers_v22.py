#!/usr/bin/env python3
"""
Merge 4 new speaker batches (20 speakers) into speakers.json, normalize
fields to match existing schema, and add sessionIds reverse-lookup.

Existing schema used in speakers.json:
  name, fullName, institution, expertise[], tier ('S'|'A'|'B'),
  oneLiner, keyContributions[], whyListen,
  pmids[], sessionIds[],  ← we populate sessionIds by scanning sessions.json
  extendedBio, signatureWork, recentActivity, conversationStarter,
  recentPapers[{title, year, pmid, relevance}]
"""

import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
BATCHES = ROOT / 'speakers-batch-v22'
SPEAKERS_OUT = ROOT.parent / 'app' / 'data' / 'speakers.json'
SESSIONS = ROOT.parent / 'app' / 'data' / 'sessions.json'
BAK = ROOT / 'speakers.pre_v22.backup.json'


def find_session_ids_for(name, sessions):
    """Return list of session IDs where this speaker appears (any role / agenda)."""
    out = []
    needle = name.strip().lower()
    for sid, s in sessions.items():
        matched = False
        sp = s.get('speakers')
        if isinstance(sp, dict):
            for role_names in sp.values():
                if isinstance(role_names, list):
                    if any((n or '').strip().lower() == needle for n in role_names):
                        matched = True
                        break
        elif isinstance(sp, list):
            for item in sp:
                n = item.get('name') if isinstance(item, dict) else item
                if (n or '').strip().lower() == needle:
                    matched = True
                    break
        if not matched:
            for a in (s.get('agenda') or []):
                if (a.get('speaker') or '').strip().lower() == needle:
                    matched = True
                    break
        if matched:
            out.append(sid)
    return out


def normalize_speaker(raw, sessions):
    """Coerce new agent output into existing speakers.json shape."""
    name = raw['name']
    session_ids = find_session_ids_for(name, sessions)
    return {
        'name': name,
        'fullName': raw.get('fullName', ''),
        'institution': raw.get('institution', ''),
        'expertise': raw.get('expertise', []) or [],
        'tier': raw.get('tier', 'B'),
        'oneLiner': raw.get('oneLiner', ''),
        'keyContributions': raw.get('keyContributions', []) or [],
        'whyListen': raw.get('whyListen', ''),
        'pmids': raw.get('pmids', []) or [],
        'sessionIds': session_ids,
        'extendedBio': raw.get('extendedBio', ''),
        'signatureWork': raw.get('signatureWork', ''),
        'recentActivity': raw.get('recentActivity', ''),
        'conversationStarter': raw.get('conversationStarter', ''),
        'recentPapers': raw.get('recentPapers', []) or [],
    }


def main():
    speakers = json.loads(SPEAKERS_OUT.read_text())
    sessions = json.loads(SESSIONS.read_text())
    BAK.write_text(json.dumps(speakers, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Backed up existing speakers.json ({len(speakers)} speakers)')

    added, updated, total_session_ids = 0, 0, 0
    for batch_file in sorted(BATCHES.glob('batch_*.json')):
        batch = json.loads(batch_file.read_text())
        for key, raw in batch.items():
            normalized = normalize_speaker(raw, sessions)
            total_session_ids += len(normalized['sessionIds'])
            if key in speakers:
                updated += 1
                # preserve older data where agent might have skipped, but prefer new
                existing = speakers[key]
                # Merge PMIDs (union, keep order)
                merged_pmids = list(dict.fromkeys(existing.get('pmids', []) + normalized['pmids']))
                normalized['pmids'] = merged_pmids
                speakers[key] = normalized
            else:
                speakers[key] = normalized
                added += 1
            print(f'  {"UPD" if key in speakers and key != normalized["name"] else "ADD"} {key:25} tier={normalized["tier"]} sessions={len(normalized["sessionIds"])}')

    SPEAKERS_OUT.write_text(json.dumps(speakers, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nTotal: {added} added, {updated} updated. Now {len(speakers)} speakers in db.')
    print(f'Total session reverse-links across new speakers: {total_session_ids}')


if __name__ == '__main__':
    main()
