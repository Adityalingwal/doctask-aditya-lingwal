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
// Its reason deliberately never says "Already read" itself, so the assertion
// below can only be satisfied by a label the screen put there.
const alreadyRead = {
  kind: "already read",
  file: "client-requirements-v2.md",
  reason: "Read before — an edited or renamed file is not read again.",
};
const notRead = {
  kind: "not read",
  file: "clinic-staff-leave-policy.pdf",
  reason: "This document is not related to this client or project.",
};
const dropped = {
  kind: "dropped",
  file: "meeting-notes-10-mar.md",
  summary: "a weekly AI summary of all open tickets",
  quote: "the client wants a weekly AI summary of every open ticket",
  reason: "These words were not found in the file, so this requirement was dropped.",
};
const kindThisScreenDoesNotKnow = {
  kind: "left for later",
  file: "handover-summary.md",
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
        reply: { body: runReply({ not_used: entries }) },
      },
    ]),
  );
  render(<ReviewScreen runId={runId} />);
}

test("every not-used entry wears the label its kind names", async () => {
  cardsFor([alreadyRead, notRead, dropped]);
  await openSection(/not used/i);

  const cards = (await screen.findAllByRole("listitem")).map((item) => item.textContent);
  const cardFor = (entry) => cards.find((text) => text.includes(entry.file));

  // The label is what tells a routine second-run skip apart from a
  // requirement that fell out of the register.
  expect(cardFor(alreadyRead)).toContain("Already read");
  expect(cardFor(notRead)).toContain("Not read");
  expect(cardFor(dropped)).toContain("Dropped");
  expect(cardFor(notRead)).not.toContain("Already read");
  expect(cardFor(dropped)).toContain(dropped.summary);
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
