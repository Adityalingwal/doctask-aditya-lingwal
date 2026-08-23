// The projects column (L4): one card per project, its status mark, and the
// Add-project button pinned at the bottom in every state. A card never shows
// a folder path — the path is shown in exactly one place, the Add-project
// box, while a folder is being chosen (L7). It collapses the same way the
// runs column does (item 19), to a rail of first letters that still carry
// each project's status mark.
import { dayMonth } from "./format_date.js";
import { useScrollbarWhileScrolling } from "./scrollbar_while_scrolling.js";
import StageMarks from "./StageMarks.jsx";

const RUNNING = "running";
const NEEDS_REVIEW = "needs review";

export default function ProjectList({
  projects,
  refusal,
  selectedProjectId,
  collapsed,
  onToggleCollapse,
  onSelectProject,
  onOpenAddProject,
}) {
  const listPane = useScrollbarWhileScrolling();

  if (collapsed) {
    return (
      <nav
        aria-label="Projects"
        className="flex min-h-0 flex-col items-center gap-2 border-line-strong bg-paper py-3 lg:border-r"
      >
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Expand the projects column"
          className="cursor-pointer border border-line-strong bg-card px-2 py-1 font-mono text-xs hover:bg-signal/40"
        >
          »
        </button>
        {projects.map((project) => (
          <ProjectMark
            key={project.project_id}
            project={project}
            open={project.project_id === selectedProjectId}
            onOpen={onSelectProject}
          />
        ))}
      </nav>
    );
  }

  return (
    <nav
      ref={listPane}
      aria-label="Projects"
      className="pane flex min-h-0 flex-col border-line-strong bg-paper lg:border-r"
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <p className="eyebrow m-0">Projects</p>
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Collapse the projects column"
          className="cursor-pointer border border-line-strong bg-card px-2 py-1 font-mono text-xs hover:bg-signal/40"
        >
          «
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {refusal !== null ? (
          <p className="m-0 px-5 py-4 text-sm text-ink-soft">{refusal}</p>
        ) : projects.length === 0 ? (
          <p className="m-0 px-5 py-4 text-sm text-ink-soft">
            No project created yet.
          </p>
        ) : (
          <ul className="m-0 flex list-none flex-col p-0">
            {projects.map((project) => (
              <ProjectCard
                key={project.project_id}
                project={project}
                open={project.project_id === selectedProjectId}
                onOpen={onSelectProject}
              />
            ))}
          </ul>
        )}
      </div>

      {/* L8: this button is here in every state, empty or not — the box it
          opens is the only place a project is ever created. */}
      <button
        type="button"
        onClick={onOpenAddProject}
        className="edge-shadow-sm m-3 cursor-pointer border-2 border-signal-edge bg-signal px-4 py-3 font-mono text-sm font-semibold hover:bg-signal/70 active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
      >
        Add project +
      </button>
    </nav>
  );
}

// One project on the collapsed rail: its first letter and the same status
// mark the card carries, so a run that needs attention is still visible with
// the column shut.
function ProjectMark({ project, open, onOpen }) {
  const live = liveRun(project);
  return (
    <button
      type="button"
      title={project.name}
      aria-label={project.name}
      aria-current={open ? "true" : undefined}
      onClick={() => onOpen(project.project_id)}
      className={`flex w-8 cursor-pointer flex-col items-center border py-1 font-mono text-xs active:translate-y-px ${
        open
          ? "border-line-strong bg-card font-semibold text-ink"
          : "border-transparent text-ink-soft hover:border-line-strong hover:bg-card hover:text-ink"
      }`}
    >
      <span>{project.name.slice(0, 1).toUpperCase()}</span>
      <StatusMark live={live} />
    </button>
  );
}

function ProjectCard({ project, open, onOpen }) {
  const live = liveRun(project);

  return (
    <li>
      <a
        href="#"
        aria-current={open ? "true" : undefined}
        onClick={(clicked) => {
          clicked.preventDefault();
          onOpen(project.project_id);
        }}
        className={`block cursor-pointer border-b border-line px-4 py-4 ${
          open
            ? "border-l-4 border-l-ink bg-card pl-3"
            : "hover:bg-signal/25 active:bg-signal/40"
        }`}
      >
        {/* A long project name wraps inside this column rather than pushing
            it wider or spilling out of it (item 7). */}
        <p className="m-0 flex items-start gap-2 text-[15px] leading-snug font-semibold break-words">
          <StatusMark live={live} />
          <span className="min-w-0 break-words">{project.name}</span>
        </p>
        <p className="m-0 mt-1 flex items-center justify-between gap-3 font-mono text-xs text-ink-soft">
          <span>{runCount(project.run_count)}</span>
          {project.most_recent_run_at !== null && (
            <span>last {dayMonth(project.most_recent_run_at)}</span>
          )}
        </p>
        {/* A fixed-height slot, live or not, so the poll bringing the same
            state back never reflows the card (never-do test 11). */}
        <div className="mt-3 flex h-5 items-center gap-2 font-mono text-xs text-ink-soft">
          {live !== undefined && live.status === RUNNING && (
            <>
              <span>{live.stage}</span>
              <StageMarks
                stage={live.stage}
                status={live.status}
                finishedStages={live.finished_stages}
              />
            </>
          )}
          {/* Item 11: a run at review with nothing left to answer says
              nothing here. "0 decisions waiting" read as work to do. */}
          {live !== undefined
            && live.status === NEEDS_REVIEW
            && live.waiting_decisions > 0 && (
            <span>
              {live.waiting_decisions} decision
              {live.waiting_decisions === 1 ? "" : "s"} waiting
            </span>
          )}
        </div>
      </a>
    </li>
  );
}

function liveRun(project) {
  return project.runs.find(
    (run) => run.status === RUNNING || run.status === NEEDS_REVIEW,
  );
}

// The one status mark, in the one meaning it carries (L4): a lime dot
// pulsing while a run works, a still lime ring while one waits at review, a
// grey ring when nothing on this project is live. Drawn as the glyphs
// themselves, not a shape — nothing on this screen is rounded (screen.css).
function StatusMark({ live }) {
  if (live === undefined) {
    return (
      <span aria-hidden="true" className="text-ink-soft">
        ○
      </span>
    );
  }
  if (live.status === NEEDS_REVIEW) {
    return (
      <span aria-hidden="true" className="text-signal">
        ◍
      </span>
    );
  }
  return (
    <span aria-hidden="true" className="pulse-dot text-signal">
      ●
    </span>
  );
}

function runCount(count) {
  return `${count} run${count === 1 ? "" : "s"}`;
}
