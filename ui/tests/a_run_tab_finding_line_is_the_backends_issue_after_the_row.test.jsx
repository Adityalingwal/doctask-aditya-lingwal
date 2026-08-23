// The Run tab's rules-and-findings block prints each finding as the history
// style's data join — `Row N · <issue>` — with the issue sentence exactly as
// the backend wrote it. The screen adds no dash, no rule id, and does not
// repeat the evidence beside it: the decision card already shows that in full.
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { Examine } from "../src/Register.jsx";
import { examineReply } from "./server_replies.js";

test("a_run_tab_finding_line_is_the_backends_issue_after_the_row", () => {
  const issue =
    "testing-feedback-12-aug.md was read, and it says nothing about this requirement.";
  const examine = examineReply({
    findings: [
      {
        finding_id: "f-1",
        row_number: 6,
        rule_id: "R4",
        rule_text: "Every written requirement must have a testing outcome.",
        issue,
        evidence: "Not known yet",
        question: "",
        outcome: null,
      },
    ],
  });

  render(<Examine examine={examine} />);

  expect(screen.getByText(`Row 6 · ${issue}`)).toBeTruthy();
  const block = screen.getByText(`Row 6 · ${issue}`).textContent;
  expect(block).not.toContain("(");
  expect(block).not.toContain("R4");
  expect(block).not.toContain("—");
});
