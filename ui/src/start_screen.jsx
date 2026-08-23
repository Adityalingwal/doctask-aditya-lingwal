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

// What is on screen is named in the address, so a link to it is a link a
// reviewer can keep: /ui/?project=<project id>&run=<run id>. A project alone
// opens that project's newest run; a run alone still works, because the run's
// own answer names its project.
const address = new URLSearchParams(window.location.search);
const openedProjectId = address.get("project") ?? "";
const openedRunId = address.get("run") ?? "";

createRoot(document.getElementById("review-screen")).render(
  <StrictMode>
    <ReviewScreen projectId={openedProjectId} runId={openedRunId} />
  </StrictMode>,
);
