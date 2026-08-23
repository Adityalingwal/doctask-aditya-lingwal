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
  fireEvent.click(await screen.findByRole("tab", { name: /history/i }));
  return await screen.findByRole("tabpanel", { name: /history/i });
}

test("entries sit under a heading naming their run and the moment, and no file", async () => {
  const history = historyReply();
  const panel = await openHistory(history);
  const [newest, , , born] = history.entries;

  const headings = [...panel.querySelectorAll("h4")].map(
    (heading) => heading.textContent,
  );
  expect(headings).toEqual([
    `Run 2 · ${dayMonthTime(newest.changed_at)}`,
    `Run 1 · ${dayMonthTime(born.changed_at)}`,
  ]);
  for (const heading of headings) {
    expect(heading).not.toContain(".md");
  }
});

test("each entry beneath still names the document it came from", async () => {
  const history = historyReply();
  const panel = await openHistory(history);
  const groups = [...panel.querySelectorAll(":scope > ul > li")];

  const firstRun = within(groups[0]).getAllByRole("listitem");
  expect(firstRun).toHaveLength(3);
  expect(firstRun[0].textContent).toContain(history.entries[0].source_file);
  expect(firstRun[1].textContent).toContain(history.entries[1].source_file);
});

test("a finding's line is the rule's own words and carries no rule id", async () => {
  const history = historyReply();
  const panel = await openHistory(history);
  const attached = history.entries[2];

  const line = [...panel.querySelectorAll("li li")].find((item) =>
    item.textContent.includes("Finding:"),
  );
  expect(line.textContent).toBe(`Row ${attached.row_number} · ${attached.detail}`);
  expect(line.textContent).not.toMatch(/\bR\d\b/);
});
