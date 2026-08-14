import { render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { exportReply, runId, runReply, serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("a run the server reports running is not shown as finished anywhere on the screen", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ status: "running", stage: "extract" }) },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  const stages = await screen.findByRole("region", { name: /stages/i });

  expect(stages.textContent).toContain("running");
  expect(stages.textContent).toContain("extract");
  expect(document.body.textContent).not.toMatch(/finished|complete|\bdone\b/i);
});

test("the register section says the register is not exported rather than showing one", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ status: "running", stage: "match", exported: false }) },
      },
    ]),
  );

  render(<ReviewScreen runId={runId} />);
  const register = await screen.findByRole("region", { name: /register/i });

  expect(within(register).queryByRole("table")).toBeNull();
  expect(register.textContent).toMatch(/not exported/i);
  expect(register.textContent).not.toContain(exportReply().rows[0].cells.what_was_asked);
});
