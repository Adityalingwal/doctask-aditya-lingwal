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

// The configuration names the statuses that deserve the caution colour. The
// register's starting status is one of them; a status the configuration does
// not name is shown plainly. Locked by the finding on the 2026-08-17 rename:
// the configuration still said "No evidence yet" after the register started
// saying "Nothing said yet", and no test caught the chip losing its colour.
test("the starting status is marked for attention and a settled one is not", async () => {
  const exported = registerReply();
  exported.rows[0].cells.status = "Nothing said yet";
  const run = { ...projectReply().runs[0], row_count: exported.rows.length };
  const project = projectReply({ runs: [run] });
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [project] }) },
      },
      { method: "GET", path: `/projects/${projectId}/register`, reply: { body: exported } },
    ]),
  );

  render(<ReviewScreen runId="" />);
  fireEvent.click(await screen.findByText(project.name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  const register = await screen.findByRole("region", { name: /register/i });

  const marked = within(register).getByText("Nothing said yet");
  expect(marked.className).toContain("border-caution");
});
