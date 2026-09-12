const navItems = [
  "Overview",
  "Agents",
  "Buyer Intelligence",
  "Suppliers",
  "Sources",
  "Approvals",
  "Data Pipeline",
  "System Health",
];

export default function Home() {
  return (
    <main className="shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">Aeropex</div>
        <nav>
          {navItems.map((item) => (
            <a href="#" key={item}>
              {item}
            </a>
          ))}
        </nav>
      </aside>
      <section className="content">
        <header>
          <p className="eyebrow">Control Panel</p>
          <h1>Aeropex Buyer Intelligence Platform</h1>
          <p className="summary">
            Platform foundation shell for operational visibility, contract-driven data exchange, and future workflow control.
          </p>
        </header>
        <div className="statusGrid">
          <div>
            <span>API</span>
            <strong>Foundation ready</strong>
          </div>
          <div>
            <span>Workers</span>
            <strong>Health task only</strong>
          </div>
          <div>
            <span>Discovery</span>
            <strong>Deferred</strong>
          </div>
        </div>
      </section>
    </main>
  );
}
