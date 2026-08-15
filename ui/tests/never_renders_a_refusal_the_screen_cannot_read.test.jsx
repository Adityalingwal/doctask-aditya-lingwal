// Never-do test for section 1.4: FastAPI's own 422 validation error sends
// `detail` as a list of objects, which React cannot render. `ui/src/
// run_requests.js:63` passes `body.detail` straight through today, so this
// answer must be turned into the fixed sentence before it ever reaches a
// component, and the whole body must still reach the browser console.
import { afterEach, expect, test, vi } from "vitest";

import { createProject } from "../src/run_requests.js";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("never_renders_a_refusal_the_screen_cannot_read", async () => {
  const validationErrorBody = {
    detail: [
      {
        type: "missing",
        loc: ["body", "source_folder_path"],
        msg: "Field required",
        input: {},
      },
    ],
  };
  vi.stubGlobal("fetch", async () => ({
    ok: false,
    status: 422,
    json: async () => validationErrorBody,
  }));
  const loggedToConsole = vi.spyOn(console, "error").mockImplementation(() => {});

  const answered = await createProject("sample-projects/intake-portal");

  expect(answered.ok).toBe(false);
  expect(answered.refusal).toBe("The application did not accept this request.");
  expect(typeof answered.refusal).toBe("string");
  expect(loggedToConsole).toHaveBeenCalled();
  const loggedBody = loggedToConsole.mock.calls.flat();
  expect(JSON.stringify(loggedBody)).toContain("source_folder_path");
});

test("a string detail is still shown unchanged", async () => {
  vi.stubGlobal("fetch", async () => ({
    ok: false,
    status: 400,
    json: async () => ({ detail: "a project needs a source folder — give one." }),
  }));

  const answered = await createProject("");

  expect(answered.refusal).toBe("a project needs a source folder — give one.");
});
