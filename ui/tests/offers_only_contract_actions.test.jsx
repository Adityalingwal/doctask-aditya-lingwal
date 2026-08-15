import { render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import {
  decisionReply,
  exportReply,
  projectsReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const ALLOWED_BUTTONS = ["show run", "approve", "reject", "finish review"];

const decisions = [
  decisionReply({ outcome: "approved" }),
  decisionReply({
    decision_id: "3d5f7b91-2222-4c33-9444-555566667777",
    kind: "export",
    question: "Export the register for this run?",
    outcome: "approved",
  }),
];

test("a run at review offers approve, reject and finish review and no other action", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ decisions }) },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  await openSection(/decisions/i);
  await screen.findByRole("button", { name: /finish review/i });

  // Scoped to the reading pane: the screen's own chrome — Add project,
  // collapse the runs column — offers buttons too, and this test is only
  // about what a run's own content may act on.
  const readingPane = screen.getByRole("main");
  const offered = within(readingPane)
    .getAllByRole("button")
    .map((button) => button.textContent.trim().toLowerCase());
  expect(offered.every((label) => ALLOWED_BUTTONS.includes(label))).toBe(true);
  expect(offered.filter((label) => label === "approve")).toHaveLength(decisions.length);
  expect(offered.filter((label) => label === "reject")).toHaveLength(decisions.length);
  expect(
    screen.queryByRole("button", {
      name: /approve all|reject all|approve everything|submit all/i,
    }),
  ).toBeNull();
});

test("an exported register offers no control at all and no cell that can be edited by hand", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: {
          body: runReply({
            status: "done",
            stage: "commit",
            decisions,
            exported: true,
          }),
        },
      },
      { method: "GET", path: `/runs/${runId}/export`, reply: { body: exportReply() } },
    ]),
  );

  render(<ReviewScreen runId={runId} />);

  // The run has left review, so the server refuses an answer to any of its
  // decisions; the section that would carry them offers none.
  await openSection(/decisions/i);
  expect(screen.queryByRole("button", { name: /^approve$|^reject$/i })).toBeNull();

  await openSection(/register/i);
  const register = await screen.findByRole("region", { name: /register/i });

  expect(within(register).queryAllByRole("textbox")).toHaveLength(0);
  expect(within(register).queryAllByRole("button")).toHaveLength(0);
  expect(register.querySelectorAll("[contenteditable]")).toHaveLength(0);
  expect(screen.queryByRole("button", { name: /export|commit|start run/i })).toBeNull();
});
