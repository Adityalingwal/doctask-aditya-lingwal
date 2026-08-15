// Never-do test for section 1.5: when every folder already has a project, the
// dropdown stays where it is and shows exactly one line — no options.
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import AddProject from "../src/AddProject.jsx";
import { projectReply } from "./server_replies.js";

test("shows_one_line_when_no_folder_is_left_to_add", () => {
  const both = [
    projectReply({ source_folder_path: "sample-projects/intake-portal" }),
    projectReply({
      project_id: "22222222-3333-4444-5555-666677778888",
      source_folder_path: "sample-projects/northside-dental",
    }),
  ];

  render(
    <AddProject
      projectsRoot="sample-projects"
      availableFolders={[
        "sample-projects/intake-portal",
        "sample-projects/northside-dental",
      ]}
      projects={both}
      onStarted={async () => {}}
      onClose={() => {}}
      onUnreachable={() => {}}
    />,
  );

  expect(screen.getByText("No folder left to add.")).toBeTruthy();
  expect(screen.getAllByRole("option")).toHaveLength(1);
});
