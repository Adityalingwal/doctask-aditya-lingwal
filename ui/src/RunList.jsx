// The runs the application knows about, drawn as the edge of a book: one card
// per run, short marks along the spine between them, and the open run's card
// breaking through the spine into the page beside it.
//
// A card never shows a run id. Nobody has a UUID to hand, which is the whole
// reason this column exists — and nothing on the card is invented: the project
// name, the status, the moment it started and the stages that finished are all
// fields the server sent.
import { useScrollbarWhileScrolling } from "./scrollbar_while_scrolling.js";

const STAGE_ORDER = ["ingest", "extract", "match", "examine", "review", "commit"];

export default function RunList({ runs, refusal, openRunId, onOpen }) {
  const listPane = useScrollbarWhileScrolling();
  return (
    <nav
      ref={listPane}
      aria-label="Runs"
      className="pane flex min-h-0 flex-col border-line-strong bg-paper lg:border-r"
    >
      {refusal !== null ? (
        <p className="m-0 px-5 py-4 text-sm text-ink-soft">{refusal}</p>
      ) : runs.length === 0 ? (
        <p className="m-0 px-5 py-4 text-sm text-ink-soft">
          The application answered with no runs.
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col p-0">
          {runs.map((run) => (
            <RunCard
              key={run.run_id}
              run={run}
              open={run.run_id === openRunId}
              onOpen={onOpen}
            />
          ))}
        </ul>
      )}
    </nav>
  );
}

function RunCard({ run, open, onOpen }) {
  const waiting = run.waiting_decisions > 0;
  return (
    <li className="relative">
      <a
        href={`/ui/?run=${encodeURIComponent(run.run_id)}`}
        aria-current={open ? "page" : undefined}
        onClick={(clicked) => {
          clicked.preventDefault();
          onOpen(run.run_id);
        }}
        className={`block border-b border-line px-5 py-4 ${
          open
            ? "-mr-px border-l-4 border-l-ink bg-card pl-4"
            : "hover:bg-signal/15"
        }`}
      >
        <p className="m-0 text-[15px] leading-snug font-semibold">
          {run.project_name}
        </p>
        <p className="m-0 mt-1 font-mono text-xs text-ink-soft">
          {startedOn(run.started_at)}
        </p>
        <div className="mt-3 flex items-center justify-between gap-3">
          <StageMarks finished={run.finished_stages} />
          {waiting ? (
            <span className="border border-signal-edge bg-signal px-2 py-0.5 font-mono text-[11px] font-semibold">
              {run.waiting_decisions} waiting
            </span>
          ) : (
            <span className="font-mono text-[11px] text-ink-soft">{run.status}</span>
          )}
        </div>
      </a>
      {/* The page edge: present on every card except the one lying open. */}
      {!open && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 right-0 h-px w-3 bg-line-strong"
        />
      )}
    </li>
  );
}

function StageMarks({ finished }) {
  return (
    <span className="flex gap-1" aria-hidden="true">
      {STAGE_ORDER.map((stage) => (
        <span
          key={stage}
          className={`block h-2 w-2 border border-line-strong ${
            finished.includes(stage) ? "bg-ink" : "bg-transparent"
          }`}
        />
      ))}
    </span>
  );
}

// The server sends a timestamp, or null for a run that has not started yet.
// Nothing is added to either one — an unreadable value is shown exactly as it
// arrived, and a run with no started_at says so in words rather than falling
// through to `new Date(null)`, which JavaScript reads as the 1970 epoch
// rather than an invalid date.
function startedOn(startedAt) {
  if (startedAt === null) {
    return "waiting to start";
  }
  const moment = new Date(startedAt);
  if (Number.isNaN(moment.getTime())) {
    return startedAt;
  }
  return moment.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
