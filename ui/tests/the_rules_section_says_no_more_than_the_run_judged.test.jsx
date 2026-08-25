// A run that judged nothing must not report a clean register. When no rule
// ran the section says so and stops; only a run that actually applied a rule
// may go on to report what it found — or that it found nothing.
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { Examine } from "../src/Register.jsx";
import { examineReply } from "./server_replies.js";

const ONE_RULE = [
  { id: "R1", text: "Every requirement must have a written scope entry." },
];

test("a_run_that_applied_no_rule_says_only_that_no_rule_ran", () => {
  const { container } = render(
    <Examine examine={examineReply({ rules: [], findings: [] })} />,
  );

  expect(container.textContent.trim()).toBe("No rule ran.");
});

test("a_run_that_applied_rules_and_found_nothing_says_no_findings", () => {
  render(<Examine examine={examineReply({ rules: ONE_RULE, findings: [] })} />);

  expect(screen.getByText("1 rule ran against 5 rows")).toBeTruthy();
  expect(screen.getByText("No findings.")).toBeTruthy();
});

test("a_run_that_raised_a_finding_still_prints_it_after_the_row", () => {
  const issue = "26-march-scope.md was read, and it says nothing about this ask.";
  render(
    <Examine
      examine={examineReply({
        rules: ONE_RULE,
        findings: [
          {
            finding_id: "f-1",
            row_number: 4,
            rule_id: "R1",
            rule_text: ONE_RULE[0].text,
            issue,
            evidence: "Not mentioned",
            question: "",
            outcome: null,
          },
        ],
      })}
    />,
  );

  expect(screen.getByText(`Row 4 · ${issue}`)).toBeTruthy();
  expect(screen.queryByText("No findings.")).toBeNull();
});
