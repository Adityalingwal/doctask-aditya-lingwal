// L4 — "every card keeps the same height in each of its states — nothing
// may reflow as the poll comes back." The third line is only ever drawn for
// a project with something live, so its slot must be in the DOM either way,
// not conditionally omitted — an omitted-then-added element is exactly what
// would reflow a poll that brought no real change.
import { render } from "@testing-library/react";
import { expect, test } from "vitest";

import ProjectList from "../src/ProjectList.jsx";

const BASE_PROJECT = {
  project_id: "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
  name: "Northside Dental",
  source_folder_path: "sample-projects/northside-dental",
  run_count: 1,
  most_recent_run_at: "2026-08-14T09:00:00+00:00",
};

const NOTHING_LIVE = {
  ...BASE_PROJECT,
  runs: [
    {
      run_id: "11111111-2222-4333-8444-555566667777",
      run_number: 1,
      status: "done",
      stage: "commit",
      started_at: "2026-08-14T09:00:00+00:00",
      waiting_decisions: 0,
      finished_stages: ["ingest", "extract", "match", "examine", "review", "commit"],
      row_count: 7,
    },
  ],
};

const SOMETHING_LIVE = {
  ...BASE_PROJECT,
  runs: [
    {
      ...NOTHING_LIVE.runs[0],
      status: "running",
      stage: "examine",
    },
  ],
};

function thirdLineSlots(container) {
  return container.querySelectorAll("li a > div.h-5");
}

test("keeps_a_card_the_same_height_when_a_poll_brings_no_change", () => {
  const { container, rerender } = render(
    <ProjectList
      projects={[NOTHING_LIVE]}
      refusal={null}
      selectedProjectId={null}
      onSelectProject={() => {}}
      onOpenAddProject={() => {}}
    />,
  );

  // The slot exists whether or not anything is live in it — one card, one
  // fixed-height slot, before any poll has brought a change.
  expect(thirdLineSlots(container)).toHaveLength(1);

  rerender(
    <ProjectList
      projects={[NOTHING_LIVE]}
      refusal={null}
      selectedProjectId={null}
      onSelectProject={() => {}}
      onOpenAddProject={() => {}}
    />,
  );
  expect(thirdLineSlots(container)).toHaveLength(1);

  // And the same slot is still there, not a newly mounted one, once a later
  // poll does bring something live.
  rerender(
    <ProjectList
      projects={[SOMETHING_LIVE]}
      refusal={null}
      selectedProjectId={null}
      onSelectProject={() => {}}
      onOpenAddProject={() => {}}
    />,
  );
  expect(thirdLineSlots(container)).toHaveLength(1);
});
