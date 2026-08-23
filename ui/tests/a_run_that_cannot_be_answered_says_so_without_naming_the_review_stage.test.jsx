// A run the server will not accept an answer for — one still working, a
// failed one, one whose review is over — says so by offering nothing to
// answer with. The sentence that used to sit under its decisions is gone
// (item 5): it explained the pipeline to someone who has never seen it, and
// the absent buttons already say the same thing. Nothing left on the panel
// borrows "at review", which is a stage name from inside the system.
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
  render(<ReviewScreen projectId="" runId={runId} />);
}

test("a finished run offers nothing to answer and explains nothing", async () => {
  screenShowingRun({ status: "done", stage: "commit" });
  await openSection(/^run/i);
  await screen.findByText("Is this the same ask as row 2?");

  expect(screen.queryByRole("button", { name: /^approve$/i })).toBeNull();
  expect(screen.queryByRole("button", { name: /^reject$/i })).toBeNull();
  expect(screen.queryByText(/not waiting for an answer/i)).toBeNull();
  expect(screen.queryByText(/read here but not changed/i)).toBeNull();
});

test("a run that cannot be answered never explains itself with a stage name", async () => {
  screenShowingRun({ status: "done", stage: "commit" });
  await openSection(/^run/i);
  await screen.findByText("Is this the same ask as row 2?");

  expect(screen.queryByText(/at review/i)).toBeNull();
});
