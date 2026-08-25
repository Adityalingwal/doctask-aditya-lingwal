// The Add-will-write block states what the adding press would write, in the
// order and the words the server sent. The one sentence the screen composes is
// the count of questions still open, and it renders that from the count the
// payload carries — never from a list it has counted itself.
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import RunTab from "../src/RunTab.jsx";
import { decisionReply, runReply } from "./server_replies.js";

const FIRST_LINE = "Row 1 · Written down → Yes — client-requirements-v1.md.";
const SECOND_LINE =
  "Row 7 · Written down → Not mentioned — client-requirements-v1.md was read "
  + "and does not mention this ask.";
const ADD_LABEL = "Add this run's changes to the register";

// Every line the block prints, read whole: the arrow marker is CSS, and the
// source tail is only a second colour on the one sentence the server sent.
function preview() {
  return [
    ...screen.getByRole("list", { name: "Add will write" }).querySelectorAll("li"),
  ].map((line) => line.textContent.trim());
}

function runTab(run, decisions = []) {
  return render(
    <RunTab
      run={run}
      decisions={decisions}
      waiting={run.open_decisions}
      answering={false}
      onAnswer={() => {}}
      onFinish={() => {}}
    />,
  );
}

test("the_add_will_write_block_prints_the_servers_entries_in_the_servers_order", () => {
  runTab(
    runReply({
      add_will_write: [
        { kind: "row change", text: FIRST_LINE },
        { kind: "absence", text: SECOND_LINE },
      ],
    }),
  );

  expect(preview()).toEqual([FIRST_LINE, SECOND_LINE]);
});

test("the_add_will_write_block_counts_open_decisions_and_never_predicts_them", () => {
  const { unmount } = runTab(
    runReply({
      open_decisions: 4,
      add_will_write: [{ kind: "row change", text: FIRST_LINE }],
      decisions: [],
    }),
    [decisionReply()],
  );

  expect(
    screen.getByText(
      "4 decisions are still open — what they change appears here as you answer.",
    ),
  ).toBeTruthy();
  unmount();

  runTab(
    runReply({
      open_decisions: 1,
      add_will_write: [{ kind: "row change", text: FIRST_LINE }],
    }),
    [decisionReply()],
  );
  expect(
    screen.getByText(
      "1 decision is still open — what they change appears here as you answer.",
    ),
  ).toBeTruthy();
});

test("the_add_will_write_block_says_nothing_about_decisions_once_all_are_answered", () => {
  runTab(
    runReply({
      open_decisions: 0,
      add_will_write: [{ kind: "nothing", text: "Nothing — the register stays as it is." }],
    }),
  );

  expect(screen.queryByText(/still open/)).toBeNull();
  expect(preview()).toEqual(["Nothing — the register stays as it is."]);
});

test("the_add_will_write_block_is_read_after_the_decisions_and_before_the_two_endings", () => {
  const { container } = runTab(
    runReply({
      open_decisions: 1,
      add_will_write: [{ kind: "row change", text: FIRST_LINE }],
    }),
    [decisionReply()],
  );

  const read = container.textContent;
  expect(read.indexOf("Is this the same ask as row 2?")).toBeLessThan(
    read.indexOf(FIRST_LINE),
  );
  expect(read.indexOf(FIRST_LINE)).toBeLessThan(read.indexOf(ADD_LABEL));
});

test("the_add_will_write_block_is_absent_from_a_run_that_has_ended", () => {
  runTab(
    runReply({ status: "done", exported: true, add_will_write: null, open_decisions: 0 }),
  );

  expect(screen.queryByRole("list", { name: "Add will write" })).toBeNull();
});
