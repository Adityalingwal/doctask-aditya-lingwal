import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import RunColumn from "../src/RunColumn.jsx";

// `new Date(null)` is the 1970 epoch in JavaScript, not an invalid date, so
// the existing `Number.isNaN` guard alone would let a queued run's row
// silently read "1 Jan". started_at needs its own explicit null check.
test("a run with no started_at reads '—', never an epoch date", async () => {
  render(
    <RunColumn
      project={{
        project_id: "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
        name: "Queued intake portal",
        source_folder_path: "sample-projects/intake-portal",
        run_count: 1,
        most_recent_run_at: null,
        runs: [
          {
            run_id: "11111111-2222-4333-8444-555566667777",
            run_number: 1,
            status: "queued",
            stage: null,
            started_at: null,
            waiting_decisions: 0,
            finished_stages: [],
            row_count: null,
          },
        ],
      }}
      selectedRunId={null}
      onOpenRun={() => {}}
      collapsed={false}
      onToggleCollapse={() => {}}
    />,
  );

  const row = await screen.findByRole("link", { name: /^1/ });
  expect(row.textContent).toContain("—");
  expect(row.textContent).not.toMatch(/1 Jan|1970/);
});
