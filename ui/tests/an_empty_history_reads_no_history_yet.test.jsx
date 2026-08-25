// A row whose audit trail is empty is not a failure and not a refusal. The
// server answers 200 with no entries, and the row's own panel — the one place
// a history is read since item 6a — says so in one line, never an error box
// and never a blank space a reader has to interpret.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import RowDrawer from "../src/RowDrawer.jsx";
import { registerReply } from "./server_replies.js";

test("an_empty_history_reads_no_history_yet", () => {
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
  fireEvent.click(within(drawer).getByRole("button", { name: /history/i }));

  expect(within(drawer).getByText("No history yet.")).toBeTruthy();
  expect(within(drawer).queryByRole("alert")).toBeNull();
  expect(drawer.querySelectorAll(".border-danger")).toHaveLength(0);
});
