// L4 — the button makes two calls, and the first one must never happen twice.
// `projects.name` carries no unique constraint (migrations/versions/
// 20260812_0001_create_slice_1_tables.py declares only a primary key on
// `id`), so retrying a failed `POST /runs` by creating a second project over
// the same folder would leave the watcher polling that folder twice. The
// component must hold the `project_id` `POST /projects` returned and skip the
// create on retry.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, expect, test, vi } from "vitest";

import AddProject from "../src/AddProject.jsx";
import { serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const FOLDER = "sample-projects/northside-dental";

test("never_creates_a_second_project_when_only_the_run_failed", async () => {
  const projectId = "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d";
  let runAttempts = 0;

  const answering = serverAnswering([
    {
      method: "POST",
      path: "/projects",
      reply: { status: 201, body: { project_id: projectId } },
    },
    {
      method: "POST",
      path: "/runs",
      reply: () => {
        runAttempts += 1;
        if (runAttempts === 1) {
          return {
            status: 409,
            body: {
              detail:
                "a run is already in progress for this project — wait for "
                + "it to finish, then start another.",
            },
          };
        }
        return { status: 202, body: { run_id: "started-run-id", status: "running" } };
      },
    },
  ]);
  vi.stubGlobal("fetch", answering);

  const onStarted = vi.fn();
  render(
    <AddProject
      projectsRoot="sample-projects"
      availableFolders={[FOLDER]}
      onStarted={onStarted}
      onClose={() => {}}
    />,
  );

  fireEvent.change(screen.getByLabelText(/folder/i), { target: { value: FOLDER } });
  fireEvent.change(screen.getByLabelText(/project name/i), {
    target: { value: "Northside Dental" },
  });

  const startButton = screen.getByRole("button", { name: /create and start run/i });

  await act(async () => {
    startButton.click();
  });
  await waitFor(() => {
    expect(screen.getByText(/already in progress/i)).toBeTruthy();
  });

  await act(async () => {
    startButton.click();
  });
  await waitFor(() => {
    expect(onStarted).toHaveBeenCalledWith("started-run-id");
  });

  const projectCalls = answering.calls.filter(
    (call) => call.method === "POST" && call.path === "/projects",
  );
  const runCalls = answering.calls.filter(
    (call) => call.method === "POST" && call.path === "/runs",
  );
  expect(projectCalls).toHaveLength(1);
  expect(runCalls).toHaveLength(2);
});
