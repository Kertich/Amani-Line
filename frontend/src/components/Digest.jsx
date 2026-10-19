import { useEffect, useState } from "react";
import { Icon, StatusPill } from "./common";
import { correctUpdate, getUpdates } from "../api";

const filters = [
  { label: "All updates", value: "" },
  { label: "Confirmed", value: "confirmed" },
  { label: "False", value: "false" },
  { label: "Corrections & retractions", value: "corrections" },
];

const emptyMessages = {
  "": "There are no community updates yet. Reports will appear here after they have been reviewed.",
  confirmed: "There are no confirmed updates yet. Check back after local reports have been verified.",
  false: "There are no updates marked false.",
  corrections: "There are no corrected or retracted updates.",
};

function formatUpdateTime(value) {
  const createdAt = new Date(value);
  if (Number.isNaN(createdAt.getTime())) return "";
  return new Intl.DateTimeFormat("en-KE", {
    dateStyle: "medium",
    timeZone: "Africa/Nairobi",
  }).format(createdAt);
}

export function Digest({ navigate, canModerateUpdates = false }) {
  const [filter, setFilter] = useState("");
  const [updates, setUpdates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [moderationDrafts, setModerationDrafts] = useState({});
  const [savingUpdate, setSavingUpdate] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    getUpdates(filter)
      .then((items) => {
        if (active) setUpdates(items);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filter]);

  async function handleCorrection(item) {
    const draft = moderationDrafts[item.id] || {};
    if (!draft.reason?.trim()) return;
    setSavingUpdate(item.id);
    setError("");
    try {
      await correctUpdate(item.id, draft.action || "correct", draft.reason.trim());
      setUpdates(await getUpdates(filter));
      setModerationDrafts((current) => ({ ...current, [item.id]: { ...draft, reason: "" } }));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingUpdate("");
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
            <span></span> MLolongo community digest
          </div>
          <h1>Updates you can trust.</h1>
          <p>
            Browse local reports by review status, with the finding and source
            shared in one place.
          </p>
        </div>
        <button className="primary" onClick={() => navigate("report")}>
          Report an update <Icon name="arrow" />
        </button>
      </div>
      <div className="digest-toolbar">
        <strong>Browse by status</strong>
        {!loading && !error && (
          <span aria-live="polite">
            {updates.length} {updates.length === 1 ? "update" : "updates"}
          </span>
        )}
      </div>
      <div className="filter-row" role="group" aria-label="Filter updates by status">
        {filters.map((item) => (
          <button
            className={`filter${filter === item.value ? " active" : ""}`}
            key={item.label}
            aria-pressed={filter === item.value}
            onClick={() => setFilter(item.value)}
          >
            {item.label}
          </button>
        ))}
        <span className="location">
          <Icon name="map" /> Mlolongo, Machakos
        </span>
      </div>
      <div className="update-list">
        {loading ? (
          <p className="form-message" role="status">Loading community updates...</p>
        ) : error ? (
          <p className="form-message error-message" role="alert">{error}</p>
        ) : updates.length === 0 ? (
          <p className="form-message">
            {emptyMessages[filter]}
          </p>
        ) : (
          updates.map((item) => (
            <article className="update-card" key={item.id}>
              <div className="update-icon" aria-hidden="true">
                {item.workflow_status === "retracted"
                  ? "!"
                  : item.workflow_status === "corrected"
                    ? "↻"
                    : item.status === "confirmed" ? "✓" : "×"}
              </div>
              <div className="update-main">
                <div className="update-top">
                  <StatusPill status={item.status} />
                  <span>{formatUpdateTime(item.published_at)}</span>
                </div>
                {["corrected", "retracted"].includes(item.workflow_status) && (
                  <aside className={`correction-banner ${item.workflow_status}`} role="status">
                    <strong>
                      {item.workflow_status === "retracted" ? "RETRACTED UPDATE" : "CORRECTION"}
                    </strong>
                    {item.correction_reason && <p>{item.correction_reason}</p>}
                    {item.correction_history?.length > 1 && (
                      <details>
                        <summary>Correction history</summary>
                        <ol>
                          {item.correction_history.map((event, index) => (
                            <li key={`${event.created_at}-${index}`}>
                              <strong>{event.action}</strong>
                              {event.reason && <span> — {event.reason}</span>}
                              <small>{event.actor_label} · {formatUpdateTime(event.created_at)}</small>
                            </li>
                          ))}
                        </ol>
                      </details>
                    )}
                  </aside>
                )}
                <h3>{item.title}</h3>
                <p>{item.detail}</p>
                <div className="source">
                  Source: {item.source || "Not listed"}
                </div>
                <div className="source">{item.publisher_label}</div>
                {canModerateUpdates && ["published", "corrected"].includes(item.workflow_status) && (
                  <div className="correction-controls">
                    <label>
                      Record a correction or retraction
                      <select
                        value={moderationDrafts[item.id]?.action || "correct"}
                        onChange={(event) => setModerationDrafts((current) => ({
                          ...current,
                          [item.id]: { ...current[item.id], action: event.target.value },
                        }))}
                        disabled={savingUpdate === item.id}
                      >
                        <option value="correct">Correct</option>
                        <option value="retract">Retract</option>
                      </select>
                    </label>
                    <textarea
                      value={moderationDrafts[item.id]?.reason || ""}
                      maxLength={2000}
                      rows={2}
                      placeholder="Reason required; the original remains visible"
                      onChange={(event) => setModerationDrafts((current) => ({
                        ...current,
                        [item.id]: { ...current[item.id], reason: event.target.value },
                      }))}
                      disabled={savingUpdate === item.id}
                    />
                    <button
                      className="danger-button"
                      disabled={savingUpdate === item.id || !moderationDrafts[item.id]?.reason?.trim()}
                      onClick={() => handleCorrection(item)}
                    >
                      {savingUpdate === item.id ? "Saving..." : "Record correction"}
                    </button>
                  </div>
                )}
              </div>
            </article>
          ))
        )}
      </div>
      <div className="digest-cta">
        <span className="cta-mark">✦</span>
        <div>
          <h3>Heard something you are unsure about?</h3>
          <p>
            Send it to Amani Line. We will check it with the right local
            sources.
          </p>
        </div>
        <button className="primary" onClick={() => navigate("report")}>
          Report something <Icon name="arrow" />
        </button>
      </div>
    </main>
  );
}
