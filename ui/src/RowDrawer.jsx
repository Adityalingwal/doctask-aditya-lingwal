import { useEffect, useState } from "react";

import History from "./History.jsx";
import { CELL_HEADINGS } from "./Register.jsx";

/**
 * One register row, read beside the table rather than instead of it: the panel
 * slides in over a dimmed backdrop and the table underneath does not move, so
 * a reader keeps their place in it. Escape, the × and the backdrop all close
 * it — a panel with one way out is a panel people get stuck in.
 */
export default function RowDrawer({ row, columns, history, onClose }) {
  const [historyOpen, setHistoryOpen] = useState(false);
  const findings = row.findings ?? [];
  const rowHistory = history.filter((entry) => entry.row_number === row.row_number);

  useEffect(() => {
    const closeOnEscape = (pressed) => {
      if (pressed.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <div
      data-testid="row-drawer-backdrop"
      className="fixed inset-0 z-10 flex justify-end bg-ink/40"
      onClick={(clicked) => {
        if (clicked.target === clicked.currentTarget) {
          onClose();
        }
      }}
    >
      <aside
        aria-label={`Row ${row.row_number}`}
        className="pane flex h-full w-full max-w-xl flex-col border-l-2 border-line-strong bg-card"
      >
        <div className="flex shrink-0 items-center justify-between border-b border-line px-6 py-4">
          <h3 className="section-name m-0">Row {row.row_number}</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="cursor-pointer border border-line px-2 font-mono text-sm text-ink-soft hover:border-line-strong hover:text-ink active:translate-y-px"
          >
            ×
          </button>
        </div>

        <div className="pane min-h-0 flex-1 px-6 py-5">
          <dl className="decision-lines m-0 gap-y-3 text-[15px]">
            {columns.map((column) => (
              <div key={column} className="contents">
                <dt className="text-ink-soft">{CELL_HEADINGS[column] ?? column}</dt>
                <dd className="m-0">{row.cells[column]}</dd>
              </div>
            ))}
          </dl>

          <h4 className="eyebrow mt-8 mb-3">Evidence</h4>
          <ul className="m-0 flex list-none flex-col gap-4 p-0">
            {row.evidence.map((entry, place) => (
              <li key={place}>
                <Evidence entry={entry} />
              </li>
            ))}
          </ul>

          {/* Item 43: a row nothing was found wrong with has no findings key
              at all, and gets no block — never "0 findings". */}
          {findings.length > 0 && (
            <>
              <h4 className="eyebrow mt-8 mb-3">Findings</h4>
              <ul className="m-0 flex list-none flex-col gap-3 p-0">
                {findings.map((finding) => (
                  <li
                    key={finding.finding_id}
                    className="border-l-4 border-caution py-1 pl-4"
                  >
                    <p className="m-0">{finding.rule_text}</p>
                    <p className="m-0 mt-1 text-ink-soft">
                      Raised by run {finding.raised_by_run}: {finding.issue}
                    </p>
                  </li>
                ))}
              </ul>
            </>
          )}

          <button
            type="button"
            aria-expanded={historyOpen}
            onClick={() => setHistoryOpen((was) => !was)}
            className="eyebrow mt-8 flex w-full cursor-pointer items-center gap-2 border-b border-line pb-2 text-left hover:text-ink active:text-ink-soft"
          >
            <span aria-hidden="true">{historyOpen ? "▾" : "▸"}</span>
            History · {countedRuns(rowHistory)}
          </button>
          {historyOpen && (
            <div className="mt-4">
              <History entries={rowHistory} />
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

function countedRuns(entries) {
  const runs = new Set(entries.map((entry) => entry.run_number)).size;
  return `${runs} run${runs === 1 ? "" : "s"}`;
}

// One block per thing a document said: where it was said, the words, and the
// cells resting on it. An absence has no words and no place — the sentence
// the server wrote says which file was read and stayed silent.
function Evidence({ entry }) {
  return (
    <>
      {entry.source_line !== null && (
        <p className="eyebrow m-0">{entry.source_line}</p>
      )}
      {entry.quote === null ? (
        <p className="m-0 border-l-2 border-line pl-4 text-ink-soft italic">
          {entry.absence}
        </p>
      ) : (
        <p className="m-0 mt-1.5 border-l-2 border-line-strong pl-4">
          &ldquo;{entry.quote}&rdquo;
        </p>
      )}
      <p className="m-0 mt-2 flex flex-wrap gap-2">
        {entry.cells.map((cell) => (
          <span
            key={cell}
            className="border border-line px-2 py-0.5 font-mono text-[11px] text-ink-soft"
          >
            {cell}
          </span>
        ))}
      </p>
    </>
  );
}
