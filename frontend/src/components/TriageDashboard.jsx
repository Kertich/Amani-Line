import { useCallback, useEffect, useState } from "react";
import {
  assignReport,
  approveUpdate,
  getPendingUpdates,
  getQueueReviewers,
  getReportEvents,
  getReportQueue,
  getReviewers,
  publishReport,
  rejectUpdate,
  triageReport,
} from "../api";
import { Icon } from "./common";

const copy = {
  en: {
    title: "Triage reports.",
    subtitle: "Prioritize, route, and review reports for your authorized scope.",
    alerts: "Urgent and overdue",
    emptyUrgent: "No urgent or overdue reports.",
    filters: "Filters",
    search: "Search reference or description",
    status: "Status",
    type: "Type",
    ward: "Ward",
    channel: "Channel",
    priority: "Priority",
    all: "All",
    apply: "Apply",
    report: "Report",
    age: "SLA age",
    view: "Open details",
    noReports: "No reports match these filters.",
    previous: "Previous",
    next: "Next",
    of: "of",
    details: "Report details",
    close: "Close",
    channelLabel: "Channel",
    priorityLabel: "Priority",
    sla: "SLA age",
    overdue: "Overdue",
    duplicates: "Possible duplicates · assistive only",
    noDuplicates: "No possible duplicates found.",
    timeline: "Timeline",
    loadingTimeline: "Loading timeline...",
    noTimeline: "No events recorded yet.",
    resident: "Resident",
    assigned: "Assigned reviewer",
    unassigned: "Unassigned",
    saveAssignment: "Save assignment",
    triage: "Triage",
    notes: "Triage notes",
    notesPlaceholder: "Add a concise internal note",
    saveTriage: "Save triage",
    requestInfo: "Request more information",
    dismissReason: "Dismissal reason (required)",
    dismiss: "Dismiss report",
    finding: "Finding",
    confirmed: "Confirmed",
    false: "False",
    updateTitle: "Update title",
    detail: "Published detail",
    source: "Source",
    verificationMethod: "Verification method",
    officialNotice: "Official notice",
    firstHandWitness: "First-hand witness",
    multipleSources: "Multiple community sources",
    evidenceUrl: "Evidence link (or add a note)",
    evidenceNote: "Evidence note (or add a link)",
    publish: "Submit update",
    approve: "Approve",
    reject: "Reject",
    rejectionReason: "Reason for rejection (required)",
    pendingApproval: "Updates awaiting approval",
    noPendingApprovals: "No updates are awaiting approval.",
    directPublish: "Publish directly",
    submittedForApproval: "Update submitted for independent approval.",
    publishedDirectly: "Update published and logged as an administrator action.",
    saving: "Saving...",
    publishing: "Publishing...",
    statuses: {
      pending: "Pending",
      reviewing: "Reviewing",
      needs_info: "Needs information",
      resolved: "Resolved",
      dismissed: "Dismissed",
    },
    priorities: { low: "Low", normal: "Normal", urgent: "Urgent" },
    channels: { web: "Web", ussd: "USSD", sms: "SMS" },
    reportTypes: {
      "Rumour to check": "Rumour to check",
      "Local issue": "Local issue",
      "Safety concern": "Safety concern",
    },
    actions: {
      created: "Report received",
      assigned: "Assigned",
      unassigned: "Unassigned",
      triage: "Triage updated",
      request_more_info: "More information requested",
      dismiss: "Dismissed",
      published: "Published",
      reviewer_access_revoked: "Reviewer access revoked",
      pii_redacted: "Sensitive details redacted",
      routed: "Routed",
      status_changed: "Status changed",
      note_added: "Note added",
    },
    success: "Report updated.",
  },
  sw: {
    title: "Panga ripoti.",
    subtitle: "Panga kipaumbele na ukague ripoti zilizoidhinishwa kwako.",
    alerts: "Dharura na zilizochelewa",
    emptyUrgent: "Hakuna ripoti ya dharura au iliyochelewa.",
    filters: "Vichujio",
    search: "Tafuta nambari au maelezo",
    status: "Hali",
    type: "Aina",
    ward: "Kata",
    channel: "Njia",
    priority: "Kipaumbele",
    all: "Zote",
    apply: "Tumia",
    report: "Ripoti",
    age: "Muda wa SLA",
    view: "Fungua maelezo",
    noReports: "Hakuna ripoti zinazolingana na vichujio.",
    previous: "Iliyotangulia",
    next: "Inayofuata",
    of: "kati ya",
    details: "Maelezo ya ripoti",
    close: "Funga",
    channelLabel: "Njia",
    priorityLabel: "Kipaumbele",
    sla: "Muda wa SLA",
    overdue: "Imechelewa",
    duplicates: "Huenda zimerudiwa · pendekezo tu",
    noDuplicates: "Hakuna ripoti zinazofanana zilizopatikana.",
    timeline: "Historia",
    loadingTimeline: "Inapakia historia...",
    noTimeline: "Hakuna matukio yaliyorekodiwa.",
    resident: "Mwananchi",
    assigned: "Mkaguzi aliyepangiwa",
    unassigned: "Haijapangiwa",
    saveAssignment: "Hifadhi mpango",
    triage: "Tathmini",
    notes: "Maelezo ya tathmini",
    notesPlaceholder: "Ongeza dokezo fupi la ndani",
    saveTriage: "Hifadhi tathmini",
    requestInfo: "Omba maelezo zaidi",
    dismissReason: "Sababu ya kufunga (inahitajika)",
    dismiss: "Funga ripoti",
    finding: "Matokeo",
    confirmed: "Imethibitishwa",
    false: "Si kweli",
    updateTitle: "Kichwa cha taarifa",
    detail: "Maelezo yatakayochapishwa",
    source: "Chanzo",
    verificationMethod: "Njia ya uthibitishaji",
    officialNotice: "Tangazo rasmi",
    firstHandWitness: "Shahidi wa moja kwa moja",
    multipleSources: "Vyanzo vingi vya jamii",
    evidenceUrl: "Kiungo cha ushahidi (au ongeza dokezo)",
    evidenceNote: "Dokezo la ushahidi (au ongeza kiungo)",
    publish: "Wasilisha taarifa",
    approve: "Idhinisha",
    reject: "Kataa",
    rejectionReason: "Sababu ya kukataa (inahitajika)",
    pendingApproval: "Taarifa zinazosubiri idhini",
    noPendingApprovals: "Hakuna taarifa zinazosubiri idhini.",
    directPublish: "Chapisha moja kwa moja",
    submittedForApproval: "Taarifa imewasilishwa kwa idhini huru.",
    publishedDirectly: "Taarifa imechapishwa na kurekodiwa kama hatua ya msimamizi.",
    saving: "Inahifadhi...",
    publishing: "Inachapisha...",
    statuses: {
      pending: "Inasubiri",
      reviewing: "Inakaguliwa",
      needs_info: "Inahitaji maelezo",
      resolved: "Imetatuliwa",
      dismissed: "Imefungwa",
    },
    priorities: { low: "Chini", normal: "Kawaida", urgent: "Dharura" },
    channels: { web: "Tovuti", ussd: "USSD", sms: "SMS" },
    reportTypes: {
      "Rumour to check": "Uvumi wa kuhakiki",
      "Local issue": "Tatizo la eneo",
      "Safety concern": "Hatari ya usalama",
    },
    actions: {
      created: "Ripoti imepokelewa",
      assigned: "Imepangiwa",
      unassigned: "Haijapangiwa",
      triage: "Tathmini imesasishwa",
      request_more_info: "Maelezo zaidi yameombwa",
      dismiss: "Imefungwa",
      published: "Imechapishwa",
      reviewer_access_revoked: "Ruhusa ya mkaguzi imeondolewa",
      pii_redacted: "Taarifa nyeti zimefichwa",
      routed: "Imeelekezwa",
      status_changed: "Hali imebadilishwa",
      note_added: "Dokezo limeongezwa",
    },
    success: "Ripoti imesasishwa.",
  },
};

const statuses = ["pending", "reviewing", "needs_info", "resolved", "dismissed"];

function ageLabel(hours) {
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d ${Math.round(hours % 24)}h`;
}

export function TriageDashboard({
  navigate,
  admin,
  canManageQueue,
  ward,
  language = "en",
}) {
  const t = copy[language] || copy.en;
  const [reports, setReports] = useState([]);
  const [urgentReports, setUrgentReports] = useState([]);
  const [counts, setCounts] = useState({});
  const [reviewers, setReviewers] = useState([]);
  const [filters, setFilters] = useState({
    search: "",
    status: "",
    type: "",
    ward: "",
    channel: "",
    priority: "",
  });
  const [searchDraft, setSearchDraft] = useState("");
  const [wardDraft, setWardDraft] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [priority, setPriority] = useState("normal");
  const [reportWard, setReportWard] = useState("");
  const [notes, setNotes] = useState("");
  const [reason, setReason] = useState("");
  const [assignee, setAssignee] = useState("");
  const [finding, setFinding] = useState("confirmed");
  const [title, setTitle] = useState("");
  const [detail, setDetail] = useState("");
  const [source, setSource] = useState("");
  const [verificationMethod, setVerificationMethod] = useState("official_notice");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [pendingUpdates, setPendingUpdates] = useState([]);
  const [pendingError, setPendingError] = useState("");
  const [rejectionReasons, setRejectionReasons] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await getReportQueue({
        ...filters,
        page: String(page),
        page_size: String(pageSize),
      });
      setReports(response.items);
      setUrgentReports(response.urgent_or_overdue);
      setCounts(response.counts);
      setTotal(response.total);
      if (canManageQueue) {
        setReviewers(admin ? await getReviewers() : await getQueueReviewers());
      } else {
        setReviewers([]);
      }
      setSelectedReport((current) =>
        current
          ? response.items.find((item) => item.id === current.id) ||
            response.urgent_or_overdue.find((item) => item.id === current.id) ||
            current
          : null,
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [admin, canManageQueue, filters, page, pageSize]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  useEffect(() => {
    let active = true;
    if (!canManageQueue) return undefined;
    getPendingUpdates()
      .then((items) => {
        if (active) setPendingUpdates(items);
      })
      .catch((requestError) => {
        if (active) setPendingError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, [canManageQueue]);

  useEffect(() => {
    if (!selectedReport) return;
    setPriority(selectedReport.priority || "normal");
    setReportWard(selectedReport.ward || ward || "");
    setNotes(selectedReport.triage_notes || "");
    setAssignee(selectedReport.assigned_to_email || "");
    setTitle(selectedReport.ai_summary || "");
    setDetail(selectedReport.description || "");
    setReason("");
    setFinding("confirmed");
    setVerificationMethod("official_notice");
    setEvidenceUrl("");
    setEvidenceNote("");
  }, [selectedReport?.id, ward]);

  useEffect(() => {
    let active = true;
    if (!selectedReport) {
      setTimeline([]);
      return () => {
        active = false;
      };
    }
    setTimelineLoading(true);
    getReportEvents(selectedReport.id)
      .then((events) => {
        if (active) setTimeline(events);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setTimelineLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedReport?.id]);

  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
    setPage(1);
  }

  async function refreshAfterAction(successMessage) {
    setMessage(successMessage);
    await loadQueue();
    if (selectedReport) {
      setTimeline(await getReportEvents(selectedReport.id));
    }
  }

  async function handleTriage(action) {
    if (!selectedReport) return;
    if (action === "dismiss" && !reason.trim()) {
      setError(t.dismissReason);
      return;
    }
    if (action === "request_more_info" && !notes.trim()) {
      setError(t.notes);
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await triageReport(selectedReport.id, {
        action,
        priority,
        ward: reportWard || null,
        notes: notes.trim() || null,
        reason: action === "dismiss" ? reason.trim() : null,
      });
      setSelectedReport((current) => ({ ...current, ...updated }));
      await refreshAfterAction(t.success);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAssignment() {
    if (!selectedReport) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await assignReport(selectedReport.id, assignee);
      await refreshAfterAction(t.success);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function handlePublish() {
    if (!selectedReport || !title.trim() || !detail.trim()) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await publishReport(selectedReport.id, {
        status: finding,
        title: title.trim(),
        detail: detail.trim(),
        source: source.trim(),
        verification_method: verificationMethod,
        evidence_url: evidenceUrl.trim() || null,
        evidence_note: evidenceNote.trim() || null,
      });
      setSelectedReport(null);
      setMessage(result.workflow_status === "published" ? t.publishedDirectly : t.submittedForApproval);
      await loadQueue();
      // Refresh the approval list so a newly submitted draft appears
      if (canManageQueue) setPendingUpdates(await getPendingUpdates());
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleApproval(updateId, action) {
    const reasonText = rejectionReasons[updateId]?.trim();
    if (action === "reject" && !reasonText) {
      setError(t.rejectionReason);
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (action === "approve") {
        await approveUpdate(updateId);
      } else {
        await rejectUpdate(updateId, reasonText);
      }
      setPendingUpdates((current) =>
        current.filter((item) => item.id !== updateId),
      );
      setMessage(t.success);
      await loadQueue();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  function openReport(report) {
    setError("");
    setSelectedReport(report);
  }

  const formatStatus = (status) => t.statuses[status] || status;
  const tableReports = reports;

  return (
    <section className="triage-dashboard" aria-label={t.title}>
      <header className="triage-heading">
        <div>
          <div className="eyebrow"><span></span>{admin ? "ADMIN TRIAGE" : "COMMUNITY VERIFICATION"}</div>
          <h1>{t.title}</h1>
          <p>{ward ? `${ward} · ` : ""}{t.subtitle}</p>
        </div>
        <button className="secondary-button" onClick={() => navigate("digest")}>
          {language === "sw" ? "Taarifa za jamii" : "Community updates"} <Icon name="arrow" />
        </button>
      </header>

      {message && <p className="form-message" role="status">{message}</p>}
      {error && <p className="form-message error-message" role="alert">{error}</p>}

      {canManageQueue && (
        <section className="approval-queue" aria-labelledby="approval-queue-heading">
          <h2 id="approval-queue-heading">{t.pendingApproval}</h2>
          {pendingError && <p className="form-message error-message" role="alert">{pendingError}</p>}
          {pendingUpdates.length === 0 ? (
            <p>{t.noPendingApprovals}</p>
          ) : pendingUpdates.map((item) => (
            <article className="approval-item" key={item.id}>
              <div>
                <span className={`pill ${item.status}`}>
                  {item.status === "confirmed" ? t.confirmed : t.false}
                </span>
                <h3>{item.title}</h3>
                <p>{item.detail}</p>
                <small>{item.author_label} · {item.source || "—"} · {item.verification_method}</small>
                {item.evidence_url && <p><a href={item.evidence_url} target="_blank" rel="noreferrer">Evidence link</a></p>}
                {item.evidence_note && <p>{item.evidence_note}</p>}
              </div>
              <div className="approval-actions">
                <button
                  className="primary"
                  disabled={busy || item.authored_by_you}
                  onClick={() => handleApproval(item.id, "approve")}
                >
                  {item.authored_by_you ? `${t.approve} · author` : t.approve}
                </button>
                <label>
                  {t.rejectionReason}
                  <textarea
                    value={rejectionReasons[item.id] || ""}
                    maxLength={2000}
                    rows={2}
                    onChange={(event) => setRejectionReasons((current) => ({
                      ...current,
                      [item.id]: event.target.value,
                    }))}
                    disabled={busy}
                  />
                </label>
                <button
                  className="danger-button"
                  disabled={busy || !rejectionReasons[item.id]?.trim()}
                  onClick={() => handleApproval(item.id, "reject")}
                >
                  {t.reject}
                </button>
              </div>
            </article>
          ))}
        </section>
      )}

      <section className="triage-summary" aria-label={t.status}>
        {statuses.map((status) => (
          <button
            className={`triage-count ${filters.status === status ? "selected" : ""}`}
            key={status}
            onClick={() => updateFilter("status", filters.status === status ? "" : status)}
          >
            <strong>{counts[status] || 0}</strong>
            <span>{formatStatus(status)}</span>
          </button>
        ))}
      </section>

      <section className="urgent-panel">
        <h2>{t.alerts}</h2>
        {urgentReports.length === 0 ? (
          <p>{t.emptyUrgent}</p>
        ) : (
          <ul>
            {urgentReports.map((report) => (
              <li key={report.id}>
                <button onClick={() => openReport(report)}>
                  <span className="priority-badge urgent">
                    {t.priorities[report.priority] || report.priority}
                  </span>
                  <strong>{report.reference}</strong>
                  <span>{report.ward || "—"}</span>
                  <span>{ageLabel(report.sla_age_hours)}</span>
                  {report.sla_overdue && <span className="overdue-badge">{t.overdue}</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <form
        className="triage-filters"
        onSubmit={(event) => {
          event.preventDefault();
          setFilters((current) => ({
            ...current,
            search: searchDraft,
            ward: wardDraft,
          }));
          setPage(1);
        }}
      >
        <h2>{t.filters}</h2>
        <label>
          <span>{t.search}</span>
          <input
            type="search"
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder={t.search}
          />
        </label>
        <label>
          <span>{t.status}</span>
          <select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}>
            <option value="">{t.all}</option>
            {statuses.map((status) => <option key={status} value={status}>{formatStatus(status)}</option>)}
          </select>
        </label>
        <label>
          <span>{t.type}</span>
          <select value={filters.type} onChange={(event) => updateFilter("type", event.target.value)}>
            <option value="">{t.all}</option>
            {Object.entries(t.reportTypes).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        {admin && (
          <label>
            <span>{t.ward}</span>
            <input
              value={wardDraft}
              maxLength={120}
              onChange={(event) => setWardDraft(event.target.value)}
            />
          </label>
        )}
        <label>
          <span>{t.channel}</span>
          <select value={filters.channel} onChange={(event) => updateFilter("channel", event.target.value)}>
            <option value="">{t.all}</option>
            {Object.entries(t.channels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label>
          <span>{t.priority}</span>
          <select value={filters.priority} onChange={(event) => updateFilter("priority", event.target.value)}>
            <option value="">{t.all}</option>
            {Object.entries(t.priorities).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <button className="secondary-button" type="submit">{t.apply}</button>
      </form>

      {loading ? (
        <p className="form-message" role="status">{language === "sw" ? "Inapakia ripoti..." : "Loading reports..."}</p>
      ) : tableReports.length === 0 ? (
        <p className="form-message">{t.noReports}</p>
      ) : (
        <>
          <div className="triage-table-wrap">
            <table className="triage-table">
              <thead>
                <tr>
                  <th>{t.report}</th>
                  <th>{t.status}</th>
                  <th>{t.ward}</th>
                  <th>{t.channel}</th>
                  <th>{t.priority}</th>
                  <th>{t.age}</th>
                </tr>
              </thead>
              <tbody>
                {tableReports.map((report) => (
                  <tr key={report.id} onClick={() => openReport(report)} tabIndex={0}
                    onKeyDown={(event) => event.key === "Enter" && openReport(report)}>
                    <td>
                      <strong>{report.reference}</strong>
                      <small>{t.reportTypes[report.report_type] || report.report_type}</small>
                    </td>
                    <td>{formatStatus(report.status)}</td>
                    <td>{report.ward || "—"}</td>
                    <td><span className="channel-badge">{t.channels[report.channel] || report.channel}</span></td>
                    <td><span className={`priority-badge ${report.priority}`}>{t.priorities[report.priority] || report.priority}</span></td>
                    <td>
                      {ageLabel(report.sla_age_hours)}
                      {report.sla_overdue && <span className="overdue-badge">{t.overdue}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <nav className="triage-pagination" aria-label="Report pages">
            <span>{total} {language === "sw" ? "ripoti" : "reports"} · {page} {t.of} {pageCount}</span>
            <div>
              <button className="secondary-button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>{t.previous}</button>
              <button className="secondary-button" disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>{t.next}</button>
            </div>
          </nav>
        </>
      )}

      {selectedReport && (
        <div className="triage-drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setSelectedReport(null)}>
          <aside className="triage-drawer" role="dialog" aria-modal="true" aria-labelledby="report-detail-heading">
            <header>
              <div>
                <div className="eyebrow"><span></span>{selectedReport.reference}</div>
                <h2 id="report-detail-heading">{t.details}</h2>
              </div>
              <button className="text-button" onClick={() => setSelectedReport(null)}>{t.close}</button>
            </header>
            <div className="triage-drawer-content">
              <div className="triage-report-tags">
                <span className="channel-badge">{t.channels[selectedReport.channel] || selectedReport.channel}</span>
                <span className={`priority-badge ${selectedReport.priority}`}>{t.priorities[selectedReport.priority] || selectedReport.priority}</span>
                <span>{formatStatus(selectedReport.status)}</span>
                <span>{selectedReport.ward || "—"}</span>
                <span>{t.sla}: {ageLabel(selectedReport.sla_age_hours)}</span>
                {selectedReport.sla_overdue && <span className="overdue-badge">{t.overdue}</span>}
              </div>
              <h3>{t.reportTypes[selectedReport.report_type] || selectedReport.report_type}</h3>
              <p className="reported-description">{selectedReport.description}</p>
              {selectedReport.ai_summary && <aside className="ai-triage"><strong>AI draft · verify independently</strong><p>{selectedReport.ai_summary}</p></aside>}

              <section className="duplicate-panel">
                <h3>{t.duplicates}</h3>
                {selectedReport.possible_duplicates?.length ? (
                  <ul>
                    {selectedReport.possible_duplicates.map((duplicate) => (
                      <li key={duplicate.id}>
                        <strong>{duplicate.reference}</strong> · {duplicate.ward}
                        <p>{duplicate.description}</p>
                      </li>
                    ))}
                  </ul>
                ) : <p>{t.noDuplicates}</p>}
              </section>

              <section className="timeline-panel">
                <h3>{t.timeline}</h3>
                {timelineLoading ? <p>{t.loadingTimeline}</p> : timeline.length === 0 ? <p>{t.noTimeline}</p> : (
                  <ol>
                    {timeline.map((event, index) => (
                      <li key={`${event.created_at}-${index}`}>
                        <strong>{t.actions[event.action] || event.action}</strong>
                        <span>{event.from_status ? `${formatStatus(event.from_status)} → ` : ""}{formatStatus(event.to_status || "")}</span>
                        {event.note && <p>{event.note}</p>}
                        <small>{event.actor_email || t.resident} · {new Date(event.created_at).toLocaleString(language === "sw" ? "sw-KE" : "en-KE")}</small>
                      </li>
                    ))}
                  </ol>
                )}
              </section>

              {canManageQueue && (
                <section className="drawer-action-panel">
                  <h3>{t.assigned}</h3>
                  <div className="drawer-inline-action">
                    <select value={assignee} onChange={(event) => setAssignee(event.target.value)} disabled={busy}>
                      <option value="">{t.unassigned}</option>
                      {reviewers.map((reviewer) => (
                        <option key={reviewer.email} value={reviewer.email}>
                          {reviewer.display_name || reviewer.email}
                        </option>
                      ))}
                    </select>
                    <button className="secondary-button" disabled={busy || assignee === (selectedReport.assigned_to_email || "")} onClick={handleAssignment}>{t.saveAssignment}</button>
                  </div>
                </section>
              )}

              {["pending", "reviewing", "needs_info"].includes(selectedReport.status) && (
                <>
                  <section className="drawer-action-panel">
                    <h3>{t.triage}</h3>
                    <label>{t.priority}
                      <select value={priority} onChange={(event) => setPriority(event.target.value)} disabled={busy}>
                        {Object.entries(t.priorities).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                      </select>
                    </label>
                    {admin && (
                      <label>{t.ward}
                        <input value={reportWard} maxLength={120} onChange={(event) => setReportWard(event.target.value)} disabled={busy} />
                      </label>
                    )}
                    <label>{t.notes}
                      <textarea value={notes} maxLength={2000} rows={3} placeholder={t.notesPlaceholder} onChange={(event) => setNotes(event.target.value)} disabled={busy} />
                    </label>
                    <div className="drawer-action-buttons">
                      <button className="secondary-button" disabled={busy} onClick={() => handleTriage("triage")}>{busy ? t.saving : t.saveTriage}</button>
                      <button className="secondary-button" disabled={busy || !notes.trim()} onClick={() => handleTriage("request_more_info")}>{t.requestInfo}</button>
                    </div>
                    <label>{t.dismissReason}
                      <textarea value={reason} maxLength={2000} rows={2} onChange={(event) => setReason(event.target.value)} disabled={busy} />
                    </label>
                    <button className="danger-button" disabled={busy || !reason.trim()} onClick={() => handleTriage("dismiss")}>{t.dismiss}</button>
                  </section>

                  <section className="drawer-action-panel">
                    <h3>{t.publish}</h3>
                    <label>{t.finding}
                      <select value={finding} onChange={(event) => setFinding(event.target.value)} disabled={busy}>
                        <option value="confirmed">{t.confirmed}</option>
                        <option value="false">{t.false}</option>
                      </select>
                    </label>
                    <label>{t.updateTitle}
                      <input value={title} maxLength={500} onChange={(event) => setTitle(event.target.value)} disabled={busy} />
                    </label>
                    <label>{t.detail}
                      <textarea value={detail} maxLength={5000} rows={4} onChange={(event) => setDetail(event.target.value)} disabled={busy} />
                    </label>
                    <label>{t.source}
                      <input value={source} maxLength={2000} onChange={(event) => setSource(event.target.value)} disabled={busy} required />
                    </label>
                    <label>{t.verificationMethod}
                      <select value={verificationMethod} onChange={(event) => setVerificationMethod(event.target.value)} disabled={busy}>
                        <option value="official_notice">{t.officialNotice}</option>
                        <option value="first_hand_witness">{t.firstHandWitness}</option>
                        <option value="multiple_community_sources">{t.multipleSources}</option>
                      </select>
                    </label>
                    <label>{t.evidenceUrl}
                      <input type="url" value={evidenceUrl} maxLength={2000} onChange={(event) => setEvidenceUrl(event.target.value)} disabled={busy} />
                    </label>
                    <label>{t.evidenceNote}
                      <textarea value={evidenceNote} maxLength={2000} rows={2} onChange={(event) => setEvidenceNote(event.target.value)} disabled={busy} />
                    </label>
                    <button
                      className="primary"
                      disabled={busy || !title.trim() || !detail.trim() || !source.trim() || (!evidenceUrl.trim() && !evidenceNote.trim())}
                      onClick={handlePublish}
                    >
                      {busy ? t.publishing : admin ? t.directPublish : t.publish}<Icon name="send" />
                    </button>
                  </section>
                </>
              )}
            </div>
          </aside>
        </div>
      )}
    </section>
  );
}
