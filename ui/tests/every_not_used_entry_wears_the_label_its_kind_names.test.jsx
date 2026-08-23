import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import { projectsReply, runId, runReply, serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

// The three kinds the server writes (`app/ingest/collect_batch.py`,
// `app/graph/register_graph.py`, `app/extract/read_document.py`), and a fourth
// this screen has never been taught.
// Its reason deliberately never says "Read before" itself, so the assertion
// below can only be satisfied by a label the screen put there.
const readBefore = {
  kind: "read before",
  file: "client-requirements-v2.md",
  reason:
    "read before under another name or with other words; an edited or "
    + "renamed file is not read again.",
};
const notRead = {
  kind: "not read",
  file: "clinic-staff-leave-policy.pdf",
  reason: "This document is not related to this client or project.",
};
const notAttached = {
  kind: "not attached",
  file: "meeting-notes-10-mar.md",
  summary: "a weekly AI summary of all open tickets",
  quote: "the client wants a weekly AI summary of every open ticket",
  source_line: null,
  reason:
    "The model said this comes from meeting-notes-10-mar.md, but those "
    + "words are not in the file.",
};
const kindThisScreenDoesNotKnow = {
  kind: "left for later",
  file: "handover-summary.md",
  reason: "Something a later version of the server recorded.",
};
// Two kinds that collide with keys every plain JavaScript object inherits:
// looked up on the label map, they find built-ins instead of undefined, so
// only an own-key guard keeps them on the no-label path.
const kindNamedLikeAnObjectBuiltIn = {
  kind: "constructor",
  file: "renamed-notes.md",
  reason: "Something a later version of the server recorded.",
};
const kindNamedLikeThePrototypeKey = {
  kind: "__proto__",
  file: "old-scope.md",
  reason: "Something a later version of the server recorded.",
};

function cardsFor(entries) {
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
  render(<ReviewScreen runId={runId} />);
}

test("every not-used entry wears the label its kind names", async () => {
  cardsFor([readBefore, notRead, notAttached]);
  await openSection(/not used/i);

  const cards = (await screen.findAllByRole("listitem")).map((item) => item.textContent);
  const cardFor = (entry) => cards.find((text) => text.includes(entry.file));

  // The label is what tells a file an earlier run had already read apart from
  // a requirement that fell out of the register.
  expect(cardFor(readBefore)).toContain("Read before");
  expect(cardFor(notRead)).toContain("Not read");
  expect(cardFor(notAttached)).toContain("Not attached to any row");
  expect(cardFor(notRead)).not.toContain("Read before");
  expect(cardFor(notAttached)).toContain(notAttached.summary);
});

test("an entry whose kind the screen does not know wears no label at all", async () => {
  cardsFor([kindThisScreenDoesNotKnow]);
  await openSection(/not used/i);

  const cards = (await screen.findAllByRole("listitem")).map((item) => item.textContent);
  const card = cards.find((text) => text.includes(kindThisScreenDoesNotKnow.reason));

  // A wrong label is worse than none: the card still says the file and the
  // reason, and claims nothing about which kind of entry this is.
  expect(card).toBeTruthy();
  expect(card).toContain(kindThisScreenDoesNotKnow.file);
  expect(card).toContain(kindThisScreenDoesNotKnow.reason);
  expect(card).not.toContain("Already read");
  expect(card).not.toContain("Not read");
  expect(card).not.toContain("Dropped");
});

test("a kind that collides with a built-in object key wears no label and does not break the screen", async () => {
  cardsFor([kindNamedLikeAnObjectBuiltIn, kindNamedLikeThePrototypeKey]);
  await openSection(/not used/i);

  const cards = (await screen.findAllByRole("listitem")).map((item) => item.textContent);

  for (const entry of [kindNamedLikeAnObjectBuiltIn, kindNamedLikeThePrototypeKey]) {
    const card = cards.find((text) => text.includes(entry.file));
    expect(card).toBeTruthy();
    expect(card).toContain(entry.reason);
    expect(card).not.toContain("Already read");
    expect(card).not.toContain("Not read");
    expect(card).not.toContain("Dropped");
  }
});
