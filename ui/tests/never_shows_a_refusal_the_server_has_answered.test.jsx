import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { runId, runReply, serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const UNKNOWN_RUN = "11111111-2222-4333-8444-555566667777";
const REFUSAL =
  `Run ${UNKNOWN_RUN} does not exist — check the id, or start a run with `
  + "POST /runs and use the id it returns.";

test("a refusal about one run is gone once another run is read successfully", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: `/runs/${UNKNOWN_RUN}`,
        reply: { status: 404, body: { detail: REFUSAL } },
      },
      { method: "GET", path: `/runs/${runId}`, reply: { body: runReply() } },
    ]),
  );

  render(<ReviewScreen runId={UNKNOWN_RUN} />);
  await screen.findByRole("alert");

  fireEvent.change(screen.getByLabelText(/run id/i), {
    target: { value: runId },
  });
  fireEvent.click(screen.getByRole("button", { name: /show run/i }));
  await screen.findByRole("region", { name: /stages/i });

  // The server answered for this run and refused nothing, so the refusal it
  // gave about the other one must not still be on the screen beside it.
  expect(screen.queryByRole("alert")).toBeNull();
  expect(document.body.textContent).not.toContain(REFUSAL);
});
