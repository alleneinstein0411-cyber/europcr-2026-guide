#!/usr/bin/env python3
"""Parse EuroPCR 2026 programme PDF using font/position-aware extraction."""

import fitz
import json
import re
from collections import defaultdict

pdf_path = "/Users/YUANCHIEHCHANG/Desktop/五月EuroPCR/programme_europcr2026_updated.pdf"

DAY_MAP = {
    'Tuesday': ('2026-05-19', 'TUE'),
    'Wednesday': ('2026-05-20', 'WED'),
    'Thursday': ('2026-05-21', 'THU'),
    'Friday': ('2026-05-22', 'FRI'),
}

DAY_PATTERN = re.compile(r'(Monday|Tuesday|Wednesday|Thursday|Friday)\s+\d+\s+May\s+2026\s*-\s*(Morning|Afternoon)')
TIME_PATTERN = re.compile(r'^(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$')

SPEAKER_ROLES_MAP = {
    'anchorperson': 'anchorpersons', 'anchorpersons': 'anchorpersons',
    'spokesperson': 'spokespersons', 'spokespersons': 'spokespersons',
    'operator': 'operators', 'operators': 'operators',
    'procedural analyst': 'proceduralAnalysts', 'procedural analysts': 'proceduralAnalysts',
    'discussant': 'discussants', 'discussants': 'discussants',
    'facilitator': 'facilitators', 'facilitators': 'facilitators',
    'moderator': 'moderators', 'moderators': 'moderators',
    'media driver': 'mediaDrivers', 'media drivers': 'mediaDrivers',
    'physician trainer': 'physicianTrainers', 'physician trainers': 'physicianTrainers',
    'experienced advisor': 'experiencedAdvisors', 'experienced advisors': 'experiencedAdvisors',
    'cathlab medical coordinator': 'cathlabCoordinators', 'cathlab medical coordinators': 'cathlabCoordinators',
    'onstage medical coordinator': 'onstageCoordinators', 'onstage medical coordinators': 'onstageCoordinators',
    'guest speaker': 'guestSpeakers', 'guest speakers': 'guestSpeakers',
    'imaging analyst': 'imagingAnalysts', 'imaging analysts': 'imagingAnalysts',
}

TYPE_KEYWORDS = {
    'Ceremony': 'Ceremony',
    'LIVE Educational Case': 'LIVE', 'LIVE Case': 'LIVE',
    'Hotline / Late-Breaking Trials': 'Hotline', 'Hotline / Late- Breaking Trials': 'Hotline',
    'Simulation-based Learning': 'Simulation', 'Simulation-based Symposium': 'Symposium',
    'Hands-on': 'Hands-on',
    'Case-based Discussion': 'CaseDiscussion',
    'How Should I Treat?': 'HowShouldITreat',
    'All You Need to Know': 'AllYouNeedToKnow',
    'International Collaboration': 'InternationalCollaboration',
    'Moderated E-Poster': 'ModeratedEPoster', 'Moderated E- Poster': 'ModeratedEPoster',
    'Translate the TOP trials into practice': 'TranslateTrials',
    'My Toolbox': 'MyToolbox',
    'Tutorial': 'Tutorial',
    'Nurses and Allied Professionals': 'NursesAlliedProfessionals',
    'Clinical Cases': 'ClinicalCases',
    'Abstracts': 'Abstracts',
    'Symposium with Recorded case': 'Symposium',
    'Symposium': 'Symposium',
    'Learning': 'Learning',
    'Imaging': 'Learning',
    'Complications': 'ClinicalCases',
    'Innovation / CV Pipeline': 'Innovation',
    'Innovation': 'Innovation',
}


def is_bold(flags):
    return bool(flags & 16)

def is_italic(flags):
    return bool(flags & 2)

def parse_speaker_names(text):
    names = []
    for part in re.split(r',\s*', text.strip()):
        part = part.strip().rstrip('.')
        if part and len(part) > 1:
            names.append(part)
    return names

def detect_track(title, room, session_type):
    title_lower = (title + ' ' + room + ' ' + session_type).lower()
    structural_kw = ['tavi', 'tavr', 'transcatheter aortic', 'transcatheter mitral',
                     'mitral valve', 'mitral repair', 'tricuspid', 'teer',
                     'structural', 'aortic stenosis', 'valv', 'laa closure',
                     'left atrial appendage', 'asd', 'pfo', 'paravalvular',
                     'pulmonary valve', 'tmvr', 'edge-to-edge']
    coronary_kw = ['pci', 'stent', 'coronary', 'bifurcation', 'cto',
                   'left main', 'drug-coated balloon', 'dcb', 'des',
                   'atherectomy', 'rotabl', 'lithotripsy', 'ivus', 'oct',
                   'ffr', 'ifr', 'angioplast', 'cabg', 'stemi', 'nstemi',
                   'acs', 'acute coronary', 'myocardial infarction',
                   'thrombus', 'calcium', 'calcified', 'plaque', 'vulnerable',
                   'chronic total', 'in-stent', 'restenosis', 'angiograph']
    hf_kw = ['heart failure', 'cardiogenic shock', 'impella', 'ecmo',
             'mechanical circulatory', 'lvad', 'cardiac support', 'active unloading']
    htn_kw = ['hypertension', 'renal denervation', 'blood pressure', 'spyral']
    pe_kw = ['pulmonary embolism', 'thrombectomy in pulmonary']
    peripheral_kw = ['peripheral', 'lower limb', 'carotid']

    scores = defaultdict(int)
    for k in coronary_kw:
        if k in title_lower: scores['coronary'] += 1
    for k in structural_kw:
        if k in title_lower: scores['structural'] += 1
    for k in hf_kw:
        if k in title_lower: scores['heartFailure'] += 1
    for k in htn_kw:
        if k in title_lower: scores['hypertension'] += 1
    for k in pe_kw:
        if k in title_lower: scores['pulmonaryEmbolism'] += 1
    for k in peripheral_kw:
        if k in title_lower: scores['peripheralInterventions'] += 1

    if 'LEARNING ROOM' in room.upper():
        if 'CORONARY' in room.upper() or 'STUDIO A' in room.upper():
            scores['coronary'] += 3
        elif 'STRUCTURAL' in room.upper():
            scores['structural'] += 3

    top = sorted(scores.items(), key=lambda x: -x[1])
    if top and top[0][1] > 0:
        if len(top) > 1 and top[1][1] > 0 and top[1][1] >= top[0][1]:
            return f"{top[0][0]},{top[1][0]}"
        return top[0][0]
    return 'coronary'


def make_room_code(room):
    room_up = room.upper()
    mappings = [
        ('MAIN ARENA', 'MAIN'), ('THEATRE BLEU', 'BLEU'), ('THEATRE BORDEAUX', 'BDX'),
        ('MAILLOT', 'MAILLOT'), ('ARLEQUIN', 'ARLQ'), ('EXCHANGE', 'EXCH'),
        ('HANDS ON', 'HOL'), ('HAVANE', 'HAVANE'), ('INNOVATION THEATRE', 'INNOV'),
        ('INNOVATION SHOWROOM', 'INSHOW'), ('AI LAB', 'AILAB'),
        ('CALCIUM SKILLS', 'CSL'),
    ]
    for pattern, code in mappings:
        if pattern in room_up:
            return code
    m = re.search(r'CASE CORNER\s*(\d[A-Z]?)', room_up)
    if m: return f'ACC{m.group(1)}'
    m = re.search(r'IMAGING SKILLS LAB\s*(\d)', room_up)
    if m: return f'ISL{m.group(1)}'
    m = re.search(r'STUDIO\s*([A-Z])', room_up)
    if m: return f'STD{m.group(1)}'
    m = re.search(r'ROOM\s*(\d+[A-Z]*)', room_up)
    if m: return m.group(1)
    return room_up[:6].replace(' ', '')


def extract_sessions():
    doc = fitz.open(pdf_path)
    all_sessions = []
    id_counter = defaultdict(int)

    for pg_idx in range(1, doc.page_count):  # skip cover
        page = doc[pg_idx]
        page_num = pg_idx + 1

        # Get structured text
        blocks_data = page.get_text("dict")

        # Collect all text spans with metadata
        spans = []
        for block in blocks_data["blocks"]:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    spans.append({
                        'x': round(span["bbox"][0], 1),
                        'y': round(span["bbox"][1], 1),
                        'x1': round(span["bbox"][2], 1),
                        'y1': round(span["bbox"][3], 1),
                        'text': text,
                        'size': round(span["size"], 1),
                        'bold': is_bold(span["flags"]),
                        'italic': is_italic(span["flags"]),
                        'font': span["font"],
                    })

        # Find day header
        current_day = None
        for s in spans:
            m = DAY_PATTERN.search(s['text'])
            if m:
                current_day = m.group(1)
                break

        if not current_day:
            continue

        # Filter out legend/header spans (y < 90 or specific legend text)
        legend_texts = {'Coronary Interventions', 'Interventions for Heart Failure',
                       'Interventions for Hypertension', 'Interventions for Structural Disease',
                       'Peripheral Interventions', 'Pulmonary Embolism', 'Available on Replay',
                       'Learning', 'LIVE', 'Livestreamed on the Course platform & App',
                       'Lunch box', 'Nurses and Allied Professionals', 'Sponsored programme'}

        content_spans = [s for s in spans
                        if s['text'] not in legend_texts
                        and not DAY_PATTERN.search(s['text'])
                        and not (s['text'].isdigit() and int(s['text']) == page_num)
                        and s['y'] > 85]  # skip very top

        if not content_spans:
            continue

        # Determine if page has two columns
        # Column boundary is typically around x=310-340
        COL_BOUNDARY = 310

        # Find time entries (BOLD, size ~11, matching HH:MM - HH:MM)
        time_entries = []
        for s in content_spans:
            if s['bold'] and s['size'] >= 10 and TIME_PATTERN.match(s['text']):
                m = TIME_PATTERN.match(s['text'])
                col = 1 if s['x'] < COL_BOUNDARY else 2
                time_entries.append({
                    'timeStart': m.group(1),
                    'timeEnd': m.group(2),
                    'x': s['x'],
                    'y': s['y'],
                    'col': col,
                })

        # For each time entry, collect all spans that belong to it
        # A session's spans are those between this time entry and the next one in the same column
        time_entries.sort(key=lambda t: (t['col'], t['y']))

        for i, te in enumerate(time_entries):
            # Find y range for this session
            y_start = te['y']
            y_end = 999
            for j in range(i + 1, len(time_entries)):
                if time_entries[j]['col'] == te['col']:
                    y_end = time_entries[j]['y'] - 1
                    break

            # Collect spans in this session's area
            col = te['col']
            if col == 1:
                x_min, x_max = 0, COL_BOUNDARY
            else:
                x_min, x_max = COL_BOUNDARY, 999

            session_spans = [s for s in content_spans
                           if x_min <= s['x'] < x_max
                           and y_start <= s['y'] < y_end
                           and s['text'] != te['timeStart'] + ' - ' + te['timeEnd']  # exclude time itself
                           and not TIME_PATTERN.match(s['text'])]

            session_spans.sort(key=lambda s: (s['y'], s['x']))

            if not session_spans:
                continue

            # Parse session spans
            room_parts = []
            type_parts = []
            title_parts = []
            subtitle = None
            sponsor = None
            speakers = {}
            objectives = []
            agenda = []
            flags = []
            description = None

            # Classify spans by formatting
            # Room: BOLD, size ~8, x in left metadata area
            # Title: BOLD, size ~11
            # Speaker roles: BOLD+ITALIC, size ~8.5
            # Agenda items: regular, size ~9
            # Agenda speakers: ITALIC only, size ~8
            # Type: regular, size ~8, in left area

            # Determine metadata x zone (left of content)
            meta_x_max = te['x'] + 90  # metadata is within ~90px of time entry x
            content_x_min = te['x'] + 60  # content starts about 60-75px right of time

            state = 'meta'  # meta -> title -> speakers -> objectives -> agenda
            current_role = None
            current_role_names = []

            for s in session_spans:
                text = s['text']

                # Skip footer-area content
                if s['y'] > 780:
                    continue

                # Room name: BOLD, size 7-9, in metadata area (x close to time x)
                if s['bold'] and not s['italic'] and 7 <= s['size'] <= 9 and s['x'] < meta_x_max and state == 'meta':
                    room_parts.append(text)
                    continue

                # Session type: NOT bold, size 7-9, in metadata area
                if not s['bold'] and not s['italic'] and 7 <= s['size'] <= 9 and s['x'] < meta_x_max and state == 'meta':
                    type_parts.append(text)
                    continue

                # Title: BOLD, size >= 10, NOT italic
                if s['bold'] and not s['italic'] and s['size'] >= 10:
                    if state in ('meta', 'title'):
                        state = 'title'
                        title_parts.append(text)
                        continue

                # Speaker roles: BOLD + ITALIC
                if s['bold'] and s['italic']:
                    # Check if it starts with a known role
                    role_match = None
                    for role_key in SPEAKER_ROLES_MAP:
                        if text.lower().startswith(role_key + ':') or text.lower().startswith(role_key + 's:'):
                            role_match = role_key
                            break

                    if role_match:
                        # Flush previous role
                        if current_role and current_role_names:
                            key = SPEAKER_ROLES_MAP.get(current_role, current_role)
                            speakers[key] = parse_speaker_names(', '.join(current_role_names))

                        state = 'speakers'
                        current_role = role_match
                        # Extract names after the colon
                        colon_idx = text.find(':')
                        names_text = text[colon_idx + 1:].strip() if colon_idx >= 0 else ''
                        current_role_names = [names_text] if names_text else []
                        continue
                    elif state == 'speakers' and current_role:
                        # Continuation of names
                        current_role_names.append(text)
                        continue

                    # Could also be subtitle/collaboration text
                    if 'collaboration' in text.lower() or 'With the' in text:
                        subtitle = text
                        continue
                    if subtitle and state in ('title', 'speakers') and s['italic']:
                        subtitle = (subtitle or '') + ' ' + text
                        continue

                # "Join us if you want:" marker
                if 'Join us if you want' in text:
                    # Flush speakers
                    if current_role and current_role_names:
                        key = SPEAKER_ROLES_MAP.get(current_role, current_role)
                        speakers[key] = parse_speaker_names(', '.join(current_role_names))
                        current_role = None
                        current_role_names = []
                    state = 'objectives'
                    continue

                # Learning objectives (after "Join us")
                if state == 'objectives' and not s['bold'] and s['size'] >= 8.5:
                    obj_text = text.lstrip('•').strip()
                    if obj_text.startswith('To ') or obj_text.startswith('to '):
                        objectives.append(obj_text)
                    elif objectives and not obj_text.startswith('>') and len(obj_text) < 60:
                        objectives[-1] += ' ' + obj_text
                    else:
                        # Transition to agenda
                        state = 'agenda'
                        # Fall through

                # Special markers
                if text.startswith('Session comprising'):
                    description = text
                    continue
                if text.startswith('Sponsored by') or text.startswith('This session has been made possible'):
                    sponsor = text
                    if 'sponsored' not in flags:
                        flags.append('sponsored')
                    continue
                if text.startswith('See session details in the Sponsored'):
                    description = text
                    if 'sponsored' not in flags:
                        flags.append('sponsored')
                    continue
                if 'seats are limited' in text.lower():
                    if 'seatsLimited' not in flags:
                        flags.append('seatsLimited')
                    continue
                if text == 'The 30 minutes after this session will be':
                    continue
                if text.startswith('dedicated to an open discussion'):
                    continue
                if text.startswith('Partners in Learning'):
                    subtitle = text if not subtitle else subtitle
                    continue
                if text.startswith('With the collaboration'):
                    subtitle = text
                    state = 'subtitle'
                    continue
                if state == 'subtitle' and s['italic'] and not s['bold']:
                    subtitle = (subtitle or '') + ' ' + text
                    continue
                elif state == 'subtitle':
                    state = 'post_subtitle'

                # Agenda items and speakers
                if state in ('agenda', 'objectives', 'post_subtitle', 'speakers', 'title'):
                    # Check if this is an agenda section
                    is_agenda_item = (s['size'] >= 8.5 and not s['bold'] and not s['italic']
                                     and s['x'] > meta_x_max - 20)
                    is_agenda_speaker = (s['italic'] and not s['bold'] and s['size'] <= 8.5
                                       and s['x'] > meta_x_max - 20)
                    is_chevron_item = text.startswith('>')

                    if is_chevron_item:
                        item_text = text.lstrip('>').strip()
                        pending = '(Pending confirmation)' in item_text
                        item_text = item_text.replace('(Pending confirmation)', '').strip()
                        agenda.append({'item': item_text, 'speaker': None, 'pending': pending})
                        state = 'agenda'
                        continue

                    if is_agenda_speaker and agenda:
                        # Speaker name for previous agenda item
                        name = text.replace('(Pending confirmation)', '').strip()
                        pending = '(Pending confirmation)' in text
                        if agenda[-1]['speaker'] is None:
                            agenda[-1]['speaker'] = name
                        if pending:
                            agenda[-1]['pending'] = True
                        continue

                    if is_agenda_item and (text.startswith('Welcome') or text.startswith('Case ')
                                          or text.startswith('Discussion') or text.startswith('Session evaluation')
                                          or text.startswith('Closing') or text.startswith('Key ')
                                          or text.startswith('Review') or text.startswith('How would')
                                          or text.startswith('Patient') or text.startswith('Operator')
                                          or text.startswith('Imaging') or text.startswith('LIVE')
                                          or text.startswith('Debriefing') or text.startswith('Final')
                                          or text.startswith('Study') or text.startswith('Summary')
                                          or text.startswith('PCI ') or len(text) > 20):
                        pending = '(Pending confirmation)' in text
                        item_text = text.replace('(Pending confirmation)', '').strip()
                        agenda.append({'item': item_text, 'speaker': None, 'pending': pending})
                        state = 'agenda'
                        continue

            # Flush final speaker role
            if current_role and current_role_names:
                key = SPEAKER_ROLES_MAP.get(current_role, current_role)
                speakers[key] = parse_speaker_names(', '.join(current_role_names))

            # Build session
            title = ' '.join(title_parts).strip()
            room = ' '.join(room_parts).strip()
            type_raw = ' '.join(type_parts).strip()

            if not title:
                continue

            # Determine session type
            session_type = 'Other'
            for keyword, mapped_type in sorted(TYPE_KEYWORDS.items(), key=lambda x: -len(x[0])):
                if keyword.lower() in type_raw.lower():
                    session_type = mapped_type
                    break

            # Fallback: check title-embedded type hints
            if session_type == 'Other':
                title_lower = title.lower()
                if 'hotline' in type_raw.lower() or 'late-breaking' in type_raw.lower():
                    session_type = 'Hotline'
                elif 'abstract' in type_raw.lower():
                    session_type = 'Abstracts'
                elif 'clinical cases' in type_raw.lower() or 'clinical case' in type_raw.lower():
                    session_type = 'ClinicalCases'
                elif 'symposium' in type_raw.lower():
                    session_type = 'Symposium'
                elif 'learning' in type_raw.lower():
                    session_type = 'Learning'

            # Detect flags
            if 'replay' not in flags and any('replay' in tp.lower() for tp in type_parts):
                flags.append('replay')
            if 'live' not in flags and any('live' == tp.lower() for tp in type_parts):
                flags.append('live')
            if 'livestreamed' not in flags and any('livestreamed' in tp.lower() for tp in type_parts):
                flags.append('livestreamed')

            track = detect_track(title, room, session_type)

            # Generate ID
            date_str = DAY_MAP.get(current_day, ('', ''))[0]
            day_code = DAY_MAP.get(current_day, ('', ''))[1]
            time_code = te['timeStart'].replace(':', '')
            room_code = make_room_code(room)
            id_key = f"{day_code}-{time_code}-{room_code}"
            id_counter[id_key] += 1
            session_id = f"{id_key}-{id_counter[id_key]:03d}"

            all_sessions.append({
                'id': session_id,
                'day': current_day,
                'date': date_str,
                'timeStart': te['timeStart'],
                'timeEnd': te['timeEnd'],
                'room': room,
                'track': track,
                'type': session_type,
                'title': title,
                'subtitle': subtitle,
                'sponsor': sponsor,
                'speakers': speakers if speakers else None,
                'description': description,
                'learningObjectives': objectives,
                'agenda': agenda,
                'flags': flags,
                'page': page_num,
            })

    doc.close()
    return all_sessions


# --- Main ---
print("Extracting sessions...")
sessions = extract_sessions()

# Split by day
by_day = defaultdict(list)
for s in sessions:
    by_day[s['day']].append(s)

# Write files
out_dir = '/Users/YUANCHIEHCHANG/Desktop/五月EuroPCR/app-data'

with open(f'{out_dir}/sessions_all_v2.json', 'w') as f:
    json.dump(sessions, f, indent=2, ensure_ascii=False)

for day_name, day_sessions in by_day.items():
    code = DAY_MAP[day_name][1].lower()
    with open(f'{out_dir}/sessions_{code}_v2.json', 'w') as f:
        json.dump(day_sessions, f, indent=2, ensure_ascii=False)

# Stats
print(f"\n{'='*50}")
print(f"EXTRACTION COMPLETE")
print(f"{'='*50}")
print(f"Total sessions: {len(sessions)}")

for day_name in ['Tuesday', 'Wednesday', 'Thursday', 'Friday']:
    ds = by_day.get(day_name, [])
    if ds:
        sp_count = set()
        for s in ds:
            if s['speakers']:
                for role, names in s['speakers'].items():
                    for n in names: sp_count.add(n)
            for a in s.get('agenda', []):
                if a.get('speaker'): sp_count.add(a['speaker'])
        print(f"  {day_name}: {len(ds)} sessions, {len(sp_count)} unique speakers")

# Type distribution
type_counts = defaultdict(int)
for s in sessions:
    type_counts[s['type']] += 1
print(f"\nSession types:")
for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")

# "Other" check
others = [s for s in sessions if s['type'] == 'Other']
print(f"\n'Other' type breakdown ({len(others)} sessions):")
for s in others[:10]:
    print(f"  p{s['page']}: {s['title'][:60]}")

# Total speakers
all_sp = set()
for s in sessions:
    if s['speakers']:
        for role, names in s['speakers'].items():
            for n in names: all_sp.add(n)
    for a in s.get('agenda', []):
        if a.get('speaker'): all_sp.add(a['speaker'])
print(f"\nTotal unique speakers: {len(all_sp)}")
