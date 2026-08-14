// The six stages in the order the graph runs them. A run does not always visit
// all six: a rules-only run goes from Ingest straight to Examine (D03/D07), so
// the strip has to say "this one never ran" rather than "this one is coming".
const STAGE_ORDER = ["ingest", "extract", "match", "examine", "review", "commit"];

const FAILED = "failed";

/**
 * What the server has confirmed about each stage — never more than that: a
 * reported stage is finished, the run's own stage is working, and a stage the
 * run has already moved past without reporting means it never ran.
 */
export function stageStates(stage, status, reportedStages) {
  const finished = new Set(reportedStages.map((reported) => reported.stage));
  const reached = STAGE_ORDER.indexOf(stage);
  return STAGE_ORDER.map((name, place) => {
    if (finished.has(name)) {
      return { name, state: "done" };
    }
    if (name === stage) {
      return { name, state: status === FAILED ? FAILED : "working" };
    }
    if (reached > -1 && place < reached) {
      return { name, state: "never ran" };
    }
    return { name, state: "not started" };
  });
}

export default function Stages({ run }) {
  // The only thing still read out of `cost_and_timing` is which stages the
  // run reported finishing. When that block leaves the API, the run needs
  // another way to say the same thing.
  const states = stageStates(run.stage, run.status, run.cost_and_timing.stages);
  return (
    <>
      <dl className="mb-6 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 font-mono text-sm">
        <dt className="text-ink-soft">run</dt>
        <dd className="m-0 break-all">{run.run_id}</dd>
        <dt className="text-ink-soft">project</dt>
        <dd className="m-0 break-all">{run.project_id}</dd>
        <dt className="text-ink-soft">status</dt>
        <dd className="m-0">{run.status}</dd>
      </dl>

      <ol className="m-0 grid list-none grid-cols-2 gap-2 p-0 sm:grid-cols-3 lg:grid-cols-6">
        {states.map((stage) => (
          <StageBox key={stage.name} stage={stage} />
        ))}
      </ol>

      {run.ended_early_reason !== null && (
        <p className="mt-5 border-l-4 border-caution pl-3 text-sm">
          <span className="eyebrow block">ended early</span>
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

function StageBox({ stage }) {
  const box = {
    done: "border-line-strong bg-card",
    working: "border-signal-edge bg-signal/25",
    failed: "border-danger bg-card",
    "never ran": "border-line bg-transparent border-dashed",
    "not started": "border-line bg-transparent border-dashed opacity-60",
  }[stage.state];

  return (
    <li className={`border ${box} px-4 py-3`}>
      <p className="eyebrow m-0 text-ink">{stage.name}</p>
      <p className="m-0 mt-1.5 font-mono text-xs text-ink-soft">{stage.state}</p>
      {stage.state === "working" && (
        <span className="signal-slide mt-2 block h-1 w-full border border-signal-edge" />
      )}
    </li>
  );
}
