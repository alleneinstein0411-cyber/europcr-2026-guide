#!/usr/bin/env python3
"""
generate-briefing.py — Generate an AI-powered briefing using the Anthropic API.

Used by the GitHub Actions briefing workflow. Given the current date and
briefing type, constructs a prompt with Dr. Chang's schedule and calls
Claude Sonnet to produce a readable Chinese briefing.

Usage:
    python3 scripts/generate-briefing.py TYPE > output.md

Types:
    pre-trip   — final check before leaving Taiwan (May 17)
    paris-eve  — Paris hotel, night before conference (May 18)
    nightly    — conference-day night briefing for tomorrow (May 19-21)
    weekly     — weekly status digest (optional)

Environment:
    ANTHROPIC_API_KEY — required
    ANTHROPIC_MODEL   — default: claude-sonnet-4-20250514

Output: Markdown body (for GitHub issue or email).
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
SRC = ROOT / "app-data"

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def build_prompt(briefing_type: str) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the briefing."""
    schedule = load_json(SRC / "schedule_final.json")
    trials = load_json(SRC / "trials" / "trials_intelligence_v1.json")
    manifest = load_json(SRC / "manifest.json")

    # Common context
    now = datetime.now(timezone.utc)
    taipei_now = now + timedelta(hours=8)
    paris_now = now + timedelta(hours=2)  # CEST

    context = {
        "type": briefing_type,
        "now_utc": now.isoformat(),
        "now_taipei": taipei_now.isoformat(),
        "now_paris": paris_now.isoformat(),
        "conference_days": manifest["conferenceDays"],
        "schedule_summary": [
            {
                "day": d["day"],
                "date": d["date"],
                "theme": d["theme"],
                "blocks": [
                    {
                        "time": b["time"],
                        "type": b.get("type"),
                        "title": b["pick"].get("title"),
                        "speakers": b["pick"].get("keyNames", []),
                        "note": b["pick"].get("note", ""),
                        "mandatory": b.get("mandatory", False),
                    }
                    for b in d["blocks"]
                ],
            }
            for d in schedule["days"]
        ],
        "registration_alerts": schedule.get("registrationAlerts", []),
        "trials_highlights": [
            {"name": t.get("trialName"), "presenter": t.get("presenter"),
             "clinical_impact": t.get("clinicalImpact", "")[:200]}
            for t in trials.get("trials", [])
        ],
    }

    system_prompt = """你是 Dr. Chang 的 EuroPCR 2026 個人助理。你的工作是產生簡潔、中文、實用的會議導覽 briefing。

風格要求：
- 全程繁體中文
- 不要客套、直接切入重點
- 用項目符號和小標題結構化
- 長度控制在 400-600 字（不含原始排程細節）
- 最後給一個明確的 TL;DR（3 句話）

Dr. Chang 的 profile：
- 介入心臟科醫師（花蓮慈濟醫院）
- 興趣排序：bifurcation ~ LM > complication ~ calcification > CTO
- 台灣 cath lab 還沒做 TAVI
- 希望學歐洲 DCB 實務、動手模擬、大師 LIVE 手術
- Trial data 可以自己讀 paper，現場重點在專家互動

結構要求：
1. 開場（1 句：今天是什麼 briefing）
2. 今明兩天重點（可以跨天）
3. 需要 action 的項目（要早到、要登記、要準備問題等）
4. 小提醒（體力、穿著、場地方位）
5. TL;DR"""

    type_specific = {
        "pre-trip": "這是出發前最終 briefing。明天/後天出發到巴黎。請整理：行前最後要確認的事、三天排程的整體節奏、Trial paper 哪幾篇要先讀過。",
        "paris-eve": "這是巴黎飯店第一晚 briefing。明天（星期二）是會議第一天。請整理：明天的行程詳細、LIVE day 的節奏、早上要幾點出發、會場方位提醒。",
        "nightly": "這是會議當晚的 briefing。明天還有會議。請整理：今天的收穫點整理問題（如果有）、明天的重點行程、提醒哪些場次要提早登記或搶位。",
        "weekly": "這是每週巡檢。距離會議還有一段時間。請整理：排程是否有異動需要注意、試驗 paper 閱讀進度建議、可以先準備的事。"
    }

    user_prompt = f"""請為 Dr. Chang 產生「{briefing_type}」briefing。

背景：
{type_specific.get(briefing_type, '')}

當前時間（UTC）：{context['now_utc']}
台北時間：{context['now_taipei']}
巴黎時間：{context['now_paris']}

這是 Dr. Chang 三天的完整排程（已由你在前一個 session 協助策劃）：

```json
{json.dumps(context['schedule_summary'], ensure_ascii=False, indent=2)}
```

登記提醒：
```json
{json.dumps(context['registration_alerts'], ensure_ascii=False, indent=2)}
```

相關重點試驗：
```json
{json.dumps(context['trials_highlights'], ensure_ascii=False, indent=2)}
```

請產生 briefing（用 Markdown 格式，直接開始內容，不要前言）。
"""

    return system_prompt, user_prompt


def call_api(system: str, user: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    body = json.dumps({
        "model": MODEL,
        "max_tokens": 2048,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    # Return the concatenated text from all text blocks
    parts = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def main():
    if len(sys.argv) < 2:
        print("Usage: generate-briefing.py {pre-trip|paris-eve|nightly|weekly}", file=sys.stderr)
        return 2

    briefing_type = sys.argv[1]
    if briefing_type not in ("pre-trip", "paris-eve", "nightly", "weekly"):
        print(f"Unknown type: {briefing_type}", file=sys.stderr)
        return 2

    try:
        system, user = build_prompt(briefing_type)
        output = call_api(system, user)
        print(output)
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
