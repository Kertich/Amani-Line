import { useState } from "react";
import { Icon } from "./common";
import { signIn, signUp } from "../api";

export function Auth({ onSuccess, onCancel, verification = false }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const response =
        mode === "login"
          ? await signIn({ email, password })
          : await signUp({ email, password });
      if (!response.session?.access_token) {
        setMessage(
          "Account created. Check your email to confirm it, then sign in to continue.",
        );
        setMode("login");
        return;
      }
      onSuccess(response.session, response.user);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="form-page">
      <button className="back" onClick={onCancel}>
        <Icon name="back" /> Back
      </button>
      <section className="success auth-wrap">
        <div className="eyebrow">
          <span></span>{" "}
          {verification ? "VERIFIER SIGN IN" : "YOUR AMANI LINE ACCOUNT"}
        </div>
        <h1>{mode === "login" ? "Welcome back." : "Create an account."}</h1>
        <p>
          {verification
            ? "Sign in with an approved community verifier account to review reported rumours, issues, and concerns."
            : "Sign in to send a private dispute resolution request."}
        </p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label htmlFor="auth-email">Email address</label>
          <input
            id="auth-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <label htmlFor="auth-password">Password</label>
          <input
            id="auth-password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error && (
            <p className="form-message error-message" role="alert">
              {error}
            </p>
          )}
          {message && (
            <p className="form-message" role="status">
              {message}
            </p>
          )}
          <button className="primary auth-submit" disabled={loading}>
            {loading
              ? "Please wait..."
              : mode === "login"
                ? "Sign in"
                : "Create account"}
            {!loading && <Icon name="arrow" />}
          </button>
        </form>
        {!verification && (
          <button
            className="text-button auth-toggle"
            onClick={() => {
              setMode(mode === "login" ? "signup" : "login");
              setError("");
              setMessage("");
            }}
          >
            {mode === "login"
              ? "New to Amani Line? Create an account"
              : "Already have an account? Sign in"}
          </button>
        )}
      </section>
    </main>
  );
}
