import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import {
  exportReply,
  projectReply,
  projectsReply,
  runId,
  serverAnswering,
} from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

function exportedProject(rowCount) {
  const run = { ...projectReply().runs[0], row_count: rowCount };
  return projectReply({ runs: [run] });
}

async function openRegister(exported) {
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
      { method: "GET", path: `/runs/${runId}/export`, reply: { body: exported } },
    ]),
  );

  render(<ReviewScreen runId="" />);
  fireEvent.click(await screen.findByText(exportedProject(1).name));
  fireEvent.click(await screen.findByRole("link", { name: /register/i }));
  return screen.findByRole("region", { name: /register/i });
}

test("the register heads the written-down cell with the question it asks", async () => {
  const register = await openRegister(exportReply());

  expect(
    within(register).getByRole("columnheader", { name: "Written down?" }),
  ).toBeTruthy();
  expect(register.textContent).not.toContain("In writing?");
  // The server still sends the stored column key; only the heading moved.
  expect(register.textContent).not.toContain("in_writing");
});

test("the register shows the four cells and no heading for a cell that left", async () => {
  const register = await openRegister(exportReply());

  expect(
    within(register)
      .getAllByRole("columnheader")
      .map((heading) => heading.textContent),
  ).toEqual(["#", "What was asked", "Written down?", "What testing found", "Status"]);
  for (const gone of ["Blocked on", "First seen", "Last moved"]) {
    expect(register.textContent).not.toContain(gone);
  }
});
