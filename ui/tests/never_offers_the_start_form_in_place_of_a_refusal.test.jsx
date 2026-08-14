// L1 — the form appears only when the run list read succeeded and returned
// zero runs. If the application could not be reached, the reviewer must see
// that refusal, never a form implying everything is fine.
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("never_offers_the_start_form_in_place_of_a_refusal", async () => {
  vi.stubGlobal(
    "fetch",
    async () => {
      throw new TypeError("Failed to fetch");
    },
  );

  render(<ReviewScreen />);

  await waitFor(() => {
    expect(screen.getByText(/did not reach the application/i)).toBeTruthy();
  });

  expect(screen.queryByLabelText(/project name/i)).toBeNull();
  expect(screen.queryByLabelText(/folder/i)).toBeNull();
  expect(screen.queryByRole("button", { name: /start run/i })).toBeNull();
});

// The same rule at the one moment it is easiest to break: before the first
// read has come back, "no runs" and "not asked yet" look identical in state —
// an empty list and no refusal. The form must wait for an actual answer, or a
// reviewer whose application is slow or down can type into it and submit.
test("never_offers_the_start_form_before_the_run_list_has_answered", async () => {
  vi.stubGlobal("fetch", () => new Promise(() => {}));

  render(<ReviewScreen />);

  expect(screen.queryByLabelText(/project name/i)).toBeNull();
  expect(screen.queryByLabelText(/folder/i)).toBeNull();
  expect(screen.queryByRole("button", { name: /start run/i })).toBeNull();
});

// Confirms the passing case really is the empty-and-answered one, so the
// refusal test above is not passing only because the form is never rendered
// at all.
test("the form does appear once the list read succeeds with zero runs", async () => {
  vi.stubGlobal("fetch", serverAnswering([{ method: "GET", path: "/runs", reply: { body: { runs: [] } } }]));

  render(<ReviewScreen />);

  await waitFor(() => {
    expect(screen.getByLabelText(/project name/i)).toBeTruthy();
  });
});
