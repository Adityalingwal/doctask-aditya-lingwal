// The line under a run's decisions is read by someone who has never seen the
// pipeline, and it appears on every run the server will not accept an answer
// for — a run still working, a failed one, and one whose review is over. It
// must therefore say what is true of all three without borrowing "at review",
// which is a stage name from inside the system.
import { render, screen } from "@testing-library/react";
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

const answered = decisionReply({ outcome: "approved" });

function screenShowingRun(overrides) {
  const listed = projectReply();
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: {
          body: projectsReply({
            projects: [
              projectReply({ runs: [{ ...listed.runs[0], ...overrides }] }),
            ],
          }),
        },
      },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: {
          body: runReply({ decisions: [answered], ...overrides }),
        },
      },
    ]),
  );
  render(<ReviewScreen runId={runId} />);
}

test("a finished run says its decisions can be read but not changed", async () => {
  screenShowingRun({ status: "done", stage: "commit" });
  await openSection(/decisions/i);

  expect(
    await screen.findByText(/decisions can be read here but not changed/i),
  ).toBeTruthy();
});

test("a run that cannot be answered never explains itself with a stage name", async () => {
  screenShowingRun({ status: "done", stage: "commit" });
  await openSection(/decisions/i);
  await screen.findByText(answered.question);

  expect(screen.queryByText(/at review/i)).toBeNull();
});
