import { useCallback, useEffect, useState } from "react";
import { clearReportPii, getPiiEscalations } from "../api";
import { TriageDashboard } from "./TriageDashboard";
import { Icon } from "./common";

const piiCopy = {
  en: {
    title: "Private safety escalations",
    description: "These reports are hidden from the queue and cannot be published until identifying details are removed.",
    redacted: "Redacted version for human review",
    placeholder: "Remove names, phone numbers, and identifying details",
    save: "Save redaction and return to review",
    saving: "Saving redaction...",
    loading: "Loading private escalations...",
    none: "No private escalations.",
  },
  sw: {
    title: "Ripoti za faragha",
    description: "Ripoti hizi zimefichwa hadi taarifa zinazomtambulisha mtu ziondolewe.",
    redacted: "Toleo lililofichwa kwa ukaguzi wa binadamu",
    placeholder: "Ondoa majina, nambari za simu na taarifa binafsi",
    save: "Hifadhi na urudishe kwenye ukaguzi",
    saving: "Inahifadhi...",
    loading: "Inapakia ripoti za faragha...",
    none: "Hakuna ripoti za faragha.",
  },
};

export function VerificationQueue({
  navigate,
  admin = false,
  canManageQueue = false,
  ward = "",
  language = "en",
}) {
  const t = piiCopy[language] || piiCopy.en;
  const [escalations, setEscalations] = useState([]);
  const [redactions, setRedactions] = useState({});
  const [loading, setLoading] = useState(Boolean(admin));
  const [savingId, setSavingId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadEscalations = useCallback(async () => {
    if (!admin) return;
    setLoading(true);
    setError("");
    try {
      setEscalations(await getPiiEscalations());
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [admin]);

  useEffect(() => {
    loadEscalations();
  }, [loadEscalations]);

  async function handleRedaction(report) {
    const description = redactions[report.id]?.trim();
    if (!description) return;
    setSavingId(report.id);
    setError("");
    setMessage("");
    try {
      await clearReportPii(report.id, description);
      setEscalations((current) => current.filter((item) => item.id !== report.id));
      setMessage(language === "sw"
        ? `${report.reference} imefichwa na kurejeshwa kwa ukaguzi.`
        : `${report.reference} was redacted and returned for human review.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingId("");
    }
  }

  return (
    <main className="inner-page">
      <button className="back" onClick={() => navigate("home")}>
        <Icon name="back" /> {language === "sw" ? "Rudi mwanzo" : "Back home"}
      </button>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {message && <p className="form-message" role="status">{message}</p>}
      {admin && (
        <section className="pii-escalations" aria-labelledby="pii-escalations-heading">
          <h2 id="pii-escalations-heading">{t.title}</h2>
          <p>{t.description}</p>
          {loading ? <p className="form-message" role="status">{t.loading}</p> : escalations.length === 0 ? (
            <p className="form-message">{t.none}</p>
          ) : (
            <div className="verification-list">
              {escalations.map((report) => (
                <article className="verification-card" key={report.id}>
                  <div className="verification-meta">
                    <strong>{report.reference}</strong>
                    <time dateTime={report.created_at}>{new Date(report.created_at).toLocaleString()}</time>
                  </div>
                  <p className="reported-description">{report.description}</p>
                  <label>
                    {t.redacted}
                    <textarea
                      value={redactions[report.id] || ""}
                      maxLength={5000}
                      rows={3}
                      onChange={(event) => setRedactions((current) => ({
                        ...current,
                        [report.id]: event.target.value,
                      }))}
                      placeholder={t.placeholder}
                      disabled={savingId === report.id}
                    />
                  </label>
                  <button
                    className="secondary-button"
                    onClick={() => handleRedaction(report)}
                    disabled={savingId === report.id || !redactions[report.id]?.trim()}
                  >
                    {savingId === report.id ? t.saving : t.save}
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
      <TriageDashboard
        navigate={navigate}
        admin={admin}
        canManageQueue={canManageQueue}
        ward={ward}
        language={language}
      />
    </main>
  );
}
