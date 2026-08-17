// Review repair, Codex finding 4. Opening the register cleared `exported` to
// null, and null was rendered as "nothing has been added" — so a project the
// server had already reported as holding rows showed an empty register for as
// long as the register read took. "Not read yet" and "read, and there is
// nothing" are two different states and the screen may not collapse them.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  projectId,
  projectReply,
  projectsReply,
  registerReply,
  runId,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const EMPTY_LINE = /Nothing has been added to this register yet/i;

test("never_calls_a_register_empty_before_it_has_been_read", async () => {
  let releaseRegister = () => {};
  const heldRegister = new Promise((resolve) => {
    releaseRegister = resolve;
  });

  const exportedProject = projectReply({
    runs: [
      {
        run_id: runId,
        run_number: 1,
        status: "done",
        stage: "commit",
        started_at: "2026-03-26T10:00:00+00:00",
        waiting_decisions: 0,
        finished_stages: ["ingest", "extract", "match", "examine", "review", "commit"],
        row_count: 7,
      },
    ],
  });

  const answering = serverAnswering([
    { method: "GET", path: "/projects", reply: () => ({ body: projectsReply({ projects: [exportedProject] }) }) },
    {
      method: "GET",
      path: `/projects/${projectId}/register`,
      reply: () => ({ body: registerReply() }),
    },
  ]);

  // Hold the register read open so the window between opening the register
  // and its answer is a real one, not a race the test happens to lose.
  const held = async (requested, options) => {
    const path = new URL(requested, "http://localhost:8000").pathname;
    if (path === `/projects/${projectId}/register`) {
      await heldRegister;
    }
    return answering(requested, options);
  };
  vi.stubGlobal("fetch", held);

  render(<ReviewScreen runId="" />);

  fireEvent.click(await screen.findByText("Acme intake portal"));
  fireEvent.click(await screen.findByRole("link", { name: /Register/i }));

  await waitFor(() => {
    expect(screen.getByText(/Reading this register/i)).toBeTruthy();
  });
  expect(screen.queryByText(EMPTY_LINE)).toBeNull();

  releaseRegister();
  await waitFor(() => {
    expect(screen.queryByText(/Reading this register/i)).toBeNull();
  });
  expect(screen.queryByText(EMPTY_LINE)).toBeNull();
});
