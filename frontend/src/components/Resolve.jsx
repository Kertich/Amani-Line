import { useState } from "react";
import { createDispute } from "../api";
import { Icon } from "./common";

const concernTypes = [
  "Land or boundary",
  "Home or tenancy",
  "Noise or neighbour concern",
  "Something else",
];

export function Resolve({ navigate, token }) {
  const [step, setStep] = useState(1);
  const [done, setDone] = useState(false);
  const [concernType, setConcernType] = useState("");
  const [desiredOutcome, setDesiredOutcome] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submitRequest() {
    setLoading(true);
    setError("");
    try {
      await createDispute(
        {
          concern_type: concernType,
          desired_outcome: desiredOutcome.trim(),
          contact_phone: contactPhone.trim() || null,
        },
        token,
      );
      setDone(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

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
                {concernTypes.map((type) => (
                  <button
                    type="button"
                    className={concernType === type ? "selected" : ""}
                    onClick={() => {
                      setConcernType(type);
                      setError("");
                      setStep(2);
                    }}
                    key={type}
                  >
                    {type} <b>›</b>
                  </button>
                ))}
              </div>
            </>
          )}
          {step === 2 && (
            <>
              <label htmlFor="desired-outcome">What outcome would help?</label>
              <textarea
                id="desired-outcome"
                value={desiredOutcome}
                onChange={(event) => setDesiredOutcome(event.target.value)}
                placeholder="Describe the outcome you hope for..."
                maxLength={5000}
                rows="6"
                required
              ></textarea>
            </>
          )}
          {step === 3 && (
            <>
              <label htmlFor="contact-phone">
                How should a local resolver reach you?
              </label>
              <input
                id="contact-phone"
                type="tel"
                autoComplete="tel"
                maxLength={40}
                value={contactPhone}
                onChange={(event) => setContactPhone(event.target.value)}
                placeholder="Phone number (optional)"
              />
              <p className="privacy-inline">
                ⌑ Your details stay private and are only used to follow up on
                this request.
              </p>
            </>
          )}
          {error && (
            <p className="form-message error-message" role="alert">
              {error}
            </p>
          )}
          <div className="form-foot">
            <button
              className="text-button"
              onClick={() =>
                step === 1 ? navigate("home") : setStep(step - 1)
              }
              disabled={loading}
            >
              {step === 1 ? "Cancel" : "Back"}
            </button>
            <button
              className="primary"
              onClick={() =>
                step === 3 ? submitRequest() : setStep(step + 1)
              }
              disabled={
                loading || (step === 2 && !desiredOutcome.trim())
              }
            >
              {loading
                ? "Sending..."
                : step === 3
                  ? "Send request"
                  : "Continue"}
              {!loading && <Icon name="arrow" />}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
