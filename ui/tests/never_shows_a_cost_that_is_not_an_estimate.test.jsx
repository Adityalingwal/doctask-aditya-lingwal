import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import {
  costAndTimingReply,
  runId,
  runReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

async function screenShowing(costAndTiming) {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: `/runs/${runId}`,
        reply: { body: runReply({ cost_and_timing: costAndTiming }) },
      },
    ]),
  );
  render(<ReviewScreen runId={runId} />);
  await openSection(/cost and timing/i);
  return screen.findByRole("region", { name: /cost and timing/i });
}

test("the cost the server reported is shown as an estimate and never as a bill", async () => {
  const reported = costAndTimingReply();
  const section = await screenShowing(reported);

  expect(section.textContent).toContain(reported.estimated_cost_usd);
  expect(section.textContent).toMatch(/estimate/i);
  expect(section.textContent).toMatch(/not a bill/i);
  for (const stage of reported.stages) {
    expect(section.textContent).toContain(stage.stage);
    expect(section.textContent).toContain(String(stage.seconds));
  }
  expect(section.textContent).toContain(String(reported.tokens.prompt));
  expect(section.textContent).toContain(String(reported.total_seconds));
});

test("a run whose model reported no tokens shows the cost as unknown, never as zero", async () => {
  const reported = costAndTimingReply({
    tokens: {
      prompt: null,
      completion: null,
      calls_reporting_usage: 0,
      calls_without_usage: 3,
    },
    estimated_cost_usd: null,
    cost_unknown_reason:
      "the model reported no token count for this run's 3 call(s), so no cost "
      + "can be estimated from them.",
  });
  const section = await screenShowing(reported);

  expect(section.textContent).toMatch(/unknown/i);
  expect(section.textContent).toContain(reported.cost_unknown_reason);
  expect(section.textContent).not.toMatch(/0\.0+\b/);
  expect(section.textContent).not.toMatch(/\$\s*0/);
  expect(section.textContent).not.toMatch(/null/);
});
