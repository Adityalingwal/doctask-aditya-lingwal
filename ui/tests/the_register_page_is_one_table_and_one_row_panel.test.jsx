// Item 6a. The register page is the table and the panel a row opens, and
// nothing else: the whole project's history is no longer a tab beside it. A
// row's own history still lives in that panel, and the full trail is still
// read over the API and the MCP tool.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  historyReply,
  projectId,
  projectReply,
  projectsReply,
  registerReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

async function openRegister() {
  const exported = registerReply();
  const run = { ...projectReply().runs[0], row_count: exported.rows.length };
  const project = projectReply({ runs: [run] });
  const answered = serverAnswering([
    {
      method: "GET",
      path: "/projects",
      reply: { body: projectsReply({ projects: [project] }) },
    },
    { method: "GET", path: `/projects/${projectId}/register`, reply: { body: exported } },
    {
      method: "GET",
      path: `/projects/${projectId}/history`,
      reply: { body: historyReply() },
    },
  ]);
  vi.stubGlobal("fetch", answered);
  render(<ReviewScreen projectId="" runId="" />);
  fireEvent.click(await screen.findByText(project.name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  return { panel: await screen.findByRole("region", { name: /register/i }), answered };
}

test("the register page offers no history tab beside its table", async () => {
  const { panel } = await openRegister();

  expect(within(panel).queryAllByRole("tab")).toEqual([]);
  expect(panel.textContent).not.toContain("2 runs");
  expect(within(panel).getByRole("table")).toBeTruthy();
  // The rules a run judged against belong to that run, and the Run tab keeps
  // them — this page never listed them (item 15).
  expect(panel.textContent).not.toContain("Rules and findings");
  expect(panel.textContent).not.toContain("ran against");
});

test("the history is still read, because the row panel is what shows it", async () => {
  const { answered } = await openRegister();

  expect(
    answered.calls.some((call) => call.path === `/projects/${projectId}/history`),
  ).toBe(true);

  fireEvent.click(await screen.findByText("Applicants upload supporting documents."));
  const drawer = await screen.findByRole("complementary", { name: /row 1/i });
  fireEvent.click(within(drawer).getByRole("button", { name: /history/i }));
  expect(drawer.textContent).toContain("testing-feedback-25-mar.md");
});
