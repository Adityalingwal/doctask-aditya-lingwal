import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

import serveDemoRuns from "./demo/serve_demo_runs.js";

// The screen is served by FastAPI under /ui/, so every built asset must be
// requested relative to that prefix rather than the site root.
export default defineConfig({
  base: "/ui/",
  plugins: [react(), tailwindcss(), serveDemoRuns()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
