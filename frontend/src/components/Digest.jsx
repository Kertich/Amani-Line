import { updates } from "./data";
import { Icon, StatusPill } from "./common";

export function Digest({ navigate }) {
  return (
    <main className="inner-page">
      <button className="back" onClick={() => navigate("home")}>
        <Icon name="back" /> Back home
      </button>
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span></span> MLolongo community digest
          </div>
          <h1>Updates you can trust.</h1>
          <p>Verified local information, in one calm place.</p>
        </div>
        <button className="primary" onClick={() => navigate("report")}>
          Report an update <Icon name="arrow" />
        </button>
      </div>
      <div className="filter-row">
        <button className="filter active">All updates</button>
        <button className="filter">Confirmed</button>
        <button className="filter">Pending</button>
        <button className="filter">False</button>
        <span className="location">
          <Icon name="map" /> Mlolongo, Machakos
        </span>
      </div>
      <div className="update-list">
        {updates.map((item) => (
          <article className="update-card" key={item.title}>
            <div className="update-icon">{item.icon}</div>
            <div className="update-main">
              <div className="update-top">
                <StatusPill status={item.status} />
                <span>{item.time}</span>
              </div>
              <h3>{item.title}</h3>
              <p>{item.detail}</p>
              <div className="source">
                <span>✓</span> {item.source}
              </div>
            </div>
            <button className="chevron">›</button>
          </article>
        ))}
      </div>
      <div className="digest-cta">
        <span className="cta-mark">✦</span>
        <div>
          <h3>Heard something you are unsure about?</h3>
          <p>
            Send it to Amani Line. We will check it with the right local
            sources.
          </p>
        </div>
        <button className="primary" onClick={() => navigate("report")}>
          Report something <Icon name="arrow" />
        </button>
      </div>
    </main>
  );
}
