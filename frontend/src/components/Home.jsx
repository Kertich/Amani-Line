export function Home({ t, navigate }) {
  return (
    <main>
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <span></span> LOCAL · TRUSTED · FOR EVERYONE
          </div>
          <h1>{t.greeting}</h1>
          <p className="lead">{t.sub}</p>
          <p className="helper">{t.helper}</p>
          <div className="action-grid">
            {t.actions.map((action) => (
              <button
                className="action-card"
                key={action.id}
                onClick={() =>
                  navigate(action.id === "check" ? "digest" : action.id)
                }
              >
                <span className="action-icon">{action.icon}</span>
                <span className="action-text">
                  <b>{action.title}</b>
                  <small>{action.text}</small>
                </span>
                <span className="action-arrow">→</span>
              </button>
            ))}
          </div>
        </div>
        <div className="hero-visual">
          <div className="sun"></div>
          <div className="cloud c-one"></div>
          <div className="cloud c-two"></div>
          <div className="hill hill-back"></div>
          <div className="hill hill-front"></div>
          <div className="home-art home-one">
            <i></i>
            <em></em>
          </div>
          <div className="home-art home-two">
            <i></i>
            <em></em>
          </div>
          <div className="tree tree-one"></div>
          <div className="tree tree-two"></div>
          <div className="speech left">
            Taarifa
            <br />
            imehakikiwa <span>✓</span>
          </div>
          <div className="speech right">
            We know
            <br />
            what's true.
          </div>
          <div className="people">
            <span className="person p-one"></span>
            <span className="person p-two"></span>
            <span className="person p-three"></span>
            <span className="person p-four"></span>
          </div>
        </div>
      </section>
      <section className="trust-section">
        <div className="trust-copy">
          <div className="eyebrow light">
            <span></span> OUR PROMISE
          </div>
          <h2>{t.trusted}</h2>
          <p>{t.note}</p>
        </div>
        <div className="trust-points">
          <div>
            <span className="trust-icon">✓</span>
            <b>Verified updates</b>
            <small>Clear labels you can understand.</small>
          </div>
          <div>
            <span className="trust-icon">⌁</span>
            <b>Made for any phone</b>
            <small>Low data. Simple steps.</small>
          </div>
          <div>
            <span className="trust-icon">♧</span>
            <b>Your privacy matters</b>
            <small>Share safely, stay in control.</small>
          </div>
        </div>
      </section>
    </main>
  );
}
