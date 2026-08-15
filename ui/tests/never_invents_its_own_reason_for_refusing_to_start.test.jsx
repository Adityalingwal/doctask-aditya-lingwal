// L9 — locked 2026-08-15, superseding this file's earlier "validates
// nothing" rule: the box may now refuse to send an empty name or an
// unchosen folder, in its own words, and nothing else. A folder that is
// chosen but that the server refuses (it does not exist, say) is still sent
// exactly as chosen, and the server's own sentence is shown unchanged — no
// second, weaker sentence written in front of it, and no other rule
// duplicated client-side.
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
      onStarted={vi.fn()}
      onClose={() => {}}
    />,
  );

  fireEvent.change(screen.getByLabelText(/project name/i), {
    target: { value: "Northside Dental" },
  });
  // The folder is left unchosen on purpose.

  await act(async () => {
    screen.getByRole("button", { name: /create and start run/i }).click();
  });

  expect(screen.getByText("Choose the folder to watch.")).toBeTruthy();
  expect(answering.calls).toHaveLength(0);
});

test("an empty name is refused in the screen's own words, and nothing is sent", async () => {
  const answering = serverAnswering([]);
  vi.stubGlobal("fetch", answering);

  render(
    <AddProject
      projectsRoot="sample-projects"
      availableFolders={[FOLDER]}
      onStarted={vi.fn()}
      onClose={() => {}}
    />,
  );

  fireEvent.change(screen.getByLabelText(/folder/i), { target: { value: FOLDER } });
  // The name field's auto-fill from the chosen folder is cleared on purpose.
  fireEvent.change(screen.getByLabelText(/project name/i), { target: { value: "" } });

  await act(async () => {
    screen.getByRole("button", { name: /create and start run/i }).click();
  });

  expect(screen.getByText("Give this project a name.")).toBeTruthy();
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
  expect(onStarted).not.toHaveBeenCalled();
});
