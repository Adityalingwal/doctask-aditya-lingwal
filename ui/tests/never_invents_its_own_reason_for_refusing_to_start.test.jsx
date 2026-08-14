// L3 — the screen validates nothing. An empty name, a blank path, a folder
// that does not exist: the request is sent anyway, and the server's own
// sentence is shown exactly as it arrived. No field is blocked before the
// request goes out, and no second, weaker sentence is written in front of
// the server's.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, expect, test, vi } from "vitest";

import StartRun from "../src/StartRun.jsx";
import { serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("never_invents_its_own_reason_for_refusing_to_start", async () => {
  // The exact sentence `app/projects/create_project.py` raises for a blank
  // source folder.
  const serverSentence =
    "a project needs a source folder — give the path of the folder its "
    + "documents arrive in, then create the project again.";

  const answering = serverAnswering([
    {
      method: "POST",
      path: "/projects",
      reply: { status: 400, body: { detail: serverSentence } },
    },
  ]);
  vi.stubGlobal("fetch", answering);

  const onStarted = vi.fn();
  render(<StartRun onStarted={onStarted} />);

  fireEvent.change(screen.getByLabelText(/project name/i), {
    target: { value: "Northside Dental" },
  });
  // The folder field is left blank on purpose.

  await act(async () => {
    screen.getByRole("button", { name: /start run/i }).click();
  });

  await waitFor(() => {
    expect(screen.getByText(serverSentence)).toBeTruthy();
  });

  // The request went out with the blank value — nothing blocked it client-side.
  const projectCalls = answering.calls.filter(
    (call) => call.method === "POST" && call.path === "/projects",
  );
  expect(projectCalls).toHaveLength(1);
  expect(JSON.parse(projectCalls[0].body).source_folder_path).toBe("");
  expect(onStarted).not.toHaveBeenCalled();
});
