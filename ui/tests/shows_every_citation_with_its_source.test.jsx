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

// The register is the project's own panel (section 2.3), reached from the
// Register entry above a project's runs — not from a run's own tabs, which
// no longer include one.
function exportedProject(rowCount) {
  const run = { ...projectReply().runs[0], row_count: rowCount };
  return projectReply({ runs: [run] });
}

test("every citation names the source file and the place the server gave it", async () => {
  const exported = registerReply();
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [exportedProject(exported.rows.length)] }) },
      },
      { method: "GET", path: `/projects/${projectId}/register`, reply: { body: exported } },
    ]),
  );

  render(<ReviewScreen runId="" />);
  fireEvent.click(await screen.findByText(exportedProject(1).name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  const register = await screen.findByRole("region", { name: /register/i });

  const [present, absence] = exported.rows[0].citations;
  const shown = within(register)
    .getAllByRole("listitem")
    .map((item) => item.textContent);

  const presentCitation = shown.find((text) => text.includes(present.source_words));
  expect(presentCitation).toBeTruthy();
  expect(presentCitation).toContain(present.source_file);
  expect(presentCitation).toContain(present.place);

  const absenceCitation = shown.find((text) => text.includes(absence.absence_statement));
  expect(absenceCitation).toBeTruthy();
  expect(absenceCitation).toContain(absence.source_file);
});

test("a citation whose quoted words the server did not send is never shown as a quote", async () => {
  const exported = registerReply();
  exported.rows[0].citations = [
    {
      cell: "what_was_asked",
      source_file: "12-march-scope.md",
      place: "Section 2 — Applicant portal",
      source_words: null,
      absence_statement: "12-march-scope.md was read, and it does not mention this ask.",
    },
  ];
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [exportedProject(exported.rows.length)] }) },
      },
      { method: "GET", path: `/projects/${projectId}/register`, reply: { body: exported } },
    ]),
  );

  render(<ReviewScreen runId="" />);
  fireEvent.click(await screen.findByText(exportedProject(1).name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  const register = await screen.findByRole("region", { name: /register/i });

  expect(register.textContent).toContain("12-march-scope.md");
  expect(register.textContent).toContain("does not mention this ask");
  expect(register.textContent).not.toContain('""');
  expect(register.textContent).not.toContain("null");
});
