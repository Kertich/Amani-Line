import { useState } from "react";
import { copy } from "./components/data";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { Home } from "./components/Home";
import { Digest } from "./components/Digest";
import { HowItWorks } from "./components/HowItWorks";
import { Report } from "./components/Report";
import { Resolve } from "./components/Resolve";

function App() {
  const [language, setLanguage] = useState("en");
  const [view, setView] = useState("home");
  const [menu, setMenu] = useState(false);
  const [reportType, setReportType] = useState("Rumour to check");
  const [submitted, setSubmitted] = useState(false);
  const [report, setReport] = useState("");
  const t = copy[language];

  const navigate = (next) => {
    setView(next);
    setMenu(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
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
      />

      {view === "home" && <Home t={t} navigate={navigate} />}
      {view === "digest" && <Digest navigate={navigate} />}
      {view === "how" && <HowItWorks navigate={navigate} />}
      {view === "report" && (
        <Report
          view={view}
          reportType={reportType}
          setReportType={setReportType}
          report={report}
          setReport={setReport}
          submitted={submitted}
          setSubmitted={setSubmitted}
          navigate={navigate}
        />
      )}
      {view === "resolve" && <Resolve navigate={navigate} />}

      <Footer />
    </div>
  );
}

export default App;
