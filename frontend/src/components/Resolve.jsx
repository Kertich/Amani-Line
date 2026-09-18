import { useState } from "react";
import { Icon } from "./common";

export function Resolve({ navigate }) {
  const [step, setStep] = useState(1);
  const [done, setDone] = useState(false);
  if (done)
    return (
      <main className="form-page">
        <button className="back" onClick={() => navigate("home")}>
          <Icon name="back" /> Back home
        </button>
        <section className="success">
          <div className="success-mark">✓</div>
          <div className="eyebrow">
            <span></span> REQUEST RECEIVED
          </div>
          <h1>A respectful next step is on its way.</h1>
          <p>
            A local resolution contact will review your request privately and
            get back to you with a suitable path.
          </p>
          <button className="primary" onClick={() => navigate("home")}>
            Return home <Icon name="arrow" />
          </button>
        </section>
      </main>
    );
  return (
    <main className="form-page">
      <button className="back" onClick={() => navigate("home")}>
        <Icon name="back" /> Back home
      </button>
      <section className="form-wrap resolve-wrap">
        <div className="form-intro">
          <div className="eyebrow">
            <span></span> RESOLVE A DISPUTE
          </div>
          <h1>Start with respect.</h1>
          <p>
            We will help connect your concern to the right local path —
            privately and fairly.
          </p>
          <div className="progress">
            <span className={step >= 1 ? "filled" : ""}></span>
            <span className={step >= 2 ? "filled" : ""}></span>
            <span className={step >= 3 ? "filled" : ""}></span>
          </div>
          <small>Step {step} of 3</small>
        </div>
        <div className="resolve-form">
          {step === 1 && (
            <>
              <label>What is the concern about?</label>
              <div className="select-list">
                <button>
                  Land or boundary <b>›</b>
                </button>
                <button>
                  Home or tenancy <b>›</b>
                </button>
                <button>
                  Noise or neighbour concern <b>›</b>
                </button>
                <button>
                  Something else <b>›</b>
                </button>
              </div>
            </>
          )}
          {step === 2 && (
            <>
              <label>What outcome would help?</label>
              <textarea
                placeholder="Describe the outcome you hope for..."
                rows="6"
              ></textarea>
            </>
          )}
          {step === 3 && (
            <>
              <label>How should a local resolver reach you?</label>
              <input placeholder="Phone number (optional)" />
              <p className="privacy-inline">
                ⌑ Your details stay private and are only used to follow up on
                this request.
              </p>
            </>
          )}
          <div className="form-foot">
            <button
              className="text-button"
              onClick={() =>
                step === 1 ? navigate("home") : setStep(step - 1)
              }
            >
              {step === 1 ? "Cancel" : "Back"}
            </button>
            <button
              className="primary"
              onClick={() => (step === 3 ? setDone(true) : setStep(step + 1))}
            >
              {step === 3 ? "Send request" : "Continue"} <Icon name="arrow" />
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
