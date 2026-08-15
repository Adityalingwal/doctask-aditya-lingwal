// Every section of the screen wears the same label: its number, its name, and
// on the right whatever that section counts. A run's sections and their order
// are fixed, so numbering them makes the order look deliberate rather than
// accidental — and the rule running between the name and the count turns the
// label into a header a reader can find while scrolling. The project's own
// register panel reuses this label without a number: it is one panel, not one
// of an ordered set.
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
