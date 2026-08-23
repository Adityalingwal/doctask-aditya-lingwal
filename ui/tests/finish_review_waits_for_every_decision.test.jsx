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

  render(<ReviewScreen projectId="" runId={runId} />);
  await openSection(/^run/i);
  await screen.findByText(unanswered.issue);

  // Item 12: the adding button is shown and disabled rather than hidden, and
  // the waiting line carries the count — a person must be able to see what
  // finishing looks like before they have finished. The old "Answer all N"
  // sentence went with it (item 40).
  expect(screen.getByRole("button", { name: ADD }).disabled).toBe(true);
  expect(screen.getByRole("button", { name: DISCARD }).disabled).toBe(false);
  expect(screen.getByText(/1 decision to answer/)).toBeTruthy();
  expect(screen.queryByText(/answer all/i)).toBeNull();
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

  render(<ReviewScreen projectId="" runId={runId} />);
  await openSection(/^run/i);

  expect(await screen.findByRole("button", { name: ADD })).toBeTruthy();
  expect(screen.getByRole("button", { name: DISCARD })).toBeTruthy();
});
