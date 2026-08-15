import { stageStates } from "./Stages.jsx";

// The six-stage strip drawn small, wherever a run's progress is shown at a
// glance: a project card (L4) and a run row (L6). The full-size strip with
// names and state text stays Stages.jsx's own — this reuses its one state
// computation rather than a second copy that could drift from it.
export default function StageMarks({ stage, status, finishedStages }) {
  const states = stageStates(stage, status, finishedStages);
  return (
    <span className="flex gap-1" aria-hidden="true">
      {states.map((one) => (
        <span key={one.name} className={`block h-2 w-2 border border-line-strong ${fill(one.state)}`} />
      ))}
    </span>
  );
}

function fill(state) {
  if (state === "done") {
    return "bg-ink";
  }
  if (state === "working") {
    return "bg-signal";
  }
  if (state === "failed") {
    return "bg-danger";
  }
  return "bg-transparent";
}
