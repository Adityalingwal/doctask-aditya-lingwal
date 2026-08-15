// The runs column (L6): one selected project's runs, newest first, and the
// collapse control that gives the register table the full width when it is
// being read. Collapse state lives in the parent and is not persisted — a
// reload always comes back expanded.
import { useScrollbarWhileScrolling } from "./scrollbar_while_scrolling.js";
import StageMarks from "./StageMarks.jsx";

const RUNNING = "running";
const NEEDS_REVIEW = "needs review";

export default function RunColumn({ project, selectedRunId, onOpenRun, collapsed, onToggleCollapse }) {
  const listPane = useScrollbarWhileScrolling();
  const openRun = project?.runs.find((run) => run.run_id === selectedRunId) ?? null;

  if (collapsed) {
    return (
      <div className="flex min-h-0 flex-col items-center border-line-strong bg-paper py-3 lg:border-r">
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Expand the runs column"
          className="border border-line-strong bg-card px-2 py-1 font-mono text-xs"
        >
          »
        </button>
        {openRun !== null && (
          <p className="mt-4 font-mono text-xs text-ink-soft" title={`Run ${openRun.run_number}`}>
            #{openRun.run_number}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-col border-line-strong bg-paper lg:border-r">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <p className="eyebrow m-0">Runs</p>
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Collapse the runs column"
          className="border border-line-strong bg-card px-2 py-1 font-mono text-xs"
        >
          «
        </button>
      </div>

      <nav ref={listPane} aria-label="Runs" className="pane min-h-0 flex-1">
        {project === null ? (
          <p className="m-0 px-4 py-4 text-sm text-ink-soft">
            Choose a project to see its runs.
          </p>
        ) : project.runs.length === 0 ? (
          <p className="m-0 px-4 py-4 text-sm text-ink-soft">
            This project has not run yet.
          </p>
        ) : (
          <ul className="m-0 flex list-none flex-col p-0">
            {project.runs.map((run) => (
              <RunRow
                key={run.run_id}
                run={run}
                open={run.run_id === selectedRunId}
                onOpen={onOpenRun}
              />
            ))}
          </ul>
        )}
      </nav>
    </div>
  );
}

function RunRow({ run, open, onOpen }) {
  return (
    <li>
      <a
        href={`/ui/?run=${encodeURIComponent(run.run_id)}`}
        aria-current={open ? "page" : undefined}
        onClick={(clicked) => {
          clicked.preventDefault();
          onOpen(run.run_id);
        }}
        className={`block border-b border-line px-4 py-3 ${
          open ? "border-l-4 border-l-ink bg-card pl-3" : "hover:bg-signal/15"
        }`}
      >
        <p className="m-0 flex items-baseline justify-between gap-2 font-mono text-xs">
          <span className="font-semibold">#{run.run_number}</span>
          <span className="text-ink-soft">{startedOn(run.started_at)}</span>
        </p>
        <p className="m-0 mt-1.5 flex items-center gap-2 font-mono text-xs text-ink-soft">
          <RowDetail run={run} />
        </p>
      </a>
    </li>
  );
}

// L6: a run row shows either its stage with the six marks, its status, or —
// once it has exported — the row count. A run at review keeps only its ◍
// mark here; the count of what it is waiting on lives on the project card
// and the tab badge, nowhere else (screen 4).
function RowDetail({ run }) {
  if (run.status === NEEDS_REVIEW) {
    return (
      <span aria-hidden="true" className="text-signal-edge">
        ◍
      </span>
    );
  }
  if (run.status === RUNNING) {
    return (
      <>
        <span>{run.stage}</span>
        <StageMarks stage={run.stage} status={run.status} finishedStages={run.finished_stages} />
      </>
    );
  }
  if (run.row_count !== null) {
    return <span>{run.row_count} row{run.row_count === 1 ? "" : "s"}</span>;
  }
  return <span>{run.status}</span>;
}

function startedOn(startedAt) {
  if (startedAt === null) {
    return "—";
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
