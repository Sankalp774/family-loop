const FALLBACK_ASK = [
  { key: "new_app", label: "New apps" },
  { key: "new_contact", label: "New in-app friends" },
  { key: "social", label: "Social apps" },
  { key: "in_app_purchase", label: "Anything that costs money" },
  { key: "extra_time_over_cap", label: "Extra time over the cap" },
];
const FALLBACK_HARD = [
  { key: "gambling", label: "Gambling" },
  { key: "dating", label: "Dating apps" },
  { key: "unsupervised_late_night_youtube", label: "YouTube late at night without you" },
];
const DEFAULT_NOTE =
  "Sports-phone preset: Maps and Phone extra time during practice is allowed. YouTube extra time waits until after homework hours (17:00).";
const DAY_CHIPS = [
  { key: "0", label: "Mon" },
  { key: "1", label: "Tue" },
  { key: "2", label: "Wed" },
  { key: "3", label: "Thu" },
  { key: "4", label: "Fri" },
  { key: "5", label: "Sat" },
  { key: "6", label: "Sun" },
];

const state = {
  user: null,
  data: null,
  model: "",
  selectedDay: null,
  calView: "month",
  calHidden: new Set(),
  editingEvent: null,
  parentPane: "home",
  simSteps: null,
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  if (data.agent && data.agent.active_agents) {
    wakePets(data.agent.active_agents, data.agent.event);
  }
  return data;
}

const PETS = [
  { id: "family_desk", name: "Desk", color: "#9a3b38" },
  { id: "setup_coach", name: "Coach", color: "#1f1d1b" },
  { id: "request_triage", name: "Triage", color: "#5c5346" },
  { id: "checkin_runner", name: "Check-in", color: "#3d6b52" },
  { id: "digest_writer", name: "Digest", color: "#3f4a44" },
  { id: "override_clerk", name: "Clerk", color: "#6f6b66" },
];

function petSVG(color) {
  const dark = "#1f1d1b";
  return `<svg viewBox="0 0 64 72" class="pet-svg" aria-hidden="true">
    <ellipse cx="32" cy="42" rx="20" ry="22" fill="${color}"/>
    <ellipse cx="32" cy="26" rx="18" ry="16" fill="${color}"/>
    <path d="M16 40 h32 v18 a8 8 0 0 1 -8 8 H24 a8 8 0 0 1 -8 -8 z" fill="${dark}" opacity="0.22"/>
    <rect x="15" y="21" width="34" height="5" rx="2.5" fill="#d9d4cc"/>
    <circle cx="24" cy="28" r="8" fill="#f7f4ef"/>
    <circle cx="40" cy="28" r="8" fill="#f7f4ef"/>
    <circle cx="24" cy="28" r="3.4" fill="${dark}"/>
    <circle cx="40" cy="28" r="3.4" fill="${dark}"/>
    <rect x="27" y="47" width="10" height="7" rx="2" fill="#f7f4ef" opacity="0.7"/>
  </svg>`;
}

function mountPets() {
  /* Pets only pop when an agent runs — nothing stays on the bar. */
}

let petQueue = Promise.resolve();

function showOnePet(spec, line) {
  const host = $("pet-pop");
  if (!host || !spec) return Promise.resolve();
  host.hidden = false;
  host.innerHTML = `<div class="pet-card" style="border-top:3px solid ${spec.color}">
    ${line ? `<p class="pet-speech">${line}</p>` : ""}
    ${petSVG(spec.color)}
    <span class="pet-name" style="color:${spec.color}">${spec.name}</span>
  </div>`;
  return new Promise((resolve) => {
    setTimeout(() => {
      host.hidden = true;
      host.innerHTML = "";
      resolve();
    }, 2200);
  });
}

function wakePets(ids, eventName) {
  const order = [];
  (ids || []).forEach((id) => {
    const spec = PETS.find((p) => p.id === id);
    if (spec && !order.some((p) => p.id === spec.id)) order.push(spec);
  });
  if (!order.length) return;
  const lineFor = (spec) => {
    if (spec.id === "family_desk") return "Desk is routing…";
    if (spec.id === "setup_coach") return "Coach is writing the policy.";
    if (spec.id === "request_triage") return "Triage is reading policy + history.";
    if (spec.id === "checkin_runner") return "Check-in is comparing the snapshot.";
    if (spec.id === "digest_writer") return "Digest is building Sunday.";
    if (spec.id === "override_clerk") return "Clerk is logging the decision.";
    return eventName ? `${spec.name} · ${eventName}` : spec.name;
  };
  petQueue = petQueue.then(async () => {
    for (const spec of order) {
      await showOnePet(spec, lineFor(spec));
    }
  });
}

async function refreshModelSwitch() {
  try {
    const info = await api("/api/model");
    document.querySelectorAll("#model-switch [data-mode]").forEach((btn) => {
      btn.classList.toggle("on", btn.dataset.mode === info.mode);
    });
    state.model = info.label;
    if ($("model-label")) $("model-label").textContent = info.label;
  } catch (_) {
    /* stay on scripted */
  }
}

function toast(msg) {
  const el = $("toast");
  el.hidden = false;
  el.textContent = msg;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { el.hidden = true; }, 3200);
}

function chipTone(label, key) {
  const t = `${label || ""} ${key || ""}`.toLowerCase();
  if (/(social|whatsapp|youtube|instagram|discord|reddit|tiktok|snap|dating|telegram|friend|contact|facebook|twitter)/.test(t)) return "social";
  if (/(khan|classroom|school|homework|educat|academy|learn|class)/.test(t)) return "edu";
  if (/(game|roblox|minecraft|fortnite|xbox|steam|play)/.test(t)) return "game";
  if (/(money|purchase|gambling|robux|cost|buy|gift|₹)/.test(t)) return "misc";
  if (/(map|phone|extra|new.app|cap|call|new_app)/.test(t)) return "other";
  return "misc";
}

function chips(container, options, selected, opts = {}) {
  container.innerHTML = "";
  container._options = options;
  container._tone = opts.tone !== false;
  options.forEach((opt) => {
    const key = String(opt.key || opt);
    const label = opt.label || String(key).replaceAll("_", " ");
    const hint = opt.hint || "";
    const btn = document.createElement("button");
    btn.type = "button";
    const tone = container._tone ? chipTone(label, key) : "";
    btn.className = `chip ${tone ? "tone-" + tone : ""}` + (selected.has(key) ? " on" : "");
    btn.textContent = label;
    if (hint) btn.title = hint;
    btn.addEventListener("click", () => {
      if (selected.has(key)) selected.delete(key);
      else selected.add(key);
      btn.classList.toggle("on");
    });
    container.appendChild(btn);
  });
  container._selected = selected;
}

function addCustomChip(container, label) {
  const text = (label || "").trim();
  if (!text) return;
  const key = text.toLowerCase().replace(/\s+/g, "_");
  const options = container._options || [];
  if (!options.some((opt) => String(opt.key || opt) === key)) {
    options.push({ key, label: text });
  }
  const selected = container._selected || new Set();
  selected.add(key);
  chips(container, options, selected, { tone: container._tone !== false });
}

function removableChips(container, items) {
  container.innerHTML = "";
  container._items = items;
  items.forEach((name, index) => {
    const btn = document.createElement("button");
    btn.type = "button";
    const tone = chipTone(name, name);
    btn.className = `chip on tone-${tone}`;
    btn.innerHTML = `${escapeHtml(name)}<span class="x">×</span>`;
    btn.addEventListener("click", () => {
      items.splice(index, 1);
      removableChips(container, items);
    });
    container.appendChild(btn);
  });
}

function show(view) {
  $("doors").hidden = view !== "doors";
  $("parent").hidden = view !== "parent";
  $("child").hidden = view !== "child";
  $("top-meta").hidden = view === "doors";
}

function visibleItems(items) {
  return (items || []).filter((item) => !state.calHidden.has(item.calendar));
}

function eventChip(item) {
  const label = `${item.all_day || !item.start_time ? "" : item.start_time + " "}${item.title}`;
  return `<button type="button" class="chip-ev ${item.readonly ? "readonly" : ""}" data-event-id="${item.id || ""}" data-readonly="${item.readonly ? "1" : "0"}" style="background:${item.color || "#0f766e"}">${item.important ? "★ " : ""}${escapeHtml(label)}</button>`;
}

function renderCalendar(host, calendar, role) {
  if (!host || !calendar) return;
  const selected = state.selectedDay || calendar.today;
  const cells = calendar.weeks.flat();
  const picked = cells.find((d) => d.date === selected && d.in_month)
    || cells.find((d) => d.date === calendar.today)
    || cells.find((d) => d.in_month);
  const todos = picked?.todos || [];
  const dayItems = visibleItems(picked?.items || []);
  const calendars = calendar.calendars || [];
  host.innerHTML = `
    <div class="cal-head">
      <div>
        <h2>Family calendar</h2>
        <p class="hint">${calendar.title} · ${calendar.event_count || 0} family events this month. Parent and child both edit this calendar.</p>
      </div>
      <div class="cal-nav">
        <button type="button" data-cal="prev">←</button>
        <button type="button" data-cal="today">Today</button>
        <button type="button" data-cal="next">→</button>
        <button type="button" class="btn-primary" data-cal="create">+ Event</button>
        ${role === "parent" ? '<button type="button" class="btn-sky" data-cal="live">Live date</button>' : ""}
      </div>
    </div>
    <div class="cal-toolbar">
      <div class="cal-views">
        ${["month", "week", "agenda"].map((v) => `<button type="button" data-view="${v}" class="${state.calView === v ? "on" : ""}">${v[0].toUpperCase() + v.slice(1)}</button>`).join("")}
      </div>
      <div class="cal-filters">
        ${calendars.map((c) => `<button type="button" data-filter="${c.key}" class="${state.calHidden.has(c.key) ? "off" : ""}" style="border-color:${c.color};${state.calHidden.has(c.key) ? "" : `background:${c.color};color:#fff`}">${c.label}</button>`).join("")}
      </div>
    </div>
    <div class="cal-legend">
      ${(calendar.legend || []).map((item) => `<span class="leg ${item.tag}">${item.label}</span>`).join("")}
    </div>
    ${state.calView === "week" ? renderWeek(calendar, selected) : ""}
    ${state.calView === "agenda" ? renderAgenda(calendar) : ""}
    ${state.calView === "month" ? `
    <div class="cal-grid">
      ${["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => `<div class="cal-dow">${d}</div>`).join("")}
      ${cells.map((d) => {
        const tags = (d.tags || []).join(" ");
        const chips = visibleItems(d.items).slice(0, 3);
        const more = visibleItems(d.items).length - chips.length;
        return `<div class="cal-day ${tags} ${d.in_month ? "" : "out"} ${d.date === selected ? "picked" : ""}" data-date="${d.date}">
          ${d.past ? '<span class="cross" aria-hidden="true"></span>' : ""}
          <span class="num">${d.day}</span>
          <div class="cal-chips">${chips.map(eventChip).join("")}${more > 0 ? `<span class="chip-more">+${more} more</span>` : ""}</div>
        </div>`;
      }).join("")}
    </div>` : ""}
    <div class="cal-detail">
      <h3>${picked ? picked.date : ""} · ${picked ? picked.weekday_name : ""}${picked?.past ? " · passed" : ""}</h3>
      ${picked?.past ? "<p class='tiny'>Passed days are crossed out. You can still add or edit events.</p>" : ""}
      <div class="cal-chips">${dayItems.map(eventChip).join("") || "<p class='muted'>No events on this day.</p>"}</div>
      <form class="todo-add" style="margin-top:.75rem">
        <input name="title" maxlength="120" placeholder="Quick to-do for this day" />
        <button type="submit" class="primary">Add to-do</button>
        <button type="button" data-cal="create">Add timed event</button>
      </form>
      <ul class="todo-list">
        ${todos.map((t) => `
          <li class="${t.done ? "done" : ""}">
            <input type="checkbox" data-todo-done="${t.id}" ${t.done ? "checked" : ""} />
            <span>${escapeHtml(t.title)}</span>
            <button type="button" class="todo-del" data-todo-del="${t.id}" aria-label="Remove">×</button>
          </li>`).join("")}
      </ul>
    </div>
  `;
  host.querySelectorAll(".cal-day[data-date]").forEach((btn) => {
    btn.addEventListener("click", (ev) => {
      if (ev.target.closest("[data-event-id]")) return;
      state.selectedDay = btn.dataset.date;
      renderCalendar(host, calendar, role);
    });
    btn.addEventListener("dblclick", () => {
      state.selectedDay = btn.dataset.date;
      openEventEditor({ date: btn.dataset.date });
    });
  });
  host.querySelectorAll("[data-event-id]").forEach((chip) => {
    chip.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const id = chip.dataset.eventId;
      if (!id || chip.dataset.readonly === "1") return;
      const item = (picked?.items || []).concat(cells.flatMap((d) => d.items || [])).find((e) => e.id === id);
      openEventEditor(item || { id, date: selected });
    });
  });
  host.querySelector("[data-cal='prev']")?.addEventListener("click", () => shiftMonth(calendar.prev, host, role));
  host.querySelector("[data-cal='next']")?.addEventListener("click", () => shiftMonth(calendar.next, host, role));
  host.querySelector("[data-cal='today']")?.addEventListener("click", () => {
    state.selectedDay = calendar.today;
    const [y, m] = calendar.today.split("-");
    shiftMonth({ year: Number(y), month: Number(m) }, host, role);
  });
  host.querySelectorAll("[data-cal='create']").forEach((btn) => {
    btn.addEventListener("click", () => openEventEditor({ date: picked?.date || calendar.today }));
  });
  host.querySelector("[data-cal='live']")?.addEventListener("click", async () => {
    const data = await api("/api/demo/live", { method: "POST" });
    state.data = data.state;
    toast("Calendar is on the live date.");
    render();
  });
  host.querySelectorAll("[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.calView = btn.dataset.view;
      renderCalendar(host, calendar, role);
    });
  });
  host.querySelectorAll("[data-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.filter;
      if (state.calHidden.has(key)) state.calHidden.delete(key);
      else state.calHidden.add(key);
      renderCalendar(host, calendar, role);
    });
  });
  host.querySelectorAll("[data-todo-done]").forEach((box) => {
    box.addEventListener("change", async () => {
      await mutateTodo(`/api/todos/${box.dataset.todoDone}`, { method: "PATCH", body: JSON.stringify({ done: box.checked }) }, host, role, calendar);
    });
  });
  host.querySelectorAll("[data-todo-del]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await mutateTodo(`/api/todos/${btn.dataset.todoDel}`, { method: "DELETE" }, host, role, calendar);
    });
  });
  host.querySelector(".todo-add")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const title = new FormData(ev.target).get("title");
    if (!title) {
      openEventEditor({ date: picked.date });
      return;
    }
    await mutateTodo("/api/todos", { method: "POST", body: JSON.stringify({ date: picked.date, title }) }, host, role, calendar);
    toast("To-do saved.");
  });
}

function renderWeek(calendar, selected) {
  const week = calendar.weeks.find((w) => w.some((d) => d.date === selected)) || calendar.weeks[0];
  return `<div class="week-wrap">${week.map((d) => `
    <div class="week-col ${d.date === calendar.today ? "today" : ""} ${d.past ? "past" : ""}" data-date="${d.date}">
      <h4>${d.weekday_name} ${d.day}</h4>
      ${visibleItems(d.items).map((item) => `<button type="button" class="week-item" data-event-id="${item.id || ""}" data-readonly="${item.readonly ? "1" : "0"}" style="background:${item.color}">${item.when ? escapeHtml(item.when) + " · " : ""}${escapeHtml(item.title)}</button>`).join("")}
    </div>`).join("")}</div>`;
}

function renderAgenda(calendar) {
  const rows = [];
  for (const week of calendar.weeks) {
    for (const day of week) {
      if (!day.in_month || day.date < calendar.today) continue;
      for (const item of visibleItems(day.items)) {
        rows.push({ day, item });
      }
    }
  }
  if (!rows.length) return `<p class="muted">No upcoming events. Click + Event to add one.</p>`;
  return `<div class="agenda">${rows.slice(0, 24).map(({ day, item }) => `
    <div class="agenda-row">
      <time>${day.date}<br/>${escapeHtml(item.when || "All day")}</time>
      <div>
        <button type="button" class="week-item" data-event-id="${item.id || ""}" data-readonly="${item.readonly ? "1" : "0"}" style="background:${item.color}">${item.important ? "★ " : ""}${escapeHtml(item.title)}</button>
        <p class="tiny">${escapeHtml(item.location || item.notes || item.calendar)}</p>
      </div>
    </div>`).join("")}</div>`;
}

function openEventEditor(item) {
  const modal = $("event-editor");
  const form = $("event-form");
  state.editingEvent = item && item.id ? item : null;
  $("event-form-title").textContent = state.editingEvent ? "Edit event" : "New event";
  form.title.value = item?.title || "";
  form.date.value = item?.date || state.selectedDay || "";
  form.end_date.value = item?.end_date || "";
  form.all_day.checked = item?.all_day ?? false;
  form.start_time.value = item?.start_time || "16:30";
  form.end_time.value = item?.end_time || "17:30";
  form.calendar.value = item?.calendar || "family";
  form.who.value = item?.who || "family";
  form.repeat.value = item?.repeat || "none";
  form.repeat_until.value = item?.repeat_until || "";
  form.location.value = item?.location || "";
  form.notes.value = item?.notes || "";
  form.important.checked = !!item?.important;
  $("event-times").hidden = form.all_day.checked;
  $("event-delete").hidden = !state.editingEvent;
  modal.hidden = false;
  form.title.focus();
}

function closeEventEditor() {
  $("event-editor").hidden = true;
  state.editingEvent = null;
}

async function refreshCalendarHost() {
  const role = state.user?.role;
  const host = role === "parent" ? $("parent-calendar") : $("child-calendar");
  const cal = state.data?.calendar;
  if (!host || !cal) return;
  const fresh = await api(`/api/calendar?year=${cal.year}&month=${cal.month}`);
  if (state.data) state.data.calendar = fresh;
  renderCalendar(host, fresh, role);
}

async function mutateTodo(path, options, host, role, calendar) {
  const data = await api(path, options);
  state.data = data.state;
  const fresh = await api(`/api/calendar?year=${calendar.year}&month=${calendar.month}`);
  if (state.data) state.data.calendar = fresh;
  renderCalendar(host, fresh, role);
}

async function shiftMonth(target, host, role) {
  if (!target) return;
  const data = await api(`/api/calendar?year=${target.year}&month=${target.month}`);
  if (state.data) state.data.calendar = data;
  renderCalendar(host, data, role);
}

function renderPolicyCard(card) {
  const el = $("policy-card");
  if (!card) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = `
    <h3>${escapeHtml(card.headline)}</h3>
    <ol class="plain-rules">${(card.sentences || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ol>
    ${card.apps?.length ? `<p class="tiny">Already allowed: ${card.apps.map(escapeHtml).join(", ")}</p>` : ""}
  `;
}

function render() {
  if (!state.user) {
    show("doors");
    return;
  }
  $("who").textContent = `${state.user.name} · ${state.user.role}`;
  $("clock-label").textContent = state.data?.clock ? `demo clock ${state.data.clock.slice(0, 16)}` : "live clock";
  $("model-label").textContent = state.model || "";
  show(state.user.role === "parent" ? "parent" : "child");
  try {
    if (state.user.role === "parent") renderParent();
    else renderChild();
  } catch (err) {
    console.error(err);
    toast(err.message || "The parent desk hit an error.");
    const home = $("pane-home");
    if (home && !home.innerHTML.trim()) {
      home.innerHTML = `<article class="panel"><h2>Family Loop</h2><p>${escapeHtml(err.message)}</p></article>`;
    }
  }
}

function fillSetupForm(s) {
  const form = $("setup-form");
  const policy = s.policy;
  const choices = s.choices || {};
  if (!policy) {
    bindChoices(choices);
    chips($("sports-days"), DAY_CHIPS, new Set(["1", "3"]), { tone: false });
    removableChips($("allowed-apps"), ["YouTube", "WhatsApp", "Khan Academy", "Google Classroom", "Maps", "Phone"]);
    return;
  }
  form.age.value = policy.age || 13;
  form.school_start.value = policy.school_hours?.start || "08:00";
  form.school_end.value = policy.school_hours?.end || "15:00";
  form.daily_cap_minutes.value = policy.daily_cap_minutes || 120;
  form.youtube_after_homework.checked = !!policy.youtube_after_homework;
  form.sports_phone_preset.checked = !!policy.sports_phone_preset;
  form.notes.value = policy.notes || choices.parent_note_default || DEFAULT_NOTE;
  if (form.homework_done_after) form.homework_done_after.value = policy.homework_done_after || "17:00";
  if (form.sports_start) form.sports_start.value = policy.sports_hours?.start || "16:30";
  if (form.sports_end) form.sports_end.value = policy.sports_hours?.end || "18:00";
  const askOpts = [...(choices.ask_first || FALLBACK_ASK)];
  (policy.ask_first || []).forEach((key) => {
    if (!askOpts.some((opt) => (opt.key || opt) === key)) askOpts.push({ key, label: key.replaceAll("_", " ") });
  });
  const hardOpts = [...(choices.hard_no || FALLBACK_HARD)];
  (policy.hard_no || []).forEach((key) => {
    if (!hardOpts.some((opt) => (opt.key || opt) === key)) hardOpts.push({ key, label: key.replaceAll("_", " ") });
  });
  chips($("ask-first"), askOpts, new Set((policy.ask_first || []).map(String)));
  chips($("hard-no"), hardOpts, new Set((policy.hard_no || []).map(String)));
  chips($("sports-days"), DAY_CHIPS, new Set((policy.sports_days || [1, 3]).map(String)), { tone: false });
  removableChips($("allowed-apps"), [...(policy.approved_apps || [])]);
  const family = $("family-form");
  if (family) {
    family.parent_name.value = s.parent?.name || "Meera";
    family.child_name.value = s.child?.name || "Aarav";
    family.city.value = s.child?.city || "Bengaluru";
  }
  const proof = $("family-proof");
  if (proof) {
    const parent = s.parent?.name || "Meera";
    const child = s.child?.name || "Aarav";
    const city = s.child?.city || "Bengaluru";
    proof.textContent = `On file: ${parent} · ${child} · ${city}`;
  }
}

function setParentPane(name, opts = {}) {
  state.parentPane = name || "home";
  ["home", "decisions", "timeline", "calendar", "memory", "desk"].forEach((pane) => {
    const el = $(`pane-${pane}`);
    if (!el) return;
    if (pane === state.parentPane) el.removeAttribute("hidden");
    else el.setAttribute("hidden", "");
  });
  document.querySelectorAll("#parent-nav [data-pane]").forEach((btn) => {
    btn.classList.toggle("on", btn.dataset.pane === state.parentPane);
  });
  if (state.parentPane === "calendar") {
    renderCalendar($("parent-calendar"), state.data?.calendar, "parent");
  }
  if (opts.scroll) {
    const pane = $(`pane-${state.parentPane}`);
    if (pane) pane.scrollIntoView({ block: "start", behavior: "smooth" });
  }
}

function decisionCard(item) {
  const id = item.id || "";
  return `<article class="decision-card tone-${item.tone || "amber"}">
    <h3>${item.tone === "red" ? "🔴" : "🟡"} ${escapeHtml(item.title || item.subject || "")}</h3>
    <p>${escapeHtml(item.detail || "")}</p>
    <p class="why"><strong>Why this matters.</strong> ${escapeHtml(item.why || "")}</p>
    <p class="tiny">Rule: ${escapeHtml(item.rule || "")}</p>
    ${id ? `<div class="row-actions">
      <button type="button" class="btn-allow" data-allow="${id}">Allow</button>
      ${String(id).startsWith("app:") ? "" : `<button type="button" class="btn-sky" data-pending="${id}">Keep pending</button>`}
      <button type="button" class="btn-deny" data-deny="${id}">Deny</button>
    </div>` : ""}
  </article>`;
}

function shortTrace(row) {
  const event = String(row.event || "");
  const map = {
    setup: "Policy saved",
    locks: "Locks checklist saved",
    new_ask: "Request history retrieved · ask filed",
    ping: "Check-in requested",
    snapshot: "Snapshot compared to approved apps",
    sunday: "Sunday digest filed",
    digest: "Sunday digest filed",
    decide: "Parent decision recorded",
    tool: "Tool completed",
  };
  return map[event] || `${row.agent || "Family desk"} · ${event}`;
}

function renderCommand(s) {
  const cmd = s.command || {};
  const child = cmd.child || {};
  const parentName = s.parent?.name || "Meera";
  const waiting = cmd.decisions_waiting || 0;
  const badge = $("nav-badge");
  if (badge) badge.textContent = waiting;
  const today = (cmd.today || []).map((row) => `<li><span>${escapeHtml(row.time)}</span> ${escapeHtml(row.title)}</li>`).join("");
  const needs = (cmd.needs_you || []).map(decisionCard).join("") || "<p class='muted'>Nothing waiting.</p>";
  const patterns = (s.patterns || []).map((p) => `<article class="pattern-card">
    <h3>${escapeHtml(p.title)}</h3>
    <p>${escapeHtml(p.body)}</p>
    ${p.request_id ? `<div class="row-actions">
      <button type="button" class="btn-allow" data-allow="${p.request_id}">Allow</button>
      <button type="button" class="btn-deny" data-deny="${p.request_id}">Deny</button>
      <button type="button" class="btn-sky" data-pending="${p.request_id}">Keep pending</button>
    </div>` : ""}
  </article>`).join("");
  const sim = (state.simSteps || []).map((step) => `<li><span>${escapeHtml(step.at)}</span> ${escapeHtml(step.text)}</li>`).join("");
  const digest = s.latest_digest || {};
  const changed = digest.what_changed || s.what_changed || {};
  const evalSteps = (digest.steps || [
    "Policy loaded",
    "7-day history loaded",
    "Latest snapshot loaded",
    "Snapshot compared",
    "Missed pings checked",
    "Pending decisions checked",
    "Exceptions classified",
    "Family state updated",
    "Digest filed",
  ]).slice(0, 9);
  const showEval = Boolean(digest.id || digest.steps);
  $("pane-home").innerHTML = `
    <header class="os-hello">
      <p class="kicker">Family Loop · ${new Date().toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })}</p>
      <h2>${escapeHtml(parentName)}</h2>
      <p class="lede">${escapeHtml(cmd.headline || "Nothing urgent today.")}</p>
    </header>
    <div class="status-strip tone-${cmd.health_tone || "green"}">
      <div><span>Family status</span><strong>${escapeHtml(cmd.health_label || "Stable")}</strong></div>
      <div><span>Urgent</span><strong>${cmd.attention?.urgent ?? 0}</strong></div>
      <div><span>Decisions</span><strong>${cmd.attention?.decisions ?? waiting}</strong></div>
      <div><span>Informational</span><strong>${cmd.attention?.informational ?? 0}</strong></div>
    </div>
    <p class="tiny attention-line">Agents only knock when someone has to say yes or no.</p>
    <article class="panel">
      <h2>60-second path</h2>
      <ol class="judge-path">
        <li><span>1</span> Rules → save house policy + locks</li>
        <li><span>2</span> Aarav asks for Reddit → pending</li>
        <li><span>3</span> Fast-forward family → Discord exception</li>
        <li><span>4</span> Sunday evaluation → Red / Needs you / Green</li>
        <li><span>5</span> Meera decides. The OS still enforces.</li>
      </ol>
    </article>
    <div class="os-grid">
      <article class="panel">
        <h2>Needs you</h2>
        ${needs}
      </article>
      <article class="panel">
        <h2>Today</h2>
        <ul class="plan-list today-list">${today || "<li>Nothing on the calendar.</li>"}</ul>
        <h2 class="week-h">This week</h2>
        <ul class="stats">
          <li>Check-ins <b>${escapeHtml(cmd.week?.checkins || "—")}</b></li>
          <li>Adherence <b>${child.adherence ?? "—"}%</b></li>
          <li>New apps <b>${cmd.week?.new_apps ?? 0}</b></li>
          <li>Pending decisions <b>${waiting}</b></li>
        </ul>
      </article>
    </div>
    ${changed.summary ? `<article class="panel">
      <h2>What changed</h2>
      <ul class="stats">
        <li>Screen time <b>${changed.screen_delta > 0 ? "+" : ""}${changed.screen_delta ?? 0}%</b></li>
        <li>New requests <b>${changed.new_requests ?? 0}</b></li>
        <li>Still waiting <b>${changed.still_waiting ?? 0}</b></li>
      </ul>
      <p>${escapeHtml(changed.summary)}</p>
    </article>` : ""}
    ${showEval ? `<article class="panel eval-panel">
      <p class="kicker">Sunday evaluation · Family Desk → Digest writer</p>
      <ol class="eval-steps">${evalSteps.map((line) => `<li>${escapeHtml(line.replace(/^✓\s*/, ""))}</li>`).join("")}</ol>
      <button type="button" class="btn-sky" id="copy-digest">Copy Sunday letter</button>
    </article>` : ""}
    <article class="panel">
      <h2>Family desk</h2>
      <ol class="trace-list">${(s.trace || []).slice(0, 6).map((row) =>
        `<li>${escapeHtml(shortTrace(row))}</li>`
      ).join("") || "<li>No tool activity yet.</li>"}</ol>
    </article>
    ${patterns ? `<article class="panel"><h2>Pattern</h2>${patterns}</article>` : ""}
    <div class="demo-rail">
      <button type="button" class="btn-sun" data-demo="simulate-saturday">Run Saturday simulation</button>
      <button type="button" class="btn-primary" data-demo="fast-forward">Fast-forward family</button>
    </div>
    ${sim ? `<article class="panel"><h2>Simulation</h2><ol class="sim-list">${sim}</ol></article>` : ""}
  `;
  $("copy-digest")?.addEventListener("click", async () => {
    const letter = digest.whatsapp || digest.letter || changed.summary || "";
    try {
      await navigator.clipboard.writeText(letter);
      toast("Sunday letter copied.");
    } catch (_) {
      toast(letter);
    }
  });
  $("pane-decisions").innerHTML = `
    <h2>${waiting} need you</h2>
    <p class="hint">The OS still enforces. You only decide.</p>
    ${(cmd.needs_you || []).map(decisionCard).join("") || "<p class='muted'>Inbox empty.</p>"}
  `;
  $("pane-timeline").innerHTML = (s.timeline || []).map((day) => `
    <article class="time-day">
      <h3>${escapeHtml(day.date)}</h3>
      <ul>${(day.items || []).map((it) => `<li class="tone-${it.tone}"><strong>${escapeHtml(it.title)}</strong><br/>${escapeHtml(it.detail || "")}</li>`).join("")}</ul>
    </article>
  `).join("") || "<p class='muted'>No memory yet. File an ask or a snapshot.</p>";
  const mem = s.memory || {};
  $("pane-memory").innerHTML = `
    <article class="panel">
      <h2>What Family Loop knows</h2>
      <p class="tiny">Persistent memory. Not a chat log.</p>
      <h3>Policy</h3>
      <p>Ask-first: ${escapeHtml((mem.policy?.ask_first || []).join(", ") || "—")}<br/>
      Hard-no: ${escapeHtml((mem.policy?.hard_no || []).join(", ") || "—")}<br/>
      YouTube: ${escapeHtml(mem.policy?.youtube || "—")}</p>
      <h3>People</h3>
      <ul>${(mem.people || []).map((p) => `<li>${escapeHtml(p.name)} — ${escapeHtml(p.role)}</li>`).join("")}</ul>
      <h3>Approvals</h3>
      <ul>${(mem.approvals || []).map((a) => `<li>${escapeHtml(a.name)} · ${escapeHtml(a.status)}</li>`).join("")}</ul>
      <h3>Routines</h3>
      <ul>${(mem.routines || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
      <h3>Recent patterns</h3>
      <ul>${(mem.patterns || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
    </article>
  `;
}

function renderParent() {
  const s = state.data || {};
  renderCommand(s);
  setParentPane(state.parentPane || "home");
  renderCalendar($("parent-calendar"), s.calendar, "parent");
  fillSetupForm(s);
  renderPolicyCard(s.policy_card);
  const form = $("locks-form");
  if (!form) return;
  form.innerHTML = "";
  (s.lock_items || []).forEach((item) => {
    const label = document.createElement("label");
    label.className = "check";
    label.innerHTML = `<input type="checkbox" name="${item.key}" ${s.locks?.[item.key] ? "checked" : ""}/> <span><strong>${item.label}</strong><br/><span class="muted">${item.hint}</span></span>`;
    form.appendChild(label);
  });
  const save = document.createElement("button");
  save.type = "submit";
  save.className = "btn-sky";
  save.textContent = "Save checklist";
  form.appendChild(save);
  const locksStatus = $("locks-status");
  if (locksStatus) {
    locksStatus.textContent = s.locks_complete
      ? `Locks claimed on ${s.locks?.locks_claimed_on || "today"}. Detection is only as strong as this list.`
      : "Locks not finished. Sunday will go Red: detection is weak.";
  }

  const inbox = $("inbox-list");
  const rows = s.requests || [];
  if (inbox) inbox.innerHTML = rows.length ? "" : "<p class='muted'>Inbox empty. File an ask above, or wait for Aarav.</p>";
  (inbox ? rows.slice().reverse() : []).forEach((req) => {
    const card = document.createElement("div");
    card.className = "card inbox-card";
    card.innerHTML = `<h3>${escapeHtml(kindLabel(req.kind))} · ${escapeHtml(req.status)}</h3>
      <label>What <input data-edit-subject="${req.id}" value="${escapeAttr(req.subject || "")}" /></label>
      <label>Why <textarea data-edit-detail="${req.id}" rows="2">${escapeAttr(req.detail || "")}</textarea></label>
      <label>Your note <textarea data-edit-note="${req.id}" rows="2">${escapeAttr(req.parent_note || "")}</textarea></label>
      <p class="tiny">${escapeHtml(req.reason || "")}</p>
      <div class="row-actions">
        <button type="button" class="btn-allow" data-allow="${req.id}">Allow</button>
        <button type="button" class="btn-deny" data-deny="${req.id}">Deny</button>
        <button type="button" class="btn-sky" data-pending="${req.id}">Make pending</button>
        <button type="button" class="btn-primary" data-save-ask="${req.id}">Save edits</button>
      </div>`;
    inbox.appendChild(card);
  });

  const digest = s.latest_digest;
  const board = $("digest-board");
  if (board && (!digest || !digest.red)) {
    board.innerHTML = "<p class='muted'>Sunday has not run this week.</p>";
  } else if (board) {
    board.innerHTML = ["red", "needs_you", "green"].map((key, i) => {
      const title = ["Red", "Needs you", "Green"][i];
      const cls = ["red", "needs", "green"][i];
      const items = digest[key] || [];
      return `<div class="bucket ${cls}"><h3>${title}</h3><ul>${
        items.length ? items.map((it) => `<li><strong>${escapeHtml(it.title)}</strong><br/>${escapeHtml(it.detail)}</li>`).join("") : "<li>none</li>"
      }</ul></div>`;
    }).join("");
  }
  const lastMsg = (s.outbox || []).filter((m) => m.channel === "whatsapp").slice(-1)[0]
    || (s.outbox || []).slice(-1)[0];
  const wa = $("wa-edit");
  if (wa && document.activeElement !== wa) {
    wa.value = lastMsg?.body || digest?.whatsapp || "";
  }

  const log = $("agent-log");
  if (log) {
    const lines = (s.agent_log || []).slice().reverse().map((row) => {
      return `<li><strong>${escapeHtml(row.at || "")}</strong> · ${escapeHtml(row.agent || "")} / ${escapeHtml(row.event || row.tool || "")}<br/>${escapeHtml(row.summary || "")}</li>`;
    });
    log.innerHTML = lines.join("") || "<li>Desk is quiet.</li>";
  }
}

function kindLabel(kind) {
  const found = (state.data?.choices?.kinds || []).find((k) => k.key === kind);
  return found ? found.label : String(kind || "").replaceAll("_", " ");
}

function renderChild() {
  const s = state.data || {};
  renderCalendar($("child-calendar"), s.calendar, "child");
  const banner = $("child-banner");
  if (s.banner) {
    banner.hidden = false;
    banner.innerHTML = `<strong>${escapeHtml(s.banner.title)}</strong><p>${escapeHtml(s.banner.body)}</p>`;
  } else {
    banner.hidden = true;
  }
  const list = $("child-asks");
  const rows = s.requests || [];
  list.innerHTML = rows.length ? "<h3 class='ask-log-title'>Sent to the desk</h3>" : "<p class='muted'>No asks filed yet. Use + add more request for a second one.</p>";
  rows.slice().reverse().forEach((req) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>${escapeHtml(req.subject)}</h3><p class="muted">${escapeHtml(kindLabel(req.kind))} · ${escapeHtml(req.status)}${req.detail ? " · " + escapeHtml(req.detail) : ""}</p>`;
    list.appendChild(card);
  });
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\n", "<br/>");
}

function escapeAttr(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function addAskForm(prefill) {
  const wrap = $("ask-forms");
  const node = $("ask-form-template").content.firstElementChild.cloneNode(true);
  if (prefill) {
    if (prefill.kind) node.kind.value = prefill.kind;
    if (prefill.subject) node.subject.value = prefill.subject;
    if (prefill.detail) node.detail.value = prefill.detail;
  }
  node.addEventListener("submit", submitAsk);
  node.querySelector(".remove-ask").addEventListener("click", () => {
    if (wrap.children.length <= 1) {
      toast("Keep at least one request box.");
      return;
    }
    node.remove();
  });
  wrap.appendChild(node);
}

async function submitAsk(ev) {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const data = await api("/api/asks", {
    method: "POST",
    body: JSON.stringify({
      kind: fd.get("kind"),
      subject: fd.get("subject"),
      detail: fd.get("detail"),
      costs_money: fd.get("costs_money") === "on",
    }),
  });
  state.data = data.state;
  ev.target.reset();
  toast("On the desk. Waiting is not a silent yes.");
  render();
}

async function refresh() {
  const me = await api("/api/me");
  state.user = me.user;
  state.data = me.state;
  state.model = me.model;
  render();
}

async function enter(role) {
  const email = role === "parent" ? "meera@familyloop.demo" : "aarav@familyloop.demo";
  const password = role === "parent" ? "parent" : "aarav";
  const data = await api("/api/login", { method: "POST", body: JSON.stringify({ email, password }) });
  state.user = data.user;
  state.data = data.state;
  bindChoices(data.state?.choices);
  render();
}

function bindChoices(choices) {
  const ask = choices?.ask_first || FALLBACK_ASK;
  const hard = choices?.hard_no || FALLBACK_HARD;
  chips($("ask-first"), ask, new Set(ask.slice(0, 4).map((c) => c.key || c)));
  chips($("hard-no"), hard, new Set(hard.slice(0, 2).map((c) => c.key || c)));
  const notes = $("parent-notes");
  if (notes && !notes.value) notes.value = choices?.parent_note_default || DEFAULT_NOTE;
}

document.querySelectorAll(".door").forEach((btn) => {
  btn.addEventListener("click", () => enter(btn.dataset.role).catch((err) => toast(err.message)));
});

const agentDock = $("agent-dock");
const agentToggle = $("agent-toggle");
const agentPop = $("agent-pop");
function closeAgents() {
  if (!agentPop) return;
  agentPop.hidden = true;
  agentToggle?.setAttribute("aria-expanded", "false");
}
agentToggle?.addEventListener("click", (ev) => {
  ev.stopPropagation();
  const open = agentPop.hidden;
  agentPop.hidden = !open;
  agentToggle.setAttribute("aria-expanded", open ? "true" : "false");
});
document.addEventListener("click", (ev) => {
  if (agentDock && !agentDock.contains(ev.target)) closeAgents();
});

$("logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  state.user = null;
  state.data = null;
  renderHome();
});

$("add-request").addEventListener("click", () => addAskForm());

$("setup-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const payload = {
    age: Number(fd.get("age")),
    school_hours: { start: fd.get("school_start"), end: fd.get("school_end") },
    ask_first: [...($("ask-first")._selected || [])],
    hard_no: [...($("hard-no")._selected || [])],
    youtube_after_homework: fd.get("youtube_after_homework") === "on",
    sports_phone_preset: fd.get("sports_phone_preset") === "on",
    daily_cap_minutes: Number(fd.get("daily_cap_minutes")),
    notes: fd.get("notes") || DEFAULT_NOTE,
    approved_apps: $("allowed-apps")._items || [],
    sports_days: [...($("sports-days")._selected || [])].map(Number),
    sports_hours: { start: fd.get("sports_start"), end: fd.get("sports_end") },
    homework_done_after: fd.get("homework_done_after"),
    child_name: $("family-form")?.child_name?.value || undefined,
  };
  const data = await api("/api/setup", { method: "POST", body: JSON.stringify(payload) });
  state.data = data.state;
  toast("House rules saved in plain words.");
  render();
});

$("locks-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const payload = {
    screen_time_on: fd.get("screen_time_on") === "on",
    ask_to_install: fd.get("ask_to_install") === "on",
    youtube_supervised: fd.get("youtube_supervised") === "on",
    roblox_pin: fd.get("roblox_pin") === "on",
    downtime_school_hours: fd.get("downtime_school_hours") === "on",
  };
  const data = await api("/api/locks", { method: "POST", body: JSON.stringify(payload) });
  state.data = data.state;
  $("locks-status").textContent = data.state.locks_complete
    ? `Locks claimed on ${data.state.locks?.locks_claimed_on || "today"}. Detection is only as strong as this list.`
    : "Locks not finished. Sunday will go Red: detection is weak.";
  toast("Checklist saved. Still not an OS write.");
});

async function handleDeskClick(ev) {
  const demoBtn = ev.target.closest("[data-demo]");
  if (demoBtn) {
    const kind = demoBtn.dataset.demo;
    const path = {
      saturday: "/api/demo/saturday",
      sunday: "/api/demo/sunday",
      ping: "/api/ping",
      digest: "/api/digest",
      reset: "/api/demo/reset",
      week: "/api/demo/week",
      live: "/api/demo/live",
      "simulate-saturday": "/api/demo/simulate-saturday",
      "fast-forward": "/api/demo/fast-forward",
    }[kind];
    if (!path) return;
    const data = await api(path, { method: "POST" });
    state.data = data.state;
    if (data.steps) state.simSteps = data.steps;
    toast(kind === "digest" ? "Sunday is on the desk." : `Demo: ${kind}`);
    if (kind === "fast-forward" || kind === "simulate-saturday") state.parentPane = "home";
    render();
    return;
  }
  const btn = ev.target.closest("[data-allow], [data-deny], [data-pending], [data-save-ask]");
  if (!btn) return;
  const allow = btn.dataset.allow;
  const deny = btn.dataset.deny;
  const pending = btn.dataset.pending;
  const saveAsk = btn.dataset.saveAsk;
  const id = allow || deny || pending || saveAsk;
  if (!id) return;
  if (String(id).startsWith("app:")) {
    if (pending) return;
    const subject = String(id).slice(4);
    const status = allow ? "allowed" : "denied";
    const data = await api("/api/exceptions", {
      method: "POST",
      body: JSON.stringify({ subject, status }),
    });
    state.data = data.state;
    toast(status === "allowed" ? `${subject} is now allowed.` : `${subject} stays off the list.`);
    render();
    return;
  }
  const note = document.querySelector(`[data-edit-note="${id}"]`)?.value || "";
  const subject = document.querySelector(`[data-edit-subject="${id}"]`)?.value;
  const detail = document.querySelector(`[data-edit-detail="${id}"]`)?.value;
  if (saveAsk || pending) {
    const data = await api(`/api/asks/${id}`, {
      method: "PATCH",
      body: JSON.stringify({
        status: pending ? "pending" : undefined,
        parent_note: note,
        subject,
        detail,
      }),
    });
    state.data = data.state;
    toast(pending ? "Ask is pending again." : "Ask edits saved.");
    render();
    return;
  }
  const data = await api(`/api/asks/${id}/decide`, {
    method: "POST",
    body: JSON.stringify({ status: allow ? "allowed" : "denied", note: note || (allow ? "Parent allowed once." : "Not this week.") }),
  });
  state.data = data.state;
  render();
}

document.addEventListener("click", (ev) => {
  const paneBtn = ev.target.closest("#parent-nav [data-pane]");
  if (paneBtn) {
    ev.preventDefault();
    setParentPane(paneBtn.dataset.pane, { scroll: true });
    return;
  }
  if (ev.target.closest("[data-demo], [data-allow], [data-deny], [data-pending], [data-save-ask]")) {
    handleDeskClick(ev).catch((err) => toast(err.message));
  }
});

$("family-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const data = await api("/api/family", {
    method: "PATCH",
    body: JSON.stringify({
      parent_name: fd.get("parent_name"),
      child_name: fd.get("child_name"),
      city: fd.get("city"),
    }),
  });
  state.data = data.state;
  const parent = data.state.parent?.name || fd.get("parent_name");
  const child = data.state.child?.name || fd.get("child_name");
  const city = data.state.child?.city || fd.get("city");
  const proof = $("family-proof");
  if (proof) {
    proof.textContent = `Saved just now: ${parent} · ${child} · ${city}`;
    proof.classList.add("flash");
  }
  toast(`Saved: ${parent}, ${child}, ${city}`);
  state.parentPane = "memory";
  render();
});

$("parent-ask-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const data = await api("/api/asks", {
    method: "POST",
    body: JSON.stringify({
      kind: fd.get("kind"),
      subject: fd.get("subject"),
      detail: fd.get("detail"),
      costs_money: fd.get("costs_money") === "on",
    }),
  });
  state.data = data.state;
  ev.target.reset();
  toast("Ask filed on the desk.");
  render();
});

$("outbox-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const data = await api("/api/outbox", {
    method: "POST",
    body: JSON.stringify({ channel: "whatsapp", body: $("wa-edit").value }),
  });
  state.data = data.state;
  toast("Sunday letter saved.");
  render();
});

$("ask-first-add").addEventListener("click", () => {
  addCustomChip($("ask-first"), $("ask-first-new").value);
  $("ask-first-new").value = "";
});
$("hard-no-add").addEventListener("click", () => {
  addCustomChip($("hard-no"), $("hard-no-new").value);
  $("hard-no-new").value = "";
});
$("allowed-add").addEventListener("click", () => {
  const name = $("allowed-new").value.trim();
  if (!name) return;
  const items = $("allowed-apps")._items || [];
  if (!items.includes(name)) items.push(name);
  removableChips($("allowed-apps"), items);
  $("allowed-new").value = "";
});

$("locks-form").addEventListener("change", () => {
  $("locks-form").requestSubmit();
});

$("model-switch")?.addEventListener("click", async (ev) => {
  const btn = ev.target.closest("[data-mode]");
  if (!btn) return;
  try {
    const data = await api("/api/model", { method: "POST", body: JSON.stringify({ mode: btn.dataset.mode }) });
    document.querySelectorAll("#model-switch [data-mode]").forEach((b) => {
      b.classList.toggle("on", b.dataset.mode === data.mode);
    });
    state.model = data.label;
    if ($("model-label")) $("model-label").textContent = data.label;
    toast(data.mode === "lmstudio" ? "LM Studio · 192.168.31.64:1234" : "Amazon Bedrock");
    wakePets(data.mode === "lmstudio" ? ["family_desk"] : ["family_desk"]);
  } catch (err) {
    toast(err.message);
    refreshModelSwitch();
  }
});

$("parent-nav")?.addEventListener("click", (ev) => {
  const btn = ev.target.closest("[data-pane]");
  if (!btn) return;
  ev.preventDefault();
  setParentPane(btn.dataset.pane, { scroll: true });
});

$("checkin-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData(ev.target);
  const data = await api("/api/checkin", {
    method: "POST",
    body: JSON.stringify({ raw_list: fd.get("raw_list"), kind: "random" }),
  });
  state.data = data.state;
  toast("Snapshot filed as a human paste.");
  render();
});

$("checkin-photo")?.addEventListener("change", async (ev) => {
  const file = ev.target.files && ev.target.files[0];
  if (!file) return;
  const status = $("ocr-status");
  status.textContent = "Reading the photo…";
  const body = new FormData();
  body.append("image", file);
  const res = await fetch("/api/ocr", { method: "POST", body, credentials: "same-origin" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    status.textContent = data.detail || "Could not read that photo.";
    toast(status.textContent);
    return;
  }
  $("checkin-text").value = data.raw_list || data.text || "";
  const n = (data.apps || []).length;
  status.textContent = n
    ? `Read ${n} app${n === 1 ? "" : "s"} from the photo. Check the list, then file.`
    : "Got text from the photo. Edit the list if a name looks wrong, then file.";
  toast("Photo converted to a Screen Time list.");
});

$("event-form").all_day.addEventListener("change", () => {
  $("event-times").hidden = $("event-form").all_day.checked;
});
$("event-cancel").addEventListener("click", closeEventEditor);
$("event-editor").addEventListener("click", (ev) => {
  if (ev.target === $("event-editor")) closeEventEditor();
});
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && !$("event-editor").hidden) closeEventEditor();
});
$("event-delete").addEventListener("click", async () => {
  if (!state.editingEvent?.id) return;
  const data = await api(`/api/events/${state.editingEvent.id}`, { method: "DELETE" });
  state.data = data.state;
  closeEventEditor();
  toast("Event removed.");
  await refreshCalendarHost();
});
$("event-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const form = ev.target;
  const payload = {
    title: form.title.value,
    date: form.date.value,
    end_date: form.end_date.value || null,
    all_day: form.all_day.checked,
    start_time: form.all_day.checked ? null : form.start_time.value,
    end_time: form.all_day.checked ? null : form.end_time.value,
    calendar: form.calendar.value,
    who: form.who.value,
    repeat: form.repeat.value,
    repeat_until: form.repeat_until.value || null,
    location: form.location.value,
    notes: form.notes.value,
    important: form.important.checked,
  };
  const editing = state.editingEvent?.id;
  const data = editing
    ? await api(`/api/events/${editing}`, { method: "PATCH", body: JSON.stringify(payload) })
    : await api("/api/events", { method: "POST", body: JSON.stringify(payload) });
  state.data = data.state;
  closeEventEditor();
  toast(editing ? "Event updated." : "Event added to the family calendar.");
  await refreshCalendarHost();
});

async function renderHome() {
  show("doors");
  $("top-meta").hidden = true;
  try {
    const doors = await api("/api/doors");
    bindChoices(doors.choices);
  } catch (err) {
    toast(err.message);
  }
}

mountPets();
refreshModelSwitch();
addAskForm();

const doorParam = new URLSearchParams(location.search).get("door");
api("/api/me").then((me) => {
  state.user = me.user;
  state.data = me.state;
  state.model = me.model;
  bindChoices(me.state?.choices);
  render();
}).catch(async () => {
  if (doorParam === "child" || doorParam === "parent") {
    try {
      await enter(doorParam);
      return;
    } catch (err) {
      toast(err.message);
    }
  }
  renderHome();
});
