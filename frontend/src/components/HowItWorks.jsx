import { Icon } from "./common";

export function HowItWorks({ navigate }) {
  return (
    <main className="inner-page how-page">
      <button className="back" onClick={() => navigate("home")}>
        <Icon name="back" /> Back home
      </button>
      <div className="center-heading">
        <div className="eyebrow">
          <span></span> SIMPLE BY DESIGN
        </div>
        <h1>From a question to clarity.</h1>
        <p>
          Amani Line helps communities respond early, with care and reliable
          local context.
        </p>
      </div>
      <div className="steps">
        <div>
          <b>01</b>
          <span className="step-icon">↗</span>
          <h3>Report</h3>
          <p>Share a rumour, concern or dispute in a few clear words.</p>
        </div>
        <div>
          <b>02</b>
          <span className="step-icon">✓</span>
          <h3>Verify</h3>
          <p>We check with official sources and trusted local verifiers.</p>
        </div>
        <div>
          <b>03</b>
          <span className="step-icon">⌁</span>
          <h3>Resolve</h3>
          <p>Get a clear next step or begin a respectful mediation path.</p>
        </div>
      </div>
      <div className="how-cta">
        <h2>Ready to get clarity?</h2>
        <button className="primary" onClick={() => navigate("report")}>
          Report something <Icon name="arrow" />
        </button>
      </div>
    </main>
  );
}
