import { useCallback, useEffect, useState } from "react";
import { addReviewer, getReviewers, removeReviewer } from "../api";
import { Icon } from "./common";

export function ReviewerAdmin() {
  const [reviewers, setReviewers] = useState([]);
  const [email, setEmail] = useState("");
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
      const reviewer = await addReviewer(email.trim());
      setReviewers((current) => [
        ...current.filter((item) => item.email !== reviewer.email),
        reviewer,
      ].sort((first, second) => first.email.localeCompare(second.email)));
      setEmail("");
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
          <div className="eyebrow"><span></span> ACCESS MANAGEMENT</div>
          <h2>Authorize reviewers.</h2>
          <p>
            Reviewers must sign in with this email address. They can open only
            reports you assign to them.
          </p>
        </div>
      </div>

      <form className="reviewer-form" onSubmit={handleAdd}>
        <label htmlFor="reviewer-email">Reviewer email address</label>
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
          <button className="primary" disabled={saving || !email.trim()}>
            {saving ? "Authorizing..." : "Authorize reviewer"}
            {!saving && <Icon name="arrow" />}
          </button>
        </div>
      </form>

      {message && <p className="form-message" role="status">{message}</p>}
      {error && <p className="form-message error-message" role="alert">{error}</p>}

      <div className="reviewer-list-heading">
        <strong>Authorized accounts</strong>
        {!loading && <span>{reviewers.length}</span>}
      </div>
      {loading ? (
        <p className="form-message" role="status">Loading authorized reviewers...</p>
      ) : error && reviewers.length === 0 ? null : reviewers.length === 0 ? (
        <p className="form-message">No reviewers have been authorized yet.</p>
      ) : (
        <ul className="reviewer-list">
          {reviewers.map((reviewer) => (
            <li key={reviewer.email}>
              <span>
                <strong>{reviewer.email}</strong>
                <small>
                  {reviewer.is_bootstrap
                    ? "Bootstrap access · managed in backend configuration"
                    : "Can review reports assigned to this email"}
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
                  {removingEmail === reviewer.email ? "Removing..." : "Revoke access"}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
