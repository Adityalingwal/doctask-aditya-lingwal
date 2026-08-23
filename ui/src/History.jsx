import { CELL_HEADINGS } from "./Register.jsx";
import { dayMonthTime } from "./format_date.js";

// The three shapes GET /projects/{id}/history sends. A row's birth arrives
// already folded into one entry by the core function, so this file only
// chooses words: it gathers what it was sent under the run each entry already
// names, and never orders or interprets it.
const ROW_CREATED = "row created";
const FINDING_ATTACHED = "finding attached";

// Said plainly, because a reader looking at a history beside a register would
// otherwise assume the export carries it too. The export is the four cells,
// their evidence and the findings — never this.
const NOTE_LINE = "Not part of the exported register.";
const EMPTY_HISTORY_LINE = "No history yet.";

/**
 * What changed in this register, grouped under the run that changed it. The
 * heading names the run and the moment and no file (S13) — one run can read
 * two documents, and each entry beneath keeps naming its own.
 */
export default function History({ entries }) {
  const runs = groupedByRun(entries);
  return (
    <>
      <p className="m-0 mb-4 flex items-center gap-2 text-sm text-ink-soft">
        <span className="inline-block border border-line px-2 py-0.5 font-mono text-[11px]">
          NOTE
        </span>
        {NOTE_LINE}
      </p>
      {entries.length === 0 ? (
        <p className="m-0 text-ink-soft">{EMPTY_HISTORY_LINE}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-6 p-0">
          {runs.map((run, place) => (
            <li key={place}>
              <h4 className="eyebrow m-0 mb-2">
                Run {run.runNumber} · {dayMonthTime(run.changedAt)}
              </h4>
              <ul className="m-0 flex list-none flex-col gap-3 p-0">
                {run.entries.map((entry, entryPlace) => (
                  <li key={entryPlace} className="border-l-2 border-line pl-4">
                    <p className="m-0">{whatChanged(entry)}</p>
                    {entry.source_file !== undefined && entry.source_file !== null && (
                      <p className="eyebrow m-0 mt-1">{entry.source_file}</p>
                    )}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

/** How many runs this history covers — the count the History tab wears. */
export function runsInHistory(entries) {
  return groupedByRun(entries).length;
}

// The order the core function answered in is kept exactly; entries are only
// gathered under the run they already name, so a run that appeared twice in
// that order would stay two headings rather than being merged into one.
function groupedByRun(entries) {
  const runs = [];
  for (const entry of entries) {
    const open = runs[runs.length - 1];
    if (open !== undefined && open.runNumber === entry.run_number) {
      open.entries.push(entry);
      continue;
    }
    runs.push({
      runNumber: entry.run_number,
      changedAt: entry.changed_at,
      entries: [entry],
    });
  }
  return runs;
}

// A cell is named by the heading a reader was shown in the register itself,
// never by the stored column key — the same mapping, imported rather than
// copied, so the two can never drift apart. A finding's own line is the
// backend's whole `detail`, which already reads `Finding: <rule text>` and
// carries no rule id (item 48).
function whatChanged(entry) {
  const row = `Row ${entry.row_number} · `;
  if (entry.kind === ROW_CREATED) {
    return `${row}Row created — "${entry.what_was_asked}"`;
  }
  if (entry.kind === FINDING_ATTACHED) {
    return `${row}${entry.detail}`;
  }
  const heading = CELL_HEADINGS[entry.cell] ?? entry.cell;
  return `${row}${heading}: ${entry.old_value} → ${entry.new_value}`;
}
