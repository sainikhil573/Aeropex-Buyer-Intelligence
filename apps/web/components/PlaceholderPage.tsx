export function PlaceholderPage({ title }: { title: string }) {
  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Future Milestone</p>
          <h1>{title}</h1>
          <p className="summary">Planned for a future milestone.</p>
        </div>
      </header>
      <section className="panel">
        <p className="emptyState">
          This module is intentionally not implemented in M1.3. No business data is fabricated.
        </p>
      </section>
    </>
  );
}
