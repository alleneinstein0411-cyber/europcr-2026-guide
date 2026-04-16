#!/usr/bin/env python3
"""
Append curated complication / ACS-STEMI / vulnerable plaque alternatives
as additional backup options on Dr. Chang's scheduled blocks.

These were researched by 4 parallel subagents (see session logs).
Each addition = sessionId + title + keyNames + note + briefing.
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SCHED_PATH = ROOT.parent / 'app' / 'data' / 'schedule.json'
SESSIONS_PATH = ROOT.parent / 'app' / 'data' / 'sessions.json'
BAK = ROOT / 'schedule.pre_v22.backup.json'

# ------------------------------------------------------------------
# The curated additions.
#   key = (day, blockTime)
#   value = list of backup entries to append
# ------------------------------------------------------------------
ADDITIONS = {
    ('Tuesday', '11:30-13:00'): [
        {
            'sessionId': 'TUE-1200-153-001',
            'keyNames_fallback': ['S. Brugaletta', 'P. Libby', 'F. Prati'],
            'note': '★ 脆弱斑塊專題。Brugaletta 主持 + Libby（斑塊生物學）+ Prati（OCT 巨擘）。',
            'briefing': {
                'summary': '全面性介紹易損斑塊識別、臨床意義與治療策略。由 S. Brugaletta 主持，邀集 P. Libby 等斑塊生物學大家、F. Prati 等影像專家，透過案例討論與觀眾互動逐一掘開「識別→為何重要→如何治療」三大課題。',
                'why_attend': '你明確想加強的「脆弱斑塊」主題在本次議程只有 7 場，這是其中最完整的一場。作為介入科醫師，你需要的 OCT/IVUS 易損斑塊識別標準、預防性介入決策，Prati + Libby + Brugaletta 一次補齊。對照 Wed 08:30 Libby 的 Lancet Commission 是宏觀層次，這場才是操作層次。',
                'key_takeaways': [
                    '易損斑塊的 OCT/IVUS-NIRS 識別標準（thin-cap、lipid burden 量化）',
                    '斑塊特性如何影響遠期復狹窄與血栓風險',
                    '預防性介入 vs 觀察性管理的臨床決策框架',
                ],
                'watch_for': 'Prati 在「斑塊識別的預後意義」段落聚焦於 IVUS-NIRS 多光譜影像如何量化脂質負荷。',
            },
        },
        {
            'sessionId': 'TUE-1130-252A-001',
            'keyNames_fallback': ['Stent Save a Life (SSL)'],
            'note': '★ ACS/STEMI 精準革命。SSL 合作，案例討論形式，多國決策樹推演。',
            'briefing': {
                'summary': '與 Stent Save a Life! 合作之 STEMI 精準治療案例討論。聚焦 STEMI 治療的數據驅動決策，強調個體化策略。透過多國案例與現場互動，呈現當代 STEMI 管理的最新思維。',
                'why_attend': '「精準革命」強調 STEMI 個體化—正是你在高危 STEMI（多血管、左主幹、廣泛前壁）面臨策略選擇時最需要。案例討論形式允許即時反饋與決策邏輯推演，比單純講座更貼近 cath lab 日常。',
                'key_takeaways': [
                    'STEMI 危險分層與造影後立即策略選擇',
                    '多血管 STEMI：責任病變 vs 旁支血管的時序與器械優化',
                    '左主幹 STEMI 的特殊考量與併發症預防',
                ],
                'watch_for': '「How I would treat」環節可比對自己的術式選擇，獲得國際團隊的實時反饋。',
            },
        },
    ],
    ('Tuesday', '14:45-16:15'): [
        {
            'sessionId': 'TUE-1445-252B-001',
            'keyNames_fallback': ['A. Erglis', 'Z. Piroth', 'N. Amabile'],
            'note': '★★★ STEMI + LM + 併發症三合一。Erglis + Piroth + Amabile，三國（匈/拉/烏）複雜案例。',
            'briefing': {
                'summary': '跨地域教學課程，A. Erglis + Z. Piroth 主持，N. Amabile 等高手評述。三個複雜案例（匈牙利大動脈瓣膜口解離、拉脫維亞血栓、烏克蘭遠期復狹窄）逐一掘開 STEMI/LM PCI 併發症預防與管理。',
                'why_attend': '這場直接傳授「術中突發狀況的識別與即時處理」—同時命中你的三個關注：ACS/STEMI、LM、併發症。Amabile 的鈣化、Piroth 的 CTO、Erglis 的複雜血行重建，是高風險 PCI 併發症的完整工具箱。對照 Al-Lamee 的生理學 LIVE：那是「決策哲學」，這場是「戰場救援」。',
                'key_takeaways': [
                    'LM 與邊界病灶解離的預防策略與 bailout device 選擇',
                    'STEMI/LM 鈣化病灶的 IVL vs rotational atherectomy 決策',
                    '冠脈穿孔的即時識別、分級與微導管/膜支架應用',
                ],
                'watch_for': 'Case 1（匈牙利）Baranyai 的操作困境 + Kumsars 的「我會怎麼做」；Case 3（烏克蘭）Furkalo 的復狹窄多次 PCI + Ruzsa 的器械層次化建議。',
            },
        },
        {
            'sessionId': 'TUE-1445-STUDIOA-001',
            'keyNames_fallback': ['A. Achim', 'G. G Toth', 'M. Noc'],
            'note': '★ STEMI 多血管病變 Learning Room。Achim + Toth 帶，Noc 當 advisor。',
            'briefing': {
                'summary': 'Achim 與 Toth 主持的互動式學習室，深入討論 STEMI 合併多血管病變的評估與治療策略，涵蓋 PCI 後旁支病變評估及分期時機。',
                'why_attend': '直接針對你臨床常見的 STEMI 多血管情境設計。Al-Lamee 的 ORBITA LIVE 雖然很酷，但本場提供更實務的分期決策框架（完全血管化 vs 分期）。如果你對 ORBITA 的 physiology-first 已經熟悉、反而需要 FIRE 時代的多血管處理原則，這場是更好的選擇。',
                'key_takeaways': [
                    'STEMI 多血管的危險分層與評估工具（FFR、iFR 在旁支的角色）',
                    'PCI 後旁支病變的時機（急性 vs 延遲）、FIRE trial 世代的完全血管化討論',
                    '高風險患者的分期策略，結合多學科觀點',
                ],
                'watch_for': 'Noc 擔任 experienced advisor—帶來心源性休克管理的洞見，可搭配 16:30 的 ACC-004 心源性休克病例課程。',
            },
        },
    ],
    ('Tuesday', '16:30-17:15'): [
        {
            'sessionId': 'TUE-1630-ACC-004',
            'keyNames_fallback': ['M. Ayoub'],
            'note': '★ STEMI + cardiogenic shock 病例課程。DanGer Shock（NEJM 2024）同代情境。',
            'briefing': {
                'summary': 'Ayoub 主持的心源性休克 STEMI 臨床病例討論，集中於急性機械支持、血動力學管理與多學科決策的前線實戰教學。',
                'why_attend': '若你要深化心源性休克的急性處置邏輯，這場補齊 Tue 14:45 多血管疾病討論的缺口。與 DanGer Shock（Impella CP vs 標準照護，NEJM 2024）同代，提供即時驗證的臨床情境。相比 Bifurcation DCB 的技術焦點，本場更著重宏觀決策與設備選擇。',
                'key_takeaways': [
                    '心源性休克 STEMI 的快速評估與機械支持決策',
                    '血動力學監測與多藥物協同策略',
                    '轉運、冠脈介入與心臟支持的整合時序',
                ],
            },
        },
        {
            'sessionId': 'TUE-1630-343-001',
            'keyNames_fallback': ['A. Mirza', 'M. Sabate'],
            'note': 'Complex anatomy STEMI。Sabate 是複雜 PCI/LM 先驅。',
            'briefing': {
                'summary': 'Mirza 與 Sabate 主持的複雜解剖 STEMI 病例工坊，聚焦特殊冠脈解剖（異常起源、幽門、LM 複雜病變）的策略性介入。',
                'why_attend': '若你在複雜冠脈解剖的技術困境中尋求精進，這場適度替代主選。Sabate 素以複雜 PCI 與 LM 病變著稱，病例課程形式提供沉浸式學習。但需權衡：若主選 bifurcation DCB 更貼近你想精進的分叉技術，此場增量價值中等；若更需要解剖異常 + 器械選擇，則值得換。',
                'key_takeaways': [
                    '異常冠脈起源、迂迴型或分支異常的影像預規劃',
                    '複雜解剖下的導管選擇、導絲策略與介入順序',
                    '支架選擇，尤其 LM 病變或多層支架情境的邏輯',
                ],
            },
        },
    ],
    ('Wednesday', '08:30-09:30'): [
        {
            'sessionId': 'WED-0830-BLEU-001',
            'keyNames_fallback': ['E. Barbato', 'G. Richardt', 'B. Vaquerizo'],
            'note': '★ 鈣化 PCI pitfalls + 併發症。Barbato 主持（前 EAPCI President）+ Richardt + Vaquerizo。',
            'briefing': {
                'summary': '鈣化病灶複雜 PCI 的經典案例討論。前 EAPCI 會長 Barbato 主持，搭配 Richardt（LIVE 示範核心術者）與 Vaquerizo 處理支架膨脹不足及冠脈穿孔案例，直接示範影像引導決策。',
                'why_attend': '你身處台灣高量介入中心，每月都碰鈣化。本場透過真實案例演練支架膨脹不足、穿孔併發症的影像診斷與逐步管理，涵蓋 IVUS 引導再擴張、covered stent 應用等操作細節，教學密度高於 Lancet Commission 的宏觀層次。',
                'key_takeaways': [
                    '支架膨脹不足的 IVUS 診斷標準與升級策略（超高壓、rota、IVL）',
                    '冠脈穿孔分級與實時管理決策（perforation type → covered stent positioning → 預後追蹤）',
                    '何時停止升級策略、何時接受「次優」結果',
                ],
                'watch_for': 'Richardt 與 Vaquerizo 對於何時停止 vs 繼續升級的臨床判斷—這是防止過度治療的關鍵教學點。',
            },
        },
        {
            'sessionId': 'WED-0830-252A-001',
            'keyNames_fallback': ['E. Margetic', 'N. Cruden'],
            'note': '★ IVUS 引導 PCI 最佳化 + 併發症管理。CVIT（日本）+ 蘇格蘭 + 克羅埃西亞三國案例。',
            'briefing': {
                'summary': '腔內影像引導 PCI 最佳化與併發症管理。國際合作課程（CVIT 日本、蘇格蘭、克羅埃西亞）。三案例：克國病灶解剖確認、日本導絲進入夾層的 IVUS 救援、蘇格蘭反覆麻煩病灶的系統化處理。',
                'why_attend': '你對複雜解剖與併發症管理高度感興趣。獨特價值是「Why I would treat this way」的影像-決策-操作三段論—直接回答「看到 IVUS 上的夾層、邊界不適當、支架膨脹不足，下一步該做什麼」。Margetic（anchor）與 Cruden（蘇格蘭）兼具技術深度與教學能力，密度達操作室水準。',
                'key_takeaways': [
                    'IVUS 在邊界病灶的角色：clarify 解剖 → 預測支架膨脹 → 決定近端/遠端優化',
                    '導絲進入夾層平面後的 IVUS 導引再入技巧（Ostojic 示範前向 re-entry）',
                    '併發症階梯管理：dissection 分級 → side branch jailing → rescue 策略',
                ],
                'watch_for': 'Irving（蘇格蘭 LIVE 術者）在「Getting into trouble, again!」案例中對風險升級的警覺、何時中止 vs 升級決策—最具臨床借鑑價值。',
            },
        },
        {
            'sessionId': 'WED-0830-341-001',
            'keyNames_fallback': ['M. Sabate', 'H. C. Tan', 'D. Moliterno', 'G. Stefanini'],
            'note': 'ACS Hotline 論壇。Sabate + Moliterno + Stefanini。新興證據辯論。',
            'briefing': {
                'summary': 'Sabate 主播，含 Tan、Abid、Moliterno、Ricalde、Stefanini 的 Hotline 論壇，實況辯論 ACS 急性冠脈症候群的創新策略與新興證據。',
                'why_attend': 'Hotline（即時論壇）vs Lancet Commission（宏觀總結）提供不同視角。若你已在 Libby 那場獲得全景洞見，改來 Hotline 可聽臨床端對細節策略的實時辯論（實踐創新、實世界限制、爭議點）。Moliterno + Stefanini 暗示機械支持、血栓負荷與風險分層的新議題。',
                'key_takeaways': [
                    'ACS 新興策略的試驗證據與實踐轉化',
                    '高風險或複雜 ACS 亞群的個體化決策',
                    '專家共識與爭議話題的實時對話',
                ],
            },
        },
    ],
    ('Thursday', '15:00-16:00'): [
        {
            'sessionId': 'THU-1500-252B-001',
            'keyNames_fallback': ['M. Hamilos', 'V. Kocka', 'R. Byrne', 'G. Tsigkas'],
            'note': '★★ STEMI 介入併發症管理。Hamilos + Kocka 主持，Byrne/Tsigkas 討論。Ping-pong 技巧案例。',
            'briefing': {
                'summary': 'STEMI 介入併發症管理：捷克、希臘、伊拉克三國呈現冠脈血栓、冠脈瘤、「Ping-pong」技巧案例。90 分鐘深度討論，Hamilos + Kocka 主持，Byrne、Sitar、Tsigkas 參與。',
                'why_attend': '聚焦於「術中突發併發症管理」—血栓形成、血管穿孔的即時決策與技巧。相比你原選的 Complication Simulator（循序漸進的人工情境），本場是真實缺陷診斷與高難度救援術式。如果你已經有基礎模擬經驗、想升級到真實多變情境，這場是好選擇。',
                'key_takeaways': [
                    '原發性 PCI 中急性血栓形成的鑑別與藥物 vs 機械救援決策',
                    '冠脈穿孔/瘤形成的風險分層與應急技巧（IVUS 引導、支架選擇、外科 backup）',
                    'Ping-pong 技巧與先進 polymer 支架策略在倒鉤病變的實踐',
                ],
            },
        },
        {
            'sessionId': 'THU-1500-251-001',
            'keyNames_fallback': ['K. Bainey', 'B.G. Libungan', 'I. Terzic'],
            'note': '★ 多國 STEMI 急性真實案例。加、冰、波三地。失敗案例救援。',
            'briefing': {
                'summary': '多國 STEMI 急性病例討論：加拿大、冰島、波士尼亞三地團隊呈現複雜真實案例，涵蓋心源性休克、併發症、多血管疾病。90 分鐘深度。Bainey、Libungan、Terzic 主持。',
                'why_attend': '相比模擬訓練的線性情境，你將看到三個跨大陸的 STEMI 真實困境：休克時器械選擇、血流重建失敗的救援、急性出血併發症處理。多國視角強化決策思維，比單一 lab 情景更貼近台灣混合患者族群。',
                'key_takeaways': [
                    'STEMI 血流重建失敗後的分層救援策略（支架血栓、穿孔、血流動力學不穩）',
                    '休克時的冠脈介入時機與多血管處理（完全血運 vs 聚焦罪魁）',
                    '活動出血併發症下的 PCI 決策框架（抗血栓 vs 臨床急性度 trade-off）',
                ],
                'watch_for': '三案例均涉及程序失敗與併發症救援，而非單純技術執行—反映實務中最常見的困境。',
            },
        },
        {
            'sessionId': 'THU-1500-BLEU-001',
            'keyNames_fallback': ['M. Götberg', 'M. Al-Hijji', 'S. Mehta'],
            'note': 'ACS 多血管疾病診斷與血運重建分期。Götberg 主持（FFR 背景）。',
            'briefing': {
                'summary': 'ACS 多血管疾病的冠脈診斷與治療規劃：罪魁 vs 非罪魁識別，生理（FFR/iFR）+ 影像（IVUS/OCT）整合決策，分階段血運重建時機。Götberg 主持，國際討論（Al-Hijji、Colleran、Martin Moreiras、Mehta）。',
                'why_attend': '多血管 ACS 的「診斷邏輯」與「決策框架」為核心—需整合影像與生理判斷病變優先順序。台灣高血壓患者多血管疾病普遍，此場提供系統性篩選與分期策略。Götberg 是 iFR 研究的重要人物，加分。',
                'key_takeaways': [
                    'ACS 急性期多血管的罪魁鑑別：症狀、心電圖、影像三角驗證',
                    'FFR/iFR 與 IVUS/OCT 整合決策（何時同時評估、何時分期）',
                    'Index vs staged 多血管 PCI 的長期結果與選擇框架',
                ],
            },
        },
    ],
}


def make_key_names(session, fallback):
    """Build the keyNames[] shown on block cards. Use the session's speakers,
    fall back to the per-addition fallback list if none found."""
    raw = []
    sp = session.get('speakers')
    if isinstance(sp, dict):
        # anchor/spokesperson first, then operators, then a couple discussants
        for role in ['anchorpersons', 'spokespersons', 'operators', 'facilitators', 'moderators', 'discussants']:
            raw.extend(sp.get(role) or [])
    elif isinstance(sp, list):
        raw = [(s.get('name') if isinstance(s, dict) else s) for s in sp]
    raw = [n for n in raw if n]
    if raw:
        return raw[:4]
    return fallback[:4] if fallback else []


def main():
    sched = json.loads(SCHED_PATH.read_text())
    sessions = json.loads(SESSIONS_PATH.read_text())

    BAK.write_text(json.dumps(sched, ensure_ascii=False, indent=2), encoding='utf-8')

    added = 0
    for day_obj in sched['days']:
        day = day_obj['day']
        for block in day_obj['blocks']:
            key = (day, block['time'])
            if key not in ADDITIONS:
                continue
            for addition in ADDITIONS[key]:
                sid = addition['sessionId']
                sess = sessions.get(sid)
                if not sess:
                    print(f'  ! skip {sid} (not in sessions.json)')
                    continue
                # Don't duplicate: skip if already in pick or backups
                if block['pick'].get('sessionId') == sid:
                    continue
                if any(b.get('sessionId') == sid for b in (block.get('backups') or [])):
                    continue

                entry = {
                    'sessionId': sid,
                    'title': sess.get('title'),
                    'keyNames': make_key_names(sess, addition.get('keyNames_fallback', [])),
                    'note': addition['note'],
                    'briefing': addition['briefing'],
                }
                block.setdefault('backups', []).append(entry)
                added += 1
                print(f'  + {day} {block["time"]} ← {sid}')

    # Bump version / note
    sched['version'] = '2.2-backups-expanded'
    sched['v22Note'] = 'Added 13 complication/ACS-STEMI/vulnerable-plaque backups with briefings across 5 blocks. 編輯排程時現在可一鍵檢視同時段所有場次。'

    SCHED_PATH.write_text(json.dumps(sched, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Done. {added} new backups appended. Version = {sched["version"]}')


if __name__ == '__main__':
    main()
