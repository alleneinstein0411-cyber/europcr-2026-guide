# EuroPCR 2026 個人化會議指南 App -- 實作計畫

## Context

張元介醫師（花蓮慈濟醫學中心 interventional cardiologist）將出席 EuroPCR 2026（5/19-22，巴黎），需要一個**策展式的個人化會議指南**。

這不是一個查詢用的資料庫，而是一個**會前預習 + 會中導航**的私人顧問。核心價值：
- **每天打開就知道今天該去哪**：推薦行程已排好，不用花時間選場
- **每場都有 context**：為什麼推薦這場？講者是誰、做過什麼？背後的 trial 脈絡？
- **講者驅動選場**：同主題多場時，大師在哪場就去哪場
- **超越官方手冊**：官方只列題目，我們補上臨床故事和研究脈絡

**格式**：離線 HTML/PWA 單一檔案，手機瀏覽器直接開，中英混合醫學用語。

**興趣領域**：Complex PCI / Left Main、TAVI / Structural Heart、Late-Breaking Trials

**參會天數**：僅三天（5/19 Tue - 5/21 Thu）。5/22 Fri 早上 10:00 Porte Maillot 取租車出發勃根地，**不參加 Friday 場次**。

**住宿**：Résidence Palais Étoile（5/17-22），步行 3 分鐘到 Palais des Congrès。

**現有資料**：3/8 版手冊 PDF（55 頁，Tue-Thu 完整），有 4/3 更新版可下載

**影響**：
- App 只需排 3 天行程（Tue/Wed/Thu），不需要 Friday
- 3/8 版 PDF 已涵蓋所有需要的天數（Tue-Thu），缺少的 Friday 對本專案無影響
- 更新版 PDF 仍需下載以取得講者名單和 Tue-Thu 的修改

---

## Phase 1: 資料準備（Data Pipeline）

### 1a. 下載更新版手冊
- 從 EuroPCR 官網下載 4/3 版 programme PDF
- 比對 3/8 版差異，取得 Friday (5/22) 場次

### 1b. 萃取所有 Session 為結構化 JSON
- 逐頁處理 PDF，萃取每個 session block：
  - `id`, `day`, `date`, `timeStart`, `timeEnd`, `room`
  - `track` (coronary/structural/heartfailure/hypertension/pulmonary)
  - `type` (LIVE/Learning/Hotline/Hands-on/Symposium/Cases/Abstracts/etc.)
  - `title`, `description`, `learningObjectives[]`
  - `flags` (live/livestreamed/sponsored)
- 預估 500+ sessions，分批處理：Tue (p2-16), Wed (p17-41), Thu (p42-55), Fri (新版)

### 1c. 取得講者名單
- 3/8 版 PDF 只列 session 標題，**不含個別講者名字**
- 需要從更新版 PDF 或 EuroPCR.com 互動式節目表取得講者資訊
- 特別關注：Late-breaking trial presenters、LIVE case operators、Session chairs/moderators
- 將每個 session 標記其講者 ID 列表

**關鍵檔案**：
- `/Users/YUANCHIEHCHANG/Desktop/五月EuroPCR/programme_europcr2026.pdf`（現有 3/8 版）
- 待下載的 4/3 更新版

---

## Phase 2: 講者深度調查 (Speaker Intelligence) -- 核心環節

**這一步是整個專案的靈魂。** 官方手冊只列名字，我們要補上「這個人為什麼重要」。

### 2a. 識別重點講者
從取得的講者名單中，篩選出需要深度調查的人：
- Late-breaking trial presenters（所有）
- LIVE case operators（所有）
- 高相關 session (Complex PCI / TAVI / LM) 的 chairs 和 invited speakers
- 預估 60-80 位需要調查

### 2b. 認知隔離的 Subagent 講者調查

**原則：每位講者（或小批同領域講者）由獨立 subagent 處理，subagent 之間不共享 context，避免資訊交叉污染。**

每個講者 subagent 的任務：
1. PubMed 搜尋 `AuthorName[Author]` 取得發表紀錄
2. WebSearch 搜尋講者機構頁面 / 學術簡歷
3. 獨立產出結構化 JSON 卡片

每位講者卡片格式：
```json
{
  "name": "Alain Cribier",
  "institution": "Rouen University Hospital, France",
  "expertise": ["TAVI", "aortic stenosis", "balloon valvuloplasty"],
  "tier": "S",
  "oneLiner": "TAVI 發明者，2002 年完成人類首例經導管主動脈瓣植入",
  "keyContributions": [
    "2002 首例 TAVI (Lancet)",
    "Percutaneous aortic valve replacement 概念提出者"
  ],
  "whyListen": "他開創了整個 TAVI 領域，聽他的場等於聽歷史見證者的視角",
  "pmids": ["12490960"],
  "sessionIds": ["WED-0830-MAIN-001"]
}
```

講者等級定義：
- **S 級**：領域宗師 / trial PI / 技術發明者，此生必聽
- **A 級**：頂尖活躍研究者，高影響力 publications
- **B 級**：優秀臨床專家，有紮實經驗
- **C 級**：一般講者或資料不足以判斷

**執行方式**：
- 每 3-5 位同領域講者打包為一個 subagent batch（如「TAVI 講者群」「CTO 講者群」「Left Main 講者群」）
- 多個 batch 並行執行
- 最大化 subagent 並行數（通常 2-3 個同時跑）
- 結果彙整後再做交叉引用

### 2c. 認知隔離的 Subagent Trial 調查

**原則：每個 trial 由獨立 subagent 研究，一個 subagent 只處理一個 trial，確保引用品質。**

每個 trial subagent 的任務：
1. PubMed 搜尋該 trial 的先前研究（protocol paper, pilot study, 先行結果）
2. WebSearch 搜尋 ClinicalTrials.gov NCT 註冊資訊
3. 獨立產出結構化 JSON 卡片

已知 Late-breaking trials：

| Trial | 講者 | subagent 搜尋焦點 |
|-------|------|---------|
| PROTECTED TAVR + BHF PROTECT-TAVI Meta-Analysis | Rajesh Kharbanda | TAVI cerebral embolic protection devices |
| FAITAVI | Flavio Ribichini | Physiology-guided PCI in TAVI patients |
| One-Month DAPT after Drug-Coated Stent in ACS | Woong Chol Kang | Short DAPT drug-coated stent ACS |
| UK TAVI 5-year | William Toff | UK TAVI registry long-term outcomes |
| TRILUMINATE 2-year | TBD | TriClip tricuspid repair 2-year |
| Long-term PCI DES vs CABG for Left Main | Brian Bergmark | EXCEL/NOBLE 延伸追蹤 |
| LAA Closure vs NOAC in AF | Jens Erik Nielsen-Kudsk | CHAMPION-AF, LAA closure |
| LANDMARK trial | TBD | 待確認具體內容 |

每個 trial 卡片格式：
```json
{
  "trialName": "PROTECTED TAVR",
  "presenter": "Rajesh Kharbanda",
  "sessionId": "WED-0945-BLEU-001",
  "pico": {
    "population": "接受 TAVI 的 severe AS 患者",
    "intervention": "使用 cerebral embolic protection device",
    "comparator": "不使用 protection device",
    "outcome": "30 天 stroke + 新 MRI 腦梗塞"
  },
  "background": "先前 PROTECTED TAVR 試驗（2022 NEJM）顯示...",
  "clinicalSignificance": "如果 meta-analysis 確認保護效果...",
  "pmids": ["35xxxxxx"],
  "nctId": "NCT03xxx"
}
```

**執行方式**：
- 8 個 trial = 8 個獨立 subagent（可與講者調查並行）
- 每個 subagent 只看自己的 trial，不參考其他 trial 的結果
- 結果彙整後交叉引用講者和 session

### 2e. 驗證層（Verification Layer）

**問題**：認知隔離確保 subagent 之間不互相污染，但無法防止單個 subagent 內部的幻覺（如把 B 研究誤植到 A 講者、編造不存在的 PMID、機構寫錯）。

**三層驗證機制**：

#### Layer 1: PMID 硬驗證（自動化）
- 每個 subagent 產出的 PMID，用 PubMed MCP `get_article_metadata` 回查
- 確認：(a) PMID 真的存在 (b) 作者名字有出現在該論文上
- 不符合的標記為 `⚠️ unverified`，不直接刪除但標紅
- 這一步可以批次自動跑，不需要人工

#### Layer 2: 交叉三角驗證（subagent 級）
- 講者 subagent 產出後，取出「此講者的代表 trial」
- 對比 trial subagent 產出的「此 trial 的 presenter / PI」
- 兩邊必須吻合。不吻合的觸發重查：
  - 派一個**驗證 subagent**，只給它講者名 + trial 名，請它獨立確認關係
  - 三方中兩方一致的採用，全不一致的標記為 `⚠️ 待確認`

#### Layer 3: 使用者審核檢查點（人工）
- 在 Session D（策展排程）之前，產出一份**講者-Trial 對照摘要表**
- 格式：每位 S/A 級講者一行，列出歸屬的 trial 和場次
- 張醫師快速掃一眼即可發現明顯誤植（領域專家秒殺幻覺）
- 確認後才進入排程

**驗證時機**：
```
Subagent 產出 → Layer 1 PMID硬查 → Layer 2 交叉比對 → 彙整 → Layer 3 使用者掃一眼 → 進入排程
```

### 2f. Hotline Session 情報
手冊中已列出多個 Hotline sessions（各天各時段），需要：
- 預測/確認每個 Hotline 的具體 trial 發表內容
- 確認 **Wednesday 09:45 "Major Late-Breaking Trials"** 為最重要場次

---

## Phase 3: 策展排程 (Curated Scheduling)

**有了講者調查 + 主題興趣，才能做最終排程。**

### 3a. Session 綜合評分
每個 session 的最終推薦度 = **主題相關度 × 講者份量**：

| 組合 | 結果 |
|------|------|
| 高相關主題 + S/A 級講者 | **必看 -- 行程鎖定** |
| 高相關主題 + B/C 級講者 | **推薦 -- 可被更好的場次取代** |
| 低相關主題 + S 級講者 | **值得考慮 -- 大師的場跨領域也有啟發** |
| 低相關主題 + C 級講者 | 跳過 |

### 3b. 衝堂解決策略
同時段有多場推薦時，決策邏輯：
1. Late-breaking trial 永遠最高（首次發表的 trial 不會重播）
2. LIVE case by S 級 operator 次之（現場手術是 EuroPCR 精華）
3. 講者等級高的優先
4. Learning session > Case discussion（learning 有更多乾貨）
5. 被放棄的場次標記為「次選 -- 可看 replay」

### 3c. 每場附帶策展筆記
推薦行程中每場 session 都有一段**策展筆記**：
- 「這場由 Dr. X 主持，他是 Y trial 的 PI，去年在 Z 上發了重要結果...」
- 「建議先了解 EXCEL trial 的爭議，才能聽懂這場的討論脈絡」
- 「同時段的另一場 ABC 也不錯，但這場講者陣容更強」

### 3d. 產出預設行程（含備案系統）
- 四天的完整行程表，每天 3-5 個時段
- 每個時段只選一場（已解決衝堂）
- 標記空檔、午餐休息

**備案系統**：每個時段不只推薦一場，而是推薦**首選 + 1-2 個備案**：
- 首選：推薦度最高的場次（綜合主題 + 講者）
- 備案 1：同時段第二好的選擇（附一句說明為什麼排第二）
- 備案 2（若有）：不同 track 但值得考慮的場次
- App 裡一鍵切換：「首選取消了？點這裡看備案」

**場景覆蓋**：
- 講者臨時換人 → 看備案的講者是否更好
- Session 取消 → 直接切到備案
- 首選太擠坐不進去 → 轉備案教室
- 聽了 10 分鐘發現不如預期 → 中途轉場到備案

**備案資料需求**：每個時段至少要調查 2-3 場（不只首選），增加 Session B 講者調查的範圍。原本只調查首選 session 的講者，現在需要涵蓋備案 session 的講者。估計講者調查量從 60-80 人增加到 **80-120 人**。

---

## Phase 4: App 開發

### 3a. 技術架構
- **單一 HTML 檔案**，全部 CSS/JS/Data 內嵌
- 目標大小：< 1MB（預估 400-600KB）
- 使用 system font stack，不載入外部資源
- `localStorage` 儲存使用者行程選擇
- PWA manifest 以 data URI 內嵌
- 硬編碼巴黎時間 UTC+2

### 3b. 五頁式 Tab Navigation
```
┌─────────────────────────────────┐
│  [行程] [節目] [試驗] [講者] [資訊] │  ← Bottom Tab Bar
└─────────────────────────────────┘
```

1. **今日行程 (Today)** -- 預設首頁，策展過的時間軸
   - 頂部 Day tabs: 二(Tue)/三(Wed)/四(Thu)/五(Fri)
   - 每個 session 卡片顯示：時間、教室、標題、track 色條、**講者名 + 等級徽章**
   - 點擊展開：**策展筆記**（為什麼選這場）、講者簡介、trial 背景、次選場次
   - 空檔時段標示休息/自由探索
   - 「現在進行中」指示器（巴黎時間）

2. **探索 (Explore)** -- 完整手冊瀏覽器（用來臨時換場或補看）
   - Day tabs + 時段 accordion
   - 篩選：track / 類型 / 推薦度 / **講者等級**
   - 搜尋：標題、講者名、trial 名
   - 一鍵替換進行程

3. **試驗 (Trials)** -- Late-breaking trial 預習卡片
   - 每個 trial 的 PICO、研究脈絡、臨床意義
   - **講者介紹**直接嵌入卡片內
   - 連結到在哪個 session 發表

4. **大師 (Faculty)** -- 重點講者檔案
   - 按等級分組（S/A/B），**不是字母排序的電話簿**
   - 每人：江湖地位一句話、代表貢獻、出現的所有 sessions
   - 「追蹤此講者」-- 一鍵把他所有場次加入行程
   - 「同領域講者」推薦

5. **資訊 (Info)** -- 會場實用資訊
   - 教室位置說明
   - Wi-Fi、午餐、注意事項
   - 時差提醒（巴黎 UTC+2 vs 台灣 UTC+8）

### 3c. 設計風格
- 配色：EuroPCR 品牌色（紫 #6B2D8B、黃 #F5C518）
- Track 色碼：Coronary 藍、Structural 綠、HF 紅、HTN 暗紅、PE 紫
- 支援 dark mode
- Touch-friendly：最小 44px 觸控目標
- 卡片陰影、圓角現代風

---

## Phase 5: 組裝與交付

### 4a. 最終內容整合
- 嵌入所有 JSON data（sessions, speakers, trials, venue）
- 檢查交叉引用完整性
- 醫學術語校對

### 4b. 測試
- iPhone Safari 測試（主要使用場景）
- Chrome Android 測試
- 離線功能驗證（開飛航模式測試）
- localStorage 行程儲存/恢復

### 4c. 出發前最後更新
- 5/18 前最後一次檢查 EuroPCR.com 是否有行程異動
- 更新任何新公布的 late-breaking trial 資訊

**交付物**：一個 `europcr2026-guide.html` 檔案，AirDrop 到手機即可使用

---

## 驗證方式 (Verification)

1. 手機瀏覽器開啟 HTML 檔案，確認五個 tab 都能正常切換
2. 搜尋 "left main" 確認能找到所有相關 session
3. 切換不同天確認行程正確顯示
4. 開飛航模式確認離線正常運作
5. 加入/移除 session 後關閉重開確認 localStorage 持久化
6. 試驗卡片的中文摘要正確且包含 PICO
7. 衝堂偵測正確運作

---

## 執行順序摘要

| 步驟 | 工作內容 | 產出 | 備註 |
|------|---------|------|------|
| 1 | 下載 4/3 更新版 PDF | 最新手冊 | 取得 Friday + 講者名單 |
| 2 | 萃取所有 sessions → JSON | 結構化 sessions | 500+ sessions，含講者欄位 |
| 3 | **講者深度調查**（subagent 並行） | 講者檔案 60-80 人 | **核心環節** |
| 4 | Late-breaking trial 背景研究 | Trial 預習卡 | PubMed + WebSearch |
| 5 | 綜合評分 + 策展排程 | 四天推薦行程 | 主題 × 講者份量 |
| 6 | 撰寫策展筆記 | 每場附帶說明 | 「為什麼選這場」 |
| 7 | 建構 HTML app + 嵌入所有資料 | `europcr2026-guide.html` | 單一離線檔案 |
| 8 | 手機實測 + 校對 + 最後更新 | 最終版交付 | 5/18 前完成 |

**關鍵路徑**：步驟 1-2 必須先完成（取得講者名單），才能啟動步驟 3-4。步驟 3 和 4 可以並行（subagent 同時跑講者和 trial）。步驟 5 排程必須等 3+4 完成。

**認知隔離原則**：
- 講者調查：每 3-5 人一個 subagent batch，按領域分組
- Trial 調查：每個 trial 一個 subagent
- Session 策展：每天一個 subagent 獨立排程
- 所有 subagent 產出 JSON 卡片，最後由主流程彙整交叉引用

---

## 專案分拆策略

這個專案太大，需要拆成多個 session，每個 session 有明確的產出和交接點。

### Session A：資料萃取（本次或下次）
**輸入**：programme PDF (3/8版 + 4/3更新版)
**工作**：
- 下載更新版 PDF
- 萃取所有 sessions → 結構化 JSON
- 取得講者名單（從更新版 PDF 或官網）
- 初步主題標記和分類
**產出**：`app-data/sessions.json` + `app-data/speaker-list.txt`（待調查名單）
**交接**：下個 session 讀取這些檔案繼續

### Session B：講者調查
**輸入**：`app-data/speaker-list.txt`（60-80 位待調查講者）
**工作**：
- 按領域分批，每批 3-5 人
- Subagent 並行調查（PubMed + WebSearch）
- 每人產出 JSON 卡片
- 標上 S/A/B/C 等級
**產出**：`app-data/speakers.json`
**注意**：這個 session 可能需要再拆（如果 60-80 人一次跑不完）

### Session C：Trial 調查
**輸入**：已知 late-breaking trial 列表
**工作**：
- 每個 trial 一個 subagent
- PubMed 搜先前研究 + NCT 查註冊
- 產出 PICO + 背景脈絡 + 臨床意義
**產出**：`app-data/trials.json`
**可以和 Session B 並行**（不同 session 或同一 session 裡並行）

### Session C.5：驗證與使用者確認
**輸入**：speakers.json + trials.json（未驗證版）
**工作**：
- Layer 1: 批次 PMID 硬驗證（PubMed MCP 回查每個引用）
- Layer 2: 講者-Trial 交叉三角驗證，不吻合的派驗證 subagent 重查
- Layer 3: 產出摘要表供張醫師掃一眼確認
- 修正所有發現的問題
**產出**：`app-data/speakers-verified.json` + `app-data/trials-verified.json`
**這一步是品質把關，不能跳過。**

### Session D：策展排程 + 筆記
**輸入**：sessions.json + speakers-verified.json + trials-verified.json
**工作**：
- 綜合評分（主題 × 講者份量）
- 解決衝堂
- 撰寫策展筆記
- 產出四天推薦行程
**產出**：`app-data/curated-schedule.json`（含策展筆記）

### Session E：App 開發
**輸入**：所有 app-data/*.json
**工作**：
- 建構 HTML/CSS/JS
- 嵌入所有資料
- 五頁式 UI
- 手機測試
**產出**：`europcr2026-guide.html`（最終交付物）

### Session F（選用）：最後更新
- 5/18 前檢查 EuroPCR.com 是否有異動
- 更新 trial 資訊
- 重新打包 HTML

### 依賴關係圖
```
Session A (資料萃取)
    ├── Session B (講者調查) ──┐
    └── Session C (Trial調查) ─┤
                               ├── Session C.5 (驗證 + 使用者確認)
                               │       │
                               │       └── Session D (策展排程)
                               │               │
                               │               └── Session E (App 開發)
                               │                       │
                               │                       └── Session F (最後更新)
```

---

## 計畫審查：已識別問題與修正

### 問題 1：講者名單取得是關鍵瓶頸，但方案模糊 ⚠️
3/8 版 PDF 確認**不含個別講者名字**。計畫假設「從更新版 PDF 或官網取得」，但：
- 4/3 版 PDF 可能也只是增加 Friday 場次和修改部分 session 題目，未必加上講者
- 唯一可靠的講者來源是 **pcronline.com 互動式節目表**（需要逐 session 抓取）

**修正**：Session A 增加一步：先下載更新版 PDF 檢查是否含講者。若不含，改從官網互動式節目表用 WebFetch 逐 session 抓取講者資訊。這會顯著增加 Session A 的工作量，可能需要把「PDF 萃取」和「講者名單取得」拆成兩步。

### 問題 2：Session A 的範圍太大
單一 session 要做：下載新 PDF + 萃取 500+ sessions + 取得講者名單 + 初步分類。
- 讀 55 頁 PDF 本身就會佔大量 context window
- 加上新版 PDF 對比，context 會爆

**修正**：Session A 拆成兩步：
- **A1**：下載更新版 PDF → 萃取 sessions → 存 JSON（這就夠吃一個 session 了）
- **A2**：從官網取得講者名單 → 匹配到 sessions → 產出待調查名單

### 問題 3：Session B 的 subagent 數量 vs context window
60-80 位講者 ÷ 每批 3-5 人 = 12-27 個 subagent 呼叫。每個 subagent 返回的結果會回到主 context。
- 主 context 累積 20+ 個 subagent 返回值會非常大
- Agent tool 一次最多並行 2-3 個 subagent

**修正**：
- Session B 必須**分批寫入磁碟**，每完成一批就寫 JSON 到 `app-data/speakers/` 目錄
- 每批完成後，結果不要保留在 context 裡，只保留彙整摘要
- 如果 60-80 人跑不完，Session B 拆成 B1（TAVI/Structural 講者）和 B2（Coronary/LM 講者）
- 每個 subagent 用 `model: "sonnet"` 降低成本，S 級候選人用 `model: "opus"` 確保品質

### 問題 4：subagent prompt 沒有模板
計畫說「每個 subagent 獨立調查」但沒寫 prompt 模板。subagent 啟動時沒有任何 context，prompt 必須完全自包含。

**修正**：加入 subagent prompt 模板（見下方）

### 問題 5：沒有跨 session 的 manifest 追蹤狀態
計畫有 6 個 session，每個讀取前一個的產出。但沒有機制確認「前一步做完了」「做到哪裡了」。

**修正**：建立 `app-data/manifest.json`，格式：
```json
{
  "project": "europcr2026-guide",
  "status": "session_a_complete",
  "sessionsExtracted": 523,
  "speakersIdentified": 72,
  "speakersResearched": 0,
  "trialsResearched": 0,
  "verified": false,
  "scheduleCurated": false,
  "appBuilt": false,
  "lastUpdated": "2026-04-14T12:00:00"
}
```
每個 session 開始時讀 manifest 確認起點，結束時更新狀態。

### 問題 6：Session C.5 驗證可能膨脹
Layer 2 交叉驗證如果發現大量不吻合（realistic），每個不吻合都需要派驗證 subagent。

**修正**：
- 設定容錯上限：如果不吻合率 > 30%，代表 prompt 設計有問題，應該修正 prompt 重跑，而不是逐個驗證
- Layer 2 只驗證 S/A 級講者（約 15-25 人），B/C 級跳過交叉驗證
- 把 Layer 1 (PMID 硬查) 整合到每個 subagent 的 prompt 裡，讓 subagent 在產出時就自行驗證一次

### 問題 7：Phase 編號不一致
Phase 1-5 和 Session A-F 混用，Phase 4 內部用 3a/3b/3c。

**修正**：統一為 Session A-F 結構，Phase 編號移除。

### 問題 8：資料持久化路徑沒定義
「app-data/」是相對路徑，沒有指定完整目錄。

**修正**：所有中間產出存在 `/Users/YUANCHIEHCHANG/Desktop/五月EuroPCR/app-data/`，結構：
```
app-data/
├── manifest.json          # 跨 session 狀態追蹤
├── sessions.json          # Session A1 產出
├── speaker-list.json      # Session A2 產出（待調查名單）
├── speakers/              # Session B 產出（每批一個檔案）
│   ├── batch-tavi.json
│   ├── batch-coronary.json
│   └── ...
├── speakers-merged.json   # Session B 完成後合併
├── trials/                # Session C 產出（每個 trial 一個檔案）
│   ├── protected-tavr.json
│   ├── faitavi.json
│   └── ...
├── trials-merged.json     # Session C 完成後合併
├── speakers-verified.json # Session C.5 產出
├── trials-verified.json   # Session C.5 產出
└── curated-schedule.json  # Session D 產出
```

### 問題 9：B 和 C 並行的實際可行性
計畫說「可以並行」，但如果是同一個 Claude session，context window 要同時容納講者 subagent 和 trial subagent 的返回值。

**修正**：B 和 C 最好在**同一個 session 內交替執行**而非真正並行：
- 先跑 2-3 批講者 → 寫入磁碟 → 清出 context
- 跑 2-3 個 trial → 寫入磁碟 → 清出 context
- 交替進行，避免 context 堆積
- 或者如果 context 夠大（1M context），可以先全部跑 trial（只有 8 個），再專心跑講者

### 問題 10：Friday 場次的 fallback
如果更新版 PDF 仍然沒有 Friday，怎麼辦？

**修正**：
- 先從 PDF 萃取 Tue-Thu
- Friday 從 pcronline.com 互動式節目表抓取
- 如果官網也沒有 Friday（有時候最後一天到很晚才公布），app 預留 Friday tab 但標注「待更新」

---

## Subagent Prompt 模板

### 講者調查 Subagent Prompt
```
你是一個醫學文獻研究員。請調查以下 interventional cardiology 講者的背景。

講者名單：
1. [Name1] - 出現在 EuroPCR 2026 的 [Session Title]
2. [Name2] - 出現在 EuroPCR 2026 的 [Session Title]
3. [Name3] - 出現在 EuroPCR 2026 的 [Session Title]

對每位講者，請：
1. 用 PubMed search_articles 搜尋 "[LastName] [FirstInitial][Author]" 取得發表紀錄
2. 用 WebSearch 搜尋 "[FullName] interventional cardiology" 取得機構和簡歷
3. 用 get_article_metadata 取得其最重要 2-3 篇論文的完整資訊（驗證 PMID 真實存在且作者名吻合）

對每位講者，產出以下 JSON（嚴格格式）：
{
  "name": "全名",
  "institution": "機構",
  "country": "國家",
  "expertise": ["專長1", "專長2"],
  "tier": "S/A/B/C",
  "oneLiner": "一句話中文定位（20字內）",
  "keyContributions": ["貢獻1", "貢獻2"],
  "whyListen": "用中文寫，為什麼一個台灣 interventional cardiologist 該聽他的場",
  "pmids": ["已驗證的PMID"],
  "verified": true/false
}

等級標準：
- S: 領域宗師/技術發明者/重大 trial PI，全球知名
- A: 頂尖活躍研究者，高引用 publications，常受邀 EuroPCR 演講
- B: 優秀臨床專家，有紮實經驗但非頂級研究者
- C: 資料不足以判斷或一般講者

重要：
- 不確定的資訊標記為 "unverified"
- 不要編造 PMID，必須從 PubMed 實際查到
- 如果搜不到某位講者的資料，tier 標為 C 並注明 "資料不足"
```

### Trial 調查 Subagent Prompt
```
你是一個臨床試驗研究員。請深度調查以下即將在 EuroPCR 2026 發表的 late-breaking trial。

Trial: [TRIAL_NAME]
Presenter: [PRESENTER_NAME]
Session: [SESSION_TITLE] at [TIME] on [DATE]

請：
1. 用 PubMed search_articles 搜尋 "[trial name]" 取得先前發表的相關論文（protocol, pilot, 先行結果）
2. 用 WebSearch 搜尋 "ClinicalTrials.gov [trial name]" 取得 NCT 註冊資訊
3. 用 get_article_metadata 驗證找到的 PMID 確實存在

產出以下 JSON（嚴格格式）：
{
  "trialName": "試驗名稱",
  "fullTitle": "完整標題",
  "presenter": "講者",
  "nctId": "NCT號碼或null",
  "pico": {
    "population": "中文描述目標族群",
    "intervention": "中文描述介入",
    "comparator": "中文描述對照",
    "outcome": "中文描述主要終點"
  },
  "background": "200字中文：這個研究的來龍去脈，為什麼要做",
  "clinicalSignificance": "100字中文：如果結果如預期，會怎麼改變臨床 practice",
  "priorResults": "如果有先前結果，簡述",
  "pmids": ["已驗證的先前研究PMID"],
  "verified": true/false
}

重要：
- PICO 用中英混合寫（專有名詞保留英文）
- 不確定的資訊標記為 "unverified"
- 如果找不到 NCT 號碼，寫 null
- 不要編造任何 PMID
```

---

### Session 切換機制
每個 session 結束前的 checklist：
1. 將所有產出寫入 `app-data/` 目錄
2. 更新 `app-data/manifest.json` 的 status 和 nextStep
3. 更新 `.claude/.../memory/project_europcr_guide.md` 的狀態欄
4. 告訴使用者：「這個 session 做完了 [X]，下次開新 session 說 [Y] 即可繼續」

每個 session 開始時的 checklist：
1. 讀取 `app-data/manifest.json` 確認起點
2. 讀取 MEMORY.md 確認 context
3. 確認前一步的產出檔案完整
4. 開始當前 session 的工作

**Context 壓力警報**：當 subagent 返回值開始堆積，主動提醒使用者考慮分段。

### 今天可以先做什麼？
建議從 **Session A1** 開始：下載更新版 PDF、萃取 sessions → JSON。Session A2（講者名單取得）視情況同一次或下一次做。
