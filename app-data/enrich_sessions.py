#!/usr/bin/env python3
"""
Enrich every session in sessions.json with:
  - topics[]   : auto-detected topic pills (ACS, Complications, VulnerablePlaque, LM, Bifurcation, Calcium, CTO, Imaging, Physiology, TAVI, LAA, MitralTEER, Tricuspid, PE, HF, Hypertension, DCB, Innovation, Simulation, CasePresentation)
  - trackCategories[] : official 2026 category tags: Coronary | Structural | HeartFailure | Hypertension | Peripheral | PulmonaryEmbolism | NursesAllied | Sponsored
  - formatLabel : short human-readable format (e.g. "LIVE Case", "How Should I Treat?", "Case-based Discussion", "Simulation", "Hands-on Lab", "Abstracts", "e-Poster", "Symposium", "Tutorial", "Learning Room", "Innovation Showroom")
  - location  : {levelLabel, wing, walkFromMain} — from PALAIS DES CONGRÈS floor convention

Writes a new file alongside: sessions.enriched.json, then a build step
replaces app/data/sessions.json with this. The original source stays in
sessions_all_v2.json.
"""

import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SRC  = ROOT.parent / 'app' / 'data' / 'sessions.json'
OUT  = ROOT.parent / 'app' / 'data' / 'sessions.json'      # overwrite in place
BAK  = ROOT / 'sessions.pre_enrich.backup.json'

# ------------------------------------------------------------------
# Topic dictionary — keyword → topic tag
#   Order matters only for display priority (first match wins if dedup)
# ------------------------------------------------------------------
TOPIC_RULES = [
    # ACS / STEMI — treat as one big bucket per Dr. Chang's instruction
    ('ACS-STEMI', r'\bSTEMI\b|\bACS\b|ST-elevation|ST elevation|acute coronary|NSTEMI|non[- ]ST|primary PCI|cardiogenic shock|thrombus|aspiration thrombectomy'),
    # Vulnerable plaque / atheroma biology
    ('VulnerablePlaque', r'vulnerable plaque|high.?risk plaque|thin.?cap|TCFA|plaque erosion|plaque rupture|atheroma|lipid.?rich|inflammation|lipoprotein|atherosc'),
    # Complications
    ('Complications', r'complication|bailout|perforation|rescue|dissection(?!\s*cascade)|tamponade|entrapment|dislodg|no.?reflow|slow.?flow|stent (fracture|loss|crush)|vascular complication|coronary injury|embolisation|ischemic shock|pitfall|went wrong|unexpected|crash'),
    # Left main
    ('LM', r'left main|\bLM\b|LM stenosis|LM bifurcation|ostial LAD|ostial LCx|distal left main|LMCA'),
    # Bifurcation
    ('Bifurcation', r'bifurcation|DK.?crush|mini.?crush|nano.?crush|two.?stent|provisional|POT|Medina|T.?stent|culottes'),
    # Calcium / Calcified
    ('Calcium', r'calcium|calcified|calcification|rotablator|shockwave|lithotripsy|IVL|orbital atherectomy|atherectomy|undilatable'),
    # CTO
    ('CTO', r'\bCTO\b|chronic total occlusion|retrograde|antegrade dissection|knuckle|CrossBoss'),
    # Intracoronary imaging
    ('Imaging', r'IVUS|OCT\b|NIRS|intracoronary imaging|intravascular imaging|optical coherence'),
    # Physiology
    ('Physiology', r'\bFFR\b|\biFR\b|\bQFR\b|\bRFR\b|physiolog|microvasc|INOCA|ANOCA|CMD|coronary flow|resistance'),
    # Drug-Coated Balloon
    ('DCB', r'\bDCB\b|drug.?coated balloon|drug.?eluting balloon|paclitaxel balloon|sirolimus balloon'),
    # TAVI
    ('TAVI', r'\bTAVI\b|\bTAVR\b|transcatheter aortic|aortic valve implant|CoreValve|Sapien|Evolut|valve embolisation|paravalvular'),
    # LAA closure
    ('LAA', r'\bLAA\b|left atrial appendage|Watchman|Amulet|LAAC|LAAO|CHAMPION-AF|OPTION'),
    # Mitral TEER / replacement
    ('Mitral', r'mitral|\bTEER\b|MitraClip|PASCAL|edge.?to.?edge|TMVR|mitral regurg'),
    # Tricuspid
    ('Tricuspid', r'tricuspid|\bTriClip\b|TEER tricuspid|tricuspid regurg'),
    # Pulmonary embolism
    ('PE', r'\bPE\b\s|pulmonary embolism|pulmonary embolus|HI-?PEITHO|FLASH|catheter.?directed|thrombectomy pe|FlowTriever'),
    # Heart failure mechanical support
    ('HF-Shock', r'heart failure|cardiogenic shock|Impella|ECMO|VA-?ECMO|mechanical support|MCS\b|PROTECT'),
    # Hypertension / RDN
    ('Hypertension', r'hypertension|renal denervation|\bRDN\b|resistant hypertens'),
    # DAPT / pharmacology
    ('DAPT', r'\bDAPT\b|antiplatelet|ticagrelor|clopidogrel|prasugrel|PCI.?pharma|antithromb'),
    # Innovation / AI
    ('AI-Innovation', r'\bAI\b|artificial intelligence|machine learning|deep learning|robotic PCI|CathWorks|FFRangio|video frame'),
    # Simulation / hands-on
    ('Simulation', r'simulation|simulator|hands.?on|skills lab|training village'),
    # Access / radial / femoral
    ('Access', r'\bradial\b|femoral|access site|closure device|Perclose|Manta|Angioseal'),
]

# Sub-category from session type (mapped to clean format labels)
FORMAT_LABELS = {
    'LIVE': 'LIVE Case',
    'Ceremony': 'Ceremony',
    'HowShouldITreat': 'How Should I Treat?',
    'CaseDiscussion': 'Case Discussion',
    'ClinicalCases': 'Case-based',
    'Simulation': 'Simulation',
    'Hands-on': 'Hands-on Lab',
    'AllYouNeedToKnow': 'All You Need to Know',
    'Abstracts': 'Abstracts',
    'Hotline': 'Hotline',
    'NursesAlliedProfessionals': 'Nurses & Allied',
    'ModeratedEPoster': 'e-Poster',
    'Innovation': 'Innovation',
    'Symposium': 'Symposium',
    'MyToolbox': 'My Toolbox',
    'TranslateTrials': 'Translate Trials',
    'Learning': 'Learning Room',
    'Tutorial': 'Tutorial',
}

# Track → official category pill (colour + label). These mirror the
# programme PDF's coloured square legend.
TRACK_TO_CATEGORY = {
    'coronary':                  ['Coronary'],
    'structural':                ['Structural'],
    'heartFailure':              ['HeartFailure'],
    'hypertension':              ['Hypertension'],
    'pulmonaryEmbolism':         ['PulmonaryEmbolism'],
    'coronary,structural':       ['Coronary', 'Structural'],
    'structural,coronary':       ['Structural', 'Coronary'],
    'coronary,hypertension':     ['Coronary', 'Hypertension'],
    'heartFailure,pulmonaryEmbolism': ['HeartFailure', 'PulmonaryEmbolism'],
    'coronary,heartFailure':     ['Coronary', 'HeartFailure'],
    'pulmonaryEmbolism,coronary':['PulmonaryEmbolism', 'Coronary'],
    'structural,heartFailure':   ['Structural', 'HeartFailure'],
    'coronary,pulmonaryEmbolism':['Coronary', 'PulmonaryEmbolism'],
}

# ------------------------------------------------------------------
# Palais des Congrès de Paris — floor convention
#   - Level 1 (Niveau 1): rooms 100s, Théâtre Havane
#   - Level 2 (Niveau 2): Grand Amphi (MAIN ARENA), Maillot, Théâtre Bleu, rooms 200s, Training Village, Exhibition
#   - Level 3 (Niveau 3): rooms 300s
#   - Level 4 (Niveau 4): auxiliary 400s (rare)
# ------------------------------------------------------------------
def room_location(room):
    if not room: return None
    r = room.strip().upper()

    # Hero rooms
    if 'MAIN ARENA' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Grand Amphi', 'walk': '主入口中央大廳後方，手扶梯上 2 樓'}
    if 'THEATRE BLEU' in r or 'THÉÂTRE BLEU' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Théâtre Bleu', 'walk': 'Grand Amphi 旁，西側'}
    if r == 'THEATRE' or 'HAVANE' in r or 'BORDEAUX' in r or 'ARLEQUIN' in r or r == 'ROOM':
        return {'levelLabel': 'Level 1', 'wing': 'Théâtre Havane (Learning Rooms)', 'walk': '主入口下 1 樓，Learning Rooms 區（Havane / Arlequin / Bordeaux）'}
    if 'MAILLOT' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Salle Maillot', 'walk': 'Grand Amphi 東側，靠 Porte Maillot 出口'}
    if 'STUDIO A' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Studio A — Learning Room (Coronary)', 'walk': 'Exhibition Hall 內，展區東北角'}
    if 'STUDIO B' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Studio B — Learning Room', 'walk': 'Exhibition Hall 內，展區北側'}
    if 'THE EXCHANGE' in r:
        return {'levelLabel': 'Level 2', 'wing': 'The Exchange (Sponsored Theatre)', 'walk': 'Exhibition Hall 中央舞台區'}
    if 'INNOVATION THEATRE' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Innovation Theatre', 'walk': 'Exhibition Hall 東側，AI / Innovation 區'}
    if 'AI LAB' in r:
        return {'levelLabel': 'Level 2', 'wing': 'AI Lab', 'walk': 'Exhibition Hall，Innovation Theatre 旁'}
    if 'HANDS ON LAB' in r or 'HANDS-ON' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Training Village — Hands-on Lab', 'walk': 'Grand Amphi 旁側廊，Training Village 入口（Thu 併發症需要這裡登記）'}
    if 'CALCIUM SKILLS LAB' in r or 'ROOM 143' in r:
        return {'levelLabel': 'Level 1', 'wing': 'Calcium Skills Lab (Room 143)', 'walk': '下 1 樓，100 區，Training Village 延伸'}
    if 'IMAGING SKILLS LAB' in r and '142' in r:
        return {'levelLabel': 'Level 1', 'wing': 'Imaging Skills Lab (Room 142)', 'walk': '下 1 樓，100 區'}
    if 'IMAGING SKILLS LAB' in r and '152' in r:
        return {'levelLabel': 'Level 1', 'wing': 'Imaging Skills Lab (Room 152)', 'walk': '下 1 樓，150 區'}
    if 'LEARNING ROOM (STRUCTURAL)' in r or 'ROOM 342' in r:
        return {'levelLabel': 'Level 3', 'wing': 'Room 342AB — Learning Room (Structural)', 'walk': '上 3 樓，東翼'}
    if 'ABSTRACT & CASE CORNER' in r and '2E' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Abstract & Case Corner 2E', 'walk': 'Exhibition Hall 東區（Abstract Corner 分區 E）'}
    if 'ABSTRACT & CASE CORNER' in r and '2F' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Abstract & Case Corner 2F', 'walk': 'Exhibition Hall 東區（Abstract Corner 分區 F）'}
    if 'ABSTRACT & CASE CORNER' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Abstract & Case Corner', 'walk': 'Exhibition Hall 中段，Abstract Corner 集中區'}
    if 'SHOWROOM' in r:
        return {'levelLabel': 'Level 2', 'wing': 'Innovation Showroom', 'walk': 'Exhibition Hall，Innovation 區'}

    # Generic numbered rooms — first digit = level
    m = re.search(r'ROOM\s*(\d)(\d{2})', r)
    if m:
        lvl = m.group(1)
        num = m.group(2)
        return {'levelLabel': f'Level {lvl}', 'wing': f'Room {lvl}{num}',
                'walk': f'上 {lvl} 樓，找 Room {lvl}{num}（{lvl}00 區）' if lvl != '1' else f'下 1 樓，找 Room 1{num}（100 區）'}

    return {'levelLabel': '場內', 'wing': room.strip(), 'walk': '在會場內，現場問工作人員或看指示牌'}


def detect_topics(session):
    blob_parts = [
        session.get('title') or '',
        session.get('subtitle') or '',
    ]
    for a in (session.get('agenda') or []):
        blob_parts.append(a.get('title') or a.get('item') or '')
    # Include speaker names so e.g. "Scheller" → DCB picks up subtly? No, skip, too noisy.
    blob = ' '.join(blob_parts)

    tags = []
    seen = set()
    for tag, pattern in TOPIC_RULES:
        if re.search(pattern, blob, re.I):
            if tag not in seen:
                tags.append(tag)
                seen.add(tag)
    return tags


def enrich_session(s):
    s = dict(s)  # shallow copy

    # 1) topics[]
    s['topics'] = detect_topics(s)

    # 2) trackCategories[]
    track = s.get('track') or ''
    cats = TRACK_TO_CATEGORY.get(track, [])
    if not cats and track:
        # best effort
        if 'coronary' in track: cats.append('Coronary')
        if 'structural' in track: cats.append('Structural')
    s['trackCategories'] = cats

    # 3) formatLabel
    s['formatLabel'] = FORMAT_LABELS.get(s.get('type'), s.get('type') or '')

    # 4) sponsor flag
    if s.get('sponsor'):
        if 'Sponsored' not in s['trackCategories']:
            s['trackCategories'] = list(s['trackCategories']) + ['Sponsored']

    # 5) location
    s['location'] = room_location(s.get('room'))

    return s


def main():
    with SRC.open() as f:
        sessions = json.load(f)

    BAK.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding='utf-8')

    enriched = {sid: enrich_session(s) for sid, s in sessions.items()}

    with OUT.open('w') as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    # Summary
    from collections import Counter
    topic_counts = Counter()
    for s in enriched.values():
        for t in s['topics']:
            topic_counts[t] += 1
    print('Enriched', len(enriched), 'sessions')
    print('Top topics:')
    for t, c in topic_counts.most_common():
        print(f'  {t:18} {c}')
    # Location coverage
    loc_known = sum(1 for s in enriched.values() if s['location'] and s['location'].get('levelLabel', '').startswith('Level'))
    print(f'Location mapped (Level X): {loc_known}/{len(enriched)}')


if __name__ == '__main__':
    main()
