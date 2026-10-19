import { useEffect, useState } from "react";
import { copy } from "./components/data";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { Home } from "./components/Home";
import { Digest } from "./components/Digest";
import { Icon } from "./components/common";
import { HowItWorks } from "./components/HowItWorks";
import { Report } from "./components/Report";
import { Resolve } from "./components/Resolve";
import { Auth } from "./components/Auth";
import { VerificationQueue } from "./components/VerificationQueue";
import { ReviewerAdmin } from "./components/ReviewerAdmin";
import { getCurrentUser } from "./api";

function App() {
  const [language, setLanguage] = useState("en");
  const [view, setView] = useState("home");
  const [menu, setMenu] = useState(false);
  const [reportType, setReportType] = useState("Rumour to check");
  const [submitted, setSubmitted] = useState(false);
  const [report, setReport] = useState("");
  const [reportReference, setReportReference] = useState("");
  const [session, setSession] = useState(() => {
    const accessToken = window.localStorage.getItem("amani-access-token");
    return accessToken ? { access_token: accessToken } : null;
  });
  const [user, setUser] = useState(null);
  const [canVerify, setCanVerify] = useState(false);
  const [canAdmin, setCanAdmin] = useState(false);
  const [canManageQueue, setCanManageQueue] = useState(false);
  const [reviewerWard, setReviewerWard] = useState("");
  const [authChecked, setAuthChecked] = useState(false);
  const t = copy[language];

  useEffect(() => {
    let active = true;
    if (!session?.access_token) {
      setUser(null);
      setCanVerify(false);
      setCanAdmin(false);
      setCanManageQueue(false);
      setReviewerWard("");
      setAuthChecked(true);
      return () => {
        active = false;
      };
    }

    getCurrentUser(session.access_token)
      .then((response) => {
        if (active) {
          setUser(response.user);
          setCanVerify(response.can_verify);
          setCanAdmin(response.can_admin);
          setCanManageQueue(response.can_manage_queue);
          setReviewerWard(response.ward || "");
        }
      })
      .catch((error) => {
        if (!active) return;
        if (error.status === 401) {
          window.localStorage.removeItem("amani-access-token");
          setSession(null);
        }
        setUser(null);
        setCanVerify(false);
        setCanAdmin(false);
        setCanManageQueue(false);
        setReviewerWard("");
      })
      .finally(() => {
        if (active) setAuthChecked(true);
      });

    return () => {
      active = false;
    };
  }, [session?.access_token]);

  const navigate = (next) => {
    if (next === "resolve" && authChecked && !session?.access_token) {
      setView("auth");
      setMenu(false);
      return;
    }
    if (next === "report") {
      setSubmitted(false);
      setReport("");
      setReportReference("");
    }
    setView(next);
    setMenu(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleAuthSuccess = (nextSession, nextUser, nextView = "resolve") => {
    window.localStorage.setItem(
      "amani-access-token",
      nextSession.access_token,
    );
    setSession(nextSession);
    setUser(nextUser);
    setCanVerify(false);
    setCanAdmin(false);
    setCanManageQueue(false);
    setReviewerWard("");
    setAuthChecked(false);
    setView(nextView);
  };

  const signOut = () => {
    window.localStorage.removeItem("amani-access-token");
    setSession(null);
    setUser(null);
    setCanVerify(false);
    setCanAdmin(false);
    setCanManageQueue(false);
    setReviewerWard("");
    setView("home");
  };

  return (
    <div className="app-shell">
      <Header
        t={t}
        menu={menu}
        setMenu={setMenu}
        setLanguage={setLanguage}
        language={language}
        navigate={navigate}
        signedIn={Boolean(session?.access_token)}
        canVerify={canVerify}
        canAdmin={canAdmin}
        signOut={signOut}
      />

      {view === "home" && <Home t={t} navigate={navigate} />}
      {view === "digest" && (
        <Digest
          navigate={navigate}
          canModerateUpdates={canAdmin || canManageQueue}
        />
      )}
      {view === "queue" && !authChecked && (
        <main className="form-page">
          <p className="form-message" role="status">
            Checking your access...
          </p>
        </main>
      )}
      {view === "queue" &&
        authChecked &&
        (canVerify ? (
          <VerificationQueue
            navigate={navigate}
            admin={canAdmin}
            canManageQueue={canManageQueue}
            ward={reviewerWard}
            language={language}
          />
        ) : session?.access_token ? (
          <main className="form-page">
            <button className="back" onClick={() => navigate("home")}>
              <Icon name="back" /> Back home
            </button>
            <section className="success auth-wrap">
              <div className="eyebrow">
                <span></span> VERIFICATION ACCESS
              </div>
              <h1>Access restricted.</h1>
              <p>
                This area is only available to approved community verifiers.
                Your account does not have permission to view or update reports.
              </p>
              <button className="primary" onClick={signOut}>
                Sign out <Icon name="arrow" />
              </button>
            </section>
          </main>
        ) : (
          <Auth
            verification
            onSuccess={(nextSession, nextUser) =>
              handleAuthSuccess(nextSession, nextUser, "queue")
            }
            onCancel={() => navigate("home")}
          />
        ))}
      {view === "admin" && !authChecked && (
        <main className="form-page">
          <p className="form-message" role="status">
            Checking administrator access...
          </p>
        </main>
      )}
      {view === "admin" &&
        authChecked &&
        (canAdmin ? (
          <main className="inner-page">
            <button className="back" onClick={() => navigate("home")}>
              <Icon name="back" /> Back home
            </button>
            <div className="page-heading">
              <div>
                <div className="eyebrow"><span></span> ADMINISTRATION</div>
                <h1>Manage reviewers.</h1>
                <p>Authorize reviewer accounts, then assign reports from the queue.</p>
              </div>
              <button className="primary" onClick={() => navigate("queue")}>
                Assign and review reports <Icon name="arrow" />
              </button>
            </div>
            <ReviewerAdmin language={language} />
          </main>
        ) : session?.access_token ? (
          <main className="form-page">
            <section className="success auth-wrap">
              <div className="eyebrow"><span></span> ADMINISTRATION</div>
              <h1>Access restricted.</h1>
              <p>Only accounts listed in the backend ADMIN_EMAILS setting can manage reviewers.</p>
              <button className="primary" onClick={() => navigate("home")}>
                Back home <Icon name="arrow" />
              </button>
            </section>
          </main>
        ) : (
          <Auth
            verification
            onSuccess={(nextSession, nextUser) =>
              handleAuthSuccess(nextSession, nextUser, "admin")
            }
            onCancel={() => navigate("home")}
          />
        ))}

      {view === "how" && <HowItWorks navigate={navigate} />}
      {view === "report" && (
        <Report
          reportType={reportType}
          setReportType={setReportType}
          report={report}
          setReport={setReport}
          submitted={submitted}
          setSubmitted={setSubmitted}
          reference={reportReference}
          setReference={setReportReference}
          navigate={navigate}
        />
      )}
      {view === "auth" && (
        <Auth
          onSuccess={handleAuthSuccess}
          onCancel={() => navigate("home")}
        />
      )}
      {view === "resolve" &&
        (authChecked ? (
          session?.access_token ? (
            <Resolve navigate={navigate} token={session.access_token} />
          ) : (
            <Auth
              onSuccess={handleAuthSuccess}
              onCancel={() => navigate("home")}
            />
          )
        ) : (
          <main className="form-page">
            <p className="form-message" role="status">
              Checking your sign-in...
            </p>
          </main>
        ))}

      <Footer />
    </div>
  );
}

export default App;
