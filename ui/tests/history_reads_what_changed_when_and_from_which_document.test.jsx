// The audit trail exists to answer three questions: what changed, when, and
// because of which source document. The HISTORY section is where a reader
// asks them, so every one of the three has to be legible in the line itself —
// and the note above them must say the register export does not carry any of
// this.
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

const NOTE_LINE = "Not part of the exported register.";

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
      {
        method: "GET",
        path: `/projects/${projectId}/register`,
        reply: { body: exported },
      },
      {
        method: "GET",
        path: `/projects/${projectId}/history`,
        reply: { body: history },
      },
    ]),
  );

  render(<ReviewScreen runId="" />);
  fireEvent.click(await screen.findByText(project.name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  return await screen.findByRole("region", { name: /history/i });
}

test("the history says what changed, when, and which document changed it", async () => {
  const history = historyReply();
  const section = await openHistory(history);
  const [statusMove, writtenMove, attached, born] = history.entries;

  const lines = within(section)
    .getAllByRole("listitem")
    .map((item) => item.textContent);

  expect(lines[0]).toContain(`Row ${statusMove.row_number}`);
  expect(lines[0]).toContain(statusMove.old_value);
  expect(lines[0]).toContain(statusMove.new_value);
  // The reader's own heading for the cell, never the stored column key.
  expect(lines[1]).toContain("Written down?");
  expect(lines[1]).toContain(writtenMove.old_value);
  expect(lines[1]).toContain(writtenMove.new_value);
  expect(section.textContent).not.toContain("in_writing");

  expect(lines[2]).toContain("Finding attached");
  expect(lines[2]).toContain(attached.detail);

  expect(lines[3]).toContain("Row created");
  expect(lines[3]).toContain(born.what_was_asked);

  // When, and because of which document.
  expect(lines[0]).toContain("Run 2");
  expect(lines[0]).toContain(statusMove.source_file);
  expect(lines[3]).toContain("Run 1");
  expect(lines[3]).toContain(born.source_file);
  // The moment, in the one date shape the whole screen uses.
  expect(lines[3]).toContain(dayMonthTime(born.changed_at));
  // An attachment came from no document, so its line names none.
  expect(lines[2]).not.toContain(".md");

  // Newest first, and the birth of the row is the oldest thing there is.
  expect(lines).toHaveLength(history.entries.length);
});

test("the history is labelled as no part of the exported register", async () => {
  const section = await openHistory(historyReply());

  expect(within(section).getByText("NOTE")).toBeTruthy();
  expect(section.textContent).toContain(NOTE_LINE);
});
