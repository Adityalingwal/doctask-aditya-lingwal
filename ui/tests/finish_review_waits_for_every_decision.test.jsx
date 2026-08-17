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

const ADD = /add this run's changes to the register/i;
const DISCARD = /discard this run's changes/i;

const answered = decisionReply({ outcome: "approved" });
// A finding, because the gate no longer waits in the queue for anybody: the
// unanswered decision has to be one of the run's own questions.
const unanswered = findingDecisionReply();

test("neither ending is offered while one decision is still unanswered", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ decisions: [answered, unanswered] }) },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  await openSection(/decisions/i);
  await screen.findByText(unanswered.issue);

  expect(screen.queryByRole("button", { name: ADD })).toBeNull();
  expect(screen.queryByRole("button", { name: DISCARD })).toBeNull();
  expect(screen.getByText("Answer all 1 to finish this review.")).toBeTruthy();
});

test("both endings are offered once the server reports every decision answered", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: {
          body: runReply({
            decisions: [
              answered,
              findingDecisionReply({ outcome: "rejected" }),
            ],
          }),
        },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  await openSection(/decisions/i);

  expect(await screen.findByRole("button", { name: ADD })).toBeTruthy();
  expect(screen.getByRole("button", { name: DISCARD })).toBeTruthy();
});
