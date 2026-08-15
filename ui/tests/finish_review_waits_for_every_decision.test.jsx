import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import {
  decisionReply,
  projectsReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const answered = decisionReply({ outcome: "approved" });
const unanswered = decisionReply({
  decision_id: "5f7b9d13-4444-4e55-8666-777788889999",
  kind: "export",
  question: "Add this run's changes to the register?",
});

test("finishing the review is not offered while one decision is still unanswered", async () => {
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
  await screen.findByText(unanswered.question);

  expect(screen.queryByRole("button", { name: /finish review/i })).toBeNull();
  expect(screen.getByText("Answer all 1 to finish this review.")).toBeTruthy();
});

test("finishing the review is offered once the server reports every decision answered", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: {
          body: runReply({
            decisions: [answered, decisionReply({ ...unanswered, outcome: "rejected" })],
          }),
        },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  await openSection(/decisions/i);

  expect(await screen.findByRole("button", { name: /finish review/i })).toBeTruthy();
});
