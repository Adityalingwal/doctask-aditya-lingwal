import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import { projectsReply, runId, runReply, serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

// The shape `app/extract/read_document.py` builds for a dropped quote: the
// file it came from, what was asked, the model's own (unverified) words, and
// why it was dropped.
const droppedRequirement = {
  kind: "not attached",
  file: "12-march-scope.md",
  summary: "an SMS reminder before every appointment",
  quote: "the client wants a text message reminder before each appointment",
  reason: "These words were not found in the file, so this requirement was dropped.",
};

test("a dropped quote names the file and what was dropped", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ skipped: [droppedRequirement] }) },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  await openSection(/not used/i);

  const cards = (await screen.findAllByRole("listitem")).map((item) => item.textContent);
  const card = cards.find((text) => text.includes(droppedRequirement.summary));

  expect(card).toBeTruthy();
  expect(card).toContain(droppedRequirement.file);
  expect(card).toContain(droppedRequirement.reason);
  // The model's unverified words are never the ones put on screen — the
  // whole reason the quote was dropped is that the document does not have it.
  expect(card).not.toContain(droppedRequirement.quote);
});
