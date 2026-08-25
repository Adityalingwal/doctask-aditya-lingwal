// L8 — the Add-project button sits at the bottom of the projects column in
// every state the columns are actually drawn in (screen 1). While the
// application has never actually answered `GET /projects` even once,
// screen 10's own rule governs instead: no empty column and no placeholder
// box is ever drawn, so the button (and the box it would open) is not
// offered in place of that unconfirmed state either — only the loading line
// and the cannot-reach strip are.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { projectsReply, serverAnswering } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("never_offers_the_add_project_box_in_place_of_a_refusal", async () => {
  vi.stubGlobal(
    "fetch",
    async () => {
      throw new TypeError("Failed to fetch");
    },
  );

  render(<ReviewScreen />);

  await waitFor(() => {
    expect(screen.getByText(/cannot reach the application/i)).toBeTruthy();
  });

  expect(screen.getByText("Loading…")).toBeTruthy();
  expect(screen.queryByRole("button", { name: /add project/i })).toBeNull();
  expect(screen.queryByLabelText(/folder/i)).toBeNull();
});

// Confirms the passing case really is "never confirmed", not that the button
// is simply broken: once the read succeeds — even with zero projects and
// zero folders — the button is there, and its dropdown lists exactly what
// the server answered with, never an invented option.
test("the button and its dropdown appear once the read succeeds, offering only confirmed folders", async () => {
  vi.stubGlobal(
    "fetch",
    serverAnswering([
      {
        method: "GET",
        path: "/projects",
        reply: { body: projectsReply({ projects: [], available_folders: [] }) },
      },
    ]),
  );

  render(<ReviewScreen />);
  await waitFor(() => {
    expect(screen.getByText("No project created yet.")).toBeTruthy();
  });

  fireEvent.click(screen.getByRole("button", { name: /add project/i }));

  // No folder was confirmed, so the dropdown offers none and says so rather
  // than inventing one.
  const folderField = screen.getByRole("button", { name: "Folder" });
  expect(folderField.textContent).toContain("No folder left to add.");
  fireEvent.click(folderField);
  expect(screen.queryByRole("option")).toBeNull();
});
