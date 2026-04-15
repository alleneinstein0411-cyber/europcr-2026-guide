#!/usr/bin/env python3
"""
add-briefings.py — Enrich schedule_final.json with per-block briefings.

Each pick + backup gets a `briefing` object with:
    - summary       : 2-4 sentence Chinese description
    - why_attend    : Why Dr. Chang specifically should care
    - key_takeaways : 1-4 action items / learning points
    - watch_for     : optional special attention note

The briefings are authored from the context of Sessions A-D (April 14-15, 2026)
where Dr. Chang's interests (bifurcation ~ LM > complication ~ calcification > CTO)
and constraints (no TAVI in current practice, LAAO low interest) were established.

Run from project root:
    python3 scripts/add-briefings.py
    python3 scripts/build-data.py   # then rebuild app/data/
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCHEDULE = ROOT / "app-data" / "schedule_final.json"

# Mapping from sessionId -> briefing object.
# Key: the sessionId as it appears in pick.sessionId or backups[].sessionId.
BRIEFINGS = {
    # ============= TUESDAY =============

    "TUE-0945-MAIN-001": {
        "summary": "EuroPCR 2026 開幕典禮。確認場地方位、拿大會 badge 和資料袋。",
        "why_attend": "開場儀式性場次。藉機摸清會場動線（Main Arena、Maillot、Studio A、Training Village 位置）— 之後三天都用得到。",
        "key_takeaways": [
            "記下 Training Village 櫃台位置（Thu 早上要登記併發症模擬）",
            "拿實體 programme book 當備案（離線可翻）"
        ]
    },

    "TUE-1000-MAIN-001": {
        "summary": "法國 Toulouse Clinique Pasteur 團隊開場 LIVE。Dumonteil 與 Tchetche 是歐洲 TAVI 量最大中心的核心操作者，一起展示完整的 TAVI 流程。",
        "why_attend": "三天 LIVE 沉浸日的開場。雖然你短期碰不到 TAVI，但看頂級術者處理 access、implant 深度、commissure alignment，對日後理解 cath lab 的 structural 方向有啟發。當作「future reference」聽。",
        "key_takeaways": [
            "熟悉 Toulouse 中心的 TAVI 流程框架",
            "觀察 Dumonteil 的影像判讀節奏"
        ],
        "watch_for": "注意 Tchetche 在 commissural alignment 上的技術細節（他是這個主題的主要推手）"
    },

    "TUE-1130-MAIN-001": {
        "summary": "兩位 S 級大師同台操刀左主幹 PCI — Lassen（歐洲分叉教父）+ Stankovic（左主幹 PCI 先驅），配 Toth 生理學視角 + Barbato guideline 觀點。",
        "why_attend": "你興趣主線（LM + bifurcation）的核心場次。明天 LBT 有 Bergmark 的左主幹 10 年 IPD 數據，今天這場先把策略基礎打牢。",
        "key_takeaways": [
            "觀察 Lassen 如何選 provisional vs 2-stent（何時升級）",
            "記住 Stankovic 對 ostial LAD/LCx 的處理順序",
            "注意 POT（proximal optimization technique）的執行細節"
        ],
        "watch_for": "如果看到 Stankovic 用 IVUS/OCT 做 landing zone 判讀，記下具體的 criteria 數字"
    },

    "TUE-1155-BLEU-001": {
        "summary": "TAVI 併發症 case discussion — Mylotte + Patterson 的 TAVI 急救場次。",
        "why_attend": "如果你未來要轉 TAVI 主攻方向才選這場。目前你沒碰 TAVI，優先度低。",
        "key_takeaways": [
            "TAVI 急性併發症的辨識時窗",
            "echo / fluoro 下的 diagnosis 速度"
        ]
    },

    "TUE-1310-BLEU-002": {
        "summary": "Fajadet（EuroPCR 共同創辦人、全球 PCI 教科書級人物）親自操刀複雜多支病變。配 Cuisset 的 ACS 策略 + Paradies 的 bifurcation DCB 經驗 + Dumonteil 支援。",
        "why_attend": "看 Fajadet 操刀是難得的體驗。複雜多支病變的 stage / sequence 決策是 cath lab 每日難題。",
        "key_takeaways": [
            "Fajadet 選哪支先做、為什麼",
            "觀察 Cuisset 在 ACS 情境下的積極 vs 保守選擇",
            "Paradies 對分支保留策略的評論"
        ],
        "watch_for": "Paradies 若討論到 bifurcation 分支 DCB，是延伸到 Thu 09:45 DCB case discussion 的橋樑"
    },

    "TUE-1310-252B-002": {
        "summary": "Nielsen-Kudsk 本人講 CHAMPION-AF 數據 + LAA closure 操作細節。為 Wed LBT 的 age subgroup 做功課。",
        "why_attend": "LAAO 不是你的優先興趣。但若未來想做 LAA closure，這場可以聽原始 trial data + operator tips。",
        "key_takeaways": [
            "CHAMPION-AF 的 age subgroup 預期結果方向",
            "Watchman FLX / Amulet 操作細節"
        ]
    },

    "TUE-1310-153-002": {
        "summary": "Ribichini + Hildick-Smith + Mashayekhi 三位 A 級講者談 DCB 在當代 PCI 的實務。",
        "why_attend": "另一個 DCB 備案，但內容會和 Thu 09:45 的 DCB bifurcation case discussion 部分重疊。"
    },

    "TUE-1445-MAIN-001": {
        "summary": "ORBITA / ORBITA-2 PI Al-Lamee 即時做 physiology 決策 — 她用 sham-controlled RCT 重新定義了穩定型心絞痛 PCI 的價值。配 Gonzalo 影像判讀 + Barbato guideline 背景。",
        "why_attend": "看她如何在 LIVE case 中即時做 physiology-based 決策 — 從 FFR reading 到 deferral vs proceed — 是教科書等級的臨床推理示範。",
        "key_takeaways": [
            "FFR cutoff 之外，Al-Lamee 還看什麼（symptoms, ischemia burden）",
            "影像 (Gonzalo) 與 physiology (Al-Lamee) 衝突時誰聽誰",
            "ORBITA 之後對 SIHD 患者 selection 態度的變化"
        ]
    },

    "TUE-1500-243-001": {
        "summary": "Mahfoud(S) 主講 renal denervation — 全球 RDN 第一人，Ribichini(A) 歐洲實務觀點。",
        "why_attend": "RDN 不是你目前的主攻。但若未來科內想發展介入性高血壓治療，這場是入門場次。"
    },

    "TUE-1630-MAILLOT-002": {
        "summary": "全會議最精華的 bifurcation DCB 場次 — Stankovic + Lassen 雙 S 級 + DCB 之父 Scheller。議程含 EBC DCB trial 最新更新、ostial LCx (Medina 0,0,1) 策略、CathWorks FFRangio 無導絲生理學。45 分鐘高密度。",
        "why_attend": "你明確感興趣的 bifurcation + DCB + 新技術三合一。Scheller 親自報告 EBC DCB trial 是第一手數據；Medina 0,0,1 是開口病灶的最棘手變體。",
        "key_takeaways": [
            "EBC DCB trial 的 12m / 24m 最新數字",
            "Scheller 對 sirolimus vs paclitaxel DCB 在分叉的建議",
            "angio-based FFR 在分叉決策的實際精度"
        ],
        "watch_for": "Medtronic 贊助場，注意區分產品推廣 vs 學術數據的比例"
    },

    "TUE-1630-251-002": {
        "summary": "Escaned + Al-Lamee 雙 S 談 IVUS/NIRS 影像 — 穩定與 ACS 的 outcome 改善。",
        "why_attend": "備案場次。雙 S 陣容強，但和主選的 bifurcation DCB 比，實戰衝擊略遜。"
    },

    "TUE-1630-252B-002": {
        "summary": "Konstantinides 講已發表的 HI-PEITHO（NEJM 2026/3）— catheter-directed therapy for intermediate-high risk PE 的 landmark RCT，61% RRR 零顱內出血。",
        "why_attend": "備案場次。數據可讀 paper，現場是 guideline implementation 解讀。PE catheter 介入非你目前主攻。"
    },

    # ============= WEDNESDAY =============

    "WED-0830-251-001": {
        "summary": "Lancet Commission 聯合場次。Peter Libby（全球動脈粥樣硬化 / 血管發炎的開山祖師）+ Al-Lamee（ORBITA 作者）+ Gonzalo 的 case discussion。重新定義 CAD 從缺血導向到動脈粥樣硬化導向。",
        "why_attend": "Paradigm-shifting 的觀念場次。Libby 一場可能改變你看 cath lab 決策的框架。Lancet Commission 的學術分量極高，也是為接下來 LBT 做思維暖身。",
        "key_takeaways": [
            "Libby 如何看 plaque biology 與 PCI 的互動",
            "從 CAD 的 lifelong 視角看 PCI 適應症",
            "CAD 再框架後，什麼樣的病人其實不該 PCI"
        ],
        "watch_for": "Gonzalo 的 case discussion 部分，他會示範影像 + 發炎 + 生理學的整合決策"
    },

    "WED-0830-THEATRE-001": {
        "summary": "Escaned + Diletti + Agostoni 的 CTO BASIC Level I LIVE。",
        "why_attend": "備案。Level I 偏基礎，以你的經驗可能多數你已知道。選主選的 Rethinking CAD 才有新觀念衝擊。"
    },

    "WED-0945-BLEU-001": {
        "summary": "★ Mandatory ★ 全會議最高優先。三大 LBT：(1) Scarsini TAVI 冠脈 IPD 統合（4 RCTs，n=1476）；(2) Bergmark 左主幹 PCI vs CABG 10 年 IPD（4 RCTs 超長期數據）；(3) Nielsen-Kudsk CHAMPION-AF age subgroup。討論團含 Leon(S)、Capodanno(A)、Krumholz(A)。",
        "why_attend": "三篇裡 Bergmark 的左主幹 10 年 IPD 跟你 #1 興趣直接相關。其他兩篇可以自己讀 paper，但 Leon / Capodanno / Krumholz 的即時點評是現場獨有的。",
        "key_takeaways": [
            "Bergmark：10 年 IPD 的 HR 和 subgroup（SYNTAX score）切點",
            "記下 Heart Team 決策邏輯的新框架",
            "Capodanno 對 TAVI 冠脈策略的立場"
        ],
        "watch_for": "Krumholz 的 outcomes research 視角可能會質疑 composite endpoint 的選擇，值得聽"
    },

    "WED-1045-MAIN-001": {
        "summary": "Fajadet 全程操刀鈣化病變 — 全球 PCI 經驗最豐富的術者之一。配 Milasinovic 的 DCB / physiology 專長，從頭到尾 90 分鐘。",
        "why_attend": "鈣化病變是每個 cath lab 每日的痛點。看全球最頂級術者完整處理 90 分鐘，教學密度比切一半高很多。你已決定放棄同時段 TAVI H2H 專心這場。",
        "key_takeaways": [
            "Fajadet 的 IVL vs RA 選擇邏輯",
            "導絲選擇在鈣化病變的細節",
            "影像判讀如何指導 debulking 策略"
        ],
        "watch_for": "對照 Thu 15:00 你要做的併發症模擬 — 看 Fajadet 怎麼避免，明天怎麼處理已發生的"
    },

    "WED-1230-MAILLOT-002": {
        "summary": "三位 A 級左主幹 / 影像專家談 OCT / IVUS 在左主幹的實務應用 — Johnson（Leeds 左主幹）、Gonzalo（OCT 大師）、Räber（Bern）。",
        "why_attend": "剛聽完上午 LBT 的左主幹 IPD 數據，這場直接講影像工具如何落地 — 邏輯最連貫。",
        "key_takeaways": [
            "Ultreon 3.0 的自動化分析在 LM PCI 能做到什麼",
            "Räber 對 OCT 在 edge dissection 辨識的細節",
            "Johnson 的 LM post-PCI MSA criteria"
        ]
    },

    "WED-1230-242AB-002": {
        "summary": "Al-Lamee + Mahfoud 雙 S — 全會議唯一雙 S 對談。RDN 360°：從 mechanism 到 real-world。",
        "why_attend": "備案。RDN 不是你主攻，但這個 S 級組合全會議僅此一場。若臨時決定轉這場，是合理選擇。"
    },

    "WED-1230-BLEU-002": {
        "summary": "De Backer + Abdel-Wahab + Dumonteil + Tchetche — 四位 A 級 TAVI 操刀者的 LIVE case。",
        "why_attend": "備案。TAVI 不是你目前主攻。"
    },

    "WED-1340-MAILLOT-002": {
        "summary": "四位 A 級影像專家談 IVUS 在鈣化病變的策略 — Barbato（ESC guideline 作者）、Gonzalo、Diletti（Rotterdam, IVUS-CHIP trial）、Johnson。",
        "why_attend": "剛看完 Fajadet 的鈣化 LIVE，這場把隱含的原則顯性化。鈣化處理 + 影像導引是日常 PCI 最需要的技能。",
        "key_takeaways": [
            "IVUS 上的鈣化角度與弧度如何決定 debulking 策略",
            "Diletti 的 IVUS-CHIP trial 核心發現",
            "Johnson 對 high-def IVUS 新機種的實際看法"
        ]
    },

    "WED-1500-STUDIOA-001": {
        "summary": "Learning Room 小組互動場次 — Barbato 帶領，Al-Bawardy 資深顧問。鈣化左主幹的安全處理 case discussion + 開放 Q&A。",
        "why_attend": "你 #1 興趣（LM + calcification）完美命中。小組格式比大堂課互動性高，可以問具體操作問題。PCR 自己標榜 Learning Room 為會議「核心體驗」。",
        "key_takeaways": [
            "從 case 中學 Barbato 的 decision tree",
            "提前準備一兩個自己的 LM + calcification 案例帶去問",
            "記下 Al-Bawardy 的實戰 tips"
        ],
        "watch_for": "小組互動要主動發言 / 提問，價值才出得來"
    },

    "WED-1500-BLEU-001": {
        "summary": "Stankovic(S) + Amabile + Lesiak 談開口病灶（isolated ostial LAD / LCx）策略。",
        "why_attend": "原本的首選，後來換成 Learning Room。Stankovic 你 Thu 還有 3 場。若 Learning Room 不合胃口可臨時轉這場。"
    },

    "WED-1500-HANDSON-001": {
        "summary": "Milasinovic facilitator — PCI bailout 模擬：mid-vessel perforation。",
        "why_attend": "備案。Thu 15:00 的鈣化併發症模擬已經涵蓋類似 complication handling，這場會部分重複。"
    },

    "WED-1635-242AB-002": {
        "summary": "MitraClip 發明者 Maisano 談亞洲解剖的 TEER 策略 — 針對亞洲人二尖瓣的尺寸、解剖變異、procedural 挑戰。",
        "why_attend": "Structural 前瞻佈局。雖然你目前科內沒做 TEER，Maisano 本人 + 亞洲解剖針對性是難得組合。當未來 5-10 年科部發展方向的參考。",
        "key_takeaways": [
            "亞洲二尖瓣 anatomy 差異",
            "Maisano 對未來 TMVR 的判斷"
        ],
        "watch_for": "這場是「遠見」不是「即戰力」。心態上當 future reference 聽。"
    },

    "WED-1635-251-002": {
        "summary": "Nielsen-Kudsk + Praz + Swaans — LAA + structural imaging 進階影像。",
        "why_attend": "備案。比起 Maisano 的 TEER 亞洲場，這場的 structural / LAA 主題對你來說更偏「已知領域」。"
    },

    # ============= THURSDAY =============

    "THU-0830-MAILLOT-001": {
        "summary": "★ Mandatory Hotline ★ SELUTION DeNovo (n=3323，sirolimus DCB vs DES) 新亞組分析 + OPTIMAL（Milasinovic 歐洲 DCB trial）首次發表。Escaned 主持，Barbato + Haude + Milasinovic 報告。",
        "why_attend": "DCB 取代 DES 在 de novo 病變是未來 5 年最大的 paradigm shift。SELUTION 12 個月 non-inferiority 已達，新亞組會告訴你哪些 subset 效果最好。OPTIMAL 是歐洲新數據首發。",
        "key_takeaways": [
            "SELUTION 的 subgroup heterogeneity（血管大小、ACS vs SIHD）",
            "OPTIMAL 的 trial design 和初步結果",
            "Escaned 主持的最後 take-home messages"
        ],
        "watch_for": "和 09:45 的 DCB bifurcation case discussion 連著聽，一脈相承"
    },

    "THU-0830-BLEU-001": {
        "summary": "Lassen(S) 談 routine primary PCI 可能出錯的地方。",
        "why_attend": "備案。主選的 DCB trials 是 Hotline 且 mandatory，幾乎不會換。"
    },

    "THU-0945-243-001": {
        "summary": "Case discussion 場。O'Kane anchor，Paradies 教 upfront DCB 側支技巧，Hildick-Smith（EBC MAIN trial PI）談主支 DES + 側支 DCB 後要不要做 FBI，陳紹良（DK Crush 發明者）帶來亞洲分叉觀點。",
        "why_attend": "這是你『好奇歐洲怎麼用 DCB』的直接回答。Case-based 互動，亞洲 + 歐洲雙觀點。陳紹良現場是難得體驗。",
        "key_takeaways": [
            "Paradies 的 upfront DCB 側支 indication 與技術 pearls",
            "Hildick-Smith 對 FBI 的 yes / no",
            "Paclitaxel vs Sirolimus 在側支的實務選擇"
        ],
        "watch_for": "若陳紹良對歐洲 DCB 策略提出反論，是非常珍貴的跨學派交流"
    },

    "THU-0945-251-001": {
        "summary": "Capodanno + Al-Lamee + Milasinovic 的學術寫作 / 審稿課。",
        "why_attend": "備案。對想投稿 EuroIntervention / JACC CI 的人有價值。但今日主選的 DCB bifurcation 對你實戰更重要。"
    },

    "THU-1045-STUDIOA-001": {
        "summary": "Stankovic facilitator 的 Learning Room 小組場 — 非左主幹真分叉病變的 provisional 策略 + 何時升級到 two-stent。H. C. Tan 資深顧問。",
        "why_attend": "你 #1 興趣核心技能。Stankovic 是 European Bifurcation Club 核心成員，小組格式讓你可以直接問操作問題。你已決定全程 60 分鐘，放棄原本要轉場的 INOCA（回放補）。",
        "key_takeaways": [
            "Stankovic 的 provisional 標準 sequence",
            "升級到 two-stent 的 trigger criteria",
            "side branch occlusion 的預測與補救"
        ],
        "watch_for": "可問他對 DCB（上一場剛聽完）的看法，看他如何整合到 bifurcation 決策"
    },

    "THU-1230-BLEU-002": {
        "summary": "★ Mandatory ★ 全會議 LM LIVE 巔峰場次。Stankovic 操刀左主幹 + 複雜分叉支架，Johnson + Lesiak + Hovasse 配合。",
        "why_attend": "Stankovic 是整個會議你排了 4 次的最多 S 級講者。這是他親自操刀的高峰。配合 Wed LBT 的左主幹 IPD 數據完整收束。",
        "key_takeaways": [
            "Stankovic 的 LM 技術 signature moves（POT, kissing, re-POT）",
            "CSP（complex stent procedure）的 sequence 決策",
            "即時 troubleshooting 的思路"
        ],
        "watch_for": "和 Tue 11:30 Lassen + Stankovic LIVE 做比較 — 風格異同"
    },

    "THU-1500-143-001": {
        "summary": "Calcium Skills Lab hands-on — 鈣化 PCI 併發症處理模擬：burr entrapment + perforation。Amabile + Mahadevan + Milasinovic 教練一對三指導。Boston Scientific + Heartroid + Terumo 贊助。",
        "why_attend": "你要的『動手練』精準對應。Complication 在你興趣排序第二。這種 burr entrapment 實戰你回國很難複製（模擬器才能安全練）。",
        "key_takeaways": [
            "Burr entrapment 的 stepwise bailout algorithm",
            "Perforation 的 covered stent / coil / fat embolization 使用時機",
            "影像在 complication 判讀的角色"
        ],
        "watch_for": "⚠️ Thu 早上一到會場直接衝 Training Village 櫃台登記！僅約 18 個名額 first-come first-served。"
    },

    "THU-1500-MAILLOT-001": {
        "summary": "Leon + Capodanno + Dumonteil — TAVI 耐久性的最新證據與未來判斷。",
        "why_attend": "備案。TAVI 目前碰不到，優先度低。但 Leon 本人 + 耐久性主題是 hot topic。"
    },

    "THU-1500-142-001": {
        "summary": "Stankovic + Toth — CT 導引 bifurcation / ostial 病灶的最佳 fluoroscopic 投影角度選擇。",
        "why_attend": "⚡ 重要備案：若 Thu 15:00 併發症模擬搶不到位，立刻轉這場。Stankovic + Toth 的 bifurcation CT projection 是冷門但實用主題。"
    },

    "THU-1615-153-001": {
        "summary": "Lassen 帶 case discussion — 模糊左主幹病變的 severity 評估與決策：angio 灰色地帶、生理學 vs 影像衝突、何時 PCI vs CABG vs conservative。",
        "why_attend": "三天的完美收尾。這是每天都會遇到的臨床問題 — 看到一個不確定的 LM 到底怎麼辦。歐洲分叉教父的實戰指導。",
        "key_takeaways": [
            "Lassen 的 severity 判讀 checklist（angiographic + physiological + imaging）",
            "Heart Team 交棒的時機點",
            "deferral 的安全性如何跟病人溝通"
        ],
        "watch_for": "整合三天所有所學收束"
    },

    "THU-1630-MAIN-001": {
        "summary": "Abdel-Wahab + Hildick-Smith + Paradies 的 bifurcation LIVE from Leipzig。",
        "why_attend": "備案。16:30 開始，比主選 Lassen 晚 15 分鐘。若 Lassen 場不合胃口可轉場。"
    },

    "THU-1635-THEATRE-001": {
        "summary": "Mahfoud + Ribichini — 全球首例 radial approach renal denervation LIVE。",
        "why_attend": "備案。歷史性場次（世界首例 radial RDN），但 RDN 不是你主攻。三天尾聲體力考量。"
    },
}


def apply_briefings():
    with open(SCHEDULE, encoding="utf-8") as f:
        schedule = json.load(f)

    applied = 0
    missing = []

    for day in schedule.get("days", []):
        for block in day.get("blocks", []):
            # Apply to pick
            pick = block.get("pick", {})
            sid = pick.get("sessionId")
            if sid:
                if sid in BRIEFINGS:
                    pick["briefing"] = BRIEFINGS[sid]
                    applied += 1
                else:
                    missing.append((day["day"], block["time"], "pick", sid))

            # Apply to backups
            for bu in block.get("backups", []) or []:
                bsid = bu.get("sessionId")
                if bsid:
                    if bsid in BRIEFINGS:
                        bu["briefing"] = BRIEFINGS[bsid]
                        applied += 1
                    else:
                        missing.append((day["day"], block["time"], "backup", bsid))

    # Write back
    with open(SCHEDULE, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    print(f"Applied {applied} briefings to schedule_final.json")
    if missing:
        print(f"\nMissing briefings for {len(missing)} session(s):")
        for d, t, kind, sid in missing:
            print(f"  {d} {t} [{kind}] {sid}")
    print(f"\nTotal briefings in map: {len(BRIEFINGS)}")


if __name__ == "__main__":
    apply_briefings()
