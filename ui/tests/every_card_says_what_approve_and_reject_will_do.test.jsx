import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import {
  decisionReply,
  findingDecisionReply,
  observationMatchReply,
  projectsReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

// What Approve and Reject will do is a fact the server knows, and since the
// decision-wording lock it is a sentence the server writes: frozen into
// `question` beside the row block and the question itself. This screen shows
// those sentences and writes none of its own.
async function cardAnchoredOn(decision, anchor) {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ decisions: [decision] }) },
      },
    ]),
  );
  render(<ReviewScreen projectId="" runId={runId} />);
  await openSection(/^run/i);
  return (await screen.findByText(anchor)).closest("li").textContent;
}

test("a possible match says the two shapes the register can take", async () => {
  const decision = decisionReply();
  const card = await cardAnchoredOn(decision, "Is this the same ask as row 2?");

  expect(card).toContain("Row 2 changes: Written down: Yes");
  expect(card).toContain(decision.if_rejected);
  // The words a person reads are about the register, never an export.
  expect(card).not.toMatch(/export/i);
});

test("an observation match prints the cells the stored move would write", async () => {
  const decision = observationMatchReply();
  const card = await cardAnchoredOn(decision, "Is this about row 2?");

  expect(card).toContain("What testing found: the reminder goes out a day early");
  expect(card).toContain("Status: Partial");
  expect(card).toContain(decision.if_rejected);
});

test("a finding says where it goes and where it stays", async () => {
  const decision = findingDecisionReply();
  const card = await cardAnchoredOn(decision, decision.issue);

  expect(card).toContain("The finding is added to row 4.");
  expect(card).toContain(decision.if_rejected);
  // Screen 4's rule is unchanged: the rule's own words, never a rule code.
  expect(card).not.toMatch(/\bR1\b/);
});

test("the consequence marker is never repeated beside the button that says it", async () => {
  const decision = observationMatchReply();
  const card = await cardAnchoredOn(decision, "Is this about row 2?");

  expect(card).not.toContain("Approve →");
  expect(card).not.toContain("Reject →");
  expect(card).toContain("Approve");
  expect(card).toContain("Reject");
});
