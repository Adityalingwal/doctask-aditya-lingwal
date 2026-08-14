import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import RunList from "../src/RunList.jsx";

// `new Date(null)` is the 1970 epoch in JavaScript, not an invalid date, so
// the existing `Number.isNaN` guard alone would let a waiting run's card
// silently read "1 Jan". started_at needs its own explicit null check.
test("a run with no started_at reads 'waiting to start', never an epoch date", async () => {
  render(
    <RunList
      runs={[
        {
          run_id: "11111111-2222-4333-8444-555566667777",
          project_name: "Queued intake portal",
          status: "waiting",
          started_at: null,
          waiting_decisions: 0,
          finished_stages: [],
        },
      ]}
      refusal={null}
      openRunId={null}
      onOpen={() => {}}
    />,
  );

  const card = await screen.findByText("Queued intake portal");
  expect(card.closest("li").textContent).toContain("waiting to start");
  expect(card.closest("li").textContent).not.toMatch(/1 Jan|1970/);
});
