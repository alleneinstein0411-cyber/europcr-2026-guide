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
  currentView: 'schedule',  // 'schedule' | 'speakers' | 'trials' | 'about' | 'session' | 'speaker' | 'trial' | 'edit' | 'search'
  currentDay: 'Tuesday',    // 'Tuesday' | 'Wednesday' | 'Thursday'
  detailId: null,           // current session/speaker/trial id if in detail view
  previousScheduleDay: 'Tuesday',  // so back button returns to the right day
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
// Topic/category rendering helpers (v2.2)
// -----------------------------------------------------------

// Topic label map — short Chinese label for compact display
const TOPIC_LABELS = {
  'ACS-STEMI':        'ACS/STEMI',
  'Complications':    '併發症',
  'VulnerablePlaque': '脆弱斑塊',
  'LM':               '左主幹',
  'Bifurcation':      '分叉',
  'Calcium':          '鈣化',
  'CTO':              'CTO',
  'Imaging':          'IVUS/OCT',
  'Physiology':       '生理學',
  'DCB':              'DCB',
  'TAVI':             'TAVI',
  'LAA':              'LAA',
  'Mitral':           '二尖瓣',
  'Tricuspid':        '三尖瓣',
  'PE':               'PE',
  'HF-Shock':         'HF/Shock',
  'Hypertension':     'RDN',
  'DAPT':             'DAPT',
  'AI-Innovation':    'AI',
  'Simulation':       '模擬',
  'Access':           '入徑',
};

const CATEGORY_LABELS = {
  'Coronary':          'Coronary',
  'Structural':        'Structural',
  'HeartFailure':      'Heart Failure',
  'Hypertension':      'Hypertension',
  'Peripheral':        'Peripheral',
  'PulmonaryEmbolism': 'Pulmonary Embolism',
  'NursesAllied':      'Nurses & Allied',
  'Sponsored':         'Sponsored',
};

// Dr. Chang's explicit interest topics — used to star/highlight sessions in concurrent lists
const INTEREST_TOPICS = ['ACS-STEMI', 'Complications', 'VulnerablePlaque'];

/** Render array of category pills (coloured square + label, official-app style). */
function renderCategoryPillsHtml(cats) {
  if (!cats || !cats.length) return '';
  return cats.map(c => `<span class="cat-pill ${escapeHtml(c)}">${escapeHtml(CATEGORY_LABELS[c] || c)}</span>`).join('');
}

/** Render array of topic pills (smaller, topic-colour-coded).
 *  Optional `starred` set highlights pills for user's interest topics.
 */
function renderTopicPillsHtml(topics, opts = {}) {
  if (!topics || !topics.length) return '';
  const limit = opts.limit || 6;
  const shown = topics.slice(0, limit);
  const rest  = topics.length - shown.length;
  const starInterests = opts.starInterests !== false;
  const html = shown.map(t => {
    const label = TOPIC_LABELS[t] || t;
    const star = starInterests && INTEREST_TOPICS.includes(t) ? '★ ' : '';
    return `<span class="topic-pill Tag-${escapeHtml(t)}">${star}${escapeHtml(label)}</span>`;
  }).join('');
  const more = rest > 0 ? `<span class="topic-pill" style="background: var(--bg-subtle); color: var(--text-muted)">+${rest}</span>` : '';
  return html + more;
}

/** Does this session touch one of Dr. Chang's interest topics? */
function sessionHitsInterests(session) {
  const t = session && session.topics;
  return !!(t && t.some(x => INTEREST_TOPICS.includes(x)));
}

/** Lookup the session (enriched with topics/trackCategories/location) backing a schedule pick or backup. */
function sessionFor(pickOrBackup) {
  return pickOrBackup && pickOrBackup.sessionId ? AppData.sessions[pickOrBackup.sessionId] : null;
}

/** Render location box for session detail. */
function renderLocationBoxHtml(loc) {
  if (!loc) return '';
  const level = loc.levelLabel || '';
  const wing = loc.wing || '';
  const walk = loc.walk || '';
  return `
    <div class="location-box">
      <span class="loc-icon">🗺️</span>
      <div style="flex:1; min-width:0">
        <span class="loc-level">${escapeHtml(level)}</span>
        <span class="loc-wing">${escapeHtml(wing)}</span>
        ${walk ? `<span class="loc-walk">🚶 ${escapeHtml(walk)}</span>` : ''}
      </div>
    </div>
  `;
}

/** Concurrent sessions for a given (day, HH:MM start).
 *  Matches by session.day === dayName AND session.timeStart overlaps the block.
 */
function findConcurrentSessions(dayName, blockTime) {
  const [startHM] = blockTime.split('-');
  const startMin = hmToMin(startHM);
  const endMin   = blockTime.includes('-') ? hmToMin(blockTime.split('-')[1]) : (startMin + 60);
  const out = [];
  for (const sid in AppData.sessions) {
    const s = AppData.sessions[sid];
    if (s.day !== dayName) continue;
    const sStart = hmToMin(s.timeStart);
    const sEnd   = hmToMin(s.timeEnd || s.timeStart);
    // Any overlap counts (concurrent = any temporal overlap)
    if (sEnd > startMin && sStart < endMin) {
      out.push(s);
    }
  }
  // Stable sort: interest sessions first, then by room code, then by timeStart.
  out.sort((a, b) => {
    const ai = sessionHitsInterests(a) ? 0 : 1;
    const bi = sessionHitsInterests(b) ? 0 : 1;
    if (ai !== bi) return ai - bi;
    const tr = (a.timeStart || '').localeCompare(b.timeStart || '');
    if (tr !== 0) return tr;
    return (a.room || '').localeCompare(b.room || '');
  });
  return out;
}

function hmToMin(hm) {
  if (!hm) return 0;
  const m = hm.match(/(\d{1,2}):(\d{2})/);
  if (!m) return 0;
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
}

/** Render a clickable speaker chip — auto-looks-up tier from AppData.speakers
 *  when the ref string doesn't already carry a (S)/(A)/(B) suffix.
 *  Used by edit-view backup options AND concurrent-session items so chips
 *  consistently show colour for any researched speaker.
 */
function renderSpeakerChipAutoTier(ref) {
  const parsed = parseSpeakerRef(ref);
  let tier = parsed.tier;
  if (!tier) {
    const sp = AppData.speakers[parsed.name];
    if (sp && sp.tier) tier = sp.tier;
  }
  const researched = speakerIsResearched(parsed.name);
  return `<button class="chip speaker-chip${researched ? ' researched' : ''}" type="button"
    onclick="event.preventDefault(); event.stopPropagation(); navigateTo('#/speaker/${encodeURIComponent(parsed.name)}')">
    <span class="chip-name">${escapeHtml(parsed.name)}</span>
    ${tier ? `<span class="chip-tier ${tier}">${tier}</span>` : ''}
  </button>`;
}

// -----------------------------------------------------------
// Data loading
// -----------------------------------------------------------

async function loadData() {
  const base = './data/';
  const files = ['meta.json', 'schedule.json', 'sessions.json', 'speakers.json', 'trials.json'];
  // Cache-bust JSON so users pick up data changes without needing a SW bump.
  // DATA_VERSION should be incremented whenever app/data/*.json changes.
  const DATA_VERSION = 'v23b';
  const loaded = await Promise.all(files.map(f =>
    fetch(base + f + '?v=' + DATA_VERSION).then(r => {
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

  // Remember the last schedule day so we can restore it when user hits back
  if (view === 'schedule' && parts[1]) {
    UIState.previousScheduleDay = parts[1];
  }

  if (view === 'schedule') {
    if (parts[1]) UIState.currentDay = parts[1];
    switchView('schedule');
  } else if (view === 'session' && parts[1]) {
    UIState.detailId = decodeURIComponent(parts[1]);
    switchView('session');
  } else if (view === 'speaker' && parts[1]) {
    UIState.detailId = decodeURIComponent(parts[1]);
    switchView('speaker');
  } else if (view === 'trial' && parts[1]) {
    UIState.detailId = decodeURIComponent(parts[1]);
    switchView('trial');
  } else if (view === 'edit' && parts[1]) {
    UIState.detailId = decodeURIComponent(parts[1]);  // blockKey like "Tuesday-16:30"
    switchView('edit');
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
  // Update nav state — detail pages don't light up a nav button
  const topLevelViews = { schedule: true, speakers: true, trials: true, about: true, search: true };
  $$('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', topLevelViews[view] && btn.dataset.view === view);
  });
  // Day tabs show only on the main schedule view
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
  // Scroll to top on any view change
  main.scrollTop = 0;
  window.scrollTo(0, 0);

  switch (UIState.currentView) {
    case 'schedule':  renderSchedule(main); break;
    case 'speakers':  renderSpeakersView(main); break;
    case 'trials':    renderTrialsView(main); break;
    case 'about':     renderAboutView(main); break;
    case 'search':    renderSearchView(main); break;
    case 'session':   renderSessionDetail(main, UIState.detailId); break;
    case 'speaker':   renderSpeakerDetail(main, UIState.detailId); break;
    case 'trial':     renderTrialDetail(main, UIState.detailId); break;
    case 'edit':      renderEditView(main, UIState.detailId); break;
  }
}

/**
 * A back button header used by all detail/subpage views.
 * Returns the page to the schedule, restoring the previously viewed day.
 */
function renderBackHeader(title, subtitle) {
  const header = document.createElement('header');
  header.className = 'detail-header';
  header.innerHTML = `
    <button class="back-btn" aria-label="返回">
      <span>←</span>
      <span>返回排程</span>
    </button>
    <div class="detail-header-title">
      <h1>${escapeHtml(title || '')}</h1>
      ${subtitle ? `<p>${escapeHtml(subtitle)}</p>` : ''}
    </div>
  `;
  header.querySelector('.back-btn').onclick = () => {
    navigateTo(`#/schedule/${encodeURIComponent(UIState.previousScheduleDay || 'Tuesday')}`);
  };
  return header;
}

function updateTopBar() {
  const sub = $('#topbar-subtitle');
  switch (UIState.currentView) {
    case 'schedule': {
      const day = AppData.schedule.days.find(d => d.day === UIState.currentDay);
      sub.textContent = day ? day.theme.split('—')[0].trim() : '';
      break;
    }
    case 'speakers': sub.textContent = `${Object.keys(AppData.speakers).length} researched speakers`; break;
    case 'trials':   sub.textContent = `${Object.keys(AppData.trials).length} trials`; break;
    case 'session':  sub.textContent = '場次詳情'; break;
    case 'speaker':  sub.textContent = '講者卡片'; break;
    case 'trial':    sub.textContent = '試驗詳情'; break;
    case 'edit':     sub.textContent = '編輯排程'; break;
    default:         sub.textContent = '';
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

  // Category + topic pills — pulled from the backing enriched session
  const backingSession = sessionFor(pick);
  if (backingSession) {
    const pillRow = document.createElement('div');
    pillRow.className = 'pill-row dense';
    pillRow.innerHTML = [
      renderCategoryPillsHtml(backingSession.trackCategories),
      renderTopicPillsHtml(backingSession.topics, { limit: 5 }),
      backingSession.room ? `<span class="format-pill">🏛️ ${escapeHtml(backingSession.room.replace(/^ROOM\s*/,''))}</span>` : '',
    ].filter(Boolean).join('');
    if (pillRow.innerHTML) article.querySelector('.block-title').after(pillRow);
  }

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
    navigateTo(`#/edit/${encodeURIComponent(blockKey(dayName, block.time))}`);
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

// -----------------------------------------------------------
// Session detail page
// -----------------------------------------------------------

function renderSessionDetail(main, sessionId) {
  const s = AppData.sessions[sessionId];
  if (!s) {
    main.innerHTML = '';
    main.appendChild(renderBackHeader('場次資料不存在', sessionId));
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

  // Back header (always present, always clickable — it's rendered into #main)
  main.innerHTML = '';
  main.appendChild(renderBackHeader(s.title, s.subtitle));

  const body = document.createElement('div');
  body.className = 'detail-body';
  body.innerHTML = `
    <div class="sheet-meta">
      <span>📅 ${escapeHtml(s.day)} ${escapeHtml(s.date)}</span>
      <span>⏰ ${escapeHtml(s.timeStart)}-${escapeHtml(s.timeEnd)}</span>
      <span>🏛️ ${escapeHtml(s.room)}</span>
      ${s.formatLabel ? `<span>🎬 ${escapeHtml(s.formatLabel)}</span>` : ''}
    </div>

    ${(s.trackCategories && s.trackCategories.length) || (s.topics && s.topics.length) ? `
      <div class="pill-row" style="margin-bottom: 12px">
        ${renderCategoryPillsHtml(s.trackCategories)}
        ${renderTopicPillsHtml(s.topics, { limit: 10 })}
      </div>
    ` : ''}

    ${renderLocationBoxHtml(s.location)}

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

    ${associatedKey ? `
      <div class="sheet-actions" style="margin-top: 24px">
        <button class="btn-primary" onclick="navigateTo('#/edit/${encodeURIComponent(associatedKey)}')">✏️ 編輯排程</button>
      </div>
    ` : ''}
  `;
  main.appendChild(body);
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
  // Auto-lookup tier from AppData.speakers so every chip shows S/A/B colour
  // when the speaker has been researched (same behaviour as edit view).
  const parsed = parseSpeakerRef(name);
  let tier = parsed.tier;
  if (!tier) {
    const sp = AppData.speakers[parsed.name];
    if (sp && sp.tier) tier = sp.tier;
  }
  const researched = speakerIsResearched(parsed.name);
  return `
    <button class="chip speaker-chip${researched ? ' researched' : ''}"
            onclick="event.stopPropagation(); navigateTo('#/speaker/${encodeURIComponent(parsed.name)}')">
      <span class="chip-name">${escapeHtml(parsed.name)}</span>
      ${tier ? `<span class="chip-tier ${tier}">${tier}</span>` : ''}
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
// Speaker detail page
// -----------------------------------------------------------

function renderSpeakerDetail(main, name) {
  const sp = AppData.speakers[name];
  main.innerHTML = '';

  // Unresearched: show minimal card based on session appearances
  if (!sp) {
    const relatedSessions = findSessionsForSpeaker(name);
    main.appendChild(renderBackHeader(name, '未研究過 — 只顯示議程出現紀錄'));

    const body = document.createElement('div');
    body.className = 'detail-body';
    body.innerHTML = `
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
    `;
    main.appendChild(body);
    return;
  }

  // Full speaker card (researched)
  const relatedSessions = (sp.sessionIds || [])
    .map(id => AppData.sessions[id])
    .filter(Boolean);

  main.appendChild(renderBackHeader(sp.name, `${sp.fullName || ''} · ${sp.institution || ''}`));

  const body = document.createElement('div');
  body.className = 'detail-body speaker-card';
  body.innerHTML = `
    <div class="speaker-tier-large ${sp.tier}" style="margin-bottom: 12px">Tier ${sp.tier}</div>

    ${sp.oneLiner ? `<div class="speaker-oneliner">${escapeHtml(sp.oneLiner)}</div>` : ''}

    ${sp.extendedBio ? `
      <div class="sheet-section">
        <h3>📖 深度介紹</h3>
        <p style="font-size: 14px; line-height: 1.65; margin: 0">${escapeHtml(sp.extendedBio)}</p>
      </div>
    ` : ''}

    ${sp.signatureWork ? `
      <div class="sheet-section signature-box">
        <h3>⭐ 代表作</h3>
        <p style="font-size: 14px; line-height: 1.55; margin: 0; font-weight: 500">${escapeHtml(sp.signatureWork)}</p>
      </div>
    ` : ''}

    ${sp.recentActivity ? `
      <div class="sheet-section">
        <h3>📡 2024-2026 動態</h3>
        <p style="font-size: 14px; line-height: 1.6; margin: 0">${escapeHtml(sp.recentActivity)}</p>
      </div>
    ` : ''}

    ${sp.conversationStarter ? `
      <div class="sheet-section convo-box">
        <h3>💬 碰面可以聊</h3>
        <p style="font-size: 14px; line-height: 1.6; margin: 0; font-style: italic">${escapeHtml(sp.conversationStarter)}</p>
      </div>
    ` : ''}

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

    ${sp.recentPapers && sp.recentPapers.length ? `
      <div class="sheet-section">
        <h3>📚 近期重要著作</h3>
        <ul class="paper-list">
          ${sp.recentPapers.map(p => `
            <li>
              ${p.pmid
                ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(p.pmid)}/" target="_blank" rel="noopener" class="paper-title">${escapeHtml(p.title || '')}</a>`
                : `<span class="paper-title">${escapeHtml(p.title || '')}</span>`}
              ${p.year ? `<span class="paper-year">(${escapeHtml(String(p.year))})</span>` : ''}
              ${p.relevance ? `<div class="paper-relevance">${escapeHtml(p.relevance)}</div>` : ''}
            </li>
          `).join('')}
        </ul>
      </div>
    ` : (sp.pmids && sp.pmids.length ? `
      <div class="sheet-section">
        <h3>📚 Key PMIDs</h3>
        <div class="pmid-list">
          ${sp.pmids.map(p => `
            <a href="https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(p)}/" target="_blank" rel="noopener"
               style="display:inline-block; padding: 4px 10px; margin: 0 4px 4px 0; background: var(--bg-subtle); border-radius: 4px; font-size: 12px; color: var(--accent)">${escapeHtml(p)}</a>
          `).join('')}
        </div>
      </div>
    ` : '')}

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
  `;
  main.appendChild(body);
}

// -----------------------------------------------------------
// Trial detail page
// -----------------------------------------------------------

function renderTrialDetail(main, trialId) {
  const t = AppData.trials[trialId];
  main.innerHTML = '';

  if (!t) {
    main.appendChild(renderBackHeader('試驗資料不存在', trialId));
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

  main.appendChild(renderBackHeader(t.trialName || t.trialId, t.domain));

  const body = document.createElement('div');
  body.className = 'detail-body';
  body.innerHTML = `
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
  main.appendChild(body);
}

// -----------------------------------------------------------
// Edit view (backup swap + notes + tags)
// -----------------------------------------------------------

function renderEditView(main, key) {
  // key = "Day-HH:MM"
  const [dayName, time] = key.split('-', 2);

  const day = AppData.schedule.days.find(d => d.day === dayName);
  if (!day) {
    main.innerHTML = '';
    main.appendChild(renderBackHeader('排程不存在', key));
    return;
  }
  const block = day.blocks.find(b => b.time.startsWith(time));
  if (!block) {
    main.innerHTML = '';
    main.appendChild(renderBackHeader('時段不存在', key));
    return;
  }

  const resolved = resolveBlockPick(dayName, block);
  const currentIsMain = !resolved.isBackup && !resolved.isCustom && !resolved.skipped;

  const options = [
    { type: 'main', idx: null, option: block.pick },
    ...(block.backups || []).map((b, i) => ({ type: 'backup', idx: i, option: b }))
  ];

  main.innerHTML = '';
  main.appendChild(renderBackHeader('編輯排程', `${dayName} ${block.time}`));

  // Pre-compute concurrent sessions (everything happening during this block)
  const curatedIds = new Set();
  if (block.pick && block.pick.sessionId) curatedIds.add(block.pick.sessionId);
  (block.backups || []).forEach(b => { if (b.sessionId) curatedIds.add(b.sessionId); });
  const concurrent = findConcurrentSessions(dayName, block.time)
    .filter(s => !curatedIds.has(s.id));
  const interestConcurrent = concurrent.filter(sessionHitsInterests);

  // Current custom override (if any) — even if not in curated list
  const ov = UserState.overrides[key] || {};
  const customSid = ov.customSessionId && !curatedIds.has(ov.customSessionId) ? ov.customSessionId : null;

  const body = document.createElement('div');
  body.className = 'detail-body';
  body.innerHTML = `
    <div class="sheet-section">
      <h3>🎯 選擇場次（策展）</h3>
      ${options.map(o => {
        const bs = sessionFor(o.option);
        const pillHtml = bs ? `
          <div class="pill-row dense" style="margin-top:6px">
            ${renderCategoryPillsHtml(bs.trackCategories)}
            ${renderTopicPillsHtml(bs.topics, { limit: 5 })}
          </div>` : '';
        const locHtml = bs && bs.location ? `<div class="option-note" style="margin-top:4px">🗺️ ${escapeHtml(bs.location.levelLabel)} · ${escapeHtml(bs.location.wing)}</div>` : '';
        // Clickable speaker chips with auto tier lookup
        const speakerChipsHtml = o.option.keyNames && o.option.keyNames.length ? `
          <div class="option-speakers" style="display:flex; flex-wrap:wrap; gap:4px; margin-top:6px">
            ${o.option.keyNames.map(renderSpeakerChipAutoTier).join('')}
          </div>
        ` : '';
        // "查看完整詳情" button on every option
        const detailLinkHtml = o.option.sessionId ? `
          <button type="button" class="option-detail-link"
            onclick="event.preventDefault(); event.stopPropagation(); navigateTo('#/session/${encodeURIComponent(o.option.sessionId)}')">
            🔍 完整議程・全部講者 →
          </button>
        ` : '';
        return `
        <label class="backup-option ${
          (o.type === 'main' && currentIsMain) ||
          (o.type === 'backup' && resolved.backupIdx === o.idx)
            ? 'active' : ''
        }">
          <input type="radio" name="pick" value="${o.type}:${o.idx === null ? '' : o.idx}">
          <span class="option-label">${o.type === 'main' ? '★ 主選' : `備案 ${o.idx + 1}`}</span>
          <div class="option-title">${escapeHtml(o.option.title)}</div>
          ${speakerChipsHtml}
          ${o.option.note ? `<div class="option-note">${escapeHtml(o.option.note)}</div>` : ''}
          ${locHtml}
          ${pillHtml}
          ${detailLinkHtml}
        </label>
      `;
      }).join('')}

      ${customSid ? (() => {
        const cs = AppData.sessions[customSid];
        if (!cs) return '';
        return `
          <label class="backup-option active">
            <input type="radio" name="pick" value="custom:${escapeHtml(customSid)}" checked>
            <span class="option-label" style="color: var(--accent)">自訂</span>
            <div class="option-title">${escapeHtml(cs.title)}</div>
            <div class="option-note">🗺️ ${escapeHtml(cs.location ? cs.location.levelLabel + ' · ' + cs.location.wing : cs.room)}</div>
          </label>
        `;
      })() : ''}

      <label class="backup-option" style="background: var(--bg-subtle)">
        <input type="radio" name="pick" value="skip" ${resolved.skipped ? 'checked' : ''}>
        <span class="option-label" style="color: var(--warning)">❌ 跳過</span>
        <div class="option-note">標記為不參加這個時段（休息或逛展場）</div>
      </label>
    </div>

    ${concurrent.length ? `
    <div class="sheet-section">
      <button class="reveal-concurrent" id="reveal-concurrent" type="button" aria-expanded="false">
        <span>🔍 同時段還有 <span class="reveal-count">${concurrent.length}</span> 場${interestConcurrent.length ? ` <span style="color:#d97706; font-weight:700">（★ ${interestConcurrent.length} 場切中你興趣）</span>` : ''}</span>
        <span class="reveal-arrow">▸</span>
      </button>
      <div id="concurrent-panel" style="display:none; margin-top:10px">
        <div class="concurrent-summary">
          <strong>為什麼看這個？</strong>策展主選/備案只是 Dr. Chang 的推薦。這裡列出同時段<b>所有其他場次</b>，幫你核對是否錯過有興趣的題目。★ 代表命中你關注的 <b>ACS/STEMI、併發症、脆弱斑塊</b>。
        </div>
        <div class="concurrent-filter" id="concurrent-filter">
          <span class="filter-chip active" data-filter="all">全部 ${concurrent.length}</span>
          ${interestConcurrent.length ? `<span class="filter-chip interest" data-filter="interest">★ 興趣 ${interestConcurrent.length}</span>` : ''}
          ${buildConcurrentTopicFilters(concurrent)}
        </div>
        <div class="concurrent-list" id="concurrent-list"></div>
      </div>
    </div>
    ` : ''}

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
      <button class="btn-secondary" id="cancel-edit">取消</button>
      <button class="btn-primary" id="save-edit">儲存</button>
    </div>
  `;
  main.appendChild(body);

  // Wire tag chips
  $$('.tag-chip', body).forEach(chip => {
    chip.onclick = () => chip.classList.toggle('active');
  });

  // Reveal concurrent panel + render list
  const revealBtn = $('#reveal-concurrent', body);
  const panel = $('#concurrent-panel', body);
  const listEl = $('#concurrent-list', body);
  let currentFilter = 'all';

  const renderConcurrentList = () => {
    if (!listEl) return;
    let items = concurrent;
    if (currentFilter === 'interest') {
      items = items.filter(sessionHitsInterests);
    } else if (currentFilter.startsWith('topic:')) {
      const topic = currentFilter.split(':')[1];
      items = items.filter(s => (s.topics || []).includes(topic));
    } else if (currentFilter.startsWith('cat:')) {
      const cat = currentFilter.split(':')[1];
      items = items.filter(s => (s.trackCategories || []).includes(cat));
    }
    if (!items.length) {
      listEl.innerHTML = '<div class="empty-state" style="padding:16px">此篩選下沒有場次</div>';
      return;
    }
    listEl.innerHTML = items.map(s => {
      const star = sessionHitsInterests(s) ? '<span class="ci-star">⭐</span>' : '';
      const starClass = sessionHitsInterests(s) ? 'starred' : '';
      const selected = ov.customSessionId === s.id ? 'selected' : '';
      const locShort = s.location ? `${s.location.levelLabel} · ${s.location.wing}` : s.room;
      // Collect up to 4 speaker names (handle flat array OR grouped object)
      const speakerNames = Array.isArray(s.speakers)
        ? s.speakers.map(sp => (sp && sp.name) || sp).filter(Boolean)
        : (s.speakers && typeof s.speakers === 'object'
            ? Object.values(s.speakers).flat().filter(Boolean)
            : []);
      const speakerChipsHtml = speakerNames.slice(0, 4).map(renderSpeakerChipAutoTier).join('');
      const extraCount = speakerNames.length - 4;
      return `
        <div class="concurrent-item ${starClass} ${selected}" data-sid="${escapeHtml(s.id)}">
          ${star}
          <div class="ci-top">
            <div class="ci-title">${escapeHtml(s.title || '(無標題)')}</div>
            <div class="ci-room">${escapeHtml(s.timeStart || '')}<br>${escapeHtml((s.room || '').replace(/^ROOM\s*/,'R.'))}</div>
          </div>
          <div class="pill-row dense">
            ${renderTopicPillsHtml(s.topics, { limit: 4 })}
            <span class="format-pill">${escapeHtml(s.formatLabel || s.type || '')}</span>
          </div>
          ${speakerChipsHtml ? `<div class="ci-speakers" style="display:flex; flex-wrap:wrap; gap:3px; margin-top:4px">${speakerChipsHtml}${extraCount > 0 ? `<span class="chip" style="font-size:10px; padding:2px 6px; color:var(--text-muted)">+${extraCount}</span>` : ''}</div>` : ''}
          <div style="font-size:11px; color: var(--text-muted); margin-top:4px">🗺️ ${escapeHtml(locShort)}</div>
          <div style="display:flex; gap:6px; margin-top:6px">
            <span class="ci-select-btn" data-action="select">${selected ? '✓ 已選此場' : '選此場'}</span>
            <span class="ci-select-btn" data-action="open" style="background: var(--bg-subtle); color: var(--text-muted)">查看詳情 →</span>
          </div>
        </div>
      `;
    }).join('');

    // Wire clicks
    $$('.concurrent-item', listEl).forEach(el => {
      const sid = el.dataset.sid;
      $$('[data-action]', el).forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          if (btn.dataset.action === 'select') {
            // Select as custom override for this block
            UserState.overrides[key] = { customSessionId: sid };
            UserState.save();
            toast('已切換至此場次（自訂）', 'success');
            // Re-render edit view to reflect
            renderEditView(main, key);
          } else if (btn.dataset.action === 'open') {
            navigateTo(`#/session/${encodeURIComponent(sid)}`);
          }
        };
      });
      // Clicking the body also opens detail
      el.onclick = () => navigateTo(`#/session/${encodeURIComponent(sid)}`);
    });
  };

  if (revealBtn) {
    revealBtn.onclick = () => {
      const open = panel.style.display !== 'none';
      panel.style.display = open ? 'none' : 'block';
      revealBtn.classList.toggle('open', !open);
      revealBtn.setAttribute('aria-expanded', String(!open));
      if (!open) renderConcurrentList();
    };

    // Filter chips
    $$('#concurrent-filter .filter-chip', body).forEach(chip => {
      chip.onclick = () => {
        $$('#concurrent-filter .filter-chip', body).forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        currentFilter = chip.dataset.filter;
        renderConcurrentList();
      };
    });
  }

  $('#save-edit', body).onclick = () => {
    saveEdit(dayName, block);
  };
  $('#cancel-edit', body).onclick = () => {
    navigateTo(`#/schedule/${encodeURIComponent(UIState.previousScheduleDay || dayName)}`);
  };

  // Set initial radio selection based on current state
  const radios = $$('input[name="pick"]', body);
  if (resolved.skipped) {
    radios.forEach(r => { if (r.value === 'skip') r.checked = true; });
  } else if (customSid) {
    // custom radio already checked via attribute
  } else if (resolved.isBackup) {
    radios.forEach(r => { if (r.value === `backup:${resolved.backupIdx}`) r.checked = true; });
  } else {
    radios.forEach(r => { if (r.value === 'main:') r.checked = true; });
  }
}

/** Build topic/category filter chips from the pool of concurrent sessions. */
function buildConcurrentTopicFilters(sessions) {
  // Count topics + categories present
  const topicCount = {}, catCount = {};
  sessions.forEach(s => {
    (s.topics || []).forEach(t => { topicCount[t] = (topicCount[t] || 0) + 1; });
    (s.trackCategories || []).forEach(c => { catCount[c] = (catCount[c] || 0) + 1; });
  });
  // Top 6 topics
  const topTopics = Object.entries(topicCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
  const cats = Object.entries(catCount).sort((a, b) => b[1] - a[1]);

  const catHtml = cats.map(([c, n]) =>
    `<span class="filter-chip" data-filter="cat:${escapeHtml(c)}">${escapeHtml(CATEGORY_LABELS[c] || c)} ${n}</span>`
  ).join('');
  const topicHtml = topTopics.map(([t, n]) =>
    `<span class="filter-chip" data-filter="topic:${escapeHtml(t)}">${escapeHtml(TOPIC_LABELS[t] || t)} ${n}</span>`
  ).join('');
  return catHtml + topicHtml;
}

function saveEdit(dayName, block) {
  const key = blockKey(dayName, block.time);
  const main = $('#main');
  const picked = $('input[name="pick"]:checked', main);

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
  const note = $('#note-editor', main).value.trim();
  if (note) UserState.notes[key] = note;
  else delete UserState.notes[key];

  // Save tags
  const activeTags = $$('.tag-chip.active', main).map(c => c.dataset.tag);
  if (activeTags.length) UserState.tags[key] = activeTags;
  else delete UserState.tags[key];

  UserState.save();
  toast('已儲存', 'success');
  // Navigate back to schedule
  navigateTo(`#/schedule/${encodeURIComponent(dayName)}`);
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

  // Flatten speaker names — schema varies: array of {name, role} OR
  // object {role: [names]} OR null. Throw-safe.
  const speakerNamesOf = (s) => {
    const sp = s.speakers;
    if (!sp) return '';
    if (Array.isArray(sp)) return sp.map(x => (x && x.name) || x || '').join(' ');
    if (typeof sp === 'object') return Object.values(sp).flat().filter(Boolean).join(' ');
    return '';
  };

  const sessions = Object.values(AppData.sessions);
  const matches = sessions.filter(s => {
    try {
      const blob = [
        s.title, s.subtitle, s.sponsor, s.room, s.type, s.formatLabel,
        (s.topics || []).join(' '),
        (s.trackCategories || []).join(' '),
        speakerNamesOf(s),
        (s.agenda || []).map(a => (a.title || a.item || '') + ' ' + (a.speaker || '')).join(' ')
      ].join(' ').toLowerCase();
      return blob.includes(q);
    } catch (e) {
      return false;
    }
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

  // Escape = back to schedule (when on any detail view)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const detailViews = { session: true, speaker: true, trial: true, edit: true };
      if (detailViews[UIState.currentView]) {
        navigateTo(`#/schedule/${encodeURIComponent(UIState.previousScheduleDay || 'Tuesday')}`);
      }
    }
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
window.toast = toast;
window.exportUserData = exportUserData;
window.importUserData = importUserData;
window.resetUserData = resetUserData;
window.hardRefresh = hardRefresh;

init();
