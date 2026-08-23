// "Show a state the server has not confirmed" — opening another run must clear
// what the last one said before the new read answers. Otherwise the previous
// run's decisions stay on screen while Approve, Reject and Finish review
// already point at the newly opened run, and Finish review can end a review
// nobody looked at.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import {
  decisionReply,
  projectReply,
  projectsReply,
  runReply,
} from "./server_replies.js";

const OPEN_RUN = "0f3f0f6a-4f8a-4a4a-9c1e-3f6b2d5a7c11";
const OTHER_RUN = "99999999-8888-4777-8666-555544443333";

// The one line of a possible-match decision that asks the question, out of
// the several blocks the backend built the whole text from.
const THE_QUESTION_LINE = "Is this the same ask as row 2?";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("never_shows_the_previous_runs_decisions_after_opening_another_run", async () => {
  const twoRuns = projectReply({
    run_count: 2,
    runs: [
      {
        run_id: OTHER_RUN,
        run_number: 2,
        status: "done",
        stage: "commit",
        started_at: "2026-03-27T10:00:00+00:00",
        waiting_decisions: 0,
        finished_stages: ["ingest", "extract", "match", "examine", "review", "commit"],
        row_count: 7,
      },
      {
        run_id: OPEN_RUN,
        run_number: 1,
        status: "needs review",
        stage: "review",
        started_at: "2026-03-26T10:00:00+00:00",
        waiting_decisions: 1,
        finished_stages: ["ingest", "extract", "match", "examine"],
        row_count: null,
      },
    ],
  });

  vi.stubGlobal("fetch", async (requested) => {
    const path = new URL(requested, "http://localhost:8000").pathname;
    if (path === "/projects") {
      return {
        ok: true,
        status: 200,
        json: async () => projectsReply({ projects: [twoRuns] }),
      };
    }
    if (path === `/runs/${OPEN_RUN}`) {
      return {
        ok: true,
        status: 200,
        json: async () => runReply({ decisions: [decisionReply()] }),
      };
    }
    // The run just opened is still being read: this is exactly the window in
    // which the screen must show nothing rather than the last run's answer.
    return new Promise(() => {});
  });

  render(<ReviewScreen projectId="" runId={OPEN_RUN} />);
  await openSection(/^run/i);
  await waitFor(() => {
    expect(screen.getByText(THE_QUESTION_LINE)).toBeTruthy();
  });

  fireEvent.click(screen.getByText("2"));

  await waitFor(() => {
    expect(screen.queryByText(THE_QUESTION_LINE)).toBeNull();
  });
  expect(screen.queryByRole("button", { name: /approve/i })).toBeNull();
  expect(screen.queryByRole("button", { name: /finish review/i })).toBeNull();
});
