// Item 7. The row panel is the one place a register's audit trail is read, so
// its history reads like a page rather than a log: the run heading, then each
// document that touched this row in that run named once, then what it changed.
// The panel already says which row it is, so no line repeats it.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import RowDrawer from "../src/RowDrawer.jsx";
import { historyReply, registerReply } from "./server_replies.js";

function openHistory(entries) {
  const exported = registerReply();
  render(
    <RowDrawer
      row={exported.rows[0]}
      columns={exported.columns}
      history={entries}
      onClose={() => {}}
    />,
  );
  const drawer = screen.getByRole("complementary", { name: "Row 1" });
  fireEvent.click(within(drawer).getByRole("button", { name: /history/i }));
  return drawer;
}

test("each document that touched the row in one run is named once", () => {
  const drawer = openHistory(historyReply().entries);

  // The panel's own Evidence heading is an h4 too; the run headings are the
  // ones inside the history.
  const runs = [...drawer.querySelectorAll("h4")]
    .map((one) => one.textContent)
    .filter((one) => one.startsWith("Run "));
  expect(runs[0]).toContain("Run 2");
  expect(runs[1]).toContain("Run 1");

  const files = [...drawer.querySelectorAll("h5")].map((one) => one.textContent);
  expect(files).toEqual([
    "testing-feedback-25-mar.md",
    "26-march-scope.md",
    "meeting-notes-10-mar.md",
  ]);
});

test("an entry that came from no document sits under the run and names none", () => {
  const drawer = openHistory(historyReply().entries);

  const attached = [...drawer.querySelectorAll("li")].find((one) =>
    one.textContent.startsWith("Finding:"),
  );
  expect(attached.textContent).toBe(
    "Finding: Every requirement must have a written scope entry.",
  );
  expect(attached.querySelector("h5")).toBeNull();
});

test("no line inside the row panel repeats the row the panel already names", () => {
  const drawer = openHistory(historyReply().entries);

  expect(drawer.textContent).toContain("Status: Requested → Done");
  expect(drawer.textContent).not.toContain("Row 1 ·");
});

test("the row panel is wide enough to read a quote on one line", () => {
  const exported = registerReply();
  render(
    <RowDrawer
      row={exported.rows[0]}
      columns={exported.columns}
      history={[]}
      onClose={() => {}}
    />,
  );

  const drawer = screen.getByRole("complementary", { name: "Row 1" });
  expect(drawer.className).toContain("max-w-3xl");
  // A narrow window still gives the panel the whole width.
  expect(drawer.className).toContain("w-full");
});
