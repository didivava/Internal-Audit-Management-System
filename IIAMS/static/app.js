(() => {
  "use strict";

  const STORAGE_KEY = "northstar-audit-demo-v1";
  const today = new Date();
  const localDate = (offset = 0) => {
    const date = new Date(today);
    date.setDate(date.getDate() + offset);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };
  const initialData = {
    audits: [
      { id: "AUD-026", title: "Procure to Pay", area: "Finance & Procurement", owner: "Morgan Lee", lead: "Jordan Davis", start: localDate(-8), end: localDate(22), risk: "High", status: "In progress", progress: 62 },
      { id: "AUD-025", title: "Customer Data Privacy", area: "Technology", owner: "Taylor Chen", lead: "Sam Rivera", start: localDate(-5), end: localDate(28), risk: "Critical", status: "In progress", progress: 38 },
      { id: "AUD-024", title: "Vendor Management", area: "Operations", owner: "Casey Patel", lead: "Jordan Davis", start: localDate(-22), end: localDate(7), risk: "High", status: "Reporting", progress: 84 },
      { id: "AUD-023", title: "Payroll Controls", area: "People & Culture", owner: "Jamie Wilson", lead: "Alex Morgan", start: localDate(11), end: localDate(39), risk: "Medium", status: "Planning", progress: 12 },
      { id: "AUD-022", title: "Business Continuity", area: "Technology", owner: "Taylor Chen", lead: "Sam Rivera", start: localDate(-48), end: localDate(-10), risk: "Medium", status: "Complete", progress: 100 }
    ],
    findings: [
      { id: "F-104", title: "Supplier bank details lack independent verification", auditId: "AUD-026", severity: "High", owner: "Morgan Lee", due: localDate(8), status: "Open", impact: "A single user can create a supplier and change payment details without independent review.", recommendation: "Require a second-person review for supplier master changes and retain approval evidence." },
      { id: "F-103", title: "Retention rules not consistently applied", auditId: "AUD-025", severity: "Critical", owner: "Taylor Chen", due: localDate(4), status: "Management response", impact: "Personal data may be retained beyond approved retention periods.", recommendation: "Implement and monitor approved retention schedules across data stores." },
      { id: "F-102", title: "Vendor reviews are past due", auditId: "AUD-024", severity: "Medium", owner: "Casey Patel", due: localDate(18), status: "In progress", impact: "Changes in vendor risk may not be identified promptly.", recommendation: "Introduce risk-based review reminders and escalation for overdue assessments." },
      { id: "F-101", title: "Purchase orders approved after commitment", auditId: "AUD-026", severity: "High", owner: "Morgan Lee", due: localDate(-2), status: "Open", impact: "Commitments may bypass delegated authority and budget checks.", recommendation: "Configure pre-commitment approval controls and monitor exceptions." },
      { id: "F-100", title: "Access recertification evidence incomplete", auditId: "AUD-025", severity: "Medium", owner: "Taylor Chen", due: localDate(26), status: "In progress", impact: "Inappropriate access may remain active after role changes.", recommendation: "Retain reviewer decisions and evidence for each access recertification cycle." },
      { id: "F-099", title: "Continuity exercise completed", auditId: "AUD-022", severity: "Low", owner: "Jamie Wilson", due: localDate(-19), status: "Closed", impact: "Exercise evidence was not centrally linked to the continuity plan.", recommendation: "Store approved exercise results alongside the current continuity plan." }
    ],
    actions: [
      { id: "ACT-208", findingId: "F-101", owner: "Morgan Lee", due: localDate(-2), status: "Not started", update: "Owner has been assigned; remediation approach to be confirmed." },
      { id: "ACT-207", findingId: "F-103", owner: "Taylor Chen", due: localDate(4), status: "In progress", update: "Retention schedule review is underway with Legal." },
      { id: "ACT-206", findingId: "F-104", owner: "Morgan Lee", due: localDate(8), status: "Not started", update: "Design a two-person approval control for supplier changes." },
      { id: "ACT-205", findingId: "F-102", owner: "Casey Patel", due: localDate(18), status: "In progress", update: "Review reminders are being added to the quarterly vendor process." },
      { id: "ACT-204", findingId: "F-100", owner: "Taylor Chen", due: localDate(26), status: "In progress", update: "New evidence checklist drafted for the next recertification." },
      { id: "ACT-203", findingId: "F-099", owner: "Jamie Wilson", due: localDate(-19), status: "Completed", update: "Exercise results added to the continuity plan repository." }
    ],
    risks: [
      { id: "R-015", entity: "Third-party data handling", category: "Technology", owner: "Taylor Chen", likelihood: 4, impact: 5, reviewDate: localDate(-12) },
      { id: "R-014", entity: "Supplier payment fraud", category: "Finance", owner: "Morgan Lee", likelihood: 4, impact: 4, reviewDate: localDate(-22) },
      { id: "R-013", entity: "Regulatory reporting accuracy", category: "Compliance", owner: "Alex Morgan", likelihood: 3, impact: 5, reviewDate: localDate(-34) },
      { id: "R-012", entity: "Critical service disruption", category: "Operations", owner: "Sam Rivera", likelihood: 3, impact: 4, reviewDate: localDate(-47) },
      { id: "R-011", entity: "Payroll processing error", category: "People", owner: "Jamie Wilson", likelihood: 2, impact: 4, reviewDate: localDate(-61) }
    ]
  };

  const state = loadState();
  let lastSavedState = structuredClone(state);
  const pageTitles = {
    dashboard: "Overview",
    audits: "Audit plan",
    findings: "Findings",
    actions: "Action tracking",
    risks: "Risk register",
    settings: "Workspace guide"
  };
  let currentPage = "dashboard";
  let searchQuery = "";
  let currentFilter = "All";

  function loadState() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) return structuredClone(initialData);
      const parsed = JSON.parse(saved);
      if (!parsed || !Array.isArray(parsed.audits) || !Array.isArray(parsed.findings) || !Array.isArray(parsed.actions) || !Array.isArray(parsed.risks)) {
        throw new Error("Saved workspace data has an unexpected format.");
      }
      return parsed;
    } catch (error) {
      console.error("Could not load saved audit workspace data.", error);
      window.setTimeout(() => showToast("Saved data could not be loaded. The demo dataset is shown instead.", true), 0);
      return structuredClone(initialData);
    }
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      lastSavedState = structuredClone(state);
      return true;
    } catch (error) {
      console.error("Could not save audit workspace data.", error);
      Object.keys(state).forEach(key => delete state[key]);
      Object.assign(state, structuredClone(lastSavedState));
      showToast("Changes could not be saved in this browser. Check storage availability.", true);
      return false;
    }
  }

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[character]);
  }

  function initials(name) {
    return String(name || "").split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join("").toUpperCase();
  }

  function prettyDate(value) {
    if (!value) return "—";
    const date = new Date(`${value}T12:00:00`);
    return Number.isNaN(date.getTime()) ? esc(value) : new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(date);
  }

  function dateDelta(value) {
    if (!value) return null;
    const target = new Date(`${value}T00:00:00`);
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    return Math.round((target - now) / 86400000);
  }

  function slug(value) {
    return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }

  function severityPill(value) {
    return `<span class="severity-pill severity-${slug(value)}">${esc(value)}</span>`;
  }

  function riskPill(value) {
    return `<span class="risk-pill risk-${slug(value)}">${esc(value)}</span>`;
  }

  function statusPill(value) {
    return `<span class="status-pill status-${slug(value)}">${esc(value)}</span>`;
  }

  function ownerCell(name) {
    return `<span class="owner-cell"><span class="mini-avatar">${esc(initials(name))}</span>${esc(name || "Unassigned")}</span>`;
  }

  function getAudit(id) {
    return state.audits.find(audit => audit.id === id);
  }

  function getFinding(id) {
    return state.findings.find(finding => finding.id === id);
  }

  function riskScore(risk) {
    return Number(risk.likelihood) * Number(risk.impact);
  }

  function riskRating(risk) {
    const score = riskScore(risk);
    return score >= 20 ? "Critical" : score >= 12 ? "High" : score >= 6 ? "Medium" : "Low";
  }

  function showToast(message, isError = false) {
    const region = document.getElementById("toast-region");
    const toast = document.createElement("div");
    toast.className = `toast${isError ? " error" : ""}`;
    toast.textContent = message;
    region.append(toast);
    window.setTimeout(() => toast.remove(), 3500);
  }

  function setPage(page) {
    if (!pageTitles[page]) return;
    currentPage = page;
    document.querySelectorAll(".page-view").forEach(view => view.classList.toggle("active", view.dataset.view === page));
    document.querySelectorAll(".nav-link").forEach(link => link.classList.toggle("active", link.dataset.page === page));
    document.getElementById("breadcrumb-current").textContent = pageTitles[page];
    document.getElementById("sidebar").classList.remove("open");
    currentFilter = "All";
    render();
  }

  function render() {
    document.getElementById("audit-count").textContent = state.audits.filter(audit => audit.status !== "Complete").length;
    document.getElementById("finding-count").textContent = state.findings.filter(finding => finding.status !== "Closed").length;
    document.getElementById("action-count").textContent = state.actions.filter(action => action.status !== "Completed").length;
    const renderers = {
      dashboard: renderDashboard,
      audits: renderAudits,
      findings: renderFindings,
      actions: renderActions,
      risks: renderRisks,
      settings: renderSettings
    };
    renderers[currentPage]();
  }

  function heading(eyebrow, title, subtitle, actions = "") {
    return `<div class="page-heading"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div><div class="heading-actions">${actions}</div></div>`;
  }

  function visibleRecords(records, terms) {
    if (!searchQuery.trim()) return records;
    const query = searchQuery.trim().toLowerCase();
    return records.filter(record => terms(record).some(value => String(value || "").toLowerCase().includes(query)));
  }

  function renderDashboard() {
    const activeAudits = state.audits.filter(audit => audit.status !== "Complete");
    const openFindings = state.findings.filter(finding => finding.status !== "Closed");
    const overdueActions = state.actions.filter(action => action.status !== "Completed" && dateDelta(action.due) < 0);
    const highRisks = state.risks.filter(risk => riskRating(risk) === "High" || riskRating(risk) === "Critical");
    const progress = activeAudits.length ? Math.round(activeAudits.reduce((total, audit) => total + Number(audit.progress || 0), 0) / activeAudits.length) : 0;
    const audits = visibleRecords(activeAudits, audit => [audit.title, audit.area, audit.owner, audit.lead, audit.status, audit.risk]).slice(0, 4);
    const dueActions = state.actions.filter(action => action.status !== "Completed").sort((a, b) => (a.due || "").localeCompare(b.due || "")).slice(0, 4);
    const severityCounts = ["Critical", "High", "Medium", "Low"].map(severity => [severity, openFindings.filter(finding => finding.severity === severity).length]);
    const maxSeverity = Math.max(1, ...severityCounts.map(([, count]) => count));
    const auditRows = audits.length ? audits.map(audit => `<tr>
      <td>${esc(audit.title)}</td><td>${esc(audit.area)}</td><td>${riskPill(audit.risk)}</td><td>${statusPill(audit.status)}</td><td>${esc(audit.progress)}%</td>
    </tr>`).join("") : `<tr><td colspan="5"><div class="empty-state">No matching audits.</div></td></tr>`;
    const actionRows = dueActions.length ? dueActions.map(action => {
      const finding = getFinding(action.findingId);
      const delta = dateDelta(action.due);
      const dateLabel = delta < 0 ? `${Math.abs(delta)}d overdue` : delta === 0 ? "Due today" : `Due ${prettyDate(action.due)}`;
      return `<div class="due-item"><span class="due-dot${delta < 0 ? " urgent" : ""}"></span><div class="due-copy"><strong>${esc(finding?.title || action.findingId)}</strong><small>${esc(action.owner)} · ${esc(action.id)}</small></div><span class="due-date">${dateLabel}</span></div>`;
    }).join("") : `<div class="empty-state">No open actions to show.</div>`;
    const severityRows = severityCounts.map(([severity, count]) => `<div class="severity-row"><span class="severity-name">${severity}</span><div class="severity-track"><span style="width:${Math.max(3, count / maxSeverity * 100)}%;background:${severity === "Critical" ? "#cb6561" : severity === "High" ? "#d28a55" : severity === "Medium" ? "#d5ad5d" : "#65a38e"}"></span></div><span class="severity-number">${count}</span></div>`).join("");
    const chartMonths = Array.from({ length: 6 }, (_, index) => new Date(today.getFullYear(), today.getMonth() - 5 + index, 1));
    const monthKey = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    const monthlyActivity = chartMonths.map(month => {
      const key = monthKey(month);
      return {
        planned: state.audits.filter(audit => audit.start?.slice(0, 7) === key).length,
        completed: state.audits.filter(audit => audit.status === "Complete" && audit.end?.slice(0, 7) === key).length
      };
    });
    const maxMonthlyActivity = Math.max(1, ...monthlyActivity.flatMap(item => [item.planned, item.completed]));
    const bars = monthlyActivity.map(item => {
      const plannedHeight = Math.max(4, Math.round(item.planned / maxMonthlyActivity * 100));
      const completedHeight = Math.max(4, Math.round(item.completed / maxMonthlyActivity * 100));
      return `<div class="bar-group"><div class="bar" title="${item.planned} planned" style="height:${plannedHeight}%"></div><div class="bar" title="${item.completed} completed" style="height:${completedHeight}%"></div></div>`;
    }).join("");
    const monthLabels = chartMonths.map(month => `<span>${new Intl.DateTimeFormat("en", { month: "short" }).format(month)}</span>`).join("");
    const todayLabel = new Intl.DateTimeFormat("en", { weekday: "long", month: "long", day: "numeric" }).format(today).toUpperCase();
    document.getElementById("view-dashboard").innerHTML = `
      ${heading(todayLabel, "Good morning, Jordan", "Here’s what’s happening across your audit workspace.", `<button class="button button-secondary" data-export="dashboard">↓ Export</button><button class="button button-primary" data-create="audit"><span class="plus">+</span> New engagement</button>`)}
      <div class="stat-grid">
        <article class="stat-card"><div class="stat-top"><span>Active engagements</span><span class="stat-icon teal">▤</span></div><div class="stat-value"><strong>${activeAudits.length}</strong><span class="stat-caption">in current plan</span></div></article>
        <article class="stat-card"><div class="stat-top"><span>Open findings</span><span class="stat-icon blue">◎</span></div><div class="stat-value"><strong>${openFindings.length}</strong><span class="stat-caption">need follow-up</span></div></article>
        <article class="stat-card"><div class="stat-top"><span>Overdue actions</span><span class="stat-icon red">↗</span></div><div class="stat-value"><strong>${overdueActions.length}</strong><span class="stat-caption">require attention</span></div></article>
        <article class="stat-card"><div class="stat-top"><span>High & critical risks</span><span class="stat-icon amber">⌁</span></div><div class="stat-value"><strong>${highRisks.length}</strong><span class="stat-caption">in the risk register</span></div></article>
      </div>
      <div class="dashboard-grid">
        <section class="panel plan-panel"><div class="panel-head"><div><h2>Audit plan progress</h2><div class="panel-subtitle">Engagements currently in your plan</div></div><button class="panel-link" data-page="audits">View plan →</button></div>
          <div class="plan-summary"><div class="progress-track"><span style="width:${progress}%"></span></div><small>${progress}% average progress</small></div>
          <div class="table-wrap"><table class="mini-table"><thead><tr><th>Engagement</th><th>Business area</th><th>Risk</th><th>Status</th><th>Progress</th></tr></thead><tbody>${auditRows}</tbody></table></div>
        </section>
        <section class="panel"><div class="panel-head"><div><h2>Audit activity</h2><div class="panel-subtitle">Engagements over the last 6 months</div></div><button class="panel-link" data-page="audits">Details</button></div>
          <div class="risk-chart"><div class="risk-chart-head"><div><strong>${state.audits.length}</strong><span>total engagements</span></div><span class="stat-change">↑ Plan overview</span></div><div class="chart-bars">${bars}</div><div class="bar-labels">${monthLabels}</div><div class="legend"><span><i></i>Planned</span><span><i></i>Completed</span></div></div>
        </section>
      </div>
      <div class="bottom-grid">
        <section class="panel"><div class="panel-head"><div><h2>Action items</h2><div class="panel-subtitle">Upcoming and overdue management actions</div></div><button class="panel-link" data-page="actions">View all →</button></div><div class="due-list">${actionRows}</div></section>
        <section class="panel"><div class="panel-head"><div><h2>Findings by severity</h2><div class="panel-subtitle">Open findings across all engagements</div></div><button class="panel-link" data-page="findings">View all →</button></div><div class="severity-list">${severityRows}</div></section>
      </div>`;
  }

  function filterToolbar(filters, selectOptions = "") {
    const tabs = filters.map(filter => `<button class="filter-tab${currentFilter === filter ? " active" : ""}" data-filter="${esc(filter)}">${esc(filter)}</button>`).join("");
    return `<div class="toolbar"><div class="filter-tabs">${tabs}</div><div class="filter-controls">${selectOptions}</div></div>`;
  }

  function renderAudits() {
    const audits = visibleRecords(state.audits, audit => [audit.id, audit.title, audit.area, audit.owner, audit.lead, audit.status, audit.risk])
      .filter(audit => currentFilter === "All" || audit.status === currentFilter);
    const rows = audits.map(audit => `<tr>
      <td><div class="primary-cell"><strong>${esc(audit.title)}</strong><small>${esc(audit.id)} · ${esc(audit.area)}</small></div></td>
      <td>${ownerCell(audit.lead)}</td><td>${prettyDate(audit.start)} – ${prettyDate(audit.end)}</td><td>${riskPill(audit.risk)}</td>
      <td><select class="table-select" data-update="audit-status" data-id="${esc(audit.id)}" aria-label="Status for ${esc(audit.title)}">${options(["Planning", "In progress", "Reporting", "Complete"], audit.status)}</select></td>
      <td><span class="cell-emphasis">${esc(audit.progress)}%</span></td><td><button class="row-action" data-delete="audit" data-id="${esc(audit.id)}" aria-label="Delete ${esc(audit.title)}" title="Delete engagement">⋯</button></td>
    </tr>`).join("");
    const statuses = ["All", "Planning", "In progress", "Reporting", "Complete"];
    document.getElementById("view-audits").innerHTML = `
      ${heading("ASSURANCE", "Audit plan", "Plan and track internal audit engagements.", `<button class="button button-secondary" data-export="audits">↓ Export</button><button class="button button-primary" data-create="audit"><span class="plus">+</span> New engagement</button>`)}
      <section class="panel table-card">${filterToolbar(statuses)}<div class="table-wrap"><table class="data-table"><thead><tr><th>Engagement</th><th>Audit lead</th><th>Schedule</th><th>Risk</th><th>Status</th><th>Progress</th><th></th></tr></thead><tbody>${rows || `<tr><td colspan="7"><div class="empty-state"><strong>No engagements found</strong>Try changing your search or filters.</div></td></tr>`}</tbody></table></div><div class="table-foot"><span>Showing ${audits.length} of ${state.audits.length} engagements</span><span>Annual plan · FY 2026</span></div></section>`;
  }

  function renderFindings() {
    const findings = visibleRecords(state.findings, finding => {
      const audit = getAudit(finding.auditId);
      return [finding.id, finding.title, finding.severity, finding.owner, finding.status, audit?.title];
    }).filter(finding => currentFilter === "All" || finding.status === currentFilter);
    const rows = findings.map(finding => `<tr>
      <td><div class="primary-cell"><strong>${esc(finding.title)}</strong><small>${esc(finding.id)} · ${esc(finding.auditId)}</small></div></td>
      <td>${severityPill(finding.severity)}</td><td>${esc(getAudit(finding.auditId)?.title || "Engagement removed")}</td><td>${ownerCell(finding.owner)}</td>
      <td>${prettyDate(finding.due)}</td><td><select class="table-select" data-update="finding-status" data-id="${esc(finding.id)}" aria-label="Status for ${esc(finding.id)}">${options(["Open", "In progress", "Management response", "Closed"], finding.status)}</select></td>
      <td><button class="row-action" data-detail="finding" data-id="${esc(finding.id)}" aria-label="View ${esc(finding.title)}" title="View details">↗</button></td>
    </tr>`).join("");
    document.getElementById("view-findings").innerHTML = `
      ${heading("FIELDWORK", "Findings", "Document observations, recommendations, and management responses.", `<button class="button button-secondary" data-export="findings">↓ Export</button><button class="button button-primary" data-create="finding"><span class="plus">+</span> New finding</button>`)}
      <section class="panel table-card">${filterToolbar(["All", "Open", "In progress", "Management response", "Closed"])}<div class="table-wrap"><table class="data-table"><thead><tr><th>Finding</th><th>Severity</th><th>Engagement</th><th>Owner</th><th>Target date</th><th>Status</th><th></th></tr></thead><tbody>${rows || `<tr><td colspan="7"><div class="empty-state"><strong>No findings found</strong>Try changing your search or filters.</div></td></tr>`}</tbody></table></div><div class="table-foot"><span>Showing ${findings.length} of ${state.findings.length} findings</span><span>Click the arrow to review finding details</span></div></section>`;
  }

  function renderActions() {
    const actions = visibleRecords(state.actions, action => {
      const finding = getFinding(action.findingId);
      return [action.id, action.owner, action.status, action.update, finding?.title, finding?.id];
    }).filter(action => currentFilter === "All" || action.status === currentFilter)
      .sort((a, b) => (a.due || "").localeCompare(b.due || ""));
    const rows = actions.map(action => {
      const finding = getFinding(action.findingId);
      const delta = action.status === "Completed" ? null : dateDelta(action.due);
      return `<tr>
        <td><div class="primary-cell"><strong>${esc(finding?.title || "Finding removed")}</strong><small>${esc(action.id)} · ${esc(action.findingId)}</small></div></td>
        <td>${ownerCell(action.owner)}</td><td>${prettyDate(action.due)}${delta !== null && delta < 0 ? `<div class="due-date" style="color:#c65458;margin-top:4px">${Math.abs(delta)} days overdue</div>` : ""}</td>
        <td><select class="table-select" data-update="action-status" data-id="${esc(action.id)}" aria-label="Status for ${esc(action.id)}">${options(["Not started", "In progress", "Completed"], action.status)}</select></td>
        <td>${esc(action.update || "—")}</td><td><button class="row-action" data-delete="action" data-id="${esc(action.id)}" aria-label="Delete ${esc(action.id)}" title="Delete action">⋯</button></td>
      </tr>`;
    }).join("");
    document.getElementById("view-actions").innerHTML = `
      ${heading("FOLLOW-UP", "Action tracking", "Monitor remediation commitments through to validation and closure.", `<button class="button button-secondary" data-export="actions">↓ Export</button><button class="button button-primary" data-create="action"><span class="plus">+</span> New action</button>`)}
      <section class="panel table-card">${filterToolbar(["All", "Not started", "In progress", "Completed"])}<div class="table-wrap"><table class="data-table"><thead><tr><th>Finding / action</th><th>Owner</th><th>Due date</th><th>Status</th><th>Latest update</th><th></th></tr></thead><tbody>${rows || `<tr><td colspan="6"><div class="empty-state"><strong>No actions found</strong>Try changing your search or filters.</div></td></tr>`}</tbody></table></div><div class="table-foot"><span>Showing ${actions.length} of ${state.actions.length} actions</span><span>Overdue actions are highlighted</span></div></section>`;
  }

  function renderRisks() {
    const risks = visibleRecords(state.risks, risk => [risk.id, risk.entity, risk.category, risk.owner, riskRating(risk)])
      .sort((a, b) => riskScore(b) - riskScore(a));
    const rows = risks.map(risk => {
      const rating = riskRating(risk);
      const scoreClass = rating === "Critical" ? "critical" : rating === "High" ? "high" : "";
      return `<tr><td><div class="primary-cell"><strong>${esc(risk.entity)}</strong><small>${esc(risk.id)} · ${esc(risk.category)}</small></div></td><td>${ownerCell(risk.owner)}</td><td><span class="risk-score ${scoreClass}">${riskScore(risk)}<small style="font:9px 'DM Sans',sans-serif;color:#9aa4ad"> / 25</small></span></td><td>${riskPill(rating)}</td><td>${prettyDate(risk.reviewDate)}</td><td><button class="row-action" data-delete="risk" data-id="${esc(risk.id)}" aria-label="Delete ${esc(risk.entity)}" title="Delete risk">⋯</button></td></tr>`;
    }).join("");
    document.getElementById("view-risks").innerHTML = `
      ${heading("RISK ASSESSMENT", "Risk register", "Maintain your auditable universe and assess inherent risk.", `<button class="button button-secondary" data-export="risks">↓ Export</button><button class="button button-primary" data-create="risk"><span class="plus">+</span> Add risk</button>`)}
      <div class="notice">Risk score is calculated as likelihood × impact (each rated 1–5). Ratings are indicative and should be calibrated to your organization’s approved methodology.</div>
      <section class="panel table-card"><div class="toolbar"><div class="filter-tabs"><span class="filter-tab active" style="cursor:default">${risks.length} auditable risks</span></div><div class="filter-controls"><span class="panel-subtitle">Sorted by inherent score</span></div></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Risk / auditable entity</th><th>Risk owner</th><th>Inherent score</th><th>Rating</th><th>Last reviewed</th><th></th></tr></thead><tbody>${rows || `<tr><td colspan="6"><div class="empty-state"><strong>No risks found</strong>Add a risk or change your search.</div></td></tr>`}</tbody></table></div><div class="table-foot"><span>Showing ${risks.length} of ${state.risks.length} risks</span><span>Inherent risk · 5 × 5 scoring</span></div></section>`;
  }

  function renderSettings() {
    document.getElementById("view-settings").innerHTML = `
      ${heading("ABOUT THIS DEMO", "Workspace guide", "A small, browser-based prototype of an internal audit management workspace.")}
      <div class="notice"><strong>Prototype limitation:</strong> records are saved only in this browser using local storage. This is not a secure, multi-user production system. Do not enter real audit evidence or confidential information.</div>
      <div class="settings-grid">
        <section class="panel settings-card"><h2>What you can do</h2><p>Explore the audit lifecycle from risk assessment through follow-up. Changes remain saved in this browser until you reset the sample data.</p>
          <div class="setting-line"><span>Audit plan</span><span>Create engagements, update status and progress</span></div>
          <div class="setting-line"><span>Findings</span><span>Record severity, impact, recommendation and response</span></div>
          <div class="setting-line"><span>Action tracking</span><span>Assign owners, due dates, updates and status</span></div>
          <div class="setting-line"><span>Risk register</span><span>Score likelihood × impact on a 5 × 5 scale</span></div>
        </section>
        <section class="panel settings-card"><h2>Data and privacy</h2><p>Export your current workspace data as JSON for a local backup. CSV exports are available from each main workspace.</p>
          <div class="setting-line"><span>Storage</span><span>This browser only</span></div>
          <div class="setting-line"><span>Authentication</span><span>Not included in this prototype</span></div>
          <div class="setting-line"><span>Audit log / evidence storage</span><span>Not included in this prototype</span></div>
          <div class="heading-actions" style="padding-top:14px"><button class="button button-secondary" data-export="json">↓ Export workspace JSON</button><button class="button button-danger" data-reset>Reset sample data</button></div>
        </section>
      </div>`;
  }

  function options(values, selected) {
    return values.map(value => `<option value="${esc(value)}"${value === selected ? " selected" : ""}>${esc(value)}</option>`).join("");
  }

  function nextId(records, prefix, width = 3) {
    const numbers = records.map(record => Number(String(record.id).match(/(\d+)$/)?.[1] || 0));
    return `${prefix}${String(Math.max(0, ...numbers) + 1).padStart(width, "0")}`;
  }

  function field(label, name, value = "", type = "text", required = true, extra = "") {
    return `<div class="form-field"><label for="field-${esc(name)}">${esc(label)}${required ? " *" : ""}</label><input id="field-${esc(name)}" name="${esc(name)}" type="${esc(type)}" value="${esc(value)}" ${required ? "required" : ""} ${extra}></div>`;
  }

  function selectField(label, name, values, selected, required = true) {
    return `<div class="form-field"><label for="field-${esc(name)}">${esc(label)}${required ? " *" : ""}</label><select id="field-${esc(name)}" name="${esc(name)}" ${required ? "required" : ""}>${options(values, selected)}</select></div>`;
  }

  function textareaField(label, name, value = "", required = false) {
    return `<div class="form-field full"><label for="field-${esc(name)}">${esc(label)}${required ? " *" : ""}</label><textarea id="field-${esc(name)}" name="${esc(name)}" ${required ? "required" : ""}>${esc(value)}</textarea></div>`;
  }

  function showDialog(title, subtitle, formFields, onSubmit, submitLabel = "Save") {
    const dialog = document.getElementById("form-dialog");
    document.getElementById("dialog-content").innerHTML = `
      <div class="dialog-head"><div><h2 id="dialog-title">${esc(title)}</h2><p>${esc(subtitle)}</p></div><button class="icon-button dialog-close" type="button" aria-label="Close dialog">×</button></div>
      <form class="dialog-form"><div class="form-grid">${formFields}</div><div class="dialog-actions"><button class="button button-secondary" type="button" data-cancel>Cancel</button><button class="button button-primary" type="submit">${esc(submitLabel)}</button></div></form>`;
    const form = dialog.querySelector("form");
    form.addEventListener("submit", event => {
      event.preventDefault();
      const values = Object.fromEntries(new FormData(form).entries());
      if (onSubmit(values) !== false) dialog.close();
    });
    dialog.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
    dialog.querySelector("[data-cancel]").addEventListener("click", () => dialog.close());
    dialog.showModal();
  }

  function createRecord(type) {
    if (type === "audit") {
      showDialog("New engagement", "Add an engagement to the current audit plan.", [
        `<div class="form-field full"><label for="field-title">Engagement name *</label><input id="field-title" name="title" required maxlength="100" placeholder="e.g. Treasury Operations"></div>`,
        field("Business area", "area", "", "text", true, 'maxlength="80"'),
        field("Engagement owner", "owner", "", "text", true, 'maxlength="80"'),
        field("Audit lead", "lead", "Jordan Davis", "text", true, 'maxlength="80"'),
        field("Start date", "start", localDate(7), "date"),
        field("Target end date", "end", localDate(37), "date"),
        field("Progress (%)", "progress", "0", "number", true, 'min="0" max="100" step="1"'),
        selectField("Inherent risk", "risk", ["Critical", "High", "Medium", "Low"], "Medium"),
        selectField("Status", "status", ["Planning", "In progress", "Reporting", "Complete"], "Planning")
      ].join(""), values => {
        if (values.end < values.start) return showToast("Target end date must be on or after the start date.", true), false;
        const progress = Math.max(0, Math.min(100, Number(values.progress)));
        state.audits.unshift({ id: nextId(state.audits, "AUD-", 3), ...values, progress: values.status === "Complete" ? 100 : progress });
        if (!persist()) return false;
        render(); showToast("Engagement added to the audit plan.");
      });
    } else if (type === "finding") {
      if (!state.audits.length) return showToast("Add an engagement before creating a finding.", true);
      showDialog("New finding", "Capture an observation and its recommended remediation.", [
        `<div class="form-field full"><label for="field-title">Finding title *</label><input id="field-title" name="title" required maxlength="140" placeholder="Summarize the control gap"></div>`,
        selectField("Engagement", "auditId", state.audits.map(audit => audit.id), state.audits[0].id),
        selectField("Severity", "severity", ["Critical", "High", "Medium", "Low"], "Medium"),
        field("Finding owner", "owner", "", "text", true, 'maxlength="80"'),
        field("Target date", "due", localDate(30), "date"),
        selectField("Status", "status", ["Open", "In progress", "Management response", "Closed"], "Open"),
        textareaField("Impact / condition", "impact", "", true),
        textareaField("Recommendation", "recommendation", "", true)
      ].join(""), values => {
        const id = nextId(state.findings, "F-", 3);
        state.findings.unshift({ id, ...values });
        if (!state.actions.some(action => action.findingId === id)) {
          state.actions.unshift({ id: nextId(state.actions, "ACT-", 3), findingId: id, owner: values.owner, due: values.due, status: "Not started", update: "Action plan to be agreed." });
        }
        if (!persist()) return false;
        render(); showToast("Finding recorded and a follow-up action created.");
      });
    } else if (type === "action") {
      if (!state.findings.length) return showToast("Add a finding before creating a follow-up action.", true);
      showDialog("New follow-up action", "Assign an owner and due date to a finding.", [
        selectField("Related finding", "findingId", state.findings.map(finding => finding.id), state.findings[0].id),
        field("Action owner", "owner", "", "text", true, 'maxlength="80"'),
        field("Due date", "due", localDate(30), "date"),
        selectField("Status", "status", ["Not started", "In progress", "Completed"], "Not started"),
        textareaField("Latest update", "update", "", false)
      ].join(""), values => {
        state.actions.unshift({ id: nextId(state.actions, "ACT-", 3), ...values });
        if (!persist()) return false;
        render(); showToast("Follow-up action added.");
      });
    } else if (type === "risk") {
      showDialog("Add auditable risk", "Score inherent likelihood and impact on a 1–5 scale.", [
        field("Risk / auditable entity", "entity", "", "text", true, 'maxlength="100"'),
        selectField("Category", "category", ["Finance", "Technology", "Operations", "Compliance", "People", "Strategy"], "Operations"),
        field("Risk owner", "owner", "", "text", true, 'maxlength="80"'),
        selectField("Likelihood", "likelihood", ["1", "2", "3", "4", "5"], "3"),
        selectField("Impact", "impact", ["1", "2", "3", "4", "5"], "3"),
        field("Last reviewed", "reviewDate", localDate(0), "date")
      ].join(""), values => {
        state.risks.unshift({ id: nextId(state.risks, "R-", 3), ...values, likelihood: Number(values.likelihood), impact: Number(values.impact) });
        if (!persist()) return false;
        render(); showToast("Risk added to the register.");
      });
    }
  }

  function showFindingDetail(id) {
    const finding = getFinding(id);
    if (!finding) return;
    const actions = state.actions.filter(action => action.findingId === finding.id);
    const details = `<div class="dialog-head"><div><h2 id="dialog-title">${esc(finding.title)}</h2><p>${esc(finding.id)} · ${esc(getAudit(finding.auditId)?.title || finding.auditId)}</p></div><button class="icon-button dialog-close" type="button" aria-label="Close dialog">×</button></div>
      <div class="dialog-form"><div class="form-grid">
        <div class="form-field"><label>Severity</label><div>${severityPill(finding.severity)}</div></div>
        <div class="form-field"><label>Status</label><div>${statusPill(finding.status)}</div></div>
        <div class="form-field"><label>Owner</label><div class="cell-emphasis">${esc(finding.owner)}</div></div>
        <div class="form-field"><label>Target date</label><div class="cell-emphasis">${prettyDate(finding.due)}</div></div>
        <div class="form-field full"><label>Impact / condition</label><div style="font-size:10px;line-height:1.6;color:#65727e">${esc(finding.impact || "—")}</div></div>
        <div class="form-field full"><label>Recommendation</label><div style="font-size:10px;line-height:1.6;color:#65727e">${esc(finding.recommendation || "—")}</div></div>
        <div class="form-field full"><label>Linked follow-up actions (${actions.length})</label><div style="font-size:10px;line-height:1.8;color:#65727e">${actions.length ? actions.map(action => `${esc(action.id)} · ${esc(action.status)} · ${esc(action.owner)}`).join("<br>") : "No follow-up actions yet."}</div></div>
      </div><div class="dialog-actions"><button class="button button-secondary" type="button" data-cancel>Close</button><button class="button button-primary" type="button" data-create-action>+ Add action</button></div></div>`;
    const dialog = document.getElementById("form-dialog");
    document.getElementById("dialog-content").innerHTML = details;
    dialog.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
    dialog.querySelector("[data-cancel]").addEventListener("click", () => dialog.close());
    dialog.querySelector("[data-create-action]").addEventListener("click", () => {
      dialog.close();
      setPage("actions");
      createRecord("action");
    });
    dialog.showModal();
  }

  function updateStatus(kind, id, value) {
    const groups = {
      "audit-status": ["audits", "status"],
      "finding-status": ["findings", "status"],
      "action-status": ["actions", "status"]
    };
    const [group, key] = groups[kind] || [];
    const record = state[group]?.find(item => item.id === id);
    if (!record) return;
    record[key] = value;
    if (kind === "audit-status" && value === "Complete") record.progress = 100;
    if (kind === "audit-status" && value !== "Complete" && Number(record.progress) === 100) record.progress = 90;
    if (!persist()) { render(); return; }
    render();
    showToast("Status updated.");
  }

  function deleteRecord(type, id) {
    const labels = { audit: "engagement", action: "action", risk: "risk" };
    const listNames = { audit: "audits", action: "actions", risk: "risks" };
    const record = state[listNames[type]]?.find(item => item.id === id);
    if (!record) return;
    if (type === "audit" && state.findings.some(finding => finding.auditId === id)) {
      showToast("This engagement has linked findings. Remove or reassign them before deleting it.", true);
      return;
    }
    if (!window.confirm(`Delete this ${labels[type]}? This cannot be undone.`)) return;
    state[listNames[type]] = state[listNames[type]].filter(item => item.id !== id);
    if (!persist()) { render(); return; }
    render(); showToast(`${labels[type][0].toUpperCase()}${labels[type].slice(1)} deleted.`);
  }

  function csvEscape(value) {
    return `"${String(value ?? "").replace(/"/g, '""')}"`;
  }

  function download(filename, content, mimeType) {
    const link = document.createElement("a");
    const url = URL.createObjectURL(new Blob([content], { type: mimeType }));
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function exportData(type) {
    if (type === "json") {
      download("northstar-audit-workspace.json", JSON.stringify(state, null, 2), "application/json");
      showToast("Workspace JSON exported.");
      return;
    }
    if (type === "dashboard") type = "audits";
    const configs = {
      audits: {
        records: state.audits,
        headers: ["ID", "Engagement", "Business area", "Owner", "Audit lead", "Start date", "End date", "Risk", "Status", "Progress"],
        values: item => [item.id, item.title, item.area, item.owner, item.lead, item.start, item.end, item.risk, item.status, item.progress]
      },
      findings: {
        records: state.findings,
        headers: ["ID", "Finding", "Engagement ID", "Severity", "Owner", "Target date", "Status", "Impact", "Recommendation"],
        values: item => [item.id, item.title, item.auditId, item.severity, item.owner, item.due, item.status, item.impact, item.recommendation]
      },
      actions: {
        records: state.actions,
        headers: ["ID", "Finding ID", "Owner", "Due date", "Status", "Latest update"],
        values: item => [item.id, item.findingId, item.owner, item.due, item.status, item.update]
      },
      risks: {
        records: state.risks,
        headers: ["ID", "Risk / auditable entity", "Category", "Owner", "Likelihood", "Impact", "Score", "Rating", "Last reviewed"],
        values: item => [item.id, item.entity, item.category, item.owner, item.likelihood, item.impact, riskScore(item), riskRating(item), item.reviewDate]
      }
    };
    const config = configs[type];
    if (!config) return;
    const csv = [config.headers, ...config.records.map(config.values)].map(row => row.map(csvEscape).join(",")).join("\r\n");
    download(`northstar-${type}.csv`, `\uFEFF${csv}`, "text/csv;charset=utf-8");
    showToast(`${pageTitles[type] || type} exported as CSV.`);
  }

  document.addEventListener("click", event => {
    const target = event.target.closest("[data-page], [data-create], [data-filter], [data-export], [data-delete], [data-detail], [data-reset]");
    if (!target) return;
    if (target.dataset.page) {
      event.preventDefault();
      setPage(target.dataset.page);
    } else if (target.dataset.create) {
      createRecord(target.dataset.create);
    } else if (target.dataset.filter) {
      currentFilter = target.dataset.filter;
      render();
    } else if (target.dataset.export) {
      exportData(target.dataset.export);
    } else if (target.dataset.delete) {
      deleteRecord(target.dataset.delete, target.dataset.id);
    } else if (target.dataset.detail) {
      showFindingDetail(target.dataset.id);
    } else if (target.hasAttribute("data-reset")) {
      if (!window.confirm("Reset this browser’s workspace to the original sample data? Your current changes will be lost.")) return;
      state.audits = structuredClone(initialData.audits);
      state.findings = structuredClone(initialData.findings);
      state.actions = structuredClone(initialData.actions);
      state.risks = structuredClone(initialData.risks);
      if (!persist()) { render(); return; }
      render(); showToast("Sample data restored.");
    }
  });

  document.addEventListener("change", event => {
    const target = event.target;
    if (target.matches("[data-update]")) updateStatus(target.dataset.update, target.dataset.id, target.value);
  });

  document.getElementById("global-search").addEventListener("input", event => {
    searchQuery = event.target.value;
    render();
  });
  document.getElementById("menu-toggle").addEventListener("click", () => document.getElementById("sidebar").classList.toggle("open"));
  document.addEventListener("keydown", event => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      document.getElementById("global-search").focus();
    }
    if (event.key === "Escape") document.getElementById("sidebar").classList.remove("open");
  });

  render();
})();
