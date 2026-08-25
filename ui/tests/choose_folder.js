import { fireEvent, screen } from "@testing-library/react";

/**
 * Choose a folder the way a person does: open the list, then press a row.
 * The dropdown is this screen's own listbox rather than the browser's select
 * (item 1), so a test picks a folder by pressing it and not by setting a value.
 */
export function chooseFolder(folder) {
  fireEvent.click(screen.getByRole("button", { name: "Folder" }));
  fireEvent.click(screen.getByRole("option", { name: folder }));
}

/** Every folder the list offers, read with the list open. */
export function offeredFolders() {
  fireEvent.click(screen.getByRole("button", { name: "Folder" }));
  return screen.getAllByRole("option").map((option) => option.textContent);
}
