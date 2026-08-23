// @vitest-environment node
//
// Items 23/31 and S17, the screen's half. `#` before a digit reads as a
// database key rather than as the row a person is looking at, and it reached
// the screen from four directions at once. The backend's side of this sweep is
// `tests/test_no_number_is_prefixed_with_a_hash.py`; this walks the sources
// the bundle is built from, so a `#1` written into any component fails here
// rather than being spotted on the screen.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

// This one file reads the repository rather than rendering anything, so it
// runs in node: under jsdom the module's own address is an http URL and the
// sources cannot be found from it.
const SOURCE_FOLDER = fileURLToPath(new URL("../src", import.meta.url));

// A colour is written the same way and is not a sentence: `#0a0a0a` and
// `#fff` are taken out before the search, so only a hash in front of a number
// a person reads is left.
const A_HEX_COLOUR = /#[0-9a-fA-F]{3,8}\b/g;
const A_HASH_BEFORE_A_DIGIT = /#\d/;

// The palette lives here, and it is the one file that is nothing but colours.
const NOT_SEARCHED = new Set(["screen.css"]);

function sourceFiles(folder) {
  return readdirSync(folder, { withFileTypes: true }).flatMap((entry) => {
    const path = join(folder, entry.name);
    if (entry.isDirectory()) {
      return sourceFiles(path);
    }
    return NOT_SEARCHED.has(entry.name) ? [] : [path];
  });
}

test("no source the screen is built from puts a hash in front of a number", () => {
  const offenders = sourceFiles(SOURCE_FOLDER).filter((path) =>
    A_HASH_BEFORE_A_DIGIT.test(
      readFileSync(path, "utf-8").replaceAll(A_HEX_COLOUR, ""),
    ),
  );

  expect(offenders).toEqual([]);
});
