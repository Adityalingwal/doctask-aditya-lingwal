// L5 — after `POST /runs` succeeds, nothing the person typed is rendered.
// The screen re-reads the list through `readListFromServer` and opens the
// returned `run_id` through `openRun`, so what appears is what the server
// confirmed, not the submitted values.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { runReply, serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("never_shows_a_run_the_server_has_not_confirmed", async () => {
  const startedRunId = "9f9f9f9f-1111-4b22-8333-444455556666";
  const serverProjectId = "8e8e8e8e-2222-4c33-9444-555566667777";
  const typedName = "typed-name-should-never-appear";
  let runStarted = false;

  const answering = serverAnswering([
    {
      method: "GET",
      path: "/runs",
      reply: () => ({
        body: {
          runs: runStarted
            ? [
                {
                  run_id: startedRunId,
                  project_name: "Server-confirmed project",
                  status: "running",
                  started_at: null,
                  waiting_decisions: 0,
                  finished_stages: [],
                },
              ]
            : [],
        },
      }),
    },
    {
      method: "POST",
      path: "/projects",
      reply: { status: 201, body: { project_id: serverProjectId } },
    },
    {
      method: "POST",
      path: "/runs",
      reply: () => {
        runStarted = true;
        return { status: 202, body: { run_id: startedRunId, status: "running" } };
      },
    },
    {
      method: "GET",
      path: `/runs/${startedRunId}`,
      reply: () => ({
        body: runReply({
          run_id: startedRunId,
          status: "running",
          stage: "ingest",
          finished_stages: [],
        }),
      }),
    },
  ]);
  vi.stubGlobal("fetch", answering);

  render(<ReviewScreen />);
  await waitFor(() => {
    expect(screen.getByLabelText(/project name/i)).toBeTruthy();
  });

  fireEvent.change(screen.getByLabelText(/project name/i), {
    target: { value: typedName },
  });
  fireEvent.change(screen.getByLabelText(/folder/i), {
    target: { value: "sample-projects/does-not-matter" },
  });

  await act(async () => {
    screen.getByRole("button", { name: /start run/i }).click();
  });

  // The name appears both on the run's new card in the list and as the
  // reading pane's heading — both read from the server, neither from what
  // was typed, so more than one match is the expected, correct outcome.
  await waitFor(() => {
    expect(screen.getAllByText("Server-confirmed project").length).toBeGreaterThan(0);
  });
  expect(screen.queryByText(typedName)).toBeNull();

  // Proving L5, not just L4: the list was re-read (not merely trusted) and
  // the run was opened through the id the server returned in its own reply.
  const listCalls = answering.calls.filter(
    (call) => call.method === "GET" && call.path === "/runs",
  );
  expect(listCalls.length).toBeGreaterThanOrEqual(2);
  expect(
    answering.calls.some(
      (call) => call.method === "GET" && call.path === `/runs/${startedRunId}`,
    ),
  ).toBe(true);
});
