#!/usr/bin/env python3
"""Parse EuroPCR 2026 programme PDF text into structured JSON sessions."""

import json
import re
from collections import defaultdict

# --- Configuration ---

SPEAKER_ROLES_MAP = {
    'Anchorperson': 'anchorpersons',
    'Anchorpersons': 'anchorpersons',
    'Spokesperson': 'spokespersons',
    'Spokespersons': 'spokespersons',
    'Operator': 'operators',
    'Operators': 'operators',
    'Procedural Analyst': 'proceduralAnalysts',
    'Procedural Analysts': 'proceduralAnalysts',
    'Discussant': 'discussants',
    'Discussants': 'discussants',
    'Facilitator': 'facilitators',
    'Facilitators': 'facilitators',
    'Moderator': 'moderators',
    'Moderators': 'moderators',
    'Media Driver': 'mediaDrivers',
    'Media Drivers': 'mediaDrivers',
    'Physician Trainer': 'physicianTrainers',
    'Physician Trainers': 'physicianTrainers',
    'Experienced Advisor': 'experiencedAdvisors',
    'Experienced Advisors': 'experiencedAdvisors',
    'Cathlab Medical Coordinator': 'cathlabCoordinators',
    'Cathlab Medical Coordinators': 'cathlabCoordinators',
    'Onstage Medical Coordinator': 'onstageCoordinators',
    'Onstage Medical Coordinators': 'onstageCoordinators',
    'Guest speaker': 'guestSpeakers',
    'Guest speakers': 'guestSpeakers',
    'Imaging analyst': 'imagingAnalysts',
    'Imaging analysts': 'imagingAnalysts',
}

ROLE_KEYS = sorted(SPEAKER_ROLES_MAP.keys(), key=len, reverse=True)
ROLE_PATTERN = re.compile(
    r'^(' + '|'.join(re.escape(k) for k in ROLE_KEYS) + r'):\s*(.*)',
    re.IGNORECASE
)

TIME_PATTERN = re.compile(r'^(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$')

DAY_MAP = {
    'Monday': ('2026-05-18', 'MON'),
    'Tuesday': ('2026-05-19', 'TUE'),
    'Wednesday': ('2026-05-20', 'WED'),
    'Thursday': ('2026-05-21', 'THU'),
    'Friday': ('2026-05-22', 'FRI'),
}

# Room normalization
ROOM_STARTERS = [
    'MAIN ARENA', 'THEATRE BLEU', 'THEATRE BORDEAUX', 'ROOM MAILLOT',
    'ROOM ARLEQUIN', 'THE EXCHANGE', 'HANDS ON LAB',
    'ABSTRACT &', 'IMAGING SKILLS', 'CALCIUM SKILLS',
    'ROOM 342AB', 'ROOM 242AB', 'ROOM 252A', 'ROOM 252B',
    'ROOM 241', 'ROOM 243', 'ROOM 251', 'ROOM 252', 'ROOM 253',
    'ROOM 341', 'ROOM 343', 'ROOM 351', 'ROOM 153',
    'STUDIO A', 'STUDIO B',
    'LEARNING ROOM',
]

# Session type indicators
TYPE_INDICATORS = [
    'Ceremony', 'LIVE Educational', 'Case', 'Learning', 'Hotline / Late-',
    'Breaking Trials', 'Clinical Cases', 'Abstracts', 'Case-based',
    'Discussion', 'How Should I', 'Treat?', 'All You Need to',
    'Know', 'International', 'Collaboration', 'Symposium',
    'Moderated E-', 'Poster', 'Simulation-based', 'Hands-on',
    'Imaging', 'Complications', 'Translate the TOP',
    'trials into practice', 'My Toolbox', 'Tutorial',
    'Nurses and Allied', 'Professionals', 'Symposium with',
    'Recorded case', 'How Should I Treat?',
    'All You Need to Know',
]


def is_room_line(line):
    """Check if a line starts a room name."""
    up = line.upper().strip()
    for r in ROOM_STARTERS:
        if up.startswith(r):
            return True
    # Also check patterns like "ROOM 252A" etc
    if re.match(r'^ROOM \d{3}[A-Z]?$', up):
        return True
    if re.match(r'^ABSTRACT &$', up):
        return True
    if re.match(r'^CASE CORNER', up):
        return True
    return False


def is_type_indicator(line):
    """Check if a line is part of session type description."""
    stripped = line.strip()
    for t in TYPE_INDICATORS:
        if stripped == t or stripped.startswith(t):
            return True
    return False


def parse_speaker_names(text):
    """Parse comma-separated speaker names, handling line wraps."""
    names = []
    for part in re.split(r',\s*', text.strip()):
        part = part.strip()
        if part:
            # Remove trailing periods
            part = part.rstrip('.')
            names.append(part)
    return names


def make_room_code(room):
    """Create a short room code for ID generation."""
    room_up = room.upper()
    if 'MAIN ARENA' in room_up:
        return 'MAIN'
    if 'THEATRE BLEU' in room_up:
        return 'BLEU'
    if 'THEATRE BORDEAUX' in room_up:
        return 'BORDEAUX'
    if 'MAILLOT' in room_up:
        return 'MAILLOT'
    if 'ARLEQUIN' in room_up:
        return 'ARLEQUIN'
    if 'EXCHANGE' in room_up:
        return 'EXCHANGE'
    if 'HANDS ON' in room_up:
        return 'HANDSON'
    if 'ABSTRACT' in room_up or 'CASE CORNER' in room_up:
        m = re.search(r'(\d[A-Z]?)', room_up)
        return f'ACC{m.group(1)}' if m else 'ACC'
    if 'IMAGING SKILLS' in room_up:
        m = re.search(r'LAB\s*(\d)', room_up)
        return f'ISL{m.group(1)}' if m else 'ISL'
    if 'CALCIUM' in room_up:
        return 'CSL'
    if 'STUDIO' in room_up:
        m = re.search(r'STUDIO\s*([A-Z])', room_up)
        return f'STUDIO{m.group(1)}' if m else 'STUDIO'
    if 'LEARNING ROOM' in room_up:
        if 'CORONARY' in room_up:
            return 'LRC'
        if 'STRUCTURAL' in room_up:
            return 'LRS'
        return 'LR'
    # ROOM XXX
    m = re.search(r'ROOM\s*(\d+[A-Z]*)', room_up)
    if m:
        return m.group(1)
    return room_up[:8].replace(' ', '')


def parse_sessions(raw_data):
    """Parse raw text data into structured sessions."""

    # Flatten all pages into a stream of (line, page, day_info) tuples
    stream = []
    for page_data in raw_data:
        page_num = page_data['page']
        day_info = page_data['day']
        for line in page_data['lines']:
            stream.append((line, page_num, day_info))

    # Split stream into session blocks at time patterns
    sessions = []
    current_block = []
    current_time = None
    current_page = None
    current_day = None

    for line, page, day_info in stream:
        if day_info:
            current_day = day_info

        m = TIME_PATTERN.match(line.strip())
        if m:
            # Save previous block
            if current_block and current_time:
                sessions.append({
                    'time_start': current_time[0],
                    'time_end': current_time[1],
                    'page': current_page,
                    'day': current_day,
                    'lines': current_block,
                })
            current_time = (m.group(1), m.group(2))
            current_page = page
            current_block = []
        else:
            current_block.append(line)

    # Don't forget the last block
    if current_block and current_time:
        sessions.append({
            'time_start': current_time[0],
            'time_end': current_time[1],
            'page': current_page,
            'day': current_day,
            'lines': current_block,
        })

    print(f"Found {len(sessions)} raw session blocks")

    # Parse each block
    parsed = []
    id_counter = defaultdict(int)

    for block in sessions:
        lines = block['lines']
        day = block['day']
        if not day:
            continue

        day_name = day['dayName']
        date_str = DAY_MAP.get(day_name, ('', ''))[0]
        day_code = DAY_MAP.get(day_name, ('', ''))[1]

        # Parse the block
        idx = 0

        # 1. Room name (may span multiple lines)
        room_parts = []
        while idx < len(lines):
            l = lines[idx].strip()
            if not l:
                idx += 1
                continue
            if is_room_line(l) or (room_parts and l in ['CASE CORNER', 'LAB 1 (ROOM', 'LAB 2 (ROOM', 'LAB (ROOM', '142)', '152)', '143)',
                                                          'CORONARY', 'STRUCTURAL', '(CORONARY)', '(STRUCTURAL)',
                                                          'ROOM', 'HAVANE -', 'SIMULATION', 'LEARNING']):
                room_parts.append(l)
                idx += 1
            elif room_parts:
                break
            else:
                # First non-empty line should be room
                room_parts.append(l)
                idx += 1
                break

        room = ' '.join(room_parts).strip()
        # Clean up room name
        room = re.sub(r'\s+', ' ', room)

        # 2. Session type (may span multiple lines)
        type_parts = []
        while idx < len(lines):
            l = lines[idx].strip()
            if not l:
                idx += 1
                continue
            if is_type_indicator(l):
                type_parts.append(l)
                idx += 1
            else:
                break

        session_type_raw = ' '.join(type_parts)

        # Map to standardized type
        session_type = 'Other'
        type_lower = session_type_raw.lower()
        if 'ceremony' in type_lower:
            session_type = 'Ceremony'
        elif 'live educational' in type_lower or 'live case' in type_lower:
            session_type = 'LIVE'
        elif 'hotline' in type_lower or 'late-breaking' in type_lower or 'breaking trials' in type_lower:
            session_type = 'Hotline'
        elif 'simulation-based symposium' in type_lower:
            session_type = 'Symposium'
        elif 'simulation' in type_lower:
            session_type = 'Simulation'
        elif 'hands-on' in type_lower:
            session_type = 'Hands-on'
        elif 'moderated e-poster' in type_lower or 'moderated e- poster' in type_lower:
            session_type = 'ModeratedEPoster'
        elif 'case-based' in type_lower:
            session_type = 'CaseDiscussion'
        elif 'how should i treat' in type_lower:
            session_type = 'HowShouldITreat'
        elif 'all you need to know' in type_lower:
            session_type = 'AllYouNeedToKnow'
        elif 'translate the top' in type_lower or 'translate' in type_lower:
            session_type = 'TranslateTrials'
        elif 'my toolbox' in type_lower:
            session_type = 'MyToolbox'
        elif 'tutorial' in type_lower:
            session_type = 'Tutorial'
        elif 'nurses and allied' in type_lower:
            session_type = 'NursesAlliedProfessionals'
        elif 'symposium' in type_lower:
            session_type = 'Symposium'
        elif 'international collaboration' in type_lower or 'international' in type_lower:
            session_type = 'InternationalCollaboration'
        elif 'clinical cases' in type_lower:
            session_type = 'ClinicalCases'
        elif 'abstracts' in type_lower:
            session_type = 'Abstracts'
        elif 'imaging' in type_lower and 'complications' in type_lower:
            session_type = 'ClinicalCases'
        elif 'complications' in type_lower:
            session_type = 'ClinicalCases'
        elif 'imaging' in type_lower:
            session_type = 'Learning'
        elif 'learning' in type_lower:
            session_type = 'Learning'

        # 3. Title (until we hit a speaker role or "Join us" or "With the collaboration" or agenda items)
        title_parts = []
        subtitle = None
        sponsor = None
        speakers = {}
        objectives = []
        agenda = []
        description = None
        flags = []

        # Continue parsing remaining lines
        remaining = lines[idx:]

        # State machine for parsing
        state = 'title'  # title -> speakers -> objectives -> agenda
        current_role_key = None
        current_role_names = []

        for line in remaining:
            l = line.strip()
            if not l:
                # Empty line - could be agenda item separator
                if state == 'agenda' and current_role_key is None:
                    continue
                if state == 'speakers' and current_role_key:
                    # Flush current role
                    if current_role_names:
                        speakers[current_role_key] = parse_speaker_names(', '.join(current_role_names))
                    current_role_key = None
                    current_role_names = []
                continue

            # Check for speaker role
            rm = ROLE_PATTERN.match(l)
            if rm:
                if state == 'title':
                    state = 'speakers'

                # Flush previous role
                if current_role_key and current_role_names:
                    speakers[current_role_key] = parse_speaker_names(', '.join(current_role_names))

                role_label = rm.group(1)
                matched_key = None
                for rk in SPEAKER_ROLES_MAP:
                    if rk.lower() == role_label.lower():
                        matched_key = SPEAKER_ROLES_MAP[rk]
                        break
                if not matched_key:
                    # Fuzzy match
                    for rk in SPEAKER_ROLES_MAP:
                        if role_label.lower().startswith(rk.lower()):
                            matched_key = SPEAKER_ROLES_MAP[rk]
                            break

                current_role_key = matched_key or role_label
                current_role_names = [rm.group(2)] if rm.group(2).strip() else []
                continue

            # Continuation of speaker names (after a role line, next line might be more names)
            if state == 'speakers' and current_role_key and not l.startswith('Join us') and not l.startswith('With the') and not l.startswith('Session comprising') and not l.startswith('Sponsored by') and not l.startswith('This session') and not l.startswith('Kindly note') and not l.startswith('Partners in') and not l.startswith('The 30 minutes'):
                # Check if this looks like more names (short, has capitals, commas)
                if len(l) < 80 and not l.startswith('•') and not l.startswith('To ') and not l.startswith('>') and not l.startswith('Welcome'):
                    # Likely continuation of names
                    current_role_names.append(l)
                    continue
                else:
                    # Flush and move on
                    if current_role_names:
                        speakers[current_role_key] = parse_speaker_names(', '.join(current_role_names))
                    current_role_key = None
                    current_role_names = []
                    state = 'post_speakers'

            # Check for objectives
            if l.startswith('Join us if you want:'):
                if current_role_key and current_role_names:
                    speakers[current_role_key] = parse_speaker_names(', '.join(current_role_names))
                    current_role_key = None
                    current_role_names = []
                state = 'objectives'
                continue

            if state == 'objectives':
                if l.startswith('•') or l.startswith('To ') or l.startswith('to '):
                    obj_text = l.lstrip('•').strip()
                    if obj_text:
                        objectives.append(obj_text)
                    continue
                elif objectives and not l.startswith('>') and not l.startswith('Welcome') and len(l) < 60 and not TIME_PATTERN.match(l):
                    # Continuation of previous objective
                    if objectives:
                        objectives[-1] += ' ' + l
                    continue
                else:
                    state = 'agenda'

            # Check for collaboration subtitle
            if l.startswith('With the collaboration of') or l.startswith('With the collaboration'):
                if state == 'title':
                    subtitle = l
                    state = 'subtitle_continuation'
                continue

            if state == 'subtitle_continuation':
                if not l.startswith('Anchorperson') and not l.startswith('Spokesperson') and not l.startswith('Join') and not ROLE_PATTERN.match(l):
                    subtitle = (subtitle or '') + ' ' + l
                    continue
                else:
                    state = 'speakers'
                    # Fall through to handle this line
                    rm = ROLE_PATTERN.match(l)
                    if rm:
                        role_label = rm.group(1)
                        for rk in SPEAKER_ROLES_MAP:
                            if rk.lower() == role_label.lower():
                                current_role_key = SPEAKER_ROLES_MAP[rk]
                                break
                        current_role_names = [rm.group(2)] if rm.group(2).strip() else []
                        continue

            # Sponsor detection
            if l.startswith('Sponsored by'):
                sponsor = l
                continue

            # Session description markers
            if l.startswith('Session comprising selected'):
                description = l
                continue

            if l.startswith('See session details in the Sponsored'):
                description = l
                flags.append('sponsored')
                continue

            if l.startswith('This session has been made possible'):
                sponsor = l
                flags.append('sponsored')
                continue

            if l.startswith('Kindly note that seats are limited'):
                flags.append('seatsLimited')
                continue

            if l.startswith('The 30 minutes after'):
                continue  # Skip this note

            if l.startswith('Partners in Learning'):
                subtitle = l if not subtitle else subtitle
                continue

            # Title accumulation
            if state == 'title':
                title_parts.append(l)
                continue

            # Agenda items (> prefix or after objectives)
            if state in ('agenda', 'post_speakers') or l.startswith('>') or l.startswith('Welcome and session objectives'):
                state = 'agenda'
                item_text = l.lstrip('>').strip()
                if item_text:
                    pending = '(Pending confirmation)' in item_text
                    item_text = item_text.replace('(Pending confirmation)', '').strip()

                    # Check if this is a speaker name for the previous item
                    # (Speaker names appear on the line after the item, are short, have initials)
                    if agenda and len(item_text) < 40 and not item_text.startswith('Discussion') and not item_text.startswith('Case ') and not item_text.startswith('Session ') and not item_text.startswith('Welcome') and not item_text.startswith('Closing') and not item_text.startswith('Review') and not item_text.startswith('Key ') and re.match(r'^[A-Z]\.?\s', item_text):
                        # This looks like a speaker name
                        agenda[-1]['speaker'] = item_text
                        if pending:
                            agenda[-1]['pending'] = True
                        continue

                    agenda.append({
                        'item': item_text,
                        'speaker': None,
                        'pending': pending,
                    })

        # Flush any remaining speaker role
        if current_role_key and current_role_names:
            speakers[current_role_key] = parse_speaker_names(', '.join(current_role_names))

        title = ' '.join(title_parts).strip()
        if not title:
            continue  # Skip blocks without a title

        # Generate ID
        time_code = block['time_start'].replace(':', '')
        room_code = make_room_code(room)
        id_key = f"{day_code}-{time_code}-{room_code}"
        id_counter[id_key] += 1
        session_id = f"{id_key}-{id_counter[id_key]:03d}"

        # Detect track from context (will need image analysis for color, use keyword heuristics)
        track = detect_track(title, room, session_type_raw, type_parts)

        parsed.append({
            'id': session_id,
            'day': day_name,
            'date': date_str,
            'timeStart': block['time_start'],
            'timeEnd': block['time_end'],
            'room': room,
            'track': track,
            'type': session_type,
            'title': title,
            'subtitle': subtitle,
            'sponsor': sponsor,
            'speakers': speakers if speakers else None,
            'learningObjectives': objectives,
            'agenda': agenda,
            'flags': flags,
            'page': block['page'],
        })

    return parsed


def detect_track(title, room, type_raw, type_parts):
    """Heuristic track detection based on title/room keywords."""
    title_lower = title.lower()

    # Structural indicators
    structural_kw = ['tavi', 'tavr', 'transcatheter aortic', 'transcatheter mitral',
                     'mitral valve', 'mitral repair', 'tricuspid', 'teer',
                     'structural heart', 'aortic stenosis', 'valve', 'valvular',
                     'laa closure', 'left atrial appendage', 'asd', 'pfo',
                     'paravalvular leak', 'pulmonary valve']

    # Coronary indicators
    coronary_kw = ['pci', 'stent', 'coronary', 'bifurcation', 'cto',
                   'left main', 'drug-coated balloon', 'dcb', 'des',
                   'atherectomy', 'rotablator', 'lithotripsy', 'ivus', 'oct',
                   'ffr', 'ifr', 'angioplasty', 'cabg', 'stemi', 'nstemi',
                   'acs', 'acute coronary', 'myocardial infarction',
                   'thrombus', 'calcium', 'calcified', 'plaque', 'vulnerable',
                   'chronic total', 'in-stent', 'restenosis']

    # Heart failure
    hf_kw = ['heart failure', 'cardiogenic shock', 'impella', 'ecmo',
             'mechanical circulatory', 'lvad', 'cardiac support']

    # Hypertension
    htn_kw = ['hypertension', 'renal denervation', 'blood pressure']

    # Peripheral / PE
    pe_kw = ['pulmonary embolism', 'thrombectomy in pulmonary', 'pe ']
    peripheral_kw = ['peripheral', 'lower limb', 'carotid', 'renal artery']

    scores = {
        'coronary': sum(1 for k in coronary_kw if k in title_lower),
        'structural': sum(1 for k in structural_kw if k in title_lower),
        'heartFailure': sum(1 for k in hf_kw if k in title_lower),
        'hypertension': sum(1 for k in htn_kw if k in title_lower),
        'pulmonaryEmbolism': sum(1 for k in pe_kw if k in title_lower),
        'peripheralInterventions': sum(1 for k in peripheral_kw if k in title_lower),
    }

    # Room-based hints
    if 'LEARNING ROOM' in room.upper():
        if 'CORONARY' in room.upper():
            scores['coronary'] += 2
        elif 'STRUCTURAL' in room.upper():
            scores['structural'] += 2

    # Check for dual track
    top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if top_scores[0][1] > 0:
        if top_scores[1][1] > 0 and top_scores[1][1] >= top_scores[0][1] - 1:
            return f"{top_scores[0][0]},{top_scores[1][0]}"
        return top_scores[0][0]

    return 'coronary'  # Default for EuroPCR


# --- Main ---
with open('/Users/YUANCHIEHCHANG/Desktop/五月EuroPCR/app-data/raw_text_all.json') as f:
    raw_data = json.load(f)

sessions = parse_sessions(raw_data)

# Split by day
by_day = defaultdict(list)
for s in sessions:
    by_day[s['day']].append(s)

# Write combined and per-day files
output_dir = '/Users/YUANCHIEHCHANG/Desktop/五月EuroPCR/app-data'

with open(f'{output_dir}/sessions_all_v2.json', 'w') as f:
    json.dump(sessions, f, indent=2, ensure_ascii=False)

for day_name, day_sessions in by_day.items():
    code = DAY_MAP[day_name][1].lower()
    with open(f'{output_dir}/sessions_{code}_v2.json', 'w') as f:
        json.dump(day_sessions, f, indent=2, ensure_ascii=False)

# Stats
print(f"\n=== EXTRACTION COMPLETE ===")
print(f"Total sessions: {len(sessions)}")
for day_name in ['Tuesday', 'Wednesday', 'Thursday', 'Friday']:
    ds = by_day.get(day_name, [])
    if ds:
        speakers_count = set()
        for s in ds:
            if s['speakers']:
                for role, names in s['speakers'].items():
                    for n in names:
                        speakers_count.add(n)
            for a in s.get('agenda', []):
                if a.get('speaker'):
                    speakers_count.add(a['speaker'])
        print(f"  {day_name}: {len(ds)} sessions, {len(speakers_count)} unique speakers")

# Type distribution
type_counts = defaultdict(int)
for s in sessions:
    type_counts[s['type']] += 1
print(f"\nSession types:")
for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")

# Track distribution
track_counts = defaultdict(int)
for s in sessions:
    track_counts[s['track']] += 1
print(f"\nTracks:")
for t, c in sorted(track_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")

all_speakers = set()
for s in sessions:
    if s['speakers']:
        for role, names in s['speakers'].items():
            for n in names:
                all_speakers.add(n)
    for a in s.get('agenda', []):
        if a.get('speaker'):
            all_speakers.add(a['speaker'])
print(f"\nTotal unique speakers across all days: {len(all_speakers)}")
