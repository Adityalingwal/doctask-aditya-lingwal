// Never-do test for section 2.4: while a project holds no committed rows,
// the server answers the empty register and the project's Register panel
// shows the empty line, never an empty table.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  projectId,
  projectReply,
  projectsReply,
  registerReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("never_shows_a_register_before_a_run_has_added_to_it", async () => {
  const neverExported = projectReply({
    runs: [
      {
        run_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        run_number: 1,
        status: "running",
        stage: "extract",
        started_at: "2026-03-26T10:00:00+00:00",
        waiting_decisions: 0,
        finished_stages: ["ingest"],
        row_count: null,
      },
    ],
  });

  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [neverExported] }) },
      },
      {
        method: "GET",
        path: `/projects/${projectId}/register`,
        reply: {
          body: registerReply({ rows: [], exported_at: null, rules: null }),
        },
      },
    ]),
  );

  render(<ReviewScreen projectId="" runId="" />);

  fireEvent.click(await screen.findByText(neverExported.name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));

  const register = await screen.findByRole("region", { name: /register/i });
  await waitFor(() => {
    expect(register.textContent).toMatch(/nothing has been added to this register yet/i);
  });
  expect(within(register).queryByRole("table")).toBeNull();
});
