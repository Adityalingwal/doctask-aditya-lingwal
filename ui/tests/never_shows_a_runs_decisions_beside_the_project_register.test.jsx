// Never-do test for section 2.3: opening the register must clear the opened
// run — its export and both refusals — the same way openRun was fixed on
// front-end-projects-and-runs. A previous run's decisions must never sit
// beside the register.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import {
  decisionReply,
  projectId,
  projectReply,
  projectsReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

// The one line of a possible-match decision that asks the question, out of
// the several blocks the backend built the whole text from.
const THE_QUESTION_LINE = "Is this the same ask as row 2?";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("never_shows_a_runs_decisions_beside_the_project_register", async () => {
  const exportedRun = {
    run_id: "99999999-8888-4777-8666-555544443333",
    run_number: 2,
    status: "done",
    stage: "commit",
    started_at: "2026-03-27T10:00:00+00:00",
    waiting_decisions: 0,
    finished_stages: ["ingest", "extract", "match", "examine", "review", "commit"],
    row_count: 1,
  };
  const withTwoRuns = projectReply({
    run_count: 2,
    runs: [exportedRun, projectReply().runs[0]],
  });

  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [withTwoRuns] }) },
      },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ decisions: [decisionReply()] }) },
      },
      {
        method: "GET",
        path: `/projects/${projectId}/register`,
        reply: { body: { rows: [], columns: [], rules: null, exported_at: "2026-03-27T10:00:00+00:00", project: { name: withTwoRuns.name } } },
      },
    ]),
  );

  render(<ReviewScreen projectId="" runId={runId} />);
  await openSection(/^run/i);
  await waitFor(() => {
    expect(screen.getByText(THE_QUESTION_LINE)).toBeTruthy();
  });

  fireEvent.click(await screen.findByRole("link", { name: /register/i }));

  await waitFor(() => {
    expect(screen.queryByText(THE_QUESTION_LINE)).toBeNull();
  });
  expect(screen.queryByRole("button", { name: /approve/i })).toBeNull();
  expect(screen.queryByRole("button", { name: /finish review/i })).toBeNull();
  expect(await screen.findByRole("region", { name: /register/i })).toBeTruthy();
});
