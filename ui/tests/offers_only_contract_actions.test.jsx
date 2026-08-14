import { render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  decisionReply,
  exportReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const ALLOWED_BUTTONS = ["show run", "approve", "reject", "finish review"];

test("the screen offers approve, reject and finish review and no other action over a run", async () => {
  const decisions = [
    decisionReply({ outcome: "approved" }),
    decisionReply({
      decision_id: "3d5f7b91-2222-4c33-9444-555566667777",
      kind: "export",
      question: "Export the register for this run?",
      outcome: "approved",
    }),
  ];
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: {
          body: runReply({ status: "done", stage: "commit", decisions, exported: true }),
        },
      },
      { method: "GET", path: `/runs/${runId}/export`, reply: { body: exportReply() } },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  await screen.findByRole("button", { name: /finish review/i });

  const offered = screen
    .getAllByRole("button")
    .map((button) => button.textContent.trim().toLowerCase());
  expect(offered.every((label) => ALLOWED_BUTTONS.includes(label))).toBe(true);
  expect(offered.filter((label) => label === "approve").length).toBe(decisions.length);
  expect(offered.filter((label) => label === "reject").length).toBe(decisions.length);
});

test("no control answers more than one decision at a time and no register cell can be edited by hand", async () => {
  const decisions = [
    decisionReply(),
    decisionReply({
      decision_id: "4e6a8c02-3333-4d44-8555-666677778888",
      kind: "finding",
      question: "Row 3 cites no source. Attach this finding to it?",
    }),
  ];
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ decisions, exported: true }) },
      },
      { method: "GET", path: `/runs/${runId}/export`, reply: { body: exportReply() } },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  const register = await screen.findByRole("region", { name: /register/i });

  expect(within(register).queryAllByRole("textbox")).toHaveLength(0);
  expect(within(register).queryAllByRole("button")).toHaveLength(0);
  expect(register.querySelectorAll("[contenteditable]")).toHaveLength(0);
  expect(
    screen.queryByRole("button", { name: /approve all|reject all|approve everything|submit all/i }),
  ).toBeNull();
  expect(screen.queryByRole("button", { name: /export|commit|start run/i })).toBeNull();
});
