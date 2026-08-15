// L5 — a project holds at most one run in `running` or `needs review` (the
// partial unique index in migration 20260812_0001, narrowed by
// 20260815_0012, makes a second one impossible to insert), so the card never
// sums across runs. `app/review/submit_decision.py:21` refuses an answer on
// a run that is not at review, so a failed run's leftover unanswered
// decisions are never offered as work waiting — counting them would offer
// work the server would then refuse.
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import ProjectList from "../src/ProjectList.jsx";

const PROJECT = {
  project_id: "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
  name: "Northside Dental",
  source_folder_path: "sample-projects/northside-dental",
  run_count: 2,
  most_recent_run_at: "2026-08-14T09:00:00+00:00",
  runs: [
    {
      run_id: "22222222-3333-4444-8555-666677778888",
      run_number: 2,
      status: "queued",
      stage: null,
      started_at: null,
      waiting_decisions: 0,
      finished_stages: [],
      row_count: null,
    },
    // A failed run with decisions nobody ever answered — the review it
    // raised them for stopped, so answering one is refused server-side.
    {
      run_id: "11111111-2222-4333-8444-555566667777",
      run_number: 1,
      status: "failed",
      stage: "extract",
      started_at: "2026-08-14T09:00:00+00:00",
      waiting_decisions: 3,
      finished_stages: ["ingest"],
      row_count: null,
    },
  ],
};

test("never_counts_decisions_from_a_run_that_is_not_at_review", () => {
  render(
    <ProjectList
      projects={[PROJECT]}
      refusal={null}
      selectedProjectId={null}
      onSelectProject={() => {}}
      onOpenAddProject={() => {}}
    />,
  );

  const card = screen.getByText("Northside Dental").closest("li");
  expect(card.textContent).not.toMatch(/waiting/i);
  expect(card.textContent).not.toContain("3");
});
