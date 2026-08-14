// Every section of the screen wears the same label: its number, its name, and
// on the right whatever that section counts. The five sections and their order
// are fixed (D15), so numbering them makes the order look deliberate rather
// than accidental.
export default function Section({ number, name, headingId, count, children }) {
  return (
    <section aria-labelledby={headingId} className="border-t border-line pt-3">
      <div className="mb-4 flex items-baseline justify-between gap-4">
        <h2 id={headingId} className="eyebrow m-0 font-normal">
          <span className="mr-3 text-ink">{number}</span>
          {name}
        </h2>
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
    <span className="border border-signal-edge bg-signal px-2 py-0.5 font-mono text-[11px] font-semibold text-ink">
      {waiting} waiting
    </span>
  );
}
