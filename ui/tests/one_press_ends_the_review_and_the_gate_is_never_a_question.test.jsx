import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import {
  decisionReply,
  projectReply,
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
const unanswered = decisionReply({
  decision_id: "5f7b9d13-4444-4e55-8666-777788889999",
  question:
    "Is 'Operations are emailed on submit' the same requirement as row 3, "
    + "'Email the operations team'?",
  row_number: 3,
});
// The gate is written when the button is pressed, so a run that has already
// been finished carries an answered export decision in the same payload.
const gate = decisionReply({
  decision_id: "3d5f7b91-2222-4c33-9444-555566667777",
  kind: "export",
  question: "Add this run's changes to the register?",
  outcome: "approved",
  row_number: null,
});

function screenShowing(decisions, overrides = {}) {
  // A run's status is printed in the runs column, which reads `GET /projects`,
  // so a test about the word on screen has to move it in both answers.
  const listed = projectReply();
  const fetching = serverAnswering([
    {
      method: "GET",
      path: "/projects",
      reply: {
        body: projectsReply({
          projects: [
            projectReply({
              runs: [{ ...listed.runs[0], ...overrides }],
            }),
          ],
        }),
      },
    },
    {
      method: "GET",
      path: `/runs/${runId}`,
      reply: { body: runReply({ decisions, ...overrides }) },
    },
    {
      method: "POST",
      path: `/runs/${runId}/finish-review`,
      reply: { body: { run_id: runId, status: "review finished" } },
    },
  ]);
  vi.stubGlobal("fetch", fetching);
  render(<ReviewScreen runId={runId} />);
  return fetching;
}

test("the export gate is never shown as a question with answers to give", async () => {
  screenShowing([answered, gate]);
  await openSection(/decisions/i);
  await screen.findByText(answered.question);

  expect(screen.queryByText(gate.question)).toBeNull();
  expect(screen.queryByText("export")).toBeNull();
});

test("neither ending is offered while one decision is still unanswered", async () => {
  screenShowing([answered, unanswered]);
  await openSection(/decisions/i);
  await screen.findByText(unanswered.question);

  expect(screen.queryByRole("button", { name: ADD })).toBeNull();
  expect(screen.queryByRole("button", { name: DISCARD })).toBeNull();
  expect(screen.getByText("Answer all 1 to finish this review.")).toBeTruthy();
});

test("both endings are offered once the server reports every decision answered", async () => {
  screenShowing([answered]);
  await openSection(/decisions/i);

  expect(await screen.findByRole("button", { name: ADD })).toBeTruthy();
  expect(screen.getByRole("button", { name: DISCARD })).toBeTruthy();
});

test("pressing add sends the answer that adds this run's changes to the register", async () => {
  const fetching = screenShowing([answered]);
  await openSection(/decisions/i);
  fireEvent.click(await screen.findByRole("button", { name: ADD }));

  await waitFor(() => expect(_finishCalls(fetching)).toHaveLength(1));
  expect(JSON.parse(_finishCalls(fetching)[0].body)).toEqual({
    add_to_register: true,
  });
});

test("pressing discard sends the answer that discards this run's changes", async () => {
  const fetching = screenShowing([answered]);
  await openSection(/decisions/i);
  fireEvent.click(await screen.findByRole("button", { name: DISCARD }));

  await waitFor(() => expect(_finishCalls(fetching)).toHaveLength(1));
  expect(JSON.parse(_finishCalls(fetching)[0].body)).toEqual({
    add_to_register: false,
  });
});

test("a discarded run is shown as discarded, in the word the server stored", async () => {
  screenShowing([answered, gate], { status: "discarded", stage: "commit" });

  expect(await screen.findByText("discarded")).toBeTruthy();
});

function _finishCalls(fetching) {
  return fetching.calls.filter(
    (call) => call.method === "POST" && call.path.endsWith("/finish-review"),
  );
}
