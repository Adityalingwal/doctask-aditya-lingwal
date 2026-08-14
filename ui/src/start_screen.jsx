import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Latin only. The full subset set ships Cyrillic, Greek and Vietnamese too, and
// everything this system produces is English (TASK.md), so they would be
// twenty-odd font files nobody ever downloads.
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-600.css";

import ReviewScreen from "./ReviewScreen.jsx";
import "./screen.css";

// The run to review is named in the address, so a link to one run is a link a
// reviewer can keep: /ui/?run=<run id>.
const openedRunId = new URLSearchParams(window.location.search).get("run") ?? "";

createRoot(document.getElementById("review-screen")).render(
  <StrictMode>
    <ReviewScreen runId={openedRunId} />
  </StrictMode>,
);
