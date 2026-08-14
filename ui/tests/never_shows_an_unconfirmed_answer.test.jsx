import { render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  decisionReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("a refused answer leaves the decision unanswered on screen and shows the server's refusal", async () => {
  const decision = decisionReply();
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ decisions: [decision] }) },
      },
      {
        method: "POST",
        path: `/runs/${runId}/decisions`,
        reply: {
          status: 409,
          body: {
            detail:
              "this run's review has already finished, so no decision can be "
              + `recorded against it — poll GET /runs/${runId} for what it did next.`,
          },
        },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  const approve = await screen.findByRole("button", { name: /^approve$/i });

  await act(async () => {
    approve.click();
  });

  await waitFor(() => {
    expect(screen.getByText(/review has already finished/i)).toBeTruthy();
  });
  const question = screen.getByText(decision.question).closest("li");
  expect(question.textContent).toMatch(/unanswered/i);
  expect(question.textContent).not.toMatch(/approved/i);
});

test("an answered decision reads back the outcome the server returned, not the button that was pressed", async () => {
  const decision = decisionReply();
  let answeredOutcome = null;
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: `/runs/${runId}`,
        // The server records "rejected" whatever was pressed; the screen must
        // report what it reads back, never what was clicked.
        reply: () => ({
          body: runReply({
            decisions: [decisionReply({ outcome: answeredOutcome })],
          }),
        }),
      },
      {
        method: "POST",
        path: `/runs/${runId}/decisions`,
        reply: () => {
          answeredOutcome = "rejected";
          return { body: { decision_id: decision.decision_id, outcome: "approved" } };
        },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  const approve = await screen.findByRole("button", { name: /^approve$/i });

  await act(async () => {
    approve.click();
  });

  await waitFor(() => {
    const question = screen.getByText(decision.question).closest("li");
    expect(question.textContent).toMatch(/rejected/i);
  });
  const question = screen.getByText(decision.question).closest("li");
  expect(question.textContent).not.toMatch(/approved/i);
});
