import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  exportReply,
  projectsReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("a run the server reports running is not shown as finished anywhere on the screen", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ status: "running", stage: "extract" }) },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  const stages = await screen.findByRole("region", { name: /stages/i });

  // Screen 3: the identifier lines above the strip — run, project, status —
  // are gone, so the run's own status is not printed as text here at all;
  // what stands in for it is the active stage's own box reading "working".
  expect(stages.textContent).toContain("extract");
  expect(stages.textContent).toContain("working");
  expect(document.body.textContent).not.toMatch(/finished|complete|\bdone\b/i);
});

test("the project's register panel says nothing has been added yet rather than showing one", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      { method: "GET", path: "/projects", reply: { body: projectsReply() } },
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ status: "running", stage: "match", exported: false }) },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  const register = await screen.findByRole("region", { name: /register/i });

  expect(within(register).queryByRole("table")).toBeNull();
  expect(register.textContent).toMatch(/nothing has been added to this register yet/i);
  expect(register.textContent).not.toContain(exportReply().rows[0].cells.what_was_asked);
});
