import { useCallback, useEffect, useState } from "react";
import { addReviewer, getReviewers, removeReviewer } from "../api";
import { Icon } from "./common";

const labels = {
  en: {
    eyebrow: "ACCESS MANAGEMENT",
    title: "Authorize reviewers.",
    intro: "Reviewers sign in with this email. A ward limits their queue and permissions to that ward.",
    email: "Reviewer email address",
    displayName: "Display name",
    ward: "Ward scope (optional)",
    authorizing: "Authorizing...",
    authorize: "Authorize reviewer",
    authorized: "Authorized accounts",
    loading: "Loading authorized reviewers...",
    none: "No reviewers have been authorized yet.",
    bootstrap: "Bootstrap access · managed in backend configuration",
    scoped: "Ward-scoped manager",
    assigned: "Can review reports assigned to this email",
    remove: "Revoke access",
    removing: "Removing...",
  },
  sw: {
    eyebrow: "USIMAMIZI WA UFIKIAJI",
    title: "Idhinisha wakaguzi.",
    intro: "Wakaguzi huingia kwa barua pepe hii. Weka kata ili kupunguza ripoti na ruhusa kwa kata hiyo.",
    email: "Barua pepe ya mkaguzi",
    displayName: "Jina la kuonyesha",
    ward: "Kata (si lazima)",
    authorizing: "Inaidhinisha...",
    authorize: "Idhinisha mkaguzi",
    authorized: "Akaunti zilizoidhinishwa",
    loading: "Inapakia wakaguzi...",
    none: "Hakuna wakaguzi walioidhinishwa bado.",
    bootstrap: "Ufikiaji wa awali · dhibiti katika usanidi wa backend",
    scoped: "Msimamizi wa kata",
    assigned: "Anaweza kukagua ripoti alizopangiwa",
    remove: "Ondoa ruhusa",
    removing: "Inaondoa...",
  },
};

export function ReviewerAdmin({ language = "en" }) {
  const t = labels[language] || labels.en;
  const [reviewers, setReviewers] = useState([]);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [ward, setWard] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [removingEmail, setRemovingEmail] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadReviewers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setReviewers(await getReviewers());
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReviewers();
  }, [loadReviewers]);

  async function handleAdd(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const reviewer = await addReviewer(email.trim(), displayName.trim(), ward.trim());
      setReviewers((current) => [
        ...current.filter((item) => item.email !== reviewer.email),
        reviewer,
      ].sort((first, second) => first.email.localeCompare(second.email)));
      setEmail("");
      setDisplayName("");
      setWard("");
      setMessage(`${reviewer.email} is now authorized to review assigned reports.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove(reviewer) {
    setRemovingEmail(reviewer.email);
    setError("");
    setMessage("");
    try {
      await removeReviewer(reviewer.email);
      setReviewers((current) =>
        current.filter((item) => item.email !== reviewer.email),
      );
      setMessage(`${reviewer.email} has been removed from reviewer access.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setRemovingEmail("");
    }
  }

  return (
    <section className="admin-panel">
      <div className="admin-panel-heading">
        <div>
          <div className="eyebrow"><span></span> {t.eyebrow}</div>
          <h2>{t.title}</h2>
          <p>{t.intro}</p>
        </div>
      </div>

      <form className="reviewer-form" onSubmit={handleAdd}>
        <label htmlFor="reviewer-email">{t.email}</label>
        <div>
          <input
            id="reviewer-email"
            type="email"
            autoComplete="email"
            required
            maxLength={320}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="reviewer@example.org"
            disabled={saving}
          />
        </div>
        <div className="reviewer-scope-fields">
          <label>
            {t.displayName}
            <input
              type="text"
              maxLength={120}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              disabled={saving}
            />
          </label>
          <label>
            {t.ward}
            <input
              type="text"
              maxLength={120}
              value={ward}
              onChange={(event) => setWard(event.target.value)}
              disabled={saving}
            />
          </label>
        </div>
        <div>
          <button className="primary" disabled={saving || !email.trim()}>
            {saving ? t.authorizing : t.authorize}
            {!saving && <Icon name="arrow" />}
          </button>
        </div>
      </form>

      {message && <p className="form-message" role="status">{message}</p>}
      {error && <p className="form-message error-message" role="alert">{error}</p>}

      <div className="reviewer-list-heading">
        <strong>{t.authorized}</strong>
        {!loading && <span>{reviewers.length}</span>}
      </div>
      {loading ? (
        <p className="form-message" role="status">{t.loading}</p>
      ) : error && reviewers.length === 0 ? null : reviewers.length === 0 ? (
        <p className="form-message">{t.none}</p>
      ) : (
        <ul className="reviewer-list">
          {reviewers.map((reviewer) => (
            <li key={reviewer.email}>
              <span>
                <strong>{reviewer.email}</strong>
                <small>
                  {reviewer.is_bootstrap
                    ? t.bootstrap
                    : reviewer.ward
                      ? `${reviewer.display_name || reviewer.email} · ${t.scoped}: ${reviewer.ward}`
                      : t.assigned}
                </small>
              </span>
              {reviewer.is_bootstrap ? (
                <span className="reviewer-tag">Configured</span>
              ) : (
                <button
                  className="text-button reviewer-remove"
                  onClick={() => handleRemove(reviewer)}
                  disabled={Boolean(removingEmail)}
                >
                  {removingEmail === reviewer.email ? t.removing : t.remove}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
