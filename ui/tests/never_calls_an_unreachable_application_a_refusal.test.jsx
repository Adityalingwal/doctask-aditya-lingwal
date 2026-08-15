// Screen 11 — an action that never reached the application is not a refusal.
// The application said nothing, so the single strip under the header is the
// only honest thing to show; a "the server refused" box beside it would put
// words in a server's mouth that was not even running.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { openSection } from "./open_section.js";
import { decisionReply, projectsReply, runId, runReply } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("never_calls_an_unreachable_application_a_refusal", async () => {
  vi.stubGlobal("fetch", async (requested, options = {}) => {
    const method = (options.method ?? "GET").toUpperCase();
    const path = new URL(requested, "http://localhost:8000").pathname;
    if (method === "POST") {
      // The application stopped between the last poll and this click.
      throw new TypeError("Failed to fetch");
    }
    if (path === "/projects") {
      return { ok: true, status: 200, json: async () => projectsReply() };
    }
    return {
      ok: true,
      status: 200,
      json: async () => runReply({ decisions: [decisionReply()] }),
    };
  });

  render(<ReviewScreen runId={runId} />);
  await openSection(/decisions/i);
  const approve = await screen.findByRole("button", { name: /approve/i });

  fireEvent.click(approve);

  await waitFor(() => {
    expect(screen.getByText(/cannot reach the application/i)).toBeTruthy();
  });
  expect(screen.queryByText(/the server refused/i)).toBeNull();
});
