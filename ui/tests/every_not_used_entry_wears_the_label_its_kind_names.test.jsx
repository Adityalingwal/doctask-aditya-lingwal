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
  render(<ReviewScreen projectId="" runId={runId} />);
}

// The entries wear their label as the heading of the group they sit in
// (item 35), so what an entry is labelled is the heading above it.
async function groups() {
  const tab = await screen.findByRole("region", { name: /skipped/i });
  return [...tab.querySelectorAll("section")].map((group) => ({
    label: group.querySelector("h3")?.textContent ?? null,
    entries: [...group.querySelectorAll("li")].map((item) => item.textContent),
  }));
}

async function groupHolding(text) {
  return (await groups()).find((group) =>
    group.entries.some((entry) => entry.includes(text)),
  );
}

test("every skipped entry wears the label its kind names", async () => {
  cardsFor([readBefore, notRead, notAttached]);
  await openSection(/skipped/i);

  // The label is what tells a file an earlier run had already read apart from
  // a requirement that fell out of the register.
  expect((await groupHolding(readBefore.file)).label).toBe("Read before");
  expect((await groupHolding(notRead.file)).label).toBe("Not read");
  const dropped = await groupHolding(notAttached.summary);
  expect(dropped.label).toBe("Not attached to any row");
  expect(dropped.entries.join("")).toContain(notAttached.summary);
});

test("an entry whose kind the screen does not know wears no label at all", async () => {
  cardsFor([kindThisScreenDoesNotKnow]);
  await openSection(/skipped/i);

  // A wrong label is worse than none: the entry still says the file and the
  // reason, and claims nothing about which kind of entry this is.
  const group = await groupHolding(kindThisScreenDoesNotKnow.reason);
  expect(group).toBeTruthy();
  expect(group.label).toBeNull();
  expect(group.entries.join("")).toContain(kindThisScreenDoesNotKnow.file);
  expect(group.entries.join("")).toContain(kindThisScreenDoesNotKnow.reason);
});

test("a kind that collides with a built-in object key wears no label and does not break the screen", async () => {
  cardsFor([kindNamedLikeAnObjectBuiltIn, kindNamedLikeThePrototypeKey]);
  await openSection(/skipped/i);

  for (const entry of [kindNamedLikeAnObjectBuiltIn, kindNamedLikeThePrototypeKey]) {
    const group = await groupHolding(entry.reason);
    expect(group).toBeTruthy();
    expect(group.label).toBeNull();
    expect(group.entries.join("")).toContain(entry.reason);
  }
});
