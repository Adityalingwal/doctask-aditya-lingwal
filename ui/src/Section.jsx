// Every section of the screen wears the same label: its name, and on the right
// whatever that section counts. The rule running between the two turns the
// label into a header a reader can find while scrolling. The numbers this
// label used to print in front of the name are gone (item 6): the tabs above
// it already fix the order, and `01` beside `Stages` read like a step in a
// process a person had to follow.
export default function Section({ name, headingId, count, children }) {
  return (
    <section aria-labelledby={headingId}>
      <div className="mb-6 flex items-center gap-4">
        <h2 id={headingId} className="m-0 whitespace-nowrap">
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
