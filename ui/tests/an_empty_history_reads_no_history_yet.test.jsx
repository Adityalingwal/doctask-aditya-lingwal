// A project whose audit trail is empty is not a failure and not a refusal.
// The server answers 200 with no entries, and the section says so in one
// line — never an error box, never a blank space a reader has to interpret.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  projectId,
  projectReply,
  projectsReply,
  registerReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("an_empty_history_reads_no_history_yet", async () => {
  const exported = registerReply({ rows: [], exported_at: null, examine: null });
  const project = projectReply();

  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [project] }) },
      },
      {
        method: "GET",
        path: `/projects/${projectId}/register`,
        reply: { body: exported },
      },
      {
        method: "GET",
        path: `/projects/${projectId}/history`,
        reply: { body: { entries: [] } },
      },
    ]),
  );

  render(<ReviewScreen runId="" />);
  fireEvent.click(await screen.findByText(project.name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  const section = await screen.findByRole("region", { name: /history/i });

  expect(within(section).getByText("No history yet.")).toBeTruthy();
  expect(within(section).queryByRole("alert")).toBeNull();
  expect(section.querySelectorAll(".border-danger")).toHaveLength(0);
  expect(within(section).queryAllByRole("listitem")).toHaveLength(0);
});
