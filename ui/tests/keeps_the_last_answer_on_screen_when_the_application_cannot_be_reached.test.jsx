// Screen 11 — whatever this screen last read stays on it, unchanged, once
// the application stops answering: erasing it saves nothing and takes away
// the reviewer's context, and the strip already says the screen is not
// current.
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import ReviewScreen from "../src/ReviewScreen.jsx";
import { projectsReply } from "./server_replies.js";

afterEach(() => {
  vi.unstubAllGlobals();
});

test(
  "keeps_the_last_answer_on_screen_when_the_application_cannot_be_reached",
  async () => {
    let calls = 0;
    vi.stubGlobal("fetch", async () => {
      calls += 1;
      if (calls === 1) {
        return { ok: true, status: 200, json: async () => projectsReply() };
      }
      // Every poll after the first never reaches the application.
      throw new TypeError("Failed to fetch");
    });

    render(<ReviewScreen />);
    await waitFor(() => {
      expect(screen.getByText("Acme intake portal")).toBeTruthy();
    });

    // The next poll (screen.json's poll_interval_ms) fails to reach the
    // application; wait past it for real, since the interval is real.
    await waitFor(
      () => {
        expect(screen.getByText(/cannot reach the application/i)).toBeTruthy();
      },
      { timeout: 6000 },
    );

    // What was last read is still exactly on screen underneath the strip.
    expect(screen.getByText("Acme intake portal")).toBeTruthy();
    expect(screen.getByText(/1 run/)).toBeTruthy();
  },
  8000,
);
