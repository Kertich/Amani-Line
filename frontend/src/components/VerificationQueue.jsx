import { useCallback, useEffect, useState } from "react";
import { assignReport, getReportQueue, getReviewers, publishReport } from "../api";
import { Icon } from "./common";

export function VerificationQueue({ navigate, admin = false }) {
  const [reports, setReports] = useState([]);
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
      const items = await getReportQueue();
      setReports(items);
      setAssignments((current) => {
        const next = { ...current };
        for (const item of items) {
          if (!(item.id in next)) {
            next[item.id] = item.assigned_to_email || "";
          }
        }
        return next;
      });
      if (admin) setReviewers(await getReviewers());
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
      {loading ? (
        <p className="form-message" role="status">Loading reports to review...</p>
      ) : error && reports.length === 0 ? null : reports.length === 0 ? (
        <p className="form-message">The verification queue is clear.</p>
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
