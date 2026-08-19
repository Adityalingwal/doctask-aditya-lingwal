// A finding card carries two labelled blocks — the finding itself, and what
// Approve and Reject will do. Each used to size its own label column from its
// own labels, so the values started at two different places down one card and
// nothing lined up. One shared column is what makes the card read as a column
// of values rather than as two lists that happen to sit above each other.
import { render } from "@testing-library/react";
import { expect, test } from "vitest";

import Question from "../src/Question.jsx";
import { findingDecisionReply } from "./server_replies.js";

const LABEL_COLUMN = "decision-lines";

test("both labelled blocks of a finding card use one label column", () => {
  const { container } = render(
    <Question
      decision={findingDecisionReply()}
      reviewing={false}
      answering={false}
      onAnswer={() => {}}
    />,
  );

  const blocks = Array.from(container.querySelectorAll("dl"));

  expect(blocks).toHaveLength(2);
  for (const block of blocks) {
    expect(block.classList.contains(LABEL_COLUMN)).toBe(true);
  }
});
