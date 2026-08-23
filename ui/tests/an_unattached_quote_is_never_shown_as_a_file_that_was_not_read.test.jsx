import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import { projectsReply, runId, runReply, serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

// A whole document Ingest never read (`app/ingest/collect_batch.py`'s
// `_skipped_entry`): `kind`, `file` and `reason`, and nothing else — in
// particular, no `summary`.
const documentThatWasNotRead = {
  kind: "not read",
  file: "budget.xlsx",
  reason: "Not a format this system reads. It reads .md, .pdf, .docx and .txt.",
};

// A dropped quote out of a file Extract did read
// (`app/extract/read_document.py`): the same `file` key, plus `summary` —
// which only a dropped entry carries.
const droppedRequirement = {
  kind: "not attached",
  file: "12-march-scope.md",
  summary: "an SMS reminder before every appointment",
  quote: "the client wants a text message reminder before each appointment",
  source_line: null,
  reason:
    "The model said this comes from 12-march-scope.md, but those words "
    + "are not in the file.",
};

test("an unattached quote is never shown as a file that was not read", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ skipped: [documentThatWasNotRead, droppedRequirement] }) },
      },
    ]),
  );

  render(<ReviewScreen projectId="" runId={runId} />);
  await openSection(/skipped/i);

  const cards = (await screen.findAllByRole("listitem")).map((item) => item.textContent);
  const documentCard = cards.find((text) => text.includes(documentThatWasNotRead.reason));
  const droppedCard = cards.find((text) => text.includes(droppedRequirement.summary));

  // Both name their own file, but only the dropped quote's card also says
  // what was asked for — a reader must be able to tell "this file was never
  // read" apart from "this file was read, and one requirement in it was
  // dropped".
  expect(documentCard).toBeTruthy();
  expect(droppedCard).toBeTruthy();
  expect(documentCard).toContain(documentThatWasNotRead.file);
  expect(documentCard).not.toContain(droppedRequirement.summary);
  expect(droppedCard).toContain(droppedRequirement.file);
  expect(droppedCard).toContain(droppedRequirement.summary);
  expect(droppedCard).not.toBe(documentCard);
});
