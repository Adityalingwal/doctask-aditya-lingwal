import { render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { exportReply, runId, runReply, serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("every citation names the source file and the place the server gave it", async () => {
  const exported = exportReply();
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ status: "done", stage: "commit", exported: true }) },
      },
      { method: "GET", path: `/runs/${runId}/export`, reply: { body: exported } },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
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
  const exported = exportReply();
  exported.rows[0].citations = [
    {
      cell: "what_was_asked",
      source_file: "12-march-scope.md",
      place: "Section 2 — Applicant portal",
      source_words: null,
      absence_statement: "the 12 March scope was read in full and asks for nothing here.",
    },
  ];
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ status: "done", stage: "commit", exported: true }) },
      },
      { method: "GET", path: `/runs/${runId}/export`, reply: { body: exported } },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  const register = await screen.findByRole("region", { name: /register/i });

  expect(register.textContent).toContain("12-march-scope.md");
  expect(register.textContent).toContain("asks for nothing here");
  expect(register.textContent).not.toContain('""');
  expect(register.textContent).not.toContain("null");
});
