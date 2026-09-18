import { Icon } from "./common";

export function Report({
  reportType,
  setReportType,
  report,
  setReport,
  submitted,
  setSubmitted,
  navigate,
}) {
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
            <b>AMN-2408</b>
          </div>
          <button className="primary" onClick={() => navigate("digest")}>
            See community updates <Icon name="arrow" />
          </button>
          <button
            className="text-button"
            onClick={() => {
              setSubmitted(false);
              setReport("");
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
          onSubmit={(e) => {
            e.preventDefault();
            if (report.trim()) setSubmitted(true);
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
          <label htmlFor="report">Tell us a little more</label>
          <textarea
            id="report"
            value={report}
            onChange={(e) => setReport(e.target.value)}
            placeholder="For example: I heard water will be off all week in Estate B. Is that true?"
            rows="6"
            required
          ></textarea>
          <div className="form-foot">
            <span>You can write in English or Kiswahili.</span>
            <button className="primary" type="submit">
              Send report <Icon name="send" />
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
