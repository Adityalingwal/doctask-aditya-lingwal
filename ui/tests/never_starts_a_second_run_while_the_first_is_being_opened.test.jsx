// L7 — once the box's own work is under way it must never start a second
// run. The gap this covers is the one between `POST /runs` answering and the
// parent finishing its re-read: the box is still mounted through it, and if
// the button is live a second click sends another `POST /runs` with the
// project id already in hand. The server does not refuse that — it queues a
// waiting run behind the active one (app/runs/run_lifecycle.py) — so the
// screen is the only thing that can prevent it.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, expect, test, vi } from "vitest";

import AddProject from "../src/AddProject.jsx";
import { serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const FOLDER = "sample-projects/northside-dental";

test("never_starts_a_second_run_while_the_first_is_being_opened", async () => {
  const projectId = "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d";
  const answering = serverAnswering([
    {
      method: "POST",
      path: "/projects",
      reply: { status: 201, body: { project_id: projectId } },
    },
    {
      method: "POST",
      path: "/runs",
      reply: { status: 202, body: { run_id: "started-run-id", status: "running" } },
    },
  ]);
  vi.stubGlobal("fetch", answering);

  // The parent's own work — re-reading the list and opening the run — is a
  // network round-trip. Holding it open is what makes the gap observable.
  let finishOpening;
  const onStarted = vi.fn(
    () => new Promise((resolve) => {
      finishOpening = resolve;
    }),
  );

  render(
    <AddProject
      projectsRoot="sample-projects"
      availableFolders={[FOLDER]}
      projects={[]}
      onStarted={onStarted}
      onClose={() => {}}
    />,
  );

  fireEvent.change(screen.getByLabelText(/folder/i), { target: { value: FOLDER } });

  const startButton = screen.getByRole("button", { name: /create and start run/i });

  await act(async () => {
    startButton.click();
  });
  await waitFor(() => {
    expect(onStarted).toHaveBeenCalledWith("started-run-id");
  });

  // The parent is still opening the run. A second click here must reach
  // nothing.
  await act(async () => {
    startButton.click();
  });

  const runCalls = answering.calls.filter(
    (call) => call.method === "POST" && call.path === "/runs",
  );
  expect(runCalls).toHaveLength(1);
  expect(onStarted).toHaveBeenCalledTimes(1);

  await act(async () => {
    finishOpening();
  });
});
