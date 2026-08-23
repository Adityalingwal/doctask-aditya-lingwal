// The six stages in the order the graph runs them. A run does not always visit
// all six: a rules-only run goes from Ingest straight to Examine (D03/D07), so
// the strip has to say "not needed" rather than "this one is coming".
const STAGE_ORDER = ["ingest", "extract", "match", "examine", "review", "commit"];

const FAILED = "failed";
// The run's own stage may still be mid-pass even after it has (prematurely)
// reported itself finished — Extract writes its mark after every document,
// not just the last one. Its own stage wins over "done" only while the run
// is genuinely still working, i.e. one of these two statuses; otherwise a
// `done` run would show `commit` as forever "working".
const ACTIVE_STATUSES = ["running", "needs review"];

/**
 * What the server has confirmed about each stage — never more than that: the
 * run's own stage wins while the run is still active, a reported stage is
 * otherwise finished, and a stage the run has already moved past without
 * reporting means it was not needed.
 */
export function stageStates(stage, status, finishedStages) {
  const finished = new Set(finishedStages);
  const reached = STAGE_ORDER.indexOf(stage);
  const active = ACTIVE_STATUSES.includes(status);
  return STAGE_ORDER.map((name, place) => {
    if (name === stage && status === FAILED) {
      return { name, state: FAILED };
    }
    if (name === stage && active) {
      return { name, state: "working" };
    }
    if (finished.has(name)) {
      return { name, state: "done" };
    }
    if (reached > -1 && place < reached) {
      return { name, state: "not needed" };
    }
    return { name, state: "pending" };
  });
}

const REVIEW_STAGE = "review";
const WAITING_FOR_REVIEW = "needs review";

// What each state is called on the strip. `pending` is this file's own name
// for the state; on screen it reads "not started", because a run that has
// already ended is never going to start those stages later (item 4). A stage
// the graph skipped keeps its own separate wording.
const STATE_WORDS = {
  done: "done",
  working: "working",
  failed: "failed",
  "not needed": "not needed",
  pending: "not started",
};

// The Review box is the one stage that waits for a person rather than working
// at something, and "working" there sent readers looking for progress that
// was never going to arrive (item 12). Label only: the state itself is
// unchanged, so the small strips and the six marks are untouched.
function stateWord(stage, status) {
  if (
    stage.name === REVIEW_STAGE
    && stage.state === "working"
    && status === WAITING_FOR_REVIEW
  ) {
    return "waiting for you";
  }
  return STATE_WORDS[stage.state] ?? stage.state;
}

// Screen 3: the identifier lines this strip used to print above itself — run,
// project, status — are gone. Both ids stay in the address bar, and the
// status is already on the project card and the run's tab badge.
export default function Stages({ run }) {
  const states = stageStates(run.stage, run.status, run.finished_stages);
  return (
    <>
      <ol className="m-0 grid list-none grid-cols-2 gap-2 p-0 sm:grid-cols-3 lg:grid-cols-6">
        {states.map((stage) => (
          <StageBox
            key={stage.name}
            stage={stage}
            word={stateWord(stage, run.status)}
          />
        ))}
      </ol>

      {run.ended_early_reason !== null && (
        <p className="mt-5 border-l-4 border-caution pl-3 text-sm">
          {/* The eyebrow prints the run's own stored status — "no changes" —
              uppercased by .eyebrow's own CSS, never a label of its own. */}
          <span className="eyebrow block">{run.status}</span>
          {run.ended_early_reason}
        </p>
      )}
      {run.failure_reason !== null && (
        <p className="mt-5 border-l-4 border-danger pl-3 text-sm">
          <span className="eyebrow block">failed at {run.stage}</span>
          {run.failure_reason}
        </p>
      )}
    </>
  );
}

function StageBox({ stage, word }) {
  const box = {
    done: "border-line-strong bg-card",
    working: "border-signal-edge bg-signal/25",
    failed: "border-danger bg-card",
    "not needed": "border-line bg-transparent border-dashed",
    pending: "border-line bg-transparent border-dashed opacity-60",
  }[stage.state];

  return (
    <li className={`border ${box} px-4 py-3`}>
      <p className="eyebrow m-0 text-ink">{stage.name}</p>
      <p className="m-0 mt-1.5 font-mono text-xs text-ink-soft">{word}</p>
      {stage.state === "working" && (
        <span className="signal-slide mt-2 block h-1 w-full border border-signal-edge" />
      )}
    </li>
  );
}
