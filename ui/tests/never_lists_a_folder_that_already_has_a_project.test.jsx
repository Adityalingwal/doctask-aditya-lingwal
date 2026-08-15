// Never-do test for "a folder is a project" (handoff/brief-folder-is-a-project-
// and-register-moves.md, section 1.5). The dropdown must show only folders
// that do not already carry a project — the difference between
// `available_folders` and every project's own `source_folder_path`.
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import AddProject from "../src/AddProject.jsx";
import { projectReply } from "./server_replies.js";

test("never_lists_a_folder_that_already_has_a_project", () => {
  const taken = projectReply({ source_folder_path: "sample-projects/intake-portal" });

  render(
    <AddProject
      projectsRoot="sample-projects"
      availableFolders={[
        "sample-projects/intake-portal",
        "sample-projects/northside-dental",
      ]}
      projects={[taken]}
      onStarted={async () => {}}
      onClose={() => {}}
      onUnreachable={() => {}}
    />,
  );

  const options = screen
    .getAllByRole("option")
    .map((option) => option.textContent);

  expect(options).not.toContain("sample-projects/intake-portal");
  expect(options.join(" ")).toContain("sample-projects/northside-dental");
});
