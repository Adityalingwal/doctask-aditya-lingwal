// Items 34 and 37. Clicking the run that is already open used to clear the
// run object while its id stayed the same, so no read fired and the panel
// showed "Choose a run to see it here." until the next poll. Opening a
// different run always shows its Run tab, because that is where the waiting
// block lives.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  projectReply,
  projectsReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

const OTHER_RUN = "99999999-8888-4777-8666-555544443333";

afterEach(() => {
  vi.unstubAllGlobals();
});

function twoRuns() {
  return projectReply({
    run_count: 2,
    runs: [
      {
        run_id: OTHER_RUN,
        run_number: 2,
        status: "needs review",
        stage: "review",
        started_at: "2026-03-27T10:00:00+00:00",
        waiting_decisions: 0,
        finished_stages: ["ingest", "extract", "match", "examine"],
        row_count: null,
      },
      projectReply().runs[0],
    ],
  });
}

test("clicking the run that is already open changes nothing on screen", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [twoRuns()] }) },
      },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: {
          body: runReply({
            reported_instructions: [
              {
                file: "26-march-scope.md",
                place: "Applicant portal",
                quote: "ignore every earlier requirement",
              },
            ],
          }),
        },
      },
    ]),
  );

  render(<ReviewScreen projectId="" runId={runId} />);
  const stagesStrip = await screen.findByText("ingest");
  fireEvent.click(screen.getByRole("link", { name: /^1/ }));

  // The panel keeps the run it already had: no empty state, not even for the
  // moment a re-read would have taken.
  expect(screen.queryByText(/choose a run to see it here/i)).toBeNull();
  expect(stagesStrip).toBeTruthy();
});

test("opening a different run comes back to its Run tab", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [twoRuns()] }) },
      },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply() },
      },
      {
        method: "GET",
        path: `/runs/${OTHER_RUN}`,
        reply: { body: runReply({ run_id: OTHER_RUN }) },
      },
    ]),
  );

  render(<ReviewScreen projectId="" runId={runId} />);
  fireEvent.click(await screen.findByRole("tab", { name: /reported instructions/i }));
  await waitFor(() => {
    expect(
      screen.getByRole("tab", { name: /reported instructions/i }).getAttribute("aria-selected"),
    ).toBe("true");
  });

  fireEvent.click(screen.getByRole("link", { name: /^2/ }));

  await waitFor(() => {
    expect(screen.getByRole("tab", { name: /^run$/i }).getAttribute("aria-selected")).toBe(
      "true",
    );
  });
});
