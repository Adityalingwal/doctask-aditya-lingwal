import { CELL_HEADINGS } from "./Register.jsx";
import { dayMonthTime } from "./format_date.js";

// The three shapes GET /projects/{id}/history sends. A row's birth arrives
// already folded into one entry by the core function, so this file only
// chooses words: it never groups, orders or interprets what it was sent.
const ROW_CREATED = "row created";
const FINDING_ATTACHED = "finding attached";

// Said plainly, because a reader looking at a history beside a register would
// otherwise assume the export carries it too. The export is the four cells,
// their evidence and the findings — never this.
const NOTE_LINE = "Not part of the exported register.";
const EMPTY_HISTORY_LINE = "No history yet.";

export default function History({ entries }) {
  return (
    <section aria-labelledby="history-heading" className="mt-8">
      <h3 id="history-heading" className="eyebrow m-0 mb-3">
        History
      </h3>
      <p className="m-0 mb-4 flex items-center gap-2 text-sm text-ink-soft">
        <span className="inline-block border border-line px-2 py-0.5 font-mono text-[11px]">
          NOTE
        </span>
        {NOTE_LINE}
      </p>
      {entries.length === 0 ? (
        <p className="m-0 text-ink-soft">{EMPTY_HISTORY_LINE}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {entries.map((entry, place) => (
            <li key={place} className="border-l-2 border-line pl-4">
              <p className="m-0">{whatChanged(entry)}</p>
              <p className="eyebrow m-0 mt-1">{whenAndFromWhere(entry)}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// A cell is named by the heading a reader was shown in the register itself,
// never by the stored column key — the same mapping, imported rather than
// copied, so the two can never drift apart.
function whatChanged(entry) {
  const row = `Row ${entry.row_number} · `;
  if (entry.kind === ROW_CREATED) {
    return `${row}Row created — "${entry.what_was_asked}"`;
  }
  if (entry.kind === FINDING_ATTACHED) {
    return `${row}Finding attached — ${entry.detail}`;
  }
  const heading = CELL_HEADINGS[entry.cell] ?? entry.cell;
  return `${row}${heading}: ${entry.old_value} → ${entry.new_value}`;
}

function whenAndFromWhere(entry) {
  const when = `${dayMonthTime(entry.changed_at)} · Run ${entry.run_number}`;
  // An attachment came from no document, and a change a merge wrote carries
  // none either. Neither may be shown naming a file it does not have.
  if (entry.source_file === undefined || entry.source_file === null) {
    return when;
  }
  return `${when} · ${entry.source_file}`;
}
