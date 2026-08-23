import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  projectId,
  projectReply,
  projectsReply,
  registerReply,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

// The register is the project's own panel (section 2.3), reached from the
// Register entry above a project's runs. What a row rests on lives in the
// panel that row opens (item 16), not in a list under the table.
function exportedProject(rowCount) {
  const run = { ...projectReply().runs[0], row_count: rowCount };
  return projectReply({ runs: [run] });
}

async function openFirstRow(exported) {
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
        reply: { body: { entries: [] } },
      },
    ]),
  );

  render(<ReviewScreen projectId="" runId="" />);
  fireEvent.click(await screen.findByText(exportedProject(1).name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  fireEvent.click(await screen.findByText(exported.rows[0].cells.what_was_asked));
  return await screen.findByRole("complementary", { name: /row 1/i });
}

test("every quote names the source line the server gave it", async () => {
  const exported = registerReply();
  const drawer = await openFirstRow(exported);

  const [quoted, absent] = exported.rows[0].evidence;
  const shown = within(drawer)
    .getAllByRole("listitem")
    .map((item) => item.textContent);

  const quotedEntry = shown.find((text) => text.includes(quoted.quote));
  expect(quotedEntry).toBeTruthy();
  expect(quotedEntry).toContain(quoted.source_line);
  // The cells resting on those words, named as the table names them.
  expect(quotedEntry).toContain(quoted.cells[0]);

  // A silence has no place to point at, so the sentence names the file.
  const absentEntry = shown.find((text) => text.includes(absent.absence));
  expect(absentEntry).toBeTruthy();
  expect(absentEntry).toContain(absent.cells[0]);
});

test("an absence is never shown as a quote", async () => {
  const exported = registerReply();
  exported.rows[0].evidence = [
    {
      source_line: null,
      quote: null,
      absence: "12-march-scope.md was read, and it does not mention this ask.",
      cells: ["What was asked"],
    },
  ];
  const drawer = await openFirstRow(exported);

  expect(drawer.textContent).toContain("12-march-scope.md");
  expect(drawer.textContent).toContain("does not mention this ask");
  expect(drawer.textContent).not.toContain('""');
  expect(drawer.textContent).not.toContain("null");
});
