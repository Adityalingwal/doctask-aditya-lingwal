// The projects column (L4): one card per project, its status mark, and the
// Add-project button pinned at the bottom in every state. A card never shows
// a folder path — the path is shown in exactly one place, the Add-project
// box, while a folder is being chosen (L7).
import { dayMonth } from "./format_date.js";
import { useScrollbarWhileScrolling } from "./scrollbar_while_scrolling.js";
import StageMarks from "./StageMarks.jsx";

const RUNNING = "running";
const NEEDS_REVIEW = "needs review";

export default function ProjectList({
  projects,
  refusal,
  selectedProjectId,
  onSelectProject,
  onOpenAddProject,
}) {
  const listPane = useScrollbarWhileScrolling();
  return (
    <nav
      ref={listPane}
      aria-label="Projects"
      className="pane flex min-h-0 flex-col border-line-strong bg-paper lg:border-r"
    >
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
        className="edge-shadow-sm m-3 border-2 border-signal-edge bg-signal px-4 py-3 font-mono text-sm font-semibold"
      >
        Add project +
      </button>
    </nav>
  );
}

function ProjectCard({ project, open, onOpen }) {
  const live = project.runs.find(
    (run) => run.status === RUNNING || run.status === NEEDS_REVIEW,
  );

  return (
    <li>
      <a
        href="#"
        aria-current={open ? "true" : undefined}
        onClick={(clicked) => {
          clicked.preventDefault();
          onOpen(project.project_id);
        }}
        className={`block border-b border-line px-5 py-4 ${
          open ? "border-l-4 border-l-ink bg-card pl-4" : "hover:bg-signal/15"
        }`}
      >
        <p className="m-0 flex items-center gap-2 text-[15px] leading-snug font-semibold">
          <StatusMark live={live} />
          {project.name}
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
          {live !== undefined && live.status === NEEDS_REVIEW && (
            <span>{live.waiting_decisions} decisions waiting</span>
          )}
        </div>
      </a>
    </li>
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
