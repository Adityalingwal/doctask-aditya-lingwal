// Item 1 and locked change (a) / S15. The folder dropdown wears this screen's
// own treatment rather than the browser's, and the button says which of the
// two endings pressing it takes: an empty folder makes a project and starts
// no run, because the server would refuse one.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  projectId,
  projectReply,
  projectsReply,
  serverAnswering,
} from "./server_replies.js";

const EMPTY_FOLDER = "sample-projects/northside-dental";

afterEach(() => {
  vi.unstubAllGlobals();
});

beforeEach(() => {
  window.history.replaceState(null, "", "/ui/");
});

const created = projectReply({
  project_id: "22222222-3333-4444-8555-666666666666",
  name: "Northside dental",
  source_folder_path: EMPTY_FOLDER,
  run_count: 0,
  runs: [],
  most_recent_run_at: null,
});

function answering(projectsAfterwards) {
  let listed = [projectReply()];
  return serverAnswering([
    {
      method: "GET",
      path: "/projects",
      reply: () => {
        const body = projectsReply({
          projects: listed,
          has_files_by_folder: {
            "sample-projects/intake-portal": true,
            [EMPTY_FOLDER]: false,
          },
        });
        listed = projectsAfterwards ?? listed;
        return { body };
      },
    },
    {
      method: "POST",
      path: "/projects",
      reply: { body: { project_id: created.project_id, created: true } },
    },
  ]);
}

async function openTheBox() {
  render(<ReviewScreen projectId="" runId="" />);
  fireEvent.click(await screen.findByRole("button", { name: /add project/i }));
  return await screen.findByRole("combobox");
}

test("the folder dropdown wears the screen's own treatment, not the browser's", async () => {
  vi.stubGlobal("fetch", answering());
  const folders = await openTheBox();

  // The browser's rounded, shaded control is taken away, and the square
  // border, mono type, focus edge and disabled treatment every other field
  // here wears are put back.
  expect(folders.className).toContain("appearance-none");
  expect(folders.className).toContain("border-line-strong");
  expect(folders.className).toContain("bg-card");
  expect(folders.className).toContain("font-mono");
  expect(folders.className).toContain("cursor-pointer");
  expect(folders.className).toContain("select-caret");
  expect(folders.className).toContain("focus:border-signal-edge");
  expect(folders.className).toContain("disabled:bg-paper");
});

test("the button offers to start a run only for a folder that holds a file", async () => {
  vi.stubGlobal("fetch", answering());
  const folders = await openTheBox();

  // Before a folder is chosen the ordinary ending is the one offered.
  expect(screen.getByRole("button", { name: /^create and start run$/i })).toBeTruthy();

  fireEvent.change(folders, { target: { value: EMPTY_FOLDER } });
  expect(screen.getByRole("button", { name: /^create project$/i })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /start run/i })).toBeNull();
});

test("creating on an empty folder opens no run and names only the project", async () => {
  const answered = answering([projectReply(), created]);
  vi.stubGlobal("fetch", answered);
  const folders = await openTheBox();

  fireEvent.change(folders, { target: { value: EMPTY_FOLDER } });
  fireEvent.click(screen.getByRole("button", { name: /^create project$/i }));

  await waitFor(() => {
    expect(window.location.search).toBe(`?project=${created.project_id}`);
  });
  // No run was asked for at all — the server would have refused one.
  expect(answered.calls.some((call) => call.path === "/runs")).toBe(false);
  expect(
    await screen.findByText(/this project has not run yet/i),
  ).toBeTruthy();
});

test("a project at review with nothing left to answer shows no waiting count", async () => {
  const waitingOnNothing = projectReply({
    runs: [{ ...projectReply().runs[0], waiting_decisions: 0 }],
  });
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [waitingOnNothing] }) },
      },
    ]),
  );
  render(<ReviewScreen projectId="" runId="" />);

  const card = (await screen.findByText(waitingOnNothing.name)).closest("a");
  expect(card.textContent).not.toContain("decisions waiting");
  expect(card.textContent).not.toContain("0 decision");
});

test("a positive waiting count is still shown", async () => {
  const waitingOnThree = projectReply({
    runs: [{ ...projectReply().runs[0], waiting_decisions: 3 }],
  });
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [waitingOnThree] }) },
      },
      { method: "GET", path: `/projects/${projectId}/register`, reply: { body: {} } },
    ]),
  );
  render(<ReviewScreen projectId="" runId="" />);

  const card = (await screen.findByText(waitingOnThree.name)).closest("a");
  expect(card.textContent).toContain("3 decisions waiting");
});
