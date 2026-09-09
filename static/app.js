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
  return data;
}

function toast(msg) {
  const el = $("toast");
  el.hidden = false;
  el.textContent = msg;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { el.hidden = true; }, 3200);
}

function chips(container, options, selected) {
  container.innerHTML = "";
  container._options = options;
  options.forEach((opt) => {
    const key = String(opt.key || opt);
    const label = opt.label || String(key).replaceAll("_", " ");
    const hint = opt.hint || "";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip" + (selected.has(key) ? " on" : "");
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
  chips(container, options, selected);
}

function removableChips(container, items) {
  container.innerHTML = "";
  container._items = items;
  items.forEach((name, index) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip on";
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
  if (state.user.role === "parent") renderParent();
  else renderChild();
}

function fillSetupForm(s) {
  const form = $("setup-form");
  const policy = s.policy;
  const choices = s.choices || {};
  if (!policy) {
    bindChoices(choices);
    chips($("sports-days"), DAY_CHIPS, new Set(["1", "3"]));
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
  chips($("sports-days"), DAY_CHIPS, new Set((policy.sports_days || [1, 3]).map(String)));
  removableChips($("allowed-apps"), [...(policy.approved_apps || [])]);
  const family = $("family-form");
  if (family) {
    family.parent_name.value = s.parent?.name || "Meera";
    family.child_name.value = s.child?.name || "Aarav";
    family.city.value = s.child?.city || "Bengaluru";
  }
}

function renderParent() {
  const s = state.data || {};
  renderCalendar($("parent-calendar"), s.calendar, "parent");
  fillSetupForm(s);
  renderPolicyCard(s.policy_card);
  const form = $("locks-form");
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
  $("locks-status").textContent = s.locks_complete
    ? `Locks claimed on ${s.locks?.locks_claimed_on || "today"}. Detection is only as strong as this list.`
    : "Locks not finished. Sunday will go Red: detection is weak.";

  const inbox = $("inbox-list");
  const rows = s.requests || [];
  inbox.innerHTML = rows.length ? "" : "<p class='muted'>Inbox empty. File an ask above, or wait for Aarav.</p>";
  rows.slice().reverse().forEach((req) => {
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
  if (!digest || !digest.red) {
    board.innerHTML = "<p class='muted'>Sunday has not run this week.</p>";
  } else {
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
  log.innerHTML = (s.agent_log || []).slice().reverse().map((row) =>
    `<li><strong>${escapeHtml(row.at || "")}</strong> · ${escapeHtml(row.agent || "")} / ${escapeHtml(row.event || row.tool || "")}<br/>${escapeHtml(row.summary || "")}</li>`
  ).join("") || "<li>Desk is quiet.</li>";
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

$("inbox-list").addEventListener("click", async (ev) => {
  const allow = ev.target.dataset.allow;
  const deny = ev.target.dataset.deny;
  const pending = ev.target.dataset.pending;
  const saveAsk = ev.target.dataset.saveAsk;
  const id = allow || deny || pending || saveAsk;
  if (!id) return;
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
  toast("Family details saved.");
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

document.querySelectorAll("[data-demo]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const kind = btn.dataset.demo;
    const path = {
      saturday: "/api/demo/saturday",
      sunday: "/api/demo/sunday",
      ping: "/api/ping",
      digest: "/api/digest",
      reset: "/api/demo/reset",
      week: "/api/demo/week",
      live: "/api/demo/live",
    }[kind];
    const data = await api(path, { method: "POST" });
    state.data = data.state;
    toast(kind === "digest" ? "Sunday is on the desk." : `Demo: ${kind}`);
    render();
  });
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
