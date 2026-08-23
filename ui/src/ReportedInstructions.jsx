// Any line in a document that tried to give the system an instruction. It is
// shown and never followed, and the documents holding it were still read —
// which is said once above the cards rather than under each, because an
// embedded instruction can appear on any document, including one that states
// no requirement at all.
export default function ReportedInstructions({ reported }) {
  if (reported.length === 0) {
    return (
      <p className="m-0 text-ink-soft">
        No document in this run tried to give the system an instruction.
      </p>
    );
  }
  return (
    <>
      <p className="m-0 mb-4 text-ink-soft">
        Reported, not followed. These documents were still read.
      </p>
      <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2">
        {reported.map((entry, place) => (
          <li key={place} className="border border-line bg-card px-4 py-3 text-sm">
            <p className="m-0">
              <span className="font-mono font-semibold">{entry.file}</span>
              <br />
              {entry.place}
            </p>
            <p className="m-0 mt-2 italic">{`"${entry.quote}"`}</p>
          </li>
        ))}
      </ul>
    </>
  );
}
