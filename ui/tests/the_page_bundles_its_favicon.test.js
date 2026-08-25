import { readFileSync } from "node:fs";


const uiRoot = process.cwd();


test("the page names a bundled favicon instead of asking the site root", () => {
  const page = readFileSync(`${uiRoot}/index.html`, "utf8");
  const favicon = readFileSync(`${uiRoot}/public/favicon.svg`, "utf8");

  expect(page).toContain(
    '<link rel="icon" href="/ui/favicon.svg" type="image/svg+xml" />',
  );
  expect(favicon).toContain("<svg");
});
