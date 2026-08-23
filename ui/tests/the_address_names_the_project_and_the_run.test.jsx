// Items 9 / S18 / 49: a link to what is on screen is a link a reviewer can
// keep, so both ids are written into the address and both are read back out
// of it. Selecting a project opens its newest run at once, which is why the
// address carries two ids rather than one.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

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

const NEWEST_RUN = "99999999-8888-4777-8666-555544443333";

afterEach(() => {
  vi.unstubAllGlobals();
});

beforeEach(() => {
  window.history.replaceState(null, "", "/ui/");
});

function twoRuns() {
  return projectReply({
    run_count: 2,
    runs: [
      {
        run_id: NEWEST_RUN,
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

function answering(project) {
  return serverAnswering([
    {
      method: "GET",
      path: "/projects",
      reply: { body: projectsReply({ projects: [project] }) },
    },
    { method: "GET", path: `/runs/${runId}`, reply: { body: runReply() } },
    {
      method: "GET",
      path: `/runs/${NEWEST_RUN}`,
      reply: {
        body: runReply({ run_id: NEWEST_RUN, status: "done", stage: "commit" }),
      },
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
  ]);
}

function address() {
  return window.location.search;
}

test("selecting a project opens its newest run and writes both ids", async () => {
  vi.stubGlobal("fetch", answering(twoRuns()));
  render(<ReviewScreen projectId="" runId="" />);

  fireEvent.click(await screen.findByText(twoRuns().name));

  await waitFor(() => {
    expect(address()).toContain(`project=${projectId}`);
  });
  await waitFor(() => {
    expect(address()).toContain(`run=${NEWEST_RUN}`);
  });
});

test("a project with no runs keeps its empty state and names only itself", async () => {
  const neverRan = projectReply({ run_count: 0, runs: [], most_recent_run_at: null });
  vi.stubGlobal("fetch", answering(neverRan));
  render(<ReviewScreen projectId="" runId="" />);

  fireEvent.click(await screen.findByText(neverRan.name));

  expect(await screen.findByText(/this project has not run yet/i)).toBeTruthy();
  await waitFor(() => {
    expect(address()).toBe(`?project=${projectId}`);
  });
});

test("a project id alone in the address opens that project's newest run", async () => {
  vi.stubGlobal("fetch", answering(twoRuns()));
  render(<ReviewScreen projectId={projectId} runId="" />);

  await waitFor(() => {
    expect(address()).toContain(`run=${NEWEST_RUN}`);
  });
  expect(address()).toContain(`project=${projectId}`);
});

test("both ids in the address open that run inside that project", async () => {
  vi.stubGlobal("fetch", answering(twoRuns()));
  render(<ReviewScreen projectId={projectId} runId={runId} />);

  await waitFor(() => {
    expect(address()).toBe(`?project=${projectId}&run=${runId}`);
  });
});

test("a run id alone in the address still opens that run, and names its project", async () => {
  vi.stubGlobal("fetch", answering(twoRuns()));
  render(<ReviewScreen projectId="" runId={runId} />);

  // The project is the server's own answer to the run read, not something
  // the address had to carry.
  await waitFor(() => {
    expect(address()).toBe(`?project=${projectId}&run=${runId}`);
  });
});
