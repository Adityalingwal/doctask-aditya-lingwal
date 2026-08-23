// The runs column (L6): a Register entry (section 2.3) above one selected
// project's runs, newest first, and the collapse control that gives the
// reading pane the full width when it is being read. Collapse state lives in
// the parent and is not persisted — a reload always comes back expanded.
import { dayMonthTime } from "./format_date.js";
import { useScrollbarWhileScrolling } from "./scrollbar_while_scrolling.js";
import StageMarks from "./StageMarks.jsx";

const RUNNING = "running";
const NEEDS_REVIEW = "needs review";

// The register's mark on the collapsed rail. The word itself is wider than a
// 3rem rail, and turned on its side it stopped being readable at a glance;
// one capital letter is not ambiguous above a column of run numbers (14).
const REGISTER_MARK = "R";

export default function RunColumn({
  project,
  selectedRunId,
  registerOpen,
  onOpenRun,
  onOpenRegister,
  collapsed,
  onToggleCollapse,
}) {
  const listPane = useScrollbarWhileScrolling();

  if (collapsed) {
    return (
      <nav
        aria-label="Runs"
        className="flex min-h-0 flex-col items-center gap-2 border-line-strong bg-paper py-3 lg:border-r"
      >
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Expand the runs column"
          className="cursor-pointer border border-line-strong bg-card px-2 py-1 font-mono text-xs hover:bg-signal/40 active:translate-y-px"
        >
          »
        </button>
        {project !== null && (
          <>
            <RailMark
              label={REGISTER_MARK}
              title="Register"
              open={registerOpen}
              onOpen={() => onOpenRegister(project.project_id)}
            />
            {project.runs.map((run) => (
              <RailMark
                key={run.run_id}
                label={String(run.run_number)}
                title={`Run ${run.run_number}`}
                open={run.run_id === selectedRunId}
                onOpen={() => onOpenRun(run.run_id)}
              />
            ))}
          </>
        )}
      </nav>
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
          className="cursor-pointer border border-line-strong bg-card px-2 py-1 font-mono text-xs hover:bg-signal/40 active:translate-y-px"
        >
          «
        </button>
      </div>

      <nav ref={listPane} aria-label="Runs" className="pane min-h-0 flex-1">
        {project === null ? (
          <p className="m-0 px-4 py-4 text-sm text-ink-soft">
            Choose a project to see its runs.
          </p>
        ) : (
          <ul className="m-0 flex list-none flex-col p-0">
            <RegisterRow
              open={registerOpen}
              rowCount={latestRowCount(project)}
              onOpen={() => onOpenRegister(project.project_id)}
            />
            {project.runs.length === 0 ? (
              <li className="px-4 py-4 text-sm text-ink-soft">
                This project has not run yet.
              </li>
            ) : (
              project.runs.map((run) => (
                <RunRow
                  key={run.run_id}
                  run={run}
                  open={run.run_id === selectedRunId}
                  onOpen={onOpenRun}
                />
              ))
            )}
          </ul>
        )}
      </nav>
    </div>
  );
}

// The collapsed rail is navigation, not decoration: every run the expanded
// column offers is reachable from it, and each mark says what it opens (3).
function RailMark({ label, title, open, onOpen }) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      aria-current={open ? "page" : undefined}
      onClick={onOpen}
      className={`w-8 cursor-pointer border py-1 font-mono text-xs active:translate-y-px ${
        open
          ? "border-line-strong bg-card font-semibold text-ink hover:bg-signal/25 active:bg-signal/40"
          : "border-transparent text-ink-soft hover:border-line-strong hover:bg-card hover:text-ink active:bg-signal/25"
      }`}
    >
      {label}
    </button>
  );
}

// The Register entry sits above a project's runs (section 2.3): the register
// is one thing the project holds, not one more run. Its row count comes from
// the same run list already shown below it — the newest run whose row_count
// is not null — rather than a second read.
function RegisterRow({ open, rowCount, onOpen }) {
  return (
    <li>
      <a
        href="#"
        aria-current={open ? "page" : undefined}
        onClick={(clicked) => {
          clicked.preventDefault();
          onOpen();
        }}
        className={`block cursor-pointer border-b border-line-strong px-4 py-3 ${
          open
            ? "border-l-4 border-l-ink bg-card pl-3 hover:bg-signal/15"
            : "hover:bg-signal/25 active:bg-signal/40"
        }`}
      >
        <p className="m-0 flex items-baseline justify-between gap-2 font-mono text-xs font-semibold">
          <span>Register</span>
          {rowCount !== null && (
            <span className="text-ink-soft">
              {rowCount} row{rowCount === 1 ? "" : "s"}
            </span>
          )}
        </p>
      </a>
    </li>
  );
}

function latestRowCount(project) {
  const latestExportedRun = project.runs.find((run) => run.row_count !== null);
  return latestExportedRun === undefined ? null : latestExportedRun.row_count;
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
        className={`block cursor-pointer border-b border-line px-4 py-3 ${
          open
            ? "border-l-4 border-l-ink bg-card pl-3 hover:bg-signal/15"
            : "hover:bg-signal/25 active:bg-signal/40"
        }`}
      >
        <p className="m-0 flex items-baseline justify-between gap-2 font-mono text-xs">
          <span className="font-semibold">{run.run_number}</span>
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
  return startedAt === null ? "—" : dayMonthTime(startedAt);
}
