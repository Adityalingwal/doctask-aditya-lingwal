import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The screen is served by FastAPI under /ui/, so every built asset must be
// requested relative to that prefix rather than the site root.
export default defineConfig({
  base: "/ui/",
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
  },
});
