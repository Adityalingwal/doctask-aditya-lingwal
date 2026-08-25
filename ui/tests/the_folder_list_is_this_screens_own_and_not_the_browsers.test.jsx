// Item 1: the open folder list is drawn by this screen rather than by the
// operating system, so it has to behave like a listbox — opening, picking,
// closing on Escape and on a click outside, and saying which row is chosen.
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import AddProject from "../src/AddProject.jsx";
import { projectReply } from "./server_replies.js";

const FIRST_FOLDER = "sample-projects/intake-portal";
const SECOND_FOLDER = "sample-projects/northside-dental";
const BOTH_FOLDERS = [FIRST_FOLDER, SECOND_FOLDER];

function addProject(availableFolders, projects = []) {
  render(
    <AddProject
      projectsRoot="sample-projects"
      availableFolders={availableFolders}
      projects={projects}
      onStarted={async () => {}}
      onCreated={async () => {}}
      onClose={() => {}}
      onUnreachable={() => {}}
    />,
  );
  return screen.getByRole("button", { name: "Folder" });
}

test("the_folder_list_opens_when_the_control_is_pressed", () => {
  const control = addProject(BOTH_FOLDERS);

  expect(control.getAttribute("aria-haspopup")).toBe("listbox");
  expect(control.getAttribute("aria-expanded")).toBe("false");
  expect(screen.queryByRole("listbox")).toBeNull();

  fireEvent.click(control);

  expect(control.getAttribute("aria-expanded")).toBe("true");
  expect(
    screen.getAllByRole("option").map((option) => option.textContent),
  ).toEqual(BOTH_FOLDERS);
});

test("picking_a_folder_names_it_on_the_control_marks_it_and_closes_the_list", () => {
  const control = addProject(BOTH_FOLDERS);
  fireEvent.click(control);
  fireEvent.click(screen.getByText(SECOND_FOLDER));

  expect(screen.queryByRole("listbox")).toBeNull();
  expect(control.textContent).toContain(SECOND_FOLDER);
  expect(document.activeElement).toBe(control);

  fireEvent.click(control);
  const chosen = screen
    .getAllByRole("option")
    .filter((option) => option.getAttribute("aria-selected") === "true");
  expect(chosen.map((option) => option.textContent)).toEqual([
    `${SECOND_FOLDER}✓`,
  ]);
});

test("escape_closes_the_folder_list_and_leaves_the_choice_alone", () => {
  const control = addProject(BOTH_FOLDERS);
  fireEvent.click(control);
  fireEvent.keyDown(control, { key: "Escape" });

  expect(screen.queryByRole("listbox")).toBeNull();
  expect(control.textContent).toContain("Choose a folder");
});

test("a_click_outside_the_folder_list_closes_it", () => {
  const control = addProject(BOTH_FOLDERS);
  fireEvent.click(control);
  fireEvent.click(screen.getByText("Add project"));

  expect(screen.queryByRole("listbox")).toBeNull();
});

test("the_arrow_keys_move_down_the_folder_list_and_enter_picks", () => {
  const control = addProject(BOTH_FOLDERS);
  fireEvent.keyDown(control, { key: "ArrowDown" });
  fireEvent.keyDown(control, { key: "ArrowDown" });
  fireEvent.keyDown(control, { key: "Enter" });

  expect(control.textContent).toContain(SECOND_FOLDER);
});

test("a_dropdown_with_no_folder_left_says_so_and_never_opens", () => {
  const taken = BOTH_FOLDERS.map((folder, place) =>
    projectReply({
      project_id: `1111111${place}-2222-4333-8444-555555555555`,
      source_folder_path: folder,
    }),
  );
  const control = addProject(BOTH_FOLDERS, taken);

  expect(control.textContent).toContain("No folder left to add.");
  expect(control.disabled).toBe(true);

  fireEvent.click(control);
  expect(screen.queryByRole("listbox")).toBeNull();
});
