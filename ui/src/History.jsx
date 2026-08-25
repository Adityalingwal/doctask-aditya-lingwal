import { CELL_HEADINGS } from "./Register.jsx";
import { dayMonthTime } from "./format_date.js";

// The three shapes GET /projects/{id}/history sends. A row's birth arrives
// already folded into one entry by the core function, so this file only
// chooses words: it gathers what it was sent under the run and the document
// each entry already names, and never orders or interprets it.
const ROW_CREATED = "row created";
const FINDING_ATTACHED = "finding attached";

// Said plainly, because a reader looking at a history beside a register would
// otherwise assume the export carries it too. The export is the four cells,
// their evidence and the findings — never this.
const NOTE_LINE = "Not part of the exported register.";
const EMPTY_HISTORY_LINE = "No history yet.";

/**
 * How one row came to say what it says, read inside that row's own panel.
 *
 * The heading names the run and the moment and no file (S13) — one run can
 * read two documents — and under it each document that touched this row in
 * that run is named once, with its changes beneath. An entry that came from
 * no document at all sits under the run heading naming none. Nothing repeats
 * the row number: the panel this sits in already is that row.
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
                {run.files.map((file, filePlace) => (
                  <li key={filePlace}>
                    {file.sourceFile !== null && (
                      <h5 className="eyebrow m-0 mb-1.5 text-ink">
                        {file.sourceFile}
                      </h5>
                    )}
                    <ul className="m-0 flex list-none flex-col gap-2 p-0">
                      {file.entries.map((entry, entryPlace) => (
                        <li
                          key={entryPlace}
                          className="border-l-2 border-line pl-4"
                        >
                          {whatChanged(entry)}
                        </li>
                      ))}
                    </ul>
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

// The order the core function answered in is kept exactly; entries are only
// gathered under the run and then the document they already name, so a run or
// a file that appeared twice in that order stays two headings rather than
// being merged into one.
function groupedByRun(entries) {
  const runs = [];
  for (const entry of entries) {
    const open = runs[runs.length - 1];
    if (open !== undefined && open.runNumber === entry.run_number) {
      gatheredUnderItsFile(open.files, entry);
      continue;
    }
    runs.push({
      runNumber: entry.run_number,
      changedAt: entry.changed_at,
      files: gatheredUnderItsFile([], entry),
    });
  }
  return runs;
}

function gatheredUnderItsFile(files, entry) {
  const sourceFile = entry.source_file ?? null;
  const open = files[files.length - 1];
  if (open !== undefined && open.sourceFile === sourceFile) {
    open.entries.push(entry);
    return files;
  }
  files.push({ sourceFile, entries: [entry] });
  return files;
}

// A cell is named by the heading a reader was shown in the register itself,
// never by the stored column key — the same mapping, imported rather than
// copied, so the two can never drift apart. A finding's own line is the
// backend's whole `detail`, which already reads `Finding: <rule text>` and
// carries no rule id (item 48).
function whatChanged(entry) {
  if (entry.kind === ROW_CREATED) {
    return `Row created — "${entry.what_was_asked}"`;
  }
  if (entry.kind === FINDING_ATTACHED) {
    return entry.detail;
  }
  const heading = CELL_HEADINGS[entry.cell] ?? entry.cell;
  return `${heading}: ${entry.old_value} → ${entry.new_value}`;
}
