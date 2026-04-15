# MAINTENANCE.md — EuroPCR 2026 Guide

Disaster recovery and update procedures for the PWA.

---

## 🎯 Quick Links

- **Live app**: https://alleneinstein0411-cyber.github.io/europcr-2026-guide/
- **Repo**: https://github.com/alleneinstein0411-cyber/europcr-2026-guide
- **Actions (cron status)**: https://github.com/alleneinstein0411-cyber/europcr-2026-guide/actions
- **Issues (briefings + alerts)**: https://github.com/alleneinstein0411-cyber/europcr-2026-guide/issues

---

## 🔄 Automatic Systems Running

| When | What | Where | Cost |
|------|------|-------|------|
| Every day 09:07 Taipei | PDF update check | GitHub Actions | Free |
| Every Sunday 20:13 Taipei | Schedule integrity check | GitHub Actions | Free |
| May 17, 23:00 Taipei | Pre-trip final briefing | GitHub Actions + Anthropic API | ~$0.11 |
| May 18, 20:00 Paris | Paris eve briefing | GitHub Actions + Anthropic API | ~$0.11 |
| May 19/20/21, 20:00 Paris | Nightly conference briefing | GitHub Actions + Anthropic API | ~$0.08 each |

All briefings land in GitHub Issues. Open the [Issues page](https://github.com/alleneinstein0411-cyber/europcr-2026-guide/issues?q=is:issue+label:briefing) to read them.

---

## 🔐 First-Time Setup (one-off)

### 1. Add Anthropic API key as GitHub secret

Required for AI-generated briefings. Without this, briefing workflows will skip silently.

```bash
# Get your API key from https://console.anthropic.com/settings/keys
gh secret set ANTHROPIC_API_KEY --repo alleneinstein0411-cyber/europcr-2026-guide
# Then paste your key when prompted
```

### 2. Enable mobile notifications

Install the GitHub app on your phone and enable notifications for this repo.
When a briefing is posted as an issue, you'll get a push notification.

### 3. Add app to home screen (iOS/Android)

1. Open https://alleneinstein0411-cyber.github.io/europcr-2026-guide/ on your phone
2. Safari (iOS): Share → Add to Home Screen
3. Chrome (Android): Menu → Install app

---

## 🛠️ Update Scenarios

### Scenario A — PDF minor update (speaker change, time tweak)

**When you get a "📢 EuroPCR Programme PDF Updated" GitHub issue:**

1. Download the new PDF:
   ```bash
   curl -o app-data/programme_europcr2026_updated.pdf \
     "https://interactive-programme.europa-organisation.com/pdf/europcr2026/programme_europcr2026.pdf"
   ```

2. Re-extract sessions. If you have the extraction script still:
   ```bash
   python3 scripts/extract-pdf.py  # (if present)
   ```

   Or manually: edit `app-data/sessions_all_v2.json` to correct the specific session.

3. Verify schedule integrity:
   ```bash
   python3 scripts/verify-schedule.py
   ```

4. Rebuild app data:
   ```bash
   python3 scripts/build-data.py
   ```

5. Commit and push:
   ```bash
   git add app-data/ app/data/
   git commit -m "data: update from PDF $(date +%Y-%m-%d)"
   git push
   ```

6. GitHub Actions auto-deploys to Pages within 1 minute.

### Scenario B — You're in Paris and something changed

**You're on a phone/laptop in the hotel and need to swap a session:**

Use the in-app edit UI:
1. Open the app
2. Find the block that changed
3. Tap "✏️ 編輯"
4. Change pick / backup / note / tag
5. Tap "儲存"

Your edit is saved in localStorage — persists across sessions, no network needed.

### Scenario C — App won't load (emergency fallback)

**If the hosted app is unreachable:**

1. Your localStorage data is still safe in any browser you previously loaded the app in
2. The schedule is also in `app-data/schedule_final.json` in the repo — you can open it on GitHub
3. If you need a backup: exported notes (via ⚙️ menu → 📤 匯出) can be re-imported later

### Scenario D — Briefings stop arriving

1. Check workflow status: https://github.com/alleneinstein0411-cyber/europcr-2026-guide/actions
2. If workflow is failing, check whether `ANTHROPIC_API_KEY` secret expired/was revoked
3. Re-add with `gh secret set ANTHROPIC_API_KEY`
4. Manually trigger a test: **Actions → AI Briefing Generator → Run workflow**

---

## 🚨 Data Surgery — Manual Edits

### Edit a single session

Open `app-data/sessions_all_v2.json`, find by session ID, edit, then:
```bash
python3 scripts/build-data.py
git add app-data/ app/data/
git commit -m "fix: update <sessionId>"
git push
```

### Edit the curated schedule

Open `app-data/schedule_final.json`, edit, then:
```bash
python3 scripts/build-data.py
git add app-data/schedule_final.json app/data/schedule.json
git commit -m "schedule: swap <day> <time>"
git push
```

### Clear all user-side data on phone

1. Open app → ⚙️ Settings
2. Tap "🗑️ 清除所有修改"
3. Confirm

---

## 🆘 Emergency Contacts

| Issue | Who / How |
|-------|-----------|
| App broken after deploy | `git revert HEAD && git push` |
| Pages not updating | Check Actions tab for failed deploy, re-run |
| API key compromised | Revoke at console.anthropic.com, re-add secret |
| Accidentally pushed personal file | `git filter-repo` or ask Claude |

---

*Last updated: 2026-04-15 by Claude during Session E*
