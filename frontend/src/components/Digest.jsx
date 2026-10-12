import { useEffect, useState } from "react";
import { Icon, StatusPill } from "./common";
import { getUpdates } from "../api";

const filters = [
  { label: "All updates", value: "" },
  { label: "Confirmed", value: "confirmed" },
  { label: "Under review", value: "pending" },
  { label: "False", value: "false" },
];

const emptyMessages = {
  "": "There are no community updates yet. Reports will appear here after they have been reviewed.",
  confirmed: "There are no confirmed updates yet. Check back after local reports have been verified.",
  pending: "There are no updates currently marked as under review.",
  false: "There are no corrections to share at the moment.",
};

function formatUpdateTime(value) {
  const createdAt = new Date(value);
  if (Number.isNaN(createdAt.getTime())) return "";
  const minutes = Math.round((createdAt.getTime() - Date.now()) / 60000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (Math.abs(minutes) < 60) return `Updated ${formatter.format(minutes, "minute")}`;
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return `Updated ${formatter.format(hours, "hour")}`;
  return `Updated ${formatter.format(Math.round(hours / 24), "day")}`;
}

export function Digest({ navigate }) {
  const [filter, setFilter] = useState("");
  const [updates, setUpdates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
                {item.status === "confirmed" ? "✓" : item.status === "false" ? "×" : "◷"}
              </div>
              <div className="update-main">
                <div className="update-top">
                  <StatusPill status={item.status} />
                  <span>{formatUpdateTime(item.created_at)}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.detail}</p>
                {item.source && (
                  <div className="source">Source: {item.source}</div>
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
