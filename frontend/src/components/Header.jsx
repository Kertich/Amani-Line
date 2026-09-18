import { Icon } from "./common";

export function Header({ t, menu, setMenu, setLanguage, language, navigate }) {
  return (
    <header className="site-header">
      <button
        className="brand"
        onClick={() => navigate("home")}
        aria-label="Amani Line home"
      >
        <span className="brand-mark">
          <span>✦</span>
        </span>
        <span>
          Amani <b>Line</b>
        </span>
      </button>
      <nav className={menu ? "open" : ""}>
        <button onClick={() => navigate("home")}>{t.nav[0]}</button>
        <button onClick={() => navigate("digest")}>{t.nav[1]}</button>
        <button onClick={() => navigate("how")}>{t.nav[2]}</button>
      </nav>
      <div className="header-actions">
        <button
          className="language"
          onClick={() => setLanguage(language === "en" ? "sw" : "en")}
        >
          <span className="globe">◎</span>{" "}
          {language === "en" ? "Kiswahili" : "English"}
        </button>
        <button className="menu-button" onClick={() => setMenu(!menu)}>
          <Icon name="menu" />
        </button>
      </div>
    </header>
  );
}
