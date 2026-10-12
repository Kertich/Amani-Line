import { useCallback, useEffect, useState } from "react";
import {
  assignReport,
  clearReportPii,
  getPiiEscalations,
  getReportQueue,
  getReviewers,
  publishReport,
} from "../api";
import { Icon } from "./common";

export function VerificationQueue({ navigate, admin = false }) {
  const [reports, setReports] = useState([]);
  const [piiEscalations, setPiiEscalations] = useState([]);
  const [redactions, setRedactions] = useState({});
  const [drafts, setDrafts] = useState({});
  const [reviewers, setReviewers] = useState([]);
  const [assignments, setAssignments] = useState({});
  const [loading, setLoading] = useState(true);
  const [publishingId, setPublishingId] = useState("");
  const [assigningId, setAssigningId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [items, reviewerItems, escalatedItems] = await Promise.all([
        getReportQueue(),
        admin ? getReviewers() : Promise.resolve([]),
        admin ? getPiiEscalations() : Promise.resolve([]),
      ]);
      setReports(items);
      setPiiEscalations(escalatedItems);
      setAssignments((current) => {
        const next = { ...current };
        for (const item of items) {
          if (!(item.id in next)) {
            next[item.id] = item.assigned_to_email || "";
          }
        }
        return next;
      });
      if (admin) setReviewers(reviewerItems);
      setDrafts((current) => {
        const next = { ...current };
        for (const item of items) {
          if (!next[item.id]) {
            next[item.id] = {
              status: "confirmed",
              title: "",
              detail: item.description,
              source: "",
            };
          }
        }
        return next;
      });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [admin]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  function updateDraft(reportId, field, value) {
    setDrafts((current) => ({
      ...current,
      [reportId]: { ...current[reportId], [field]: value },
    }));
  }

  async function handlePublish(report) {
    const draft = drafts[report.id];
    if (!draft?.title.trim() || !draft.detail.trim()) return;
    setPublishingId(report.id);
    setError("");
    setMessage("");
    try {
      await publishReport(report.id, {
        status: draft.status,
        title: draft.title.trim(),
        detail: draft.detail.trim(),
        source: draft.source.trim() || null,
      });
      setReports((current) => current.filter((item) => item.id !== report.id));
      setMessage(`${report.reference} was published to community updates.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setPublishingId("");
    }
  }

  async function handleAssign(report) {
    setAssigningId(report.id);
    setError("");
    setMessage("");
    try {
      const updated = await assignReport(
        report.id,
        assignments[report.id] || null,
      );
      setReports((current) =>
        current.map((item) =>
          item.id === report.id
            ? {
                ...item,
                assigned_to_email: updated.assigned_to_email,
                status: updated.status,
              }
            : item,
        ),
      );
      setMessage(
        assignments[report.id]
          ? `${report.reference} assigned to ${assignments[report.id]}.`
          : `${report.reference} returned to the unassigned queue.`,
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setAssigningId("");
    }
  }

  async function handleClearPii(report) {
    const description = redactions[report.id]?.trim();
    if (!description) return;
    setAssigningId(report.id);
    setError("");
    setMessage("");
    try {
      const updated = await clearReportPii(report.id, description);
      setPiiEscalations((current) =>
        current.filter((item) => item.id !== report.id),
      );
      setReports((current) => [...current, updated]);
      setDrafts((current) => ({
        ...current,
        [report.id]: {
          status: "confirmed",
          title: "",
          detail: updated.ai_summary || updated.description,
          source: "",
        },
      }));
      setMessage(
        `${report.reference} was redacted by an administrator and returned for human review.`,
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setAssigningId("");
    }
  }

  return (
    <main className="inner-page">
      <button className="back" onClick={() => navigate("home")}>
        <Icon name="back" /> Back home
      </button>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span></span> {admin ? "ADMIN REPORT MANAGEMENT" : "COMMUNITY VERIFICATION"}
          </div>
          <h1>{admin ? "Assign and review." : "Review reports."}</h1>
          <p>
            {admin
              ? "Assign submissions to authorized reviewers or publish a verified update yourself."
              : "Review reports assigned to your account and publish a clear, sourced update."}
          </p>
        </div>
        <button className="primary" onClick={() => navigate("digest")}>
          Community updates <Icon name="arrow" />
        </button>
      </div>

      {message && <p className="form-message" role="status">{message}</p>}
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {admin && piiEscalations.length > 0 && (
        <section className="pii-escalations" aria-labelledby="pii-escalations-heading">
          <h2 id="pii-escalations-heading">Private safety escalations</h2>
          <p>
            These reports are hidden from the standard reviewer queue and cannot
            be published until an administrator removes identifying details.
          </p>
          <div className="verification-list">
            {piiEscalations.map((report) => (
              <article className="verification-card" key={report.id}>
                <div className="verification-meta">
                  <strong>{report.reference}</strong>
                  <span>Private review required</span>
                  <time dateTime={report.created_at}>
                    {new Date(report.created_at).toLocaleString()}
                  </time>
                </div>
                <p className="reported-description">{report.description}</p>
                <label>
                  Redacted version for human review
                  <textarea
                    value={redactions[report.id] || ""}
                    maxLength={5000}
                    rows={3}
                    onChange={(event) =>
                      setRedactions((current) => ({
                        ...current,
                        [report.id]: event.target.value,
                      }))
                    }
                    placeholder="Remove names, phone numbers, and identifying details"
                    disabled={assigningId === report.id}
                  />
                </label>
                <button
                  className="secondary-button"
                  onClick={() => handleClearPii(report)}
                  disabled={
                    assigningId === report.id ||
                    !redactions[report.id]?.trim()
                  }
                >
                  {assigningId === report.id
                    ? "Saving redaction..."
                    : "Save redaction and return to review"}
                </button>
              </article>
            ))}
          </div>
        </section>
      )}
      {loading ? (
        <p className="form-message" role="status">Loading reports to review...</p>
      ) : error && reports.length === 0 ? null : reports.length === 0 ? (
        piiEscalations.length === 0 && (
          <p className="form-message">The verification queue is clear.</p>
        )
      ) : (
        <div className="verification-list">
          {reports.map((report) => {
            const draft = drafts[report.id] || {};
            const isPublishing = publishingId === report.id;
            const isAssigning = assigningId === report.id;
            return (
              <article className="verification-card" key={report.id}>
                <div className="verification-meta">
                  <strong>{report.reference}</strong>
                  <span>{report.report_type}</span>
                  <time dateTime={report.created_at}>
                    {new Date(report.created_at).toLocaleString()}
                  </time>
                </div>
                <p className="reported-description">{report.description}</p>
                {(report.ai_summary ||
                  report.ai_category ||
                  report.ai_review_required ||
                  report.duplicate_count > 0) && (
                  <aside className="ai-triage" aria-label="AI triage suggestions">
                    <strong>AI assistance — unverified; use your own judgment</strong>
                    <p>
                      Language: {report.ai_language || "unknown"}
                      {report.ai_category &&
                        ` · Suggested category: ${report.ai_category}`}
                      {report.ai_confidence != null &&
                        ` · Confidence: ${Math.round(report.ai_confidence * 100)}%`}
                      {report.ai_dispute_category &&
                        ` · Suggested mediator: ${report.ai_dispute_category}`}
                    </p>
                    {report.ai_summary && (
                      <p><strong>Draft summary:</strong> {report.ai_summary}</p>
                    )}
                    {report.ai_normalized_text &&
                      report.ai_normalized_text !== report.description && (
                        <p>
                          <strong>Normalized text:</strong>{" "}
                          {report.ai_normalized_text}
                        </p>
                      )}
                    {report.ai_review_required && (
                      <p>
                        <strong>Human review required:</strong>{" "}
                        {report.ai_review_reason || "The AI could not classify this reliably."}
                      </p>
                    )}
                    {report.duplicate_count > 0 && (
                      <p>
                        Grouped with {report.duplicate_count} similar report
                        {report.duplicate_count === 1 ? "" : "s"}.
                      </p>
                    )}
                  </aside>
                )}
                {admin && (
                  <div className="report-assignment">
                    <label htmlFor={`assignment-${report.id}`}>
                      Assigned reviewer
                    </label>
                    <div>
                      <select
                        id={`assignment-${report.id}`}
                        value={assignments[report.id] ?? ""}
                        onChange={(event) =>
                          setAssignments((current) => ({
                            ...current,
                            [report.id]: event.target.value,
                          }))
                        }
                        disabled={isAssigning || isPublishing}
                      >
                        <option value="">Unassigned</option>
                        {reviewers.map((reviewer) => (
                          <option key={reviewer.email} value={reviewer.email}>
                            {reviewer.email}
                          </option>
                        ))}
                      </select>
                      <button
                        className="secondary-button"
                        onClick={() => handleAssign(report)}
                        disabled={
                          isAssigning ||
                          isPublishing ||
                          (assignments[report.id] || "") ===
                            (report.assigned_to_email || "")
                        }
                      >
                        {isAssigning ? "Saving..." : "Save assignment"}
                      </button>
                    </div>
                  </div>
                )}
                <div className="verification-fields">
                  <label>
                    Finding
                    <select
                      value={draft.status || "confirmed"}
                      onChange={(event) =>
                        updateDraft(report.id, "status", event.target.value)
                      }
                      disabled={isPublishing}
                    >
                      <option value="confirmed">Confirmed</option>
                      <option value="false">False</option>
                    </select>
                  </label>
                  <label>
                    Update title
                    <input
                      value={draft.title || ""}
                      maxLength={500}
                      onChange={(event) =>
                        updateDraft(report.id, "title", event.target.value)
                      }
                      placeholder="A clear headline for the community"
                      required
                      disabled={isPublishing}
                    />
                  </label>
                  <label>
                    Published detail
                    <textarea
                      value={draft.detail || ""}
                      maxLength={5000}
                      onChange={(event) =>
                        updateDraft(report.id, "detail", event.target.value)
                      }
                      rows={4}
                      required
                      disabled={isPublishing}
                    />
                  </label>
                  <label>
                    Source (optional)
                    <input
                      value={draft.source || ""}
                      maxLength={2000}
                      onChange={(event) =>
                        updateDraft(report.id, "source", event.target.value)
                      }
                      placeholder="Where this finding was verified"
                      disabled={isPublishing}
                    />
                  </label>
                </div>
                <button
                  className="primary"
                  onClick={() => handlePublish(report)}
                  disabled={
                    isPublishing ||
                    !draft.title?.trim() ||
                    !draft.detail?.trim()
                  }
                >
                  {isPublishing ? "Publishing..." : "Publish update"}
                  {!isPublishing && <Icon name="send" />}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </main>
  );
}
