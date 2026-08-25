// L4 — the button makes two calls, and the first one must never happen twice.
// A folder is now the project's identity (a real unique constraint on
// `projects.source_folder_path`, migrations/versions/20260815_0013), and
// `POST /projects` get-or-creates, so a second call over the same folder
// would no longer create a duplicate row — but it would still be one wasted
// round trip on every retry, and the whole point of holding `project_id`
// client-side is to skip it. The component must hold the `project_id`
// `POST /projects` returned and skip the create on retry.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, expect, test, vi } from "vitest";

import AddProject from "../src/AddProject.jsx";
import { serverAnswering } from "./server_replies.js";
import { chooseFolder } from "./choose_folder.js";

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
      reply: { status: 201, body: { project_id: projectId, created: true } },
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
      projects={[]}
      onStarted={onStarted}
      onClose={() => {}}
    />,
  );

  chooseFolder(FOLDER);

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
