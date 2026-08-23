import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import {
  decisionReply,
  findingDecisionReply,
  projectsReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

// What Approve and Reject will do is a fact the server knows, so it is the
// same fixed text on every card of one kind. It is never part of the stored
// question, which is the model's own sentence and stays frozen.
const observationMatch = decisionReply({
  decision_id: "3d5f7b91-2222-4c33-8444-555566667777",
  kind: "observation match",
  question:
    "Testing feedback (testing-feedback-25-mar.md) says: 'the reminder goes "
    + "out a day early'. Is this about row #2 — SMS reminders before an "
    + "appointment?",
  row_number: 2,
  if_approved: [
    { cell: "What testing found", value: "the reminder goes out a day early" },
    { cell: "Status", value: "Partial" },
  ],
});

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
  render(<ReviewScreen runId={runId} />);
  await openSection(/decisions/i);
  return (await screen.findByText(anchor)).closest("li").textContent;
}

test("a possible match says the two shapes the register can take", async () => {
  const decision = decisionReply();
  const card = await cardAnchoredOn(decision, decision.question);

  expect(card).toContain("one row");
  expect(card).toContain("a separate row");
  // The words a person reads are about the register, never an export.
  expect(card).not.toMatch(/export/i);
});

test("an observation match prints the cells the stored move would write", async () => {
  const card = await cardAnchoredOn(observationMatch, observationMatch.question);

  expect(card).toContain("row #2 records");
  expect(card).toContain("What testing found: the reminder goes out a day early");
  expect(card).toContain("Status: Partial");
  expect(card).toContain("nothing changes on the register");
});

test("a finding says where it goes and where it stays", async () => {
  const decision = findingDecisionReply();
  const card = await cardAnchoredOn(decision, decision.issue);

  expect(card).toContain(
    "the finding is attached to row #4 and appears in the register",
  );
  expect(card).toContain(
    "the finding stays in this run's record and never reaches the register",
  );
  // Screen 4's rule is unchanged: the rule's own words, never a rule code.
  expect(card).not.toMatch(/\bR1\b/);
});

test("the question the model wrote never carries the consequence text", async () => {
  const card = await cardAnchoredOn(observationMatch, observationMatch.question);

  expect(card).toContain(observationMatch.question);
  expect(observationMatch.question).not.toMatch(/approve|reject/i);
});
