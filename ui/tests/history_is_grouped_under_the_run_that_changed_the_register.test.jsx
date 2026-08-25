// Items 17, S13 and 48. One heading per run, naming the run and the moment
// and no file — a run can read two documents, so the file belongs on each
// entry rather than on the heading over both. A finding's line is the
// backend's own detail, which carries no rule id.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { dayMonthTime } from "../src/format_date.js";
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

async function openHistory(history) {
  const exported = registerReply();
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
      { method: "GET", path: `/projects/${projectId}/history`, reply: { body: history } },
    ]),
  );
  render(<ReviewScreen projectId="" runId="" />);
  fireEvent.click(await screen.findByText(project.name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  // Since item 6a the history is read inside the row's own panel, so it is
  // opened the way a person opens it: press the row, then its history.
  fireEvent.click(await screen.findByText("Applicants upload supporting documents."));
  const drawer = await screen.findByRole("complementary", { name: /row 1/i });
  fireEvent.click(within(drawer).getByRole("button", { name: /history/i }));
  return drawer;
}

// The panel's own Evidence heading is an h4 too, so the run headings are the
// ones that name a run.
function runHeadings(panel) {
  return [...panel.querySelectorAll("h4")]
    .map((heading) => heading.textContent)
    .filter((heading) => heading.startsWith("Run "));
}

test("entries sit under a heading naming their run and the moment, and no file", async () => {
  const history = historyReply();
  const panel = await openHistory(history);
  const [newest, , , born] = history.entries;

  const headings = runHeadings(panel);
  expect(headings).toEqual([
    `Run 2 · ${dayMonthTime(newest.changed_at)}`,
    `Run 1 · ${dayMonthTime(born.changed_at)}`,
  ]);
  for (const heading of headings) {
    expect(heading).not.toContain(".md");
  }
});

test("a document is named once above the entries it changed, not on each of them", async () => {
  const history = historyReply();
  const panel = await openHistory(history);

  const files = [...panel.querySelectorAll("h5")].map((one) => one.textContent);
  expect(files).toContain(history.entries[0].source_file);
  expect(files).toContain(history.entries[1].source_file);

  const lines = entryLines(panel);
  expect(lines).toHaveLength(history.entries.length);
  for (const line of lines) {
    expect(line).not.toContain(".md");
  }
});

test("a finding's line is the rule's own words and carries no rule id", async () => {
  const history = historyReply();
  const panel = await openHistory(history);
  const attached = history.entries[2];

  const line = entryLines(panel).find((item) => item.includes("Finding:"));
  expect(line).toBe(attached.detail);
  expect(line).not.toMatch(/\bR\d\b/);
});

// Run, then document, then the change itself: the innermost list is the one a
// reader reads.
function entryLines(panel) {
  return [...panel.querySelectorAll("li li li")].map((item) => item.textContent);
}
