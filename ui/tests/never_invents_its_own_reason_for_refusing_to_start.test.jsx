// L9 — locked 2026-08-15, updated for folder-is-a-project (2026-08-16): the
// box has no name field at all now (a project's name is derived from its
// folder, in core), so its own check is only that a folder is chosen. A
// folder that is chosen but that the server refuses (it does not exist, say)
// is still sent exactly as chosen, and the server's own sentence is shown
// unchanged — no second, weaker sentence written in front of it, and no
// other rule duplicated client-side.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, expect, test, vi } from "vitest";

import AddProject from "../src/AddProject.jsx";
import { serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const FOLDER = "sample-projects/northside-dental";

test("an unchosen folder is refused in the screen's own words, and nothing is sent", async () => {
  const answering = serverAnswering([]);
  vi.stubGlobal("fetch", answering);

  render(
    <AddProject
      projectsRoot="sample-projects"
      availableFolders={[FOLDER]}
      projects={[]}
      onStarted={vi.fn()}
      onClose={() => {}}
    />,
  );

  // The folder is left unchosen on purpose.
  await act(async () => {
    screen.getByRole("button", { name: /create and start run/i }).click();
  });

  expect(screen.getByText("Choose the folder to watch.")).toBeTruthy();
  expect(answering.calls).toHaveLength(0);
});

test("a chosen folder the server refuses is sent exactly as chosen, and the server's own sentence is shown unchanged", async () => {
  const serverSentence =
    "the folder 'sample-projects/northside-dental' is not there — put it "
    + "there, or use one that exists, then try again.";
  const answering = serverAnswering([
    {
      method: "POST",
      path: "/projects",
      reply: { status: 400, body: { detail: serverSentence } },
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

  fireEvent.change(screen.getByLabelText(/folder/i), { target: { value: FOLDER } });

  await act(async () => {
    screen.getByRole("button", { name: /create and start run/i }).click();
  });

  await waitFor(() => {
    expect(screen.getByText(serverSentence)).toBeTruthy();
  });

  const projectCalls = answering.calls.filter(
    (call) => call.method === "POST" && call.path === "/projects",
  );
  expect(projectCalls).toHaveLength(1);
  expect(JSON.parse(projectCalls[0].body).source_folder_path).toBe(FOLDER);
  expect(JSON.parse(projectCalls[0].body).name).toBeUndefined();
  expect(onStarted).not.toHaveBeenCalled();
});
