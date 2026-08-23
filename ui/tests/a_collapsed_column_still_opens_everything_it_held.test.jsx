// Items 2, 3, 7, 14 and 19. Both side columns collapse to a 3rem rail, and a
// rail is navigation rather than a reminder of what is open: every project and
// every run stays reachable from it, and the reading pane takes the width.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  projectId,
  projectReply,
  projectsReply,
  registerReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

const OTHER_RUN = "99999999-8888-4777-8666-555544443333";

afterEach(() => {
  vi.unstubAllGlobals();
});

function twoRuns() {
  return projectReply({
    run_count: 2,
    runs: [
      {
        run_id: OTHER_RUN,
        run_number: 2,
        status: "done",
        stage: "commit",
        started_at: "2026-03-27T10:00:00+00:00",
        waiting_decisions: 0,
        finished_stages: [
          "ingest",
          "extract",
          "match",
          "examine",
          "review",
          "commit",
        ],
        row_count: 1,
      },
      projectReply().runs[0],
    ],
  });
}

function screenShowing(projects) {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects }) },
      },
      { method: "GET", path: `/runs/${runId}`, reply: { body: runReply() } },
      {
        method: "GET",
        path: `/runs/${OTHER_RUN}`,
        reply: { body: runReply({ run_id: OTHER_RUN, status: "done", stage: "commit" }) },
      },
      {
        method: "GET",
        path: `/projects/${projectId}/register`,
        reply: { body: registerReply() },
      },
      {
        method: "GET",
        path: `/projects/${projectId}/history`,
        reply: { body: { entries: [] } },
      },
    ]),
  );
  render(<ReviewScreen projectId="" runId={runId} />);
}

test("a run is marked by its plain number, expanded and collapsed alike", async () => {
  screenShowing([twoRuns()]);
  const runs = await screen.findByRole("navigation", { name: /runs/i });

  expect(within(runs).getAllByRole("link").map((link) => link.textContent)).toEqual(
    expect.arrayContaining([expect.stringMatching(/^2/), expect.stringMatching(/^1/)]),
  );
  expect(runs.textContent).not.toMatch(/#\d/);

  fireEvent.click(screen.getByRole("button", { name: /collapse the runs column/i }));
  const rail = await screen.findByRole("navigation", { name: /runs/i });
  expect(rail.textContent).not.toMatch(/#\d/);
});

test("the collapsed runs rail carries the register and every run", async () => {
  screenShowing([twoRuns()]);
  const runs = await screen.findByRole("navigation", { name: /runs/i });
  fireEvent.click(screen.getByRole("button", { name: /collapse the runs column/i }));
  const rail = await screen.findByRole("navigation", { name: /runs/i });

  const marks = within(rail)
    .getAllByRole("button")
    .filter((mark) => !mark.getAttribute("aria-label").includes("column"));
  expect(marks.map((mark) => mark.textContent)).toEqual(["R", "2", "1"]);
  // Every mark is clickable and says so.
  for (const mark of marks) {
    expect(mark.className).toContain("cursor-pointer");
    expect(mark.className).toContain("hover:");
  }

  fireEvent.click(within(rail).getByRole("button", { name: "Register" }));
  expect(await screen.findByRole("region", { name: /register/i })).toBeTruthy();
});

test("the collapsed runs rail opens a run", async () => {
  screenShowing([twoRuns()]);
  const runs = await screen.findByRole("navigation", { name: /runs/i });
  fireEvent.click(screen.getByRole("button", { name: /collapse the runs column/i }));
  const rail = await screen.findByRole("navigation", { name: /runs/i });

  fireEvent.click(within(rail).getByRole("button", { name: "Run 2" }));
  expect(window.location.search).toContain(`run=${OTHER_RUN}`);
});

test("the projects column collapses to a rail of marks that still open a project", async () => {
  const second = projectReply({
    project_id: "22222222-3333-4444-8555-666666666666",
    name: "Northside dental",
    source_folder_path: "sample-projects/northside-dental",
    runs: [],
    run_count: 0,
    most_recent_run_at: null,
  });
  screenShowing([twoRuns(), second]);

  const projects = await screen.findByRole("navigation", { name: /projects/i });
  const pane = document.querySelector(".lg\\:grid-cols-\\[13rem_12rem_1fr\\]");
  expect(pane).toBeTruthy();

  fireEvent.click(
    within(projects).getByRole("button", { name: /collapse the projects column/i }),
  );
  const rail = await screen.findByRole("navigation", { name: /projects/i });

  const marks = within(rail)
    .getAllByRole("button")
    .filter((mark) => !mark.getAttribute("aria-label").includes("column"));
  expect(marks.map((mark) => mark.getAttribute("aria-label"))).toEqual([
    "Acme intake portal",
    "Northside dental",
  ]);
  // The status mark travels with the project, so a run waiting for a person
  // is still visible with the column shut.
  expect(marks[0].textContent).toContain("◍");
  // The reading pane takes the width the column gave up.
  expect(
    document.querySelector(".lg\\:grid-cols-\\[3rem_12rem_1fr\\]"),
  ).toBeTruthy();

  fireEvent.click(marks[1]);
  expect(window.location.search).toContain(`project=${second.project_id}`);
});

test("a long project name wraps inside the column instead of overflowing it", async () => {
  const longName = projectReply({
    name: "Northside dental multi-site appointment and reminders programme",
  });
  screenShowing([longName]);

  const card = (await screen.findAllByText(longName.name))[0].closest("a");
  expect(card.querySelector(".break-words")).toBeTruthy();
  expect(card.className).not.toContain("whitespace-nowrap");
});
