// Items 35, 38 and S12. Three groups, one line per entry, and every sentence
// the server's. An observation that reached no row is titled by what it says
// rather than by the file it came out of — the file was read.
import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import { projectsReply, runId, runReply, serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const READ_BEFORE = {
  kind: "read before",
  file: "client-requirements-v1.md",
  reason: "unchanged since it was read.",
};

const NOT_READ = {
  kind: "not read",
  file: "notes.docx",
  reason: "Not a format this system reads. It reads .md and .pdf.",
};

// The words were located in the file, so the entry names its place.
const LOCATED = {
  kind: "not attached",
  file: "testing-feedback-12-aug.md",
  summary: "Testing requested an SMS summary after each chat.",
  source_line: 'testing-feedback-12-aug.md, under "Chat widget"',
  reason: "This is not about any requirement in the register.",
};

// The words were never in the file, so there is no place to name and the
// reason names the file instead (S12).
const NEVER_IN_THE_FILE = {
  kind: "not attached",
  file: "testing-feedback-12-aug.md",
  summary: "The bot replies in Hindi.",
  quote: "the bot answers in Hindi",
  source_line: null,
  reason:
    "The model said this comes from testing-feedback-12-aug.md, but those "
    + "words are not in the file.",
};

async function skippedTab(entries) {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ skipped: entries }) },
      },
    ]),
  );
  render(<ReviewScreen projectId="" runId={runId} />);
  await openSection(/skipped/i);
  return await screen.findByRole("region", { name: /skipped/i });
}

test("the three kinds are three groups in one fixed order", async () => {
  const tab = await skippedTab([NEVER_IN_THE_FILE, NOT_READ, READ_BEFORE]);

  expect(
    [...tab.querySelectorAll("section h3")].map((heading) => heading.textContent),
  ).toEqual(["Read before", "Not read", "Not attached to any row"]);
});

test("each entry is one line and the reasons share one column", async () => {
  const tab = await skippedTab([READ_BEFORE, NOT_READ]);

  const lines = [...tab.querySelectorAll("li")];
  expect(lines).toHaveLength(2);
  for (const line of lines) {
    expect(line.querySelector(".skipped-line")).toBeTruthy();
  }
  expect(lines[0].textContent).toContain(READ_BEFORE.file);
  expect(lines[0].textContent).toContain(READ_BEFORE.reason);
});

test("an observation that reached no row is titled by what it says", async () => {
  const tab = await skippedTab([LOCATED]);
  const line = tab.querySelector("li");

  // The file is named by the source line under it, never as the title: the
  // file was read, and calling it "skipped" would be untrue (item 38).
  expect(line.firstChild.textContent).toBe(`“${LOCATED.summary}”`);
  expect(line.textContent).toContain(LOCATED.source_line);
  expect(line.textContent).toContain(LOCATED.reason);
});

test("an observation whose words were never in the file names no place", async () => {
  const tab = await skippedTab([NEVER_IN_THE_FILE]);
  const line = tab.querySelector("li");

  expect(line.textContent).toContain(NEVER_IN_THE_FILE.summary);
  expect(line.textContent).toContain(NEVER_IN_THE_FILE.reason);
  // The reason names the file; the screen invents no place of its own, and
  // the model's unverified words never reach the screen.
  expect(line.textContent).not.toContain("under");
  expect(line.textContent).not.toContain("null");
  expect(line.textContent).not.toContain(NEVER_IN_THE_FILE.quote);
});

test("a run that skipped nothing says so", async () => {
  const tab = await skippedTab([]);

  expect(tab.textContent).toContain("Nothing in this run was skipped.");
});
