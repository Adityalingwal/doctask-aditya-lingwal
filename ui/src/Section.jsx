// Every section of the screen wears the same label: its number, its name, and
// on the right whatever that section counts. The five sections and their order
// are fixed (D15), so numbering them makes the order look deliberate rather
// than accidental — and the rule running between the name and the count turns
// the label into a header a reader can find while scrolling.
export default function Section({ number, name, headingId, count, children }) {
  return (
    <section aria-labelledby={headingId}>
      <div className="mb-6 flex items-center gap-4">
        <h2 id={headingId} className="m-0 flex items-baseline gap-3 whitespace-nowrap">
          <span className="section-number">{number}</span>
          <span className="section-name">{name}</span>
        </h2>
        <span className="h-px flex-1 bg-line" aria-hidden="true" />
        {count !== undefined && count !== null && (
          <span className="eyebrow shrink-0">{count}</span>
        )}
      </div>
      {children}
    </section>
  );
}

// The count that earns the accent: work the run is still waiting on. Everything
// else the screen counts stays grey.
export function WaitingCount({ waiting }) {
  if (waiting === 0) {
    return <span className="eyebrow">nothing waiting</span>;
  }
  return (
    <span className="border border-signal-edge bg-signal px-2.5 py-1 font-mono text-xs font-semibold tracking-wide text-ink">
      {waiting} waiting
    </span>
  );
}
