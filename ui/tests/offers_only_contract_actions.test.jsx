import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import {
  decisionReply,
  observationMatchReply,
  projectId,
  projectReply,
  projectsReply,
  registerReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const ALLOWED_BUTTONS = [
  "show run",
  "approve",
  "reject",
  "add this run's changes to the register",
  "discard this run's changes",
];

// The export gate is not among them: it is written by the ending press and is
// never offered as a question, so a run at review shows only its own.
const decisions = [
  decisionReply({ outcome: "approved" }),
  observationMatchReply({ outcome: "approved" }),
];

test("a run at review offers approve, reject and the two endings and no other action", async () => {
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

  render(<ReviewScreen projectId="" runId={runId} />);
  await openSection(/^run/i);
  await screen.findByRole("button", { name: /add this run's changes to the register/i });

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

// The register is the project's own panel (section 2.3), reached from the
// Register entry above a project's runs — not from a run's own tabs, which
// no longer include one.
test("the register panel offers no control at all and no cell that can be edited by hand", async () => {
  const exported = registerReply();
  const exportedRun = { ...projectReply().runs[0], row_count: exported.rows.length };

  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [projectReply({ runs: [exportedRun] })] }) },
      },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: {
          body: runReply({ status: "done", stage: "commit", decisions, exported: true }),
        },
      },
      { method: "GET", path: `/projects/${projectId}/register`, reply: { body: exported } },
    ]),
  );

  render(<ReviewScreen projectId="" runId={runId} />);

  // The run has left review, so the server refuses an answer to any of its
  // decisions; the section that would carry them offers none.
  await openSection(/^run/i);
  expect(screen.queryByRole("button", { name: /^approve$|^reject$/i })).toBeNull();

  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  const register = await screen.findByRole("region", { name: /register/i });

  expect(within(register).queryAllByRole("textbox")).toHaveLength(0);
  expect(within(register).queryAllByRole("button")).toHaveLength(0);
  expect(register.querySelectorAll("[contenteditable]")).toHaveLength(0);
  expect(screen.queryByRole("button", { name: /export|commit|start run/i })).toBeNull();
});
