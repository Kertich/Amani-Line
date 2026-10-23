import { useState } from "react";
import { Icon } from "./common";
import { createReport } from "../api";

export function Report({
  reportType,
  setReportType,
  report,
  setReport,
  submitted,
  setSubmitted,
  reference,
  setReference,
  navigate,
  language = "en",
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [ward, setWard] = useState("");
  const copy =
    language === "sw"
      ? {
          ward: "Kata",
          wardPlaceholder: "Kwa mfano, Mlolongo",
          wardHelp: "Tumia jina sawa na lililowekwa kwa wakaguzi wa kata yako.",
        }
      : {
          ward: "Your ward",
          wardPlaceholder: "For example, Mlolongo",
          wardHelp: "Use the same ward name set for your local reviewers.",
        };

  if (submitted)
    return (
      <main className="form-page">
        <button className="back" onClick={() => navigate("home")}>
          <Icon name="back" /> Back home
        </button>
        <section className="success">
          <div className="success-mark">✓</div>
          <div className="eyebrow">
            <span></span> REPORT RECEIVED
          </div>
          <h1>Thank you for speaking up.</h1>
          <p>
            Your report is now pending review. A local verifier will check it
            and we will update this page when there is more to share.
          </p>
          <div className="reference">
            <span>Your reference</span>
            <b>{reference}</b>
          </div>
          <button className="primary" onClick={() => navigate("digest")}>
            See community updates <Icon name="arrow" />
          </button>
          <button
            className="text-button"
            onClick={() => {
              setSubmitted(false);
              setReport("");
              setWard("");
              setReference("");
              setError("");
            }}
          >
            Send another report
          </button>
        </section>
      </main>
    );
  return (
    <main className="form-page">
      <button className="back" onClick={() => navigate("home")}>
        <Icon name="back" /> Back home
      </button>
      <section className="form-wrap">
        <div className="form-intro">
          <div className="eyebrow">
            <span></span> REPORT SOMETHING
          </div>
          <h1>Let’s look into it.</h1>
          <p>
            Tell us what you heard or noticed. Your name will not be shared
            publicly.
          </p>
          <div className="safe-note">
            <span>⌑</span>
            <div>
              <b>Private by default</b>
              <small>
                We only share your report with the people who can help verify
                it.
              </small>
            </div>
          </div>
        </div>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (!report.trim()) return;
            setLoading(true);
            setError("");
            try {
              const result = await createReport({
                report_type: reportType,
                description: report.trim(),
                ward: ward.trim(),
              });
              setReference(result.reference);
              setSubmitted(true);
            } catch (requestError) {
              setError(requestError.message);
            } finally {
              setLoading(false);
            }
          }}
        >
          <label>What would you like to report?</label>
          <div className="type-options">
            {["Rumour to check", "Local issue", "Safety concern"].map(
              (type) => (
                <button
                  type="button"
                  className={reportType === type ? "selected" : ""}
                  onClick={() => setReportType(type)}
                  key={type}
                >
                  {type}
                </button>
              ),
            )}
          </div>
          <label htmlFor="ward">{copy.ward}</label>
          <input
            id="ward"
            type="text"
            maxLength={120}
            value={ward}
            onChange={(e) => setWard(e.target.value)}
            placeholder={copy.wardPlaceholder}
            required
          />
          <small className="field-hint">{copy.wardHelp}</small>
          <label htmlFor="report">Tell us a little more</label>
          <textarea
            id="report"
            maxLength={5000}
            value={report}
            onChange={(e) => setReport(e.target.value)}
            placeholder="For example: I heard water will be off all week in Estate B. Is that true?"
            rows="6"
            required
          ></textarea>
          {error && (
            <p className="form-message error-message" role="alert">
              {error}
            </p>
          )}
          <div className="form-foot">
            <span>You can write in English or Kiswahili.</span>
            <button className="primary" type="submit" disabled={loading}>
              {loading ? "Sending..." : "Send report"} {!loading && <Icon name="send" />}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
