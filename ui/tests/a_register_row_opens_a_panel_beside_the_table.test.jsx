// Items 15, 16, 18, 20 and the 33 drawer lock. The register page is a table
// and a history, and what a row rests on is read in a panel that slides in
// over it — the table itself never moves, so a reader keeps their place.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  findingOnTheRegister,
  historyReply,
  projectId,
  projectReply,
  projectsReply,
  registerReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

const ROW_ASK = "Applicants upload supporting documents.";

function exportedProject(rowCount) {
  const run = { ...projectReply().runs[0], row_count: rowCount };
  return projectReply({ runs: [run] });
}

async function openRegister(exported, history) {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: {
          body: projectsReply({ projects: [exportedProject(exported.rows.length)] }),
        },
      },
      { method: "GET", path: `/projects/${projectId}/register`, reply: { body: exported } },
      {
        method: "GET",
        path: `/projects/${projectId}/history`,
        reply: { body: history ?? { entries: [] } },
      },
    ]),
  );
  render(<ReviewScreen projectId="" runId="" />);
  fireEvent.click(await screen.findByText(exportedProject(1).name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  return await screen.findByRole("region", { name: /register/i });
}

async function openTheRow(exported, history) {
  const panel = await openRegister(exported, history);
  fireEvent.click(await screen.findByText(ROW_ASK));
  return { panel, drawer: await screen.findByRole("complementary", { name: /row 1/i }) };
}

test("the first column is headed Row and the number stays in the cell", async () => {
  const panel = await openRegister(registerReply());

  const headings = within(panel).getAllByRole("columnheader");
  expect(headings[0].textContent).toBe("Row");
  expect(within(panel).getByRole("rowheader").textContent).toBe("1");
});

test("clicking a row opens a panel the table does not move for", async () => {
  const exported = registerReply();
  const { panel, drawer } = await openTheRow(exported);

  // The table is still there, unmoved, behind a dimmed backdrop.
  expect(within(panel).getByRole("table")).toBeTruthy();
  expect(screen.getByTestId("row-drawer-backdrop").className).toContain("bg-ink/40");
  for (const column of exported.columns) {
    expect(drawer.textContent).toContain(exported.rows[0].cells[column]);
  }
});

test("the close mark, Escape and the backdrop each close the panel", async () => {
  const closings = [
    async () => fireEvent.click(screen.getByRole("button", { name: /close/i })),
    async () => fireEvent.keyDown(window, { key: "Escape" }),
    async () => fireEvent.click(screen.getByTestId("row-drawer-backdrop")),
  ];
  for (const close of closings) {
    await openTheRow(registerReply());
    await close();
    expect(screen.queryByRole("complementary", { name: /row 1/i })).toBeNull();
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  }
});

test("evidence is one block per quote, in the order the payload sent them", async () => {
  const exported = registerReply();
  const { drawer } = await openTheRow(exported);

  const blocks = within(drawer)
    .getAllByRole("listitem")
    .map((item) => item.textContent);
  const [quoted, absent] = exported.rows[0].evidence;

  expect(blocks[0]).toContain(quoted.source_line);
  expect(blocks[0]).toContain(quoted.quote);
  expect(blocks[0]).toContain(quoted.cells[0]);
  // An absence shows the sentence in place of a quote, and names no place.
  expect(blocks[1]).toContain(absent.absence);
  expect(blocks[1]).toContain(absent.cells[0]);
  expect(blocks[1]).not.toContain("under");
});

test("a row with findings marks the table and lists them by their own id", async () => {
  const exported = registerReply();
  const finding = findingOnTheRegister();
  exported.rows[0].findings = [finding];
  const { panel, drawer } = await openTheRow(exported);

  expect(panel.textContent).toContain("1 finding");
  expect(drawer.textContent).toContain(finding.rule_text);
  expect(drawer.textContent).toContain(
    `Raised by run ${finding.raised_by_run}: ${finding.issue}`,
  );
  // Keyed on the finding, never on the rule: one rule can raise on one row in
  // two runs (S25).
  expect(panel.textContent).not.toContain(finding.rule_id);
});

test("a row nothing was found wrong with is never marked", async () => {
  const exported = registerReply();
  const { panel, drawer } = await openTheRow(exported);

  // The payload carries no findings key at all on a clean row (item 43).
  expect(Object.hasOwn(exported.rows[0], "findings")).toBe(false);
  expect(panel.textContent).not.toContain("finding");
  expect(drawer.textContent).not.toContain("Findings");
  expect(drawer.textContent).not.toContain("0 findings");
  expect(drawer.textContent).not.toContain("No findings");
});

test("the panel's history is this row's alone, and starts collapsed", async () => {
  const history = historyReply({
    entries: [
      ...historyReply().entries,
      {
        kind: "cell change",
        row_number: 9,
        cell: "status",
        old_value: "Requested",
        new_value: "Done",
        changed_at: "2026-03-27T09:30:00+00:00",
        run_number: 2,
        source_file: "another-row.md",
      },
    ],
  });
  const { drawer } = await openTheRow(registerReply(), history);

  const opener = within(drawer).getByRole("button", { name: /history/i });
  expect(opener.getAttribute("aria-expanded")).toBe("false");
  expect(drawer.textContent).not.toContain("another-row.md");

  fireEvent.click(opener);
  expect(drawer.textContent).toContain("testing-feedback-25-mar.md");
  expect(drawer.textContent).not.toContain("another-row.md");
});
