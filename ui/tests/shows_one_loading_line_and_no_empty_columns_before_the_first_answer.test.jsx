// Screen 10 — before `GET /projects` has actually answered once, the screen
// draws exactly one thing: a centred loading line. No empty projects column,
// no empty runs column, no placeholder box for either — there is no timer,
// no delay and no threshold, only the one boolean that says whether the
// first read has answered.
import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("shows_one_loading_line_and_no_empty_columns_before_the_first_answer", () => {
  // A promise that never resolves: the first read is permanently in flight.
  vi.stubGlobal("fetch", () => new Promise(() => {}));

  render(<ReviewScreen />);

  expect(screen.getByText("Loading…")).toBeTruthy();
  expect(screen.queryByRole("navigation")).toBeNull();
  expect(screen.queryByRole("button", { name: /add project/i })).toBeNull();
  expect(screen.queryByText("No project created yet.")).toBeNull();
  expect(screen.queryByRole("main")).toBeNull();
});
