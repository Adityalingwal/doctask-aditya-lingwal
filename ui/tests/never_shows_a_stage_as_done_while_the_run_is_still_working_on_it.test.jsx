import { expect, test } from "vitest";

import { stageStates } from "../src/Stages.jsx";

// Every row of the table in the finished-stages brief (L9): the run's own
// stage may only win over a reported "done" while the run is genuinely still
// active, and a terminal run must never be shown as still working.
test("a running run's own stage always reads working, whether or not it has already reported itself finished", () => {
  const reportedFinished = stageStates("extract", "running", ["ingest", "extract"]);
  const notYetReported = stageStates("extract", "running", ["ingest"]);

  expect(reportedFinished.find((stage) => stage.name === "extract").state).toBe(
    "working",
  );
  expect(notYetReported.find((stage) => stage.name === "extract").state).toBe(
    "working",
  );
});

test("a review still waiting reads working, never done, even once it has a review mark", () => {
  const states = stageStates("review", "needs review", ["ingest"]);

  expect(states.find((stage) => stage.name === "review").state).toBe("working");
});

test("a failed run's own stage reads failed", () => {
  const states = stageStates("extract", "failed", ["ingest", "extract"]);

  expect(states.find((stage) => stage.name === "extract").state).toBe("failed");
});

test("a done run's current stage reads done once the run is no longer active", () => {
  const states = stageStates("commit", "done", ["ingest", "extract", "match", "commit"]);

  expect(states.find((stage) => stage.name === "commit").state).toBe("done");
});

test("a run with no changes still shows its early stage done", () => {
  const states = stageStates("ingest", "no changes", ["ingest"]);

  expect(states.find((stage) => stage.name === "ingest").state).toBe("done");
});

test("a discarded run shows review done, not working", () => {
  const states = stageStates("review", "discarded", ["ingest", "review"]);

  expect(states.find((stage) => stage.name === "review").state).toBe("done");
});

test("a rules-only run never shows extract or match as anything but not needed", () => {
  const states = stageStates("examine", "running", ["ingest"]);

  expect(states.find((stage) => stage.name === "extract").state).toBe("not needed");
  expect(states.find((stage) => stage.name === "match").state).toBe("not needed");
  expect(states.find((stage) => stage.name === "examine").state).toBe("working");
});

test("a stage the run has not reached yet reads pending", () => {
  const states = stageStates("extract", "running", ["ingest"]);

  expect(states.find((stage) => stage.name === "commit").state).toBe("pending");
});
