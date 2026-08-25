const BLOCK_NAME = "Add will write";
// Where a line stops saying what changes and starts naming the documents
// behind it. The screen only colours the two halves apart; every word of both
// is the server's, printed exactly as it was sent.
const TAIL_STARTS_AT = " — ";

const DECISIONS_STILL_OPEN =
  "{count} decisions are still open — what they change appears here as you "
  + "answer.";
const ONE_DECISION_STILL_OPEN =
  "1 decision is still open — what they change appears here as you answer.";

/**
 * What the adding press would write, line for line as the server sent it.
 *
 * The block is always here while a run waits at review, because an empty Add
 * is a choice a person should be able to see rather than a silence they have
 * to guess at. The one sentence this screen writes is the count of questions
 * still open — everything else is read, never composed.
 */
export default function AddWillWrite({ entries, openDecisions }) {
  return (
    <section
      aria-labelledby="add-will-write-heading"
      className="border border-line-strong px-4 pt-3 pb-1"
    >
      <h3 id="add-will-write-heading" className="eyebrow m-0 mb-2 text-ink">
        {BLOCK_NAME}
      </h3>
      <ul
        aria-labelledby="add-will-write-heading"
        className="m-0 flex list-none flex-col p-0"
      >
        {entries.map((entry, place) => (
          <li
            key={place}
            className="will-write border-t border-line py-1.5 font-mono text-sm"
          >
            <Sentence text={entry.text} />
          </li>
        ))}
      </ul>
      {openDecisions > 0 && (
        <p className="m-0 border-t border-line py-2 font-mono text-sm text-ink-soft">
          {openDecisions === 1
            ? ONE_DECISION_STILL_OPEN
            : DECISIONS_STILL_OPEN.replace("{count}", String(openDecisions))}
        </p>
      )}
    </section>
  );
}

function Sentence({ text }) {
  const tail = text.indexOf(TAIL_STARTS_AT);
  if (tail === -1) {
    return text;
  }
  return (
    <>
      {text.slice(0, tail)}
      <span className="text-ink-soft">{text.slice(tail)}</span>
    </>
  );
}
