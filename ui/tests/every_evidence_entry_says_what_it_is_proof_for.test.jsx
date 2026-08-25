// The row panel's evidence entries name the cells they stand behind, and each
// pill row is labelled so a reader is never left guessing what the pills are.
// An entry that records a document's silence is evidence too, and carries the
// same label.
import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import RowDrawer from "../src/RowDrawer.jsx";
import { registerReply } from "./server_replies.js";

const PROOF_FOR = "Proof for";

test("every_evidence_entry_wears_the_proof_for_label_absences_included", () => {
  const exported = registerReply();
  const row = exported.rows[0];
  render(
    <RowDrawer
      row={row}
      columns={exported.columns}
      history={[]}
      onClose={() => {}}
    />,
  );

  const drawer = screen.getByRole("complementary", { name: "Row 1" });
  // The fixture's second entry is an absence: no place, no words, only the
  // sentence saying which document was read and stayed silent.
  expect(row.evidence.length).toBe(2);
  expect(row.evidence[1].quote).toBeNull();
  expect(within(drawer).getAllByText(PROOF_FOR).length).toBe(row.evidence.length);
});

test("an_evidence_source_line_leads_with_the_file_and_follows_with_the_place", () => {
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
  expect(within(drawer).getByText("12-march-scope.md")).toBeTruthy();
  expect(
    within(drawer).getByText(', under "Section 2 — Applicant portal"'),
  ).toBeTruthy();
});
