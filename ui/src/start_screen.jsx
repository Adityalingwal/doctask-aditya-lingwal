import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/600.css";

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
