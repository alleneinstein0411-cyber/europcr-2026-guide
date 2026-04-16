#!/usr/bin/env python3
"""
Thu 15:00 block: promote the Multivessel ACS session (Götberg S + Mehta S)
from backup 5 to main pick; demote Complication Simulation hands-on lab
to a backup. Rationale (per Dr. Chang, 2026-04-16): rota complication
management can be trained domestically; the dual-S ACS discussion is a
EuroPCR-only opportunity.

Also:
  - Remove THU-1500-143-001 from registrationAlerts (no longer the pick,
    so Training Village registration sequence isn't needed)
  - Add the demoted Hands-on Sim to replayPlan so it's not lost
"""

import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SCHED = ROOT.parent / 'app' / 'data' / 'schedule.json'
BAK = ROOT / 'schedule.pre_thu1500_swap.backup.json'

sch = json.loads(SCHED.read_text())
BAK.write_text(json.dumps(sch, ensure_ascii=False, indent=2), encoding='utf-8')

# Find Thu 15:00 block
for d in sch['days']:
    if d['day'] != 'Thursday': continue
    for blk in d['blocks']:
        if not blk['time'].startswith('15:00'): continue

        old_pick = blk['pick']
        backups = blk.get('backups', [])

        # Find the multivessel ACS backup
        acs_idx = None
        for i, b in enumerate(backups):
            if b.get('sessionId') == 'THU-1500-BLEU-001':
                acs_idx = i; break
        assert acs_idx is not None, 'THU-1500-BLEU-001 not in backups'

        new_pick_raw = backups.pop(acs_idx)

        # Build fresh briefing for the new pick
        new_pick = {
            'sessionId': 'THU-1500-BLEU-001',
            'title': 'Challenges of multivessel disease in ACS',
            'keyNames': ['M. Götberg(S)', 'S. Mehta(S)', 'M. Al-Hijji(B)', 'R. Colleran(A)'],
            'note': '★★ 雙 S 同台：Götberg(S) anchor + Mehta(S) disc。SLIM + COMPLETE + iFR-SWEDEHEART 真人現場。',
            'briefing': {
                'summary': '★★ 雙 S 同台 — Götberg (iFR-SWEDEHEART PI, Lund) 當 anchorperson，Mehta (COMPLETE trial PI, McMaster) 當 discussant，搭 Al-Hijji + Colleran。60 分鐘 Case Discussion 聚焦多血管 ACS 的罪魁 vs 非罪魁識別、FFR/iFR + IVUS/OCT 整合、分階段血運重建時機。',
                'why_attend': '你原本選的 Rota 併發症模擬在國內也能練，犧牲價值較低。這場是 EuroPCR 唯一能同時聽到 Götberg + Mehta 本人當場辯論多血管 ACS 決策的機會 — 兩個寫進 ESC / ACC guideline 的 trial PI 同場，現場 nuance 勝過讀 paper。',
                'key_takeaways': [
                    'Mehta 對 COMPLETE-2（staged timing + physiology-guided）的最新立場 — 2026 即將公布',
                    'Götberg 如何回答「STEMI non-culprit lesion 急性期 microvascular dysfunction 會不會騙過 iFR」',
                    'FFR vs iFR 在 NSTEMI 多血管 index procedure 的策略選擇（SLIM 框架落地）',
                ],
                'watch_for': 'Götberg 當 anchor，決定討論順序與攻擊角度 — 注意他怎麼 push Mehta 回答 COMPLETE-2 是否會推翻 culprit-only 的 NSTEMI 建議。',
            }
        }

        # Demote old pick to first backup (most recent swap visible)
        old_pick_as_backup = {
            'sessionId': old_pick['sessionId'],
            'title': old_pick.get('title', ''),
            'keyNames': old_pick.get('keyNames', []),
            'note': old_pick.get('note', ''),
            'briefing': old_pick.get('briefing', {}),
        }

        # New order: old pick first, then remaining backups (minus the ACS one we pulled)
        new_backups = [old_pick_as_backup] + backups

        blk['pick'] = new_pick
        blk['backups'] = new_backups
        blk['changedFromDraft'] = True
        blk['swappedAt'] = '2026-04-16'
        blk['swapReason'] = 'Rota 併發症國內可訓，換 Götberg+Mehta 雙 S ACS multivessel discussion（EuroPCR 唯一機會）'

        print(f'Swapped Thu {blk["time"]}:')
        print(f'  NEW PICK:  {new_pick["sessionId"]} — {new_pick["title"]}')
        print(f'  BACKUPS: {[b["sessionId"] for b in new_backups]}')

# Remove the registrationAlert for THU-1500-143-001
before = len(sch.get('registrationAlerts', []))
sch['registrationAlerts'] = [a for a in sch.get('registrationAlerts', []) if a.get('session') != 'THU-1500-143-001']
print(f'\nRegistration alerts: {before} → {len(sch["registrationAlerts"])} (removed hands-on registration)')

# Add the Rota hands-on to replayPlan since we gave it up
already = any(r.get('sessionId') == 'THU-1500-143-001' for r in sch.get('replayPlan', []))
if not already:
    sch.setdefault('replayPlan', []).append({
        'sessionId': 'THU-1500-143-001',
        'title': 'Complication management in calcified lesions (Hands-on Sim)',
        'reason': '換成 Götberg+Mehta 雙 S ACS multivessel。Rota 併發症處理國內有機會訓練，優先度較低。有空可看回放 moderator 講解部分。',
        'priority': 'low',
    })
    print('Added Hands-on Sim to replayPlan')

# Update version bump
sch['version'] = '2.4-thu1500-acs-swap'
sch['lastSwap'] = {
    'date': '2026-04-16',
    'block': 'Thursday 15:00-16:00',
    'from': 'THU-1500-143-001 (Rota Complications Hands-on)',
    'to': 'THU-1500-BLEU-001 (Multivessel ACS - Götberg+Mehta dual S)',
}

SCHED.write_text(json.dumps(sch, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\nSaved. Schedule version = {sch["version"]}')
