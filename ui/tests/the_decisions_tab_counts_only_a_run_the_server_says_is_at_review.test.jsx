// L5 — unanswered decisions left on a run that is not at review are never
// counted anywhere. `app/review/submit_decision.py` refuses an answer on such
// a run, so a badge offering three of them offers work the server would then
// refuse. The project card already obeys this; the tab badge must too.
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  decisionReply,
  projectReply,
  projectsReply,
  runId,
  runReply,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("the_decisions_tab_counts_only_a_run_the_server_says_is_at_review", async () => {
  const failedRun = projectReply({
    runs: [
      {
        run_id: runId,
        run_number: 1,
        status: "failed",
        stage: "extract",
        started_at: "2026-03-26T10:00:00+00:00",
        waiting_decisions: 3,
        finished_stages: ["ingest"],
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
        json: async () => projectsReply({ projects: [failedRun] }),
      };
    }
    return {
      ok: true,
      status: 200,
      json: async () =>
        runReply({
          status: "failed",
          stage: "extract",
          failure_reason: "The OpenRouter key is missing.",
          decisions: [
            decisionReply({ decision_id: "aaaaaaa1-1111-4111-8111-111111111111" }),
            decisionReply({ decision_id: "aaaaaaa2-2222-4222-8222-222222222222" }),
            decisionReply({ decision_id: "aaaaaaa3-3333-4333-8333-333333333333" }),
          ],
        }),
    };
  });

  render(<ReviewScreen runId={runId} />);

  const tab = await screen.findByRole("tab", { name: /decisions/i });
  await waitFor(() => {
    expect(screen.getByRole("tab", { name: /stages/i })).toBeTruthy();
  });
  expect(tab.textContent).not.toContain("3");
});
