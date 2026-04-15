/* ============================================================
 * EuroPCR 2026 Guide — main app logic
 *
 * Architecture:
 *   AppData      - loaded once from /data/*.json (read-only)
 *   UserState    - persisted in localStorage (mutable: overrides, notes, tags)
 *   UIState      - in-memory only (current view, modal state)
 *
 * Views are rendered declaratively from state. Hash-based routing for
 * deep-linkable views (#/session/XXX, #/speaker/YYY, etc).
 * ============================================================ */

'use strict';

// -----------------------------------------------------------
// State
// -----------------------------------------------------------

const AppData = {
  sessions: {},    // { [sessionId]: sessionObj }
  speakers: {},    // { [speakerName]: speakerObj }
  trials: {},      // { [trialId]: trialObj }
  schedule: null,  // original curated schedule
  meta: null,
};

const UIState = {
  currentView: 'schedule',  // 'schedule' | 'speakers' | 'trials' | 'about'
  currentDay: 'Tuesday',    // 'Tuesday' | 'Wednesday' | 'Thursday'
  sheetOpen: false,
};

const LS_KEY = 'europcr2026.userState.v1';

const UserState = {
  overrides: {},      // { [blockKey]: { backupIdx: N, customSessionId: "...", skipped: bool } }
                      //   blockKey = "Day-HH:MM" e.g. "Tuesday-16:30"
  notes: {},          // { [blockKey]: "text" } OR { [sessionId]: "text" }
  tags: {},           // { [blockKey]: ["重點", "已確認"] }
  attended: {},       // { [blockKey]: true } after conference for tracking
  preferences: {
    autoDayTab: true, // auto-switch to today's tab based on conference date
  },

  load() {
    try {
      const saved = localStorage.getItem(LS_KEY);
      if (saved) Object.assign(this, JSON.parse(saved));
    } catch (err) {
      console.warn('Failed to load user state:', err);
    }
  },
  save() {
    const { overrides, notes, tags, attended, preferences } = this;
    localStorage.setItem(LS_KEY, JSON.stringify({ overrides, notes, tags, attended, preferences }));
  },
  reset() {
    this.overrides = {};
    this.notes = {};
    this.tags = {};
    this.attended = {};
    localStorage.removeItem(LS_KEY);
  },
};

// -----------------------------------------------------------
// Helpers
// -----------------------------------------------------------

function $(sel, ctx = document) { return ctx.querySelector(sel); }
function $$(sel, ctx = document) { return Array.from(ctx.querySelectorAll(sel)); }

function blockKey(day, time) { return `${day}-${time.split('-')[0]}`; }

function toast(msg, kind = '', duration = 2200) {
  const el = $('#toast');
  el.textContent = msg;
  el.className = 'toast ' + kind;
  el.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { el.hidden = true; }, duration);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

/**
 * Parse "E. Barbato(A)" -> { name: "E. Barbato", tier: "A" }
 * Parse "T. Cuisset"    -> { name: "T. Cuisset", tier: null }
 */
function parseSpeakerRef(ref) {
  const m = ref.match(/^(.+?)\((S|A|B)\)$/);
  if (m) return { name: m[1].trim(), tier: m[2] };
  return { name: ref.trim(), tier: null };
}

function speakerIsResearched(name) {
  return name in AppData.speakers;
}

function formatTime(block) {
  return block.time;  // already formatted like "16:30-17:15"
}

// -----------------------------------------------------------
// Data loading
// -----------------------------------------------------------

async function loadData() {
  const base = './data/';
  const files = ['meta.json', 'schedule.json', 'sessions.json', 'speakers.json', 'trials.json'];
  const loaded = await Promise.all(files.map(f =>
    fetch(base + f).then(r => {
      if (!r.ok) throw new Error(`Failed to load ${f}: ${r.status}`);
      return r.json();
    })
  ));
  AppData.meta = loaded[0];
  AppData.schedule = loaded[1];
  AppData.sessions = loaded[2];
  AppData.speakers = loaded[3];
  AppData.trials = loaded[4];
}

// -----------------------------------------------------------
// Current block resolution (respects user overrides)
// -----------------------------------------------------------

/**
 * Get the currently-selected pick for a block (respecting user overrides).
 * Returns { pick, isBackup: bool, isCustom: bool, backupIdx: N|null }
 */
function resolveBlockPick(day, block) {
  const key = blockKey(day, block.time);
  const ov = UserState.overrides[key];

  if (!ov) {
    return { pick: block.pick, isBackup: false, isCustom: false, backupIdx: null };
  }

  if (ov.skipped) {
    return { pick: null, isBackup: false, isCustom: false, backupIdx: null, skipped: true };
  }

  if (ov.customSessionId) {
    // User picked a custom session not in backup list
    const session = AppData.sessions[ov.customSessionId];
    if (session) {
      return {
        pick: {
          sessionId: ov.customSessionId,
          title: session.title,
          keyNames: (session.speakers || []).slice(0, 4).map(s => s.name),
          note: '(你選的自訂場次)',
        },
        isBackup: false, isCustom: true, backupIdx: null,
      };
    }
  }

  if (typeof ov.backupIdx === 'number' && block.backups && block.backups[ov.backupIdx]) {
    return { pick: block.backups[ov.backupIdx], isBackup: true, isCustom: false, backupIdx: ov.backupIdx };
  }

  // Fallback to original
  return { pick: block.pick, isBackup: false, isCustom: false, backupIdx: null };
}

// -----------------------------------------------------------
// Router & view switching
// -----------------------------------------------------------

function navigateTo(hash) {
  location.hash = hash;
}

function handleRoute() {
  const hash = location.hash || '#/schedule';
  const parts = hash.replace(/^#\//, '').split('/');

  const view = parts[0] || 'schedule';

  // Sheet routes: just open the sheet overlay; do NOT re-render #main.
  // (Re-rendering during a click event can cause the click to be "absorbed"
  //  by a freshly-rendered button underneath, including a close button.)
  const sheetRoutes = { session: true, speaker: true, trial: true };

  // Auto-close sheet when navigating away from a sheet route
  // (catches back button, programmatic navigation, etc.)
  if (!sheetRoutes[view] && UIState.sheetOpen) {
    $('#sheet').hidden = true;
    $('#sheet-backdrop').hidden = true;
    UIState.sheetOpen = false;
    document.body.style.overflow = '';
  }

  if (sheetRoutes[view]) {
    // If no underlying view was rendered yet (deep-link cold load), render once now.
    if (!$('#main').firstChild) {
      if (UIState.currentView === 'speakers') renderSpeakersView($('#main'));
      else if (UIState.currentView === 'trials') renderTrialsView($('#main'));
      else if (UIState.currentView === 'about') renderAboutView($('#main'));
      else if (UIState.currentView === 'search') renderSearchView($('#main'));
      else {
        UIState.currentView = 'schedule';
        switchView('schedule');
      }
    }
    if (view === 'session' && parts[1]) {
      openSessionSheet(decodeURIComponent(parts[1]));
    } else if (view === 'speaker' && parts[1]) {
      openSpeakerSheet(decodeURIComponent(parts[1]));
    } else if (view === 'trial' && parts[1]) {
      openTrialSheet(decodeURIComponent(parts[1]));
    }
    return;
  }

  // Non-sheet routes
  if (view === 'schedule') {
    if (parts[1]) UIState.currentDay = parts[1];
    switchView('schedule');
  } else if (view === 'speakers') {
    switchView('speakers');
  } else if (view === 'trials') {
    switchView('trials');
  } else if (view === 'about') {
    switchView('about');
  } else if (view === 'search') {
    switchView('search');
  } else {
    switchView('schedule');
  }
}

function switchView(view) {
  UIState.currentView = view;
  // Update nav state
  $$('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.view === view);
  });
  // Show/hide day tabs
  $('#day-tabs').classList.toggle('hidden', view !== 'schedule');
  render();
}

// -----------------------------------------------------------
// Render: dispatcher
// -----------------------------------------------------------

function render() {
  // loading-view is inside #main and gets wiped on first render, so guard it.
  const loading = $('#loading-view');
  if (loading) loading.hidden = true;
  updateTopBar();
  const main = $('#main');
  main.innerHTML = '';

  if (UIState.currentView === 'schedule') {
    renderSchedule(main);
  } else if (UIState.currentView === 'speakers') {
    renderSpeakersView(main);
  } else if (UIState.currentView === 'trials') {
    renderTrialsView(main);
  } else if (UIState.currentView === 'about') {
    renderAboutView(main);
  } else if (UIState.currentView === 'search') {
    renderSearchView(main);
  }
}

function updateTopBar() {
  const sub = $('#topbar-subtitle');
  if (UIState.currentView === 'schedule') {
    const day = AppData.schedule.days.find(d => d.day === UIState.currentDay);
    sub.textContent = day ? day.theme.split('—')[0].trim() : '';
  } else if (UIState.currentView === 'speakers') {
    sub.textContent = `${Object.keys(AppData.speakers).length} researched speakers`;
  } else if (UIState.currentView === 'trials') {
    sub.textContent = `${Object.keys(AppData.trials).length} trials`;
  } else {
    sub.textContent = '';
  }
}

// -----------------------------------------------------------
// Render: Schedule view
// -----------------------------------------------------------

function renderSchedule(main) {
  // Update day tab active state
  $$('.day-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.day === UIState.currentDay);
  });

  const day = AppData.schedule.days.find(d => d.day === UIState.currentDay);
  if (!day) {
    main.innerHTML = '<div class="empty-state">No schedule for this day.</div>';
    return;
  }

  // Day theme
  const themeEl = document.createElement('div');
  themeEl.className = 'day-theme';
  themeEl.innerHTML = `<strong>${escapeHtml(day.day)} 主軸：</strong> ${escapeHtml(day.theme)}`;
  main.appendChild(themeEl);

  // Blocks
  day.blocks.forEach((block, idx) => {
    const el = renderBlock(day.day, block, idx);
    main.appendChild(el);
  });
}

function renderBlock(dayName, block, idx) {
  const tpl = $('#tpl-block').content.cloneNode(true);
  const article = tpl.querySelector('.block');
  const resolved = resolveBlockPick(dayName, block);

  if (resolved.skipped) {
    article.innerHTML = `
      <header class="block-head">
        <span class="block-time">${escapeHtml(block.time)}</span>
        <span class="block-type">已跳過</span>
      </header>
      <p class="block-note">此時段標記為不參加。<button class="btn-edit" style="margin-top:8px">恢復</button></p>
    `;
    article.querySelector('.btn-edit').onclick = () => {
      delete UserState.overrides[blockKey(dayName, block.time)];
      UserState.save();
      render();
    };
    return article;
  }

  const pick = resolved.pick;
  const key = blockKey(dayName, block.time);
  article.dataset.blockId = key;
  article.dataset.day = dayName;
  article.dataset.time = block.time;

  if (block.mandatory) article.classList.add('mandatory');
  if (block.type === 'Simulation' || block.changedFromDraft) {
    article.classList.add('swapped');
  }
  if (resolved.isBackup || resolved.isCustom) article.classList.add('swapped');

  const needsReg = (AppData.schedule.registrationAlerts || [])
    .some(a => a.session === pick.sessionId);
  if (needsReg) article.classList.add('has-registration');

  // Head
  const head = article.querySelector('.block-head');
  head.querySelector('.block-time').textContent = block.time;
  const typeEl = head.querySelector('.block-type');
  typeEl.textContent = block.type || '';
  typeEl.classList.add(block.type || 'Unknown');

  const badges = [];
  if (block.mandatory) badges.push(`<span class="block-badge mandatory">必</span>`);
  if (needsReg) badges.push(`<span class="block-badge reg-required">需登記</span>`);
  head.querySelector('.block-badge').outerHTML = badges.join('');

  // Title
  article.querySelector('.block-title').textContent = pick.title || '(無標題)';

  // Speakers
  const spList = article.querySelector('.block-speakers');
  (pick.keyNames || []).forEach(ref => {
    const chip = renderSpeakerChip(ref);
    spList.appendChild(chip);
  });

  // Note
  const noteEl = article.querySelector('.block-note');
  if (pick.note) {
    noteEl.textContent = pick.note;
  } else {
    noteEl.remove();
  }

  // User note
  const userNote = UserState.notes[key];
  if (userNote) {
    const un = document.createElement('div');
    un.className = 'block-user-note';
    un.textContent = '📝 ' + userNote;
    article.querySelector('.block-note')?.after(un) || article.appendChild(un);
  }

  // Tags
  const tagsEl = article.querySelector('.block-tags');
  const tags = UserState.tags[key] || [];
  tags.forEach(t => {
    const s = document.createElement('span');
    s.className = 'block-tag';
    s.textContent = t;
    tagsEl.appendChild(s);
  });

  // Actions
  article.querySelector('.btn-detail').onclick = (e) => {
    e.stopPropagation();
    if (pick.sessionId) navigateTo(`#/session/${encodeURIComponent(pick.sessionId)}`);
  };
  article.querySelector('.btn-edit').onclick = (e) => {
    e.stopPropagation();
    openEditSheet(dayName, block, idx);
  };

  // Clicking the block itself opens detail (shortcut)
  article.onclick = () => {
    if (pick.sessionId) navigateTo(`#/session/${encodeURIComponent(pick.sessionId)}`);
  };

  return article;
}

function renderSpeakerChip(ref) {
  const { name, tier } = parseSpeakerRef(ref);
  const tpl = $('#tpl-speaker-chip').content.cloneNode(true);
  const btn = tpl.querySelector('.speaker-chip');
  btn.dataset.speakerName = name;
  btn.querySelector('.chip-name').textContent = name;
  const tierEl = btn.querySelector('.chip-tier');
  if (tier) {
    tierEl.textContent = tier;
    tierEl.classList.add(tier);
  } else {
    tierEl.remove();
  }
  if (speakerIsResearched(name)) btn.classList.add('researched');
  // Always clickable — even unresearched speakers get a minimal sessions-only card
  btn.onclick = (e) => {
    e.stopPropagation();
    navigateTo(`#/speaker/${encodeURIComponent(name)}`);
  };
  return btn;
}

/**
 * Find all sessions where a given speaker name appears (any role, any agenda item).
 * Used for building minimal cards for unresearched speakers.
 */
function findSessionsForSpeaker(name) {
  const matches = [];
  const needle = name.toLowerCase();
  for (const sid in AppData.sessions) {
    const s = AppData.sessions[sid];
    let found = false;

    // Check speakers (grouped or flat)
    if (s.speakers) {
      if (Array.isArray(s.speakers)) {
        if (s.speakers.some(sp => (sp.name || sp || '').toLowerCase() === needle)) found = true;
      } else {
        for (const role in s.speakers) {
          const names = s.speakers[role] || [];
          if (Array.isArray(names) && names.some(n => (n || '').toLowerCase() === needle)) {
            found = true;
            break;
          }
        }
      }
    }

    // Check agenda items
    if (!found && Array.isArray(s.agenda)) {
      if (s.agenda.some(a => (a.speaker || '').toLowerCase() === needle)) found = true;
    }

    if (found) matches.push(s);
  }

  // Sort by day then time
  const dayOrder = { Tuesday: 1, Wednesday: 2, Thursday: 3, Friday: 4 };
  matches.sort((a, b) => {
    const da = dayOrder[a.day] || 99, db = dayOrder[b.day] || 99;
    if (da !== db) return da - db;
    return (a.timeStart || '').localeCompare(b.timeStart || '');
  });

  return matches;
}

// -----------------------------------------------------------
// Sheet (bottom modal) — open/close
// -----------------------------------------------------------

function openSheet(contentHtml) {
  $('#sheet-content').innerHTML = contentHtml;

  // Belt-and-suspenders: directly attach onclick to every close button.
  // This works even if the delegated listener on #sheet is broken by some
  // browser extension, SW caching, or other weirdness.
  $$('#sheet-content [data-close], #sheet-content .close-sheet').forEach(btn => {
    btn.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      closeSheet();
    };
  });

  $('#sheet').hidden = false;
  $('#sheet-backdrop').hidden = false;
  UIState.sheetOpen = true;
  document.body.style.overflow = 'hidden';
}

function closeSheet() {
  $('#sheet').hidden = true;
  $('#sheet-backdrop').hidden = true;
  UIState.sheetOpen = false;
  document.body.style.overflow = '';
  // Clear hash if we're on a detail route
  if (location.hash.match(/^#\/(session|speaker|trial)/)) {
    history.replaceState(null, '', '#/' + UIState.currentView);
  }
}

// -----------------------------------------------------------
// Session detail sheet
// -----------------------------------------------------------

function openSessionSheet(sessionId) {
  const s = AppData.sessions[sessionId];
  if (!s) {
    toast('場次資料不存在', 'error');
    return;
  }

  const trialsForSession = Object.values(AppData.trials)
    .filter(t => t.sessionId === sessionId || (Array.isArray(t.sessionId) && t.sessionId.includes(sessionId)));

  // Find which block this sessionId is associated with (as pick OR backup), for briefing + notes
  let associatedKey = null;
  let associatedBriefing = null;
  AppData.schedule.days.forEach(d => {
    d.blocks.forEach(b => {
      if (b.pick && b.pick.sessionId === sessionId) {
        associatedKey = blockKey(d.day, b.time);
        if (b.pick.briefing) associatedBriefing = b.pick.briefing;
      }
      (b.backups || []).forEach(bu => {
        if (bu.sessionId === sessionId) {
          if (!associatedKey) associatedKey = blockKey(d.day, b.time);
          if (!associatedBriefing && bu.briefing) associatedBriefing = bu.briefing;
        }
      });
    });
  });

  const html = `
    <div class="sheet-header">
      <div>
        <h2>${escapeHtml(s.title)}</h2>
        ${s.subtitle ? `<p style="font-size:13px; color: var(--text-muted); margin-top: 4px">${escapeHtml(s.subtitle)}</p>` : ''}
      </div>
      <button class="icon-btn" data-close style="background:var(--bg-subtle); flex-shrink:0">✕</button>
    </div>

    <div class="sheet-meta">
      <span>📅 ${escapeHtml(s.day)} ${escapeHtml(s.date)}</span>
      <span>⏰ ${escapeHtml(s.timeStart)}-${escapeHtml(s.timeEnd)}</span>
      <span>🏛️ ${escapeHtml(s.room)}</span>
      <span style="text-transform: capitalize">🏷️ ${escapeHtml(s.track || 'n/a')}</span>
    </div>

    ${s.sponsor ? `<p style="font-size: 12px; color: var(--text-muted); margin-bottom: 14px">💼 ${escapeHtml(s.sponsor.replace(/^Sponsored by\s+/i, 'Sponsored by '))}</p>` : ''}

    ${associatedBriefing ? renderBriefingBox(associatedBriefing) : ''}

    ${trialsForSession.length ? `
      <div class="sheet-section">
        <h3>📑 Trials</h3>
        <ul class="sheet-list">
          ${trialsForSession.map(t => `
            <li class="clickable" onclick="navigateTo('#/trial/${encodeURIComponent(t.trialId)}')">
              <span>${escapeHtml(t.trialName || t.trialId)}</span>
              <span style="color: var(--text-muted)">→</span>
            </li>
          `).join('')}
        </ul>
      </div>
    ` : ''}

    ${s.learningObjectives && s.learningObjectives.length ? `
      <div class="sheet-section">
        <h3>🎯 Learning Objectives</h3>
        <ol style="padding-left: 20px; margin: 0">
          ${s.learningObjectives.map(o => `<li style="margin-bottom: 4px; font-size: 13px; line-height: 1.45">${escapeHtml(o)}</li>`).join('')}
        </ol>
      </div>
    ` : ''}

    ${renderSessionSpeakersSection(s.speakers)}

    ${s.agenda && s.agenda.length ? `
      <div class="sheet-section">
        <h3>📋 Agenda</h3>
        <div>
          ${s.agenda.map((item, i) => `
            <div class="agenda-item">
              <div class="agenda-num">${i + 1}.</div>
              <div class="agenda-body">
                ${escapeHtml(item.title || item.item || '')}
                ${item.speaker ? `<div class="agenda-speaker">
                  — <button class="speaker-link" onclick="event.stopPropagation(); navigateTo('#/speaker/${encodeURIComponent(item.speaker)}')">${escapeHtml(item.speaker)}</button>
                </div>` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    ` : ''}

    ${associatedKey && UserState.notes[associatedKey] ? `
      <div class="sheet-section">
        <h3>📝 My Note</h3>
        <div class="block-user-note" style="margin: 0">${escapeHtml(UserState.notes[associatedKey])}</div>
      </div>
    ` : ''}

    <div class="sheet-actions">
      ${associatedKey ? `
        <button class="btn-secondary" onclick="openEditSheetByKey('${associatedKey}')">✏️ 編輯排程</button>
      ` : ''}
      <button class="btn-primary" data-close>關閉</button>
    </div>
  `;
  openSheet(html);
}

/**
 * Render the enriched briefing box for a curated block.
 * The briefing comes from schedule_final.json > days[].blocks[].pick.briefing (or .backups[].briefing)
 */
function renderBriefingBox(b) {
  if (!b) return '';
  return `
    <div class="briefing-box">
      <h3>🎯 Dr. Chang's Briefing</h3>
      ${b.summary ? `<div class="briefing-summary">${escapeHtml(b.summary)}</div>` : ''}
      ${b.why_attend ? `<div class="briefing-why"><strong>為什麼要聽：</strong>${escapeHtml(b.why_attend)}</div>` : ''}
      ${b.key_takeaways && b.key_takeaways.length ? `
        <div style="margin-bottom: 6px; font-size: 12px; color: var(--text-muted); font-weight: 600">💡 聽完要帶走</div>
        <ul class="briefing-takeaways">
          ${b.key_takeaways.map(k => `<li>${escapeHtml(k)}</li>`).join('')}
        </ul>
      ` : ''}
      ${b.watch_for ? `<div class="briefing-watch"><strong>⚡ 特別注意：</strong>${escapeHtml(b.watch_for)}</div>` : ''}
    </div>
  `;
}

function renderSpeakerChipHtml(name, role) {
  const researched = speakerIsResearched(name);
  return `
    <button class="chip speaker-chip${researched ? ' researched' : ''}"
            onclick="event.stopPropagation(); navigateTo('#/speaker/${encodeURIComponent(name)}')">
      <span class="chip-name">${escapeHtml(name)}</span>
      ${role ? `<span style="font-size:10px; color: var(--text-muted); margin-left: 3px">${escapeHtml(role)}</span>` : ''}
    </button>
  `;
}

/**
 * Render speakers section. Handles both:
 *   - Flat array [{name, role}]
 *   - Grouped object { anchorpersons: [names], operators: [names], ... }
 */
function renderSessionSpeakersSection(speakers) {
  if (!speakers) return '';

  // Role label map (Chinese)
  const roleLabels = {
    anchorpersons: '主持',
    spokespersons: '發言人',
    proceduralAnalysts: '程序分析',
    operators: '操作者',
    discussants: '討論者',
    imagingAnalysts: '影像分析',
    imagingExperts: '影像專家',
    mediaDrivers: 'Media Driver',
    onstageCoordinators: 'Onstage',
    cathlabCoordinators: 'Cath Lab',
    facilitators: 'Facilitators',
    physicianTrainers: 'Trainers',
    experiencedAdvisors: '資深顧問',
    chatMasters: 'Chat Master',
    guestSpeakers: '客座',
  };

  let html = '';

  if (Array.isArray(speakers)) {
    // Flat list
    if (!speakers.length) return '';
    html = `<div style="display: flex; flex-wrap: wrap; gap: 6px">
      ${speakers.map(sp => renderSpeakerChipHtml(sp.name || sp, sp.role || '')).join('')}
    </div>`;
  } else if (typeof speakers === 'object') {
    // Grouped by role
    const sections = [];
    for (const [role, names] of Object.entries(speakers)) {
      if (!Array.isArray(names) || !names.length) continue;
      const label = roleLabels[role] || role;
      sections.push(`
        <div style="margin-bottom: 8px">
          <div style="font-size: 11px; color: var(--text-faint); margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.04em">${escapeHtml(label)}</div>
          <div style="display: flex; flex-wrap: wrap; gap: 5px">
            ${names.map(n => renderSpeakerChipHtml(n, '')).join('')}
          </div>
        </div>
      `);
    }
    if (!sections.length) return '';
    html = sections.join('');
  }

  return `
    <div class="sheet-section">
      <h3>👥 Speakers</h3>
      ${html}
    </div>
  `;
}

// -----------------------------------------------------------
// Speaker sheet
// -----------------------------------------------------------

function openSpeakerSheet(name) {
  const sp = AppData.speakers[name];

  // Unresearched: show minimal card based on session appearances
  if (!sp) {
    const relatedSessions = findSessionsForSpeaker(name);
    const html = `
      <div class="speaker-card">
        <div class="sheet-header">
          <div>
            <h2>${escapeHtml(name)}</h2>
            <p class="speaker-fullname" style="color: var(--text-faint); font-style: italic">未研究過 — 只顯示議程出現紀錄</p>
          </div>
          <button class="icon-btn" data-close style="background:var(--bg-subtle); flex-shrink:0">✕</button>
        </div>

        ${relatedSessions.length ? `
          <div class="sheet-section">
            <h3>🗓️ Sessions at EuroPCR 2026 (${relatedSessions.length})</h3>
            <ul class="sheet-list">
              ${relatedSessions.slice(0, 30).map(s => `
                <li class="clickable" onclick="navigateTo('#/session/${encodeURIComponent(s.id)}')">
                  <div style="flex: 1; min-width: 0">
                    <div style="font-size: 12px; color: var(--text-muted)">${escapeHtml(s.day)} ${escapeHtml(s.timeStart)} · ${escapeHtml(s.room || '')}</div>
                    <div style="font-size: 13px; margin-top: 2px; line-height: 1.3">${escapeHtml(s.title)}</div>
                  </div>
                  <span style="color: var(--text-muted); flex-shrink: 0">→</span>
                </li>
              `).join('')}
            </ul>
            ${relatedSessions.length > 30 ? `<p style="text-align:center; color: var(--text-faint); font-size:12px; margin-top:8px">顯示前 30 場，共 ${relatedSessions.length} 場</p>` : ''}
          </div>
        ` : `
          <div class="empty-state">
            <p>查無相關場次</p>
            <p style="font-size:12px; margin-top: 8px">可能是 PDF 解析造成的名字碎片</p>
          </div>
        `}
      </div>
    `;
    openSheet(html);
    return;
  }

  // Full speaker card (researched)
  // Find sessions this speaker is in
  const relatedSessions = (sp.sessionIds || [])
    .map(id => AppData.sessions[id])
    .filter(Boolean);

  const html = `
    <div class="speaker-card">
      <div class="sheet-header">
        <div>
          <h2>${escapeHtml(sp.name)}</h2>
          <p class="speaker-fullname">${escapeHtml(sp.fullName || '')}</p>
          <p class="speaker-institution">${escapeHtml(sp.institution || '')}</p>
          <div class="speaker-tier-large ${sp.tier}">Tier ${sp.tier}</div>
        </div>
        <button class="icon-btn" data-close style="background:var(--bg-subtle); flex-shrink:0">✕</button>
      </div>

      ${sp.oneLiner ? `<div class="speaker-oneliner">${escapeHtml(sp.oneLiner)}</div>` : ''}

      ${sp.expertise && sp.expertise.length ? `
        <div class="sheet-section">
          <h3>🧠 Expertise</h3>
          <div class="speaker-expertise-list">
            ${sp.expertise.map(e => `<span class="tag">${escapeHtml(e)}</span>`).join('')}
          </div>
        </div>
      ` : ''}

      ${sp.keyContributions && sp.keyContributions.length ? `
        <div class="sheet-section">
          <h3>📝 Key Contributions</h3>
          <ul style="padding-left: 20px; margin: 0">
            ${sp.keyContributions.map(c => `<li style="margin-bottom: 4px; font-size: 13px; line-height: 1.45">${escapeHtml(c)}</li>`).join('')}
          </ul>
        </div>
      ` : ''}

      ${sp.whyListen ? `
        <div class="sheet-section">
          <h3>🎯 Why Listen</h3>
          <p style="font-size: 14px; line-height: 1.55; margin: 0">${escapeHtml(sp.whyListen)}</p>
        </div>
      ` : ''}

      ${sp.pmids && sp.pmids.length ? `
        <div class="sheet-section">
          <h3>📚 Key PMIDs</h3>
          <div class="pmid-list">
            ${sp.pmids.map(p => `
              <a href="https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(p)}/" target="_blank" rel="noopener"
                 style="display:inline-block; padding: 4px 10px; margin: 0 4px 4px 0; background: var(--bg-subtle); border-radius: 4px; font-size: 12px; color: var(--accent)">${escapeHtml(p)}</a>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${relatedSessions.length ? `
        <div class="sheet-section">
          <h3>🗓️ Sessions at EuroPCR 2026 (${relatedSessions.length})</h3>
          <ul class="sheet-list">
            ${relatedSessions.slice(0, 20).map(s => `
              <li class="clickable" onclick="navigateTo('#/session/${encodeURIComponent(s.id)}')">
                <div style="flex: 1; min-width: 0">
                  <div style="font-size: 12px; color: var(--text-muted)">${escapeHtml(s.day)} ${escapeHtml(s.timeStart)}</div>
                  <div style="font-size: 13px; margin-top: 2px; line-height: 1.3">${escapeHtml(s.title)}</div>
                </div>
                <span style="color: var(--text-muted); flex-shrink: 0">→</span>
              </li>
            `).join('')}
          </ul>
        </div>
      ` : ''}
    </div>
  `;
  openSheet(html);
}

// -----------------------------------------------------------
// Trial sheet
// -----------------------------------------------------------

function openTrialSheet(trialId) {
  const t = AppData.trials[trialId];
  if (!t) {
    toast('試驗資料不存在', 'error');
    return;
  }

  const facts = [
    ['Trial', t.trialName || ''],
    ['Presenter', t.presenter || ''],
    ['Session', Array.isArray(t.sessionId) ? t.sessionId.join(', ') : (t.sessionId || '')],
    ['Type', t.type || ''],
    ['Domain', t.domain || ''],
    ['Design', t.design || ''],
    ['Main Result', t.mainResult || t.expectedResult || ''],
    ['Prior Result', t.priorResult || t.result12mo || ''],
  ].filter(([, v]) => v);

  const html = `
    <div class="sheet-header">
      <div>
        <h2>${escapeHtml(t.trialName || t.trialId)}</h2>
        ${t.domain ? `<span class="trial-domain">${escapeHtml(t.domain)}</span>` : ''}
      </div>
      <button class="icon-btn" data-close style="background:var(--bg-subtle); flex-shrink:0">✕</button>
    </div>

    ${t.question ? `
      <div class="trial-question">
        <strong>核心問題：</strong>${escapeHtml(t.question)}
      </div>
    ` : ''}

    <div class="sheet-section">
      <ul class="trial-fact-list">
        ${facts.map(([label, value]) => `
          <li>
            <span class="label">${escapeHtml(label)}</span>
            <span class="value">${escapeHtml(value)}</span>
          </li>
        `).join('')}
      </ul>
    </div>

    ${t.componentTrials && t.componentTrials.length ? `
      <div class="sheet-section">
        <h3>🧩 Component Trials</h3>
        <ul style="padding-left: 20px; margin: 0">
          ${t.componentTrials.map(c => `<li style="font-size: 13px; line-height: 1.45; margin-bottom: 6px">${escapeHtml(c)}</li>`).join('')}
        </ul>
      </div>
    ` : ''}

    ${t.whyAttend ? `
      <div class="sheet-section">
        <h3>🎯 為什麼要聽</h3>
        <p style="font-size: 14px; line-height: 1.55; margin: 0">${escapeHtml(t.whyAttend)}</p>
      </div>
    ` : ''}

    ${t.clinicalImpact ? `
      <div class="sheet-section">
        <h3>💊 臨床影響</h3>
        <p style="font-size: 14px; line-height: 1.55; margin: 0">${escapeHtml(t.clinicalImpact)}</p>
      </div>
    ` : ''}

    ${t.keyPmids && t.keyPmids.length ? `
      <div class="sheet-section">
        <h3>📚 Key PMIDs</h3>
        <div class="pmid-list">
          ${t.keyPmids.map(p => `
            <a href="https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(p)}/" target="_blank" rel="noopener"
               style="display:inline-block; padding: 4px 10px; margin: 0 4px 4px 0; background: var(--bg-subtle); border-radius: 4px; font-size: 12px; color: var(--accent)">${escapeHtml(p)}</a>
          `).join('')}
        </div>
      </div>
    ` : ''}
  `;
  openSheet(html);
}

// -----------------------------------------------------------
// Edit sheet (backup swap + notes + tags)
// -----------------------------------------------------------

function openEditSheet(dayName, block, idx) {
  const key = blockKey(dayName, block.time);
  const resolved = resolveBlockPick(dayName, block);

  const currentIsMain = !resolved.isBackup && !resolved.isCustom && !resolved.skipped;

  const options = [
    { type: 'main', idx: null, option: block.pick },
    ...(block.backups || []).map((b, i) => ({ type: 'backup', idx: i, option: b }))
  ];

  const html = `
    <div class="sheet-header">
      <div>
        <h2>編輯排程</h2>
        <p style="font-size: 13px; color: var(--text-muted); margin-top: 2px">${escapeHtml(dayName)} ${escapeHtml(block.time)}</p>
      </div>
      <button class="icon-btn" data-close style="background:var(--bg-subtle); flex-shrink:0">✕</button>
    </div>

    <div class="sheet-section">
      <h3>🎯 選擇場次</h3>
      ${options.map(o => `
        <label class="backup-option ${
          (o.type === 'main' && currentIsMain) ||
          (o.type === 'backup' && resolved.backupIdx === o.idx)
            ? 'active' : ''
        }">
          <input type="radio" name="pick" value="${o.type}:${o.idx === null ? '' : o.idx}">
          <span class="option-label">${o.type === 'main' ? '主選' : `備案 ${o.idx + 1}`}</span>
          <div class="option-title">${escapeHtml(o.option.title)}</div>
          ${o.option.keyNames ? `<div class="option-speakers">${o.option.keyNames.map(k => escapeHtml(k)).join(' · ')}</div>` : ''}
          ${o.option.note ? `<div class="option-note">${escapeHtml(o.option.note)}</div>` : ''}
        </label>
      `).join('')}

      <label class="backup-option" style="background: var(--bg-subtle)">
        <input type="radio" name="pick" value="skip" ${resolved.skipped ? 'checked' : ''}>
        <span class="option-label" style="color: var(--warning)">❌ 跳過</span>
        <div class="option-note">標記為不參加這個時段（休息或逛展場）</div>
      </label>
    </div>

    <div class="sheet-section">
      <h3>📝 我的備註</h3>
      <textarea class="note-editor" id="note-editor"
        placeholder="寫下筆記、觀察、提醒（斷網可用，存本機）...">${escapeHtml(UserState.notes[key] || '')}</textarea>
    </div>

    <div class="sheet-section">
      <h3>🏷️ 標籤</h3>
      <div class="tag-picker" id="tag-picker">
        ${['重點', '已確認', '待追蹤', '已出席', '已做筆記'].map(tag => `
          <span class="tag-chip ${(UserState.tags[key] || []).includes(tag) ? 'active' : ''}" data-tag="${tag}">${tag}</span>
        `).join('')}
      </div>
    </div>

    <div class="sheet-actions">
      <button class="btn-secondary" data-close>取消</button>
      <button class="btn-primary" id="save-edit">儲存</button>
    </div>
  `;
  openSheet(html);

  // Wire up interactions
  $$('.tag-chip', $('#sheet-content')).forEach(chip => {
    chip.onclick = () => chip.classList.toggle('active');
  });

  $('#save-edit').onclick = () => {
    saveEdit(dayName, block);
  };
}

function openEditSheetByKey(key) {
  // Find the block by key "Day-HH:MM"
  const [dayName, time] = key.split('-', 2);
  const fullTime = time; // Already HH:MM

  const day = AppData.schedule.days.find(d => d.day === dayName);
  if (!day) return;
  const idx = day.blocks.findIndex(b => b.time.startsWith(fullTime));
  if (idx < 0) return;
  openEditSheet(dayName, day.blocks[idx], idx);
}

function saveEdit(dayName, block) {
  const key = blockKey(dayName, block.time);
  const picked = $('input[name="pick"]:checked', $('#sheet-content'));

  if (picked) {
    const val = picked.value;
    if (val === 'skip') {
      UserState.overrides[key] = { skipped: true };
    } else if (val.startsWith('main:')) {
      delete UserState.overrides[key];
    } else if (val.startsWith('backup:')) {
      const idx = parseInt(val.split(':')[1], 10);
      UserState.overrides[key] = { backupIdx: idx };
    }
  }

  // Save note
  const note = $('#note-editor').value.trim();
  if (note) UserState.notes[key] = note;
  else delete UserState.notes[key];

  // Save tags
  const activeTags = $$('.tag-chip.active', $('#sheet-content')).map(c => c.dataset.tag);
  if (activeTags.length) UserState.tags[key] = activeTags;
  else delete UserState.tags[key];

  UserState.save();
  toast('已儲存', 'success');
  closeSheet();
  render();
}

// -----------------------------------------------------------
// Speakers view (list all researched speakers)
// -----------------------------------------------------------

function renderSpeakersView(main) {
  const speakers = Object.values(AppData.speakers);

  // Group by tier
  const byTier = { S: [], A: [], B: [] };
  speakers.forEach(s => { if (byTier[s.tier]) byTier[s.tier].push(s); });
  for (const t in byTier) byTier[t].sort((a, b) => a.name.localeCompare(b.name));

  let html = '<h2 style="padding: 0 4px 12px">60 位已研究講者</h2>';

  ['S', 'A', 'B'].forEach(tier => {
    const list = byTier[tier];
    if (!list.length) return;
    html += `<h3 style="margin: 12px 4px 8px; color: var(--text-muted); font-size: 13px; text-transform: uppercase; letter-spacing: 0.04em">Tier ${tier} — ${list.length}</h3>`;
    html += list.map(sp => `
      <div class="search-result" onclick="navigateTo('#/speaker/${encodeURIComponent(sp.name)}')">
        <div class="search-result-meta">
          <span class="speaker-tier-large ${sp.tier}" style="padding: 1px 8px; font-size: 11px">Tier ${sp.tier}</span>
          ${escapeHtml(sp.institution || '')}
        </div>
        <div class="search-result-title">${escapeHtml(sp.name)} — ${escapeHtml(sp.fullName || '')}</div>
        ${sp.oneLiner ? `<div style="font-size: 12px; color: var(--text-muted); margin-top: 4px; line-height: 1.4">${escapeHtml(sp.oneLiner.slice(0, 120))}${sp.oneLiner.length > 120 ? '...' : ''}</div>` : ''}
      </div>
    `).join('');
  });

  main.innerHTML = html;
}

// -----------------------------------------------------------
// Trials view
// -----------------------------------------------------------

function renderTrialsView(main) {
  const trials = Object.values(AppData.trials);

  let html = '<h2 style="padding: 0 4px 12px">8 個重點試驗 + Hotline</h2>';

  trials.forEach(t => {
    html += `
      <div class="search-result" onclick="navigateTo('#/trial/${encodeURIComponent(t.trialId)}')">
        <div class="search-result-meta">
          ${t.domain ? `<span class="trial-domain" style="margin-right: 6px">${escapeHtml(t.domain)}</span>` : ''}
          ${escapeHtml(t.presenter || '')}
        </div>
        <div class="search-result-title">${escapeHtml(t.trialName || t.trialId)}</div>
        ${t.question ? `<div style="font-size: 12px; color: var(--text-muted); margin-top: 4px; line-height: 1.4">❓ ${escapeHtml(t.question.slice(0, 140))}${t.question.length > 140 ? '...' : ''}</div>` : ''}
      </div>
    `;
  });

  main.innerHTML = html;
}

// -----------------------------------------------------------
// Search view — fuzzy search all 547 sessions
// -----------------------------------------------------------

function renderSearchView(main) {
  main.innerHTML = `
    <input type="text" class="search-input" id="search-input" placeholder="搜尋場次、講者、試驗、房間..." autofocus>
    <div id="search-results" style="margin-top: 12px"></div>
  `;

  const input = $('#search-input');
  input.oninput = () => {
    const q = input.value.trim().toLowerCase();
    renderSearchResults(q);
  };
  renderSearchResults('');
}

function renderSearchResults(q) {
  const container = $('#search-results');
  if (!q) {
    container.innerHTML = '<div class="empty-state">輸入關鍵字搜尋...</div>';
    return;
  }

  const sessions = Object.values(AppData.sessions);
  const matches = sessions.filter(s => {
    const blob = [
      s.title, s.subtitle, s.sponsor, s.room, s.type,
      (s.speakers || []).map(sp => sp.name).join(' '),
      (s.agenda || []).map(a => (a.title || a.item || '') + ' ' + (a.speaker || '')).join(' ')
    ].join(' ').toLowerCase();
    return blob.includes(q);
  }).slice(0, 50);

  if (!matches.length) {
    container.innerHTML = '<div class="empty-state">無結果</div>';
    return;
  }

  container.innerHTML = matches.map(s => `
    <div class="search-result" onclick="navigateTo('#/session/${encodeURIComponent(s.id)}')">
      <div class="search-result-meta">
        📅 ${escapeHtml(s.day)} ${escapeHtml(s.timeStart)} · 🏛️ ${escapeHtml(s.room)} · ${escapeHtml(s.type || '')}
      </div>
      <div class="search-result-title">${escapeHtml(s.title)}</div>
    </div>
  `).join('');
}

// -----------------------------------------------------------
// About / Settings view
// -----------------------------------------------------------

function renderAboutView(main) {
  const m = AppData.meta;
  const overrideCount = Object.keys(UserState.overrides).length;
  const noteCount = Object.keys(UserState.notes).length;
  const tagCount = Object.values(UserState.tags).flat().length;

  main.innerHTML = `
    <h2 style="padding: 4px 4px 16px">EuroPCR 2026 Guide</h2>

    <div style="background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 16px">
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
        <span style="color: var(--text-muted)">Data version</span>
        <span style="font-family: var(--font-mono); font-size: 13px">${escapeHtml(m.dataVersion)}</span>
      </div>
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
        <span style="color: var(--text-muted)">PDF version</span>
        <span style="font-size: 13px">${escapeHtml(m.pdfVersion)}</span>
      </div>
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
        <span style="color: var(--text-muted)">Build time</span>
        <span style="font-family: var(--font-mono); font-size: 12px">${escapeHtml(m.buildTime.slice(0, 19).replace('T', ' '))}</span>
      </div>
      <hr style="border: none; border-top: 1px solid var(--border); margin: 12px 0">
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
        <span style="color: var(--text-muted)">Sessions</span>
        <span>${m.counts.sessions}</span>
      </div>
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
        <span style="color: var(--text-muted)">Researched speakers</span>
        <span>${m.counts.speakers}</span>
      </div>
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
        <span style="color: var(--text-muted)">Trials</span>
        <span>${m.counts.trials}</span>
      </div>
      <div style="display: flex; justify-content: space-between">
        <span style="color: var(--text-muted)">Scheduled blocks</span>
        <span>${m.counts.scheduledBlocks}</span>
      </div>
    </div>

    <div style="background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 16px">
      <h3 style="font-size: 14px; margin-bottom: 12px">🗂️ 我的修改</h3>
      <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px">
        <span style="color: var(--text-muted)">排程覆蓋</span>
        <span>${overrideCount}</span>
      </div>
      <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px">
        <span style="color: var(--text-muted)">個人備註</span>
        <span>${noteCount}</span>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 13px">
        <span style="color: var(--text-muted)">標籤</span>
        <span>${tagCount}</span>
      </div>
      <div style="display: flex; gap: 8px; margin-top: 12px">
        <button class="btn-secondary" onclick="exportUserData()" style="flex: 1">📤 匯出筆記</button>
        <button class="btn-secondary" onclick="importUserData()" style="flex: 1">📥 匯入</button>
      </div>
      <button class="btn-secondary" onclick="resetUserData()" style="margin-top: 8px; background: var(--accent-soft); color: var(--accent); width: 100%">🗑️ 清除所有修改（小心）</button>
    </div>

    <div style="background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 16px">
      <h3 style="font-size: 14px; margin-bottom: 10px">🔄 App 更新</h3>
      <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px; line-height: 1.5">
        如果 App 看起來怪怪的、點擊沒反應、或是剛更新了但看不到新內容，按這個按鈕強制重新載入。
      </p>
      <button class="btn-primary" onclick="hardRefresh()" style="width: 100%">🔄 強制重新整理（清快取 + 重載）</button>
    </div>

    <div style="background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 12px; padding: 16px">
      <h3 style="font-size: 14px; margin-bottom: 10px">🚨 登記提醒</h3>
      ${(AppData.schedule.registrationAlerts || []).map(a => `
        <div style="padding: 10px; background: #fef3c7; border-radius: 8px; margin-bottom: 8px; font-size: 13px">
          <strong>${escapeHtml(a.session)}</strong>
          <div style="margin-top: 4px">${escapeHtml(a.action)}</div>
          <div style="color: var(--text-muted); margin-top: 4px">${escapeHtml(a.reason)}</div>
        </div>
      `).join('')}
    </div>

    <p style="text-align: center; color: var(--text-faint); font-size: 11px; margin-top: 20px">
      Data last built: ${escapeHtml(m.buildTime.slice(0, 10))}<br>
      Works offline after first load.
    </p>
  `;
}

function exportUserData() {
  const data = {
    overrides: UserState.overrides,
    notes: UserState.notes,
    tags: UserState.tags,
    attended: UserState.attended,
    exportedAt: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `europcr-notes-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function importUserData() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'application/json';
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      if (data.overrides) UserState.overrides = data.overrides;
      if (data.notes) UserState.notes = data.notes;
      if (data.tags) UserState.tags = data.tags;
      if (data.attended) UserState.attended = data.attended;
      UserState.save();
      toast('已匯入', 'success');
      render();
    } catch (err) {
      toast('匯入失敗：檔案格式錯誤', 'error');
    }
  };
  input.click();
}

function resetUserData() {
  if (!confirm('確定要清除所有備註、標籤、排程覆蓋？')) return;
  UserState.reset();
  toast('已清除', 'success');
  render();
}

async function hardRefresh() {
  if (!confirm('這會清除快取並重新下載所有資料。你的備註和排程選擇都會保留（存在本機）。繼續？')) return;
  try {
    // Delete all caches
    const keys = await caches.keys();
    await Promise.all(keys.map(k => caches.delete(k)));

    // Unregister all service workers
    if (navigator.serviceWorker) {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map(r => r.unregister()));
    }

    toast('快取已清除，重新載入中...', 'success');
    // Reload bypassing cache
    setTimeout(() => {
      location.reload(true);
    }, 600);
  } catch (err) {
    toast('清除失敗：' + err.message, 'error');
  }
}

// -----------------------------------------------------------
// Init
// -----------------------------------------------------------

async function init() {
  UserState.load();

  try {
    await loadData();
  } catch (err) {
    console.error(err);
    $('#loading-view').innerHTML = `<p style="color: var(--danger)">載入失敗：${escapeHtml(err.message)}</p>`;
    return;
  }

  // Auto-pick today's tab if on conference day
  if (UserState.preferences.autoDayTab) {
    const today = new Date().toISOString().slice(0, 10);
    const confDay = AppData.schedule.days.find(d => d.date === today);
    if (confDay) UIState.currentDay = confDay.day;
  }

  // Default to Tuesday if no day set or before conference
  if (!UIState.currentDay) UIState.currentDay = 'Tuesday';

  // Bind events
  bindEvents();

  handleRoute();
}

function bindEvents() {
  // Day tabs
  $$('.day-tab').forEach(tab => {
    tab.onclick = () => {
      UIState.currentDay = tab.dataset.day;
      navigateTo(`#/schedule/${tab.dataset.day}`);
    };
  });

  // Bottom nav
  $$('.nav-btn').forEach(btn => {
    btn.onclick = () => {
      navigateTo(`#/${btn.dataset.view}`);
    };
  });

  // Top bar search
  $('#btn-search').onclick = () => navigateTo('#/search');
  $('#btn-settings').onclick = () => navigateTo('#/about');

  // Sheet backdrop
  $('#sheet-backdrop').onclick = closeSheet;

  // Persistent close button (belt-and-suspenders fallback, always in DOM)
  const persistentClose = $('#sheet-persistent-close');
  if (persistentClose) persistentClose.onclick = closeSheet;

  // Delegated close handler — any element with data-close or class="close-sheet"
  // inside the sheet will close it. This is more robust than inline onclick.
  $('#sheet').addEventListener('click', (e) => {
    const target = e.target.closest('[data-close], .close-sheet');
    if (target) {
      e.preventDefault();
      e.stopPropagation();
      closeSheet();
    }
  });

  // Swipe-down-to-close gesture on the sheet handle
  let touchStartY = null;
  const sheetEl = $('#sheet');
  sheetEl.addEventListener('touchstart', (e) => {
    // Only start tracking if touch begins near the top of the sheet (handle area)
    const rect = sheetEl.getBoundingClientRect();
    const y = e.touches[0].clientY;
    if (y - rect.top < 40) {
      touchStartY = y;
    } else {
      touchStartY = null;
    }
  }, { passive: true });
  sheetEl.addEventListener('touchmove', (e) => {
    if (touchStartY === null) return;
    const dy = e.touches[0].clientY - touchStartY;
    if (dy > 0) {
      sheetEl.style.transform = `translateY(${Math.min(dy, 300)}px)`;
    }
  }, { passive: true });
  sheetEl.addEventListener('touchend', (e) => {
    if (touchStartY === null) return;
    const dy = (e.changedTouches[0]?.clientY ?? touchStartY) - touchStartY;
    sheetEl.style.transform = '';
    if (dy > 80) closeSheet();
    touchStartY = null;
  }, { passive: true });

  // Escape to close sheet
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && UIState.sheetOpen) closeSheet();
  });

  // Hash change
  window.addEventListener('hashchange', handleRoute);
}

// Register service worker (if supported)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(err => {
      console.warn('SW registration failed:', err);
    });
  });
}

// Expose some functions for inline event handlers
window.navigateTo = navigateTo;
window.closeSheet = closeSheet;
window.toast = toast;
window.openEditSheetByKey = openEditSheetByKey;
window.exportUserData = exportUserData;
window.importUserData = importUserData;
window.resetUserData = resetUserData;
window.hardRefresh = hardRefresh;

init();
