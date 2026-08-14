import { fireEvent, screen } from "@testing-library/react";

/**
 * Open one section of the run the way a person does, by its tab. One section is
 * read at a time, so a test that looks at the register or the timings has to
 * open it first.
 */
export async function openSection(name) {
  fireEvent.click(await screen.findByRole("tab", { name }));
}
